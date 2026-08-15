# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The coordinator's complete view of a member, and the discipline behind it.

Four properties are under test here, and each one is written so that it fails if
the property stops holding rather than if the code merely changes shape:

1. **Completeness.** Opening one member answers every question a coordinator
   has about them — who they are, what they are, what they hold at every branch,
   how each was paid for, and who verified it — in one call.
2. **One instant.** Every date-derived answer on that screen is derived as at
   the same moment, including the ones nested inside another DTO. The test for
   this asks the dossier about a date in the past and asserts the *inner*
   derivation moved with it, which is the half that is easy to lose.
3. **Nothing is duplicated.** Identity stays on core's Red Profile, the gateway
   stays in the payments app, and the membership facts stay on the memberships.
   Each is proved by changing the value at its source and watching this app's
   own row stay byte-identical while the screen changes.
4. **Scope is the floor.** The register and the dossier's membership block both
   end in `frappe.get_list`. The leak test builds a member visible to nobody in
   the caller's scope and asserts they never come back.

Nothing here is mocked. Geo comes from core's fixtures, payment from the real
`onerc_payments` Manual driver, and approval from the real engine.
"""

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.api import member as member_api
from vmmsx.member.services import approval
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

# Every field `VMMS Member` is allowed to hold. Listed explicitly, so that a
# thirteenth column added to the doctype fails this suite and has to be argued
# for rather than arriving quietly. See `TestIdentityIsNotDuplicated`.
MEMBER_OWNED_FIELDS = frozenset(
	{
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"naming_series",
		"red_profile",
		"status",
		"joined_on",
		"notes",
		"_user_tags",
		"_comments",
		"_assign",
		"_liked_by",
	}
)

# Names of identity facts that must never become columns on the member record.
IDENTITY_FIELDS = (
	"full_name",
	"first_name",
	"last_name",
	"email",
	"phone",
	"gender",
	"date_of_birth",
	"nationality",
	"citizenship_status",
	"profile_photo",
	"home_geo_node",
)


class DossierTestCase(MemberTestCase):
	"""One person, memberships at two branches, and a coordinator who may see both."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=600)
		fixtures.make_type(fixtures.TYPE_FREE, approval.MODE_ROUTED, fee=0)
		fixtures.make_type(fixtures.TYPE_PROOF, approval.MODE_ROUTED, fee=1200)

		# The workflow's stage links to this role, so it has to exist before the
		# workflow is saved. Every other suite creates it as a side effect of
		# making its approver user; this one states it, because its approver is
		# built later and only by the proof-of-membership class.
		fixtures.make_role(fixtures.APPROVER_ROLE)
		fixtures.make_workflow()
		fixtures.grant_membership_access(fixtures.SCOPE_ROLE)
		fixtures.grant_member_access(fixtures.SCOPE_ROLE)

		cls.coordinator = cls.scoped_user("dossier_coordinator")

	@classmethod
	def paid_membership(cls, profile: str, geo_node: str, activate: bool = True):
		"""A membership settled through the real Manual gateway."""
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, geo_node)
		membership_service.submit(membership)
		row = frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

		if activate:
			fixtures.confirm_payment_through_manual_driver(row)

		return frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

	@classmethod
	def expire_naturally(cls, membership, ended_days_ago: int = 10):
		"""Backdate a membership's window so it is past, without running the sweep.

		This is the pre-expire-job window on purpose: the row is still stored as
		Active, and what the dossier says about it has to come from the date
		comparison rather than from the stored status.
		"""
		valid_to = add_days(getdate(today()), -ended_days_ago)

		frappe.db.set_value(
			fixtures.MEMBERSHIP_DOCTYPE,
			membership.name,
			{"valid_from": add_days(valid_to, -365), "valid_to": valid_to},
			update_modified=False,
		)
		frappe.clear_document_cache(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

		return frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

	def dossier(self, member: str, as_of=None) -> dict:
		"""The endpoint, called the way an HTTP caller calls it.

		`as_of` is stringified deliberately rather than passed as a date: the
		whitelisted signature says `str | None` because that is what arrives over
		the wire, and a test that handed it a `datetime.date` would be exercising
		a path no real caller takes.
		"""
		return member_api.get_dossier(member, as_of=str(as_of) if as_of else None)


class TestTheDossierIsComplete(DossierTestCase):
	"""Every block the coordinator's view promises, from one call."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile(
			"Wanjiku",
			"Kamau",
			phone="+254700000001",
			gender=frappe.db.get_value("Gender", {"name": "Female"}) or None,
			date_of_birth="1990-04-11",
		)
		cls.here = cls.paid_membership(cls.profile, cls.society_a["ward"])
		cls.member = cls.here.member

	def test_one_call_answers_every_block(self):
		dossier = self.dossier(self.member)

		for block in ("identity", "standing", "memberships", "history"):
			self.assertIn(block, dossier, f"the dossier has no {block} block")

	def test_identity_comes_back_as_a_person_not_a_docname(self):
		"""The walk-through's complaint: the record named a record, not a person."""
		identity = self.dossier(self.member)["identity"]

		self.assertEqual(identity["full_name"], "Wanjiku Kamau")
		self.assertNotEqual(identity["full_name"], self.member)
		self.assertNotEqual(identity["full_name"], self.profile)

	def test_identity_carries_the_contact_and_person_facts(self):
		identity = self.dossier(self.member)["identity"]

		self.assertEqual(identity["phone"], "+254700000001")
		self.assertEqual(str(identity["date_of_birth"]), "1990-04-11")
		self.assertEqual(identity["red_profile"], self.profile)

	def test_the_membership_block_names_a_readable_branch(self):
		row = self.dossier(self.member)["memberships"][0]

		self.assertEqual(row["membership_geo_node"], self.society_a["ward"])
		self.assertTrue(row["membership_geo_path"], "the branch came back with no readable path")
		self.assertIn("Timau", row["membership_geo_path"])

	def test_the_membership_block_carries_its_validity_and_type(self):
		row = self.dossier(self.member)["memberships"][0]

		self.assertTrue(row["valid_from"])
		self.assertTrue(row["valid_to"])
		self.assertTrue(row["membership_type_name"])
		self.assertTrue(row["is_current"])

	def test_the_payment_picture_is_there_per_membership(self):
		payment = self.dossier(self.member)["memberships"][0]["payment"]

		self.assertTrue(payment["settled"])
		self.assertTrue(payment["payable"])
		self.assertEqual(payment["fee_amount"], 600)
		self.assertTrue(payment["fee_currency"])

	def test_certificate_access_is_reported_per_membership(self):
		certificate = self.dossier(self.member)["memberships"][0]["certificate"]

		self.assertTrue(certificate["available"], "an active membership offered no certificate")
		self.assertTrue(certificate["configured"])
		self.assertIn("may_print", certificate)

	def test_a_membership_that_is_not_active_offers_no_certificate(self):
		"""`assert_active`'s rule, reported by the page instead of thrown at it."""
		pending = self.paid_membership(
			fixtures.make_profile("Not", "Active"), self.society_a["ward"], activate=False
		)

		row = self.dossier(pending.member)["memberships"][0]

		self.assertFalse(row["certificate"]["available"])

	def test_standing_reports_the_derived_status(self):
		standing = self.dossier(self.member)["standing"]

		self.assertEqual(standing["status"], "Active")
		self.assertEqual(standing["current_count"], 1)
		self.assertTrue(standing["current_geo_paths"])


class TestMultiBranch(DossierTestCase):
	"""One person, two branches, and a status derived from the set of them."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Multi", "Branch")
		cls.nairobi = cls.paid_membership(cls.profile, cls.society_a["ward"])
		cls.mombasa = cls.paid_membership(cls.profile, cls.society_a["other_ward"])
		cls.member = cls.nairobi.member

	def test_the_fixture_really_made_two_at_two_places(self):
		"""Without this the multi-branch assertions could pass on one row."""
		self.assertEqual(self.nairobi.member, self.mombasa.member)
		self.assertNotEqual(self.nairobi.geo_node, self.mombasa.geo_node)

	def test_both_branches_come_back(self):
		rows = self.dossier(self.member)["memberships"]

		self.assertEqual({row["name"] for row in rows}, {self.nairobi.name, self.mombasa.name})

	def test_each_branch_is_shown_distinctly(self):
		rows = self.dossier(self.member)["memberships"]
		branches = {row["membership_geo_node"] for row in rows}

		self.assertEqual(branches, {self.society_a["ward"], self.society_a["other_ward"]})

	def test_active_in_one_and_expired_in_another_is_active(self):
		"""The reconciliation the brief names, asserted on the derived status."""
		self.expire_naturally(self.mombasa)
		membership_service.expire(frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, self.mombasa.name))

		dossier = self.dossier(self.member)
		statuses = {row["name"]: row["effective_status"] for row in dossier["memberships"]}

		self.assertEqual(statuses[self.nairobi.name], "Active")
		self.assertEqual(statuses[self.mombasa.name], "Expired")
		self.assertEqual(
			dossier["standing"]["status"],
			"Active",
			"holding a current membership at one branch did not make the member active",
		)

	def test_the_standing_counts_say_which_branch_carries_it(self):
		self.expire_naturally(self.mombasa)
		membership_service.expire(frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, self.mombasa.name))

		standing = self.dossier(self.member)["standing"]

		self.assertEqual(standing["current_count"], 1)
		self.assertEqual(standing["visible_count"], 2)


class TestOneInstantReachesEveryDerivation(DossierTestCase):
	"""The `as_of` date resolves once and reaches every derived answer, nested ones included."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("As", "Of")
		cls.membership = cls.paid_membership(cls.profile, cls.society_a["ward"])
		cls.member = cls.membership.member
		# Ended ten days ago, still stored Active: the pre-sweep window.
		cls.expired = cls.expire_naturally(cls.membership, ended_days_ago=10)

	def test_the_dossier_reports_the_date_it_answered_as_at(self):
		dossier = self.dossier(self.member)

		self.assertEqual(dossier["as_of"], getdate(today()))

	def test_as_at_today_the_window_has_closed(self):
		row = self.dossier(self.member)["memberships"][0]

		self.assertTrue(row["lapsed"])
		self.assertEqual(row["effective_status"], "Expired")
		self.assertFalse(row["is_current"])

	def test_the_stored_status_still_says_active(self):
		"""Guards the test above: the lapse is derived, not read off the row.

		Without this, `lapsed` could be passing because something expired the
		membership rather than because a date was compared.
		"""
		stored = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, self.membership.name, "membership_status")

		self.assertEqual(stored, "Active")

	def test_asking_about_a_past_date_moves_every_derivation_together(self):
		"""The nested-DTO fix, pinned.

		`renewable` is derived by `renewal.is_renewable`, which defaults to today
		unless it is told otherwise. Asked about a date on which the membership
		was still current, the row must say it had not lapsed *and* that it was
		not yet renewable. If `as_of` stopped reaching the inner call, `lapsed`
		would move and `renewable` would not, and the row would carry two answers
		to one question.
		"""
		while_valid = add_days(getdate(today()), -20)

		row = self.dossier(self.member, as_of=while_valid)["memberships"][0]

		self.assertFalse(row["lapsed"], "the outer derivation ignored as_of")
		self.assertFalse(
			row["renewable"],
			"as_of did not reach the nested renewable derivation: the row says it had"
			" not lapsed but could already be renewed",
		)
		self.assertEqual(row["effective_status"], "Active")

	def test_as_at_today_the_same_two_agree_the_other_way(self):
		"""The mirror: both move, so the test above is not passing on two falses."""
		row = self.dossier(self.member)["memberships"][0]

		self.assertTrue(row["lapsed"])
		self.assertTrue(row["renewable"])

	def test_every_block_reports_the_same_instant(self):
		while_valid = add_days(getdate(today()), -20)
		dossier = self.dossier(self.member, as_of=while_valid)

		self.assertEqual(dossier["as_of"], while_valid)
		self.assertEqual(dossier["standing"]["as_of"], while_valid)
		self.assertEqual(dossier["memberships"][0]["as_of"], while_valid)


