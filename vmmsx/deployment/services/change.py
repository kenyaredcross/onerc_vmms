# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Changing a deployment people have already been asked to go on.

A deployment is a plan until somebody is invited to it. After that it is an
arrangement other people have made their week around — childcare, a shift swap,
a bus — and moving the date, the place or the person in charge is a different
act from editing a draft. This module is what makes it a different act.

Three rules, and they only ever apply once there is somebody to owe them to:

1. **It is audited.** Every material change is written into the deployment's own
   feed, field by field, with what it was and what it became. `track_changes` on
   the doctype already keeps a `Version`, and a Version is a developer's record;
   the feed is what a coordinator and a volunteer read.
2. **It requires a reason, written for this change.** Not a reason left in the
   field from last month — `change_reason` has to have changed in the same save,
   which is the only version of "give a reason" that cannot be satisfied by
   doing nothing.
3. **The people affected are told.** Everybody whose assignment is still open:
   placed, asked, or accepted. Not the ones who declined or withdrew, who are
   not going and do not need to hear that the bus leaves an hour earlier.

**Nothing here fires on a deployment nobody is on.** A coordinator drafting one
in the morning and correcting it in the afternoon writes no reason, sends no
notification and leaves no feed entry, because there is nobody the change is
material *to*. The rule arrives with the first invitation, which is exactly when
it starts to matter.

