# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Grant the society's chosen content-editor role write access to the wording.

Run from `after_migrate` rather than from a patch, and that is the whole point
of the module. A patch runs once per site by name, but the setting this reads is
one a society changes whenever it reorganises: naming a different role a year
later has to actually grant that role something, and a patch that already ran
never will.

So the shape is the one `registration/services/permissions.py` already uses
here: read the setting, grant what it names, and do nothing at all when it is
empty. Nothing is ever revoked. Withdrawing a role's access is an act with
consequences a migrate should not perform on its own, and a society that
renames a role would otherwise find its editors locked out by a deploy.

The floor is System Manager, which the doctypes carry in their own JSON. That is
a framework role rather than a society role, so naming it is the documented
exemption, not a hardcoded society role.
"""

import frappe

CONTENT_DOCTYPES = ("VMMS Content Block", "VMMS Content Surface")

SETTINGS_DOCTYPE = "National Society Settings"

EDITOR_ROLE_FIELD = "vmms_content_editor_role"


def configured_role() -> str | None:
	"""The role a society named, if it named one that still exists.

	A Link field can be left holding a role somebody has since deleted, so the
	existence check is not defensive noise: granting permissions to a missing
	role throws, and it would throw during a migrate.
	"""
	if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
		return None

	role = frappe.db.get_single_value(SETTINGS_DOCTYPE, EDITOR_ROLE_FIELD)

	if not role or not frappe.db.exists("Role", role):
		return None

	return role


def install() -> None:
	"""Give the configured role read and write on the content doctypes.

	Read and write, but not create or delete: an editor rewords the slots the
	product defines. Adding and removing slots changes what the pages render and
	belongs with whoever administers the site.
	"""
	role = configured_role()

	if not role:
		return

	for doctype in CONTENT_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue

		_grant(doctype, role)

	frappe.clear_cache()


def _grant(doctype: str, role: str) -> None:
	"""One permission row, created if absent and topped up if present.

	`add_permission` is a no-op when the row already exists, so the levels are
	set explicitly afterwards. Both calls are safe to repeat, which is what lets
	this run on every migrate.
	"""
	from frappe.permissions import add_permission, update_permission_property

	add_permission(doctype, role, 0)

	for ptype in ("read", "write"):
		update_permission_property(doctype, role, 0, ptype, 1)
