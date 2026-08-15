# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Matching — who could do this work, here, on this date.

A service, not a page. It takes a need (a Terms of Reference and a place) and
returns candidate volunteers. There is no desk screen, no client bundle and no
portal route: `api/deployment.py` exposes it, and anything that wants a list
calls it.

The scope guarantee
-------------------

**A searcher can never be shown a volunteer they are not allowed to see, and
there is no argument by which they could ask to be.** Three things make that
true, and each is load-bearing:

1. **The scope is derived from the session and cannot be passed in.** Look at
   `candidates()`: there is no `user` parameter and no `nodes` parameter. A
   caller supplies what they are *looking for*, never who they are or where
   they may look. An endpoint that accepted a scope override would be an
   endpoint for reading anybody's register wearing a search-shaped name, and the
   check stopping that would be one more thing to get right. There is nothing to
   get right here.
2. **The scope comes from core, through the same registration core's own
   enforcement uses.** `_searchable_nodes()` asks `registry` which role scopes
   `VMMS Volunteer` — the society's `vmms_volunteer_scope_role` setting, resolved
   by core, never a role name written here — and then asks
   `scope.get_user_geo_scope` for that role's nodes. That is the identical pair
   of calls behind the list view's `WHERE ... IN`, so a volunteer this service
   returns is by construction a volunteer the searcher could already open, and
   the two cannot drift into disagreeing.
3. **It fails closed at every step.** No resolvable role, no assignment, or a
   need anchored outside the searcher's area all produce an empty node set, and
   an empty node set produces no candidates. Empty is never read as
   "unfiltered": the intersection is computed first and the query is not run at
   all when it is empty, because a `filters={"home_geo_node": ("in", [])}` is
   the kind of thing a framework is entitled to treat as no filter.

The need's own subtree narrows it further. A searcher with national scope
looking for volunteers for a branch's work gets that branch's volunteers, not
the country's, because the answer is the *intersection* of what they may see
with where the work is.

What is matched, and what is not
--------------------------------

Real, and enforced below:

* **geo** — the hard filter above.
* **the volunteer's own status** — a Suspended or Exited volunteer is not a
  candidate. Answered by `certification.deployability()`, which derives it.
* **certifications, with the lapse computed on the date being asked about.** A
  mandatory requirement the volunteer does not hold, or holds lapsed, excludes
  them. A lapse of any type the society marked as blocking excludes them even
  if these particular terms did not ask for it. Nothing reads a stored flag;
  there is no stored flag to read.

