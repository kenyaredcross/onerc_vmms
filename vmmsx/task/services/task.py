# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Assigning work, and the conversation that follows it.

One service, one verb per thing that can happen to a task, every one of them
idempotent and every one of them taking a document rather than a name. The
lifecycle is `states.py`; this module is what moves along it and what gets told
each time it does.

    assign()             a coordinator creates and sends a task
    accept()             the volunteer takes it on
    ask()                the volunteer asks something
    answer()             a coordinator replies
    request_progress()   a coordinator asks how it is going
    report_progress()    the volunteer says, optionally with a photograph
    submit()             the volunteer offers the work as done
    sign_off()           a coordinator agrees, and the task is completed
    send_back()          a coordinator does not agree, and it returns to accepted
    cancel()             a coordinator calls it off

**Every move is a state change plus a thread entry plus a notification, in that
order, and the order is what makes idempotence real.** Each verb first asks
whether its move is still available. A second `accept()` on an accepted task
observes that, returns the same answer, and never reaches the thread or the
notification, so nothing is said twice. This is the same guarantee
`announce.publish()` gives, arrived at the same way, and it is why
`notifications/services/direct.py` does not need idempotence of its own.

**Who may do what is not decided here.** This module is called from
`api/tasks.py`, which checks permission on the coordinator's verbs and ownership
on the volunteer's, and from nowhere else. Putting the check here would mean a
service that could not be called by a background job or a seed.

**Two audiences, resolved separately.** A volunteer is told through the login
behind their Red Profile, which they may not have. A coordinator is told through
`doc.owner`, which is the person who filed the task, and that is the right answer
here for the reason `invitation.askers` gives at length: this asks who did the
filing, not who a record is about.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from vmmsx.notifications.services import direct
from vmmsx.task.services import states

TASK_DOCTYPE = "VMMS Task"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"

# The thread's own vocabulary. Display only, and nothing in this app branches on
# one of these values: they are what makes a thread read as a conversation.
ENTRY_ASSIGNED = "assigned"
ENTRY_ACCEPTED = "accepted"
ENTRY_QUESTION = "question"
ENTRY_ANSWER = "answer"
ENTRY_PROGRESS_REQUESTED = "progress requested"
ENTRY_PROGRESS = "progress"
ENTRY_SUBMITTED = "submitted"
ENTRY_COMPLETED = "completed"
ENTRY_RETURNED = "returned"
ENTRY_CANCELLED = "cancelled"

THREAD_FIELD = "updates"


# --- creating one ---------------------------------------------------------


def assign(
	volunteer: str,
	subject: str,
	description: str,
	geo_node: str | None = None,
	due_on: str | None = None,
	deployment: str | None = None,
) -> "frappe.Document":
	"""Create a task, put it in the volunteer's list, and tell them.

	The one verb here that takes arguments rather than a document, because it is
	the one that makes the document. Everything after it is a move on a task that
	already exists.

	`geo_node` falls back to the volunteer's own branch, which is what a
	coordinator assigning work to somebody in front of them means. It is a
	fallback and not a rule: work is sometimes anchored where it happens rather
	than where the person lives, and ACC-02 asks for an anchor, not for a
	particular one. A volunteer with no branch and no anchor given is refused,
	because a task nobody can see is a task nobody will chase.
	"""
	anchor = geo_node or frappe.db.get_value(VOLUNTEER_DOCTYPE, volunteer, "home_geo_node")

	if not anchor:
		frappe.throw(
			_(
				"This task needs to say which part of the society it belongs to, and the"
				" volunteer has no branch to take it from. Choose one."
			),
			frappe.ValidationError,
			title=_("No Anchor"),
		)

	task = frappe.get_doc(
		{
			"doctype": TASK_DOCTYPE,
			"volunteer": volunteer,
			"subject": subject,
			"description": description,
			"geo_node": anchor,
			"due_on": due_on,
			"deployment": deployment,
			"status": states.ASSIGNED,
			"assigned_on": now_datetime(),
		}
	)

	_add_entry(task, ENTRY_ASSIGNED, description)
	task.insert()

	_tell_volunteer(task, _("You have been assigned a task: {0}").format(task.subject))

	return task


# --- the volunteer's verbs ------------------------------------------------


def accept(task) -> dict:
	"""Take the task on. Idempotent, and the second call changes nothing."""
	if not states.can_move(task.status, states.ACCEPTED) or task.status != states.ASSIGNED:
		return _outcome(task, moved=False)

	task.status = states.ACCEPTED
	task.accepted_on = now_datetime()

	_add_entry(task, ENTRY_ACCEPTED, None)
	_save(task)

	_tell_coordinators(task, _("A volunteer accepted the task: {0}").format(task.subject))

	return _outcome(task, moved=True)


