# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Proving a membership you already hold — the member's own submission.

`test_proof.py` covers the clerk's half of Proof-of-Membership: a coordinator
enters a pre-rollout member, attaches the evidence, and the routed approval runs
with no gateway involved. This suite covers the half where **the member fills
the form in themselves**, and everything it asserts follows from the one thing
that makes those two situations different — a clerk is recording what the
society knows, and an applicant is claiming something nobody has checked.

So the assertions here are mostly about a boundary rather than a feature:

    claimed dates never reach `valid_from`, on any path, ever
    an unverified claim cannot be approved at all
    a verified date is attributable — who confirmed it, and when
    the applicant's endpoint cannot name a verified field

Every test drives the real endpoints and the real engine. Nothing calls
`activate()` directly or writes a state by hand, because the questions worth
asking are all about which door a value came through.
"""

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.approvals import states
from vmmsx.approvals.services import engine
from vmmsx.member.services import approval
from vmmsx.member.services import membership as membership_service
from vmmsx.member.services import proof
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase
from vmmsx.registration.services import declarations as declaration_service

EXTRA_TEST_RECORD_DEPENDENCIES = []

# Long enough ago to be plainly historical, and derived rather than written down
# so that "expired two years ago" stays true after 2027.
JOINED_YEARS_AGO = 6


def years_ago(years: int) -> str:
	return str(add_days(getdate(today()), -365 * years))


class ProofSubmissionTestCase(MemberTestCase):
	"""Shared world: a routed fee-charging type, a lifetime type, and an approver.

	The fee is deliberate, and `test_proof.py` says why: a pre-rollout member
	belongs to the society's ordinary paying type, so "no gateway transaction was
	created" has to be true of a type that charges rather than true by accident of
	one that does not.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.approver = cls.scoped_user("proof_sub_approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])
		fixtures.make_workflow(applicant_field="member")
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.make_template()

		cls.fixed_type = fixtures.make_type(fixtures.TYPE_PROOF, approval.MODE_ROUTED, fee=500)
		cls.lifetime_type = fixtures.make_type(
			fixtures.TYPE_LIFETIME, approval.MODE_ROUTED, fee=500, is_lifetime=1, duration_days=0
		)

		# Additive and idempotent. The declaration reaches a migrated site through
		# `after_migrate`; a suite must not depend on when that last ran.
		declaration_service.install()

	# --- the applicant's door ---------------------------------------------

	def applicant(self, handle: str, first: str = "Proof", last: str = "Claimant"):
		"""Somebody signed in, with a profile core can resolve from their login."""
		user = fixtures.make_user(handle)
		profile = fixtures.make_profile(first, last, user=user)

		return user, profile

	def submit_claim(self, user: str, type_key: str | None = None, **claim):
		"""Post a proof of an existing membership, as the applicant themselves."""
		from vmmsx.api import registration as registration_api

		values = {
			"membership_type": type_key or fixtures.TYPE_PROOF,
			"geo_node": self.society_a["ward"],
			"proof_attachment": fixtures.make_proof_file(),
			"proof_claimed_start_date": years_ago(JOINED_YEARS_AGO),
			"proof_claimed_expiry_date": years_ago(JOINED_YEARS_AGO - 1),
			"proof_membership_number": "TRCS/2019/00412",
			"proof_registered_at": "Kinondoni Branch",
			"proof_reference_number": "RCT-88120",
			"declarations_accepted": self.required_declarations(),
		}
		values.update(claim)

		with fixtures.acting_as(user):
			return registration_api.register_existing_membership(**values)

	def required_declarations(self) -> list[str]:
		from vmmsx.registration.tests.fixtures import required_declarations

		return required_declarations(fixtures.MEMBERSHIP_DOCTYPE)

	def verify(self, name: str, start=None, expiry=None) -> dict:
		"""Record what the approver read off the document, through the real endpoint."""
		from vmmsx.api import member as member_api

		with fixtures.acting_as(self.approver):
			return member_api.verify_membership_proof(
				membership=name,
				proof_verified_start_date=start,
				proof_verified_expiry_date=expiry,
			)

	def approve(self, name: str) -> None:
		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(name), states.DECISION_APPROVED)


