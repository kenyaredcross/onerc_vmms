# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Surge Roster Entry — one checked professional on a branch's surge roster.

Written through `volunteer/services/surge.py`, which owns what an entry means.
The controller holds the one rule that must hold however the record is saved,
from the console or the desk: one active entry per volunteer per profession.
Whether an entry is ready is never stored; see the service.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class VMMSSurgeRosterEntry(Document):
	def validate(self):
		if self.status != "Active":
			return

		duplicate = frappe.db.exists(
			self.doctype,
			{
				"volunteer": self.volunteer,
				"profession": self.profession,
				"status": "Active",
				"name": ("!=", self.name),
			},
		)

		if duplicate:
			frappe.throw(
				_("This volunteer is already on the surge roster as {0}.").format(self.profession),
				frappe.ValidationError,
			)
