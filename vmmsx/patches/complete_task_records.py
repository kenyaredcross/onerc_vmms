# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Give every existing task the deadline field it now carries, and a priority.

`VMMS Task` grew a due *datetime* and a priority. The datetime is the authored
field now and the day beside it is derived from it, so a task written before this
existed carries a day and no datetime — and the first person to save one would
find its deadline quietly cleared, because `derive_due_day` reads the datetime.

The controller fills the datetime back from the day for exactly that reason, so
nothing is broken without this patch; what it buys is that every *query* on
`due_at` — the overdue sweep, the register's own ordering — sees the whole
register rather than only the rows somebody has saved since. A day with no time
is taken as the end of that day, which is what a deadline given in days has
always meant.

`priority` is filled to Normal for the same reason: a Select left null sorts and
filters differently from one holding the value everything else holds, and a
register where half the rows have no priority is a register nobody can sort.

**Written with `db.set_value`.** Saving each document would run `validate`, which
walks the dependency graph and re-derives the day — real work, on every task on
the site, to write two values that are derived from what the row already says.
"""

import frappe

TASK_DOCTYPE = "VMMS Task"


def execute():
	if not frappe.db.table_exists(TASK_DOCTYPE):
		return

	for row in frappe.get_all(
		TASK_DOCTYPE,
		filters=[
			[TASK_DOCTYPE, "due_at", "is", "not set"],
			[TASK_DOCTYPE, "due_on", "is", "set"],
		],
		fields=["name", "due_on"],
	):
		frappe.db.set_value(
			TASK_DOCTYPE, row["name"], "due_at", f"{row['due_on']} 23:59:59", update_modified=False
		)

	for name in frappe.get_all(
		TASK_DOCTYPE, filters=[[TASK_DOCTYPE, "priority", "is", "not set"]], pluck="name"
	):
		frappe.db.set_value(TASK_DOCTYPE, name, "priority", "Normal", update_modified=False)
