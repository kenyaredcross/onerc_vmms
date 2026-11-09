# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Whether a society issues volunteer cards, who signs its membership
certificates, and the certificate that carries the Fundamental Principles.

**The card switch.** Some societies issue no volunteer card (Kenya). On by
default, so a society that has never opened the setting keeps the card it had.
Off, the card is not shown on the portal home, the profile or a volunteer's
record in the console, is not attached to the approval letter, and the server
refuses to render it.

**The signatures.** Two pictures and two titles, printed above and under the two
signature lines of the membership certificate. Empty is ordinary: the line is
left blank to be signed by hand. A society that changes signatory uploads the new
picture and every certificate printed afterwards carries it — nothing about a
certificate is stored.

**The template.** Seeded from a file, once, as an ordinary editable record. A
membership type uses it by naming it as its Certificate Template; nothing here
points any type at it.

Custom Fields vmmsx owns on core's National Society Settings. Core's doctype is
not edited.
"""

from pathlib import Path

import frappe

SETTINGS_DOCTYPE = "National Society Settings"
TEMPLATE_DOCTYPE = "VMMS Template"
TEMPLATE_KEY = "membership_certificate_principles"
SEED = Path(frappe.get_app_path("vmmsx")) / "templating" / "seeds" / "membership_certificate_principles.html"

CONTEXT_KEYS = (
	"member_name, membership_id, membership_type, geo_path, valid_from, valid_to, benefits,"
	" society_name, society_logo, issued_on, enrolled_day, enrolled_month, enrolled_year,"
	" signature_left, signature_right, signatory_left, signatory_right, blackletter_font"
)

FIELDS = (
	{
		"fieldname": "vmms_issues_volunteer_cards",
		"label": "Issues Volunteer Cards",
		"fieldtype": "Check",
		"default": "1",
		"insert_after": "vmms_certificate_print_role",
		"description": (
			"Off when the society issues no volunteer card. The card is then not shown, printed"
			" or attached anywhere. Owned by vmmsx."
		),
	},
	{
		"fieldname": "vmms_certificate_signatures_section",
		"label": "Certificate Signatures",
		"fieldtype": "Section Break",
		"insert_after": "vmms_issues_volunteer_cards",
	},
	{
		"fieldname": "vmms_certificate_signatory_left",
		"label": "Left Signatory Title",
		"fieldtype": "Data",
		"insert_after": "vmms_certificate_signatures_section",
		"description": "Printed under the left signature line, for example The Governor.",
	},
	{
		"fieldname": "vmms_certificate_signature_left",
		"label": "Left Signature",
		"fieldtype": "Attach Image",
		"insert_after": "vmms_certificate_signatory_left",
		"description": (
			"A picture of the signature, printed above the left line of the membership certificate."
			" Leave empty to sign by hand. A transparent PNG prints best."
		),
	},
	{
		"fieldname": "vmms_certificate_signatures_column",
		"fieldtype": "Column Break",
		"insert_after": "vmms_certificate_signature_left",
	},
	{
		"fieldname": "vmms_certificate_signatory_right",
		"label": "Right Signatory Title",
		"fieldtype": "Data",
		"insert_after": "vmms_certificate_signatures_column",
		"description": "Printed under the right signature line, for example Secretary General.",
	},
	{
		"fieldname": "vmms_certificate_signature_right",
		"label": "Right Signature",
		"fieldtype": "Attach Image",
		"insert_after": "vmms_certificate_signatory_right",
		"description": (
			"A picture of the signature, printed above the right line of the membership certificate."
			" Leave empty to sign by hand."
		),
	},
)


def execute():
	install_fields()
	install_template()


def install_fields() -> None:
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if not frappe.db.exists("DocType", SETTINGS_DOCTYPE):
		return

	for definition in FIELDS:
		if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": definition["fieldname"]}):
			continue

		field = dict(definition)
		meta = frappe.get_meta(SETTINGS_DOCTYPE)
		if not meta.has_field(field["insert_after"]):
			field.pop("insert_after")

		create_custom_field(SETTINGS_DOCTYPE, field, ignore_validate=True)
		frappe.clear_cache(doctype=SETTINGS_DOCTYPE)


def install_template() -> None:
	"""Seed the principles certificate, once. An edited one is the society's."""
	if not frappe.db.exists("DocType", TEMPLATE_DOCTYPE) or frappe.db.exists(TEMPLATE_DOCTYPE, TEMPLATE_KEY):
		return

	from vmmsx.patches.setup_member_module import CERTIFICATE_CATEGORY_KEY

	frappe.get_doc(
		{
			"doctype": TEMPLATE_DOCTYPE,
			"template_key": TEMPLATE_KEY,
			"template_name": "Membership Certificate with the Fundamental Principles",
			"template_category": CERTIFICATE_CATEGORY_KEY,
			"subject": "Membership Certificate",
			"body": SEED.read_text(),
			"output_format": "html",
			"is_active": 1,
			"description": (
				"A framed certificate carrying the seven Fundamental Principles and two signature"
				" lines. Its title is the membership type's benefit ending in Certificate, for"
				f" example Life Membership Certificate. Context keys: {CONTEXT_KEYS}. Edit freely."
			),
		}
	).insert(ignore_permissions=True)
