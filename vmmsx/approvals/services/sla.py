# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The clock, and what happens when it runs out.

An application rotting in an absent approver's queue is the number-one failure
mode of a system like this. It is not a crash, nothing is logged, and the first
anybody hears of it is a volunteer asking why nobody replied for four months.
So every stage has an SLA, and every stage says what happens when it is
breached.

Two properties this module is built around:

1. **Escalation never lands on the person who was already late.** They had
   their SLA. Handing the same document back to them is a loop with extra
   notifications. `routing.escalate` is given the routed approvers to exclude,
   and walks past any node whose only holders are among them.
2. **A breach widens authority; it never narrows it.** The late approver keeps
   the document and can still act — the escalation target is added, not
   substituted. Taking it off the late approver's desk would hide the fact that
   they were late from the only people able to notice.

Breach handling changes no state and saves no document: who may act on a
breached stage is *computed* from the clock by `engine.authorised`, so the gate
is right whether or not the nightly sweep ever ran. The sweep exists to notify
people, not to grant anybody anything.
"""

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.utils import add_to_date, cint, get_datetime, now_datetime
from onerc_core.geo.services import adapter

from vmmsx.approvals import states
from vmmsx.approvals.services import assignment, config, contract, routing

BREACH_ESCALATE_UP = "escalate_up"
BREACH_NOTIFY_ONLY = "notify_only"
BREACH_NONE = "none"
BREACH_ACTIONS = (BREACH_ESCALATE_UP, BREACH_NOTIFY_ONLY, BREACH_NONE)

# Named, so the log line is a fact the tests can assert on rather than prose
# that drifts.
STRANDED_LOG_TITLE = "Approval breached its SLA with nowhere to escalate"


def due_on(doc, stage):
	"""When this stage's clock runs out, or None if it has no clock."""
	entered = contract.stage_entered_on(doc)

	if not (entered and stage and cint(stage.sla_days)):
		return None

	return add_to_date(get_datetime(entered), days=cint(stage.sla_days))


def is_breached(doc, stage, now=None) -> bool:
	due = due_on(doc, stage)

	return bool(due) and (now or now_datetime()) > due


def days_overdue(doc, stage, now=None) -> int:
	due = due_on(doc, stage)

	if not due:
		return 0

	overdue = ((now or now_datetime()) - due).days

	return max(overdue, 0)


def sweep(now=None) -> dict:
	"""Every open application, every governed doctype. The daily job.

	Idempotent by construction: it escalates by *adding* an assignee who is not
	already assigned, so a second run the same day adds nobody and comments
	nothing. Returns a summary rather than logging one, so a caller — the
	scheduler, a test, an administrator in the console — can see what it did.
	"""
	now = now or now_datetime()
	summary = {"checked": 0, "breached": 0, "escalated": 0, "notified": 0, "stranded": 0}

	for doctype in config.governed_doctypes():
		workflow = config.for_doctype(doctype)

		for name in _in_review(doctype):
			summary["checked"] += 1
			outcome = apply_breach(frappe.get_doc(doctype, name), workflow, now=now)

			if not outcome["breached"]:
				continue

			summary["breached"] += 1

			if outcome["escalated_to"]:
				summary["escalated"] += 1
			elif outcome["action"] == BREACH_ESCALATE_UP:
				summary["stranded"] += 1

			if outcome["notified"]:
				summary["notified"] += 1

	return summary


def apply_breach(doc, workflow=None, now=None) -> dict:
	"""Act on one document's breach, if it has one.

	The return value is the record of what happened — which stage, how overdue,
	who it went to and where they sit. Callers assert on it; nothing has to be
	inferred from a log line.
	"""
	workflow = workflow or config.for_doctype(doc.doctype)
	stage = config.stage_by_name(workflow, contract.stage(doc))
	outcome = {
		"doctype": doc.doctype,
		"name": doc.name,
		"breached": False,
		"action": stage.on_sla_breach if stage else None,
		"days_overdue": 0,
		"escalated_to": [],
		"escalation_node": None,
		"notified": [],
	}

	if not stage or contract.state(doc) != states.IN_REVIEW:
		return outcome

	if not is_breached(doc, stage, now):
		return outcome

	outcome["breached"] = True
	outcome["days_overdue"] = days_overdue(doc, stage, now)

	if stage.on_sla_breach == BREACH_NONE:
		# An explicit society choice to let it sit. Recorded, not silently
		# reinterpreted as something more helpful.
		return outcome

	node = config.anchor(doc, workflow)
	late = routing.routed(stage, node)

	if stage.on_sla_breach == BREACH_NOTIFY_ONLY:
		outcome["notified"] = _notify(late, doc, stage, outcome["days_overdue"])

		return outcome

	escalation = routing.escalate(stage.required_role, node, exclude=set(late))

	if not escalation["approvers"]:
		# Nobody above holds the role. Core will not invent a fallback approver
		# and neither will we — appointing the site's administrator as approver
		# of last resort is exactly the kind of decision software should not
		# take on a society's behalf. It is logged because an application that
		# nobody anywhere can act on is an operational fault, not a quiet state.
		frappe.log_error(
			title=STRANDED_LOG_TITLE,
			message=(
				f"{doc.doctype} {doc.name} has been overdue for {outcome['days_overdue']} day(s) at stage "
				f"{stage.name}. Nobody holds {stage.required_role} above {adapter.get_full_path(node)} "
				f"who was not already routed it."
			),
			reference_doctype=doc.doctype,
			reference_name=doc.name,
		)

		return outcome

	added = assignment.add(
		doc.doctype,
		doc.name,
		escalation["approvers"],
		description=_("Escalated: overdue by {0} day(s)").format(outcome["days_overdue"]),
	)["added"]

	outcome["escalated_to"] = escalation["approvers"]
	outcome["escalation_node"] = escalation["node"]
	outcome["notified"] = _notify(escalation["approvers"], doc, stage, outcome["days_overdue"])

	if added:
		# Once, when the escalation first happens. A daily "still overdue"
		# comment would bury the timeline it is meant to explain.
		doc.add_comment(
			"Comment",
			_("Overdue by {0} day(s). Escalated to {1} at {2}.").format(
				outcome["days_overdue"],
				", ".join(added),
				adapter.get_full_path(escalation["node"]),
			),
		)

	return outcome


def _in_review(doctype: str) -> list[str]:
	"""Names of that doctype's applications currently under review."""
	return frappe.get_all(doctype, filters={contract.STATE_FIELD: states.IN_REVIEW}, pluck="name")


def _notify(users: list[str], doc, stage, overdue: int) -> list[str]:
	"""Tell people, through the framework's own notification path."""
	if not users:
		return []

	enqueue_create_notification(
		users,
		{
			"type": "Alert",
			"document_type": doc.doctype,
			"document_name": doc.name,
			"subject": _("{0} {1} is overdue by {2} day(s) at {3}").format(
				doc.doctype, doc.name, overdue, stage.stage_label
			),
			"from_user": frappe.session.user,
		},
	)

	return list(users)
