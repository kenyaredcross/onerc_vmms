# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Where the society can be found, for the map and the list beside it.

**`published` is this app's third `allow_guest` endpoint**, after
`content.surface` and `society.branding`, and it is guest-readable for the same
kind of reason the first one is: a branch locator that made people sign in first
would answer nobody's question. Somebody looking for their nearest office does
not have an account yet, and quite often the reason they are looking is to go and
get one.

**The boundary is `is_published` on each location, and that is the whole of it.**
Not a role, not a scope, and nothing written in this file: a place appears on the
public map because a coordinator ticked a box on its form, which is a decision
with a document and an audit trail behind it, exactly as `is_public` on a content
surface is the whole of the guest-read rule there. No code here branches on which
location it got.

**Two DTOs, not one with a flag.** The public one is built field by field from
the six things a visitor needs to find a place and get in touch with it. The
internal `notes` field is absent from it, and absent rather than blanked, so a
field added to the doctype later is not silently added to a public API. The
coordinator's DTO is the second function, behind the ordinary permission layer.
"""

import frappe

LOCATION_DOCTYPE = "VMMS Branch Location"

# A directory is a directory. A national society with more places than this has
# a page that nobody scrolls and a map nobody can read, and the fix for that is
# searching by area rather than a longer list.
PAGE = 200


@frappe.whitelist(allow_guest=True)
def published(geo_node: str | None = None) -> dict:
	"""Every location a society has put on its public map.

	`geo_node` narrows to one part of the hierarchy and its subtree, which is
	what "offices in this county" means. It cannot widen anything: the
	`is_published` filter is applied whatever it says, and an unknown node
	answers with nothing.

	Read with permissions bypassed, deliberately and narrowly. The caller is a
	guest, so the ordinary layer would refuse every row, and the alternative is a
	role granted to Guest, which is a much broader thing to be true. What is read
	is bounded by the filter above and what is returned is bounded by the DTO
	below, so the bypass cannot disclose an unpublished location or an internal
	field of a published one.
	"""
	filters: dict = {"is_published": 1}

	if geo_node:
		nodes = _subtree(geo_node)

		if not nodes:
			return {"count": 0, "locations": []}

		filters["geo_node"] = ("in", nodes)

	rows = frappe.get_all(
		LOCATION_DOCTYPE,
		filters=filters,
		fields=[
			"name",
			"location_name",
			"geo_node",
			"address",
			"latitude",
			"longitude",
			"phone",
			"email",
			"opening_hours",
			"photo",
		],
		order_by="location_name asc",
		limit_page_length=PAGE,
		ignore_permissions=True,  # See the docstring: bounded by is_published.
	)

	locations = [_public_dto(row) for row in rows]

	return {
		"count": len(locations),
		"locations": locations,
		# What a map needs before it can draw itself: the box containing every
		# pin. Computed here rather than in the browser so a page with one
		# location and a page with fifty both open at a sensible zoom, and so the
		# frontend holds no opinion about where a society is in the world.
		"bounds": _bounds(locations),
	}


@frappe.whitelist()
def branch_locations() -> dict:
	"""Every location in the caller's own area, published or not.

	The coordinator's read, and the ordinary permission layer is the whole of the
	check: `VMMS Branch Location` is registered as scopeable on `geo_node`, and
	the query is `frappe.get_list` rather than `frappe.get_all` because only the
	first runs core's permission query condition. A location outside the caller's
	assignment is not returnable, and there is no argument here at all, which is
	the strongest form of that guarantee.
	"""
	rows = frappe.get_list(
		LOCATION_DOCTYPE,
		fields=[
			"name",
			"location_name",
			"geo_node",
			"address",
			"latitude",
			"longitude",
			"phone",
			"email",
			"opening_hours",
			"photo",
			"is_published",
			"notes",
		],
		order_by="location_name asc",
		limit_page_length=PAGE,
	)

	return {
		"count": len(rows),
		"locations": [{**_public_dto(row), "is_published": bool(row.is_published), "notes": row.notes} for row in rows],
	}


def _public_dto(row) -> dict:
	"""One location as a visitor sees it, built field by field.

	`has_point` travels with the row so the page never has to ask whether `0.0`
	means the Gulf of Guinea or an empty field. The controller refuses half a
	pair on save, so the two coordinates are either both real or both absent by
	the time anything reads them.
	"""
	return {
		"name": row.name,
		"location_name": row.location_name or "",
		"geo_node": row.geo_node or "",
		"address": row.address or "",
		"latitude": row.latitude,
		"longitude": row.longitude,
		"has_point": bool(row.latitude or row.longitude),
		"phone": row.phone or "",
		"email": row.email or "",
		"opening_hours": row.opening_hours or "",
		"photo": row.photo or "",
	}


def _bounds(locations: list[dict]) -> dict | None:
	"""The box containing every pin, or None when there is nothing to draw.

	None rather than a default box centred somewhere, because "somewhere" would
	be a country written into a source file, and that is precisely what this app
	does not do. A page with no pins draws no map.
	"""
	points = [row for row in locations if row["has_point"]]

	if not points:
		return None

	latitudes = [row["latitude"] for row in points]
	longitudes = [row["longitude"] for row in points]

	return {
		"south": min(latitudes),
		"north": max(latitudes),
		"west": min(longitudes),
		"east": max(longitudes),
	}


def _subtree(geo_node: str) -> list[str]:
	"""A node and everything beneath it, through core's adapter and only it.

	The same shape as `api/opportunities.py::_subtree`, including putting the node
	itself back: `get_descendants` deliberately excludes it, and a filter set to a
	branch has to include the offices *at* that branch. There is no `tabGeo Node`
	query in this app and this is not going to be the first.
	"""
	from onerc_core.geo.services import adapter

	try:
		return [geo_node, *adapter.get_descendants(geo_node)]
	except frappe.DoesNotExistError:
		# A node that does not exist is a narrowing to nothing, not an error: the
		# argument arrives from a query string and a guest typing one should be
		# told there is nothing there rather than handed a traceback.
		return []
