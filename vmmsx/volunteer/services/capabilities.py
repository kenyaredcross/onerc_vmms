# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What a volunteer can do *now* — seeded once from the application, owned here.

The line this module draws
--------------------------

An application is a **statement made on a day**. A volunteer is a **standing
relationship**. Some of what an applicant writes down is true of the day and
stays true of it forever; the rest is true of the person and stops being true
the moment the person changes. Those are different kinds of fact and they do
not live in the same place:

    lives on the VOLUNTEER          stays on the APPLICATION
    (current, editable)             (historical, shown as declared)
    ----------------------          ------------------------------
    skills                          motivation
    languages                       prior_experience
    availability                    the identification captured at intake
    citizenship, residency          (and the day's copy of everything left)
    serving branch

The test of which side a field belongs on is one question: *if this changed
tomorrow, would the application have been wrong?* A volunteer who learns to
drive does not make last year's application false, so skills are current facts
and belong on the volunteer. Why somebody applied is a fact about the applying,
and editing it later would be rewriting history rather than recording a change,
so motivation stays where it was said.

**Nothing is read live from the application.** That was the alternative and it
is wrong for exactly the reason above: it would make a volunteer's current
skills unchangeable without editing a settled application, and it would make
correcting a typo on an application silently change what somebody is qualified
for today. The two are meant to diverge. `seed()` below copies once and never
looks back, and `volunteer/tests/test_coordinator_view.py` asserts the
divergence rather than trusting it.

The two questions a Geo Node can answer, and why only one is here
-----------------------------------------------------------------

**Serving Branch** is where somebody works for the society. It is
`VMMS Volunteer.home_geo_node` — a historical fieldname for the ACC-02 anchor —
and it is the volunteer's, because it is a fact about their volunteering: a
transfer moves it, geo scoping filters on it, and an approval routes from it.

**Home Area** is where somebody lives. It is a fact about the *person*, not
about their volunteering, and core already owns it as `Red Profile.home_geo_node`
— written once at registration by `registration/services/intake.py::place()`.
So it is **not copied here**. `placement()` below reads it through
`identity.py`, at the moment somebody looks, exactly as the name and phone
number beside it are read. Storing a second copy on the volunteer would be the
same mistake as storing a second copy of somebody's name, and it would go wrong
in the same way: two answers, and no way to tell which is current.

Citizenship and residency are neither. Core's spine does not hold them, and
they are asked because volunteering asks them, so they are the volunteer's and
are seeded here.

Seeding is fill-the-blanks, not overwrite
-----------------------------------------

`seed()` writes a field only where the volunteer's own is empty. It runs from
`application.accept()`, once per acceptance, and the rule matters for the
second acceptance: somebody who volunteered, exited, and applied again years
later is the *same person*, and their current skills are the ones the society
has been maintaining, not the ones on a form they filled in last week. It is
the same doctrine `volunteer.ensure()` already applies to placement, stated
once more here because it now governs six more fields.

That also makes `seed()` idempotent in the strong sense: the second call
observes the work is done and returns the same answer.

Queryability, which is the point of the structure
-------------------------------------------------

These are Table MultiSelects of society-configured vocabularies rather than
text, so `search()` below can answer "who can do this, and is free then". It
answers **through** `frappe.get_list`, never `frappe.get_all`: the first applies
core's geo scoping as a permission query condition and the second does not. A
capability filter narrows what a coordinator already had authority to see; it
never widens it. There is a test whose whole job is to prove an out-of-scope
volunteer with the right skill does not come back.

No skill, language, availability slot, level or role name appears in this file.
Which vocabularies a society keeps is its own business, and this module only
knows the field they hang off.
"""

import frappe

VOLUNTEER_DOCTYPE = "VMMS Volunteer"

# The ACC-02 anchor on VMMS Volunteer, which is the volunteer's Serving Branch.
# Named once here so this module never spells the historical fieldname twice.
SERVING_BRANCH_FIELD = "home_geo_node"

# How many rows a name search may gather before it is handed to the scoped read.
# It is a candidate set, not an answer, so the ceiling only has to be larger
# than any register a coordinator would sensibly search by typing part of a name.
_NAME_SEARCH_CEILING = 500

# The volunteer-owned multi-selects, paired with the child field each row keys
# on. One tuple, used by seeding, by the DTO and by search, so the three cannot
# drift into disagreeing about what a capability is.
#
# `(field on the record, link field on the child row, vocabulary doctype, the
# vocabulary's display field)`.
SELECTORS = (
	("skills", "skill", "VMMS Skill", "skill_name"),
	("languages", "language", "Language", "language_name"),
	("availability", "availability_slot", "VMMS Availability Slot", "slot_name"),
)

# The scalar facts about the person that the volunteer owns once accepted. Same
# spelling on both records, deliberately: a rename on one side should break the
# seed loudly rather than quietly copy nothing.
SEEDED_SCALARS = (
	"country_of_citizenship",
	"residency_type",
	"country_of_residence",
	"residence_address",
)

RESIDENCY_LOCAL = "Local"
RESIDENCY_ABROAD = "Abroad"

# What an Abroad answer uses, and what a Local one must not keep lying around.
_ABROAD_ONLY = ("country_of_residence", "residence_address")


# --- controller-facing tidying ---------------------------------------------


def reconcile_residency(volunteer) -> None:
	"""Clear the half of the residency answer this volunteer's toggle does not use.

	A Local volunteer has no business keeping a stale address abroad around.
	Without this, switching the field back in the desk and saving would leave
	two contradictory answers on one record, and a coordinator reading the form
	would have no way to know which one the society meant.

	**Deliberately not symmetrical with the application's version.** There, an
	Abroad answer also clears `home_geo_node`, because on an application that
	field is ordinary optional data. Here `home_geo_node` is the Serving Branch
	and the ACC-02 anchor: somebody living abroad still serves with a branch,
	and clearing it would make the record unsaveable.
	"""
	if volunteer.get("residency_type") == RESIDENCY_ABROAD:
		return

	for fieldname in _ABROAD_ONLY:
		volunteer.set(fieldname, None)


# --- seeding, at acceptance ------------------------------------------------


def seed(volunteer, application) -> dict:
	"""Copy the application's living data onto the volunteer. Idempotent.

	Called from `application.accept()`, after the volunteer exists and before
	the affiliation index is refreshed from it. Returns the fields it actually
	wrote, so the acceptance DTO can say what happened rather than implying it.

	Only blanks are filled; see the module docstring for why a second
	application must not overwrite what a society has been maintaining.

	The Serving Branch is not seeded here. `volunteer.ensure()` already sets it
	when it creates the record, and it is the one field on this list that must
	exist before the record can be saved at all — so seeding it afterwards would
	be writing a value that was necessarily already there.

	**The save bypasses permissions, and this is the justification.** It is the
	same one `volunteer.ensure()` states and for the same reason: this path runs
	as whichever approver made the decision, and an approver holds no write
	permission on the volunteer register and has no business holding one. The
	check that mattered happened in `engine.decide`, against the specific person
	this document routed to. Nothing a caller supplied reaches a field here
	either: every value is copied off an application the engine has settled.
	"""
	seeded = {}

	for fieldname in SEEDED_SCALARS:
		value = application.get(fieldname)

		if value and not volunteer.get(fieldname):
			volunteer.set(fieldname, value)
			seeded[fieldname] = value

	for fieldname, link_field, _doctype, _label_field in SELECTORS:
		if volunteer.get(fieldname):
			continue

		values = [row.get(link_field) for row in application.get(fieldname) or [] if row.get(link_field)]

		if not values:
			continue

		volunteer.set(fieldname, [{link_field: value} for value in values])
		seeded[fieldname] = values

	if seeded:
		volunteer.save(ignore_permissions=True)

	return seeded


# --- reading ---------------------------------------------------------------


def selector_dto(rows, link_field: str, doctype: str, name_field: str) -> list[dict]:
	"""A Table MultiSelect's rows, resolved to `{key, label}` pairs.

	Never the raw child rows: a coordinator reading `skills` on the wire should
	see the society's own word for a skill, not a Link value, and a DTO handing
	back child documents would leak `parent`, `parentfield` and `idx` to every
	caller.

	The label is read live rather than copied, so a society renaming a skill
	renames it on every screen at once and no history is rewritten.
	"""
	keys = [row.get(link_field) for row in rows or [] if row.get(link_field)]

	if not keys:
		return []

	labels = dict(
		frappe.get_all(doctype, filters={"name": ("in", keys)}, fields=["name", name_field], as_list=True)
	)

	return [{"key": key, "label": labels.get(key) or key} for key in keys]


def current(volunteer) -> dict:
	"""What this volunteer can do now, as an explicit dict. Built field by field.

	The volunteer's own copy, not the application's. That is the whole
	distinction this module exists to hold, so there is **no fallback** to the
	application when a field is empty: a volunteer with no skills recorded has
	no skills recorded, and quietly showing the ones they claimed years ago in
	that slot would be presenting a claim as a current fact.
	"""
	return {
		fieldname: selector_dto(volunteer.get(fieldname), link_field, doctype, label_field)
		for fieldname, link_field, doctype, label_field in SELECTORS
	}


def placement(volunteer) -> dict:
	"""Where this volunteer serves and where they live, under names that differ.

	Two Geo Nodes answering two different questions is exactly the confusion
	ACC-02 invites, so both come back with their full path resolved through
	core's adapter and neither is called simply `geo_node`.

	**Serving Branch is stored; Home Area is read.** The first is the
	volunteer's anchor. The second is `Red Profile.home_geo_node`, core's own
	field, read here through `identity.py` at the moment of asking and copied
	nowhere — the same treatment the name and phone number get, for the same
	reason. A volunteer who moves house has their Red Profile corrected once and
	every screen in the society is right on next open.
	"""
	from onerc_core.geo.services import adapter

	from vmmsx.volunteer.services import identity

	abroad = volunteer.get("residency_type") == RESIDENCY_ABROAD
	branch = volunteer.get(SERVING_BRANCH_FIELD)
	home = identity.read(volunteer, ("home_geo_node",)).get("home_geo_node")

	return {
		"geo_node": branch,
		"geo_path": adapter.get_full_path(branch) if branch else None,
		"home_geo_node": home,
		"home_geo_path": adapter.get_full_path(home) if home else None,
		"country_of_citizenship": volunteer.country_of_citizenship,
		"residency_type": volunteer.residency_type,
		# Only ever populated on the side of the toggle that uses them. The
		# controller clears the other side on every save, so this is a statement
		# about the record rather than a filter applied on the way out.
		"country_of_residence": volunteer.country_of_residence if abroad else None,
		"residence_address": volunteer.residence_address if abroad else None,
	}


# --- searching, within scope ----------------------------------------------


def search(
	skills: list | None = None,
	languages: list | None = None,
	availability: list | None = None,
	geo_node: str | None = None,
	status: str | None = None,
	search: str | None = None,
	limit: int = 100,
	offset: int = 0,
) -> list[str]:
	"""Volunteers matching these capabilities, **within the caller's geo scope**.

	Each argument is a list of vocabulary keys and each narrows the result: a
	volunteer must hold at least one of the skills asked for *and* at least one
	of the languages *and* be free in at least one of the slots. Any-of within a
	vocabulary and all-of across them is what a coordinator staffing something
	actually means by "a first aider who speaks either of these and can do
	weekends".

	**The scope is not this function's to apply, and that is the design.** The
	final read is `frappe.get_list`, which runs core's permission query
	condition for `VMMS Volunteer`; `frappe.get_all` would skip it and is not
	used here. So a capability filter can only ever narrow what the caller could
	already see. If a society has not configured its volunteer scope role, core
	fails closed and this returns nothing, which is the correct answer rather
	than a bug.

	`geo_node` narrows *further*, to one subtree, and is likewise not a way in:
	naming a node the caller has no authority over returns nothing, because the
	scope condition still applies underneath it.

	`search` is the question a coordinator asks when they know who they mean and
	not what the record is called: a person's name, or the volunteer's docname.
	It resolves names through **core's Red Profile**, because that is where a
	person's name lives and this app keeps none of its own — the satellite rule
	the whole Member and Volunteer design is built on. Like every other argument
	here it can only remove people from an already-scoped list: the profiles it
	matches become a `name in (...)` filter on the same `get_list`, so a
	coordinator who types a name they may not see gets nothing back rather than
	a record.

	`offset` pages through that same scoped result. It narrows like everything
	else here and cannot reach past the scope: it is applied by the database to
	rows core's permission condition already admitted, so skipping forward
	skips within what the caller could see anyway. `count()` below answers how
	many there are to page through.

	This is the queryable surface the deployment matching service was waiting
	for. It is deliberately **not** wired into matching here: matching decides
	things about a deployment's requirements that are not this module's to
	decide, and un-stubbing it is its own piece of work.
	"""
	filters = _search_filters(
		skills=skills,
		languages=languages,
		availability=availability,
		geo_node=geo_node,
		status=status,
		search=search,
	)

	if filters is None:
		return []

	return frappe.get_list(
		VOLUNTEER_DOCTYPE,
		filters=filters,
		pluck="name",
		order_by="modified desc",
		limit_start=offset,
		limit_page_length=limit,
	)


def count(
	skills: list | None = None,
	languages: list | None = None,
	availability: list | None = None,
	geo_node: str | None = None,
	status: str | None = None,
	search: str | None = None,
) -> int:
	"""How many volunteers `search()` would match, ignoring its page.

	**The same filters, built by the same function**, which is the whole reason
	this is not a second query written out again: a count derived from different
	filters than the page it labels is a pager that lies, and it would lie
	silently. `_search_filters` is the one place the question is composed.

	Still `frappe.get_list`, so the count is of what this caller may see rather
	than of the register. A society that has configured no scope role counts
	nothing, matching what `search()` returns.
	"""
	filters = _search_filters(
		skills=skills,
		languages=languages,
		availability=availability,
		geo_node=geo_node,
		status=status,
		search=search,
	)

	if filters is None:
		return 0

	# `limit_page_length=0` is "no limit" to Frappe. The names are counted rather
	# than aggregated in SQL because an aggregate through `get_list` is not
	# reliably given the permission condition, and a count that quietly ignored
	# scope would be worse than a slightly heavier query at society scale.
	return len(
		frappe.get_list(VOLUNTEER_DOCTYPE, filters=filters, pluck="name", limit_page_length=0)
	)


def _search_filters(
	skills: list | None = None,
	languages: list | None = None,
	availability: list | None = None,
	geo_node: str | None = None,
	status: str | None = None,
	search: str | None = None,
) -> dict | None:
	"""The filters `search()` and `count()` both stand on, or None for "nothing".

	None is not an empty dict: an empty dict means "no narrowing, return the
	caller's whole scope", and None means the criteria are provably unsatisfiable
	— an intersection already came out empty, so no later filter could widen it.
	Collapsing the two would turn a search that matches nobody into a search that
	returns everybody, which is the worst direction for this to fail in.
	"""
	from onerc_core.geo.services import adapter

	asked = {"skills": skills, "languages": languages, "availability": availability}
	candidates = None

	for fieldname, link_field, _doctype, _label_field in SELECTORS:
		wanted = [value for value in (asked.get(fieldname) or []) if value]

		if not wanted:
			continue

		holders = _holders_of(fieldname, link_field, wanted)
		candidates = holders if candidates is None else candidates & holders

		if not candidates:
			# Nothing satisfies the filters so far, and no later filter can
			# widen an intersection. Stop before asking the database again.
			return None

	if search and search.strip():
		named = _named(search.strip())

		if not named:
			return None

		candidates = named if candidates is None else candidates & named

		if not candidates:
			return None

	filters = {}

	if status:
		filters["status"] = status

	if candidates is not None:
		filters["name"] = ("in", sorted(candidates))

	if geo_node:
		# Through core's adapter, never a query against the geo tables: which
		# nodes sit beneath one is core's question and this app has no second
		# answer to it.
		filters[SERVING_BRANCH_FIELD] = ("in", [geo_node, *adapter.get_descendants(geo_node)])

	return filters


def _named(term: str) -> set[str]:
	"""Volunteers whose person, or whose own docname, matches what was typed.

	**The name comes from core's `Red Profile`, never from here.** A volunteer
	record owns no identity fields at all — no name, no email, not even a
	`fetch_from` — which is the satellite rule the Member and Volunteer modules
	are both built on. So a name search is two reads: find the profiles, then
	find the volunteers pointing at them.

	The docname is matched as well, because a coordinator who *does* remember
	`VOL-00012` should not have to type a name instead. Both are candidate sets
	handed back to `search()`, which turns them into a filter on a **scoped**
	`get_list` — reading profiles unscoped here discloses nothing, because no
	record reaches a caller from this function.
	"""
	like = f"%{term}%"

	profiles = frappe.get_all(
		"Red Profile",
		or_filters={"full_name": ("like", like), "email": ("like", like)},
		pluck="name",
		limit_page_length=_NAME_SEARCH_CEILING,
	)

	matched = set(
		frappe.get_all(
			VOLUNTEER_DOCTYPE,
			filters={"red_profile": ("in", profiles)},
			pluck="name",
			limit_page_length=_NAME_SEARCH_CEILING,
		)
		if profiles
		else []
	)

	matched.update(
		frappe.get_all(
			VOLUNTEER_DOCTYPE,
			filters={"name": ("like", like)},
			pluck="name",
			limit_page_length=_NAME_SEARCH_CEILING,
		)
	)

	return matched


def _holders_of(fieldname: str, link_field: str, values: list[str]) -> set[str]:
	"""Volunteers holding any of these vocabulary keys in this multi-select.

	Read off the child table, which is the only way to ask it, and filtered by
	**both** `parenttype` and `parentfield`. A Table MultiSelect is one physical
	table per child doctype, and the same three selectors hang off
	`VMMS Volunteer Application` as well — so a query filtered only by the link
	value would return applicants as though they were volunteers.

	This is a candidate list and not an answer: it is handed back to `search()`,
	which turns it into a `name in (...)` filter on a **scoped** `get_list`. No
	record reaches a caller from here, which is why reading it unscoped is not a
	way around the scope.
	"""
	child_doctype = frappe.get_meta(VOLUNTEER_DOCTYPE).get_field(fieldname).options

	return set(
		frappe.get_all(
			child_doctype,
			filters={
				"parenttype": VOLUNTEER_DOCTYPE,
				"parentfield": fieldname,
				link_field: ("in", values),
			},
			pluck="parent",
		)
	)
