# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Membership on one page for somebody whose details the society already holds.

`my_quick_membership` says who qualifies: a volunteer, or somebody whose
volunteer application is pending or in review. The one-page form then sends
only the membership — type, branch, the phone that pays, the declarations —
and must leave the person's own record exactly as it was.
"""

import frappe

from vmmsx.api import registration as registration_api
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestQuickMembership(RegistrationTestCase):
	def test_a_newcomer_gets_the_full_form(self):
		user = fixtures.website_account("quick.newcomer")

		with fixtures.acting_as(user):
			self.assertFalse(registration_api.my_quick_membership()["available"])

	def test_a_pending_volunteer_application_qualifies(self):
		user, application = self.register_as_volunteer("quick.pending")
		self.assertIn(application.approval_state, registration_api.KNOWN_APPLICATION_STATES)

		with fixtures.acting_as(user):
			answer = registration_api.my_quick_membership()

		self.assertTrue(answer["available"])
		self.assertEqual(str(answer["date_of_birth"]), fixtures.DEFAULT_DATE_OF_BIRTH)

	def test_a_draft_volunteer_application_qualifies(self):
		user = fixtures.website_account("quick.draft")
		with fixtures.acting_as(user):
			registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				first_name="Amina",
				last_name="Draft",
				date_of_birth=fixtures.DEFAULT_DATE_OF_BIRTH,
			)
			self.assertTrue(registration_api.my_quick_membership()["available"])

	def test_a_profile_short_of_a_membership_detail_gets_the_full_form(self):
		"""The society asks members for identity; this draft has no date of birth."""
		user = fixtures.website_account("quick.short")
		with fixtures.acting_as(user):
			registration_api.save_my_volunteer_draft(geo_node=self.branch(), first_name="Amina", last_name="Short")
			self.assertFalse(registration_api.my_quick_membership()["available"])

	def test_a_volunteer_qualifies(self):
		user, application = self.register_as_volunteer("quick.volunteer")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		with fixtures.acting_as(user):
			self.assertTrue(registration_api.my_quick_membership()["available"])

	def test_the_one_page_form_joins_without_touching_the_person(self):
		user, application = self.register_as_volunteer("quick.joins")
		profile = application.red_profile
		before = frappe.db.get_value(
			"Red Profile", profile, ["first_name", "last_name", "residency_type", "home_geo_node"], as_dict=True
		)

		with fixtures.acting_as(user):
			registration_api.save_my_member_draft(
				membership_type=fixtures.TYPE_ROUTED,
				geo_node=self.branch(),
				payer_phone="0711000222",
				answers={},
				declarations_accepted=fixtures.required_declarations(fixtures.MEMBERSHIP_DOCTYPE),
			)
			result = registration_api.submit_my_registration("member")

		self.assertTrue(result["name"])
		after = frappe.db.get_value(
			"Red Profile", profile, ["first_name", "last_name", "residency_type", "home_geo_node"], as_dict=True
		)
		self.assertEqual(before, after)
