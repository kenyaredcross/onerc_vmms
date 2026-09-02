# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Task — a piece of work a coordinator asks one volunteer to do.

**The controller holds no rules of its own**, the same as `VMMS Announcement`
and `VMMS Time Log` before it. Everything is in `vmmsx/task/services/`:
`states.py` is the lifecycle, `task.py` is every move along it and everything
that gets told when one happens. What is left here is the pair of guarantees
that have to hold however the document was written, including from a script, a
bulk edit or the desk form, none of which go through the service.

**`status` is checked, not enforced.** The field is read-only on the form and
only the service writes it, so this is the second line of defence rather than
the first. It refuses a value outside the closed set, because a status the code
does not know is a task that no query will ever find and no verb will ever move.

**ACC-02 is the doctype's, not this file's.** `geo_node` is `reqd` on the field,
which is where "required at creation, not filled in later" is actually made
true. `task.assign()` fills it from the volunteer's own branch when a caller
does not name one, and refuses rather than guessing when there is nothing to
take it from.

**Two rules did have to come here**, and both for the same reason: they are
about the document as a whole and cannot be checked anywhere a single verb can
see. The due day is derived from the due datetime, so no screen can put a
deadline on Tuesday and a due date on Wednesday — the same shape
`VMMS Deployment` uses for its period. And a dependency loop is refused before it
is written, because the rows about to be saved are only visible here.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from vmmsx.task.services import states, task


class VMMSTask(Document):
	def validate(self):
		self.assert_known_status()
		self.derive_due_day()
		self.assert_no_dependency_cycle()

	def derive_due_day(self):
		"""Keep the due datetime and the due day saying the same thing.

		One fact, written once. `due_at` is what somebody sets; `due_on` is
		read-only and derived from it, because every register in this app windows
		on days and every volunteer needs to know what time it is wanted by.

		**It fills backwards as well.** A task written before `due_at` existed
		carries only the day, and a rule that refused to save one until somebody
		retyped its deadline as a datetime would make every historical task
		unopenable. A day with no time is taken as the end of that day, which is
		what a deadline given in days has always meant.
		"""
		if not self.due_at and self.due_on:
			self.due_at = f"{getdate(self.due_on)} 23:59:59"

		self.due_on = getdate(self.due_at) if self.due_at else None

	def assert_no_dependency_cycle(self):
		"""Refuse a dependency that leads back here, however long the chain.

		Here rather than in a verb because the rows being saved are only visible
		from the document. `task.assert_no_cycle` walks the graph and says why a
		loop is refused rather than merely detected.
		"""
		task.assert_no_cycle(self)

	def assert_known_status(self):
		"""Refuse a status outside the closed set in `states.py`."""
		if self.status in states.ALL:
			return

		frappe.throw(
			_("{0} is not a task status. Expected one of: {1}.").format(
				frappe.bold(self.status), ", ".join(states.ALL)
			),
			frappe.ValidationError,
			title=_("Unknown Task Status"),
		)
