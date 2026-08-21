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
		"status": "advisory",
		"why": (
			"Answered, from the moment a caller gives dates: `VMMS Availability Schedule` is"
			" read for every volunteer on the page and each is marked available, unavailable"
			" or unknown across the deployment's own days. It ranks rather than excludes,"
			" because a register where nobody has filled a schedule in yet would otherwise"
			" read as a register where nobody is free. `only_available` makes it a filter for"
			" a caller who wants one."
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
		"status": "advisory",
		"why": (
			"Answered, from the moment a caller gives dates: a volunteer already assigned to"
			" another deployment whose days overlap these is marked as clashing, and the"
			" clashing deployment is named. It ranks rather than excludes, because whether"
			" somebody may serve on two things at once is a society's judgement about those"
			" two things and not a rule this app should invent. `exclude_conflicts` makes it a"
			" filter for a caller who wants one."
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
	start_date=None,
	end_date=None,
	only_available: bool = False,
	exclude_conflicts: bool = False,
) -> dict:
	"""Volunteers who fit this need, within the searcher's own area.

	`as_of` is the date the certification questions are asked about, defaulting
	to today. A caller building a candidate list for a deployment that starts in
	a month passes that date and gets the people who will still be certified
	then, which is the question they actually have.

	`start_date` and `end_date` are the deployment's own span, and giving them is
	what turns on the two criteria this module used to list as pending:

	    availability   read off `VMMS Availability Schedule`, per volunteer,
	                   across every weekday the span touches
	    clashes        another assignment of theirs whose days overlap these

	**Both rank rather than exclude, unless asked.** A register where hardly
	anybody has written a schedule yet would read as a register where hardly
	anybody is free, and a coordinator who has decided somebody can do two things
	at once should not have to fight the search about it. `only_available` and
	`exclude_conflicts` turn each into a real filter for the caller who wants
	one, and the screen draws them as two toggles rather than deciding.

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

	# Both of these are bulk reads over the page, for the same reason the two
	# above are: a query per volunteer is what made this screen slow the first
	# time. They answer nothing at all when the caller gave no dates, which is
	# why an old caller that never heard of them pays for neither.
	free = _bulk_availability(names, start_date, end_date)
	clashes = _bulk_conflicts(names, start_date, end_date)

	matched = [
		assessment
		for assessment in (
			_assess(
				volunteers[name],
				held_by_volunteer.get(name, []),
				required,
				as_of,
				availability=free.get(name),
				clash=clashes.get(name),
			)
			for name in names
			if name in volunteers
		)
		if assessment["is_candidate"]
		# The two advisory criteria, applied as filters only where the caller
		# asked. `is_unavailable` and not `not is_available`: somebody whose
		# schedule nobody has written is `unknown`, and dropping them would make a
		# register that has not answered look like one with nobody free.
		and not (only_available and assessment["availability"]["is_unavailable"])
		and not (exclude_conflicts and assessment["clash"]["is_clashing"])
	]

	matched.sort(key=_rank)

	return {
		"terms_of_reference": terms_of_reference,
		"geo_node": geo_node,
		"geo_path": adapter.get_full_path(geo_node) if geo_node else None,
		"as_of": as_of,
		# The span the availability and clash answers were computed over, echoed
		# back so a screen can say what it asked rather than assume.
		"start_date": getdate(start_date) if start_date else None,
		"end_date": getdate(end_date) if end_date else None,
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
	end = doc.get("needed_until") or doc.get("end_date")

	return candidates(
		doc.terms_of_reference,
		doc.get("geo_node"),
		as_of=as_of or start,
		limit=limit or doc.get("volunteers_requested"),
		# The document already knows its own span, so the availability and clash
		# answers come for free here. A caller who had to take the dates apart by
		# hand to get them would mostly not bother.
		start_date=start,
		end_date=end,
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

	# The names and the photographs, in one more query for the whole page rather
	# than a two-hop lookup per volunteer. A volunteer's identity lives on core's
	# Red Profile, and `identity.display_name` resolves one at a time — right for a
	# single record, and N queries across a page of fifty.
	#
	# Only `full_name` and `profile_photo` are read. Both are in
	# `identity._READABLE`; nothing in `identity._WITHHELD` is asked for here, and
	# the field list is written out rather than fetched wholesale so that a
	# sensitive field arriving on Red Profile later cannot be swept in by accident.
	profiles = {
		row["name"]: row
		for row in frappe.get_all(
			"Red Profile",
			filters={"name": ("in", [row["red_profile"] for row in rows if row["red_profile"]])},
			fields=["name", "full_name", "profile_photo"],
		)
	}

	for row in rows:
		person = profiles.get(row["red_profile"]) or {}
		row["full_name"] = person.get("full_name")
		row["profile_photo"] = person.get("profile_photo")

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


def _bulk_availability(names: list[str], start_date, end_date) -> dict:
	"""Whether each volunteer on the page is free across the deployment's days.

	Delegated whole to `volunteer/services/availability.py`, which owns what a
	weekly pattern means and answers in two queries for the page. Nothing about
	weekdays or schedules is re-derived here: a second reader of that pattern
	would be a second chance for the candidate list and the volunteer's own
	screen to disagree about when somebody said they were free.

	Empty when the caller gave no dates, which is the honest answer — there is no
	span to be free across.
	"""
	if not (names and start_date and end_date):
		return {}

	from vmmsx.volunteer.services import availability

	return availability.assess_many(names, start_date, end_date)


def _bulk_conflicts(names: list[str], start_date, end_date) -> dict:
	"""Which of these volunteers are already committed over the same days.

	One query for the whole page. Overlap is the ordinary interval test — an
	assignment starts before this ends and ends after this starts — and it counts
	only assignments that mean somebody is actually going. A question they have
	not answered is not a commitment, and a decline is the opposite of one.

	**`get_all`, not `get_list`.** A clash matters most when the other deployment
	is somewhere the searcher cannot see: a coordinator in one county needs to
	know this volunteer is already spoken for in the next one, and a scoped read
	would hide exactly the clash worth knowing about. What comes back is used to
	*warn*, and the deployment named is a docname and its dates — not its roster,
	its notes, or anything else about work outside the caller's area.
	"""
	if not (names and start_date and end_date):
		return {}

	from vmmsx.deployment.services import assignment

	rows = frappe.get_all(
		assignment.ASSIGNMENT_DOCTYPE,
		filters={
			"volunteer": ("in", names),
			"status": ("in", assignment.ON_DEPLOYMENT),
			"start_date": ("<=", getdate(end_date)),
			"end_date": (">=", getdate(start_date)),
		},
		fields=["volunteer", "deployment", "start_date", "end_date"],
		ignore_permissions=True,
	)

	clashes: dict[str, list[dict]] = {}

	for row in rows:
		clashes.setdefault(row["volunteer"], []).append(
			{
				"deployment": row["deployment"],
				"start_date": row["start_date"],
				"end_date": row["end_date"],
			}
		)

	return clashes


# --- assessing one volunteer, from rows already read -----------------------


def _assess(
	volunteer_row: dict,
	held_rows: list[dict],
	required: dict,
	as_of,
	availability: dict | None = None,
	clash: list[dict] | None = None,
) -> dict:
	"""Everything this service can say about one volunteer against one need.

	Takes the volunteer's own bulk-fetched row, their bulk-fetched
	certifications, their availability answer and their clashing assignments,
	rather than querying for any of them — the caller has already read all four
	for the whole page this volunteer is one of. Still computed fresh on every
	call: the deployability and the lapse are derived from dates at the moment of
	asking, so this answers about `as_of` and not about whenever a job last ran.

	**Neither availability nor a clash touches `is_candidate`.** That verdict
	stays exactly what it was — deployable, and holding what the terms require —
	because those two are facts about whether somebody *may* be sent, while being
	free and being double-booked are judgements about whether they *should* be,
	and the second pair belongs to the coordinator. The filters that act on them
	live in `candidates()` and only where a caller asked for them.
	"""
	from vmmsx.volunteer.services import certification

	deployability = certification.deployability_from(volunteer_row, held_rows, as_of)
	current = {row["certification_type"] for row in held_rows if not certification.is_lapsed(row, as_of)}

	missing = [key for key in required["mandatory"] if key not in current]
	desirable_held = [key for key in required["desirable"] if key in current]
	home = volunteer_row.get("home_geo_node")

	return {
		"volunteer": volunteer_row["name"],
		"red_profile": volunteer_row.get("red_profile"),
		# Read in bulk by `_bulk_volunteers`, not per volunteer: the display name
		# lives on core's Red Profile and resolving it one at a time is N queries
		# across a page. Falls back to the profile docname rather than to an empty
		# string, matching `identity.display_name`'s own answer.
		"full_name": volunteer_row.get("full_name") or volunteer_row.get("red_profile") or "",
		# The photograph, so a coordinator picking six people from a list of fifty
		# is choosing between faces rather than between rows of text. Null for
		# somebody who has not uploaded one, which every screen draws as initials.
		"photo": volunteer_row.get("profile_photo"),
		"status": volunteer_row.get("status"),
		"home_geo_node": home,
		"geo_path": adapter.get_full_path(home) if home else None,
		"deployable": deployability["deployable"],
		"blocking_reasons": deployability["reasons"],
		"missing_certifications": missing,
		"desirable_certifications_held": desirable_held,
		# Advisory, both of them: shown, ranked on, and never part of the verdict.
		# Defaulted rather than left absent when the caller gave no dates, so a
		# screen reads the same keys either way and never has to test for their
		# existence before it can render a row.
		"availability": availability or _unknown_availability(),
		"clash": {
			"is_clashing": bool(clash),
			"deployments": clash or [],
		},
		# The one derived verdict, and the only field callers should branch on.
		"is_candidate": deployability["deployable"] and not missing,
	}


def _unknown_availability() -> dict:
	"""The availability answer for a call that asked no dates.

	Built through the availability service rather than as a literal here, so this
	module holds no second copy of what the three states mean.
	"""
	from vmmsx.volunteer.services import availability

	return availability.assess(None, None, None)


def _rank(assessment: dict) -> tuple:
	"""Best first: free, then unclashing, then most of the desirable certifications.

	Ranking is still deliberately shallow, and the two new keys do not change
	that. They order what a coordinator would order by hand anyway — somebody who
	said they are free before somebody nobody has asked, and somebody unspoken-for
	before somebody already committed elsewhere — rather than expressing an
	opinion about which volunteer a society ought to send.

	The availability key is 0 for available, 1 for unknown, 2 for unavailable, so
	the person who has not filled in a schedule sits between the two answers
	rather than at the bottom with the people who said no. Ties break on the
	docname so the same search twice returns the same order rather than quietly
	reshuffling.
	"""
	free = assessment["availability"]
	rank_of_availability = 0 if free["is_available"] else 2 if free["is_unavailable"] else 1

	return (
		rank_of_availability,
		1 if assessment["clash"]["is_clashing"] else 0,
		-len(assessment["desirable_certifications_held"]),
		assessment["volunteer"],
	)
