# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""BUZZ-01 — install the geo-anchor custom field on Buzz's event doctype.

Dormant when Buzz is not installed on this site, the same graceful-absence
pattern the LMS and payments seams already use: vmmsx does not declare `buzz`
in `required_apps`, so a society running without it is ordinary, and this patch
must not throw or half-install anything for it. Idempotent otherwise — a second
run finds the field already there and changes nothing.
"""

import frappe

from vmmsx.buzz.services import geo

# What the field is called on Buzz's own event form, and what it used to be
# called. The fieldname never changes — it is the seam's contract — but the
# label is read by whoever creates an event, and "Geo Node" is core's word for
# the record rather than anything that means where the event is happening.
FIELD_LABEL = "Location"
LEGACY_LABEL = "Geo Node"


def execute():
	install_geo_anchor_field()


def install_geo_anchor_field() -> None:
	"""BUZZ-01. An event MAY be placed in the geo hierarchy — never must.

	Optional is the deliberate choice, not the default left unexamined.
	`Buzz Event` is Buzz's own doctype, created through Buzz's own native
	flows, which know nothing about vmmsx or a geo hierarchy. Making the anchor
	mandatory would force every event a society creates through Buzz — including
	a purely virtual one with no geographic scope at all — through a constraint
	this app invented, which is exactly the reverse of the leak this seam's
	docstring warns against: not vmmsx reading Buzz's model, but vmmsx imposing
	on it.
	"""
	if not geo.is_available():
		return

	existing = frappe.db.get_value(
		"Custom Field", {"dt": geo.EVENT_DOCTYPE, "fieldname": geo.GEO_NODE_FIELD}, "name"
	)

	if existing:
		# The field is there; only its wording may be out of date. It shipped
		# labelled "Geo Node", which is core's word for the record rather than
		# anything the person filling in an event form would recognise, and this
		# installer runs on every migrate precisely so a correction can reach a
		# site that already has the field. Nothing else about it is touched: a
		# society that has renamed the label to its own word keeps that.
		if frappe.db.get_value("Custom Field", existing, "label") == LEGACY_LABEL:
			frappe.db.set_value("Custom Field", existing, "label", FIELD_LABEL)
			frappe.clear_cache(doctype=geo.EVENT_DOCTYPE)

		return

	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	create_custom_field(
		geo.EVENT_DOCTYPE,
		{
			"fieldname": geo.GEO_NODE_FIELD,
			"label": FIELD_LABEL,
			"fieldtype": "Link",
			"options": "Geo Node",
			"insert_after": "venue",
			"description": (
				"BUZZ-01. Where this event sits in the society's geo hierarchy. Optional: an event"
				" may be placed in the hierarchy, but nothing requires it. Owned by vmmsx."
			),
		},
		ignore_validate=True,
	)
