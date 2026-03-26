import frappe
from frappe.model.document import Document


class GeoNode(Document):

	def before_save(self):
		self.set_parent_levels()

	def set_parent_levels(self):
		self.level_1_node = None
		self.level_2_node = None

		if not self.parent_geo_node:
			return

		parent = frappe.get_doc("Geo Node", self.parent_geo_node)
		geo_level = frappe.get_doc("Geo Level", self.geo_level)

		if geo_level.level_order == 2:
			self.level_1_node = self.parent_geo_node

		elif geo_level.level_order == 3:
			self.level_2_node = self.parent_geo_node
			if parent.parent_geo_node:
				self.level_1_node = parent.parent_geo_node