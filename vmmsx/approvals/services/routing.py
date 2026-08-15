# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Routing — turning a stage plus a place into named people.

Core answers *who can approve here*: `resolve_approvers(geo_node, role, rule)`
walks the geo tree and returns the holders of a role. It deliberately decides
nothing else — not how many must act, not what an empty list means, not who
picks up the slack when nobody does. That is this layer.

Everything geo goes through core. There is no `tabGeo Node` query in this app
and no second copy of the walk; if routing and core's read scope ever disagreed
about who holds what where, the product would route approvals to people who
cannot open the document. They read one table through one service, so they
cannot.

    resolve()      every holder the rule finds       — who *could* act
    routed()       who the document is assigned to   — who *may* act
    escalate()     the nearest holder upward who is not already late

`routed()` differs from `resolve()` only for `single`, which is the whole point
of that rule: one named person owns the decision instead of it sitting in a
pool. The choice is deterministic — core returns holders sorted — so
re-resolving the same stage tomorrow lands on the same person rather than
quietly moving the queue around.
"""

import frappe
from frappe import _
from onerc_core.access.services.approvers import (
	RULE_AT_LEVEL,
	RULE_NEAREST_ANCESTOR,
	resolve_approvers,
)
from onerc_core.geo.services import adapter

# `fixed_node` is this layer's addition: core resolves relative to the document,
# and "always the national training desk, wherever the applicant lives" is not a
# relative question. It is expressed through core all the same — see
# `holders_exactly_at`.
RULE_FIXED_NODE = "fixed_node"
RULES = (RULE_NEAREST_ANCESTOR, RULE_AT_LEVEL, RULE_FIXED_NODE)

COMPLETION_SINGLE = "single"
COMPLETION_ANY_OF = "any_of"
COMPLETION_ALL_OF = "all_of"
COMPLETION_RULES = (COMPLETION_SINGLE, COMPLETION_ANY_OF, COMPLETION_ALL_OF)


def resolve(stage, geo_node: str, on_date: str | None = None) -> list[str]:
	"""Every user the stage's rule finds for a document anchored at `geo_node`.

	The same configuration resolves to a county coordinator in one society and a
	district officer in another, because the walk finds whoever holds the role,
	wherever they sit. Nothing here knows either word.
	"""
	if stage.resolution_rule not in RULES:
		frappe.throw(
			_("{0} is not a resolution rule. Expected one of: {1}.").format(
				frappe.bold(stage.resolution_rule), ", ".join(RULES)
			),
			title=_("Unknown Resolution Rule"),
		)

	if not geo_node:
		return []

	if stage.resolution_rule == RULE_FIXED_NODE:
		return holders_exactly_at(stage.fixed_geo_node, stage.required_role, on_date)

	if stage.resolution_rule == RULE_AT_LEVEL:
		return resolve_approvers(
			geo_node, stage.required_role, rule=RULE_AT_LEVEL, geo_level=stage.geo_level, on_date=on_date
		)

	return resolve_approvers(geo_node, stage.required_role, rule=RULE_NEAREST_ANCESTOR, on_date=on_date)


def routed(stage, geo_node: str, on_date: str | None = None) -> list[str]:
	"""Who this stage is actually routed to — the people the gate will admit.

	`single` routes to one person: the first of the resolved holders, ordered by
	core. `any_of` and `all_of` route to all of them and differ only in how many
	must act, which `is_complete` decides.
	"""
	resolved = resolve(stage, geo_node, on_date)

	if stage.completion_rule == COMPLETION_SINGLE:
		return resolved[:1]

	return resolved


def holders_exactly_at(geo_node: str, role: str, on_date: str | None = None) -> list[str]:
	"""Holders at exactly this node — no walking up, no subtree.

	Expressed through core rather than with a query of our own: `at_level`
	starts its walk at the node it was given, and a node is always the first
	node in its own chain at its own level, so asking core for "this node's
	level, from this node" is exactly "holders here". One source of truth for
	liveness, and no `tabGeo Assignment` query in this app.
	"""
	if not (geo_node and role):
		return []

	level = adapter.get_level(geo_node)

	return resolve_approvers(geo_node, role, rule=RULE_AT_LEVEL, geo_level=level["key"], on_date=on_date)


def escalate(role: str, geo_node: str, exclude: set[str] | None = None, on_date: str | None = None) -> dict:
	"""The nearest holder of `role` above `geo_node` who is not already late.

	    Walks the ancestors nearest-first and skips any node whose only holders are
	    in `exclude` — the people the document was already routed to. Escalating to
	    the person who is late is the bug this signature exists to prevent: they had
	    their SLA, and handing the same document back to them is not an escalation,
	    it is a loop.

	Returns `{"approvers": [...], "node": <where they were found>}`, with an
	empty list when nobody above holds the role. Nobody above is a real answer:
	the top of the tree has nobody to escalate to, and inventing a fallback
	approver — the site's administrator, say — would put a decision in the hands
	of whoever installed the software.
	"""
	exclude = exclude or set()

	if not (role and geo_node):
		return {"approvers": [], "node": None}

	for ancestor in adapter.get_ancestors(geo_node):
		fresh = [user for user in holders_exactly_at(ancestor.name, role, on_date) if user not in exclude]

		if fresh:
			return {"approvers": fresh, "node": ancestor.name}

	return {"approvers": [], "node": None}


def is_complete(stage, routed_approvers: list[str], approved_by: set[str]) -> bool:
	"""Has this stage had enough decisions to advance?

	`single` and `any_of` need one; `all_of` needs every routed approver. An
	`all_of` stage with nobody routed is **never** complete — that is the case
	the guardrail is about, and returning True here would let a stage nobody
	could act on approve itself.
	"""
	if stage.completion_rule == COMPLETION_ALL_OF:
		return bool(routed_approvers) and set(routed_approvers) <= approved_by

	return bool(approved_by)
