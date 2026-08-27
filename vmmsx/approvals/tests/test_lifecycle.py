# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The lifecycle — submission, stages, rejection, withdrawal, cooldown, expiry.

The recurring theme is that **nothing here is destructive**. A rejected
application is a rejected application: the record survives, with its reason and
its audit trail, because "we told them no in March" is information the society
needs and a deleted row is not. The same goes for withdrawal and expiry.

The other theme is idempotence. Submitting twice, or recording the decision you
already recorded, must not produce a second audit row, a second assignment, or a
reset clock — in a real desk, with a slow connection and an impatient user, all
three will be attempted.
"""

import frappe
from frappe.utils import add_to_date, now_datetime

from vmmsx.approvals import states
from vmmsx.approvals.services import contract, engine
from vmmsx.approvals.tests import fixtures
from vmmsx.approvals.tests.base import ApprovalTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestTwoStageReview(ApprovalTestCase):
	"""County endorses, region signs off. The ordinary path, end to end."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("flow_county", [fixtures.APPROVER_ROLE])
		cls.region = fixtures.make_user("flow_region", [fixtures.SECOND_ROLE])

		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])
		fixtures.make_assignment(cls.region, fixtures.SECOND_ROLE, cls.kenya["region"])

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE),
				fixtures.stage(2, fixtures.LABEL_REGION, fixtures.SECOND_ROLE, can_reject=0),
			]
		)

	def test_a_new_application_is_a_draft(self):
		application = self.application("draft", self.kenya["kihara"])

		self.assertEqual(self.state(application), states.DRAFT)
		self.assertIsNone(contract.stage(self.reload(application)))

	def test_submission_enters_the_first_stage(self):
		application = self.application("first stage", self.kenya["kihara"])
		status = engine.submit(self.reload(application))

		self.assertEqual(status["state"], states.IN_REVIEW)
		self.assertEqual(status["stage"]["sequence"], 1)
		self.assertEqual(status["approvers"], [self.county])

	def test_approval_moves_it_to_the_next_stage_and_the_next_person(self):
		application = self.application("second stage", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.county):
			status = engine.decide(self.reload(application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.IN_REVIEW)
		self.assertEqual(status["stage"]["sequence"], 2)
		self.assertEqual(status["approvers"], [self.region])
		self.assertNotIn(application, self.queue_of(self.county))
		self.assertIn(application, self.queue_of(self.region))

	def test_the_last_stage_approves_the_application(self):
		application = self.application("final", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.county):
			engine.decide(self.reload(application), states.DECISION_APPROVED)

		with fixtures.acting_as(self.region):
			status = engine.decide(self.reload(application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.APPROVED)
		self.assertIsNone(status["stage"])
		self.assertNotIn(application, self.queue_of(self.region))

	def test_the_audit_trail_records_both_decisions_in_order(self):
		application = self.application("audit", self.kenya["kihara"])
		engine.submit(self.reload(application))

		for user in (self.county, self.region):
			with fixtures.acting_as(user):
				engine.decide(self.reload(application), states.DECISION_APPROVED)

		decisions = contract.decisions(self.reload(application))

		self.assertEqual([row.stage_sequence for row in decisions], [1, 2])
		self.assertEqual([row.approver for row in decisions], [self.county, self.region])
		self.assertEqual(
			[row.stage_label for row in decisions], [fixtures.LABEL_COUNTY, fixtures.LABEL_REGION]
		)

	def test_a_second_stage_approver_cannot_act_while_it_is_at_the_first(self):
		"""Stages are sequential, and the gate is per stage, not per workflow."""
		application = self.application("out of turn", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.region), self.assertRaises(frappe.PermissionError):
			engine.decide(self.reload(application), states.DECISION_APPROVED)

	def test_an_approved_application_cannot_be_decided_again(self):
		application = self.application("decided", self.kenya["kihara"])
		engine.submit(self.reload(application))

		for user in (self.county, self.region):
			with fixtures.acting_as(user):
				engine.decide(self.reload(application), states.DECISION_APPROVED)

		with fixtures.acting_as(self.region), self.assertRaises(frappe.ValidationError):
			engine.decide(self.reload(application), states.DECISION_APPROVED)


class TestIdempotence(ApprovalTestCase):
	"""Everything here will be attempted twice by a real user on a real network.

	One stage, `all_of`, two coordinators — so the stage is still current after
	the first decision and a repeated call has something to be idempotent
	*about*. With a single-approver stage the second call would simply find a
	decided application, which tests a different rule.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.coordinators = sorted(
			fixtures.make_user(f"idem_{handle}", [fixtures.APPROVER_ROLE]) for handle in ("one", "two")
		)
		cls.county = cls.coordinators[0]

		for coordinator in cls.coordinators:
			fixtures.make_assignment(coordinator, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(
					1,
					fixtures.LABEL_COUNTY,
					fixtures.APPROVER_ROLE,
					completion_rule="all_of",
				)
			]
		)

	def test_submitting_twice_changes_nothing(self):
		application = self.application("submit twice", self.kenya["kihara"])
		first = engine.submit(self.reload(application))
		second = engine.submit(self.reload(application))

		self.assertEqual(first["stage"]["name"], second["stage"]["name"])
		self.assertEqual(first["stage"]["entered_on"], second["stage"]["entered_on"])

	def test_submitting_twice_does_not_restart_the_sla_clock(self):
		"""Otherwise anybody could reset an approver's deadline by re-submitting."""
		application = self.application("clock keeps", self.kenya["kihara"])
		engine.submit(self.reload(application))
		entered = contract.stage_entered_on(self.reload(application))

		engine.submit(self.reload(application))

		self.assertEqual(contract.stage_entered_on(self.reload(application)), entered)

	def test_submitting_twice_does_not_duplicate_the_assignment(self):
		application = self.application("no double todo", self.kenya["kihara"])
		engine.submit(self.reload(application))
		engine.submit(self.reload(application))

		self.assertEqual(
			frappe.db.count(
				"ToDo",
				{
					"reference_type": fixtures.APPROVABLE_DOCTYPE,
					"reference_name": application,
					"allocated_to": self.county,
					"status": ("in", ("Open", "Overdue")),
				},
			),
			1,
		)

	def test_re_submitting_restores_an_assignment_somebody_closed(self):
		"""Assignment is a notification, and notifications can be dismissed."""
		application = self.application("restore todo", self.kenya["kihara"])
		engine.submit(self.reload(application))

		frappe.db.set_value(
			"ToDo",
			{"reference_type": fixtures.APPROVABLE_DOCTYPE, "reference_name": application},
			"status",
			"Closed",
		)
		self.assertNotIn(application, self.queue_of(self.county))

		engine.submit(self.reload(application))

		self.assertIn(application, self.queue_of(self.county))

	def test_the_same_decision_twice_is_recorded_once(self):
		application = self.application("same decision", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.county):
			first = engine.decide(self.reload(application), states.DECISION_APPROVED)
			second = engine.decide(self.reload(application), states.DECISION_APPROVED)

		self.assertEqual(first["state"], second["state"])
		self.assertEqual(first["stage"]["name"], second["stage"]["name"])
		self.assertEqual(len(contract.decisions(self.reload(application))), 1)

	def test_a_different_decision_afterwards_is_refused(self):
		"""Changing your mind is a new stage or a new application, not a rewrite."""
		application = self.application("change mind", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.county):
			engine.decide(self.reload(application), states.DECISION_APPROVED)

			with self.assertRaises(frappe.ValidationError):
				engine.decide(self.reload(application), states.DECISION_REJECTED, "changed my mind")


class TestRejection(ApprovalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("reject_county", [fixtures.APPROVER_ROLE])
		cls.applicant = fixtures.make_user("reject_applicant", [fixtures.APPLICANT_ROLE])
		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)]
		)

	def submitted(self, title: str) -> str:
		application = fixtures.make_application(
			title, self.kenya["kihara"], applicant=self.applicant, owner=self.applicant
		)
		engine.submit(fixtures.load(application))

		return application

	def test_a_rejection_needs_a_reason(self):
		application = self.submitted("no reason")

		with fixtures.acting_as(self.county), self.assertRaises(frappe.MandatoryError):
			engine.decide(fixtures.load(application), states.DECISION_REJECTED)

	def test_a_blank_reason_is_not_a_reason(self):
		application = self.submitted("blank reason")

		with fixtures.acting_as(self.county), self.assertRaises(frappe.MandatoryError):
			engine.decide(fixtures.load(application), states.DECISION_REJECTED, "   ")

	def test_a_refused_rejection_records_nothing(self):
		application = self.submitted("refused rejection")

		with fixtures.acting_as(self.county), self.assertRaises(frappe.MandatoryError):
			engine.decide(fixtures.load(application), states.DECISION_REJECTED)

		self.assertEqual(self.state(application), states.IN_REVIEW)
		self.assertEqual(contract.decisions(fixtures.load(application)), [])

	def test_a_rejection_with_a_reason_terminates_the_application(self):
		application = self.submitted("rejected")

		with fixtures.acting_as(self.county):
			status = engine.decide(
				fixtures.load(application), states.DECISION_REJECTED, "References could not be verified."
			)

		self.assertEqual(status["state"], states.REJECTED)
		self.assertIsNone(status["stage"])
		self.assertNotIn(application, self.queue_of(self.county))

	def test_the_reason_is_kept_where_the_applicant_can_be_told(self):
		application = self.submitted("reason kept")

		with fixtures.acting_as(self.county):
			engine.decide(fixtures.load(application), states.DECISION_REJECTED, "Under the minimum age.")

		decision = contract.decisions(fixtures.load(application))[0]

		self.assertEqual(decision.decision, states.DECISION_REJECTED)
		self.assertEqual(decision.reason, "Under the minimum age.")
		self.assertEqual(decision.approver, self.county)

	def test_a_rejected_application_leaves_the_record_intact(self):
		"""No dead record. The application survives, with its reason and history.

		Deleting or blanking it would destroy the only evidence of what was
		decided — and the applicant is entitled to that evidence more than
		anybody.
		"""
		application = self.submitted("intact")
		before = fixtures.load(application)

		with fixtures.acting_as(self.county):
			engine.decide(fixtures.load(application), states.DECISION_REJECTED, "Not this time.")

		after = fixtures.load(application)

		self.assertTrue(frappe.db.exists(fixtures.APPROVABLE_DOCTYPE, application))
		self.assertEqual(after.title, before.title)
		self.assertEqual(after.get(fixtures.GEO_FIELD), before.get(fixtures.GEO_FIELD))
		self.assertEqual(after.get(fixtures.APPLICANT_FIELD), self.applicant)
		self.assertEqual(after.owner, self.applicant)
		self.assertEqual(len(contract.decisions(after)), 1)


