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
from vmmsx.deployment.services import invitation, matching, participation
from vmmsx.deployment.services import project as project_service
from vmmsx.deployment.services import request as request_service
from vmmsx.deployment.services import terms, tor_document
from vmmsx.deployment.services import transfer as transfer_service

DEPLOYMENT_DOCTYPE = "VMMS Deployment"
REQUEST_DOCTYPE = "VMMS Deployment Request"
TRANSFER_DOCTYPE = "VMMS Branch Transfer"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"
PROJECT_DOCTYPE = "VMMS Project"
TERMS_DOCTYPE = "VMMS Terms of Reference"


# --- matching -------------------------------------------------------------


@frappe.whitelist()
def find_candidates(
	terms_of_reference: str,
	geo_node: str,
	as_of: str | None = None,
	limit: int | None = None,
) -> dict:
	"""Volunteers who fit this need, within the caller's own area.

	The scope is derived from the session on every call and cannot be supplied,
	so an out-of-scope volunteer is not returnable by any argument. `as_of` moves
	the certification questions to another date, which is what a caller planning
	a deployment for next month actually wants to ask.
	"""
	return matching.candidates(terms_of_reference, geo_node, as_of=as_of, limit=limit)


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
	"""Put a volunteer on a deployment's roster. Idempotent.

	This is the act that makes a deployment time log possible for that person, so
	it is gated on write permission on the deployment: adding somebody to a
	roster is changing what the society says happened.
	"""
	deployment = _readable(DEPLOYMENT_DOCTYPE, name)
	deployment.check_permission("write")

	if participation.add(deployment, volunteer, joined_on=joined_on):
		deployment.save()

	return deployment_service.deployment_dto(deployment)


@frappe.whitelist()
def invite_volunteer(name: str, volunteer: str, joined_on: str | None = None) -> dict:
	"""Ask a volunteer to join a deployment, and notify them. Idempotent.

	Gated on write permission on the deployment, the same as `add_participant`,
	because it writes the same roster row. The difference between the two is what
	the coordinator is saying: `add_participant` records that somebody is going,
	this one asks whether they will.
	"""
	deployment = _readable(DEPLOYMENT_DOCTYPE, name)
	deployment.check_permission("write")

	return invitation.invite(deployment, volunteer, joined_on=joined_on)


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
def respond_to_invitation(deployment: str, accept: bool | int | str, note: str | None = None) -> dict:
	"""Accept or decline one of the caller's own invitations.

	This one names a deployment, which the possessive endpoints above never do,
	so the check that would otherwise be missing is written out: the roster row
	being answered has to be the caller's own. That is **ownership**, not geo
	scope, and it is the same distinction `participation.py` draws. A volunteer
	has no scope, so a permission check here would refuse everybody; an ownership
	check refuses everybody but the one person entitled to answer.

	The deployment is loaded without a read check for exactly that reason, and it
	is never returned: what comes back is `invitation`'s own outcome, built field
	by field, so a volunteer answering an invitation is not handed the roster of
	everybody else who was asked.
	"""
	volunteer = _my_volunteer()

	if not volunteer:
		frappe.throw(
			frappe._("You do not have a volunteer record, so there is nothing to answer."),
			frappe.PermissionError,
		)

	document = frappe.get_doc(DEPLOYMENT_DOCTYPE, deployment)

	if not participation.is_participant(document.name, volunteer):
		# The same answer a volunteer gets for a deployment that does not exist.
		# Distinguishing the two would let somebody probe for deployment names.
		frappe.throw(
			frappe._("There is no invitation for you on this deployment."),
			frappe.PermissionError,
		)

	return invitation.respond(document, volunteer, accepted=_flag(accept), note=note)


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
		"deployments": [
			deployment_service.status_dto(frappe.get_doc(DEPLOYMENT_DOCTYPE, name)) for name in visible
		],
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
		"deployments": [
			_my_deployment_row(frappe.get_doc(DEPLOYMENT_DOCTYPE, name))
			for name in participation.deployments_of(volunteer)
		],
	}


