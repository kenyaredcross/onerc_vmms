# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Only the approval engine moves an application.

`approval_state`, `approval_stage`, `approval_stage_entered_on` and the
decisions table are read-only on the form, and that is a form hint, nothing
more. Frappe does not refuse a read-only field on save, so anybody holding
write permission on the record could set `approval_state` to Approved through
the REST API and skip every stage, every approver and the audit trail. On a
membership that made it Active with no decision recorded, and a regional
approval stage would have been one `set_value` away from being skipped by the
county stage before it.

So a save made **with permission checks** (a person, through the desk, the REST
API or a whitelisted method) may not change those fields unless the engine
itself is making it: `engine._save_transition` raises
`frappe.flags.vmms_approval_transition` for exactly the document it saves.
A save made with `ignore_permissions` is the application's own code acting on
purpose (an import, a migration loader), and that is left alone, as the rest of
the framework leaves it alone.

The service certificate request has carried this rule in its own controller
since it was built, with its own wording, and keeps it. This is the same rule for
every other doctype the engine governs.
"""

import datetime
import re

import frappe
from frappe import _
from frappe.utils import get_datetime

from vmmsx.approvals import states
from vmmsx.approvals.services import contract

ENGINE_FIELDS = (contract.STATE_FIELD, contract.STAGE_FIELD, contract.STAGE_ENTERED_FIELD)
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}")
DECISION_FIELDS = ("stage", "stage_label", "stage_sequence", "approver", "decision", "reason", "decided_on")


def validate(doc, method=None) -> None:
	"""`doc_events` validate hook for every engine-governed doctype."""
	if doc.flags.ignore_permissions or is_engine_transition(doc):
		return

	if not moved_outside_engine(doc):
		return

	frappe.throw(
		_("Use Approve, Reject or Request more information to record a decision."),
		frappe.PermissionError,
		title=_("Decision Not Recorded"),
	)


def is_engine_transition(doc) -> bool:
	"""Is the engine saving this very document right now?"""
	return frappe.flags.vmms_approval_transition == (doc.doctype, doc.name)


def moved_outside_engine(doc) -> bool:
	"""Do this save's engine-owned fields differ from what is stored?

	A new document is compared with a blank one: it may arrive as a Draft and
	nothing else. Arriving already Approved, already in a stage, or carrying a
	decision is a decision nobody made.
	"""
	before = None if doc.is_new() else doc.get_doc_before_save()

	if before is None:
		return (
			contract.state(doc) != states.DRAFT
			or bool(doc.get(contract.STAGE_FIELD))
			or bool(doc.get(contract.STAGE_ENTERED_FIELD))
			or bool(contract.decisions(doc))
		)

	if contract.state(doc) != contract.state(before):
		return True

	for field in ENGINE_FIELDS[1:]:
		if _comparable(doc.get(field)) != _comparable(before.get(field)):
			return True

	return _decision_rows(doc) != _decision_rows(before)


def _decision_rows(doc) -> list:
	return [[_comparable(row.get(field)) for field in DECISION_FIELDS] for row in contract.decisions(doc)]


def _comparable(value):
	"""Datetimes come back from the database as objects and from a form as strings."""
	if value in (None, ""):
		return None

	if isinstance(value, datetime.datetime | datetime.date):
		return get_datetime(value)

	if isinstance(value, str) and _DATETIME.match(value):
		return get_datetime(value)

	return str(value)
