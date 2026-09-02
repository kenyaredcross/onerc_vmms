# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Asking forty people to do the same thing, and being honest about what happened.

A `VMMS Task Batch` is an **administrative grouping, not a shared task**. Forty
volunteers doing a household survey are doing forty pieces of work with forty
conversations, forty checklists and forty sign-offs; what they share is the brief
they were given. So the batch holds the brief and the list of people, and
generating it makes forty ordinary `VMMS Task` records that from that moment
have nothing to do with each other.

**Generating forty tasks will not produce forty tasks, and pretending otherwise
is the failure this module is shaped around.** Some of those volunteers already
hold a task from this batch, one was suspended after the list was drawn up, and
one will fail for a reason nobody predicted. Three properties follow:

1. **One bad row never blocks a good one.** Each volunteer is created inside its
   own savepoint, so a refusal rolls back that person and nothing else. Frappe's
   own `savepoint`/`rollback(save_point=...)` pair, the same mechanism
   `deployment/services/assignment.py::deploy` uses.
2. **Every row records what happened and why.** Created, Existing, Skipped or
   Failed, with a sentence. A batch that reported "37 of 40" and left the reader
   to work out which three would be a batch nobody could act on.
3. **A retry processes only what is unresolved and never duplicates.** A row that
   says Created is skipped on the next run; a row that says Failed is tried
   again. The `result` field is what makes that possible, and a blank one means
   "not tried yet".

**Editing a batch afterwards changes nothing that was already sent.** The brief
is *copied* onto each task at generation, and the batch's own fields are frozen
once it has generated. Anything else would mean a coordinator tidying a typo
silently rewriting work forty people had already read — and the brief a volunteer
agreed to has to be the brief they were shown.

**The counts are derived, never stored.** `counts()` reads the generated tasks
and answers from their current state, so a batch's report of how much of its work
is finished cannot drift from the tasks themselves.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from vmmsx.task.services import states, task as task_service

BATCH_DOCTYPE = "VMMS Task Batch"
TASK_DOCTYPE = "VMMS Task"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"

# What one row of a batch can come to. A closed set, in the order a reader cares
# about them: the ones that worked, the one that was already there, the two that
# need somebody's attention.
RESULT_CREATED = "Created"
RESULT_EXISTING = "Existing"
RESULT_SKIPPED = "Skipped"
RESULT_FAILED = "Failed"

RESULTS = (RESULT_CREATED, RESULT_EXISTING, RESULT_SKIPPED, RESULT_FAILED)

# The rows a run will attempt: never tried, or tried and not resolved. `Created`
# and `Existing` both mean this person has their task, and re-running must not
# make them a second one.
RESOLVED = (RESULT_CREATED, RESULT_EXISTING)

# What a batch copies onto every task it generates. The brief and the schedule
# are the whole point of the grouping; everything else about a task is its own
# from the moment it exists.
CARRIED = ("priority", "task_type", "project", "due_at")


# --- who it can go to --------------------------------------------------------


def candidates(batch_doc, **filters) -> dict:
	"""Volunteers this batch could go to, within the caller's own area.

	**Not a second search.** This is `matching.candidates`, which already answers
	geo, skills, languages, certifications, availability, clashes and workload,
	and already stands on `frappe.get_list` so the caller's scope is the floor
	rather than a filter. What this adds is the batch's own defaults: its Geo
	Node, its deployment's terms of reference where it has one, and its due date
	as the day the availability question is asked about.

	A batch with no deployment names no terms of reference, and then no
	certification question is asked — see `matching.candidates`.
	"""
	from vmmsx.deployment.services import matching

	terms_of_reference = None

	if batch_doc.deployment:
		terms_of_reference = frappe.db.get_value(
			"VMMS Deployment", batch_doc.deployment, "terms_of_reference"
		)

	return matching.candidates(
		terms_of_reference,
		filters.pop("geo_node", None) or batch_doc.geo_node,
		start_date=filters.pop("start_date", None) or batch_doc.due_at,
		end_date=filters.pop("end_date", None) or batch_doc.due_at,
		**filters,
	)


