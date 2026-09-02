# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One number that has asked not to hear from the society on WhatsApp."""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class VMMSWhatsAppOptOut(Document):
	def before_insert(self):
		# Stamped here rather than defaulted on the field, so a record written by
		# the webhook and one recorded by hand on the desk carry the same kind of
		# answer to when somebody asked.
		self.opted_out_on = self.opted_out_on or now_datetime()
