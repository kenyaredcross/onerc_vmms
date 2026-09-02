# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Assigning work, and the conversation that follows it.

One service, one verb per thing that can happen to a task, every one of them
idempotent and every one of them taking a document rather than a name. The
lifecycle is `states.py`; this module is what moves along it and what gets told
each time it does.

    assign()             a coordinator creates and sends a task
    accept()             the volunteer takes it on
    decline()            the volunteer says no, before starting
    ask()                the volunteer asks something
    answer()             a coordinator replies
    request_progress()   a coordinator asks how it is going
    report_progress()    the volunteer says, optionally with a photograph
    tick()               the volunteer marks one checklist item done
    submit()             the volunteer offers the work as done
    sign_off()           a coordinator agrees, and the task is completed
    send_back()          a coordinator does not agree, and it returns to accepted
    reassign()           a coordinator gives the same work to somebody else
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

**Three things gate a task, and everything else is a record.** A required
checklist item that is not ticked stops a submission; an unfinished dependency
stops a start unless a manager writes down why; and the state table stops
everything it does not contain. Nothing else refuses anything — not a missing
expected-hours figure, not an unanswered response deadline, not an empty
briefing-file list — because a field nobody filled in is a record-keeping gap and
turning one into a refusal is how a gap becomes an operational failure. The same
argument `deployment/services/assignment.py` makes about readiness.

**Reassignment keeps both records**, the way a deployment replacement does: the
original moves to `reassigned` and points at the task that took it over, which
points back. Overwriting the volunteer would erase the fact that anybody was ever
asked.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, get_datetime, getdate, now_datetime

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
ENTRY_DECLINED = "declined"
ENTRY_REASSIGNED = "reassigned"
ENTRY_ESCALATED = "escalated"
ENTRY_REMINDED = "reminded"

THREAD_FIELD = "updates"


# --- creating one ---------------------------------------------------------


# Everything `assign` will copy off a caller and nothing else, so a caller that
# passes an extra key cannot write a field nobody reviewed. Named as data rather
# than as fifteen keyword arguments because `batch.py` builds this dict from a
# batch record and would otherwise have to spell every one of them twice.
ASSIGNABLE = (
	"priority",
	"task_type",
	"project",
	"due_at",
	"planned_start",
	"planned_end",
	"response_deadline",
	"expected_hours",
	"reminder_every_days",
	"escalate_to",
	# The manager's written override for a dependency that is not finished. On
	# the list because a coordinator lining work up out of order says so when
	# they set it, not afterwards on a form the volunteer is looking at.
	"blocked_override_reason",
	"work_name",
	"work_address",
	"work_latitude",
	"work_longitude",
	"meeting_name",
	"meeting_address",
	"meeting_latitude",
	"meeting_longitude",
	"travel_instructions",
	"local_contact_name",
	"local_contact_phone",
)

# The two child tables a coordinator may set up front. Separate from `ASSIGNABLE`
# because they are lists of rows rather than values, and because each is
# normalised column by column rather than passed through.
ASSIGNABLE_TABLES = {
	"checklist": ("item", "is_required", "notes"),
	"brief_files": ("label", "file", "notes"),
	"depends_on": ("depends_on", "notes"),
}


def assign(
	volunteer: str,
	subject: str,
	description: str,
	geo_node: str | None = None,
	due_on: str | None = None,
	deployment: str | None = None,
	**extra,
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
			# The day is derived from the datetime in `validate`. A caller that has
			# only a day passes `due_on` and gets the end of it, which is what a
			# deadline given in days has always meant.
			"due_at": extra.get("due_at") or (f"{getdate(due_on)} 23:59:59" if due_on else None),
			"deployment": deployment,
			"status": states.ASSIGNED,
			"assigned_on": now_datetime(),
			**{field: extra[field] for field in ASSIGNABLE if field in extra},
			**{
				field: _rows(extra[field], columns)
				for field, columns in ASSIGNABLE_TABLES.items()
				if field in extra
			},
		}
	)

	_add_entry(task, ENTRY_ASSIGNED, description)
	task.insert()

	_tell_volunteer(task, _("You have been assigned a task: {0}").format(task.subject))

	return task


# --- the volunteer's verbs ------------------------------------------------


