"""A volunteer's own profile: how complete it is, and their emergency contacts.

The completeness list asks the registration's own submission checks, so these
tests hold the shape and the things this module adds — the photo, the
emergency contact read off the volunteer record — rather than re-testing every
rule `application.assert_ready` already has suites for.
"""

import frappe

from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase


class TestProfileCompleteness(RegistrationTestCase):
	def accepted(self, handle: str):
		user, application = self.register_as_volunteer(handle)
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()
		return user, application

	def test_a_new_volunteer_is_told_what_is_still_missing(self):
		from vmmsx.api import volunteer as volunteer_api

		user, _application = self.accepted("completeness.reader")

		with fixtures.acting_as(user):
			answer = volunteer_api.my_profile_completeness()

		items = {item["key"]: item for item in answer["items"]}

		# Everything the registration insisted on is already there.
		for key in ("date_of_birth", "citizenship", "identification", "residence", "education"):
			self.assertTrue(items[key]["done"], key)

		# The contact came across from the application at acceptance.
		self.assertTrue(items["emergency_contact"]["done"])

		# The fixture registers without a photograph.
		self.assertFalse(items["photo"]["done"])
		self.assertEqual(items["photo"]["section"], "photo")
		self.assertLess(answer["percent"], 100)
		self.assertEqual(answer["done"], sum(1 for item in answer["items"] if item["done"]))
		self.assertEqual(answer["total"], len(answer["items"]))

	def test_somebody_who_is_not_a_volunteer_gets_nothing(self):
		from vmmsx.api import volunteer as volunteer_api

		stranger = fixtures.website_account("completeness.stranger")

		with fixtures.acting_as(stranger):
			self.assertIsNone(volunteer_api.my_profile_completeness())

	def test_ninety_nine_is_the_most_an_incomplete_profile_shows(self):
		from vmmsx.volunteer.services import completeness

		_user, application = self.accepted("completeness.rounding")
		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, application.volunteer)

		answer = completeness.of_volunteer(volunteer)
		missing = [item for item in answer["items"] if not item["done"]]

		self.assertTrue(missing)
		self.assertLessEqual(answer["percent"], 99)


class TestMyEmergencyContacts(RegistrationTestCase):
	def accepted(self, handle: str):
		user, application = self.register_as_volunteer(handle)
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()
		return user, application

	def test_acceptance_gives_the_volunteer_their_contacts(self):
		from vmmsx.api import volunteer as volunteer_api

		user, _application = self.accepted("contacts.seeded")

		with fixtures.acting_as(user):
			mine = volunteer_api.my_volunteer()

		self.assertEqual([row["contact_name"] for row in mine["emergency_contacts"]], ["Mercy Otieno"])
		self.assertTrue(mine["emergency_contacts"][0]["may_contact_in_emergency"])

	def test_the_volunteer_replaces_them_and_the_application_is_untouched(self):
		from vmmsx.api import volunteer as volunteer_api

		user, application = self.accepted("contacts.replaced")
		fixtures.ensure_relationship("Parent")

		with fixtures.acting_as(user):
			saved = volunteer_api.update_my_emergency_contacts(
				[
					{
						"contact_name": "Grace Wanjiru",
						"relationship": "Parent",
						"primary_phone": "+254700000002",
						"may_contact_in_emergency": True,
					}
				]
			)

		self.assertEqual([row["contact_name"] for row in saved], ["Grace Wanjiru"])

		application.reload()
		self.assertEqual([row.contact_name for row in application.emergency_contacts], ["Mercy Otieno"])

	def test_nobody_to_call_is_refused(self):
		from vmmsx.api import volunteer as volunteer_api

		user, _application = self.accepted("contacts.emptied")

		with fixtures.acting_as(user):
			with self.assertRaises(frappe.MandatoryError):
				volunteer_api.update_my_emergency_contacts([])

			with self.assertRaises(frappe.MandatoryError):
				volunteer_api.update_my_emergency_contacts(
					[
						{
							"contact_name": "Grace Wanjiru",
							"relationship": "Sibling",
							"primary_phone": "+254700000002",
							"may_contact_in_emergency": False,
						}
					]
				)

	def test_a_contact_must_be_whole_and_use_the_list(self):
		from vmmsx.api import volunteer as volunteer_api

		user, _application = self.accepted("contacts.halfway")

		with fixtures.acting_as(user):
			with self.assertRaises(frappe.MandatoryError):
				volunteer_api.update_my_emergency_contacts(
					[{"contact_name": "Grace Wanjiru", "relationship": "Sibling", "may_contact_in_emergency": 1}]
				)

			with self.assertRaises(frappe.ValidationError):
				volunteer_api.update_my_emergency_contacts(
					[
						{
							"contact_name": "Grace Wanjiru",
							"relationship": "Not A Real Relationship",
							"primary_phone": "+254700000002",
							"may_contact_in_emergency": 1,
						}
					]
				)

	def test_somebody_who_is_not_a_volunteer_cannot_write_any(self):
		from vmmsx.api import volunteer as volunteer_api

		stranger = fixtures.website_account("contacts.stranger")

		with fixtures.acting_as(stranger), self.assertRaises(frappe.PermissionError):
			volunteer_api.update_my_emergency_contacts(fixtures.emergency_contact())

	def test_the_patch_fills_a_volunteer_accepted_before_the_table_existed(self):
		from vmmsx.patches import seed_volunteer_emergency_contacts

		_user, application = self.accepted("contacts.backfilled")
		frappe.db.delete(
			"VMMS Emergency Contact", {"parent": application.volunteer, "parenttype": "VMMS Volunteer"}
		)

		seed_volunteer_emergency_contacts.execute()

		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, application.volunteer)
		self.assertEqual([row.contact_name for row in volunteer.emergency_contacts], ["Mercy Otieno"])
