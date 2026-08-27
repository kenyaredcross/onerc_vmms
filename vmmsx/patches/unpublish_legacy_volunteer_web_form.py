# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

import frappe


LEGACY_FORM = "register-as-a-volunteer"


def execute():
	"""Leave one supported public door into volunteer registration.

	The React journey writes person facts to Red Profile and creates the thin
	application in one transaction. The older native Web Form cannot perform
	that transaction and would otherwise remain a second, incomplete route on
	an existing site even after its exported JSON is unpublished.
	"""
	if frappe.db.exists("Web Form", LEGACY_FORM):
		frappe.db.set_value("Web Form", LEGACY_FORM, "published", 0, update_modified=False)
