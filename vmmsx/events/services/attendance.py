# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Who said they are coming, and nothing else about the event.

**This is the vmmsx side of a line, not a crossing of it.** The events app owns
registration, ticket types, coupons, payment, guest verification and check in,
and `vmmsx/buzz/tests/test_delegation.py` fails the build if any file in this
app names one of those doctypes. Nothing here reads a booking or a ticket. What
this module owns is the society's own record of an intention: a volunteer told
us they mean to be there. Two different facts, kept apart on purpose, and this
one is the only one a coordinator planning a branch's week can act on.

**It replaced a `localStorage` key.** The Attend button used to write
`vmmsx:attending` in whichever browser pressed it, with a comment saying it was
the seam a doctype would slot into. This is that doctype. The behaviour a person
notices is that saying yes on a laptop is still true on a phone.

**Every verb is idempotent**, in the sense `CLAUDE.md` requires: the second call
observes the work is done and returns the same answer. Saying yes twice is one
row, and withdrawing something never said is not an error.

**No function here takes a person.** The profile comes from the session, the
same shape as `notifications/services/delivery.py` and every `my_*` endpoint in
the app. A caller cannot name anybody, so there is no check to get wrong.
"""

import frappe
from frappe.utils import now_datetime

ATTENDANCE_DOCTYPE = "VMMS Event Attendance"
PROFILE_DOCTYPE = "Red Profile"

ATTENDING = "Attending"
CANCELLED = "Cancelled"


def my_profile() -> str | None:
	"""The Red Profile carrying this session, or None.

	None is ordinary rather than an error. A signed-in person who has not
	registered for anything yet has no profile, and the honest answer to "what
	are you attending" is nothing, not a failure.
	"""
	user = frappe.session.user

	if not user or user == "Guest":
		return None

	return frappe.db.get_value(PROFILE_DOCTYPE, {"user": user}, "name")


def attend(event: str) -> dict:
	"""Say the session's owner intends to be at this event.

	Idempotent: a second call on a row already `Attending` rewrites nothing and
	returns the same answer. A row previously `Cancelled` is moved back rather
	than joined by a second one, because a person who changes their mind twice
	still has one standing answer.
	"""
	profile = _require_profile()
	event = _require_event(event)

	existing = _row(profile, event)

	if existing:
		if existing.status == ATTENDING:
			return _answer(event, ATTENDING)

		doc = frappe.get_doc(ATTENDANCE_DOCTYPE, existing.name)
		doc.status = ATTENDING
		doc.responded_on = now_datetime()
		_write(doc)

		return _answer(event, ATTENDING)

	doc = frappe.get_doc(
		{
			"doctype": ATTENDANCE_DOCTYPE,
			"red_profile": profile,
			"event": event,
			"status": ATTENDING,
			"responded_on": now_datetime(),
		}
	)
	_write(doc, insert=True)

	return _answer(event, ATTENDING)


def cancel(event: str) -> dict:
	"""Withdraw the intention. Idempotent, and it never deletes the row.

	The row survives for the reason `deployment/services/invitation.py` gives
	about a reply that was actually given: a coordinator who counted somebody in
	should be able to see that the answer changed, rather than finding that it
	appears never to have been given at all.

	Withdrawing something never said is not an error. It is a person pressing a
	control on a stale page, and the truthful answer is the one they wanted.
	"""
	profile = _require_profile()
	event = _require_event(event)

	existing = _row(profile, event)

	if not existing or existing.status == CANCELLED:
		return _answer(event, CANCELLED)

	doc = frappe.get_doc(ATTENDANCE_DOCTYPE, existing.name)
	doc.status = CANCELLED
	doc.responded_on = now_datetime()
	_write(doc)

	return _answer(event, CANCELLED)


def my_events() -> list[str]:
	"""The event identifiers this session's owner is currently attending.

	Identifiers only. What those events *are* is the listing's answer, read back
	through the seam by whoever needs it, so this module holds no copy of a
	title or a date that could go stale against the record it was copied from.
	"""
	profile = my_profile()

	if not profile:
		return []

	return [
		row.event
		for row in frappe.get_all(
			ATTENDANCE_DOCTYPE,
			filters={"red_profile": profile, "status": ATTENDING},
			fields=["event"],
			order_by="modified desc",
			limit_page_length=0,
			# Elevated for the reason `_write` gives at length: this is the
			# caller's own answer, selected by a profile derived from their
			# session, and a volunteer holds no role on this register.
			ignore_permissions=True,
		)
		if row.event
	]


def counts(events: list[str]) -> dict[str, int]:
	"""How many people have said they are going to each of these events.

	**The society's own answer to "how many are coming", and not Buzz's.** Buzz
	holds bookings — a seat, a ticket, a payment — and this holds intentions
	told to the branch. They are different numbers and the difference is the
	point: the coordinator planning transport counts the people who said they
	would be there, which includes everybody who never books anything, and
	`buzz/tests/test_delegation.py` still fails the build if this app so much as
	names a booking doctype.

	One grouped query for a whole page of cards. A count per card would be sixty
	round trips to draw a listing, and the number is decoration on a card rather
	than the reason for it.

	Elevated, and narrowly. What comes back is a count and nothing else — no
	name, no profile, no row — for events the caller was already shown, and a
	volunteer holds no role on this register for the reason `_write` sets out.
	"""
	wanted = [str(event).strip() for event in events or [] if str(event or "").strip()]

	if not wanted:
		return {}

	rows = frappe.get_all(
		ATTENDANCE_DOCTYPE,
		filters={"event": ("in", sorted(set(wanted))), "status": ATTENDING},
		fields=["event", "count(name) as going"],
		group_by="event",
		limit_page_length=0,
		ignore_permissions=True,
	)

	return {row.event: row.going for row in rows}


def count(event: str) -> int:
	"""The same for one event, for the screen a card opens."""
	return counts([event]).get(str(event or "").strip(), 0)


def roster(event: str, limit: int = 200) -> list[dict]:
	"""Who said they are coming, for somebody entitled to know.

	**Not for the volunteer's own screen, and that is a deliberate line.** A
	person marking "I will be there" is telling their society, not publishing it
	to every other volunteer on the site, and a portal card listing the names of
	everybody going would be a disclosure nobody consented to when they pressed
	the button. So the volunteer's card gets the number and the coordinator's
	screen gets the names — `api/events.py::attendees` is the only caller and it
	is gated on read permission for this register, which no self-service role
	holds.

	The names come from Red Profile, live, because that is where a person's name
	is; nothing is copied onto the attendance row and never has been.
	"""
	event = str(event or "").strip()

	if not event:
		return []

	rows = frappe.get_all(
		ATTENDANCE_DOCTYPE,
		filters={"event": event, "status": ATTENDING},
		fields=["red_profile", "responded_on"],
		order_by="responded_on asc",
		limit_page_length=limit,
		# The caller's entitlement was established at the endpoint, on this
		# doctype, before this was called. Elevated here so the read can join to
		# Red Profile in one pass rather than through a per-row permission check
		# on a register a coordinator already holds.
		ignore_permissions=True,
	)

	profiles = [row.red_profile for row in rows if row.red_profile]

	if not profiles:
		return []

	people = {
		row.name: row
		for row in frappe.get_all(
			"Red Profile",
			filters={"name": ("in", profiles)},
			# Named explicitly, so a field added to core's spine never starts
			# appearing on an events screen. The same discipline
			# `volunteer/services/identity._READABLE` keeps.
			fields=["name", "full_name", "email", "phone"],
			limit_page_length=0,
		)
	}

	return [
		{
			"red_profile": row.red_profile,
			"full_name": (people.get(row.red_profile) or {}).get("full_name") or row.red_profile,
			"email": (people.get(row.red_profile) or {}).get("email"),
			"phone": (people.get(row.red_profile) or {}).get("phone"),
			"responded_on": str(row.responded_on or ""),
		}
		for row in rows
		if row.red_profile in people
	]


def is_attending(event: str) -> bool:
	"""Whether this session's owner has said yes to one event."""
	if not event:
		return False

	profile = my_profile()

	if not profile:
		return False

	row = _row(profile, str(event))

	return bool(row and row.status == ATTENDING)


