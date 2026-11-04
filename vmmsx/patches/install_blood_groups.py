"""Seed the old registration options and preserve existing blood-group values."""

import frappe

BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Don't Know")
DOCTYPE = "VMMS Blood Group"


def execute():
	if not frappe.db.exists("DocType", DOCTYPE):
		return
	values = set(BLOOD_GROUPS)
	if frappe.db.exists("DocType", "Red Profile") and frappe.get_meta("Red Profile").has_field(
		"vmms_blood_group"
	):
		values.update(frappe.get_all("Red Profile", pluck="vmms_blood_group"))
	for value in sorted(value for value in values if value):
		if not frappe.db.exists(DOCTYPE, value):
			frappe.get_doc({"doctype": DOCTYPE, "__newname": value}).insert(ignore_permissions=True)
	field = frappe.db.get_value(
		"Custom Field", {"dt": "Red Profile", "fieldname": "vmms_blood_group"}, "name"
	)
	if field:
		document = frappe.get_doc("Custom Field", field)
		if document.fieldtype != "Link" or document.options != DOCTYPE:
			# Data and Link share the same varchar column. Seed all existing values
			# before changing metadata; no column or captured value is replaced.
			frappe.db.set_value("Custom Field", field, {"fieldtype": "Link", "options": DOCTYPE})
		frappe.clear_cache(doctype="Red Profile")
