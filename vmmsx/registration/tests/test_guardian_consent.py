# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A minor's application, and the two ticks that stand between it and approval.

The rule: an applicant below the age this society treats as adult cannot be
approved until a parent or guardian's consent has been **recorded** and somebody
at the society has **verified** it. Those are two different facts and the tests
below keep insisting they are, because collapsing them is the obvious
simplification and it is the one that would let an applicant vouch for their own
guardian.

`vmms_minor_age` is society configuration and ships empty. The last class here is
the one that matters most on a site that has not configured it: no age, no rule,
and nothing about the guardian machinery fires at all.
"""

import frappe

from vmmsx.registration.services import society as registration_society
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase
from vmmsx.volunteer.services import application as application_service

EXTRA_TEST_RECORD_DEPENDENCIES = []

MINOR_AGE = 18


class MinorTestCase(RegistrationTestCase):
	"""A society that has said eighteen, restored afterwards.

	The setting is written per class rather than in the shared `setUpClass`,
	because most of this app's suites are about a society that has configured no
	age of majority and must go on being.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fixtures.set_settings(vmms_minor_age=MINOR_AGE)

	@classmethod
	def tearDownClass(cls):
		fixtures.set_settings(vmms_minor_age=0)
		super().tearDownClass()

	def register_minor(self, handle: str, **values):
		values.setdefault("applicant_date_of_birth", fixtures.minor_date_of_birth(16))

		return self.register_as_volunteer(handle, **values)


class TestWhoIsAMinor(MinorTestCase):
	def test_the_society_setting_is_read_back(self):
		self.assertEqual(registration_society.minor_age(), MINOR_AGE)

	def test_a_sixteen_year_old_is_flagged_as_one(self):
		_, application = self.register_minor("young.applicant")

		self.assertTrue(application.is_minor)
		self.assertTrue(application_service.is_minor(application))

	def test_an_adult_is_not(self):
		_, application = self.register_as_volunteer("adult.applicant")

		self.assertFalse(application.is_minor)

	def test_the_flag_is_derived_and_not_something_anybody_types(self):
		"""Written on every save from the date of birth, so a hand-set value does
		not survive contact with the next save."""
		_, application = self.register_as_volunteer("cannot.claim.minor")

		document = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name)
		document.is_minor = 1
		document.save(ignore_permissions=True)

		self.assertFalse(document.is_minor)


class TestApprovingAMinor(MinorTestCase):
	def test_a_minor_can_submit_without_any_guardian_consent(self):
		"""Same reason the emergency contact is not a submission requirement: the
		branch may be the one who has to go and get the signed form."""
		_, application = self.register_minor("submits.without.consent")

		self.assertEqual(application.approval_state, "In Review")

	def test_approving_with_no_guardian_consent_is_refused(self):
		_, application = self.register_minor("no.consent")

		with self.assertRaises(frappe.ValidationError) as refusal:
			self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		self.assertIn("guardian", str(refusal.exception).lower())

	def test_a_recorded_but_unverified_consent_is_not_enough(self):
		"""The test this whole feature turns on.

		A consent the applicant typed in and nobody has checked is exactly the
		ordinary state of a freshly submitted application, and approving on it
		would make the verification field decorative.
		"""
		_, application = self.register_minor(
			"unverified.consent", guardian_consents=fixtures.guardian_consent()
		)

		self.assertTrue(application.guardian_consents[0].consent_given)
		self.assertFalse(application.guardian_consents[0].is_verified)

		with self.assertRaises(frappe.ValidationError):
			self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

	def test_a_verified_consent_lets_the_approval_through(self):
		_, application = self.register_minor(
			"verified.consent", guardian_consents=fixtures.guardian_consent()
		)

		fixtures.verify_guardian_consent(application)
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		application.reload()

		self.assertEqual(application.approval_state, "Approved")
		self.assertTrue(application.volunteer)

	def test_a_verified_consent_that_was_never_given_is_not_enough(self):
		"""Both ticks, and neither substitutes for the other."""
		_, application = self.register_minor(
			"verified.but.refused",
			guardian_consents=fixtures.guardian_consent(consent_given=0, consent_date=None),
		)

		fixtures.verify_guardian_consent(application)

		with self.assertRaises(frappe.ValidationError):
			self.approve(fixtures.APPLICATION_DOCTYPE, application.name)


class TestTheApplicantCannotVerifyThemselves(MinorTestCase):
	def test_the_portal_cannot_send_a_verification(self):
		"""`GUARDIAN_CONSENT_FIELDS` is an allow-list, and this is why.

		An applicant who could post `is_verified` could approve their own minor
		application, which is the single thing this feature exists to prevent.
		"""
		user = fixtures.website_account("tries.to.self.verify")

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(
				self.branch(),
				applicant_date_of_birth=fixtures.minor_date_of_birth(16),
				guardian_consents=fixtures.guardian_consent(is_verified=1, verified_by="Administrator"),
			)

		self.assertFalse(application.guardian_consents[0].is_verified)
		self.assertFalse(application.guardian_consents[0].verified_by)

		with self.assertRaises(frappe.ValidationError):
			self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

	def test_re_saving_a_draft_clears_a_verification(self):
		"""Fail-closed, and deliberately so.

		The endpoint replaces the table wholesale, so an applicant editing a
		returned application resubmits guardian details with no verification on
		them. A verification attaches to the details that were verified, and
		these have just changed.
		"""
		from vmmsx.api import registration as registration_api

		user = fixtures.website_account("resubmits.guardian")

		with fixtures.acting_as(user):
			draft = registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				date_of_birth=fixtures.minor_date_of_birth(16),
				declarations_accepted=fixtures.required_declarations(),
				guardian_consents=fixtures.guardian_consent(),
			)

		document = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, draft["name"])
		fixtures.verify_guardian_consent(document)
		self.assertTrue(
			frappe.get_doc(fixtures.APPLICATION_DOCTYPE, draft["name"]).guardian_consents[0].is_verified
		)

		with fixtures.acting_as(user):
			registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				date_of_birth=fixtures.minor_date_of_birth(16),
				declarations_accepted=fixtures.required_declarations(),
				guardian_consents=fixtures.guardian_consent(phone="+254700000099"),
			)

		again = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, draft["name"])

		self.assertFalse(again.guardian_consents[0].is_verified)
		self.assertFalse(again.guardian_consents[0].verified_by)


