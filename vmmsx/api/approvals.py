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

	**Read permission, not write.** Being able to open the record (core's geo
	scope included) is the precondition; `engine.decide` is the authority. An
	approver whose role may only read applications is still the person the
	document routed to, and asking for write here refused every county
	Volunteer Approver on a site whose role reads volunteer applications only.
	"""
	return engine.decide(_approvable(doctype, name, ptype="read"), decision, reason)


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
	"""Refuse doctypes this app does not approve, before anything else happens.

	**The question is the contract, not the configuration.** It used to be "is
	there a workflow for this", and that was the same answer right up until an
	application could be accepted before its society had written one. Those
	applications are real, their applicants can see them in the portal, and an
	endpoint answering "not approvable" about a document this app had just
	accepted would be denying the thing it handed them. The narrowing this check
	exists for is untouched: `contract.meets` passes only a doctype carrying the
	engine's own four fields, which nothing outside this app has.
	"""
	if config.is_approvable(doctype) or contract.meets(doctype):
		return

	frappe.throw(
		_("{0} is not under an approval workflow.").format(frappe.bold(doctype)),
		title=_("Not Approvable"),
	)


# --- the caller's own cases, beyond what is routed to them right now --------

# Maximum response page and scoped draft scan batch. Older cases remain
# reachable by offset instead of disappearing behind this limit.
_CASE_CEILING = 200

# The bands a queue screen navigates between, named once.
#
# `in_review` is what the queue opens on: every application in the caller's
# scope that has been submitted and is being decided. The ones this caller may
# decide right now come first — `my_queue`, re-checked per row — so a regional
# approver whose scope also covers county-stage work finds their own on top
# without a separate "assigned to me" list. `drafts` were started and never
# submitted; `changes` are drafts an approver sent back; `closed` is history,
# optionally narrowed to one terminal state.
#
# `all` and `actionable` stay answerable for callers that still ask for them.
#
# History is not personal: an application this branch sent back for
# corrections is the branch's to see, not only the approver who pressed the
# button. Every band stands on `frappe.get_list`, which runs core's permission
# query condition, so a coordinator reads their own areas and nothing else.
CASE_ALL = "all"
CASE_ACTIONABLE = "actionable"
CASE_IN_REVIEW = "in_review"
CASE_DRAFTS = "drafts"
CASE_CHANGES = "changes"
CASE_CLOSED = "closed"

CASE_GROUPS = (CASE_IN_REVIEW, CASE_DRAFTS, CASE_CHANGES, CASE_CLOSED, CASE_ALL, CASE_ACTIONABLE)

# Submitted resolves to In Review inside the same transaction; both mean
# "with the reviewers", and a membership parked on its payment sits here too.
_REVIEW_STATES = (states.SUBMITTED, states.IN_REVIEW)


@frappe.whitelist()
def my_cases(
	doctype: str,
	group: str = CASE_IN_REVIEW,
	limit: int | None = None,
	offset: int = 0,
	state: str | None = None,
) -> dict:
	"""One band of `doctype`'s applications, inside the caller's own scope.

	    in_review    Submitted or In Review; the caller's own decisions first
	    drafts       Draft, never sent back — started and not yet submitted
	    changes      Draft **and** a "More info requested" decision on it
	    closed       one of the four terminal states; `state` narrows it to one
	    all          every application the caller may read
	    actionable   routed to this user now — `my_queue`

	`in_review`, `closed` and `all` also return `total`, counted by the same
	scoped `frappe.get_list` as the page.

	**Every state named here is one of the seven in `states.py` and none of them
	is derived from a stage label.**

	**Scope is the floor, not a filter.** Nothing the caller sends can widen the
	result.
	"""
	_assert_governed(doctype)

	if group not in CASE_GROUPS:
		frappe.throw(
			_("{0} is not one of: {1}.").format(frappe.bold(group), ", ".join(CASE_GROUPS)),
			title=_("Unknown Case Group"),
		)

	if state and state not in states.TERMINAL_STATES:
		frappe.throw(
			_("{0} is not one of: {1}.").format(frappe.bold(state), ", ".join(states.TERMINAL_STATES)),
			title=_("Unknown State"),
		)

	if group == CASE_ACTIONABLE:
		rows = my_queue(doctype)

		return {"group": group, "count": len(rows), "cases": rows}

	# An empty band, not an exception, for somebody who may not read this
	# register at all: `my_queue` already answers that caller with `[]`.
	if not frappe.has_permission(doctype, "read"):
		return {"group": group, "count": 0, "total": 0, "cases": []}

	page_size = _bounded(limit)
	try:
		start = max(0, int(offset))
	except TypeError, ValueError:
		start = 0

	filters = None
	if group == CASE_IN_REVIEW:
		names = _in_review(doctype, page_size + 1, start)
		filters = {"approval_state": ("in", list(_REVIEW_STATES))}
	elif group == CASE_ALL:
		names = frappe.get_list(
			doctype,
			order_by="modified desc, name desc",
			limit_start=start,
			limit_page_length=page_size + 1,
			pluck="name",
		)
		filters = {}
	elif group == CASE_CLOSED:
		filters = {"approval_state": state or ("in", list(states.TERMINAL_STATES))}
		names = frappe.get_list(
			doctype,
			filters=filters,
			order_by="modified desc, name desc",
			limit_start=start,
			limit_page_length=page_size + 1,
			pluck="name",
		)
	else:
		names = _drafts(doctype, page_size + 1, start, returned=group == CASE_CHANGES)

	has_more = len(names) > page_size
	names = names[:page_size]

	answer = {
		"group": group,
		"count": len(names),
		"has_more": has_more,
		# `engine.status` per row, so every band describes an application with
		# the same DTO. Read permission was already applied by the listing.
		"cases": [engine.status(frappe.get_doc(doctype, name)) for name in names],
	}
	if filters is not None:
		# The aggregate uses the same permission-aware query as the page. Never
		# expose an unrestricted database count alongside a scoped list.
		totals = frappe.get_list(
			doctype,
			filters=filters,
			fields=[{"COUNT": "name", "as": "total"}],
			order_by=None,
			limit_page_length=1,
		)
		answer["total"] = int(totals[0]["total"]) if totals else 0
	return answer


def _in_review(doctype: str, limit: int, offset: int) -> list[str]:
	"""Applications with the reviewers, the caller's own decisions first.

	The caller's own come from `my_queue`, which re-checks routing per row, and
	are kept only if the scoped listing would also show them — so the head of
	the list can never reach past what the rest of it may. The rest follow,
	newest first, with those names left out so nothing appears twice.
	"""
	filters = {"approval_state": ("in", list(_REVIEW_STATES))}
	mine = [row["name"] for row in my_queue(doctype)]
	if mine:
		mine = frappe.get_list(
			doctype,
			filters={**filters, "name": ("in", mine)},
			order_by="modified asc, name asc",
			pluck="name",
			limit_page_length=0,
		)

	head = mine[offset : offset + limit]
	rest_start = max(0, offset - len(mine))
	rest_limit = limit - len(head)
	if rest_limit <= 0:
		return head

	rest_filters = dict(filters)
	if mine:
		rest_filters["name"] = ("not in", mine)
	rest = frappe.get_list(
		doctype,
		filters=rest_filters,
		order_by="modified desc, name desc",
		limit_start=rest_start,
		limit_page_length=rest_limit,
		pluck="name",
	)
	return head + rest


def _bounded(limit) -> int:
	"""A caller's page size, never above the ceiling and never below one."""
	try:
		asked = int(limit or _CASE_CEILING)
	except TypeError, ValueError:
		asked = _CASE_CEILING

	return max(1, min(asked, _CASE_CEILING))


def _drafts(doctype: str, limit, offset: int = 0, returned: bool = False) -> list[str]:
	"""Drafts, newest first: the ones sent back, or the ones never sent.

	Both bands are Drafts and the decisions table tells them apart — a "More
	info requested" decision is the only thing that distinguishes an
	application waiting on its applicant from one nobody has ever submitted.

	Two reads rather than a join: the scoped listing decides which documents the
	caller may see at all, and the decisions table then says which of those got
	there by being returned. Reading decisions first would be a query across
	every branch's applications with the scope applied afterwards, which is the
	shape of an accidental disclosure.
	"""
	selected = []
	scanned = 0
	while len(selected) < offset + limit:
		drafts = frappe.get_list(
			doctype,
			filters={"approval_state": states.DRAFT},
			order_by="modified desc, name desc",
			limit_start=scanned,
			limit_page_length=_CASE_CEILING,
			pluck="name",
		)
		if not drafts:
			break
		sent_back = set(
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
		selected.extend(name for name in drafts if (name in sent_back) == returned)
		scanned += len(drafts)
		if len(drafts) < _CASE_CEILING:
			break
	return selected[offset : offset + limit]
