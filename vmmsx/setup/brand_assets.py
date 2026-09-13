# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Make National Society brand images public from the regular settings form."""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

SETTINGS_DOCTYPE = "National Society Settings"
PUBLIC_IMAGE_FIELDS = ("logo", "logo_dark", "favicon")
PROPERTY = "make_attachment_public"


def install() -> None:
	"""Apply public-upload metadata idempotently to every society brand image."""
	meta = frappe.get_meta(SETTINGS_DOCTYPE)

	for fieldname in PUBLIC_IMAGE_FIELDS:
		field = meta.get_field(fieldname)
		if not field or field.make_attachment_public:
			continue

		setter = frappe.db.get_value(
			"Property Setter",
			{"doc_type": SETTINGS_DOCTYPE, "field_name": fieldname, "property": PROPERTY},
			["name", "value"],
			as_dict=True,
		)
		if setter and str(setter.value) == "1":
			continue

		make_property_setter(SETTINGS_DOCTYPE, fieldname, PROPERTY, "1", "Check")

	frappe.clear_cache(doctype=SETTINGS_DOCTYPE)
