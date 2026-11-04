# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A volunteer asking to move, and the two branches deciding it.

`transfer.py` is what a transfer *is* — one field moves, and only when the
predicate says so. This is how one is asked for and who hears about it:

- **The volunteer asks**, from their portal, with where and why
  (`request_mine`). It is raised as theirs — `requested_by_volunteer` — dated
  today, and goes to their own branch first.
- **The branch they are leaving releases them**, then **the branch they are
  joining accepts them**. That is the society's approval workflow for the
  doctype: two stages, the second routed from `to_geo_node`
  (`VMMS Approval Stage.anchor_field`). Nothing here names a stage.
- **A coordinator who raises one has already released them.** Raising a
  transfer is the release, so asking the same person to approve it again would
  be a form for nothing: `release_by_raiser` records that decision for them,
  and the transfer goes straight to the branch it is moving somebody to.
- **It takes effect on the last approval.** A volunteer's request carries
  today's date, so `transfer.try_apply` moves them the moment it is settled.

The volunteer is written to three times at most: when it is received, and when
it is approved or declined (`notifications/seeds/transfer_emails.py`). Moving
from the first branch to the second sends nothing; they are waiting either way.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, now_datetime, today

from vmmsx.approvals import states
from vmmsx.approvals.services import contract
from vmmsx.deployment.services import transfer as transfer_service

TRANSFER_DOCTYPE = transfer_service.TRANSFER_DOCTYPE
VOLUNTEER_DOCTYPE = transfer_service.VOLUNTEER_DOCTYPE

#: Who may ask to move themselves. A suspended volunteer's placement is a
#: matter between them and their branch, not a form.
MAY_REQUEST = ("Active",)


# --- the volunteer --------------------------------------------------------


def requests_open() -> bool:
	"""May a volunteer ask to move from their portal on this site?

	Only where a transfer is decided by somebody. A society that applies
	transfers directly — the shipped default, and any site that chose `routed`
	but has no transfer workflow yet — would move a volunteer the moment they
	pressed the button, so the button is not offered and the request refused.
	"""
	from vmmsx.deployment.services import approval

	if transfer_service.mode() != approval.MODE_ROUTED:
		return False

	return approval.has_workflow(TRANSFER_DOCTYPE)


def my_volunteer(user: str | None = None) -> str | None:
	"""The caller's own volunteer record, or None."""
	user = user or frappe.session.user

	if not user or user == "Guest":
		return None

	profile = frappe.db.get_value("Red Profile", {"user": user}, "name")

	if not profile:
		return None

	return frappe.db.get_value(VOLUNTEER_DOCTYPE, {"red_profile": profile}, "name")


def request_mine(to_geo_node: str, reason: str) -> dict:
	"""Raise the caller's own transfer request. Returns where it stands.

	**Raised as the system, and this is why that is safe.** A volunteer holds no
	permission on the transfer register and should not: what they may ask for is
	exactly one thing — their own move — and everything about it is fixed here
	rather than taken from them. The volunteer is the caller's, the origin is
	snapshotted from their record, the date is today, and the reason is theirs.
	The transfer's own `validate` still runs: a move to the same branch, to a
	place volunteers cannot be placed, or alongside another open transfer is
	refused exactly as it would be for a coordinator.
	"""
	from vmmsx import elevation

	volunteer = my_volunteer()

	if not volunteer:
		frappe.throw(
			_("Only a volunteer can ask to move branch."),
			frappe.PermissionError,
			title=_("Not a Volunteer"),
		)

	if frappe.db.get_value(VOLUNTEER_DOCTYPE, volunteer, "status") not in MAY_REQUEST:
		frappe.throw(
			_("Talk to your branch about moving. Your volunteer record is not active."),
			frappe.ValidationError,
			title=_("Cannot Request a Transfer"),
		)

	if not requests_open():
		frappe.throw(
			_("Ask your branch about moving. Transfers cannot be requested here yet."),
			frappe.ValidationError,
			title=_("Transfers Not Open"),
		)

	reason = (reason or "").strip()

	if not reason:
		frappe.throw(_("Say why you would like to move."), frappe.MandatoryError, title=_("No Reason"))

	transfer = frappe.get_doc(
		{
			"doctype": TRANSFER_DOCTYPE,
			"volunteer": volunteer,
			"to_geo_node": to_geo_node,
			"effective_date": today(),
			"reason": reason,
			"requested_by_volunteer": 1,
		}
	)
	transfer_service.snapshot_origin(transfer)

	with elevation.as_system():
		transfer.insert(ignore_permissions=True)
		transfer_service.submit(transfer)

	transfer.reload()
	tell_received(transfer)

	return summary(transfer)