class TestTheThreeProofPaths(ProofSubmissionTestCase):
	"""Lifetime, still-current, and already-expired — the acceptance criterion."""

	def test_a_lifetime_membership_is_recorded_with_no_end_date(self):
		user, _profile = self.applicant("proof_lifetime")
		result = self.submit_claim(
			user, type_key=fixtures.TYPE_LIFETIME, proof_claimed_expiry_date=None
		)

		self.verify(result["name"], start=years_ago(JOINED_YEARS_AGO))
		self.approve(result["name"])

		membership = self.reload(result["name"])

		self.assertEqual(membership.membership_status, membership_service.STATUS_ACTIVE)
		self.assertEqual(membership.valid_from, getdate(years_ago(JOINED_YEARS_AGO)))
		# Empty rather than a far-future sentinel, which is the whole of what
		# lifetime means in this app — see `membership._valid_to`.
		self.assertIsNone(membership.valid_to)

	def test_a_still_current_fixed_period_keeps_the_dates_the_approver_confirmed(self):
		user, _profile = self.applicant("proof_current")
		start = years_ago(2)
		expiry = str(add_days(getdate(today()), 90))

		result = self.submit_claim(
			user, proof_claimed_start_date=start, proof_claimed_expiry_date=expiry
		)

		self.verify(result["name"], start=start, expiry=expiry)
		self.approve(result["name"])

		membership = self.reload(result["name"])

		self.assertEqual(membership.membership_status, membership_service.STATUS_ACTIVE)
		self.assertEqual(membership.valid_from, getdate(start))
		self.assertEqual(membership.valid_to, getdate(expiry))
		# Not the fresh period. If `activate()` had ignored the verified dates
		# this would be today, and the person would have been silently handed a
		# year they did not have.
		self.assertNotEqual(membership.valid_from, getdate(today()))

	def test_a_membership_proved_to_have_expired_is_recorded_as_expired(self):
		user, _profile = self.applicant("proof_expired")
		start = years_ago(JOINED_YEARS_AGO)
		expiry = years_ago(2)

		result = self.submit_claim(
			user, proof_claimed_start_date=start, proof_claimed_expiry_date=expiry
		)

		self.verify(result["name"], start=start, expiry=expiry)
		self.approve(result["name"])

		membership = self.reload(result["name"])

		self.assertEqual(membership.membership_status, membership_service.STATUS_EXPIRED)
		self.assertEqual(membership.valid_to, getdate(expiry))
		# The approval itself succeeded. The society verified a true fact about a
		# membership that has run out; what it must not do is call that person a
		# current member.
		self.assertEqual(membership.approval_state, states.APPROVED)

	def test_an_expired_proof_lands_the_member_on_the_renewal_path(self):
		""""Direct the member to renewal" — the state renewal already opens from."""
		from vmmsx.member.services import renewal

		user, _profile = self.applicant("proof_renewable")
		result = self.submit_claim(
			user,
			proof_claimed_start_date=years_ago(JOINED_YEARS_AGO),
			proof_claimed_expiry_date=years_ago(2),
		)

		self.verify(result["name"], start=years_ago(JOINED_YEARS_AGO), expiry=years_ago(2))
		self.approve(result["name"])

		self.assertTrue(renewal.is_renewable(self.reload(result["name"])))

	def test_the_member_is_never_briefly_active_on_the_way_to_expired(self):
		"""The status is decided once, in `activate`, not corrected by the sweep."""
		user, _profile = self.applicant("proof_never_active")
		result = self.submit_claim(
			user,
			proof_claimed_start_date=years_ago(JOINED_YEARS_AGO),
			proof_claimed_expiry_date=years_ago(2),
		)

		self.verify(result["name"], start=years_ago(JOINED_YEARS_AGO), expiry=years_ago(2))
		self.approve(result["name"])

		# The daily sweep finds nothing to do, because nothing was ever wrongly
		# Active for it to find.
		self.assertEqual(membership_service.expire_lapsed()["expired"], 0)


