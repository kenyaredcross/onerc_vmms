import frappe
from frappe.model.document import Document


class DeploymentRating(Document):

	def before_save(self):
		self.calculate_overall()

	def calculate_overall(self):
		scores = [
			self.punctuality or 0,
			self.performance or 0,
			self.communication or 0,
			self.teamwork or 0,
		]
		filled = [s for s in scores if s > 0]
		if filled:
			self.overall = round(sum(filled) / len(filled))
		else:
			self.overall = 0
