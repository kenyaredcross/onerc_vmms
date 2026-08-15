# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install the settings fields that say which roles may see this module's records.

vmmsx registers all three of the Deployment module's own doctypes as
geo-scopeable through core's `onerc_scopeable_doctypes` hook, and names each
role with `role_from_setting` rather than a literal — because *which* of a
society's roles may see what is deployed near them is a society's decision, not
this app's. Core resolves each field's value at enforcement time.

**Three fields, because these are three questions.** A society may reasonably
let every coordinator see the deployments running in their area while keeping
who asked for what, and who is being moved between branches, narrower. Folding
them into one setting would make that a choice nobody could express.

Each is a **Custom Field owned by vmmsx**, exactly like the anchor levels and
the two scope roles before it. Core's National Society Settings doctype is not
edited.

**All three are deliberately left empty.** Empty means no role resolves, which
means core fails closed: no non-administrator can read one of these records
until a society chooses the role. That is the correct pre-portal state. A
deployment names where the society is working and who it sent; a transfer names
somebody being moved. Defaulting to *some* role would be this app guessing at a
society's access policy. Administrators are unaffected by the framework
exemption, so there is always somebody who can set them, and core logs every
unresolved read so the closed state is visible rather than looking like nobody
having been granted anything yet.

A separate patch from `setup_deployment_module` for the same reason
membership's and volunteering's were separate from their own setups: one patch,
one concern, and a patch runs once per site by name.
"""

import frappe

from vmmsx.deployment.services.society import (
	DEPLOYMENT_SCOPE_ROLE_FIELD,
	REQUEST_SCOPE_ROLE_FIELD,
	TRANSFER_APPROVAL_MODE_FIELD,
	TRANSFER_SCOPE_ROLE_FIELD,
)

SETTINGS_DOCTYPE = "National Society Settings"

SCOPE_ROLES = (
	(
		DEPLOYMENT_SCOPE_ROLE_FIELD,
		"Deployment Scope Role",
		TRANSFER_APPROVAL_MODE_FIELD,
		"Which role may see VMMS Deployment records, and where, combined with that role's Geo"
		" Assignments. Left empty, no non-administrator can read a deployment at all. Owned by vmmsx.",
	),
	(
		REQUEST_SCOPE_ROLE_FIELD,
		"Deployment Request Scope Role",
		DEPLOYMENT_SCOPE_ROLE_FIELD,
		"Which role may see VMMS Deployment Request records, and where. A separate question from"
		" the one above: a society may well let coordinators see what is being deployed near them"
		" without letting them see who asked for it and why. Left empty, no non-administrator can"
		" read a request at all. Owned by vmmsx.",
	),
	(
		TRANSFER_SCOPE_ROLE_FIELD,
		"Branch Transfer Scope Role",
		REQUEST_SCOPE_ROLE_FIELD,
		"Which role may see VMMS Branch Transfer records, and where. Scoped on from_geo_node, the"
		" branch the volunteer is leaving, which is also where a routed transfer is approved by"
		" default. Note the consequence, which is intended: a transfer stays visible to the branch"
		" it moved somebody out of, because that is the branch it is a record about. Left empty, no"
		" non-administrator can read a transfer at all. Owned by vmmsx.",
	),
)


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	for fieldname, label, insert_after, description in SCOPE_ROLES:
		if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": fieldname}):
			continue

		create_custom_field(
			SETTINGS_DOCTYPE,
			{
				"fieldname": fieldname,
				"label": label,
				# A Link to Role, so the desk offers only roles that exist. Core
				# still validates the value on save: a Link can be left holding a
				# role that was later deleted.
				"fieldtype": "Link",
				"options": "Role",
				"insert_after": insert_after,
				"description": description,
			},
			ignore_validate=True,
		)
