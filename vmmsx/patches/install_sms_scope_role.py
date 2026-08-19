# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install the settings field that says which role may send SMS.

vmmsx does not own an SMS doctype — sending goes through `onerc_sms`'s own
`SMS Campaign`, an optional companion app, using its generic "Doctype Query"
builder against `VMMS Volunteer`/`VMMS Member` directly. Geo scoping is not
registered here the way it is for `onerc_scopeable_doctypes`: it falls out for
free because `SMS Campaign.resolve_from_doctype()` reads those already-scoped
doctypes with the campaign's own owner's permissions. See
`vmmsx/sms/services/society.py`.

What *is* this app's decision is narrower: which society role, if any, may
open onerc_sms's campaign builder at all. A **Custom Field owned by vmmsx**,
exactly like every other scope-role setting. Core's National Society Settings
doctype is not edited.

**Left empty.** No non-administrator reaches onerc_sms's campaign builder
until a society chooses the role — `staff/services/console.py::sms_access()`
answers False until then, so the side door in the console stays closed rather
than pointing at a screen that would refuse them.

A separate patch from any single module's setup, the same reason
`install_deployment_scope_roles` and `install_stipend_scope_roles` are their
own: one patch, one concern, and a patch runs once per site by name.
"""

import frappe

from vmmsx.sms.services.society import SCOPE_ROLE_FIELD

SETTINGS_DOCTYPE = "National Society Settings"


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": SCOPE_ROLE_FIELD}):
		return

	create_custom_field(
		SETTINGS_DOCTYPE,
		{
			"fieldname": SCOPE_ROLE_FIELD,
			"label": "SMS Scope Role",
			# A Link to Role, so the desk offers only roles that exist. Core
			# still validates the value on save: a Link can be left holding a
			# role that was later deleted.
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": "vmms_announcement_scope_role",
			"description": "Which role may open onerc_sms's campaign builder, if that app is"
			" installed. Left empty, nobody but an administrator sees the side door for it in the"
			" manager console. Owned by vmmsx.",
		},
		ignore_validate=True,
	)
