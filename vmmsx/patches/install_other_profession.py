# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Give the configured Profession picker an honest free-text escape hatch.

``vmms_profession`` remains a Link to the shared Profession register.  The
explicit ``Other`` row is therefore a real option rather than a browser-only
value that the framework would reject, while ``vmms_other_profession`` holds
what the applicant actually calls their work.  The detail is optional on the
shared profile and required only by the volunteer registration UI.
"""

import frappe

PROFILE_DOCTYPE = "Red Profile"
PROFESSION_DOCTYPE = "Profession"
PROFESSION_FIELD = "vmms_profession"
FIELDNAME = "vmms_other_profession"


def execute() -> None:
	if frappe.db.table_exists(PROFESSION_DOCTYPE) and not frappe.db.exists(PROFESSION_DOCTYPE, "Other"):
		frappe.get_doc({"doctype": PROFESSION_DOCTYPE, "__newname": "Other"}).insert(
			ignore_permissions=True
		)

	if not frappe.get_meta(PROFILE_DOCTYPE).has_field(PROFESSION_FIELD):
		return

	if frappe.db.exists("Custom Field", {"dt": PROFILE_DOCTYPE, "fieldname": FIELDNAME}):
		return

	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	create_custom_field(
		PROFILE_DOCTYPE,
		{
			"fieldname": FIELDNAME,
			"label": "Other Profession",
			"fieldtype": "Data",
			"insert_after": PROFESSION_FIELD,
			"depends_on": f"eval:doc.{PROFESSION_FIELD} == 'Other'",
			"description": "The person's profession when Profession is Other. Owned by vmmsx.",
		},
		ignore_validate=True,
	)
