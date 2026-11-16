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
2. **The scope comes from core, through Frappe's own `get_match_cond` for
   `VMMS Volunteer`** — core's permission query condition and any user
   permissions, the identical text `frappe.get_list` and the list view's own
   `WHERE ... IN` stand on, so a volunteer this service returns is by
   construction a volunteer the searcher could already open. A society that has not configured a scope role for the
   volunteer register gets nothing back here for the same reason every other
   `frappe.get_list` screen in this app gets nothing: an unresolvable scope is
   `frappe.get_list`'s to fail closed on, not this module's to work around.

The need's own subtree narrows it further, as `geo_node`. A searcher with national scope looking for volunteers
for a branch's work gets that branch's volunteers, not the country's, because
the answer is the *intersection* of what they may see with where the work is —
computed in the one query `matching_names()` runs.

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
* **skills, professions, languages, the surge roster and a name search** —
  each any-of within itself and all of them together, so "a nurse or a
  clinical officer who speaks Somali" is one question.

Not matched, and deliberately not faked — see `PENDING_CRITERIA`.

Every filter runs in one query, over the whole county
---------------------------------------------------
`matching_names()` asks the database one question per search: who in the
need's subtree, inside the searcher's scope, is Active, holds every mandatory
certification on the date asked about, has no blocking lapse, and fits the
skills, professions, languages, surge roster and clash filters. All of it is a
`WHERE` clause on `VMMS Volunteer`, driven by the indexed `home_geo_node`, with
each per-person question an indexed lookup by `volunteer` or `parent`. Nothing
is assessed in Python before it has passed every filter.

That is what makes the total true. The page-of-fifty design this replaced
filtered *after* paging, so "3 found" could mean 300 fit, and a coordinator
picking from a county of thousands never saw the list they asked for. Now
`considered` and `candidate_count` are the number of people who fit, the
ranking is over all of them, and the page is a slice of that order. Only the
page is then read in full (names, photographs, certifications, availability)
by the bulk readers below.

