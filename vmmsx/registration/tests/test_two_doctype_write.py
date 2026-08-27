# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One form, two documents, and no identity left on the satellite.

The seam this suite covers is the one a native Web Form cannot do by itself: it
writes one document, and a registration needs core's identity spine as well. So
`before_insert` resolves or creates the Red Profile for the session user, links
it, and blanks the fields it read.

Four properties, each of which would be a real defect if it stopped holding:

1. the profile is created and carries **this** login;
2. the identity the form collected is on the profile and **not** on the record;
3. registering again reuses the profile rather than making a second;
4. a desk insert is untouched by any of it.
"""

import frappe

from vmmsx.registration.services import intake
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestTheProfileIsCreatedAndLinked(RegistrationTestCase):
	def test_the_form_creates_a_red_profile_for_the_session_user(self):
		user, application = self.register_as_volunteer("new.applicant")

		self.assertTrue(application.red_profile)
		self.assertEqual(frappe.db.get_value(fixtures.PROFILE_DOCTYPE, application.red_profile, "user"), user)

	def test_the_profile_carries_what_the_form_collected(self):
		_, application = self.register_as_volunteer(
			"detailed.applicant",
			applicant_first_name="Wanjiku",
			applicant_last_name="Njoroge",
			applicant_phone="+254700111222",
		)

		profile = frappe.get_doc(fixtures.PROFILE_DOCTYPE, application.red_profile)

		self.assertEqual(profile.first_name, "Wanjiku")
		self.assertEqual(profile.last_name, "Njoroge")
		self.assertEqual(profile.phone, "+254700111222")

	def test_the_profile_email_is_the_login_and_not_a_form_value(self):
		"""An email on a public form is a claim; the login is the site's answer."""
		user, application = self.register_as_volunteer("claims.nothing")

		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, application.red_profile, "email"), user
		)

	def test_the_branch_they_chose_is_recorded_on_their_profile(self):
		_, application = self.register_as_volunteer("placed.applicant")

		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, application.red_profile, "home_geo_node"),
			self.branch(),
		)


class TestNoIdentityReachesTheSatellite(RegistrationTestCase):
	def test_the_intake_fields_are_empty_on_the_saved_application(self):
		_, application = self.register_as_volunteer(
			"clean.applicant", applicant_first_name="Halima", applicant_phone="+254700333444"
		)

		stored = frappe.db.get_value(
			fixtures.APPLICATION_DOCTYPE, application.name, list(intake.INTAKE_FIELDS), as_dict=True
		)

		self.assertEqual([value for value in stored.values() if value], [])

	def test_the_intake_fields_are_empty_on_the_saved_membership(self):
		_, membership = self.register_as_member(
			"clean.member", fixtures.TYPE_ROUTED, applicant_first_name="Halima"
		)

		stored = frappe.db.get_value(
			fixtures.MEMBERSHIP_DOCTYPE, membership.name, list(intake.INTAKE_FIELDS), as_dict=True
		)

		self.assertEqual([value for value in stored.values() if value], [])

	def test_a_desk_user_cannot_store_identity_by_typing_into_the_section(self):
		"""`validate` blanks them whatever path the save came down.

		The registration path already emptied them before the record existed;
		this is the guarantee that does not depend on that path having run.
		"""
		profile = fixtures.make_profile("Paper", "Registrant")

		application = frappe.get_doc(
			{
				"doctype": fixtures.APPLICATION_DOCTYPE,
				"red_profile": profile,
				"geo_node": self.branch(),
				"applicant_first_name": "Typed",
				"applicant_phone": "+254700555666",
			}
		).insert()

		self.assertIsNone(
			frappe.db.get_value(fixtures.APPLICATION_DOCTYPE, application.name, "applicant_first_name")
		)
		self.assertIsNone(
			frappe.db.get_value(fixtures.APPLICATION_DOCTYPE, application.name, "applicant_phone")
		)


