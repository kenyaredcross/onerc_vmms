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
"""

import frappe
from frappe import _
from frappe.model.document import Document

from vmmsx.task.services import states


class VMMSTask(Document):
	def validate(self):
		self.assert_known_status()

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