def _row(profile: str, event: str):
	return frappe.db.get_value(
		ATTENDANCE_DOCTYPE,
		{"red_profile": profile, "event": event},
		["name", "status"],
		as_dict=True,
	)


def _require_profile() -> str:
	profile = my_profile()

	if not profile:
		# Distinct from "you may not": there is nothing to refuse, because the
		# society has no record of this person to hang an answer on. It happens
		# to a signed-in account that has never registered for anything.
		frappe.throw(
			frappe._("Register with your society before saying you will attend an event."),
			frappe.ValidationError,
		)

	return profile


def _require_event(event: str) -> str:
	event = str(event or "").strip()

	if not event:
		frappe.throw(frappe._("Name the event."), frappe.ValidationError)

	return event


def _write(doc, insert: bool = False) -> None:
	"""Write an answer that was authorised by the shape of the endpoint.

	**The one elevated write in this module, and the reason is the volunteer.**
	A volunteer or member holds no role on `VMMS Event Attendance` and correctly
	never will: granting every portal user write permission on the register so
	they could add their own row would hand them everybody else's answers to get
	at one of their own.

	What replaces the permission check is not nothing, and it is stronger than a
	permission check would be. The row's `red_profile` is not a parameter. It is
	derived from `frappe.session.user` in `my_profile()` a few lines above, so
	there is no argument anywhere in this module that could name another person,
	and therefore no check that could be forgotten. That is the same reasoning
	`task/services/task.py::_save` sets out, with the boundary drawn one step
	tighter: tasks are authorised at the API and moved by the service, while
	here the service cannot be pointed off the caller at all.
	"""
	if insert:
		doc.insert(ignore_permissions=True)
	else:
		doc.save(ignore_permissions=True)


def _answer(event: str, status: str) -> dict:
	"""What every verb returns, so a caller never has to ask again to find out."""
	return {"event": event, "status": status, "attending": status == ATTENDING}
