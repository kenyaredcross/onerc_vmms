# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Create Module Defs for VMMS Templating and VMMS Member.

A second patch rather than a re-run of `register_modules`, because a Frappe
patch executes **once per site, by name**. `register_modules` is already in this
site's Patch Log from the approvals stage, so adding modules to `modules.txt`
afterwards would never create their Module Defs — and every doctype in them
fails to import with a message about `frappe.core.doctype.<name>` not existing,
which says nothing about the real cause.

So each time a module is added, a patch is added with it. That is the pattern
`CLAUDE.md` describes; this is the second instance of it.

Runs pre-model-sync, so the modules exist before their doctypes are synced.
`add_module_defs` skips modules that already have one, so this is safe on a
fresh install where `modules.txt` was read at install time.
"""

from frappe.installer import add_module_defs


def execute():
	add_module_defs("vmmsx", ignore_if_duplicate=True)
