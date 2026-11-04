# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The change history of a registration, read from Frappe's own `Version` log.

The same record the desk's timeline is built from: who created the record, and
every later save that changed a field or a table row, with the old and new
values. Both documents are covered, because most of what an applicant enters
lives on their Red Profile rather than on the application itself.

Read only. Approval decisions have their own history on the Decision tab and
are not repeated here.
"""

import json

import frappe
from frappe.utils import cstr, flt, get_fullname

PROFILE_DOCTYPE = "Red Profile"
LIMIT = 200
MAX_VALUE = 200

# Never shown, whatever the meta says: framework bookkeeping and secrets.
_SKIPPED_TYPES = {"Password", "Section Break", "Column Break", "Tab Break", "HTML", "Button"}


def trail(document, profile: str | None = None, record_label: str = "Application") -> list[dict]:
	"""Newest first: one entry per save, each listing what that save changed."""
	sources = [(document.doctype, document.name, record_label)]
	if profile:
		sources.append((PROFILE_DOCTYPE, profile, "Personal details"))

	entries = []
	for doctype, name, label in sources:
		if not frappe.db.exists(doctype, name):
			continue
		meta = frappe.get_meta(doctype)
		created = frappe.db.get_value(doctype, name, ["creation", "owner"], as_dict=True)
		if created and doctype == document.doctype:
			entries.append(
				{
					"on": created.creation,
					"by": get_fullname(created.owner),
					"record": label,
					"kind": "created",
					"changes": [],
				}
			)
		for version in frappe.get_all(
			"Version",
			filters={"ref_doctype": doctype, "docname": name},
			fields=["creation", "owner", "data"],
			order_by="creation desc",
			limit=LIMIT,
		):
			changes = _changes(meta, version.data)
			if changes:
				entries.append(
					{
						"on": version.creation,
						"by": get_fullname(version.owner),
						"record": label,
						"kind": "changed",
						"changes": changes,
					}
				)

	entries.sort(key=lambda entry: entry["on"], reverse=True)
	return entries[:LIMIT]


def _changes(meta, raw) -> list[dict]:
	try:
		data = json.loads(raw or "{}")
	except ValueError:
		return []

	changes = []
	for fieldname, old, new in data.get("changed") or []:
		field = _field(meta, fieldname)
		if field and not _same(field, old, new):
			changes.append({"field": _label(field), "from": _shown(field, old), "to": _shown(field, new)})

	# A save that rewrites a table removes every row and adds it back. A row
	# removed and re-added with the same values did not change, so the pair is
	# dropped rather than listed as two edits.
	added = [(table, row) for table, row in data.get("added") or []]
	removed = [(table, row) for table, row in data.get("removed") or []]
	for table, row in list(added):
		match = next(
			(
				pair
				for pair in removed
				if pair[0] == table and _row_values(meta, table, pair[1]) == _row_values(meta, table, row)
			),
			None,
		)
		if match:
			added.remove((table, row))
			removed.remove(match)

	for rows, verb in ((added, "Added"), (removed, "Removed")):
		for table, row in rows:
			field = _field(meta, table)
			if field:
				changes.append(
					{
						"field": _label(field),
						"from": None,
						"to": None,
						"row": f"{verb} {_row_summary(field, row)}",
					}
				)

	for table, idx, _rowname, row_changes in data.get("row_changed") or []:
		field = _field(meta, table)
		if not field:
			continue
		child = frappe.get_meta(field.options) if field.options else None
		for fieldname, old, new in row_changes or []:
			child_field = _field(child, fieldname) if child else None
			if child_field and not _same(child_field, old, new):
				changes.append(
					{
						"field": f"{_label(field)}, row {idx}: {_label(child_field)}",
						"from": _shown(child_field, old),
						"to": _shown(child_field, new),
					}
				)

	return changes


def _field(meta, fieldname):
	field = meta.get_field(fieldname) if meta else None
	if not field or field.fieldtype in _SKIPPED_TYPES or field.hidden:
		return None
	return field


# The registration form's own names, where the field's label is a system one.
_LABELS = {
	"home_geo_node": "Residence",
	"geo_node": "Branch / County",
	"residency_type": "Residency",
}


def _label(field) -> str:
	return _LABELS.get(field.fieldname) or field.label or field.fieldname.replace("_", " ").capitalize()


def _value(value):
	if value in (None, ""):
		return None
	text = cstr(value)
	if text.startswith(("/private/files/", "/files/")):
		text = text.rsplit("/", 1)[-1]
	return text if len(text) <= MAX_VALUE else f"{text[:MAX_VALUE]}…"


def _same(field, old, new) -> bool:
	"""Empty and zero are the same number; a save that swaps them changed nothing."""
	if field.fieldtype in ("Int", "Float", "Currency", "Percent", "Check"):
		return flt(old) == flt(new)
	return cstr(old) == cstr(new)


def _shown(field, value):
	"""A value as a person reads it: a linked record by its title, not its key."""
	if field.fieldtype == "Check":
		return "Yes" if value in (1, "1", True) else "No"
	if field.fieldtype == "Link" and value and field.options:
		title = _title(field.options, value)
		if title:
			return _value(title)
	return _value(value)


def _title(doctype: str, name: str):
	cache = frappe.flags.setdefault("vmmsx_audit_titles", {})
	key = (doctype, name)
	if key not in cache:
		meta = frappe.get_meta(doctype)
		title_field = meta.title_field if meta.title_field and meta.title_field != "name" else None
		cache[key] = frappe.db.get_value(doctype, name, title_field) if title_field else None
	return cache[key]


def _row_values(meta, table: str, row) -> tuple:
	field = meta.get_field(table)
	child = frappe.get_meta(field.options) if field and field.options else None
	return tuple(
		cstr((row or {}).get(column.fieldname))
		for column in (child.fields if child else [])
		if column.fieldtype not in _SKIPPED_TYPES
	)


def _row_summary(field, row) -> str:
	"""A row, by the first few values a person would recognise it by."""
	child = frappe.get_meta(field.options) if field.options else None
	values = []
	for column in child.fields if child else []:
		if column.fieldtype in _SKIPPED_TYPES or column.hidden or column.fieldtype == "Check":
			continue
		value = _shown(column, (row or {}).get(column.fieldname))
		if value:
			values.append(value)
		if len(values) == 2:
			break
	return f"row: {' · '.join(values)}" if values else "a row"
