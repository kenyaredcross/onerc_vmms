# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Field tables, read from the doctype JSON rather than typed into the guide.

A hand-written field table is wrong the first time somebody adds a field and
nobody notices. So the table is generated: `fields()` opens the real
`.json` the site installs from, and the guide's accuracy stops depending on
whoever last edited it.

The prose in the "What it does" column is the field's own `description` — the
help text an administrator sees under the field on the form — so the guide and
the desk say the same thing by construction. Where a field has no description
(a Table that is self-evident on the form, an audit column) the section module
supplies one, and:

- a field with neither **fails the build**;
- a supplied description for a field that no longer exists **fails the build**.

Either way the guide cannot quietly drift out of step with the schema. Layout
fields — section and column breaks — are omitted; they are furniture, and
listing them would bury the fields that matter.
"""

import json
import re
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = APP_ROOT / "vmmsx"

LAYOUT_FIELDTYPES = frozenset({"Section Break", "Column Break", "Tab Break", "Fold", "HTML"})

FIELD_TABLE_HEADERS = ("Field", "Type", "What it does")
FIELD_TABLE_WIDTHS = (1.55, 1.75, 3.20)


def load(doctype: str) -> dict:
	"""The doctype's JSON, found by its `name` rather than by a guessed path."""
	snake = doctype.lower().replace(" ", "_").replace("-", "_")
	path = PACKAGE_ROOT.glob(f"*/doctype/{snake}/{snake}.json")

	for candidate in path:
		definition = json.loads(candidate.read_text())

		if definition.get("name") == doctype:
			return definition

	raise FileNotFoundError(f"No doctype JSON for {doctype!r} under {PACKAGE_ROOT}")


def fields(doctype: str, descriptions: dict[str, str] | None = None) -> list[list[str]]:
	"""Rows of (field, type, what it does) for every non-layout field."""
	definition = load(doctype)
	supplied = dict(descriptions or {})
	rows = []

	for field in definition.get("fields", []):
		if field.get("fieldtype") in LAYOUT_FIELDTYPES:
			continue

		fieldname = field["fieldname"]
		description = field.get("description") or supplied.pop(fieldname, None)

		if not description:
			raise ValueError(
				f"{doctype}.{fieldname} has no description in its JSON and none was supplied."
				" Every documented field says what it does — see vmmsx/docs/doctypes.py."
			)

		supplied.pop(fieldname, None)
		rows.append([fieldname, _type_of(field), description])

	if supplied:
		raise ValueError(
			f"{doctype}: descriptions were supplied for fields that do not exist:"
			f" {', '.join(sorted(supplied))}. The guide is describing a schema that has changed."
		)

	return rows


def _type_of(field: dict) -> str:
	"""The field's type and its constraints, as one readable cell."""
	fieldtype = field["fieldtype"]
	options = field.get("options")

	if fieldtype == "Select" and options:
		base = "Select: " + " / ".join(part for part in options.split("\n") if part)
	elif options and fieldtype in ("Link", "Table", "Table MultiSelect"):
		base = f"{fieldtype} → {options}"
	else:
		base = fieldtype

	notes = []

	if field.get("reqd"):
		notes.append("required")
	elif field.get("mandatory_depends_on"):
		notes.append("conditionally required")

	if field.get("unique"):
		notes.append("unique")

	if field.get("read_only"):
		notes.append("read-only, engine-written")

	if field.get("translatable"):
		notes.append("translatable")

	default = field.get("default")

	if default not in (None, ""):
		notes.append(f"default {default}")

	return base + (f"\n({', '.join(notes)})" if notes else "")


def naming_of(doctype: str) -> str:
	"""How the doctype is named — read from the source, not asserted.

	The naming series is a constant in the controller rather than an `autoname`
	in the JSON, so it is lifted out of the controller's text. Reading it beats
	repeating it: a series that changes changes the guide with it.
	"""
	definition = load(doctype)

	if definition.get("istable"):
		return (
			"Child table. Rows are named by the framework with an opaque hash, and that row name —"
			" never the label — is the row's identity everywhere in the engine."
		)

	series = _naming_series(doctype)
	rename = "" if definition.get("allow_rename") else " Renaming is switched off."

	if series:
		# "AWF-.#####" -> prefix "AWF-" and five digits -> "AWF-00001"
		example = series.split(".")[0] + "1".rjust(series.count("#"), "0")

		return (
			f"Opaque series {series} ({example}, and so on), assigned in the controller's"
			f" autoname(). Mutable data never goes in a primary key.{rename}"
		)

	return (definition.get("autoname") or "Assigned by the controller's autoname().") + rename


def _naming_series(doctype: str) -> str | None:
	"""The `AWF-.#####`-shaped constant in the doctype's controller, if it has one."""
	snake = doctype.lower().replace(" ", "_").replace("-", "_")

	for candidate in PACKAGE_ROOT.glob(f"*/doctype/{snake}/{snake}.py"):
		found = re.search(r"""["']([A-Z]{2,}-\.#+)["']""", candidate.read_text())

		if found:
			return found.group(1)

	return None
