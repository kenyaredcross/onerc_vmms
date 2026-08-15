# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The doctype permissions a self-service role needs, and not one more.

The self-service workspaces point at two ordinary desk list views — a volunteer's
time logs and their certifications — and a list view needs a DocPerm. Which role
holds it is a society's answer, read from settings; *what* it may do is this
app's, and it is `read` on two doctypes.

**Why only these two.** `VMMS Volunteer` and `VMMS Membership` are registered with
core as geo-scopeable, so a DocPerm on either would grant nothing: core fails
closed for somebody holding no Geo Assignment, and correctly, because the register
is not a volunteer's to browse. Their own record is reached through this app's
owner-bypassed endpoints instead. `VMMS Time Log` and `VMMS Certification` are not
geo-registered, so a DocPerm is the whole answer for them, and the User Permission
created alongside the role narrows what it returns to this person's own rows.

**Read, and nothing else.** Not create, not write, not delete. A volunteer looking
at the hours somebody recorded for them is a different act from recording them,
and a society that wants its volunteers filing their own time says so by adding
the permission. Widening by default would be this app deciding a society's
policy from a workspace layout.

The grants are Custom DocPerms, which is what an administrator adds through the
Role Permissions Manager. The shipped doctype JSONs still name only System
Manager, because which society role gets anything is configuration and a literal
in a JSON file is exactly what this app does not do.
"""

import frappe

# What a self-service role may read, so that the workspace built for it is not a
# list of permission errors. Both are unregistered with core's geo scoping; see
# the module docstring for why nothing geo-scoped appears here.
SELF_SERVICE_READABLE = ("VMMS Time Log", "VMMS Certification")

PERMISSION = "read"


def install() -> dict:
	"""Grant the configured volunteer self-service role its read permissions.

	Idempotent: a permission already granted is left alone, and an unconfigured
	or deleted role grants nothing. Called by the same patch and the same seed
	that build the workspaces, because a surface and the permission it needs are
	one decision.
	"""
	from vmmsx.volunteer.services import society as volunteer_society

	role = volunteer_society.volunteer_member_role()

	if not role:
		return {"role": None, "granted": [], "note": "no volunteer self-service role configured"}

	granted = [doctype for doctype in SELF_SERVICE_READABLE if grant_read(doctype, role)]

	return {"role": role, "granted": granted}


def grant_read(doctype: str, role: str) -> bool:
	"""Let `role` read `doctype`. Returns whether anything was added.

	`add_permission` returns falsy when a DocPerm for that role and level already
	exists, which is what makes re-running this cost nothing. The property is set
	explicitly afterwards regardless, so a row somebody created and then emptied
	is repaired rather than trusted.
	"""
	from frappe.permissions import add_permission, update_permission_property

	if not frappe.db.exists("DocType", doctype):
		return False

	added = bool(add_permission(doctype, role, 0))

	update_permission_property(doctype, role, 0, PERMISSION, 1)
	frappe.clear_cache(doctype=doctype)

	return added
