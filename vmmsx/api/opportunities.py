# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Published HRMS openings and portal application endpoints.

Readers expose only curated, published openings. Applicants use their own
signed-in identity and create records in HRMS's existing Job Applicant register.
No browser call needs Job Opening read permission.
"""

import frappe
from frappe import _

from vmmsx.hr.services import application as application_service
from vmmsx.hr.services import openings as seam
from vmmsx.registration.services import evidence
from vmmsx.setup import job_applicant_fields as applicant_fields
from vmmsx.setup import job_opening_fields as opening_fields

APPLICANT_DOCTYPE = "Job Applicant"


@frappe.whitelist()
def browse(
	search: str | None = None,
	department: str | None = None,
	limit: int = 60,
) -> dict:
	"""Published, open job openings the society is recruiting for.

	`available` travels with the rows rather than being a second endpoint,
	because the screen needs it at the moment it decides what to draw: no
	openings because HRMS is not installed and no openings because the society
	is not recruiting are different sentences to put in front of somebody.
	"""
	return {
		"available": seam.is_available(),
		"opportunities": seam.published(search=search, department=department, limit=limit),
	}


@frappe.whitelist()
def detail(name: str) -> dict | None:
	"""One opening in full, for the screen a card opens.

	The same boundary as the listing — `publish` and `status`, both HRMS's own
	decisions — so naming a docname buys nothing a caller could not already see.
	None rather than an error for an opening that has closed: following an old
	link is an ordinary thing to do, and the screen says so.
	"""
	return seam.detail(name)


@frappe.whitelist()
def filters() -> dict:
	"""What the picker on the board offers.

	Departments only, and only those with something open. Where an opening is
	held is HRMS's `location`, which is its own Branch record rather than a Geo
	Node — this app does not have a second answer to where a job is, and does
	not invent one by mapping between the two.
	"""
	return {
		"available": seam.is_available(),
		"departments": seam.departments(),
	}


# --- applying -----------------------------------------------------------------
#
# The board above is a guest surface: anybody may browse what a society has
# published. Everything below is the volunteer's own door, and every endpoint
# resolves them from the session rather than taking a person — so no argument
# names anybody, and nobody can apply as, or read, somebody else.
#
# Employment openings are untouched by all of it. They keep HRMS's own public
# form, and `application.assert_may_apply` says so in words rather than failing
# a permission check somebody would have to guess at.


@frappe.whitelist()
def opening_questions(name: str) -> dict:
	"""The screening questions on an opening, and whether the caller may answer them.

	Both in one call, because a form needs them at the same moment: what to draw,
	and whether to draw a submit button or a sentence explaining why not.

	The society's own marking scheme — the weights, the expected answers, the
	knock-off flags — is deliberately not here. A candidate who could read it
	would be answering a different exam.
	"""
	opening = seam.detail(name)

	if not opening:
		return {"opening": None, "questions": [], "may_apply": False, "reason": None}

	volunteer = _my_volunteer()
	reason = None

	# Asked by catching the refusal rather than by restating its rules, so the
	# form's explanation and the server's refusal cannot come apart.
	try:
		application_service.assert_may_apply(application_service.read(name), volunteer)
		may_apply = True
	except Exception:
		may_apply = False
		reason = _last_message()

	return {
		"opening": opening,
		"questions": application_service.questions(name),
		"may_apply": may_apply,
		"reason": reason,
		"already_applied": bool(
			volunteer and application_service.live_application(name, volunteer)
		),
	}


@frappe.whitelist()
def job_application_form(name: str) -> dict:
	"""A safe application form for a published opening, without Job Opening read permission."""
	opening = seam.detail(name)
	if not opening:
		return {"opening": None}

	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in to apply."), frappe.PermissionError)

	profile = frappe.db.get_value("Red Profile", {"user": user}, ["full_name", "phone"], as_dict=True)
	account = frappe.db.get_value("User", user, ["full_name", "email"], as_dict=True)
	email = (account.email if account else user) or user
	volunteer = _my_volunteer()
	volunteering = frappe.db.get_value("Job Opening", name, opening_fields.PURPOSE_FIELD) == opening_fields.PURPOSE_VOLUNTEER
	eligibility = _volunteer_eligibility(volunteer)
	return {
		"opening": opening,
		"volunteering": volunteering,
		"questions": application_service.questions(name),
		"identity": {
			"full_name": (profile.full_name if profile else None) or (account.full_name if account else None) or "",
			"email": email,
			"phone": (profile.phone if profile else None) or "",
		},
		"already_applied": bool(volunteer and application_service.live_application(name, volunteer)) if volunteering else bool(
			frappe.db.exists(APPLICANT_DOCTYPE, {"job_title": name, "email_id": email, "status": ("in", application_service.LIVE_STATUSES)})
		),
		"may_apply": eligibility == "approved",
		"eligibility": eligibility,
	}


@frappe.whitelist(methods=["POST"])
def apply_for_job(
	name: str,
	full_name: str,
	phone: str | None = None,
	cover_letter: str | None = None,
	resume: str | None = None,
	answers: dict | str | None = None,
) -> dict:
	"""Create an HRMS Job Applicant from the signed-in account's own email."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in to apply."), frappe.PermissionError)
	if not seam.detail(name):
		frappe.throw(_("This opening is no longer accepting applications."), frappe.ValidationError)
	eligibility = _volunteer_eligibility(_my_volunteer())
	if eligibility != "approved":
		frappe.throw(_eligibility_message(eligibility), frappe.PermissionError)
	if frappe.db.get_value("Job Opening", name, opening_fields.PURPOSE_FIELD) == opening_fields.PURPOSE_VOLUNTEER:
		frappe.throw(_("Use the volunteer application for this role."), frappe.ValidationError)

	account = frappe.db.get_value("User", frappe.session.user, ["email"], as_dict=True)
	email = (account.email if account else frappe.session.user) or ""
	if not email or "@" not in email:
		frappe.throw(_("Your account needs an email address before you can apply."), frappe.ValidationError)
	full_name = (full_name or "").strip()
	if not full_name:
		frappe.throw(_("Enter your full name."), frappe.MandatoryError)
	if frappe.db.exists(APPLICANT_DOCTYPE, {"job_title": name, "email_id": email, "status": ("in", application_service.LIVE_STATUSES)}):
		frappe.throw(_("You have already applied for this opening."), frappe.DuplicateEntryError)

	resume = evidence.assert_uploaded(resume, "CV or resume") if resume else None
	if resume:
		file = frappe.db.get_value("File", {"file_url": resume}, ["owner", "attached_to_name"], as_dict=True)
		if not file or file.owner != frappe.session.user or file.attached_to_name:
			frappe.throw(_("Upload your own CV or resume before applying."), frappe.PermissionError)

	parsed = frappe.parse_json(answers) if isinstance(answers, str) else (answers or {})
	if not isinstance(parsed, dict):
		frappe.throw(_("Answers must be a set of question responses."), frappe.ValidationError)
	for question in application_service.questions(name):
		if question["question_type"] == "Upload" and parsed.get(question["question_id"]):
			url = evidence.assert_uploaded(parsed[question["question_id"]], question["question"])
			file = frappe.db.get_value("File", {"file_url": url}, ["owner", "attached_to_name"], as_dict=True)
			if not file or file.owner != frappe.session.user or file.attached_to_name:
				frappe.throw(_("Upload your own file for {0}.").format(question["question"]), frappe.PermissionError)
	applicant = frappe.get_doc({
		"doctype": APPLICANT_DOCTYPE,
		"job_title": name,
		"applicant_name": full_name,
		"email_id": email,
		"phone_number": (phone or "").strip(),
		"cover_letter": (cover_letter or "").strip(),
		"status": applicant_fields.STATUS_OPEN,
		applicant_fields.ANSWERS_FIELD: application_service.answer_rows(name, parsed),
	})
	applicant.insert(ignore_permissions=True)
	if resume:
		secured = evidence.secure(applicant, resume)
		frappe.db.set_value(APPLICANT_DOCTYPE, applicant.name, "resume_attachment", secured, update_modified=False)
	for row in applicant.get(applicant_fields.ANSWERS_FIELD) or []:
		if row.answer_file:
			secured = evidence.secure(applicant, row.answer_file)
			frappe.db.set_value(row.doctype, row.name, "answer_file", secured, update_modified=False)
	return {"name": applicant.name, "opening": name}


