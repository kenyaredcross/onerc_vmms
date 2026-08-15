# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A member's own memberships — derived from the session, across every branch.

`my_memberships()` takes no arguments, and that is the property under test
rather than a convenience. An endpoint that accepted a member name would be a
general-purpose reader of anybody's memberships wearing a possessive name, and
the only thing standing between it and that would be a check somebody had to
remember to write. There is no such check here because there is nothing to
check: the caller cannot name somebody else, because the caller cannot name
anybody.

**Multi-branch is the ordinary case, not an edge case.** One person may hold
memberships at several branches at once — the schema permits it, the member's
derived status is computed from the set of them, and this view must return all
of them. A test that only ever built one membership per person would pass just
as happily against an implementation that returned the first row it found.

The chain each call walks is `User -> Red Profile.user -> VMMS Member.red_profile
-> VMMS Membership.member`, and every break in it is ordinary rather than an
error: somebody logged in who is not a member is a visitor, not a failure.
"""

import frappe

from vmmsx.member.services import approval
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class MyMembershipsTestCase(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=600)

		cls.member_user = cls.scoped_user("mine_member")
		cls.other_user = cls.scoped_user("mine_other")

	def setUp(self):
		super().setUp()
		self.addCleanup(fixtures.reset_branding)

	def mine(self) -> list[dict]:
		from vmmsx.api import member as member_api

		return member_api.my_memberships()

	@classmethod
	def membership_at(cls, profile: str, geo_node: str, activate: bool = True):
		"""One membership at one branch.

		A classmethod called from `setUpClass`, because this suite's transaction
		rolls back once per class and `Red Profile.user` is unique in core: a
		profile built per method for the same login collides on the second one.
		"""
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, geo_node)
		membership_service.submit(membership)
		row = frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

		if activate:
			row.on_payment_confirmed(amount=600, transaction_id=row.payment_transaction)

		return frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)


class TestItReturnsEveryBranch(MyMembershipsTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Mine", "Holder", user=cls.member_user)

		# Two active memberships at two branches of one society, and a third
		# still awaiting payment somewhere else entirely. Built here rather than
		# per method so that every method sees the same three — a membership
		# created inside one test would otherwise be present for the tests that
		# happen to run after it, and absent for the rest.
		cls.nairobi = cls.membership_at(cls.profile, cls.society_a["ward"])
		cls.mombasa = cls.membership_at(cls.profile, cls.society_a["other_ward"])
		cls.pending = cls.membership_at(cls.profile, cls.society_b["ward"], activate=False)

	def test_the_fixture_really_made_two_at_two_places(self):
		"""Without this the multi-branch assertion could pass on one row."""
		self.assertNotEqual(self.nairobi.name, self.mombasa.name)
		self.assertNotEqual(self.nairobi.geo_node, self.mombasa.geo_node)
		self.assertEqual(self.nairobi.member, self.mombasa.member)

	def test_every_branch_comes_back(self):
		with fixtures.acting_as(self.member_user):
			rows = self.mine()

		self.assertEqual(
			{row["name"] for row in rows},
			{self.nairobi.name, self.mombasa.name, self.pending.name},
			"a membership at another branch was lost",
		)

	def test_two_concurrently_active_ones_are_both_returned(self):
		"""The requirement stated on its own: concurrent, not sequential."""
		with fixtures.acting_as(self.member_user):
			active = {
				row["name"]
				for row in self.mine()
				if row["membership_status"] == membership_service.STATUS_ACTIVE
			}

		self.assertEqual(active, {self.nairobi.name, self.mombasa.name})

	def test_each_carries_its_own_branch(self):
		with fixtures.acting_as(self.member_user):
			nodes = {row["geo_node"] for row in self.mine()}

		self.assertEqual(nodes, {self.nairobi.geo_node, self.mombasa.geo_node, self.pending.geo_node})

	def test_each_row_is_the_membership_status_dto(self):
		"""The view reuses the DTO rather than assembling a second opinion."""
		with fixtures.acting_as(self.member_user):
			row = next(row for row in self.mine() if row["name"] == self.nairobi.name)

		for key in (
			"membership_status",
			"geo_node",
			"geo_path",
			"valid_from",
			"valid_to",
			"membership_type_name",
			"fee",
			"payment_settled",
			"approval_settled",
			"member_name",
		):
			self.assertIn(key, row, f"the view dropped {key}")

		self.assertEqual(row["member_name"], "Mine Holder")

	def test_an_active_one_offers_a_certificate(self):
		with fixtures.acting_as(self.member_user):
			rows = {row["name"]: row for row in self.mine()}

		self.assertTrue(rows[self.nairobi.name]["certificate_available"])
		self.assertTrue(rows[self.mombasa.name]["certificate_available"])

	def test_a_membership_that_is_not_active_offers_no_certificate(self):
		with fixtures.acting_as(self.member_user):
			row = next(row for row in self.mine() if row["name"] == self.pending.name)

		self.assertNotEqual(row["membership_status"], membership_service.STATUS_ACTIVE)
		self.assertFalse(row["certificate_available"])


class TestItIsDerivedFromTheSession(MyMembershipsTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Session", "Holder", user=cls.member_user)
		cls.mine_row = cls.membership_at(cls.profile, cls.society_a["ward"])

		other_profile = fixtures.make_profile("Session", "Other", user=cls.other_user)
		cls.theirs = cls.membership_at(other_profile, cls.society_a["ward"])

	def test_a_different_user_sees_only_their_own(self):
		with fixtures.acting_as(self.other_user):
			names = {row["name"] for row in self.mine()}

		self.assertEqual(names, {self.theirs.name})
		self.assertNotIn(self.mine_row.name, names)

	def test_the_endpoint_takes_no_arguments_at_all(self):
		"""The structural guarantee: there is nothing to pass, so nothing to abuse."""
		import inspect

		from vmmsx.api import member as member_api

		self.assertEqual(list(inspect.signature(member_api.my_memberships).parameters), [])

	def test_switching_session_switches_the_answer(self):
		"""Proves it re-derives every call rather than resolving once."""
		with fixtures.acting_as(self.member_user):
			first = {row["name"] for row in self.mine()}

		with fixtures.acting_as(self.other_user):
			second = {row["name"] for row in self.mine()}

		self.assertEqual(first, {self.mine_row.name})
		self.assertEqual(second, {self.theirs.name})


class TestABrokenChainIsOrdinary(MyMembershipsTestCase):
	def test_a_user_with_no_red_profile_gets_an_empty_list(self):
		stranger = self.scoped_user("mine_no_profile")

		with fixtures.acting_as(stranger):
			self.assertEqual(self.mine(), [])

	def test_a_profile_with_no_member_record_gets_an_empty_list(self):
		user = self.scoped_user("mine_no_member")
		fixtures.make_profile("Profiled", "NotAMember", user=user)

		with fixtures.acting_as(user):
			self.assertEqual(self.mine(), [])

	def test_a_member_with_no_memberships_gets_an_empty_list(self):
		from vmmsx.member.services import member as member_service

		user = self.scoped_user("mine_no_memberships")
		profile = fixtures.make_profile("Membered", "NoMemberships", user=user)
		member_service.ensure(profile)

		with fixtures.acting_as(user):
			self.assertEqual(self.mine(), [])

	def test_none_of_these_raise(self):
		"""Stated on its own: somebody logged in who is not a member is a visitor."""
		stranger = self.scoped_user("mine_quiet")

		with fixtures.acting_as(stranger):
			try:
				self.mine()
			except Exception as exception:
				# Deliberately broad: the assertion is that *nothing* is raised,
				# so narrowing this would let some other failure through.
				self.fail(f"a non-member raised instead of getting an empty list: {exception}")
