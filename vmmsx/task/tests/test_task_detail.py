# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Everything a task grew when one line of subject stopped being enough.

The lifecycle suite next door is about the verbs. This one is about the five
things a coordinator and a volunteer actually need a task to carry, and about
the one property they all share: **three things gate a task and nothing else
does.**

    a required checklist item that is not ticked   stops a submission
    an unfinished dependency                       stops a start, unless overridden
    the state table                                stops everything it does not contain

Not a missing expected-hours figure, not an unanswered response deadline, not an
empty briefing-file list. A field nobody filled in is a record-keeping gap, and
turning one into a refusal is how a gap becomes an operational failure — the
same argument `deployment/services/assignment.py` makes about readiness.

The other four:

* **Declining is not cancelling.** A volunteer saying no before starting and a
  coordinator calling work off are different facts, and only one of them is
  worth chasing.
* **Reassignment keeps both records.** The original is never overwritten.
* **The place is inherited, not copied.** Forty tasks under one deployment happen
  in the same place, and copying the address forty times means forty rows to
  correct when the meeting point moves.
* **Overdue is derived.** A stored flag is right until the clock moves.
"""

import frappe
from frappe.utils import add_days, add_to_date, now_datetime, today

from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase
from vmmsx.task.services import states
from vmmsx.task.services import task as task_service

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TaskDetailTestCase(DeploymentTestCase):
	def setUp(self):
		super().setUp()

		self.branch = self.society_a["branch"]
		self.volunteer = fixtures.make_volunteer(fixtures.make_profile(), self.branch).name

	def another_volunteer(self):
		return fixtures.make_volunteer(
			fixtures.make_profile("Other", frappe.generate_hash(length=6)), self.branch
		).name

	def assign(self, **overrides):
		values = {
			"volunteer": self.volunteer,
			"subject": "Check the warehouse stock",
			"description": "Count what is on the shelves and note anything expired.",
		}
		values.update(overrides)

		return task_service.assign(**values)

	def accepted(self, **overrides):
		task = self.assign(**overrides)
		task_service.accept(task)

		return task


class TestTheDeadlineHasOneSourceOfTruth(TaskDetailTestCase):
	def test_a_day_alone_fills_in_the_datetime(self):
		"""Every task written before the datetime existed, and every caller that
		still speaks in days."""
		task = self.assign(due_on=add_days(today(), 3))

		self.assertTrue(task.due_at)
		self.assertIn("23:59:59", str(task.due_at))

	def test_the_datetime_decides_the_day(self):
		task = self.assign(due_at=f"{add_days(today(), 5)} 09:00:00")

		self.assertEqual(str(task.due_on), add_days(today(), 5))

	def test_the_two_cannot_disagree(self):
		task = self.assign(due_at=f"{add_days(today(), 5)} 09:00:00")
		task.due_on = add_days(today(), 99)
		task.save(ignore_permissions=True)

		self.assertEqual(str(task.due_on), add_days(today(), 5))

	def test_overdue_is_derived_rather_than_stored(self):
		task = self.assign(due_at=f"{add_days(today(), -1)} 09:00:00")

		self.assertTrue(task_service.is_overdue(task))

	def test_a_task_that_is_finished_is_not_overdue(self):
		"""Overdue is about work still owed. A cancelled task owes nothing."""
		task = self.assign(due_at=f"{add_days(today(), -1)} 09:00:00")
		task_service.cancel(task, "No longer needed.")

		self.assertFalse(task_service.is_overdue(task))

	def test_a_task_with_no_deadline_is_never_overdue(self):
		self.assertFalse(task_service.is_overdue(self.assign()))


class TestTheChecklistIsTheOneGateOnSubmission(TaskDetailTestCase):
	def checklist_task(self):
		return self.accepted(
			checklist=[
				{"item": "Count the shelves", "is_required": 1},
				{"item": "Photograph anything expired", "is_required": 0},
			]
		)

	def test_the_items_are_written_as_given(self):
		task = self.checklist_task()

		self.assertEqual(len(task.checklist), 2)
		self.assertTrue(task.checklist[0].is_required)

	def test_a_required_item_that_is_not_done_stops_the_submission(self):
		task = self.checklist_task()

		with self.assertRaises(frappe.MandatoryError):
			task_service.submit(task, "Finished.")

	def test_the_refusal_names_what_is_left(self):
		task = self.checklist_task()

		self.assertEqual(task_service.checklist_outstanding(task), ["Count the shelves"])

	def test_an_optional_item_stops_nothing(self):
		task = self.checklist_task()
		task_service.tick(task, index=1)

		self.assertEqual(task_service.submit(task, "Finished.")["status"], states.SUBMITTED)

	def test_ticking_stamps_when_it_was_done(self):
		task = self.checklist_task()
		task_service.tick(task, index=1)

		self.assertTrue(task.checklist[0].is_done)
		self.assertTrue(task.checklist[0].done_on)

	def test_unticking_clears_the_stamp(self):
		"""A time left behind on an unticked row says the item was done and then
		untouched."""
		task = self.checklist_task()
		task_service.tick(task, index=1)
		task_service.tick(task, index=1, done=False)

		self.assertFalse(task.checklist[0].is_done)
		self.assertIsNone(task.checklist[0].done_on)

	def test_an_item_that_is_not_there_is_refused(self):
		task = self.checklist_task()

		with self.assertRaises(frappe.ValidationError):
			task_service.tick(task, index=99)

	def test_a_caller_cannot_pre_tick_an_item_when_setting_the_work(self):
		"""`is_done` is the volunteer's to set, not the person setting the work."""
		task = self.assign(checklist=[{"item": "Count the shelves", "is_done": 1}])

		self.assertFalse(task.checklist[0].is_done)


