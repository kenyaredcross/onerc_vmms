# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Create the Module Def for VMMS Events.

Its own patch, for the reason `register_registration_module.py` sets out at
length: a Frappe patch runs **once per site, by name**, so every earlier
`register_*_module` is already in this site's Patch Log and cannot be re-run.
A module added now needs a name the log has not seen.

Without it, `VMMS Event Attendance` fails to import during migrate with a
message about `frappe.core.doctype.<name>` that says nothing about the missing
Module Def which actually caused it.

The cache rebuild below is the same one that patch explains: on a migrate,
`frappe.local.module_app` is already built by the time a pre-model-sync patch
runs, so model sync would not find a module created seconds earlier and would
skip its doctypes **without failing**. Deleting the cached map and rebuilding it
is what `frappe.installer.install_app` does three lines after `add_module_defs`,
and it is what makes one migrate enough.
"""

import frappe
from frappe.installer import add_module_defs


def execute():
	add_module_defs("vmmsx", ignore_if_duplicate=True)

	frappe.cache.delete_value("app_modules")

	if hasattr(frappe, "client_cache"):
		frappe.client_cache.delete_value("installed_app_modules")

	frappe.setup_module_map(include_all_apps=True)
