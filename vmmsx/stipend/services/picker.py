# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The volunteer picker — who this supervisor may put on stipend paperwork.

A service, not a page. Stipend paperwork names people, and the moment an app
lets somebody browse a list of people it has to answer *which* people. This
module is that answer, and it is the only way a volunteer gets onto a progress
report or a payment form.

The scope guarantee
-------------------

**A supervisor can never be shown, or given, a volunteer they are not allowed to
see, and there is no argument by which they could ask to be.** Four things make
that true, and each is load-bearing:

0. **A Frappe role says whether the register may be read at all.** Roles answer
   *what*, geo answers *where*, and both are asked. This one is asked first
   because the queries below use `frappe.get_all`, which checks no permissions.
1. **The scope is derived from the session and cannot be passed in.** Look at
   `candidates()` and `resolve()`: neither takes a `user`, a `nodes` or a
   `geo_node` parameter. A caller supplies what they are *looking for*, never who
   they are or where they may look. An endpoint that accepted a scope override
   would be an endpoint for reading the whole volunteer register wearing a
   search-shaped name, and the check stopping that would be one more thing to get
   right. There is nothing to get right here.
2. **The scope comes from core, through the same registration core's own
   enforcement uses.** `_searchable_nodes()` asks `registry` which role scopes
   `VMMS Volunteer` — the society's `vmms_volunteer_scope_role` setting, resolved
   by core, never a role name written here — and then asks
   `scope.get_user_geo_scope` for that role's nodes. That is the identical pair of
   calls behind the volunteer list view's `WHERE ... IN`, so a volunteer this
   service returns is by construction a volunteer the supervisor could already
   open. This module computes no scope of its own: it asks core, exactly as
   `deployment/services/matching.py` asks core, so there is one answer to "where
   may this session see volunteers" and both services read it rather than two
   services deciding it.
3. **The search term is applied after the geo filter, never before.** The
   in-scope set is computed first and the term narrows it. Filtering by name and
   then checking scope would make the picker a probe: a supervisor could type an
   email and learn from the shape of the answer whether that person is on the
   register at all.
4. **It fails closed at every step.** No resolvable role, no assignment, or a
   term matching nobody in scope all produce an empty result, and an empty node
   set is never read as "unfiltered" — the query is not run at all, because a
   `filters={"home_geo_node": ("in", [])}` is the kind of thing a framework is
   entitled to treat as no filter.

Typing a name instead of browsing
---------------------------------

`resolve()` is the stricter mode: a supervisor who already knows exactly who they
mean gives a volunteer docname, a Red Profile docname or an email address rather
than scrolling a list. **It is not a way around the scope.** The identifier is
turned into a volunteer and then put through the same check, and the refusal is
**one message for both** "there is no such volunteer" and "that volunteer is not
yours" — because two different messages would turn this into an oracle for the
existence of anybody's email address on the register.

What is not filtered, and deliberately not faked
------------------------------------------------

