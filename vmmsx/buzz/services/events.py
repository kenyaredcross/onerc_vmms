# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""BUZZ-02 — reading Buzz's published events, and stopping there.

The second half of the Buzz seam, and the reason it is a *separate* file from
`geo.py` is that the two cross the boundary in opposite directions. `geo.py`
writes into Buzz's model: vmmsx adds one custom field to `Buzz Event`. This
module only reads, and only what Buzz already publishes to the world.

**Browse here, book there.** The portal lists events and then hands off. Every
card's call to action is a full navigation to Buzz's own event page at
`/b/<route>`, because Buzz owns registration, ticket types, coupons, payment,
guest verification and check-in, and each of those is a flow with money or
identity in it. Re-exposing any of them through a vmmsx endpoint would mean a
second implementation of a booking rule that has to stay in step with Buzz's
forever. So this file names no booking, ticket, attendee or check-in doctype —
`tests/test_delegation.py` asserts that against the source, and it asserts it
for the whole app including this file.

**Published is Buzz's decision, not ours.** The filter is `is_published`, the
same flag Buzz's own public pages read. vmmsx invents no second notion of
visibility and no approval step of its own: an event a society has published in
Buzz is an event the portal shows, and one it has not is one the portal does not
know exists.

**Geo is a filter, never a gate.** BUZZ-01 made `geo_node` optional on purpose,
so most events carry no anchor at all. Filtering *out* the unanchored ones would
hide the majority of a society's events from the people it runs them for, so an
unplaced event is shown to everybody and `near` narrows only among events that
actually declared a placement. That is the reverse of ACC-02's rule for
vmmsx's own records, and deliberately: this is Buzz's record, not ours.

