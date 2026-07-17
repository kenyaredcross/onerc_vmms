# Copyright (c) 2025, Kenya Red Cross Society and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from ...utils.utils import disable_energy_point_email_notifications


class VMSettings(Document):
	def validate(self):
		if not self.disable_energy_point_email_notifications:
			return

		users = frappe.get_all("User", filters={"enabled": 1}, pluck="name")
		for user in users:
			disable_energy_point_email_notifications(user)
