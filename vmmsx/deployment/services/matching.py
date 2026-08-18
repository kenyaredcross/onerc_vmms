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
there is no argument by which they could ask to be.** Two things make that
true, and each is load-bearing:

1. **The scope is derived from the session and cannot be passed in.** Look at
   `candidates()`: there is no `user` parameter and no `nodes` parameter. A
   caller supplies what they are *looking for*, never who they are or where
   they may look. An endpoint that accepted a scope override would be an
   endpoint for reading anybody's register wearing a search-shaped name, and the
   check stopping that would be one more thing to get right. There is nothing to
   get right here.
2. **The scope comes from core, through `capabilities.search()`/`count()`,
   which is `frappe.get_list` under a queryable surface.** `frappe.get_list`
   runs core's permission query condition for `VMMS Volunteer` on every call,
   the identical mechanism the list view's own `WHERE ... IN` stands on, so a
   volunteer this service returns is by construction a volunteer the searcher
   could already open. A society that has not configured a scope role for the
   volunteer register gets nothing back here for the same reason every other
   `frappe.get_list` screen in this app gets nothing: an unresolvable scope is
   `frappe.get_list`'s to fail closed on, not this module's to work around.

The need's own subtree narrows it further, as `geo_node` passed to
`capabilities.search()`. A searcher with national scope looking for volunteers
for a branch's work gets that branch's volunteers, not the country's, because
the answer is the *intersection* of what they may see with where the work is —
computed once, by `capabilities._search_filters()`, rather than a second time
here.

What is matched, and what is not
--------------------------------

Real, and enforced below:

* **geo** — the hard filter above.
* **the volunteer's own status** — a Suspended or Exited volunteer is not a
  candidate. Answered by `certification.deployability_from()`, which derives it.
* **certifications, with the lapse computed on the date being asked about.** A
  mandatory requirement the volunteer does not hold, or holds lapsed, excludes
  them. A lapse of any type the society marked as blocking excludes them even
  if these particular terms did not ask for it. Nothing reads a stored flag;
  there is no stored flag to read.
* **skills and a name/docname search** — `skills` and `search` are passed
  straight through to `capabilities.search()`, the same queryable surface the
  volunteer Registry stands on, so "a first aider who also does logistics" is a
  question this module can now actually ask instead of listing under
  `PENDING_CRITERIA`.

Not matched, and deliberately not faked — see `PENDING_CRITERIA`.

Ranking is over the page fetched, not the whole scope
-------------------------------------------------------

