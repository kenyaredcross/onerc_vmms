# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Stipend approval — present, submittable, and an honest dead end.

**This is a stub, and it says so out loud.** A progress report or a payment form
can be submitted. It then sits in `Pending Departmental Approval` and **nobody
can approve it, including an administrator**. An attempt is refused with a
message naming what is missing and what it waits for. That is the whole feature,
and it is deliberately the whole feature.

Why it is not wired to the approval engine
------------------------------------------

The stipend chain is **supervisor to head of department**. The head of department
is the head of the *volunteer's* department, and a department is not a place.

`vmmsx/approvals` resolves approvers by walking **upward through geo**: it asks
core who holds a named role at, or above, the document's Geo Node. Point this
module at it and every stipend report would route successfully, promptly, and to
the wrong person — a branch or county coordinator standing above the report in
the geo tree, who is not the head of anybody's department. A wrong approver who
approves is far worse than no approver at all: the paperwork comes back signed,
the audit trail says a decision was taken, and nothing anywhere records that the
person who took it had no standing to.

So the engine is not called, no `VMMS Approval Workflow` governs these doctypes,
and these doctypes deliberately do **not** satisfy the engine's document
contract — there is no `approval_stage`, no `approval_stage_entered_on` and no
decisions table on either of them. That absence is the guard: a workflow cannot
be pointed at a doctype that does not meet the contract, so nobody can wire this
to geo routing by configuration alone, and doing it in code means adding fields
whose absence is asserted by this module's tests.

Departmental resolution belongs to the delegation subsystem, which does not
exist. Building half of it here — a settings field naming a head-of-department
role, say, resolved against geo — would produce exactly the confident wrong
answer described above.

What is here instead
--------------------

* a two-value lifecycle, in code, closed: `Draft` and
  `Pending Departmental Approval`;
* `submit()` and `withdraw()`, both idempotent, so a supervisor can put the
  paperwork up and take it back;
* `decide()`, which **always refuses**, with `PENDING_ROUTING_REFUSAL`;
* the routing target recorded on the report by
  `stipend/services/department.py`, so the subsystem that eventually resolves a
  head of department inherits an answer rather than a blank.

**There is no terminal state**, and that is the honest shape rather than an
omission: the only ways out of `Pending Departmental Approval` are approval and
rejection, neither of which exists. Adding an `Approved` value nobody can reach
would put a lie in a Select. When departmental routing arrives, this module is
what it replaces.

Nothing here branches on a role name, a department name or a stage label. There
are no stages: stages are the engine's, and this does not use the engine.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

STATE_FIELD = "approval_state"
SUBMITTED_ON_FIELD = "submitted_on"
SUBMITTED_BY_FIELD = "submitted_by"

# Set by `submit()` and `withdraw()` for the duration of the save they perform,
# and by nothing else. A state change arriving without it did not come through
# this module, which means it skipped the preconditions a move has — a report
# has to cover somebody before it goes up — and it is refused. The flag is a
# door, not a permission: it is set on the document being saved and dropped
# again the moment the save returns.
STATE_MOVE_FLAG = "stipend_state_move"

DRAFT = "Draft"
PENDING_DEPARTMENTAL = "Pending Departmental Approval"

STATES = (DRAFT, PENDING_DEPARTMENTAL)

# The whole grammar. Deliberately small, and deliberately without a terminal
# state: the two moves that would end this lifecycle are approval and rejection,
# and neither is built.
TRANSITIONS: dict[str, tuple[str, ...]] = {
	DRAFT: (PENDING_DEPARTMENTAL,),
	PENDING_DEPARTMENTAL: (DRAFT,),
}

# The refusal, as one constant, so that the message a caller sees and the message
# a test asserts on are the same string rather than two that drifted apart.
PENDING_ROUTING_REFUSAL = (
	"Stipend approval runs from the supervisor to the head of the volunteer's department, and"
	" departmental routing is not built yet. It is not routed through the geo approval engine"
	" instead, because that engine resolves approvers by walking up the geo tree and would send"
	" this to a geo parent rather than to a head of department, which would look approved and"
	" would not be. This paperwork stays in Pending Departmental Approval until the delegation"
	" subsystem can resolve a head of department."
)

# What a caller is told about the state they are in, returned in every DTO so a
# reader never has to infer the dead end from a state name.
PENDING_NOTE = (
	"Submitted and waiting. Nobody can approve this yet, including an administrator: departmental"
	" approval routing has not been built. The departments it would route to are recorded on the"
	" report."
)


def state(doc) -> str:
	"""The document's state. An empty field reads as Draft, never as nothing."""
	return doc.get(STATE_FIELD) or DRAFT


def is_pending(doc) -> bool:
	return state(doc) == PENDING_DEPARTMENTAL


def can_transition(current: str | None, target: str) -> bool:
	return target in TRANSITIONS.get(current or DRAFT, ())


def assert_transition(current: str | None, target: str) -> None:
	"""Throw unless the move is legal. The single chokepoint for state changes."""
	if target not in STATES:
		frappe.throw(
			_("{0} is not a stipend approval state. Expected one of: {1}.").format(
				frappe.bold(target), ", ".join(STATES)
			),
			frappe.ValidationError,
			title=_("Unknown Approval State"),
		)

	if can_transition(current, target):
		return

	frappe.throw(
		_("Stipend paperwork cannot go from {0} to {1}.").format(
			frappe.bold(_(current or DRAFT)), frappe.bold(_(target))
		),
		frappe.ValidationError,
		title=_("Invalid Approval Transition"),
	)


