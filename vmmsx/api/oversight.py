# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The console's Region and National tabs.

Two endpoints, one per tab, each a gate in front of
`analytics/services/oversight.py`, where the scope guarantees are written.

**The area is checked, then counted.** A regional head may name only a region
they are assigned to; national staff may name any. The counts inside are the
caller's own scope regardless, so the check is about not laying out a map of
counties somebody has no business looking at, not the last line of defence.

**`place` only narrows.** It picks the county (or, on the national tab, the
region) whose breakdowns are shown. A place outside the area is ignored, not
refused: it is a stale link, not an attack.
"""

import frappe
from frappe import _

from vmmsx.analytics.services import oversight


@frappe.whitelist()
def region(area: str | None = None, place: str | None = None) -> dict:
	"""A region county by county, for somebody responsible for it."""
	areas = oversight.regions_for()

	if not areas:
		if oversight.national_allowed():
			# National staff on a society with no regions yet: nothing to lay out.
			return {"areas": [], "area": None}

		frappe.throw(_("You are not responsible for a region."), frappe.PermissionError)

	allowed = {row["name"] for row in areas}
	area = area if area in allowed else areas[0]["name"]

	return {**oversight.overview(area, place), "areas": areas}


@frappe.whitelist()
def national(place: str | None = None) -> dict:
	"""The whole country, region by region and county by county."""
	if not oversight.national_allowed():
		frappe.throw(_("The national figures are for national staff."), frappe.PermissionError)

	area = oversight.national_area()

	if not area:
		frappe.throw(_("The society's places have not been set up yet."))

	return oversight.overview(area, place)


@frappe.whitelist()
def map_shapes() -> dict:
	"""The country's counties as map shapes, for whoever may open either tab.

	Every county rather than the caller's: a regional map shows the whole
	country with the region picked out, which is how a reader finds it.
	"""
	if not (oversight.national_allowed() or oversight.regions_for()):
		frappe.throw(_("The maps are for regional and national staff."), frappe.PermissionError)

	from vmmsx.analytics.services import boundaries

	area = oversight.national_area()

	if not area:
		return {"view_box": "0 0 1000 750", "shapes": [], "has_file": False, "matched": 0, "credit": None}

	return boundaries.shapes(oversight.counties(area))
