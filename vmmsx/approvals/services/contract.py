# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What a doctype must provide to be approvable — and how the engine reads it.

The engine is generic. It governs Volunteer Application, Membership,
Deployment Request and anything a later module invents, and it may not name any
of them — the same inversion core uses for scopeable doctypes. What it can do
is state a contract, check it once, and refuse a workflow whose governed
doctype does not meet it.

The contract is four fields plus the geo anchor:

    approval_state              Select or Data — the state, from `states.py`
    approval_stage              Data           — opaque row name of the current stage
    approval_stage_entered_on   Datetime       — the SLA clock for that stage
    <a Table field of VMMS Approval Decision>  — the audit trail
    <the geo anchor Link>       named by the workflow's `geo_node_field` (ACC-02)

Three of those are read-only to a user and written only here. The decisions
table is discovered by its `options` rather than by a fixed fieldname, because
a module may reasonably want to call it `approval_history`; the state fields are
fixed names because code reads them on doctypes it has never heard of, and one
configurable fieldname per concept is one more thing that can be misconfigured
into a silent no-op.

Nothing in this module knows what a stage is called or what a society named its
roles. It moves values between the engine and a document.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from vmmsx.approvals import states

STATE_FIELD = "approval_state"
STAGE_FIELD = "approval_stage"
STAGE_ENTERED_FIELD = "approval_stage_entered_on"

DECISION_DOCTYPE = "VMMS Approval Decision"

REQUIRED_FIELDS = (
	(STATE_FIELD, ("Select", "Data")),
	(STAGE_FIELD, ("Data",)),
	(STAGE_ENTERED_FIELD, ("Datetime",)),
)


def describe() -> str:
	"""The contract in one sentence, for error messages. Documentation that throws."""
	return _(
		"An approvable doctype needs: {0} (Select or Data), {1} (Data), {2} (Datetime),"
		" and a Table field of {3}."
	).format(
		frappe.bold(STATE_FIELD),
		frappe.bold(STAGE_FIELD),
		frappe.bold(STAGE_ENTERED_FIELD),
		frappe.bold(DECISION_DOCTYPE),
	)


def assert_approvable(doctype: str) -> None:
	"""Throw unless `doctype` can carry an approval.

	Called when a workflow is saved, so a misconfiguration surfaces while an
	administrator is looking at the form — not months later when the first
	application is submitted and the engine writes a field that is not there.
	"""
	meta = frappe.get_meta(doctype)
	missing = []

	for fieldname, fieldtypes in REQUIRED_FIELDS:
		field = meta.get_field(fieldname)

		if not field:
			missing.append(f"{fieldname} ({'/'.join(fieldtypes)})")
		elif field.fieldtype not in fieldtypes:
			missing.append(f"{fieldname} (is {field.fieldtype}, must be {'/'.join(fieldtypes)})")

	if not _decision_table_field(meta):
		missing.append(f"a Table field of {DECISION_DOCTYPE}")

	if missing:
		frappe.throw(
			_("{0} cannot be approved: it is missing {1}. {2}").format(
				frappe.bold(doctype), ", ".join(missing), describe()
			),
			frappe.MandatoryError,
			title=_("Doctype Not Approvable"),
		)


def decisions_field(doctype: str) -> str:
	"""Fieldname of the decisions table on `doctype`."""
	field = _decision_table_field(frappe.get_meta(doctype))

	if not field:
		frappe.throw(
			_("{0} has no {1} table. {2}").format(frappe.bold(doctype), DECISION_DOCTYPE, describe()),
			frappe.MandatoryError,
			title=_("Doctype Not Approvable"),
		)

	return field.fieldname


def _decision_table_field(meta):
	"""First Table field pointing at VMMS Approval Decision, or None."""
	for field in meta.get_table_fields():
		if field.options == DECISION_DOCTYPE:
			return field

	return None


# --- reading and writing the engine's own fields --------------------------


def state(doc) -> str:
	"""The document's state. An empty field reads as Draft, never as nothing."""
	return doc.get(STATE_FIELD) or states.DRAFT


def set_state(doc, target: str) -> None:
	"""Move to `target`, through the transition grammar.

	Every state change in the engine comes through here, which is what makes
	`states.TRANSITIONS` the whole grammar rather than a diagram that drifted.
	"""
	states.assert_transition(state(doc), target)
	doc.set(STATE_FIELD, target)


def stage(doc) -> str | None:
	"""Opaque row name of the stage under review, or None."""
	return doc.get(STAGE_FIELD) or None


def set_stage(doc, stage_name: str | None, entered_on=None) -> None:
	"""Point the document at a stage and start that stage's clock.

	Clearing the stage (None) also clears the clock: a document with no stage
	has no SLA, and a stale timestamp would make a terminal application look
	overdue forever.
	"""
	doc.set(STAGE_FIELD, stage_name)
	doc.set(STAGE_ENTERED_FIELD, (entered_on or now_datetime()) if stage_name else None)


def stage_entered_on(doc):
	return doc.get(STAGE_ENTERED_FIELD)


def decisions(doc) -> list:
	"""The audit trail, oldest first."""
	return doc.get(decisions_field(doc.doctype)) or []


def decisions_at(doc, stage_name: str) -> list:
	return [row for row in decisions(doc) if row.stage == stage_name]


def record_decision(doc, stage_row, user: str, decision: str, reason: str | None) -> None:
	"""Append one decision to the audit trail.

	`stage_label` is snapshotted rather than looked up later: a society that
	relabels a stage next year must not thereby rewrite what happened this
	year. The label is stored for humans; `stage` is what code uses.
	"""
	doc.append(
		decisions_field(doc.doctype),
		{
			"stage": stage_row.name,
			"stage_sequence": stage_row.sequence,
			"stage_label": stage_row.stage_label,
			"approver": user,
			"decision": decision,
			"reason": reason,
			"decided_on": now_datetime(),
		},
	)
