# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The progress report — one period, one place, many volunteers.

A society's stipend paperwork starts with a narrative: what a branch did over a
fortnight or a month, and who did it. That is one document covering many people,
which is why the volunteers are a child table rather than the report being
per-person. Filed per person, a month's work becomes a stack nobody reads
together, and the payment form would have nothing single to pair with.

**Adding a volunteer goes through the picker, always.** `add_volunteer()` takes
whatever a supervisor typed or clicked, hands it to
`stipend/services/picker.py`, and gets back either a volunteer that session may
see or a refusal. There is no variant that skips the check: the scope guarantee
is a property of there being one door, not of everybody remembering to knock.

**Everything is idempotent.** `add_volunteer()` on somebody already on the report
updates their line rather than adding a second one, and says it changed nothing.
Saving is the caller's, so a caller adding five people saves once.

**Approval is a stub, and this module does not pretend otherwise.** `submit()`
hands over to `stipend/services/approval.py`, which moves the report into
`Pending Departmental Approval` and refuses every attempt to decide it. Read that
module before wiring anything to this one.
"""

import frappe
from frappe import _
from onerc_core.geo.services import adapter

from vmmsx.stipend.services import approval, department, picker

REPORT_DOCTYPE = "VMMS Stipend Progress Report"
VOLUNTEERS_FIELD = "volunteers"


def volunteers_of(doc) -> list[str]:
	"""Every volunteer this report covers, in row order."""
	return [row.volunteer for row in doc.get(VOLUNTEERS_FIELD) or [] if row.volunteer]


def covers(doc, volunteer: str) -> bool:
	return volunteer in set(volunteers_of(doc))


def signature(doc) -> tuple:
	"""What must not change once the report is submitted.

	The people and what they are recorded as having done. Sorted, so reordering
	rows in the grid is not mistaken for rewriting the report.
	"""
	return tuple(
		sorted(
			(row.volunteer, row.activity or "", row.notes or "")
			for row in doc.get(VOLUNTEERS_FIELD) or []
			if row.volunteer
		)
	)


def add_volunteer(doc, identifier: str, activity: str | None = None, notes: str | None = None) -> bool:
	"""Put a volunteer on the report. Idempotent. Returns whether anything changed.

	`identifier` is whatever the supervisor has: a volunteer docname, a Red
	Profile docname, or an email address. It is resolved and scope-checked in one
	call, and a volunteer outside this session's area is refused with a message
	that does not say whether they exist.

	Refused outright while the report is submitted, because its substance is
	somebody else's to decide until it is withdrawn.
	"""
	_assert_draft(doc)

	volunteer = picker.resolve(identifier)
	existing = _row_for(doc, volunteer)

	if existing:
		return _update(existing, activity, notes)

	doc.append(
		VOLUNTEERS_FIELD,
		{"volunteer": volunteer, "activity": activity, "notes": notes},
	)

	return True


def remove_volunteer(doc, volunteer: str) -> bool:
	"""Take a volunteer off the report. Idempotent.

	No scope check, deliberately: removing somebody discloses nothing and refusing
	it would leave a report nobody could correct after an assignment changed.

	Refused, however, while a paired payment form still pays them. The report says
	who the period was about and the form may pay only those people, so taking
	somebody out of the narrative while a form pays them would leave that form
	holding a line its own rules forbid.
	"""
	_assert_draft(doc)
	_assert_nobody_is_paying_them(doc, volunteer)

	rows = doc.get(VOLUNTEERS_FIELD) or []
	remaining = [row for row in rows if row.volunteer != volunteer]

	if len(remaining) == len(rows):
		return False

	doc.set(VOLUNTEERS_FIELD, remaining)

	return True


def submit(doc) -> dict:
	"""Send the report up. Idempotent, and a dead end by design.

	A report covering nobody is refused: the narrative is about people, the
	payment form pays the people it names, and a report with an empty table
	cannot pair with a form that pays anybody.
	"""
	assert_covers_somebody(doc)

	return approval.submit(doc)


def withdraw(doc) -> dict:
	"""Take the report back to Draft so it can be corrected. Idempotent."""
	return approval.withdraw(doc)


def assert_covers_somebody(doc) -> None:
	if volunteers_of(doc):
		return

	frappe.throw(
		_(
			"This report covers nobody. A progress report is a narrative about the volunteers it"
			" names, and the payment form paired with it may pay only those volunteers, so an empty"
			" table would make both documents unusable."
		),
		frappe.MandatoryError,
		title=_("No Volunteers On The Report"),
	)


def status(doc) -> dict:
	"""Everything a caller needs about one report. An explicit DTO, field by field.

	Never a Document and never a raw query result. The approval half is the stub's
	own DTO, which states plainly that nobody can decide this yet, and the routing
	half is the target recorded for the subsystem that eventually will.
	"""
	return {
		"report": doc.name,
		"geo_node": doc.geo_node,
		"geo_path": adapter.get_full_path(doc.geo_node) if doc.geo_node else None,
		"period_from": doc.period_from,
		"period_to": doc.period_to,
		"volunteer_count": len(volunteers_of(doc)),
		"volunteers": [
			{
				"volunteer": row.volunteer,
				"activity": row.activity,
				"notes": row.notes,
				"department": row.department,
			}
			for row in doc.get(VOLUNTEERS_FIELD) or []
		],
		"approval": approval.status(doc),
		"pending_routing": department.describe(doc),
	}


# --- internals ------------------------------------------------------------


def _row_for(doc, volunteer: str):
	for row in doc.get(VOLUNTEERS_FIELD) or []:
		if row.volunteer == volunteer:
			return row

	return None


def _update(row, activity: str | None, notes: str | None) -> bool:
	"""Fill in what a second call supplied, and report whether it was new.

	Only ever adds: a second call that supplies nothing does not blank what the
	first one recorded, because "add them again" is not an instruction to erase.
	"""
	changed = False

	for field, value in (("activity", activity), ("notes", notes)):
		if value and row.get(field) != value:
			row.set(field, value)
			changed = True

	return changed


def _assert_nobody_is_paying_them(doc, volunteer: str) -> None:
	"""Throw while a paired payment form still has a line for this volunteer.

	The payment service is imported here rather than at the top because it imports
	this module: a form is stated in terms of its report, and the one question
	going the other way is this one.
	"""
	from vmmsx.stipend.services import payment as payment_service

	if doc.is_new():
		return

	paying = payment_service.forms_paying(doc.name, volunteer)

	if not paying:
		return

	frappe.throw(
		_(
			"{0} cannot come off this report while {1} still pays them. Take their days off that"
			" form first, or this report would be describing a period that pays somebody it does"
			" not mention."
		).format(frappe.bold(volunteer), frappe.bold(", ".join(paying))),
		frappe.ValidationError,
		title=_("Still Being Paid"),
	)


def _assert_draft(doc) -> None:
	if not approval.is_pending(doc):
		return

	frappe.throw(
		_("This report has been submitted. Withdraw it back to {0} before changing who it covers.").format(
			frappe.bold(_(approval.DRAFT))
		),
		frappe.ValidationError,
		title=_("Submitted Paperwork Is Frozen"),
	)
