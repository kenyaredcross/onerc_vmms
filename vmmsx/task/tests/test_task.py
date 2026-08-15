# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The task lifecycle: what each verb moves, and what a second call does not.

Two properties are being asserted throughout, and they are the two the service
was written around:

1. **Every verb is idempotent.** The second identical call observes the work is
   done, returns the same answer with `moved` false, and never reaches the
   thread or the notification. That is what makes the notification exactly-once
   without `direct.py` needing idempotence of its own.
2. **Finishing is not the volunteer's decision alone.** `submit()` reaches
   `submitted` and stops. `sign_off()` is a separate verb on a separate door,
   which is the whole reason `submitted` is a state rather than a flag.
"""

import frappe

from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase
from vmmsx.task.services import states
from vmmsx.task.services import task as task_service


class TestTaskLifecycle(DeploymentTestCase):
	def setUp(self):
		super().setUp()

		self.branch = self.society_a["branch"]
		self.volunteer = fixtures.make_volunteer(fixtures.make_profile(), self.branch).name

	def assign(self, **overrides):
		values = {
			"volunteer": self.volunteer,
			"subject": "Check the warehouse stock",
			"description": "Count what is on the shelves and note anything expired.",
		}
		values.update(overrides)

		return task_service.assign(**values)

	def accepted(self):
		task = self.assign()
		task_service.accept(task)

		return task

	# --- creating ---------------------------------------------------------

	def test_a_new_task_is_assigned_and_stamped(self):
		task = self.assign()

		self.assertEqual(task.status, states.ASSIGNED)
		self.assertIsNotNone(task.assigned_on)
		self.assertEqual(len(task.updates), 1)

	def test_the_anchor_falls_back_to_the_volunteers_branch(self):
		"""ACC-02 without making a coordinator retype what the record already knows."""
		task = self.assign()

		self.assertEqual(task.geo_node, self.branch)

	def test_a_named_anchor_wins_over_the_fallback(self):
		task = self.assign(geo_node=self.society_a["region"])

		self.assertEqual(task.geo_node, self.society_a["region"])

	# --- the volunteer's verbs -------------------------------------------

	def test_accepting_moves_it_once(self):
		task = self.assign()

		first = task_service.accept(task)
		second = task_service.accept(task)

		self.assertTrue(first["moved"])
		self.assertFalse(second["moved"])
		self.assertEqual(task.status, states.ACCEPTED)
		self.assertIsNotNone(task.accepted_on)

	def test_a_question_is_a_flag_and_not_a_state(self):
		"""The distinction `states.py` is explicit about: asking does not move
		the task, so there is no remembered way back to invent."""
		task = self.accepted()

		task_service.ask(task, "Which shelf did you mean?")

		self.assertTrue(task.open_question)
		self.assertEqual(task.status, states.ACCEPTED)

	def test_progress_does_not_offer_the_work_as_done(self):
		task = self.accepted()

		task_service.report_progress(task, "Half of it counted.")

		self.assertEqual(task.status, states.ACCEPTED)

	def test_submitting_stops_short_of_completed(self):
		task = self.accepted()

		task_service.submit(task, note="All counted.")

		self.assertEqual(task.status, states.SUBMITTED)
		self.assertIsNotNone(task.submitted_on)
		self.assertEqual(task.completion_notes, "All counted.")

	def test_submitting_from_assigned_is_refused_by_the_table(self):
		"""`assigned` has no edge to `submitted`, so the verb declines to move it
		rather than skipping the acceptance."""
		task = self.assign()

		outcome = task_service.submit(task)

		self.assertFalse(outcome["moved"])
		self.assertEqual(task.status, states.ASSIGNED)

	def test_proof_lands_on_the_thread_entry(self):
		task = self.accepted()

		task_service.submit(task, note="Done.", proof="/files/shelf.jpg")

		self.assertEqual(task.updates[-1].proof, "/files/shelf.jpg")

	# --- the coordinator's verbs -----------------------------------------

	def test_answering_clears_the_flag(self):
		task = self.accepted()
		task_service.ask(task, "Which shelf?")

		task_service.answer(task, "The one by the door.")

		self.assertFalse(task.open_question)

	def test_signing_off_completes_it_once(self):
		task = self.accepted()
		task_service.submit(task)

		first = task_service.sign_off(task)
		second = task_service.sign_off(task)

		self.assertTrue(first["moved"])
		self.assertFalse(second["moved"])
		self.assertEqual(task.status, states.COMPLETED)
		self.assertIsNotNone(task.closed_on)

	def test_signing_off_unsubmitted_work_is_refused(self):
		task = self.accepted()

		outcome = task_service.sign_off(task)

		self.assertFalse(outcome["moved"])
		self.assertEqual(task.status, states.ACCEPTED)

	def test_sending_back_returns_it_and_clears_the_submission(self):
		task = self.accepted()
		task_service.submit(task)

		task_service.send_back(task, "The expiry dates are missing.")

		self.assertEqual(task.status, states.ACCEPTED)
		self.assertIsNone(task.submitted_on)

	def test_a_returned_task_can_be_submitted_again(self):
		task = self.accepted()
		task_service.submit(task)
		task_service.send_back(task, "Not yet.")

		outcome = task_service.submit(task, note="Now with dates.")

		self.assertTrue(outcome["moved"])
		self.assertEqual(task.status, states.SUBMITTED)

	def test_cancelling_is_available_from_submitted(self):
		"""Work overtaken by events still has to be closable, and the honest
		close is a cancellation rather than approving what is no longer wanted."""
		task = self.accepted()
		task_service.submit(task)

		outcome = task_service.cancel(task, "The warehouse was closed.")

		self.assertTrue(outcome["moved"])
		self.assertEqual(task.status, states.CANCELLED)

	# --- closed is closed -------------------------------------------------

	def test_nothing_can_be_added_to_a_finished_task(self):
		task = self.accepted()
		task_service.submit(task)
		task_service.sign_off(task)

		with self.assertRaises(frappe.ValidationError):
			task_service.ask(task, "One more thing?")

	def test_a_completed_task_cannot_be_reopened(self):
		task = self.accepted()
		task_service.submit(task)
		task_service.sign_off(task)

		self.assertFalse(task_service.send_back(task, "Actually no.")["moved"])
		self.assertEqual(task.status, states.COMPLETED)

	# --- the schema's own guard ------------------------------------------

	def test_a_status_outside_the_closed_set_is_refused(self):
		"""The controller's second line of defence, for a script or a bulk edit
		that never went through the service."""
		task = self.assign()
		task.status = "nearly done"

		with self.assertRaises(frappe.ValidationError):
			task.save()
