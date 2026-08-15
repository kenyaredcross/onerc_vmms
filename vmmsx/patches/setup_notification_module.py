# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install the settings field that says which role may broadcast, and where.

vmmsx registers `VMMS Announcement` as geo-scopeable through core's
`onerc_scopeable_doctypes` hook and names its role with `role_from_setting`
rather than a literal, for the reason the access model gives: which of a
society's roles may speak on behalf of a branch is that society's decision, and
a role name in a source file is exactly what ACC-03 and the access model forbid.

**Scoping an announcement is a stronger control here than it is elsewhere.** For
a membership, geo scoping decides who may *read* a record. For an announcement
it also decides, through core's Geo Assignment, who may *write* one and from
where — and writing one sends a message to every volunteer and member beneath
that node. A branch coordinator assigned at a branch can announce to their
branch; they cannot announce to the country, because the node they anchor to has
to be one their assignment covers.

**It ships empty, and empty fails closed.** No role resolves, so no
non-administrator can broadcast anything until a society names the role. That is
the right default for a system whose failure mode is an unauthorised message
arriving in fifty thousand inboxes with the national society's name on it. The
framework exemption means an administrator can always set it.

The announcement *types* are not seeded. News, Alert, Advisory read like
obvious defaults and are not: they are a society's own vocabulary, the same as
`VMMS Template Category` and `VMMS Time Log Category`, and shipping three
English nouns would be this app deciding what a national society calls the
things it sends. `vmmsx/seed/kenya.py` is where a worked example belongs.
"""

import frappe

SETTINGS_DOCTYPE = "National Society Settings"

SCOPE_ROLE_FIELD = "vmms_announcement_scope_role"


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": SCOPE_ROLE_FIELD}):
		return

	create_custom_field(
		SETTINGS_DOCTYPE,
		{
			"fieldname": SCOPE_ROLE_FIELD,
			"label": "Announcement Scope Role",
			# A Link to Role, so the desk offers only roles that exist. Core
			# still validates the value on save, since a Link can be left
			# holding a role that was later deleted.
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": "vmms_content_editor_role",
			"description": (
				"Which role may write and send announcements, and from which part of the"
				" hierarchy, combined with that role's Geo Assignments. An announcement reaches"
				" everybody at or beneath the node it is sent from. Left empty, only an"
				" administrator can send one. Owned by vmmsx."
			),
		},
		ignore_validate=True,
	)
