# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install what the Member module needs to exist before it can be configured.

Four things, all idempotent, all *seeds a society then edits* rather than
constants the code depends on:

1. **The ACC-03 anchor-level field** on core's National Society Settings, as a
   Custom Field. vmmsx owns the field and installs it; core's source is not
   touched, because a product pushing its own fields into the shared
   foundation's schema is how the foundation stops being shared. Left empty,
   which means "anchor anywhere" until a society narrows it.
2. **The template categories** — certificate, agreement, notification. A
   starting vocabulary, not a closed one: a society may add to it, and no source
   file branches on a category value.
3. **The default membership-certificate template**, seeded from
   `vmmsx/templating/seeds/`, not from a string in this file. It exists so a
   society has something that works on day one, and it is an ordinary editable
   record from the moment it lands.
4. **The `member` Affiliation Type**, so this app's satellite has somewhere to
   report on core's index.

Every step checks before it writes, so re-running the patch — which migrate will
do on a site that already has all four — changes nothing and overwrites nothing
an administrator has since edited.
"""

from pathlib import Path

import frappe

from vmmsx.member.services.member import MEMBER_AFFILIATION_KEY
from vmmsx.member.services.society import ANCHOR_LEVEL_FIELD

SETTINGS_DOCTYPE = "National Society Settings"

SEED_DIR = Path(__file__).resolve().parents[1] / "templating" / "seeds"

CERTIFICATE_TEMPLATE_KEY = "membership_certificate"
CERTIFICATE_CATEGORY_KEY = "certificate"

# The starting vocabulary. Seeded, then owned by the society.
TEMPLATE_CATEGORIES = (
	("certificate", "Certificate", "Issued as evidence — a membership certificate, an award."),
	("agreement", "Agreement", "Signed by a person — a volunteer agreement, a code of conduct."),
	("notification", "Notification", "Sent to a person — an email or a message body."),
)


def execute():
	install_anchor_level_field()
	install_template_categories()
	install_certificate_template()
	install_member_affiliation_type()


def install_anchor_level_field() -> None:
	"""ACC-03 — where a society says memberships may be anchored."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": ANCHOR_LEVEL_FIELD}):
		return

	create_custom_field(
		SETTINGS_DOCTYPE,
		{
			"fieldname": ANCHOR_LEVEL_FIELD,
			"label": "Membership Anchor Level",
			"fieldtype": "Link",
			"options": "Geo Level",
			"insert_after": "phone_number_example",
			"description": (
				"ACC-03. The geo level a VMMS Membership must be anchored at. Left empty, a"
				" membership may be anchored at any level — this narrows it, it does not enable"
				" it. Owned by vmmsx."
			),
		},
		ignore_validate=True,
	)


def install_template_categories() -> None:
	for key, name, description in TEMPLATE_CATEGORIES:
		if frappe.db.exists("VMMS Template Category", key):
			continue

		frappe.get_doc(
			{
				"doctype": "VMMS Template Category",
				"category_key": key,
				"category_name": name,
				"description": description,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)


def install_certificate_template() -> None:
	"""Seed the default certificate — from a file, never from a Python string."""
	if frappe.db.exists("VMMS Template", CERTIFICATE_TEMPLATE_KEY):
		return

	body = (SEED_DIR / "membership_certificate.html").read_text()

	frappe.get_doc(
		{
			"doctype": "VMMS Template",
			"template_key": CERTIFICATE_TEMPLATE_KEY,
			"template_name": "Membership Certificate",
			"template_category": CERTIFICATE_CATEGORY_KEY,
			"subject": "Certificate of Membership",
			"body": body,
			"output_format": "html",
			"is_active": 1,
			"description": (
				"The default membership certificate. Context keys: member_name, membership_id,"
				" membership_type, geo_path, valid_from, valid_to, benefits, society_name,"
				" society_logo, issued_on, payment_receipt, payment_transaction. Edit freely —"
				" nothing in the code depends on this wording."
			),
		}
	).insert(ignore_permissions=True)


def install_member_affiliation_type() -> None:
	"""The vocabulary entry this app's satellite reports under."""
	if frappe.db.exists("Affiliation Type", MEMBER_AFFILIATION_KEY):
		return

	frappe.get_doc(
		{
			"doctype": "Affiliation Type",
			"affiliation_type_key": MEMBER_AFFILIATION_KEY,
			"affiliation_type_name": "Member",
			"description": "A member of the national society. Owned by vmmsx's VMMS Member satellite.",
			"is_active": 1,
		}
	).insert(ignore_permissions=True)
