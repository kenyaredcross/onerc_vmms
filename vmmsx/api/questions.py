# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The form builder's own surface: a society editing what it asks applicants.

`VMMS Application Question` has always been editable on the desk. What it had no
way to be was editable by somebody who does not open the desk, and the desk form
shows a `Link to DocType` field where a person means "the volunteer form" — so
the one screen in this product that exists to avoid a deploy still felt like
configuration work. These endpoints are the console's half of it.

**This module names no registration, and neither does the screen it serves.**
`targets()` derives the answerable doctypes from the schema — whichever ones
carry the answer table — exactly as `questions.asks()` does, so the volunteer
application and the membership are two rows in an answer rather than two
branches. A third registration that opts in appears here on its own.

**"Administrator only" is a doctype permission, not a role written down.**
`VMMS Application Question` ships with one permission row, `System Manager`, and
`staff/services/permissions.py` deliberately never grants it to a scope role: a
question changes what every future applicant is asked, which is a different kind
of act from running a register. So the gate below is `frappe.has_permission` on
the doctype, which today means exactly the administrator and tomorrow means
whoever a society deliberately adds through the Role Permissions Manager. No
role name appears here or in `portal/src/`, which is the same rule
`staff/services/console.py` follows for every other tab.

**Every write goes through the document's own `save()`.** The controller's
`validate()` is what refuses a Select with no choices, and routing around it
with `db_set` would let this screen create a question the wizard cannot draw.
Permissions are checked here *and* by the framework on save, which is defence in
depth rather than duplication: the check here produces a sentence a person can
read, and the one underneath is the one that actually holds.

