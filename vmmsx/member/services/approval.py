# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""MEM-02 — how a membership becomes approved, selected by configuration.

A membership type carries one field, `approval_mode`, and that field is the
whole of the decision:

    routed             the VMMS approval engine routes it to a resolved person,
                       who approves or rejects it
    auto_on_payment    there is no approver; confirmed payment is the approval

**Nothing here branches on a membership type's name, and nothing branches on a
stage's label.** The two tables at the bottom of this module are keyed by the
configuration value itself, so adding a mode is adding an entry, and a society
switching a type from routed to auto-on-payment is a settings change that no
source file knows happened. This is the same shape the approval engine proved
with Kenya and The Gambia: one code path, configuration alone deciding the
outcome.

**Routing is delegated entirely.** This module never resolves an approver, never
touches `tabGeo Assignment`, and never queries geo. It calls
`approvals.services.engine`, which calls core. Two resolvers would eventually
disagree, and the day they did, memberships would route to people who cannot
open them.
"""

import frappe
from frappe import _

from vmmsx.approvals import states
from vmmsx.approvals.services import contract, engine

MODE_ROUTED = "routed"
MODE_AUTO_ON_PAYMENT = "auto_on_payment"
MODES = (MODE_ROUTED, MODE_AUTO_ON_PAYMENT)


def mode(membership_type) -> str:
	"""The configured approval mode, refusing one nobody defined."""
	configured = membership_type.approval_mode

	if configured in MODES:
		return configured

	frappe.throw(
		_("{0} is not an approval mode on membership type {1}. Expected one of: {2}.").format(
			frappe.bold(configured), frappe.bold(membership_type.name), ", ".join(MODES)
		),
		frappe.ValidationError,
		title=_("Unknown Approval Mode"),
	)


def begin(membership, membership_type) -> None:
	"""Start whatever this type's mode requires. Idempotent.

	Looked up rather than branched: `_BEGIN[mode]`. There is no `if` on a type
	name anywhere in this file.
	"""
	_BEGIN[mode(membership_type)](membership)


def is_settled(membership, membership_type) -> bool:
	"""Has this membership's approval requirement been met?

	One half of the activation predicate — the other is payment. Both are
	questions about configuration, not about which code path ran, which is what
	makes activation safe to re-evaluate after any event and in any order.
	"""
	return _SETTLED[mode(membership_type)](membership)


def requires_approver(membership_type) -> bool:
	"""Whether this type needs a human at all. For a DTO, never for a branch."""
	return mode(membership_type) == MODE_ROUTED


# --- routed ---------------------------------------------------------------


def _begin_routed(membership) -> None:
	"""Hand the document to the approval engine and let it route.

	`engine.submit` enforces the anchor rules, resolves approvers through core,
	moves the approval state and assigns the document — all of it. It is
	idempotent: a membership already in review is re-synced, not restarted.
	"""
	if states.is_terminal(contract.state(membership)):
		return

	engine.submit(membership)


def _settled_routed(membership) -> bool:
	return contract.state(membership) == states.APPROVED


# --- auto on payment ------------------------------------------------------


def _begin_auto(membership) -> None:
	"""Nothing to start. Payment confirmation is the whole approval."""


def _settled_auto(membership) -> bool:
	"""Always true: this type asked for no approver.

	Activation still waits for payment — that requirement is the payment
	predicate's to answer, and keeping the two separate is what stops
	"no approver needed" from quietly meaning "no payment needed".
	"""
	return True


# --- the dispatch tables --------------------------------------------------
#
# Keyed by the configuration value. A mode is added by adding a row here, and
# never by adding a branch to a caller.

_BEGIN = {
	MODE_ROUTED: _begin_routed,
	MODE_AUTO_ON_PAYMENT: _begin_auto,
}

_SETTLED = {
	MODE_ROUTED: _settled_routed,
	MODE_AUTO_ON_PAYMENT: _settled_auto,
}
