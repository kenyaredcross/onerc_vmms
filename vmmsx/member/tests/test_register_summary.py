# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The member register's own figures, and the scope they are computed inside.

Two things are proved here, and the second is the one that matters most.

**The figures are aggregates over the whole scoped register**, not counts of a
page. `find_members` returns one page and a `total` for the current filter; a
screen that put that `total` in a headline would report a different number the
moment somebody typed in the search box, and would be believed. So
`register_summary` counts across everything the caller may read, and splits life
from term on `VMMS Membership Type.is_lifetime` — never on a type's *name*,
because a society names its own types and "Annual" is one society's word.

**Scope is the floor, not a filter.** Every read in the summary and in
`approvals.my_cases` is `frappe.get_list`, so core's permission query condition
applies exactly as it does to the register page. `VMMS Membership` is both
governed by an approval workflow and registered as scopeable, which makes it the
one doctype where both properties can be asked in the same test — which is why
the approval-band scoping assertion lives here rather than beside the engine's
own suite, whose stand-in doctype core does not scope.
"""

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.api import approvals
from vmmsx.api import member as member_api
from vmmsx.approvals import states
from vmmsx.approvals.services import engine
from vmmsx.member.services import approval
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class RegisterSummaryTestCase(MemberTestCase):
	"""One society, two branches, and both kinds of membership type."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_FREE, approval.MODE_ROUTED, fee=0)
		fixtures.make_type(
			fixtures.TYPE_LIFETIME, approval.MODE_ROUTED, fee=0, is_lifetime=1
		)

		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.grant_membership_access(fixtures.SCOPE_ROLE)
		fixtures.grant_member_access(fixtures.APPROVER_ROLE)

		# `scoped_user` grants the scope role across both societies, so the
		# approver is stopped — or not — by the engine's person-gate rather than
		# by geo scoping at the door. Whether they may *decide* is a different
		# question from whether they may *see*, and this suite is about the
		# figures rather than about either gate.
		cls.approver = cls.scoped_user("summary_approver", [fixtures.APPROVER_ROLE])
		# Placed in both societies, so `activated` below can raise a live
		# membership on either side of the scope boundary these tests are about.
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["region"])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_b["region"])

		# One coordinator per society, each holding the scope role in their own
		# area and nowhere else.
		cls.here = fixtures.make_user("summary_here", [fixtures.SCOPE_ROLE])
		cls.elsewhere = fixtures.make_user("summary_elsewhere", [fixtures.SCOPE_ROLE])
		fixtures.grant_membership_scope(cls.here, cls.society_a["county"])
		fixtures.grant_membership_scope(cls.elsewhere, cls.society_b["district"])

		fixtures.make_workflow(fixtures.APPROVER_ROLE)

	def figures_for(self, user: str) -> dict:
		"""`register_summary` as somebody, without leaving the session moved."""
		with fixtures.acting_as(user):
			return member_api.register_summary()

	def activated(self, handle: str, type_key: str, node: str, **overrides):
		"""A live membership, activated by a real approver's decision."""
		from vmmsx.member.services import membership as membership_service

		profile = fixtures.make_profile(handle, "Member")
		membership = fixtures.make_membership(profile, type_key, node, **overrides)
		result = membership_service.submit(membership)

		with fixtures.acting_as(self.approver):
			engine.decide(
				frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, result["name"]),
				states.DECISION_APPROVED,
			)

		return frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, result["name"])


class TestTheFigures(RegisterSummaryTestCase):
	def test_life_and_term_are_split_on_the_flag_not_on_a_name(self):
		# Deltas, not absolutes: Frappe rolls the test transaction back once per
		# class, so a membership another method made is still there for this one.
		before = self.figures_for(self.here)

		self.activated("Term", fixtures.TYPE_FREE, self.society_a["ward"])
		self.activated("Life", fixtures.TYPE_LIFETIME, self.society_a["ward"])

		after = self.figures_for(self.here)

		self.assertEqual(after["active"] - before["active"], 2)
		self.assertEqual(after["lifetime"] - before["lifetime"], 1)
		self.assertEqual(after["term"] - before["term"], 1)
		# A society that calls its type something else is counted identically:
		# `is_lifetime` is the fact, the name is only a label.
		self.assertEqual(after["lifetime"] + after["term"], after["active"])

	def test_a_membership_whose_validity_has_run_out_is_not_counted_as_active(self):
		before = self.figures_for(self.here)

		self.activated("Live", fixtures.TYPE_FREE, self.society_a["ward"])
		lapsed = self.activated("Lapsed", fixtures.TYPE_FREE, self.society_a["ward"])

		# Stored as Active, `valid_to` in the past — the ordinary window before
		# the nightly sweep notices. The derived answer is what a register shows.
		frappe.db.set_value(
			fixtures.MEMBERSHIP_DOCTYPE, lapsed.name, "valid_to", add_days(getdate(today()), -1)
		)

		after = self.figures_for(self.here)

		self.assertEqual(after["active"] - before["active"], 1, "the lapsed one was counted")
		self.assertEqual(
			frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, lapsed.name, "membership_status"),
			"Active",
			"the stored status is untouched; only the derived answer differs",
		)

	def test_renewals_approaching_counts_term_memberships_inside_the_window(self):
		before = self.figures_for(self.here)
		window = before["renewal_window_days"]

		soon = self.activated("Soon", fixtures.TYPE_FREE, self.society_a["ward"])
		later = self.activated("Later", fixtures.TYPE_FREE, self.society_a["ward"])
		self.activated("LifeNoExpiry", fixtures.TYPE_LIFETIME, self.society_a["ward"])

		frappe.db.set_value(
			fixtures.MEMBERSHIP_DOCTYPE, soon.name, "valid_to", add_days(getdate(today()), 5)
		)
		frappe.db.set_value(
			fixtures.MEMBERSHIP_DOCTYPE,
			later.name,
			"valid_to",
			add_days(getdate(today()), window + 30),
		)

		after = self.figures_for(self.here)

		# One of the three: the one falling due inside the window. A lifetime
		# membership never falls due, so it is never approaching.
		self.assertEqual(after["renewing"] - before["renewing"], 1)

	def test_the_summary_is_not_the_size_of_a_page(self):
		for index in range(3):
			self.activated(f"Paged{index}", fixtures.TYPE_FREE, self.society_a["ward"])

		with fixtures.acting_as(self.here):
			page = member_api.find_members(current_only=True, limit=1)

		figures = self.figures_for(self.here)

		# The whole reason this endpoint exists: a page's length is a page's
		# length however it is labelled.
		self.assertEqual(len(page["rows"]), 1)
		self.assertGreaterEqual(figures["active"], 3)
		self.assertEqual(figures["active"], page["total"])


