# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Step: Kenya's geography — eight regions, 47 counties and the KRCS sub-counties.

Moved from `VMMS-Kenya scripts/seed.py`, with its validation and planning
unchanged: every level and node is planned before anything is written, an
existing node is reused by its code or by its name under the same parent, and
a conflict stops the step rather than guessing.
"""

import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "geography.json"

LEVELS = [
	("national", "National"),
	("region", "Region"),
	("county", "County"),
	("sub_county", "Sub-county"),
	("ward", "Ward"),
]


def normalise(value):
	return " ".join(unicodedata.normalize("NFKC", value).replace("\u2019", "'").split()).casefold()


def region_label(label):
	return re.sub(r"^KRCS\s+", "", label.strip(), flags=re.IGNORECASE)


def without_region_prefix(data):
	return {
		**data,
		"nodes": [
			{**row, "label": region_label(row["label"])} if row["level"] == "region" else dict(row)
			for row in data["nodes"]
		],
	}


def validate_dataset(data):
	nodes = data["nodes"]
	seen, siblings = {}, set()
	orders = {key: order for order, (key, _) in enumerate(LEVELS)}
	for row in nodes:
		code, level, label, parent = (row[k] for k in ("code", "level", "label", "parent"))
		if not code or code in seen or level not in orders or not label.strip():
			raise ValueError(f"Invalid or duplicate geographic identity: {row}")
		if level == "national":
			if parent is not None:
				raise ValueError("National root cannot have a parent")
		elif parent not in seen or orders[seen[parent]["level"]] != orders[level] - 1:
			raise ValueError(f"Missing or incorrect parent for {code}")
		sibling = (parent, normalise(label))
		if sibling in siblings:
			raise ValueError(f"Duplicate sibling: {label}")
		siblings.add(sibling)
		seen[code] = row
	counts = dict(Counter(row["level"] for row in nodes))
	if counts != data["counts"]:
		raise ValueError(f"Dataset counts do not match manifest: {counts}")
	if counts.get("national") != 1 or counts.get("region") != 8 or counts.get("county") != 47:
		raise ValueError("Expected one national root, eight regions, and 47 counties")
	return counts


def plan_seed(frappe, data):
	"""Preflight every level and node before making any changes."""
	data = without_region_prefix(data)
	levels = frappe.get_all(
		"Geo Level",
		fields=[
			"name",
			"geo_level_name",
			"geo_level_order",
			"requires_parent",
			"is_active",
			"is_lowest_level",
		],
	)
	level_map, missing_levels = {}, []
	for order, (key, label) in enumerate(LEVELS, 1):
		matches = [r for r in levels if r.name == key or normalise(r.geo_level_name) == normalise(label)]
		if len(matches) > 1:
			raise ValueError(f"Ambiguous existing Geo Level: {label}")
		if matches:
			row = matches[0]
			if (row.geo_level_order, row.requires_parent, row.is_active) != (order, int(order > 1), 1):
				raise ValueError(f"Existing level {row.name} has conflicting order/parent/active settings")
			level_map[key] = row.name
		else:
			level_map[key] = key
			missing_levels.append((key, label, order))
	foreign_lowest = [
		r.name for r in levels if r.is_active and r.is_lowest_level and r.name not in level_map.values()
	]
	if foreign_lowest:
		raise ValueError(f"Another hierarchy has the lowest-level marker: {foreign_lowest}")

	existing = frappe.get_all(
		"Geo Node",
		fields=[
			"name",
			"geo_node_name",
			"geo_level",
			"parent_geo_node",
			"geo_code",
			"is_group",
		],
	)
	by_code, by_sibling = {}, {}
	for row in existing:
		if row.geo_code:
			by_code.setdefault(row.geo_code, []).append(row)
		label = region_label(row.geo_node_name) if row.geo_level == level_map["region"] else row.geo_node_name
		by_sibling.setdefault((row.parent_geo_node or None, normalise(label)), []).append(row)
	mapped, create, reuse = {}, [], []
	for row in data["nodes"]:
		parent = mapped.get(row["parent"]) if row["parent"] else None
		matches = by_code.get(row["code"], []) or by_sibling.get((parent, normalise(row["label"])), [])
		if len(matches) > 1:
			raise ValueError(f"Ambiguous existing node: {row['code']}")
		if matches:
			found = matches[0]
			if (
				found.geo_level != level_map[row["level"]]
				or (found.parent_geo_node or None) != parent
				or normalise(
					region_label(found.geo_node_name) if row["level"] == "region" else found.geo_node_name
				)
				!= normalise(row["label"])
			):
				raise ValueError(f"Existing geographic code/parent/name conflict: {row['code']}")
			if row["level"] != "ward" and not found.is_group:
				raise ValueError(f"Existing parent is not a group: {found.name}")
			mapped[row["code"]] = found.name
			reuse.append(found.name)
		else:
			# Virtual references are used only for planning; real docnames are
			# resolved parent-first during the insert pass.
			mapped[row["code"]] = row["code"]
			create.append(row)
	return level_map, missing_levels, mapped, create, reuse


def seed(frappe, data, apply=False):
	data = without_region_prefix(data)
	counts = validate_dataset(data)
	level_map, missing_levels, mapped, create, reuse = plan_seed(frappe, data)
	summary = {
		"mode": "apply" if apply else "dry-run",
		"site": frappe.local.site,
		"dataset_counts": counts,
		"create_levels": len(missing_levels),
		"create_nodes": len(create),
		"reuse_nodes": len(reuse),
		"excluded_legacy_records": len(data.get("exceptions", [])),
	}
	if not apply:
		return summary
	for key, label, order in missing_levels:
		frappe.get_doc(
			{
				"doctype": "Geo Level",
				"geo_level_key": key,
				"geo_level_name": label,
				"geo_level_order": order,
				"requires_parent": int(order > 1),
				"is_active": 1,
				"is_lowest_level": 0,
			}
		).insert(ignore_permissions=True)
	ward = frappe.get_doc("Geo Level", level_map["ward"])
	if not ward.is_lowest_level:
		ward.is_lowest_level = 1
		ward.save(ignore_permissions=True)
	for row in create:
		doc = frappe.get_doc(
			{
				"doctype": "Geo Node",
				"geo_node_name": row["label"],
				"geo_level": level_map[row["level"]],
				"geo_code": row["code"],
				"parent_geo_node": mapped[row["parent"]] if row["parent"] else None,
				"is_group": int(row["level"] != "ward"),
			}
		).insert(ignore_permissions=True)
		mapped[row["code"]] = doc.name
	# Re-run the preflight against real docnames and verify every inserted node.
	_, remaining_levels, _, remaining_nodes, _ = plan_seed(frappe, data)
	if remaining_levels or remaining_nodes:
		raise RuntimeError("Post-import verification found missing geography")
	summary["node_map"] = mapped
	return summary


def load() -> dict:
	return json.loads(DATA.read_text())


def under_the_existing_root(frappe, data: dict) -> dict:
	"""Hang the regions under the society's own national node, whatever it is called.

	The Society step (or the setup wizard) makes one parentless node named after
	the society. The dataset's root is "Kenya Red Cross Society"; matched by name,
	a society named anything else would get a second national tree.
	"""
	roots = frappe.get_all(
		"Geo Node",
		filters={"parent_geo_node": ("is", "not set")},
		fields=["geo_node_name", "geo_code"],
	)
	if len(roots) != 1 or roots[0].geo_code:
		return data
	return {
		**data,
		"nodes": [
			{**row, "label": roots[0].geo_node_name} if row["level"] == "national" else row
			for row in data["nodes"]
		],
	}


def run(frappe, settings: dict, apply: bool) -> dict:
	result = seed(frappe, under_the_existing_root(frappe, load()), apply=apply)
	# The docname of every node, kept by the script for the old-data migration.
	# Too long to show on a page, and not used here.
	result.pop("node_map", None)
	if apply:
		frappe.clear_cache()
	return result
