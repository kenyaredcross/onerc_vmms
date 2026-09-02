# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A deployment's period, its six statuses, and closing it out.

Three things this suite is about, and each is a rule somebody could reasonably
have written differently:

1. **One period, two shapes.** `planned_start` and `planned_end` are what
   somebody writes; `start_date` and `end_date` are derived from them. Two
   writable fields for one fact would drift, and every register in this app
   windows on days while every volunteer needs to know what time to be there.
   The derivation runs both ways, so a record written before the datetimes
   existed still opens.

2. **Suspended is a pause and Closed Out is an ending with paperwork.** The
   grammar is what refuses the moves that make no sense — back to Planned once
   people have been there, or closing out work that has not finished.

3. **Nothing blocks a close-out.** Not an unmarked roster, not an open task, not
   somebody who never filed their hours. A close-out that can be refused is one
   that does not happen.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.deployment.services import deployment as deployment_service
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class ScheduleTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.terms = fixtures.make_terms()

	def deployment(self, **overrides):
		return fixtures.make_deployment(self.terms.name, self.society_a["branch"], **overrides)


class TestThePeriodHasOneSourceOfTruth(ScheduleTestCase):
	def test_dates_alone_fill_in_the_datetimes(self):
		"""Every record written before the datetimes existed, and every caller
		that still speaks in days."""
		deployment = self.deployment(start_date=today(), end_date=add_days(today(), 3))

		self.assertTrue(deployment.planned_start)
		self.assertTrue(deployment.planned_end)

	def test_a_period_given_in_days_means_the_whole_of_both_days(self):
		deployment = self.deployment(start_date=today(), end_date=today())

		self.assertIn("00:00:00", str(deployment.planned_start))
		self.assertIn("23:59:59", str(deployment.planned_end))

	def test_datetimes_decide_the_dates_rather_than_the_other_way_round(self):
		deployment = self.deployment()
		deployment.planned_start = f"{add_days(today(), 5)} 07:30:00"
		deployment.planned_end = f"{add_days(today(), 9)} 18:00:00"
		deployment.save()

		self.assertEqual(str(deployment.start_date), add_days(today(), 5))
		self.assertEqual(str(deployment.end_date), add_days(today(), 9))

	def test_the_two_cannot_disagree(self):
		"""A screen that wrote a start on Tuesday and a start date on Wednesday
		would be overruled rather than believed."""
		deployment = self.deployment()
		deployment.planned_start = f"{add_days(today(), 5)} 07:30:00"
		deployment.start_date = add_days(today(), 99)
		deployment.save()

		self.assertEqual(str(deployment.start_date), add_days(today(), 5))

	def test_a_period_that_runs_backwards_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.deployment(start_date=today(), end_date=add_days(today(), -3))


class TestTheScheduleIsCoherent(ScheduleTestCase):
	def test_a_briefing_after_the_work_ends_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.deployment(
				start_date=today(),
				end_date=add_days(today(), 2),
				briefing_on=f"{add_days(today(), 30)} 08:00:00",
			)

	def test_a_return_before_the_start_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.deployment(
				start_date=today(),
				end_date=add_days(today(), 2),
				expected_return=f"{add_days(today(), -5)} 08:00:00",
			)

	def test_an_actual_period_that_runs_backwards_is_refused(self):
		deployment = self.deployment()
		deployment.actual_start = f"{today()} 08:00:00"
		deployment.actual_end = f"{add_days(today(), -1)} 08:00:00"

		with self.assertRaises(frappe.ValidationError):
			deployment.save()

	def test_a_schedule_half_filled_in_is_left_alone(self):
		"""A society plans as much as it knows about, and the rest arrives later."""
		deployment = self.deployment(briefing_on=f"{today()} 07:00:00")

		self.assertTrue(deployment.name)
		self.assertIsNone(deployment.check_in_deadline)