class TestNoMoneyChangesHands(ProofSubmissionTestCase):
	def test_a_proof_submission_creates_no_payment_transaction(self):
		user, _profile = self.applicant("proof_no_payment")
		result = self.submit_claim(user)

		membership = self.reload(result["name"])

		self.assertFalse(membership.payment_transaction)
		self.assertFalse(membership.payment_receipt)
		self.assertFalse(membership.paid_on)
		# On a type that charges 500. If it were free, this would pass for the
		# wrong reason.
		self.assertTrue(self.fixed_type.fee_amount)

	def test_no_payment_transaction_exists_after_approval_either(self):
		user, _profile = self.applicant("proof_no_payment_after")
		result = self.submit_claim(user)

		self.verify(result["name"], start=years_ago(3), expiry=str(add_days(getdate(today()), 30)))
		self.approve(result["name"])

		membership = self.reload(result["name"])

		self.assertEqual(membership.membership_status, membership_service.STATUS_ACTIVE)
		self.assertFalse(membership.payment_transaction)


class TestAClaimIsNotAFact(ProofSubmissionTestCase):
	"""The acceptance criterion: claimed dates cannot silently become official."""

	def test_a_claim_alone_never_sets_the_validity(self):
		user, _profile = self.applicant("proof_claim_only")
		result = self.submit_claim(user)

		membership = self.reload(result["name"])

		self.assertEqual(membership.proof_claimed_start_date, getdate(years_ago(JOINED_YEARS_AGO)))
		self.assertFalse(membership.valid_from)
		self.assertFalse(membership.valid_to)
		self.assertFalse(membership.proof_verified_start_date)

	def test_an_unverified_claim_cannot_be_approved(self):
		user, _profile = self.applicant("proof_unverified")
		result = self.submit_claim(user)

		with self.assertRaises(frappe.MandatoryError):
			self.approve(result["name"])

		# And it is still sitting where it was, rather than half-decided.
		self.assertNotEqual(self.reload(result["name"]).approval_state, states.APPROVED)
		self.assertNotEqual(
			self.membership_status(result["name"]), membership_service.STATUS_ACTIVE
		)

	def test_a_fixed_period_claim_verified_without_an_expiry_cannot_be_approved(self):
		user, _profile = self.applicant("proof_half_verified")
		result = self.submit_claim(user)

		self.verify(result["name"], start=years_ago(3))

		with self.assertRaises(frappe.MandatoryError):
			self.approve(result["name"])

	def test_the_approver_can_correct_the_claim_and_the_correction_is_what_counts(self):
		"""The case the whole split exists for: the applicant was wrong."""
		user, _profile = self.applicant("proof_corrected")
		claimed_start = years_ago(JOINED_YEARS_AGO)
		result = self.submit_claim(user, proof_claimed_start_date=claimed_start)

		# The document said 2021, not what they remembered.
		confirmed_start = years_ago(3)
		confirmed_expiry = str(add_days(getdate(today()), 200))

		self.verify(result["name"], start=confirmed_start, expiry=confirmed_expiry)
		self.approve(result["name"])

		membership = self.reload(result["name"])

		self.assertEqual(membership.valid_from, getdate(confirmed_start))
		self.assertNotEqual(membership.valid_from, getdate(claimed_start))
		# The claim survives beside it. An approver who corrected a date has not
		# erased what they were told.
		self.assertEqual(membership.proof_claimed_start_date, getdate(claimed_start))

	def test_a_verification_is_attributable(self):
		user, _profile = self.applicant("proof_attributable")
		result = self.submit_claim(user)

		self.verify(result["name"], start=years_ago(3), expiry=str(add_days(getdate(today()), 30)))

		membership = self.reload(result["name"])

		self.assertEqual(membership.proof_verified_by, self.approver)
		self.assertTrue(membership.proof_verified_on)

	def test_the_applicant_cannot_send_a_verified_date(self):
		"""The allow-list, tested at the door rather than trusted.

		`CLAIM_FIELDS` is what the endpoint accepts, and the four verified fields
		are not in it. This asserts the endpoint has no parameter for one at all —
		a `TypeError`, not a silently ignored value — because a field that is
		merely dropped today is a field somebody adds to a `**kwargs` next year.
		"""
		from vmmsx.api import registration as registration_api

		user, _profile = self.applicant("proof_tamperer")

		with fixtures.acting_as(user), self.assertRaises(TypeError):
			registration_api.register_existing_membership(
				membership_type=fixtures.TYPE_PROOF,
				geo_node=self.society_a["ward"],
				proof_attachment=fixtures.make_proof_file(),
				proof_claimed_start_date=years_ago(3),
				proof_verified_start_date=years_ago(3),
			)

		for field in proof.VERIFIED_FIELDS:
			self.assertNotIn(field, proof.CLAIM_FIELDS)

	def test_the_applicant_cannot_verify_their_own_proof(self):
		from vmmsx.api import member as member_api

		user, _profile = self.applicant("proof_self_verifier")
		result = self.submit_claim(user)

		with fixtures.acting_as(user), self.assertRaises(frappe.PermissionError):
			member_api.verify_membership_proof(
				membership=result["name"], proof_verified_start_date=years_ago(3)
			)