class TestWhatHasToHappenFirst(TaskDetailTestCase):
	def test_a_task_with_an_unfinished_prerequisite_cannot_be_started(self):
		first = self.assign(subject="Collect the keys")
		second = self.assign(subject="Open the store", depends_on=[{"depends_on": first.name}])

		with self.assertRaises(frappe.ValidationError):
			task_service.accept(second)

	def test_once_the_prerequisite_is_finished_it_can(self):
		first = self.assign(subject="Collect the keys")
		task_service.accept(first)
		task_service.submit(first)
		task_service.sign_off(first)

		second = self.assign(subject="Open the store", depends_on=[{"depends_on": first.name}])

		self.assertEqual(task_service.accept(second)["status"], states.ACCEPTED)

	def test_a_cancelled_prerequisite_counts_as_finished(self):
		"""Work that was called off is never going to complete, and treating it as
		outstanding would block the next task for ever."""
		first = self.assign(subject="Collect the keys")
		task_service.cancel(first, "Not needed.")

		second = self.assign(subject="Open the store", depends_on=[{"depends_on": first.name}])

		self.assertEqual(task_service.accept(second)["status"], states.ACCEPTED)

	def test_a_manager_may_override_it_in_writing(self):
		first = self.assign(subject="Collect the keys")
		second = self.assign(
			subject="Open the store",
			depends_on=[{"depends_on": first.name}],
			blocked_override_reason="The keys were handed over in person this morning.",
		)

		self.assertEqual(task_service.accept(second)["status"], states.ACCEPTED)

	def test_a_task_cannot_wait_on_itself(self):
		task = self.assign()
		task.append("depends_on", {"depends_on": task.name})

		with self.assertRaises(frappe.ValidationError):
			task.save(ignore_permissions=True)

	def test_a_loop_of_two_is_refused(self):
		first = self.assign(subject="One")
		second = self.assign(subject="Two", depends_on=[{"depends_on": first.name}])

		first.append("depends_on", {"depends_on": second.name})

		with self.assertRaises(frappe.ValidationError):
			first.save(ignore_permissions=True)

	def test_a_longer_loop_is_refused_too(self):
		"""The walk follows each prerequisite's own prerequisites, so a chain
		three deep is caught by the same rule."""
		first = self.assign(subject="One")
		second = self.assign(subject="Two", depends_on=[{"depends_on": first.name}])
		third = self.assign(subject="Three", depends_on=[{"depends_on": second.name}])

		first.append("depends_on", {"depends_on": third.name})

		with self.assertRaises(frappe.ValidationError):
			first.save(ignore_permissions=True)

	def test_an_ordinary_chain_is_not_a_loop(self):
		first = self.assign(subject="One")
		second = self.assign(subject="Two", depends_on=[{"depends_on": first.name}])
		third = self.assign(subject="Three", depends_on=[{"depends_on": second.name}])

		self.assertTrue(third.name)


class TestDecliningIsNotCancelling(TaskDetailTestCase):
	def test_a_volunteer_may_say_no_before_starting(self):
		task = self.assign()
		answer = task_service.decline(task, "I am away that week.")

		self.assertEqual(answer["status"], states.DECLINED)
		self.assertEqual(task.decline_reason, "I am away that week.")

	def test_a_decline_needs_a_reason(self):
		task = self.assign()

		with self.assertRaises(frappe.MandatoryError):
			task_service.decline(task, "")

	def test_somebody_who_accepted_cannot_decline(self):
		"""They have stopped, not declined, and that belongs in front of the
		coordinator."""
		task = self.accepted()

		self.assertFalse(task_service.decline(task, "Changed my mind.")["moved"])
		self.assertEqual(task.status, states.ACCEPTED)

	def test_a_declined_task_is_finished_with(self):
		task = self.assign()
		task_service.decline(task, "I am away that week.")

		self.assertFalse(states.is_open(task.status))
		self.assertTrue(task.closed_on)

	def test_declining_twice_changes_nothing(self):
		task = self.assign()
		task_service.decline(task, "I am away that week.")

		self.assertFalse(task_service.decline(task, "Still away.")["moved"])


