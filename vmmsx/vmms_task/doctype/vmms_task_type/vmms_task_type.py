# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What a society calls a kind of work.

An open set of records, and **nothing in this app branches on one**. A task's
type is for a coordinator filtering their register and for a report saying how
much household visiting a branch did last quarter; no rule anywhere reads it.
That is the same footing `VMMS Certification Type` and `VMMS TOR Methodology`
stand on, and it is why this doctype has no fields beyond a name, a description
and the switch that stops it being offered for new work.

`is_active` retires a type without erasing it: every task already carrying it
keeps it, because a register that renamed history when a society changed its
vocabulary would be a register nobody could report from.
"""

from frappe.model.document import Document


class VMMSTaskType(Document):
	pass