def accept(task) -> dict:
	"""Take the task on. Idempotent, and the second call changes nothing.

	**Where the dependency gate fires.** Accepting is starting, so this is the
	moment something unfinished in front of the task matters — not the moment it
	was assigned, when a coordinator may perfectly well be lining up work in
	order. A manager's written override in `blocked_override_reason` lets it
	through; `assert_startable` says why that exists.
	"""
	if not states.can_move(task.status, states.ACCEPTED) or task.status != states.ASSIGNED:
		return _outcome(task, moved=False)

	assert_startable(task)

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


def report_progress(
	task, note: str, proof: str | None = None, percent: float | None = None
) -> dict:
	"""Say how the work is going, optionally with a photograph.

	Separate from `submit()` on purpose. A progress report is not an offer to
	close the task, and a coordinator reading one is not being asked to decide
	anything. Conflating the two would mean every update landing in somebody's
	decision queue.

	`percent` is optional and never inferred from anything: a volunteer who has
	not said how far along they are has not said, and a number this app worked out
	from the checklist would be this app's opinion wearing their name.
	"""
	_assert_open(task)

	if percent is not None:
		task.percent_complete = min(max(flt(percent), 0), 100)

	_add_entry(task, ENTRY_PROGRESS, note, proof=proof)
	_save(task)

	_tell_coordinators(task, _("A volunteer reported progress on the task: {0}").format(task.subject))

	return _outcome(task, moved=False)


def submit(
	task,
	note: str | None = None,
	proof: str | None = None,
	hours: float | None = None,
	evidence: str | None = None,
) -> dict:
	"""Offer the work as done, for a coordinator to agree with. Idempotent.

	**Not `completed`.** The volunteer's word is what moves it here, and a
	coordinator's is what moves it the rest of the way, which is exactly what the
	brief asked for and the reason `submitted` is a state of its own.
	"""
	if not states.can_move(task.status, states.SUBMITTED):
		return _outcome(task, moved=False)

	assert_checklist(task)

	task.status = states.SUBMITTED
	task.submitted_on = now_datetime()
	task.completion_notes = note

	if hours is not None:
		task.actual_hours = flt(hours)

	if evidence is not None:
		task.final_evidence = evidence

	# Handing work in is saying it is finished. A percentage left at ninety on a
	# submitted task is a number somebody forgot rather than a claim they meant.
	task.percent_complete = 100

	_add_entry(task, ENTRY_SUBMITTED, note, proof=proof)
	_save(task)

	_tell_coordinators(task, _("A volunteer says a task is done: {0}").format(task.subject))

	return _outcome(task, moved=True)


def decline(task, reason: str) -> dict:
	"""Say no, before starting. Idempotent, and terminal.

	**Only from `assigned`.** Somebody who accepted work and then cannot do it has
	not declined it; they have stopped, after a coordinator planned around them,
	and that belongs in front of the coordinator rather than in a button the
	volunteer can press alone. The state table is what enforces that, and
	`states.py` carries the argument.

	A reason is required, for the same reason `send_back` requires one: a refusal
	nobody explained teaches the next coordinator nothing, and they will ask the
	same person again next week.
	"""
	if not (reason or "").strip():
		frappe.throw(
			_("Say why you cannot take this on. It is the one thing the record cannot infer."),
			frappe.MandatoryError,
			title=_("No Reason Given"),
		)

	if not states.can_move(task.status, states.DECLINED):
		return _outcome(task, moved=False)

	task.status = states.DECLINED
	task.decline_reason = reason
	task.closed_on = now_datetime()
	task.open_question = 0

	_add_entry(task, ENTRY_DECLINED, reason)
	_save(task)

	_tell_coordinators(task, _("A volunteer declined a task: {0}").format(task.subject))

	return _outcome(task, moved=True)


def tick(task, index: int, done: bool = True, notes: str | None = None, evidence: str | None = None) -> dict:
	"""Mark one checklist item done, or undo it. Idempotent on the same answer.

	`index` is the row's `idx`, which is what a screen has and what survives a
	reorder better than a position in a list. The completion time is stamped here
	and cleared on an undo, because a time left behind on an unticked row says the
	item was done and then untouched.
	"""
	row = next((row for row in task.checklist or [] if row.idx == cint(index)), None)

	if not row:
		frappe.throw(
			_("This task has no checklist item {0}.").format(frappe.bold(index)),
			frappe.ValidationError,
			title=_("No Such Item"),
		)

	_assert_open(task)

	row.is_done = 1 if done else 0
	row.done_on = now_datetime() if done else None

	if notes is not None:
		row.notes = notes

	if evidence is not None:
		row.evidence = evidence

	_save(task)

	return _outcome(task, moved=False)


