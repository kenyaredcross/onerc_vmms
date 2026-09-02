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


# --- the caller's own cases, beyond what is routed to them right now --------

# What `my_cases` will read before it stops. A ceiling on work rather than a
# page size: these lists are a branch's history, and a coordinator who has
# cleared more than this wants a report rather than a screen.
_CASE_CEILING = 200

# The three bands a queue screen navigates between, named once.
#
# `actionable` is `my_queue` — what is routed to this user right now. The other
# two are history, and history is not personal: an application this branch sent
# back for corrections is the branch's to see, not only the approver who
# happened to press the button. Both are bounded by the same floor everything
# else in this app stands on — `frappe.get_list`, which runs core's permission
# query condition — so a coordinator reads their own areas and nothing else.
CASE_ACTIONABLE = "actionable"
CASE_CHANGES = "changes"
CASE_CLOSED = "closed"

CASE_GROUPS = (CASE_ACTIONABLE, CASE_CHANGES, CASE_CLOSED)


@frappe.whitelist()
def my_cases(doctype: str, group: str = CASE_ACTIONABLE, limit: int | None = None) -> dict:
	"""One band of `doctype`'s approvals, inside the caller's own scope.

	The queue screens navigate three bands and `my_queue` only answers the
	first. This answers all three from the governed doctype itself rather than
	from ToDo rows, because the other two are not assignments: an application
	sent back for corrections has no approver at all, and a closed one has
	finished having any.

	    actionable   routed to this user now — `my_queue`, re-checked per row
	    changes      state is exactly Draft **and** somebody has recorded a
	                 "More info requested" decision on it, which is the only
	                 thing that distinguishes an application waiting on its
	                 applicant from one nobody has ever submitted
	    closed       state is one of the four terminal ones

	**Every state named here is one of the seven in `states.py` and none of them
	is derived from a stage label.** The bands are built from `approval_state`
	and from the decisions table, both of which are code; a society's stage
	names are displayed by the screen and compared nowhere.

	**Scope is the floor, not a filter.** The read is `frappe.get_list`, so
	core's permission query condition applies exactly as it does to the register
	pages; `frappe.get_all` would skip it and is not used. Nothing the caller
	sends can widen the result.
	"""
	_assert_governed(doctype)

	if group not in CASE_GROUPS:
		frappe.throw(
			_("{0} is not one of: {1}.").format(frappe.bold(group), ", ".join(CASE_GROUPS)),
			title=_("Unknown Case Group"),
		)

	if group == CASE_ACTIONABLE:
		rows = my_queue(doctype)

		return {"group": group, "count": len(rows), "cases": rows}

	# **An empty band, not an exception, for somebody who may not read this
	# register at all.** `my_queue` already answers that caller with `[]` — it
	# reads their own ToDos, and they have none — so a queue screen whose first
	# band rendered empty and whose second band 500'd would be reporting two
	# different things about one permission. Nothing is disclosed either way:
	# "nothing here for you" is the same answer in both cases.
	if not frappe.has_permission(doctype, "read"):
		return {"group": group, "count": 0, "cases": []}

	names = _changed(doctype, limit) if group == CASE_CHANGES else _closed(doctype, limit)

	return {
		"group": group,
		"count": len(names),
		# `engine.status` per row, so a history screen and a live one describe an
		# application with the same DTO. Read permission was already applied by
		# the listing above; nothing here is a second door into a document.
		"cases": [engine.status(frappe.get_doc(doctype, name)) for name in names],
	}


def _bounded(limit) -> int:
	"""A caller's page size, never above the ceiling and never below one."""
	try:
		asked = int(limit or _CASE_CEILING)
	except (TypeError, ValueError):
		asked = _CASE_CEILING

	return max(1, min(asked, _CASE_CEILING))


def _closed(doctype: str, limit) -> list[str]:
	"""Applications in one of the four terminal states, newest first."""
	return frappe.get_list(
		doctype,
		filters={"approval_state": ("in", list(states.TERMINAL_STATES))},
		order_by="modified desc",
		limit_page_length=_bounded(limit),
		pluck="name",
	)


def _changed(doctype: str, limit) -> list[str]:
	"""Drafts that were sent back, newest first.

	Two reads rather than a join: the scoped listing decides which documents the
	caller may see at all, and the decisions table then says which of those
	drafts got there by being returned rather than by never having been sent.
	Doing it the other way round — reading decisions first — would be a query
	across every branch's applications with the scope applied afterwards, which
	is the shape of an accidental disclosure.
	"""
	drafts = frappe.get_list(
		doctype,
		filters={"approval_state": states.DRAFT},
		order_by="modified desc",
		limit_page_length=_bounded(limit),
		pluck="name",
	)

	if not drafts:
		return []

	returned = set(
		frappe.get_all(
			contract.DECISION_DOCTYPE,
			filters={
				"parenttype": doctype,
				"parent": ("in", drafts),
				"decision": states.DECISION_MORE_INFO,
			},
			pluck="parent",
		)
	)

	# The listing's order is preserved: it is already newest-first and re-sorting
	# a filtered subset would silently override it.
	return [name for name in drafts if name in returned]
