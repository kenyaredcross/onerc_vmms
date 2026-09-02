# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Fill in the two things every existing deployment now has to carry.

`VMMS Deployment` grew a responsible coordinator and a period written as
datetimes. Both are new, both are load-bearing, and every deployment already on
a site has neither — which would leave the register full of records that cannot
be saved again without somebody retyping them one at a time.

**The coordinator is the document's own owner.** Not a guess: the owner is
literally whoever created the deployment, which on every path in this app is the
coordinator who set it up or the approver whose decision fulfilled the request
that became it. Where that account no longer exists — a staff member who has
left, a site restored without its users — the field is left empty and the record
is flagged in the log rather than being pointed at somebody arbitrary. A society
fills those in; there is no honest automatic answer.

**The period is taken from the two dates.** A deployment that ran from the 4th
to the 11th began at some point on the 4th and ended at some point on the 11th,
so the datetimes are the start of the first day and the end of the last, which
is exactly what a period given in days has always meant. `derive_period` does
the same thing on every save from now on; this is that rule applied once to
everything written before it existed.

**Written with `db.set_value`, deliberately.** Saving each document would run
`validate`, which would run the material-change rules against records that have
people assigned to them — and demand a reason for a change nobody made. There is
nothing here for a controller to check: the values are derived from what the
record already says.
"""

import frappe

DEPLOYMENT_DOCTYPE = "VMMS Deployment"


def execute():
	if not frappe.db.table_exists(DEPLOYMENT_DOCTYPE):
		return

	_fill_periods()
	_fill_coordinators()


def _fill_periods() -> None:
	"""Every deployment with dates and no datetimes gets the days it already ran."""
	rows = frappe.get_all(
		DEPLOYMENT_DOCTYPE,
		filters=[
			[DEPLOYMENT_DOCTYPE, "planned_start", "is", "not set"],
			[DEPLOYMENT_DOCTYPE, "start_date", "is", "set"],
		],
		fields=["name", "start_date", "end_date"],
	)

	for row in rows:
		frappe.db.set_value(
			DEPLOYMENT_DOCTYPE,
			row["name"],
			{
				"planned_start": f"{row['start_date']} 00:00:00",
				"planned_end": f"{row['end_date'] or row['start_date']} 23:59:59",
			},
			update_modified=False,
		)


def _fill_coordinators() -> None:
	"""The owner, where the owner is still an account on this site."""
	rows = frappe.get_all(
		DEPLOYMENT_DOCTYPE,
		filters=[[DEPLOYMENT_DOCTYPE, "coordinator", "is", "not set"]],
		fields=["name", "owner"],
	)

	orphaned = []

	for row in rows:
		if row["owner"] and frappe.db.exists("User", row["owner"]):
			frappe.db.set_value(
				DEPLOYMENT_DOCTYPE, row["name"], "coordinator", row["owner"], update_modified=False
			)
			continue

		orphaned.append(row["name"])

	if orphaned:
		frappe.log_error(
			title="Deployments with no coordinator",
			message=(
				"These deployments were created by an account this site no longer has, so no"
				" responsible coordinator could be filled in. Somebody has to name one before"
				f" each can be saved again: {', '.join(orphaned)}"
			),
		)
