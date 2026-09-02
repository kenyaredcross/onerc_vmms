# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The active volunteer register's own figures, and the People overview's.

**Every figure is an aggregate over the caller's whole scope, not a page of
one.** The register screen shows four numbers above a paged table; if they came
from that table's `total` they would change when somebody typed in the search
box, and would be believed. So they have their own endpoint, and it counts
through `frappe.get_list` — core's permission query condition included, which is
what makes the answer a fact about who is asking rather than about the database.

**And a figure the server cannot compute affordably is `None`, never a guess.**
The People overview's unique-person count is the union of two registers' Red
Profiles, which is a column read rather than a count: fine at branch size, wrong
at national size. Past the ceiling the endpoint answers `None` and the screen
drops the block — a missing figure is a smaller failure than a wrong one.
"""

import frappe
from frappe.utils import add_days, get_first_day, getdate, today

from vmmsx.api import people as people_api
from vmmsx.api import volunteer as volunteer_api
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

VOLUNTEER_STATUS_ACTIVE = "Active"
VOLUNTEER_STATUS_PROSPECTIVE = "Prospective"


class RegisterSummaryTestCase(VolunteerTestCase):
	"""Two coordinators, each seeing one society and not the other."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.grant_doctype_access(fixtures.VOLUNTEER_DOCTYPE, fixtures.SCOPE_ROLE)

		cls.here = fixtures.make_user("vol_summary_here")
		cls.elsewhere = fixtures.make_user("vol_summary_elsewhere")
		fixtures.grant_volunteer_scope(cls.here, cls.society_a["region"])
		fixtures.grant_volunteer_scope(cls.elsewhere, cls.society_b["region"])

	def volunteer_at(self, handle: str, node: str, status: str = VOLUNTEER_STATUS_ACTIVE, **fields):
		"""One volunteer, put straight into the standing this test is about.

		`status` is derived and read-only on the doctype — the lifecycle endpoints
		are the only things that move it — so a test arranging a register writes
		it directly rather than driving four applications through the engine to
		reach the same arrangement.
		"""
		profile = fixtures.make_profile(handle, "Volunteer")
		volunteer = fixtures.make_volunteer(profile, node)

		frappe.db.set_value(
			fixtures.VOLUNTEER_DOCTYPE,
			volunteer.name,
			{"status": status, **fields},
			update_modified=False,
		)

		return volunteer

	def figures_for(self, user: str) -> dict:
		with fixtures.acting_as(user):
			return volunteer_api.register_summary()


class TestTheFigures(RegisterSummaryTestCase):
	def test_only_active_volunteers_are_counted(self):
		# Deltas, not absolutes: Frappe rolls the test transaction back once per
		# class, so a volunteer another method made is still there for this one.
		before = self.figures_for(self.here)

		self.volunteer_at("Active", self.society_a["ward"])
		self.volunteer_at("Prospective", self.society_a["ward"], VOLUNTEER_STATUS_PROSPECTIVE)

		after = self.figures_for(self.here)

		# The register is of active volunteers. Prospective, Suspended and Exited
		# are each a state with its own screen and its own workflow.
		self.assertEqual(after["active"] - before["active"], 1)

	def test_joined_this_month_is_a_window_on_the_same_register(self):
		before = self.figures_for(self.here)
		month_start = get_first_day(getdate(today()))

		self.volunteer_at("Recent", self.society_a["ward"], joined_on=month_start)
		self.volunteer_at("Older", self.society_a["ward"], joined_on=add_days(month_start, -40))

		after = self.figures_for(self.here)

		self.assertEqual(after["active"] - before["active"], 2)
		self.assertEqual(after["joined_month"] - before["joined_month"], 1)

	def test_branches_represented_counts_distinct_serving_branches(self):
		before = self.figures_for(self.here)

		self.volunteer_at("BranchOne", self.society_a["ward"])
		self.volunteer_at("BranchOneAgain", self.society_a["ward"])
		self.volunteer_at("BranchTwo", self.society_a["other_ward"])

		after = self.figures_for(self.here)

		# Three volunteers, two branches. A headcount is not a branch count.
		self.assertEqual(after["active"] - before["active"], 3)
		self.assertEqual(after["branches"] - before["branches"], 2)

	def test_the_summary_is_not_the_size_of_a_page(self):
		for index in range(3):
			self.volunteer_at(f"Paged{index}", self.society_a["ward"])

		with fixtures.acting_as(self.here):
			page = volunteer_api.find_volunteers(status=VOLUNTEER_STATUS_ACTIVE, limit=1)

		figures = self.figures_for(self.here)

		self.assertEqual(len(page["volunteers"]), 1)
		self.assertGreaterEqual(figures["active"], 3)
		# The register's own size, and the page's `total` for the same question,
		# agree — which is the point: one is not derived from the other.
		self.assertEqual(figures["active"], page["total"])

	def test_the_active_register_row_carries_what_the_screen_shows(self):
		self.volunteer_at("Rowed", self.society_a["ward"], joined_on=today())

		with fixtures.acting_as(self.here):
			row = volunteer_api.find_volunteers(status=VOLUNTEER_STATUS_ACTIVE, limit=1)["volunteers"][0]

		for key in ("volunteer", "full_name", "photo", "status", "joined_on", "geo_path"):
			self.assertIn(key, row, f"the register column {key} has nothing behind it")

		self.assertEqual(row["status"], VOLUNTEER_STATUS_ACTIVE)


