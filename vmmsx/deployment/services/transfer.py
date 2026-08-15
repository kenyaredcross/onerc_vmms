# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Branch transfer — one field moves, and nothing else does.

A volunteer moves from one branch to another. The whole of what that means, in
this app, is that `VMMS Volunteer.home_geo_node` stops naming one Geo Node and
starts naming another. `_move_placement()` below is the only write in this
module, and it writes that one field.

History is not rewritten
------------------------

This is the rule the module is built around, so it is worth stating as a
consequence rather than as an intention: **there is no code here that touches a
deployment, a time log or a certification, and there is no code anywhere else
that rewrites one when a volunteer moves.** A volunteer who served at their old
branch served at their old branch. Their past deployments keep the Geo Node they
were run at, their time logs keep the Geo Node the time was served at, and their
certifications are not about a place at all. What changes is where the volunteer
is *now*.

The access consequence falls out of core's scope model with no special code:

* the old branch keeps seeing the records anchored beneath it, because geo scope
  is a question about **a record's own anchor** and those anchors did not move;
* the new branch sees the volunteer, because the volunteer's anchor is the one
  thing that did;
* the old branch stops seeing the volunteer as one of theirs, for the same
  reason and at the same instant.

Nothing had to be written to make that true, and that is the argument for
storing a placement in exactly one place.

What a society decides, and what this module decides
----------------------------------------------------

**Whether a transfer needs authorising is configuration**, read from
`vmms_transfer_approval_mode` and dispatched through
`deployment/services/approval.py` — the same two tables a deployment request
uses. Empty configuration is the direct mode, so a site upgrading into this
module does not discover that every transfer now throws for want of a workflow
it has never been asked to create. The recommended posture is `routed`: moving a
volunteer between branches changes who can see them and who approves for them,
and that is a decision somebody should own.

**Where a routed transfer routes from is also configuration**, and it needs no
code here at all. The record is anchored on `from_geo_node` — the branch
currently responsible for the volunteer authorises their release — and a society
that would rather the receiving branch decide points its approval workflow's
`geo_node_field` at `to_geo_node`, which the engine already reads from
configuration.

**Applying is a predicate, not a sequence.** `try_apply()` asks four questions,
all answered from the record: is it still pending, is its approval settled, has
its effective date arrived, and is the volunteer still where this transfer says
they were. It is therefore safe to call after any event and in any order, and
the daily sweep that catches a future-dated transfer is the same function.
"""

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, today

from vmmsx.deployment.services import approval, society

TRANSFER_DOCTYPE = "VMMS Branch Transfer"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"

STATUS_PENDING = "Pending"
STATUS_EFFECTIVE = "Effective"
STATUS_CANCELLED = "Cancelled"

STATUSES = (STATUS_PENDING, STATUS_EFFECTIVE, STATUS_CANCELLED)

APPLICATION_FLAG = "vmms_transfer_applying"

# Named so the report and the tests assert on a fact rather than on prose.
HISTORY_RULE = (
	"A transfer changes the volunteer's home_geo_node and nothing else. Past deployments, time"
	" logs and certifications keep the geo anchors they were saved with, because the volunteer"
	" was there when they were made. The old branch therefore keeps seeing those records under"
	" geo scoping, and the new branch sees the volunteer as current, without either outcome"
	" needing code: both follow from scope being a question about a record's own anchor."
)


def mode() -> str:
	"""The approval mode this society applies to branch transfers."""
	return society.transfer_approval_mode()


def _where() -> str:
	"""What a refusal about the mode should name: the setting, not the record."""
	return society.TRANSFER_APPROVAL_MODE_FIELD


# --- creation -------------------------------------------------------------


def snapshot_origin(transfer) -> None:
	"""Fill `from_geo_node` from the volunteer. Called from `before_insert`.

	Snapshotted rather than typed so that a transfer records where somebody
	actually was, not where whoever raised it believed they were. Read-only
	afterwards, which is what keeps a completed transfer a record of where they
	came from.
	"""
	if transfer.from_geo_node:
		return

	if not transfer.volunteer:
		frappe.throw(
			_("A branch transfer moves a volunteer. Name one."),
			frappe.MandatoryError,
			title=_("No Volunteer"),
		)

	transfer.from_geo_node = frappe.db.get_value(VOLUNTEER_DOCTYPE, transfer.volunteer, "home_geo_node")


def validate(transfer) -> None:
	"""Everything a transfer must satisfy. Called from the controller's `validate`."""
	assert_status(transfer.transfer_status)
	_assert_is_a_move(transfer)
	_assert_destination_allowed(transfer)
	_assert_no_other_pending(transfer)