def checklist_outstanding(task) -> list[str]:
	"""Required checklist items still unticked, in the words they were written in.

	Returned rather than thrown, so a screen can grey out its own submit button
	and say what is left without provoking an error — and so `assert_checklist`
	has exactly one place the list is decided.
	"""
	return [row.item for row in (task.checklist or []) if row.is_required and not row.is_done]


def assert_checklist(task) -> None:
	"""Throw unless every required checklist item is done.

	The one gate the checklist has, and it is at submission rather than on save:
	a task is worked through over days, and a checklist that refused a save until
	it was complete would be a checklist nobody could fill in gradually.
	"""
	outstanding = checklist_outstanding(task)

	if not outstanding:
		return

	frappe.throw(
		_("This task cannot be handed in yet. Still to do: {0}.").format(
			", ".join(str(item) for item in outstanding)
		),
		frappe.MandatoryError,
		title=_("Checklist Not Finished"),
	)


# --- what has to happen first -----------------------------------------------


def blocking(task) -> list[dict]:
	"""The tasks this one depends on that are not finished. Empty when it is free.

	Completed is finished. **Cancelled counts as finished too**, and that is the
	deliberate reading: work that was called off is never going to complete, and
	treating it as an outstanding prerequisite would leave the task that depends
	on it blocked for ever with nothing anybody could do about it.
	"""
	names = [row.depends_on for row in (task.depends_on or []) if row.depends_on]

	if not names:
		return []

	return [
		row
		for row in frappe.get_all(
			TASK_DOCTYPE,
			filters={"name": ("in", names), "status": ("not in", states.TERMINAL)},
			fields=["name", "subject", "status"],
			ignore_permissions=True,
		)
	]


def assert_startable(task) -> None:
	"""Throw unless nothing unfinished stands in front of this task.

	**A manager may override it, and has to say so in writing.** Real work gets
	started out of order — the prerequisite is done in practice and the record has
	not caught up — and a dependency that could never be overruled would be a
	dependency people stopped recording. `blocked_override_reason` is that
	override, and it is a sentence rather than a checkbox precisely so somebody
	has to take responsibility for it.
	"""
	blockers = blocking(task)

	if not blockers:
		return

	if (task.blocked_override_reason or "").strip():
		return

	frappe.throw(
		_(
			"This task waits on work that is not finished: {0}. Finish it first, or say why"
			" this one is starting anyway."
		).format(", ".join(f"{row['subject']} ({row['status']})" for row in blockers)),
		frappe.ValidationError,
		title=_("Something Comes First"),
	)


def assert_no_cycle(task) -> None:
	"""Refuse a dependency that leads back to this task, however long the chain.

	Walked breadth-first over `VMMS Task Dependency`, following each prerequisite's
	own prerequisites, with a seen-set so a loop somewhere else in the graph
	terminates the walk rather than this one. Checked on the task's own `validate`,
	which is the only place that sees the rows about to be written.

	A cycle is not a rule somebody is breaking on purpose; it is what happens when
	two coordinators each record that their task comes second. Refusing it here is
	the only place it can be refused before it exists.
	"""
	names = {row.depends_on for row in (task.depends_on or []) if row.depends_on}

	if not names:
		return

	if task.name in names:
		frappe.throw(
			_("A task cannot wait on itself."),
			frappe.ValidationError,
			title=_("Circular Dependency"),
		)

	seen, frontier = set(names), list(names)

	while frontier:
		rows = frappe.get_all(
			"VMMS Task Dependency",
			filters={"parenttype": TASK_DOCTYPE, "parent": ("in", frontier)},
			fields=["parent", "depends_on"],
			ignore_permissions=True,
		)
		frontier = []

		for row in rows:
			if row["depends_on"] == task.name:
				frappe.throw(
					_(
						"{0} already waits on this task, directly or through something else, so"
						" this dependency would make a loop neither of them could ever leave."
					).format(frappe.bold(row["parent"])),
					frappe.ValidationError,
					title=_("Circular Dependency"),
				)

			if row["depends_on"] and row["depends_on"] not in seen:
				seen.add(row["depends_on"])
				frontier.append(row["depends_on"])


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