def assert_stored_transition(doc) -> None:
	"""Refuse a state that was set on the document rather than moved to.

	Called from both controllers' `validate`, which makes the grammar above the
	whole grammar rather than a diagram the services happen to follow. The field
	is read-only on the form, so this is not about the desk; it is about a script
	assigning `approval_state` and saving, which would otherwise walk straight
	past `submit()` and `withdraw()`.

	A brand new document may be created in any legal starting state, which is
	Draft or nothing at all.
	"""
	target = state(doc)

	if doc.is_new():
		if target == DRAFT:
			return

		frappe.throw(
			_("New stipend paperwork starts at {0}. Submit it instead of setting its state.").format(
				frappe.bold(_(DRAFT))
			),
			frappe.ValidationError,
			title=_("Invalid Approval Transition"),
		)

	stored = frappe.db.get_value(doc.doctype, doc.name, STATE_FIELD) or DRAFT

	if target == stored:
		return

	if not doc.flags.get(STATE_MOVE_FLAG):
		frappe.throw(
			_(
				"The approval state is moved by submitting or withdrawing, not by setting it. Setting"
				" it directly would skip what a move checks first."
			),
			frappe.ValidationError,
			title=_("Approval State Is Not Set By Hand"),
		)

	assert_transition(stored, target)


def assert_unchanged_while_pending(doc, signature, what: str) -> None:
	"""Refuse a substantive edit to paperwork that is sitting with an approver.

	Submitted paperwork is somebody else's to decide, so its substance is frozen
	until it is taken back. The one move out is `withdraw()`, and a save that is
	itself the withdrawal passes here because the document's state is already back
	at Draft by the time this runs.

	`signature` is a callable turning a document into something comparable. A
	callable rather than a fieldname because the fields that matter are child
	tables, and two lists of freshly loaded child rows never compare equal by
	identity however unchanged they are.
	"""
	if doc.is_new() or not is_pending(doc):
		return

	before = doc.get_doc_before_save()

	if before is None or not is_pending(before):
		# The save that submitted it. What is being frozen is what was submitted,
		# so the submission itself cannot be the thing that breaks the rule.
		return

	if signature(doc) == signature(before):
		return

	frappe.throw(
		_("This has been submitted, so {0} cannot change. Withdraw it back to {1} first.").format(
			what, frappe.bold(_(DRAFT))
		),
		frappe.ValidationError,
		title=_("Submitted Paperwork Is Frozen"),
	)


# --- the moves that exist -------------------------------------------------


def submit(doc) -> dict:
	"""Put this paperwork up for approval. Idempotent.

	Idempotent in the way every service in this app is: a second call observes
	that the work is done and returns the same answer, rather than re-stamping who
	submitted it and when. Saving is the caller's, because both controllers
	re-derive fields on save and a nested save here would re-enter that.
	"""
	if is_pending(doc):
		return status(doc)

	assert_transition(state(doc), PENDING_DEPARTMENTAL)

	doc.set(STATE_FIELD, PENDING_DEPARTMENTAL)
	doc.set(SUBMITTED_ON_FIELD, now_datetime())
	doc.set(SUBMITTED_BY_FIELD, frappe.session.user)
	_save_move(doc)

	return status(doc)


def withdraw(doc) -> dict:
	"""Take it back to Draft. Idempotent.

	The one move out of the pending state, and it exists because the alternative
	is paperwork that can be neither approved nor corrected. The submission stamps
	are cleared with it, so `submitted_on` always describes a submission that is
	currently outstanding rather than one somebody took back.
	"""
	if not is_pending(doc):
		return status(doc)

	assert_transition(state(doc), DRAFT)

	doc.set(STATE_FIELD, DRAFT)
	doc.set(SUBMITTED_ON_FIELD, None)
	doc.set(SUBMITTED_BY_FIELD, None)
	_save_move(doc)

	return status(doc)


def _save_move(doc) -> None:
	"""Save a document whose state this module has just moved.

	The flag is set for exactly the duration of the save and dropped whether it
	succeeded or not, so a document held in memory afterwards cannot be saved a
	second time with a hand-set state and be let through on a leftover flag.
	"""
	doc.flags[STATE_MOVE_FLAG] = True

	try:
		doc.save()
	finally:
		doc.flags.pop(STATE_MOVE_FLAG, None)


def decide(doc, decision: str | None = None, reason: str | None = None) -> dict:
	"""Approve or reject. **Always refuses.**

	The arguments are named and ignored on purpose: this is the shape the call
	will have when departmental routing exists, so the endpoint that eventually
	works is the endpoint that refuses today, rather than a new one appearing and
	callers having to find it.

	Refused for everybody. There is no administrator path, no `ignore_permissions`
	equivalent and no override argument, because the thing that is missing is not
	permission — it is the answer to *who*.
	"""
	frappe.throw(
		_(PENDING_ROUTING_REFUSAL),
		frappe.ValidationError,
		title=_("Departmental Approval Not Built"),
	)


# --- reading --------------------------------------------------------------


def status(doc) -> dict:
	"""Where this paperwork stands. An explicit DTO, built field by field."""
	pending = is_pending(doc)

	return {
		"doctype": doc.doctype,
		"name": doc.name,
		"approval_state": state(doc),
		"is_pending": pending,
		# Constants, not computations. Nobody may decide this, and saying so in
		# the payload means a UI does not have to infer it from a state name.
		"can_be_decided": False,
		"can_be_withdrawn": pending,
		"blocked_because": PENDING_ROUTING_REFUSAL,
		"note": PENDING_NOTE if pending else None,
		"submitted_on": doc.get(SUBMITTED_ON_FIELD),
		"submitted_by": doc.get(SUBMITTED_BY_FIELD),
	}
