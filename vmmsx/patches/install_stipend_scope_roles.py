# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install the settings fields that say which roles may see stipend paperwork.

vmmsx registers both of the Stipend module's doctypes as geo-scopeable through
core's `onerc_scopeable_doctypes` hook, and names each role with
`role_from_setting` rather than a literal — because *which* of a society's roles
may read what a branch did last month, and what it paid for it, is a society's
decision, not this app's. Core resolves each field's value at enforcement time.

**Two fields, because these are two questions.** A narrative of a period of work
and the money paid for it are read by different people in most societies. Folding
them into one setting would make that impossible to express, and the wrong way
round: a society that wanted every coordinator to read the narrative would have
to show them the payments as well.

Each is a **Custom Field owned by vmmsx**, exactly like the anchor levels and the
scope roles before it. Core's National Society Settings doctype is not edited.

**Both are deliberately left empty.** Empty means no role resolves, which means
core fails closed: no non-administrator can read one of these records until a
society chooses the role. That is the correct pre-portal state, and a stronger
case than most — a payment form names people and the sums paid to them.
Administrators are unaffected by the framework exemption, so there is always
somebody who can set them, and core logs every unresolved read so the closed
state is visible rather than looking like nobody having been granted anything
yet.

**Geo scoping is the whole of the access model for these two doctypes**, and it
is deliberately not joined by the approval engine's person-gate. Stipend approval
is departmental, the engine resolves approvers by walking up the geo tree, and no
workflow governs these doctypes; see `vmmsx/stipend/services/approval.py`. That
makes these two settings the only thing standing between a payment form and
somebody who should not read it, which is why they fail closed.

A separate patch from `setup_stipend_module` for the same reason the earlier
modules' were separate from their own setups: one patch, one concern, and a patch
runs once per site by name.
"""

import frappe

from vmmsx.stipend.services.society import (
	ANCHOR_LEVEL_FIELD,
	PAYMENT_SCOPE_ROLE_FIELD,
	REPORT_SCOPE_ROLE_FIELD,
)

SETTINGS_DOCTYPE = "National Society Settings"

SCOPE_ROLES = (
	(
		REPORT_SCOPE_ROLE_FIELD,
		"Stipend Report Scope Role",
		ANCHOR_LEVEL_FIELD,
		"Which role may see VMMS Stipend Progress Report records, and where, combined with that"
		" role's Geo Assignments. Left empty, no non-administrator can read a progress report at"
		" all. Owned by vmmsx.",
	),
	(
		PAYMENT_SCOPE_ROLE_FIELD,
		"Stipend Payment Scope Role",
		REPORT_SCOPE_ROLE_FIELD,
		"Which role may see VMMS Stipend Payment Form records, and where. A separate question from"
		" the one above, and usually a narrower answer: a payment form names people and the sums"
		" paid to them, and a society may well let coordinators read the narrative of a period"
		" without reading its payroll. Left empty, no non-administrator can read a payment form at"
		" all. Owned by vmmsx.",
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
				# A Link to Role, so the desk offers only roles that exist. Core
				# still validates the value on save: a Link can be left holding a
				# role that was later deleted.
				"label": label,
				"fieldtype": "Link",
				"options": "Role",
				"insert_after": insert_after,
				"description": description,
			},
			ignore_validate=True,
		)
