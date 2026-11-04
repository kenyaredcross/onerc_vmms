# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A society that never cancels memberships (Kenya) is offered no cancel action, and the server refuses one."""

import frappe

from vmmsx.member.services import approval
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase
from vmmsx.patches import install_membership_cancellation_setting

EXTRA_TEST_RECORD_DEPENDENCIES = []

SETTINGS = "National Society Settings"


class TestMembershipCancellationSetting(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		install_membership_cancellation_setting.execute()
		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_FREE, approval.MODE_ROUTED, fee=0)

	def setUp(self):
		super().setUp()
		self.addCleanup(self.allow, True)

	def allow(self, value: bool) -> None:
		frappe.db.set_single_value(SETTINGS, membership_service.CANCELLATION_SETTING, int(value))

	def submitted(self):
		profile = fixtures.make_profile("Cancel", "Case")
		membership = fixtures.make_membership(profile, fixtures.TYPE_FREE, self.society_a["ward"])
		membership_service.submit(membership)
		return self.reload(membership.name)

	def test_on_by_default_a_membership_can_be_cancelled(self):
		membership = self.submitted()

		self.assertTrue(membership_service.status(membership)["can_cancel"])
		membership_service.cancel(membership, "Moved away")
		self.assertEqual(self.membership_status(membership.name), membership_service.STATUS_CANCELLED)

	def test_when_the_society_never_cancels_there_is_no_action_and_it_is_refused(self):
		self.allow(False)
		membership = self.submitted()

		before = membership.membership_status

		self.assertFalse(membership_service.status(membership)["can_cancel"])
		with self.assertRaises(frappe.ValidationError):
			membership_service.cancel(membership, "Moved away")
		self.assertEqual(self.membership_status(membership.name), before)