def withdraw_mine(name: str) -> dict:
	"""Take back the caller's own request, while nobody has finished deciding it."""
	from vmmsx import elevation
	from vmmsx.approvals.services import engine

	transfer = frappe.get_doc(TRANSFER_DOCTYPE, name) if frappe.db.exists(TRANSFER_DOCTYPE, name) else None

	if not transfer or transfer.volunteer != my_volunteer():
		frappe.throw(_("That is not one of your transfers."), frappe.PermissionError, title=_("Not Yours"))

	if transfer.transfer_status != transfer_service.STATUS_PENDING:
		frappe.throw(
			_("This transfer has already been decided."), frappe.ValidationError, title=_("Already Decided")
		)

	with elevation.as_system():
		if states.is_open(contract.state(transfer)):
			engine.withdraw(transfer, _("Withdrawn by the volunteer."))
			transfer.reload()

		transfer_service.cancel(transfer, _("Withdrawn by the volunteer."))

	return summary(transfer)


def mine() -> dict | None:
	"""The caller's open transfer, or the last one decided in the past month."""
	volunteer = my_volunteer()

	if not volunteer:
		return None

	rows = frappe.get_all(
		TRANSFER_DOCTYPE,
		filters={"volunteer": volunteer},
		fields=["name", "transfer_status", "modified"],
		order_by="creation desc",
		limit=1,
	)

	if not rows:
		return None

	row = rows[0]

	if row.transfer_status != transfer_service.STATUS_PENDING and date_diff(today(), getdate(row.modified)) > 30:
		return None

	return summary(frappe.get_doc(TRANSFER_DOCTYPE, row.name))


# --- the coordinator ------------------------------------------------------


def release_by_raiser(transfer, user: str | None = None) -> None:
	"""Record the raiser's release, where they are the one the first stage asks.

	A coordinator who raised the transfer has released the volunteer by raising
	it. Recorded through the engine as an ordinary decision by them, so the
	audit trail says who released whom and when, and the transfer moves on to
	the branch it is moving somebody to. Somebody who raised it but is not the
	first stage's approver — an administrator, say — leaves the stage to its
	approver like any other.
	"""
	from vmmsx.approvals.services import config, engine

	user = user or frappe.session.user
	transfer.reload()

	if contract.state(transfer) != states.IN_REVIEW:
		return

	workflow = config.optional(TRANSFER_DOCTYPE)
	first = config.stages(workflow)[0] if workflow and config.stages(workflow) else None

	if not first or contract.stage(transfer) != first.name:
		return

	if not engine.may_act(transfer, user, workflow):
		return

	engine.decide(transfer, states.DECISION_APPROVED, _("Raised by the branch."), user=user)
	transfer.reload()