def _my_deployment_row(deployment) -> dict:
	"""One of the caller's own deployments, with the work named in words.

	`status_dto` carries `terms_of_reference`, which is an opaque key the app
	refers to and not something to show somebody: a person reading their own
	history wants "Flood Response Team", not `flood-response`. Added here rather
	than in the service, because the coordinator's screens already resolve the
	full terms of reference and do not need a second copy of its label.
	"""
	row = deployment_service.status_dto(deployment)

	return {
		**row,
		"title": frappe.db.get_value(
			"VMMS Terms of Reference", deployment.terms_of_reference, "tor_name"
		)
		or deployment.terms_of_reference,
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

_DEPLOYMENT_STATUSES = ("Planned", "Active", "Completed", "Cancelled")


@frappe.whitelist()
def branch_deployments(
	status: str | None = None, limit: int | None = None, mine: bool | int | str = False
) -> dict:
	"""Deployments in the caller's own area, most recently touched first.

	An unknown status answers with nothing rather than with everything, which is
	the direction a filter should fail in.

	**`mine` narrows to what this person filed, and it can only narrow.** It adds
	an owner filter on top of a result core's query condition has already bounded
	to the caller's geo scope, so it is never a way to reach a deployment the
	permission layer would not have shown. `doc.owner` is the right question
	here for the reason `invitation.py` states: this asks who *did the filing*,
	not who the record is about, and those are the same person for a deployment
	somebody set up themselves.
	"""
	if status and status not in _DEPLOYMENT_STATUSES:
		return {"count": 0, "deployments": [], "open_count": 0}

	filters = {"status": status} if status else {}

	if _flag(mine):
		filters["owner"] = frappe.session.user

	names = frappe.get_list(
		DEPLOYMENT_DOCTYPE,
		filters=filters,
		order_by="modified desc",
		limit_page_length=min(int(limit or PAGE), PAGE),
		pluck="name",
	)

	rows = [
		deployment_service.status_dto(frappe.get_doc(DEPLOYMENT_DOCTYPE, name)) for name in names
	]

	return {
		"count": len(rows),
		"deployments": rows,
		# What a coordinator's attention is for: the ones still running. Counted
		# from the rows already fetched rather than by a second query, so the
		# number and the list can never disagree.
		"open_count": len([row for row in rows if row.get("is_open")]),
	}


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
def create_project(
	project_name: str,
	geo_node: str,
	start_date: str | None = None,
	end_date: str | None = None,
	summary: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Open a programme of work. The Geo Node is required here, at creation.

	ACC-02 is a property of the record existing, not a step in a workflow, and
	the service refuses an unanchored project before the mandatory check can
	produce a field name instead of a sentence.
	"""
	frappe.has_permission(PROJECT_DOCTYPE, ptype="create", throw=True)

	doc = project_service.create(
		project_name=project_name,
		geo_node=geo_node,
		start_date=start_date,
		end_date=end_date,
		summary=summary,
		notes=notes,
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
def set_project_status(name: str, status: str, reason: str | None = None) -> dict:
	"""Move a project's status. Idempotent, and refuses a move outside the grammar.

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
	responsibilities: str | None = None,
	geo_scope: str | None = None,
	default_duration_days: int | None = None,
	approval_mode: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Write a terms of reference, optionally under a project.

	The stable key is derived by the service and never asked for: a society
	writing terms on a screen has no reason to invent a slug, and the key is what
	every deployment afterwards points at.
	"""
	frappe.has_permission(TERMS_DOCTYPE, ptype="create", throw=True)

	doc = terms.create(
		tor_name=tor_name,
		project=project,
		purpose=purpose,
		responsibilities=responsibilities,
		geo_scope=geo_scope,
		default_duration_days=default_duration_days,
		approval_mode=approval_mode,
		notes=notes,
	)

	return terms.dto(doc.name)


@frappe.whitelist()
def branch_terms(
	project: str | None = None,
	active_only: bool | int | str = False,
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
	filters = {}

	if project:
		filters["project"] = project

	if _flag(active_only):
		filters["is_active"] = 1

	if _flag(mine):
		filters["owner"] = frappe.session.user

	names = frappe.get_list(
		TERMS_DOCTYPE,
		filters=filters,
		order_by="creation desc",
		limit_page_length=min(int(limit or PAGE), PAGE),
		pluck="name",
	)

	rows = [terms.dto(name) for name in names]

	return {"count": len(rows), "terms": rows}


@frappe.whitelist()
def get_terms(name: str) -> dict:
	"""One terms of reference, and the same document rendered for the screen.

	Two keys rather than a merged blob: `terms` is the reviewed field list every
	other caller gets, and `document` is the society's own template rendered
	against it — the identical markup the PDF is made from, so what somebody
	reads on the screen and what comes out of the printer cannot drift apart.

	Read permission decides. There is no holder bypass, for the reason
	`_readable` states: a terms of reference is the society's paperwork.
	"""
	_readable(TERMS_DOCTYPE, name)

	return {
		"terms": terms.dto(name),
		"document": tor_document.render_document(name)["body"],
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
	notes: str | None = None,
) -> dict:
	"""Set up a deployment directly, under terms that already exist.

	The other way one comes into being is an approved `VMMS Deployment Request`,
	and that path is deliberately untouched: this is the branch running its own
	duty rather than asking anybody for people. The insert is ordinary, so core's
	query condition refuses a deployment anchored outside the caller's own area.
	"""
	frappe.has_permission(DEPLOYMENT_DOCTYPE, ptype="create", throw=True)

	doc = deployment_service.create(
		terms_of_reference=terms_of_reference,
		geo_node=geo_node,
		start_date=start_date,
		end_date=end_date,
		notes=notes,
	)

	return deployment_service.deployment_dto(doc)


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