def sign_off(
	task,
	note: str | None = None,
	outcome: str | None = None,
	rating: int | None = None,
	lessons: str | None = None,
	hours: float | None = None,
) -> dict:
	"""Agree the work is done. Idempotent, and terminal.

	Everything past `note` is optional and nothing waits for any of it. A sign-off
	that could be blocked by an unfilled rating is a sign-off that does not
	happen, and a register of work that was finished months ago and never closed
	is worse than one whose ratings are thin.
	"""
	if not states.can_move(task.status, states.COMPLETED):
		return _outcome(task, moved=False)

	task.status = states.COMPLETED
	task.closed_on = now_datetime()
	task.open_question = 0
	task.percent_complete = 100

	if outcome:
		task.outcome = outcome

	if rating is not None:
		task.manager_rating = rating

	if lessons:
		task.lessons_learned = lessons

	if hours is not None:
		task.actual_hours = flt(hours)

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
	# Kept after the work is resubmitted, deliberately: the volunteer is being
	# asked to fix something, and a reason that vanished the moment they picked
	# the task back up would be a reason they could not re-read.
	task.return_reason = reason
	task.rework_count = cint(task.rework_count) + 1

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


# --- giving the work to somebody else ---------------------------------------


def reassign(task, volunteer: str, reason: str) -> dict:
	"""Hand the same work to somebody else, keeping both records.

	**The original is never overwritten**, exactly as a deployment replacement is
	not. It moves to `reassigned` and points at the task that took over, which
	points back. Editing the volunteer instead would erase the fact that anybody
	had ever been asked, and with it any way of telling a reassignment from a
	typo — which is also how a volunteer's own record of what they were asked to
	do quietly loses entries.

	The new task starts at `assigned` and carries the brief, the schedule, the
	place and the checklist across; what it does not carry is the conversation,
	the progress or the evidence, because none of that is the new person's and
	presenting it as theirs would be false.

	A reason is required. Both people are told, and separately: being taken off
	work you had accepted and being handed work at short notice are different
	pieces of news.
	"""
	if not (reason or "").strip():
		frappe.throw(
			_("Say why this work is going to somebody else. It is the one thing the record"
			  " cannot infer."),
			frappe.MandatoryError,
			title=_("No Reason Given"),
		)

	if not states.can_move(task.status, states.REASSIGNED):
		return _outcome(task, moved=False)

	replacement = assign(
		volunteer=volunteer,
		subject=task.subject,
		description=task.description,
		geo_node=task.geo_node,
		deployment=task.deployment,
		**{field: task.get(field) for field in ASSIGNABLE if task.get(field) is not None},
		checklist=[
			{"item": row.item, "is_required": row.is_required, "notes": row.notes}
			for row in (task.checklist or [])
		],
		brief_files=[
			{"label": row.label, "file": row.file, "notes": row.notes}
			for row in (task.brief_files or [])
		],
		depends_on=[
			{"depends_on": row.depends_on, "notes": row.notes} for row in (task.depends_on or [])
		],
	)

	replacement.db_set("reassigned_from_task", task.name, update_modified=False)
	replacement.db_set("reassignment_reason", reason, update_modified=False)
	replacement.reload()

	task.status = states.REASSIGNED
	task.closed_on = now_datetime()
	task.open_question = 0
	task.reassigned_to_task = replacement.name
	task.reassignment_reason = reason

	_add_entry(task, ENTRY_REASSIGNED, reason)
	_save(task)

	_tell_volunteer(task, _("A task is no longer yours: {0}").format(task.subject))

	return {**_outcome(task, moved=True), "replacement": replacement.name}


# --- chasing it --------------------------------------------------------------


def is_overdue(task, now=None) -> bool:
	"""Is this task open and past the moment it was due?

	Derived, never stored. A stored flag would be right until the clock moved and
	then wrong until something noticed, and the something that noticed would be a
	job somebody had to remember to schedule.
	"""
	if not (task.get("due_at") and states.is_open(task.get("status"))):
		return False

	return get_datetime(task.get("due_at")) < (now or now_datetime())