def _volunteer_eligibility(volunteer: str | None) -> str:
	"""Use the linked record and the registration engine's open application check."""
	status = frappe.db.get_value("VMMS Volunteer", volunteer, "status") if volunteer else None
	if status == "Active":
		return "approved"

	from vmmsx.api import registration

	if registration._open_registration(registration.APPLICATION_DOCTYPE):
		return "pending"
	return "inactive" if status in ("Suspended", "Exited") else "not_registered"


def _eligibility_message(eligibility: str) -> str:
	if eligibility == "pending":
		return _("Your volunteer application must be fully approved before you can apply for an opportunity.")
	if eligibility == "inactive":
		return _("Your volunteer record must be active before you can apply. Please contact your branch.")
	return _("Register as a volunteer and wait for full approval before applying for an opportunity.")


def _last_message() -> str | None:
	"""The sentence the refusal above queued, taken off the message log.

	`frappe.throw` puts its message there on the way out. Reading it back is how
	this endpoint reports *why* somebody may not apply without restating the rule
	— and clearing it is what stops the same sentence being rendered a second
	time as an error on a request that succeeded.
	"""
	log = frappe.local.message_log or []

	if not log:
		return None

	message = log[-1]
	frappe.clear_last_message()

	return frappe.utils.strip_html(
		message.get("message") if isinstance(message, dict) else str(message)
	).strip() or None