def assert_status(status: str | None) -> None:
	if status in STATUSES:
		return

	frappe.throw(
		_("{0} is not a transfer status. Expected one of: {1}.").format(
			frappe.bold(status), ", ".join(STATUSES)
		),
		frappe.ValidationError,
		title=_("Unknown Transfer Status"),
	)


def _assert_is_a_move(transfer) -> None:
	"""A transfer from somewhere to the same somewhere is not a transfer.

	Refused rather than treated as a no-op: saved, it would sit in the register
	looking like a move that happened, and it would route to an approver who has
	nothing to decide.
	"""
	if not transfer.to_geo_node:
		frappe.throw(
			_("A branch transfer needs somewhere to move the volunteer to."),
			frappe.MandatoryError,
			title=_("No Destination"),
		)

	if transfer.from_geo_node != transfer.to_geo_node:
		return

	from onerc_core.geo.services import adapter

	frappe.throw(
		_("{0} is already at {1}. A transfer moves somebody somewhere else.").format(
			frappe.bold(transfer.volunteer), frappe.bold(adapter.get_full_path(transfer.to_geo_node))
		),
		frappe.ValidationError,
		title=_("Not A Move"),
	)


def _assert_destination_allowed(transfer) -> None:
	"""The destination must satisfy the rule a volunteer's placement always did.

	Asked of the **Volunteer** module's own setting, not of a second one here.
	Where a volunteer may be placed is one question with one answer, and two
	settings meaning it would let a transfer put somebody somewhere they could
	not have been registered.
	"""
	from vmmsx.volunteer.services import society as volunteer_society

	volunteer_society.assert_anchor_level(transfer.to_geo_node)


def _assert_no_other_pending(transfer) -> None:
	"""One open transfer per volunteer.

	Two would each have snapshotted the same origin and would each expect to move
	the volunteer from it. Whichever applied second would either move somebody
	who had already moved, or be refused by the origin check and sit there
	looking unexplained. Refusing the second at creation says why, once.
	"""
	if transfer.transfer_status != STATUS_PENDING:
		return

	other = frappe.db.exists(
		TRANSFER_DOCTYPE,
		{
			"volunteer": transfer.volunteer,
			"transfer_status": STATUS_PENDING,
			"name": ("!=", transfer.name),
		},
	)

	if not other:
		return

	frappe.throw(
		_(
			"{0} already has an open branch transfer, {1}. Cancel or complete that one before"
			" raising another: two open transfers would each expect to move the volunteer from"
			" where they are today, and only one of them could."
		).format(frappe.bold(transfer.volunteer), frappe.bold(other)),
		frappe.ValidationError,
		title=_("Transfer Already Open"),
	)


# --- submission -----------------------------------------------------------


def submit(transfer) -> dict:
	"""Put a transfer into motion, then see whether it takes effect at once.

	Idempotent. A transfer already in review is handed back to the engine, which
	re-syncs the queue rather than restarting review; one already applied is left
	alone by the predicate.
	"""
	approval.begin(transfer, mode(), _where())

	applied = try_apply(transfer)

	return applied or status(transfer)


# --- applying -------------------------------------------------------------


def is_settled(transfer) -> bool:
	"""Has this transfer's approval requirement been met?"""
	return approval.is_settled(transfer, mode(), _where())


def is_due(transfer, on_date=None) -> bool:
	"""Has the effective date arrived?"""
	return getdate(transfer.effective_date) <= getdate(on_date or today())


def origin_still_holds(transfer) -> bool:
	"""Is the volunteer still where this transfer says they were?

	A transfer moves somebody *from* a named branch. If they have since been
	moved by something else, applying it anyway would move them from a place they
	are no longer in, which is the kind of silent overwrite this app refuses
	everywhere else. It is not an error state; it is a transfer that has been
	overtaken and needs a human to look at it.
	"""
	current = frappe.db.get_value(VOLUNTEER_DOCTYPE, transfer.volunteer, "home_geo_node")

	return current == transfer.from_geo_node