def escalate(task, reason: str | None = None) -> dict:
	"""Raise this task with whoever the coordinator named. Records it, once.

	Silent where nobody was named, which is the shipped state: escalating to a
	person a society never chose would mean guessing at a hierarchy this app does
	not have.
	"""
	if not task.escalate_to:
		return _outcome(task, moved=False)

	task.append(
		"escalations",
		{
			"escalated_on": now_datetime(),
			"escalated_to": task.escalate_to,
			"reason": reason or _("Overdue and not answered."),
		},
	)
	task.last_contacted_on = now_datetime()

	_add_entry(task, ENTRY_ESCALATED, reason)
	_save(task)

	direct.tell(
		[task.escalate_to],
		_("An overdue task was escalated to you: {0}").format(task.subject),
		TASK_DOCTYPE,
		task.name,
	)

	return _outcome(task, moved=False)


def chase_overdue(now=None) -> dict:
	"""Nudge the people holding overdue work, and escalate what a nudge has not moved.

	The scheduled sweep, and it is built to be dull: it only ever touches tasks
	that are open, past due, and carry a reminder interval a society set. A task
	with no interval — the shipped state — is never chased, because sending
	reminders nobody asked for is how a system trains people to ignore it.

	**`last_contacted_on` is what makes it idempotent**, and it is the only reason
	the sweep can run hourly without becoming a nuisance. A task contacted inside
	its own interval is skipped; one that has never been contacted is nudged; one
	still open a full interval *after* being nudged is escalated, once, to the
	person the coordinator named.

	Returns what it did rather than logging it, so the scheduler's own record says
	something and a test can assert on the answer instead of on a side effect.
	"""
	moment = now or now_datetime()

	candidates = frappe.get_all(
		TASK_DOCTYPE,
		filters=[
			[TASK_DOCTYPE, "status", "in", states.OPEN],
			[TASK_DOCTYPE, "due_at", "is", "set"],
			[TASK_DOCTYPE, "due_at", "<", moment],
			[TASK_DOCTYPE, "reminder_every_days", ">", 0],
		],
		pluck="name",
	)

	reminded, escalated = [], []

	for name in candidates:
		task = frappe.get_doc(TASK_DOCTYPE, name)
		interval = cint(task.reminder_every_days)

		if task.last_contacted_on and get_datetime(task.last_contacted_on) > add_days(
			moment, -interval
		):
			continue

		if task.last_contacted_on and task.escalate_to:
			escalate(task, _("Still open {0} day(s) after the last reminder.").format(interval))
			escalated.append(name)
			continue

		task.last_contacted_on = moment
		_add_entry(task, ENTRY_REMINDED, _("This task is overdue."))
		_save(task)
		_tell_volunteer(task, _("A task of yours is overdue: {0}").format(task.subject))
		reminded.append(name)

	return {"reminded": reminded, "escalated": escalated}


# --- where the work is -------------------------------------------------------
#
# A task has the same two places a deployment has, under its own prefixes, and
# reaches them through the same `geocoding` module. Nothing is copied: the code
# that builds a map link for a deployment builds one for a task.

WORK = "work"
MEETING = "meeting"
PLACES = (WORK, MEETING)


def where_dto(task) -> dict:
	"""Where the work is and how to get there — the task's own, or its deployment's.

	**A deployment-linked task inherits rather than duplicates.** Every task under
	one deployment happens in the same place, and copying the address onto forty
	tasks would mean forty rows to correct when the meeting point moved. So a task
	that says nothing about where it is answers with its deployment's answer, and
	one that does say something overrides it — which is the case a standalone task
	and a "meet at the ward office instead of the camp" task both need.

	The override is per place rather than wholesale: a task may take the
	deployment's work site and name its own meeting point.
	"""
	from vmmsx.deployment.services import geocoding

	mine = {
		WORK: geocoding.dto(task, WORK),
		MEETING: geocoding.dto(task, MEETING),
	}
	inherited = _deployment_where(task)

	return {
		"work": mine[WORK] if _says_something(mine[WORK]) else inherited.get("site", mine[WORK]),
		"meeting_point": mine[MEETING]
		if _says_something(mine[MEETING])
		else inherited.get("meeting_point", mine[MEETING]),
		"travel_instructions": task.travel_instructions or inherited.get("travel_notes"),
		"local_contact": {
			"name": task.local_contact_name or inherited.get("local_contact", {}).get("name"),
			"phone": task.local_contact_phone or inherited.get("local_contact", {}).get("phone"),
		},
		# So a screen can say "from the deployment" rather than presenting an
		# inherited address as something somebody typed on this task.
		"inherited_from": task.deployment if inherited else None,
	}


