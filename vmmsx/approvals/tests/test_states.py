# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The state machine is closed, and the transition table is the whole grammar."""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.approvals import states

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestStateSet(IntegrationTestCase):
	def test_the_seven_states(self):
		self.assertEqual(
			set(states.STATES),
			{"Draft", "Submitted", "In Review", "Approved", "Rejected", "Withdrawn", "Expired"},
		)

	def test_open_and_terminal_partition_the_set(self):
		"""Every state is one or the other, and none is both."""
		self.assertEqual(set(states.OPEN_STATES) | set(states.TERMINAL_STATES), set(states.STATES))
		self.assertEqual(set(states.OPEN_STATES) & set(states.TERMINAL_STATES), set())

	def test_every_state_appears_in_the_transition_table(self):
		"""A state with no entry would be a hole nothing could leave."""
		self.assertEqual(set(states.TRANSITIONS), set(states.STATES))

	def test_every_target_is_a_real_state(self):
		for source, targets in states.TRANSITIONS.items():
			for target in targets:
				self.assertIn(target, states.STATES, f"{source} → {target} is not a state")

	def test_terminal_states_go_nowhere(self):
		for state in states.TERMINAL_STATES:
			self.assertEqual(states.TRANSITIONS[state], (), f"{state} is terminal but has transitions")


class TestTransitions(IntegrationTestCase):
	def test_the_ordinary_path(self):
		self.assertTrue(states.can_transition(states.DRAFT, states.SUBMITTED))
		self.assertTrue(states.can_transition(states.SUBMITTED, states.IN_REVIEW))
		self.assertTrue(states.can_transition(states.IN_REVIEW, states.APPROVED))

	def test_stage_advance_is_a_real_transition(self):
		"""In Review to In Review: the state holds, the stage moves."""
		self.assertTrue(states.can_transition(states.IN_REVIEW, states.IN_REVIEW))

	def test_more_information_returns_to_the_applicant(self):
		self.assertTrue(states.can_transition(states.IN_REVIEW, states.DRAFT))

	def test_a_draft_cannot_be_approved_without_review(self):
		self.assertFalse(states.can_transition(states.DRAFT, states.APPROVED))
		self.assertFalse(states.can_transition(states.DRAFT, states.REJECTED))

	def test_a_submitted_application_cannot_be_rejected_before_a_stage(self):
		"""A rejection is a decision, and a decision happens at a stage."""
		self.assertFalse(states.can_transition(states.SUBMITTED, states.REJECTED))

	def test_a_decided_application_cannot_be_reopened(self):
		for state in states.TERMINAL_STATES:
			for target in states.STATES:
				self.assertFalse(states.can_transition(state, target), f"{state} → {target}")

	def test_an_unset_state_counts_as_draft(self):
		self.assertTrue(states.can_transition(None, states.SUBMITTED))
		self.assertFalse(states.can_transition(None, states.APPROVED))

	def test_assert_transition_names_the_illegal_move(self):
		with self.assertRaises(frappe.ValidationError):
			states.assert_transition(states.DRAFT, states.APPROVED)

	def test_assert_transition_rejects_an_invented_state(self):
		with self.assertRaises(frappe.ValidationError):
			states.assert_transition(states.DRAFT, "Pending Review Maybe")

	def test_assert_transition_permits_the_legal_move(self):
		# No exception is the assertion.
		states.assert_transition(states.IN_REVIEW, states.REJECTED)


class TestDecisions(IntegrationTestCase):
	def test_the_three_decisions(self):
		self.assertEqual(set(states.DECISIONS), {"Approved", "Rejected", "More info requested"})

	def test_an_invented_decision_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			states.assert_decision("Approved with conditions")

	def test_a_real_decision_passes(self):
		for decision in states.DECISIONS:
			states.assert_decision(decision)
