# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The surge roster's doors. Thin: what an entry means is `volunteer/services/surge.py`.

Every door checks the **volunteer**, not the entry. An entry carries no geo
anchor of its own; who may see or change it is who may see or change the
person it is about, which is Frappe's roles plus core's geo scoping on
`VMMS Volunteer`. Reads ask `read`, acts ask `write`, the same split
`api/volunteer.py` draws between `_readable` and `_writable`.
"""

import frappe

from vmmsx.volunteer.services import surge

VOLUNTEER_DOCTYPE = "VMMS Volunteer"


@frappe.whitelist()
def surge_roster(
	geo_node: str | None = None, profession: str | None = None, search: str | None = None
) -> dict:
	"""The roster inside the caller's scope, grouped by profession."""
	return surge.roster(geo_node=geo_node, profession=profession, search=search)


@frappe.whitelist()
def add_to_surge_roster(
	volunteer: str,
	profession: str | None = None,
	licence_number: str | None = None,
	issuing_body: str | None = None,
	licence_expiry: str | None = None,
	licence_document: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Put a volunteer on the roster after checking their licence."""
	doc = _writable_volunteer(volunteer)
	entry = surge.add(
		doc,
		profession=profession,
		licence_number=licence_number,
		issuing_body=issuing_body,
		licence_expiry=licence_expiry,
		licence_document=licence_document,
		notes=notes,
	)

	return _answer(entry)


@frappe.whitelist()
def renew_surge_licence(
	name: str,
	licence_number: str | None = None,
	issuing_body: str | None = None,
	licence_expiry: str | None = None,
	licence_document: str | None = None,
) -> dict:
	"""Record a renewed licence for somebody already on the roster."""
	entry = _writable_entry(name)
	surge.renew(entry, licence_number, issuing_body, licence_expiry, licence_document)

	return _answer(entry)


@frappe.whitelist()
def stand_down_from_surge(name: str, reason: str | None = None) -> dict:
	"""Take somebody off the roster, with a reason. The entry is kept."""
	entry = _writable_entry(name)
	surge.stand_down(entry, reason)

	return _answer(entry)


@frappe.whitelist()
def licence_copy(name: str, inline: str | int | None = None) -> None:
	"""Open the copy of the licence on a roster entry, for whoever may read the volunteer.

	The file is private and the entry doctype is not readable on its own, so
	reading the volunteer is the permission, as `download_evidence` does for
	registration files. Only the file this entry names can be fetched here.
	"""
	entry = frappe.get_doc(surge.ENTRY_DOCTYPE, name)
	frappe.get_doc(VOLUNTEER_DOCTYPE, entry.volunteer).check_permission("read")

	if not entry.licence_document:
		frappe.throw(frappe._("No copy of the licence is on file."), frappe.DoesNotExistError)

	file_name = frappe.db.get_value(
		"File",
		{
			"file_url": entry.licence_document,
			"attached_to_doctype": entry.doctype,
			"attached_to_name": entry.name,
		},
		"name",
	) or frappe.db.get_value("File", {"file_url": entry.licence_document}, "name")

	if not file_name:
		frappe.throw(frappe._("No copy of the licence is on file."), frappe.DoesNotExistError)

	file = frappe.get_doc("File", file_name)
	frappe.local.response.filename = file.file_name
	frappe.local.response.filecontent = file.get_content()
	frappe.local.response.type = "download"
	frappe.local.response.display_content_as = "inline" if frappe.utils.cint(inline) else "attachment"


def _writable_volunteer(name: str):
	doc = frappe.get_doc(VOLUNTEER_DOCTYPE, name)
	doc.check_permission("write")

	return doc


def _writable_entry(name: str):
	entry = frappe.get_doc(surge.ENTRY_DOCTYPE, name)
	_writable_volunteer(entry.volunteer)

	return entry


def _answer(entry) -> dict:
	"""The volunteer's entries after the act, as the record page draws them."""
	return {"entry": entry.name, "surge": surge.for_volunteer(entry.volunteer)}