See `PENDING_CRITERIA`. The picker holds no opinion on whether a suspended or
departed volunteer may appear on stipend paperwork: a report covers a period that
has already happened, somebody who left in March was there in February, and a
rule about which of them a society will still pay is a society's rule. The status
is returned with every candidate so that whoever is choosing can see it.
"""

import frappe
from frappe import _
from frappe.utils import cint
from onerc_core.access.services import registry, scope
from onerc_core.geo.services import adapter

VOLUNTEER_DOCTYPE = "VMMS Volunteer"
PROFILE_DOCTYPE = "Red Profile"

# Fields on core's identity spine a supervisor may search by. Deliberately the
# ones a person would type from memory, and deliberately not every field on the
# profile: this is a search box, not a query builder over somebody's record.
SEARCHABLE_PROFILE_FIELDS = ("full_name", "first_name", "last_name", "email")

# The one refusal for an identifier that did not resolve to a volunteer this
# session may see. Deliberately identical whether the volunteer does not exist,
# exists under a different identifier, or exists and is somebody else's: an
# error message that distinguished them would confirm who is on the register to
# anybody who can guess an email address.
UNRESOLVED_IDENTIFIER = (
	"No volunteer you may see matches that. Check the identifier, or ask whoever holds the"
	" assignment for that area to add them."
)

# What a caller is told is *not* being filtered on, returned with every result so
# that a list is never mistaken for a list of the people who ought to be on it.
PENDING_CRITERIA = (
	{
		"criterion": "volunteer status",
		"status": "pending",
		"why": (
			"A suspended or departed volunteer is still returned. Stipend paperwork covers a period"
			" that has already happened, so somebody who left last month was there the month before,"
			" and whether a society will still pay them is the society's rule rather than this app's."
			" The status is on every candidate so that whoever is choosing can see it."
		),
	},
	{
		"criterion": "already on this period's paperwork",
		"status": "proposed",
		"why": (
			"Nothing excludes a volunteer who already appears on another progress report covering"
			" overlapping days. Whether that should be refused, warned about, or allowed outright is"
			" a society's policy and has not been decided, so no rule is invented here."
		),
	},
)


def candidates(search: str | None = None, limit: int | None = None) -> dict:
	"""Volunteers this session may put on stipend paperwork.

	`search` narrows by the person's name or email, or by the volunteer docname.
	It narrows an already-scoped set and can only ever remove people from it.

	`limit` truncates the list, and is reported back as `truncated` when it bit,
	because a silently shortened list reads as "these are all of them".

	Returns an explicit dict. Never a Document and never a raw query result.
	"""
	nodes = _searchable_nodes()
	in_scope = _volunteers_at(nodes)
	matched = _narrowed(in_scope, search)

	matched.sort(key=lambda row: (row["full_name"] or "", row["volunteer"]))
	truncated = bool(limit) and len(matched) > cint(limit)

	return {
		"search": search or None,
		# A count of people this session may already see, so it discloses nothing
		# about the rest of the register.
		"in_scope": len(in_scope),
		"candidate_count": len(matched),
		"truncated": truncated,
		"candidates": matched[: cint(limit)] if limit else matched,
		"pending_criteria": [dict(row) for row in PENDING_CRITERIA],
	}


def resolve(identifier: str) -> str:
	"""One volunteer, named exactly, and only if this session may see them.

	Accepts a `VMMS Volunteer` docname, a `Red Profile` docname or an email
	address. Returns the volunteer docname; throws otherwise, with the same
	message whichever way it failed.

	This is the whole of the stricter mode. There is no variant that skips the
	check and no argument that widens it.
	"""
	volunteer = _identified(identifier)

	if not (volunteer and is_in_scope(volunteer)):
		frappe.throw(_(UNRESOLVED_IDENTIFIER), frappe.PermissionError, title=_("Volunteer Not Available"))

	return volunteer


def is_in_scope(volunteer: str) -> bool:
	"""Is this volunteer inside the session's own area?

	The predicate every write path goes through. Asked of the volunteer's own
	anchor against the set core gave us, so it agrees with the list view by
	construction.
	"""
	if not volunteer:
		return False

	home = frappe.db.get_value(VOLUNTEER_DOCTYPE, volunteer, "home_geo_node")

	return bool(home) and home in _searchable_nodes()


def assert_in_scope(volunteer: str) -> None:
	"""Throw unless this session may put `volunteer` on its paperwork.

	Same refusal as `resolve()`, for the same reason: a caller that already holds
	a docname learns nothing from being told which half of the check failed.
	"""
	if is_in_scope(volunteer):
		return

	frappe.throw(_(UNRESOLVED_IDENTIFIER), frappe.PermissionError, title=_("Volunteer Not Available"))


def describe(volunteer: str) -> dict:
	"""One candidate, as a DTO. Built field by field, never a Document."""
	from vmmsx.volunteer.services import identity

	doc = frappe.get_doc(VOLUNTEER_DOCTYPE, volunteer)

	return {
		"volunteer": doc.name,
		"red_profile": doc.red_profile,
		"full_name": identity.display_name(doc),
		"status": doc.status,
		"home_geo_node": doc.home_geo_node,
		"geo_path": adapter.get_full_path(doc.home_geo_node) if doc.home_geo_node else None,
	}


# --- the scope guarantee --------------------------------------------------


def _searchable_nodes() -> set[str]:
	"""Where the session user may see volunteers. Never an argument, never cached.

	Resolved through core's own registration for `VMMS Volunteer`, so the role is
	whichever role the society named in its settings and this file contains no
	role name at all. An unregistered doctype, an unresolvable role or a user
	holding nothing all come back empty, and empty means nothing is visible.

	Recomputed on every call, deliberately. Caching it would mean a supervisor who
	lost their assignment last week could still add volunteers today, which is the
	failure core's whole access model exists to prevent.

	**Role permission is asked first, and separately.** Geo scoping answers
	*where*; a Frappe role answers *what*, and they are two questions. The queries
	below use `frappe.get_all`, which does not check permissions, so a caller with
	no read permission on the volunteer register at all would otherwise be handed
	a page of it by a service that only ever asked about geo.
	"""
	if not frappe.has_permission(VOLUNTEER_DOCTYPE, ptype="read"):
		return set()

	registration = registry.for_doctype(VOLUNTEER_DOCTYPE)

	if not registration:
		# Nobody registered the volunteer register as scopeable. This service will
		# not invent an access policy for it: with no scope layer to ask, there is
		# no scope to honour, and returning everybody would be this module quietly
		# deciding that.
		return set()

	role = registry.resolve_role(registration)

	if not role:
		# Core has already logged the unresolved role. Failing closed is the only
		# safe answer: granting on "we could not tell" is how a scope layer becomes
		# decorative.
		return set()

	return scope.get_user_geo_scope(frappe.session.user, role)


def _volunteers_at(nodes: set[str]) -> list[dict]:
	"""Every volunteer placed at any of these nodes, as candidate DTOs.

	Returns nothing at all for an empty set rather than running the query. A query
	builder is entitled to read an empty `IN` as no condition, and the one place
	that must never happen is here.
	"""
	if not nodes:
		return []

	rows = frappe.get_all(
		VOLUNTEER_DOCTYPE,
		filters={"home_geo_node": ("in", sorted(nodes))},
		fields=["name", "red_profile", "status", "home_geo_node"],
		order_by="name asc",
	)
	people = _people(row["red_profile"] for row in rows)

	return [
		{
			"volunteer": row["name"],
			"red_profile": row["red_profile"],
			"full_name": _display_name(people.get(row["red_profile"])),
			"status": row["status"],
			"home_geo_node": row["home_geo_node"],
			"geo_path": adapter.get_full_path(row["home_geo_node"]) if row["home_geo_node"] else None,
		}
		for row in rows
	]


def _narrowed(in_scope: list[dict], search: str | None) -> list[dict]:
	"""The in-scope list, narrowed by a term. Never widened by one.

	The term is matched in Python against people already fetched rather than
	pushed into the query, because the set it filters is the security boundary and
	this way the term cannot reach the database ahead of the scope filter.
	"""
	term = (search or "").strip().lower()

	if not term:
		return list(in_scope)

	people = _people(row["red_profile"] for row in in_scope)

	return [
		row
		for row in in_scope
		if term in row["volunteer"].lower() or _matches(people.get(row["red_profile"]), term)
	]


def _people(profiles) -> dict[str, dict]:
	"""The searchable identity fields for these profiles, keyed by profile name.

	One query for the whole page rather than one per row, and only the fields a
	search box needs. `get_all` on named profiles rather than `get_doc`: a whole
	Red Profile carries its affiliation index, which core gates on read, and
	pulling the document here to take a name would step around a boundary this app
	has no business stepping around.
	"""
	names = sorted({profile for profile in profiles if profile})

	if not names:
		return {}

	rows = frappe.get_all(
		PROFILE_DOCTYPE,
		filters={"name": ("in", names)},
		fields=["name", *SEARCHABLE_PROFILE_FIELDS],
	)

	return {row["name"]: row for row in rows}


def _matches(person: dict | None, term: str) -> bool:
	"""Does this person's name or email contain the term?"""
	if not person:
		return False

	return any(term in (person.get(field) or "").lower() for field in SEARCHABLE_PROFILE_FIELDS)


