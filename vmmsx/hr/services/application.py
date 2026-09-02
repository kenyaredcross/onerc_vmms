# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Applying for a volunteering opening, on HRMS's own `Job Applicant`.

`openings.py` is the board — browse here, apply there, and HRMS owns everything
after somebody decides they want it. That remains true for **employment**
openings: this file never touches one, the public web form is untouched, and a
society running recruitment in HRMS finds nothing about it changed.

A **volunteering** opening is a different act by a different person. The
applicant is already somebody the society knows: an approved, active volunteer
with a Red Profile, a branch and a login. Sending them to a public form to retype
their own name — and to an applicant record with no thread back to the volunteer
register — would throw away everything the society already holds about them. So a
volunteering opening is applied for through this app, and the record it produces
is still HRMS's `Job Applicant`, because that is where a recruiter's pipeline,
timeline and comments already live.

**Four rules, and each is here because the alternative is worse.**

1. **Only an approved active volunteer may apply for a volunteering opening.**
   Not a rule about worthiness — it is what makes the prefill and the eligibility
   question answerable at all. Somebody who is not yet a volunteer applies to
   *become* one, which is registration, and this app already has that door.
2. **One live application per person per opening.** A second would put two
   records of the same intention in front of the same recruiter, each with its
   own status, and approving one would leave the other saying something else. A
   withdrawn or rejected one does not block a new attempt: applying again after a
   no is a real thing people do, and it produces a second record rather than
   overwriting what happened the first time.
3. **The questions are snapshotted onto the answers.** A society edits its
   screening questions, and an application decided next March against wording
   that changed in January would otherwise read as an answer to a question nobody
   asked.
4. **An accepted application becomes work in one deliberate act, once.**
   `convert()` is idempotent and refuses to run twice, because a second run would
   put the same person on the same deployment twice.

**Private uploads go through `registration/services/evidence.py`**, the same
module the volunteer application uses, so a document somebody attached to an
application is private and permission-checked on exactly one code path rather
than two.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime

from vmmsx.registration.services import evidence
from vmmsx.setup import job_applicant_fields as applicant_fields
from vmmsx.setup import job_opening_fields as opening_fields

OPENING_DOCTYPE = "Job Opening"
APPLICANT_DOCTYPE = "Job Applicant"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"

# HRMS's statuses that mean the society has not finished with this application.
# A withdrawal is not among them because it is not a status: see
# `setup/job_applicant_fields.py`.
LIVE_STATUSES = (
	applicant_fields.STATUS_OPEN,
	"Replied",
	applicant_fields.STATUS_SHORTLISTED,
	applicant_fields.STATUS_HOLD,
	applicant_fields.STATUS_ACCEPTED,
)

# Which answer types are checked, and how. Keyed by the value on
# `Job Application Screening Questions.question_type`, so adding a type is a row
# here and never a branch at a call site.
#
# `Rating` is deliberately absent: nothing in vmmsx grades against it, and
# validating a number nobody reads would be theatre. `Upload` is absent for the
# opposite reason — it is checked by `evidence.assert_uploaded`, which asks a
# question about a *file* that no text validator could.
_CHECKS: dict[str, str] = {
	"Number": "number",
	"Date": "date",
	"Select": "one_of",
	"MultiSelect": "any_of",
	"Yes/No": "yes_no",
	"Email": "email",
}

YES, NO = "Yes", "No"


# --- the opening -------------------------------------------------------------


def read(opening: str):
	"""The opening, through the document cache. Treat as read-only."""
	return frappe.get_cached_doc(OPENING_DOCTYPE, opening)


def purpose(opening_doc) -> str:
	"""Employment or volunteering. Employment where a society has not said.

	The direction every unset setting in this app takes: a society that has not
	answered has not thereby made every opening a volunteering one, and HRMS's own
	behaviour is what an opening created before this field existed should keep.
	"""
	return opening_doc.get(opening_fields.PURPOSE_FIELD) or opening_fields.PURPOSE_EMPLOYMENT


def is_volunteering(opening_doc) -> bool:
	return purpose(opening_doc) == opening_fields.PURPOSE_VOLUNTEER


