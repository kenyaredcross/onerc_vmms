# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The events screen's door onto Buzz. Read-only, and it stops at browsing.

Two endpoints, both thin: everything they know about events is in
`vmmsx/buzz/services/events.py`, the seam, and this file adds a DTO boundary and
nothing else. Naming Buzz's doctype here would break the rule
`vmmsx/buzz/tests/test_delegation.py` enforces, and the rule is worth the
indirection — it is what keeps the crossing findable in one place.

**There is no booking endpoint here and there will not be one.** Every card's
call to action for a ticket is a full navigation to Buzz's own event page,
because Buzz owns ticket types, coupons, payment, guest verification and
check-in, and each of those is a flow with money or identity in it. A vmmsx
endpoint wrapping any of them would be a second implementation of a rule that
has to stay in step with Buzz's forever, and the first time the two disagreed
somebody would be charged the wrong amount.

**`attend` is not that, and the distinction is the whole reason it is allowed
to exist here.** It writes the society's own record of an intention — this
volunteer told us they mean to be there — which is a fact about a person the
society already holds a file on, not a claim about a seat, a payment or a place
held. Nothing it writes is read by Buzz and nothing Buzz writes is read by it.
`events/services/attendance.py` sets the line out in full, and
`vmmsx/buzz/tests/test_delegation.py` still fails the build if any file in this
app names a booking, ticket, attendee or check-in doctype.

**The possessive three take no person.** `attending`, `attend` and
`cancel_attendance` derive the profile from the session, the same shape as
`my_queue` and `my_memberships`, so a caller cannot answer on anybody's behalf
and there is no check here to get wrong.

**Signed in, deliberately.** Neither is `allow_guest`. The public landing page's
events are content blocks an administrator wrote, and `api/content.py::surface`
is the only guest-readable endpoint in this app: opening a screen to the public
is a flag on a content surface, not a decorator somebody has to find in a source
file. Events on the *portal* are for people who have joined.

**Buzz absent is an ordinary state, not an error.** vmmsx does not declare
`buzz` in `required_apps`. On a site without it both endpoints answer empty, and
the screen says so rather than showing a spinner forever.
"""

import frappe

from vmmsx.buzz.services import events as seam
from vmmsx.events.services import attendance


@frappe.whitelist()
def upcoming(
	search: str | None = None,
	category: str | None = None,
	near: str | None = None,
	venue: str | None = None,
	host: str | None = None,
	date_from: str | None = None,
	date_to: str | None = None,
	limit: int = 60,
) -> dict:
	"""Published events that have not finished, soonest first.

	`available` travels with the rows rather than being a second endpoint,
	because the screen needs it at the moment it decides what to draw: no events
	because Buzz is not installed and no events because none are scheduled are
	different sentences to put in front of somebody, and asking twice would mean
	a page that changes its mind after it has rendered.
	"""
	return {
		"available": seam.is_available(),
		"events": seam.upcoming(
			search=search,
			category=category,
			near=near,
			venue=venue,
			host=host,
			date_from=date_from,
			date_to=date_to,
			limit=limit,
		),
	}


@frappe.whitelist()
def detail(event: str) -> dict | None:
	"""One published event in full, for the screen a card opens.

	**The card and this answer the same question at two depths, and the boundary
	is identical**: `is_published`, which is Buzz's own decision. Naming a
	docname buys nothing a caller could not already see in the listing, so there
	is no permission check to get wrong and none to forget.

	None rather than an error for an event that is not there or not published:
	an old link is an ordinary thing to follow, and the screen says so.

	Booking is still Buzz's. The detail screen has more room for the call to
	action than a card does and it is the same call to action — a full navigation
	to `href`. There is no ticket, price or availability in this DTO, because
	acquiring one is a flow with money in it that this app does not re-implement.
	"""
	return seam.detail(event)


@frappe.whitelist()
def attending(include_finished: int = 0) -> dict:
	"""What the logged-in person has said they are going to, soonest first.

	Takes no person, so it cannot be pointed at anybody else's diary.

	**The identifiers are ours and the events are Buzz's**, joined here and
	nowhere else. `attendance.my_events()` holds nothing but identifiers, so an
	event whose details changed after somebody said yes comes back changed, and
	one the society has since unpublished comes back not at all rather than as a
	card describing something that is no longer on.

	`include_finished` is what the calendar asks for and the events screen does
	not: looking back at what you turned up to last month is reasonable on a
	grid of days and confusing under a heading that says upcoming.
	"""
	names = attendance.my_events()

	return {
		"available": seam.is_available(),
		# The identifiers travel with the cards. A person may have answered for
		# an event that has since been unpublished, and the screen needs to be
		# able to tell "you are attending nothing" from "the one thing you were
		# attending is no longer listed" without asking a second time.
		"answered": names,
		"events": seam.by_names(names, include_finished=bool(int(include_finished or 0))),
	}


@frappe.whitelist(methods=["POST"])
def attend(event: str) -> dict:
	"""Say you intend to be at an event. Idempotent.

	**Not a booking.** See this module's docstring: it records what the person
	told their society, which is the thing a coordinator plans a branch's week
	around. It holds no seat and takes no money, and the screen that calls it is
	careful never to say otherwise.

	The event is checked against the published listing before the answer is
	kept, so a docname somebody guessed or an event that has been withdrawn
	cannot leave a row pointing at nothing.
	"""
	if not seam.detail(event):
		frappe.throw(frappe._("That event is not on."), frappe.DoesNotExistError)

	return attendance.attend(event)


@frappe.whitelist(methods=["POST"])
def cancel_attendance(event: str) -> dict:
	"""Withdraw the intention. Idempotent, and it does not check the listing.

	Deliberately asymmetric with `attend`. Saying yes to something that is not
	on is a mistake worth refusing; taking back an answer is never one, and an
	event unpublished after somebody said they were coming is exactly when a
	person most wants the answer off their list.
	"""
	return attendance.cancel(event)


@frappe.whitelist()
def calendar(date_from: str, date_to: str) -> dict:
	"""Every published event touching a window, and which of them are yours.

	One request rather than two, because the grid cannot draw a single day
	correctly until it knows both: a day carrying an event the person is going
	to is marked differently from a day merely carrying an event, and asking
	separately would mean a calendar that changes its markings after it has
	rendered.

	`attending` is a list of identifiers rather than a flag on each card,
	because the same event appears on the grid whether or not it is theirs and a
	second DTO shape for the same record is how two screens start disagreeing
	about what an event is.
	"""
	return {
		"available": seam.is_available(),
		"events": seam.in_range(date_from, date_to),
		"attending": attendance.my_events(),
	}


@frappe.whitelist()
def filters() -> dict:
	"""What the pickers on the events screen offer.

	Categories come from Buzz. Places come from core's adapter through the geo
	endpoint the volunteer application's picker already uses, so this returns
	only the categories and leaves the geo picker to `api/geo.py` — one tree
	reader, not two.
	"""
	return {
		"available": seam.is_available(),
		"categories": seam.categories(),
		# Where something is on, and who is running it. Both are drawn from the
		# events that are actually upcoming rather than from the society's whole
		# venue book, so a picker never offers a place with nothing at it.
		"venues": seam.venues(),
		"hosts": seam.hosts(),
	}
