# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Somebody responsible for a region: sees all of it, edits none of it.

A County Coordinator acts in one county. The person above them (Kenya Red
Cross calls them Head of Region) has to see every county in the region (its
volunteers, members, applications, materials and deployments) without being
made the officer who edits them. Giving them the county roles at region level
would have done the seeing and handed over the editing, the approving and the
material issuing with it.

So this is one role, held through a Geo Assignment at the region, that:

- **reads** the scoped registers in that region. Core's
  `read_role_from_setting` adds it to each registration in `hooks.py` as a
  reading role: it widens who may open a record and never who may change it;
- has **read, report and print** DocPerms on those doctypes and nothing more;
- approves memberships only where the society's workflow routes a stage to it,
  and that authority comes from the engine, not from any write permission.

The role is named in a setting, like every other role this app reads, so a
society may point it at a role of its own. The shipped default is
`Head of Region`.

Idempotent and additive, run from `after_migrate`: an existing role, field,
value or permission is never changed.
"""

import frappe

SETTINGS_DOCTYPE = "National Society Settings"
ROLE_FIELD = "vmms_regional_oversight_role"
ROLE_HEAD_OF_REGION = "Head of Region"

# What the role reads. The first group is geo-scoped through core and carries
# the reading role in `hooks.py`; the rest are not scoped at all and are read
# by the county roles in the same way today.
READ_DOCTYPES = (
	"VMMS Volunteer",
	"VMMS Volunteer Application",
	"VMMS Membership",
	"VMMS Branch Asset",
	"VMMS Asset Transaction",
	"VMMS Deployment",
	# The programme a deployment runs under, the people on it and the requests
	# for one: the Operations screens a regional head opens beside the
	# deployments themselves. Scoped through core like the deployment.
	"Project",
	"VMMS Deployment Assignment",
	"VMMS Deployment Request",
	"VMMS Member",
	"VMMS Membership Type",
	"VMMS Membership Benefit",
	# Not scoped, and read by the county roles the same way.
	"VMMS Terms of Reference",
)


# The weekly approval summary's two settings. See approvals/services/digest.py.
DIGEST_FIELDS = (
	{
		"fieldname": "vmms_approval_digest_weekday",
		"label": "Weekly Approval Summary Day",
		"fieldtype": "Select",
		"options": "Monday\nTuesday\nWednesday\nThursday\nFriday\nSaturday\nSunday",
		"default": "Monday",
		"insert_after": ROLE_FIELD,
		"description": "The morning the weekly approval summaries are sent.",
	},
	{
		"fieldname": "vmms_approval_oversight_days",
		"label": "National Oversight After (Days)",
		"fieldtype": "Int",
		"default": "14",
		"insert_after": "vmms_approval_digest_weekday",
		"description": (
			"National staff are sent a weekly count of approvals waiting longer than this."
			" Applications sent back for more information are counted separately."
		),
	},
)


# The county shapes the Region and National maps draw. See
# analytics/services/boundaries.py for what may be attached and how it is read.
MAP_FIELDS = (
	{
		"fieldname": "vmms_boundary_file",
		"label": "County Boundaries",
		"fieldtype": "Attach",
		"insert_after": "vmms_approval_oversight_days",
		"description": (
			"A GeoJSON file of the counties, or a zip of them as published on HDX. Shapes are matched"
			" to counties by code or by name. Without it the maps show a dot for each county."
		),
	},
	{
		"fieldname": "vmms_boundary_credit",
		"label": "County Boundaries Source",
		"fieldtype": "Data",
		"insert_after": "vmms_boundary_file",
		"description": "Shown under the maps, as the file's licence asks. For example: Boundaries: IEBC, via OCHA (CC BY-IGO).",
	},
)


def install() -> None:
	_role()
	_field()
	_digest_fields()
	_default()
	_permissions()
	frappe.clear_cache(doctype=SETTINGS_DOCTYPE)


def _digest_fields() -> None:
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	for field in (*DIGEST_FIELDS, *MAP_FIELDS):
		if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": field["fieldname"]}):
			continue

		create_custom_field(SETTINGS_DOCTYPE, dict(field), ignore_validate=True)


def core_reads_through_oversight_role() -> bool:
	"""Does the installed onerc_core let the oversight role read?

	The reading role is an onerc_core capability that is not committed there;
	it is applied per site from `deploy/onerc_core-read-role/`. Without it the
	role still exists and still routes the regional approval stage, but core
	admits its holders to no records, so they see nothing.
	"""
	from onerc_core.access.services import registry

	return hasattr(registry, "READ_ROLE_SETTING_KEY")


def role() -> str | None:
	"""The society's regional oversight role, or None if it has not named one."""
	from onerc_core.society.services import config

	return (config.settings().get(ROLE_FIELD) or "").strip() or None


def _role() -> None:
	if frappe.db.exists("Role", ROLE_HEAD_OF_REGION):
		return

	frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": ROLE_HEAD_OF_REGION,
			"desk_access": 1,
			"description": (
				"Oversees every county in the region they are assigned to: sees volunteers,"
				" members, applications, materials and deployments, edits none of them, and"
				" approves memberships where the workflow routes a regional stage to them."
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
			"label": "Regional Oversight Role",
			"fieldtype": "Link",
			"options": "Role",
			"insert_after": "vmms_membership_scope_role",
			"description": (
				"Who sees every county in the region they are assigned to, without editing."
				" Combined with that role's Geo Assignments. Owned by vmmsx."
			),
		},
		ignore_validate=True,
	)


def _default() -> None:
	if not frappe.get_meta(SETTINGS_DOCTYPE).has_field(ROLE_FIELD):
		return

	if frappe.db.get_single_value(SETTINGS_DOCTYPE, ROLE_FIELD):
		return

	frappe.db.set_single_value(SETTINGS_DOCTYPE, ROLE_FIELD, ROLE_HEAD_OF_REGION)


def _permissions() -> None:
	"""Read, report and print on each doctype, for the role the setting names."""
	grant_read(frappe.db.get_single_value(SETTINGS_DOCTYPE, ROLE_FIELD))


def grant_read(name: str | None) -> None:
	"""Read, report and print on each of READ_DOCTYPES for `name`. Never more.

	Shared with the national oversight role, which reads the same registers.
	"""
	from frappe.permissions import add_permission, update_permission_property

	if not (name and frappe.db.exists("Role", name)):
		return

	for doctype in READ_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue

		if frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": name, "permlevel": 0}):
			continue

		add_permission(doctype, name, 0)
		for ptype in ("report", "print"):
			update_permission_property(doctype, name, 0, ptype, 1, validate=False)
