# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The clock, the escalation, and the person it must never go back to.

An application rotting in an absent approver's queue is the number-one failure
mode of a system like this — nothing crashes, nothing is logged, and the first
anybody hears of it is a volunteer asking why nobody replied for four months.

Two things are being proved here. That a breach escalates *up the tree*, and
that it escalates to somebody **other than the person who was already late** —
including in the arrangement where the late approver also holds authority at the
node above, which is where the naive implementation quietly hands them the same
document back and calls it an escalation.
"""

import frappe
from frappe.utils import add_to_date, now_datetime

from vmmsx.approvals import states
from vmmsx.approvals.services import config, engine, routing, sla
from vmmsx.approvals.tests import fixtures
from vmmsx.approvals.tests.base import ApprovalTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

SLA_DAYS = 5


class SLATestCase(ApprovalTestCase):
	BREACH_ACTION = sla.BREACH_ESCALATE_UP

	def submitted(self, title: str) -> str:
		application = fixtures.make_application(title, self.kenya["kihara"])
		engine.submit(fixtures.load(application))

		return application

	def overdue(self, title: str, days: int = 10) -> str:
		"""An application whose stage clock started long enough ago to breach."""
		application = self.submitted(title)

		frappe.db.set_value(
			fixtures.APPROVABLE_DOCTYPE,
			application,
			"approval_stage_entered_on",
			add_to_date(now_datetime(), days=-days),
			update_modified=False,
		)

		return application

	def comments_on(self, application: str) -> int:
		return frappe.db.count(
			"Comment",
			{
				"reference_doctype": fixtures.APPROVABLE_DOCTYPE,
				"reference_name": application,
				"comment_type": "Comment",
			},
		)


class TestTheClock(SLATestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.coordinator = fixtures.make_user("clock_county", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.coordinator, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE, sla_days=SLA_DAYS)]
		)

	def stage(self):
		return config.stages(config.for_doctype(fixtures.APPROVABLE_DOCTYPE))[0]

	def test_a_fresh_stage_is_not_breached(self):
		application = self.submitted("clock fresh")

		self.assertFalse(sla.is_breached(fixtures.load(application), self.stage()))

	def test_the_due_date_is_the_stage_clock(self):
		application = self.submitted("clock due")
		doc = fixtures.load(application)

		self.assertEqual(
			sla.due_on(doc, self.stage()),
			add_to_date(doc.approval_stage_entered_on, days=SLA_DAYS),
		)

	def test_an_old_stage_is_breached(self):
		application = self.overdue("clock old")

		self.assertTrue(sla.is_breached(fixtures.load(application), self.stage()))

	def test_it_says_how_overdue(self):
		application = self.overdue("clock overdue", days=SLA_DAYS + 3)

		self.assertEqual(sla.days_overdue(fixtures.load(application), self.stage()), 3)

	def test_the_status_carries_the_clock(self):
		application = self.overdue("clock status")
		status = engine.status(fixtures.load(application))

		self.assertTrue(status["stage"]["is_breached"])
		self.assertGreaterEqual(status["stage"]["days_overdue"], 1)


class TestEscalatesUpTheTree(SLATestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.late = fixtures.make_user("escalate_late", [fixtures.APPROVER_ROLE])
		cls.regional = fixtures.make_user("escalate_region", [fixtures.APPROVER_ROLE])

		fixtures.make_assignment(cls.late, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])
		fixtures.make_assignment(cls.regional, fixtures.APPROVER_ROLE, cls.kenya["region"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE, sla_days=SLA_DAYS)]
		)

	def test_nothing_happens_before_the_clock_runs_out(self):
		application = self.submitted("escalate early")
		outcome = sla.apply_breach(fixtures.load(application))

		self.assertFalse(outcome["breached"])
		self.assertNotIn(application, self.queue_of(self.regional))

	def test_a_breach_escalates_to_the_node_above(self):
		application = self.overdue("escalate up")
		outcome = sla.apply_breach(fixtures.load(application))

		self.assertTrue(outcome["breached"])
		self.assertEqual(outcome["escalated_to"], [self.regional])
		self.assertEqual(outcome["escalation_node"], self.kenya["region"])

	def test_the_escalation_target_gets_it_in_their_queue(self):
		application = self.overdue("escalate queue")
		sla.apply_breach(fixtures.load(application))

		self.assertIn(application, self.queue_of(self.regional))

	def test_the_late_approver_keeps_it_too(self):
		"""A breach widens authority; it never takes the document off a desk.

		Removing it would hide the fact that they were late from the only people
		able to notice.
		"""
		application = self.overdue("escalate keeps")
		sla.apply_breach(fixtures.load(application))

		self.assertIn(application, self.queue_of(self.late))

	def test_the_escalation_target_may_now_act(self):
		application = self.overdue("escalate acts")
		sla.apply_breach(fixtures.load(application))

		with fixtures.acting_as(self.regional):
			status = engine.decide(fixtures.load(application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.APPROVED)

	def test_the_late_approver_may_still_act(self):
		application = self.overdue("escalate late acts")
		sla.apply_breach(fixtures.load(application))

		with fixtures.acting_as(self.late):
			status = engine.decide(fixtures.load(application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.APPROVED)

	def test_authority_widens_the_moment_the_clock_runs_out(self):
		"""The sweep notifies; it does not grant. The gate reads the clock itself.

		So an escalation is correct whether or not the nightly job ever ran —
		which matters, because the night it does not run is the night somebody
		needs it.
		"""
		application = self.overdue("escalate without sweep")

		with fixtures.acting_as(self.regional):
			self.assertTrue(engine.may_act(fixtures.load(application)))

	def test_the_sweep_finds_it(self):
		application = self.overdue("escalate sweep")
		summary = sla.sweep()

		self.assertGreaterEqual(summary["breached"], 1)
		self.assertGreaterEqual(summary["escalated"], 1)
		self.assertIn(application, self.queue_of(self.regional))

	def test_sweeping_twice_escalates_once(self):
		"""Idempotent: the second run adds nobody and says nothing new."""
		application = self.overdue("escalate twice")
		sla.sweep()
		comments = self.comments_on(application)
		assignments = len(self.queue_of(self.regional))

		sla.sweep()

		self.assertEqual(self.comments_on(application), comments)
		self.assertEqual(len(self.queue_of(self.regional)), assignments)


class TestNeverBackToThePersonWhoIsLate(SLATestCase):
	"""The bug this class exists for.

	The late county coordinator *also* holds authority at the region — a real
	arrangement, since senior staff are often assigned at more than one level. A
	naive escalation walks up, finds a holder, and hands the document straight
	back to the person who has been sitting on it. That is not an escalation, it
	is a loop with extra notifications.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.late = fixtures.make_user("loop_late", [fixtures.APPROVER_ROLE])
		cls.regional = fixtures.make_user("loop_region", [fixtures.APPROVER_ROLE])

		fixtures.make_assignment(cls.late, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])
		# The same person, again, higher up.
		fixtures.make_assignment(cls.late, fixtures.APPROVER_ROLE, cls.kenya["region"])
		fixtures.make_assignment(cls.regional, fixtures.APPROVER_ROLE, cls.kenya["region"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE, sla_days=SLA_DAYS)]
		)

	def test_the_late_approver_holds_authority_at_the_escalation_node(self):
		"""The arrangement, stated — otherwise the next test proves nothing."""
		self.assertIn(self.late, routing.holders_exactly_at(self.kenya["region"], fixtures.APPROVER_ROLE))

	def test_the_escalation_skips_them(self):
		application = self.overdue("loop skip")
		outcome = sla.apply_breach(fixtures.load(application))

		self.assertEqual(outcome["escalated_to"], [self.regional])
		self.assertNotIn(self.late, outcome["escalated_to"])

	def test_the_resolver_itself_refuses_to_return_them(self):
		self.assertEqual(
			routing.escalate(fixtures.APPROVER_ROLE, self.kenya["kihara"], exclude={self.late}),
			{"approvers": [self.regional], "node": self.kenya["region"]},
		)


