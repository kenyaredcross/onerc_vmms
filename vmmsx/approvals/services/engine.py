# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The engine — submit, decide, withdraw, expire.

Every approval in vmmsx runs through here: volunteer applications, membership,
deployment requests, whatever a later module adds. The engine never names one.
It reads a `VMMS Approval Workflow` for the governed doctype, resolves people
through core, and moves state through `states.py`.

**The gate.** `authorised()` is the whole security story. Acting on an approval
is not "does the user hold County Coordinator" — Frappe's native Workflow can
ask that, which is exactly why it is not enough. It is "is this user among the
people *this document* resolved to, at *this* stage, right now", and the answer
is recomputed from Geo Assignment on every call. Nothing is trusted from the
document, the session, or a ToDo: an assignment is where the work appears, never
proof that somebody may do it.

**Idempotence.** Submitting an application that is already under review re-syncs
the queue and returns; recording the decision you already recorded returns the
same answer instead of a second audit row. Services here are safe to call
twice, because in a distributed desk they will be.

**One save per operation.** State is moved on the in-memory document, saved
once, and only then does the queue get synced — so a rejected save leaves no
ToDo pointing at an approval that did not happen.
"""

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, now_datetime
from onerc_core.access.services import scope
from onerc_core.access.services.enforcement import guard
from onerc_core.geo.services import adapter

from vmmsx.approvals import states
from vmmsx.approvals.services import applicant, assignment, config, contract, routing, sla


def submit(doc, user: str | None = None) -> dict:
	"""Move a draft into review, or re-sync one that is already there.

	Enforces the anchor rules before anything else: an application with no Geo
	Node (ACC-02) or one anchored at a level this society does not allow
	(ACC-03) never enters review, because neither can be routed.
	"""
	user = user or frappe.session.user
	workflow = config.for_doctype(doc.doctype)

	if contract.state(doc) == states.IN_REVIEW:
		# Already in review. Re-resolve and re-sync the queue — an assignment
		# somebody closed by hand comes back — and change no state.
		auth = authorised(doc, workflow)
		assignment.sync(doc.doctype, doc.name, auth["approvers"], _stage_description(doc, auth["stage"]))

		return status(doc, user, workflow)

	config.anchor(doc, workflow)
	config.assert_anchor_allowed(doc, workflow)
	assert_single_open(doc, workflow)
	assert_cooldown(doc, workflow)

	contract.set_state(doc, states.SUBMITTED)
	routed = _advance(doc, workflow, after=None)

	return _commit(doc, workflow, routed, user)


def decide(doc, decision: str, reason: str | None = None, user: str | None = None) -> dict:
	"""Record one decision at the current stage, and move if that completes it.

	This is the gate. Everything before the audit row is a refusal waiting to
	happen: wrong state, wrong person, a rejection at a stage that may only
	endorse, a rejection with no reason.
	"""
	user = user or frappe.session.user
	states.assert_decision(decision)

	workflow = config.for_doctype(doc.doctype)

	if contract.state(doc) != states.IN_REVIEW:
		frappe.throw(
			_("{0} {1} is {2}, not under review. There is nothing to decide.").format(
				doc.doctype, frappe.bold(doc.name), frappe.bold(_(contract.state(doc)))
			),
			frappe.ValidationError,
			title=_("Not Under Review"),
		)

	auth = authorised(doc, workflow)
	stage = auth["stage"]

	if not stage:
		frappe.throw(
			_("{0} {1} points at a stage that no longer exists in its workflow.").format(
				doc.doctype, frappe.bold(doc.name)
			),
			title=_("Stage Missing"),
		)

	# Core's geo scope first: an approver must be able to reach the record at
	# all. A no-op for a doctype nobody registered as scopeable, and the two
	# checks agree by construction — routing only ever names holders whose
	# scope covers the node.
	guard(doc.doctype, doc.name, user)

	if user not in auth["approvers"]:
		frappe.throw(
			_(
				"This approval is routed to a specific approver and you are not one of them."
				" Holding the role is not enough — the document resolved to the person who holds"
				" {0} for {1}."
			).format(frappe.bold(stage.required_role), frappe.bold(adapter.get_full_path(auth["node"]))),
			frappe.PermissionError,
			title=_("Not Your Approval"),
		)

	if decision == states.DECISION_REJECTED:
		_assert_may_reject(stage, reason)

	already = [row for row in contract.decisions_at(doc, stage.name) if row.approver == user]

	if already:
		return _already_decided(doc, workflow, user, already[-1], decision)

	contract.record_decision(doc, stage, user, decision, reason)

	if decision == states.DECISION_REJECTED:
		# The application is refused; the applicant's record is untouched. A
		# rejection ends this application, not the person.
		contract.set_state(doc, states.REJECTED)
		contract.set_stage(doc, None)
		routed = []
	elif decision == states.DECISION_MORE_INFO:
		# Back to the applicant. Review restarts from the first stage when they
		# resubmit, because what the earlier stages endorsed is not what they
		# will be resubmitting.
		contract.set_state(doc, states.DRAFT)
		contract.set_stage(doc, None)
		routed = []
	else:
		routed = _after_approval(doc, workflow, stage, auth)

	return _commit(doc, workflow, routed, user)


def withdraw(doc, reason: str | None = None, user: str | None = None) -> dict:
	"""The applicant takes their application back, where policy allows it."""
	user = user or frappe.session.user
	workflow = config.for_doctype(doc.doctype)

	if not workflow.allow_withdrawal:
		frappe.throw(
			_("{0} applications cannot be withdrawn once they exist.").format(frappe.bold(doc.doctype)),
			frappe.ValidationError,
			title=_("Withdrawal Not Allowed"),
		)

	if user != doc.owner and not scope.has_unrestricted_scope(user):
		frappe.throw(
			_("Only the applicant may withdraw this application."),
			frappe.PermissionError,
			title=_("Not Your Application"),
		)

	contract.set_state(doc, states.WITHDRAWN)
	contract.set_stage(doc, None)
	doc.save()
	assignment.clear(doc.doctype, doc.name)
	doc.add_comment("Comment", _("Withdrawn by {0}. {1}").format(user, reason or ""))

	return status(doc, user, workflow)


def expire(doc, workflow=None) -> dict:
	"""Close an application nobody moved. The terminal state for abandonment."""
	workflow = workflow or config.for_doctype(doc.doctype)

	contract.set_state(doc, states.EXPIRED)
	contract.set_stage(doc, None)
	doc.save()
	assignment.clear(doc.doctype, doc.name)
	doc.add_comment(
		"Comment",
		_("Expired after {0} day(s) without activity.").format(cint(workflow.application_expiry_days)),
	)

	return status(doc, frappe.session.user, workflow)


def expire_stale(now=None) -> dict:
	"""Expire open applications a society has said should not stay open forever.

	Scheduled daily alongside the SLA sweep. `application_expiry_days = 0` — the
	default — means never, so this does nothing at all until a society asks for
	it.
	"""
	now = now or now_datetime()
	summary = {"checked": 0, "expired": 0}

	for doctype in config.governed_doctypes():
		workflow = config.for_doctype(doctype)
		days = cint(workflow.application_expiry_days)

		if days <= 0:
			continue

		cutoff = add_to_date(now, days=-days)
		stale = frappe.get_all(
			doctype,
			filters={
				contract.STATE_FIELD: ("in", states.OPEN_STATES),
				"modified": ("<", cutoff),
			},
			pluck="name",
		)

		summary["checked"] += len(stale)

		for name in stale:
			expire(frappe.get_doc(doctype, name), workflow)
			summary["expired"] += 1

	return summary


# --- the gate -------------------------------------------------------------


def authorised(doc, workflow=None) -> dict:
	"""Who may act on this document right now, and why.

	    routed      — the people the stage resolved to
	    escalated   — the nearest holders above, admitted in two cases below
	    effective   — who the completion rule counts. The routed people
	                  normally; the escalation target when the stage resolved
	                  nobody, which is what stops an `all_of` stage with no
	                  approvers from deadlocking instead of escalating.
	    approvers   — routed + escalated: everyone the gate admits

	The escalation is admitted when either:

	1. **the stage resolved nobody** — there is no other way for the
	   application to move, whatever the breach policy says; or
	2. **the stage is breached and the society asked for `escalate_up`** —
	   `notify_only` is a reminder and `none` is a deliberate decision to wait,
	   and neither of them hands anybody else authority. The configured breach
	   action governs the gate as well as the notification, so the two cannot
	   say different things.

	A breach only ever *widens* this set. Being late does not remove an
	approver's authority; it adds somebody else's.

	Recomputed from Geo Assignment on every call, deliberately. Caching it on
	the document would mean an approver who lost their assignment last week
	could still approve today, which is the failure the whole access model
	exists to prevent.
	"""
	workflow = workflow or config.for_doctype(doc.doctype)
	stage = config.stage_by_name(workflow, contract.stage(doc))

	if not stage:
		return {
			"stage": None,
			"node": None,
			"routed": [],
			"escalated": [],
			"effective": [],
			"approvers": [],
			"breached": False,
		}

	node = config.anchor(doc, workflow)
	routed = routing.routed(stage, node)
	breached = sla.is_breached(doc, stage)
	escalated = []

	if not routed or (breached and stage.on_sla_breach == sla.BREACH_ESCALATE_UP):
		escalated = routing.escalate(stage.required_role, node, exclude=set(routed))["approvers"]

	return {
		"stage": stage,
		"node": node,
		"routed": routed,
		"escalated": escalated,
		"effective": routed or escalated,
		"approvers": routed + [user for user in escalated if user not in routed],
		"breached": breached,
	}


def may_act(doc, user: str | None = None, workflow=None) -> bool:
	"""The gate as a predicate, for screens that need to show or hide a button."""
	user = user or frappe.session.user

	return user in authorised(doc, workflow)["approvers"]


# --- movement -------------------------------------------------------------


def _advance(doc, workflow, after: int | None) -> list[str]:
	"""Enter the next stage that can be entered. Returns who it routed to.

	Walks the stages in sequence and stops at the first one with somebody in
	it. A stage that resolves nobody is either:

	- **optional** — skipped, which is what a society means by optional; or
	- **not optional** — entered anyway, blocked and escalated. It does *not*
	  pass. A stage that requires an approver and cannot find one must be
	  visible, not silently satisfied; that is the difference between "nobody
	  needed to sign this" and "nobody could".

	Falling off the end means every remaining stage was optional and empty, and
	the application is approved — by a configuration that asked for no
	approvals, not by accident.
	"""
	node = config.anchor(doc, workflow)

	for stage in config.stages_after(workflow, after):
		routed = routing.routed(stage, node)

		if routed:
			contract.set_state(doc, states.IN_REVIEW)
			contract.set_stage(doc, stage.name)

			return routed

		if stage.is_optional:
			continue

		contract.set_state(doc, states.IN_REVIEW)
		contract.set_stage(doc, stage.name)

		return routing.escalate(stage.required_role, node, exclude=set())["approvers"]

	contract.set_state(doc, states.APPROVED)
	contract.set_stage(doc, None)

	return []


def _after_approval(doc, workflow, stage, auth) -> list[str]:
	"""Advance if the completion rule is satisfied; otherwise keep waiting.

	`single` and `any_of` are satisfied by the decision just recorded. `all_of`
	waits for every approver the stage counts on, and the queue shrinks to the
	ones who have not answered — the approver who just acted should not keep
	seeing it.
	"""
	approved_by = {
		row.approver
		for row in contract.decisions_at(doc, stage.name)
		if row.decision == states.DECISION_APPROVED
	}

	if routing.is_complete(stage, auth["effective"], approved_by):
		return _advance(doc, workflow, after=stage.sequence)

	return [user for user in auth["approvers"] if user not in approved_by]


def _commit(doc, workflow, routed: list[str], user: str) -> dict:
	"""Save once, then put the document in front of whoever it now belongs to."""
	doc.save()
	assignment.sync(
		doc.doctype,
		doc.name,
		routed,
		_stage_description(doc, config.stage_by_name(workflow, contract.stage(doc))),
	)

	return status(doc, user, workflow)


def _already_decided(doc, workflow, user: str, existing, decision: str) -> dict:
	"""A second decision from the same person at the same stage.

	The same decision again is the idempotent case — a double-clicked button, a
	retried request — and returns the same answer without a second audit row. A
	*different* decision is refused: changing your mind is a new stage or a new
	application, not a rewritten history.
	"""
	if existing.decision == decision:
		return status(doc, user, workflow)

	frappe.throw(
		_("You already recorded {0} at this stage. A decision cannot be replaced.").format(
			frappe.bold(_(existing.decision))
		),
		frappe.ValidationError,
		title=_("Already Decided"),
	)


def _assert_may_reject(stage, reason: str | None) -> None:
	if not stage.can_reject:
		frappe.throw(
			_("{0} may only endorse this application onward, not reject it.").format(
				frappe.bold(stage.stage_label)
			),
			frappe.ValidationError,
			title=_("Stage Cannot Reject"),
		)

	if not (reason or "").strip():
		frappe.throw(
			_("A rejection needs a reason. The applicant is entitled to know why."),
			frappe.MandatoryError,
			title=_("Reason Required"),
		)


def assert_single_open(doc, workflow) -> None:
	"""One open application per applicant. Refuse a second while the first lives.

	**The rule that was missing, and what it cost.** `assert_cooldown` governs
	re-applying after a *rejection*, and nothing at all governed applying again
	while an application was still under review. So somebody could walk the
	registration wizard twice and put two live applications in front of the same
	approver, each routed, each assigned, each answerable — and approving one
	would create the volunteer record the other was still asking for. Every
	rule the engine has was about a single document; this is the first one about
	the *set*, which is why nothing caught it.

	**Open is "not terminal", asked of `states.py` rather than listed here.** A
	Draft, a Submitted and an In Review application are all things the society
	still owes an answer on. Approved, Rejected, Withdrawn and Expired are
	finished, and re-applying after one of those is a legitimate act the cooldown
	governs. Deriving it from the closed set means a state added later is
	classified once, in the module that owns states.

	**Only where the workflow names an applicant field, and that is the whole of
	when this rule is safe.** `config.applicant` falls back to `owner` when a
	workflow names none, and `owner` is the wrong question here: it is whoever
	*filed* the document, not whoever it is *about*. This app already states that
	distinction — "owner bypass is `Red Profile.user`, never `doc.owner`; a
	membership's owner is the clerk" — and applying a one-per-person rule to the
	fallback would mean a coordinator entering ten paper applications had the
	second one refused because they filed the first. So an unconfigured workflow
	gets no rule rather than a wrong one, and a module that wants this names its
	applicant field, which is the same act that makes `assert_cooldown` work.

	Checked at submission rather than at insert, deliberately: a coordinator may
	have several drafts on their desk, and a draft is not an application anybody
	has been asked to answer. It becomes one here.
	"""
	if not workflow.applicant_field:
		return

	field, value = config.applicant(doc, workflow)

	if not value:
		return

	open_states = [state for state in states.STATES if not states.is_terminal(state)]

	duplicate = frappe.db.exists(
		doc.doctype,
		{
			field: value,
			contract.STATE_FIELD: ("in", open_states),
			"name": ("!=", doc.name),
		},
	)

	if not duplicate:
		return

	frappe.throw(
		_(
			"There is already an open {0} for this applicant ({1}), and it has not been decided"
			" yet. A second one would put two live applications in front of the same approver."
			" Wait for that one to be decided, or withdraw it first."
		).format(_(doc.doctype), frappe.bold(duplicate)),
		frappe.ValidationError,
		title=_("Application Already Open"),
	)


def assert_cooldown(doc, workflow) -> None:
	"""Refuse a re-application inside the society's cooldown window.

	The applicant is identified by whichever field the workflow names — a Red
	Profile, a membership number, or the document's owner when it names none.
	"""
	days = cint(workflow.reapplication_cooldown_days)

	if days <= 0:
		return

	field, value = config.applicant(doc, workflow)

	if not value:
		return

	previous = frappe.get_all(
		doc.doctype,
		filters={field: value, contract.STATE_FIELD: states.REJECTED, "name": ("!=", doc.name)},
		pluck="name",
	)

	if not previous:
		return

	last = frappe.db.get_value(
		contract.DECISION_DOCTYPE,
		{
			"parenttype": doc.doctype,
			"parent": ("in", previous),
			"decision": states.DECISION_REJECTED,
		},
		"decided_on",
		order_by="decided_on desc",
	)

	if not last:
		return

	available_on = add_to_date(get_datetime(last), days=days)

	if now_datetime() >= available_on:
		return

	frappe.throw(
		_("A previous application was rejected on {0}. A new one may be made from {1}.").format(
			frappe.bold(frappe.format(get_datetime(last), {"fieldtype": "Datetime"})),
			frappe.bold(frappe.format(available_on, {"fieldtype": "Datetime"})),
		),
		frappe.ValidationError,
		title=_("Re-application Too Soon"),
	)


# --- the DTO --------------------------------------------------------------


def status(doc, user: str | None = None, workflow=None) -> dict:
	"""Everything a caller needs about this approval, as an explicit dict.

	Built field by field. A `Document` or a raw query result would leak fields
	nobody reviewed and turn every schema change into an API change.

	Approver *names* are shown to the people in the chain — whoever may act now,
	whoever has already acted, and users with unrestricted scope. Everyone else,
	the applicant included, gets the count: that their application is with two
	people is theirs to know; which two is not automatically theirs to know. An
	approver who has endorsed sees where it went next, because they are part of
	the decision, not an onlooker.

	**`applicant` travels with every status, and it is not a widening.** Whoever
	may read this DTO has already been allowed to read the document it describes
	— `api/approvals.py` checks that first — and the document links the person by
	name. What this adds is that the link is followed, so a queue lists people
	rather than docnames. See `applicant.py` for how it is resolved without this
	module learning what either governed doctype is.
	"""
	user = user or frappe.session.user
	workflow = workflow or config.for_doctype(doc.doctype)
	auth = authorised(doc, workflow)
	state = contract.state(doc)
	node = doc.get(workflow.geo_node_field)
	in_the_chain = set(auth["approvers"]) | {row.approver for row in contract.decisions(doc)}
	visible = user in in_the_chain or scope.has_unrestricted_scope(user)

	return {
		"doctype": doc.doctype,
		"name": doc.name,
		"state": state,
		"is_open": states.is_open(state),
		"is_terminal": states.is_terminal(state),
		"geo_node": node,
		"geo_path": adapter.get_full_path(node) if node else None,
		"applicant": applicant.of(doc, workflow),
		"stage": _stage_dto(doc, auth),
		"can_act": user in auth["approvers"],
		"approver_count": len(auth["approvers"]),
		"approvers": auth["approvers"] if visible else None,
		"escalated_to": auth["escalated"] if visible else None,
		"allow_withdrawal": bool(workflow.allow_withdrawal),
		"can_withdraw": bool(workflow.allow_withdrawal) and states.is_open(state) and user == doc.owner,
		"decisions": [
			{
				"stage": row.stage,
				"stage_sequence": row.stage_sequence,
				"stage_label": row.stage_label,
				"approver": row.approver,
				"decision": row.decision,
				"reason": row.reason,
				"decided_on": row.decided_on,
			}
			for row in contract.decisions(doc)
		],
	}


def _stage_dto(doc, auth) -> dict | None:
	stage = auth["stage"]

	if not stage:
		return None

	return {
		"name": stage.name,
		"sequence": stage.sequence,
		"label": _(stage.stage_label),
		"required_role": stage.required_role,
		"completion_rule": stage.completion_rule,
		"can_reject": bool(stage.can_reject),
		"is_optional": bool(stage.is_optional),
		"entered_on": contract.stage_entered_on(doc),
		"due_on": sla.due_on(doc, stage),
		"is_breached": auth["breached"],
		"days_overdue": sla.days_overdue(doc, stage),
		# Nobody resolved and the stage is not optional: it is waiting on an
		# escalation, not on an approver. Surfaced so a queue screen can say so
		# rather than showing an approval with nobody's name against it.
		"is_blocked": not auth["routed"],
	}


def _stage_description(doc, stage) -> str:
	"""What the approver sees in their queue."""
	if not stage:
		return ""

	return _("{0}: {1} {2}").format(_(stage.stage_label), doc.doctype, doc.name)