class TestTheSixStatuses(ScheduleTestCase):
	def test_a_running_deployment_can_be_paused(self):
		deployment = self.deployment(status=deployment_service.STATUS_ACTIVE)
		deployment_service.set_status(deployment, deployment_service.STATUS_SUSPENDED)

		self.assertEqual(deployment.status, deployment_service.STATUS_SUSPENDED)

	def test_a_paused_deployment_is_still_open(self):
		"""Suspended is work that has not finished, and a register that filtered
		it out with the completed ones would lose it."""
		deployment = self.deployment(status=deployment_service.STATUS_ACTIVE)
		deployment_service.set_status(deployment, deployment_service.STATUS_SUSPENDED)

		self.assertTrue(deployment_service.is_open(deployment))

	def test_a_paused_deployment_resumes(self):
		deployment = self.deployment(status=deployment_service.STATUS_ACTIVE)
		deployment_service.set_status(deployment, deployment_service.STATUS_SUSPENDED)
		deployment_service.set_status(deployment, deployment_service.STATUS_ACTIVE)

		self.assertEqual(deployment.status, deployment_service.STATUS_ACTIVE)

	def test_a_paused_deployment_does_not_go_back_to_planned(self):
		"""People were there."""
		deployment = self.deployment(status=deployment_service.STATUS_ACTIVE)
		deployment_service.set_status(deployment, deployment_service.STATUS_SUSPENDED)

		with self.assertRaises(frappe.ValidationError):
			deployment_service.set_status(deployment, deployment_service.STATUS_PLANNED)

	def test_work_that_has_not_finished_cannot_be_closed_out(self):
		deployment = self.deployment(status=deployment_service.STATUS_ACTIVE)

		with self.assertRaises(frappe.ValidationError):
			deployment_service.close_out(deployment)

	def test_a_closed_out_deployment_moves_no_further(self):
		deployment = self.deployment(status=deployment_service.STATUS_COMPLETED)
		deployment_service.close_out(deployment)

		with self.assertRaises(frappe.ValidationError):
			deployment_service.set_status(deployment, deployment_service.STATUS_ACTIVE)


class TestClosingOutWaitsForNothing(ScheduleTestCase):
	def test_it_records_who_did_it_and_when(self):
		deployment = self.deployment(status=deployment_service.STATUS_COMPLETED)
		deployment_service.close_out(deployment)

		self.assertEqual(deployment.status, deployment_service.STATUS_CLOSED_OUT)
		self.assertEqual(deployment.closed_out_by, frappe.session.user)
		self.assertTrue(deployment.closed_out_on)

	def test_neither_optional_field_is_required(self):
		deployment = self.deployment(status=deployment_service.STATUS_COMPLETED)
		answer = deployment_service.close_out(deployment)

		self.assertTrue(answer["is_closed_out"])
		self.assertIsNone(deployment.lessons_learned)
		self.assertIsNone(deployment.mission_report)

	def test_lessons_are_kept_where_somebody_wrote_them(self):
		deployment = self.deployment(status=deployment_service.STATUS_COMPLETED)
		deployment_service.close_out(deployment, lessons="Two boats were one too few.")

		self.assertEqual(deployment.lessons_learned, "Two boats were one too few.")

	def test_an_unanswered_roster_does_not_block_it(self):
		"""The rule this test exists to protect: a close-out that can be refused
		is a close-out that does not happen."""
		deployment = self.deployment()
		volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Never", "Answered"), self.society_a["branch"]
		)

		from vmmsx.deployment.services import invitation

		invitation.invite(deployment, volunteer.name)
		deployment_service.set_status(deployment, deployment_service.STATUS_COMPLETED)

		self.assertTrue(deployment_service.close_out(deployment)["is_closed_out"])

	def test_it_lands_in_the_deployments_own_feed(self):
		from vmmsx.deployment.services import feed

		deployment = self.deployment(status=deployment_service.STATUS_COMPLETED)
		deployment_service.close_out(deployment)

		entries = feed.of(deployment.name)["entries"]

		self.assertTrue(any(deployment_service.STATUS_CLOSED_OUT in (row["note"] or "") for row in entries))
