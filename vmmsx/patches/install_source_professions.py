"""Seed the reviewed legacy profession register on install and upgrade.

The 2026-10-20 source export contains 687 labels, or 684 after collapsing
whitespace. Use the same spelling as migration crosswalk targets; retaining
double spaces would leave those targets pointing at absent records.
Existing professions and profile links are never renamed or overwritten.
"""

import json
from pathlib import Path

import frappe


def profession_names() -> list[str]:
	return json.loads(Path(__file__).with_name("source_professions.json").read_text(encoding="utf-8"))


def execute() -> None:
	for name in profession_names():
		if not frappe.db.exists("Profession", name):
			frappe.get_doc({"doctype": "Profession", "__newname": name}).insert(ignore_permissions=True)
