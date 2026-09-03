# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Deployment API — explicit DTOs, session-derived scope, no second door.

Every endpoint names its arguments, checks permission through Frappe (which
brings core's geo scoping with it), and returns a dict this module builds field
by field. None of them returns a Document or a raw query result.

**Deciding a routed deployment request or branch transfer is deliberately not
here.** Both are acted on through `vmmsx/api/approvals.py`, the generic engine
endpoint, because the person-gate lives there and a second door into the same
decision would be a second place to get it wrong.

**`find_candidates` takes no user and no scope.** A caller says what they are
looking for and where the work is; who they are is the session, and where they
may look is core's answer about that session. There is no argument by which a
caller could widen their own area, which is why there is no check here that
could get it wrong. See the scope guarantee at the top of
`deployment/services/matching.py`.
"""

import frappe
from onerc_core.access.services.enforcement import guard

from vmmsx.deployment.services import deployment as deployment_service
from vmmsx.deployment.services import invitation, matching, participation, terms, tor_document
from vmmsx.deployment.services import project as project_service
from vmmsx.deployment.services import request as request_service
from vmmsx.deployment.services import transfer as transfer_service
from vmmsx.setup.project_fields import FUNDING_STATUSES as _FUNDING_STATUSES

DEPLOYMENT_DOCTYPE = "VMMS Deployment"
# One person's place on a deployment. Named here as well as on the service
# because half the endpoints below act on one directly.
ASSIGNMENT_DOCTYPE = "VMMS Deployment Assignment"
REQUEST_DOCTYPE = "VMMS Deployment Request"
TRANSFER_DOCTYPE = "VMMS Branch Transfer"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"
# ERPNext's own, adopted as the canonical programme of work. Named here rather
# than typed at each call site so the day this app is pointed at something else
# there is one line to change. See `deployment/services/project.py`.
PROJECT_DOCTYPE = "Project"
TERMS_DOCTYPE = "VMMS Terms of Reference"
# Core's, named here only so `deployment_map` can ask whether a deployment's
# anchor still exists. Everything else geo goes through the adapter.
DEPLOYMENT_GEO_DOCTYPE = "Geo Node"


# --- matching -------------------------------------------------------------


@frappe.whitelist()
def find_candidates(
	terms_of_reference: str,
	geo_node: str,
	as_of: str | None = None,
	limit: int | None = None,
	offset: int = 0,
	search: str | None = None,
	skills: list | None = None,
	languages: list | None = None,
	start_date: str | None = None,
	end_date: str | None = None,
	only_available: bool | int | str = False,
	exclude_conflicts: bool | int | str = False,
	max_workload: int | None = None,
) -> dict:
	"""Volunteers who fit this need, within the caller's own area.

	The scope is derived from the session on every call and cannot be supplied,
	so an out-of-scope volunteer is not returnable by any argument. `as_of` moves
	the certification questions to another date, which is what a caller planning
	a deployment for next month actually wants to ask.

	`search` (a name or a docname) and `skills` narrow the page before it is
	assessed, and `offset` pages through it — see `matching.candidates()` for why
	this is not merely a display filter.

	`start_date` and `end_date` turn on the availability and clash answers, which
	rank rather than exclude; `only_available` and `exclude_conflicts` turn each
	into a filter for a caller who has decided they want one. `max_workload` is
	the third of the same kind and drops the people already carrying more open
	assignments than that.
	"""
	return matching.candidates(
		terms_of_reference,
		geo_node,
		as_of=as_of,
		limit=limit,
		offset=offset,
		search=search,
		skills=skills,
		languages=languages,
		start_date=start_date,
		end_date=end_date,
		only_available=_flag(only_available),
		exclude_conflicts=_flag(exclude_conflicts),
		max_workload=max_workload,
	)


@frappe.whitelist()
def find_candidates_for_request(name: str, limit: int | None = None) -> dict:
	"""The same question, asked of a request that already carries the need.

	The request is loaded through the permission layer first: a caller who may
	not see the request may not use it to search either.
	"""
	request = _readable(REQUEST_DOCTYPE, name)

	return matching.candidates_for(request, limit=limit)


# --- deployments ----------------------------------------------------------


@frappe.whitelist()
def get_deployment(name: str) -> dict:
	"""One deployment: its terms, its period, its place and its roster."""
	return deployment_service.deployment_dto(_readable(DEPLOYMENT_DOCTYPE, name))


@frappe.whitelist()
def deployment_map(status: str | None = None) -> dict:
	"""Where this coordinator's people are, by area, with a point where there is one.

	**The map and the ranked list are one answer, not two.** Every area comes back
	whether or not it can be plotted, with `latitude`/`longitude` present only
	where the geo tree carries them. A screen draws pins for the ones it can and
	says plainly how many it could not — which is the honest thing, because a
	tree is filled in from the top down over months and a map that silently
	omitted the unplotted areas would under-report exactly where the gaps are.

	**Scoped by the deployment listing, not by the geo tree.** The nodes named
	here are the anchors of deployments this caller may already read, so nothing
	is disclosed that `branch_deployments` would not have disclosed anyway. The
	geo tree itself is not scopeable — it is the thing scoping is expressed *in*.

	Counts are of people actually on each deployment, which is Assigned plus
	Accepted. A question nobody has answered is not somebody who is there.
	"""
	from onerc_core.geo.services import adapter

	from vmmsx.deployment.services import assignment as assignment_service

	filters = {}

	if status in _DEPLOYMENT_STATUSES:
		filters["status"] = status
	elif status:
		# An unknown status answers with nothing rather than with everything,
		# which is the direction a filter should fail in.
		return {"areas": [], "deployed": 0, "unplotted": 0}

	rows = frappe.get_list(
		DEPLOYMENT_DOCTYPE,
		filters=filters,
		fields=["name", "geo_node", "status"],
		limit_page_length=0,
	)

	running = [row for row in rows if row["status"] in deployment_service.OPEN_STATUSES]
	tallies = assignment_service.counts_for_many([row["name"] for row in running])
	points = adapter.get_points(sorted({row["geo_node"] for row in running if row["geo_node"]}))

	areas: dict[str, dict] = {}

	for row in running:
		node = row["geo_node"]

		# A deployment whose anchor has since been deleted. A cascade should
		# prevent it and a partially-restored backup will not, and the dashboard
		# is the wrong place to discover it: `get_full_path` throws on a node that
		# is not there, which would take down the whole panel over one bad row.
		# Skipped, exactly as `participation.history_of` skips a record that
		# outlived its parent.
		if not node or not frappe.db.exists(DEPLOYMENT_GEO_DOCTYPE, node):
			continue

		area = areas.setdefault(
			node,
			{
				"geo_node": node,
				"geo_path": adapter.get_full_path(node),
				"deployments": 0,
				"people": 0,
				"waiting": 0,
				**(points.get(node) or {}),
			},
		)

		tally = tallies.get(row["name"], {})
		area["deployments"] += 1
		area["people"] += tally.get("on_deployment", 0)
		area["waiting"] += tally.get("Pending", 0)

	ranked = sorted(areas.values(), key=lambda area: (-area["people"], area["geo_path"] or ""))

	return {
		"areas": ranked,
		"deployed": sum(area["people"] for area in ranked),
		# How many areas the map cannot draw, so the screen can say so rather
		# than quietly showing fewer pins than there are places.
		"unplotted": sum(1 for area in ranked if "latitude" not in area),
	}


@frappe.whitelist()
def get_deployment_feed(name: str, limit: int | None = None) -> dict:
	"""What has happened on this deployment, newest first.

	Two sources merged at read time — the deployment's own updates and the task
	reports written against tasks linked to it — because a volunteer submitting a
	task report is reporting on the deployment, and copying the report here would
	make two records of one thing that immediately start drifting.

	Read permission on the deployment decides, which brings core's geo scoping
	with it. `feed.py` decides nothing about who may look; answering that twice
	is how two answers come to disagree.
	"""
	_readable(DEPLOYMENT_DOCTYPE, name)

	from vmmsx.deployment.services import feed

	return feed.of(name, limit=limit)


@frappe.whitelist()
def post_deployment_update(
	name: str,
	note: str,
	entry_type: str = "update",
	proof: str | None = None,
) -> dict:
	"""Write one entry to a deployment's feed.

	**Write permission, not read.** A feed anybody who could open the deployment
	could write to would not be a record of anything. The author and the time are
	stamped from the session inside the service and are not arguments here, so an
	entry cannot be back-dated or attributed to somebody else.
	"""
	deployment = _readable(DEPLOYMENT_DOCTYPE, name)
	deployment.check_permission("write")

	from vmmsx.deployment.services import feed

	return feed.post(deployment, note, entry_type=entry_type, proof=proof)


@frappe.whitelist()
def set_deployment_status(name: str, status: str, reason: str | None = None) -> dict:
	"""Move a deployment through its lifecycle. Idempotent.

	Write permission is checked before the transition, so a caller who may read a
	deployment cannot end one.
	"""
	deployment = _readable(DEPLOYMENT_DOCTYPE, name)
	deployment.check_permission("write")

	return deployment_service.set_status(deployment, status, reason)


@frappe.whitelist()
def add_participant(name: str, volunteer: str, joined_on: str | None = None) -> dict:
	"""Place a volunteer on a deployment. Idempotent.

	This is the act that makes a deployment time log possible for that person, so
	it is gated on write permission on the deployment: placing somebody is
	changing what the society says happened.
	"""
	deployment = _readable(DEPLOYMENT_DOCTYPE, name)
	deployment.check_permission("write")

	participation.add(deployment, volunteer, joined_on=joined_on)

	return deployment_service.deployment_dto(deployment)


@frappe.whitelist()
def invite_volunteer(
	name: str,
	volunteer: str,
	joined_on: str | None = None,
	answer_by: str | None = None,
	assignment_title: str | None = None,
	assignment_description: str | None = None,
	supervisor: str | None = None,
) -> dict:
	"""Ask a volunteer to join a deployment, and notify them. Idempotent.

	Gated on write permission on the deployment, the same as `add_participant`,
	because it raises the same kind of record. The difference between the two is
	what the coordinator is saying: `add_participant` records that somebody is
	going, this one asks whether they will.
	"""
	deployment = _readable(DEPLOYMENT_DOCTYPE, name)
	deployment.check_permission("write")

	return invitation.invite(
		deployment,
		volunteer,
		joined_on=joined_on,
		answer_by=answer_by,
		assignment_title=assignment_title,
		assignment_description=assignment_description,
		supervisor=supervisor,
	)


@frappe.whitelist()
def assign_volunteers(
	name: str,
	volunteers: list | str,
	ask: bool | int | str = True,
	notes: str | None = None,
) -> dict:
	"""Raise assignments for several volunteers at once. The bulk act.

	**One call, and an honest report.** Some of the people picked will fail —
	already assigned, deployment full, terms retired since — and the answer says
	which and why, per person, rather than refusing the batch or silently
	dropping them. `assignment.deploy` wraps each insert in its own savepoint so
	one refusal cannot roll back the rest.

	`ask` is the fork between this app's two verbs, and it is a fork rather than
	a merge on purpose: on, and each person is *asked* and can answer; off, and
	each is *placed* by a coordinator who has already arranged it. Collapsing
	them would make "who was asked" and "who is going" one question.

	Gated on write permission on the deployment, the same as the two singular
	endpoints beside it. The list is a list of volunteer names; anything that is
	not one is refused by the service, per row, with a reason.
	"""
	deployment = _readable(DEPLOYMENT_DOCTYPE, name)
	deployment.check_permission("write")

	from vmmsx.deployment.services import assignment as assignment_service

	return assignment_service.deploy(
		deployment,
		_names(volunteers),
		status=(assignment_service.STATUS_PENDING if _flag(ask) else assignment_service.STATUS_ASSIGNED),
		notes=notes,
	)


def _status_rows(names: list[str]) -> list[dict]:
	"""`status_dto` for a list of deployments, with one query for all their counts.

	The roster is a register of documents now, so a deployment's headcount is a
	query rather than `len()` on a child table. Every listing in this module goes
	through here so that a page of a hundred deployments costs one grouped count
	rather than a hundred, which is the difference between a register that opens
	and one that times out at the size a national society runs at.

	Order is the caller's, preserved: these lists are already sorted by the query
	that produced them, and re-sorting here would silently override it.
	"""
	if not names:
		return []

	from vmmsx.deployment.services import assignment as assignment_service

	tallies = assignment_service.counts_for_many(names)

	return [
		deployment_service.status_dto(frappe.get_doc(DEPLOYMENT_DOCTYPE, name), counts=tallies.get(name))
		for name in names
	]


def _names(value: list | str) -> list[str]:
	"""A list of docnames as it arrives over HTTP.

	Frappe hands a whitelisted method either a real list or the JSON it was sent
	as, depending on how the caller framed the request. Parsed once here rather
	than at each call site, and filtered to non-empty strings so a trailing null
	in the payload does not become a row in the failure report.
	"""
	if isinstance(value, str):
		value = frappe.parse_json(value or "[]")

	if not isinstance(value, list):
		return []

	return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]


@frappe.whitelist()
def set_assignment_role(name: str, role: str) -> dict:
	"""Name somebody the deployment's leader, or return them to the ranks.

	Gated on write permission on the **assignment**, which core scopes on its own
	`geo_node`: naming a leader is a decision about the work, not about the
	person, so it belongs to whoever may write the deployment's own area.
	`assignment.set_role` refuses a role outside the two, and the controller
	refuses a second leader.
	"""
	from vmmsx.deployment.services import assignment as assignment_service

	document = _readable(assignment_service.ASSIGNMENT_DOCTYPE, name)
	document.check_permission("write")

	return assignment_service.set_role(document, role)


@frappe.whitelist()
def record_assignment_attendance(
	name: str, outcome: str, hours: float | None = None, notes: str | None = None
) -> dict:
	"""Say what happened on the day: all of it, some of it, or none of it.

	The coordinator's statement, and deliberately not the volunteer's. `hours` is
	the figure a coordinator verified; a volunteer's own time log is a separate
	claim on a separate record, and a register that merged the two would have no
	way to show them disagreeing — which is the only reason anybody verifies
	anything.

	Gated on write permission on the assignment, which brings core's geo scoping
	with it.
	"""
	doc = _readable(ASSIGNMENT_DOCTYPE, name)
	doc.check_permission("write")

	from vmmsx.deployment.services import assignment as assignment_service

	return assignment_service.record_attendance(doc, outcome, hours=hours, notes=notes)


@frappe.whitelist()
def replace_assignment(name: str, volunteer: str, reason: str, authorised_by: str | None = None) -> dict:
	"""Swap somebody out and somebody in, keeping both records.

	The original is never overwritten: it moves to Replaced and points at the
	assignment that took over, which points back. Editing the volunteer instead
	would erase the fact that anybody had ever been asked, and with it any way to
	tell a replacement from a typo.

	A reason is required. Both people are told, separately, because being taken
	off a deployment and being asked onto one at short notice are different
	pieces of news.
	"""
	doc = _readable(ASSIGNMENT_DOCTYPE, name)
	doc.check_permission("write")

	from vmmsx.deployment.services import assignment as assignment_service

	return assignment_service.replace(doc, volunteer, reason, authorised_by=authorised_by)


@frappe.whitelist()
def record_assignment_readiness(name: str, event: str) -> dict:
	"""Stamp one of the four moments an assignment has: briefed, safe, in, out.

	One endpoint rather than four, because they are one act — a coordinator (or a
	gate marshal) recording that something happened at a time — and four
	near-identical endpoints would be four places to forget the permission check.
	The event is looked up rather than branched on, so adding a fifth moment is a
	row in the table below.

	**None of them gates anything.** Somebody who never acknowledged the safety
	brief is not thereby refused a check-in: refusing people at the gate on a
	field nobody filled in is how a record-keeping gap becomes an operational
	failure. Whether an unbriefed person deploys is a coordinator's decision.
	"""
	from vmmsx.deployment.services import assignment as assignment_service

	events = {
		"briefed": assignment_service.mark_briefed,
		"safety": assignment_service.acknowledge_safety,
		"check_in": assignment_service.check_in,
		"check_out": assignment_service.check_out,
	}

	if event not in events:
		frappe.throw(
			frappe._("{0} is not something recorded against an assignment. Expected one of: {1}.").format(
				frappe.bold(event), ", ".join(events)
			),
			frappe.ValidationError,
			title=frappe._("Unknown Event"),
		)

	doc = _readable(ASSIGNMENT_DOCTYPE, name)
	doc.check_permission("write")

	return events[event](doc)


@frappe.whitelist()
def withdraw_assignment(name: str, reason: str | None = None) -> dict:
	"""Take an assignment back. The coordinator's own act.

	Not a deletion, and the service says why: the person was asked, or was
	placed, and that happened. Somebody who served part of a deployment and went
	home is recorded with `left_on` instead, because withdrawing them would make
	the time they actually served unfilable.
	"""
	from vmmsx.deployment.services import assignment as assignment_service

	document = _readable(assignment_service.ASSIGNMENT_DOCTYPE, name)
	document.check_permission("write")

	return assignment_service.withdraw(document, reason)


@frappe.whitelist()
def my_invitations() -> dict | None:
	"""The caller's own deployment invitations, waiting and answered.

	Possessive, like `my_deployments` beside it and for the same reason: a
	volunteer holds no Geo Assignment, so every coordinator endpoint fails closed
	for them, and their own invitations are the last thing they should have to
	ask permission to see. There is no argument by which a caller could name
	anybody else.

	None for somebody who is not a volunteer, matching `my_volunteer`.
	"""
	volunteer = _my_volunteer()

	if not volunteer:
		return None

	return {
		"volunteer": volunteer,
		"waiting": invitation.pending_for(volunteer),
		"answered": invitation.answered_for(volunteer),
	}


@frappe.whitelist()
def respond_to_assignment(assignment: str, accept: bool | int | str, note: str | None = None) -> dict:
	"""Accept or decline one of the caller's own assignments.

	**Accepting is accepting the terms of reference**, which is why there is no
	separate contract in this app and why `VMMS Terms of Reference` is
	submittable: the assignment records the exact submitted document the person
	was shown, and an amendment afterwards cannot reach back and change what they
	agreed to.

	This one names a record, which the possessive endpoints above never do, so
	the check that would otherwise be missing is written out: the assignment being
	answered has to belong to the caller's own volunteer record. That is
	**ownership**, not geo scope, and it is the same distinction
	`participation.py` draws. A volunteer has no scope, so a permission check
	here would refuse everybody; an ownership check refuses everybody but the one
	person entitled to answer.

	The assignment is loaded without a read check for exactly that reason. What
	comes back is `assignment.dto`, built field by field, so answering is not a
	way to be handed the roster of everybody else who was asked.
	"""
	volunteer = _my_volunteer()

	if not volunteer:
		frappe.throw(
			frappe._("You do not have a volunteer record, so there is nothing to answer."),
			frappe.PermissionError,
		)

	from vmmsx.deployment.services import assignment as assignment_service

	document = frappe.get_doc(assignment_service.ASSIGNMENT_DOCTYPE, assignment)

	if document.volunteer != volunteer:
		# The same answer a volunteer gets for an assignment that does not exist.
		# Distinguishing the two would let somebody probe for assignment names.
		frappe.throw(
			frappe._("That is not your assignment to answer."),
			frappe.PermissionError,
		)

	return assignment_service.respond(document, accepted=_flag(accept), note=note)


@frappe.whitelist()
def get_my_assignment(assignment: str) -> dict:
	"""One of the caller's own assignments, with the mission they are agreeing to.

	The volunteer's read before they answer. It carries the whole terms of
	reference — background, objectives, itinerary, responsibilities — because
	accepting is accepting that document and somebody should not have to agree to
	a title. Ownership decides, exactly as it does in `respond_to_assignment`.
	"""
	volunteer = _my_volunteer()

	if not volunteer:
		frappe.throw(frappe._("You do not have a volunteer record."), frappe.PermissionError)

	from vmmsx.deployment.services import assignment as assignment_service

	document = frappe.get_doc(assignment_service.ASSIGNMENT_DOCTYPE, assignment)

	if document.volunteer != volunteer:
		frappe.throw(frappe._("That is not your assignment."), frappe.PermissionError)

	deployment = frappe.get_doc(DEPLOYMENT_DOCTYPE, document.deployment)

	return {
		"assignment": assignment_service.dto(document),
		# The mission itself, read through the terms the assignment names rather
		# than the ones the deployment currently points at. Those are the same
		# today and need not be tomorrow, and what a volunteer is agreeing to is
		# the document they were sent.
		"terms": terms.mission_dto(document.terms_of_reference),
		"deployment": {
			"name": deployment.name,
			"status": deployment.status,
			"start_date": deployment.start_date,
			"end_date": deployment.end_date,
			"geo_node": deployment.geo_node,
			"notes": deployment.notes,
		},
	}


def _flag(value: bool | int | str) -> bool:
	"""A checkbox as it arrives over HTTP.

	Frappe hands whitelisted methods strings, so `"false"` and `"0"` both arrive
	truthy and a volunteer declining would be recorded as accepting. Named once
	here rather than repeated at each call site.
	"""
	if isinstance(value, str):
		return value.strip().lower() not in ("", "0", "false", "no")

	return bool(value)


@frappe.whitelist()
def deployments_of_volunteer(volunteer: str) -> dict:
	"""Which deployments this volunteer has been on.

	The volunteer is loaded through the permission layer first, so this answers
	only about somebody the caller may already see. The deployments themselves
	are then filtered by core's own scoping, because a volunteer the caller can
	see may have served somewhere the caller cannot.
	"""
	frappe.get_doc(VOLUNTEER_DOCTYPE, volunteer).check_permission("read")

	names = participation.deployments_of(volunteer)
	visible = [name for name in names if _in_scope(DEPLOYMENT_DOCTYPE, name)]

	return {
		"volunteer": volunteer,
		"deployments": _status_rows(visible),
	}


@frappe.whitelist()
def my_deployments() -> dict | None:
	"""Where the logged-in person has served. Takes no argument, so names nobody.

	**Not `deployments_of_volunteer` with the caller's own name**, and the
	difference is not stylistic. That endpoint is the coordinator's: it checks
	`read` on the volunteer and then filters the deployments through core's geo
	scoping, both of which fail closed for somebody holding no Geo Assignment. A
	volunteer holds none — correctly, because the register is not theirs to
	browse — so pointing the portal at it refused every volunteer their own
	deployment history, which is the one part of it nobody should have to ask
	permission for.

	So this is the possessive twin, the same shape as `volunteer.my_volunteer`
	and `volunteer.my_time_logs`: the volunteer comes from the session, and there
	is no argument by which a caller could name anybody else. **Nothing is scoped
	out**, deliberately: a volunteer sent to help another county is entitled to
	the record of having gone, and filtering by where they may *look* would drop
	exactly the deployments worth showing them.

	None for somebody who is not a volunteer, matching `my_volunteer`.
	"""
	volunteer = _my_volunteer()

	if not volunteer:
		return None

	return {
		"volunteer": volunteer,
		"deployments": [_titled(row) for row in _status_rows(participation.deployments_of(volunteer))],
	}


def _titled(row: dict) -> dict:
	"""One of the caller's own deployments, with the work named in words.

	`status_dto` carries `terms_of_reference`, which is an opaque key the app
	refers to and not something to show somebody: a person reading their own
	history wants "Flood Response Team", not `flood-response`. Added here rather
	than in the service, because the coordinator's screens already resolve the
	full terms of reference and do not need a second copy of its label.
	"""
	return {
		**row,
		"title": frappe.db.get_value("VMMS Terms of Reference", row["terms_of_reference"], "tor_name")
		or row["terms_of_reference"],
	}


def _my_volunteer() -> str | None:
	"""The volunteer record of whoever is logged in, or None.

	Delegated to `api/volunteer.py`, which owns the two-hop resolution and its
	Guest refusal. A second copy here would be a second answer to who the caller
	is, and the two would eventually disagree.
	"""
	from vmmsx.api.volunteer import _my_volunteer as resolve

	return resolve()


# --- the coordinator's listings -------------------------------------------
#
# Everything above answers about a deployment somebody already named. These two
# are how a coordinator finds one in the first place, and they are the same
# shape as `tasks.branch_tasks`: `frappe.get_list`, so core's permission query
# condition runs and the caller's Geo Assignment is the floor the answer stands
# on. Every argument narrows that floor and none of them widens it, so there is
# no combination of them that returns a deployment outside the caller's area.
#
# `frappe.get_all` would ignore permissions and hand back a whole-site answer
# wearing the shape of a scoped one. It is not used here and must not be.

PAGE = 100

# Every status a deployment can actually hold, taken from the service that owns
# them rather than retyped here.
#
# **It used to be four of the six**, and the two it left out were the two that
# matter most to a screen: a Suspended deployment silently answered with nothing
# when asked for, and a Closed Out one could not be filtered for at all. A
# filter that fails on a real value is worse than no filter, because the empty
# list reads as "there are none".
_DEPLOYMENT_STATUSES = deployment_service.STATUSES


@frappe.whitelist()
def branch_deployments(
	status: str | None = None,
	statuses: list | str | None = None,
	limit: int | None = None,
	mine: bool | int | str = False,
) -> dict:
	"""Deployments in the caller's own area, most recently touched first.

	An unknown status answers with nothing rather than with everything, which is
	the direction a filter should fail in.

	**`statuses` is the plural of `status`, and it exists because a band is not
	one status.** "Ongoing" means Planned *or* Active *or* Suspended *or*
	Completed-but-not-closed-out, and a screen that could only ask for one at a
	time had to fetch the unfiltered page and sieve it in the browser — which
	means the band was really "whichever members of the band happened to be on
	the first page". Asking the database for the set is the difference between a
	register and a sample. Every value is checked against the six the doctype
	actually has; an unknown one empties the whole filter rather than being
	quietly dropped.

	`total` is how many there are in the band inside the caller's scope, counted
	through the same scoped listing rather than taken from the page's length. The
	two are separate fields because a screen needs both: one labels the list, the
	other says how much of the register it is showing.

	**`mine` narrows to what this person filed, and it can only narrow.** It adds
	an owner filter on top of a result core's query condition has already bounded
	to the caller's geo scope, so it is never a way to reach a deployment the
	permission layer would not have shown. `doc.owner` is the right question
	here for the reason `invitation.py` states: this asks who *did the filing*,
	not who the record is about, and those are the same person for a deployment
	somebody set up themselves.
	"""
	wanted = _status_filter(status, statuses)

	if wanted is None:
		return {"count": 0, "total": 0, "deployments": [], "open_count": 0}

	filters = dict(wanted)

	if _flag(mine):
		filters["owner"] = frappe.session.user

	names = frappe.get_list(
		DEPLOYMENT_DOCTYPE,
		filters=filters,
		order_by="modified desc",
		limit_page_length=min(int(limit or PAGE), PAGE),
		pluck="name",
	)

	rows = _status_rows(names)

	return {
		"count": len(rows),
		# Counted through the same scoped listing and the same filters, so the
		# pager and the list cannot describe two different questions.
		"total": _deployment_count(filters),
		"deployments": rows,
		# What a coordinator's attention is for: the ones still running. Counted
		# from the rows already fetched rather than by a second query, so the
		# number and the list can never disagree.
		"open_count": len([row for row in rows if row.get("is_open")]),
	}


def _status_filter(status: str | None, statuses: list | str | None) -> dict | None:
	"""The status clause for a listing, or None when the caller named nonsense.

	None rather than an empty dict, because "no filter" and "a filter that
	matches nothing" are opposite answers and returning the first for the second
	would hand back every deployment in scope to somebody who asked for a status
	that does not exist.
	"""
	wanted = _names(statuses) if statuses else ([status] if status else [])

	if not wanted:
		return {}

	if any(value not in _DEPLOYMENT_STATUSES for value in wanted):
		return None

	return {"status": ("in", wanted) if len(wanted) > 1 else wanted[0]}


def _deployment_count(filters: dict) -> int:
	"""How many deployments match, through the scoped listing rather than around it.

	`frappe.db.count` would skip core's permission query condition; `get_list`
	runs it. The aggregate is the dict form because Frappe rejects a SQL function
	written as a string in a SELECT.
	"""
	rows = frappe.get_list(
		DEPLOYMENT_DOCTYPE, filters=filters, fields=[{"COUNT": "name"}], as_list=True
	)

	return frappe.utils.cint(rows[0][0]) if rows else 0


@frappe.whitelist()
def branch_requests(limit: int | None = None) -> dict:
	"""Deployment requests raised in the caller's own area, newest first.

	The approval half of each row is the engine's own DTO, which decides for
	itself how much of the approver list this caller may see, and is None for a
	request whose terms ask for no approver. Same boundary as `get_request`.
	"""
	names = frappe.get_list(
		REQUEST_DOCTYPE,
		order_by="creation desc",
		limit_page_length=min(int(limit or PAGE), PAGE),
		pluck="name",
	)

	rows = []

	for name in names:
		request = frappe.get_doc(REQUEST_DOCTYPE, name)
		rows.append(
			{
				**request_service.status(request),
				"approval": request_service.approval_dto(request),
			}
		)

	return {"count": len(rows), "requests": rows}


# --- requests -------------------------------------------------------------


@frappe.whitelist()
def request_deployment(
	terms_of_reference: str,
	geo_node: str,
	needed_from: str,
	needed_until: str,
	volunteers_requested: int = 1,
	justification: str | None = None,
) -> dict:
	"""Raise a request for volunteers and put it into motion.

	The Geo Node is required here, at creation, and not filled in later: ACC-02
	is a property of the record existing, not a step in a workflow. Whether the
	request then needs an approver is its terms of reference's answer, and this
	endpoint does not know which way that goes.
	"""
	frappe.has_permission(REQUEST_DOCTYPE, ptype="create", throw=True)

	request = frappe.get_doc(
		{
			"doctype": REQUEST_DOCTYPE,
			"terms_of_reference": terms_of_reference,
			"geo_node": geo_node,
			"needed_from": needed_from,
			"needed_until": needed_until,
			"volunteers_requested": volunteers_requested,
			"justification": justification,
		}
	)
	request.insert()

	return request_service.submit(request)


@frappe.whitelist()
def get_request(name: str) -> dict:
	"""Where a request stands, and where its approval stands.

	Two DTOs rather than one merged dict: the second is the engine's own, and it
	decides for itself how much of the approver list this caller may see. It is
	None for a request whose terms ask for no approver, which is more honest than
	an empty shape that looks like an approval nobody has started.
	"""
	request = _readable(REQUEST_DOCTYPE, name)

	return {
		**request_service.status(request),
		"approval": request_service.approval_dto(request),
	}


# --- branch transfers -----------------------------------------------------


@frappe.whitelist()
def request_transfer(
	volunteer: str,
	to_geo_node: str,
	effective_date: str,
	reason: str,
) -> dict:
	"""Move a volunteer to another branch, from wherever they are now.

	`from_geo_node` is not an argument: it is snapshotted from the volunteer, so
	a transfer records where somebody actually was rather than where the caller
	believed they were. Whether it needs authorising is the society's setting,
	and this endpoint does not know which way that goes either.

	**The snapshot is taken before the insert, not left to `before_insert`.**
	`insert()` checks create permission first, and this doctype is geo-scoped on
	`from_geo_node` — so a document that has not been anchored yet is one core
	refuses on sight, and every caller but an administrator would be told they
	may not move anybody. `snapshot_origin` is idempotent, so the controller's
	own `before_insert` still covers a transfer raised anywhere else.
	"""
	frappe.has_permission(TRANSFER_DOCTYPE, ptype="create", throw=True)

	transfer = frappe.get_doc(
		{
			"doctype": TRANSFER_DOCTYPE,
			"volunteer": volunteer,
			"to_geo_node": to_geo_node,
			"effective_date": effective_date,
			"reason": reason,
		}
	)
	transfer_service.snapshot_origin(transfer)
	transfer.insert()

	return transfer_service.submit(transfer)


@frappe.whitelist()
def get_transfer(name: str) -> dict:
	"""Where a transfer stands, its approval, and what it would interrupt.

	`in_flight_deployments` is reported and acted on by nothing: a volunteer
	transferred mid-deployment stays on that deployment, which keeps its own
	place. It is here so that whoever is deciding can see it rather than discover
	it.
	"""
	transfer = _readable(TRANSFER_DOCTYPE, name)

	return {
		**transfer_service.status(transfer),
		"approval": transfer_service.approval_dto(transfer),
		"in_flight_deployments": transfer_service.in_flight_deployments(transfer),
	}


@frappe.whitelist()
def cancel_transfer(name: str, reason: str | None = None) -> dict:
	"""Call off a transfer that has not taken effect."""
	transfer = _readable(TRANSFER_DOCTYPE, name)
	transfer.check_permission("write")

	return transfer_service.cancel(transfer, reason)


# --- projects and terms of reference --------------------------------------
#
# The paperwork that has to exist before a deployment does: a programme of work,
# a specification written under it, and then the deployment itself. All three
# registers answer through `frappe.get_list`, never `frappe.get_all` — only the
# first runs core's permission query condition, and the second is a silent
# whole-site answer wearing the shape of a scoped one.
#
# **`mine` narrows and can only narrow.** Every listing here is already bounded
# by the caller's geo scope before the owner filter is applied, so the flag is
# never a way to reach a record the permission layer would have withheld. It
# defaults on for these two registers because a coordinator writing a programme
# is looking for their own, and off for deployments, which are a branch's
# shared register rather than one person's.


@frappe.whitelist()
def project_options() -> dict:
	"""What a screen needs before it can offer to open a programme of work.

	The areas this coordinator may file one in, the one to fill in when there is
	exactly one, and the Company the record will belong to. **The picker is a
	convenience and not the control** — `project_service.assert_may_anchor` runs
	again on the way in, because the request behind a dropdown can name any node
	on the site.

	`default_geo_node` is null where somebody holds several assignments, and that
	is the answer rather than a missing one: guessing which of a person's areas
	they meant is how a programme ends up in the wrong branch's register.
	"""
	frappe.has_permission(PROJECT_DOCTYPE, ptype="create", throw=True)

	from vmmsx.deployment.services.placement import geo_path

	nodes = project_service.authorised_nodes()

	return {
		"geo_nodes": [{"name": node, "geo_path": geo_path(node)} for node in nodes],
		"default_geo_node": project_service.default_node(),
		"company": project_service.default_company(),
		"statuses": list(project_service.STATUSES),
		"funding_statuses": list(_FUNDING_STATUSES),
	}


@frappe.whitelist()
def create_project(
	project_name: str,
	geo_node: str,
	start_date: str | None = None,
	end_date: str | None = None,
	summary: str | None = None,
	notes: str | None = None,
	status: str | None = None,
	company: str | None = None,
	donor: str | None = None,
	funding_reference: str | None = None,
	funding_status: str | None = None,
) -> dict:
	"""Open a programme of work. The Geo Node is required here, at creation.

	ACC-02 is a property of the record existing, not a step in a workflow, and
	the service refuses an unanchored project before the mandatory check can
	produce a field name instead of a sentence. It then refuses one anchored
	somewhere this caller does not run, which is the rule a filtered picker looks
	like it enforces and does not.

	Everything else about the programme — its type, priority, cost centre,
	holiday list, the risks and assumptions — is edited on the record afterwards.
	This is the door, not the whole form.
	"""
	frappe.has_permission(PROJECT_DOCTYPE, ptype="create", throw=True)

	doc = project_service.create(
		project_name=project_name,
		geo_node=geo_node,
		start_date=start_date,
		end_date=end_date,
		summary=summary,
		notes=notes,
		status=status,
		company=company,
		donor=donor,
		funding_reference=funding_reference,
		funding_status=funding_status,
	)

	return project_service.dto(doc)


@frappe.whitelist()
def branch_projects(
	status: str | None = None, limit: int | None = None, mine: bool | int | str = True
) -> dict:
	"""Programmes of work in the caller's own area, newest first.

	An unknown status answers with nothing rather than with everything, the same
	direction `branch_deployments` fails in.
	"""
	if status and status not in project_service.STATUSES:
		return {"count": 0, "projects": [], "open_count": 0}

	filters = {"status": status} if status else {}

	if _flag(mine):
		filters["owner"] = frappe.session.user

	names = frappe.get_list(
		PROJECT_DOCTYPE,
		filters=filters,
		order_by="creation desc",
		limit_page_length=min(int(limit or PAGE), PAGE),
		pluck="name",
	)

	rows = [project_service.dto(frappe.get_doc(PROJECT_DOCTYPE, name)) for name in names]

	return {
		"count": len(rows),
		"projects": rows,
		"open_count": len([row for row in rows if row.get("is_open")]),
	}


@frappe.whitelist()
def get_project(name: str) -> dict:
	"""One project: the terms of reference written under it, and the deployments run under them.

	A deployment reaches a project only through its terms — there is no second
	link on `VMMS Deployment`, by design — so the deployments here are found by
	first listing the project's own terms and then asking for deployments
	anchored to any of them. Composed here rather than at three call sites, for
	the reason `get_terms` states: reading a project's whole shape as one call is
	the only way its pieces cannot disagree with each other.

	No owner filter, unlike `branch_projects`/`branch_terms`: this is the
	project's own children, not what any one coordinator filed, and geo scope
	from `frappe.get_list`'s permission query condition is the only floor. Every
	terms of reference ever written under the project comes back, active or
	retired, and every deployment regardless of status — a project's detail page
	is its whole history, not today's open work.
	"""
	project = _readable(PROJECT_DOCTYPE, name)

	tor_names = frappe.get_list(
		TERMS_DOCTYPE,
		filters={"project": project.name},
		order_by="creation desc",
		pluck="name",
	)

	deployment_names = (
		frappe.get_list(
			DEPLOYMENT_DOCTYPE,
			filters={"terms_of_reference": ["in", tor_names]},
			order_by="modified desc",
			pluck="name",
		)
		if tor_names
		else []
	)

	return {
		"project": project_service.dto(project),
		"terms": [terms.dto(n) for n in tor_names],
		"deployments": _status_rows(deployment_names),
	}


@frappe.whitelist()
def set_project_status(name: str, status: str, reason: str | None = None) -> dict:
	"""Move a project's status. Idempotent, and refuses a status outside the four.

	The four are ERPNext's — Open, On hold, Completed, Cancelled — and there is
	deliberately no transition table behind them: a standard field that ERPNext's
	own screens and a society's native Workflow can both move is not a field this
	app may quietly put a private grammar over. `project_service` says so at
	length.

	Write permission, which brings core's geo scoping with it: closing a
	programme is an act on the branch's register, not on a personal record.
	"""
	doc = frappe.get_doc(PROJECT_DOCTYPE, name)
	doc.check_permission("write")

	return project_service.set_status(doc, status, reason=reason)


@frappe.whitelist()
def create_terms(
	tor_name: str,
	project: str | None = None,
	purpose: str | None = None,
	mission_background: str | None = None,
	responsibilities: str | None = None,
	geo_scope: str | None = None,
	expected_start_date: str | None = None,
	expected_end_date: str | None = None,
	default_duration_days: int | None = None,
	approval_mode: str | None = None,
	is_active: bool | int | str = True,
	has_no_resources: bool | int | str = False,
	notes: str | None = None,
	**tables,
) -> dict:
	"""Write a terms of reference, optionally under a project.

	The stable key is derived by the service and never asked for: a society
	writing terms on a screen has no reason to invent a slug, and the key is what
	every deployment afterwards points at.

	**Left as a draft.** A mission document is written over several sittings, and
	`submit_terms` is the separate, deliberate act that says the wording is
	final. The screens draw those as two buttons for exactly that reason.

	The six mission tables are optional and arrive through `**tables`, parsed the
	same way the editor's own payload is, so writing a whole mission in one call
	and building it up tab by tab go through one normaliser.
	"""
	frappe.has_permission(TERMS_DOCTYPE, ptype="create", throw=True)

	doc = terms.create(
		tor_name=tor_name,
		project=project,
		purpose=purpose,
		mission_background=mission_background,
		responsibilities=responsibilities,
		geo_scope=geo_scope,
		expected_start_date=expected_start_date,
		expected_end_date=expected_end_date,
		default_duration_days=default_duration_days,
		approval_mode=approval_mode,
		is_active=_flag(is_active),
		has_no_resources=_flag(has_no_resources),
		notes=notes,
		**_terms_payload(tables),
	)

	return terms.dto(doc.name)


@frappe.whitelist()
def update_terms(name: str, **values) -> dict:
	"""Edit a terms of reference that is still a draft.

	**A draft only**, and the service says why in words: submitting freezes the
	wording because accepting a deployment assignment is accepting exactly this
	document. An amendment is a new record, so what somebody already agreed to is
	never rewritten underneath them.

	The editor sends one tab at a time, so a table the caller did not mention is
	left alone rather than emptied — a screen saving the mission tab must not
	silently delete the itinerary the next tab holds.
	"""
	_readable(TERMS_DOCTYPE, name).check_permission("write")

	return terms.update(name, **_terms_payload(values))


def _terms_payload(values: dict) -> dict:
	"""The editor's payload, with its tables parsed out of the JSON they arrive as.

	Frappe hands a whitelisted method either a real list or the JSON string it
	was sent, depending on how the caller framed the request. Parsed here so the
	service takes lists either way, and unknown keys are left for `terms.update`
	to ignore rather than being filtered twice in two places that could disagree.
	"""
	tables = (
		"stakeholders",
		"objectives",
		"expected_outputs",
		"approach_methods",
		"itinerary",
		"resources",
		"required_certifications",
	)

	parsed = dict(values)

	for field in tables:
		if isinstance(parsed.get(field), str):
			parsed[field] = frappe.parse_json(parsed[field] or "[]")

	return parsed


@frappe.whitelist()
def submit_terms(name: str) -> dict:
	"""Freeze a terms of reference's wording. Idempotent on one already submitted.

	The deliberate act that makes a mission agreeable to. Gated on submit
	permission, which is a grant of its own rather than a consequence of write:
	writing the document and declaring it final are two different authorities,
	and a society may well give them to different people.
	"""
	_readable(TERMS_DOCTYPE, name)

	return terms.submit(name)


@frappe.whitelist()
def send_terms_for_approval(name: str) -> dict:
	"""Hand a finished mission document to the society's approvers.

	The other of the two submission paths, and which one a site has is that
	society's configuration rather than a choice made here: with a
	`VMMS Approval Workflow` for terms of reference, this is the door and
	`submit_terms` refuses; with none, `submit_terms` is the door and this
	refuses. Neither ever half-works, which is why the refusals are explicit
	rather than a silent fallback to the other path.

	Deciding it afterwards is `api/approvals.py`, the generic engine endpoint,
	for the reason this module's own docstring gives: the person-gate lives there
	and a second door into the same decision would be a second place to get it
	wrong.
	"""
	_readable(TERMS_DOCTYPE, name)

	return terms.send_for_approval(name)


@frappe.whitelist()
def supersede_terms(name: str, **values) -> dict:
	"""Start a replacement for terms that deployments are already running under.

	Not an amendment: amending needs a cancel first, and terms a deployment
	points at refuse to be cancelled, because the people already deployed agreed
	to exactly that wording. This writes a *new* draft carrying the whole mission
	across, with `supersedes` pointing back at the original, and leaves the
	original untouched and still in force.

	`values` overrides any editable field on the copy, parsed the same way the
	terms editor's own payload is, so respecifying a period or a scope does not
	mean writing it twice.
	"""
	_readable(TERMS_DOCTYPE, name)
	frappe.has_permission(TERMS_DOCTYPE, ptype="create", throw=True)

	return terms.supersede(name, **_terms_payload(values))


@frappe.whitelist()
def tor_methodologies() -> dict:
	"""The configured vocabularies used by the terms editor.

	The approach tab's picker. Active ones only: a retired methodology stays on
	every terms of reference already citing it and is not offered for a new one,
	which is the same rule every other vocabulary in this app follows.

	`get_all` rather than `get_list`, deliberately: this is configuration
	vocabulary with no geo anchor, the same footing `application_options` reads
	skills and languages on. There is nothing here to scope.
	"""
	rows = frappe.get_all(
		"VMMS TOR Methodology",
		filters={"is_active": 1},
		fields=["name", "methodology_name", "description"],
		order_by="methodology_name asc",
	)

	certifications = frappe.get_all(
		"VMMS Certification Type",
		filters={"is_active": 1},
		fields=["name", "certification_type_name", "description"],
		order_by="certification_type_name asc",
	)

	# The two Link vocabularies the resource grid needs, and the Select behind
	# its funding column. A resource line names a unit and a currency on the
	# doctype and the editor drew both as free text, so "litres", "Litres" and
	# "L" were three units and a costed mission could not be totalled across
	# branches.
	units = frappe.get_all("UOM", filters={"enabled": 1}, pluck="name", order_by="name asc")
	currencies = frappe.get_all("Currency", filters={"enabled": 1}, pluck="name", order_by="name asc")

	funding = frappe.get_meta("VMMS TOR Resource").get_field("funding_status")

	return {
		"methodologies": rows,
		"certification_types": certifications,
		"units": units,
		"currencies": currencies,
		"funding_statuses": [
			option.strip() for option in (funding.options or "").split("\n") if option.strip()
		]
		if funding
		else [],
	}


@frappe.whitelist()
def deployment_options() -> dict:
	"""Configured Link choices used when setting up a deployment.

	Email Template is framework configuration rather than operational data, so it
	is read as a whole vocabulary just as the terms editor reads methodologies.
	"""
	frappe.has_permission(DEPLOYMENT_DOCTYPE, ptype="create", throw=True)

	return {
		"email_templates": frappe.get_all(
			"Email Template",
			fields=["name", "subject"],
			order_by="name asc",
		)
	}


# The three operational records a document may be attached to, in the order a
# register should offer them. A row rather than a branch, so a fourth is a line
# here and nothing else.
_DOCUMENT_PARENTS = (PROJECT_DOCTYPE, TERMS_DOCTYPE, DEPLOYMENT_DOCTYPE)


@frappe.whitelist()
def operations_documents(search: str | None = None, doctype: str | None = None) -> dict:
	"""Private files attached to operational records in the caller's scope.

	**The scope is the parent's, and that is the whole access model.** `File`
	itself is not geo-scopeable — it is attached to something that is — so the
	readable parents are listed first through `frappe.get_list`, which runs
	core's permission query condition, and only files hanging off *those* are
	read. A file whose parent is outside the caller's areas is never named.

	`doctype` narrows to one kind of parent and `search` narrows by file name or
	by the record it is attached to. Both narrow the same scoped result; an
	unknown `doctype` returns nothing rather than everything, which is the
	direction a filter should fail in.

	`targets` is the subset of those parents the caller may *write*, which is
	what an upload is allowed to attach to. It is returned rather than computed
	in the browser so the control offers exactly what the server would accept.
	"""
	wanted = _DOCUMENT_PARENTS if not doctype else tuple(d for d in _DOCUMENT_PARENTS if d == doctype)

	if doctype and not wanted:
		return {"count": 0, "files": [], "targets": [], "record_types": list(_DOCUMENT_PARENTS)}

	# A parent doctype the caller cannot read at all is skipped rather than
	# allowed to throw: `get_list` raises on one with no DocPerm, and a
	# coordinator who may run deployments but may not see projects should get the
	# deployment files rather than an error page. The same rule
	# `api/person.py::registers` follows.
	parents: dict[str, list[str]] = {
		parent: frappe.get_list(parent, pluck="name", limit_page_length=0)
		for parent in wanted
		if frappe.has_permission(parent, "read")
	}
	files = []
	needle = (search or "").strip().lower()

	for parent, names in parents.items():
		if not names:
			continue
		rows = frappe.get_all(
			"File",
			filters={"attached_to_doctype": parent, "attached_to_name": ["in", names], "is_folder": 0},
			fields=["name", "file_name", "file_url", "file_size", "is_private", "attached_to_doctype", "attached_to_name", "owner", "creation", "modified"],
			order_by="modified desc",
			limit_page_length=200,
		)
		for row in rows:
			if needle and needle not in (row.get("file_name") or "").lower() and needle not in (row.get("attached_to_name") or "").lower():
				continue
			files.append(row)

	files.sort(key=lambda row: row.get("modified") or row.get("creation"), reverse=True)
	# Targets are always every kind, whatever the register is filtered to: the
	# filter narrows what you are reading, not what you may file a new document
	# against.
	writable = {
		parent: parents.get(parent)
		if parent in parents
		else frappe.get_list(parent, pluck="name", limit_page_length=0)
		for parent in _DOCUMENT_PARENTS
		if frappe.has_permission(parent, "read")
	}
	targets = [
		{"doctype": parent, "name": name}
		for parent, names in writable.items()
		for name in names
		if frappe.has_permission(parent, ptype="write", doc=name)
	]
	return {
		"count": len(files),
		"files": files,
		"targets": targets,
		"record_types": list(_DOCUMENT_PARENTS),
	}


@frappe.whitelist()
def branch_terms(
	project: str | None = None,
	active_only: bool | int | str = False,
	state: str | None = None,
	search: str | None = None,
	limit: int | None = None,
	mine: bool | int | str = True,
) -> dict:
	"""Terms of reference the caller may read, newest first.

	`project` narrows to one programme's specifications, which is the listing a
	coordinator wants when they are about to deploy under one of them.

	These are configuration rather than an operational record, so they carry no
	`geo_node` and core does not scope them: `geo_scope` says where they may be
	*used*, which is a different question and is enforced when a deployment is
	anchored. The owner filter is what keeps this register personal, and it is
	why `mine` defaults on here.
	"""
	from vmmsx.approvals import states as approval_states

	filters = {}

	if project:
		filters["project"] = project

	if _flag(active_only):
		filters["is_active"] = 1

	if _flag(mine):
		filters["owner"] = frappe.session.user

	if state:
		# One of the seven in `states.py`, never a stage label: stages are a
		# society's own wording and nothing in this app compares them. An unknown
		# value empties the result rather than being dropped, which is the
		# direction a filter should fail in.
		if state not in approval_states.STATES:
			return {"count": 0, "terms": [], "states": list(approval_states.STATES)}

		filters["approval_state"] = state

	if search:
		# Frappe's `like` on the register's own two human-readable columns. An
		# `or_filters` rather than two reads, so paging still describes one
		# question.
		needle = f"%{search.strip()}%"
		or_filters = {"tor_name": ("like", needle), "tor_key": ("like", needle)}
	else:
		or_filters = None

	names = frappe.get_list(
		TERMS_DOCTYPE,
		filters=filters,
		or_filters=or_filters,
		order_by="creation desc",
		limit_page_length=min(int(limit or PAGE), PAGE),
		pluck="name",
	)

	rows = [terms.dto(name) for name in names]

	return {
		"count": len(rows),
		"terms": rows,
		# The closed set a filter control may offer, handed over rather than
		# retyped in the browser.
		"states": list(approval_states.STATES),
	}


@frappe.whitelist()
def get_terms(name: str) -> dict:
	"""One terms of reference, the same document rendered for the screen, and
	the deployments run under it.

	Three keys rather than a merged blob: `terms` is the reviewed field list
	every other caller gets, `document` is the society's own template rendered
	against it — the identical markup the PDF is made from, so what somebody
	reads on the screen and what comes out of the printer cannot drift apart —
	and `deployments` is composed here rather than folded into `terms.dto()`,
	because `terms.dto()` is embedded verbatim inside every `deployment_dto()`
	call: were the deployment list part of its own shape, every single
	deployment read would recursively re-embed the full list of its own
	siblings, unbounded. Composed only at this call site instead.

	Read permission decides. There is no holder bypass, for the reason
	`_readable` states: a terms of reference is the society's paperwork.
	"""
	_readable(TERMS_DOCTYPE, name)

	deployment_names = frappe.get_list(
		DEPLOYMENT_DOCTYPE,
		filters={"terms_of_reference": name},
		order_by="modified desc",
		limit_page_length=PAGE,
		pluck="name",
	)

	return {
		# `mission_dto`, not `dto`: this is the one screen that shows a terms of
		# reference in full, so it is the one place that pays for reading the six
		# child tables. Every other caller — every deployment header, every list
		# row — gets the lean summary, which is why `dto` stays lean.
		"terms": terms.mission_dto(name),
		"document": tor_document.render_document(name)["body"],
		"deployments": _status_rows(deployment_names),
	}


@frappe.whitelist()
def download_terms(name: str):
	"""The terms of reference as a PDF, on the society's letterhead.

	Same permission as reading it: a document somebody may open on the screen is
	one they may put on paper, and a second answer here would be a second place
	for the two to disagree.
	"""
	_readable(TERMS_DOCTYPE, name)

	frappe.local.response.filename = tor_document.pdf_filename(name)
	frappe.local.response.filecontent = tor_document.pdf_for(name)
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def create_deployment(
	terms_of_reference: str,
	geo_node: str,
	start_date: str,
	end_date: str,
	volunteers_required: int | None = None,
	status: str | None = None,
	email_template: str | None = None,
	notes: str | None = None,
	coordinator: str | None = None,
	**place,
) -> dict:
	"""Set up a deployment directly, under terms that already exist.

	The other way one comes into being is an approved `VMMS Deployment Request`,
	and that path is deliberately untouched: this is the branch running its own
	duty rather than asking anybody for people. The insert is ordinary, so core's
	query condition refuses a deployment anchored outside the caller's own area.

	`volunteers_required` is optional and zero means the society has not said —
	a deployment that has not said how many it needs is never full.
	"""
	frappe.has_permission(DEPLOYMENT_DOCTYPE, ptype="create", throw=True)

	doc = deployment_service.create(
		terms_of_reference=terms_of_reference,
		geo_node=geo_node,
		start_date=start_date,
		end_date=end_date,
		volunteers_required=volunteers_required,
		status=status,
		email_template=email_template,
		notes=notes,
		coordinator=coordinator,
		**place,
	)

	return deployment_service.deployment_dto(doc)


@frappe.whitelist()
def update_deployment(name: str, **values) -> dict:
	"""Correct a deployment that already exists.

	**The half of the deployment record that had no door.** `create_deployment`
	has always accepted the site, the meeting point, the travel notes and the
	local contact through `**place`, and a coordinator who learned any of them a
	week later had nowhere to put them: the console's form only ran at creation
	and there was no update endpoint at all. Everything `change.py` does — the
	material-change comparison, the reason it insists on, the announcement to
	everybody already invited — existed for an edit path that could not be
	reached.

	Write permission, which brings core's geo scoping with it: a deployment is
	the branch's record, not a personal one. The narrow field list lives in
	`deployment.EDITABLE_FIELDS`, which says at length what is deliberately
	absent from it and why.
	"""
	deployment = _readable(DEPLOYMENT_DOCTYPE, name)
	deployment.check_permission("write")

	return deployment_service.deployment_dto(deployment_service.update(deployment, values))


# --- where it is, and how people get there ---------------------------------


@frappe.whitelist()
def locate_deployment(name: str, place: str, force: bool | int | str = False) -> dict:
	"""Turn one of a deployment's two addresses into a point. Never fails a save.

	**An explicit act, not a side effect.** Nothing geocodes when a deployment is
	saved: a third party being slow must never be the reason a coordinator cannot
	file their work. So this is a button, and everything it can go wrong with
	comes back as `located: false` and a sentence — no provider configured, an
	address nobody can place, a timeout — rather than as an error.

	A pin already on the record wins unless `force` is set, because somebody who
	moved it knew something the address does not.
	"""
	deployment = _readable(DEPLOYMENT_DOCTYPE, name)
	deployment.check_permission("write")

	from vmmsx.deployment.services import geocoding

	geocoding.assert_known(place, geocoding.PLACES)

	return geocoding.locate_place(deployment, place, force=_flag(force))


@frappe.whitelist()
def place_deployment_pin(name: str, place: str, latitude: float, longitude: float) -> dict:
	"""Drop one of a deployment's two pins by hand. The correction a geocoder cannot make.

	Clears the "located on" stamp, because the point no longer came from the
	address — which is the difference a later reader needs and the reason an
	automatic pass will leave it alone.
	"""
	deployment = _readable(DEPLOYMENT_DOCTYPE, name)
	deployment.check_permission("write")

	from vmmsx.deployment.services import geocoding

	geocoding.assert_known(place, geocoding.PLACES)

	return geocoding.relocate(deployment, place, latitude, longitude)


# --- ending it -------------------------------------------------------------


@frappe.whitelist()
def close_out_deployment(
	name: str, lessons: str | None = None, report: str | None = None
) -> dict:
	"""Move a completed deployment to Closed Out. Both fields optional, always.

	Nothing blocks it — not an unmarked roster, not an open task, not somebody
	who never filed their hours. A close-out that can be refused is one that does
	not happen, and a register full of work that ended in March is worse than one
	whose paperwork is thin. The transition table is the only rule: Completed is
	the one status this is reachable from.
	"""
	deployment = _readable(DEPLOYMENT_DOCTYPE, name)
	deployment.check_permission("write")

	return deployment_service.close_out(deployment, lessons=lessons, report=report)


# --- shared ---------------------------------------------------------------


def _readable(doctype: str, name: str):
	"""Load a document the caller is allowed to see.

	Ordinary permission only: Frappe's roles *and* core's geo scoping, because
	all three of this module's doctypes are registered as scopeable. There is no
	holder bypass here, deliberately. A deployment is the society's record of
	work, not a personal one, and a volunteer reaching their own participation
	does so through their own record rather than by opening the register.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")

	return doc


def _in_scope(doctype: str, name: str) -> bool:
	"""Is this record inside the caller's geo scope?

	Asked through core's own guard so the verdict is the one every other layer
	would reach, rather than a fourth opinion assembled here.
	"""
	try:
		guard(doctype, name)
	except frappe.PermissionError:
		return False

	return True


# --- the operations command centre ------------------------------------------

# What "ongoing" means, once, here — and it is four statuses rather than two.
#
# A deployment is still somebody's problem while it is Planned, Active or
# Suspended, and also while it is Completed but not yet Closed Out: the work
# stopped and the paperwork did not. Closed Out and Cancelled are the two that
# are genuinely over, and they are the two this band excludes.
ONGOING_STATUSES = (
	deployment_service.STATUS_PLANNED,
	deployment_service.STATUS_ACTIVE,
	deployment_service.STATUS_SUSPENDED,
	deployment_service.STATUS_COMPLETED,
)

# How many deployments the map and the summary will read. A ceiling on work
# rather than a page size; `capped` says when it was reached so a screen can
# present its figures as a floor rather than as a total.
_OPERATIONS_CEILING = 500

# How close to starting counts as "soon", for the summary's own tile.
_STARTING_SOON_DAYS = 14


@frappe.whitelist()
def operations_summary() -> dict:
	"""The operations overview's figures, over the caller's whole scope.

	Every number here is counted across the scoped register rather than across
	one page of it, which is the entire reason it exists: the dashboard used to
	derive its tiles from `branch_deployments`' capped page and had to say so in
	a footnote. A footnote is not a fix.

	    ongoing        deployments still somebody's problem, and the four
	                   statuses that make up that band, each counted separately
	    people         how many are actually out — Assigned plus Accepted — on
	                   the ones that are Active
	    starting_soon  Planned deployments beginning inside the window, and how
	                   many places are still open on them
	    pending        invitations asked and unanswered, across the band
	    requests       deployment requests still waiting on an outcome
	    terms          terms of reference the caller may read, and how many of
	                   those are still in an open approval state

	**Scope is the floor, not a filter.** Every read is `frappe.get_list`, so
	core's permission query condition applies; nothing here takes an argument, so
	there is nothing a caller could send that would widen it.
	"""
	from frappe.utils import add_days, cint, getdate, today

	from vmmsx.deployment.services import assignment as assignment_service

	moment = getdate(today())
	horizon = add_days(moment, _STARTING_SOON_DAYS)

	rows = frappe.get_list(
		DEPLOYMENT_DOCTYPE,
		filters={"status": ("in", list(ONGOING_STATUSES))},
		fields=["name", "status", "start_date", "volunteers_required"],
		order_by="modified desc",
		limit_page_length=_OPERATIONS_CEILING + 1,
	)

	capped = len(rows) > _OPERATIONS_CEILING
	rows = rows[:_OPERATIONS_CEILING]

	tallies = assignment_service.counts_for_many([row["name"] for row in rows])

	def tally(row) -> dict:
		return tallies.get(row["name"]) or {}

	by_status = {status: 0 for status in ONGOING_STATUSES}

	for row in rows:
		if row["status"] in by_status:
			by_status[row["status"]] += 1

	active = [row for row in rows if row["status"] == deployment_service.STATUS_ACTIVE]
	soon = [
		row
		for row in rows
		if row["status"] == deployment_service.STATUS_PLANNED
		and row.get("start_date")
		and moment <= getdate(row["start_date"]) <= horizon
	]

	return {
		"as_of": moment,
		"ongoing": len(rows),
		"by_status": by_status,
		"people": sum(tally(row).get("on_deployment", 0) for row in active),
		"starting_soon": len(soon),
		"starting_soon_days": _STARTING_SOON_DAYS,
		"unfilled_soon": sum(
			max(cint(row.get("volunteers_required")) - tally(row).get("on_deployment", 0), 0)
			for row in soon
			if cint(row.get("volunteers_required")) > 0
		),
		"pending": sum(tally(row).get("Pending", 0) for row in rows),
		# Completed and not yet Closed Out: the work is over and the paperwork is
		# not. Its own figure because it is its own job.
		"closing_out": by_status.get(deployment_service.STATUS_COMPLETED, 0),
		**_request_figures(),
		**_terms_figures(),
		"capped": capped,
	}


def _request_figures() -> dict:
	"""Deployment requests in scope, and how many are still waiting on somebody.

	Asked before the read rather than caught after it, the same rule
	`api/person.py::registers` follows: `get_list` raises on a doctype the caller
	has no read permission for at all, and one absent permission must cost this
	block its two numbers rather than the whole dashboard. A coordinator who may
	run deployments and may not see requests gets `None` here, and the screen
	draws nothing rather than a zero that would read as "there are none".
	"""
	if not frappe.has_permission(REQUEST_DOCTYPE, "read"):
		return {"requests": None, "requests_open": None}

	names = frappe.get_list(
		REQUEST_DOCTYPE,
		order_by="creation desc",
		limit_page_length=_OPERATIONS_CEILING,
		pluck="name",
	)

	open_requests = 0

	for name in names:
		request = frappe.get_doc(REQUEST_DOCTYPE, name)
		status = request_service.status(request)

		if not status.get("is_fulfilled") and not status.get("is_refused"):
			open_requests += 1

	return {"requests": len(names), "requests_open": open_requests}


def _terms_figures() -> dict:
	"""Terms of reference in scope, and how many are still under approval.

	`approval_state` is read off the field and compared against the closed set in
	`states.py` — never against a stage label, which is a society's own wording
	and is displayed rather than branched on.
	"""
	from vmmsx.approvals import states

	# See `_request_figures`: an absent permission costs this block its numbers,
	# never the page.
	if not frappe.has_permission(TERMS_DOCTYPE, "read"):
		return {"terms": None, "terms_awaiting": None}

	total = frappe.get_list(TERMS_DOCTYPE, fields=[{"COUNT": "name"}], as_list=True)
	awaiting = frappe.get_list(
		TERMS_DOCTYPE,
		filters={"approval_state": ("in", [states.SUBMITTED, states.IN_REVIEW])},
		fields=[{"COUNT": "name"}],
		as_list=True,
	)

	return {
		"terms": frappe.utils.cint(total[0][0]) if total else 0,
		"terms_awaiting": frappe.utils.cint(awaiting[0][0]) if awaiting else 0,
	}


@frappe.whitelist()
def deployment_sites(status: str | None = None) -> dict:
	"""Every readable deployment as a point on a map, with the mission picture.

	**The counterpart of `deployment_map`, not a replacement for it.** That one
	aggregates by Geo Node and answers "where are most of our people"; a coloured
	circle over a county cannot be selected, and selecting one deployment to read
	its site, its meeting point, its coordinator and its readiness is the whole
	of what an operations map is for. So this returns the deployments themselves,
	each with the coordinates already on its own record.

	**The coordinates are the deployment's own, never the geo tree's and never a
	constant.** `where_dto` reads the two places a deployment has —
	`geocoding.dto` says which fields those are — and `has_point` is False where
	nobody has located it yet. A deployment with no point is *still in the
	answer*, counted in `unplotted`, because a map that silently dropped them
	would under-report exactly where the gaps in the data are.

	**Scope is the floor.** `frappe.get_list` runs core's permission query
	condition; `status` narrows within that and an unknown one empties the result
	rather than widening it.
	"""
	from vmmsx.deployment.services import assignment as assignment_service

	wanted = _status_filter(status, None)

	if wanted is None:
		return {"deployments": [], "count": 0, "plotted": 0, "unplotted": 0, "capped": False}

	filters = dict(wanted) or {"status": ("in", list(ONGOING_STATUSES))}

	names = frappe.get_list(
		DEPLOYMENT_DOCTYPE,
		filters=filters,
		order_by="modified desc",
		limit_page_length=_OPERATIONS_CEILING + 1,
		pluck="name",
	)

	capped = len(names) > _OPERATIONS_CEILING
	names = names[:_OPERATIONS_CEILING]

	# Two grouped queries for the whole page rather than two per row: a map of
	# forty deployments must not be eighty queries.
	tallies = assignment_service.counts_for_many(names)
	readiness = assignment_service.readiness_for_many(names)

	rows = [
		_site_row(frappe.get_doc(DEPLOYMENT_DOCTYPE, name), tallies.get(name), readiness.get(name))
		for name in names
	]

	plotted = [row for row in rows if row["where"]["site"]["has_point"]]

	return {
		"deployments": rows,
		"count": len(rows),
		"plotted": len(plotted),
		# Named rather than left to be counted, so the screen says "3 of 11 have
		# no location yet" instead of quietly drawing eight pins.
		"unplotted": len(rows) - len(plotted),
		"capped": capped,
	}


def _site_row(deployment, counts: dict | None, readiness: dict | None) -> dict:
	"""One deployment as the map's detail panel reads it. Built field by field.

	`status_dto` carries the period, the control times, the headcount and the
	places left; `where_dto` carries the two places and how to get to them;
	`coordinator_dto` carries who to ring. All three are the DTOs their own
	services already build, composed here rather than re-derived — so the map
	panel and the deployment page cannot come to describe the same deployment
	differently.
	"""
	return {
		**deployment_service.status_dto(deployment, counts=counts),
		"where": deployment_service.where_dto(deployment),
		"coordinator_contact": deployment_service.coordinator_dto(deployment),
		# How ready the roster is, from the same grouped read the whole page
		# shares. Empty rather than absent for a deployment with nobody on it.
		"readiness": readiness or {"briefed": 0, "safety": 0, "checked_in": 0, "leaders": 0},
	}
