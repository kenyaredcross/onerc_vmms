# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Task Update — one entry in a task's thread.

A child table with no controller logic. Every row is written by
`task/services/task.py::_add_entry`, which stamps the author from the session
and the time from the clock, so there is nothing here for a `validate` to check
that is not already true by construction.
"""

from frappe.model.document import Document


class VMMSTaskUpdate(Document):
	pass