def questions(opening: str) -> list[dict]:
	"""The screening questions on an opening, in the order they are asked.

	Built field by field rather than handed over as rows: the scoring columns —
	`weight`, `max_score`, `expected_answer`, `is_knock_off` — are the society's
	own marking scheme and are nobody's business on the form somebody is filling
	in. A candidate who could read `expected_answer` would be answering a
	different exam.
	"""
	opening_doc = read(opening)

	return [
		{
			"question_id": row.question_id,
			"question": row.question,
			"question_type": row.question_type,
			"is_required": bool(row.is_required),
			"help_text": row.help_text,
			"options": _options(row),
			"depends_on_question": row.depends_on_question,
			"show_if_answer_is": row.show_if_answer_is,
		}
		for row in (opening_doc.get("screening_questions") or [])
	]


def _options(row) -> list[str]:
	"""A Select or MultiSelect question's choices, one per line, blanks dropped."""
	return [line.strip() for line in (row.options or "").splitlines() if line.strip()]


def assert_questions_unlocked(opening_doc) -> None:
	"""Refuse a change to the question set once anybody has answered it.

	**The answers snapshot the wording, and that is not enough on its own.**
	Adding a required question after fifty people have applied would make fifty
	applications retrospectively incomplete against a question none of them was
	shown; removing one would strand fifty answers pointing at nothing. Either
	way the register stops being comparable, which is the only thing a screening
	question set is for.

	Wording, help text and order stay editable — none of those changes what was
	asked, and a typo in a question fifty people already answered is worth fixing.
	What is frozen is the *set*: which questions exist, of what type, and whether
	each is required.
	"""
	if opening_doc.is_new():
		return

	if not frappe.db.exists(APPLICANT_DOCTYPE, {"job_title": opening_doc.name}):
		return

	before = opening_doc.get_doc_before_save()

	if not before:
		return

	if _shape(before) == _shape(opening_doc):
		return

	frappe.throw(
		_(
			"People have already answered this opening's questions, so the questions themselves"
			" cannot change: a set that moved underneath the answers would stop the applications"
			" being comparable, which is the only thing a screening set is for. Reword a question"
			" or reorder them freely; to ask something new, close this opening and post another."
		),
		frappe.ValidationError,
		title=_("Already Answered"),
	)


def _shape(opening_doc) -> set[tuple]:
	"""What must not change: which questions exist, of what type, and required or not.

	A set rather than a list, so reordering is not a change — the order is a
	presentation decision and nobody's answer depends on it.
	"""
	return {
		(row.question_id, row.question_type, bool(row.is_required))
		for row in (opening_doc.get("screening_questions") or [])
	}


def on_opening_validate(doc, method=None) -> None:
	"""Wired through `doc_events`; HRMS's controller is not edited."""
	assert_questions_unlocked(doc)


# --- who may apply -----------------------------------------------------------


def assert_may_apply(opening_doc, volunteer: str | None) -> None:
	"""Throw unless this person may apply for this opening, through this door.

	Two refusals, and they say different things on purpose. An employment opening
	refused here is not a rejection of the person — it is this door saying it is
	the wrong door, and HRMS's own form is the right one. A volunteering opening
	refused because the caller is not an approved volunteer is the eligibility
	rule the agreed scope asks for, and it points at the thing they should do
	instead.
	"""
	if not is_volunteering(opening_doc):
		frappe.throw(
			_(
				"{0} is a job rather than a volunteering role, and it is applied for through the"
				" society's own recruitment pages."
			).format(frappe.bold(opening_doc.job_title)),
			frappe.ValidationError,
			title=_("Not A Volunteering Role"),
		)

	if opening_doc.status != "Open":
		frappe.throw(
			_("{0} is no longer taking applications.").format(frappe.bold(opening_doc.job_title)),
			frappe.ValidationError,
			title=_("Closed"),
		)

	if not volunteer:
		frappe.throw(
			_(
				"Volunteering roles are open to the society's own approved volunteers. Register as"
				" a volunteer first, and this will be here when you are."
			),
			frappe.PermissionError,
			title=_("Not A Volunteer Yet"),
		)

	status = frappe.db.get_value(VOLUNTEER_DOCTYPE, volunteer, "status")

	if status != "Active":
		frappe.throw(
			_(
				"Your volunteer record is {0}, so it cannot be used to apply for a role just now."
				" Speak to your branch."
			).format(frappe.bold(_(status or "missing"))),
			frappe.PermissionError,
			title=_("Volunteer Record Not Active"),
		)