`candidates()` no longer loads every volunteer in the searcher's area to rank
them and slice off the top. It asks `capabilities.search()` for one bounded,
already-scoped page of names — the same pagination the Registry screen uses —
and only *that* page is assessed and ranked. At a few dozen volunteers in
scope this is invisible; at the thousands a national society's register can
hold, assessing everyone before ranking anyone was the actual cost of this
search, not the certification lookups. `considered` in the response is the
count `capabilities.count()` would page through, so a caller can tell "there
are more than are shown" from `truncated` without this module pretending a
page of fifty is a ranking of three thousand.
"""

import frappe
from frappe.utils import cint, getdate, today
from onerc_core.geo.services import adapter

from vmmsx.deployment.services import terms as terms_service

VOLUNTEER_DOCTYPE = "VMMS Volunteer"

# The page size a search is bounded to when the caller does not ask for a
# smaller one. Assessment (certifications, deployability) only runs on names
# this many long, never on a whole scope.
MATCH_PAGE = 50

# What a caller is told is *not* being matched on yet, returned with every
# result so that a list of ten candidates is never mistaken for a list of the
# ten people who fit. Each entry names the seam it is waiting for.
PENDING_CRITERIA = (
	{
		"criterion": "availability",
		"status": "pending",
		"why": (
			"Availability is a structured selector on the volunteer register, but"
			" nothing here asks it a question yet: days, hours and shift patterns"
			" against a deployment's own dates is its own piece of matching logic,"
			" not a filter this module has taken on."
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
	offset: int = 0,
	search: str | None = None,
	skills: list | None = None,
) -> dict:
	"""Volunteers who fit this need, within the searcher's own area.

	`as_of` is the date the certification questions are asked about, defaulting
	to today. A caller building a candidate list for a deployment that starts in
	a month passes that date and gets the people who will still be certified
	then, which is the question they actually have.

	`search` (a name or a docname) and `skills` (a list of `VMMS Skill` keys)
	narrow the page fetched *before* anything is assessed, through
	`capabilities.search()` — the queryable surface the volunteer Registry
	already stands on. `offset` pages through the same filtered, scoped result.

	`limit` bounds the page fetched and defaults to `MATCH_PAGE`. It is not
	merely a display truncation any more: it is how many volunteers this call
	assesses at all, which is what keeps this cheap at society scale. Reported
	back as `truncated` whenever the filtered scope holds more than this page,
	because a page of fifty must never read as "these are all of them".

	Returns an explicit dict. Never a Document and never a raw query result.
	"""
	from vmmsx.volunteer.services import capabilities

	as_of = getdate(as_of or today())
	required = terms_service.requirements(terms_of_reference)
	page_size = cint(limit) or MATCH_PAGE
	page_offset = cint(offset)

	try:
		names = capabilities.search(
			geo_node=geo_node,
			skills=skills,
			search=search,
			limit=page_size,
			offset=page_offset,
		)
		considered_total = capabilities.count(geo_node=geo_node, skills=skills, search=search)
	except frappe.PermissionError:
		# `frappe.get_list`, unlike `frappe.get_all`, throws for a caller who
		# holds no ordinary read permission on VMMS Volunteer at all — a role
		# built with only a geo-scope assignment and no Role Permission grant.
		# Failing closed here means empty, the answer an unresolvable scope
		# already gets everywhere else in this module, not a raw permission
		# error surfacing on a screen that asked an honest question.
		names = []
		considered_total = 0

	volunteers = _bulk_volunteers(names)
	held_by_volunteer = _bulk_certifications(names)

	matched = [
		assessment
		for assessment in (
			_assess(volunteers[name], held_by_volunteer.get(name, []), required, as_of)
			for name in names
			if name in volunteers
		)
		if assessment["is_candidate"]
	]

	matched.sort(key=_rank)

	return {
		"terms_of_reference": terms_of_reference,
		"geo_node": geo_node,
		"geo_path": adapter.get_full_path(geo_node) if geo_node else None,
		"as_of": as_of,
		"required_certifications": required["mandatory"],
		"desirable_certifications": required["desirable"],
		# The total the filter would page through, not the size of the page
		# assessed below — the two now differ on purpose. See the module
		# docstring's "ranking is over the page fetched" note.
		"considered": considered_total,
		"candidate_count": len(matched),
		"truncated": considered_total > page_offset + len(names),
		"candidates": matched,
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


# --- bulk reads, once per page, never once per volunteer ------------------


def _bulk_volunteers(names: list[str]) -> dict:
	"""The handful of scalar fields `_assess` needs, for a whole page at once.

	`frappe.get_all` with an explicit field list, never `frappe.get_doc`: a full
	document load pulls every child table on the volunteer — skills, languages,
	availability — to answer with four scalar fields, once per name in the page.
	Keyed by name, so a caller looks a volunteer up rather than re-filtering a
	list.
	"""
	if not names:
		return {}

	rows = frappe.get_all(
		VOLUNTEER_DOCTYPE,
		filters={"name": ("in", names)},
		fields=["name", "red_profile", "status", "home_geo_node"],
	)

	return {row["name"]: row for row in rows}


def _bulk_certifications(names: list[str]) -> dict:
	"""Every held certification for a whole page of volunteers, in one query.

	Replaces what used to be a `certification.held()` call per volunteer —
	sometimes two, once for the blocking list and once for the lapsed list —
	with one query grouped in Python. The lapse itself is still computed by
	`certification.is_lapsed()`, never re-derived here, so there remains exactly
	one definition of what "lapsed" means.
	"""
	from vmmsx.volunteer.services import certification

	if not names:
		return {}

	fields = [*certification.HELD_FIELDS, "volunteer"]
	rows = frappe.get_all(
		certification.CERTIFICATION_DOCTYPE,
		filters={"volunteer": ("in", names)},
		fields=fields,
	)

	grouped: dict[str, list[dict]] = {}

	for row in rows:
		grouped.setdefault(row["volunteer"], []).append(row)

	return grouped


# --- assessing one volunteer, from rows already read -----------------------


def _assess(volunteer_row: dict, held_rows: list[dict], required: dict, as_of) -> dict:
	"""Everything this service can say about one volunteer against one need.

	Takes the volunteer's own bulk-fetched row and their bulk-fetched
	certifications rather than querying for either — the caller has already
	read both for the whole page this volunteer is one of. Still computed fresh
	on every call: the deployability and the lapse are derived from dates at the
	moment of asking, so this answers about `as_of` and not about whenever a job
	last ran.
	"""
	from vmmsx.volunteer.services import certification, identity

	deployability = certification.deployability_from(volunteer_row, held_rows, as_of)
	current = {
		row["certification_type"] for row in held_rows if not certification.is_lapsed(row, as_of)
	}

	missing = [key for key in required["mandatory"] if key not in current]
	desirable_held = [key for key in required["desirable"] if key in current]
	home = volunteer_row.get("home_geo_node")

	return {
		"volunteer": volunteer_row["name"],
		"red_profile": volunteer_row.get("red_profile"),
		"full_name": identity.display_name(volunteer_row),
		"status": volunteer_row.get("status"),
		"home_geo_node": home,
		"geo_path": adapter.get_full_path(home) if home else None,
		"deployable": deployability["deployable"],
		"blocking_reasons": deployability["reasons"],
		"missing_certifications": missing,
		"desirable_certifications_held": desirable_held,
		# The one derived verdict, and the only field callers should branch on.
		"is_candidate": deployability["deployable"] and not missing,
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
