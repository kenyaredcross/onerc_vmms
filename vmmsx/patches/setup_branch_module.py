# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install the settings field that says which role maintains branch locations.

`VMMS Branch Location` is registered as geo-scopeable through core's
`onerc_scopeable_doctypes` hook, naming its role with `role_from_setting` rather
than a literal, exactly as every other registration in `hooks.py` does. A county
coordinator maintains the places in their own county; the national office
maintains everything, because their assignment covers everything.

**Scoping governs the desk, not the map.** What a signed-out visitor sees is
`is_published` on each location and nothing else, served by
`api/locations.py::published`. That is the same division the content module
draws: `is_public` on a surface is the whole of its guest-read rule, and no code
branches on which surface it got. So this setting decides who may *maintain* a
location. It has no bearing on who may look one up, because the answer to that
is everybody.

**It ships empty, and empty fails closed** for the desk half. No role resolves,
so no non-administrator can add or edit a location until a society names the
role. Nothing about the public map depends on it: a site whose administrator
published three offices serves those three whether or not this field was ever
filled in.
"""

import frappe

SETTINGS_DOCTYPE = "National Society Settings"

SCOPE_ROLE_FIELD = "vmms_branch_location_scope_role"


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": SCOPE_ROLE_FIELD}):
		return

	create_custom_field(
		SETTINGS_DOCTYPE,
		{
			"fieldname": SCOPE_ROLE_FIELD,
			"label": "Branch Location Scope Role",
			# A Link to Role, so the desk offers only roles that exist. Core still
			# validates the value on save, since a Link can be left holding a role
			# that was later deleted.
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": "vmms_task_scope_role",
			"description": (
				"Which role may add and edit the society's offices, warehouses and training"
				" centres, and in which part of the hierarchy, combined with that role's Geo"
				" Assignments. It does not decide who may see them: a location ticked as shown"
				" on the public map is served to anybody. Left empty, only an administrator can"
				" maintain a location. Owned by vmmsx."
			),
		},
		ignore_validate=True,
	)
