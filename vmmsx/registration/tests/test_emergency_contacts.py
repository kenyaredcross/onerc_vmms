# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Who to call, and the difference between having a number and being allowed to use it.

The rule under test is that a society does not take an application until it
knows who to contact if something happens to the applicant. It is checked at
**submission** (`assert_ready`) and again at **approval** (`assert_approvable`):
the second catches records that never came through the registration door, such
as imports and desk edits, which is how the approval tests below build theirs.
"""

import frappe

from vmmsx.patches import install_relationships
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestSubmissionRequiresOne(RegistrationTestCase):
	def test_an_application_with_no_emergency_contact_is_refused(self):
		user = fixtures.website_account("no.contact.yet")

		with fixtures.acting_as(user):
			with self.assertRaises(frappe.MandatoryError) as refusal:
				fixtures.submit_volunteer_form(self.branch(), emergency_contacts=[])

		self.assertIn("emergency contact", str(refusal.exception).lower())

	def test_a_contact_we_may_not_call_is_not_enough_to_submit(self):
		user = fixtures.website_account("uncallable.at.submit")

		with fixtures.acting_as(user):
			with self.assertRaises(frappe.MandatoryError):
				fixtures.submit_volunteer_form(
					self.branch(),
					emergency_contacts=fixtures.emergency_contact(may_contact_in_emergency=0),
				)


class TestApprovalRequiresOne(RegistrationTestCase):
	def submitted_then_stripped(self, handle: str, **contact):
		"""A submitted application whose contact was then removed or withheld.

		Submission now insists on a callable contact, so the only way an
		application reaches approval without one is a later edit or an import.
		"""
		user = fixtures.website_account(handle)

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch())

		document = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name)
		if contact:
			document.emergency_contacts[0].update(contact)
		else:
			document.set("emergency_contacts", [])
		document.save(ignore_permissions=True)

		return document

	def test_approving_without_one_is_refused(self):
		application = self.submitted_then_stripped("unapprovable.no.contact")

		with self.assertRaises(frappe.ValidationError) as refusal:
			self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		self.assertIn("emergency contact", str(refusal.exception).lower())

	def test_the_refusal_leaves_the_application_where_it_was(self):
		"""A refused approval is not half a decision.

		The gate is in `validate`, so the engine's decision row and state change
		roll back with it. An application left holding a recorded approval it was
		refused would be the worst of both.
		"""
		application = self.submitted_then_stripped("rolled.back")

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
		application = self.submitted_then_stripped("withheld.permission", may_contact_in_emergency=0)

		with self.assertRaises(frappe.ValidationError):
			self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

	def test_adding_one_afterwards_lets_the_approval_through(self):
		"""The branch chases the detail, and then the decision goes ahead."""
		application = self.submitted_then_stripped("contact.added.later")

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
		self.assertEqual(application.emergency_contacts[0].relationship, "Sibling")

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


class TestTheRelationshipList(RegistrationTestCase):
	def test_the_form_is_offered_the_standard_list_in_order(self):
		from vmmsx.api.volunteer import application_options

		install_relationships.execute()
		offered = [row["key"] for row in application_options()["relationships"]]

		self.assertEqual(offered[:3], ["Mother", "Father", "Sibling"])
		self.assertIn("Other", offered)

	def test_a_relationship_the_list_does_not_have_is_refused(self):
		with self.assertRaises(frappe.LinkValidationError):
			self.register_as_volunteer(
				"unlisted.relationship",
				emergency_contacts=[{**fixtures.emergency_contact()[0], "relationship": "Not on the list"}],
			)

	def test_a_value_stored_before_the_list_existed_is_kept_but_not_offered(self):
		from vmmsx.api.volunteer import application_options

		_, application = self.register_as_volunteer("legacy.relationship")
		frappe.db.set_value(
			"VMMS Emergency Contact", application.emergency_contacts[0].name, "relationship", "Auntie"
		)

		install_relationships.execute()

		self.assertEqual(frappe.db.get_value("VMMS Relationship", "Auntie", "is_active"), 0)
		self.assertNotIn("Auntie", [row["key"] for row in application_options()["relationships"]])
		# And the application holding it still saves.
		frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name).save(ignore_permissions=True)
