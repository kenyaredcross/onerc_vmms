# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Turning an address into a point, and a point into a link somebody can follow.

Two jobs, and the second is the one that matters most on the day. A volunteer
standing at a bus stand with an invitation on their phone needs a link that
opens a map and a link that gives them directions. That is `map_link` and
`directions_link`, they are pure string building, they need no network and they
never fail.

The first job is geocoding, and everything about how it is built here follows
from one decision: **a deployment must never fail to save because a third party
was slow.** So

* nothing geocodes on `validate`. `locate_place` is an explicit act a
  screen asks for, and a deployment saves perfectly well with no coordinates at
  all — which is also the honest state for a place that has no address anybody
  has written down yet;
* every failure is a `None` and a recorded reason, never an exception. A
  provider that is down, a site with no provider configured, an address the
  provider cannot place, a timeout, a malformed answer: all the same shape of
  answer, and all leave the record exactly as it was;
* **a pin somebody dropped by hand is never overwritten.** Coordinates already
  on the record win over anything a geocoder would say, because a coordinator
  who has moved the pin knows something the address does not — a compound gate
  on the far side of a block, a landing site in a field with no address at all.
  `locate` only ever fills a blank, and `relocate` is the deliberate override.

**The provider is site configuration, not society configuration**, which is a
departure from this app's usual direction and a deliberate one. Which role may
see a deployment is a society's decision; which HTTP endpoint resolves an
address is a property of the deployment the software is running on, in the same
family as the database host. It is read from `site_config.json`:

    "vmms_geocoding_url": "https://nominatim.openstreetmap.org/search"

With nothing configured — the shipped state — geocoding is simply off, and
`locate` says so in a sentence a coordinator can act on rather than failing
silently. Manual pins keep working, so a society that never configures a
provider still gets maps and directions.

**OpenStreetMap, because the portal already draws OSM tiles.** The links point
at openstreetmap.org rather than any commercial map, so nothing here sends a
society's deployment locations to a third party the moment somebody opens a
record.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

# The site-config key that names the search endpoint. Absent means off.
PROVIDER_KEY = "vmms_geocoding_url"

# Seconds. Short on purpose: this runs inside a request somebody is waiting on,
# and a geocode that has not answered in five seconds has failed as far as the
# person at the screen is concerned.
TIMEOUT = 5

# The two prefixes a deployment carries a place under. Written down once so the
# field names are derived rather than typed at each call site.
#
# **A "place" is a prefix, not a fixed list.** Everything below derives its field
# names from whatever prefix it is handed, so a task's own work location and
# meeting point use the same code and the same links without this module knowing
# that tasks exist. Each caller states which prefixes it has, and
# `assert_known` refuses anything else.
SITE = "site"
MEETING = "meeting"
PLACES = (SITE, MEETING)


def is_configured() -> bool:
	"""Has this site been given somewhere to ask? Nothing here works without one."""
	return bool(frappe.conf.get(PROVIDER_KEY))


# --- links ------------------------------------------------------------------


def map_link(latitude, longitude) -> str | None:
	"""A URL that opens a map on this point, or None where there is no point.

	`None` rather than a link to nowhere: a screen showing "open the map" on a
	deployment with no coordinates sends somebody to the middle of the Atlantic,
	which is where zero and zero are.
	"""
	if not _is_point(latitude, longitude):
		return None

	return f"https://www.openstreetmap.org/?mlat={latitude}&mlon={longitude}#map=16/{latitude}/{longitude}"


def directions_link(latitude, longitude, from_latitude=None, from_longitude=None) -> str | None:
	"""A URL that routes to this point, from another one where one is known.

	Without a starting point the route is left open — the map asks the reader's
	own device where they are, which is a better answer than guessing from the
	branch's coordinates that they are setting off from the office.
	"""
	if not _is_point(latitude, longitude):
		return None

	start = (
		f"{from_latitude},{from_longitude}" if _is_point(from_latitude, from_longitude) else ""
	)

	return f"https://www.openstreetmap.org/directions?route={start};{latitude},{longitude}"


def _is_point(latitude, longitude) -> bool:
	"""Both present, and not the null island that an empty Float pair produces."""
	return bool(frappe.utils.flt(latitude) or frappe.utils.flt(longitude))


# --- resolving an address ---------------------------------------------------


def locate(query: str | None) -> dict:
	"""Resolve an address to a point. Never raises; always says what happened.

	Returns `{"located": bool, "latitude": …, "longitude": …, "reason": …}`. The
	reason is a sentence for a coordinator, present on every unsuccessful answer
	and absent on a successful one, so a screen has something to show that is not
	"something went wrong".
	"""
	if not (query or "").strip():
		return _failed(_("There is no address to look up. Write one, or place the pin by hand."))

	if not is_configured():
		return _failed(
			_(
				"This site has no geocoding service configured, so an address cannot be turned"
				" into a point automatically. Place the pin by hand, or ask an administrator to"
				" configure one."
			)
		)

	try:
		import requests

		answer = requests.get(
			frappe.conf.get(PROVIDER_KEY),
			params={"q": query, "format": "json", "limit": 1},
			headers={"User-Agent": f"vmmsx/{frappe.local.site}"},
			timeout=TIMEOUT,
		)
		answer.raise_for_status()
		rows = answer.json()
	except Exception as problem:
		# Logged rather than raised. A geocoding provider that is down is an
		# operational fact somebody should be able to look up afterwards, and it
		# is not a reason a coordinator cannot get on with their afternoon.
		frappe.log_error(title="Geocoding failed", message=str(problem))

		return _failed(
			_("The address could not be looked up just now. Place the pin by hand, or try again.")
		)

	if not rows:
		return _failed(
			_("Nothing was found for {0}. Try a fuller address, or place the pin by hand.").format(
				frappe.bold(query)
			)
		)

	first = rows[0]

	return {
		"located": True,
		"latitude": frappe.utils.flt(first.get("lat")),
		"longitude": frappe.utils.flt(first.get("lon")),
		"matched": first.get("display_name"),
		"reason": None,
	}