def is_applicable(transfer, on_date=None) -> bool:
	"""Should this transfer move the volunteer now?

	Four questions, all answered from the record and from configuration. None of
	them is about which code path ran, which is what makes this safe to ask after
	any event and in any order.
	"""
	if transfer.transfer_status != STATUS_PENDING or transfer.applied_on:
		return False

	if approval.is_refused(transfer):
		return False

	return is_settled(transfer) and is_due(transfer, on_date) and origin_still_holds(transfer)


def try_apply(transfer, on_date=None) -> dict | None:
	"""Move the placement if the predicate holds. Returns the DTO, or None.

	The single entry point. Idempotent: a transfer that has already been applied
	fails the predicate on its own `applied_on` stamp and returns None.
	"""
	if not is_applicable(transfer, on_date):
		return None

	return apply_transfer(transfer)


def apply_transfer(transfer) -> dict:
	"""Make it real. One field on one other record, and a note of what was in flight.

	The comment is written because a transfer taking effect while somebody is in
	the middle of a deployment is the one situation where a coordinator at either
	end needs to know without being told twice. **It changes nothing**: the
	deployment keeps its own anchor and its own roster, and the volunteer stays on
	it, because they are on it. Whether a society wants a mid-deployment transfer
	to be refused, deferred to the deployment's end, or simply recorded is a
	policy nobody has chosen, and recording it is the only one of the three that
	does not invent a rule.
	"""
	in_flight = in_flight_deployments(transfer)

	_move_placement(transfer)

	transfer.transfer_status = STATUS_EFFECTIVE
	transfer.applied_on = now_datetime()
	_save(transfer)

	if in_flight:
		transfer.add_comment(
			"Comment",
			_(
				"Applied while {0} was deployed on {1}. Those deployments are unchanged: they keep"
				" the place they were run at, and the volunteer stays on their rosters."
			).format(transfer.volunteer, ", ".join(in_flight)),
		)

	return status(transfer)


def _move_placement(transfer) -> None:
	"""The one write this module makes.

	**It bypasses permissions, and this is the justification.** The path runs as
	whoever recorded the approval, or as the scheduler for a transfer whose
	effective date arrived overnight. An approver holds no write permission on
	the volunteer register and should not need any in order to approve a
	transfer; the scheduler is nobody at all. The permission that matters was
	checked when the transfer was created, and again by the engine's person-gate
	before the decision was accepted where a society routes them.

	Saved through the document rather than with `db.set_value` so that the
	volunteer's own ACC-02 and ACC-03 rules run: a transfer may not put somebody
	somewhere they could not have been registered, and the check that says so is
	the volunteer controller's, not a copy of it here.
	"""
	volunteer = frappe.get_doc(VOLUNTEER_DOCTYPE, transfer.volunteer)
	volunteer.home_geo_node = transfer.to_geo_node
	volunteer.save(ignore_permissions=True)


def in_flight_deployments(transfer, on_date=None) -> list[str]:
	"""Open deployments this volunteer is on that are running right now.

	Reported, never acted on. See `apply_transfer`.
	"""
	from vmmsx.deployment.services import deployment as deployment_service
	from vmmsx.deployment.services import participation

	running = []

	for name in participation.deployments_of(transfer.volunteer):
		deployment = frappe.get_cached_doc(deployment_service.DEPLOYMENT_DOCTYPE, name)

		if deployment_service.in_flight(deployment, on_date):
			running.append(name)

	return running


# --- cancelling -----------------------------------------------------------


def cancel(transfer, reason: str | None = None) -> dict:
	"""Call a transfer off. Idempotent, and refused once it has taken effect.

	A transfer that has already moved somebody is not cancellable, because
	cancelling it would have to move them back, and moving somebody back is
	another transfer with its own reason and its own approval rather than the
	undoing of this one.
	"""
	if transfer.transfer_status == STATUS_CANCELLED:
		return status(transfer)

	if transfer.applied_on:
		frappe.throw(
			_(
				"This transfer has already moved {0} to {1} and cannot be cancelled. Raise a"
				" transfer back if they should return: moving somebody is an act with its own"
				" reason, not the undoing of another one."
			).format(frappe.bold(transfer.volunteer), frappe.bold(transfer.to_geo_node)),
			frappe.ValidationError,
			title=_("Transfer Already Effective"),
		)

	transfer.transfer_status = STATUS_CANCELLED
	_save(transfer)
	transfer.add_comment("Comment", _("Cancelled. {0}").format(reason or ""))

	return status(transfer)