def ask(task, question: str) -> dict:
	"""Ask something about the task, without moving it.

	Not idempotent, and correctly so: two questions are two questions, and the
	verb that has to be safe to repeat is the one that changes state. What is
	guarded is asking on a finished task, which would be a question nobody is
	going to answer.
	"""
	_assert_open(task)

	task.open_question = 1

	_add_entry(task, ENTRY_QUESTION, question)
	_save(task)

	_tell_coordinators(task, _("A volunteer asked about the task: {0}").format(task.subject))

	return _outcome(task, moved=False)


def report_progress(task, note: str, proof: str | None = None) -> dict:
	"""Say how the work is going, optionally with a photograph.

	Separate from `submit()` on purpose. A progress report is not an offer to
	close the task, and a coordinator reading one is not being asked to decide
	anything. Conflating the two would mean every update landing in somebody's
	decision queue.
	"""
	_assert_open(task)

	_add_entry(task, ENTRY_PROGRESS, note, proof=proof)
	_save(task)

	_tell_coordinators(task, _("A volunteer reported progress on the task: {0}").format(task.subject))

	return _outcome(task, moved=False)


def submit(task, note: str | None = None, proof: str | None = None) -> dict:
	"""Offer the work as done, for a coordinator to agree with. Idempotent.

	**Not `completed`.** The volunteer's word is what moves it here, and a
	coordinator's is what moves it the rest of the way, which is exactly what the
	brief asked for and the reason `submitted` is a state of its own.
	"""
	if not states.can_move(task.status, states.SUBMITTED):
		return _outcome(task, moved=False)

	task.status = states.SUBMITTED
	task.submitted_on = now_datetime()
	task.completion_notes = note

	_add_entry(task, ENTRY_SUBMITTED, note, proof=proof)
	_save(task)

	_tell_coordinators(task, _("A volunteer says a task is done: {0}").format(task.subject))

	return _outcome(task, moved=True)


# --- the coordinator's verbs ----------------------------------------------


def answer(task, reply: str) -> dict:
	"""Answer the volunteer's question and clear the flag. Idempotent in effect.

	Safe to call with no question outstanding: the reply is still worth recording
	and the flag is already down, so the second call is a note in the thread and
	nothing else.
	"""
	_assert_open(task)

	task.open_question = 0

	_add_entry(task, ENTRY_ANSWER, reply)
	_save(task)

	_tell_volunteer(task, _("Your question was answered on the task: {0}").format(task.subject))

	return _outcome(task, moved=False)


def request_progress(task, note: str | None = None) -> dict:
	"""Ask the volunteer how it is going."""
	_assert_open(task)

	_add_entry(task, ENTRY_PROGRESS_REQUESTED, note)
	_save(task)

	_tell_volunteer(task, _("An update was requested on your task: {0}").format(task.subject))

	return _outcome(task, moved=False)


def sign_off(task, note: str | None = None) -> dict:
	"""Agree the work is done. Idempotent, and terminal."""
	if not states.can_move(task.status, states.COMPLETED):
		return _outcome(task, moved=False)

	task.status = states.COMPLETED
	task.closed_on = now_datetime()
	task.open_question = 0

	_add_entry(task, ENTRY_COMPLETED, note)
	_save(task)

	_tell_volunteer(task, _("Your completed task was approved: {0}").format(task.subject))

	return _outcome(task, moved=True)


def send_back(task, reason: str) -> dict:
	"""Do not agree, and return the task to the volunteer. Idempotent.

	The only backwards move in the state table. `submitted_on` is cleared with
	it, because a task that has been sent back has not been submitted any more
	and a date left behind would say it had.

	A reason is required rather than optional: sending work back without saying
	why is how a volunteer learns nothing and submits the same thing again.
	"""
	if not states.can_move(task.status, states.ACCEPTED):
		return _outcome(task, moved=False)

	task.status = states.ACCEPTED
	task.submitted_on = None

	_add_entry(task, ENTRY_RETURNED, reason)
	_save(task)

	_tell_volunteer(task, _("Your task needs more work: {0}").format(task.subject))

	return _outcome(task, moved=True)


def cancel(task, reason: str | None = None) -> dict:
	"""Call the task off. Idempotent, and terminal.

	Available from every open state, including `submitted`: a task overtaken by
	events after somebody offered it as done still has to be closable, and the
	honest close is a cancellation rather than an approval of work that is no
	longer wanted.
	"""
	if not states.can_move(task.status, states.CANCELLED):
		return _outcome(task, moved=False)

	task.status = states.CANCELLED
	task.closed_on = now_datetime()
	task.open_question = 0

	_add_entry(task, ENTRY_CANCELLED, reason)
	_save(task)

	_tell_volunteer(task, _("A task assigned to you was cancelled: {0}").format(task.subject))

	return _outcome(task, moved=True)


# --- reading --------------------------------------------------------------