class TestIdentityIsNotDuplicated(DossierTestCase):
	"""Identity is core's. This app reads it and stores none of it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Original", "Name", phone="+254700000002")
		cls.membership = cls.paid_membership(cls.profile, cls.society_a["ward"])
		cls.member = cls.membership.member

	def test_the_member_doctype_holds_no_identity_column(self):
		"""Stated positively: only the member's own attributes persist."""
		fieldnames = {field.fieldname for field in frappe.get_meta(fixtures.MEMBER_DOCTYPE).fields}

		for identity_field in IDENTITY_FIELDS:
			self.assertNotIn(
				identity_field,
				fieldnames,
				f"{identity_field} became a column on {fixtures.MEMBER_DOCTYPE}",
			)

	def test_the_member_row_holds_nothing_but_its_own_attributes(self):
		"""A thirteenth column has to be argued for, not arrive quietly."""
		row = frappe.db.get_value(fixtures.MEMBER_DOCTYPE, self.member, "*", as_dict=True)

		self.assertTrue(
			set(row.keys()) <= MEMBER_OWNED_FIELDS,
			f"unexpected columns on {fixtures.MEMBER_DOCTYPE}: {set(row.keys()) - MEMBER_OWNED_FIELDS}",
		)

	def test_no_fetch_from_smuggles_identity_onto_the_record(self):
		"""A fetched value is a stored copy wearing a different hat."""
		for field in frappe.get_meta(fixtures.MEMBER_DOCTYPE).fields:
			self.assertFalse(
				field.fetch_from,
				f"{field.fieldname} fetches {field.fetch_from} onto the member record",
			)

	def test_correcting_a_name_changes_the_screen_and_not_the_row(self):
		"""The whole point, asserted both ways in one test."""
		before = frappe.db.get_value(fixtures.MEMBER_DOCTYPE, self.member, "*", as_dict=True)

		frappe.db.set_value("Red Profile", self.profile, "first_name", "Corrected")
		frappe.db.set_value("Red Profile", self.profile, "full_name", "Corrected Name")
		frappe.clear_document_cache("Red Profile", self.profile)

		after = frappe.db.get_value(fixtures.MEMBER_DOCTYPE, self.member, "*", as_dict=True)

		self.assertEqual(dict(before), dict(after), "correcting a name wrote to the member record")
		self.assertEqual(self.dossier(self.member)["identity"]["full_name"], "Corrected Name")

	def test_moving_someones_home_area_leaves_the_member_row_byte_identical(self):
		"""Home Area is core's `Red Profile.home_geo_node`, never copied here."""
		before = frappe.db.get_value(fixtures.MEMBER_DOCTYPE, self.member, "*", as_dict=True)

		frappe.db.set_value("Red Profile", self.profile, "home_geo_node", self.society_b["ward"])
		frappe.clear_document_cache("Red Profile", self.profile)

		after = frappe.db.get_value(fixtures.MEMBER_DOCTYPE, self.member, "*", as_dict=True)
		identity = self.dossier(self.member)["identity"]

		self.assertEqual(dict(before), dict(after), "moving somebody's home wrote to the member record")
		self.assertEqual(identity["home_geo_node"], self.society_b["ward"])

	def test_the_home_area_is_not_the_membership_branch(self):
		"""Two Geo Nodes, two questions, and never merged."""
		frappe.db.set_value("Red Profile", self.profile, "home_geo_node", self.society_b["ward"])
		frappe.clear_document_cache("Red Profile", self.profile)

		dossier = self.dossier(self.member)

		self.assertEqual(dossier["identity"]["home_geo_node"], self.society_b["ward"])
		self.assertEqual(dossier["memberships"][0]["membership_geo_node"], self.society_a["ward"])


