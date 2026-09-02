# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Who else hears about it, when the volunteer is a child.

A society that accepts sixteen-year-olds has undertaken to keep their parent
informed, and until now it wrote to the young person and to nobody else. The
guardian's details existed only as a row on an application that had already been
decided — which is the wrong place for them, because everything a society writes
to a young volunteer afterwards happens long after that application is closed.

Three things are asserted here, and the second is the one that is easy to get
wrong and expensive to get wrong:

1. **Accepting a minor copies their guardian onto the person**, once, from the
   consent row that was verified.
2. **Whether to copy is asked at send time, against today's date.** A stored
   `is_minor` flag would have a society writing to somebody's parents years after
   their eighteenth birthday, which is not a courtesy — it is disclosing an
   adult's business to a third party.
3. **A society that has configured no age of majority copies nobody**, which is
   the same fail-open direction every other reader of that setting takes.
"""

import frappe
from frappe.utils import add_years, today

from vmmsx.notifications.services import audience, direct
from vmmsx.registration.services import guardian
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

MINOR_AGE = 18
GUARDIAN_DOCTYPE = "VMMS Guardian"
GUARDIAN_EMAIL = "grace.otieno@example.com"


class GuardianTestCase(RegistrationTestCase):
	"""A society that has said eighteen, restored afterwards.

	Written per class rather than into the shared arrangement, for the reason
	`test_guardian_consent.MinorTestCase` gives: most of this app's suites are
	about a society that has configured no age of majority and must go on being.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fixtures.set_settings(vmms_minor_age=MINOR_AGE)

	@classmethod
	def tearDownClass(cls):
		fixtures.set_settings(vmms_minor_age=0)
		super().tearDownClass()

	def accept_a_minor(self, handle: str, years_old: int = 16, **consent):
		"""Register somebody under age, verify the consent, approve. Returns both."""
		values = {"email": GUARDIAN_EMAIL, **consent}
		rows = fixtures.guardian_consent(**values)

		_, application = self.register_as_volunteer(
			handle,
			applicant_date_of_birth=fixtures.minor_date_of_birth(years_old),
			guardian_consents=rows,
		)

		fixtures.verify_guardian_consent(application)
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()

		return application, application.red_profile

	def guardians_of(self, red_profile: str) -> list[dict]:
		return frappe.get_all(
			GUARDIAN_DOCTYPE,
			filters={"red_profile": red_profile},
			fields=["name", "guardian_name", "email", "phone", "is_verified", "source_application"],
		)


class TestCarryingTheGuardianForward(GuardianTestCase):
	def test_accepting_a_minor_records_their_guardian_against_the_person(self):
		application, red_profile = self.accept_a_minor("has.a.guardian")
		rows = self.guardians_of(red_profile)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].guardian_name, "Grace Otieno")
		self.assertEqual(rows[0].email, GUARDIAN_EMAIL)
		self.assertEqual(rows[0].source_application, application.name)

	def test_the_verification_travels_with_it(self):
		"""What a society checked stays checked. Re-verifying a consent that has
		already been verified once, on a second record, would be asking somebody
		to vouch for a document they never saw."""
		_, red_profile = self.accept_a_minor("verified.travels")

		self.assertTrue(self.guardians_of(red_profile)[0].is_verified)

	def test_adopting_twice_records_one_guardian(self):
		"""Idempotent, keyed on the guardian rather than on the application: a
		society should not end up writing to the same parent twice because
		somebody re-ran an acceptance."""
		application, red_profile = self.accept_a_minor("adopted.twice")

		guardian.adopt(application)
		guardian.adopt(application)

		self.assertEqual(len(self.guardians_of(red_profile)), 1)

	def test_an_adult_application_records_no_guardian(self):
		_, application = self.register_as_volunteer("no.guardian.needed")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()

		self.assertEqual(self.guardians_of(application.red_profile), [])

	def test_the_consent_rows_stay_on_the_application(self):
		"""Copied out, not moved. The consent is part of the record of a decision
		and the standing guardian record is a different thing with a different
		life."""
		application, _ = self.accept_a_minor("consent.stays.put")

		self.assertEqual(len(application.guardian_consents), 1)
		self.assertTrue(application.guardian_consents[0].is_verified)


