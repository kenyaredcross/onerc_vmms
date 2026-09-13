# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Put the queue back in step with who may actually act.

**Authority and visibility are separate, and only one of them is live.**
`engine.authorised` recomputes from Geo Assignment on every call, deliberately —
an approver who lost their assignment last week cannot approve today. But
`api/approvals.py::my_queue` starts from the caller's own ToDos, and a ToDo is
written once, when a stage is entered. So an application submitted while nobody
held the role resolved nobody, was assigned to nobody, and kept that emptiness
after somebody was finally given the role: the gate would have admitted them,
and the queue never showed them the document.

That is not a hypothetical. A society whose approvers were placed at one rung
while its workflow resolved at another had every application outside that one
branch land unassigned, and granting the role afterwards did not surface a
single one of them.

**This is the re-ask.** For every governed document still awaiting a decision it
recomputes `authorised` and syncs the assignment to match. It changes no state,
records no decision and grants nobody anything: authority is whatever Geo
Assignment already says, and this only makes the inbox agree with it.

**And the other half of the same question.** An application can now be accepted
before its workflow is written — `engine.park` holds it at Submitted with no
stage rather than turning an applicant away over configuration they cannot
write — so this sweep also *routes* those, the moment there is a workflow to
route them through. Same list, same question asked at a different moment: who
should be looking at this right now.

Idempotent by construction — `assignment.sync` sets the assignee list to exactly
the authorised set, so a second run is a no-op and a stale assignee is removed
rather than left behind.

