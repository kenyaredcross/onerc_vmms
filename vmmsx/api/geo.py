# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Read-only geo browsing, for a client-side cascading picker.

Whitelisted browsing through onerc_core's geographic adapter. It exists because the adapter is Python, and a cascading
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
def browse(parent: str | None = None, level: str | None = None, scoped: str | int | None = None) -> dict:
	"""Children of a parent, roots, or all nodes at a requested active level.

	`level` lets registration start at County without requiring a Region answer.
	The stored county node still carries its existing ancestry and routing.

	`scoped` is for staff pickers: only the nodes on the way down to the caller's
	own Geo Assignments, or inside them, come back. A rung left with one option
	answers itself in the picker, so a Head of Region finds their region already
	chosen and a county coordinator their county. National staff (see
	`oversight.national_allowed`) keep the whole tree. The public join form does
	not pass it: somebody applying chooses any branch. This narrows what a picker
	offers; what a person may *read* is still the permission layer's answer.

	Built for a cascading picker: call with no `parent` for the first dropdown,
	then call again with whatever the person picked to fill the next one. An
	empty `nodes` list is the picker's own signal to stop asking — the node just
	chosen has nothing beneath it, which is core's own definition of a leaf,
	not a level a picker has to be told about separately.
	"""
	levels = adapter.level_labels()
	labels = {row["key"]: row["name"] for row in levels}
	nodes = adapter.get_children(parent) if parent else adapter.get_root_regions()
	if level:
		orders = {row["key"]: row["order"] for row in levels}
		if level not in orders:
			frappe.throw(_("Choose an active geographic level."), frappe.ValidationError)
		# Stop at the requested level; registration does not need the entire ward tree.
		pending, nodes, visited = list(nodes), [], set()
		while pending:
			node = pending.pop(0)
			if node["name"] in visited:
				continue
			visited.add(node["name"])
			if node["geo_level"] == level:
				nodes.append(node)
			elif orders.get(node["geo_level"], float("inf")) < orders[level]:
				pending.extend(adapter.get_children(node["name"]))
		nodes.sort(key=lambda node: (node["geo_node_name"].casefold(), node["name"]))

	if frappe.utils.cint(scoped):
		reach = _reach()
		if reach is not None:
			nodes = [node for node in nodes if node["name"] in reach]

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


def _reach(user: str | None = None) -> set[str] | None:
	"""Every node a scoped picker may offer this person, or None for all of them.

	Their assignments' nodes, everything beneath those, and the ancestors above
	them, so the picker can walk down to where they stand. Any role's live
	assignment counts, through core's own `GRANTS_AUTHORITY_SQL`. Nobody with no
	assignment and no national standing is offered anything, failing closed like
	the scope it mirrors.
	"""
	from vmmsx.analytics.services import oversight

	user = user or frappe.session.user

	if oversight.national_allowed(user):
		return None

	reach: set[str] = set()
	for anchor in _anchors(user):
		try:
			reach.add(anchor)
			reach.update(row["name"] for row in adapter.get_ancestors(anchor))
			reach.update(adapter.get_descendants(anchor))
		except frappe.DoesNotExistError:
			# An assignment at a node since removed grants nothing; it must not
			# break every picker on the console.
			continue

	return reach


def _anchors(user: str) -> list[str]:
	"""The nodes of this person's live assignments, whatever the role."""
	from frappe.utils import getdate, today
	from onerc_core.onerc_core.doctype.geo_assignment.geo_assignment import GRANTS_AUTHORITY_SQL

	return frappe.db.sql(
		f"""
		SELECT DISTINCT assignment.geo_node
		FROM `tabGeo Assignment` assignment
		WHERE assignment.user = %(user)s
			AND {GRANTS_AUTHORITY_SQL}
		""",
		{"user": user, "on_date": getdate(today())},
		pluck=True,
	)


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
