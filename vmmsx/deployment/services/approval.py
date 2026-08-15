# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Whether a deployment decision needs a person, selected by configuration.

Two records in this module can be gated by an approval, and neither is gated by
default:

    VMMS Deployment Request   the mode is on its Terms of Reference, so a
                              society may route international deployments and
                              wave through a branch first-aid duty
    VMMS Branch Transfer      the mode is one society-wide setting, because a
                              transfer has no "type" to hang it off

Both read the same two values and dispatch through the same two tables:

    direct    there is no approver. The requirement is settled the moment it is
              asked about, and what happens next is governed by the operational
              predicate rather than by anybody's decision
    routed    the VMMS approval engine routes it to a resolved person, who
              approves or rejects it, exactly as it routes a volunteer
              application or a membership

**Nothing here branches on a Terms of Reference name, and nothing branches on a
stage's label.** The two tables at the bottom are keyed by the configuration
value itself, so adding a mode is adding an entry, and a society switching a
terms of reference from direct to routed is a settings change that no source
file knows happened. This is the shape `member/services/approval.py` proved with
`approval_mode` on a membership type, deliberately reused rather than reinvented.

**Routing is delegated entirely.** This module never resolves an approver, never
touches `tabGeo Assignment`, and never queries geo. It calls
`approvals.services.engine`, which calls core. Two resolvers would eventually
disagree, and the day they did, deployments would route to people who cannot
open them. `deployment/tests/test_delegation.py` walks the AST and fails if this
module grows one.

**The direct mode leaves the approval state alone.** A request in `direct` mode
stays at `Draft` and is fulfilled anyway, because the absence of an approval is
not an approval and writing `Approved` onto a record nobody approved would be a
lie in an audit trail. `_settled_direct` answers the question the predicate
actually asks, which is "is anything still owed here", and the answer is no.
"""

import frappe
from frappe import _

from vmmsx.approvals import states
from vmmsx.approvals.services import contract, engine

MODE_DIRECT = "direct"
MODE_ROUTED = "routed"
MODES = (MODE_DIRECT, MODE_ROUTED)


def assert_mode(configured: str | None, where: str) -> str:
	"""Return the mode, refusing one nobody defined.

	`where` names the record the value came from, so a misconfiguration says
	which terms of reference or which setting to go and fix rather than leaving
	somebody to find it.
	"""
	if configured in MODES:
		return configured

	frappe.throw(
		_("{0} is not an approval mode on {1}. Expected one of: {2}.").format(
			frappe.bold(configured), frappe.bold(where), ", ".join(MODES)
		),
		frappe.ValidationError,
		title=_("Unknown Approval Mode"),
	)


def begin(doc, mode: str, where: str) -> None:
	"""Start whatever this mode requires. Idempotent.

	Looked up rather than branched: `_BEGIN[mode]`. There is no `if` on a terms
	of reference name anywhere in this file.
	"""
	_BEGIN[assert_mode(mode, where)](doc)


def is_settled(doc, mode: str, where: str) -> bool:
	"""Has this record's approval requirement been met?

	A question about configuration, not about which code path ran, which is what
	makes the operational predicates that read it safe to re-evaluate after any
	event and in any order.
	"""
	return _SETTLED[assert_mode(mode, where)](doc)


def requires_approver(mode: str, where: str) -> bool:
	"""Whether this mode needs a human at all. For a DTO, never for a branch."""
	return assert_mode(mode, where) == MODE_ROUTED


def is_refused(doc) -> bool:
	"""Has an approver closed this record against the applicant?

	Read by the operational predicates so that a rejected request is not merely
	unsettled but finished. Withdrawn and Expired are terminal in the same way:
	none of the three will ever settle, and treating them as "still waiting"
	would leave a record that nothing can move and nothing will ever close.

	True only for a record the engine actually moved. A `direct` record sits at
	Draft forever and is refused by nobody.
	"""
	state = contract.state(doc)

	return states.is_terminal(state) and state != states.APPROVED


# --- direct ---------------------------------------------------------------


def _begin_direct(doc) -> None:
	"""Nothing to start. This society asked for no approver on this work."""


def _settled_direct(doc) -> bool:
	"""Always true: nothing is owed.

	Whether the record then does anything is the operational predicate's
	question. Keeping the two separate is what stops "no approver needed" from
	quietly meaning "no other requirement either".
	"""
	return True


# --- routed ---------------------------------------------------------------


def _begin_routed(doc) -> None:
	"""Hand the document to the approval engine and let it route.

	`engine.submit` enforces the anchor rules, resolves approvers through core,
	moves the approval state and assigns the document. It is idempotent: a record
	already in review is re-synced, not restarted.
	"""
	if states.is_terminal(contract.state(doc)):
		return

	engine.submit(doc)


def _settled_routed(doc) -> bool:
	return contract.state(doc) == states.APPROVED


# --- the dispatch tables --------------------------------------------------
#
# Keyed by the configuration value. A mode is added by adding a row here, and
# never by adding a branch to a caller.

_BEGIN = {
	MODE_DIRECT: _begin_direct,
	MODE_ROUTED: _begin_routed,
}

_SETTLED = {
	MODE_DIRECT: _settled_direct,
	MODE_ROUTED: _settled_routed,
}