class TestRegisteringAgainReusesTheProfile(RegistrationTestCase):
	def test_a_volunteer_application_reuses_an_existing_profile(self):
		user = fixtures.website_account("returning.applicant")
		profile = intake.for_user(user, {"first_name": "Amina", "last_name": "Otieno"})

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch())

		self.assertEqual(self.profile_count(user), 1)
		self.assertEqual(
			frappe.db.get_value(fixtures.APPLICATION_DOCTYPE, application.name, "red_profile"),
			profile,
		)

	def test_an_existing_profile_is_not_overwritten_by_a_later_form(self):
		"""Registration adds what core does not know. It never contradicts it."""
		user = fixtures.website_account("stable.applicant")
		profile_name = intake.for_user(
			user,
			{
				"first_name": "Original",
				"last_name": "Applicant",
				"phone": "+254700777888",
			},
		)

		with fixtures.acting_as(user):
			fixtures.submit_volunteer_form(
				self.branch(), applicant_first_name="Changed", applicant_phone="+254700999000"
			)

		profile = frappe.get_doc(fixtures.PROFILE_DOCTYPE, profile_name)

		self.assertEqual(profile.first_name, "Original")
		self.assertEqual(profile.phone, "+254700777888")

	def test_a_field_core_does_not_know_yet_is_filled_in(self):
		"""The other half of the same rule: empty is not the same as set."""
		user = fixtures.website_account("growing.applicant")
		profile = intake.for_user(user, {"first_name": "Amina", "last_name": "Otieno"})

		self.assertFalse(frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "phone"))

		with fixtures.acting_as(user):
			fixtures.submit_volunteer_form(self.branch(), applicant_phone="+254700121212")

		self.assertEqual(
			frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "phone"), "+254700121212"
		)


class TestTheDeskPathIsUntouched(RegistrationTestCase):
	def test_a_clerk_creating_an_application_keeps_the_profile_they_named(self):
		"""The claim runs only for somebody registering themselves.

		A coordinator entering a paper application must never have their own
		profile attached to it, and this is the test that would fail if the
		claim ever stopped checking.
		"""
		profile = fixtures.make_profile("Somebody", "Else")

		application = frappe.get_doc(
			{
				"doctype": fixtures.APPLICATION_DOCTYPE,
				"red_profile": profile,
				"geo_node": self.branch(),
			}
		).insert()

		self.assertEqual(application.red_profile, profile)

	def test_a_desk_insert_stays_at_draft_and_is_not_submitted(self):
		"""Only a registration is put into motion on the save that created it.

		Every other path in this app inserts and then submits deliberately, and
		none of them may start behaving differently.
		"""
		profile = fixtures.make_profile("Draft", "Applicant")

		application = frappe.get_doc(
			{
				"doctype": fixtures.APPLICATION_DOCTYPE,
				"red_profile": profile,
				"geo_node": self.branch(),
			}
		).insert()

		self.assertEqual(
			frappe.db.get_value(fixtures.APPLICATION_DOCTYPE, application.name, "approval_state"), "Draft"
		)

	def test_a_registration_is_put_into_motion_by_the_form(self):
		"""The positive half. Without it the test above would pass for a hook
		that never submitted anything at all."""
		_, application = self.register_as_volunteer("moving.applicant")

		self.assertEqual(
			frappe.db.get_value(fixtures.APPLICATION_DOCTYPE, application.name, "approval_state"),
			"In Review",
		)


class TestAdoption(RegistrationTestCase):
	def test_a_paper_profile_with_the_same_email_is_adopted_not_duplicated(self):
		"""Somebody the branch already registered, who now makes an account.

		Core makes `Red Profile.email` unique, so the alternative to adopting is
		the insert being refused and the person being stuck.
		"""
		user = fixtures.website_account("already.known")
		existing = fixtures.make_profile("Already", "Known", email=user)

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch())

		self.assertEqual(application.red_profile, existing)
		self.assertEqual(self.profile_count(user), 1)

	def test_a_profile_already_bound_to_another_login_is_refused(self):
		"""Two identities pointing at one person is an administrator's problem.

		A public form resolving it by overwriting whichever it found would be the
		worst possible answer.
		"""
		other = fixtures.website_account("the.other.person")
		user = fixtures.website_account("the.claimant")

		# A profile carrying this claimant's email but somebody else's login.
		# Written directly, because nothing in the app can produce it.
		profile = fixtures.make_profile("Contested", "Identity", email=user)
		frappe.db.set_value(fixtures.PROFILE_DOCTYPE, profile, "user", other)
		frappe.clear_document_cache(fixtures.PROFILE_DOCTYPE, profile)

		with fixtures.acting_as(user), self.assertRaises(frappe.ValidationError):
			fixtures.submit_volunteer_form(self.branch())