def live_application(opening: str, volunteer: str) -> str | None:
	"""This volunteer's application to this opening that the society has not finished with.

	Withdrawn and rejected ones are deliberately not counted: applying again after
	a no is a real thing people do, and it produces a second record rather than
	overwriting the first.
	"""
	rows = frappe.get_all(
		APPLICANT_DOCTYPE,
		filters={
			"job_title": opening,
			applicant_fields.VOLUNTEER_FIELD: volunteer,
			"status": ("in", LIVE_STATUSES),
		},
		fields=["name", applicant_fields.WITHDRAWN_FIELD],
		ignore_permissions=True,
	)

	return next(
		(row["name"] for row in rows if not row.get(applicant_fields.WITHDRAWN_FIELD)), None
	)


def assert_not_duplicate(opening: str, volunteer: str) -> None:
	"""Throw where a live application already exists."""
	existing = live_application(opening, volunteer)

	if not existing:
		return

	frappe.throw(
		_(
			"You have already applied for this and the society has not answered yet ({0}). A"
			" second application would put two records of the same intention in front of the"
			" same person."
		).format(frappe.bold(existing)),
		frappe.DuplicateEntryError,
		title=_("Already Applied"),
	)


# --- the answers -------------------------------------------------------------


def answer_rows(opening: str, answers: dict) -> list[dict]:
	"""Every question on the opening, checked, with its wording snapshotted onto the row.

	Driven by the *opening's* questions rather than by what the caller sent, which
	is the whole security property: a payload naming a question that does not
	exist writes nothing, and one that omits a required question is refused rather
	than quietly accepted.

	The upload path is `evidence.assert_uploaded`, which refuses anything that is
	not a real uploaded file — a caller cannot pass a path to somebody else's
	document and have it recorded as their answer.
	"""
	rows = []

	for question in questions(opening):
		given = answers.get(question["question_id"])
		given = given.strip() if isinstance(given, str) else given

		if question["question_type"] == "Upload":
			if question["is_required"] or given:
				given = evidence.assert_uploaded(given, question["question"])
		elif question["is_required"] and given in (None, "", []):
			frappe.throw(
				_("{0} has to be answered.").format(frappe.bold(question["question"])),
				frappe.MandatoryError,
				title=_("Unanswered Question"),
			)
		elif given not in (None, "", []):
			_check(question, given)

		rows.append(
			{
				"question_id": question["question_id"],
				"question": question["question"],
				"question_type": question["question_type"],
				"is_required": 1 if question["is_required"] else 0,
				"answer": None if question["question_type"] == "Upload" else _as_text(given),
				"answer_file": given if question["question_type"] == "Upload" else None,
			}
		)

	return rows


def _as_text(given) -> str | None:
	"""One answer as the string the row stores. A multi-select is comma-joined."""
	if given in (None, "", []):
		return None

	if isinstance(given, list | tuple):
		return ", ".join(str(item) for item in given)

	return str(given)


def _check(question: dict, given) -> None:
	"""Validate one answer against its own type. Silent for a type with no check."""
	check = _CHECKS.get(question["question_type"])

	if not check:
		return

	getattr(_Checks, check)(question, given)


