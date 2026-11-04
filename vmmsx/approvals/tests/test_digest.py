# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The weekly approval summaries.

Two stages on the stand-in doctype: the county first, then a regional stage
whose breach action is `weekly_digest`. Time is moved by passing `now`, never by
editing timestamps, so what is late is decided by the same clock the job uses.
"""

from unittest.mock import patch

import frappe
from frappe.utils import add_days, get_datetime, now_datetime

from vmmsx.approvals import states
from vmmsx.approvals.services import digest, engine, sla
from vmmsx.approvals.tests import fixtures
from vmmsx.approvals.tests.base import ApprovalTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

REGIONAL_ROLE = fixtures.SECOND_ROLE


class DigestTestCase(ApprovalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		levels = cls.kenya["levels"]
		cls.county_kiambu = fixtures.make_user("digest_kiambu", [fixtures.APPROVER_ROLE])
		cls.county_nakuru = fixtures.make_user("digest_nakuru", [fixtures.APPROVER_ROLE])
		cls.regional = fixtures.make_user("digest_region", [REGIONAL_ROLE])
		fixtures.make_assignment(cls.county_kiambu, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])
		fixtures.make_assignment(cls.county_nakuru, fixtures.APPROVER_ROLE, cls.kenya["nakuru"])
		fixtures.make_assignment(cls.regional, REGIONAL_ROLE, cls.kenya["region"])

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(
					1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE,
					resolution_rule="at_level", geo_level=levels["county"], completion_rule="any_of",
				),
				fixtures.stage(
					2, fixtures.LABEL_REGION, REGIONAL_ROLE,
					resolution_rule="at_level", geo_level=levels["region"], completion_rule="any_of",
					is_optional=1, on_sla_breach=sla.BREACH_WEEKLY_DIGEST,
				),
			]
		)

	def setUp(self):
		super().setUp()
		# Only this test's applications: the stand-in may hold rows from other modules.
		frappe.db.delete(fixtures.APPROVABLE_DOCTYPE)
		patcher = patch("vmmsx.setup.regional_oversight.role", return_value=REGIONAL_ROLE)
		patcher.start()
		self.addCleanup(patcher.stop)
		national = patch.object(digest, "NATIONAL_DOCTYPES", (fixtures.APPROVABLE_DOCTYPE,))
		national.start()
		self.addCleanup(national.stop)

	# --- helpers ------------------------------------------------------------

	def at_region(self, title: str, node: str) -> str:
		"""Submitted and approved by its county, so it waits on the region."""
		name = self.application(title, node)
		engine.submit(self.reload(name))
		county = self.county_kiambu if node in (self.kenya["kihara"], self.kenya["ndenderu"]) else self.county_nakuru

		with fixtures.acting_as(county):
			engine.decide(self.reload(name), states.DECISION_APPROVED)

		return name

	def later(self, days: int):
		return add_days(now_datetime(), days)


class TestApproverSummary(DigestTestCase):
	def test_nothing_late_sends_nothing(self):
		self.at_region("fresh", self.kenya["kihara"])

		self.assertEqual(digest.approver_summaries(self.later(1)), {})

	def test_a_late_item_reaches_the_regional_approver_only(self):
		self.at_region("late one", self.kenya["kihara"])
		self.at_region("late two", self.kenya["bahati"])

		summaries = digest.approver_summaries(self.later(6))

		self.assertEqual(set(summaries), {self.regional})
		section = summaries[self.regional]["sections"][0]
		self.assertEqual(section["waiting_total"], 2)
		self.assertEqual(section["late_total"], 2)
		self.assertEqual({row["place"] for row in section["waiting"]}, {"Kihara", "Bahati"})

	def test_earlier_stage_backlog_is_listed_by_place(self):
		self.at_region("at region", self.kenya["kihara"])
		stuck = self.application("stuck at county", self.kenya["bahati"])
		engine.submit(self.reload(stuck))

		section = digest.approver_summaries(self.later(6))[self.regional]["sections"][0]

		self.assertEqual(section["earlier"]["total"], 1)
		self.assertEqual(section["earlier"]["places"][0]["place"], "Bahati")

	def test_returned_applications_are_separate_and_not_waiting(self):
		self.at_region("waiting", self.kenya["kihara"])
		returned = self.application("returned", self.kenya["ndenderu"])
		engine.submit(self.reload(returned))

		with fixtures.acting_as(self.county_kiambu):
			engine.decide(self.reload(returned), states.DECISION_MORE_INFO, reason="Add your ID copy")

		section = digest.approver_summaries(self.later(6))[self.regional]["sections"][0]

		self.assertEqual(section["waiting_total"], 1)
		self.assertEqual(section["with_applicant"]["total"], 1)
		self.assertEqual(section["earlier"]["total"], 0)

	def test_the_daily_sweep_does_not_alert_on_a_digest_stage(self):
		name = self.at_region("swept", self.kenya["kihara"])

		outcome = sla.apply_breach(self.reload(name), now=get_datetime(self.later(9)))

		self.assertTrue(outcome["breached"])
		self.assertEqual(outcome["notified"], [])
		self.assertEqual(outcome["escalated_to"], [])


class TestDelivery(DigestTestCase):
	def test_sent_once_a_week(self):
		self.at_region("weekly", self.kenya["kihara"])
		monday = self.later(7)

		first = digest.send(monday)
		second = digest.send(monday)
		next_week = digest.send(add_days(monday, 7))

		self.assertIn(self.regional, first["approvers"])
		self.assertEqual(second["approvers"], [])
		self.assertIn(self.regional, next_week["approvers"])

	def test_the_hourly_job_waits_for_the_chosen_morning(self):
		with patch.object(digest, "now_datetime", return_value=get_datetime("2026-11-09 06:30:00")), patch.object(digest, "send") as send:
			digest.hourly()
			send.assert_not_called()

		with patch.object(digest, "now_datetime", return_value=get_datetime("2026-11-10 08:00:00")), patch.object(digest, "send") as send:
			digest.hourly()  # a Tuesday
			send.assert_not_called()

		with patch.object(digest, "now_datetime", return_value=get_datetime("2026-11-09 07:05:00")), patch.object(digest, "send") as send:
			digest.hourly()  # Monday morning
			send.assert_called_once()


class TestNationalSummary(DigestTestCase):
	def test_recipients_hold_the_oversight_role_at_the_top(self):
		self.assertEqual(digest.national_recipients(), [self.regional])

	def test_only_items_past_the_threshold_count(self):
		self.at_region("national", self.kenya["kihara"])

		self.assertIsNone(digest.national_summary(self.later(digest.oversight_days() - 1)))

		summary = digest.national_summary(self.later(digest.oversight_days()))
		section = summary["sections"][0]

		self.assertEqual(summary["threshold"], digest.oversight_days())
		self.assertEqual(section["overdue_total"], 1)
		self.assertEqual(section["by_stage"], [{"label": fixtures.LABEL_REGION, "count": 1}])

	def test_returned_applications_are_counted_separately(self):
		self.at_region("still waiting", self.kenya["kihara"])
		returned = self.application("national returned", self.kenya["ndenderu"])
		engine.submit(self.reload(returned))

		with fixtures.acting_as(self.county_kiambu):
			engine.decide(self.reload(returned), states.DECISION_MORE_INFO, reason="Add your ID copy")

		section = digest.national_summary(self.later(20))["sections"][0]

		self.assertEqual(section["overdue_total"], 1)
		self.assertEqual(section["with_applicant_total"], 1)
		self.assertEqual(section["with_applicant_old"], 1)
