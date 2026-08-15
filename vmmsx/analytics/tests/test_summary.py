# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What the analytics panel counts, and what it refuses to count.

The claim in `analytics/services/summary.py` is that a coordinator can never be
counted a record they could not open, and that there is no argument by which
they could ask to be. Two things make that testable:

* **`frappe.get_list`, never `frappe.get_all`.** Only the first applies core's
  permission query condition. A count assembled with the second would answer for
  the whole site, and it would do so silently, which is why this suite spends
  most of its time on a user holding nothing.
* **`geo_node` narrows and cannot widen.** A branch coordinator naming the
  region still gets their branch, because the argument is intersected with what
  they already hold rather than replacing it.
"""

from vmmsx.analytics.services import summary
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase


class TestBranchSummary(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.region = cls.society_a["region"]
		cls.branch = cls.society_a["branch"]
		cls.other_region = cls.society_b["region"]

		# One volunteer in each society, so a scope that leaks would show up as a
		# count of two rather than as a wrong number nobody could distinguish.
		cls.here = fixtures.make_volunteer(fixtures.make_profile(), cls.branch).name
		cls.elsewhere = fixtures.make_volunteer(fixtures.make_profile(), cls.other_region).name

		# The scope role needs read permission on the doctype as well as a Geo
		# Assignment. In production `staff/services/permissions.py` grants that
		# from `after_migrate`; here it is arranged explicitly, so a test that
		# fails is failing on scoping rather than on an ungranted doctype.
		fixtures.grant_doctype_access(fixtures.VOLUNTEER_DOCTYPE, fixtures.VOLUNTEER_SCOPE_ROLE)

		cls.local = cls.viewer("analytics-local", fixtures.VOLUNTEER_SCOPE_ROLE, cls.branch)
		cls.national = cls.viewer("analytics-national", fixtures.VOLUNTEER_SCOPE_ROLE, cls.region)
		cls.nobody = fixtures.make_user("analytics-nobody")

	# --- failing closed ---------------------------------------------------

	def test_somebody_holding_nothing_counts_nothing(self):
		"""The direction the whole module has to fail in.

		This user holds no role on any of the doctypes, so Frappe refuses each
		query outright rather than returning nothing. `_rows` catches that and
		answers zero, which is what lets a coordinator holding one scope role and
		not another see real numbers beside honest zeroes instead of a screen
		that will not draw.
		"""
		with fixtures.acting_as(self.nobody):
			answer = summary.branch_summary()

		self.assertEqual(answer["volunteers"]["total"], 0)
		self.assertEqual(answer["members"]["total"], 0)
		self.assertEqual(answer["hours"]["total"], 0.0)

	def test_a_node_that_does_not_exist_counts_nothing(self):
		with fixtures.acting_as(self.national):
			answer = summary.branch_summary(geo_node="Geo Node That Was Never Created")

		self.assertEqual(answer["volunteers"]["total"], 0)

	# --- scoping ----------------------------------------------------------

	def test_a_scoped_coordinator_sees_their_own_society_only(self):
		with fixtures.acting_as(self.national):
			answer = summary.branch_summary()

		self.assertEqual(answer["volunteers"]["total"], 1)

	def test_naming_a_wider_node_does_not_widen_the_answer(self):
		"""The argument is intersected with what the caller holds. A branch
		coordinator naming the region above them still gets their branch."""
		with fixtures.acting_as(self.local):
			named = summary.branch_summary(geo_node=self.region)
			unnamed = summary.branch_summary()

		self.assertEqual(named["volunteers"]["total"], unnamed["volunteers"]["total"])

	def test_naming_another_society_counts_nothing(self):
		with fixtures.acting_as(self.national):
			answer = summary.branch_summary(geo_node=self.other_region)

		self.assertEqual(answer["volunteers"]["total"], 0)

	# --- the shape of the answer -----------------------------------------

	def test_the_status_breakdown_names_every_state_including_the_empty_ones(self):
		"""A breakdown that dropped its zeroes would change shape as records moved
		through it, and a chart whose bars appear and disappear cannot be read."""
		with fixtures.acting_as(self.national):
			answer = summary.branch_summary()

		self.assertIn("Active", answer["volunteers"]["by_status"])
		self.assertIn("Exited", answer["volunteers"]["by_status"])
		self.assertEqual(sum(answer["volunteers"]["by_status"].values()), 1)

	def test_no_status_string_is_written_in_the_service(self):
		"""The vocabularies come from `frappe.get_meta`, so a state added to a
		doctype turns up here without anybody editing the service."""
		source = (summary.__file__ or "").replace(".pyc", ".py")

		with open(source, encoding="utf-8") as handle:
			text = handle.read()

		for status in ("Prospective", "Suspended", "Awaiting Payment", "Planned"):
			self.assertNotIn(status, text)

	def test_the_trend_covers_the_months_asked_for(self):
		with fixtures.acting_as(self.national):
			answer = summary.branch_summary(months=6)

		self.assertEqual(len(answer["trend"]), 6)
		self.assertEqual(sorted(answer["trend"], key=lambda row: row["month"]), answer["trend"])

	def test_hours_are_summed_for_visible_volunteers_only(self):
		fixtures.make_time_log(self.here, self.branch, hours=4)
		fixtures.make_time_log(self.elsewhere, self.other_region, hours=9)

		with fixtures.acting_as(self.national):
			answer = summary.branch_summary()

		self.assertEqual(answer["hours"]["total"], 4.0)
		self.assertEqual(answer["hours"]["logged_by"], 1)

	def test_coverage_breaks_down_one_rung_and_no_further(self):
		with fixtures.acting_as(self.national):
			answer = summary.branch_summary(geo_node=self.region)

		self.assertTrue(all("label" in row for row in answer["coverage"]))
		self.assertTrue(all(row["geo_node"] != self.region for row in answer["coverage"]))
