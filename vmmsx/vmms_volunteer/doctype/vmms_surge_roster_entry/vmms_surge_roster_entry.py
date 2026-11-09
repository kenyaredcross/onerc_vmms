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
from frappe.utils import getdate, today


class VMMSSurgeRosterEntry(Document):
	def validate(self):
		self._refuse_a_past_expiry()

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

	def _refuse_a_past_expiry(self):
		"""A licence recorded as valid until a date already gone is not a licence.

		Only when the date is being set or changed: an entry whose licence has
		since run out must still save, to be stood down or have a note added.
		"""
		if not self.licence_expiry:
			return

		if not (self.is_new() or self.has_value_changed("licence_expiry")):
			return

		if getdate(self.licence_expiry) < getdate(today()):
			frappe.throw(
				_("This licence has already expired. Ask for the renewed licence."),
				frappe.ValidationError,
				title=_("Licence Expired"),
			)

