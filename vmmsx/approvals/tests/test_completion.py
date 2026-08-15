# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""How many must act — the question core deliberately refused to answer.

`resolve_approvers` produces a list of people. Whether one of them is enough,
whether any of them will do, or whether every one of them must sign is a policy
this layer owns, and the three rules mean three different things:

    single   one named person owns it — the others are not routed at all
    any_of   everybody is routed, the first to act carries it
    all_of   everybody is routed, and the stage waits for every one of them

The guardrail is in the last class: an `all_of` stage that resolves nobody must
not pass. "Everybody agreed" and "there was nobody to ask" are not the same
sentence, and a system that cannot tell them apart approves applications no
human ever looked at.
"""

import frappe

from vmmsx.approvals import states
from vmmsx.approvals.services import config, contract, engine, routing
from vmmsx.approvals.tests import fixtures
from vmmsx.approvals.tests.base import ApprovalTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class CompletionTestCase(ApprovalTestCase):
	"""Two coordinators at one county — the arrangement all three rules differ over."""

	COMPLETION_RULE = routing.COMPLETION_SINGLE
	HANDLES = ("one", "two")

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.coordinators = sorted(
			fixtures.make_user(f"{cls.COMPLETION_RULE}_{handle}", [fixtures.APPROVER_ROLE])
			for handle in cls.HANDLES
		)

		for coordinator in cls.coordinators:
			fixtures.make_assignment(coordinator, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(
					1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE, completion_rule=cls.COMPLETION_RULE
				)
			]
		)

	def stage(self):
		return config.stages(config.for_doctype(fixtures.APPROVABLE_DOCTYPE))[0]

	def submitted(self, title: str) -> str:
		application = fixtures.make_application(title, self.kenya["kihara"])
		engine.submit(fixtures.load(application))

		return application


class TestSingle(CompletionTestCase):
	COMPLETION_RULE = routing.COMPLETION_SINGLE

	def test_both_coordinators_could_approve(self):
		"""Resolution finds both. Routing is what narrows it."""
		self.assertEqual(routing.resolve(self.stage(), self.kenya["kihara"]), self.coordinators)

	def test_only_one_is_routed(self):
		self.assertEqual(routing.routed(self.stage(), self.kenya["kihara"]), self.coordinators[:1])

	def test_the_choice_is_deterministic(self):
		"""Same stage, same place, same person — not whoever the query felt like."""
		for _ in range(3):
			self.assertEqual(routing.routed(self.stage(), self.kenya["kihara"]), self.coordinators[:1])

	def test_the_routed_one_advances_it(self):
		application = self.submitted("single routed")

		with fixtures.acting_as(self.coordinators[0]):
			status = engine.decide(fixtures.load(application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.APPROVED)

	def test_the_other_one_is_not_this_application_s_approver(self):
		"""A colleague with identical authority, and still not the routed person."""
		application = self.submitted("single other")

		with fixtures.acting_as(self.coordinators[1]), self.assertRaises(frappe.PermissionError):
			engine.decide(fixtures.load(application), states.DECISION_APPROVED)

	def test_only_the_routed_one_has_it_in_their_queue(self):
		application = self.submitted("single queue")

		self.assertIn(application, self.queue_of(self.coordinators[0]))
		self.assertNotIn(application, self.queue_of(self.coordinators[1]))


class TestAnyOf(CompletionTestCase):
	COMPLETION_RULE = routing.COMPLETION_ANY_OF

	def test_everybody_is_routed(self):
		self.assertEqual(routing.routed(self.stage(), self.kenya["kihara"]), self.coordinators)

	def test_it_is_in_everybody_s_queue(self):
		application = self.submitted("any queue")

		for coordinator in self.coordinators:
			self.assertIn(application, self.queue_of(coordinator))

	def test_one_decision_carries_it(self):
		application = self.submitted("any one")

		with fixtures.acting_as(self.coordinators[1]):
			status = engine.decide(fixtures.load(application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.APPROVED)

	def test_the_queue_empties_once_it_is_decided(self):
		application = self.submitted("any queue clear")

		with fixtures.acting_as(self.coordinators[0]):
			engine.decide(fixtures.load(application), states.DECISION_APPROVED)

		for coordinator in self.coordinators:
			self.assertNotIn(application, self.queue_of(coordinator))


class TestAllOf(CompletionTestCase):
	COMPLETION_RULE = routing.COMPLETION_ALL_OF

	def test_one_decision_is_not_enough(self):
		application = self.submitted("all first")

		with fixtures.acting_as(self.coordinators[0]):
			status = engine.decide(fixtures.load(application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.IN_REVIEW)
		self.assertEqual(self.state(application), states.IN_REVIEW)

	def test_the_one_who_acted_stops_seeing_it(self):
		application = self.submitted("all queue")

		with fixtures.acting_as(self.coordinators[0]):
			engine.decide(fixtures.load(application), states.DECISION_APPROVED)

		self.assertNotIn(application, self.queue_of(self.coordinators[0]))
		self.assertIn(application, self.queue_of(self.coordinators[1]))

	def test_the_last_decision_completes_it(self):
		application = self.submitted("all both")

		for coordinator in self.coordinators:
			with fixtures.acting_as(coordinator):
				status = engine.decide(fixtures.load(application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.APPROVED)

	def test_both_decisions_are_in_the_audit_trail(self):
		application = self.submitted("all audit")

		for coordinator in self.coordinators:
			with fixtures.acting_as(coordinator):
				engine.decide(fixtures.load(application), states.DECISION_APPROVED)

		decisions = contract.decisions(fixtures.load(application))

		self.assertEqual(sorted(row.approver for row in decisions), self.coordinators)

	def test_is_complete_never_passes_an_empty_stage(self):
		"""The guardrail, at the level of the predicate itself."""
		self.assertFalse(routing.is_complete(self.stage(), [], set()))
		self.assertFalse(routing.is_complete(self.stage(), [], {"somebody@example.test"}))


class TestAllOfWithNobodyResolved(ApprovalTestCase):
	"""An `all_of` stage that resolves nobody escalates. It never passes.

	The stage resolves at county level by policy, and this county holds nobody.
	Vacuous truth would approve it — every one of no approvers has approved —
	which is exactly the bug the guardrail names. Instead the stage is entered,
	visibly blocked, and the authority to act moves to the nearest holder above.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.regional = fixtures.make_user("allof_region", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.regional, fixtures.APPROVER_ROLE, cls.kenya["region"])

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(
					1,
					fixtures.LABEL_COUNTY,
					fixtures.APPROVER_ROLE,
					resolution_rule=routing.RULE_AT_LEVEL,
					geo_level=cls.kenya["levels"]["county"],
					completion_rule=routing.COMPLETION_ALL_OF,
				)
			]
		)

	def test_the_stage_resolves_nobody(self):
		stage = config.stages(config.for_doctype(fixtures.APPROVABLE_DOCTYPE))[0]

		self.assertEqual(routing.routed(stage, self.kenya["kihara"]), [])

	def test_it_does_not_approve_itself(self):
		application = self.application("all_of empty", self.kenya["kihara"])
		status = engine.submit(self.reload(application))

		self.assertEqual(status["state"], states.IN_REVIEW)
		self.assertTrue(status["stage"]["is_blocked"])

	def test_it_escalates_instead(self):
		application = self.application("all_of escalates", self.kenya["kihara"])
		status = engine.submit(self.reload(application))

		self.assertEqual(status["approvers"], [self.regional])
		self.assertIn(application, self.queue_of(self.regional))

	def test_and_the_escalation_target_can_actually_finish_it(self):
		"""Escalating to somebody who then cannot act is not an escalation."""
		application = self.application("all_of finish", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.regional):
			status = engine.decide(self.reload(application), states.DECISION_APPROVED)

		self.assertEqual(status["state"], states.APPROVED)


