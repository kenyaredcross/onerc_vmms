# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Create Module Def records for modules added after the app was installed.

A fresh install reads `modules.txt` and creates the Module Defs itself. A site
where vmmsx is *already* installed never re-reads it, so a module added later —
VMMS Approvals is the first — has no Module Def, and every doctype in it fails
to import with nothing said about why.

Runs pre-model-sync, so the module exists before its doctypes are synced.
Idempotent: `add_module_defs` skips modules that already have one.
"""

from frappe.installer import add_module_defs


def execute():
	add_module_defs("vmmsx", ignore_if_duplicate=True)
