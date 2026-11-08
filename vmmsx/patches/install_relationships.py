# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The relationship list an emergency contact picks from.

`VMMS Emergency Contact.relationship` was free text and is now a Link to
`VMMS Relationship`. Data and Link share the same varchar column, so nothing
stored moves; but a Link refuses a value with no record behind it, and an
application holding one could no longer be saved or approved.

So every value already stored gets a record before anything else. A value from
the standard list is offered as normal; anything else ("Auntie", a typo) is
kept, switched off, so its contact still saves and the form does not offer it.

A patch, run once, rather than an `after_migrate` hook: a society that deletes
"Neighbour" must not find it back after the next deploy.
"""

import frappe

DOCTYPE = "VMMS Relationship"

RELATIONSHIPS = (
	"Mother",
	"Father",
	"Sibling",
	"Spouse",
	"Child",
	"Guardian",
	"Other relative",
	"Friend",
	"Colleague",
	"Neighbour",
	"Other",
)


def execute():
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	frappe.reload_doc("vmms_registration", "doctype", "vmms_relationship")

	for index, label in enumerate(RELATIONSHIPS, start=1):
		_ensure(label, sequence=index * 10, active=True)

	if frappe.db.table_exists("VMMS Emergency Contact"):
		stored = frappe.get_all("VMMS Emergency Contact", pluck="relationship", distinct=True)
		for label in sorted({(value or "").strip() for value in stored} - {""}):
			_ensure(label, sequence=1000, active=False)


def _ensure(label: str, *, sequence: int, active: bool) -> None:
	# Exists is case-insensitive on MariaDB, so "sibling" finds "Sibling" and a
	# second, differently-cased record is never made.
	if frappe.db.exists(DOCTYPE, label):
		return

	frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"relationship_name": label,
			"sequence": sequence,
			"is_active": int(active),
		}
	).insert(ignore_permissions=True)