class _Checks:
	"""One method per answer type, looked up by name rather than branched on.

	A class only because it is a namespace: `_CHECKS` maps a question type to a
	method name, so a new type is a row in that table and a method here, and never
	an `if` in `answer_rows`.
	"""

	@staticmethod
	def number(question, given) -> None:
		try:
			flt(given, precision=6)
			float(str(given).strip())
		except (TypeError, ValueError):
			_refuse(question, _("a number"))

	@staticmethod
	def date(question, given) -> None:
		try:
			getdate(given)
		except Exception:
			_refuse(question, _("a date"))

	@staticmethod
	def one_of(question, given) -> None:
		if question["options"] and str(given) not in question["options"]:
			_refuse(question, ", ".join(question["options"]))

	@staticmethod
	def any_of(question, given) -> None:
		chosen = given if isinstance(given, list | tuple) else [given]

		if not question["options"]:
			return

		for item in chosen:
			if str(item) not in question["options"]:
				_refuse(question, ", ".join(question["options"]))

	@staticmethod
	def yes_no(question, given) -> None:
		if str(given) not in (YES, NO):
			_refuse(question, f"{YES} / {NO}")

	@staticmethod
	def email(question, given) -> None:
		if "@" not in str(given):
			_refuse(question, _("an email address"))


def _refuse(question: dict, expected: str) -> None:
	frappe.throw(
		_("{0} expects {1}.").format(frappe.bold(question["question"]), expected),
		frappe.ValidationError,
		title=_("Answer Not Understood"),
	)


# --- applying ----------------------------------------------------------------


def apply(opening: str, volunteer: str, answers: dict | None = None, cover_letter: str | None = None):
	"""Make the application. Returns the `Job Applicant` document.

	**Inserted elevated, and the argument is the volunteer's.** A volunteer holds
	no role on HRMS's applicant register and correctly never will — it is a
	recruiter's pipeline, not a personal record — so an ordinary insert would
	refuse the one person the endpoint exists for. What replaces the permission
	check is not nothing: `assert_may_apply` has established that this person is
	an approved active volunteer and that this opening is a volunteering one that
	is still open, and `assert_not_duplicate` that they have not already applied.
	The volunteer is resolved from the session by the endpoint above and is never
	an argument, so nobody can apply as anybody else.

	The identity is copied from the Red Profile rather than asked for. The society
	already holds it, and a form that made somebody retype their own name would be
	a form that could disagree with the register.
	"""
	opening_doc = read(opening)

	assert_may_apply(opening_doc, volunteer)
	assert_not_duplicate(opening, volunteer)

	identity = _identity(volunteer)
	rows = answer_rows(opening, answers or {})

	applicant = frappe.get_doc(
		{
			"doctype": APPLICANT_DOCTYPE,
			"job_title": opening,
			"applicant_name": identity["full_name"],
			"email_id": identity["email"],
			"phone_number": identity["phone"],
			"status": applicant_fields.STATUS_OPEN,
			"cover_letter": cover_letter,
			applicant_fields.VOLUNTEER_FIELD: volunteer,
			applicant_fields.PROFILE_FIELD: identity["red_profile"],
			applicant_fields.GEO_NODE_FIELD: opening_doc.get("vmms_geo_node")
			or identity["home_geo_node"],
			applicant_fields.ANSWERS_FIELD: rows,
		}
	)
	applicant.insert(ignore_permissions=True)

	_secure_answers(applicant)

	return applicant


def _identity(volunteer: str) -> dict:
	"""Name, email, phone and branch, from the records the society already holds.

	Read through the Volunteer's own Red Profile. Empty strings rather than
	`None` for the contact fields, because HRMS makes the email mandatory and a
	sentence about a missing email is a better failure than a null one.
	"""
	row = frappe.db.get_value(
		VOLUNTEER_DOCTYPE, volunteer, ["red_profile", "home_geo_node"], as_dict=True
	)

	if not row:
		frappe.throw(
			_("This volunteer record could not be read."),
			frappe.DoesNotExistError,
			title=_("No Volunteer Record"),
		)

	profile = frappe.db.get_value(
		"Red Profile", row.red_profile, ["full_name", "email", "phone"], as_dict=True
	) or frappe._dict()

	if not profile.get("email"):
		frappe.throw(
			_(
				"Your record has no email address on it, and an application cannot be sent"
				" without one. Add one to your profile first."
			),
			frappe.MandatoryError,
			title=_("No Email Address"),
		)

	return {
		"red_profile": row.red_profile,
		"home_geo_node": row.home_geo_node,
		"full_name": profile.get("full_name") or row.red_profile,
		"email": profile.get("email"),
		"phone": profile.get("phone") or "",
	}


