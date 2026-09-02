# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The opportunities board: the society's published job openings.

**It reads HRMS's `Job Opening`**, through the seam in
`vmmsx/hr/services/openings.py`, which is the only file in this app that names
that doctype. This endpoint adds a DTO boundary and nothing else, the same shape
as `api/events.py` over the Buzz seam.

**What this replaced, and why.** The board used to read
`VMMS Deployment Request` — the society's own record of needing people
somewhere. That record is real and still does its job, but it was the wrong
thing to advertise: it is an internal staffing note, and there was no way for
anybody to answer one. The screen said so out loud, explaining that a
coordinator matches volunteers from the register instead, which is an honest
sentence and a poor advertisement. A society already running its recruitment in
HRMS has the opening, the application form and the pipeline there, so pointing
the board at it is what lets somebody actually apply.

**Browse here, apply there.** There is no application endpoint in this file and
there will not be one. HRMS owns the applicant record, the duplicate check and
everything after it, and each card's call to action is a full navigation to
HRMS's own application form. A vmmsx endpoint wrapping any of that would be a second
implementation of a rule that has to stay in step with HRMS's forever.

**Signed in, deliberately.** Neither endpoint is `allow_guest`. The three
guest-readable endpoints in this app are `content.surface`, `society.branding`
and `locations.published`, each bounded by a flag on a document; a fourth needs
the same justification, which is a question somebody has *before* they have an
account. HRMS publishes its own openings to the website for that audience.

**HRMS absent is an ordinary state, not an error.** vmmsx does not declare
`hrms` in `required_apps`. On a site without it both endpoints answer empty and
the screen says so rather than showing a spinner forever.
"""

import frappe

from vmmsx.hr.services import application as application_service
from vmmsx.hr.services import openings as seam

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