class TestTheSearch(RegisterSummaryTestCase):
	def test_search_narrows_the_register_by_a_persons_name(self):
		self.activated("Kilonzo", fixtures.TYPE_FREE, self.society_a["ward"])
		self.activated("Wanjiku", fixtures.TYPE_FREE, self.society_a["ward"])

		with fixtures.acting_as(self.here):
			found = member_api.find_members(current_only=True, search="kilonzo")
			everything = member_api.find_members(current_only=True)

		# Case-folded, and it narrows: one of the two, not both and not neither.
		self.assertEqual(found["total"], 1)
		self.assertGreater(everything["total"], found["total"])
		self.assertIn("Kilonzo", found["rows"][0]["full_name"])

	def test_search_narrows_and_can_never_widen(self):
		mine = self.activated("Mine", fixtures.TYPE_FREE, self.society_a["ward"])
		theirs = self.activated("Theirs", fixtures.TYPE_FREE, self.society_b["ward"])

		with fixtures.acting_as(self.here):
			# Naming somebody outside the caller's scope reaches nothing: the
			# scope condition still applies underneath the filter.
			found = member_api.find_members(current_only=True, search="Theirs")
			mine_found = member_api.find_members(current_only=True, search="Mine")

		self.assertEqual(found["total"], 0)
		self.assertEqual(mine_found["total"], 1)
		self.assertTrue(mine.name and theirs.name)


class TestScope(RegisterSummaryTestCase):
	def test_the_summary_counts_only_what_the_caller_may_read(self):
		before_here = self.figures_for(self.here)
		before_there = self.figures_for(self.elsewhere)

		self.activated("HereOne", fixtures.TYPE_FREE, self.society_a["ward"])
		self.activated("HereTwo", fixtures.TYPE_FREE, self.society_a["ward"])
		self.activated("Elsewhere", fixtures.TYPE_FREE, self.society_b["ward"])

		after_here = self.figures_for(self.here)
		after_there = self.figures_for(self.elsewhere)

		# Three memberships were made. Neither coordinator is told so: each one's
		# figure moved by what happened inside their own area.
		self.assertEqual(after_here["active"] - before_here["active"], 2)
		self.assertEqual(after_there["active"] - before_there["active"], 1)

	def test_an_approval_band_is_scoped_by_the_same_floor(self):
		mine = self.activated("BandHere", fixtures.TYPE_FREE, self.society_a["ward"])
		theirs = self.activated("BandElsewhere", fixtures.TYPE_FREE, self.society_b["ward"])

		with fixtures.acting_as(self.here):
			closed = {
				case["name"]
				for case in approvals.my_cases(
					fixtures.MEMBERSHIP_DOCTYPE, approvals.CASE_CLOSED
				)["cases"]
			}

		# Both were approved. `frappe.get_list` is the line the scope rests on;
		# `frappe.get_all` would have handed the other society's over.
		self.assertEqual(
			frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, theirs.name, "approval_state"),
			states.APPROVED,
		)
		self.assertIn(mine.name, closed)
		self.assertNotIn(theirs.name, closed)

	def test_a_society_with_no_scope_role_configured_is_told_nothing(self):
		self.activated("Closed", fixtures.TYPE_FREE, self.society_a["ward"])
		self.addCleanup(fixtures.set_scope_role, fixtures.SCOPE_ROLE)
		fixtures.set_scope_role(None)

		with fixtures.acting_as(self.here):
			figures = member_api.register_summary()

		# Fails closed. Memberships carry personal data, and the safe direction
		# for an unconfigured setting is nothing rather than everything.
		self.assertEqual(figures["active"], 0)
