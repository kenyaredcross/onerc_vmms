# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Create the Module Def for VMMS Registration.

Its own patch, because a Frappe patch runs **once per site, by name** and every
`register_*_module` before it is already in this site's Patch Log. Re-running
one of those is not a thing the framework offers, so a module added now needs a
name the log has not seen.

Without it, `VMMS Application Question` and `VMMS Application Answer` fail to
import during migrate with a message about `frappe.core.doctype.<name>`, which
says nothing about the missing Module Def that actually caused it.

Pre-model-sync, so the module exists before its doctypes are synced.
`add_module_defs` skips modules that already have one, which is the fresh-install
case where `modules.txt` was read at install time.

**Creating the Module Def is not enough on its own, and this is the part every
earlier `register_*_module` patch in this app quietly got away with.** Frappe
resolves a module to its app through `frappe.local.module_app`, a reverse map
built once per process by `setup_module_map()` and cached under `app_modules`.
On a migrate that map is already built by the time a pre-model-sync patch runs,
so model sync looks up a module created seconds earlier, does not find it, and
skips every doctype in it **without failing** — the migrate reports success and
the doctypes simply are not there. A second migrate then works, because the next
process builds the map with the module in it.

`install_app` has exactly this problem and solves it three lines after calling
`add_module_defs`: delete the cached map and rebuild it before syncing. This
does the same, so one migrate is enough. That matters on a hosted site, where
migrate is the only thing that runs and `seed_society` further down the same run
may create records in the doctypes this module owns.
"""

import frappe
from frappe.installer import add_module_defs


def execute():
	add_module_defs("vmmsx", ignore_if_duplicate=True)

	# The rebuild, in the order `frappe.installer.install_app` does it. Both
	# caches, because `setup_module_map` reads a different one depending on
	# whether it was asked for all apps or only the installed ones, and a stale
	# value in either is a module the sync cannot see.
	frappe.cache.delete_value("app_modules")

	if hasattr(frappe, "client_cache"):
		frappe.client_cache.delete_value("installed_app_modules")

	frappe.setup_module_map(include_all_apps=True)
