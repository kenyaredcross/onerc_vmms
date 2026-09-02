# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What the society took in and what it paid out, from the records it keeps.

**This is a report, not a book of account.** Nothing here writes, and nothing
here holds a figure of its own: every number is derived at read time from two
registers the console already shows one row at a time — memberships, and stipend
payment forms. That is a deliberate limit, and the two paragraphs below are the
whole of what it costs, because a screen that did not say so would be a screen
that quietly invented money.

**Income is at the published fee, because no record holds an amount.** A
`VMMS Membership` records *that* somebody paid — a transaction reference, a
receipt number, a date — and never how much. The only amount in the system is
`VMMS Membership Type.fee_amount`, the society's own list price. So a membership
is counted at the fee its type carried *when this report ran*, which is right
until a society changes a price and then reprices its own history. Every payload
carries `basis: "published_fee"` so the screen can say it in one line rather
than implying an exactness that is not there. If a society needs true receipts,
the fix is an amount field on the membership and not a cleverer sum here.

**A proved membership is not income.** `membership_source` tells the two apart:
`Gateway` is somebody who paid the society through this system, `Proof` is
somebody who already held a membership elsewhere and showed evidence of it. Both
are real members; only the first brought money in. Counting the second would
turn a data-migration exercise into a revenue spike.

**Expenses are stipend payment forms, and there is nothing else.** No expense
record exists in this app, so a cost that is not a volunteer stipend cannot be
reported and is not guessed at. The payload says how many forms it summed, so
"expenses are low" and "expenses are unrecorded" are distinguishable on the
screen.

**Currency is reported, never converted.** Each register carries its own
currency link and a site may hold more than one. Rather than pick a rate this
app has no business owning, every total is grouped by currency and the caller is
handed the set. A single-currency society — nearly all of them — sees one entry
and the screen reads normally.

