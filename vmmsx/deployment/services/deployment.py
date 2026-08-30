# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The deployment's own lifecycle, and what a caller is told about one.

**Statuses are code; the work is configuration.** The four values below are a
closed set with a fixed transition table, for the same reason approval states
are code: each one means something the server acts on, so a society adding a
fifth would produce a deployment nothing knows how to handle. What a society
genuinely varies is *what it deploys people to do*, and that is
`VMMS Terms of Reference` — an open set of records on which **no code anywhere
branches**.

**Every status change goes through `assert_transition`.** The table is the whole
grammar. Cancelled and Completed are terminal: a deployment that finished is
history, and reopening it by editing a field would silently change what its time
logs were logged against.

**The status deliberately does not gate time logs.** Ownership does, and only
ownership: somebody who served on a deployment may file the hours afterwards,
which is the ordinary case, and a Completed deployment refusing its own
participants' logs would be a rule that punishes accurate record-keeping. See
`participation.OWNERSHIP_RULE`.
"""

import frappe
from frappe import _
from frappe.utils import getdate, today

DEPLOYMENT_DOCTYPE = "VMMS Deployment"

STATUS_PLANNED = "Planned"
STATUS_ACTIVE = "Active"
STATUS_COMPLETED = "Completed"
STATUS_CANCELLED = "Cancelled"

STATUSES = (STATUS_PLANNED, STATUS_ACTIVE, STATUS_COMPLETED, STATUS_CANCELLED)

# Open: the deployment is still somebody's problem. Terminal: it is not.
OPEN_STATUSES = (STATUS_PLANNED, STATUS_ACTIVE)
TERMINAL_STATUSES = (STATUS_COMPLETED, STATUS_CANCELLED)

TRANSITIONS: dict[str, tuple[str, ...]] = {
	# Planned to Planned, and Active to Active, are in the table because saving a
	# deployment without changing its status is the commonest thing that happens
	# to one. They are real transitions, not omissions.
	STATUS_PLANNED: (STATUS_PLANNED, STATUS_ACTIVE, STATUS_COMPLETED, STATUS_CANCELLED),
	# A deployment that has begun may still be called off; what it may not do is
	# go back to having been merely planned, because people were there.
	STATUS_ACTIVE: (STATUS_ACTIVE, STATUS_COMPLETED, STATUS_CANCELLED),
	STATUS_COMPLETED: (STATUS_COMPLETED,),
	STATUS_CANCELLED: (STATUS_CANCELLED,),
}


def assert_status(status: str | None) -> None:
	"""Throw unless `status` is one of the four."""
	if status in STATUSES:
		return

	frappe.throw(
		_("{0} is not a deployment status. Expected one of: {1}.").format(
			frappe.bold(status), ", ".join(STATUSES)
		),
		frappe.ValidationError,
		title=_("Unknown Deployment Status"),
	)


def can_transition(current: str | None, target: str) -> bool:
	"""Is `current` to `target` in the grammar?

	An unset status counts as Planned: a deployment that has never been moved is
	a planned one, whatever its field happens to hold.
	"""
	return target in TRANSITIONS.get(current or STATUS_PLANNED, ())


def assert_transition(current: str | None, target: str) -> None:
	"""Throw unless the move is legal. The single chokepoint for status changes."""
	assert_status(target)

	if can_transition(current, target):
		return

	if current in TERMINAL_STATUSES:
		frappe.throw(
			_("This deployment is {0}. A deployment that has ended cannot be moved again.").format(
				frappe.bold(_(current))
			),
			frappe.ValidationError,
			title=_("Deployment Already Ended"),
		)

	frappe.throw(
		_("A deployment cannot go from {0} to {1}.").format(
			frappe.bold(_(current or STATUS_PLANNED)), frappe.bold(_(target))
		),
		frappe.ValidationError,
		title=_("Invalid Deployment Transition"),
	)


def set_status(deployment, target: str, reason: str | None = None) -> dict:
	"""Move a deployment's status and save it. Idempotent.

	Idempotent because the table admits every status to itself: asking for the
	status a deployment already has writes nothing and records nothing.
	"""
	if deployment.status == target:
		return status_dto(deployment)

	assert_transition(deployment.status, target)
	deployment.status = target
	deployment.save()

	if reason:
		deployment.add_comment("Comment", _("{0}. {1}").format(_(target), reason))

	# Into the feed as well as onto the field, so that somebody reading an account
	# of the deployment sees when it started and when it ended in the same list as
	# everything that happened in between. The comment above is the desk's audit
	# trail and this is the account people read; they answer different questions
	# and both are cheap.
	from vmmsx.deployment.services import feed

	feed.note_status(deployment, target, reason)

	return status_dto(deployment)


def create(
	terms_of_reference: str,
	geo_node: str,
	start_date,
	end_date,
	volunteers_required: int | None = None,
	status: str | None = None,
	email_template: str | None = None,
	notes: str | None = None,
):
	"""Insert a deployment directly, without a request in front of it.

	The other way in is `request.fulfil`, which is the approval engine making a
	request real and elevates for a reason it states at length. This is the
	coordinator who is not asking anybody: a branch running its own duty under
	its own terms. So it is an **ordinary insert** — core's query condition runs
	on the anchor and refuses a deployment filed outside the coordinator's own
	area, which is exactly the check `fulfil` cannot use and this one must.

	The two coherence rules are checked here rather than left to the first save,
	so a caller is told which of them refused: these terms are retired, or this
	place is outside them.

	`volunteers_required` is how many people the deployment needs, and it is the
	cap `assignment.assert_room` measures the roster against. Optional, and zero
	means the society has not said — a deployment that has not said how many it
	needs is never full, which is the right default for a branch duty nobody has
	put a number on.
	"""
	from vmmsx.deployment.services import terms

	if not geo_node:
		# ACC-02 restated at the boundary, so a caller gets a sentence about
		# placement rather than a mandatory-field name.
		frappe.throw(
			_("A deployment must be anchored to a place in the organisation before it can be saved."),
			frappe.MandatoryError,
			title=_("Where Is This Deployment?"),
		)

	terms.assert_offered(terms_of_reference)
	terms.assert_within_scope(terms_of_reference, geo_node)

	deployment = frappe.get_doc(
		{
			"doctype": DEPLOYMENT_DOCTYPE,
			"terms_of_reference": terms_of_reference,
			"geo_node": geo_node,
			"start_date": getdate(start_date),
			"end_date": getdate(end_date),
			"status": status or STATUS_PLANNED,
			"volunteers_required": frappe.utils.cint(volunteers_required),
			"email_template": email_template or None,
			"notes": notes,
		}
	)
	deployment.insert()

	return deployment


def is_open(deployment) -> bool:
	return deployment.status in OPEN_STATUSES


def covers(deployment, on_date=None) -> bool:
	"""Was this deployment running on `on_date`? A question about its period only.

	Used to describe a deployment, never to accept or refuse a time log: what a
	log needs is the roster, and a volunteer filing late is filing accurately.
	"""
	as_of = getdate(on_date or today())

	return getdate(deployment.start_date) <= as_of <= getdate(deployment.end_date)


def in_flight(deployment, on_date=None) -> bool:
	"""Is this deployment both open and currently running?"""
	return is_open(deployment) and covers(deployment, on_date)


# --- the DTOs -------------------------------------------------------------


def status_dto(deployment, counts: dict | None = None) -> dict:
	"""Where a deployment stands, as an explicit dict. Built field by field.

	Never the Document: that would leak every field on the record, including ones
	nobody reviewed, and turn every schema change into an API change.

	**`counts` is passed in by listings and computed here only for one-offs.**
	The roster lives in `VMMS Deployment Assignment` now, so the headcount is a
	query rather than `len()` on a child table, and a listing that let this run
	its own query per row would be the N+1 that makes the register crawl at the
	size a national society actually runs at. `assignment.counts_for_many` answers
	the whole page in one grouped query; callers reading a single deployment can
	leave it out and pay for one.
	"""
	from vmmsx.deployment.services import assignment
	from vmmsx.deployment.services.placement import geo_path

	tally = counts if counts is not None else assignment.counts_for(deployment.name)

	return {
		"name": deployment.name,
		"terms_of_reference": deployment.terms_of_reference,
		"geo_node": deployment.geo_node,
		# Through `placement.geo_path`, so a deployment whose anchor was deleted
		# underneath it is one odd-looking row rather than a register that refuses
		# to open. That module says why the case is real.
		"geo_path": geo_path(deployment.geo_node),
		"status": deployment.status,
		"is_open": is_open(deployment),
		"start_date": deployment.start_date,
		"end_date": deployment.end_date,
		"volunteers_required": deployment.volunteers_required or 0,
		"email_template": deployment.email_template,
		# Who is actually going: Assigned plus Accepted. The name is kept from
		# when the roster was a child table, because every screen and every test
		# reads it and renaming it would buy nothing.
		"participant_count": tally["on_deployment"],
		# The rest of the register in the same breath, so a listing row can say
		# "4 of 6, 3 still to answer" without a second call.
		"assignment_counts": tally,
		"places_left": max(frappe.utils.cint(deployment.volunteers_required) - tally["on_deployment"], 0)
		if frappe.utils.cint(deployment.volunteers_required) > 0
		else None,
	}


def deployment_dto(deployment) -> dict:
	"""Everything about one deployment: its terms, its period, and who is on it."""
	from vmmsx.deployment.services import assignment, terms

	return {
		**status_dto(deployment),
		"terms": terms.dto(deployment.terms_of_reference),
		# The whole assignment register, settled rows included: a coordinator
		# looking at a deployment needs to see who declined as much as who
		# accepted, or they will ask the same person again next week.
		"participants": assignment.roster_of(deployment.name),
		"leader": assignment.leader_of(deployment.name),
		"notes": deployment.notes,
	}
