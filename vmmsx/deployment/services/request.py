# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The deployment request lifecycle — submit, fulfil.

**Fulfilment is a predicate, not a sequence.** A request becomes a deployment
when two things are true: its approval requirement is settled, and it has not
become one already. Both are questions about the record and about
configuration, never about which code path happened to run, so `try_fulfil()` is
safe to call after any event and in any order. That is the same shape membership
activation and volunteer acceptance already have, and it is why the approval
engine can turn a request into a deployment without knowing deployments exist.

**Whether an approver is needed at all is the terms of reference's answer.**
`terms.approval_mode()` returns `direct` or `routed`, and
`deployment/services/approval.py` dispatches on it through two tables. Nothing
here compares a terms of reference to a name and nothing branches on a stage
label, which is what lets a society move one piece of work under an approval
without a line of code changing.

**What a fulfilled request creates, and what it deliberately does not.** It
creates the deployment: the terms, the place, the dates. It does **not** put
anybody on the roster. Who goes is a coordinator's judgement, informed by
`matching.candidates_for()` and made with facts this app does not hold, and a
request that quietly deployed the first N people who matched would be this
software deciding who serves.
"""

import frappe
from frappe import _

from vmmsx.deployment.services import approval, terms

REQUEST_DOCTYPE = "VMMS Deployment Request"
DEPLOYMENT_DOCTYPE = "VMMS Deployment"

FULFILMENT_FLAG = "vmms_request_fulfilling"


def mode_of(request) -> str:
	"""The approval mode governing this request, from its terms of reference."""
	return terms.approval_mode(request.terms_of_reference)


def _where(request) -> str:
	"""What a refusal about the mode should name: the terms, not the request."""
	return request.terms_of_reference


# --- submission -----------------------------------------------------------


def submit(request) -> dict:
	"""Put a request into motion, then see whether it can be fulfilled at once.

	Idempotent. Called twice, the second call restarts nothing: `approval.begin`
	hands an already-routed document back to the engine, which re-syncs the queue
	rather than restarting review, and `try_fulfil` sees the deployment already
	linked and does nothing.

	A `direct` request is fulfilled by this call, because nothing is owed on it.
	A `routed` one is handed to the engine and waits.
	"""
	terms.assert_offered(request.terms_of_reference)

	approval.begin(request, mode_of(request), _where(request))

	fulfilled = try_fulfil(request)

	return fulfilled or status(request)


# --- fulfilment -----------------------------------------------------------


def is_settled(request) -> bool:
	"""Has this request's approval requirement been met?"""
	return approval.is_settled(request, mode_of(request), _where(request))


def is_fulfillable(request) -> bool:
	"""Is there a deployment to create that has not been created already?"""
	if request.deployment:
		return False

	if approval.is_refused(request):
		return False

	return is_settled(request)


def try_fulfil(request) -> dict | None:
	"""Create the deployment if the predicate holds. Returns the DTO, or None.

	The single entry point for a request becoming a deployment. Idempotent: a
	request that has already produced one fails the predicate on its own
	`deployment` link and returns None.
	"""
	if not is_fulfillable(request):
		return None

	return fulfil(request)


def fulfil(request) -> dict:
	"""Make it real: one deployment, carrying the request's terms, place and dates.

	**The insert bypasses permissions, and this is the justification.** The
	caller that matters is the approval engine: this runs inside whichever
	approver recorded the decision, and an approver holds no create permission on
	the deployment register and should not need any in order to approve a
	request. The elevation is not a shortcut around a check, because the check
	already happened — in `engine.decide`, against the person this document
	routed to, and before that in the permission that let somebody raise the
	request at all. Nothing a caller supplied reaches a field that was not
	already validated on the request itself. A `direct` request reaches here from
	its own submitter, whose create permission on the request was checked
	normally.
	"""
	from vmmsx.deployment.services import deployment as deployment_service

	deployment = frappe.get_doc(
		{
			"doctype": DEPLOYMENT_DOCTYPE,
			"terms_of_reference": request.terms_of_reference,
			"geo_node": request.geo_node,
			"start_date": request.needed_from,
			"end_date": request.needed_until,
			"status": deployment_service.STATUS_PLANNED,
			# How many the request asked for becomes how many the deployment needs.
			# The request already carries the number and somebody already approved
			# it, so making a coordinator retype it on the deployment would be a
			# second chance for the two to disagree about the same authorised
			# figure. It stays editable afterwards: what was approved and what the
			# branch turns out to need are allowed to diverge, and the deployment's
			# own number is what the roster is capped against.
			"volunteers_required": frappe.utils.cint(request.volunteers_requested),
		}
	)
	deployment.insert(ignore_permissions=True)

	request.deployment = deployment.name
	_save(request)

	return status(request)


# --- the lifecycle hook ---------------------------------------------------


def on_update(request, method=None) -> None:
	"""Re-evaluate fulfilment after any save. Called from the controller.

	This is how a decision recorded by the approval engine becomes a deployment
	without the engine knowing deployments exist. The flag stops the save inside
	`fulfil()` from re-entering.
	"""
	if request.flags.get(FULFILMENT_FLAG):
		return

	try_fulfil(request)


def _save(request) -> None:
	"""Persist a fulfilment-path change without re-entering `on_update`."""
	request.flags[FULFILMENT_FLAG] = True

	try:
		# `deployment` is service-written and read-only to users, and this path
		# runs as whichever approver made the decision — somebody with no write
		# permission on the request and no need for any. The permission that
		# matters was checked when the request was created and again by the
		# engine's person-gate before the decision was accepted.
		request.save(ignore_permissions=True)
	finally:
		request.flags[FULFILMENT_FLAG] = False


# --- the DTO --------------------------------------------------------------


def status(request) -> dict:
	"""Where a request stands, as an explicit dict. Built field by field.

	Never the Document: that would leak every field on the record, including ones
	nobody reviewed, and turn every schema change into an API change.
	"""
	from onerc_core.geo.services import adapter

	mode = mode_of(request)

	return {
		"name": request.name,
		"terms_of_reference": request.terms_of_reference,
		"geo_node": request.geo_node,
		"geo_path": adapter.get_full_path(request.geo_node) if request.geo_node else None,
		"volunteers_requested": request.volunteers_requested,
		"needed_from": request.needed_from,
		"needed_until": request.needed_until,
		"approval_mode": mode,
		"requires_approver": approval.requires_approver(mode, _where(request)),
		"approval_settled": is_settled(request),
		"is_refused": approval.is_refused(request),
		"deployment": request.deployment,
		"is_fulfilled": bool(request.deployment),
	}


def approval_dto(request, user: str | None = None) -> dict | None:
	"""The engine's own view of this request's approval, or None where there is none.

	The engine builds it and decides for itself how much of the approver list
	this caller may see. A request whose terms ask for no approver has no
	approval to describe, and saying so is more honest than an empty shape that
	looks like one which has not started.
	"""
	from vmmsx.approvals.services import config, engine

	if not approval.requires_approver(mode_of(request), _where(request)):
		return None

	if not config.is_approvable(request.doctype):
		return None

	return engine.status(request, user)