class TestWhatTheFormMustSay(ProofSubmissionTestCase):
	def test_a_claim_with_no_start_date_is_refused(self):
		user, _profile = self.applicant("proof_no_start")

		with self.assertRaises(frappe.MandatoryError):
			self.submit_claim(user, proof_claimed_start_date=None)

	def test_a_fixed_period_claim_with_no_expiry_is_refused(self):
		user, _profile = self.applicant("proof_no_expiry")

		with self.assertRaises(frappe.MandatoryError):
			self.submit_claim(user, proof_claimed_expiry_date=None)

	def test_a_lifetime_claim_with_an_expiry_is_refused(self):
		user, _profile = self.applicant("proof_lifetime_expiry")

		with self.assertRaises(frappe.ValidationError):
			self.submit_claim(
				user, type_key=fixtures.TYPE_LIFETIME, proof_claimed_expiry_date=years_ago(1)
			)

	def test_dates_out_of_order_are_refused(self):
		user, _profile = self.applicant("proof_backwards")

		with self.assertRaises(frappe.ValidationError):
			self.submit_claim(
				user,
				proof_claimed_start_date=years_ago(1),
				proof_claimed_expiry_date=years_ago(4),
			)

	def test_a_submission_with_no_attachment_is_refused(self):
		user, _profile = self.applicant("proof_no_file")

		with self.assertRaises(frappe.MandatoryError):
			self.submit_claim(user, proof_attachment="")

	def test_an_attachment_that_was_not_uploaded_here_is_refused(self):
		user, _profile = self.applicant("proof_foreign_file")

		with self.assertRaises(frappe.ValidationError):
			self.submit_claim(user, proof_attachment="https://example.invalid/receipt.png")

	def test_the_declaration_must_be_accepted(self):
		user, _profile = self.applicant("proof_no_declaration")

		with self.assertRaises(frappe.MandatoryError):
			self.submit_claim(user, declarations_accepted=[])

	def test_the_declaration_is_stored_with_the_wording_that_was_agreed_to(self):
		user, _profile = self.applicant("proof_declaration_snapshot")
		result = self.submit_claim(user)

		accepted = declaration_service.accepted_of(self.reload(result["name"]))
		rows = [row for row in accepted if row["accepted"]]

		self.assertTrue(rows)

		for row in rows:
			self.assertTrue(row["body"])
			self.assertTrue(row["version"])
			self.assertTrue(row["accepted_on"])


