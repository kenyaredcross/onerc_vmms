import frappe
from frappe import _
from frappe.model.document import Document


class VMMSAssetTransaction(Document):
	def before_insert(self):
		if not self.flags.asset_service:
			frappe.throw(_("Record asset transactions through the asset service."), frappe.PermissionError)
		if self.quantity <= 0:
			frappe.throw(_("Quantity must be positive."))
		if self.transaction_type not in ("Receipt", "Issue", "Return"):
			frappe.throw(_("Invalid asset transaction type."))
		if self.geo_node != frappe.db.get_value("VMMS Branch Asset", self.asset, "geo_node"):
			frappe.throw(_("The transaction branch must match its asset."))

	def validate(self):
		if not self.is_new():
			frappe.throw(_("Asset transactions cannot be edited."))
