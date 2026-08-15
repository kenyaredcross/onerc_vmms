# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""BUZZ-01 — the only file in vmmsx that knows Buzz's event doctype exists.

**Deliberately thin.** This is a geo-anchor seam and nothing more: Buzz's
`Buzz Event` gains one field, `geo_node`, a Link to core's Geo Node — added as a
Custom Field by a vmmsx-owned patch, never by editing Buzz's own schema. That is
the entire crossing. This module does not read an event's attendees, bookings,
tickets or check-ins, and no other file in vmmsx names `Buzz Event` at all
(`test_delegation.py` in this package asserts that against the source, the way
`vmmsx/member/tests/test_delegation.py` already does for the learning and
payment seams).

**No identity bridge.** An attendee stays Buzz-native. There is no path here
from a booking or a ticket to a Red Profile, a VMMS Volunteer or a VMMS Member —
that bridge (RP-14) is a deliberately deferred, separate decision, and building
it was explicitly out of scope for this seam. Placing an event in the geo
hierarchy says nothing about who attends it.

**Safe when Buzz is absent.** vmmsx does not declare `buzz` in `required_apps`:
a society running without Buzz is an ordinary, supported state, not a
half-installed one. `is_available()` asks `frappe.get_installed_apps()` rather
than importing and catching failure — an app can sit in the bench without being
installed on *this* site, which is the case that actually matters, and a
question answered by an exception cannot be asked at configuration time. The
patch that installs the field checks this before doing anything, and
`geo_node_of()` answers `None` rather than raising when Buzz is not here.
"""

import frappe

BUZZ_APP = "buzz"
EVENT_DOCTYPE = "Buzz Event"
GEO_NODE_FIELD = "geo_node"


def is_available() -> bool:
	"""Is Buzz installed on this site?"""
	return BUZZ_APP in frappe.get_installed_apps()


def geo_node_of(event: str) -> str | None:
	"""Where this event is anchored, or None — unplaced, or Buzz not installed.

	The one read this seam performs, and it reads only the field vmmsx itself
	installed. An event with no anchor is ordinary: the field is optional, and
	most events a society runs through Buzz's own flows will never set it.
	"""
	if not is_available():
		return None

	return frappe.db.get_value(EVENT_DOCTYPE, event, GEO_NODE_FIELD)
