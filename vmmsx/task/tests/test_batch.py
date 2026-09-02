# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Asking forty people to do the same thing, and being honest about what happened.

A batch is an **administrative grouping, not a shared task**. Everything below
follows from that, and from one fact the design is shaped around: generating
forty tasks will not produce forty tasks.

    one bad row never blocks a good one     each person is written in their own savepoint
    every row records what happened          Created, Existing, Skipped or Failed, with a reason
    a retry resolves only what is unresolved and never duplicates
    editing a batch afterwards changes nothing that was already sent
    the counts are derived, never stored

The last two are the ones that would be easy to get wrong in a way nobody
noticed for months: a coordinator tidying a typo silently rewriting work forty
people had read, and a stored counter drifting the moment somebody signs a task
off from its own page.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase
from vmmsx.task.services import batch as batch_service
from vmmsx.task.services import states
from vmmsx.task.services import task as task_service

EXTRA_TEST_RECORD_DEPENDENCIES = []

BATCH_DOCTYPE = "VMMS Task Batch"
TASK_DOCTYPE = "VMMS Task"


class BatchTestCase(DeploymentTestCase):
	def setUp(self):
		super().setUp()

		self.branch = self.society_a["branch"]

	def volunteer(self, handle: str | None = None):
		return fixtures.make_volunteer(
			fixtures.make_profile("Batch", handle or frappe.generate_hash(length=6)), self.branch
		).name

	def gone_volunteer(self) -> str:
		"""A volunteer who was on the list and is not on the register any more.

		Force-deleted, which is how it actually happens: `seed/purge.py` does it
		when a site changes hands, and a partially restored backup does it by
		accident. The row on the batch survives its subject, which is exactly the
		case `_verdict`'s existence check is for.
		"""
		name = self.volunteer()
		frappe.delete_doc(fixtures.VOLUNTEER_DOCTYPE, name, force=True, ignore_permissions=True)

		return name

	def make_batch(self, volunteers=None, **overrides):
		values = {
			"doctype": BATCH_DOCTYPE,
			"subject": "Household survey, Kigamboni",
			"brief": "Visit every household on your list and record what you find.",
			"geo_node": self.branch,
			"volunteers": [{"volunteer": name} for name in (volunteers or [])],
		}
		values.update(overrides)

		return frappe.get_doc(values).insert()


class TestABatchIsAGroupingRatherThanATask(BatchTestCase):
	def test_creating_one_generates_nothing(self):
		"""Drawing up the list and sending the work are two acts."""
		batch = self.make_batch([self.volunteer(), self.volunteer()])

		self.assertIsNone(batch.generated_on)
		self.assertEqual(frappe.db.count(TASK_DOCTYPE, {"batch": batch.name}), 0)

	def test_generating_makes_one_ordinary_task_per_person(self):
		batch = self.make_batch([self.volunteer(), self.volunteer()])
		answer = batch_service.generate(batch)

		self.assertEqual(answer["created"], 2)
		self.assertEqual(frappe.db.count(TASK_DOCTYPE, {"batch": batch.name}), 2)

	def test_each_task_carries_the_brief_rather_than_pointing_at_it(self):
		batch = self.make_batch([self.volunteer()])
		batch_service.generate(batch)

		task = frappe.get_doc(TASK_DOCTYPE, batch.volunteers[0].task)

		self.assertEqual(task.description, batch.brief)
		self.assertEqual(task.subject, batch.subject)
		self.assertEqual(task.batch, batch.name)

	def test_the_schedule_and_the_kind_of_work_come_across(self):
		batch = self.make_batch(
			[self.volunteer()], due_at=f"{add_days(today(), 7)} 17:00:00", priority="High"
		)
		batch_service.generate(batch)

		task = frappe.get_doc(TASK_DOCTYPE, batch.volunteers[0].task)

		self.assertEqual(task.priority, "High")
		self.assertEqual(str(task.due_on), add_days(today(), 7))

	def test_a_batch_with_nobody_on_it_is_refused(self):
		batch = self.make_batch([])

		with self.assertRaises(frappe.MandatoryError):
			batch_service.generate(batch)