class TestNotifyOnly(SLATestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.late = fixtures.make_user("notify_late", [fixtures.APPROVER_ROLE])
		cls.regional = fixtures.make_user("notify_region", [fixtures.APPROVER_ROLE])

		fixtures.make_assignment(cls.late, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])
		fixtures.make_assignment(cls.regional, fixtures.APPROVER_ROLE, cls.kenya["region"])

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(
					1,
					fixtures.LABEL_COUNTY,
					fixtures.APPROVER_ROLE,
					sla_days=SLA_DAYS,
					on_sla_breach=sla.BREACH_NOTIFY_ONLY,
				)
			]
		)

	def test_it_reminds_the_approver(self):
		application = self.overdue("notify reminds")
		outcome = sla.apply_breach(fixtures.load(application))

		self.assertTrue(outcome["breached"])
		self.assertEqual(outcome["notified"], [self.late])

	def test_it_re_routes_nobody(self):
		application = self.overdue("notify no reroute")
		sla.apply_breach(fixtures.load(application))

		self.assertEqual([], [user for user in [self.regional] if application in self.queue_of(user)])

	def test_the_person_above_still_may_not_act(self):
		"""notify_only is a reminder, not a transfer of authority.

		The breach widens the gate only where the society asked for an
		escalation; here it asked for a nudge.
		"""
		application = self.overdue("notify no authority")

		with fixtures.acting_as(self.regional), self.assertRaises(frappe.PermissionError):
			engine.decide(fixtures.load(application), states.DECISION_APPROVED)