class TestOrdinaryMembershipsAreUnaffected(ProofSubmissionTestCase):
	"""The rules above govern claims. Nothing else may have changed underneath."""

	def test_a_gateway_membership_records_no_declaration_refusal(self):
		"""The distinction between "asked and refused" and "never asked".

		`VMMS Membership` now carries a declaration, and it is about uploaded
		evidence. An ordinary member registration does not show it, so it must not
		leave a row saying they declined it — see
		`api/registration._apply_declarations`.
		"""
		from vmmsx.api import registration as registration_api

		user, _profile = self.applicant("proof_gateway_clean", "Gateway", "Applicant")
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=600)

		with fixtures.acting_as(user):
			result = registration_api.register_as_member(
				membership_type=fixtures.TYPE_AUTO, geo_node=self.society_a["ward"]
			)

		self.assertEqual(self.reload(result["name"]).get("declarations"), [])

	def test_a_clerks_proof_entry_still_gets_the_fresh_period(self):
		"""MEM-01's path, untouched. There is no claim, so there is nothing to verify."""
		profile = fixtures.make_profile("Clerk", "Entered")
		membership = fixtures.make_membership(
			profile,
			fixtures.TYPE_PROOF,
			self.society_a["ward"],
			membership_source="Proof",
			proof_attachment=fixtures.make_proof_file(),
		)
		membership_service.submit(membership)

		self.approve(membership.name)

		record = self.reload(membership.name)
		start = getdate(today())

		self.assertEqual(record.membership_status, membership_service.STATUS_ACTIVE)
		self.assertEqual(record.valid_from, start)
		self.assertEqual(record.valid_to, add_days(start, self.fixed_type.duration_days))


class TestDuplicatesAndRetries(ProofSubmissionTestCase):
	def test_a_second_open_submission_is_refused(self):
		user, _profile = self.applicant("proof_second_open")
		self.submit_claim(user)

		with self.assertRaises(frappe.ValidationError):
			self.submit_claim(user)

	def test_proving_a_plan_the_member_already_holds_is_refused(self):
		user, _profile = self.applicant("proof_already_held")
		first = self.submit_claim(user)

		self.verify(first["name"], start=years_ago(2), expiry=str(add_days(getdate(today()), 90)))
		self.approve(first["name"])

		self.assertEqual(
			self.membership_status(first["name"]), membership_service.STATUS_ACTIVE
		)

		with self.assertRaises(frappe.ValidationError):
			self.submit_claim(user)

	def test_a_lapsed_membership_does_not_block_a_new_one(self):
		"""The duplicate rule asks whether a membership is *current*, not stored-Active.

		Without that, proving an expired membership would lock the member out of
		the renewal the expiry was supposed to send them to.
		"""
		user, _profile = self.applicant("proof_lapsed_then_new")
		first = self.submit_claim(user)

		self.verify(first["name"], start=years_ago(JOINED_YEARS_AGO), expiry=years_ago(2))
		self.approve(first["name"])

		self.assertEqual(
			self.membership_status(first["name"]), membership_service.STATUS_EXPIRED
		)

		# The second submission is accepted, which is what "direct them to
		# renewal" needs to be true.
		self.submit_claim(user)

	def test_a_returned_submission_is_corrected_rather_than_duplicated(self):
		user, _profile = self.applicant("proof_returned")
		first = self.submit_claim(user)

		with fixtures.acting_as(self.approver):
			engine.decide(
				self.reload(first["name"]),
				states.DECISION_MORE_INFO,
				"The receipt is not readable. Please upload a clearer photograph.",
			)

		self.assertEqual(self.approval_state(first["name"]), states.DRAFT)

		corrected = self.submit_claim(user, proof_registered_at="Ilala Branch")

		# The same record, corrected — not a second membership beside it.
		self.assertEqual(corrected["name"], first["name"])
		self.assertEqual(
			frappe.db.count(fixtures.MEMBERSHIP_DOCTYPE, {"name": ("in", [first["name"]])}), 1
		)
		self.assertEqual(self.reload(first["name"]).proof_registered_at, "Ilala Branch")

	def test_the_returned_submission_carries_the_reason_back_to_the_applicant(self):
		from vmmsx.api import registration as registration_api

		user, _profile = self.applicant("proof_returned_reason")
		result = self.submit_claim(user)

		with fixtures.acting_as(self.approver):
			engine.decide(
				self.reload(result["name"]), states.DECISION_MORE_INFO, "The receipt is not readable."
			)

		with fixtures.acting_as(user):
			open_now = registration_api.my_open_registrations()

		self.assertEqual(open_now["member"]["reason"], "The receipt is not readable.")
		self.assertTrue(open_now["member"]["reviewed"])

	def test_a_returned_submission_still_reads_back_what_was_claimed(self):
		from vmmsx.api import registration as registration_api

		user, _profile = self.applicant("proof_returned_dto")
		result = self.submit_claim(user)

		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(result["name"]), states.DECISION_MORE_INFO, "Unreadable.")

		with fixtures.acting_as(user):
			dto = registration_api.my_registration("member")

		self.assertEqual(dto["membership_source"], membership_service.SOURCE_PROOF)
		self.assertEqual(dto["claimed"]["proof_membership_number"], "TRCS/2019/00412")
		# The society's own verification is not part of what the applicant's form
		# round-trips, in either direction.
		self.assertNotIn("verified", dto)


