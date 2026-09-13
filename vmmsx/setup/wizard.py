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