class TestThePaymentPictureIsReadLive(DossierTestCase):
	"""How a fee was settled comes from the payments app, not from a copy."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Paid", "Member")
		cls.membership = cls.paid_membership(cls.profile, cls.society_a["ward"])
		cls.member = cls.membership.member

	def payment_of(self, member: str) -> dict:
		return self.dossier(member)["memberships"][0]["payment"]

	def test_the_gateway_is_read_from_the_payments_app(self):
		payment = self.payment_of(self.member)

		self.assertTrue(payment["live"], "the live half of the payment picture was never read")
		self.assertTrue(payment["gateway"], "no gateway came back for a gateway-settled membership")
		self.assertEqual(payment["gateway_status"], "Completed")

	def test_the_receipt_comes_back(self):
		payment = self.payment_of(self.member)

		self.assertTrue(
			payment["gateway_receipt"] or payment["receipt"],
			"a membership settled through the manual driver reported no receipt",
		)

	def test_renaming_the_gateway_changes_the_screen_without_touching_the_membership(self):
		"""The mutation that proves it is read and not stored."""
		before = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, self.membership.name, "*", as_dict=True)
		gateway = frappe.db.get_value(
			"OneRC Payment Transaction", self.membership.payment_transaction, "gateway"
		)

		frappe.db.set_value("OneRC Payment Gateway", gateway, "label", "Renamed Gateway")
		frappe.clear_document_cache("OneRC Payment Gateway", gateway)

		after = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, self.membership.name, "*", as_dict=True)

		self.assertEqual(self.payment_of(self.member)["gateway"], "Renamed Gateway")
		self.assertEqual(dict(before), dict(after), "the gateway name was copied onto the membership")

	def test_the_membership_stores_no_gateway_column(self):
		fieldnames = {field.fieldname for field in frappe.get_meta(fixtures.MEMBERSHIP_DOCTYPE).fields}

		self.assertNotIn("gateway", fieldnames)
		self.assertNotIn("payment_gateway", fieldnames)

	def test_a_free_membership_says_nothing_was_owed(self):
		free = fixtures.make_membership(
			fixtures.make_profile("Free", "Member"), fixtures.TYPE_FREE, self.society_a["ward"]
		)
		membership_service.submit(free)

		payment = self.payment_of(frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, free.name).member)

		self.assertFalse(payment["payable"])
		self.assertTrue(payment["settled"])
		self.assertFalse(payment["live"], "a free membership reached the payments app")


class TestProofIsDistinguishableFromGateway(DossierTestCase):
	"""A pre-rollout member's fee was verified by a person, not by a gateway."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# `scoped_user`, not `make_user`: deciding a membership means saving it,
		# and core's geo scoping is consulted before the engine's person-gate is
		# ever reached. Without the scope grant this approver would be refused at
		# the door and the test would prove nothing about approval.
		cls.approver = cls.scoped_user("dossier_approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)

		cls.profile = fixtures.make_profile("Proof", "Member")
		cls.membership = fixtures.make_membership(
			cls.profile,
			fixtures.TYPE_PROOF,
			cls.society_a["ward"],
			membership_source=membership_service.SOURCE_PROOF,
			proof_attachment=fixtures.make_proof_file(),
		)
		membership_service.submit(cls.membership)

		with fixtures.acting_as(cls.approver):
			from vmmsx.api import approvals as approvals_api

			approvals_api.decide(
				fixtures.MEMBERSHIP_DOCTYPE, cls.membership.name, "Approved", "Record book checked"
			)

		cls.member = frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, cls.membership.name).member

	def payment_of(self) -> dict:
		return self.dossier(self.member)["memberships"][0]["payment"]

	def test_it_is_marked_as_proof_rather_than_gateway(self):
		payment = self.payment_of()

		self.assertTrue(payment["is_proof"])
		self.assertEqual(payment["source"], membership_service.SOURCE_PROOF)

	def test_it_never_reaches_the_payments_app(self):
		"""There is no transaction and never will be: the fee predates this system."""
		payment = self.payment_of()

		self.assertFalse(payment["live"])
		self.assertFalse(payment["transaction"])

	def test_it_names_the_person_who_verified_it(self):
		"""What stands in for a gateway is the approver who looked at the evidence."""
		payment = self.payment_of()

		self.assertEqual(payment["verified_by"], self.approver)
		self.assertTrue(payment["verified_on"])

	def test_the_evidence_is_reachable_from_the_dossier(self):
		self.assertTrue(self.payment_of()["proof_attachment"])

	def test_the_verification_appears_in_the_history(self):
		history = self.dossier(self.member)["history"]

		self.assertTrue(history, "an approved membership recorded no history")
		self.assertEqual(history[0]["decision"], "Approved")
		self.assertEqual(history[0]["approver"], self.approver)
		self.assertEqual(history[0]["reason"], "Record book checked")


