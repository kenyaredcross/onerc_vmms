# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Create the Module Def for VMMS Content.

Its own patch, not a re-run of an earlier one, for the reason `CLAUDE.md`
records and `register_member_modules` explains at length: a Frappe patch
executes once per site by name, `modules.txt` is only read at install time, and
a module added to a site that already has vmmsx installed therefore has no
Module Def. Every doctype in it then fails to import during migrate with a
message about `frappe.core.doctype.<name>`, which says nothing about the cause.

Runs pre-model-sync so the module exists before its doctypes are synced.
`add_module_defs` skips modules that already have one.
"""

from frappe.installer import add_module_defs


def execute():
	add_module_defs("vmmsx", ignore_if_duplicate=True)
