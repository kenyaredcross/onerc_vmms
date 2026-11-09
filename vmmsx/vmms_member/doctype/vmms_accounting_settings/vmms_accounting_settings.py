# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class VMMSAccountingSettings(Document):
	def validate(self):
		if not self.enabled:
			return

		if "erpnext" not in frappe.get_installed_apps():
			frappe.throw(_("ERPNext is not installed on this site, so there is nothing to post to."))

		if self.income_account:
			company, root_type, is_group = frappe.db.get_value(
				"Account", self.income_account, ["company", "root_type", "is_group"]
			)
			if company != self.company:
				frappe.throw(_("The income account belongs to {0}, not {1}.").format(company, self.company))
			if root_type != "Income" or is_group:
				frappe.throw(_("Choose an income account that can be posted to, not a group."))
