# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The vmmsx contribution to Frappe's first-run setup wizard.

Identity stays in onerc_core's National Society Settings and geography stays in
its Geo Level model.  The wizard is only a friendlier way of writing those
existing sources of truth; it deliberately introduces no VMMS copy of either.
"""

import re

import frappe
from frappe import _

from vmmsx.member.services.society import ANCHOR_LEVEL_FIELD as MEMBER_ANCHOR_FIELD
from vmmsx.setup import default_roles
from vmmsx.volunteer.services.society import ANCHOR_LEVEL_FIELD as VOLUNTEER_ANCHOR_FIELD

SETTINGS_DOCTYPE = "National Society Settings"


def get_setup_stages(args=None):  # nosemgrep
	"""Return one atomic setup task for Frappe's multi-app wizard engine."""
	return [
		{
			"status": _("Setting up your National Society"),
			"fail_msg": _("Failed to set up your National Society"),
			"tasks": [
				{
					"fn": setup_national_society,
					"args": args or {},
					"fail_msg": _("Failed to set up your National Society"),
				}
			],
		}
	]


def setup_national_society(args):  # nosemgrep
	"""Save identity, create the level ladder, and set both intake anchors."""
	args = frappe._dict(args or {})
	levels = _level_names(args)
	if not levels:
		# A multi-app setup may resume after our task succeeded but before a later
		# app finished. Frappe normally skips a completed app; tolerate stale app
		# completion metadata too when the full VMMS configuration is already there.
		if _already_configured():
			return
		frappe.throw(_("Add at least one geographic level."))

	level_keys = [_ensure_level(name, order, order == len(levels)) for order, name in enumerate(levels, 1)]
	anchor_order = int(args.get("vmms_application_anchor_order") or len(level_keys))
	if anchor_order < 1 or anchor_order > len(level_keys):
		frappe.throw(_("Choose an application level from the geographic hierarchy you entered."))

	settings = frappe.get_single(SETTINGS_DOCTYPE)
	settings.update(
		{
			"organization_name": (args.get("vmms_organization_name") or "").strip(),
			"organization_short_name": (args.get("vmms_organization_short_name") or "").strip(),
			"country": args.get("country"),
			"primary_language": _language_code(args.get("language")),
			"logo": args.get("vmms_logo"),
			MEMBER_ANCHOR_FIELD: level_keys[anchor_order - 1],
			VOLUNTEER_ANCHOR_FIELD: level_keys[anchor_order - 1],
		}
	)
	settings.save(ignore_permissions=True)
	_ensure_national_node(level_keys[0], settings.organization_name)

	# The role wiring could not run at install time, and this is the first moment
	# it can. `default_roles.install()` saves this same Single, and on a fresh site
	# the four identity fields above are mandatory and empty — the app ships with
	# no society on it — so `after_install` caught the MandatoryError, logged it and
	# carried on. Nothing re-runs it afterwards: this app declares
	# `setup_wizard_stages` and not `setup_wizard_complete`, so without this call
	# the six scope-role settings stay blank until somebody thinks to run
	# `bench migrate`, and a blank `vmms_volunteer_scope_role` is an access model
	# with nothing in it — no console section, and an approval that routes to
	# nobody. Idempotent, and it fills blanks only, so a society that has already
	# chosen its own roles keeps them.
	default_roles.install()


def _level_names(args) -> list[str]:
	"""Read the unlimited hierarchy editor's JSON value."""
	try:
		rows = frappe.parse_json(args.get("vmms_geo_levels_json") or "[]")
	except TypeError, ValueError:
		frappe.throw(_("The geographic hierarchy could not be read. Please review its levels."))

	return [
		name for row in rows if (name := ((row.get("label") if isinstance(row, dict) else row) or "").strip())
	]


def _language_code(language: str | None) -> str | None:
	"""Turn the wizard's display label into National Society Settings' Link key."""
	if not language:
		return None
	return frappe.db.get_value("Language", {"language_name": language}) or language


def _already_configured() -> bool:
	settings = frappe.get_single(SETTINGS_DOCTYPE)
	return bool(
		settings.organization_name
		and settings.organization_short_name
		and settings.country
		and settings.primary_language
		and settings.logo
		and settings.get(MEMBER_ANCHOR_FIELD)
		and settings.get(VOLUNTEER_ANCHOR_FIELD)
		and frappe.db.exists("Geo Level", settings.get(MEMBER_ANCHOR_FIELD))
		and frappe.db.exists("Geo Level", settings.get(VOLUNTEER_ANCHOR_FIELD))
	)


def _ensure_national_node(top_level: str, organization_name: str) -> str:
	"""Create the one parentless national root for a newly configured society.

	The level ladder alone does not give the portal a selectable location. On a
	setup retry, keep the existing root and all child nodes rather than making
	a second national tree. A root is organisational, so it is always a group.
	"""
	existing = frappe.db.get_value(
		"Geo Node", {"geo_level": top_level, "parent_geo_node": ("is", "not set")}, "name"
	)
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Geo Node",
				"geo_node_name": organization_name,
				"geo_level": top_level,
				"is_group": 1,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _ensure_level(label: str, order: int, is_lowest: bool) -> str:
	"""Create a level once and return its stable key.

	A repeated wizard submission can happen after a browser retry. Matching the
	label first makes that retry idempotent; generating a suffix avoids taking an
	existing key that belongs to a differently named level.
	"""
	existing = frappe.db.get_value("Geo Level", {"geo_level_name": label}, "name")
	if existing:
		return existing

	base = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or f"level_{order}"
	key = base
	suffix = 2
	while frappe.db.exists("Geo Level", key):
		key = f"{base}_{suffix}"
		suffix += 1

	doc = frappe.get_doc(
		{
			"doctype": "Geo Level",
			"geo_level_name": label,
			"geo_level_key": key,
			"geo_level_order": order,
			"requires_parent": int(order > 1),
			"is_lowest_level": int(is_lowest),
			"is_active": 1,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name
