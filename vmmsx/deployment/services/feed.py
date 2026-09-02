# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What happened on a deployment, in the order it happened.

A deployment record answers "who is going and under what terms" from its own
fields. It cannot answer "what is going on", and that is the question somebody
opening a running deployment actually has. This module is that answer: one
chronological account, merged at read time from two sources that stay where they
are.

Two sources, one feed, no copying
---------------------------------

* **`VMMS Deployment Update`**, a child table on the deployment. Notes from the
  field, milestones, concerns — plus the entries this module writes itself when
  a deployment changes status or somebody joins or leaves it. Those automatic
  entries are what make the feed a timeline rather than only the notes people
  remembered to write.
* **`VMMS Task Update`**, on every task linked to this deployment. A volunteer
  submitting a task report is reporting on the deployment, and a coordinator
  reading the deployment should see it — but the report belongs to the task, and
  copying it here would make two records of one thing that immediately start
  drifting.

**Merged on read, never on write.** The alternative — writing a deployment
update every time a task update is posted — would double every report, and the
copy would go stale the moment somebody edited the original. This costs two
queries per read and owes nothing to a background job.

**One read, one instant.** Composed as a single call for the reason every detail
screen in this app is composed that way: a feed assembled from two sources read
at two different moments could show a status change without the roster change
that caused it, and the confusion would only surface later.

**Nothing here decides who may look.** `api/deployment.py` answers that with the
ordinary permission check on the deployment, which brings core's geo scoping
with it. Answering it twice is how two answers come to disagree.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

DEPLOYMENT_DOCTYPE = "VMMS Deployment"
TASK_DOCTYPE = "VMMS Task"
TASK_UPDATE_DOCTYPE = "VMMS Task Update"

# The kinds of entry somebody may write. `status` and `roster` are deliberately
# not among them: those are this module's own account of something that
# happened, and a person writing one by hand would be putting a fact into the
# record that nothing actually did.
WRITABLE = ("update", "milestone", "concern")

# The two this module writes itself.
STATUS = "status"
ROSTER = "roster"

# How many entries a feed hands back. A deployment that ran for a season with a
# task report a day is a real thing, and a screen that tried to render all of it
# at once would be a screen nobody could scroll.
PAGE = 200


def post(
	deployment_doc,
	note: str,
	entry_type: str = "update",
	proof: str | None = None,
) -> dict:
	"""Write one entry to a deployment's feed.

	**The author and the time come from the session**, never from the caller. A
	feed somebody could back-date, or attribute to another person, would be worse
	than no feed at all: it would look like a record while being a thing anybody
	could write anything into.

	Refuses an empty note. An entry with no words and no picture says nothing,
	and a feed full of them is harder to read than one without them.
	"""
	if entry_type not in WRITABLE:
		frappe.throw(
			_("{0} is not something anybody writes. Expected one of: {1}.").format(
				frappe.bold(entry_type), ", ".join(WRITABLE)
			),
			frappe.ValidationError,
			title=_("Unknown Entry"),
		)

	if not (note or "").strip() and not proof:
		frappe.throw(
			_("An update needs something in it — a note, a photograph, or both."),
			frappe.ValidationError,
			title=_("Nothing To Post"),
		)

	return _append(deployment_doc, entry_type, note, proof=proof)


def note_status(deployment_doc, status: str, reason: str | None = None) -> None:
	"""Record that the deployment moved, in the feed as well as on the field.

	Written by `deployment.set_status` rather than by a screen, so a deployment
	that was ended has an entry saying so whichever door ended it.
	"""
	_append(
		deployment_doc,
		STATUS,
		_("Marked {0}.").format(_(status)) + (f" {reason}" if reason else ""),
		system=True,
	)


def note_roster(deployment_doc, sentence: str) -> None:
	"""Record that somebody joined or left, in the feed as well as on the register.

	Takes a finished sentence rather than a volunteer and a verb, because the
	callers know things this module does not — whether somebody was placed or
	accepted, whether they withdrew or were withdrawn — and passing the pieces
	would mean re-deriving that here from the same facts.
	"""
	_append(deployment_doc, ROSTER, sentence, system=True)


def stage(deployment_doc, entry_type: str, note: str | None, proof: str | None = None) -> None:
	"""Append an entry **without saving**, for a caller already inside the save.

	The one shape `_append` cannot serve. Everything else here writes a feed
	entry from outside a save and has to persist it, so it appends and saves. A
	caller running in the deployment's own `validate` must not: saving from
	inside a save either recurses or, worse, succeeds and leaves the document in
	the caller's hands with a `modified` timestamp that no longer matches the
	row — which surfaces later as `TimestampMismatchError` on the *next* save,
	a long way from the code that caused it.

	So this appends the row and lets the save that is already running persist it.
	That also makes the entry atomic with the change it describes: a save that is
	refused leaves no feed entry claiming something happened.

	The author and the time still come from the session, exactly as `post` does.
	"""
	deployment_doc.append(
		"updates",
		{
			"entry_type": entry_type,
			"author": frappe.session.user,
			"posted_on": now_datetime(),
			"note": (note or "").strip() or None,
			"proof": proof,
		},
	)


