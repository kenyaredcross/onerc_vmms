import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today


class Volunteer(Document):

	def before_save(self):
		self.set_full_name()
		self.set_age()

	def set_full_name(self):
		parts = [self.first_name, self.middle_name, self.last_name]
		self.full_name = " ".join(p for p in parts if p)

	def set_age(self):
		if self.date_of_birth:
			from frappe.utils import date_diff
			days = date_diff(today(), self.date_of_birth)
			self.age = int(days / 365.25)