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

from vmmsx.task.services import batch as batch_service
from vmmsx.task.services import states
from vmmsx.task.services import task as task_service

TASK_DOCTYPE = "VMMS Task"
BATCH_DOCTYPE = "VMMS Task Batch"

# A list is a list. A coordinator with a thousand tasks behind them wants the
# open ones, and the closed ones are a report rather than a screen.
PAGE = 100


# --- the coordinator's door -----------------------------------------------


@frappe.whitelist()
def task_options() -> dict:
	"""Every list the assign form draws a control from, in one call.

	The same shape `api/volunteer.py::application_options` and the recruitment
	console's `options` take, and for the same reason: four selects each fetching
	their own vocabulary is four chances for a form to render half-populated.

	`priorities` and the task's own kinds come from the record; `escalate_to` is
	a `User` and is deliberately **not** a whole-directory read — the escalation
	target is somebody in the society's staff, and the picker searches rather
	than enumerating. That is why it is absent here and asked for by name.

	Read permission on the task, which is the floor for a screen that is about to
	create one. Nothing here is scoped, because a vocabulary says nothing about
	any person or any place.
	"""
	frappe.has_permission(TASK_DOCTYPE, ptype="read", throw=True)

	priority = frappe.get_meta(TASK_DOCTYPE).get_field("priority")

	return {
		"priorities": [
			option.strip() for option in (priority.options or "").split("\n") if option.strip()
		]
		if priority
		else [],
		"task_types": frappe.get_all(
			"VMMS Task Type",
			filters={"is_active": 1},
			fields=["name", "task_type_name"],
			order_by="task_type_name asc",
		),
		# ERPNext's, and absent on a site without it — the same graceful absence
		# the recruitment options keep.
		"projects": frappe.get_all("Project", fields=["name", "project_name"], order_by="name asc")
		if frappe.db.exists("DocType", "Project")
		else [],
	}


