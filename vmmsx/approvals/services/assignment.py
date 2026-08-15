# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Putting the document in the right person's queue.

Routing names people; this puts the document in front of them. Frappe's
assignment (a ToDo plus `_assign`) is the desk's own inbox, so an approval
arrives where the approver already looks instead of in a role-wide list nobody
owns.

**Assignment is a notification, never an authorisation.** The gate asks routing
who may act, every time, and never reads a ToDo — otherwise any desk user who
can create an assignment could hand themselves an approval. That is why `sync`
is free to be lossy: a ToDo somebody closed by hand costs a reminder, not a
decision.

Every function here is idempotent. `sync` computes the difference between who
should hold the document and who does, so calling it twice adds nothing twice.
"""

import frappe
from frappe.desk.form import assign_to

OPEN_STATUSES = ("Open", "Overdue")


def assignees(doctype: str, name: str) -> set[str]:
	"""Who currently holds this document in their queue.

	`frappe.get_all` rather than `assign_to.get`, which caps at five rows — a
	silent truncation would make `sync` re-add the sixth approver on every
	call.
	"""
	return set(
		frappe.get_all(
			"ToDo",
			filters={
				"reference_type": doctype,
				"reference_name": name,
				"status": ("in", OPEN_STATUSES),
			},
			pluck="allocated_to",
		)
	)


def sync(doctype: str, name: str, users: list[str], description: str | None = None) -> dict:
	"""Make the queue holders exactly `users`. Returns what changed."""
	desired = set(users or [])
	current = assignees(doctype, name)

	added = sorted(desired - current)
	removed = sorted(current - desired)

	if added:
		_assign(doctype, name, added, description)

	for user in removed:
		assign_to.remove(doctype, name, user)

	return {"added": added, "removed": removed}


def add(doctype: str, name: str, users: list[str], description: str | None = None) -> dict:
	"""Add holders without removing anyone — what an escalation does.

	An escalation widens the queue rather than replacing it: the original
	approver is late, not relieved of the application, and taking it off their
	desk would hide the fact that they were late from the only person who could
	notice.
	"""
	added = sorted(set(users or []) - assignees(doctype, name))

	if added:
		_assign(doctype, name, added, description)

	return {"added": added, "removed": []}


def clear(doctype: str, name: str) -> dict:
	"""Empty the queue — a decided application is nobody's task."""
	return sync(doctype, name, [])


def _assign(doctype: str, name: str, users: list[str], description: str | None) -> None:
	assign_to.add(
		{
			"doctype": doctype,
			"name": name,
			"assign_to": users,
			"description": description or "",
		}
	)
