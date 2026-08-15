# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The payment form — the money half of a period somebody already described.

A payment form is **paired with a progress report**, and the pairing is what
makes it safe. The report says which days the period covers, where it happened
and who was involved; the form may then pay only those people, only for those
days, and only at that place. Every one of those is checked on every save rather
than at submission, so a form cannot be built wrong and discovered wrong later.

Three fields are **copied from the report on every save and read-only here**:
the two period dates, and by implication the roster the grid is checked against.
Copied rather than fetched once, because a report whose period is corrected must
not leave a form paying for days the report no longer covers. The anchor is the
exception: `geo_node` is held on the form itself, because core's geo scoping
filters each doctype on a field of its own and a form scoped through a link would
be a form nobody could scope. It is checked against the report's anchor instead,
so holding it twice cannot mean holding two different answers.

**The currency is the society's**, read from National Society Settings through
`stipend/services/society.py`. No currency code appears in this module, and a
society that has not configured one gets a form with an empty currency rather
than somebody else's.

**Nothing computes an amount.** There is no rate and no hours-times-rate: what a
day is worth is a society's decision. The form derives one number only, the
total, and derives it from the rows every time. See
`stipend/services/attendance.py` for the shape of the grid and why it is the
shape it is.

**Approval is a stub.** `submit()` moves the form into
`Pending Departmental Approval` and nobody can decide it, including an
administrator. See `stipend/services/approval.py`.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate
from onerc_core.geo.services import adapter

from vmmsx.stipend.services import approval, attendance, picker, society
from vmmsx.stipend.services import report as report_service

PAYMENT_DOCTYPE = "VMMS Stipend Payment Form"
ATTENDANCE_FIELD = "attendance"


def paired_report(doc):
	"""The progress report this form pays for. Throws if it names none."""
	if not doc.progress_report:
		frappe.throw(
			_(
				"A payment form pays for a progress report. Without one there is no period, no place"
				" and nobody it is allowed to pay."
			),
			frappe.MandatoryError,
			title=_("No Progress Report"),
		)

	return frappe.get_doc(report_service.REPORT_DOCTYPE, doc.progress_report)


def eligible(doc) -> set[str]:
	"""Everybody the paired report names. The only people this form may pay."""
	return set(report_service.volunteers_of(paired_report(doc)))


def forms_paying(report: str, volunteer: str) -> list[str]:
	"""Payment forms paired with `report` that already pay `volunteer`, sorted.

	Asked by the report before it lets somebody be taken off it. Without this,
	removing a volunteer from the narrative would leave every paired form holding a
	line the form's own rules forbid: valid on disk, refused the next time anybody
	saves it, and confusing at exactly the moment somebody is trying to correct
	something.

	`frappe.get_all` rather than `get_list` on purpose. This is an integrity
	question, not a read of somebody's data, and the answer must not depend on what
	the person doing the removing happens to be able to open: a form they cannot see
	is still a form that would break.
	"""
	forms = frappe.get_all(PAYMENT_DOCTYPE, filters={"progress_report": report}, pluck="name")

	if not forms:
		return []

	return sorted(
		{
			row["parent"]
			for row in frappe.get_all(
				attendance.LINE_DOCTYPE,
				filters={
					"parenttype": PAYMENT_DOCTYPE,
					"parent": ("in", forms),
					"volunteer": volunteer,
				},
				fields=["parent"],
			)
		}
	)


def sync(doc) -> None:
	"""Bring the form into line with its report, and derive what is derived.

	Called from `validate`, so it runs on every save and there is no state in
	which the two documents disagree. Order matters and is deliberate: the pairing
	is checked first, because every rule after it is stated in terms of a period
	and a roster that have to be the report's.
	"""
	paired = paired_report(doc)

	_assert_same_place(doc, paired)
	_adopt_period(doc, paired)
	_adopt_currency(doc)

	attendance.assert_lines(doc, set(report_service.volunteers_of(paired)), doc.period_from, doc.period_to)
	attendance.recompute(doc)


def signature(doc) -> tuple:
	"""What must not change once the form is submitted: every line of the grid.

	Sorted, so reordering rows is not mistaken for changing what is being paid.
	"""
	return tuple(
		sorted(
			(
				row.volunteer,
				str(getdate(row.attendance_date)),
				int(bool(row.attended)),
				flt(row.hours),
				flt(row.stipend_amount),
			)
			for row in doc.get(ATTENDANCE_FIELD) or []
			if row.volunteer and row.attendance_date
		)
	)


def add_line(
	doc,
	identifier: str,
	attendance_date,
	attended: bool = True,
	hours: float | None = None,
	stipend_amount: float = 0,
) -> bool:
	"""Record one volunteer's one day. Idempotent. Returns whether anything changed.

	The volunteer goes through the picker, so a supervisor cannot pay somebody
	outside their own area by naming them, and then through the report, so they
	cannot pay somebody the narrative never mentioned. Two checks because they are
	two questions: the first is about who this session may see, the second about
	who this period was about, and passing one says nothing about the other.

	A second call for the same volunteer and day **replaces that day's line**
	rather than adding a second one. That is what makes the grid's per-day total
	the day's total, and it is the same rule `attendance.assert_lines` enforces on
	save for lines that arrived any other way.
	"""
	_assert_draft(doc)

	volunteer = picker.resolve(identifier)
	day = getdate(attendance_date)

	if volunteer not in eligible(doc):
		frappe.throw(
			_(
				"{0} is not on this form's progress report, so this form cannot pay them. Add them to the report first."
			).format(frappe.bold(volunteer)),
			frappe.ValidationError,
			title=_("Volunteer Not On The Report"),
		)

	values = {
		"volunteer": volunteer,
		"attendance_date": day,
		"attended": 1 if attended else 0,
		"hours": flt(hours),
		"stipend_amount": flt(stipend_amount),
	}
	existing = _row_for(doc, volunteer, day)

	if existing:
		if all(existing.get(field) == value for field, value in values.items()):
			return False

		existing.update(values)

		return True

	doc.append(ATTENDANCE_FIELD, values)

	return True