class TestReassignmentKeepsBothRecords(TaskDetailTestCase):
	def test_the_original_is_kept_and_points_forward(self):
		task = self.assign()
		answer = task_service.reassign(task, self.another_volunteer(), "Called to another branch.")

		self.assertEqual(task.status, states.REASSIGNED)
		self.assertEqual(task.reassigned_to_task, answer["replacement"])

	def test_and_the_replacement_points_back(self):
		task = self.assign()
		answer = task_service.reassign(task, self.another_volunteer(), "Called to another branch.")
		replacement = frappe.get_doc("VMMS Task", answer["replacement"])

		self.assertEqual(replacement.reassigned_from_task, task.name)
		self.assertEqual(replacement.reassignment_reason, "Called to another branch.")

	def test_the_original_volunteer_is_never_overwritten(self):
		task = self.assign()
		was = task.volunteer

		task_service.reassign(task, self.another_volunteer(), "Called away.")
		task.reload()

		self.assertEqual(task.volunteer, was)

	def test_the_brief_and_the_checklist_come_across(self):
		task = self.assign(checklist=[{"item": "Count the shelves", "is_required": 1}])
		answer = task_service.reassign(task, self.another_volunteer(), "Called away.")
		replacement = frappe.get_doc("VMMS Task", answer["replacement"])

		self.assertEqual(replacement.description, task.description)
		self.assertEqual(len(replacement.checklist), 1)

	def test_the_conversation_does_not(self):
		"""None of it is the new person's, and presenting it as theirs would be
		false."""
		task = self.accepted()
		task_service.report_progress(task, "Half done.")

		answer = task_service.reassign(task, self.another_volunteer(), "Called away.")
		replacement = frappe.get_doc("VMMS Task", answer["replacement"])

		self.assertEqual(len(replacement.updates), 1)

	def test_a_reassignment_needs_a_reason(self):
		task = self.assign()

		with self.assertRaises(frappe.MandatoryError):
			task_service.reassign(task, self.another_volunteer(), "")

	def test_a_finished_task_cannot_be_reassigned(self):
		task = self.assign()
		task_service.cancel(task, "Not needed.")

		self.assertFalse(
			task_service.reassign(task, self.another_volunteer(), "Too late.")["moved"]
		)


class TestWhereTheWorkIs(TaskDetailTestCase):
	def deployment(self, **overrides):
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")

		return fixtures.make_deployment(terms.name, self.branch, **overrides)

	def test_a_standalone_task_carries_its_own_place(self):
		task = self.assign(work_name="The district store", work_address="Behind the market")

		where = task_service.where_dto(task)

		self.assertEqual(where["work"]["name"], "The district store")
		self.assertIsNone(where["inherited_from"])

	def test_a_deployment_task_inherits_the_deployments_place(self):
		"""Copying the address onto forty tasks means forty rows to correct when
		the meeting point moves."""
		deployment = self.deployment(
			site_name="Kigamboni reception centre", meeting_point="Branch office car park"
		)
		task = self.assign(deployment=deployment.name)

		where = task_service.where_dto(task)

		self.assertEqual(where["work"]["name"], "Kigamboni reception centre")
		self.assertEqual(where["meeting_point"]["name"], "Branch office car park")
		self.assertEqual(where["inherited_from"], deployment.name)

	def test_a_task_may_override_one_place_and_inherit_the_other(self):
		deployment = self.deployment(
			site_name="Kigamboni reception centre", meeting_point="Branch office car park"
		)
		task = self.assign(deployment=deployment.name, meeting_name="The ward office")

		where = task_service.where_dto(task)

		self.assertEqual(where["work"]["name"], "Kigamboni reception centre")
		self.assertEqual(where["meeting_point"]["name"], "The ward office")

	def test_a_place_with_a_point_gets_a_map_link(self):
		task = self.assign(work_name="The district store", work_latitude=-6.79, work_longitude=39.2)

		self.assertIn("openstreetmap.org", task_service.where_dto(task)["work"]["map"])

	def test_travel_instructions_are_inherited_too(self):
		deployment = self.deployment(travel_notes="The last two kilometres are unpaved.")
		task = self.assign(deployment=deployment.name)

		self.assertEqual(
			task_service.where_dto(task)["travel_instructions"],
			"The last two kilometres are unpaved.",
		)