def _display_name(person: dict | None) -> str:
	"""What to call somebody in a picker, from what the search query already read."""
	if not person:
		return ""

	full = (person.get("full_name") or "").strip()

	if full:
		return full

	return " ".join(part for part in (person.get("first_name"), person.get("last_name")) if part).strip()


# --- turning what somebody typed into a volunteer -------------------------


def _identified(identifier: str) -> str | None:
	"""The volunteer an identifier names, before any scope question is asked.

	Deliberately separate from the check in `resolve()`: this function is allowed
	to find anybody, and nothing but `resolve()` and `assert_in_scope()` may act on
	what it found. Keeping the two apart is what makes the scope check impossible
	to forget, because there is exactly one place it happens.
	"""
	identifier = (identifier or "").strip()

	if not identifier:
		return None

	if frappe.db.exists(VOLUNTEER_DOCTYPE, identifier):
		return identifier

	profile = identifier if frappe.db.exists(PROFILE_DOCTYPE, identifier) else _profile_by_email(identifier)

	if not profile:
		return None

	return frappe.db.get_value(VOLUNTEER_DOCTYPE, {"red_profile": profile}, "name")


def _profile_by_email(email: str) -> str | None:
	"""Core's profile for an email address, if there is exactly one.

	The email is core's, not this app's, and it is matched exactly rather than by
	prefix: a `like` here would let somebody find a person by guessing at the start
	of their address.
	"""
	return frappe.db.get_value(PROFILE_DOCTYPE, {"email": email}, "name")
