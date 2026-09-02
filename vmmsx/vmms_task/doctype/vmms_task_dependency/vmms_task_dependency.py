# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Work that has to be finished before a task can start.

A row per prerequisite. The rules are the parent's — a cycle is refused on the
task's own `validate`, and starting a blocked task needs a manager's written
override — because neither is a question one row can answer.
"""

from frappe.model.document import Document


class VMMSTaskDependency(Document):
	pass