# --- the sweep ------------------------------------------------------------


def apply_due(on_date=None) -> dict:
	"""Apply every pending transfer whose day has come. Scheduled daily, idempotent.

	A transfer arranged for next month sits Pending until next month; nothing
	else would notice the date arriving. Running this twice in a day moves nobody
	twice, because `try_apply` reads the record rather than remembering what this
	sweep did.

	A transfer that has been overtaken — the volunteer moved by something else
	since it was raised — is counted as `overtaken` rather than skipped silently.
	It needs a person to look at it, and a sweep that said nothing would leave it
	sitting Pending forever with no signal.
	"""
	summary = {"checked": 0, "applied": 0, "overtaken": 0}

	pending = frappe.get_all(TRANSFER_DOCTYPE, filters={"transfer_status": STATUS_PENDING}, pluck="name")

	for name in pending:
		transfer = frappe.get_doc(TRANSFER_DOCTYPE, name)
		summary["checked"] += 1

		if try_apply(transfer, on_date):
			summary["applied"] += 1
		elif is_settled(transfer) and is_due(transfer, on_date) and not origin_still_holds(transfer):
			summary["overtaken"] += 1
			frappe.logger().warning(
				f"vmmsx: branch transfer {name} was not applied because {transfer.volunteer} is no"
				f" longer at {transfer.from_geo_node}; it needs a person to look at it"
			)

	return summary


# --- the lifecycle hook ---------------------------------------------------


def on_update(transfer, method=None) -> None:
	"""Re-evaluate the transfer after any save. Called from the controller.

	This is how an approval decision recorded by the engine moves a volunteer
	without the engine knowing that placements exist. The flag stops the save
	inside `apply_transfer()` from re-entering.
	"""
	if transfer.flags.get(APPLICATION_FLAG):
		return

	try_apply(transfer)


def _save(transfer) -> None:
	"""Persist an application-path change without re-entering `on_update`."""
	transfer.flags[APPLICATION_FLAG] = True

	try:
		# `transfer_status` and `applied_on` are service-written and read-only to
		# users, and this runs on paths with no interactive session at all: the
		# daily sweep is the ordinary case. The permission that matters was
		# checked when the transfer was created.
		transfer.save(ignore_permissions=True)
	finally:
		transfer.flags[APPLICATION_FLAG] = False


# --- the DTO --------------------------------------------------------------


def status(transfer) -> dict:
	"""Where a transfer stands, as an explicit dict. Built field by field."""
	from onerc_core.geo.services import adapter

	configured = mode()

	return {
		"name": transfer.name,
		"volunteer": transfer.volunteer,
		"from_geo_node": transfer.from_geo_node,
		"from_geo_path": adapter.get_full_path(transfer.from_geo_node) if transfer.from_geo_node else None,
		"to_geo_node": transfer.to_geo_node,
		"to_geo_path": adapter.get_full_path(transfer.to_geo_node) if transfer.to_geo_node else None,
		"effective_date": transfer.effective_date,
		"transfer_status": transfer.transfer_status,
		"applied_on": transfer.applied_on,
		"is_effective": transfer.transfer_status == STATUS_EFFECTIVE,
		"approval_mode": configured,
		"requires_approver": approval.requires_approver(configured, _where()),
		"approval_settled": is_settled(transfer),
		"is_refused": approval.is_refused(transfer),
		"origin_still_holds": origin_still_holds(transfer),
	}


def approval_dto(transfer, user: str | None = None) -> dict | None:
	"""The engine's own view of this transfer's approval, or None where there is none."""
	from vmmsx.approvals.services import config, engine

	if not approval.requires_approver(mode(), _where()):
		return None

	if not config.is_approvable(transfer.doctype):
		return None

	return engine.status(transfer, user)