class TestOptionalStageIsSkipped(ApprovalTestCase):
	"""Optional means skipped when nobody resolves — the society said so."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.regional = fixtures.make_user("optional_region", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.regional, fixtures.APPROVER_ROLE, cls.kenya["region"])

		cls.workflow = fixtures.make_workflow(
			[
				fixtures.stage(
					1,
					fixtures.LABEL_COUNTY,
					fixtures.APPROVER_ROLE,
					resolution_rule=routing.RULE_AT_LEVEL,
					geo_level=cls.kenya["levels"]["county"],
					is_optional=1,
					can_reject=0,
				),
				fixtures.stage(2, fixtures.LABEL_REGION, fixtures.APPROVER_ROLE),
			]
		)

	def test_review_starts_at_the_stage_that_resolves(self):
		application = self.application("optional skip", self.kenya["kihara"])
		status = engine.submit(self.reload(application))

		self.assertEqual(status["stage"]["sequence"], 2)
		self.assertEqual(status["approvers"], [self.regional])

	def test_the_skipped_stage_leaves_no_decision_behind(self):
		"""Nothing was decided there, so nothing is recorded there."""
		application = self.application("optional audit", self.kenya["kihara"])
		engine.submit(self.reload(application))

		self.assertEqual(contract.decisions(self.reload(application)), [])
