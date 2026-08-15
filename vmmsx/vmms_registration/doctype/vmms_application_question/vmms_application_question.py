# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Application Question — a question a society adds to a registration.

The point of this doctype is that a society can ask for something the product
never anticipated without anybody writing code. A branch that wants a letter
from the area chief creates one row here, and the question appears on the
registration wizard, on the desk form, and in front of the approver deciding
the application. There is no deploy in that sentence.

**A question is configuration; an answer is a record.** This doctype is the
first, `VMMS Application Answer` is the second, and the answer snapshots the
question's wording and type at the moment it was given. Rewording a question
next year must not rewrite what somebody was asked this year, which is the same
rule `VMMS Approval Decision` applies to a stage's label.

**`asked_on` is a Link to DocType, not a Select of the two we ship.** Same
shape as `VMMS Approval Workflow.workflow_for`, and for the same reason: this
module names no registration. A third registration added later is governed by
creating rows, not by editing an option list here.

**Deactivating is not deleting.** `is_active` stops the question being asked of
new applicants and leaves every answer already given in place. An answer was
part of an application somebody decided, and deleting it would take evidence
out from under a decision that has already been made.
"""

import frappe
from frappe import _
from frappe.model.document import Document

# The types an answer may take. `Attach` is the one that made this worth
# building: a society collecting a chief's letter has nowhere else to put it.
FIELD_TYPES = ("Data", "Small Text", "Select", "Check", "Date", "Int", "Attach")

SELECT = "Select"


class VMMSApplicationQuestion(Document):
	def validate(self):
		self.question_label = (self.question_label or "").strip()
		self._assert_answerable()

	def _assert_answerable(self) -> None:
		"""A Select with no choices is a question nobody can answer.

		Checked here rather than left to `mandatory_depends_on` alone, because
		that only governs the desk form and a question created by a patch or a
		seed would slip past it into a wizard that then draws an empty dropdown.
		"""
		if self.field_type != SELECT:
			return

		if [line.strip() for line in (self.options or "").splitlines() if line.strip()]:
			return

		frappe.throw(
			_("A question answered from a list needs at least one choice."),
			frappe.MandatoryError,
			title=_("No Choices"),
		)

	def choices(self) -> list[str]:
		"""The vocabulary this question accepts, in the order it was written."""
		if self.field_type != SELECT:
			return []

		return [line.strip() for line in (self.options or "").splitlines() if line.strip()]
