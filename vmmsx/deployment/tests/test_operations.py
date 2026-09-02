# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What the operations console reads: the status bands, the map, the aggregates.

Three properties, and the first one is a bug this suite exists to keep fixed.

**Every status the doctype has is a status the API can be asked about.** The
whitelisted layer used to know four of the six: `Suspended` and `Closed Out`
were absent from `_DEPLOYMENT_STATUSES`, so asking for either answered with an
empty list — which on a screen reads as "there are none of those", and is the
worst way for a filter to fail. The band a register shows is now a *set* the
database is asked for rather than whichever members of it happened to land on
one page.

**The map plots deployments, not areas, and it never hides a gap.** A deployment
carries its own site and meeting coordinates; one nobody has located yet is
still in the answer and counted in `unplotted`, because a tree of operational
sites is filled in over months and a map that silently drew fewer pins would
under-report exactly the gap it exists to show.

**The aggregates are over the caller's whole scope**, computed through
`frappe.get_list` so core's permission query condition is the floor. A screen
that derived them from one capped page would report a different number as the
register grew.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.api import deployment as deployment_api
from vmmsx.deployment.services import deployment as deployment_service
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class OperationsTestCase(DeploymentTestCase):
	"""One coordinator who may read deployments across society A, and nowhere else."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.grant_doctype_access(fixtures.DEPLOYMENT_DOCTYPE, fixtures.DEPLOYMENT_SCOPE_ROLE)

		cls.terms = fixtures.make_terms().name
		# Terms of its own for the other society: a terms of reference names
		# where it may be *used*, and the fixture's default scope is society A.
		# A deployment anchored outside that scope is refused, which is the rule
		# working rather than a fixture problem.
		cls.other_terms = fixtures.make_terms(
			f"{fixtures.TEST_PREFIX}-ops-elsewhere", geo_scope=cls.society_b["region"]
		).name
		cls.here = cls.viewer("ops_here", fixtures.DEPLOYMENT_SCOPE_ROLE, cls.society_a["region"])
		cls.elsewhere = cls.viewer(
			"ops_elsewhere", fixtures.DEPLOYMENT_SCOPE_ROLE, cls.society_b["region"]
		)

	def at(self, status: str, node: str | None = None, **overrides):
		"""A deployment in one of the six states, in society A unless told otherwise."""
		return fixtures.make_deployment(
			self.terms, node or self.society_a["post"], status=status, **overrides
		)

	def elsewhere_at(self, status: str, **overrides):
		"""The same, in the other society and under that society's own terms."""
		return fixtures.make_deployment(
			self.other_terms, self.society_b["ward"], status=status, **overrides
		)

	def names_in(self, answer: dict) -> set[str]:
		return {row["name"] for row in answer["deployments"]}


class TestEveryStatusIsReachable(OperationsTestCase):
	def test_the_api_knows_all_six_of_the_doctype_s_statuses(self):
		# Read off the service that owns them rather than retyped, so a seventh
		# status could not be added without this failing.
		self.assertEqual(
			tuple(deployment_api._DEPLOYMENT_STATUSES), tuple(deployment_service.STATUSES)
		)
		self.assertIn(deployment_service.STATUS_SUSPENDED, deployment_api._DEPLOYMENT_STATUSES)
		self.assertIn(deployment_api._DEPLOYMENT_STATUSES[4], ("Closed Out",))

	def test_a_suspended_deployment_can_be_asked_for(self):
		suspended = self.at(deployment_service.STATUS_SUSPENDED)

		with fixtures.acting_as(self.here):
			answer = deployment_api.branch_deployments(status=deployment_service.STATUS_SUSPENDED)

		# It used to answer with nothing, which on a screen reads as "there are
		# no suspended deployments".
		self.assertIn(suspended.name, self.names_in(answer))

	def test_a_closed_out_deployment_can_be_asked_for(self):
		closed = self.at(deployment_service.STATUS_CLOSED_OUT)

		with fixtures.acting_as(self.here):
			answer = deployment_api.branch_deployments(status=deployment_service.STATUS_CLOSED_OUT)

		self.assertIn(closed.name, self.names_in(answer))

	def test_an_unknown_status_answers_with_nothing_rather_than_everything(self):
		self.at(deployment_service.STATUS_ACTIVE)

		with fixtures.acting_as(self.here):
			answer = deployment_api.branch_deployments(status="Mobilising")

		# A filter should fail towards nothing. "Mobilising" is a word a screen
		# uses for a column; it is not a status the doctype has.
		self.assertEqual(answer["deployments"], [])
		self.assertEqual(answer["total"], 0)


