# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Create the Module Def for VMMS Volunteer.

A third patch rather than a re-run of the two before it, because a Frappe patch
executes **once per site, by name**. `register_modules` and
`register_member_modules` are already in this site's Patch Log from the earlier
stages, so adding a module to `modules.txt` afterwards would never create its
Module Def — and every doctype in it fails to import during migrate with a
message about `frappe.core.doctype.<name>` not existing, which says nothing at
all about the real cause.

So each time a module is added, a patch is added with it. That is the pattern
`CLAUDE.md` describes; this is the third instance of it.

Runs pre-model-sync, so the module exists before its doctypes are synced.
`add_module_defs` skips modules that already have one, so this is safe on a
fresh install where `modules.txt` was read at install time.

**A Module Def is necessary and, on the first migrate, not sufficient.** Frappe
caches the module-to-app map (`installed_app_modules`, read back into
`frappe.local.module_app`) and builds it from each app's `modules.txt` at boot.
On the run that first adds a module, that cache predates the change, so nothing
in the same migrate can resolve the new module to this app — `load_doctype_module`
falls back to `frappe.core` and every doctype in the module fails with

    No module named 'frappe.core.doctype.<name>'

which is the same misleading message a missing Module Def produces, from a
different cause. Rebuilding the map here fixes it inside the run that needs it,
so adding a module takes one migrate rather than one failed migrate, a
`clear-cache` and a second one.
"""

import frappe
from frappe.installer import add_module_defs


def execute():
	add_module_defs("vmmsx", ignore_if_duplicate=True)

	# Drop the stale map, then rebuild it for this process. Both halves are
	# needed: the first stops the next boot reading the pre-change value, the
	# second makes the new module resolvable for the rest of *this* migrate.
	frappe.client_cache.delete_value("installed_app_modules")
	frappe.cache.delete_value("app_modules")
	frappe.setup_module_map(include_all_apps=False)