class TestEndorseOnlyStage(ApprovalTestCase):
	"""A stage may be configured to pass an application on, but never to end it."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.branch = fixtures.make_user("endorse_branch", [fixtures.APPROVER_ROLE])
		cls.county = fixtures.make_user("endorse_county", [fixtures.SECOND_ROLE])

		fixtures.make_assignment(cls.branch, fixtures.APPROVER_ROLE, cls.kenya["kihara"])
		fixtures.make_assignment(cls.county, fixtures.SECOND_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(1, fixtures.LABEL_BRANCH, fixtures.APPROVER_ROLE, can_reject=0),
				fixtures.stage(2, fixtures.LABEL_COUNTY, fixtures.SECOND_ROLE),
			]
		)

	def test_the_endorsing_stage_cannot_reject(self):
		application = self.application("endorse only", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.branch), self.assertRaises(frappe.ValidationError):
			engine.decide(self.reload(application), states.DECISION_REJECTED, "I would rather not")

	def test_but_the_stage_after_it_can(self):
		application = self.application("endorse then reject", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.branch):
			engine.decide(self.reload(application), states.DECISION_APPROVED)

		with fixtures.acting_as(self.county):
			status = engine.decide(self.reload(application), states.DECISION_REJECTED, "Not eligible.")

		self.assertEqual(status["state"], states.REJECTED)


class TestMoreInformation(ApprovalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("info_county", [fixtures.APPROVER_ROLE])
		cls.applicant = fixtures.make_user("info_applicant", [fixtures.APPLICANT_ROLE])
		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)]
		)

	def submitted(self, title: str) -> str:
		application = fixtures.make_application(title, self.kenya["kihara"], owner=self.applicant)
		engine.submit(fixtures.load(application))

		return application

	def test_it_goes_back_to_the_applicant(self):
		application = self.submitted("more info")

		with fixtures.acting_as(self.county):
			status = engine.decide(
				fixtures.load(application), states.DECISION_MORE_INFO, "Please attach an ID."
			)

		self.assertEqual(status["state"], states.DRAFT)
		self.assertIsNone(status["stage"])
		self.assertNotIn(application, self.queue_of(self.county))

	def test_the_request_is_in_the_audit_trail(self):
		application = self.submitted("more info audit")

		with fixtures.acting_as(self.county):
			engine.decide(fixtures.load(application), states.DECISION_MORE_INFO, "Please attach an ID.")

		decision = contract.decisions(fixtures.load(application))[0]

		self.assertEqual(decision.decision, states.DECISION_MORE_INFO)
		self.assertEqual(decision.reason, "Please attach an ID.")

	def test_a_request_for_more_information_needs_instructions(self):
		application = self.submitted("more info without instructions")

		with fixtures.acting_as(self.county), self.assertRaises(frappe.MandatoryError):
			engine.decide(fixtures.load(application), states.DECISION_MORE_INFO, "  ")

		self.assertEqual(self.state(application), states.IN_REVIEW)
		self.assertEqual(contract.decisions(fixtures.load(application)), [])

	def test_resubmission_starts_the_review_again(self):
		"""What the earlier stages saw is not what they are being asked about now."""
		application = self.submitted("resubmit")

		with fixtures.acting_as(self.county):
			engine.decide(fixtures.load(application), states.DECISION_MORE_INFO, "Please attach an ID.")

		status = engine.submit(fixtures.load(application))

		self.assertEqual(status["state"], states.IN_REVIEW)
		self.assertEqual(status["stage"]["sequence"], 1)
		self.assertIn(application, self.queue_of(self.county))


class TestWithdrawal(ApprovalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("withdraw_county", [fixtures.APPROVER_ROLE])
		cls.applicant = fixtures.make_user("withdraw_applicant", [fixtures.APPLICANT_ROLE])
		cls.stranger = fixtures.make_user("withdraw_stranger", [fixtures.APPLICANT_ROLE])
		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)], allow_withdrawal=1
		)

	def submitted(self, title: str) -> str:
		application = fixtures.make_application(title, self.kenya["kihara"], owner=self.applicant)
		engine.submit(fixtures.load(application))

		return application

	def test_the_applicant_may_withdraw(self):
		application = self.submitted("withdrawn")

		with fixtures.acting_as(self.applicant):
			status = engine.withdraw(fixtures.load(application), "Moving abroad.")

		self.assertEqual(status["state"], states.WITHDRAWN)
		self.assertNotIn(application, self.queue_of(self.county))

	def test_the_status_says_so_before_they_try(self):
		application = self.submitted("can withdraw")

		with fixtures.acting_as(self.applicant):
			status = engine.status(fixtures.load(application))

		self.assertTrue(status["allow_withdrawal"])
		self.assertTrue(status["can_withdraw"])

	def test_a_stranger_may_not_withdraw_somebody_else_s_application(self):
		application = self.submitted("stranger")

		with fixtures.acting_as(self.stranger), self.assertRaises(frappe.PermissionError):
			engine.withdraw(fixtures.load(application))

	def test_the_approver_may_not_withdraw_it_either(self):
		"""An approver rejects, with a reason. Withdrawing on someone's behalf
		would put an applicant's decision in an approver's hands."""
		application = self.submitted("approver withdraw")

		with fixtures.acting_as(self.county), self.assertRaises(frappe.PermissionError):
			engine.withdraw(fixtures.load(application))

	def test_a_withdrawn_application_is_final(self):
		application = self.submitted("withdrawn final")

		with fixtures.acting_as(self.applicant):
			engine.withdraw(fixtures.load(application))

		with fixtures.acting_as(self.county), self.assertRaises(frappe.ValidationError):
			engine.decide(fixtures.load(application), states.DECISION_APPROVED)

	def test_a_draft_may_be_withdrawn_before_anybody_sees_it(self):
		application = fixtures.make_application("draft withdraw", self.kenya["kihara"], owner=self.applicant)

		with fixtures.acting_as(self.applicant):
			status = engine.withdraw(fixtures.load(application))

		self.assertEqual(status["state"], states.WITHDRAWN)


class TestWithdrawalNotAllowed(ApprovalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("nowithdraw_county", [fixtures.APPROVER_ROLE])
		cls.applicant = fixtures.make_user("nowithdraw_applicant", [fixtures.APPLICANT_ROLE])
		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)], allow_withdrawal=0
		)

	def test_the_policy_is_enforced(self):
		application = fixtures.make_application("no withdrawal", self.kenya["kihara"], owner=self.applicant)
		engine.submit(fixtures.load(application))

		with fixtures.acting_as(self.applicant), self.assertRaises(frappe.ValidationError):
			engine.withdraw(fixtures.load(application))

	def test_and_the_status_does_not_offer_it(self):
		application = fixtures.make_application(
			"no withdrawal dto", self.kenya["kihara"], owner=self.applicant
		)

		with fixtures.acting_as(self.applicant):
			status = engine.status(fixtures.load(application))

		self.assertFalse(status["allow_withdrawal"])
		self.assertFalse(status["can_withdraw"])


class TestReapplicationCooldown(ApprovalTestCase):
	COOLDOWN_DAYS = 30

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("cooldown_county", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)],
			applicant_field=fixtures.APPLICANT_FIELD,
			reapplication_cooldown_days=cls.COOLDOWN_DAYS,
		)

	def rejected_application(self, applicant: str) -> str:
		application = fixtures.make_application("cooldown first", self.kenya["kihara"], applicant=applicant)
		engine.submit(fixtures.load(application))

		with fixtures.acting_as(self.county):
			engine.decide(fixtures.load(application), states.DECISION_REJECTED, "Not eligible yet.")

		return application

	def age_the_rejection(self, application: str, days: int) -> None:
		"""Move the recorded decision back in time, as the calendar would."""
		row = contract.decisions(fixtures.load(application))[0]

		frappe.db.set_value(
			contract.DECISION_DOCTYPE,
			row.name,
			"decided_on",
			add_to_date(now_datetime(), days=-days),
			update_modified=False,
		)

	def test_re_applying_too_soon_is_refused(self):
		applicant = "RP-COOLDOWN-1"
		self.rejected_application(applicant)

		again = fixtures.make_application("cooldown second", self.kenya["kihara"], applicant=applicant)

		with self.assertRaises(frappe.ValidationError):
			engine.submit(fixtures.load(again))

		self.assertEqual(self.state(again), states.DRAFT)

	def test_somebody_else_is_not_caught_by_it(self):
		self.rejected_application("RP-COOLDOWN-2")

		other = fixtures.make_application("cooldown other", self.kenya["kihara"], applicant="RP-COOLDOWN-3")
		status = engine.submit(fixtures.load(other))

		self.assertEqual(status["state"], states.IN_REVIEW)

	def test_once_the_window_passes_they_may_apply_again(self):
		applicant = "RP-COOLDOWN-4"
		rejected = self.rejected_application(applicant)
		self.age_the_rejection(rejected, self.COOLDOWN_DAYS + 1)

		again = fixtures.make_application("cooldown after", self.kenya["kihara"], applicant=applicant)
		status = engine.submit(fixtures.load(again))

		self.assertEqual(status["state"], states.IN_REVIEW)


class TestExpiry(ApprovalTestCase):
	EXPIRY_DAYS = 60

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("expiry_county", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)],
			application_expiry_days=cls.EXPIRY_DAYS,
		)

	def aged(self, title: str, days: int) -> str:
		application = fixtures.make_application(title, self.kenya["kihara"])
		engine.submit(fixtures.load(application))

		frappe.db.set_value(
			fixtures.APPROVABLE_DOCTYPE,
			application,
			"modified",
			add_to_date(now_datetime(), days=-days),
			update_modified=False,
		)

		return application

	def test_an_abandoned_application_expires(self):
		application = self.aged("abandoned", self.EXPIRY_DAYS + 1)
		summary = engine.expire_stale()

		self.assertGreaterEqual(summary["expired"], 1)
		self.assertEqual(self.state(application), states.EXPIRED)

	def test_expiry_empties_the_queue(self):
		application = self.aged("abandoned queue", self.EXPIRY_DAYS + 1)
		engine.expire_stale()

		self.assertNotIn(application, self.queue_of(self.county))

	def test_a_live_application_is_left_alone(self):
		application = fixtures.make_application("still live", self.kenya["kihara"])
		engine.submit(fixtures.load(application))

		engine.expire_stale()

		self.assertEqual(self.state(application), states.IN_REVIEW)

	def test_an_expired_application_is_final(self):
		application = self.aged("expired final", self.EXPIRY_DAYS + 1)
		engine.expire_stale()

		with fixtures.acting_as(self.county), self.assertRaises(frappe.ValidationError):
			engine.decide(fixtures.load(application), states.DECISION_APPROVED)

	def test_the_record_survives_expiry(self):
		application = self.aged("expired intact", self.EXPIRY_DAYS + 1)
		engine.expire_stale()

		self.assertTrue(frappe.db.exists(fixtures.APPROVABLE_DOCTYPE, application))
