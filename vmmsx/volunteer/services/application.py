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
from frappe.utils import cint, getdate, today

from vmmsx.approvals import states
from vmmsx.approvals.services import contract, engine
from vmmsx.registration.services import declarations, questions
from vmmsx.registration.services import society as registration_society
from vmmsx.volunteer.services import hr, identity
from vmmsx.volunteer.services import volunteer as volunteer_service

APPLICATION_DOCTYPE = "VMMS Volunteer Application"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"

IDENTIFICATION_TYPE_DOCTYPE = "Identification Type"

# The three vmmsx-owned Custom Fields on core's `Identification Type` that say
# what a society insists on seeing. Installed by
# `patches/install_identity_document_rules.py`; named here so the reader and the
# patch agree on the spelling and nothing else in this module hardcodes one.
REQUIRED_DOCUMENT_FIELD = "vmms_is_required_for_volunteers"
DOCUMENT_ATTACHMENT_FIELD = "vmms_requires_attachment"
DOCUMENT_MINIMUM_AGE_FIELD = "vmms_minimum_age"

# The vmmsx-owned Custom Field on core's `Red Profile` that holds whether
# somebody has a disability. Installed by
# `patches/install_disability_fields.py`, which records why it lives on the
# spine rather than on the volunteer record.
DISABILITY_FIELD = "vmms_disability_status"

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

	**What is deliberately not here.** Emergency contacts and a minor's guardian
	consent are required to *approve*, not to submit — see `assert_approvable`.
	An applicant should be able to send their application in and have the branch
	chase the missing consent form, rather than being turned away at the door by
	a requirement somebody else has to satisfy.
	"""
	_assert_country_of_citizenship(application)
	_assert_identification(application)
	_assert_identity_documents(application)
	_assert_date_of_birth(application)
	_assert_disability_answered(application)
	_assert_residency_complete(application)
	questions.assert_answered(application)
	declarations.assert_accepted(application)


def _assert_country_of_citizenship(application) -> None:
	"""A volunteer application needs the person's country of citizenship."""
	if _profile_value(application, "country_of_citizenship"):
		return

	frappe.throw(
		_("Add your Country of Citizenship to your profile before submitting."),
		frappe.MandatoryError,
		title=_("Missing Citizenship"),
	)