**Safe when Buzz is absent.** Same graceful-absence contract as `geo.py` and the
payments and learning seams: `frappe.get_installed_apps()` is asked rather than
an import attempted, and every reader answers empty rather than raising.
"""

import frappe
from frappe.utils import getdate, today

from vmmsx.buzz.services import geo

EVENT_DOCTYPE = "Buzz Event"
CATEGORY_DOCTYPE = "Event Category"
VENUE_DOCTYPE = "Event Venue"
HOST_DOCTYPE = "Event Host"

# Where Buzz serves an event to the public. One place, so a card's link and the
# `href` in the DTO cannot drift apart.
EVENT_PATH = "/b"

# A listing is a listing. Somebody scrolling a season of events does not need
# five hundred of them in one response, and an unbounded read on a public-ish
# endpoint is how a slow query becomes an outage.
MAX_ROWS = 60

# A calendar month is not a listing and the cap has to be different in kind. A
# grid that quietly stopped at sixty would draw a month with the last week
# empty, which is worse than a slow query: it is a wrong answer that looks like
# a right one. Still bounded, because unbounded is how a slow query becomes an
# outage, but bounded well above any month a national society will actually run.
MAX_RANGE_ROWS = 300

# The columns every card is built from, named once. Three readers select them
# now, and a field added to the DTO in `_as_card` but to only two of three
# queries is a card that renders differently depending on which screen asked.
_CARD_FIELDS = [
	"name",
	"title",
	"route",
	"short_description",
	"category",
	"venue",
	"medium",
	"start_date",
	"end_date",
	"start_time",
	"end_time",
	"time_zone_label",
	"banner_image",
	"card_image",
	# Three facts about the event itself, all of them already on Buzz's own
	# public page. None is a ticket, a price or a seat — see `_as_card`, which
	# says what each is for and why reading them is not a step across the
	# booking boundary this seam exists to hold.
	"free_event",
	"registrations_close_at",
	"external_registration_page",
	"registration_url",
	geo.GEO_NODE_FIELD,
]


def is_available() -> bool:
	"""Is Buzz installed on this site? Delegated, so there is one answer."""
	return geo.is_available()


def event_url(route: str | None) -> str | None:
	"""Buzz's own public page for this event, or None if it has no route.

	An event with no route is one Buzz has not finished publishing —
	`validate_route` fills the field in on publish — so there is nowhere to send
	somebody and the card renders without its call to action rather than with a
	link to a 404.
	"""
	return f"{EVENT_PATH}/{route}" if route else None


def upcoming(
	search: str | None = None,
	category: str | None = None,
	near: str | None = None,
	venue: str | None = None,
	host: str | None = None,
	date_from: str | None = None,
	date_to: str | None = None,
	limit: int = MAX_ROWS,
) -> list[dict]:
	"""Published events that have not finished yet, soonest first.

	`end_date` rather than `start_date` decides what "upcoming" means, so a
	four-day training that began yesterday is still on the page for somebody
	deciding whether to turn up tomorrow. Buzz leaves `end_date` empty for a
	single-day event, so the comparison falls back to `start_date`.

	`near` is a Geo Node. It admits events anchored at or beneath it *and* every
	event with no anchor at all, for the reason in the module docstring: the
	anchor is optional, so absence cannot be read as "somewhere else".

	`venue` and `host` are Buzz's own records — where the event is held and who
	is running it. They are exact matches rather than searches, because both are
	picked from a list the same query built.

	`date_from` and `date_to` narrow the window. They are **inside** the
	"upcoming" rule rather than instead of it: `date_from` cannot reach into the
	past, because this reader answers what is still to come and a date picker is
	not a way around that. `date_to` closes the far end, so "what is on this
	month" is a question somebody can actually ask.
	"""
	if not is_available():
		return []

	rows = frappe.get_all(
		EVENT_DOCTYPE,
		filters=_filters(search, category, venue, host, date_from, date_to),
		or_filters=_not_finished(),
		fields=_CARD_FIELDS,
		order_by="start_date asc, start_time asc",
		limit_page_length=_bounded(limit),
		# Buzz's own public listing reads published events without a permission
		# check, and this endpoint serves the same rows to the same people. The
		# gate is `is_published`, which is the society's decision on that
		# document, not the portal's; requiring read permission on Buzz Event
		# would mean granting every volunteer a role in another app just to see
		# what their branch has already put in public.
		ignore_permissions=True,
	)

	if near:
		rows = _within(rows, near)

	return [_as_card(row) for row in rows]


def detail(event: str) -> dict | None:
	"""One published event, with the long description a card has no room for.

	**Same boundary as the listing, and only the boundary.** `is_published` is
	the whole rule, exactly as in `upcoming()`, so this cannot serve an event
	Buzz has not put in public — a caller who guesses a docname gets nothing.
	Nothing about the roster, the tickets sold or the attendees is here, and
	`test_delegation.py` asserts this file names none of those doctypes.

	`about` is Buzz's Text Editor field and is the one thing this reader adds
	over `_as_card`: it is the event's own page copy, written on the desk by the
	society, and it is what makes a detail screen worth opening.
	"""
	if not is_available():
		return None

	row = frappe.db.get_value(
		EVENT_DOCTYPE,
		{"name": event, "is_published": 1},
		[
			"name",
			"title",
			"route",
			"short_description",
			"about",
			"category",
			"venue",
			"medium",
			"start_date",
			"end_date",
			"start_time",
			"end_time",
			"time_zone_label",
			"banner_image",
			"card_image",
			"host",
			"free_event",
			"registrations_close_at",
			"external_registration_page",
			"registration_url",
			geo.GEO_NODE_FIELD,
		],
		as_dict=True,
	)

	if not row:
		return None

	return {
		**_as_card(row),
		# The wide crop is the right one for a hero; the card image stands in.
		"banner": row.get("banner_image") or row.get("card_image") or "",
		"about": row.get("about") or "",
		"host": row.get("host") or "",
		"venue_address": _venue_address(row.get("venue")),
	}


def by_names(names: list[str], include_finished: bool = False) -> list[dict]:
	"""The published events among a list of identifiers, soonest first.

	**The read behind "what am I attending".** `events/services/attendance.py`
	holds identifiers and nothing else, deliberately, so that no title or date
	is copied into a vmmsx row where it could drift out of step with the record
	it was copied from. This is how those identifiers become events again, and
	it is the same boundary as every other reader here: `is_published`, which is
	the listing's own decision. An answer somebody gave to an event since
	unpublished comes back as nothing, which is right. The event is not on.

	`include_finished` is what a calendar needs and a listing does not. Looking
	back at what you attended last month is a reasonable thing to do on a
	calendar and a confusing thing to find on a page headed "upcoming", so the
	caller says which it wants rather than this guessing.
	"""
	if not is_available():
		return []

	wanted = [str(name) for name in (names or []) if str(name or "").strip()]

	if not wanted:
		return []

	rows = frappe.get_all(
		EVENT_DOCTYPE,
		filters=[[EVENT_DOCTYPE, "is_published", "=", 1], [EVENT_DOCTYPE, "name", "in", wanted]],
		or_filters=None if include_finished else _not_finished(),
		fields=_CARD_FIELDS,
		order_by="start_date asc, start_time asc",
		limit_page_length=_bounded(len(wanted)),
		# Same argument as `upcoming`: these are events the society has already
		# put in public, and requiring read permission on another app's doctype
		# would mean granting every volunteer a role in it.
		ignore_permissions=True,
	)

	return [_as_card(row) for row in rows]


def in_range(date_from: str, date_to: str, limit: int = MAX_RANGE_ROWS) -> list[dict]:
	"""Every published event touching a window, including one already finished.

	**Separate from `upcoming()` rather than a flag on it, because it breaks
	that reader's rule on purpose.** `upcoming()` refuses to reach into the past
	and says so in its own docstring: it answers what is still to come, and a
	date picker is not a way around that. A calendar asks a genuinely different
	question. Somebody paging back to last month wants to see the day they
	turned up, and a month grid that empties itself the moment it is behind
	today reads as broken rather than as principled.

	Overlap, not containment. An event that started before the window and is
	still running inside it belongs on the grid, which is why the near end is
	two ORed comparisons rather than one: the listing leaves `end_date` empty
	for a single-day event, so neither column can answer alone.
	"""
	if not is_available() or not date_from or not date_to:
		return []

	rows = frappe.get_all(
		EVENT_DOCTYPE,
		filters=[
			[EVENT_DOCTYPE, "is_published", "=", 1],
			[EVENT_DOCTYPE, "start_date", "<=", str(date_to)],
		],
		or_filters=[
			[EVENT_DOCTYPE, "start_date", ">=", str(date_from)],
			[EVENT_DOCTYPE, "end_date", ">=", str(date_from)],
		],
		fields=_CARD_FIELDS,
		order_by="start_date asc, start_time asc",
		limit_page_length=_bounded(limit, ceiling=MAX_RANGE_ROWS),
		ignore_permissions=True,
	)

	return [_as_card(row) for row in rows]


def _venue_address(venue: str | None) -> str:
	"""Where the venue actually is, for somebody deciding whether they can get there.

	Buzz names a venue by its docname, which is a label rather than an address.
	A detail screen that showed only "Nairobi Central Branch Hall" would be
	withholding the one fact somebody opened it for.
	"""
	if not venue:
		return ""

	return frappe.db.get_value(VENUE_DOCTYPE, venue, "address") or ""


def categories() -> list[dict]:
	"""The enabled categories, for the picker on the events screen.

	Every enabled category, not only those with an event on them: a filter that
	silently loses an option when the last event in it passes is a filter that
	looks broken. The screen shows a plain empty state instead.
	"""
	if not is_available():
		return []

	rows = frappe.get_all(
		CATEGORY_DOCTYPE,
		filters={"enabled": 1},
		fields=["name", "description"],
		order_by="name asc",
		# Same argument as `upcoming`: a category is a label on a public page.
		ignore_permissions=True,
	)

	return [{"category": row.name, "label": row.name, "description": row.description or ""} for row in rows]


def venues() -> list[dict]:
	"""The venues with a published, still-upcoming event at them.

	Unlike `categories()`, which offers every enabled one, this offers only
	places something is actually happening. The two differ because the failure
	differs: a category with nothing in it reads as a filter that lost its
	options, while a venue with nothing on reads as a place to turn up to on a
	day when nobody is there. A society's whole venue book is not a useful
	question for somebody deciding where to go this month.
	"""
	if not is_available():
		return []

	rows = frappe.get_all(
		EVENT_DOCTYPE,
		filters=_filters(None, None),
		or_filters=_not_finished(),
		pluck="venue",
		# Same argument as `upcoming`: these are labels on already-public events.
		ignore_permissions=True,
	)

	return [{"venue": name, "label": name} for name in sorted({row for row in rows if row})]


def hosts() -> list[dict]:
	"""Who is running something, for the organisation picker. Same rule as venues."""
	if not is_available():
		return []

	rows = frappe.get_all(
		EVENT_DOCTYPE,
		filters=_filters(None, None),
		or_filters=_not_finished(),
		pluck="host",
		ignore_permissions=True,
	)

	return [{"host": name, "label": name} for name in sorted({row for row in rows if row})]


def _not_finished() -> list[list]:
	"""Either date still ahead of us. ORed, and that is the whole rule.

	Buzz leaves `end_date` empty for a single-day event, so "has it finished"
	cannot be asked of one column. Two ORed comparisons answer it exactly, and
	they answer it in SQL rather than in Python over an unbounded read:

	- a multi-day event that began yesterday and ends tomorrow matches on
	  `end_date`, so it stays on the page for somebody deciding whether to turn
	  up for the rest of it;
	- a single-day event today matches on `start_date`, its `end_date` being
	  empty;
	- a single-day event last week matches neither, because a NULL `end_date`
	  compares false rather than true.
	"""
	return [
		[EVENT_DOCTYPE, "start_date", ">=", today()],
		[EVENT_DOCTYPE, "end_date", ">=", today()],
	]


def _filters(
	search: str | None,
	category: str | None,
	venue: str | None = None,
	host: str | None = None,
	date_from: str | None = None,
	date_to: str | None = None,
) -> list[list]:
	"""What the database is asked, rather than what is sorted out afterwards."""
	filters: list[list] = [[EVENT_DOCTYPE, "is_published", "=", 1]]

	if category:
		filters.append([EVENT_DOCTYPE, "category", "=", category])

	if venue:
		filters.append([EVENT_DOCTYPE, "venue", "=", venue])

	if host:
		filters.append([EVENT_DOCTYPE, "host", "=", host])

	# A window inside "upcoming", never instead of it. `_not_finished()` is ORed
	# and still applies, so the near end can be brought forward but not into the
	# past: this reader answers what is still to come, and a date picker is not a
	# way round that.
	if date_from:
		filters.append([EVENT_DOCTYPE, "start_date", ">=", max(str(date_from), today())])

	# Closed against `start_date`, so an event that starts inside the window is in
	# it however long it runs. Asking `end_date` to fit as well would drop the
	# four-day training somebody is looking for from "what is on this week".
	if date_to:
		filters.append([EVENT_DOCTYPE, "start_date", "<=", str(date_to)])

	if search:
		# Title only. `about` is a Text Editor field full of markup, and a
		# `%like%` across it matches on tag names rather than on words somebody
		# typed.
		filters.append([EVENT_DOCTYPE, "title", "like", f"%{search.strip()}%"])

	return filters


def _bounded(limit: int, ceiling: int = MAX_ROWS) -> int:
	"""A caller's row limit, held between one and whatever that reader's cap is.

	The ceiling is a parameter because a listing and a calendar month are not
	the same size of question. See `MAX_RANGE_ROWS`.
	"""
	try:
		value = int(limit)
	except (TypeError, ValueError):
		return ceiling

	return max(1, min(value, ceiling))


def _within(rows: list, near: str) -> list:
	"""Events at or beneath `near`, plus every event that declared no placement.

	The descendant set is resolved through core's adapter, the only way vmmsx is
	allowed to ask a question about the geo tree.
	"""
	from onerc_core.geo.services import adapter

	inside = set(adapter.get_descendants(near) or [])
	inside.add(near)

	return [row for row in rows if not row.get(geo.GEO_NODE_FIELD) or row.get(geo.GEO_NODE_FIELD) in inside]


def _as_card(row: dict) -> dict:
	"""One event, built field by field.

	An explicit DTO rather than the row, for the reason `CLAUDE.md` gives: a
	`get_all` result handed to a caller leaks whatever the schema gained since
	anybody last looked, and this row comes from *another app's* schema, which
	this one does not control and cannot review.
	"""
	start = row.get("start_date")
	end = row.get("end_date")

	return {
		# Stringified because `Buzz Event` is autoincrement-named, so the row
		# carries an int and every other docname this app hands a caller is a
		# string. Which naming rule another app chose is not a fact this DTO
		# should pass on: `EventCard.event` says `string`, react-router hands
		# `detail()` back a string, and a field whose type follows Buzz's
		# schema is the leak this boundary exists to stop.
		"event": str(row.get("name") or ""),
		"title": row.get("title") or "",
		"summary": row.get("short_description") or "",
		"category": row.get("category") or "",
		"venue": row.get("venue") or "",
		"medium": row.get("medium") or "",
		"start_date": str(start) if start else "",
		# Normalised to the day it actually runs, so the frontend never has to
		# decide what an absent end date means.
		"end_date": str(end) if end else (str(start) if start else ""),
		"start_time": str(row.get("start_time")) if row.get("start_time") else "",
		"end_time": str(row.get("end_time")) if row.get("end_time") else "",
		"time_zone": row.get("time_zone_label") or "",
		# `card_image` is Buzz's own listing image and is the right one for a
		# grid; the banner is a wide hero crop and only stands in when there is
		# nothing else. Either may be empty, and the card draws a placeholder.
		"image": row.get("card_image") or row.get("banner_image") or "",
		"geo_node": row.get(geo.GEO_NODE_FIELD) or "",
		# **Where the call to action actually goes.** Buzz's own event page,
		# unless the society said registration happens somewhere else — an
		# `external_registration_page` with a `registration_url` behind it is a
		# society telling Buzz "not here", and a card that ignored it sent
		# everybody to a page with no way to book on it.
		#
		# Still a full navigation away, which is the whole of what this boundary
		# asks: nothing about tickets, prices or seats is re-implemented here,
		# and the link is honoured rather than second-guessed.
		"href": _registration_url(row) or event_url(row.get("route")),
		# Whether the society is charging for this one. A published fact and the
		# first thing a volunteer wants to know; not a price, and not a ticket.
		"free": bool(row.get("free_event")),
		# When it stops being possible to register, or empty where the society
		# has not said. A card that shows an event nobody can book any more,
		# with no indication of it, is a card that wastes somebody's afternoon.
		"registrations_close_at": str(row.get("registrations_close_at") or ""),
		"multi_day": bool(start and end and getdate(end) != getdate(start)),
	}


def _registration_url(row: dict) -> str:
	"""The society's own registration page for this event, where it set one.

	Both halves, because either alone is a half-configured event: the tickbox
	without an address is a society that meant to point somewhere and did not,
	and an address without the tickbox is one that changed its mind. Empty in
	both cases, and the caller falls back to Buzz's page.
	"""
	if not row.get("external_registration_page"):
		return ""

	return str(row.get("registration_url") or "").strip()