Not matched, and deliberately not faked — see `PENDING_CRITERIA`. The largest
of them is skills: a volunteer application collects `declared_skills` as free
text that no code reads, and there is no structured record of what a volunteer
can do. Matching on that text would produce a filter that looks like a
capability check and is a substring search, which is worse than not having one.
"""

import frappe
from frappe.utils import cint, getdate, today
from onerc_core.access.services import registry, scope
from onerc_core.geo.services import adapter

from vmmsx.deployment.services import terms as terms_service

VOLUNTEER_DOCTYPE = "VMMS Volunteer"

# What a caller is told is *not* being matched on yet, returned with every
# result so that a list of ten candidates is never mistaken for a list of the
# ten people who fit. Each entry names the seam it is waiting for.
PENDING_CRITERIA = (
	{
		"criterion": "skills",
		"status": "pending",
		"why": (
			"There is no structured record of what a volunteer can do. A volunteer application"
			" collects declared skills as free text which no code reads, and the volunteer register"
			" holds no skill of its own. Matching on that text would be a substring search wearing"
			" a capability check's name, so it is not done at all."
		),
	},
	{
		"criterion": "availability",
		"status": "pending",
		"why": (
			"Availability is free text on the application for the same reason: days, hours and"
			" shift patterns are society variable and belong in a configured vocabulary that does"
			" not exist yet. Nothing here reads it."
		),
	},
	{
		"criterion": "training in progress",
		"status": "pending",
		"why": (
			"The learning seam awards a certification when a course completes, so a volunteer"
			" part way through the training these terms require is simply not yet certified and is"
			" not a candidate. Whether a society wants to see them anyway, marked as qualifying"
			" soon, is a decision nobody has taken."
		),
	},
	{
		"criterion": "already deployed elsewhere",
		"status": "proposed",
		"why": (
			"Nothing excludes a volunteer who is already on another deployment over the same"
			" days. Whether double-booking should exclude somebody, warn about them, or be"
			" allowed outright is a society's policy and has not been decided, so no rule is"
			" invented here."
		),
	},
)


def candidates(
	terms_of_reference: str,
	geo_node: str,
	as_of=None,
	limit: int | None = None,
) -> dict:
	"""Volunteers who fit this need, within the searcher's own area.

	`as_of` is the date the certification questions are asked about, defaulting
	to today. A caller building a candidate list for a deployment that starts in
	a month passes that date and gets the people who will still be certified
	then, which is the question they actually have.

	`limit` truncates the ranked list. It is reported back as `truncated` when it
	bit, because a silently shortened list reads as "these are all of them".

	Returns an explicit dict. Never a Document and never a raw query result.
	"""
	as_of = getdate(as_of or today())
	required = terms_service.requirements(terms_of_reference)
	nodes = _need_nodes(geo_node)

	considered = _volunteers_at(nodes)
	matched = [
		assessment
		for assessment in (_assess(name, required, as_of) for name in considered)
		if assessment["is_candidate"]
	]

	matched.sort(key=_rank)
	truncated = bool(limit) and len(matched) > cint(limit)

	return {
		"terms_of_reference": terms_of_reference,
		"geo_node": geo_node,
		"geo_path": adapter.get_full_path(geo_node) if geo_node else None,
		"as_of": as_of,
		"required_certifications": required["mandatory"],
		"desirable_certifications": required["desirable"],
		# Both counts are about people the searcher may already see, so neither
		# tells them anything about the rest of the register.
		"considered": len(considered),
		"candidate_count": len(matched),
		"truncated": truncated,
		"candidates": matched[: cint(limit)] if limit else matched,
		"pending_criteria": [dict(row) for row in PENDING_CRITERIA],
	}


def candidates_for(doc, as_of=None, limit: int | None = None) -> dict:
	"""The same question asked of a document that carries a need.

	A `VMMS Deployment Request` and a `VMMS Deployment` both name a terms of
	reference and a Geo Node, and both know which date their work begins, so
	neither caller should have to take those apart by hand. The date defaults to
	the day the work starts rather than to today: a request raised in March for
	work in June wants the people who will be certified in June.
	"""
	start = doc.get("needed_from") or doc.get("start_date")

	return candidates(
		doc.terms_of_reference,
		doc.get("geo_node"),
		as_of=as_of or start,
		limit=limit or doc.get("volunteers_requested"),
	)


# --- the scope guarantee --------------------------------------------------


def _searchable_nodes() -> set[str]:
	"""Where the session user may see volunteers. Never an argument, never cached.

	Resolved through core's own registration for `VMMS Volunteer`, so the role is
	whichever role the society named in its settings and this file contains no
	role name at all. An unregistered doctype, an unresolvable role or a user
	holding nothing all come back empty, and empty means nothing is visible.

	Recomputed on every call, deliberately. Caching it would mean a searcher who
	lost their assignment last week could still find volunteers today, which is
	the failure core's whole access model exists to prevent.
	"""
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
		# safe answer: granting on "we could not tell" is how a scope layer
		# becomes decorative.
		return set()

	return scope.get_user_geo_scope(frappe.session.user, role)


def _need_nodes(geo_node: str) -> set[str]:
	"""The nodes a candidate may sit at: the need's subtree, inside the searcher's area.

	An intersection, in that order. The searcher's scope is the ceiling and the
	need's place is the narrowing, so a national coordinator searching for a
	ward's work gets that ward, and a ward coordinator searching for the region's
	work gets their ward rather than the region.
	"""
	searchable = _searchable_nodes()

	if not (geo_node and searchable):
		return set()

	beneath = {geo_node, *adapter.get_descendants(geo_node)}

	return beneath & searchable


def _volunteers_at(nodes: set[str]) -> list[str]:
	"""Volunteers placed at any of these nodes.

	Returns nothing at all for an empty set rather than running the query. A
	query builder is entitled to read an empty `IN` as no condition, and the one
	place that must never happen is here.
	"""
	if not nodes:
		return []

	return frappe.get_all(
		VOLUNTEER_DOCTYPE,
		filters={"home_geo_node": ("in", sorted(nodes))},
		order_by="name asc",
		pluck="name",
	)


# --- assessing one volunteer ----------------------------------------------


def _assess(volunteer_name: str, required: dict, as_of) -> dict:
	"""Everything this service can say about one volunteer against one need.

	Assembled field by field, and computed on every call: the deployability and
	the lapse are derived from dates at the moment of asking, so this answers
	about `as_of` and not about whenever a job last ran.
	"""
	from vmmsx.volunteer.services import certification, identity

	volunteer = frappe.get_doc(VOLUNTEER_DOCTYPE, volunteer_name)
	deployability = certification.deployability(volunteer, as_of)
	current = _current_certifications(volunteer_name, as_of)

	missing = [key for key in required["mandatory"] if key not in current]
	desirable_held = [key for key in required["desirable"] if key in current]

	return {
		"volunteer": volunteer.name,
		"red_profile": volunteer.red_profile,
		"full_name": identity.display_name(volunteer),
		"status": volunteer.status,
		"home_geo_node": volunteer.home_geo_node,
		"geo_path": adapter.get_full_path(volunteer.home_geo_node) if volunteer.home_geo_node else None,
		"deployable": deployability["deployable"],
		"blocking_reasons": deployability["reasons"],
		"missing_certifications": missing,
		"desirable_certifications_held": desirable_held,
		# The one derived verdict, and the only field callers should branch on.
		"is_candidate": deployability["deployable"] and not missing,
	}


def _current_certifications(volunteer_name: str, as_of) -> set[str]:
	"""Certification types this volunteer holds and which have not lapsed by `as_of`.

	The lapse is asked of `certification.is_lapsed` rather than filtered with an
	`expiry_date <` in a query. Both would give the same answer today; only this
	keeps one definition of what lapsed means, so a change to that rule cannot
	leave a query here still applying the old one.
	"""
	from vmmsx.volunteer.services import certification

	return {
		row["certification_type"]
		for row in certification.held(volunteer_name)
		if not certification.is_lapsed(row, as_of)
	}


def _rank(assessment: dict) -> tuple:
	"""Best first: most of the desirable certifications, then by name.

	Ranking is deliberately shallow. Sorting candidates by anything cleverer
	would be this app expressing an opinion about which volunteer a society ought
	to send, and that is a coordinator's judgement made with facts this service
	does not hold. Ties break on the docname so the same search twice returns the
	same order rather than quietly reshuffling.
	"""
	return (-len(assessment["desirable_certifications_held"]), assessment["volunteer"])
