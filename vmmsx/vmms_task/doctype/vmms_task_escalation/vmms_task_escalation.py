# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One time a task was raised with somebody above the person holding it.

Append-only and read-only: an escalation is a record of a thing that happened on
a date, and a register where the history could be edited afterwards would be
worth less than no register at all.
"""

from frappe.model.document import Document


class VMMSTaskEscalation(Document):
	pass