def _says_something(place: dict) -> bool:
	"""Has anybody actually filled this place in? A name, an address or a point."""
	return bool(place.get("name") or place.get("address") or place.get("has_point"))


def _deployment_where(task) -> dict:
	"""The deployment's own place block, or an empty dict for a standalone task."""
	if not task.deployment:
		return {}

	from vmmsx.deployment.services import deployment as deployment_service

	return deployment_service.where_dto(frappe.get_cached_doc("VMMS Deployment", task.deployment))


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
		# --- what kind of work, and what it belongs to ------------------------
		"priority": task.priority,
		"task_type": task.task_type,
		"project": task.project,
		"batch": task.batch,
		# --- when -------------------------------------------------------------
		"due_at": task.due_at,
		"planned_start": task.planned_start,
		"planned_end": task.planned_end,
		"response_deadline": task.response_deadline,
		"expected_hours": flt(task.expected_hours) or None,
		"actual_hours": flt(task.actual_hours) or None,
		"percent_complete": flt(task.percent_complete),
		# Derived on every read rather than stored: a stored flag is right until
		# the clock moves and then wrong until something notices.
		"is_overdue": is_overdue(task),
		# --- what has to be done ----------------------------------------------
		"checklist": [
			{
				"idx": row.idx,
				"item": row.item,
				"is_required": bool(row.is_required),
				"is_done": bool(row.is_done),
				"done_on": row.done_on,
				"notes": row.notes,
				"evidence": row.evidence,
			}
			for row in task.checklist or []
		],
		"checklist_outstanding": checklist_outstanding(task),
		# The manager's own files, kept apart from the volunteer's evidence on the
		# thread. `VMMS Task Brief File` says why.
		"brief_files": [
			{"label": row.label, "file": row.file, "notes": row.notes}
			for row in task.brief_files or []
		],
		# --- what comes first --------------------------------------------------
		"depends_on": [row.depends_on for row in task.depends_on or []],
		"blocking": blocking(task),
		"blocked_override_reason": task.blocked_override_reason,
		# --- where -------------------------------------------------------------
		"where": where_dto(task),
		# --- chasing -----------------------------------------------------------
		"reminder_every_days": task.reminder_every_days,
		"last_contacted_on": task.last_contacted_on,
		"escalate_to": task.escalate_to,
		"escalations": [
			{"escalated_on": row.escalated_on, "escalated_to": row.escalated_to, "reason": row.reason}
			for row in task.escalations or []
		],
		# --- how it ended ------------------------------------------------------
		"outcome": task.outcome,
		"final_evidence": task.final_evidence,
		"return_reason": task.return_reason,
		"rework_count": cint(task.rework_count),
		"manager_rating": task.manager_rating,
		"lessons_learned": task.lessons_learned,
		"decline_reason": task.decline_reason,
		"reassigned_to_task": task.reassigned_to_task,
		"reassigned_from_task": task.reassigned_from_task,
		"reassignment_reason": task.reassignment_reason,
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
		"due_at": task.get("due_at"),
		"assigned_on": task.assigned_on,
		"open_question": bool(task.open_question),
		"is_open": states.is_open(task.status),
		# The four a list actually sorts and colours by. Everything else on the
		# full DTO is for the task's own page.
		"priority": task.get("priority"),
		"task_type": task.get("task_type"),
		"percent_complete": flt(task.get("percent_complete")),
		"is_overdue": is_overdue(task),
	}


# --- the plumbing ---------------------------------------------------------


def _rows(rows, columns: tuple[str, ...]) -> list[dict]:
	"""One child table, rebuilt column by column from whatever a caller passed.

	Never passed through. A caller that hands over an extra key would otherwise
	write a field nobody reviewed — `is_done` and `done_on` on a checklist item,
	say, which are the volunteer's to set and not the person setting the work.
	"""
	return [
		{key: row.get(key) for key in columns}
		for row in (rows or [])
		if isinstance(row, dict)
	]


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
	"""Notify whoever holds this task, if they have a login to be notified at.

	`about` names them regardless, so a young volunteer's guardian is copied by
	email even where there is no login to raise a notification against — see
	`direct.tell`.
	"""
	login = direct.login_of(task.volunteer)

	return direct.tell(
		[login] if login else [], subject, TASK_DOCTYPE, task.name, about=task.volunteer
	)


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
