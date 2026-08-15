# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Stipend Report Volunteer — one volunteer's line on a progress report.

A child row with no behaviour of its own. Everything about it is decided by the
parent: the scope check that let the volunteer on at all lives in
`stipend/services/picker.py`, the department is derived by
`stipend/services/department.py`, and the "one row per volunteer" rule is
enforced on the parent, where the whole table can be seen at once.
"""

from frappe.model.document import Document


class VMMSStipendReportVolunteer(Document):
	pass
