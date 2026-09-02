# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Who to call, and the difference between having a number and being allowed to use it.

The rule under test is that a society does not enrol somebody as a volunteer
until it knows who to contact if something happens to them. It is a condition of
**approval**, not of submission, and the first test here is the one that says why
that distinction was chosen: an applicant can send their application in and let
the branch chase the missing detail, rather than being turned away at the door
over work somebody else has to do.
"""

import frappe

from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestSubmissionDoesNotRequireOne(RegistrationTestCase):
	def test_an_application_with_no_emergency_contact_still_submits(self):
		user = fixtures.website_account("no.contact.yet")

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch(), emergency_contacts=[])

		self.assertEqual(application.approval_state, "In Review")
		self.assertEqual(application.emergency_contacts, [])


class TestApprovalRequiresOne(RegistrationTestCase):
	def test_approving_without_one_is_refused(self):
		user = fixtures.website_account("unapprovable.no.contact")

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch(), emergency_contacts=[])

		with self.assertRaises(frappe.ValidationError) as refusal:
			self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		self.assertIn("emergency contact", str(refusal.exception).lower())

	def test_the_refusal_leaves_the_application_where_it_was(self):
		"""A refused approval is not half a decision.

		The gate is in `validate`, so the engine's decision row and state change
		roll back with it. An application left holding a recorded approval it was
		refused would be the worst of both.
		"""
		user = fixtures.website_account("rolled.back")

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch(), emergency_contacts=[])

		with self.assertRaises(frappe.ValidationError):
			self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		application.reload()

		self.assertEqual(application.approval_state, "In Review")
		self.assertFalse(application.volunteer)
		self.assertEqual(application.approval_decisions, [])

	def test_a_contact_we_may_not_call_does_not_count(self):
		"""A number on file we have been told not to use is not an emergency contact.

		This is the test the whole `may_contact_in_emergency` field exists for.
		Counting the row rather than the permission would have the register
		answering yes to a question it cannot answer.
		"""
		user = fixtures.website_account("withheld.permission")

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(
				self.branch(),
				emergency_contacts=fixtures.emergency_contact(may_contact_in_emergency=0),
			)

		with self.assertRaises(frappe.ValidationError):
			self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

	def test_adding_one_afterwards_lets_the_approval_through(self):
		"""The branch chases the detail, and then the decision goes ahead."""
		user = fixtures.website_account("contact.added.later")

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch(), emergency_contacts=[])

		document = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name)
		document.append("emergency_contacts", fixtures.emergency_contact()[0])
		document.save(ignore_permissions=True)

		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		document.reload()

		self.assertEqual(document.approval_state, "Approved")
		self.assertTrue(document.volunteer)

	def test_an_ordinary_registration_carries_one_and_approves(self):
		_, application = self.register_as_volunteer("has.a.contact")

		self.assertEqual(len(application.emergency_contacts), 1)
		self.assertEqual(application.emergency_contacts[0].relationship, "Sister")

		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()

		self.assertEqual(application.approval_state, "Approved")


class TestItStaysOffTheIdentitySpine(RegistrationTestCase):
	def test_nothing_is_written_to_the_red_profile(self):
		"""OD-1, as a test rather than as a paragraph.

		The emergency contact is vmmsx's, on the application, and core's
		`next_of_kin` extension is left alone — so the day it arrives there is
		nothing to reconcile. `identity._WITHHELD` refusing to surface it is the
		other half of the same decision and is tested in the volunteer suite.
		"""
		user, application = self.register_as_volunteer("spine.untouched")
		profile = self.profile_of(user)

		meta = frappe.get_meta(fixtures.PROFILE_DOCTYPE)
		self.assertFalse(meta.has_field("next_of_kin"))

		# Nothing about the contact reached the profile under any spelling.
		values = frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, ["first_name", "phone"], as_dict=True)
		self.assertNotEqual(values.phone, application.emergency_contacts[0].primary_phone)