class TestChasingOverdueWork(TaskDetailTestCase):
	def overdue(self, **overrides):
		values = {"due_at": f"{add_days(today(), -3)} 09:00:00", "reminder_every_days": 2}
		values.update(overrides)

		return self.accepted(**values)

	def test_a_task_with_no_reminder_interval_is_never_chased(self):
		"""The shipped state. Reminders nobody asked for are how a system trains
		people to ignore it."""
		self.overdue(reminder_every_days=0)

		self.assertEqual(task_service.chase_overdue()["reminded"], [])

	def test_an_overdue_task_with_an_interval_is_nudged(self):
		task = self.overdue()

		self.assertIn(task.name, task_service.chase_overdue()["reminded"])

	def test_and_the_nudge_is_recorded_so_it_does_not_repeat(self):
		task = self.overdue()
		task_service.chase_overdue()

		self.assertTrue(frappe.db.get_value("VMMS Task", task.name, "last_contacted_on"))
		self.assertEqual(task_service.chase_overdue()["reminded"], [])

	def test_a_task_that_is_not_yet_due_is_left_alone(self):
		self.accepted(due_at=f"{add_days(today(), 3)} 09:00:00", reminder_every_days=2)

		self.assertEqual(task_service.chase_overdue()["reminded"], [])

	def test_a_second_interval_without_progress_escalates(self):
		task = self.overdue(escalate_to="Administrator")
		task_service.chase_overdue()
		frappe.db.set_value(
			"VMMS Task", task.name, "last_contacted_on",
			add_to_date(now_datetime(), days=-9), update_modified=False,
		)

		self.assertIn(task.name, task_service.chase_overdue()["escalated"])

	def test_an_escalation_with_nobody_named_does_nothing(self):
		task = self.overdue()

		self.assertFalse(task_service.escalate(task)["moved"])
		self.assertEqual(len(task.escalations or []), 0)

	def test_an_escalation_is_written_into_the_record(self):
		task = self.overdue(escalate_to="Administrator")
		task_service.escalate(task, "Nobody has answered.")

		self.assertEqual(len(task.escalations), 1)
		self.assertEqual(task.escalations[0].escalated_to, "Administrator")


class TestHowItEnds(TaskDetailTestCase):
	def submitted(self, **overrides):
		task = self.accepted(**overrides)
		task_service.submit(task, "Done.")

		return task

	def test_submitting_says_the_work_is_finished(self):
		task = self.submitted()

		self.assertEqual(task.percent_complete, 100)

	def test_the_volunteers_own_hours_and_evidence_are_recorded(self):
		task = self.accepted()
		task_service.submit(task, "Done.", hours=3.5, evidence="/files/count.pdf")

		self.assertEqual(task.actual_hours, 3.5)
		self.assertEqual(task.final_evidence, "/files/count.pdf")

	def test_progress_is_the_volunteers_own_estimate(self):
		task = self.accepted()
		task_service.report_progress(task, "Half the shelves done.", percent=50)

		self.assertEqual(task.percent_complete, 50)

	def test_sending_work_back_keeps_the_reason_and_counts_it(self):
		task = self.submitted()
		task_service.send_back(task, "The expiry dates are missing.")

		self.assertEqual(task.return_reason, "The expiry dates are missing.")
		self.assertEqual(task.rework_count, 1)

	def test_the_reason_survives_the_resubmission(self):
		"""The volunteer is being asked to fix something and has to be able to
		re-read what."""
		task = self.submitted()
		task_service.send_back(task, "The expiry dates are missing.")
		task_service.submit(task, "Fixed.")

		self.assertEqual(task.return_reason, "The expiry dates are missing.")

	def test_signing_off_records_the_outcome_and_waits_for_nothing(self):
		task = self.submitted()
		task_service.sign_off(task, "Good work.", outcome="Stock counted, four items expired.")

		self.assertEqual(task.status, states.COMPLETED)
		self.assertEqual(task.outcome, "Stock counted, four items expired.")
		# A `Rating` reads back as zero rather than as nothing, which is Frappe's
		# own answer for "nobody rated this" and the one a screen renders as an
		# empty row of stars.
		self.assertFalse(task.manager_rating)

	def test_a_rating_and_lessons_are_kept_where_somebody_gave_them(self):
		task = self.submitted()
		task_service.sign_off(task, outcome="Done.", rating=1, lessons="Two counters next time.")

		self.assertEqual(task.manager_rating, 1)
		self.assertEqual(task.lessons_learned, "Two counters next time.")