# --- what would happen -------------------------------------------------------


def preview(batch_doc) -> dict:
	"""What generating this batch would do, without doing any of it.

	Every row gets the same verdict `generate` would reach, from the same
	predicate, so the preview and the run cannot disagree. The one thing it
	cannot predict is a failure nobody foresaw, which is precisely why `Failed`
	exists as a result and not as a preview verdict.
	"""
	rows = []

	for row in batch_doc.volunteers or []:
		verdict, reason = _verdict(batch_doc, row)
		rows.append(
			{
				"volunteer": row.volunteer,
				"result": row.result,
				"task": row.task,
				"would": verdict,
				"reason": reason,
			}
		)

	return {
		"batch": batch_doc.name,
		"selected": len(rows),
		"rows": rows,
		"would_create": len([row for row in rows if row["would"] == RESULT_CREATED]),
		"would_skip": len([row for row in rows if row["would"] == RESULT_SKIPPED]),
		"already_have_one": len([row for row in rows if row["would"] == RESULT_EXISTING]),
	}


def _verdict(batch_doc, row) -> tuple[str, str | None]:
	"""What this one row would come to, and why. The single predicate.

	Order matters and is deliberate: a row already resolved is left alone before
	anything else is asked about it, because a retry must not re-examine — let
	alone re-refuse — somebody who already has their task.
	"""
	if row.result in RESOLVED:
		return row.result, None

	if not row.volunteer:
		return RESULT_SKIPPED, _("No volunteer named on this row.")

	if not frappe.db.exists(VOLUNTEER_DOCTYPE, row.volunteer):
		return RESULT_SKIPPED, _("This volunteer record no longer exists.")

	existing = _task_for(batch_doc.name, row.volunteer)

	if existing:
		return RESULT_EXISTING, _("This person already has a task from this batch.")

	return RESULT_CREATED, None


def _task_for(batch: str, volunteer: str) -> str | None:
	"""This batch's task for this volunteer, whatever state it is in, or None.

	Whatever state, deliberately: a task somebody declined or a coordinator
	cancelled is still a task this batch generated, and generating a second one
	would be the batch quietly asking again on its own initiative.
	"""
	return frappe.db.get_value(TASK_DOCTYPE, {"batch": batch, "volunteer": volunteer}, "name")


# --- doing it -----------------------------------------------------------------


def generate(batch_doc) -> dict:
	"""Create one task per unresolved volunteer. Safe to run again, always.

	Each person is written inside their own savepoint, so one refusal rolls back
	that person and leaves everybody before them created. That is the property
	that makes a forty-row batch usable at all: without it, the thirty-ninth
	volunteer having been suspended last week would undo the other thirty-nine.

	**Nothing is re-created.** A row already marked Created or Existing is passed
	over untouched, which is what makes a retry a retry rather than a second run.
	"""
	if not (batch_doc.volunteers or []):
		frappe.throw(
			_("This batch has nobody on it. Choose the volunteers before generating it."),
			frappe.MandatoryError,
			title=_("Nobody Selected"),
		)

	for row in batch_doc.volunteers:
		if row.result in RESOLVED:
			continue

		verdict, reason = _verdict(batch_doc, row)

		if verdict != RESULT_CREATED:
			row.result, row.reason = verdict, reason
			row.task = _task_for(batch_doc.name, row.volunteer) if verdict == RESULT_EXISTING else None
			continue

		_attempt(batch_doc, row)

	batch_doc.generated_on = now_datetime()
	batch_doc.generated_by = frappe.session.user
	# **Link validation is skipped on this save, deliberately.** A batch is a
	# record of who was selected and what happened to them, and the rows most
	# worth recording are the ones whose subject is no longer on the register —
	# a volunteer removed since the list was drawn up, a deployment purged. Frappe
	# would refuse to save the row that says so, which would leave the batch
	# unable to report the one thing it exists to report. The links were validated
	# when each row was added; a dangling one now is a fact, not a mistake being
	# introduced.
	batch_doc.flags.ignore_links = True
	batch_doc.save()

	return {**report(batch_doc), "counts": counts(batch_doc)}


