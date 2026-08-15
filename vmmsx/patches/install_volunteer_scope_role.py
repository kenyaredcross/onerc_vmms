# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install the settings field that says which role may see volunteers.

vmmsx registers `VMMS Volunteer` as geo-scopeable through core's
`onerc_scopeable_doctypes` hook, and names its role with `role_from_setting`
rather than a literal — because *which* of a society's roles may see the
volunteer register is a society's decision, not this app's. Core resolves the
field's value at enforcement time.

The field is a **Custom Field owned by vmmsx**, exactly like the ACC-03 anchor
level and exactly like `vmms_membership_scope_role` before it. Core's National
Society Settings doctype is not edited: a product pushing its own fields into
the shared foundation's source is how the foundation stops being shared.

**It is deliberately left empty.** Empty means no role resolves, which means
core fails closed — no non-administrator can read a volunteer record until a
society chooses the role. That is the correct pre-portal state: the volunteer
register holds personal data about people who have not been employed by anybody,
and defaulting to *some* role would be this app guessing at a society's access
policy. Administrators are unaffected by the framework exemption, so there is
always somebody who can set it, and core logs every unresolved read so the
closed state is visible rather than looking like nobody having been granted
anything yet.

A separate patch from `setup_volunteer_module` for the same reason membership's
was separate from its own setup: one patch, one concern, and a patch runs once
per site by name.
"""

import frappe

from vmmsx.volunteer.services.society import EMPLOYEE_COMPANY_FIELD, SCOPE_ROLE_FIELD

SETTINGS_DOCTYPE = "National Society Settings"


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": SCOPE_ROLE_FIELD}):
		return

	create_custom_field(
		SETTINGS_DOCTYPE,
		{
			"fieldname": SCOPE_ROLE_FIELD,
			"label": "Volunteer Scope Role",
			# A Link to Role, so the desk offers only roles that exist. Core
			# still validates the value on save — a Link can be left holding a
			# role that was later deleted.
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": EMPLOYEE_COMPANY_FIELD,
			"description": (
				"Which role may see VMMS Volunteer records, and where, combined with that role's"
				" Geo Assignments. Left empty, no non-administrator can read a volunteer record at"
				" all. Owned by vmmsx."
			),
		},
		ignore_validate=True,
	)
