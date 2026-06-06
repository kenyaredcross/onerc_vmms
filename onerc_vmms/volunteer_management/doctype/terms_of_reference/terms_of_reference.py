import frappe
from frappe.model.document import Document
from frappe.utils import date_diff


class TermsofReference(Document):

	def before_save(self):
		self.calculate_duration()
		self.calculate_total_cost()
		self.check_budget()

	def before_submit(self):
		if self.status != "Approved":
			frappe.throw("TOR must be Approved before submitting.")

	def calculate_duration(self):
		if self.start_date and self.end_date:
			self.duration_days = date_diff(self.end_date, self.start_date) + 1

	def calculate_total_cost(self):
		total = 0
		for row in self.resources:
			qty = row.quantity or 0
			unit_cost = row.unit_cost or 0
			days = row.days or 1
			row.cost = qty * unit_cost * days
			total += row.cost
		self.total_cost = total

	def check_budget(self):
		if not self.project:
			self.budget_status = "No Project Linked"
			return
		budget = frappe.db.get_value("Project", self.project, "estimated_costing") or 0
		self.project_budget = budget
		if not budget:
			self.budget_status = "No Budget Set"
			return
		if self.total_cost > budget:
			self.budget_status = "Over Budget"
			frappe.throw(
				f"Total cost ({self.total_cost}) exceeds project budget ({budget}). "
				f"Please revise resources or increase the project budget."
			)
		else:
			self.budget_status = "Within Budget"
