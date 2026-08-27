# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""How an application becomes a volunteer — the engine's third consumer.

**Routing is delegated entirely.** This module never resolves an approver, never
touches a geo table, and never asks who holds what where. It calls
`approvals.services.engine`, which calls core. Volunteer Application is the third
doctype to go through that engine — after the stand-in the engine's own tests
use, and after Membership — and the value of a third consumer is entirely in it
being the *same* engine: a second routing path would eventually disagree with the
first, and the day it did, applications would route to people who cannot open
them. `tests/test_delegation.py` walks the AST of every file under `volunteer/`
and fails if one of them grows a resolver.

**Acceptance is a predicate, not a sequence**, the same shape membership
activation has:

    approved?          asked of the engine's state — `contract.state(...)`
    already accepted?  asked of the application's own `volunteer` link

`try_accept()` is therefore safe to call after any event and in any order, and
it is called from `on_update`, which runs after every save. So an approval
recorded by the engine turns into a volunteer without the engine knowing that
volunteers exist. There is no ordering bug to have, because there is no
ordering.

**No source file branches on a stage.** Which stages an application passes
through, who they need, and how many of them must act are rows in a
`VMMS Approval Workflow` a society wrote. This module asks one question of the
engine — is the state Approved — and a society that configures no approvals at
all gets an application that approves on submission, because that is what the
engine does with stages that resolve nobody and are optional. That path needs no
code here either.
"""

import frappe
from frappe import _
from frappe.utils import getdate, today

from vmmsx.approvals import states
from vmmsx.approvals.services import contract, engine
from vmmsx.registration.services import questions
from vmmsx.volunteer.services import hr, identity
from vmmsx.volunteer.services import volunteer as volunteer_service

APPLICATION_DOCTYPE = "VMMS Volunteer Application"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"

ACCEPTANCE_FLAG = "vmms_application_accepting"


# --- controller-facing defaults --------------------------------------------
#
# The application owns only its Serving Branch. Where the person lives is read
# from Red Profile and used as a convenient default, never copied onto this row.


def default_serving_branch(application) -> None:
	"""Serving Branch defaults from Home Area for a Local applicant. Idempotent.

	Only when Serving Branch is still blank, so a coordinator's own choice is
	never overwritten. An applicant living abroad has no Home Area and must say
	explicitly where they will serve.
	"""
	if application.get("geo_node") or not application.get("red_profile"):
		return

	home = frappe.db.get_value("Red Profile", application.red_profile, "home_geo_node")

	if home:
		application.geo_node = home


# --- submission -----------------------------------------------------------


def submit(application) -> dict:
	"""Put an application into motion. Idempotent.

	Everything about routing happens inside `engine.submit()`: it enforces the
	anchor rules (ACC-02 and the workflow's permitted levels, ACC-03), resolves
	the people through core, moves the approval state and puts the document in
	their queue. Called on an application already under review, it re-syncs the
	queue and restarts nothing.

	Profile completeness is checked here, before any of that, deliberately not in
	`validate()`: citizenship, identification, date of birth and a completed
	residence answer are required to *submit*, not to let a draft exist. That is
	the same build-a-draft-in-stages allowance a paper intake needs.
	"""
	if states.is_terminal(contract.state(application)):
		return status(application)

	assert_ready(application)
	engine.submit(application)

	accepted = try_accept(application)

	return accepted or status(application)


# --- readiness to submit ---------------------------------------------------


def assert_ready(application) -> None:
	"""Refuse submission until the application is complete enough to review.

	Four profile checks, none of them in `validate()`. A draft may be built up over
	several saves before an applicant or a clerk is ready to send it on — every
	existing way of creating an application still creates a bare draft — so
	these join the gate at the one moment this app can insist the record is
	actually reviewable, rather than the moment it starts existing.

	The third is the society's own, and it is here for exactly the same reason:
	a question a branch added is as required as identification is, and neither is
	required to hold a half-finished draft. `assert_answered` is a no-op until
	somebody creates a question, so a society that has added none is unaffected.
	"""
	_assert_country_of_citizenship(application)
	_assert_identification(application)
	_assert_date_of_birth(application)
	_assert_residency_complete(application)
	questions.assert_answered(application)


def _assert_country_of_citizenship(application) -> None:
	"""A volunteer application needs the person's country of citizenship."""
	if _profile_value(application, "country_of_citizenship"):
		return

	frappe.throw(
		_("Add your Country of Citizenship to your profile before submitting."),
		frappe.MandatoryError,
		title=_("Missing Citizenship"),
	)


def _assert_identification(application) -> None:
	"""Identification lives on Red Profile but is required by this process."""
	profile = application.get("red_profile")

	if profile and frappe.db.exists(
		"Red Profile Identification",
		{
			"parent": profile,
			"parenttype": "Red Profile",
			"parentfield": "identifications",
			"id_type": ("is", "set"),
			"id_number": ("is", "set"),
		},
	):
		return

	frappe.throw(
		_(
			"An application cannot be submitted without an identification. Add an ID Type and ID Number"
			" to your profile before submitting."
		),
		frappe.MandatoryError,
		title=_("Missing Identification"),
	)


def _assert_date_of_birth(application) -> None:
	"""A volunteer's date of birth is required. It is read off the Red Profile.

	**Why the profile and not the application.** `applicant_date_of_birth` is a
	transient intake buffer: `intake.claim_profile` reads it in `before_insert`
	and blanks it, so by the time anything is submitted the field is empty on
	every application whether or not a date was ever given. The date itself lives
	on the Red Profile, which is core's spine and the only place identity is held,
	so that is the only honest thing to test.

	**Why it is mandatory here and optional on the profile.** The same asymmetry
	`_assert_identification` states. Core will hold a person it knows nothing
	about; a society sending somebody on a deployment will not. Age governs what a
	volunteer may be asked to do and what safeguarding applies to them, and a
	register that cannot answer how old its volunteers are cannot answer either.
	Nothing is backfilled — an application already accepted is untouched, because
	this runs at submission and not at save.
	"""
	given = application.get("applicant_date_of_birth") or _profile_value(application, "date_of_birth")

	if given:
		return

	frappe.throw(
		_(
			"An application cannot be submitted without a date of birth. Add it to your profile"
			" and submit again."
		),
		frappe.MandatoryError,
		title=_("Missing Date of Birth"),
	)


def _assert_residency_complete(application) -> None:
	"""The person's Red Profile must contain one complete residence shape."""
	residency_type = _profile_value(application, "residency_type")

	if residency_type == "Abroad":
		if _profile_value(application, "country_of_residence") and _profile_value(
			application, "residence_address"
		):
			return

		frappe.throw(
			_(
				"An applicant living abroad must give both a Country of Residence and an Address"
				" Abroad before this application can be submitted."
			),
			frappe.MandatoryError,
			title=_("Missing Residency Details"),
		)

	if residency_type == "Local" and _profile_value(application, "home_geo_node"):
		return

	if residency_type == "Local":
		frappe.throw(
			_("Add your Home Area to your profile before submitting."),
			frappe.MandatoryError,
			title=_("Missing Home Area"),
		)

	frappe.throw(
		_("Choose whether your residence is Local or Abroad on your profile before submitting."),
		frappe.MandatoryError,
		title=_("Missing Residency"),
	)


def _profile_value(application, fieldname: str):
	profile = application.get("red_profile")

	return frappe.db.get_value("Red Profile", profile, fieldname) if profile else None


# --- acceptance -----------------------------------------------------------


def is_approved(application) -> bool:
	"""Has the approval settled in this application's favour?

	One question, asked of the engine's own state field. Not of a stage, not of
	a decision row, not of who acted — those are the engine's business and a
	reading of them here would be a second interpretation of the same events.
	"""
	return contract.state(application) == states.APPROVED


def is_acceptable(application) -> bool:
	"""Is there a volunteer to create that has not been created already?"""
	return is_approved(application) and not application.volunteer


def try_accept(application) -> dict | None:
	"""Create the volunteer if the predicate holds. Returns the DTO, or None.

	The single entry point for becoming a volunteer. Idempotent — an application
	that has already produced one fails the predicate on its own `volunteer`
	link and returns None.
	"""
	if not is_acceptable(application):
		return None

	return accept(application)


def accept(application) -> dict:
	"""Make it real: the satellite, its living data, the affiliation index, and HR.

	Order matters and is the same order Design 2 requires everywhere. The
	satellite is written first, because it is the truth; core's affiliation index
	is refreshed from it afterwards, because it is a summary. HR comes last and
	cannot fail the acceptance — see `hr.provision`.

	**Seeding sits between the first two, and this is the one moment it happens.**
	What the applicant declared about themselves becomes the volunteer's own
	current record of skills, languages, availability, citizenship and residency,
	and from here on the two are separate: editing the volunteer does not touch
	the application, and correcting the application does not touch the volunteer.
	`capabilities.seed()` fills blanks only, so a second application years later
	cannot overwrite what the society has been maintaining since.
	"""
	from vmmsx.volunteer.services import capabilities

	volunteer = volunteer_service.ensure(
		application.red_profile,
		# The application's anchor — the Serving Branch the applicant chose —
		# becomes the volunteer's, for a person who is not already a volunteer.
		# Somebody who is keeps the placement they have: relocating them is a
		# deliberate act with a doctype of its own (VMMS Branch Transfer), not a
		# side effect of a second application.
		home_geo_node=application.geo_node,
	)

	application.volunteer = volunteer.name
	_save(application)

	seeded = capabilities.seed(volunteer, application)

	# Re-read: `refresh` derives the status from the applications, and the link
	# it reads was written a line ago.
	settled = volunteer_service.refresh(volunteer.name)

	volunteer.reload()
	provisioned = hr.provision(volunteer)

	return {
		**status(application),
		"volunteer_status": settled["status"],
		"seeded": sorted(seeded),
		"hr": provisioned,
	}


# --- the lifecycle hook ---------------------------------------------------


def on_update(application, method=None) -> None:
	"""Re-evaluate acceptance after any save. Registered on the controller.

	This is how a decision recorded by the approval engine becomes a volunteer
	without the engine knowing volunteers exist. The flag stops the save inside
	`accept()` from re-entering.

	**The state change is read before acceptance runs and reported after it.**
	Both halves matter. Before, because `accept()` saves the application again
	and the "what did this save change" question would answer itself away.
	After, because the congratulations email carries the card, and the card only
	exists once `accept()` has created the volunteer record it describes.
	"""
	if application.flags.get(ACCEPTANCE_FLAG):
		return

	before = application.get_doc_before_save()
	previous = before.get(contract.STATE_FIELD) if before else None

	try_accept(application)

	_report(application, previous)


def _report(application, previous: str | None) -> None:
	"""Tell the applicant what just happened to their application.

	Everything about *when* to send is `lifecycle.notify`'s: it compares the two
	states and sends nothing when the save did not move the application. What
	this function owns is the subject — who the applicant is, and the card that
	goes with an approval.
	"""
	from vmmsx.notifications.services import lifecycle

	person = identity.read(application)

	lifecycle.notify(
		application,
		previous,
		contract.state(application),
		{
			"email": person.get("email"),
			"name": identity.display_name(application),
			"kind": _("volunteer"),
			"geo_path": _geo_path(application),
			"portal_path": "/portal/profile",
			"attachment": _card_attachment(application),
		},
	)


def _geo_path(application) -> str:
	"""Where this application is anchored, in the society's own words."""
	from onerc_core.geo.services import adapter

	return adapter.get_full_path(application.geo_node) if application.geo_node else ""


def _card_attachment(application) -> tuple[str, bytes] | None:
	"""The new volunteer's card, for the approval email. None in every other case.

	Only ever built for an application that has produced a volunteer record, so
	an acknowledgement and a rejection carry nothing. Never raises: a card that
	could not be rendered must not stop the person being told they were accepted,
	which is the more important half of the message.
	"""
	if not application.volunteer:
		return None

	try:
		from vmmsx.volunteer.services import card

		volunteer = frappe.get_doc(VOLUNTEER_DOCTYPE, application.volunteer)

		if not card.holds_card(volunteer):
			return None

		return card.pdf_filename(volunteer), card.pdf_for(volunteer)
	except Exception:
		frappe.log_error(
			title="vmmsx: could not build a volunteer card for the approval email",
			message=frappe.get_traceback(),
		)

		return None


def _save(application) -> None:
	"""Persist an acceptance-path change without re-entering `on_update`."""
	application.flags[ACCEPTANCE_FLAG] = True

	try:
		# `volunteer` is engine-written and read-only to users, and this path runs
		# as whichever approver made the decision — somebody with no permission on
		# the volunteer register, and no need for any. The permission that matters
		# was checked when the application was created and again by the engine's
		# person-gate before the decision was accepted.
		application.save(ignore_permissions=True)
	finally:
		application.flags[ACCEPTANCE_FLAG] = False


# --- withdrawal -----------------------------------------------------------


def withdraw(application, reason: str | None = None) -> dict:
	"""The applicant takes their application back, where the workflow allows it.

	Delegated whole to the engine, which owns whether withdrawal is permitted at
	all and whether this user is the applicant.
	"""
	engine.withdraw(application, reason=reason)

	return status(application)


# --- the DTO --------------------------------------------------------------


def status(application) -> dict:
	"""Where an application stands, as an explicit dict. Built field by field.

	Never the Document, and never the engine's status dict passed through: this
	one is assembled here so that a field added to the doctype does not silently
	become part of this app's API.
	"""
	from onerc_core.geo.services import adapter

	return {
		"name": application.name,
		"red_profile": application.red_profile,
		"geo_node": application.geo_node,
		"geo_path": adapter.get_full_path(application.geo_node) if application.geo_node else None,
		"applied_on": application.applied_on,
		"approval_state": contract.state(application),
		"is_approved": is_approved(application),
		"is_open": states.is_open(contract.state(application)),
		"volunteer": application.volunteer,
	}


def approval_dto(application, user: str | None = None) -> dict:
	"""The engine's own view of this approval — who may act, and what happened.

	A pass-through to `engine.status()`, which decides for itself how much of the
	approver list this user is entitled to see. Kept separate from `status()`
	above so that nothing in this module is tempted to re-derive any of it.
	"""
	return engine.status(application, user=user)


def verification_dto(volunteer) -> dict:
	"""How this volunteer came to be one, read from the application, right now.

	The volunteer record holds no approval state of its own and must not grow
	one: it would be a copy of the application's, wrong the first time somebody
	corrected a decision, and there would then be two answers to whether this
	person was verified. So the volunteer page asks the application every time it
	is opened, and stores nothing.

	**Which application.** Only an application the engine settled as Approved
	ever records the volunteer it produced — `accept()` writes that link — so
	every application found here is part of this person's approval trail by
	construction. Somebody who applied again years later has two, and the most
	recent is the current answer; the count is reported so the page can say there
	were others rather than silently showing one.

	**What it reads, and what it deliberately does not.** The application's own
	stored fields and its decision rows, through the engine's `contract`
	accessors. It does not call `engine.status()`, which resolves approvers
	through core and needs a configured workflow to do it: a page showing who
	verified somebody last year must not stop rendering because the society is
	midway through rewriting this year's workflow. Nothing here decides anything
	either — no state is compared, no stage is branched on, and `stage_label` is
	passed through as the display string the engine snapshotted.

	**Permission.** The caller has already been allowed to read the volunteer;
	`api/volunteer.py::_readable` checks it and core's geo scoping answers it. The
	application is deliberately not separately scopeable — its access rule is the
	engine's person-gate, which governs *deciding*, not reading a settled outcome
	— so there is no second check to make here. What comes back is built field by
	field below and discloses no more than the engine's own status DTO already
	returns to any reader.
	"""
	linked = frappe.get_all(
		APPLICATION_DOCTYPE,
		filters={"volunteer": volunteer.name},
		order_by="applied_on desc, creation desc",
		pluck="name",
	)

	if not linked:
		# Ordinary, not an error: a volunteer a society loaded directly has no
		# application behind them, and the page says so rather than implying an
		# approval that never happened.
		return {
			"volunteer": volunteer.name,
			"application": None,
			"application_count": 0,
			"approval_state": None,
			"applied_on": None,
			"geo_node": None,
			"decisions": [],
			"declared": None,
		}

	application = frappe.get_doc(APPLICATION_DOCTYPE, linked[0])

	return {
		"volunteer": volunteer.name,
		"application": application.name,
		"application_count": len(linked),
		"approval_state": contract.state(application),
		"applied_on": application.applied_on,
		"geo_node": application.geo_node,
		"decisions": [
			{
				"stage_label": row.stage_label,
				"approver": row.approver,
				"decision": row.decision,
				"decided_on": row.decided_on,
				"reason": row.reason,
			}
			for row in contract.decisions(application)
		],
		# A snapshot of what this person said about themselves on the day they
		# applied, and nothing more. It is **not** what they can do now. What a
		# volunteer can currently do is on the volunteer record, seeded from here
		# once at acceptance and edited there ever since; what they are certified
		# to do is VMMS Certification. The three must not be merged or reconciled
		# — the page labels this block as declared for exactly that reason.
		#
		# `motivation` and `prior_experience` are here and **only** here: they are
		# facts about the applying rather than about the volunteer, so editing them
		# later would be rewriting history rather than recording a change.
		# Identification is a live person fact read from Red Profile, not a
		# declaration stored on this application. `skills`, `languages` and `availability` appear
		# here as well as on the volunteer, and that is not duplication: this is
		# what was claimed, that is what is true, and a coordinator comparing the
		# two is the reason both are shown.
		"declared": {
			"skills": _selector_dto(application.skills, "skill", "VMMS Skill", "skill_name"),
			"languages": _selector_dto(application.languages, "language", "Language", "language_name"),
			"availability": _selector_dto(
				application.availability, "availability_slot", "VMMS Availability Slot", "slot_name"
			),
			"motivation": _selector_dto(
				application.motivation, "motivation", "VMMS Motivation", "motivation_name"
			),
			"prior_experience": application.prior_experience,
		},
	}


def decision_dto(application) -> dict:
	"""Everything a coordinator needs for a proper decision, structured.

	The whole point of Part 4: a coordinator opening this application sees a
	queryable decision picture, not a wall of free text. Built field by field —
	identity read live through `identity.py` and never duplicated onto this
	record, citizenship and residency (whichever half of the toggle applies),
	where this applicant would serve, what they declared in the society's own
	structured vocabularies, and the identification this application required to
	reach this screen at all.

	Nothing here is stored anywhere but the application and Red Profile
	themselves: correcting a Red Profile field corrects this view the next time
	it is read, and there is no copy anywhere to go out of date.
	"""
	from onerc_core.geo.services import adapter

	person = identity.read(application)

	if person.get("residency_type") == "Abroad":
		residency = {
			"residency_type": "Abroad",
			"home_geo_node": None,
			"home_geo_path": None,
			"country_of_residence": person.get("country_of_residence"),
			"residence_address": person.get("residence_address"),
		}
	else:
		home = person.get("home_geo_node")
		residency = {
			"residency_type": person.get("residency_type"),
			"home_geo_node": home,
			"home_geo_path": adapter.get_full_path(home) if home else None,
			"country_of_residence": None,
			"residence_address": None,
		}

	identifications = _identifications_dto(application)

	return {
		"name": application.name,
		"red_profile": application.red_profile,
		"full_name": identity.display_name(application),
		"email": person.get("email"),
		"phone": person.get("phone"),
		# The face, and the two facts a volunteering office is asked for
		# constantly. All three are already in `identity._READABLE` and were
		# already being read on the line above — they were simply never put in
		# the payload, so the approver's screen showed initials in a circle for
		# an applicant who has uploaded a photograph. Read live from Red Profile
		# like everything else here; nothing is copied onto the application.
		"profile_photo": person.get("profile_photo"),
		"gender": person.get("gender"),
		"date_of_birth": person.get("date_of_birth"),
		"preferred_language": person.get("preferred_language"),
		"applied_on": application.applied_on,
		"country_of_citizenship": person.get("country_of_citizenship"),
		**residency,
		"geo_node": application.geo_node,
		"geo_path": adapter.get_full_path(application.geo_node) if application.geo_node else None,
		"skills": _selector_dto(application.skills, "skill", "VMMS Skill", "skill_name"),
		"languages": _selector_dto(application.languages, "language", "Language", "language_name"),
		"availability": _selector_dto(
			application.availability, "availability_slot", "VMMS Availability Slot", "slot_name"
		),
		"motivation": _selector_dto(
			application.motivation, "motivation", "VMMS Motivation", "motivation_name"
		),
		"prior_experience": application.prior_experience,
		"identification": identifications[0] if identifications else None,
		"identifications": identifications,
		# What this society asked for beyond the standard form, read off the
		# application's own snapshots rather than the live question list, so an
		# application decided last year still shows the question it was asked.
		"answers": questions.answers_of(application),
	}


def _selector_dto(rows, link_field: str, doctype: str, name_field: str) -> list[dict]:
	"""A Table MultiSelect's rows, resolved to {key, label} pairs.

	Delegated to `capabilities.selector_dto`, which is the one implementation.
	The volunteer's own selectors and the application's are the same three
	vocabularies read the same way, and two copies of the resolution would be
	two chances for the register and the application to label a skill
	differently on the same screen.
	"""
	from vmmsx.volunteer.services import capabilities

	return capabilities.selector_dto(rows, link_field, doctype, name_field)


def _identifications_dto(application) -> list[dict]:
	"""The applicant's current Red Profile identifications, primary first."""
	return identity.identifications(application)


# --- housekeeping ---------------------------------------------------------


def applied_on_or_today(application):
	"""The application date, defaulting to today for one made programmatically."""
	return getdate(application.applied_on or today())


def assert_applicant(application) -> None:
	"""An application always belongs to somebody core already knows."""
	if application.red_profile and frappe.db.exists("Red Profile", application.red_profile):
		return

	frappe.throw(
		_("An application is always made by a person core already knows. Link a Red Profile."),
		frappe.MandatoryError,
		title=_("No Red Profile"),
	)