def _failed(reason: str) -> dict:
	return {"located": False, "latitude": None, "longitude": None, "matched": None, "reason": reason}


# --- putting a point on a deployment ----------------------------------------


def fields_for(place: str) -> dict[str, str]:
	"""The four field names a place is written under, derived from its prefix.

	The whole of this module's coupling to a doctype: a record carries
	`<place>_address`, `<place>_latitude`, `<place>_longitude` and
	`<place>_located_on`, and everything else follows from that.
	"""
	return {
		"address": f"{place}_address",
		"latitude": f"{place}_latitude",
		"longitude": f"{place}_longitude",
		"located_on": f"{place}_located_on",
	}


def assert_known(place: str, allowed: tuple[str, ...]) -> None:
	"""Throw unless `place` is one this caller has.

	The allowed list belongs to the caller rather than to this module, because a
	deployment has a site and a meeting point and a task has a work location and a
	meeting point, and neither should be able to name the other's.
	"""
	if place in allowed:
		return

	frappe.throw(
		_("{0} is not a place on this record. Expected one of: {1}.").format(
			frappe.bold(place), ", ".join(allowed)
		),
		frappe.ValidationError,
		title=_("Unknown Place"),
	)


def has_point(deployment, place: str) -> bool:
	fields = fields_for(place)

	return _is_point(deployment.get(fields["latitude"]), deployment.get(fields["longitude"]))


def locate_place(deployment, place: str, force: bool = False) -> dict:
	"""Fill in one of a record's points from its address. Saves on success.

	**A blank only, unless `force`.** A pin already on the record was either
	geocoded before or dropped by somebody who knew better, and overwriting it on
	every save would undo their correction every time the address was tidied.
	`force` is the manual "look this up again" — a deliberate act, never a side
	effect.

	Returns the same shape `locate` does, so a screen has one thing to read
	whether the answer came from the provider, from the guard above, or from a
	failure. On success the record is saved and `*_located_on` is stamped, which
	is what tells a later reader that this point came from an address rather than
	from somebody's finger.
	"""
	fields = fields_for(place)

	if has_point(deployment, place) and not force:
		return {
			"located": True,
			"latitude": deployment.get(fields["latitude"]),
			"longitude": deployment.get(fields["longitude"]),
			"matched": None,
			"reason": None,
		}

	answer = locate(deployment.get(fields["address"]))

	if not answer["located"]:
		return answer

	deployment.set(fields["latitude"], answer["latitude"])
	deployment.set(fields["longitude"], answer["longitude"])
	deployment.set(fields["located_on"], now_datetime())
	deployment.save()

	return answer


def relocate(deployment, place: str, latitude, longitude) -> dict:
	"""Drop the pin by hand. The correction a geocoder cannot make.

	Clears `*_located_on`, because the point no longer came from the address —
	and that difference is the whole reason the field exists. A later automatic
	pass finds coordinates present and leaves them alone.
	"""
	fields = fields_for(place)

	deployment.set(fields["latitude"], frappe.utils.flt(latitude))
	deployment.set(fields["longitude"], frappe.utils.flt(longitude))
	deployment.set(fields["located_on"], None)
	deployment.save()

	return {
		"located": has_point(deployment, place),
		"latitude": deployment.get(fields["latitude"]),
		"longitude": deployment.get(fields["longitude"]),
		"matched": None,
		"reason": None,
	}


def dto(deployment, place: str, name_field: str | None = None) -> dict:
	"""One place, with its links. Always the same shape.

	`map`/`directions` are `None` where there is no point, which is what lets a
	screen decide between drawing a link and drawing the address as plain text
	without knowing anything about coordinates.

	`name_field` is the one thing a prefix cannot derive: a society calls a
	deployment's meeting point `meeting_point` rather than `meeting_name`, and a
	caller that has to spell the other three anyway would rather spell this one
	than have this module hold a table of exceptions.
	"""
	fields = fields_for(place)
	latitude = deployment.get(fields["latitude"])
	longitude = deployment.get(fields["longitude"])

	return {
		"name": deployment.get(name_field or f"{place}_name"),
		"address": deployment.get(fields["address"]),
		"latitude": latitude or None,
		"longitude": longitude or None,
		"has_point": _is_point(latitude, longitude),
		# Present only where the point was resolved from the address. A pin
		# dropped by hand has none, and a screen may say so.
		"located_on": str(deployment.get(fields["located_on"]))
		if deployment.get(fields["located_on"])
		else None,
		"map": map_link(latitude, longitude),
		"directions": directions_link(latitude, longitude),
	}