def remove_line(doc, volunteer: str, attendance_date) -> bool:
	"""Take one volunteer's one day off the grid. Idempotent."""
	_assert_draft(doc)

	day = getdate(attendance_date)
	rows = doc.get(ATTENDANCE_FIELD) or []
	remaining = [
		row for row in rows if not (row.volunteer == volunteer and getdate(row.attendance_date) == day)
	]

	if len(remaining) == len(rows):
		return False

	doc.set(ATTENDANCE_FIELD, remaining)

	return True


def submit(doc) -> dict:
	"""Send the form up. Idempotent, and a dead end by design."""
	return approval.submit(doc)


def withdraw(doc) -> dict:
	"""Take the form back to Draft so it can be corrected. Idempotent."""
	return approval.withdraw(doc)


def status(doc) -> dict:
	"""Everything a caller needs about one form. An explicit DTO, field by field.

	The per-volunteer totals are computed here rather than stored, which is the
	whole reason the grid is one row per volunteer per day: the answer to "what is
	owed to this person for this period" is a sum over rows that cannot disagree
	with the rows it sums.
	"""
	return {
		"payment_form": doc.name,
		"progress_report": doc.progress_report,
		"geo_node": doc.geo_node,
		"geo_path": adapter.get_full_path(doc.geo_node) if doc.geo_node else None,
		"period_from": doc.period_from,
		"period_to": doc.period_to,
		"currency": doc.currency,
		"line_count": len(attendance.lines(doc)),
		"per_volunteer": attendance.per_volunteer(doc),
		"total_payable": flt(doc.total_payable),
		"approval": approval.status(doc),
	}


def attendance_on(doc, day) -> dict:
	"""Who was on this form's grid on one day. An explicit DTO."""
	rows = attendance.on_date(doc, day)

	return {
		"payment_form": doc.name,
		"attendance_date": getdate(day),
		"attended": [row["volunteer"] for row in rows if row["attended"]],
		"absent": [row["volunteer"] for row in rows if not row["attended"]],
		"lines": rows,
	}


# --- pairing --------------------------------------------------------------


def _assert_same_place(doc, paired) -> None:
	"""The form and its report describe one period of work in one place."""
	if doc.geo_node and paired.geo_node and doc.geo_node == paired.geo_node:
		return

	frappe.throw(
		_(
			"This form is anchored at {0} and its progress report at {1}. A form pays for the report it is paired with, so the two are one place."
		).format(
			frappe.bold(adapter.get_full_path(doc.geo_node) if doc.geo_node else "-"),
			frappe.bold(adapter.get_full_path(paired.geo_node) if paired.geo_node else "-"),
		),
		frappe.ValidationError,
		title=_("Form And Report Disagree"),
	)


def _adopt_period(doc, paired) -> None:
	"""The period is the report's, copied on every save rather than fetched once."""
	doc.period_from = paired.period_from
	doc.period_to = paired.period_to


def _adopt_currency(doc) -> None:
	"""Set the currency from society configuration at creation, and leave it after.

	**At creation it overwrites rather than fills.** Frappe pre-fills a field named
	`currency` from the site's Global Defaults, so a brand new form arrives here
	already holding whichever currency another app configured for the whole site.
	That is somebody else's answer to a question this society has its own answer
	to, and quietly keeping it is precisely the "no currency is ever assumed"
	promise being broken by the framework instead of by this file.

	**Afterwards it is left alone.** A form's amounts were typed in the currency it
	carried at the time, so a society that changes its currency next year must not
	silently re-denominate last year's paperwork. The one exception is a form that
	has no currency at all, which is filled if the society has since chosen one.

	Only ever a currency this site actually holds: the setting is a Link, but a
	site can be restored with settings and without the currency record, and a form
	that refused to save because of that would be this module turning a
	configuration gap into an outage. An empty currency is honest; a guessed one is
	not.
	"""
	if doc.is_new() or not doc.currency:
		doc.currency = _configured_currency()


def _configured_currency() -> str | None:
	configured = society.default_currency()

	return configured if configured and frappe.db.exists("Currency", configured) else None


# --- internals ------------------------------------------------------------


def _row_for(doc, volunteer: str, day):
	for row in doc.get(ATTENDANCE_FIELD) or []:
		if row.volunteer == volunteer and row.attendance_date and getdate(row.attendance_date) == day:
			return row

	return None


def _assert_draft(doc) -> None:
	if not approval.is_pending(doc):
		return

	frappe.throw(
		_(
			"This payment form has been submitted. Withdraw it back to {0} before changing what it pays."
		).format(frappe.bold(_(approval.DRAFT))),
		frappe.ValidationError,
		title=_("Submitted Paperwork Is Frozen"),
	)
