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

Idempotent by construction — `assignment.sync` sets the assignee list to exactly
the authorised set, so a second run is a no-op and a stale assignee is removed
rather than left behind.

Runs from `after_migrate`, because the thing that invalidates a queue is a
society changing who holds a role where, and a deploy is the one moment this app
is guaranteed to get to look. It is also what
`patches/repair_approval_routing.py` calls after placing the missing approver.
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


def resync_pending(doctype: str | None = None) -> dict:
	"""Re-assign every pending approval to whoever the gate admits today.

	Returns doctype -> number of documents whose assignment changed, so a
	migrate that repaired something says so and one that found nothing in need
	of repair is visibly quiet.
	"""
	governed = [doctype] if doctype else config.governed_doctypes()
	report: dict[str, int] = {}

	for name in governed:
		if not frappe.db.exists("DocType", name):
			continue

		changed = 0

		for row in _pending(name):
			if _resync_one(name, row):
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


def _resync_one(doctype: str, name: str) -> bool:
	"""One document. Answers whether the assignment actually moved.

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