**Deactivating, never deleting.** There is no delete endpoint, and that is the
doctype's own rule showing through: an answer already given was part of an
application somebody decided, and removing the question it hung off would take
evidence out from under a decision. `set_active` is the whole of "stop asking
this".
"""

import frappe

from vmmsx.registration.services import questions

QUESTION_DOCTYPE = questions.QUESTION_DOCTYPE
ANSWER_FIELD = questions.ANSWER_FIELD

# The types the wizard and the desk form can both actually draw. Read from the
# doctype's own Select rather than listed again here, so a type added to the
# field appears in the builder without this file being edited — the same rule
# `api/volunteer.py::application_options` follows for `residency_type`.
FIELD_TYPE_FIELD = "field_type"


@frappe.whitelist()
def targets() -> dict:
	"""The registrations a question can be attached to, and the types it may take.

	**Derived, never named.** A doctype is answerable because it carries the
	answer table, which is the same question `questions.asks()` asks before it
	touches anything. So this app's two registrations are two rows here rather
	than two literals, and a module that opts in later needs no edit.

	`field_types` rides along for the reason `application_options` gives: the
	screen draws both in one pass, and a second round trip for a list that never
	changes is a spinner for nothing.
	"""
	_assert_may_read()

	answerable = frappe.get_all(
		"DocField",
		filters={"fieldname": ANSWER_FIELD, "parenttype": "DocType"},
		pluck="parent",
	)

	meta = frappe.get_meta(QUESTION_DOCTYPE)
	field_type = meta.get_field(FIELD_TYPE_FIELD)

	return {
		"targets": [
			{
				"doctype": doctype,
				# The doctype's own name, translated. `DocType` carries no label
				# field in this framework version, so there is nothing else to
				# read; the screen drops the `VMMS ` prefix for display exactly
				# as `ReviewQueue.tsx` already does, which keeps the stripping in
				# one idiom rather than inventing a label here.
				"label": frappe._(doctype),
				"count": frappe.db.count(QUESTION_DOCTYPE, {"asked_on": doctype, "is_active": 1}),
			}
			for doctype in sorted(answerable)
			if frappe.db.exists("DocType", doctype)
		],
		"field_types": [
			option.strip()
			for option in ((field_type.options if field_type else "") or "").split("\n")
			if option.strip()
		],
		# What this caller may do with any of it, answered by the same check the
		# writes make. The screen draws its controls from this and decides
		# nothing itself, the same contract as `can_act` and `can_edit`.
		"can_edit": bool(frappe.has_permission(QUESTION_DOCTYPE, ptype="write")),
	}


@frappe.whitelist()
def catalogue(asked_on: str) -> dict:
	"""Every question on one registration, **including the retired ones**.

	Deliberately not `questions.asked_on()`, which is the applicant's view and
	active-only. An administrator needs to see what they switched off, or
	deactivating a question would look like deleting it and they would make a
	second one next year.

	Rows are explicit and built field by field, and they carry `answer_count` —
	how many applications already answered this — because that is what makes the
	"deactivate, never delete" rule legible at the moment somebody is looking for
	a delete button.
	"""
	_assert_may_read()

	rows = frappe.get_all(
		QUESTION_DOCTYPE,
		filters={"asked_on": asked_on},
		fields=[
			"name",
			"asked_on",
			"question_label",
			"field_type",
			"options",
			"is_required",
			"is_active",
			"help_text",
			"sequence",
		],
		order_by="sequence asc, creation asc",
	)

	return {
		"asked_on": asked_on,
		"questions": [_row(row) for row in rows],
		"can_edit": bool(frappe.has_permission(QUESTION_DOCTYPE, ptype="write")),
	}


@frappe.whitelist()
def save_question(
	asked_on: str,
	question_label: str,
	field_type: str,
	name: str | None = None,
	options: str | None = None,
	is_required: bool | int | str = False,
	help_text: str | None = None,
	sequence: int | None = None,
) -> dict:
	"""Create a question, or edit one. Returns the row as the screen will draw it.

	`name` is what makes this one endpoint rather than two: the screen's form is
	the same shape either way, and an edit that had to be a different call would
	be a second place for the field list to drift.

	**`asked_on` is not editable on an existing question.** Moving a question
	from one registration to another would orphan every answer already given
	under it — the answers live on the *application*, and they would then be
	answers to a question that is no longer asked there. Creating a new question
	and retiring the old one is the honest way to do that, and it leaves the
	trail intact.

	The save is the document's own, so the controller's `validate()` runs and a
	Select with no choices is refused here exactly as it is on the desk.
	"""
	_assert_may_write()

	if name:
		question = frappe.get_doc(QUESTION_DOCTYPE, name)

		if question.asked_on != asked_on:
			frappe.throw(
				frappe._(
					"A question cannot be moved to a different registration. Retire this one and add it where you want it."
				),
				frappe.ValidationError,
				title=frappe._("Cannot Move"),
			)
	else:
		question = frappe.new_doc(QUESTION_DOCTYPE)
		question.asked_on = asked_on
		question.is_active = 1

	question.question_label = question_label
	question.field_type = field_type
	question.options = options or ""
	question.is_required = 1 if _flag(is_required) else 0
	question.help_text = help_text or ""

	if sequence is not None:
		question.sequence = int(sequence)
	elif not name:
		# A new question goes to the end rather than to position zero, where it
		# would silently reorder a form somebody already designed.
		question.sequence = _next_sequence(asked_on)

	question.save()

	return _row(question.as_dict())


@frappe.whitelist()
def set_question_active(name: str, is_active: bool | int | str) -> dict:
	"""Start or stop asking a question. The only way to take one off a form.

	There is no delete endpoint and this is why: every answer already given stays
	exactly where it is, attached to the application it was part of. A question
	switched off is not asked of anybody new and rewrites nothing behind it.
	"""
	_assert_may_write()

	question = frappe.get_doc(QUESTION_DOCTYPE, name)
	question.is_active = 1 if _flag(is_active) else 0
	question.save()

	return _row(question.as_dict())


@frappe.whitelist()
def reorder_questions(asked_on: str, order: list | str) -> dict:
	"""Set the order the questions are drawn in, from a list of their names.

	The whole list is sent rather than one move, so the result cannot depend on
	what the screen thought the previous order was. A name that is not a question
	on this registration is ignored rather than throwing: the screen and the
	server can disagree about what exists if somebody else has been editing, and
	the correct answer to that is to order what is there.
	"""
	_assert_may_write()

	names = frappe.parse_json(order) if isinstance(order, str) else (order or [])

	mine = set(
		frappe.get_all(QUESTION_DOCTYPE, filters={"asked_on": asked_on}, pluck="name")
	)

	for position, name in enumerate(names):
		if name not in mine:
			continue

		question = frappe.get_doc(QUESTION_DOCTYPE, name)
		question.sequence = position
		question.save()

	return catalogue(asked_on)


# --- the shared pieces ----------------------------------------------------


def _row(row: dict) -> dict:
	"""One question as the builder draws it. Built field by field, never the doc.

	`choices` is split here rather than in the browser so the screen and
	`questions._choices` agree about what a choice list is — one per line,
	trimmed, blanks dropped.
	"""
	return {
		"name": row.get("name"),
		"asked_on": row.get("asked_on"),
		"label": row.get("question_label") or "",
		"field_type": row.get("field_type"),
		"options": row.get("options") or "",
		"choices": [
			line.strip() for line in (row.get("options") or "").splitlines() if line.strip()
		],
		"is_required": bool(row.get("is_required")),
		"is_active": bool(row.get("is_active")),
		"help_text": row.get("help_text") or "",
		"sequence": row.get("sequence") or 0,
		# How many applications already carry an answer to this. The number that
		# makes "deactivate, never delete" make sense to somebody looking for a
		# delete button.
		"answer_count": frappe.db.count(
			questions.ANSWER_DOCTYPE, {"question": row.get("name")}
		)
		if row.get("name")
		else 0,
	}


def _next_sequence(asked_on: str) -> int:
	last = frappe.get_all(
		QUESTION_DOCTYPE,
		filters={"asked_on": asked_on},
		fields=["sequence"],
		order_by="sequence desc",
		limit=1,
	)

	return (last[0].sequence or 0) + 1 if last else 0


def _assert_may_read() -> None:
	frappe.has_permission(QUESTION_DOCTYPE, ptype="read", throw=True)


def _assert_may_write() -> None:
	frappe.has_permission(QUESTION_DOCTYPE, ptype="write", throw=True)


def _flag(value: bool | int | str) -> bool:
	"""A checkbox as it arrives over HTTP, where `"false"` is a truthy string.

	The same coercion `api/tasks.py::_flag` makes, for the same reason.
	"""
	if isinstance(value, str):
		return value.strip().lower() not in ("", "0", "false", "no")

	return bool(value)