class TestTheHeadingNamesThePerson(DossierTestCase):
	"""Both records read as a person, and neither stores one."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Heading", "Person")
		cls.membership = cls.paid_membership(cls.profile, cls.society_a["ward"])
		cls.member = cls.membership.member

	def test_the_member_dossier_supplies_a_name_for_the_heading(self):
		self.assertEqual(self.dossier(self.member)["identity"]["full_name"], "Heading Person")

	def test_the_membership_dto_supplies_a_name_for_the_heading(self):
		dto = member_api.get_membership(self.membership.name)

		self.assertEqual(dto["member_name"], "Heading Person")

	def test_neither_doctype_carries_a_title_field_holding_identity(self):
		"""A computed title field would put identity on the doctype's meta."""
		member_title = frappe.get_meta(fixtures.MEMBER_DOCTYPE).title_field
		membership_title = frappe.get_meta(fixtures.MEMBERSHIP_DOCTYPE).title_field

		self.assertNotIn(member_title or "", IDENTITY_FIELDS)
		self.assertNotIn(membership_title or "", IDENTITY_FIELDS)


class TestPriceIsVisibleWhenChoosing(DossierTestCase):
	"""The fee is on the type and was never shown at the moment of the decision."""

	def test_a_paid_type_reports_its_fee_and_currency(self):
		dto = member_api.membership_type_pricing(fixtures.TYPE_AUTO)

		self.assertTrue(dto["known"])
		self.assertEqual(dto["amount"], 600)
		self.assertTrue(dto["currency"])
		self.assertFalse(dto["free"])

	def test_a_free_type_says_free_rather_than_zero(self):
		dto = member_api.membership_type_pricing(fixtures.TYPE_FREE)

		self.assertTrue(dto["free"])
		self.assertEqual(dto["amount"], 0)

	def test_it_reports_what_else_the_choice_commits_to(self):
		dto = member_api.membership_type_pricing(fixtures.TYPE_FREE)

		self.assertEqual(dto["duration_days"], 365)
		self.assertTrue(dto["requires_approver"], "a routed type did not say it needs an approver")

	def test_an_auto_on_payment_type_needs_no_approver(self):
		self.assertFalse(member_api.membership_type_pricing(fixtures.TYPE_AUTO)["requires_approver"])

	def test_an_empty_form_is_answered_rather_than_thrown_at(self):
		self.assertFalse(member_api.membership_type_pricing(None)["known"])
		self.assertFalse(member_api.membership_type_pricing("no-such-type")["known"])

	def test_the_price_follows_the_configuration(self):
		"""Read live: changing the fee changes what the form says, with no deploy."""
		frappe.db.set_value(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO, "fee_amount", 950)
		frappe.clear_document_cache(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO)

		self.assertEqual(member_api.membership_type_pricing(fixtures.TYPE_AUTO)["amount"], 950)