def _secure_answers(applicant) -> None:
	"""Move every uploaded answer into private storage, anchored to the application.

	**Through `frappe.db.set_value` on the child row**, which is the same shape
	`registration/services/questions.py::anchor_files` uses and for the same
	reason it gives: the `File` itself was saved properly and carries its own
	version; this only follows it to where it moved. Saving the parent instead
	would be a second save of a document that has just been inserted.
	"""
	for row in applicant.get(applicant_fields.ANSWERS_FIELD) or []:
		if not row.answer_file:
			continue

		secured = evidence.secure(applicant, row.answer_file)

		if secured and secured != row.answer_file:
			frappe.db.set_value(
				row.doctype, row.name, "answer_file", secured, update_modified=False
			)
			row.answer_file = secured


# --- taking it back ----------------------------------------------------------


def withdraw(applicant, reason: str | None = None) -> dict:
	"""The applicant's own act. Idempotent, and never a rejection.

	**A pair of fields rather than a sixth status**, and the distinction is the
	whole point: HRMS's statuses record what the *society* decided, and marking
	somebody Rejected because they changed their mind would put a decision nobody
	made into their record — one that a reference or a future application would
	read as the society's opinion of them.

	The status is moved to `Hold`, which is HRMS's own word for an application
	nobody is progressing, so a recruiter's pipeline stops showing it as live
	without anybody having decided anything about the person.
	"""
	if applicant.get(applicant_fields.WITHDRAWN_FIELD):
		return dto(applicant)

	applicant.set(applicant_fields.WITHDRAWN_FIELD, now_datetime())
	applicant.set("vmms_withdrawal_reason", reason)
	applicant.status = applicant_fields.STATUS_HOLD
	applicant.save(ignore_permissions=True)
	applicant.add_comment("Comment", _("Withdrawn by the applicant. {0}").format(reason or ""))

	return dto(applicant)


def is_withdrawn(applicant) -> bool:
	return bool(applicant.get(applicant_fields.WITHDRAWN_FIELD))


# --- turning it into work ----------------------------------------------------


def convert(applicant) -> dict:
	"""Turn an accepted application into the work it was for. Once, and never twice.

	Two shapes, chosen by what the opening names rather than by an argument: an
	opening that staffs a deployment produces a `VMMS Deployment Assignment`, and
	one that does not produces a `VMMS Task`. A caller that could choose would be
	a caller that could put somebody on a deployment the opening was never about.

	**Idempotent, and that is the property that matters most.** A second run finds
	the link already written and returns it; without that, a double-clicked button
	puts the same person on the same deployment twice, and one of those two
	records is then a lie nobody can tell from the other.

	Explicit rather than automatic on acceptance. Accepting somebody is a
   recruiter's decision about a person; putting them on a roster is an
	operational act with a date and a place attached, and a society that wanted
	those to be one act can make them one on a screen — but the app must not
	assume it.
	"""
	if not is_volunteering(read(applicant.job_title)):
		frappe.throw(
			_("This is an employment application, and it is HRMS's own to progress."),
			frappe.ValidationError,
			title=_("Not A Volunteering Application"),
		)

	if applicant.status != applicant_fields.STATUS_ACCEPTED:
		frappe.throw(
			_("{0} is {1}. Only an accepted application becomes work.").format(
				frappe.bold(applicant.name), frappe.bold(_(applicant.status))
			),
			frappe.ValidationError,
			title=_("Not Accepted"),
		)

	if is_withdrawn(applicant):
		frappe.throw(
			_("This application was withdrawn by the applicant."),
			frappe.ValidationError,
			title=_("Withdrawn"),
		)

	existing = applicant.get("vmms_deployment_assignment") or applicant.get("vmms_task")

	if existing:
		return {"already": True, **_outcome(applicant)}

	volunteer = applicant.get(applicant_fields.VOLUNTEER_FIELD)

	if not volunteer:
		frappe.throw(
			_("This application is not linked to a volunteer record, so there is nobody to place."),
			frappe.ValidationError,
			title=_("No Volunteer"),
		)

	opening_doc = read(applicant.job_title)

	if opening_doc.get("vmms_deployment"):
		_to_assignment(applicant, opening_doc, volunteer)
	else:
		_to_task(applicant, opening_doc, volunteer)

	applicant.reload()

	return {"already": False, **_outcome(applicant)}