def for_volunteer(volunteer: str, user: str) -> dict:
	"""What a coordinator looking at one volunteer may do about moving them.

	`can_raise` is the same answer the transfer's own permission gives a new
	record anchored where this volunteer is today: the caller holds the transfer
	role at or above their branch, and may create transfers at all. A volunteer
	with a transfer already open gets that transfer back instead, because a
	second one would be refused.
	"""
	from vmmsx import multi_anchor

	home, status = frappe.db.get_value(VOLUNTEER_DOCTYPE, volunteer, ["home_geo_node", "status"]) or (None, None)
	open_name = frappe.db.get_value(
		TRANSFER_DOCTYPE, {"volunteer": volunteer, "transfer_status": transfer_service.STATUS_PENDING}, "name"
	)
	nodes = multi_anchor.reach(TRANSFER_DOCTYPE, user)
	covers = nodes is None or home in nodes

	return {
		"branch": home,
		"can_raise": bool(
			home
			and status in MAY_REQUEST
			and not open_name
			and covers
			and frappe.has_permission(TRANSFER_DOCTYPE, ptype="create", user=user)
		),
		# Whether a raised transfer goes to the other branch for approval, or
		# simply takes effect on its date. The form says which.
		"approved_by_branches": requests_open(),
		"transfer": summary(frappe.get_doc(TRANSFER_DOCTYPE, open_name)) if open_name and covers else None,
	}


def direction_filters(direction: str, nodes: set[str] | None) -> dict:
	"""Outgoing: leaving the caller's branches. Incoming: joining them."""
	field = "to_geo_node" if direction == "incoming" else "from_geo_node"

	if nodes is None:
		return {}

	return {field: ("in", sorted(nodes) or [""])}


def rows_for(user: str, direction: str, show: str = "open") -> list[dict]:
	"""The caller's transfers in one direction, as console rows.

	`get_list`, so the transfer's own scoping (`vmmsx/multi_anchor.py`) applies on
	top of the direction: nobody is shown a transfer they could not open.
	"""
	from vmmsx.approvals.services import engine
	from vmmsx import multi_anchor

	filters = direction_filters(direction, multi_anchor.reach(TRANSFER_DOCTYPE, user))

	if show == "open":
		filters["transfer_status"] = transfer_service.STATUS_PENDING
	else:
		filters["transfer_status"] = ("!=", transfer_service.STATUS_PENDING)

	names = frappe.get_list(
		TRANSFER_DOCTYPE,
		filters=filters,
		pluck="name",
		order_by="creation desc" if show == "open" else "modified desc",
		limit=200,
	)

	rows = []

	for name in names:
		transfer = frappe.get_doc(TRANSFER_DOCTYPE, name)
		row = summary(transfer)
		row["can_act"] = states.is_open(contract.state(transfer)) and engine.may_act(transfer, user)
		rows.append(row)

	return rows


# --- what a transfer looks like on a screen -------------------------------


def summary(transfer) -> dict:
	"""One transfer, as both the volunteer and the console show it."""
	from vmmsx.places import place_name
	from vmmsx.volunteer.services import identity

	state = contract.state(transfer)
	volunteer = frappe.get_doc(VOLUNTEER_DOCTYPE, transfer.volunteer)

	return {
		"name": transfer.name,
		"volunteer": transfer.volunteer,
		"volunteer_name": identity.display_name(volunteer),
		"from_geo_node": transfer.from_geo_node,
		"from_place": place_name(transfer.from_geo_node),
		"to_geo_node": transfer.to_geo_node,
		"to_place": place_name(transfer.to_geo_node),
		"reason": transfer.reason or "",
		"effective_date": str(transfer.effective_date) if transfer.effective_date else None,
		"requested_by_volunteer": bool(transfer.get("requested_by_volunteer")),
		"requested_on": str(transfer.creation)[:10] if transfer.creation else None,
		"transfer_status": transfer.transfer_status,
		"approval_state": state,
		"waiting_on": _waiting_on(transfer),
		"days_waiting": _days_at_stage(transfer),
		"decision_reason": _last_reason(transfer),
		"is_effective": transfer.transfer_status == transfer_service.STATUS_EFFECTIVE,
		"can_withdraw": transfer.transfer_status == transfer_service.STATUS_PENDING,
	}


def _waiting_on(transfer) -> str:
	"""The place whose decision this transfer is waiting for, by its own name."""
	from vmmsx.approvals.services import config
	from vmmsx.places import place_name

	if contract.state(transfer) != states.IN_REVIEW:
		return ""

	workflow = config.optional(TRANSFER_DOCTYPE)
	stage = config.stage_by_name(workflow, contract.stage(transfer)) if workflow else None

	if not stage:
		return ""

	return place_name(config.stage_anchor(transfer, workflow, stage))