class TestTheAnchorPickerAgreesWithEnforcement(DossierTestCase):
	"""What the picker offers is what Submit will accept. No pick-then-reject."""

	def setUp(self):
		super().setUp()
		self.addCleanup(fixtures.set_anchor_level, None)

	def test_unconstrained_when_neither_surface_narrows_it(self):
		fixtures.set_anchor_level(None)

		dto = member_api.geo_node_levels()

		self.assertTrue(dto["unconstrained"])

	def test_the_settings_level_narrows_the_picker(self):
		fixtures.set_anchor_level(self.society_a["levels"]["ward"])

		dto = member_api.geo_node_levels()

		self.assertFalse(dto["unconstrained"])
		self.assertEqual(dto["levels"], [self.society_a["levels"]["ward"]])

	def test_every_level_the_picker_offers_is_one_that_saves(self):
		"""The agreement, asserted by actually saving at the offered level."""
		fixtures.set_anchor_level(self.society_a["levels"]["ward"])

		for level in member_api.geo_node_levels()["levels"]:
			node = frappe.db.get_value("Geo Node", {"geo_level": level}, "name")
			membership = fixtures.make_membership(
				fixtures.make_profile("Anchor", f"Ok{level}"), fixtures.TYPE_FREE, node
			)

			self.assertTrue(membership.name)

	def test_a_level_the_picker_withholds_is_one_that_would_be_refused(self):
		"""The other half: the trap the picker exists to close is real."""
		fixtures.set_anchor_level(self.society_a["levels"]["ward"])

		offered = member_api.geo_node_levels()["levels"]

		self.assertNotIn(self.society_a["levels"]["county"], offered)

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_membership(
				fixtures.make_profile("Anchor", "Refused"),
				fixtures.TYPE_FREE,
				self.society_a["county"],
			)


