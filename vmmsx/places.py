# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A place by its own name, the way printed and emailed documents show it.

"Baringo", not "Baringo — KRCS South Rift — Kenya Red Cross Society". The
region and the society above a branch are the society's own structure, and
everybody reading a card, a certificate or a letter already knows them. The
portal applies the same rule to every path it shows (`format.ts::geoPath`).

Read through core's adapter, which owns the geo tree: the place is the first
rung of the path it renders, deepest first. A node at the society itself has a
one-rung path, and that rung is its name.
"""


def place_name(node: str | None) -> str:
	"""The node's own name, or "" when there is no node."""
	if not node:
		return ""

	from onerc_core.geo.services import adapter

	path = adapter.get_full_path(node) or ""

	return path.split(adapter.PATH_SEPARATOR.strip())[0].strip()
