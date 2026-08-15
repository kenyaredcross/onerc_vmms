# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Lapse is derived, not stored — and these tests are written to catch a flag.

The claim under test is narrow and falsifiable: **nothing anywhere persists
whether a certification has lapsed.** `expiry_date` is stored, because it is a
fact computed once from configuration. Lapse is not, because it is a comparison
against the date you are asking about, and a stored answer is wrong the moment
the date moves.

Three kinds of proof, because "we did not store it" is easy to assert badly:

1. **Behavioural.** The same untouched certification reads as valid on one date
   and lapsed on another, with no write in between — asserted by capturing
   `modified` and the row's Version count and showing neither moved.
2. **Structural.** No field on `VMMS Certification` — or on any doctype in this
   app — is a lapse flag under any spelling, and no scheduled job runs anything
   in this module. A future author adding either breaks this.
3. **Consequential.** The rule the whole thing exists for: a lapsed
   certification makes its holder non-deployable *while they stay Active*, and
   the answer is derived at the moment of asking, including for a date in the
   past.

No certification name appears in the module's source; the fixtures supply real
ones so that a reader can confirm the app never reads one.
"""

import json
from pathlib import Path

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.api import volunteer as volunteer_api
from vmmsx.volunteer.services import certification
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

# Spellings a stored lapse could plausibly arrive under. Substring-matched
# against every fieldname and label in the app.
LAPSE_SPELLINGS = ("laps", "expired", "is_expired", "has_expired", "valid_flag")

# One field matches the pattern and is deliberately not a lapse flag:
# `blocks_deployment_when_lapsed` is a **policy switch on the type**, saying what
# a lapse should cost, and it is read at derivation time. It records nothing
# about whether any particular certification has lapsed. Allow-listed by name
# rather than by loosening the pattern, so that adding a genuine flag whose name
# happens to contain "lapsed" still fails.
NOT_A_LAPSE_FLAG = frozenset({"VMMS Certification Type.blocks_deployment_when_lapsed"})


class CertificationTestCase(VolunteerTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# 365 days, and a type that never expires. Both are configuration; the
		# numbers live here rather than anywhere in the app.
		fixtures.make_certification_type(fixtures.CERT_FIRST_AID, validity_days=365)
		fixtures.make_certification_type(fixtures.CERT_PSYCHOSOCIAL, validity_days=90)
		fixtures.make_certification_type(fixtures.CERT_NEVER_EXPIRES, validity_days=0)

	def volunteer(self, handle: str = "Cert"):
		"""An Active volunteer, reported to core's index the way acceptance would.

		Active, so that a deployability failure is about a certification and not
		about the volunteer's own status — and reported, so that the test which
		checks a lapse does not quietly end somebody's volunteering has an
		affiliation row to check against in the first place.
		"""
		from vmmsx.volunteer.services import volunteer as volunteer_service

		profile = fixtures.make_profile(handle, "Holder")
		volunteer = fixtures.make_volunteer(profile, self.society_a["ward"])

		frappe.db.set_value(fixtures.VOLUNTEER_DOCTYPE, volunteer.name, "status", "Active")
		volunteer.reload()
		volunteer_service.report(volunteer)

		return volunteer

	def certify(self, volunteer, type_key: str, completed_on=None, **fields):
		return certification.record(
			volunteer=volunteer.name,
			certification_type=type_key,
			completion_date=completed_on or today(),
			**fields,
		)


class TestExpiryIsComputedFromConfiguration(CertificationTestCase):
	def test_expiry_is_completion_plus_the_types_validity_period(self):
		volunteer = self.volunteer()
		completed = getdate(add_days(today(), -10))
		held = self.certify(volunteer, fixtures.CERT_FIRST_AID, completed)

		self.assertEqual(getdate(held.expiry_date), getdate(add_days(completed, 365)))

	def test_a_different_type_gives_a_different_expiry_with_no_code_change(self):
		volunteer = self.volunteer()
		completed = getdate(today())

		first = self.certify(volunteer, fixtures.CERT_FIRST_AID, completed)
		second = self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, completed)

		self.assertEqual(getdate(first.expiry_date), getdate(add_days(completed, 365)))
		self.assertEqual(getdate(second.expiry_date), getdate(add_days(completed, 90)))

	def test_a_type_with_no_validity_period_never_expires(self):
		volunteer = self.volunteer()
		held = self.certify(volunteer, fixtures.CERT_NEVER_EXPIRES)

		self.assertIsNone(held.expiry_date)
		self.assertFalse(certification.is_lapsed(held))
		self.assertFalse(certification.is_lapsed(held, as_of=add_days(today(), 40000)))

	def test_changing_the_types_period_moves_the_expiry_on_the_next_save(self):
		"""Configuration, not a constant — and the certifications follow it."""
		volunteer = self.volunteer()
		held = self.certify(volunteer, fixtures.CERT_FIRST_AID, today())

		self.assertEqual(getdate(held.expiry_date), getdate(add_days(today(), 365)))

		certification_type = frappe.get_doc(fixtures.CERTIFICATION_TYPE_DOCTYPE, fixtures.CERT_FIRST_AID)
		certification_type.validity_days = 30
		certification_type.save()
		frappe.clear_document_cache(fixtures.CERTIFICATION_TYPE_DOCTYPE, fixtures.CERT_FIRST_AID)
		self.addCleanup(fixtures.make_certification_type, fixtures.CERT_FIRST_AID, 365)

		held.save()

		self.assertEqual(getdate(held.expiry_date), getdate(add_days(today(), 30)))


class TestLapseIsDerived(CertificationTestCase):
	def test_a_certification_past_its_expiry_reads_as_lapsed(self):
		volunteer = self.volunteer()
		held = self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))

		self.assertTrue(certification.is_lapsed(held))

	def test_a_current_certification_does_not(self):
		volunteer = self.volunteer()
		held = self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, today())

		self.assertFalse(certification.is_lapsed(held))

	def test_the_same_record_reads_differently_on_different_dates(self):
		"""The heart of it. One record, two dates, two answers, no write.

		If lapse were stored, the two calls below would have to agree — and
		asking about a date other than today would be meaningless.
		"""
		volunteer = self.volunteer()
		held = self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, today())
		expiry = getdate(held.expiry_date)

		self.assertFalse(certification.is_lapsed(held, as_of=expiry))
		self.assertTrue(certification.is_lapsed(held, as_of=add_days(expiry, 1)))
		self.assertFalse(certification.is_lapsed(held, as_of=add_days(expiry, -1)))

	def test_reading_the_lapse_writes_absolutely_nothing(self):
		"""No save, no version row, no `modified` bump. Asserted, not assumed."""
		volunteer = self.volunteer()
		held = self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))

		before_modified = frappe.db.get_value(fixtures.CERTIFICATION_DOCTYPE, held.name, "modified")
		before_versions = frappe.db.count(
			"Version", {"ref_doctype": fixtures.CERTIFICATION_DOCTYPE, "docname": held.name}
		)

		self.assertTrue(certification.is_lapsed(held))
		self.assertTrue(certification.lapsed(volunteer.name))
		self.assertFalse(certification.is_deployable(volunteer))

		self.assertEqual(
			frappe.db.get_value(fixtures.CERTIFICATION_DOCTYPE, held.name, "modified"),
			before_modified,
			"deriving the lapse modified the record",
		)
		self.assertEqual(
			frappe.db.count("Version", {"ref_doctype": fixtures.CERTIFICATION_DOCTYPE, "docname": held.name}),
			before_versions,
			"deriving the lapse wrote a version row",
		)

	def test_it_answers_the_same_from_a_plain_row_as_from_a_document(self):
		"""Callers hold both; the answer must not depend on which."""
		volunteer = self.volunteer()
		held = self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))
		row = certification.held(volunteer.name)[0]

		self.assertEqual(certification.is_lapsed(held), certification.is_lapsed(row))

	def test_a_renewal_un_lapses_it_by_moving_the_completion_date(self):
		"""The only way a lapse goes away: the underlying fact changes."""
		volunteer = self.volunteer()
		held = self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))

		self.assertTrue(certification.is_lapsed(held))

		renewed = self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, today())

		self.assertEqual(renewed.name, held.name, "a renewal made a second row")
		self.assertFalse(certification.is_lapsed(renewed))


class TestNothingPersistsTheLapse(CertificationTestCase):
	"""The structural half. A future author adding a flag breaks these."""

	def test_the_certification_doctype_has_no_lapse_field(self):
		meta = frappe.get_meta(fixtures.CERTIFICATION_DOCTYPE)
		offenders = [
			field.fieldname
			for field in meta.fields
			if any(
				spelling in (field.fieldname or "").lower() or spelling in (field.label or "").lower()
				for spelling in LAPSE_SPELLINGS
			)
		]

		self.assertEqual(offenders, [], "a lapse flag has appeared on the certification")

	def test_no_doctype_in_this_app_has_one(self):
		"""Not on the volunteer either — the derivation has no home anywhere."""
		offenders = []
		root = Path(frappe.get_app_path("vmmsx"))

		for path in root.glob("*/doctype/*/*.json"):
			definition = json.loads(path.read_text())

			for field in definition.get("fields", []):
				name = (field.get("fieldname") or "").lower()
				label = (field.get("label") or "").lower()
				qualified = f"{definition.get('name')}.{field['fieldname']}"

				if qualified in NOT_A_LAPSE_FLAG:
					continue

				if any(spelling in name or spelling in label for spelling in LAPSE_SPELLINGS):
					offenders.append(qualified)

		self.assertEqual(offenders, [], "a lapse flag has appeared somewhere in the app")

	def test_the_one_allow_listed_field_really_is_only_a_policy_switch(self):
		"""Guards the allow-list above: it exempts a switch, not a state.

		A policy switch lives on the *type* and is the same for every holder. A
		state would live on the held certification and differ between them. If
		this field ever moved onto `VMMS Certification`, it would have become the
		stored lapse this whole module exists to avoid — and this fails.
		"""
		for qualified in NOT_A_LAPSE_FLAG:
			doctype, fieldname = qualified.rsplit(".", 1)

			self.assertEqual(doctype, fixtures.CERTIFICATION_TYPE_DOCTYPE)
			self.assertIsNone(
				frappe.get_meta(fixtures.CERTIFICATION_DOCTYPE).get_field(fieldname),
				"the policy switch has appeared on the held certification",
			)

	def test_no_scheduled_job_touches_the_volunteer_module(self):
		"""No cron flips anything here, so nothing can be stale because one failed."""
		scheduled = []

		for jobs in frappe.get_hooks("scheduler_events").values():
			scheduled.extend(jobs if isinstance(jobs, list) else [jobs])

		offenders = [job for job in scheduled if "vmmsx.volunteer" in str(job)]

		self.assertEqual(offenders, [], "a scheduled job has appeared in the volunteer module")

	def test_the_expiry_date_is_the_only_stored_input(self):
		"""What *is* stored is a date, and it is enough to derive the rest."""
		meta = frappe.get_meta(fixtures.CERTIFICATION_DOCTYPE)
		field = meta.get_field("expiry_date")

		self.assertEqual(field.fieldtype, "Date")
		self.assertTrue(field.read_only, "the derived input must not be typed over")


class TestALapseCostsDeployability(CertificationTestCase):
	def test_a_lapsed_certification_makes_an_active_volunteer_non_deployable(self):
		"""The rule the module exists to express, stated in one assertion."""
		volunteer = self.volunteer()
		self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))

		answer = certification.deployability(volunteer)

		self.assertEqual(volunteer.status, "Active", "the volunteer must stay Active")
		self.assertFalse(answer["deployable"])
		self.assertTrue(answer["reasons"])

	def test_lapsing_does_not_end_somebody_volunteering(self):
		"""Non-deployable is not inactive. Conflating them would remove people."""
		volunteer = self.volunteer()
		self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))

		self.assertFalse(certification.is_deployable(volunteer))
		self.assertEqual(
			self.volunteer_status(volunteer.name),
			"Active",
			"a lapse quietly changed the volunteer's status",
		)
		self.assertIn("volunteer", self.affiliation_types(volunteer.red_profile))

	def test_a_current_certification_leaves_them_deployable(self):
		volunteer = self.volunteer()
		self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, today())

		self.assertTrue(certification.is_deployable(volunteer))

	def test_a_type_configured_not_to_block_does_not_block(self):
		"""Whether a lapse costs deployability is configuration, not a constant."""
		volunteer = self.volunteer()
		self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))

		self.assertFalse(certification.is_deployable(volunteer))

		self.addCleanup(self._set_blocking, fixtures.CERT_PSYCHOSOCIAL, 1)
		self._set_blocking(fixtures.CERT_PSYCHOSOCIAL, 0)

		self.assertTrue(certification.is_deployable(volunteer), "the setting changed nothing")

	def _set_blocking(self, type_key: str, value: int) -> None:
		frappe.db.set_value(
			fixtures.CERTIFICATION_TYPE_DOCTYPE, type_key, "blocks_deployment_when_lapsed", value
		)
		frappe.clear_document_cache(fixtures.CERTIFICATION_TYPE_DOCTYPE, type_key)

	def test_deployability_can_be_asked_about_a_past_date(self):
		"""Only possible because nothing is stored. The question worth having.

		"Was this volunteer certified on the day of the deployment" is a question
		a stored flag simply cannot answer, and it is the question an inquiry
		asks.
		"""
		volunteer = self.volunteer()
		held = self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))
		expiry = getdate(held.expiry_date)

		self.assertTrue(certification.is_deployable(volunteer, as_of=add_days(expiry, -1)))
		self.assertFalse(certification.is_deployable(volunteer, as_of=add_days(expiry, 1)))

	def test_a_non_active_volunteer_is_not_deployable_whatever_they_hold(self):
		volunteer = self.volunteer()
		self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, today())

		from vmmsx.volunteer.services import volunteer as volunteer_service

		volunteer_service.suspend(volunteer, reason="Under review.")

		self.assertFalse(certification.is_deployable(volunteer))

	def test_the_reason_names_the_society_s_own_word_for_the_certification(self):
		"""Interpolated from configuration, never a literal in the source."""
		volunteer = self.volunteer()
		self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))

		configured = frappe.db.get_value(
			fixtures.CERTIFICATION_TYPE_DOCTYPE, fixtures.CERT_PSYCHOSOCIAL, "certification_type_name"
		)
		reasons = " ".join(certification.deployability(volunteer)["reasons"])

		self.assertIn(configured, reasons)


class TestOneCertificationPerType(CertificationTestCase):
	def test_a_second_row_of_the_same_type_is_refused(self):
		volunteer = self.volunteer()
		self.certify(volunteer, fixtures.CERT_FIRST_AID, today())

		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				{
					"doctype": fixtures.CERTIFICATION_DOCTYPE,
					"volunteer": volunteer.name,
					"certification_type": fixtures.CERT_FIRST_AID,
					"completion_date": today(),
				}
			).insert()

	def test_a_different_type_is_fine(self):
		volunteer = self.volunteer()
		self.certify(volunteer, fixtures.CERT_FIRST_AID, today())
		self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, today())

		self.assertEqual(len(certification.held(volunteer.name)), 2)

	def test_training_cannot_have_been_completed_in_the_future(self):
		volunteer = self.volunteer()

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": fixtures.CERTIFICATION_DOCTYPE,
					"volunteer": volunteer.name,
					"certification_type": fixtures.CERT_FIRST_AID,
					"completion_date": add_days(today(), 1),
				}
			).insert()


class TestSeeingYourOwnCertifications(CertificationTestCase):
	"""`my_certifications()` — the surface the derived lapse is actually for.

	A volunteer holds no scope role and cannot browse the register, so their own
	training reaches them the same way their own record does: through an endpoint
	that answers from the session and cannot be asked about anybody else.

	The thing worth testing here is not that a list comes back. It is that the
	`lapsed` on each row and the `deployable` above them are **computed in the
	response**, from a date, at the moment of asking — which is why a list view
	of `VMMS Certification` cannot be this surface, however well it is filtered.
	"""

	def logged_in_volunteer(self, handle: str = "selfcert"):
		"""A volunteer whose Red Profile carries a login, and that login.

		The handle is made unique per call. Frappe rolls the test transaction back
		once per class rather than per method, and core makes `Red Profile.user`
		unique, so a fixed handle would make the second test in this class collide
		with the profile the first one left behind.
		"""
		from vmmsx.volunteer.services import volunteer as volunteer_service

		handle = f"{handle}_{frappe.generate_hash(length=6)}"
		user = fixtures.make_user(handle)
		profile = fixtures.make_profile(handle.title(), "Owner", user=user)
		volunteer = fixtures.make_volunteer(profile, self.society_a["ward"])

		frappe.db.set_value(fixtures.VOLUNTEER_DOCTYPE, volunteer.name, "status", "Active")
		volunteer.reload()
		volunteer_service.report(volunteer)

		return volunteer, user

	def test_it_takes_no_arguments_at_all(self):
		"""The possessive shape, asserted rather than assumed.

		An endpoint that accepted a name would be a reader of anybody's training
		wearing a possessive name, and the check stopping that would be one more
		thing to get right. An `as_of` is refused for a different reason: this is
		somebody's answer about their own training today, and a caller who really
		needs another date has the permission-checked `get_certifications`.
		"""
		import inspect

		self.assertEqual(list(inspect.signature(volunteer_api.my_certifications).parameters), [])

	def test_it_returns_the_session_users_own_certifications(self):
		volunteer, user = self.logged_in_volunteer()
		self.certify(volunteer, fixtures.CERT_FIRST_AID, today())

		with fixtures.acting_as(user):
			mine = volunteer_api.my_certifications()

		self.assertEqual(mine["volunteer"], volunteer.name)
		self.assertEqual(
			[row["certification_type"] for row in mine["certifications"]],
			[fixtures.CERT_FIRST_AID],
		)

	def test_it_never_returns_somebody_elses(self):
		"""Two volunteers, two logins, and neither sees the other's training."""
		mine, my_user = self.logged_in_volunteer("selfcert_one")
		theirs, their_user = self.logged_in_volunteer("selfcert_two")

		self.certify(mine, fixtures.CERT_FIRST_AID, today())
		self.certify(theirs, fixtures.CERT_PSYCHOSOCIAL, today())

		with fixtures.acting_as(my_user):
			answer = volunteer_api.my_certifications()

		self.assertEqual(answer["volunteer"], mine.name)
		self.assertEqual(
			[row["certification_type"] for row in answer["certifications"]],
			[fixtures.CERT_FIRST_AID],
			"somebody else's certification came back",
		)

		with fixtures.acting_as(their_user):
			self.assertEqual(volunteer_api.my_certifications()["volunteer"], theirs.name)

	def test_the_lapse_on_each_row_is_derived_in_the_response(self):
		"""Not read from the record, because it is not on the record."""
		volunteer, user = self.logged_in_volunteer()
		self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))
		self.certify(volunteer, fixtures.CERT_FIRST_AID, today())

		with fixtures.acting_as(user):
			rows = {
				row["certification_type"]: row for row in volunteer_api.my_certifications()["certifications"]
			}

		self.assertTrue(rows[fixtures.CERT_PSYCHOSOCIAL]["lapsed"])
		self.assertFalse(rows[fixtures.CERT_FIRST_AID]["lapsed"])

	def test_reading_it_writes_nothing(self):
		"""The same proof the service carries, made about the surface."""
		volunteer, user = self.logged_in_volunteer()
		held = self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))

		before_modified = frappe.db.get_value(fixtures.CERTIFICATION_DOCTYPE, held.name, "modified")
		before_versions = frappe.db.count(
			"Version", {"ref_doctype": fixtures.CERTIFICATION_DOCTYPE, "docname": held.name}
		)

		with fixtures.acting_as(user):
			self.assertTrue(volunteer_api.my_certifications()["certifications"][0]["lapsed"])

		self.assertEqual(
			frappe.db.get_value(fixtures.CERTIFICATION_DOCTYPE, held.name, "modified"),
			before_modified,
			"showing somebody their certifications modified one",
		)
		self.assertEqual(
			frappe.db.count("Version", {"ref_doctype": fixtures.CERTIFICATION_DOCTYPE, "docname": held.name}),
			before_versions,
			"showing somebody their certifications wrote a version row",
		)

	def test_it_reports_deployability_from_the_same_function_matching_uses(self):
		"""So a person is never told one thing and excluded by another."""
		volunteer, user = self.logged_in_volunteer()
		self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))

		with fixtures.acting_as(user):
			answer = volunteer_api.my_certifications()

		self.assertFalse(answer["deployable"])
		self.assertTrue(answer["blocking_reasons"])
		self.assertEqual(answer["status"], "Active", "a lapse changed their status")
		self.assertEqual(answer["deployable"], certification.is_deployable(volunteer))

	def test_renewing_makes_them_deployable_again_on_the_next_read(self):
		"""No job, no refresh, no stored state to correct. Just the next call."""
		volunteer, user = self.logged_in_volunteer()
		self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, add_days(today(), -100))

		with fixtures.acting_as(user):
			self.assertFalse(volunteer_api.my_certifications()["deployable"])

		self.certify(volunteer, fixtures.CERT_PSYCHOSOCIAL, today())

		with fixtures.acting_as(user):
			answer = volunteer_api.my_certifications()

		self.assertTrue(answer["deployable"])
		self.assertFalse(answer["certifications"][0]["lapsed"])

	def test_each_row_names_the_certification_in_the_societys_own_words(self):
		"""Read live from the type, never copied onto the held certification."""
		volunteer, user = self.logged_in_volunteer()
		self.certify(volunteer, fixtures.CERT_FIRST_AID, today())
		configured = frappe.db.get_value(
			fixtures.CERTIFICATION_TYPE_DOCTYPE, fixtures.CERT_FIRST_AID, "certification_type_name"
		)

		with fixtures.acting_as(user):
			row = volunteer_api.my_certifications()["certifications"][0]

		self.assertEqual(row["certification_type_name"], configured)
		self.assertEqual(row["certification_type"], fixtures.CERT_FIRST_AID)

	def test_relabelling_the_type_relabels_what_they_are_shown(self):
		"""Live, because the name is display and the key is what code refers to."""
		volunteer, user = self.logged_in_volunteer()
		self.certify(volunteer, fixtures.CERT_FIRST_AID, today())

		self.addCleanup(fixtures.make_certification_type, fixtures.CERT_FIRST_AID, 365)
		frappe.db.set_value(
			fixtures.CERTIFICATION_TYPE_DOCTYPE,
			fixtures.CERT_FIRST_AID,
			"certification_type_name",
			"Renamed By The Society",
		)
		frappe.clear_document_cache(fixtures.CERTIFICATION_TYPE_DOCTYPE, fixtures.CERT_FIRST_AID)

		with fixtures.acting_as(user):
			row = volunteer_api.my_certifications()["certifications"][0]

		self.assertEqual(row["certification_type_name"], "Renamed By The Society")

	def test_somebody_who_is_not_a_volunteer_gets_none(self):
		"""An ordinary visitor, not a failure. Same answer as `my_volunteer`."""
		user = fixtures.make_user("selfcert_stranger")

		with fixtures.acting_as(user):
			self.assertIsNone(volunteer_api.my_certifications())

	def test_a_volunteer_holding_nothing_gets_an_empty_list_not_an_error(self):
		volunteer, user = self.logged_in_volunteer()

		with fixtures.acting_as(user):
			answer = volunteer_api.my_certifications()

		self.assertEqual(answer["volunteer"], volunteer.name)
		self.assertEqual(answer["certifications"], [])
		self.assertTrue(answer["deployable"], "holding nothing is not a lapse")

	def test_the_dto_carries_exactly_the_fields_that_were_decided(self):
		"""Explicit, built field by field, so a schema change is not an API change.

		The row shape gained `blocks_deployment` with the coordinator's view, and
		it gained it here too rather than only there. That is deliberate:
		`api/volunteer.py::_certification_rows` is shared by both endpoints
		precisely so the view a volunteer gets of their own training and the view
		a coordinator gets of it cannot drift into disagreeing, and building a
		second shape for one of them would give up exactly that. It is also the
		right thing to tell somebody about their own record: this DTO already
		says whether they are deployable and why not, and the per-row flag is
		what makes a list of dates legible against that answer.
		"""
		volunteer, user = self.logged_in_volunteer()
		self.certify(volunteer, fixtures.CERT_FIRST_AID, today())

		with fixtures.acting_as(user):
			answer = volunteer_api.my_certifications()

		self.assertEqual(
			set(answer),
			{"volunteer", "as_of", "status", "deployable", "blocking_reasons", "certifications"},
		)
		self.assertEqual(
			set(answer["certifications"][0]),
			{
				"name",
				"certification_type",
				"certification_type_name",
				"completion_date",
				"expiry_date",
				"reference_number",
				"lapsed",
				"blocks_deployment",
			},
		)