def _attempt(batch_doc, row) -> None:
	"""One volunteer, inside their own savepoint. Never raises.

	The savepoint is the whole of the partial-success guarantee, and it has to be
	here rather than around the loop: a rollback to a point outside the loop would
	take the successful rows with it, which is the failure this shape exists to
	prevent.
	"""
	point = f"batch_{frappe.generate_hash(length=8)}"
	frappe.db.savepoint(point)

	try:
		task = task_service.assign(
			volunteer=row.volunteer,
			subject=batch_doc.subject,
			# **Copied, not referenced.** Editing the batch afterwards must not
			# rewrite work forty people have already read.
			description=batch_doc.brief,
			geo_node=batch_doc.geo_node,
			deployment=batch_doc.deployment,
			**{field: batch_doc.get(field) for field in CARRIED if batch_doc.get(field)},
		)
		task.db_set("batch", batch_doc.name, update_modified=False)
	except Exception as problem:
		frappe.db.rollback(save_point=point)
		row.result, row.task, row.reason = RESULT_FAILED, None, _clean(problem)
		return

	row.result, row.task, row.reason = RESULT_CREATED, task.name, None


def _clean(problem: Exception) -> str:
	"""A refusal in the words it was refused in, with the markup taken off.

	`frappe.throw` builds HTML, and a report row is read as text. Borrowed
	verbatim from `assignment.deploy`, which learned the same lesson.
	"""
	message = getattr(problem, "message", None) or str(problem)

	return frappe.utils.strip_html(message).strip() or _("This one could not be created.")


# --- reading it ---------------------------------------------------------------


def report(batch_doc) -> dict:
	"""Row by row, what happened. The answer a coordinator reads after generating.

	Never a summary alone: "37 of 40" with no list is a report nobody can act on,
	and the three that did not work are the only part anybody needs.
	"""
	rows = [
		{
			"volunteer": row.volunteer,
			"result": row.result,
			"task": row.task,
			"reason": row.reason,
		}
		for row in batch_doc.volunteers or []
	]

	return {
		"batch": batch_doc.name,
		"generated_on": batch_doc.generated_on,
		"generated_by": batch_doc.generated_by,
		"selected": len(rows),
		"rows": rows,
		"unresolved": [row for row in rows if row["result"] not in RESOLVED],
		**{result.lower(): len([row for row in rows if row["result"] == result]) for result in RESULTS},
	}


def counts(batch_doc) -> dict:
	"""How the generated work is going, read off the tasks themselves.

	**Derived on every read.** Stored counters drift the moment somebody signs a
	task off from its own page rather than through the batch, and a batch whose
	numbers disagreed with its tasks would be worse than one with no numbers.

	One grouped query for the states, plus one for overdue, rather than a query
	per task: a batch is forty rows and a register is a hundred batches.
	"""
	generated = [row.task for row in (batch_doc.volunteers or []) if row.task]

	tally = {state: 0 for state in states.ALL}
	overdue = 0

	if generated:
		rows = frappe.get_all(
			TASK_DOCTYPE,
			filters={"name": ("in", generated)},
			fields=["name", "status", "due_at"],
			ignore_permissions=True,
		)

		for row in rows:
			if row["status"] in tally:
				tally[row["status"]] += 1

			if task_service.is_overdue(frappe._dict(row)):
				overdue += 1

	return {
		**tally,
		"selected": len(batch_doc.volunteers or []),
		"created": len(generated),
		# "In progress" is accepted work that has not been handed in — the answer
		# to "how much of this is actually happening", which neither `assigned`
		# nor `submitted` gives on its own.
		"in_progress": tally[states.ACCEPTED],
		"not_responded": tally[states.ASSIGNED],
		"overdue": overdue,
		"failed": len(
			[row for row in (batch_doc.volunteers or []) if row.result == RESULT_FAILED]
		),
		"skipped": len(
			[row for row in (batch_doc.volunteers or []) if row.result == RESULT_SKIPPED]
		),
	}
