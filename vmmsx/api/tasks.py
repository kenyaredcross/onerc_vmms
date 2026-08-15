# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Task API — two doors, and they are checked differently on purpose.

**The coordinator's door** names a task and is checked the ordinary way:
Frappe's roles plus core's geo scoping, because `VMMS Task` is registered as
scopeable on its `geo_node` anchor. A coordinator may act on a task in their own
area and no argument widens that.

**The volunteer's door** also names a task, which the possessive endpoints
elsewhere in this app never do, so the check that would otherwise be missing is
written out: the task has to belong to the caller's own volunteer record. That is
**ownership**, not scope, and it is the distinction `participation.py` draws at
length. A volunteer holds no Geo Assignment, correctly, so a permission check
would refuse every one of them their own work; an ownership check refuses
everybody except the one person the task was assigned to.

`my_tasks` takes no argument at all, like `my_memberships` and `my_volunteer`,
so the list a volunteer sees cannot be pointed at anybody else.

**No endpoint returns a Document.** Both doors answer with `task.dto` or
`task.summary`, built field by field, so a schema change is not silently an API
change.
"""

import frappe
from frappe import _

from vmmsx.task.services import states
from vmmsx.task.services import task as task_service

TASK_DOCTYPE = "VMMS Task"

# A list is a list. A coordinator with a thousand tasks behind them wants the
# open ones, and the closed ones are a report rather than a screen.
PAGE = 100


# --- the coordinator's door -----------------------------------------------


@frappe.whitelist()
def assign_task(
	volunteer: str,
	subject: str,
	description: str,
	geo_node: str | None = None,
	due_on: str | None = None,
	deployment: str | None = None,
) -> dict:
	"""Assign a task to a volunteer and notify them.

	`create` permission on the task, checked before anything is written, and the
	anchor is checked by core's own scoping when the document is inserted: a
	coordinator cannot anchor a task outside the area they hold.
	"""
	frappe.has_permission(TASK_DOCTYPE, ptype="create", throw=True)

	return task_service.dto(
		task_service.assign(
			volunteer=volunteer,
			subject=subject,
			description=description,
			geo_node=geo_node,
			due_on=due_on,
			deployment=deployment,
		)
	)


@frappe.whitelist()
def branch_tasks(status: str | None = None, volunteer: str | None = None, limit: int | None = None) -> dict:
	"""Every task in the caller's own area, most recently touched first.

	**Scope is not a filter this endpoint applies; it is the floor it stands on**,
	the same as `volunteer.find_volunteers`. The query is `frappe.get_list`, not
	`frappe.get_all`: only the first runs core's permission query condition for
	`VMMS Task`, and the difference is the whole of the guarantee. Every argument
	below narrows that result and none of them widens it, so a task outside the
	caller's assignment is not returnable by any combination of them.

	An unknown status answers with nothing rather than with everything, which is
	the direction a filter should fail in.
	"""
	if status and status not in states.ALL:
		return _listing([])

	filters: dict = {}

	if status:
		filters["status"] = status

	if volunteer:
		filters["volunteer"] = volunteer

	names = frappe.get_list(
		TASK_DOCTYPE,
		filters=filters,
		order_by="modified desc",
		limit_page_length=min(int(limit or PAGE), PAGE),
		pluck="name",
	)

	return _listing([task_service.summary(frappe.get_doc(TASK_DOCTYPE, name)) for name in names])


def _listing(rows: list[dict]) -> dict:
	"""A page of tasks and the two counts a coordinator's attention is for.

	One shape for both the ordinary answer and the empty one, so a caller never
	has to tell the two apart.
	"""
	return {
		"count": len(rows),
		"tasks": rows,
		# What a coordinator's attention is actually for: work offered as done and
		# waiting on them, and questions nobody has answered. Counted from the
		# page rather than queried again, because both are properties of the rows
		# already in hand.
		"awaiting_sign_off": sum(1 for row in rows if row["status"] == states.SUBMITTED),
		"awaiting_answer": sum(1 for row in rows if row["open_question"]),
	}


@frappe.whitelist()
def get_task(name: str) -> dict:
	"""One task in full, with its thread, for whoever may see it.

	Either door reaches this: a coordinator through geo scoping, the volunteer it
	belongs to through ownership. Asking both questions here rather than in two
	endpoints keeps one answer to what a task looks like.
	"""
	return task_service.dto(_visible(name))


@frappe.whitelist()
def answer_question(name: str, reply: str) -> dict:
	"""Answer the volunteer's outstanding question."""
	return task_service.answer(_writable(name), reply)


@frappe.whitelist()
def request_progress(name: str, note: str | None = None) -> dict:
	"""Ask the volunteer how the work is going."""
	return task_service.request_progress(_writable(name), note)


@frappe.whitelist()
def sign_off(name: str, note: str | None = None) -> dict:
	"""Agree that submitted work is done. Idempotent."""
	return task_service.sign_off(_writable(name), note)


@frappe.whitelist()
def send_back(name: str, reason: str) -> dict:
	"""Return submitted work to the volunteer, saying why. Idempotent."""
	return task_service.send_back(_writable(name), reason)


