# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Stipend Attendance Line — one volunteer, one day, one amount.

A child row with no behaviour of its own. Every rule about it needs the whole
grid to check — is this volunteer on the report, is this day inside the period,
is this the only line for that pair — so all of them live in
`stipend/services/attendance.py`, which sees the table rather than the row.
"""

from frappe.model.document import Document


class VMMSStipendAttendanceLine(Document):
	pass