@frappe.whitelist()
def assign_task(
	volunteer: str,
	subject: str,
	description: str,
	geo_node: str | None = None,
	due_on: str | None = None,
	deployment: str | None = None,
	**extra,
) -> dict:
	"""Assign a task to a volunteer and notify them.

	`create` permission on the task, checked before anything is written, and the
	anchor is checked by core's own scoping when the document is inserted: a
	coordinator cannot anchor a task outside the area they hold.

	Everything past `deployment` is optional and arrives through `**extra`,
	filtered against `task.ASSIGNABLE` and `task.ASSIGNABLE_TABLES` by the
	service — so a caller that sends an extra key writes nothing rather than
	writing a field nobody reviewed. The three tables are parsed out of the JSON
	they may arrive as, the same way the terms editor's payload is.
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
			**_payload(extra),
		)
	)


def _payload(values: dict) -> dict:
	"""A task payload with its child tables parsed out of the JSON they arrive as.

	Frappe hands a whitelisted method either a real list or the JSON string it was
	sent, depending on how the caller framed the request. Parsed here so the
	service takes lists either way; unknown keys are left for the service to
	ignore rather than being filtered twice in two places that could disagree.
	"""
	parsed = dict(values)

	for field in task_service.ASSIGNABLE_TABLES:
		if isinstance(parsed.get(field), str):
			parsed[field] = frappe.parse_json(parsed[field]) or []

	return parsed


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
def sign_off(
	name: str,
	note: str | None = None,
	outcome: str | None = None,
	rating: int | None = None,
	lessons: str | None = None,
	hours: float | None = None,
) -> dict:
	"""Agree that submitted work is done. Idempotent.

	Everything past `note` is optional and nothing waits for any of it: a sign-off
	that could be blocked by an unfilled rating is a sign-off that does not
	happen.
	"""
	return task_service.sign_off(
		_writable(name), note, outcome=outcome, rating=rating, lessons=lessons, hours=hours
	)


@frappe.whitelist()
def reassign_task(name: str, volunteer: str, reason: str) -> dict:
	"""Give the same work to somebody else, keeping both records.

	The original is never overwritten: it moves to `reassigned` and points at the
	task that took over, which points back. Editing the volunteer instead would
	erase the fact that anybody had ever been asked — and quietly remove an entry
	from the first person's own record of what they were asked to do.
	"""
	return task_service.reassign(_writable(name), volunteer, reason)


@frappe.whitelist()
def escalate_task(name: str, reason: str | None = None) -> dict:
	"""Raise a task with whoever the coordinator named on it. Records it.

	Silent where nobody was named, which is the shipped state: escalating to a
	person a society never chose would mean guessing at a hierarchy this app does
	not have.
	"""
	return task_service.escalate(_writable(name), reason)


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
def report_progress(
	name: str, note: str, proof: str | None = None, percent: float | None = None
) -> dict:
	"""Say how the work is going, optionally attaching a photograph.

	`proof` is a file URL Frappe's own upload endpoint returned, not a file: the
	upload is the framework's business and it has already decided what this
	person may store and how large it may be.

	`percent` is the volunteer's own estimate and is never inferred from the
	checklist: a number this app worked out would be this app's opinion wearing
	their name.
	"""
	return task_service.report_progress(_mine(name), note, proof=proof, percent=percent)


@frappe.whitelist()
def decline_task(name: str, reason: str) -> dict:
	"""Say no to a task, before starting it. Idempotent.

	Only from `assigned`: somebody who accepted work and then cannot do it has not
	declined it, and that belongs in front of the coordinator rather than in a
	button. A reason is required, because a refusal nobody explained teaches the
	next coordinator nothing.
	"""
	return task_service.decline(_mine(name), reason)


@frappe.whitelist()
def tick_checklist(
	name: str,
	index: int,
	done: bool | int | str = True,
	notes: str | None = None,
	evidence: str | None = None,
) -> dict:
	"""Mark one checklist item done, or undo it. Idempotent on the same answer."""
	return task_service.tick(
		_mine(name), index, done=_flag(done), notes=notes, evidence=evidence
	)


@frappe.whitelist()
def submit_task(
	name: str,
	note: str | None = None,
	proof: str | None = None,
	hours: float | None = None,
	evidence: str | None = None,
) -> dict:
	"""Offer the work as done, for a coordinator to sign off. Idempotent.

	This does not complete the task, and the name says so. Completion is
	`sign_off`, on the other door, which is the whole point of `submitted` being
	a state of its own.

	Refused while a required checklist item is unticked — the one thing on a task
	that stops a submission, and the reason the checklist has a required flag at
	all.
	"""
	return task_service.submit(
		_mine(name), note=note, proof=proof, hours=hours, evidence=evidence
	)


# --- the batch door -------------------------------------------------------
#
# A batch is a coordinator's record, so every endpoint here is on the
# coordinator's door: ordinary permission, which brings core's geo scoping with
# it. A volunteer never sees a batch — they see the task it made them, which is
# an ordinary task from the moment it exists.


@frappe.whitelist()
def create_batch(
	subject: str,
	brief: str,
	geo_node: str,
	volunteers: list | str | None = None,
	**values,
) -> dict:
	"""Open a batch: the brief, where it belongs, and who it is for.

	Creating it generates nothing. Drawing up the list and sending the work are
	two acts, and a coordinator wants to look at the list — and at
	`preview_batch`'s verdict on it — before forty people are told anything.
	"""
	frappe.has_permission(BATCH_DOCTYPE, ptype="create", throw=True)

	names = frappe.parse_json(volunteers) if isinstance(volunteers, str) else (volunteers or [])

	doc = frappe.get_doc(
		{
			"doctype": BATCH_DOCTYPE,
			"subject": subject,
			"brief": brief,
			"geo_node": geo_node,
			**{field: values[field] for field in _BATCH_FIELDS if field in values},
			"volunteers": [{"volunteer": name} for name in names if name],
		}
	)
	doc.insert()

	return batch_service.report(doc)


# What a caller may set on a batch beyond the three it must. Named as data so an
# extra key in a request writes nothing rather than a field nobody reviewed.
_BATCH_FIELDS = ("project", "deployment", "due_at", "task_type", "priority", "notes")


@frappe.whitelist()
def add_to_batch(name: str, volunteers: list | str) -> dict:
	"""Add people to a batch. Legal after generation, unlike everything else on it.

	The one part of a generated batch that is still a coordinator's to change,
	and deliberately: adding somebody and generating again is how a batch grows.
	The rows already resolved are untouched by the next run.
	"""
	doc = _batch(name)
	names = frappe.parse_json(volunteers) if isinstance(volunteers, str) else (volunteers or [])
	held = {row.volunteer for row in doc.volunteers or []}

	for volunteer in names:
		if volunteer and volunteer not in held:
			doc.append("volunteers", {"volunteer": volunteer})

	doc.save()

	return batch_service.report(doc)


@frappe.whitelist()
def preview_batch(name: str) -> dict:
	"""What generating this batch would do, without doing any of it.

	The same predicate `generate_batch` uses, so the preview and the run cannot
	disagree about who is going to get a task.
	"""
	return batch_service.preview(_batch(name, write=False))


@frappe.whitelist()
def generate_batch(name: str) -> dict:
	"""Create one task per unresolved volunteer, and report row by row.

	Safe to run again: a row that already has its task is passed over, a row that
	failed is tried again. One bad row never blocks a good one — each person is
	written inside their own savepoint.
	"""
	return batch_service.generate(_batch(name))


@frappe.whitelist()
def get_batch(name: str) -> dict:
	"""One batch: its rows, and how the work it generated is going."""
	doc = _batch(name, write=False)

	return {
		"batch": {
			"name": doc.name,
			"subject": doc.subject,
			"brief": doc.brief,
			"geo_node": doc.geo_node,
			"project": doc.project,
			"deployment": doc.deployment,
			"due_at": doc.due_at,
			"task_type": doc.task_type,
			"priority": doc.priority,
			"notes": doc.notes,
			"generated_on": doc.generated_on,
			"generated_by": doc.generated_by,
			"is_generated": bool(doc.generated_on),
		},
		"report": batch_service.report(doc),
		"counts": batch_service.counts(doc),
	}


@frappe.whitelist()
def branch_batches(limit: int | None = None) -> dict:
	"""Batches in the caller's own area, newest first.

	`frappe.get_list`, not `get_all`: only the first runs core's permission query
	condition, and the second is a whole-site answer wearing the shape of a scoped
	one.
	"""
	names = frappe.get_list(
		BATCH_DOCTYPE,
		order_by="creation desc",
		limit_page_length=min(int(limit or PAGE), PAGE),
		pluck="name",
	)
	rows = []

	for batch in names:
		doc = frappe.get_doc(BATCH_DOCTYPE, batch)
		rows.append(
			{
				"name": doc.name,
				"subject": doc.subject,
				"geo_node": doc.geo_node,
				"generated_on": doc.generated_on,
				"counts": batch_service.counts(doc),
			}
		)

	return {"count": len(rows), "batches": rows}


@frappe.whitelist()
def batch_candidates(name: str, **filters) -> dict:
	"""Volunteers this batch could go to, within the caller's own area.

	`matching.candidates` with the batch's own defaults filled in — its anchor,
	its deployment's terms of reference where it has one, and its due date as the
	day the availability question is asked about. The scope is the caller's
	session and cannot be supplied.
	"""
	return batch_service.candidates(_batch(name, write=False), **filters)


def _batch(name: str, write: bool = True):
	"""A batch the caller may see, and may act on where `write` is asked for.

	Ordinary permission, which brings core's geo scoping with it. The same shape
	`_writable`/`_visible` have below, kept separate because a batch is not a task
	and neither door's ownership rule applies to it.
	"""
	doc = frappe.get_doc(BATCH_DOCTYPE, name)
	doc.check_permission("write" if write else "read")

	return doc


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
