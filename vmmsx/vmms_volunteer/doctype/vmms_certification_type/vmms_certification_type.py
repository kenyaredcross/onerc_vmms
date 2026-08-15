# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Certification Type — configuration, and the source of every expiry date.

A society's own list of the qualifications it recognises. Nothing in this app
knows what any of them is called: the name is display, the key is what code
refers to, and `validity_days` is the whole of what drives expiry on every
certification held under this type.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class VMMSCertificationType(Document):
	def validate(self):
		self.validate_validity()

	def validate_validity(self):
		"""A validity period is a number of days, or zero for never expires."""
		if cint(self.validity_days) >= 0:
			return

		frappe.throw(
			_(
				"A validity period cannot be negative. Use zero for a certification that never"
				" expires — a certification of a never-expiring type can never read as lapsed."
			),
			frappe.ValidationError,
			title=_("Invalid Validity Period"),
		)
