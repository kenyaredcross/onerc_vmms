"""Links from a shared Geo Node to VMMS-owned ERPNext Cost Centers."""

import frappe

GEO_DOCTYPE = "Geo Node"
GROUP_FIELD = "vmms_cost_center_group"
POSTING_FIELD = "vmms_cost_center"


def install() -> None:
	"""Add the links without changing onerc_core's Geo Node source."""
	if "erpnext" not in frappe.get_installed_apps():
		return
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	for field in (
		{
			"fieldname": GROUP_FIELD,
			"label": "VMMS Reporting Cost Center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"read_only": 1,
			"no_copy": 1,
			"hidden": 1,
			"description": "Group Cost Center for this node and its descendants.",
		},
		{
			"fieldname": POSTING_FIELD,
			"label": "VMMS Posting Cost Center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"read_only": 1,
			"no_copy": 1,
			"insert_after": "geo_code",
			"description": "Membership income at this node posts here.",
		},
	):
		if not frappe.db.exists("Custom Field", {"dt": GEO_DOCTYPE, "fieldname": field["fieldname"]}):
			create_custom_field(GEO_DOCTYPE, dict(field), ignore_validate=True)
