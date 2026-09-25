"""Install the asset scope role setting on National Society Settings."""

import frappe


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	fieldname = "vmms_asset_scope_role"
	if frappe.db.exists("Custom Field", {"dt": "National Society Settings", "fieldname": fieldname}):
		return
	create_custom_field(
		"National Society Settings",
		{
			"fieldname": fieldname,
			"label": "Asset Scope Role",
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": "vmms_branch_location_scope_role",
			"description": "Role allowed to manage branch assets within its Geo Assignments. Defaults to VMMS Asset Manager.",
		},
		ignore_validate=True,
	)
