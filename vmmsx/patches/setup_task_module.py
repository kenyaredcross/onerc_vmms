# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install the settings field that says which role may assign and chase tasks.

vmmsx registers `VMMS Task` as geo-scopeable through core's
`onerc_scopeable_doctypes` hook and names its role with `role_from_setting`
rather than a literal, for the reason the access model gives and every other
registration in `hooks.py` repeats: which of a society's roles supervises
volunteers' work is that society's decision, and a role name in a source file is
exactly what the access model forbids.

**Geo scoping is doing two jobs here, as it does for announcements.** It decides
who may read a task, and because a task is anchored where the work belongs, it
also decides where somebody may assign one. A branch coordinator assigned at a
branch can hand out work in their branch; they cannot anchor a task at the
country, because the anchor has to sit inside the scope they hold.

What geo scoping deliberately does *not* decide is whether the volunteer holding
a task may see it. That is ownership, answered in `api/tasks.py` by the task's
own `volunteer` field, because a volunteer holds no Geo Assignment and never
should: the register is not theirs to browse, but the work assigned to them is
theirs to do.

**It ships empty, and empty fails closed.** No role resolves, so no
non-administrator can assign or read a task until a society names the role. The
framework exemption means an administrator can always set it.
"""

import frappe

SETTINGS_DOCTYPE = "National Society Settings"

SCOPE_ROLE_FIELD = "vmms_task_scope_role"


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": SCOPE_ROLE_FIELD}):
		return

	create_custom_field(
		SETTINGS_DOCTYPE,
		{
			"fieldname": SCOPE_ROLE_FIELD,
			"label": "Task Scope Role",
			# A Link to Role, so the desk offers only roles that exist. Core still
			# validates the value on save, since a Link can be left holding a role
			# that was later deleted.
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": "vmms_announcement_scope_role",
			"description": (
				"Which role may assign tasks to volunteers, chase them and sign off completed"
				" work, and in which part of the hierarchy, combined with that role's Geo"
				" Assignments. The volunteer holding a task always sees it through their own"
				" portal and needs no role for it. Left empty, only an administrator can assign"
				" a task. Owned by vmmsx."
			),
		},
		ignore_validate=True,
	)
