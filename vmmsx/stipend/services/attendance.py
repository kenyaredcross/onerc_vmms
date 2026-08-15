# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The daily attendance grid — one row per volunteer per day, and why.

The shape, and the two questions that chose it
----------------------------------------------

A payment form has to answer two questions, and they pull in opposite
directions:

1. **What is payable to one volunteer for the period?** Sum that volunteer's
   days.
2. **Who attended on day X?** Take that day's rows.

Modelled **tall** — `VMMS Stipend Attendance Line`, one row per (volunteer,
date), carrying that day's attendance and that day's amount — both are a filter
and a sum over the same table. The first filters on `volunteer`, the second on
`attendance_date`, and the second works *across* payment forms as well as within
one, because a date is a value in a column rather than a column name.

Modelled **wide** — a row per volunteer with a column per day — the first
question is easy and the second is not a query at all: "who attended on the 14th"
becomes "read the column called `day_14`", which cannot be indexed, cannot be
asked across a period boundary, and stops working the moment a society runs a
period longer than the columns somebody guessed at. It also puts the calendar in
the schema: a 31-column table is a February with seven empty columns and a
migration every time a society wants a fortnightly cycle.

The wide shape is the one people draw on paper, because on paper a month fits
across the page. It is the wrong shape for a database, and the grid a supervisor
sees on the form is Frappe's own child-table grid over the tall rows, so nothing
is lost by storing it the way the questions want it stored.

What is derived, and what is typed
----------------------------------

**Every total is derived.** `total_payable` is recomputed from the rows on every
save, and per-volunteer totals are not stored anywhere at all — they are computed
from the same rows on request. A stored total is a number that will one day
disagree with the rows it claims to add up, and the day it does, nobody can tell
which one is the truth.

**No amount is derived.** There is no rate, no hours-times-rate, and no default:
what a society pays for a day is a society's decision, and an app that invented
one would be paying people a number nobody chose. `hours` is recorded and never
multiplied by anything.

The rules enforced here are the ones that are true for every society: you cannot
pay somebody the report never mentioned, you cannot pay for a day outside the
period the report covers, you cannot pay somebody twice for one day, you cannot
pay a negative amount, and you cannot pay a daily stipend for a day somebody was
not there.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

LINE_DOCTYPE = "VMMS Stipend Attendance Line"
PAYMENT_DOCTYPE = "VMMS Stipend Payment Form"

ATTENDANCE_FIELD = "attendance"


def assert_lines(doc, eligible: set[str], period_from, period_to) -> None:
	"""Throw unless every line on this form is payable. Checked on every save.

	`eligible` is the set of volunteers the paired progress report names. It is
	passed in rather than looked up here, so this module holds no opinion about
	where the roster comes from and the payment service stays the one place that
	knows a form is paired with a report.
	"""
	seen: set[tuple[str, str]] = set()

	for row in lines(doc):
		_assert_complete(row)
		_assert_on_the_report(row, eligible)
		_assert_within_period(row, period_from, period_to)
		_assert_once_per_day(row, seen)
		_assert_amount(row)


def recompute(doc) -> None:
	"""Write the derived total onto the form. Idempotent by construction.

	Recomputed from the rows every time rather than adjusted, so there is no path
	by which the stored total can be a stale sum of rows that have since changed.
	"""
	doc.total_payable = flt(sum(flt(row.stipend_amount) for row in lines(doc)))


def lines(doc) -> list:
	"""The grid's rows, or an empty list. A form with no lines is a valid draft."""
	return doc.get(ATTENDANCE_FIELD) or []


# --- the two questions ----------------------------------------------------


def per_volunteer(doc) -> list[dict]:
	"""Total payable to each volunteer over the period, and what it is made of.

	The first of the two questions the shape was chosen for. Sorted by volunteer
	so the same form read twice reads the same way.

	Days attended and days recorded are both returned, because they are different
	numbers whenever an absence was recorded, and a total that dropped the
	distinction would leave a reader unable to tell a short period from a patchy
	one.
	"""
	totals: dict[str, dict] = {}

	for row in lines(doc):
		entry = totals.setdefault(
			row.volunteer,
			{
				"volunteer": row.volunteer,
				"days_recorded": 0,
				"days_attended": 0,
				"hours": 0.0,
				"total_payable": 0.0,
			},
		)
		entry["days_recorded"] += 1
		entry["days_attended"] += 1 if row.attended else 0
		entry["hours"] = flt(entry["hours"] + flt(row.hours))
		entry["total_payable"] = flt(entry["total_payable"] + flt(row.stipend_amount))

	return [totals[name] for name in sorted(totals)]


def payable_to(doc, volunteer: str) -> float:
	"""What this form pays one volunteer for the period. Zero if it names them nowhere."""
	return flt(sum(flt(row.stipend_amount) for row in lines(doc) if row.volunteer == volunteer))


def on_date(doc, day) -> list[dict]:
	"""Every line on this form for one day, attended or not.

	The second question, asked of a single form. Rows rather than volunteer names,
	because "who was there on the 14th" is nearly always followed by "and for how
	long", and the caller already has both.
	"""
	wanted = getdate(day)

	return [
		{
			"volunteer": row.volunteer,
			"attendance_date": getdate(row.attendance_date),
			"attended": bool(row.attended),
			"hours": flt(row.hours),
			"stipend_amount": flt(row.stipend_amount),
		}
		for row in lines(doc)
		if row.attendance_date and getdate(row.attendance_date) == wanted
	]