@frappe.whitelist()
def apply_to_opening(name: str, answers: dict | str | None = None, cover_letter: str | None = None) -> dict:
	"""Apply for a volunteering opening as the caller's own volunteer record.

	The volunteer comes from the session and is never an argument, the same rule
	every possessive endpoint in this app follows. The service refuses an
	employment opening, a closed one, somebody who is not an approved active
	volunteer, and a second live application.
	"""
	parsed = frappe.parse_json(answers) if isinstance(answers, str) else (answers or {})

	return application_service.dto(
		application_service.apply(
			name, _my_volunteer(), answers=parsed, cover_letter=cover_letter
		)
	)


@frappe.whitelist()
def my_applications() -> dict:
	"""The caller's own applications, with the answers they gave.

	Takes no person, so it names nobody. `ignore_permissions` with the argument
	stated: a volunteer holds no role on HRMS's applicant register — it is a
	recruiter's pipeline — and the volunteer here is resolved from the session, so
	this cannot read anybody else's.
	"""
	volunteer = _my_volunteer()

	if not volunteer:
		return {"volunteer": None, "applications": []}

	names = frappe.get_all(
		APPLICANT_DOCTYPE,
		filters={"vmms_volunteer": volunteer},
		order_by="creation desc",
		pluck="name",
		ignore_permissions=True,
	)

	return {
		"volunteer": volunteer,
		"applications": [
			application_service.dto(frappe.get_doc(APPLICANT_DOCTYPE, name)) for name in names
		],
	}


@frappe.whitelist()
def withdraw_application(name: str, reason: str | None = None) -> dict:
	"""Take an application back. The applicant's own act, and never a rejection.

	Ownership rather than permission, the distinction `api/tasks.py` draws at
	length: the application has to belong to the caller's own volunteer record.
	"""
	return application_service.withdraw(_mine(name), reason)


@frappe.whitelist()
def convert_application(name: str) -> dict:
	"""Turn an accepted application into the work it was for. Idempotent.

	The **coordinator's** door, unlike everything else below the board: ordinary
	write permission on the applicant record, because placing somebody on a
	deployment is an act on the society's register rather than on a personal one.
	"""
	applicant = frappe.get_doc(APPLICANT_DOCTYPE, name)
	applicant.check_permission("write")

	return application_service.convert(applicant)


def _mine(name: str):
	"""An application that belongs to the caller's own volunteer record.

	A `PermissionError` for anybody else, and the same one whether the record
	exists or not: telling a caller that somebody else's application is there is
	itself a disclosure.
	"""
	volunteer = _my_volunteer()
	applicant = frappe.get_doc(APPLICANT_DOCTYPE, name)

	if not volunteer or applicant.get("vmms_volunteer") != volunteer:
		frappe.throw(
			frappe._("This is not your application."),
			frappe.PermissionError,
			title=frappe._("Not Yours"),
		)

	return applicant


def _my_volunteer() -> str | None:
	"""The caller's own volunteer record, or None.

	Through the Red Profile behind the session, which is this app's one answer to
	"who is this" — never `doc.owner`, for the reason `member/services/review.py`
	records: owner is who filed a record, not who it is about.
	"""
	profile = frappe.db.get_value("Red Profile", {"user": frappe.session.user}, "name")

	if not profile:
		return None

	return frappe.db.get_value("VMMS Volunteer", {"red_profile": profile}, "name")
