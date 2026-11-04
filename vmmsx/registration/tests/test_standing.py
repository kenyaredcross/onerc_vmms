# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Somebody who already belongs.

`registration.my_standing` tells the branch directory and the join wizard where
the signed-in person already is, and `_assert_not_a_volunteer` refuses a second
volunteer application from somebody the society already has: approving it would
move nobody, because `volunteer.ensure` keeps the placement a volunteer has.
"""

import frappe

from vmmsx.api import registration as registration_api
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestStanding(RegistrationTestCase):
	def _volunteer(self, handle: str):
		user, application = self.register_as_volunteer(handle)
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)
		application.reload()
		return user, application

	def test_an_undecided_applicant_is_not_yet_a_volunteer(self):
		user, _ = self.register_as_volunteer("standing.waiting")

		with fixtures.acting_as(user):
			standing = registration_api.my_standing()

		self.assertIsNone(standing["volunteer"])

	def test_an_accepted_volunteer_is_told_their_branch(self):
		user, _ = self._volunteer("standing.accepted")

		with fixtures.acting_as(user):
			standing = registration_api.my_standing()

		self.assertEqual(standing["volunteer"]["branch"], self.branch())
		self.assertEqual(standing["volunteer"]["status"], "Active")
		self.assertEqual(
			standing["volunteer"]["branch_label"],
			frappe.db.get_value("Geo Node", self.branch(), "geo_node_name"),
		)

	def test_a_second_volunteer_application_is_refused(self):
		user, _ = self._volunteer("standing.again")
		before = frappe.db.count(fixtures.APPLICATION_DOCTYPE)

		with fixtures.acting_as(user), self.assertRaisesRegex(frappe.ValidationError, "already a volunteer"):
			fixtures.submit_volunteer_form(self.branch())

		self.assertEqual(frappe.db.count(fixtures.APPLICATION_DOCTYPE), before)

	def test_nor_can_one_be_saved_as_a_draft(self):
		user, _ = self._volunteer("standing.draft")

		with fixtures.acting_as(user), self.assertRaisesRegex(frappe.ValidationError, "already a volunteer"):
			registration_api.save_my_volunteer_draft(geo_node=self.branch())

	def test_a_volunteer_who_left_may_come_back(self):
		user, application = self._volunteer("standing.returning")
		frappe.db.set_value("VMMS Volunteer", application.volunteer, "status", "Exited")

		with fixtures.acting_as(user):
			self.assertIsNone(registration_api.my_standing()["volunteer"])
			fixtures.submit_volunteer_form(self.branch())

	def test_a_membership_is_listed_with_its_branch(self):
		user, membership = self.register_as_member("standing.member", fixtures.TYPE_AUTO)
		fixtures.confirm_payment_through_manual_driver(membership)

		with fixtures.acting_as(user):
			standing = registration_api.my_standing()

		self.assertEqual([row["branch"] for row in standing["memberships"]], [self.branch()])
		self.assertEqual(standing["memberships"][0]["status"], "Active")
		self.assertIsNone(standing["volunteer"])

	def test_somebody_with_no_profile_belongs_nowhere(self):
		user = fixtures.website_account("standing.nobody")

		with fixtures.acting_as(user):
			self.assertEqual(registration_api.my_standing(), {"volunteer": None, "memberships": []})

	def test_a_guest_is_refused(self):
		with fixtures.acting_as("Guest"), self.assertRaises(frappe.PermissionError):
			registration_api.my_standing()
