import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, add_years


class OneRCMemberSubscription(Document):

	def before_save(self):
		self.set_dates()
		self.sync_member_status()

	def set_dates(self):
		if not self.from_date:
			self.from_date = frappe.utils.today()
		if not self.to_date and self.from_date:
			self.to_date = add_years(self.from_date, 1)

	def sync_member_status(self):
		if not self.member:
			return
		status_map = {
			"Draft": "Non Member",
			"Pending Payment": "Pending",
			"Active": "Active",
			"Expired": "Expired",
			"Cancelled": "Non Member",
		}
		new_status = status_map.get(self.status, "Non Member")
		frappe.db.set_value("OneRC Member", self.member, "membership_status", new_status)
