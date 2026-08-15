# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install the editable slots every screen has, and the role that may edit them.

Two things, both idempotent, and the difference between them matters:

1. **The surfaces and their blocks**, from `content/seeds/default_content.py`.
   Seeded, never refreshed: `blocks.seed()` creates what is missing and leaves
   everything else alone, so it cannot revert a sentence a society has
   rewritten.

   The work is `blocks.install_defaults()`, and the *scheduling* of it is now in
   `after_migrate` rather than in this patch. That was a correction: a patch
   runs once per site by name, so this file could only ever seed the slots that
   existed the day a site first migrated, and every slot added by a later
   release stayed missing on every existing site. The screen using one fell back
   to its hardcoded wording with no pencil on it, which is uneditable copy — the
   exact state this module exists to prevent, and invisible because a fallback
   renders perfectly. The call is left here as well so a fresh install has its
   content before anything else runs; both paths reach the same idempotent
   service.

2. **The settings field naming the role that may edit page content**, as a
   Custom Field vmmsx owns on core's National Society Settings. Not a literal
   role name in this file, for the reason the access model gives: which of a
   society's roles may reword the public home page is that society's decision.

   It ships **empty**, and empty means only System Manager can edit, which is
   the framework exemption rather than a policy this app invented. The pencil
   simply does not appear for anybody else until a society names a role, so the
   failure mode of an unconfigured site is a page that cannot be edited rather
   than one anybody can rewrite.

The permission grant itself is `install_content_editor_role`, a separate patch,
because the grant has to be re-applied whenever a society *changes* the setting
and a patch runs once. That one is wired into `after_migrate`.
"""

import frappe

from vmmsx.content.services import blocks as block_service

SETTINGS_DOCTYPE = "National Society Settings"

EDITOR_ROLE_FIELD = "vmms_content_editor_role"


def execute():
	install_editor_role_field()
	block_service.install_defaults()


def install_editor_role_field() -> None:
	"""Where a society says who may reword its pages."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": EDITOR_ROLE_FIELD}):
		return

	create_custom_field(
		SETTINGS_DOCTYPE,
		{
			"fieldname": EDITOR_ROLE_FIELD,
			"label": "Page Content Editor Role",
			# A Link to Role, so the desk offers only roles that exist.
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": "vmms_membership_scope_role",
			"description": (
				"Which role may edit the wording and photographs on the public landing page and"
				" throughout the portal, using the pencil that appears on the page. Left empty,"
				" only an administrator can. Owned by vmmsx."
			),
		},
		ignore_validate=True,
	)
