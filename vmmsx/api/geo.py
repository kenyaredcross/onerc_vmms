# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Read-only geo browsing, for a client-side cascading picker.

A thin, whitelisted door onto onerc_core's own geo adapter — this file adds no
logic of its own. It exists because the adapter is Python, and a cascading
picker running in a browser needs something to call: **no app outside
onerc_core may import Geo Node or Geo Level directly**, and this endpoint is
how `vmms_volunteer_application.js` (Home Area and Serving Branch) and the
portal's cascading selects read the tree without ever touching `tabGeo Node`
itself.

Every level's *label* — "Region", "County", "Ward" — is read from
`adapter.level_labels()`, never hardcoded: a society names its own ladder, and
the picker asks what to call each rung rather than assuming one.
"""

import frappe
from frappe import _
from onerc_core.geo.services import adapter


@frappe.whitelist()
def ladder() -> dict:
	"""The society's active levels, top-down — the rungs a cascading form draws.

	A picker that walks the tree one node at a time needs nothing but `browse`.
	A picker built out of **select fields** needs this as well, because it draws
	its controls before anybody has chosen anything: a society four levels deep
	gets four selects, disabled until the one above them is answered, and a
	society two deep gets two. Neither number is in a source file.

	**`order` is why this returns rows rather than a count.** Two societies can
	share one site and each numbers its own ladder from 1, so a site can have six
	active levels over three rungs. A caller drawing controls counts *distinct
	orders*, not levels, and `name` tells it what each rung is called — plural,
	where two societies name the same rung differently. Core says all of this out
	loud in `adapter.hierarchy_overview`'s `shares_order_with`.

	`is_lowest` is carried through because it is the society's own statement of
	where its ladder ends, which is not the same question as whether a particular
	node happens to be a leaf. A form uses the ladder to decide how many controls
	to draw and an empty `browse` to stop asking.
	"""
	return {
		"levels": [
			{
				"key": row["key"],
				"name": row["name"],
				"order": row["order"],
				"is_lowest": bool(row["is_lowest"]),
			}
			for row in adapter.level_labels()
		]
	}


@frappe.whitelist()
def browse(parent: str | None = None) -> dict:
	"""One rung of the tree: this node's children, or the top rung if `parent` is empty.

	Built for a cascading picker: call with no `parent` for the first dropdown,
	then call again with whatever the person picked to fill the next one. An
	empty `nodes` list is the picker's own signal to stop asking — the node just
	chosen has nothing beneath it, which is core's own definition of a leaf,
	not a level a picker has to be told about separately.
	"""
	labels = {row["key"]: row["name"] for row in adapter.level_labels()}
	nodes = adapter.get_children(parent) if parent else adapter.get_root_regions()

	return {
		"parent": parent,
		"nodes": [
			{
				"name": node["name"],
				"label": node["geo_node_name"],
				"level": node["geo_level"],
				"level_name": labels.get(node["geo_level"], node["geo_level"]),
			}
			for node in nodes
		],
	}


@frappe.whitelist()
def path(node: str) -> dict:
	"""A node with its full ancestry, root first — what a picker restores from.

	Used to pre-fill a cascading picker that already has a value (opening an
	existing application): the client walks this list in order, opening one
	dropdown per ancestor before selecting the node itself.

	Built entirely from `adapter.get_ancestors()` and `adapter.get_children()` /
	`adapter.get_root_regions()` — never a direct read of Geo Node — because the
	node's own row is exactly "the entry matching this name among its parent's
	children", which the adapter already knows how to answer.
	"""
	labels = {row["key"]: row["name"] for row in adapter.level_labels()}
	# Nearest-first, and also the existence check: throws for a node not there.
	ancestors = adapter.get_ancestors(node)
	parent = ancestors[0]["name"] if ancestors else None
	siblings = adapter.get_children(parent) if parent else adapter.get_root_regions()
	own = next((row for row in siblings if row["name"] == node), None)

	if not own:
		frappe.throw(_("Geo Node {0} does not exist").format(node), frappe.DoesNotExistError)

	# own + ancestors is nearest-first (node, parent, grandparent, ...); a
	# picker wants root first, leaf last.
	chain = list(reversed([own, *ancestors]))

	return {
		"node": node,
		"chain": [
			{
				"name": row["name"],
				"label": row["geo_node_name"],
				"level": row["geo_level"],
				"level_name": labels.get(row["geo_level"], row["geo_level"]),
				"parent": row["parent_geo_node"],
			}
			for row in chain
		],
	}