def _assert_disability_answered(application) -> None:
	"""A volunteer application needs an answer about disability. Any of the three.

	**Answered, not disclosed.** "Prefer not to say" satisfies this, and that is
	the whole design: a society running an inclusive programme has to know what
	adjustments to offer, and the way to ask without coercing anybody is to make
	*answering* required and disclosure optional. Blank means nobody was asked;
	declining is a different state and the field holds it.

	**Silent on a site that has not installed the field.** These are Custom
	Fields, and a bench between syncing this module and running its patch has the
	doctype and not the column — the same guard `_required_document_types` makes,
	for the same reason. A society is not refusing every application because a
	migration has not finished.
	"""
	if not frappe.get_meta("Red Profile").has_field(DISABILITY_FIELD):
		return

	if _profile_value(application, DISABILITY_FIELD):
		return

	frappe.throw(
		_(
			"Answer the disability question on your profile before submitting. You may choose"
			" not to say."
		),
		frappe.MandatoryError,
		title=_("Question Not Answered"),
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


def _assert_identity_documents(application) -> None:
	"""Every document this society insists on, produced and where required copied.

	The floor above is "some identification". This is the society's own answer on
	top of it, read from the `vmms_`-prefixed Custom Fields on core's
	`Identification Type` — so a branch that starts requiring a birth certificate
	ticks a box on a record it already has, and no source file here names a
	document.

	Three ways this is deliberately quiet:

	1. **A society that has ticked nothing is unaffected.** No required types,
	   no requirement — the same "empty narrows nothing" direction every other
	   society setting takes.
	2. **A required document below its own minimum age is not insisted on.** A
	   national ID card that is not issued until sixteen cannot be a condition
	   of a fourteen-year-old volunteering, and a society that has said so on the
	   type should not have to maintain a second list of exceptions.
	3. **It does nothing at all before the rules are installed.** A site
	   mid-migrate has the doctype and not yet the Custom Fields, and a filter on
	   a column that is not there would throw where the honest answer is that
	   this society has not configured anything yet.
	"""
	required = _required_document_types()

	if not required:
		return

	age = _age_of(application)
	# `identity.identifications` already drops any row missing a type or a
	# number, so what is here is what the applicant has actually produced.
	held = {row["id_type"]: row for row in identity.identifications(application)}

	for document in required:
		minimum = cint(document.get(DOCUMENT_MINIMUM_AGE_FIELD))

		if minimum and age is not None and age < minimum:
			continue

		row = held.get(document["name"])

		if not row:
			frappe.throw(
				_(
					"This society asks every volunteer for {0}. Add it to your profile before submitting."
				).format(frappe.bold(document["label"])),
				frappe.MandatoryError,
				title=_("Missing Identification"),
			)

		if document.get(DOCUMENT_ATTACHMENT_FIELD) and not row.get("attachment"):
			frappe.throw(
				_(
					"This society asks for a copy of your {0}, not only the number. Upload one to"
					" your profile before submitting."
				).format(frappe.bold(document["label"])),
				frappe.MandatoryError,
				title=_("Missing Document Copy"),
			)


def _required_document_types() -> list[dict]:
	"""The active identification types this society insists a volunteer produces.

	Empty — and cheap — on a site whose `Identification Type` does not yet carry
	the vmmsx rules, which is every site between syncing this module and running
	the patch that installs them.
	"""
	meta = frappe.get_meta(IDENTIFICATION_TYPE_DOCTYPE)

	if not meta.has_field(REQUIRED_DOCUMENT_FIELD):
		return []

	rows = frappe.get_all(
		IDENTIFICATION_TYPE_DOCTYPE,
		filters={"is_active": 1, REQUIRED_DOCUMENT_FIELD: 1},
		fields=[
			"name",
			"identification_type_name",
			DOCUMENT_ATTACHMENT_FIELD,
			DOCUMENT_MINIMUM_AGE_FIELD,
		],
		order_by="identification_type_name asc",
	)

	return [
		{
			"name": row["name"],
			# The society's own word for it, falling back to the key so an
			# unnamed type still produces a message somebody can act on.
			"label": row.get("identification_type_name") or row["name"],
			DOCUMENT_ATTACHMENT_FIELD: row.get(DOCUMENT_ATTACHMENT_FIELD),
			DOCUMENT_MINIMUM_AGE_FIELD: row.get(DOCUMENT_MINIMUM_AGE_FIELD),
		}
		for row in rows
	]


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


# --- age, and the guardian rules that hang off it --------------------------
#
# Age is **derived, never stored**. A number written down is wrong the following
# year, and an application carrying "17" that was approved in 2024 tells nobody
# anything useful in 2026. `is_minor` on the doctype is a read-only convenience
# for the desk form's `depends_on`, recomputed on every save from the two things
# that actually decide it: the person's date of birth on their Red Profile, and
# the age this society counts as adult.


def _age_of(application, reference=None) -> int | None:
	"""The applicant's age in whole years, or None when nobody has said.

	Read from Red Profile, which is where the date of birth lives — with the
	intake buffer as a fallback for the one moment it has not landed there yet,
	the same pair `_assert_date_of_birth` reads.

	None is a real answer and not an error: a draft that has not been asked for a
	date of birth yet has no age, and every caller here treats that as "no rule
	fires" rather than guessing one.
	"""
	born = application.get("applicant_date_of_birth") or _profile_value(application, "date_of_birth")

	if not born:
		return None

	born = getdate(born)
	on = getdate(reference or today())

	# The standard whole-years calculation: subtract the years, then take one
	# back if this year's birthday has not happened yet.
	return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


def is_minor(application, reference=None) -> bool:
	"""Is this applicant below the age this society treats as adult?

	False whenever the society has not configured an age of majority, and false
	when nobody has given a date of birth. Both are "no rule fires": an app that
	guessed eighteen would be inventing a law, and one that treated an unknown
	date as a child would block every draft.

	**Asked as of today rather than as of the application date**, and the
	difference is the whole point. The rule this serves is "a minor's
	application needs a verified guardian consent before it is approved" — so
	the question is whether the person being approved is a minor now, not
	whether they were one when they filled in the form. Somebody who applied at
	seventeen and turned eighteen while their application sat in a queue does not
	need their parent's permission, and asking for it would be the system failing
	to notice a birthday.

	What the birthday does *not* do is erase anything: the guardian consent rows
	already recorded stay on the application, because they are the record of what
	happened, and only the gate stops applying.
	"""
	threshold = registration_society.minor_age()

	if not threshold:
		return False

	age = _age_of(application, reference)

	return age is not None and age < threshold


# --- readiness to be approved ----------------------------------------------


def assert_approvable(application) -> None:
	"""Refuse an approval the society is not in a position to make.

	**Separate from `assert_ready` on purpose.** Those are the applicant's own
	obligations, checked while they are still the person who can fix them. These
	two are the branch's: an emergency contact is something a coordinator can
	take over the phone, and a guardian's consent is something somebody at the
	society has to go and verify. Blocking *submission* on either would turn away
	an application over work that had not started yet; blocking *approval* is the
	rule actually wanted — nobody is enrolled as a volunteer until the society
	knows who to call and, for a child, has satisfied itself that a parent
	agreed.

	Called from the controller's `validate` on the save that moves the
	application into Approved, so it runs whichever door the decision came
	through — the API gate, the desk, or a service — and the whole decision rolls
	back with a sentence the approver can act on.
	"""
	_assert_emergency_contact(application)
	_assert_guardian_consent(application)


def _assert_emergency_contact(application) -> None:
	"""At least one contact the applicant has actually permitted us to call.

	The permission is counted, not merely the row. A number on file that the
	applicant has told us not to use is not an emergency contact — it is a number
	we may not call — and treating the two as the same would mean the register
	answering "yes" to a question it cannot answer.
	"""
	contacts = [row for row in application.get("emergency_contacts") or [] if row.may_contact_in_emergency]

	if contacts:
		return

	frappe.throw(
		_(
			"This application has no emergency contact we may call. Add one, with the applicant's"
			" permission to contact them, before approving it."
		),
		frappe.ValidationError,
		title=_("No Emergency Contact"),
	)


def _assert_guardian_consent(application) -> None:
	"""A minor needs a guardian's consent, and somebody has to have checked it.

	Two conditions and they are not the same one twice. `consent_given` is what
	the guardian said; `is_verified` is what a reviewer at the society did about
	it. An application carrying a claimed consent nobody has looked at is the
	ordinary state of a freshly submitted application, and it is exactly the
	state this refuses to approve.

	A no-op for an adult, and a no-op for every applicant at a society that has
	not configured an age of majority.
	"""
	if not is_minor(application):
		return

	verified = [
		row for row in application.get("guardian_consents") or [] if row.consent_given and row.is_verified
	]

	if verified:
		return

	frappe.throw(
		_(
			"This applicant is under {0}. Their application cannot be approved until a parent or"
			" guardian's consent has been recorded and a reviewer has marked it verified."
		).format(frappe.bold(registration_society.minor_age())),
		frappe.ValidationError,
		title=_("Guardian Consent Not Verified"),
	)


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

	**A guardian is carried forward for the same reason and at the same moment.**
	The consent rows on the application are part of the decision and stay there;
	what is copied out is a standing record of who a young volunteer's parent is,
	because everything a society writes to them from here — an invitation, a task,
	a change of plan — happens long after this application is closed and must not
	be a reason to reopen it. See `registration/services/guardian.adopt`.
	"""
	from vmmsx.registration.services import guardian
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

	# After the volunteer exists and before the DTO is built, so a caller can
	# report it. Never raises — see `guardian.adopt`: a guardian record that
	# could not be written must not roll back somebody's acceptance.
	guardians = guardian.adopt(application)

	return {
		**status(application),
		"volunteer_status": settled["status"],
		"seeded": sorted(seeded),
		"hr": provisioned,
		"guardians": guardians,
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
	this function owns is the subject — who the applicant is, the card that goes
	with an approval, and who else is copied.
	"""
	from vmmsx.notifications.services import lifecycle
	from vmmsx.registration.services import guardian

	person = identity.read(application)

	lifecycle.notify(
		application,
		previous,
		contract.state(application),
		{
			"email": person.get("email"),
			# The number the society already holds. A text is the nudge to go and
			# read the letter, never the letter — see `lifecycle._sms_for`.
			"phone": person.get("phone"),
			"name": identity.display_name(application),
			"kind": _("volunteer"),
			"geo_path": _geo_path(application),
			"portal_path": "/portal/profile",
			"attachment": _card_attachment(application),
			# A young applicant's parent, copied on the four letters that decide
			# their application. Asked of the *person* rather than of this
			# application's own `is_minor`, and asked now rather than when the
			# form was filled in — see `guardian.emails_for`.
			"cc": guardian.emails_for(application.red_profile),
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
		# What the applicant answered about disability, so the branch arranging
		# their first shift knows to ask about adjustments rather than finding
		# out on the day. Read live from Red Profile like everything above it.
		# `None` on a site whose Custom Fields have not been installed yet, which
		# reads the same as unanswered.
		"disability_status": person.get(DISABILITY_FIELD),
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
		# The three things an approver has to be able to check before approving,
		# because `assert_approvable` will refuse the decision over two of them.
		# A screen that hid them would leave somebody pressing Approve and being
		# told no, with no way to see what was missing.
		"emergency_contacts": _emergency_contacts_dto(application),
		"is_minor": is_minor(application),
		"guardian_consents": _guardian_consents_dto(application),
		# Read off the acceptance rows' own snapshots, never the live
		# declarations: what matters is the wording this applicant agreed to.
		"declarations": declarations.accepted_of(application),
	}


def _emergency_contacts_dto(application) -> list[dict]:
	"""Who this applicant said to call, built field by field."""
	return [
		{
			"contact_name": row.contact_name,
			"relationship": row.relationship,
			"primary_phone": row.primary_phone,
			"alternative_phone": row.alternative_phone,
			"may_contact_in_emergency": bool(row.may_contact_in_emergency),
		}
		for row in application.get("emergency_contacts") or []
	]


def _guardian_consents_dto(application) -> list[dict]:
	"""A minor's guardian consents, including who verified one and when.

	`verified_by` and `verified_on` travel with the row because the approver's
	question is not only "is there consent" but "has anybody checked it" — and an
	unverified consent is precisely what stops the approval going through.
	"""
	return [
		{
			"guardian_name": row.guardian_name,
			"relationship": row.relationship,
			"phone": row.phone,
			"email": row.email,
			"consent_given": bool(row.consent_given),
			"consent_date": row.consent_date,
			"verification_method": row.verification_method,
			"consent_evidence": row.consent_evidence,
			"is_verified": bool(row.is_verified),
			"verified_by": row.verified_by,
			"verified_on": row.verified_on,
		}
		for row in application.get("guardian_consents") or []
	]


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