**What counts as material is a list, not a judgement.** `MATERIAL_FIELDS` below
is where the work is: where it is, when it is, how to get there, who is in
charge, and what it is being run under. Everything else — the notes, the
headcount, an email template — is a coordinator tidying up.
"""

import frappe
from frappe import _

# Fieldname → how a sentence refers to it. Written as data because the feed
# entry, the notification and the refusal all have to name the same things, and
# three lists would eventually disagree.
MATERIAL_FIELDS: dict[str, str] = {
	"terms_of_reference": "the terms of reference",
	"geo_node": "where it is anchored",
	"coordinator": "the responsible coordinator",
	"planned_start": "when it starts",
	"planned_end": "when it ends",
	"briefing_on": "the briefing",
	"check_in_deadline": "the check-in deadline",
	"expected_return": "the expected return",
	"site_name": "the deployment point",
	"site_address": "the deployment point's address",
	"meeting_point": "the meeting point",
	"meeting_address": "the meeting point's address",
	"travel_notes": "the travel notes",
	"local_contact_name": "the local contact",
	"local_contact_phone": "the local contact's phone number",
}

REASON_FIELD = "change_reason"


def material_changes(deployment) -> list[dict]:
	"""What changed in this save that people already invited would care about.

	Empty on an insert, and empty when nothing on the list moved. Compared
	against `get_doc_before_save`, which is the row as it was read at the start of
	this save rather than as it is now — the only honest source for "what it was".

	**Outside a save it falls back to the stored row**, because `_doc_before_save`
	only exists while one is running. That is what lets a screen ask "what would
	change if I saved this" before saving it, which is the question a coordinator
	is actually being asked when the form demands a reason. Inside a save the
	fallback never fires, so it costs nothing on the path that matters.
	"""
	if deployment.is_new():
		return []

	before = deployment.get_doc_before_save() or frappe.get_doc(
		deployment.doctype, deployment.name
	)

	changes = []

	for field, label in MATERIAL_FIELDS.items():
		was, now = before.get(field), deployment.get(field)

		if _same(was, now):
			continue

		changes.append({"field": field, "label": label, "was": _readable(was), "now": _readable(now)})

	return changes


def _same(was, now) -> bool:
	"""Equal enough. Blank and None are the same absence, and dates compare as text.

	Frappe hands a Datetime back as a `datetime` on a saved document and as the
	string somebody typed on an unsaved one, so the two are compared as strings —
	which is also what the feed entry is going to print.
	"""
	return str(was or "") == str(now or "")


def _readable(value) -> str:
	"""What a sentence says a field was. Never `None`, never a repr."""
	if value in (None, ""):
		return _("nothing")

	return frappe.format_value(value, {"fieldtype": "Data"}) if not hasattr(value, "year") else str(value)


# --- the reason -------------------------------------------------------------


def on_validate(deployment) -> None:
	"""The whole rule, in the one place it can run before anything is written.

	Both halves belong in `validate` and not in `on_update`: the reason has to
	refuse the save, and the feed entry has to be part of it. An entry appended
	after the save has succeeded is an entry that survives a rollback, and one
	appended by a *second* save leaves the caller holding a document whose
	timestamp no longer matches the row.

	The notification is the one thing that cannot happen here — telling somebody
	about a change that is then rolled back is worse than not telling them — so
	that is `announce`, from `on_update`, and it writes nothing.
	"""
	changes = material_changes(deployment)

	if not (changes and affected(deployment.name)):
		return

	assert_reason(deployment, changes)
	record(deployment, changes)


def record(deployment, changes: list[dict] | None = None) -> None:
	"""Put the change into the deployment's own feed, as part of this save.

	Field by field, because "this deployment changed" is not something anybody
	can act on and "the meeting point moved from the branch office to the bus
	stand" is. `track_changes` keeps a `Version` as well; a Version is a
	developer's record and this is the one people read.
	"""
	from vmmsx.deployment.services import feed

	changes = changes if changes is not None else material_changes(deployment)

	if not changes:
		return

	feed.stage(deployment, "update", _sentence(deployment, changes))


def assert_reason(deployment, changes: list[dict] | None = None) -> None:
	"""Throw unless this save carries a reason written for this change.

	**A reason that did not change is not a reason.** The field holds whatever
	was written last time, so accepting it would make the rule satisfiable by
	doing nothing at all — which is the failure mode of every "mandatory
	justification" field that is checked for emptiness rather than for freshness.

	Silent where nobody has been invited yet. Called from `validate`, so the
	refusal arrives before the change is written rather than after it.
	"""
	if not (changes if changes is not None else material_changes(deployment)):
		return

	if not affected(deployment.name):
		return

	before = deployment.get_doc_before_save() or frappe.get_doc(
		deployment.doctype, deployment.name
	)
	reason = (deployment.get(REASON_FIELD) or "").strip()

	if reason and reason != (before.get(REASON_FIELD) or "").strip():
		return

	frappe.throw(
		_(
			"{0} people have already been asked to go on this deployment. Say why it is changing"
			" — they arranged their week around what it said before, and the reason goes to them"
			" with the change."
		).format(frappe.bold(len(affected(deployment.name)))),
		frappe.MandatoryError,
		title=_("Say Why It Changed"),
	)


# --- who is owed the news ---------------------------------------------------


def affected(deployment: str) -> list[dict]:
	"""Assignments still open on this deployment: placed, asked, or accepted.

	Not the settled ones. Somebody who declined last week is not going, and
	telling them the briefing moved is noise that trains people to stop reading.
	"""
	from vmmsx.deployment.services import assignment

	return frappe.get_all(
		assignment.ASSIGNMENT_DOCTYPE,
		filters={"deployment": deployment, "status": ("in", assignment.OPEN_STATUSES)},
		fields=["name", "volunteer"],
	)


# --- telling them -----------------------------------------------------------


def announce(deployment, changes: list[dict] | None = None) -> dict:
	"""Tell everybody still on the deployment. Writes nothing.

	Called from `on_update`, after the save has succeeded, because a notification
	about a change that was then rolled back is worse than no notification — and
	writing nothing is what makes it safe to run there. The feed entry was staged
	during `validate` and persisted by the save that has just finished.

	**The changes are re-derived from `get_doc_before_save`**, which is still the
	pre-save row at this point in the lifecycle; the document has not been reloaded
	between `validate` and here.

	Returns what it did, so a caller can say so and a test can assert on it rather
	than on a side effect.
	"""
	from vmmsx.deployment.services import assignment
	from vmmsx.notifications.services import direct

	changes = changes if changes is not None else material_changes(deployment)
	people = affected(deployment.name)

	if not (changes and people):
		return {"changes": len(changes or []), "told": []}

	sentence = _sentence(deployment, changes)
	told = []

	for row in people:
		# No early return on a missing login. Somebody with no account still has
		# a place on this deployment, and — if they are a minor — a parent who
		# must be told it moved. `direct.tell` copies the guardian off `about`
		# and quietly notifies nobody in-app.
		login = direct.login_of(row["volunteer"])

		told.extend(
			direct.tell(
				[login] if login else [],
				_("A deployment you are on has changed"),
				assignment.ASSIGNMENT_DOCTYPE,
				row["name"],
				about=row["volunteer"],
			)
		)

	return {"changes": len(changes), "told": told, "sentence": sentence}


def _sentence(deployment, changes: list[dict]) -> str:
	"""The change, in the words a coordinator and a volunteer both read.

	Field by field, because "this deployment changed" is not something anybody
	can act on and "the meeting point moved from the branch office to the bus
	stand" is.
	"""
	lines = [
		_("{0}: {1} → {2}").format(_(change["label"]), change["was"], change["now"])
		for change in changes
	]
	reason = (deployment.get(REASON_FIELD) or "").strip()

	return "\n".join([*lines, "", _("Reason: {0}").format(reason)]) if reason else "\n".join(lines)