@frappe.whitelist()
def cancel_task(name: str, reason: str | None = None) -> dict:
	"""Call a task off. Idempotent."""
	return task_service.cancel(_writable(name), reason)


# --- the volunteer's door -------------------------------------------------


@frappe.whitelist()
def my_tasks(include_closed: bool | int | str = False) -> dict | None:
	"""The caller's own tasks. Takes no person, so it names nobody.

	Open ones by default, because that is what a person opening the screen is
	there for. Nothing is geo-scoped out: a volunteer sent to help another county
	is entitled to the record of the work they were asked to do there, and
	filtering by where they may *look* would drop exactly the tasks worth showing
	them. Same argument as `deployment.my_deployments`.

	None for somebody who is not a volunteer, matching `my_volunteer`.
	"""
	volunteer = _my_volunteer()

	if not volunteer:
		return None

	filters: dict = {"volunteer": volunteer}

	if not _flag(include_closed):
		filters["status"] = ("in", states.OPEN)

	names = frappe.get_all(
		TASK_DOCTYPE,
		filters=filters,
		order_by="modified desc",
		limit_page_length=PAGE,
		pluck="name",
		# A volunteer reading their own tasks. The volunteer comes from the
		# session and is never an argument, so this cannot read anybody else's;
		# requiring read permission would mean granting every volunteer a role
		# over the whole task register to see the work assigned to them.
		ignore_permissions=True,
	)

	return {
		"volunteer": volunteer,
		"tasks": [task_service.summary(frappe.get_doc(TASK_DOCTYPE, name)) for name in names],
	}


@frappe.whitelist()
def accept_task(name: str) -> dict:
	"""Take on a task assigned to the caller. Idempotent."""
	return task_service.accept(_mine(name))


@frappe.whitelist()
def ask_about_task(name: str, question: str) -> dict:
	"""Ask a question about a task assigned to the caller."""
	return task_service.ask(_mine(name), question)


@frappe.whitelist()
def report_progress(name: str, note: str, proof: str | None = None) -> dict:
	"""Say how the work is going, optionally attaching a photograph.

	`proof` is a file URL Frappe's own upload endpoint returned, not a file: the
	upload is the framework's business and it has already decided what this
	person may store and how large it may be.
	"""
	return task_service.report_progress(_mine(name), note, proof=proof)


@frappe.whitelist()
def submit_task(name: str, note: str | None = None, proof: str | None = None) -> dict:
	"""Offer the work as done, for a coordinator to sign off. Idempotent.

	This does not complete the task, and the name says so. Completion is
	`sign_off`, on the other door, which is the whole point of `submitted` being
	a state of its own.
	"""
	return task_service.submit(_mine(name), note=note, proof=proof)


# --- shared ---------------------------------------------------------------


def _writable(name: str):
	"""A task the caller may act on as a coordinator.

	Ordinary permission: Frappe's roles and core's geo scoping, because the
	doctype is registered as scopeable. `write` rather than `read`, because every
	verb behind this changes the record.
	"""
	task = frappe.get_doc(TASK_DOCTYPE, name)
	task.check_permission("write")

	return task


def _mine(name: str):
	"""A task assigned to the caller's own volunteer record.

	Loaded without a read check, deliberately: a volunteer holds no Geo
	Assignment, so `check_permission` would refuse every one of them. The
	ownership check below is what stands in its place, and it is narrower than a
	permission check rather than wider, since it admits exactly one person.
	"""
	volunteer = _my_volunteer()

	if not volunteer:
		frappe.throw(
			_("You do not have a volunteer record, so no tasks are assigned to you."),
			frappe.PermissionError,
		)

	task = frappe.get_doc(TASK_DOCTYPE, name)

	if task.volunteer != volunteer:
		# The same answer as a task that does not exist. Telling the two apart
		# would let somebody probe for docnames.
		frappe.throw(_("That task is not assigned to you."), frappe.PermissionError)

	return task


def _visible(name: str):
	"""A task the caller may read through either door.

	The coordinator's question is asked first because it is the ordinary one, and
	the volunteer's is the fallback. A `PermissionError` from the first is not an
	answer yet, only the end of the first of two ways in.
	"""
	task = frappe.get_doc(TASK_DOCTYPE, name)

	try:
		task.check_permission("read")
	except frappe.PermissionError:
		if task.volunteer != _my_volunteer():
			raise

	return task


def _my_volunteer() -> str | None:
	"""The volunteer record of whoever is logged in, or None.

	Delegated to `api/volunteer.py`, which owns the two-hop resolution and its
	Guest refusal, for the reason `api/deployment.py` gives: a second copy would
	be a second answer to who the caller is, and the two would eventually
	disagree.
	"""
	from vmmsx.api.volunteer import _my_volunteer as resolve

	return resolve()


def _flag(value: bool | int | str) -> bool:
	"""A checkbox as it arrives over HTTP, where `"false"` is a truthy string."""
	if isinstance(value, str):
		return value.strip().lower() not in ("", "0", "false", "no")

	return bool(value)