class TestTheProofFileIsPrivate(ProofSubmissionTestCase):
	def test_the_uploaded_proof_is_made_private_and_anchored(self):
		user, _profile = self.applicant("proof_private")
		result = self.submit_claim(user)

		membership = self.reload(result["name"])
		record = frappe.get_doc("File", {"file_url": membership.proof_attachment})

		self.assertTrue(record.is_private)
		self.assertTrue(membership.proof_attachment.startswith("/private/files/"))
		# Anchored, which is what makes it readable by exactly the people who may
		# read the membership — see `evidence.secure`.
		self.assertEqual(record.attached_to_doctype, fixtures.MEMBERSHIP_DOCTYPE)
		self.assertEqual(record.attached_to_name, membership.name)

	def test_the_approver_can_read_the_proof(self):
		"""Private is not the same as unreachable, and the anchor is the difference.

		A private `File` with no `attached_to_doctype` belongs to whoever uploaded
		it and to nobody else, so an approver would see a filename and get a
		permission error clicking it. Anchored, it inherits the membership's own
		permissions — which are already the right answer.
		"""
		user, _profile = self.applicant("proof_approver_reads")
		result = self.submit_claim(user)

		record = frappe.get_doc(
			"File", {"file_url": self.reload(result["name"]).proof_attachment}
		)

		with fixtures.acting_as(self.approver):
			self.assertTrue(frappe.has_permission("File", doc=record.name))

	def test_nobody_else_can_read_the_membership_the_proof_hangs_off(self):
		user, _profile = self.applicant("proof_owner")
		result = self.submit_claim(user)

		stranger = fixtures.make_user("proof_stranger")

		with fixtures.acting_as(stranger), self.assertRaises(frappe.PermissionError):
			frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, result["name"]).check_permission("read")


class TestTheApproverSeesBothHalves(ProofSubmissionTestCase):
	def test_the_review_dto_keeps_the_claim_and_the_verification_apart(self):
		from vmmsx.api import member as member_api

		user, _profile = self.applicant("proof_review_dto")
		result = self.submit_claim(user)

		with fixtures.acting_as(self.approver):
			before = member_api.get_review(result["name"])

		self.assertIsNotNone(before["claimed"])
		self.assertIsNone(before["verified"])
		self.assertEqual(before["claimed"]["proof_registered_at"], "Kinondoni Branch")

		self.verify(result["name"], start=years_ago(3), expiry=years_ago(1))

		with fixtures.acting_as(self.approver):
			after = member_api.get_review(result["name"])

		self.assertEqual(after["claimed"]["proof_claimed_start_date"], years_ago(JOINED_YEARS_AGO))
		self.assertEqual(after["verified"]["proof_verified_start_date"], years_ago(3))
		# The approver is warned before deciding that what they have recorded is
		# an expired membership, by the same derivation `activate` will use.
		self.assertTrue(after["verified"]["expired"])

	def test_a_gateway_membership_has_nothing_to_verify(self):
		from vmmsx.api import member as member_api

		profile = fixtures.make_profile("Gateway", "NothingToVerify")
		fixtures.make_type(fixtures.TYPE_ROUTED, approval.MODE_ROUTED, fee=400)
		membership = fixtures.make_membership(profile, fixtures.TYPE_ROUTED, self.society_a["ward"])
		membership_service.submit(membership)

		with fixtures.acting_as(self.approver), self.assertRaises(frappe.ValidationError):
			member_api.verify_membership_proof(
				membership=membership.name, proof_verified_start_date=years_ago(3)
			)
