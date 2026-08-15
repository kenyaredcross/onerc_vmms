# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Create the Module Def for VMMS Branch.

The same patch as `register_task_module` beside it, for the same reason, and it
is a second entry rather than a shared one because a patch runs once per site by
name: a site that has already run one of them would skip the other if they were
the same line in `patches.txt`, and the module it names would have no Module Def.

Runs pre-model-sync so the module exists before `VMMS Branch Location` is
synced. `add_module_defs` skips modules that already have one.
"""

from frappe.installer import add_module_defs


def execute():
	add_module_defs("vmmsx", ignore_if_duplicate=True)
