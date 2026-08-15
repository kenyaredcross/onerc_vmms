# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install the settings field that says which role may see memberships.

vmmsx registers `VMMS Membership` as geo-scopeable through core's
`onerc_scopeable_doctypes` hook, and names its role with `role_from_setting`
rather than a literal — because *which* of a society's roles may see membership
records is a society's decision, not this app's. Core resolves the field's value
at enforcement time.

The field is a **Custom Field owned by vmmsx**, exactly like the ACC-03 anchor
level. Core's National Society Settings doctype is not edited: a product pushing
its own fields into the shared foundation's source is how the foundation stops
being shared.

**It is deliberately left empty.** Empty means no role resolves, which means
core fails closed — no non-administrator can read a membership until a society
chooses the role. That is the correct pre-portal state: memberships hold
personal data, and defaulting to *some* role would be this app guessing at a
society's access policy. Administrators are unaffected by the framework
exemption, so there is always somebody who can set it.

A separate patch from `setup_member_module` because a Frappe patch runs once per
site by name, and that one has already run everywhere.
"""

import frappe

SETTINGS_DOCTYPE = "National Society Settings"

SCOPE_ROLE_FIELD = "vmms_membership_scope_role"


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": SCOPE_ROLE_FIELD}):
		return

	create_custom_field(
		SETTINGS_DOCTYPE,
		{
			"fieldname": SCOPE_ROLE_FIELD,
			"label": "Membership Scope Role",
			# A Link to Role, so the desk offers only roles that exist. Core
			# still validates the value on save — a Link can be left holding a
			# role that was later deleted.
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": "vmms_membership_anchor_level",
			"description": (
				"Which role may see VMMS Membership records, and where — combined with that"
				" role's Geo Assignments. Left empty, no non-administrator can read a membership"
				" at all. Owned by vmmsx."
			),
		},
		ignore_validate=True,
	)