def _days_at_stage(transfer) -> int:
	entered = transfer.get(contract.STAGE_ENTERED_FIELD)

	if not entered or transfer.transfer_status != transfer_service.STATUS_PENDING:
		return 0

	return max(date_diff(now_datetime(), entered), 0)


def _last_reason(transfer) -> str:
	rows = transfer.get("approval_decisions") or []

	return (rows[-1].get("reason") or "") if rows else ""


# --- what the volunteer is told -------------------------------------------


def tell_received(transfer) -> None:
	"""The acknowledgement, sent once by whoever raised it, after any release.

	Sent from the request rather than from a state change, because the state a
	coordinator's transfer passes through on its way to the second branch would
	otherwise say "your branch will review it first" about a release already
	given. A transfer that took effect at once — a society with no approval for
	transfers — is told it was approved instead, by `on_update`.
	"""
	if transfer.transfer_status != transfer_service.STATUS_PENDING:
		return

	from vmmsx.notifications.seeds import transfer_emails

	_send(transfer, transfer_emails.REQUESTED)


def on_update(transfer, previous) -> None:
	"""Tell the volunteer when their transfer is approved or declined.

	Driven by the change, never the verb: `previous` is the document as it was
	loaded before this save. Approved is said once — when the approval lands, or,
	where the society approves no transfers, when it takes effect.
	"""
	from vmmsx.notifications.seeds import transfer_emails

	was_state = previous.get(contract.STATE_FIELD) if previous else None
	was_status = previous.get("transfer_status") if previous else None
	state = contract.state(transfer)

	if state != was_state and state == states.APPROVED:
		_send(transfer, transfer_emails.APPROVED)
	elif state != was_state and state == states.REJECTED:
		_send(transfer, transfer_emails.DECLINED)
	elif (
		transfer.transfer_status == transfer_service.STATUS_EFFECTIVE
		and was_status != transfer_service.STATUS_EFFECTIVE
		and state not in (states.APPROVED,)
	):
		# Moved without an approval cycle: the society handles transfers directly.
		_send(transfer, transfer_emails.APPROVED)


def _send(transfer, template: str) -> None:
	"""Render and queue one message. Never raises: see `lifecycle.notify`.

	Once per message per document in hand: taking effect saves the transfer a
	second time inside the save that settled it, and both ask.
	"""
	told = transfer.flags.setdefault("vmms_transfer_told", set())

	if template in told:
		return

	told.add(template)

	try:
		from frappe.email.doctype.email_template.email_template import get_email_template
		from frappe.utils import get_url

		from vmmsx.notifications.services import branding
		from vmmsx.places import place_name
		from vmmsx.volunteer.services import identity

		if not frappe.db.exists("Email Template", template):
			return

		volunteer = frappe.get_doc(VOLUNTEER_DOCTYPE, transfer.volunteer)
		person = identity.read(volunteer, ("email",))
		recipient = (person.get("email") or "").strip()

		if not recipient:
			return

		rendered = get_email_template(
			template,
			{
				"holder_name": identity.display_name(volunteer),
				"record_id": transfer.name,
				"from_place": place_name(transfer.from_geo_node),
				"to_place": place_name(transfer.to_geo_node),
				"raised_by_branch": not transfer.get("requested_by_volunteer"),
				"effective_date": frappe.utils.formatdate(transfer.effective_date) if transfer.effective_date else "",
				"is_effective": transfer.transfer_status == transfer_service.STATUS_EFFECTIVE,
				"reason": _last_reason(transfer),
				"portal_url": get_url("/portal/profile"),
				"society_name": branding.lockup().get("brand_name") or "",
			},
		)

		frappe.sendmail(
			recipients=[recipient],
			subject=rendered["subject"],
			message=rendered["message"],
			now=False,
			reference_doctype=transfer.doctype,
			reference_name=transfer.name,
		)
	except Exception:
		frappe.log_error(title="vmmsx: could not send a transfer email", message=frappe.get_traceback())