class TestOneBadRowNeverBlocksAGoodOne(BatchTestCase):
	def test_a_row_naming_a_volunteer_that_is_gone_is_skipped(self):
		good = self.volunteer()
		batch = self.make_batch([good])
		batch.append("volunteers", {"volunteer": self.volunteer()})
		batch.save()
		frappe.delete_doc(
			fixtures.VOLUNTEER_DOCTYPE, batch.volunteers[1].volunteer, force=True,
			ignore_permissions=True,
		)

		answer = batch_service.generate(batch)

		self.assertEqual(answer["created"], 1)
		self.assertEqual(answer["skipped"], 1)

	def test_and_the_good_one_still_has_its_task(self):
		good = self.volunteer()
		batch = self.make_batch([good])
		batch.append("volunteers", {"volunteer": self.volunteer()})
		batch.save()
		frappe.delete_doc(
			fixtures.VOLUNTEER_DOCTYPE, batch.volunteers[1].volunteer, force=True,
			ignore_permissions=True,
		)
		batch_service.generate(batch)

		self.assertTrue(frappe.db.exists(TASK_DOCTYPE, {"batch": batch.name, "volunteer": good}))

	def test_every_row_says_what_happened(self):
		batch = self.make_batch([self.volunteer()])
		batch.append("volunteers", {"volunteer": self.volunteer()})
		batch.save()
		frappe.delete_doc(
			fixtures.VOLUNTEER_DOCTYPE, batch.volunteers[1].volunteer, force=True,
			ignore_permissions=True,
		)

		rows = batch_service.generate(batch)["rows"]

		self.assertEqual(rows[0]["result"], batch_service.RESULT_CREATED)
		self.assertEqual(rows[1]["result"], batch_service.RESULT_SKIPPED)
		self.assertTrue(rows[1]["reason"])

	def test_the_unresolved_rows_are_named_rather_than_counted(self):
		"""'37 of 40' with no list is a report nobody can act on."""
		batch = self.make_batch([self.volunteer()])
		batch.append("volunteers", {"volunteer": self.volunteer()})
		batch.save()
		frappe.delete_doc(
			fixtures.VOLUNTEER_DOCTYPE, batch.volunteers[1].volunteer, force=True,
			ignore_permissions=True,
		)

		answer = batch_service.generate(batch)

		self.assertEqual(len(answer["unresolved"]), 1)
		self.assertEqual(answer["unresolved"][0]["volunteer"], batch.volunteers[1].volunteer)


class TestARetryResolvesOnlyWhatIsUnresolved(BatchTestCase):
	def test_running_it_twice_creates_nothing_the_second_time(self):
		batch = self.make_batch([self.volunteer(), self.volunteer()])
		batch_service.generate(batch)

		before = frappe.db.count(TASK_DOCTYPE, {"batch": batch.name})
		batch_service.generate(batch)

		self.assertEqual(frappe.db.count(TASK_DOCTYPE, {"batch": batch.name}), before)

	def test_somebody_added_afterwards_gets_theirs_on_the_next_run(self):
		"""Adding people and generating again is how a batch is meant to grow."""
		batch = self.make_batch([self.volunteer()])
		batch_service.generate(batch)

		latecomer = self.volunteer()
		batch.append("volunteers", {"volunteer": latecomer})
		batch.save()
		batch_service.generate(batch)

		self.assertTrue(
			frappe.db.exists(TASK_DOCTYPE, {"batch": batch.name, "volunteer": latecomer})
		)

	def test_a_person_who_already_has_one_is_reported_as_existing(self):
		volunteer = self.volunteer()
		batch = self.make_batch([volunteer])
		batch_service.generate(batch)

		# The row is cleared the way a coordinator clearing a stuck report would,
		# so the run has to reach the duplicate guard rather than the shortcut.
		batch.volunteers[0].result = None
		batch.save()

		answer = batch_service.generate(batch)

		self.assertEqual(answer["existing"], 1)
		self.assertEqual(frappe.db.count(TASK_DOCTYPE, {"batch": batch.name}), 1)

	def test_a_declined_task_does_not_get_a_second_one(self):
		"""Generating again would be the batch asking on its own initiative."""
		volunteer = self.volunteer()
		batch = self.make_batch([volunteer])
		batch_service.generate(batch)

		task = frappe.get_doc(TASK_DOCTYPE, batch.volunteers[0].task)
		task_service.decline(task, "I am away that week.")

		batch.volunteers[0].result = None
		batch.save()
		batch_service.generate(batch)

		self.assertEqual(frappe.db.count(TASK_DOCTYPE, {"batch": batch.name}), 1)


class TestThePreviewAgreesWithTheRun(BatchTestCase):
	def test_it_says_who_would_get_one(self):
		batch = self.make_batch([self.volunteer(), self.volunteer()])
		answer = batch_service.preview(batch)

		self.assertEqual(answer["would_create"], 2)
		self.assertEqual(answer["selected"], 2)

	def test_it_writes_nothing(self):
		batch = self.make_batch([self.volunteer()])
		batch_service.preview(batch)

		self.assertEqual(frappe.db.count(TASK_DOCTYPE, {"batch": batch.name}), 0)
		self.assertIsNone(batch.generated_on)

	def test_it_reaches_the_same_verdict_the_run_does(self):
		batch = self.make_batch([self.volunteer()])
		batch.append("volunteers", {"volunteer": self.volunteer()})
		batch.save()
		frappe.delete_doc(
			fixtures.VOLUNTEER_DOCTYPE, batch.volunteers[1].volunteer, force=True,
			ignore_permissions=True,
		)

		preview = batch_service.preview(batch)
		run = batch_service.generate(batch)

		self.assertEqual(
			[row["would"] for row in preview["rows"]], [row["result"] for row in run["rows"]]
		)


