# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Task Batch — the brief forty people were given, and what became of it.

An **administrative grouping, not a shared task**. `task/services/batch.py`
carries the whole argument and every verb; what is here is the one rule that has
to hold however the record was written, including from the desk form.

**A generated batch is frozen.** Once tasks have been made from it, the subject,
the brief, the schedule and the anchor stop being editable. Editing them would
be a coordinator tidying a typo and silently rewriting work forty people had
already read — and worse, the batch would then disagree with the tasks it made
without anything saying so. What stays editable is the volunteers table, because
adding somebody and generating again is exactly how a batch is meant to grow.

The counts are deliberately not fields. `batch.counts()` reads the generated
tasks and answers from their current state, so a batch's report of its own work
cannot drift from the work.
"""

import frappe
from frappe import _
from frappe.model.document import Document

# What stops being editable once the batch has generated. Named as data because
# the refusal message lists them, and two lists would eventually disagree.
FROZEN_AFTER_GENERATION = {
	"subject": "the subject",
	"brief": "the brief",
	"geo_node": "the anchor",
	"project": "the project",
	"deployment": "the deployment",
	"due_at": "the due date",
	"task_type": "the task type",
	"priority": "the priority",
}


class VMMSTaskBatch(Document):
	def validate(self):
		self.assert_not_rewriting_history()

	def assert_not_rewriting_history(self):
		"""Refuse an edit to what has already been sent out.

		Only after generation, and only to the fields that were copied onto the
		tasks. Before that a batch is a draft and every field is a coordinator's to
		change; afterwards, the brief on forty tasks is the brief forty people
		read, and the batch must not be able to claim it was something else.
		"""
		if self.is_new() or not self.generated_on:
			return

		before = self.get_doc_before_save()

		if not before:
			return

		changed = [
			label
			for field, label in FROZEN_AFTER_GENERATION.items()
			if str(before.get(field) or "") != str(self.get(field) or "")
		]

		if not changed:
			return

		frappe.throw(
			_(
				"This batch has already generated its tasks, so {0} cannot change: the tasks"
				" carry what was written when they were sent, and forty people have read it."
				" Add volunteers and generate again, or start a new batch."
			).format(", ".join(str(label) for label in changed)),
			frappe.ValidationError,
			title=_("Already Sent"),
		)
