# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What the manager console draws for the person who opened it.

One endpoint, and it exists so that `portal/src/admin/AdminLayout.tsx` can draw
a sidebar without deciding anything. The frontend renders the sections it is
given; the server decides which those are, from the same permission layer every
screen behind them already goes through.

**No role name crosses this boundary, in either direction.** The caller cannot
name a person and cannot name a section — the answer is about
`frappe.session.user` and nothing else, the same shape as `approvals.my_queue`
and the possessive endpoints in `api/member.py`. And the answer carries section
*keys*, which are this app's vocabulary, not a society's: what the tab is called
is a content block like every other word in the product.

**Drawing a tab is a convenience, never the check.** A caller who forges a
section into the list reaches a screen whose own endpoints re-ask the permission
layer and answer empty. Same contract as `can_edit` on a content surface: the
flag saves a round trip, it does not grant anything.
"""

import frappe

from vmmsx.api import assets
from vmmsx.staff.services import console


@frappe.whitelist()
def sections() -> dict:
	"""The console sections this person may open, in sidebar order.

	`available` travels with the list rather than being a second endpoint, for
	the reason `api/events.py::upcoming` gives about Buzz: the layout needs it at
	the moment it decides what to draw, and asking twice would mean a console
	that changes its mind after it has rendered. It is `False` for somebody
	holding none of the society's staff scope roles, and the layout sends them
	back to their own portal rather than drawing a shell of empty screens.
	"""
	from vmmsx.staff.services.workspaces import has_desk_access

	allowed = console.visible()

	return {
		"available": bool(allowed),
		"sections": allowed,
		# Whether to offer a way through to the Frappe desk.
		#
		# The console covers what a coordinator does day to day; the desk is
		# where everything else lives — the doctypes no screen has been built
		# for yet, the settings, the reports. An administrator setting a society
		# up needs it and should not have to be told the address.
		#
		# It is the same question the VMMS tile on the apps screen asks, answered
		# by the same function, so a person who would get a permission error at
		# `/app` is never shown a door to it. A volunteer sees no console at all,
		# and a coordinator without desk access sees the console without this.
		"desk": bool(has_desk_access()),
		# Which kinds of record this person may start. A read-only role (Head of
		# Region, NSD) opens the same screens as a coordinator and is not offered
		# Add asset, New project, Write terms or Create deployment. Like the
		# sections, a convenience: every create endpoint still asks for itself.
		"creates": [
			key
			for key, doctype in CREATABLE.items()
			if frappe.db.exists("DocType", doctype) and frappe.has_permission(doctype, ptype="create")
		]
		# Assets are written by whoever holds the asset role, not through a
		# DocPerm, so the answer is the one `api/assets.py` gives its own writes.
		+ (["asset"] if assets.can_manage() else []),
	}


# The console's create buttons, by this app's own key for each.
CREATABLE = {
	"project": "Project",
	"terms": "VMMS Terms of Reference",
	"deployment": "VMMS Deployment",
}