class TestAGeneratedBatchIsFrozen(BatchTestCase):
	def test_the_brief_cannot_be_rewritten_afterwards(self):
		"""Forty people have read it."""
		batch = self.make_batch([self.volunteer()])
		batch_service.generate(batch)

		batch.brief = "Actually, visit only the households on the east side."

		with self.assertRaises(frappe.ValidationError):
			batch.save()

	def test_nor_can_the_subject_or_the_anchor(self):
		batch = self.make_batch([self.volunteer()])
		batch_service.generate(batch)

		batch.subject = "Something else"

		with self.assertRaises(frappe.ValidationError):
			batch.save()

	def test_but_people_may_still_be_added(self):
		batch = self.make_batch([self.volunteer()])
		batch_service.generate(batch)

		batch.append("volunteers", {"volunteer": self.volunteer()})
		batch.save()

		self.assertEqual(len(batch.volunteers), 2)

	def test_before_generation_everything_is_editable(self):
		batch = self.make_batch([self.volunteer()])
		batch.brief = "A better brief."
		batch.save()

		self.assertEqual(batch.brief, "A better brief.")

	def test_editing_the_batch_never_reaches_the_tasks(self):
		batch = self.make_batch([self.volunteer()])
		batch_service.generate(batch)
		task = frappe.get_doc(TASK_DOCTYPE, batch.volunteers[0].task)

		batch.notes = "Chased the ward office about access."
		batch.save()
		task.reload()

		self.assertEqual(task.description, "Visit every household on your list and record what you find.")


class TestTheCountsAreDerived(BatchTestCase):
	def generated(self, how_many: int = 3):
		batch = self.make_batch([self.volunteer() for _ in range(how_many)])
		batch_service.generate(batch)

		return batch

	def test_a_fresh_batch_is_all_assigned(self):
		batch = self.generated()
		counts = batch_service.counts(batch)

		self.assertEqual(counts["created"], 3)
		self.assertEqual(counts["not_responded"], 3)
		self.assertEqual(counts["in_progress"], 0)

	def test_accepting_one_moves_it_to_in_progress(self):
		batch = self.generated()
		task_service.accept(frappe.get_doc(TASK_DOCTYPE, batch.volunteers[0].task))

		counts = batch_service.counts(batch)

		self.assertEqual(counts["in_progress"], 1)
		self.assertEqual(counts["not_responded"], 2)

	def test_the_counts_follow_the_tasks_rather_than_the_batch(self):
		"""Signed off from the task's own page, which never touches the batch."""
		batch = self.generated(1)
		task = frappe.get_doc(TASK_DOCTYPE, batch.volunteers[0].task)
		task_service.accept(task)
		task_service.submit(task)
		task_service.sign_off(task)

		self.assertEqual(batch_service.counts(batch)[states.COMPLETED], 1)

	def test_overdue_is_counted_from_the_tasks_own_deadline(self):
		batch = self.make_batch(
			[self.volunteer()], due_at=f"{add_days(today(), -2)} 09:00:00"
		)
		batch_service.generate(batch)

		self.assertEqual(batch_service.counts(batch)["overdue"], 1)

	def test_a_row_that_cannot_be_written_is_recorded_as_failed(self):
		"""The branch for the reason nobody predicted. Here it is a deployment
		that was purged after the list was drawn up, which is a real way for a
		batch to be half-valid by the time somebody presses the button.
		"""
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")
		deployment = fixtures.make_deployment(terms.name, self.branch)
		batch = self.make_batch([self.volunteer()], deployment=deployment.name)
		frappe.delete_doc(
			fixtures.DEPLOYMENT_DOCTYPE, deployment.name, force=True, ignore_permissions=True
		)

		answer = batch_service.generate(batch)

		self.assertEqual(answer["failed"], 1)
		self.assertTrue(answer["rows"][0]["reason"])

	def test_a_failed_row_is_tried_again_on_the_next_run(self):
		"""Unlike a created one. That is the whole difference between a retry and
		a second run."""
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")
		deployment = fixtures.make_deployment(terms.name, self.branch)
		batch = self.make_batch([self.volunteer()], deployment=deployment.name)
		frappe.delete_doc(
			fixtures.DEPLOYMENT_DOCTYPE, deployment.name, force=True, ignore_permissions=True
		)
		batch_service.generate(batch)

		self.assertEqual(len(batch_service.preview(batch)["rows"]), 1)
		self.assertEqual(batch_service.preview(batch)["would_create"], 1)

	def test_the_failures_and_skips_are_counted_from_the_rows(self):
		batch = self.make_batch([self.volunteer()])
		batch.append("volunteers", {"volunteer": self.volunteer()})
		batch.save()
		frappe.delete_doc(
			fixtures.VOLUNTEER_DOCTYPE, batch.volunteers[1].volunteer, force=True,
			ignore_permissions=True,
		)
		batch_service.generate(batch)

		self.assertEqual(batch_service.counts(batch)["skipped"], 1)