def _append(
	deployment_doc,
	entry_type: str,
	note: str | None,
	proof: str | None = None,
	system: bool = False,
) -> dict:
	"""Add one row and save. The single writer, so every entry is stamped the same.

	**`system` decides whether the save is elevated, and the distinction is the
	whole permission story of this module.**

	`post()` — a person writing an update — passes it false, and the save runs as
	that person against `VMMS Deployment`. It has to: a feed anybody could write
	to would not be a record of anything, and
	`api/deployment.py::post_deployment_update` has already checked write on the
	deployment before this is reached.

	`note_status` and `note_roster` pass it true, because they are not somebody
	writing — they are this app noting what it just did, and the act that caused
	them was authorised at its own door. The case that forces it is a volunteer
	accepting their own assignment: they hold no Geo Assignment and no role on
	the deployment register, `assignment.respond` therefore saves the assignment
	elevated, and an ordinary save here would refuse the one person entitled to
	answer — turning a feed entry into the reason their answer failed. The author
	is still stamped from the session, so the entry says who caused it.
	"""
	row = deployment_doc.append(
		"updates",
		{
			"entry_type": entry_type,
			"author": frappe.session.user,
			"posted_on": now_datetime(),
			"note": (note or "").strip() or None,
			"proof": proof,
		},
	)

	deployment_doc.save(ignore_permissions=system)

	return _entry(
		source="deployment",
		entry_type=row.entry_type,
		author=row.author,
		posted_on=row.posted_on,
		note=row.note,
		proof=row.proof,
	)


# --- reading it -----------------------------------------------------------


def of(deployment: str, limit: int | None = None) -> dict:
	"""The whole account of one deployment, newest first.

	Both sources in one call, sorted together. The two are distinguishable in the
	result — `source` says which — because a coordinator reading "arrived at the
	camp" wants to know whether that is the deployment's own log or a volunteer's
	report against a task, and the answer changes who they would ask about it.
	"""
	page = min(int(limit or PAGE), PAGE)

	entries = _deployment_entries(deployment) + _task_entries(deployment)

	# Sorted here rather than in either query, because the two come from
	# different tables and there is nothing to order by until both are in hand.
	# `posted_on` is stamped by the writer in both cases, so the two are
	# comparable without any adjustment.
	entries.sort(key=lambda row: (row["posted_on"] is not None, row["posted_on"]), reverse=True)

	return {
		"deployment": deployment,
		"count": len(entries),
		"truncated": len(entries) > page,
		"entries": entries[:page],
	}


def _deployment_entries(deployment: str) -> list[dict]:
	"""The deployment's own feed rows.

	`get_all` on the child table with `parenttype` and `parentfield` both given:
	a child table is one physical table per doctype, and filtering only by
	`parent` would match a row from any other doctype sharing a docname.
	"""
	rows = frappe.get_all(
		"VMMS Deployment Update",
		filters={
			"parenttype": DEPLOYMENT_DOCTYPE,
			"parentfield": "updates",
			"parent": deployment,
		},
		fields=["entry_type", "author", "posted_on", "note", "proof"],
		order_by="posted_on desc",
	)

	return [
		_entry(
			source="deployment",
			entry_type=row["entry_type"],
			author=row["author"],
			posted_on=row["posted_on"],
			note=row["note"],
			proof=row["proof"],
		)
		for row in rows
	]


def _task_entries(deployment: str) -> list[dict]:
	"""Every task update written against a task on this deployment.

	Two queries: the tasks, then their updates. Not a join, because the task
	rows carry the subject and the volunteer that each entry is labelled with,
	and reading them separately keeps this to two bounded reads rather than one
	wide one.

	Returns nothing rather than raising when the deployment has no tasks, which
	is the ordinary case for a deployment that has only just started.
	"""
	tasks = {
		row["name"]: row
		for row in frappe.get_all(
			TASK_DOCTYPE,
			filters={"deployment": deployment},
			fields=["name", "subject", "volunteer"],
		)
	}

	if not tasks:
		return []

	rows = frappe.get_all(
		TASK_UPDATE_DOCTYPE,
		filters={
			"parenttype": TASK_DOCTYPE,
			"parentfield": "updates",
			"parent": ("in", list(tasks)),
		},
		fields=["parent", "entry_type", "author", "posted_on", "note", "proof"],
		order_by="posted_on desc",
	)

	return [
		_entry(
			source="task",
			entry_type=row["entry_type"],
			author=row["author"],
			posted_on=row["posted_on"],
			note=row["note"],
			proof=row["proof"],
			task=row["parent"],
			subject=tasks[row["parent"]]["subject"],
			volunteer=tasks[row["parent"]]["volunteer"],
		)
		for row in rows
	]


def _entry(source: str, entry_type: str, author: str, posted_on, note, proof, **extra) -> dict:
	"""One feed entry, in the one shape both sources are rendered in.

	Built field by field, and the author's display name resolved here so a screen
	shows "Amina Yusuf" rather than a login. `full_name` falls back to the login
	itself rather than to nothing: an entry whose author's User record has since
	been renamed should still say who wrote it.
	"""
	return {
		"source": source,
		"entry_type": entry_type,
		"author": author,
		"author_name": _author_name(author),
		"posted_on": posted_on,
		"note": note,
		"proof": proof,
		"task": extra.get("task"),
		"subject": extra.get("subject"),
		"volunteer": extra.get("volunteer"),
	}


def _author_name(author: str | None) -> str | None:
	"""What to call the person who wrote an entry.

	`get_cached_value`, because a feed of two hundred entries is written by a
	handful of people and this is asked once per row.
	"""
	if not author:
		return None

	return frappe.get_cached_value("User", author, "full_name") or author
