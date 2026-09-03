# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Stipend API — explicit DTOs, session-derived scope, and one honest refusal.

Every endpoint names its arguments, checks permission through Frappe (which
brings core's geo scoping with it), and returns a dict this module builds field
by field. None of them returns a Document or a raw query result.

**`find_volunteers` takes no user and no scope.** A caller says what they are
looking for; who they are is the session, and where they may look is core's
answer about that session. There is no argument by which a caller could widen
their own area, which is why there is no check here that could get it wrong. See
the scope guarantee at the top of `stipend/services/picker.py`.

**`decide` always refuses, and that is the feature.** Stipend approval runs from
the supervisor to the head of the volunteer's department; departmental resolution
does not exist, and this app will not route the decision through the geo approval
engine instead, because that engine would resolve confidently to a geo parent
rather than to a head of department. The endpoint exists, in the shape it will
have when routing is built, and says plainly why it cannot act. It is **not**
routed through `vmmsx/api/approvals.py`: that endpoint is the geo engine's door,
these doctypes are deliberately not governed by a `VMMS Approval Workflow`, and
`_assert_governed` there would refuse them with a message about the wrong thing.
"""

import frappe
from frappe import _
from frappe.utils import getdate

from vmmsx.stipend.services import approval, attendance, picker
from vmmsx.stipend.services import payment as payment_service
from vmmsx.stipend.services import report as report_service

REPORT_DOCTYPE = "VMMS Stipend Progress Report"
PAYMENT_DOCTYPE = "VMMS Stipend Payment Form"

# The two doctypes this module will act on, and the whole of them.
#
# Submission is looked up rather than branched on: a report has one precondition
# a form does not (it must cover somebody), so the two have different submit
# functions, and a table keyed by doctype keeps that difference in one line
# instead of an `if` that grows a third arm the day a third document appears.
# Everything else below is genuinely the same question asked of two documents,
# and is written once.
_SUBMIT = {
	REPORT_DOCTYPE: report_service.submit,
	PAYMENT_DOCTYPE: payment_service.submit,
}

STIPEND_DOCTYPES = tuple(_SUBMIT)


# --- the coordinator's listings -------------------------------------------
#
# How a coordinator finds paperwork in the first place. Same shape as
# `tasks.branch_tasks` and `deployment.branch_deployments`: `frappe.get_list`,
# so core's permission query condition runs and the caller's Geo Assignment is
# the floor the answer stands on. `frappe.get_all` would ignore permissions and
# return a whole-site answer wearing the shape of a scoped one.
#
# One function over both doctypes, because "what paperwork is in my area" is
# genuinely the same question asked twice — the difference between a report and
# a form is in the DTO each service already builds, not in the listing.

PAGE = 100


@frappe.whitelist()
def branch_paperwork(doctype: str, limit: int | None = None) -> dict:
	"""Stipend paperwork in the caller's own area, most recently touched first.

	`doctype` selects which of the two, and is checked against the module's own
	tuple rather than trusted: an arbitrary doctype arriving here would otherwise
	be listed through this endpoint's permission check instead of its own.
	"""
	if doctype not in STIPEND_DOCTYPES:
		frappe.throw(_("{0} is not stipend paperwork.").format(doctype))

	names = frappe.get_list(
		doctype,
		order_by="modified desc",
		limit_page_length=min(int(limit or PAGE), PAGE),
		pluck="name",
	)

	describe = report_service.status if doctype == REPORT_DOCTYPE else payment_service.status
	rows = [describe(frappe.get_doc(doctype, name)) for name in names]

	return {
		"doctype": doctype,
		"count": len(rows),
		"paperwork": rows,
		# Counted from the rows already fetched rather than by a second query, so
		# the number and the list can never disagree.
		"pending_count": len([row for row in rows if row.get("approval", {}).get("is_pending")]),
	}


@frappe.whitelist()
def create_report(geo_node: str, period_from: str, period_to: str, narrative: str | None = None) -> dict:
	"""Start a progress report for a period of work in one place.

	The Geo Node is required here, at creation, and not filled in later: ACC-02
	is a property of the record existing, not a step in a workflow. An ordinary
	insert, so core's scoping runs on the anchor and a coordinator cannot file
	paperwork outside their own area.
	"""
	frappe.has_permission(REPORT_DOCTYPE, ptype="create", throw=True)

	report = frappe.get_doc(
		{
			"doctype": REPORT_DOCTYPE,
			"geo_node": geo_node,
			"period_from": period_from,
			"period_to": period_to,
			"narrative": narrative,
		}
	)
	report.insert()

	return report_service.status(report)


@frappe.whitelist()
def create_payment_form(progress_report: str, currency: str | None = None) -> dict:
	"""Start a payment form against a report, inheriting its place and period.

	The pairing is the service's rule, not this endpoint's: a form and its report
	describe one period of work in one place, and `payment.status`' own
	`_assert_same_place` is what enforces it. Copying the three fields across
	here rather than asking a caller for them is what makes that check something
	the UI cannot get wrong.
	"""
	frappe.has_permission(PAYMENT_DOCTYPE, ptype="create", throw=True)

	report = _readable(REPORT_DOCTYPE, progress_report)

	form = frappe.get_doc(
		{
			"doctype": PAYMENT_DOCTYPE,
			"progress_report": report.name,
			"geo_node": report.geo_node,
			"period_from": report.period_from,
			"period_to": report.period_to,
			"currency": currency or frappe.defaults.get_global_default("currency"),
		}
	)
	form.insert()

	return payment_service.status(form)


# --- the picker -----------------------------------------------------------


@frappe.whitelist()
def find_volunteers(search: str | None = None, limit: int | None = None) -> dict:
	"""Volunteers the caller may put on stipend paperwork.

	The scope is derived from the session on every call and cannot be supplied, so
	an out-of-scope volunteer is not returnable by any argument. `search` narrows
	an already-scoped list and can only ever remove people from it.
	"""
	return picker.candidates(search=search, limit=limit)


@frappe.whitelist()
def resolve_volunteer(identifier: str) -> dict:
	"""One volunteer, named exactly, and only if the caller may see them.

	The stricter mode: a supervisor who knows who they mean types a volunteer
	docname, a Red Profile docname or an email instead of browsing. The identifier
	is still put through the scope check, and the refusal is the same message
	whether the volunteer does not exist or simply is not theirs.
	"""
	return picker.describe(picker.resolve(identifier))


# --- progress reports -----------------------------------------------------


@frappe.whitelist()
def get_report(name: str) -> dict:
	"""Where a report stands, who it covers, and where it would eventually route."""
	return report_service.status(_readable(REPORT_DOCTYPE, name))


@frappe.whitelist()
def add_volunteer_to_report(
	name: str,
	identifier: str,
	activity: str | None = None,
	notes: str | None = None,
) -> dict:
	"""Put a volunteer on a report. Idempotent.

	Two gates, and they are two different questions. Write permission on the
	report says whether the caller may change this document; the picker says
	whether this volunteer is theirs to add. Passing one says nothing about the
	other.
	"""
	report = _readable(REPORT_DOCTYPE, name)
	report.check_permission("write")

	if report_service.add_volunteer(report, identifier, activity=activity, notes=notes):
		report.save()

	return report_service.status(report)


@frappe.whitelist()
def set_report_narrative(name: str, narrative: str) -> dict:
	"""Rewrite what a draft report says.

	Write permission on the report, which brings core's scoping with it. The
	draft check is the service's, so this door and the desk answer the same way.
	"""
	report = _readable(REPORT_DOCTYPE, name)
	report.check_permission("write")

	if report_service.set_narrative(report, narrative):
		report.save()

	return report_service.status(report)


@frappe.whitelist()
def remove_volunteer_from_report(name: str, volunteer: str) -> dict:
	"""Take a volunteer off a report. Idempotent."""
	report = _readable(REPORT_DOCTYPE, name)
	report.check_permission("write")

	if report_service.remove_volunteer(report, volunteer):
		report.save()

	return report_service.status(report)


# --- payment forms --------------------------------------------------------


@frappe.whitelist()
def get_payment_form(name: str) -> dict:
	"""What a form pays, per volunteer and in total, and where its approval stands."""
	return payment_service.status(_readable(PAYMENT_DOCTYPE, name))


@frappe.whitelist()
def record_attendance(
	name: str,
	identifier: str,
	attendance_date: str,
	attended: bool = True,
	hours: float | None = None,
	stipend_amount: float = 0,
) -> dict:
	"""Record one volunteer's one day on a payment form. Idempotent.

	A second call for the same volunteer and day replaces that day's line rather
	than adding a second one, which is what keeps a day's total the day's total.
	"""
	form = _readable(PAYMENT_DOCTYPE, name)
	form.check_permission("write")

	if payment_service.add_line(
		form,
		identifier,
		attendance_date,
		attended=attended,
		hours=hours,
		stipend_amount=stipend_amount,
	):
		form.save()

	return payment_service.status(form)


@frappe.whitelist()
def who_attended(attendance_date: str, name: str | None = None) -> dict:
	"""Who was there on one day.

	With `name`, one form's grid. Without it, every payment form the caller may
	read, which is the query the grid's shape was chosen for: one filter on one
	column, working across forms, periods and places without knowing any of them.
	Forms the caller may not read are dropped, one by one, through core's guard.
	"""
	if name:
		return payment_service.attendance_on(_readable(PAYMENT_DOCTYPE, name), attendance_date)

	rows = attendance.register_on(attendance_date)

	return {
		"payment_form": None,
		"attendance_date": getdate(attendance_date),
		"attended": sorted({row["volunteer"] for row in rows}),
		# Empty by construction, not by coincidence: the register-wide question asks
		# only about the people who were there, across forms whose absences are
		# nobody's business but their own form's. The key is present so a caller
		# handles one shape whichever way they asked.
		"absent": [],
		"lines": rows,
	}


# --- the approval stub ----------------------------------------------------


@frappe.whitelist()
def submit_for_approval(doctype: str, name: str) -> dict:
	"""Send stipend paperwork up. It lands in Pending Departmental Approval and stays.

	Deliberately not a no-op: the paperwork really is submitted, really is frozen
	against edits, and really does record who submitted it and when, because all
	of that is true today and none of it depends on there being an approver.
	"""
	doc = _stipend(doctype, name, ptype="write")

	return _SUBMIT[doc.doctype](doc)


@frappe.whitelist()
def withdraw(doctype: str, name: str) -> dict:
	"""Take stipend paperwork back to Draft so it can be corrected. Idempotent."""
	return approval.withdraw(_stipend(doctype, name, ptype="write"))


@frappe.whitelist()
def decide(doctype: str, name: str, decision: str | None = None, reason: str | None = None) -> dict:
	"""Approve or reject stipend paperwork. **Always refuses.**

	The arguments are named and ignored on purpose: this is the shape the call
	will have once departmental routing exists, so the endpoint that eventually
	works is the endpoint that refuses today rather than a new one appearing and
	callers having to find it.

	The refusal is nobody's exception. An administrator gets it too, because what
	is missing is not permission but the answer to *who*: the head of the
	volunteer's department, which nothing in this app can resolve.
	"""
	return approval.decide(_stipend(doctype, name, ptype="read"), decision, reason)


@frappe.whitelist()
def get_approval_status(doctype: str, name: str) -> dict:
	"""Where the approval stands, and why it cannot move."""
	return approval.status(_stipend(doctype, name, ptype="read"))


# --- shared ---------------------------------------------------------------


def _readable(doctype: str, name: str):
	"""Load a document the caller is allowed to see.

	Ordinary permission only: Frappe's roles *and* core's geo scoping, because
	both of this module's doctypes are registered as scopeable. There is no holder
	bypass here, deliberately. Stipend paperwork is the society's record of work
	and money, not a personal one.
	"""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")

	return doc


def _stipend(doctype: str, name: str, ptype: str):
	"""Load one of this module's own documents, refusing any other doctype first.

	Checked before anything else happens, so these endpoints are not a
	general-purpose way to poke at arbitrary doctypes.
	"""
	if doctype not in STIPEND_DOCTYPES:
		frappe.throw(
			_("{0} is not stipend paperwork.").format(frappe.bold(doctype)),
			frappe.ValidationError,
			title=_("Not Stipend Paperwork"),
		)

	doc = frappe.get_doc(doctype, name)
	doc.check_permission(ptype)

	return doc
