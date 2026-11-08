# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Volunteer, member and membership numbers in the old VMMS's formats.

Kenya's records keep the numbers people already carry, and new ones continue
them:

- volunteer `VOL-26-031710`: two-digit year, six digits, **one counter that
  never restarts**. The old system issued it from a Document Naming Rule on
  Employee (`VOL.-.YY.-`, counter 31,709), so the year in the number is the
  year it was issued, not a new sequence;
- member `VM-MEM-2026-01475` and membership `VM-MSH-2026-02594`: four-digit
  year, five digits, a fresh count each year. Plain naming series, set in the
  doctypes, whose `tabSeries` keys (`VM-MEM-2026-`) are the old system's own.

A naming series cannot express the volunteer's rule, since it keys its counter
on the year. The rule is therefore the same Document Naming Rule, installed
here on every migrate so the number never depends on someone recreating it.
Frappe applies a rule before the doctype's own series; the series in the JSON
is the same format, kept as a fallback.

**Never lowers a counter.** `install()` creates the rule only when there is
none; `raise_counters()` moves a counter up to at least what it is asked for
and to at least the highest number already on the site, so migrated records
and new ones cannot collide. Existing records keep their names.
"""

from __future__ import annotations

import re

import frappe

VOLUNTEER = "VMMS Volunteer"
VOLUNTEER_PREFIX = "VOL.-.YY.-"
VOLUNTEER_DIGITS = 6
VOLUNTEER_NAME = re.compile(r"^VOL-\d{2}-(\d{6})$")

# The series each doctype shipped with before, and the one it ships with now.
SHIPPED = {
	"VMMS Volunteer": ("VOL-.#####", "VOL-.YY.-.######"),
	"VMMS Member": ("MEM-.#####", "VM-MEM-.YYYY.-.#####"),
	"VMMS Membership": ("MSHIP-.#####", "VM-MSH-.YYYY.-.#####"),
}

SERIES = {
	"VMMS Member": re.compile(r"^(VM-MEM-\d{4}-)(\d{5})$"),
	"VMMS Membership": re.compile(r"^(VM-MSH-\d{4}-)(\d{5})$"),
}


def volunteer_rule() -> str | None:
	return frappe.db.get_value(
		"Document Naming Rule",
		{"document_type": VOLUNTEER, "prefix": VOLUNTEER_PREFIX},
		"name",
	)


def install() -> None:
	"""The new series in force, and the volunteer rule if the site has none."""
	adopt_series()

	if volunteer_rule():
		return

	frappe.get_doc(
		{
			"doctype": "Document Naming Rule",
			"document_type": VOLUNTEER,
			"prefix": VOLUNTEER_PREFIX,
			"prefix_digits": VOLUNTEER_DIGITS,
			"counter": highest_volunteer_number(),
			"priority": 0,
		}
	).insert(ignore_permissions=True)


def adopt_series() -> list[str]:
	"""Move a site still on the old shipped series onto the new one.

	A site with records keeps its series in a Property Setter: Frappe writes
	one when the doctype syncs (`preserve_naming_series_options_in_property_setter`),
	so a changed series in the JSON never reaches a site already in use. The
	setter is rewritten only where it still holds the exact old shipped value;
	a series a society chose for itself is left alone.
	"""
	changed = []

	for doctype, (old, new) in SHIPPED.items():
		for prop in ("options", "default"):
			setter = frappe.db.get_value(
				"Property Setter",
				{"doc_type": doctype, "field_name": "naming_series", "property": prop},
				["name", "value"],
				as_dict=True,
			)
			if setter and setter.value == old:
				frappe.db.set_value("Property Setter", setter.name, "value", new)
				changed.append(f"{doctype} {prop}")

		if any(item.startswith(doctype) for item in changed):
			frappe.clear_cache(doctype=doctype)

	return changed


def highest_volunteer_number() -> int:
	names = frappe.get_all(VOLUNTEER, filters={"name": ("like", "VOL-__-%")}, pluck="name")
	numbers = [int(match.group(1)) for name in names if (match := VOLUNTEER_NAME.match(name))]
	return max(numbers, default=0)


def highest_in_series(doctype: str) -> dict[str, int]:
	pattern = SERIES[doctype]
	prefix = "VM-MEM-" if doctype == "VMMS Member" else "VM-MSH-"
	found: dict[str, int] = {}

	for name in frappe.get_all(doctype, filters={"name": ("like", f"{prefix}%")}, pluck="name"):
		if match := pattern.match(name):
			key, number = match.group(1), int(match.group(2))
			found[key] = max(found.get(key, 0), number)

	return found


def series_counter(key: str) -> int | None:
	"""`tabSeries` is a bare table, not a DocType. None when the key is not there yet."""
	row = frappe.db.sql("select `current` from `tabSeries` where `name` = %s", key)
	return int(row[0][0] or 0) if row else None


def plan(volunteer_floor: int = 0, series_floors: dict[str, int] | None = None) -> dict:
	"""Where each counter is now and where `raise_counters` would put it."""
	rule = volunteer_rule()
	current = int(frappe.db.get_value("Document Naming Rule", rule, "counter") or 0) if rule else None
	volunteer_target = max(current or 0, volunteer_floor, highest_volunteer_number())

	wanted: dict[str, int] = dict(series_floors or {})
	for doctype in SERIES:
		for key, number in highest_in_series(doctype).items():
			wanted[key] = max(wanted.get(key, 0), number)

	series = {}
	for key in sorted(wanted):
		now = series_counter(key)
		series[key] = {"current": now, "target": max(now or 0, wanted[key])}

	return {
		"volunteer_rule": rule,
		"volunteer": {"current": current, "target": volunteer_target},
		"series": series,
	}


def raise_counters(volunteer_floor: int = 0, series_floors: dict[str, int] | None = None) -> dict:
	"""Move every counter up to its target from `plan`. Nothing ever goes down."""
	install()
	planned = plan(volunteer_floor, series_floors)

	volunteer = planned["volunteer"]
	if volunteer["target"] != volunteer["current"]:
		frappe.db.set_value("Document Naming Rule", planned["volunteer_rule"], "counter", volunteer["target"])

	for key, counter in planned["series"].items():
		if counter["target"] == counter["current"]:
			continue
		if counter["current"] is not None:
			frappe.db.sql("update `tabSeries` set `current` = %s where `name` = %s", (counter["target"], key))
		else:
			frappe.db.sql("insert into `tabSeries` (`name`, `current`) values (%s, %s)", (key, counter["target"]))

	frappe.clear_document_cache("Document Naming Rule", planned["volunteer_rule"])
	return plan(volunteer_floor, series_floors)