class TestVerificationIsAttributed(MinorTestCase):
	def test_ticking_it_records_who_and_when(self):
		_, application = self.register_minor("attributed", guardian_consents=fixtures.guardian_consent())

		with fixtures.acting_as(self.approver):
			document = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name)
			document.guardian_consents[0].is_verified = 1
			document.save(ignore_permissions=True)

		row = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name).guardian_consents[0]

		self.assertEqual(row.verified_by, self.approver)
		self.assertTrue(row.verified_on)

	def test_withdrawing_it_takes_the_attribution_with_it(self):
		"""A name left behind would say somebody vouched for a consent that is no
		longer marked as verified."""
		_, application = self.register_minor(
			"withdrawn.attribution", guardian_consents=fixtures.guardian_consent()
		)

		fixtures.verify_guardian_consent(application)

		document = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name)
		document.guardian_consents[0].is_verified = 0
		document.save(ignore_permissions=True)

		row = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name).guardian_consents[0]

		self.assertFalse(row.verified_by)
		self.assertFalse(row.verified_on)


class TestGuardianAndEmergencyContactStaySeparate(MinorTestCase):
	def test_one_person_in_both_roles_is_two_records(self):
		"""The very common case, and the one a single merged row would break.

		A mother is both the guardian who consents and the person to call. They
		are different acts with different legal weight, and a society that
		withdrew one must not thereby have withdrawn the other.
		"""
		_, application = self.register_minor(
			"mother.does.both",
			emergency_contacts=fixtures.emergency_contact(
				contact_name="Grace Otieno", relationship="Mother", primary_phone="+254700000002"
			),
			guardian_consents=fixtures.guardian_consent(),
		)

		self.assertEqual(len(application.emergency_contacts), 1)
		self.assertEqual(len(application.guardian_consents), 1)
		self.assertEqual(
			application.emergency_contacts[0].contact_name,
			application.guardian_consents[0].guardian_name,
		)

		# Removing the guardian consent leaves the emergency contact standing.
		document = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name)
		document.guardian_consents = []
		document.save(ignore_permissions=True)

		self.assertEqual(len(document.emergency_contacts), 1)


class TestAnUnconfiguredSocietyIsUnaffected(RegistrationTestCase):
	"""No `vmms_minor_age`, which is the shipped state. Nothing fires."""

	def test_nobody_is_a_minor(self):
		self.assertIsNone(registration_society.minor_age())

		_, application = self.register_as_volunteer(
			"young.but.unconfigured",
			applicant_date_of_birth=fixtures.minor_date_of_birth(16),
		)

		self.assertFalse(application.is_minor)

	def test_a_young_applicant_is_approved_with_no_guardian_consent(self):
		"""A society that has not configured minor handling has not thereby said
		it accepts nobody. Guessing eighteen would be this app inventing a law."""
		_, application = self.register_as_volunteer(
			"approved.unconfigured",
			applicant_date_of_birth=fixtures.minor_date_of_birth(16),
		)

		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()

		self.assertEqual(application.approval_state, "Approved")


class TestGuardianDetailsAreNotPublic(MinorTestCase):
	"""Who may read a child's parent's phone number.

	The guardian block rides on the application and has no access rule of its
	own, deliberately: an application's readers are decided in one place, and a
	second rule beside it would eventually disagree. So the test is that the
	place is doing its job — the approver the application routed to can read it,
	and another website account cannot read it at all.
	"""

	def test_the_approver_it_routed_to_reads_the_guardian_details(self):
		from vmmsx.api import volunteer as volunteer_api

		_, application = self.register_minor(
			"guardian.visible", guardian_consents=fixtures.guardian_consent()
		)

		with fixtures.acting_as(self.approver):
			decision = volunteer_api.get_decision(application.name)

		self.assertTrue(decision["is_minor"])
		self.assertEqual(decision["guardian_consents"][0]["guardian_name"], "Grace Otieno")
		self.assertEqual(decision["guardian_consents"][0]["phone"], "+254700000002")
		# The reviewer's own half travels too, because "has anybody checked this"
		# is exactly what the approver needs and what the gate will refuse over.
		self.assertFalse(decision["guardian_consents"][0]["is_verified"])

	def test_another_applicant_cannot_read_them(self):
		from vmmsx.api import volunteer as volunteer_api

		_, application = self.register_minor(
			"guardian.private", guardian_consents=fixtures.guardian_consent()
		)

		stranger = fixtures.website_account("guardian.stranger")

		with fixtures.acting_as(stranger), self.assertRaises(frappe.PermissionError):
			volunteer_api.get_decision(application.name)

	def test_the_emergency_contact_is_just_as_closed(self):
		from vmmsx.api import volunteer as volunteer_api

		_, application = self.register_minor("contact.private")
		stranger = fixtures.website_account("contact.stranger")

		with fixtures.acting_as(stranger), self.assertRaises(frappe.PermissionError):
			volunteer_api.get_decision(application.name)