class TestTheRegisterIsScoped(DossierTestCase):
	"""Scope is the floor the register stands on, not a filter it applies."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# A coordinator whose authority covers society A's county and nothing else.
		cls.local = fixtures.make_user("register_local", [fixtures.SCOPE_ROLE])
		fixtures.make_assignment(cls.local, fixtures.SCOPE_ROLE, cls.society_a["county"])

		cls.inside = cls.paid_membership(fixtures.make_profile("Inside", "Scope"), cls.society_a["ward"])
		cls.outside = cls.paid_membership(fixtures.make_profile("Outside", "Scope"), cls.society_b["ward"])

	def register_as(self, user: str, **kwargs) -> dict:
		with fixtures.acting_as(user):
			return member_api.find_members(**kwargs)

	def test_the_fixture_really_put_them_in_different_societies(self):
		"""Without this the leak assertion could pass on one row."""
		self.assertNotEqual(self.inside.geo_node, self.outside.geo_node)

	def test_a_coordinator_sees_the_members_in_their_scope(self):
		rows = self.register_as(self.local)["rows"]

		self.assertIn(self.inside.name, {row["membership"] for row in rows})

	def test_a_coordinator_never_sees_a_member_outside_their_scope(self):
		"""The leak test. This is the one that must not be allowed to pass wrongly."""
		rows = self.register_as(self.local)["rows"]

		self.assertNotIn(
			self.outside.name,
			{row["membership"] for row in rows},
			"the register returned a membership outside the caller's geo scope",
		)

	def test_naming_an_out_of_scope_branch_is_not_a_way_in(self):
		"""A filter narrows; it never widens."""
		rows = self.register_as(self.local, geo_node=self.society_b["ward"])["rows"]

		self.assertEqual(rows, [])

	def test_the_register_shows_names_rather_than_codes(self):
		rows = self.register_as(self.local)["rows"]
		row = next(row for row in rows if row["membership"] == self.inside.name)

		self.assertEqual(row["full_name"], "Inside Scope")
		self.assertNotEqual(row["full_name"], row["member"])

	def test_the_register_shows_branch_status_and_validity(self):
		rows = self.register_as(self.local)["rows"]
		row = next(row for row in rows if row["membership"] == self.inside.name)

		self.assertTrue(row["geo_path"])
		self.assertTrue(row["membership_type_name"])
		self.assertEqual(row["effective_status"], "Active")
		self.assertTrue(row["valid_from"])
		self.assertTrue(row["valid_to"])

	def test_a_person_at_two_branches_is_two_rows_and_one_member(self):
		"""The multi-branch model, in the shape of the output."""
		profile = fixtures.make_profile("Two", "Branches")
		self.paid_membership(profile, self.society_a["ward"])
		self.paid_membership(profile, self.society_a["other_ward"])

		found = self.register_as(self.local)
		member = frappe.db.get_value(fixtures.MEMBER_DOCTYPE, {"red_profile": profile}, "name")
		theirs = [row for row in found["rows"] if row["member"] == member]

		self.assertEqual(len(theirs), 2)
		self.assertEqual(len({row["geo_node"] for row in theirs}), 2)

	def test_an_unconfigured_scope_role_returns_nothing_rather_than_everything(self):
		"""Core fails closed, and the register inherits that rather than working around it."""
		self.addCleanup(fixtures.set_scope_role, fixtures.SCOPE_ROLE)
		fixtures.set_scope_role(None)

		self.assertEqual(self.register_as(self.local)["rows"], [])


class TestTheDossierMembershipBlockIsScopedToo(DossierTestCase):
	"""Opening a member does not disclose a membership at a branch you cannot see."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.local = fixtures.make_user("dossier_local", [fixtures.SCOPE_ROLE])
		fixtures.make_assignment(cls.local, fixtures.SCOPE_ROLE, cls.society_a["county"])

		cls.profile = fixtures.make_profile("Split", "Across")
		cls.visible = cls.paid_membership(cls.profile, cls.society_a["ward"])
		cls.hidden = cls.paid_membership(cls.profile, cls.society_b["ward"])
		cls.member = cls.visible.member

	def test_the_fixture_really_split_them_across_two_societies(self):
		self.assertEqual(self.visible.member, self.hidden.member)
		self.assertNotEqual(self.visible.geo_node, self.hidden.geo_node)

	def test_an_administrator_sees_both(self):
		"""Guards the test below: both memberships genuinely exist."""
		rows = self.dossier(self.member)["memberships"]

		self.assertEqual({row["name"] for row in rows}, {self.visible.name, self.hidden.name})

	def test_a_scoped_coordinator_sees_only_their_own_branch(self):
		with fixtures.acting_as(self.local):
			rows = self.dossier(self.member)["memberships"]

		names = {row["name"] for row in rows}

		self.assertIn(self.visible.name, names)
		self.assertNotIn(
			self.hidden.name,
			names,
			"the dossier disclosed a membership at a branch outside the caller's scope",
		)