class TestTheOngoingBand(OperationsTestCase):
	def test_a_band_is_one_question_the_database_answers(self):
		planned = self.at(deployment_service.STATUS_PLANNED)
		active = self.at(deployment_service.STATUS_ACTIVE)
		suspended = self.at(deployment_service.STATUS_SUSPENDED)
		completed = self.at(deployment_service.STATUS_COMPLETED)
		closed = self.at(deployment_service.STATUS_CLOSED_OUT)
		cancelled = self.at(deployment_service.STATUS_CANCELLED)

		with fixtures.acting_as(self.here):
			answer = deployment_api.branch_deployments(
				statuses=list(deployment_api.ONGOING_STATUSES)
			)

		found = self.names_in(answer)

		for name in (planned.name, active.name, suspended.name, completed.name):
			self.assertIn(name, found)

		# The two that are genuinely over. Neither is dropped from the product —
		# both are in Past deployments — but neither is ongoing work.
		self.assertNotIn(closed.name, found)
		self.assertNotIn(cancelled.name, found)

	def test_the_total_is_the_band_not_the_page(self):
		for _ in range(3):
			self.at(deployment_service.STATUS_ACTIVE)

		with fixtures.acting_as(self.here):
			page = deployment_api.branch_deployments(
				statuses=list(deployment_api.ONGOING_STATUSES), limit=1
			)

		self.assertEqual(len(page["deployments"]), 1)
		self.assertGreaterEqual(page["total"], 3)
		self.assertNotEqual(page["count"], page["total"])

	def test_one_bad_value_empties_the_whole_filter_rather_than_being_dropped(self):
		self.at(deployment_service.STATUS_ACTIVE)

		with fixtures.acting_as(self.here):
			answer = deployment_api.branch_deployments(statuses=["Active", "Nonsense"])

		# Quietly dropping the unknown one would answer a different question from
		# the one that was asked.
		self.assertEqual(answer["deployments"], [])


class TestTheMap(OperationsTestCase):
	def test_a_located_deployment_carries_its_own_coordinates(self):
		located = self.at(
			deployment_service.STATUS_ACTIVE,
			site_name="Hola Sub-County Hospital",
			site_latitude=-1.4997,
			site_longitude=40.0301,
		)

		with fixtures.acting_as(self.here):
			answer = deployment_api.deployment_sites()

		row = next(row for row in answer["deployments"] if row["name"] == located.name)

		# The deployment's own point, not the geo tree's and not a constant.
		self.assertTrue(row["where"]["site"]["has_point"])
		self.assertEqual(row["where"]["site"]["name"], "Hola Sub-County Hospital")
		self.assertIsNotNone(row["where"]["site"]["map"])

	def test_an_unlocated_deployment_is_counted_rather_than_dropped(self):
		unlocated = self.at(deployment_service.STATUS_ACTIVE)

		with fixtures.acting_as(self.here):
			answer = deployment_api.deployment_sites()

		found = next(row for row in answer["deployments"] if row["name"] == unlocated.name)

		self.assertFalse(found["where"]["site"]["has_point"])
		self.assertGreaterEqual(answer["unplotted"], 1)
		self.assertEqual(answer["plotted"] + answer["unplotted"], answer["count"])

	def test_each_row_carries_the_mission_picture_a_panel_needs(self):
		self.at(deployment_service.STATUS_ACTIVE, volunteers_required=6)

		with fixtures.acting_as(self.here):
			row = deployment_api.deployment_sites()["deployments"][0]

		for key in (
			"status",
			"terms_of_reference",
			"geo_path",
			"coordinator",
			"planned_start",
			"planned_end",
			"briefing_on",
			"check_in_deadline",
			"expected_return",
			"participant_count",
			"assignment_counts",
			"places_left",
		):
			self.assertIn(key, row, f"the map panel reads {key}")

		self.assertIn("meeting_point", row["where"])
		self.assertIn("local_contact", row["where"])
		self.assertIn("travel_notes", row["where"])
		self.assertEqual(
			set(row["readiness"]), {"briefed", "safety", "checked_in", "leaders"}
		)
		# An explicit DTO built field by field, never the Document.
		self.assertNotIn("doctype", row)

	def test_the_map_is_scoped_like_everything_else(self):
		mine = self.at(deployment_service.STATUS_ACTIVE)
		theirs = self.elsewhere_at(deployment_service.STATUS_ACTIVE)

		with fixtures.acting_as(self.here):
			found = self.names_in(deployment_api.deployment_sites())

		self.assertIn(mine.name, found)
		self.assertNotIn(theirs.name, found)

	def test_an_unknown_status_empties_the_map_rather_than_filling_it(self):
		self.at(deployment_service.STATUS_ACTIVE)

		with fixtures.acting_as(self.here):
			answer = deployment_api.deployment_sites(status="Mobilising")

		self.assertEqual(answer["deployments"], [])
		self.assertEqual(answer["unplotted"], 0)


