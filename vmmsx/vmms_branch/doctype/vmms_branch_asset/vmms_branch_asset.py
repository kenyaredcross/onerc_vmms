import frappe
from frappe import _
from frappe.model.document import Document


class VMMSBranchAsset(Document):
	def validate(self):
		if not self.asset_name or not self.asset_name.strip():
			frappe.throw(_("Enter an asset name."))
		duplicate = frappe.db.exists(
			self.doctype,
			{
				"asset_name": self.asset_name,
				"geo_node": self.geo_node,
				"name": ("!=", self.name or ""),
			},
		)
		if duplicate:
			frappe.throw(_("This branch already has an asset with that name."))
		if self.is_new():
			if self.total_quantity or self.available_quantity:
				frappe.throw(_("New assets start at zero. Receive stock after creation."))
		else:
			old = self.get_doc_before_save()
			if old and self.geo_node != old.geo_node:
				frappe.throw(_("Move stock with a branch transfer, not by changing its branch."))
			if old and (
				self.total_quantity != old.total_quantity or self.available_quantity != old.available_quantity
			):
				frappe.throw(_("Use an asset transaction to change stock quantities."))