def dto(task) -> dict:
	"""One task, built field by field, with its thread.

	Never the document: a `VMMS Task` carries fields nobody reviewed for
	disclosure, and the rule about explicit DTOs on public endpoints exists so
	that adding a field to the schema is not silently adding it to the API.
	"""
	return {
		"name": task.name,
		"subject": task.subject,
		"description": task.description,
		"status": task.status,
		"volunteer": task.volunteer,
		"geo_node": task.geo_node,
		"deployment": task.deployment,
		"due_on": task.due_on,
		"assigned_on": task.assigned_on,
		"accepted_on": task.accepted_on,
		"submitted_on": task.submitted_on,
		"closed_on": task.closed_on,
		"open_question": bool(task.open_question),
		"completion_notes": task.completion_notes,
		"is_open": states.is_open(task.status),
		"thread": [
			{
				"entry_type": row.entry_type,
				"author": row.author,
				"posted_on": row.posted_on,
				"note": row.note,
				"proof": row.proof,
			}
			for row in task.updates or []
		],
	}


def summary(task) -> dict:
	"""A task as it appears in a list. The DTO without the thread.

	A separate shape rather than the full one trimmed by the caller, because a
	list of thirty tasks each carrying its whole conversation is a response
	nobody wanted and a disclosure nobody reviewed.
	"""
	return {
		"name": task.name,
		"subject": task.subject,
		"status": task.status,
		"volunteer": task.volunteer,
		"geo_node": task.geo_node,
		"due_on": task.due_on,
		"assigned_on": task.assigned_on,
		"open_question": bool(task.open_question),
		"is_open": states.is_open(task.status),
	}


# --- the plumbing ---------------------------------------------------------


def _assert_open(task) -> None:
	"""Refuse to write to a finished task.

	A ValidationError rather than a PermissionError, the same distinction
	`participation.assert_participant` draws: this is not about the acting user's
	authority, it is about whether the thing being described can still happen. A
	coordinator with every permission there is may not add to a cancelled task's
	thread either.
	"""
	if states.is_open(task.status):
		return

	frappe.throw(
		_("This task is {0} and nothing more can be added to it.").format(task.status),
		frappe.ValidationError,
		title=_("Task Is Closed"),
	)


def _save(task) -> None:
	"""Write a move that has already been authorised at the boundary.

	**The one elevated write in this module, and the reason is the volunteer.**
	A volunteer holds no role on `VMMS Task` and correctly never will: the task
	register is a coordinator's, and granting every volunteer write permission on
	it so they could accept their own work would hand them the whole register to
	get at one row of it. So an ordinary `save()` here refuses the person the
	verb exists for.

	What replaces the permission check is not nothing. Every caller reaches this
	through `api/tasks.py`, which has already answered the authority question in
	the way that fits the door it is: `_writable` checks `write` permission, which
	brings core's geo scoping with it, and `_mine` checks that the task is
	assigned to the caller's own volunteer record. That is the same division the
	approval engine draws, and for the same reason it draws it: authority is
	decided once, at the boundary, by the code that knows which question to ask,
	and the service below it moves state.

	**`assign()` deliberately does not use this.** Creating a task is an ordinary
	`insert()` through the ordinary permission layer, because the person creating
	one is a coordinator who does hold the role, and core's scoping has to run on
	the anchor so a coordinator cannot file work outside their own area.
	"""
	task.save(ignore_permissions=True)


def _add_entry(task, entry_type: str, note: str | None, proof: str | None = None) -> None:
	"""Append one entry to the thread.

	The author is the session and never an argument, so no caller can make the
	thread say somebody said something they did not. The time is stamped here
	rather than by the form, so the order of a conversation is the order it
	happened in.
	"""
	task.append(
		THREAD_FIELD,
		{
			"entry_type": entry_type,
			"author": frappe.session.user,
			"posted_on": now_datetime(),
			"note": note,
			"proof": proof,
		},
	)


def _outcome(task, moved: bool) -> dict:
	"""What a caller is told. `moved` is the visible form of idempotence: the
	second identical call answers with the same state and `moved` false."""
	return {
		"task": task.name,
		"status": task.status,
		"open_question": bool(task.open_question),
		"moved": moved,
	}


def _tell_volunteer(task, subject: str) -> list[str]:
	"""Notify whoever holds this task, if they have a login to be notified at."""
	login = direct.login_of(task.volunteer)

	return direct.tell([login] if login else [], subject, TASK_DOCTYPE, task.name)


def _tell_coordinators(task, subject: str) -> list[str]:
	"""Notify whoever assigned the task.

	`doc.owner`, which is the person who filed it. The self-service rules
	elsewhere in this app insist the bypass is `Red Profile.user` and not
	`doc.owner`, and this is the other case that rule distinguishes: those ask
	who a record is *about*, and a task is about the volunteer. This asks who
	*asked for* the work, and `owner` is exactly that person.
	"""
	if task.owner == frappe.session.user or task.owner == "Administrator":
		return []

	return direct.tell([task.owner], subject, TASK_DOCTYPE, task.name)
