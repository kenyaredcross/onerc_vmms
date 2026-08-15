# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The approval API — the only way to act on an approval.

There are no desk workflow buttons, and that is the design rather than an
omission. Frappe's native Workflow gates a transition on a role plus a
`safe_eval` condition that cannot call our code: it can ask whether the user
holds County Coordinator, but never whether they are *the* County Coordinator
this document routed to. Every action therefore comes through here, where the
engine can ask the real question.

Every endpoint:

- **names its arguments** — no `**kwargs` reaching into `form_dict`;
- **checks the governed doctype first**, so this is not a general-purpose way
  to poke at arbitrary doctypes;
- **checks read permission** through Frappe, which brings core's geo scoping
  with it, before the engine applies the person-gate;
- **returns an explicit DTO** built by `engine.status()` — never a Document,
  never a raw query result.
"""

import frappe
from frappe import _

from vmmsx.approvals import states
from vmmsx.approvals.services import config, contract, engine


@frappe.whitelist()
def submit_for_approval(doctype: str, name: str) -> dict:
	"""Move an application into review and route it to its first approvers."""
	return engine.submit(_approvable(doctype, name, ptype="write"))


@frappe.whitelist()
def decide(doctype: str, name: str, decision: str, reason: str | None = None) -> dict:
	"""Approve, reject, or ask for more information at the current stage.

	Refused unless the acting user is among the approvers this document
	resolved to — holding the role is not enough.
	"""
	return engine.decide(_approvable(doctype, name, ptype="write"), decision, reason)


@frappe.whitelist()
def withdraw(doctype: str, name: str, reason: str | None = None) -> dict:
	"""Take an application back, where the workflow allows withdrawal."""
	return engine.withdraw(_approvable(doctype, name, ptype="write"), reason)


@frappe.whitelist()
def get_status(doctype: str, name: str) -> dict:
	"""Where an application stands, and whether the caller may act on it."""
	return engine.status(_approvable(doctype, name, ptype="read"))


@frappe.whitelist()
def anchor_levels(doctype: str) -> dict:
	"""Geo Levels a new `doctype` document may anchor to — ACC-03, for a picker.

	Built from `config.allowed_anchor_levels_for`, the exact row
	`assert_anchor_allowed` reads at Submit, so a geo_node Link field filtered
	to `levels` can never offer a level Submit would go on to reject. Read-only
	and advisory: it narrows what a picker shows, and enforcement stays where
	it already was. `unconstrained` is True when nothing narrows it — no
	workflow governs `doctype` yet, or one exists but names no levels — and a
	picker should apply no filter in that case rather than one that offers
	nothing.
	"""
	levels = config.allowed_anchor_levels_for(doctype)

	return {"levels": levels, "unconstrained": not levels}


@frappe.whitelist()
def my_queue(doctype: str | None = None) -> list[dict]:
	"""Applications awaiting *this user's* decision.

	Assignment is where the work appears, so the candidates come from the
	caller's own ToDos — but every one is re-checked against routing before it
	is returned. A stale assignment shows nothing; an approver whose Geo
	Assignment ended yesterday has an empty queue today, whatever their ToDo
	list says.
	"""
	governed = config.governed_doctypes()

	if doctype:
		_assert_governed(doctype)
		governed = [doctype]

	if not governed:
		return []

	pending = frappe.get_all(
		"ToDo",
		filters={
			"allocated_to": frappe.session.user,
			"status": ("in", ("Open", "Overdue")),
			"reference_type": ("in", governed),
		},
		fields=["reference_type", "reference_name"],
	)

	queue = []

	for row in pending:
		doc = frappe.get_doc(row.reference_type, row.reference_name)

		if contract.state(doc) != states.IN_REVIEW or not engine.may_act(doc):
			continue

		queue.append(engine.status(doc))

	return queue


def _approvable(doctype: str, name: str, ptype: str):
	"""Load a governed document the caller is allowed to see."""
	_assert_governed(doctype)

	doc = frappe.get_doc(doctype, name)
	doc.check_permission(ptype)

	return doc


def _assert_governed(doctype: str) -> None:
	"""Refuse doctypes no workflow governs, before anything else happens."""
	if config.is_approvable(doctype):
		return

	frappe.throw(
		_("{0} is not under an approval workflow.").format(frappe.bold(doctype)),
		title=_("Not Approvable"),
	)
