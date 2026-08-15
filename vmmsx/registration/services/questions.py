# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The society's own questions, asked and answered.

A society asks for things this product never anticipated. A letter from the
area chief, a school stamp, a next of kin, the name of the branch that referred
somebody. `VMMS Application Question` is how it adds one; this module is the
whole of what the rest of the app knows about them.

**Nothing here names a registration.** `asked_on` is the governed doctype, the
same shape `VMMS Approval Workflow.workflow_for` uses, so the volunteer
application and the membership are two callers of one service rather than two
code paths. A third registration is a caller too.

**Answers are validated against the question, every time, server-side.** The
wizard draws a date picker or a dropdown because the DTO told it to, and then
the server re-asks the same questions of whatever actually arrived. A choice
outside the list is refused here, not in the browser, for the same reason
`MultiCombo` filters but never sets: a value the site does not have is a
rejection built in the wrong place.

**Required is checked at submission, not at insert.** A draft with a blank
answer is a person part-way through a form, and refusing to save it would lose
them the rest of what they typed. The submission is where an application stops
being theirs and starts being the society's, so that is where it has to be
complete. Same seam `assert_ready` already occupies for identification.

**A question added today is never applied backwards.** `assert_answered` reads
the answers on the document, not the current question list, when deciding
whether an application that has already been submitted is complete. A society
adding a question in March must not invalidate every application submitted in
February, which is what asking the live list would do.
"""

import frappe
from frappe import _
from frappe.utils import cint, cstr, getdate

QUESTION_DOCTYPE = "VMMS Application Question"
ANSWER_DOCTYPE = "VMMS Application Answer"

# The field every registration carries its answers in. One name, so a doctype
# opts in by adding the table under it and this module needs no register of who
# has one.
ANSWER_FIELD = "custom_answers"

ATTACH = "Attach"
CHECK = "Check"
SELECT = "Select"
DATE = "Date"
INT = "Int"


def asks(doctype: str) -> bool:
	"""Does this doctype carry an answer table at all?

	Asked before anything else touches `doc.custom_answers`, so a registration
	that has not opted in is silently unaffected rather than throwing on a field
	it does not have.
	"""
	return bool(frappe.get_meta(doctype).get_field(ANSWER_FIELD))


def asked_on(doctype: str) -> list[dict]:
	"""The active questions for `doctype`, in the order a form should draw them.

	An explicit DTO per question, built field by field. The wizard renders from
	this and nothing else, so a question type it does not recognise is a question
	it can decline to draw rather than one it renders wrongly.
	"""
	if not frappe.db.exists("DocType", QUESTION_DOCTYPE):
		# Mid-migrate on a site that has not synced this module yet. No questions
		# is the honest answer, and it keeps the registration endpoints working.
		return []

	rows = frappe.get_all(
		QUESTION_DOCTYPE,
		filters={"asked_on": doctype, "is_active": 1},
		fields=["name", "question_label", "field_type", "options", "is_required", "help_text", "sequence"],
		order_by="sequence asc, creation asc",
	)

	return [
		{
			"name": row.name,
			"label": row.question_label,
			"field_type": row.field_type,
			"choices": _choices(row),
			"is_required": bool(row.is_required),
			"help_text": row.help_text or "",
		}
		for row in rows
	]


def apply(doc, answers: dict | None) -> list[str]:
	"""Write the applicant's answers onto the document. Returns the questions set.

	Replaces the table wholesale rather than merging, because this is called with
	the complete set of answers a form collected and a merge would leave an answer
	to a question the applicant has since changed their mind about.

	Unknown keys are ignored rather than refused: a question deactivated between
	the wizard loading and the applicant finishing is not the applicant's
	mistake, and there is nothing useful to tell them about it.
	"""
	if not asks(doc.doctype):
		return []

	# A JSON body arrives parsed; a form-encoded one arrives as a string. Both are
	# ordinary ways to call a whitelisted method, so neither is an error here.
	answers = frappe.parse_json(answers) if isinstance(answers, str) else (answers or {})
	questions = {row["name"]: row for row in asked_on(doc.doctype)}

	doc.set(ANSWER_FIELD, [])
	written = []

	for name, question in questions.items():
		if name not in answers:
			continue

		value = answers[name]

		if _is_blank(value):
			continue

		doc.append(
			ANSWER_FIELD,
			{
				"question": name,
				# Snapshots, both of them. See the doctype's docstring.
				"question_label": question["label"],
				"field_type": question["field_type"],
				**_stored(question, value),
			},
		)
		written.append(name)

	return written


def anchor_files(doc) -> list[str]:
	"""Tie uploaded answer files to the document, so the approver can open them.

	**This is what makes an uploaded chief's letter readable by anybody but the
	applicant.** A private `File` with no `attached_to_doctype` belongs to
	whoever uploaded it and to System Manager, and to nobody else — so an
	approver opening the application would see a filename and get a permission
	error clicking it. Attached to the application, the file inherits the
	document's own permissions, which are already the right answer: exactly the
	people who may read the application may read what was uploaded to it.

	Runs after the insert, because the document it points at has to exist. The
	desk path never needs it: an `Attach` field inside a grid attaches to its own
	parent as it uploads, and this refuses to move a file that is already
	anchored somewhere.
	"""
	if not asks(doc.doctype):
		return []

	anchored = []

	for row in doc.get(ANSWER_FIELD) or []:
		if row.field_type != ATTACH or not row.answer_file:
			continue

		name = frappe.db.get_value(
			"File", {"file_url": row.answer_file, "attached_to_name": ("is", "not set")}, "name"
		)

		if not name:
			continue

		# Elevated because the person this runs for is the applicant, who holds no
		# permission on `File` beyond their own upload and none at all on the
		# register they have just applied to join. The write is bounded to a file
		# they own and already uploaded, and it only ever *narrows* who can reach
		# it: an unattached private file is theirs alone, and this hands it to the
		# document's own permission rules.
		frappe.db.set_value(
			"File",
			name,
			{"attached_to_doctype": doc.doctype, "attached_to_name": doc.name},
			update_modified=False,
		)
		anchored.append(row.answer_file)

	return anchored


def assert_answered(doc) -> None:
	"""Refuse a submission that leaves a required question blank.

	Reads the answers on the document against the questions *currently* asked,
	which is right at submission and wrong afterwards: this runs on the way in,
	while the applicant is still the person who can fix it.
	"""
	if not asks(doc.doctype):
		return

	answered = {row.question for row in doc.get(ANSWER_FIELD) or [] if _row_has_value(row)}

	missing = [
		question["label"]
		for question in asked_on(doc.doctype)
		if question["is_required"] and question["name"] not in answered
	]

	if not missing:
		return

	frappe.throw(
		_("This society asks for {0}, and the application cannot be submitted without it.").format(
			frappe.bold(", ".join(missing))
		),
		frappe.MandatoryError,
		title=_("Question Not Answered"),
	)


def answers_of(doc) -> list[dict]:
	"""What this applicant said, as DTOs an approver's screen can render.

	Reads the snapshots on the rows rather than the questions behind them, so an
	application decided last year still displays the question it was actually
	asked. `is_file` saves every reader from re-deriving the one distinction that
	changes how an answer is drawn.
	"""
	if not asks(doc.doctype):
		return []

	return [
		{
			"question": row.question,
			"label": row.question_label,
			"field_type": row.field_type,
			"value": row.answer_value or "",
			"file_url": row.answer_file or "",
			"is_file": row.field_type == ATTACH,
		}
		for row in doc.get(ANSWER_FIELD) or []
	]


# --- storing one answer ---------------------------------------------------


def _stored(question: dict, value) -> dict:
	"""One answer, coerced and checked against the question that asked for it.

	A dict rather than a value, because an attachment goes in a different column
	from everything else and the caller should not have to know which.
	"""
	field_type = question["field_type"]

	if field_type == ATTACH:
		return {"answer_file": _file(question, value), "answer_value": ""}

	return {"answer_value": _text(question, value)}


def _text(question: dict, value) -> str:
	"""Everything that is not a file, as the text the row stores."""
	field_type = question["field_type"]

	if field_type == CHECK:
		# Anything a form can put in a checkbox: True, "true", 1, "on".
		return "1" if cstr(value).strip().lower() in ("1", "true", "yes", "on") else "0"

	if field_type == INT:
		return cstr(cint(value))

	if field_type == DATE:
		try:
			return cstr(getdate(value))
		except Exception:
			frappe.throw(
				_("{0} needs to be a date.").format(frappe.bold(question["label"])),
				frappe.ValidationError,
				title=_("Not a Date"),
			)

	if field_type == SELECT:
		return _choice(question, value)

	return cstr(value).strip()


def _choice(question: dict, value) -> str:
	"""A Select answer, refused unless the question offers it.

	The whole vocabulary is the question's `choices`, so this is the one place an
	answer to a list question can come from and a browser cannot widen it.
	"""
	answer = cstr(value).strip()

	if answer in question["choices"]:
		return answer

	frappe.throw(
		_("{0} is not one of the answers offered for {1}.").format(
			frappe.bold(answer), frappe.bold(question["label"])
		),
		frappe.ValidationError,
		title=_("Answer Not Offered"),
	)


def _file(question: dict, value) -> str:
	"""A site-relative file URL, and nothing else.

	The applicant uploads through the framework's own file handler and sends back
	the URL it returned. Refusing anything that does not look like one stops this
	field becoming a way to point the approver's browser at somebody else's
	server, which is the same rule `links.py` applies to a content block's href.
	"""
	url = cstr(value).strip()

	if not url:
		return ""

	if url.startswith("/files/") or url.startswith("/private/files/"):
		return url

	frappe.throw(
		_("The file answering {0} was not uploaded to this site.").format(frappe.bold(question["label"])),
		frappe.ValidationError,
		title=_("File Not Recognised"),
	)


# --- small shared questions -----------------------------------------------


def _choices(row) -> list[str]:
	if row.field_type != SELECT:
		return []

	return [line.strip() for line in (row.options or "").splitlines() if line.strip()]


def _is_blank(value) -> bool:
	"""An answer nobody gave. False is a real answer to a tick, so it is not blank."""
	if value is None:
		return True

	if isinstance(value, bool):
		return False

	return not cstr(value).strip()


def _row_has_value(row) -> bool:
	"""Did this row actually record something?

	A `Check` answered "no" counts: the applicant answered it. An empty text
	answer or a missing file does not.
	"""
	if row.field_type == ATTACH:
		return bool(row.answer_file)

	if row.field_type == CHECK:
		return cstr(row.answer_value or "") != ""

	return bool(cstr(row.answer_value or "").strip())