**The scope is the same one `frappe.get_list` applies**, read from Frappe's own
`get_match_cond` for `VMMS Volunteer`: core's geo condition and any user
permissions, verbatim, `AND`ed into the query. A caller with no read on the
register gets `frappe.PermissionError` from it, which `candidates()` turns into
`register_readable: false` as before.
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
		"criterion": "how much they are already carrying",
		"status": "advisory",
		"why": (
			"Answered: every volunteer on the page comes back with how many open assignments"
			" they hold — placed, asked or accepted — across every deployment, including ones"
			" outside the searcher's own area. It ranks rather than excludes, because how much"
			" is too much is a judgement about a person and a week that no number in this app"
			" can make. `max_workload` makes it a filter for a caller who wants one."
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
	terms_of_reference: str | None,
	geo_node: str,
	as_of=None,
	limit: int | None = None,
	offset: int = 0,
	search: str | None = None,
	skills: list | None = None,
	languages: list | None = None,
	start_date=None,
	end_date=None,
	only_available: bool = False,
	exclude_conflicts: bool = False,
	max_workload: int | None = None,
	professions: list | None = None,
	surge_only: bool = False,
	exclude_deployment: str | None = None,
	availability_slots: list | None = None,
	certification_types: list | None = None,
	residence_counties: list | None = None,
	residence_sub_counties: list | None = None,
	residence_wards: list | None = None,
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

	`max_workload` is the third of the same kind: every candidate comes back with
	how many open assignments they already hold, and giving a number drops the
	people carrying more than that. Advisory by default like the other two,
	because how much is too much depends on the person, the week and the work,
	and no number in this app knows any of those.

	`search` (a name, email or docname), `skills` (`VMMS Skill` keys),
	`languages`, `professions` (`Profession` names, read off the person's Red
	Profile) and `surge_only` (an active, in-licence surge roster entry) are
	filters in the same query as everything else — see `matching_names()`.
	`exclude_deployment` leaves out the people already open on that deployment
	and does not count it as their clash, for a coordinator topping one up.
	`offset` pages through the ranked result.

	**`terms_of_reference` may be `None`**, and then no certification question is
	asked at all. A bulk task batch wants to know who is available in a branch
	without naming a mission document, and inventing a requirement for it would be
	this app deciding what work needs.

	`limit` is the page size and defaults to `MATCH_PAGE`. Only the page is read
	in full; `candidate_count` is everybody who fits, and `truncated` says when
	that is more than the page.

	Returns an explicit dict. Never a Document and never a raw query result.
	"""
	as_of = getdate(as_of or today())
	# **No terms of reference means no certification questions**, not an error.
	# A bulk task batch asks who is available in a branch without naming a
	# mission document, and the honest answer to "what must they hold" is
	# nothing — everything else this function does still applies, including
	# deployability, availability, workload and the geo scope.
	required = (
		terms_service.requirements(terms_of_reference)
		if terms_of_reference
		else {"mandatory": [], "desirable": []}
	)
	page_size = cint(limit) or MATCH_PAGE
	page_offset = cint(offset)

	register_readable = True

	try:
		ranked = matching_names(
			terms_of_reference,
			geo_node,
			as_of=as_of,
			required=required,
			search=search,
			skills=skills,
			languages=languages,
			professions=professions,
			surge_only=surge_only,
			start_date=start_date,
			end_date=end_date,
			only_available=only_available,
			exclude_conflicts=exclude_conflicts,
			max_workload=max_workload,
			exclude_deployment=exclude_deployment,
			availability_slots=availability_slots,
			certification_types=certification_types,
			residence_counties=residence_counties,
			residence_sub_counties=residence_sub_counties,
			residence_wards=residence_wards,
		)
	except frappe.PermissionError:
		# "Nobody fits this work" and "you cannot read the volunteer register"
		# are different facts, and a coordinator shown the first when the second
		# is true will go looking for the fault in their terms of reference.
		# `register_readable` is what lets the screen say which one it is.
		register_readable = False
		ranked = []

	names = ranked[page_offset : page_offset + page_size]

	volunteers = _bulk_volunteers(names)
	held_by_volunteer = _bulk_certifications(names)

	# The page alone is read in full: names, photographs, certifications,
	# availability, clashes. Every one a bulk read over the page, never a query
	# per volunteer.
	free = _bulk_availability(names, start_date, end_date)
	clashes = _bulk_conflicts(names, start_date, end_date, exclude_deployment)
	workload = _bulk_workload(names)

	# Already ranked by `matching_names`. The verdict is asked again per row as
	# a safety net: a row the query let through that `_assess` refuses is
	# dropped rather than offered.
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
				workload=workload.get(name, 0),
			)
			for name in names
			if name in volunteers
		)
		if assessment["is_candidate"]
	]

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
		# Everybody who fits, across the whole county — not the page. The page is
		# `candidates`, a slice of this many in rank order.
		"considered": len(ranked),
		# False when this caller cannot read the volunteer register at all. See
		# the `except` above: it separates an empty answer from an inaccessible
		# one, which no other field here can express.
		"register_readable": register_readable,
		"candidate_count": len(ranked),
		"truncated": len(ranked) > page_offset + len(names),
		"candidates": matched,
		"pending_criteria": [dict(row) for row in PENDING_CRITERIA],
	}


# The filters past the needs and the toggles, named once so the endpoint, the
# "ask everyone matching" path and the search all take the same set.
LIST_FILTERS = (
	"availability_slots",
	"certification_types",
	"residence_counties",
	"residence_sub_counties",
	"residence_wards",
)


def matching_names(
	terms_of_reference: str | None,
	geo_node: str | None,
	as_of=None,
	required: dict | None = None,
	search: str | None = None,
	skills: list | None = None,
	languages: list | None = None,
	professions: list | None = None,
	surge_only: bool = False,
	start_date=None,
	end_date=None,
	only_available: bool = False,
	exclude_conflicts: bool = False,
	max_workload: int | None = None,
	exclude_deployment: str | None = None,
	availability_slots: list | None = None,
	certification_types: list | None = None,
	residence_counties: list | None = None,
	residence_sub_counties: list | None = None,
	residence_wards: list | None = None,
) -> list[str]:
	"""Everybody who fits, best first, as volunteer names. One query, then a sort.

	The filters are the old Deployment Request Tool's quick filters, kept so a
	coordinator who used it finds the same ones (Nov 2026): skills, professions
	(its "designation"), certifications (its "courses"), languages, the
	availability a volunteer gave at registration, and where they live — county,
	sub-county and ward of residence, as written on their profile.

	The page `candidates()` shows is a slice of this, and "ask everyone who
	matches" is all of it — the same answer, so the number a coordinator was
	shown is the number of people asked.

	Raises `frappe.PermissionError` for a caller who cannot read the volunteer
	register at all, as `frappe.get_list` would.

	**Ranked in Python, over rows already filtered.** The query returns one short
	row per person who fits — name, workload, clash, desirable certifications
	held, whether they have written a schedule — so the ordering `_rank` defines
	is applied to the whole set without a second definition of it in SQL.
	Availability is the one key SQL cannot answer (it is a weekly pattern), and it
	is asked only of the people who have a schedule at all, in two queries.
	"""
	from frappe.desk.reportview import get_match_cond

	from vmmsx.deployment.services import assignment
	from vmmsx.volunteer.services import availability
	from vmmsx.volunteer.services.capabilities import SELECTORS
	from vmmsx.volunteer.services.certification import CERTIFICATION_DOCTYPE, CERTIFICATION_TYPE_DOCTYPE
	from vmmsx.volunteer.services.surge import ENTRY_DOCTYPE, STATUS_ACTIVE as SURGE_ACTIVE
	from vmmsx.volunteer.services.volunteer import STATUS_ACTIVE

	as_of = getdate(as_of or today())
	required = required or (
		terms_service.requirements(terms_of_reference)
		if terms_of_reference
		else {"mandatory": [], "desirable": []}
	)
	has_span = bool(start_date and end_date)

	# Raises for a caller with no read on the register; `%` is already doubled.
	scope = get_match_cond(VOLUNTEER_DOCTYPE)

	volunteer = f"`tab{VOLUNTEER_DOCTYPE}`"
	certifications = f"`tab{CERTIFICATION_DOCTYPE}`"
	assignments = f"`tab{assignment.ASSIGNMENT_DOCTYPE}`"
	values = {
		"active": STATUS_ACTIVE,
		"as_of": as_of,
		"open": tuple(assignment.OPEN_STATUSES),
		"on_deployment": tuple(assignment.ON_DEPLOYMENT),
		"deployment": exclude_deployment or "",
	}
	where = [f"{volunteer}.status = %(active)s"]
	joins = ""

	if geo_node:
		where.append(f"{volunteer}.home_geo_node in %(nodes)s")
		values["nodes"] = (geo_node, *adapter.get_descendants(geo_node))

	# Any of the chosen values within one list; every list together.
	asked = {"skills": skills, "languages": languages, "availability": availability_slots}

	for fieldname, link_field, _doctype, _label in SELECTORS:
		wanted = tuple(value for value in (asked.get(fieldname) or []) if value)

		if not wanted:
			continue

		child = frappe.get_meta(VOLUNTEER_DOCTYPE).get_field(fieldname).options
		values[fieldname] = wanted
		where.append(
			f"""exists (select 1 from `tab{child}` chosen
				where chosen.parent = {volunteer}.name
				and chosen.parenttype = %(volunteer_doctype)s
				and chosen.parentfield = '{fieldname}'
				and chosen.`{link_field}` in %({fieldname})s)"""
		)
		values["volunteer_doctype"] = VOLUNTEER_DOCTYPE

	wanted_professions = tuple(value for value in (professions or []) if value)
	term = (search or "").strip()
	# Where they live, as their profile says. Text the registration form wrote,
	# matched exactly: the choices offered are read from the same column.
	residence = {
		field: wanted
		for field, chosen in (
			("vmms_residence_county", residence_counties),
			("vmms_residence_sub_county", residence_sub_counties),
			("vmms_residence_ward", residence_wards),
		)
		if (wanted := tuple(value for value in (chosen or []) if value))
	}

	if wanted_professions or term or residence:
		joins = f"left join `tabRed Profile` person on person.name = {volunteer}.red_profile"

	if wanted_professions:
		values["professions"] = wanted_professions
		where.append("person.vmms_profession in %(professions)s")

	for field, wanted in residence.items():
		values[field] = wanted
		where.append(f"person.`{field}` in %({field})s")

	if term:
		values["like"] = f"%{term}%"
		where.append(
			f"({volunteer}.name like %(like)s or person.full_name like %(like)s or person.email like %(like)s)"
		)

	if surge_only:
		values["surge_active"] = SURGE_ACTIVE
		where.append(
			f"""exists (select 1 from `tab{ENTRY_DOCTYPE}` entry
				where entry.volunteer = {volunteer}.name
				and entry.status = %(surge_active)s
				and (entry.licence_expiry is null or entry.licence_expiry >= %(as_of)s))"""
		)

	# Holding every mandatory certification, in date on the day asked about —
	# `certification.is_lapsed` is "expiry before as_of", so in date is the rest.
	for index, key in enumerate(required["mandatory"]):
		values[f"mandatory_{index}"] = key
		where.append(
			f"""exists (select 1 from {certifications} held
				where held.volunteer = {volunteer}.name
				and held.certification_type = %(mandatory_{index})s
				and (held.expiry_date is null or held.expiry_date >= %(as_of)s))"""
		)

	# Holding any of the certifications the coordinator filtered by, in date.
	wanted_certifications = tuple(value for value in (certification_types or []) if value)

	if wanted_certifications:
		values["certifications"] = wanted_certifications
		where.append(
			f"""exists (select 1 from {certifications} held
				where held.volunteer = {volunteer}.name
				and held.certification_type in %(certifications)s
				and (held.expiry_date is null or held.expiry_date >= %(as_of)s))"""
		)

	# No lapse of a type the society marked as blocking, asked or not.
	where.append(
		f"""not exists (select 1 from {certifications} held
			join `tab{CERTIFICATION_TYPE_DOCTYPE}` kind on kind.name = held.certification_type
			where held.volunteer = {volunteer}.name
			and held.expiry_date < %(as_of)s
			and kind.blocks_deployment_when_lapsed = 1)"""
	)

	if exclude_deployment:
		where.append(
			f"""not exists (select 1 from {assignments} mine
				where mine.volunteer = {volunteer}.name
				and mine.deployment = %(deployment)s
				and mine.status in %(open)s)"""
		)
		# Nor the people already waiting for its send time.
		where.append(
			f"""not exists (select 1 from `tabVMMS Scheduled Ask` waiting
				where waiting.parent = %(deployment)s
				and waiting.parenttype = 'VMMS Deployment'
				and waiting.volunteer = {volunteer}.name)"""
		)

	if has_span:
		values["start"] = getdate(start_date)
		values["end"] = getdate(end_date)
		clash = f"""exists (select 1 from {assignments} other
			where other.volunteer = {volunteer}.name
			and other.status in %(on_deployment)s
			and other.start_date <= %(end)s
			and other.end_date >= %(start)s
			and other.deployment != %(deployment)s)"""
	else:
		clash = "0"

	if exclude_conflicts and has_span:
		where.append(f"not {clash}")

	desirable = tuple(required["desirable"])
	values["desirable"] = desirable or ("",)
	having = ""

	if max_workload is not None:
		values["max_workload"] = cint(max_workload)
		having = "having workload <= %(max_workload)s"

	rows = frappe.db.sql(
		f"""
		select
			{volunteer}.name as name,
			(select count(*) from {assignments} carrying
				where carrying.volunteer = {volunteer}.name
				and carrying.status in %(open)s) as workload,
			{clash} as clashing,
			(select count(distinct held.certification_type) from {certifications} held
				where held.volunteer = {volunteer}.name
				and held.certification_type in %(desirable)s
				and (held.expiry_date is null or held.expiry_date >= %(as_of)s)) as desirable_held,
			exists (select 1 from `tab{availability.SCHEDULE_DOCTYPE}` written
				where written.volunteer = {volunteer}.name) as has_schedule
		from {volunteer}
		{joins}
		where {" and ".join(where)} {scope}
		{having}
		""",
		values,
		as_dict=True,
	)

	# Availability, for the people who have said anything about it at all.
	scheduled = [row["name"] for row in rows if row["has_schedule"]] if has_span else []
	answers = availability.assess_many(scheduled, start_date, end_date) if scheduled else {}

	ranked = []

	for row in rows:
		free = answers.get(row["name"])
		state = 1 if not free else 0 if free["is_available"] else 2 if free["is_unavailable"] else 1

		if only_available and state == 2:
			continue

		ranked.append(
			(state, 1 if row["clashing"] else 0, -cint(row["desirable_held"]), cint(row["workload"]), row["name"])
		)

	ranked.sort()

	return [key[-1] for key in ranked]


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

	# A page is nearly always one county, so its place is asked once, not once
	# per row — the per-row path was half the cost of a search.
	paths = {node: adapter.get_full_path(node) for node in {row["home_geo_node"] for row in rows} if node}

	for row in rows:
		person = profiles.get(row["red_profile"]) or {}
		row["full_name"] = person.get("full_name")
		row["profile_photo"] = person.get("profile_photo")
		row["geo_path"] = paths.get(row["home_geo_node"])

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


def _bulk_conflicts(names: list[str], start_date, end_date, exclude_deployment: str | None = None) -> dict:
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
			# The deployment being topped up is not somebody's clash with itself.
			"deployment": ("!=", exclude_deployment or ""),
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


def _bulk_workload(names: list[str]) -> dict[str, int]:
	"""How many open assignments each of these volunteers already holds.

	One grouped query for the whole page, for the same reason every other read
	here is bulk: a count per volunteer is what makes a candidate screen slow at
	the size a national society runs at.

	**`get_all`, not `get_list`, on the same argument `_bulk_conflicts` makes.**
	Somebody's workload matters most when the rest of it is in a county this
	searcher cannot see, and a scoped read would report the person with four
	deployments in the next district as carrying nothing. What comes back is a
	number, never a list of work outside the caller's area.

	Open, not everything: placed, asked or accepted. A deployment somebody
	finished last year is not something they are carrying.
	"""
	if not names:
		return {}

	from frappe.query_builder.functions import Count

	from vmmsx.deployment.services import assignment

	table = frappe.qb.DocType(assignment.ASSIGNMENT_DOCTYPE)

	rows = (
		frappe.qb.from_(table)
		.select(table.volunteer, Count(table.name).as_("total"))
		.where(table.volunteer.isin(names) & table.status.isin(assignment.OPEN_STATUSES))
		.groupby(table.volunteer)
		.run(as_dict=True)
	)

	return {row["volunteer"]: row["total"] for row in rows}


# --- assessing one volunteer, from rows already read -----------------------


def _assess(
	volunteer_row: dict,
	held_rows: list[dict],
	required: dict,
	as_of,
	availability: dict | None = None,
	clash: list[dict] | None = None,
	workload: int = 0,
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
		"geo_path": volunteer_row["geo_path"]
		if "geo_path" in volunteer_row
		else (adapter.get_full_path(home) if home else None),
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
		# How much this person is already carrying, everywhere. A number rather
		# than a verdict: it ranks, and it filters only where `max_workload` was
		# given.
		"workload": workload,
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

	Workload sits *after* the desirable certifications and not before them: it is
	a tie-break for two people who fit equally well, which is what spreading the
	work fairly actually means, rather than a reason to send somebody less
	qualified.
	"""
	free = assessment["availability"]
	rank_of_availability = 0 if free["is_available"] else 2 if free["is_unavailable"] else 1

	return (
		rank_of_availability,
		1 if assessment["clash"]["is_clashing"] else 0,
		-len(assessment["desirable_certifications_held"]),
		assessment.get("workload", 0),
		assessment["volunteer"],
	)
