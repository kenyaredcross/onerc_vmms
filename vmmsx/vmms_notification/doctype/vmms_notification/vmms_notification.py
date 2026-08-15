# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Notification — one person's copy of one announcement.

Deliberately almost empty. It holds a recipient, a link to the announcement, and
whether it has been read; the wording is read through the link and never copied
here, so an announcement corrected after it went out is corrected in every copy
at once.

The one rule it does carry is that a person holds **one** copy of an
announcement. That is the invariant the fan-out's idempotence rests on, and it
is enforced here as well as checked in `delivery.ensure()` because the two
protect against different things: `ensure` stops the ordinary retry cheaply, and
this stops a second copy arriving by any other route at all, including a desk
insert and a data import.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class VMMSNotification(Document):
	def validate(self):
		self.refuse_duplicate()

	def refuse_duplicate(self):
		"""One copy per person per announcement."""
		existing = frappe.db.exists(
			self.doctype,
			{
				"announcement": self.announcement,
				"recipient": self.recipient,
				"name": ["!=", self.name or ""],
			},
		)

		if existing:
			frappe.throw(
				_("{0} already holds a copy of this announcement.").format(self.recipient),
				frappe.DuplicateEntryError,
			)