class TestBreachActionNone(SLATestCase):
	"""An explicit society choice to let it sit — recorded, not reinterpreted."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.late = fixtures.make_user("none_late", [fixtures.APPROVER_ROLE])
		cls.regional = fixtures.make_user("none_region", [fixtures.APPROVER_ROLE])

		fixtures.make_assignment(cls.late, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])
		fixtures.make_assignment(cls.regional, fixtures.APPROVER_ROLE, cls.kenya["region"])

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(
					1,
					fixtures.LABEL_COUNTY,
					fixtures.APPROVER_ROLE,
					sla_days=SLA_DAYS,
					on_sla_breach=sla.BREACH_NONE,
				)
			]
		)

	def test_the_breach_is_still_reported(self):
		application = self.overdue("none reported")
		outcome = sla.apply_breach(fixtures.load(application))

		self.assertTrue(outcome["breached"])
		self.assertEqual(outcome["escalated_to"], [])
		self.assertEqual(outcome["notified"], [])

	def test_nobody_new_is_involved(self):
		application = self.overdue("none quiet")
		sla.apply_breach(fixtures.load(application))

		self.assertNotIn(application, self.queue_of(self.regional))


class TestNowhereToEscalate(SLATestCase):
	"""Nobody above holds the role. No fallback approver is invented."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.late = fixtures.make_user("stranded_late", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.late, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE, sla_days=SLA_DAYS)]
		)

	def test_it_escalates_to_nobody_rather_than_to_the_administrator(self):
		application = self.overdue("stranded")
		outcome = sla.apply_breach(fixtures.load(application))

		self.assertTrue(outcome["breached"])
		self.assertEqual(outcome["escalated_to"], [])

	def test_the_application_is_not_quietly_approved(self):
		application = self.overdue("stranded state")
		sla.apply_breach(fixtures.load(application))

		self.assertEqual(self.state(application), states.IN_REVIEW)

	def test_the_sweep_counts_it_as_stranded(self):
		self.overdue("stranded counted")
		summary = sla.sweep()

		self.assertGreaterEqual(summary["stranded"], 1)

	def test_and_says_so_in_the_error_log(self):
		"""An application nobody anywhere can act on is a fault, not a state."""
		application = self.overdue("stranded logged")
		sla.sweep()

		self.assertTrue(
			frappe.db.exists(
				"Error Log",
				{
					"method": sla.STRANDED_LOG_TITLE,
					"reference_doctype": fixtures.APPROVABLE_DOCTYPE,
					"reference_name": application,
				},
			),
			"a stranded escalation left no trace anybody could find",
		)