Runs from `after_migrate`, because the thing that invalidates a queue is a
society changing who holds a role where, and a deploy is the one moment this app
is guaranteed to get to look.
"""

import frappe

from vmmsx.approvals import states
from vmmsx.approvals.services import assignment as assignment_service
from vmmsx.approvals.services import config, contract, engine

# The states in which a document is still waiting for somebody to act. Taken
# from `states.py` rather than written out, so a state added there is accounted
# for here instead of quietly falling out of every queue.
PENDING = (states.SUBMITTED, states.IN_REVIEW)


def on_authority_changed(doc=None, method: str | None = None) -> None:
	"""Somebody's authority moved, so the queues built from it are now stale.

	**This is the standing answer to "it happened once, make it never happen
	again".** Authority is recomputed on every call, so the *gate* is correct the
	instant a Geo Assignment is saved. The **queue** is not: it is built from
	ToDos, and a ToDo is written once, when a stage is entered. So an approver
	appointed after an application was submitted could act on it and could not
	see it — which is the worst shape a permission bug can take, because
	everything looks configured and nothing looks wrong.

	Re-syncing on migrate closed it for a deploy and left it open for every
	appointment made between deploys. Hanging it off the assignment itself is
	what closes it for good: appoint somebody, and the applications they can now
	decide arrive in their queue.

	**Enqueued rather than run inline.** Saving a Geo Assignment is core's act,
	not this app's, and it must not slow down or fail because a queue somewhere
	needed rebuilding. `enqueue` also means the work happens after the commit, so
	it recomputes against the authority that was actually saved.
	"""
	frappe.enqueue(
		"vmmsx.approvals.services.repair.resync_pending",
		queue="short",
		# One rebuild per assignment saved is plenty; a coordinator adding five
		# rows in a row should not queue five sweeps of the same documents.
		job_id="vmmsx-resync-pending",
		deduplicate=True,
		enqueue_after_commit=True,
	)


def on_workflow_saved(doc=None, method: str | None = None) -> None:
	"""A society has just written the workflow its applications were waiting for.

	**Applications can arrive before a workflow does.** `engine.park` accepts
	them — Submitted, routed to nobody — because a site is live from the day it
	is installed and configuring who signs off on what happens on an
	administrator's own timetable. This is the other end of that: the moment the
	workflow exists, everything held against it is routed and lands in the queue
	of whoever it resolves to.

	Enqueued, after the commit, for the same reasons `on_authority_changed`
	gives: saving configuration must not slow down or fail because a sweep
	wanted running, and the sweep must see the workflow that was actually saved.
	"""
	governed = (doc.workflow_for if doc else None) or None

	frappe.enqueue(
		"vmmsx.approvals.services.repair.resync_pending",
		queue="short",
		job_id=f"vmmsx-resync-pending-{governed or 'all'}",
		deduplicate=True,
		enqueue_after_commit=True,
		doctype=governed,
	)


def resync_pending(doctype: str | None = None) -> dict:
	"""Put every pending approval where it belongs today. Two repairs, one sweep.

	    parked     accepted before a workflow existed — Submitted, no stage.
	               Routed now, which is the submission the engine could not
	               perform at the time
	    routed     already in a stage. Re-assigned to whoever the gate admits
	               today, which is what a change of authority invalidates

	Both are read off the same pending list because they are the same question
	asked of documents at two different moments — *who should be looking at this
	right now* — and one sweep that answers it is easier to trust than two that
	could disagree about which documents it covers.

	Returns doctype -> number of documents it actually moved, so a migrate that
	repaired something says so and one that found nothing is visibly quiet.
	"""
	governed = [doctype] if doctype else config.governed_doctypes()
	report: dict[str, int] = {}

	for name in governed:
		if not frappe.db.exists("DocType", name):
			continue

		changed = 0

		for row in _pending(name):
			if _repair_one(name, row):
				changed += 1

		if changed:
			report[name] = changed

	return report


def _pending(doctype: str) -> list[str]:
	"""Documents of this doctype still awaiting a decision.

	`frappe.get_all` rather than `get_list`: this runs from a patch and from
	`after_migrate`, where there is no session whose scope should narrow a
	repair. It reads one field and writes no answer to a caller.
	"""
	field = contract.STATE_FIELD

	if not frappe.get_meta(doctype).has_field(field):
		return []

	return frappe.get_all(doctype, filters={field: ("in", PENDING)}, pluck="name")


def _repair_one(doctype: str, name: str) -> bool:
	"""One document, sent to whichever of the two repairs it needs.

	Parked is *Submitted with no stage*: the engine wrote that and nothing else
	does, because every other way into Submitted resolves to a stage inside the
	same transaction. It is the one shape that says "this was accepted and never
	routed".
	"""
	if _is_parked(doctype, name):
		return _route(doctype, name)

	return _resync_one(doctype, name)


def _is_parked(doctype: str, name: str) -> bool:
	"""Was this accepted before there was a workflow to route it through?"""
	fields = [contract.STATE_FIELD, contract.STAGE_FIELD]
	row = frappe.db.get_value(doctype, name, fields, as_dict=True)

	if not row:
		return False

	return row.get(contract.STATE_FIELD) == states.SUBMITTED and not row.get(contract.STAGE_FIELD)


def _route(doctype: str, name: str) -> bool:
	"""Put a parked application into review. Answers whether it moved.

	`engine.submit` is the whole of it: it already knows this case — a Submitted
	document with a workflow behind it is one it parked earlier — so the repair
	is simply the submission it could not perform at the time.

	**As the system, like every other write the engine makes on somebody's
	behalf.** This runs from a background job whose user is whoever saved the
	workflow or the assignment that triggered it, and that person holds no write
	permission on an applicant's registration — nor should they need one to have
	configured a workflow. The engine's own person-gate still governs every
	decision made afterwards; see `registration/services/intake.submit_once`,
	which elevates the identical write for the identical reason.

	Nothing here may raise, for the reason `_resync_one` gives: one application
	anchored at a level the new workflow forbids must not stop the rest from
	being routed, and the honest outcome for it is a log entry and a document
	that stays parked.
	"""
	from vmmsx import elevation

	try:
		with elevation.as_system():
			engine.submit(frappe.get_doc(doctype, name))
	except Exception:
		frappe.log_error(title=f"Approval routing failed for {doctype} {name}")

		return False

	# Asked again rather than assumed. The workflow could have gone away between
	# the sweep starting and this document being reached, in which case `submit`
	# parked it a second time and nothing moved — and a repair that counts work
	# it did not do is a report nobody can trust.
	return not _is_parked(doctype, name)


def _resync_one(doctype: str, name: str) -> bool:
	"""One document already in a stage. Answers whether the assignment actually moved.

	Nothing here may raise. A single malformed document — a stage deleted out of
	a workflow, an anchor pointing at a node somebody removed — must not take
	down a migrate for every other site on the bench, and the honest outcome for
	it is an untouched queue plus a log entry rather than a failed deploy.
	"""
	try:
		doc = frappe.get_doc(doctype, name)
		admitted = sorted(engine.authorised(doc)["approvers"])
	except Exception:
		frappe.log_error(title=f"Approval resync failed for {doctype} {name}")

		return False

	if not admitted:
		# Nobody is admitted, so there is nothing to route to. The assignment is
		# deliberately left alone: clearing it would take the document out of the
		# last approver's inbox to replace it with nothing, and a stale ToDo is
		# checked against routing before `my_queue` shows it anyway.
		return False

	if sorted(assignment_service.assignees(doctype, name)) == admitted:
		return False

	try:
		assignment_service.sync(doctype, name, admitted)
	except Exception:
		frappe.log_error(title=f"Approval reassignment failed for {doctype} {name}")

		return False

	return True
