# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Whether a society cancels memberships at all.

Some do not: in Kenya a membership runs until it expires. On by default, so a
society that has never opened the setting keeps the cancel action it had.
"""

import frappe

SETTINGS_DOCTYPE = "National Society Settings"
FIELD = {
	"fieldname": "vmms_memberships_can_be_cancelled",
	"label": "Memberships Can Be Cancelled",
	"fieldtype": "Check",
	"default": "1",
	"insert_after": "vmms_member_max_age",
	"description": "Off when a membership always runs until it expires. The cancel action is then not offered anywhere.",
}


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
		return

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": FIELD["fieldname"]}):
		return

	field = dict(FIELD)
	if not frappe.get_meta(SETTINGS_DOCTYPE).has_field(field["insert_after"]):
		field.pop("insert_after")

	create_custom_field(SETTINGS_DOCTYPE, field, ignore_validate=True)
	frappe.clear_cache(doctype=SETTINGS_DOCTYPE)