**Scope is `frappe.get_list` and nothing else.** Both reads go through the
permission layer, so a coordinator's Geo Assignment is the floor every figure
stands on and no argument on the screen widens it. Somebody holding scope over
one branch sees that branch's money; nobody sees a national total by asking
nicely.
"""

from collections import defaultdict

import frappe
from frappe.utils import add_months, flt, get_first_day, getdate, today

MEMBERSHIP_DOCTYPE = "VMMS Membership"
MEMBERSHIP_TYPE_DOCTYPE = "VMMS Membership Type"
PAYMENT_DOCTYPE = "VMMS Stipend Payment Form"

#: The membership source that means money changed hands through this system.
#: See the module docstring — `Proof` is somebody's existing membership, not a
#: sale.
SOURCE_GATEWAY = "Gateway"

#: What every income figure is derived from, travelling with the payload so the
#: screen states it rather than implying otherwise.
BASIS_PUBLISHED_FEE = "published_fee"

#: A report is a report. Both registers are read whole for the window asked
#: for, so the window is what bounds the query and this is the backstop.
MAX_ROWS = 5000

#: How many months of history the trend carries when the caller names no window.
DEFAULT_MONTHS = 12


def summary(from_date: str | None = None, to_date: str | None = None) -> dict:
	"""The whole finance screen, in one read.

	One endpoint rather than four, because the figures are only meaningful
	beside each other: income without the expenses over the same window is a
	number somebody will subtract from something else by hand and get wrong.
	"""
	start, end = _window(from_date, to_date)

	income = _income(start, end)
	expenses = _expenses(start, end)

	return {
		"from_date": str(start),
		"to_date": str(end),
		"basis": BASIS_PUBLISHED_FEE,
		"income": income,
		"expenses": expenses,
		# Income minus expenditure, per currency, computed here so the screen
		# never subtracts two figures that are in different money.
		"net": _net(income["totals"], expenses["totals"]),
		# The month-by-month series both sides share, so one chart can carry
		# them and the two bars for a month are always the same month.
		"months": _months(start, end, income["by_month"], expenses["by_month"]),
	}


# --- income ------------------------------------------------------------------


def _income(start, end) -> dict:
	"""Membership fees received in the window, at the published fee.

	`paid_on` is the date, not `creation`: a society records a payment when it
	is reconciled, which is routinely a different day from when the applicant
	filled the form in.
	"""
	rows = frappe.get_list(
		MEMBERSHIP_DOCTYPE,
		filters=[
			["paid_on", "between", [str(start), f"{end} 23:59:59"]],
			["membership_source", "=", SOURCE_GATEWAY],
		],
		fields=["name", "membership_type", "paid_on", "geo_node", "membership_status"],
		order_by="paid_on desc",
		limit_page_length=MAX_ROWS,
	)

	fees = _fees({row["membership_type"] for row in rows if row.get("membership_type")})

	totals: dict[str, float] = defaultdict(float)
	by_month: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
	by_type: dict[str, dict] = {}

	for row in rows:
		fee = fees.get(row.get("membership_type"))

		# A type that was deleted, or one with no fee set. The membership is
		# still counted — it is a real payment — but it contributes nothing to a
		# total, and `unpriced` says how many so the screen can own the gap
		# rather than the number quietly being short.
		if not fee or not fee["amount"]:
			by_type.setdefault(
				row.get("membership_type") or "—",
				{
					"membership_type": row.get("membership_type"),
					"label": _label(row, fees),
					"count": 0,
					"amount": 0.0,
					"currency": None,
					"unpriced": True,
				},
			)
			by_type[row.get("membership_type") or "—"]["count"] += 1
			continue

		currency = fee["currency"]
		amount = fee["amount"]

		totals[currency] += amount
		by_month[_month_of(row["paid_on"])][currency] += amount

		bucket = by_type.setdefault(
			row["membership_type"],
			{
				"membership_type": row["membership_type"],
				"label": fee["label"],
				"count": 0,
				"amount": 0.0,
				"currency": currency,
				"unpriced": False,
			},
		)
		bucket["count"] += 1
		bucket["amount"] += amount

	return {
		"totals": _as_money(totals),
		"count": len(rows),
		"by_month": {month: _as_money(amounts) for month, amounts in by_month.items()},
		"by_type": sorted(by_type.values(), key=lambda entry: (-entry["amount"], entry["label"] or "")),
		# The most recent payments, for the list beside the figures. Bounded
		# small: this is a finance summary, not the membership register.
		"recent": [
			{
				"name": row["name"],
				"membership_type": row.get("membership_type"),
				"label": _label(row, fees),
				"paid_on": str(row["paid_on"]),
				"status": row.get("membership_status"),
				"amount": (fees.get(row.get("membership_type")) or {}).get("amount"),
				"currency": (fees.get(row.get("membership_type")) or {}).get("currency"),
			}
			for row in rows[:12]
		],
	}


def _fees(types: set[str]) -> dict[str, dict]:
	"""The published fee of each membership type named, in one read.

	Read directly rather than through `get_list`: a coordinator who may read a
	membership may not necessarily hold read on the *type* table, and refusing
	the whole report over a price list would be the wrong failure. The type name
	is already on the membership row they were admitted to.
	"""
	if not types:
		return {}

	rows = frappe.get_all(
		MEMBERSHIP_TYPE_DOCTYPE,
		filters={"name": ("in", list(types))},
		fields=["name", "membership_type_name", "fee_amount", "fee_currency"],
		ignore_permissions=True,
	)

	return {
		row["name"]: {
			"label": row.get("membership_type_name") or row["name"],
			"amount": flt(row.get("fee_amount")),
			"currency": row.get("fee_currency") or _default_currency(),
		}
		for row in rows
	}


def _label(row: dict, fees: dict[str, dict]) -> str:
	fee = fees.get(row.get("membership_type"))

	return (fee or {}).get("label") or row.get("membership_type") or "—"


# --- expenditure -------------------------------------------------------------


def _expenses(start, end) -> dict:
	"""Stipend payment forms whose period falls in the window.

	Dated by `period_to` — the end of the work being paid for — rather than by
	when the form was filed, so a form raised late lands in the month the money
	was earned. Draft forms are included and counted separately: a coordinator
	looking at the position needs to see what is about to be paid, and a screen
	that showed only approved forms would report a society as solvent right up
	to the moment it was not.
	"""
	rows = frappe.get_list(
		PAYMENT_DOCTYPE,
		filters=[["period_to", "between", [str(start), str(end)]]],
		fields=[
			"name",
			"total_payable",
			"currency",
			"period_from",
			"period_to",
			"geo_node",
			"approval_state",
			"progress_report",
		],
		order_by="period_to desc",
		limit_page_length=MAX_ROWS,
	)

	totals: dict[str, float] = defaultdict(float)
	by_month: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
	by_state: dict[str, dict] = {}

	for row in rows:
		currency = row.get("currency") or _default_currency()
		amount = flt(row.get("total_payable"))

		totals[currency] += amount
		by_month[_month_of(row["period_to"])][currency] += amount

		state = row.get("approval_state") or "Draft"
		bucket = by_state.setdefault(state, {"state": state, "count": 0, "amount": 0.0, "currency": currency})
		bucket["count"] += 1
		bucket["amount"] += amount

	return {
		"totals": _as_money(totals),
		"count": len(rows),
		"by_month": {month: _as_money(amounts) for month, amounts in by_month.items()},
		"by_state": sorted(by_state.values(), key=lambda entry: -entry["amount"]),
		"recent": [
			{
				"name": row["name"],
				"amount": flt(row.get("total_payable")),
				"currency": row.get("currency") or _default_currency(),
				"period_from": str(row.get("period_from") or ""),
				"period_to": str(row.get("period_to") or ""),
				"state": row.get("approval_state") or "Draft",
				"progress_report": row.get("progress_report"),
			}
			for row in rows[:12]
		],
	}


# --- shaping -----------------------------------------------------------------


def _net(income: list[dict], expenses: list[dict]) -> list[dict]:
	"""Income minus expenditure, per currency and never across them."""
	by_currency: dict[str, dict] = {}

	for entry in income:
		by_currency.setdefault(
			entry["currency"], {"currency": entry["currency"], "income": 0.0, "expenses": 0.0}
		)
		by_currency[entry["currency"]]["income"] += entry["amount"]

	for entry in expenses:
		by_currency.setdefault(
			entry["currency"], {"currency": entry["currency"], "income": 0.0, "expenses": 0.0}
		)
		by_currency[entry["currency"]]["expenses"] += entry["amount"]

	for entry in by_currency.values():
		entry["net"] = entry["income"] - entry["expenses"]

	return sorted(by_currency.values(), key=lambda entry: entry["currency"])


def _months(start, end, income: dict, expenses: dict) -> list[dict]:
	"""Every month in the window, in order, whether or not anything happened.

	A gap is a fact — a month with no memberships sold is not a month to leave
	out of the chart, because the shape of the year is the thing being read.
	"""
	months: list[dict] = []
	cursor = get_first_day(start)
	last = get_first_day(end)

	while getdate(cursor) <= getdate(last):
		key = str(cursor)[:7]
		months.append(
			{
				"month": key,
				"income": income.get(key, []),
				"expenses": expenses.get(key, []),
			}
		)
		cursor = add_months(cursor, 1)

		if len(months) > 120:  # a decade; a window this wide is a bug upstream
			break

	return months


def _as_money(totals: dict) -> list[dict]:
	"""A `{currency: amount}` map as the list every payload carries.

	A list rather than a map because it is always iterated and never looked up,
	and because the frontend rendering one currency and the frontend rendering
	three should be the same code.
	"""
	return sorted(
		({"currency": currency, "amount": amount} for currency, amount in totals.items() if amount),
		key=lambda entry: -entry["amount"],
	)


def _month_of(value) -> str:
	return str(getdate(value))[:7]


def _window(from_date: str | None, to_date: str | None):
	"""The window asked for, or the last twelve months to today."""
	end = getdate(to_date) if to_date else getdate(today())
	start = getdate(from_date) if from_date else get_first_day(add_months(end, -(DEFAULT_MONTHS - 1)))

	if start > end:
		start, end = end, start

	return start, end


def _default_currency() -> str:
	"""The site's own currency, for a record that names none."""
	return frappe.db.get_default("currency") or "USD"
