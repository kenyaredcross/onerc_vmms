# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A link back to the membership on ERPNext's Sales Invoice and Payment Entry.

So an accountant reading either document can open the membership it was for,
and a report can filter on it. Custom Fields, installed on every migrate where
ERPNext is present, the same way `geo_cost_center_fields` adds its links.
"""

import frappe

FIELD = "vmms_membership"


def install() -> None:
	if "erpnext" not in frappe.get_installed_apps():
		return

	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	for doctype, after in (("Sales Invoice", "customer"), ("Payment Entry", "party_name")):
		if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": FIELD}):
			continue
		create_custom_field(
			doctype,
			{
				"fieldname": FIELD,
				"label": "VMMS Membership",
				"fieldtype": "Link",
				"options": "VMMS Membership",
				"insert_after": after,
				"read_only": 1,
				"no_copy": 1,
				"in_standard_filter": 1,
			},
			ignore_validate=True,
		)
