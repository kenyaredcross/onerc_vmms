# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The project's own lifecycle, and what a caller is told about one.

Same shape as `deployment.py`, and for the same reason: **statuses are code,
the work is configuration**. The four values below are a closed set with a fixed
transition table, because each one means something the server acts on. What a
society varies is *which programmes it runs*, and that is the records, on which
no code anywhere branches.

**A project decides nothing about a deployment.** It is the container a terms of
reference is written under, and containment is the whole of the relationship: a
Completed project keeps every deployment already run under it, and closing one
is not a way to stop work that is already in the field. The rule this module
does hold is the one that stops a *new* terms of reference being written under a
programme that has ended, which is `assert_open`.

**A deployment reaches its project through its terms.** There is no second link
and there must not be one: two paths to the same answer are two answers as soon
as somebody edits one of them.
"""

import frappe
from frappe import _
from frappe.utils import getdate

PROJECT_DOCTYPE = "VMMS Project"

STATUS_PLANNED = "Planned"
STATUS_ACTIVE = "Active"
STATUS_COMPLETED = "Completed"
STATUS_CANCELLED = "Cancelled"

STATUSES = (STATUS_PLANNED, STATUS_ACTIVE, STATUS_COMPLETED, STATUS_CANCELLED)

OPEN_STATUSES = (STATUS_PLANNED, STATUS_ACTIVE)
TERMINAL_STATUSES = (STATUS_COMPLETED, STATUS_CANCELLED)

TRANSITIONS: dict[str, tuple[str, ...]] = {
	# Every open status admits itself, because saving a project without moving it
	# is the commonest thing that happens to one. Those are real transitions.
	STATUS_PLANNED: (STATUS_PLANNED, STATUS_ACTIVE, STATUS_COMPLETED, STATUS_CANCELLED),
	STATUS_ACTIVE: (STATUS_ACTIVE, STATUS_COMPLETED, STATUS_CANCELLED),
	STATUS_COMPLETED: (STATUS_COMPLETED,),
	STATUS_CANCELLED: (STATUS_CANCELLED,),
}


def read(name: str):
	"""The project record, through the document cache. Treat as read-only."""
	return frappe.get_cached_doc(PROJECT_DOCTYPE, name)


# --- the status ------------------------------------------------------------


def assert_status(status: str | None) -> None:
	"""Throw unless `status` is one of the four."""
	if status in STATUSES:
		return

	frappe.throw(
		_("{0} is not a project status. Expected one of: {1}.").format(
			frappe.bold(status), ", ".join(STATUSES)
		),
		frappe.ValidationError,
		title=_("Unknown Project Status"),
	)


def can_transition(current: str | None, target: str) -> bool:
	"""Is `current` to `target` in the grammar? An unset status counts as Planned."""
	return target in TRANSITIONS.get(current or STATUS_PLANNED, ())


def assert_transition(current: str | None, target: str) -> None:
	"""Throw unless the move is legal. The single chokepoint for status changes."""
	assert_status(target)

	if can_transition(current, target):
		return

	if current in TERMINAL_STATUSES:
		frappe.throw(
			_("This project is {0}. A project that has ended cannot be moved again.").format(
				frappe.bold(_(current))
			),
			frappe.ValidationError,
			title=_("Project Already Ended"),
		)

	frappe.throw(
		_("A project cannot go from {0} to {1}.").format(
			frappe.bold(_(current or STATUS_PLANNED)), frappe.bold(_(target))
		),
		frappe.ValidationError,
		title=_("Invalid Project Transition"),
	)


def set_status(doc, target: str, reason: str | None = None) -> dict:
	"""Move a project's status and save it. Idempotent.

	Idempotent because the table admits every status to itself: asking for the
	status a project already has writes nothing and records nothing.
	"""
	if doc.status == target:
		return dto(doc)

	assert_transition(doc.status, target)
	doc.status = target
	doc.save()

	if reason:
		doc.add_comment("Comment", _("{0}. {1}").format(_(target), reason))

	return dto(doc)


def is_open(doc) -> bool:
	return doc.status in OPEN_STATUSES


def assert_open(name: str) -> None:
	"""Throw unless new work may still be written under this project.

	Checked when a terms of reference is written under a project, and never
	afterwards. A closed project keeps everything already run under it, because
	ending a programme must not erase the record that it happened. Same rule, and
	the same reason, as `terms.assert_active`.
	"""
	if not name:
		return

	doc = read(name)

	if is_open(doc):
		return

	frappe.throw(
		_("{0} is {1} and cannot take new terms of reference.").format(
			frappe.bold(doc.project_name or doc.name), frappe.bold(_(doc.status))
		),
		frappe.ValidationError,
		title=_("Project Closed"),
	)


# --- creating one ----------------------------------------------------------


def create(
	project_name: str,
	geo_node: str,
	start_date=None,
	end_date=None,
	summary: str | None = None,
	notes: str | None = None,
	status: str | None = None,
):
	"""Insert a project. An ordinary insert, deliberately.

	No elevation: core's query condition runs on the anchor, so a coordinator
	cannot file a programme outside their own area, and the refusal comes from
	the same permission layer that decides everything else about placement. The
	controller holds the coherence rules; this holds the shape of the call.
	"""
	if not geo_node:
		# ACC-02 restated at the boundary rather than left to the mandatory check,
		# so a caller gets a sentence about placement instead of a field name.
		frappe.throw(
			_("A project must be anchored to a place in the organisation before it can be saved."),
			frappe.MandatoryError,
			title=_("Where Is This Project?"),
		)

	doc = frappe.get_doc(
		{
			"doctype": PROJECT_DOCTYPE,
			"project_name": project_name,
			"geo_node": geo_node,
			"status": status or STATUS_PLANNED,
			"start_date": getdate(start_date) if start_date else None,
			"end_date": getdate(end_date) if end_date else None,
			"summary": summary,
			"notes": notes,
		}
	)
	doc.insert()

	return doc


# --- describing one --------------------------------------------------------


def dto(doc) -> dict:
	"""One project, as an explicit dict. Built field by field.

	Never the Document: that would leak every field on the record, including ones
	nobody reviewed, and turn a schema change into an API change.
	"""
	from onerc_core.geo.services import adapter

	return {
		"name": doc.name,
		"project_name": doc.project_name,
		"status": doc.status,
		"is_open": is_open(doc),
		"geo_node": doc.geo_node,
		"geo_path": adapter.get_full_path(doc.geo_node) if doc.geo_node else None,
		"start_date": str(doc.start_date) if doc.start_date else None,
		"end_date": str(doc.end_date) if doc.end_date else None,
		"summary": doc.summary,
		"notes": doc.notes,
		"created_on": str(doc.creation) if doc.creation else None,
	}