class TestTheAggregates(OperationsTestCase):
	def test_the_summary_counts_the_band_rather_than_a_page(self):
		with fixtures.acting_as(self.here):
			before = deployment_api.operations_summary()

		self.at(deployment_service.STATUS_ACTIVE)
		self.at(deployment_service.STATUS_SUSPENDED)
		self.at(deployment_service.STATUS_CLOSED_OUT)

		with fixtures.acting_as(self.here):
			after = deployment_api.operations_summary()

		# Two of the three are ongoing. The closed-out one is not.
		self.assertEqual(after["ongoing"] - before["ongoing"], 2)
		self.assertEqual(
			after["by_status"][deployment_service.STATUS_SUSPENDED]
			- before["by_status"][deployment_service.STATUS_SUSPENDED],
			1,
		)

	def test_close_out_work_is_completed_and_not_yet_closed_out(self):
		with fixtures.acting_as(self.here):
			before = deployment_api.operations_summary()

		self.at(deployment_service.STATUS_COMPLETED)
		self.at(deployment_service.STATUS_CLOSED_OUT)

		with fixtures.acting_as(self.here):
			after = deployment_api.operations_summary()

		# The work is over and the paperwork is not: that is one deployment, not
		# two and not none.
		self.assertEqual(after["closing_out"] - before["closing_out"], 1)

	def test_starting_soon_counts_planned_deployments_inside_the_window(self):
		with fixtures.acting_as(self.here):
			before = deployment_api.operations_summary()
			window = before["starting_soon_days"]

		self.at(
			deployment_service.STATUS_PLANNED,
			start_date=add_days(today(), 3),
			end_date=add_days(today(), 10),
		)
		self.at(
			deployment_service.STATUS_PLANNED,
			start_date=add_days(today(), window + 30),
			end_date=add_days(today(), window + 40),
		)

		with fixtures.acting_as(self.here):
			after = deployment_api.operations_summary()

		self.assertEqual(after["starting_soon"] - before["starting_soon"], 1)

	def test_the_summary_is_scoped_to_the_caller(self):
		with fixtures.acting_as(self.elsewhere):
			before = deployment_api.operations_summary()

		self.at(deployment_service.STATUS_ACTIVE)

		with fixtures.acting_as(self.elsewhere):
			after = deployment_api.operations_summary()

		# A deployment in the other society moved nothing here.
		self.assertEqual(after["ongoing"], before["ongoing"])


class TestOperationsDocuments(OperationsTestCase):
	def test_the_record_types_are_handed_over_rather_than_guessed(self):
		with fixtures.acting_as(self.here):
			answer = deployment_api.operations_documents()

		self.assertEqual(
			answer["record_types"],
			[fixtures.PROJECT_DOCTYPE, fixtures.TERMS_DOCTYPE, fixtures.DEPLOYMENT_DOCTYPE],
		)

	def test_an_unknown_record_type_returns_nothing_rather_than_everything(self):
		with fixtures.acting_as(self.here):
			answer = deployment_api.operations_documents(doctype="User")

		self.assertEqual(answer["files"], [])
		self.assertEqual(answer["targets"], [])

	def test_targets_are_only_records_the_caller_may_write(self):
		mine = self.at(deployment_service.STATUS_PLANNED)

		with fixtures.acting_as(self.here):
			targets = deployment_api.operations_documents()["targets"]

		named = {(target["doctype"], target["name"]) for target in targets}

		for doctype, name in named:
			self.assertTrue(
				frappe.has_permission(doctype, ptype="write", doc=name, user=self.here),
				f"{doctype} {name} was offered as an upload target without write permission",
			)

		self.assertTrue(mine.name)