def _to_assignment(applicant, opening_doc, volunteer: str) -> None:
	"""A place on the deployment the opening staffs, raised as a question.

	`Pending`, not `Assigned`: the person applied, the society accepted, and the
	assignment carries the terms of reference they are now being asked to agree
	to. Accepting a role in the abstract is not the same act as agreeing to a
	particular mission document, and this app has never treated it as one.
	"""
	from vmmsx.deployment.services import assignment as assignment_service

	deployment = frappe.get_doc("VMMS Deployment", opening_doc.get("vmms_deployment"))
	doc = assignment_service.create(
		deployment,
		volunteer,
		status=assignment_service.STATUS_PENDING,
		assignment_title=opening_doc.job_title,
		notes=_("Accepted from {0}.").format(applicant.name),
	)

	frappe.db.set_value(
		applicant.doctype, applicant.name, "vmms_deployment_assignment", doc.name,
		update_modified=False,
	)


def _to_task(applicant, opening_doc, volunteer: str) -> None:
	"""A piece of work, where the opening names no deployment.

	The opening's description is the brief, which is the same copy-not-reference
	rule a task batch follows: editing the advertisement afterwards must not
	rewrite work somebody has already been given.
	"""
	from vmmsx.task.services import task as task_service

	doc = task_service.assign(
		volunteer=volunteer,
		subject=opening_doc.job_title,
		description=frappe.utils.strip_html(opening_doc.description or "").strip()
		or opening_doc.job_title,
		geo_node=opening_doc.get("vmms_geo_node"),
		project=opening_doc.get("vmms_project"),
		due_at=f"{opening_doc.vmms_available_to} 23:59:59"
		if opening_doc.get("vmms_available_to")
		else None,
	)

	frappe.db.set_value(
		applicant.doctype, applicant.name, "vmms_task", doc.name, update_modified=False
	)


def _outcome(applicant) -> dict:
	return {
		"applicant": applicant.name,
		"deployment_assignment": applicant.get("vmms_deployment_assignment"),
		"task": applicant.get("vmms_task"),
	}


# --- describing one ----------------------------------------------------------


def dto(applicant) -> dict:
	"""One application, as an explicit dict. Built field by field.

	Never the Document: `Job Applicant` carries a recruiter's notes, a rating and
	a salary range, none of which is the applicant's to read on their own
	self-service page.
	"""
	return {
		"name": applicant.name,
		"opening": applicant.job_title,
		"opening_title": frappe.db.get_value(OPENING_DOCTYPE, applicant.job_title, "job_title")
		if applicant.job_title
		else None,
		"status": applicant.status,
		"applied_on": str(applicant.creation) if applicant.creation else None,
		"volunteer": applicant.get(applicant_fields.VOLUNTEER_FIELD),
		"geo_node": applicant.get(applicant_fields.GEO_NODE_FIELD),
		"is_withdrawn": is_withdrawn(applicant),
		"withdrawn_on": applicant.get(applicant_fields.WITHDRAWN_FIELD),
		"withdrawal_reason": applicant.get("vmms_withdrawal_reason"),
		"cover_letter": applicant.cover_letter,
		# What they answered, with the questions as they were asked. Shown back to
		# the applicant, which is the whole reason the snapshot exists.
		"answers": [
			{
				"question_id": row.question_id,
				"question": row.question,
				"question_type": row.question_type,
				"answer": row.answer,
				"answer_file": row.answer_file,
			}
			for row in applicant.get(applicant_fields.ANSWERS_FIELD) or []
		],
		**_outcome(applicant),
	}
