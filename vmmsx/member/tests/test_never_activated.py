# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A member who never finished joining has not lapsed.

Memberships made in this app get a start date only when `activate()` runs, so
"has a start date" used to be the whole test of "was once a member". Memberships
carried over from the old VMMS break that: the old system filled in a start date
when the record was created, so drafts and unpaid applications arrive with one.
Read the old way, every such person was Lapsed, core was told their affiliation
Ended, and they were given a joining date they never had.

The memberships here are shaped the way the importer leaves them: inserted, then
given dates and a status directly, with no activation behind them.
"""

import frappe

from vmmsx.member.services import approval
from vmmsx.member.services import member as member_service
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

START = "2025-03-01"
END = "2025-12-31"


class TestNeverActivatedIsNotLapsed(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=200)

	def carried_over(self, handle: str, status: str) -> tuple[str, str]:
		"""A membership as the importer writes it: dated, in `status`, never activated."""
		profile = fixtures.make_profile(handle, "Legacy")
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])
		frappe.db.set_value(
			"VMMS Membership",
			membership.name,
			{"membership_status": status, "valid_from": START, "valid_to": END},
		)

		return membership.member, membership.name

	def test_a_dated_membership_still_in_a_joining_state_leaves_the_member_prospective(self):
		for index, status in enumerate(membership_service.ACTIVATABLE):
			with self.subTest(status=status):
				member, _ = self.carried_over(f"Joining{index}", status)
				member_service.refresh(member)

				self.assertEqual(self.member_status(member), member_service.STATUS_PROSPECTIVE)
				self.assertIsNone(frappe.db.get_value("VMMS Member", member, "joined_on"))

	def test_an_expired_membership_still_makes_the_member_lapsed(self):
		member, _ = self.carried_over("Expired", membership_service.STATUS_EXPIRED)
		member_service.refresh(member)

		self.assertEqual(self.member_status(member), member_service.STATUS_LAPSED)

	def test_the_joining_date_ignores_memberships_that_never_activated(self):
		"""A dated draft must not become the member's joining date."""
		member, name = self.carried_over("Earliest", membership_service.STATUS_DRAFT)
		self.assertIsNone(member_service._first_activation(member))

		frappe.db.set_value("VMMS Membership", name, "membership_status", membership_service.STATUS_EXPIRED)
		self.assertEqual(str(member_service._first_activation(member)), START)

	def test_one_cancelled_after_it_ran_still_counts_as_having_been_a_member(self):
		"""Cancelled is not a joining state: a dated, cancelled membership had started."""
		member, _ = self.carried_over("Cancelled", membership_service.STATUS_CANCELLED)
		member_service.refresh(member)

		self.assertEqual(self.member_status(member), member_service.STATUS_LAPSED)
