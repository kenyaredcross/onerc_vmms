# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The canonical, closed set of approval states — and the only place they live.

Frappe's native Workflow gates a transition on a role plus a `safe_eval`
condition that cannot call our code. It can ask *does this user hold County
Coordinator*; it cannot ask *is this user the specific person this document
routed to*. Role membership is not authorisation here, so the state machine is
ours, in code, and this module is it.

Two rules hold, and the tests are written to break them:

1. **States are code; stages are configuration.** A state is one of the seven
   below — a closed set, a fixed transition table, no society may add an
   eighth. A *stage* is a row in `VMMS Approval Stage`, named by a society,
   ordered by `sequence`, and **nothing in this app branches on a stage's
   label**. `tests/test_no_stage_branching.py` walks the AST of every source
   file and fails if one does.
2. **Every state change goes through `assert_transition`.** The table below is
   the whole grammar of the lifecycle: if a path is not in it, no service may
   invent it locally.

`docstatus` is deliberately unused. An approvable document stays at
`docstatus = 0` and its lifecycle is the state below — submit/cancel is
Frappe's machinery for a different problem, and mixing the two would put half
the lifecycle somewhere this module cannot see.
"""

import frappe
from frappe import _

DRAFT = "Draft"
SUBMITTED = "Submitted"
IN_REVIEW = "In Review"
APPROVED = "Approved"
REJECTED = "Rejected"
WITHDRAWN = "Withdrawn"
EXPIRED = "Expired"

STATES = (DRAFT, SUBMITTED, IN_REVIEW, APPROVED, REJECTED, WITHDRAWN, EXPIRED)

# Open: the application is still someone's problem. Terminal: it is not, and
# nothing may move it again — a decided application is history, not a record to
# be reopened by editing a field.
OPEN_STATES = (DRAFT, SUBMITTED, IN_REVIEW)
TERMINAL_STATES = (APPROVED, REJECTED, WITHDRAWN, EXPIRED)

# What a decision may say. Also a closed set, and also not a society's to
# extend: "more info requested" returns the application to the applicant, which
# is a lifecycle move, not a comment.
DECISION_APPROVED = "Approved"
DECISION_REJECTED = "Rejected"
DECISION_MORE_INFO = "More info requested"

DECISIONS = (DECISION_APPROVED, DECISION_REJECTED, DECISION_MORE_INFO)

TRANSITIONS: dict[str, tuple[str, ...]] = {
	# Submitted is the entry state. It resolves to In Review in the same
	# transaction, except where every stage is optional and resolves nobody —
	# then a workflow that its society configured to require no approvals
	# approves, which is what it asked for.
	DRAFT: (SUBMITTED, WITHDRAWN, EXPIRED),
	SUBMITTED: (IN_REVIEW, APPROVED, WITHDRAWN, EXPIRED),
	# In Review to In Review is stage advance: the state is unchanged and the
	# stage moved. It is in the table because it is a real transition that the
	# engine performs, not an omission.
	IN_REVIEW: (IN_REVIEW, APPROVED, REJECTED, DRAFT, WITHDRAWN, EXPIRED),
	APPROVED: (),
	REJECTED: (),
	WITHDRAWN: (),
	EXPIRED: (),
}


def is_open(state: str | None) -> bool:
	return state in OPEN_STATES


def is_terminal(state: str | None) -> bool:
	return state in TERMINAL_STATES


def can_transition(current: str | None, target: str) -> bool:
	"""Is `current` → `target` in the grammar?

	An unset state counts as Draft: a document that has never been through the
	engine is a draft, whatever its field happens to hold.
	"""
	return target in TRANSITIONS.get(current or DRAFT, ())


def assert_transition(current: str | None, target: str) -> None:
	"""Throw unless the move is legal. The single chokepoint for state changes."""
	if target not in STATES:
		frappe.throw(
			_("{0} is not an approval state. Expected one of: {1}.").format(
				frappe.bold(target), ", ".join(STATES)
			),
			title=_("Unknown Approval State"),
		)

	if can_transition(current, target):
		return

	if is_terminal(current):
		frappe.throw(
			_("This application is already {0}. A decided application cannot be moved again.").format(
				frappe.bold(_(current))
			),
			frappe.ValidationError,
			title=_("Application Already Decided"),
		)

	frappe.throw(
		_("An application cannot go from {0} to {1}.").format(
			frappe.bold(_(current or DRAFT)), frappe.bold(_(target))
		),
		frappe.ValidationError,
		title=_("Invalid Approval Transition"),
	)


def assert_decision(decision: str) -> None:
	"""Throw unless `decision` is one of the three a stage may record."""
	if decision in DECISIONS:
		return

	frappe.throw(
		_("{0} is not a decision. Expected one of: {1}.").format(frappe.bold(decision), ", ".join(DECISIONS)),
		title=_("Unknown Decision"),
	)
