# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Somebody responsible for the whole country: sees all of it, edits none of it.

The regional oversight role (`regional_oversight.py`) is held through a Geo
Assignment at a region. Somebody could be given that same role at the top of
the tree and they would read the country. But the society wants these people
identified by what they are, not by where they happen to be assigned. Kenya Red
Cross calls them NSD Coordinators (National Society Development). So this is a
role of its own, and **holding it is the whole grant**: no Geo Assignment is
needed or read.

The role:

- **reads** every scoped register, everywhere. Core's
  `national_read_role_from_setting` adds it to each registration in `hooks.py`.
  Like the regional reading role, it widens who may open a record and never who
  may change it;
- has **read, report and print** DocPerms on the same doctypes as the regional
  role, and nothing more;
- opens the National tab and every region's tab, and receives the national
  weekly summary of approvals waiting too long;
- approves nothing. No workflow stage is routed to it.

Named in a setting like every other role this app reads, with the shipped
default `NSD Coordinator`. Idempotent and additive, run from `after_migrate`:
an existing role, field, value or permission is never changed.
"""

import frappe

from vmmsx.setup.regional_oversight import ROLE_FIELD as REGIONAL_ROLE_FIELD
from vmmsx.setup.regional_oversight import SETTINGS_DOCTYPE, grant_read

ROLE_FIELD = "vmms_national_oversight_role"
ROLE_NSD_COORDINATOR = "NSD Coordinator"


def install() -> None:
	_role()
	_field()
	_default()
	grant_read(frappe.db.get_single_value(SETTINGS_DOCTYPE, ROLE_FIELD))
	frappe.clear_cache(doctype=SETTINGS_DOCTYPE)


def role() -> str | None:
	"""The society's national oversight role, or None if it has not named one."""
	from onerc_core.society.services import config

	return (config.settings().get(ROLE_FIELD) or "").strip() or None


def holds(user: str | None = None) -> bool:
	"""Does this person hold the national oversight role?"""
	name = role()

	return bool(name and name in frappe.get_roles(user or frappe.session.user))


def holders() -> list[str]:
	"""Enabled users holding the national oversight role."""
	name = role()

	if not name:
		return []

	return sorted(
		frappe.db.sql_list(
			"""
			SELECT DISTINCT user.name
			FROM `tabHas Role` has_role
			INNER JOIN `tabUser` user ON user.name = has_role.parent
			WHERE has_role.parenttype = 'User'
				AND has_role.role = %(role)s
				AND user.enabled = 1
				AND user.name NOT IN ('Administrator', 'Guest')
			""",
			{"role": name},
		)
	)


def core_reads_nationally() -> bool:
	"""Does the installed onerc_core let the national role read everywhere?

	Like the regional reading role, this is applied per site from
	`deploy/onerc_core-read-role/`. Without it the role still opens the National
	tab, but core admits its holders to no records, so the figures are empty.
	"""
	from onerc_core.access.services import registry

	return hasattr(registry, "NATIONAL_READ_ROLE_SETTING_KEY")


def _role() -> None:
	if frappe.db.exists("Role", ROLE_NSD_COORDINATOR):
		return

	frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": ROLE_NSD_COORDINATOR,
			"desk_access": 1,
			"description": (
				"Oversees the whole country: sees every region's volunteers, members,"
				" applications, materials and deployments, and edits none of them."
				" Needs no Geo Assignment."
			),
		}
	).insert(ignore_permissions=True)


def _field() -> None:
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": ROLE_FIELD}):
		return

	create_custom_field(
		SETTINGS_DOCTYPE,
		{
			"fieldname": ROLE_FIELD,
			"label": "National Oversight Role",
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": REGIONAL_ROLE_FIELD,
			"description": (
				"Who sees every region and county in the country, without editing."
				" Holding the role is enough; no Geo Assignment is needed. Owned by vmmsx."
			),
		},
		ignore_validate=True,
	)


def _default() -> None:
	if not frappe.get_meta(SETTINGS_DOCTYPE).has_field(ROLE_FIELD):
		return

	if frappe.db.get_single_value(SETTINGS_DOCTYPE, ROLE_FIELD):
		return

	frappe.db.set_single_value(SETTINGS_DOCTYPE, ROLE_FIELD, ROLE_NSD_COORDINATOR)