class TestScope(RegisterSummaryTestCase):
	def test_the_summary_counts_only_what_the_caller_may_read(self):
		before_here = self.figures_for(self.here)
		before_there = self.figures_for(self.elsewhere)

		self.volunteer_at("ScopedHereOne", self.society_a["ward"])
		self.volunteer_at("ScopedHereTwo", self.society_a["ward"])
		self.volunteer_at("ScopedElsewhere", self.society_b["ward"])

		after_here = self.figures_for(self.here)
		after_there = self.figures_for(self.elsewhere)

		# Three volunteers were made. Neither coordinator is told so.
		self.assertEqual(after_here["active"] - before_here["active"], 2)
		self.assertEqual(after_there["active"] - before_there["active"], 1)

	def test_a_society_with_no_scope_role_configured_is_told_nothing(self):
		self.volunteer_at("Closed", self.society_a["ward"])
		self.addCleanup(fixtures.set_scope_role, fixtures.SCOPE_ROLE)
		fixtures.set_scope_role(None)

		figures = self.figures_for(self.here)

		# Fails closed. The safe direction for an unconfigured setting is nothing
		# rather than everything.
		self.assertEqual(figures["active"], 0)


class TestThePeopleOverview(RegisterSummaryTestCase):
	def test_the_summary_answers_in_four_blocks(self):
		with fixtures.acting_as(self.here):
			answer = people_api.summary()

		self.assertEqual(set(answer), {"queue", "intake", "registers", "people"})
		# Every block says whether it is readable at all, so a screen can tell
		# "nothing here" apart from "not yours to see".
		for row in answer["registers"] + answer["intake"]:
			self.assertIn("readable", row)
		self.assertEqual(
			{row["kind"] for row in answer["registers"]}, {"volunteers", "members"}
		)
		self.assertEqual({row["kind"] for row in answer["intake"]}, {"volunteers", "members"})

	def test_the_register_block_agrees_with_the_register_s_own_endpoint(self):
		self.volunteer_at("Agreed", self.society_a["ward"])

		with fixtures.acting_as(self.here):
			overview = people_api.summary()

		register = self.figures_for(self.here)
		volunteers = next(
			row for row in overview["registers"] if row["kind"] == "volunteers"
		)

		# Two screens, one number. Both go through the same scoped listing.
		self.assertEqual(volunteers["active"], register["active"])

	def test_the_register_block_is_scoped(self):
		with fixtures.acting_as(self.elsewhere):
			before = next(
				row for row in people_api.summary()["registers"] if row["kind"] == "volunteers"
			)["active"]

		self.volunteer_at("NotTheirs", self.society_a["ward"])

		with fixtures.acting_as(self.elsewhere):
			after = next(
				row for row in people_api.summary()["registers"] if row["kind"] == "volunteers"
			)["active"]

		self.assertEqual(after, before)

	def test_an_ungoverned_intake_says_so_rather_than_reporting_zero(self):
		with fixtures.acting_as(self.here):
			intake = people_api.summary()["intake"]

		for door in intake:
			# Governed implies readable: the engine cannot route what the caller
			# may not open.
			self.assertFalse(door["governed"] and not door["readable"])

			if door["governed"]:
				self.assertIsInstance(door["in_review"], int)
				self.assertIsInstance(door["changes_requested"], int)
			else:
				# "Nothing to do" and "nobody has configured this" are different
				# answers, and a zero would say the first when the second is true.
				self.assertIsNone(door["in_review"])
				self.assertIsNone(door["changes_requested"])
				self.assertIsNone(door["breached"])

	def test_the_people_block_is_either_computed_or_absent(self):
		self.volunteer_at("Counted", self.society_a["ward"])

		with fixtures.acting_as(self.here):
			people = people_api.summary()["people"]

		self.assertEqual(
			set(people), {"unique", "both", "volunteers", "members", "capped"}
		)

		if people["capped"]:
			# Past the ceiling every figure is None, and the screen omits the
			# block rather than showing one derived from a truncated read.
			self.assertIsNone(people["unique"])
			self.assertIsNone(people["both"])
		else:
			self.assertGreaterEqual(people["unique"], people["volunteers"])
			self.assertGreaterEqual(people["unique"], people["members"])
			# Somebody in both registers is one person, counted once.
			self.assertEqual(
				people["unique"], people["volunteers"] + people["members"] - people["both"]
			)