def attended_on(doc, day) -> list[str]:
	"""Just the volunteers who were there on that day, sorted."""
	return sorted({row["volunteer"] for row in on_date(doc, day) if row["attended"]})


def register_on(day) -> list[dict]:
	"""Who attended on one day, across every payment form the caller may read.

	The same question asked of the register rather than of one form, and the
	reason the tall shape earns its keep: it is one filter on one indexed column,
	and it works across forms, periods and places without knowing any of them.

	**Access is applied to the parent forms, one by one, through core's own
	guard.** The child rows are fetched first because a date filter cannot be
	expressed against a parent, and every row from a form the caller may not read
	is then dropped. `frappe.get_all` does not check permissions, which is exactly
	why the filtering here is explicit rather than assumed.
	"""
	rows = frappe.get_all(
		LINE_DOCTYPE,
		filters={
			"attendance_date": getdate(day),
			"attended": 1,
			# Named explicitly rather than assumed. A child doctype is a table like
			# any other, and filtering on the parent it belongs to is what keeps this
			# query answering about payment forms even if a later document ever
			# carries the same rows.
			"parenttype": PAYMENT_DOCTYPE,
		},
		fields=["parent", "volunteer", "attendance_date", "hours", "stipend_amount"],
		order_by="parent asc, volunteer asc",
	)
	visible: dict[str, bool] = {}
	found = []

	for row in rows:
		if row["parent"] not in visible:
			visible[row["parent"]] = _readable(row["parent"])

		if not visible[row["parent"]]:
			continue

		found.append(
			{
				"payment_form": row["parent"],
				"volunteer": row["volunteer"],
				"attendance_date": getdate(row["attendance_date"]),
				"hours": flt(row["hours"]),
				"stipend_amount": flt(row["stipend_amount"]),
			}
		)

	return found


def _readable(payment_form: str) -> bool:
	"""May this session read that payment form?

	Asked through core's own guard so the verdict is the one every other layer
	would reach, rather than a second opinion assembled here. Frappe's role
	permission is asked first, because the guard answers about geo and a caller
	with no permission on the doctype at all must not get past on scope alone.
	"""
	from onerc_core.access.services.enforcement import guard

	if not frappe.has_permission(PAYMENT_DOCTYPE, ptype="read", doc=payment_form):
		return False

	try:
		guard(PAYMENT_DOCTYPE, payment_form)
	except frappe.PermissionError:
		return False

	return True


# --- one rule per function ------------------------------------------------


def _assert_complete(row) -> None:
	if row.volunteer and row.attendance_date:
		return

	frappe.throw(
		_("Every attendance line names a volunteer and a day. Row {0} does not.").format(
			frappe.bold(row.idx)
		),
		frappe.MandatoryError,
		title=_("Incomplete Attendance Line"),
	)


def _assert_on_the_report(row, eligible: set[str]) -> None:
	"""A payment form pays the people its progress report is about, and nobody else.

	The narrative is what the money is for. Paying somebody the report never
	mentions is a payment with nothing behind it, and it is the one shape of
	mistake this form exists to make impossible.
	"""
	if row.volunteer in eligible:
		return

	frappe.throw(
		_(
			"{0} is not on this form's progress report, so this form cannot pay them. Add them to the report first."
		).format(frappe.bold(row.volunteer)),
		frappe.ValidationError,
		title=_("Volunteer Not On The Report"),
	)


def _assert_within_period(row, period_from, period_to) -> None:
	if not (period_from and period_to):
		return

	day = getdate(row.attendance_date)

	if getdate(period_from) <= day <= getdate(period_to):
		return

	frappe.throw(
		_("{0} is outside the period this form covers, which runs from {1} to {2}.").format(
			frappe.bold(frappe.format(day, {"fieldtype": "Date"})),
			frappe.bold(frappe.format(period_from, {"fieldtype": "Date"})),
			frappe.bold(frappe.format(period_to, {"fieldtype": "Date"})),
		),
		frappe.ValidationError,
		title=_("Day Outside The Period"),
	)


def _assert_once_per_day(row, seen: set[tuple[str, str]]) -> None:
	key = (row.volunteer, str(getdate(row.attendance_date)))

	if key not in seen:
		seen.add(key)

		return

	frappe.throw(
		_(
			"{0} already has a line for {1}. One volunteer has one line per day, which is what makes the day's total the day's total."
		).format(
			frappe.bold(row.volunteer),
			frappe.bold(frappe.format(getdate(row.attendance_date), {"fieldtype": "Date"})),
		),
		frappe.ValidationError,
		title=_("Duplicate Attendance Line"),
	)


def _assert_amount(row) -> None:
	amount = flt(row.stipend_amount)

	if amount < 0:
		frappe.throw(
			_("A stipend line cannot be negative. Row {0} is {1}.").format(
				frappe.bold(row.idx), frappe.bold(amount)
			),
			frappe.ValidationError,
			title=_("Negative Stipend"),
		)

	if amount and not row.attended:
		frappe.throw(
			_(
				"Row {0} pays {1} for a day they are marked absent. A daily stipend is paid for attending; record the absence with no amount, or mark the day attended."
			).format(frappe.bold(row.idx), frappe.bold(row.volunteer)),
			frappe.ValidationError,
			title=_("Paid For An Absence"),
		)