class TestWhoGetsCopied(GuardianTestCase):
	def test_a_minor_has_their_guardian_copied(self):
		_, red_profile = self.accept_a_minor("copy.the.parent")

		self.assertEqual(guardian.emails_for(red_profile), [GUARDIAN_EMAIL])

	def test_the_age_is_judged_today_and_not_at_registration(self):
		"""The test this whole design turns on.

		The guardian record is untouched and the consent on the application still
		says what it said. What changed is the person's age, and that is the only
		thing the copy rule reads.
		"""
		_, red_profile = self.accept_a_minor("turns.eighteen")

		self.assertEqual(guardian.emails_for(red_profile), [GUARDIAN_EMAIL])

		frappe.db.set_value(
			"Red Profile", red_profile, "date_of_birth", add_years(today(), -21)
		)
		frappe.clear_document_cache("Red Profile", red_profile)

		self.assertEqual(guardian.emails_for(red_profile), [])
		self.assertTrue(self.guardians_of(red_profile), "the record itself is not deleted")

	def test_a_guardian_with_no_address_is_on_the_record_and_not_written_to(self):
		_, red_profile = self.accept_a_minor("unreachable.parent", email=None)

		self.assertTrue(self.guardians_of(red_profile))
		self.assertEqual(guardian.emails_for(red_profile), [])

	def test_a_deactivated_guardian_stops_being_copied(self):
		_, red_profile = self.accept_a_minor("replaced.parent")
		row = self.guardians_of(red_profile)[0]

		frappe.db.set_value(GUARDIAN_DOCTYPE, row.name, "is_active", 0)

		self.assertEqual(guardian.emails_for(red_profile), [])

	def test_the_phone_answers_the_same_question_for_the_sms_channel(self):
		_, red_profile = self.accept_a_minor("texts.the.parent")

		self.assertEqual(guardian.phones_for(red_profile), ["+254700000002"])


class TestTheNotificationServicesAsk(GuardianTestCase):
	def test_a_branch_announcement_reaches_the_guardian(self):
		"""One insertion point rather than one per announcement service."""
		_, red_profile = self.accept_a_minor("hears.announcements")

		self.assertIn(GUARDIAN_EMAIL, audience.emails({red_profile}))

	def test_an_sms_audience_carries_the_guardian_too(self):
		_, red_profile = self.accept_a_minor("hears.texts")

		self.assertIn("+254700000002", audience.phones({red_profile}))

	def test_a_deployment_or_task_notification_copies_the_guardian(self):
		"""`direct.tell` is in-app only for the person; a guardian holds no login,
		so this is the one path that has to reach out by mail."""
		application, _ = self.accept_a_minor("hears.about.deployments")

		copied = direct._copy_guardians(application.volunteer, "You have been asked to help")

		self.assertEqual(copied, [GUARDIAN_EMAIL])

	def test_a_notification_about_somebody_else_copies_nobody(self):
		"""`about` is whose life it is, not who has a screen to show it on. A
		message to a coordinator names no volunteer and copies no parent."""
		self.assertEqual(direct._copy_guardians(None, "Somebody answered an invitation"), [])


class TestASocietyThatHasNotConfiguredAnAgeOfMajority(RegistrationTestCase):
	"""The shipped default, where none of this fires at all."""

	def test_nobody_is_a_minor(self):
		_, application = self.register_as_volunteer("no.age.configured")

		self.assertFalse(guardian.is_minor(application.red_profile))

	def test_nobody_is_copied_even_where_a_guardian_is_recorded(self):
		_, application = self.register_as_volunteer(
			"guardian.but.no.age",
			applicant_date_of_birth=fixtures.minor_date_of_birth(16),
			guardian_consents=fixtures.guardian_consent(email=GUARDIAN_EMAIL),
		)

		guardian.adopt(application)

		self.assertEqual(guardian.emails_for(application.red_profile), [])
