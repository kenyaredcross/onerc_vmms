import frappe
from frappe.model.document import Document
from frappe.utils import date_diff, today, getdate


class Volunteer(Document):

	def before_save(self):
		self.set_full_name()
		self.set_age()
		self.set_organization_name()

	def on_update(self):
		if self.volunteer_status == "Active" and not self.employee:
			self.create_employee()

	def set_full_name(self):
		parts = [self.first_name, self.middle_name, self.last_name]
		self.full_name = " ".join(p for p in parts if p)

	def set_age(self):
		if self.date_of_birth:
			days = date_diff(today(), self.date_of_birth)
			self.age = int(days / 365.25)

	def set_organization_name(self):
		self.organization_name = frappe.db.get_single_value(
			"National Society Settings", "organization_name"
		) or ""

	def create_employee(self):
		if not frappe.db.get_value("Employee", {"user_id": self.user_account}):
			employee = frappe.get_doc({
				"doctype": "Employee",
				"first_name": self.first_name,
				"last_name": self.last_name,
				"employee_name": self.full_name,
				"user_id": self.user_account,
				"gender": self.gender,
				"date_of_birth": self.date_of_birth,
				"date_of_joining": today(),
				"is_volunteer": 1,
				"status": "Active",
			})
			employee.insert(ignore_permissions=True)
			frappe.db.set_value("Volunteer", self.name, "employee", employee.name)
			frappe.db.commit()
