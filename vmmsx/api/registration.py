# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Registering yourself, for callers that are not a Web Form.

`registration/services/intake.py` resolves a person's Red Profile from their
login and creates one if the society has never met them. The two governed
controllers call it from `before_insert`, which is the only window a Web Form
gives them. A single-page frontend has no such window: it posts to an endpoint,
and the browser has no business inventing an identity on the way.

**Every endpoint here is possessive, and none of them takes a person.** The
profile they act on is the session's, always — the shape `my_memberships`,
`my_volunteer` and `my_queue` already use. A `claim_profile(user)` would be an
endpoint for minting identity for anybody, wearing a possessive name, and a
`register(red_profile=...)` would be one for enrolling anybody as anybody.

**The email is never a parameter.** It is the login, for the reason the
self-service layer records: a form value would let anybody claim anybody.

**Registering and correcting are two different doors.** `claim_my_profile` and
the two `register_as_*` endpoints are *additive*: `intake._enrich` fills in what
core does not know and never overwrites what it does, so filling in a form a
second time cannot quietly rewrite the society's record. `update_my_profile` is
the other half that rule always implied — intake's own docstring says "a person
correcting their own name does it on their profile" — and it is the endpoint
that lets them. It overwrites, deliberately, on the one profile carrying the
caller's own login, and it still cannot touch the email.

**The two registration endpoints are not `api/volunteer.py::apply_to_volunteer`
or `api/member.py::apply_for_membership`, and must not become them.** Those two
are the *clerk's* door: they name a `red_profile`, so a coordinator can enter a
paper application on somebody else's behalf, and they check `create` permission
because a clerk is somebody a society has granted something to. A person
registering themselves is the opposite case in both halves — they name nobody
but themselves, and they hold nothing at all, because the very first thing they
ever do here is this. Keeping the two doors apart is what lets the self-service
one be elevated without that elevation reaching a caller who can name a victim.
"""

import frappe
from frappe import _
from frappe.utils import cstr, getdate

from vmmsx.registration.services import declarations, evidence, intake, questions

PROFILE_DOCTYPE = "Red Profile"
APPLICATION_DOCTYPE = "VMMS Volunteer Application"
MEMBERSHIP_DOCTYPE = "VMMS Membership"

# The two self-registrations a person can have, and the wizard path that files
# each. They are independent: registering as a volunteer says nothing about
# whether somebody may also register as a member, which is what every check in
# this module and in the engine already assumed one doctype at a time.
REGISTRATION_PATHS = (
	("volunteer", APPLICATION_DOCTYPE),
	("member", MEMBERSHIP_DOCTYPE),
)

# What a person may correct about themselves, and the closed list `update_my_
# profile` writes. `email` and `user` are absent and must stay absent: they are
# the binding between a login and a person, and somebody who could rewrite
# either could point their own profile at somebody else's identity.
SELF_EDITABLE_FIELDS = (
	"first_name",
	"last_name",
	"phone",
	"gender",
	"date_of_birth",
	"preferred_language",
	"country_of_citizenship",
	"citizenship_status",
	"residency_type",
	"home_geo_node",
	"country_of_residence",
	"residence_address",
	# A photograph is a fact about the person, like the six above it, and it goes
	# on the card they carry. What a *branch* decided — serving branch, status,
	# certifications — is not here and must not be, which is the whole of what
	# this list separates.
	"profile_photo",
)

# Fields holding a file URL rather than a value. Checked against the framework's
# own upload paths before they reach core: a person uploads through Frappe's file
# handler and sends back the URL it returned, and anything that does not look
# like one is refused. Otherwise this endpoint would be a way to point every
# screen showing somebody's portrait — including a printed card — at an
# arbitrary server. Same rule `questions._file` applies to an uploaded answer and
# `links.py` applies to a content block's href.
FILE_FIELDS = ("profile_photo",)

UPLOAD_PREFIXES = evidence.UPLOAD_PREFIXES

# What an applicant may say about an emergency contact. A closed list, because
# these arrive as loose dicts from a browser and `document.update()` on a child
# row would take whatever was sent.
EMERGENCY_CONTACT_FIELDS = (
	"contact_name",
	"relationship",
	"primary_phone",
	"alternative_phone",
	"may_contact_in_emergency",
)

# What an applicant may say about their guardian's consent — and the three
# fields conspicuously absent from it.
#
# `is_verified`, `verified_by` and `verified_on` are the *society's* record that
# somebody at the branch checked this consent, and they are the whole of what
# stands between a typed-in parent's name and an approved minor. An applicant
# who could set them could verify their own guardian's consent, which is the one
# thing this feature exists to prevent. They are set on the desk, by the
# reviewer, and stamped by `VMMS Guardian Consent.validate`.
#
# **A consequence worth stating: re-saving a draft clears a verification.** This
# endpoint replaces the table wholesale, as it does for skills and languages, so
# an applicant who edits a returned application sends guardian rows with no
# verification on them and the reviewer's tick goes. That is the right
# direction: a verification attaches to the guardian details that were verified,
# and details that have just been resubmitted have not been checked. Failing
# closed here costs a reviewer one tick; failing open would approve a minor on a
# consent nobody looked at.
GUARDIAN_CONSENT_FIELDS = (
	"guardian_name",
	"relationship",
	"phone",
	"email",
	"consent_given",
	"consent_date",
	"verification_method",
	"consent_evidence",
)

# Rows carrying a file URL, which is a claim until it is checked.
GUARDIAN_CONSENT_FILE_FIELDS = ("consent_evidence",)

# Core refuses a profile with either of these empty, so an edit that blanks one
# is refused here with a sentence rather than at the ORM with a stack trace.
NAME_FIELDS = ("first_name", "last_name")


def _assert_signed_in() -> str:
	"""Everything here belongs to somebody. Guest is refused before anything else."""
	user = frappe.session.user

	if not user or user == "Guest":
		frappe.throw(_("Sign in before registering."), frappe.PermissionError, title=_("Not Signed In"))

	return user


def _profile_dto(profile: str) -> dict:
	"""What the frontend needs about a person, and nothing more.

	Built field by field. The Red Profile is core's identity spine and carries
	more than a registration form has any reason to see.
	"""
	person = frappe.db.get_value(
		PROFILE_DOCTYPE,
		profile,
		[
			"name",
			"first_name",
			"last_name",
			"email",
			"phone",
			"gender",
			"date_of_birth",
			"preferred_language",
			"profile_photo",
			"country_of_citizenship",
			"citizenship_status",
			"residency_type",
			"home_geo_node",
			"country_of_residence",
			"residence_address",
		],
		as_dict=True,
	)

	identifications = frappe.get_all(
		"Red Profile Identification",
		filters={
			"parent": profile,
			"parenttype": PROFILE_DOCTYPE,
			"parentfield": "identifications",
		},
		fields=["id_type", "id_number", "attachment", "is_primary"],
		order_by="is_primary desc, idx asc",
	)

	return {
		"red_profile": person.name,
		"first_name": person.first_name,
		"last_name": person.last_name,
		"full_name": " ".join(filter(None, [person.first_name, person.last_name])),
		"email": person.email,
		"phone": person.phone,
		"gender": person.gender,
		"date_of_birth": person.date_of_birth,
		"preferred_language": person.preferred_language,
		"country_of_citizenship": person.country_of_citizenship,
		"citizenship_status": person.citizenship_status,
		"residency_type": person.residency_type,
		# Served because `update_my_profile` already accepts it: a form that can
		# set a photograph and cannot read back the one already on file would show
		# an empty control to somebody who has had a portrait on their card for a
		# year, and the obvious way to fix that is to upload it again.
		"profile_photo": person.profile_photo,
		# Residence is person-owned profile data. A later registration reads it
		# back so the applicant can confirm or correct it without re-entering it.
		"home_geo_node": person.home_geo_node,
		"country_of_residence": person.country_of_residence,
		"residence_address": person.residence_address,
		"identifications": [
			{
				"id_type": row.id_type,
				"id_number": row.id_number,
				"attachment": row.attachment,
				"is_primary": bool(row.is_primary),
			}
			for row in identifications
		],
	}


@frappe.whitelist()
def my_profile() -> dict | None:
	"""The caller's Red Profile if they have one. Creates nothing.

	None for somebody core has never met, which is an ordinary state for a
	visitor who has just signed up and not yet registered for anything. The
	wizard uses this to prefill the identity step and the portal's profile screen
	to fill its edit form; `claim_my_profile` is the call that actually brings a
	profile into being, and `update_my_profile` the one that corrects it.
	"""
	user = frappe.session.user

	if not user or user == "Guest":
		return None

	profile = frappe.db.get_value(PROFILE_DOCTYPE, {"user": user}, "name")

	return _profile_dto(profile) if profile else None


@frappe.whitelist()
def identity_options() -> dict:
	"""The vocabulary the identity step of a registration form has to draw.

	One list today, and it lives here rather than beside the volunteer
	application's vocabularies because gender is a **Red Profile** field: both
	registration paths ask it, and neither of them owns it. The volunteer
	application's own vocabularies are `api/volunteer.py::application_options`.

	Not hardcoded in the frontend for the reason nothing else is: a society
	configures its own Gender rows, and a list typed into a browser bundle would
	be a second answer that drifts from the one the Link field enforces.
	"""
	return {"genders": [row["name"] for row in frappe.get_all("Gender", order_by="name asc")]}


@frappe.whitelist()
def claim_my_profile(
	first_name: str | None = None,
	last_name: str | None = None,
	phone: str | None = None,
	gender: str | None = None,
	date_of_birth: str | None = None,
) -> dict:
	"""Resolve or create the caller's Red Profile, and return it.

	Idempotent, and it has to be: a wizard that a person backs out of and starts
	again must not leave two profiles behind, and `intake.for_user` guarantees it
	will not.

	The values are **additive only**. `intake._enrich` fills in what core does
	not know yet and never overwrites what it does, so somebody re-registering
	cannot quietly rewrite the name the society has on file by typing a
	different one into a form. That is registration's rule, not a new one here.
	"""
	user = _assert_signed_in()

	values = {
		"first_name": first_name,
		"last_name": last_name,
		"phone": phone,
		"gender": gender,
		"date_of_birth": date_of_birth,
	}

	profile = intake.for_user(user, {key: value for key, value in values.items() if value})

	if not profile:
		# `for_user` returns None only when the session names no User row at
		# all, which should be impossible behind a login check. Refusing loudly
		# beats returning a dict with no profile in it.
		frappe.throw(
			_("Your account could not be matched to a person record."),
			frappe.ValidationError,
			title=_("No Profile"),
		)

	return _profile_dto(profile)


@frappe.whitelist()
def update_my_profile(
	first_name: str | None = None,
	last_name: str | None = None,
	phone: str | None = None,
	gender: str | None = None,
	date_of_birth: str | None = None,
	preferred_language: str | None = None,
	profile_photo: str | None = None,
	country_of_citizenship: str | None = None,
	citizenship_status: str | None = None,
	residency_type: str | None = None,
	home_geo_node: str | None = None,
	country_of_residence: str | None = None,
	residence_address: str | None = None,
	id_type: str | None = None,
	id_number: str | None = None,
) -> dict:
	"""Correct the caller's own Red Profile. The details are theirs.

	**Why this overwrites when registration does not.** `intake._enrich` refuses
	to contradict core because a *registration form* is a claim made in passing:
	somebody joining as a member in August should not silently rewrite the name
	their volunteer application put on file in March. This endpoint is the
	opposite act. It is a person looking at what the society holds about them and
	saying "that is wrong" — the correction intake's own docstring points at — so
	it says so in its name and does exactly what it says.

	**It still cannot touch the email.** `SELF_EDITABLE_FIELDS` is a closed list
	and `email` is not in it, because the email is the login: an endpoint that
	could change it could walk this profile onto another person's account. The
	same goes for `user`. Changing an email address is a Frappe account change,
	and it belongs where the site already handles it.

	**Possessive, like everything else in this file.** No parameter names a
	person. The profile is resolved from `frappe.session.user` through the unique
	column core maintains, so there is no argument to tamper with.

	`None` means "leave this alone", which is what makes a caller that sends
	three fields safe. An empty string clears an optional field — somebody
	withdrawing a phone number, a gender they would rather not state, or a
	photograph they no longer want on their card — but a name may not be emptied,
	because core refuses a profile without one.

	**`profile_photo` is a file URL and is checked as one.** The browser uploads
	through the framework's own handler, which has already decided what this
	person may store and how large it may be, and sends back the URL it was
	given. Anything that is not one of this site's own upload paths is refused:
	the value ends up on a printed card and on every screen showing this person,
	so an endpoint that accepted an arbitrary URL would put somebody else's
	server there. See `FILE_FIELDS`.
	"""
	user = _assert_signed_in()

	profile = frappe.db.get_value(PROFILE_DOCTYPE, {"user": user}, "name")

	if not profile:
		frappe.throw(
			_("You do not have a profile with the society yet. Register first."),
			frappe.ValidationError,
			title=_("No Profile"),
		)

	supplied = {
		"first_name": first_name,
		"last_name": last_name,
		"phone": phone,
		"gender": gender,
		"date_of_birth": date_of_birth,
		"preferred_language": preferred_language,
		"profile_photo": profile_photo,
		"country_of_citizenship": country_of_citizenship,
		"citizenship_status": citizenship_status,
		"residency_type": residency_type,
		"home_geo_node": home_geo_node,
		"country_of_residence": country_of_residence,
		"residence_address": residence_address,
	}

	_write_profile(profile, supplied, id_type=id_type, id_number=id_number)

	return _profile_dto(profile)


def _write_profile(
	profile: str,
	supplied: dict,
	*,
	id_type: str | None = None,
	id_number: str | None = None,
) -> None:
	"""Write person-owned registration facts to one already-resolved profile."""

	changes = {
		field: value
		for field, value in supplied.items()
		if field in SELF_EDITABLE_FIELDS and value is not None
	}

	meta = frappe.get_meta(PROFILE_DOCTYPE)

	for field, value in list(changes.items()):
		if str(value).strip():
			# Checked before it is stored rather than sanitised on the way out:
			# the value reaches a printed card and every screen showing this
			# person, so the wrong one must never land at all.
			if field in FILE_FIELDS and not str(value).strip().startswith(UPLOAD_PREFIXES):
				frappe.throw(
					_("{0} was not uploaded to this site.").format(frappe.bold(_(meta.get_label(field)))),
					frappe.ValidationError,
					title=_("File Not Recognised"),
				)

			continue

		if field in NAME_FIELDS:
			frappe.throw(
				_("{0} cannot be left empty.").format(frappe.bold(_(meta.get_label(field)))),
				frappe.ValidationError,
				title=_("Name Needed"),
			)

		# Blank means cleared, and it has to reach the field as None: an empty
		# string on a Date is not a date, and a Link would store one.
		changes[field] = None

	identification_supplied = id_type is not None or id_number is not None

	if identification_supplied and not (str(id_type or "").strip() and str(id_number or "").strip()):
		frappe.throw(
			_("Identification Type and Identification Number must be provided together."),
			frappe.MandatoryError,
			title=_("Incomplete Identification"),
		)

	if changes or identification_supplied:
		# Elevated, and narrowly. A volunteer or member holds no write permission
		# on Red Profile and should not — it is core's spine and it carries every
		# person the society knows. What is written here is one row, resolved from
		# the caller's own login, from values about themselves, through the
		# document's own `save()` so core's validation still runs: the society's
		# configured phone pattern, the recomposed full name, and the guard that
		# keeps the affiliation index service-written. Nothing skips a rule; the
		# only thing skipped is a role check the subject of the record could not
		# hold without being given the whole register.
		with intake.as_system():
			document = frappe.get_doc(PROFILE_DOCTYPE, profile)
			document.update(changes)

			if identification_supplied:
				primary = next((row for row in document.identifications if row.is_primary), None)

				if primary is None and document.identifications:
					primary = document.identifications[0]
					primary.is_primary = 1

				if primary is None:
					document.append(
						"identifications",
						{
							"id_type": str(id_type).strip(),
							"id_number": str(id_number).strip(),
							"is_primary": 1,
						},
					)
				else:
					primary.id_type = str(id_type).strip()
					primary.id_number = str(id_number).strip()

			document.save()

		frappe.clear_document_cache(PROFILE_DOCTYPE, profile)


# --- registering yourself -------------------------------------------------


def _intake_fields(
	first_name: str | None,
	last_name: str | None,
	phone: str | None,
	gender: str | None,
	date_of_birth: str | None,
) -> dict:
	"""The transient identity buffer, filled exactly as a Web Form fills it.

	These are not stored. `intake.claim_profile` reads and blanks them in
	`before_insert`, and `validate()` blanks them again, so the saved record
	carries no name, phone or date of birth however it was created. Passing them
	here rather than calling `claim_my_profile` first is what makes registering
	one call: there is no window in which a profile exists and the registration
	it was created for does not.
	"""
	return {
		"applicant_first_name": first_name,
		"applicant_last_name": last_name,
		"applicant_phone": phone,
		"applicant_gender": gender,
		"applicant_date_of_birth": date_of_birth,
	}


def _adopt_photo(profile_photo: str | None) -> None:
	"""Put the portrait a registrant chose onto the profile the registration made.

	**Why this is not a second call from the browser.** It was one, and it is the
	half of a registration that could silently not happen: the wizard uploaded the
	file, registered, and then posted the photograph on its own afterwards, with
	the failure deliberately swallowed so a lost portrait could not cost somebody
	the application that had already succeeded. That is the right instinct and the
	wrong shape — anything between the two calls, a reload or a closed tab, left a
	person registered with the picture they had chosen nowhere on file, and the
	only symptom was an empty control the next time they registered for anything.
	Carried with the registration, there is no window for it to fall into.

	**Additive, like everything else a registration writes.** `intake._enrich`
	will not contradict what core already holds, and neither will this: a profile
	that already carries a portrait keeps it. Replacing one is a *correction*, and
	`update_my_profile` is the door named for that.

	The URL is checked the way `update_my_profile` checks it, because it reaches
	the same places — a printed card, and every screen showing this person.
	"""
	if not profile_photo or not str(profile_photo).strip():
		return

	url = str(profile_photo).strip()

	if not url.startswith(UPLOAD_PREFIXES):
		frappe.throw(
			_("Your photograph was not uploaded to this site."),
			frappe.ValidationError,
			title=_("File Not Recognised"),
		)

	profile = frappe.db.get_value(PROFILE_DOCTYPE, {"user": frappe.session.user}, "name")

	if not profile or frappe.db.get_value(PROFILE_DOCTYPE, profile, "profile_photo"):
		return

	with intake.as_system():
		document = frappe.get_doc(PROFILE_DOCTYPE, profile)
		document.profile_photo = url
		document.save()

	frappe.clear_document_cache(PROFILE_DOCTYPE, profile)


def _open_registration(doctype: str) -> str | None:
	"""The caller's own undecided registration of this kind, or None.

	One implementation behind both the guard below and the endpoint the wizard
	reads, so the screen that says "you have already applied" and the server that
	refuses a second application can never disagree about whether you have.

	The caller is the session. Looked up rather than resolved through
	`intake.for_user`, which *creates* a profile when it finds none — right for a
	registration and wrong for a check, which must not bring into existence the
	thing it is asking about. `Red Profile.user` is unique in core, so the lookup
	is exact.

	**Open is "not terminal", asked of `states.py`.** Draft, Submitted and In
	Review are all things the society still owes an answer on; the four terminal
	states are finished, and applying again after one of them is a legitimate act
	the engine's cooldown governs instead.
	"""
	from vmmsx.approvals import states
	from vmmsx.approvals.services import contract

	profile = frappe.db.get_value(PROFILE_DOCTYPE, {"user": frappe.session.user}, "name")

	if not profile:
		return None

	# Each governed doctype names its applicant differently: an application
	# points at the Red Profile, a membership at the member satellite hanging off
	# it. Both resolve back to the same person.
	if doctype == APPLICATION_DOCTYPE:
		field, value = "red_profile", profile
	else:
		field = "member"
		value = frappe.db.get_value("VMMS Member", {"red_profile": profile}, "name")

	if not value:
		return None

	open_states = [state for state in states.STATES if not states.is_terminal(state)]

	return frappe.db.exists(doctype, {field: value, contract.STATE_FIELD: ("in", open_states)})


@frappe.whitelist()
def my_open_registrations() -> dict:
	"""What the caller has open, **one answer per kind of registration**.

	Possessive like everything else here: it takes no argument, so it cannot be
	pointed at anybody. The wizard reads it before drawing a single step, so
	somebody who has already applied is told so on arrival rather than on the
	last screen of a form they filled in for the second time.

	**One answer per kind, because the kinds are independent.** Both rules that
	actually refuse a second registration ask their question of a single doctype
	— `_assert_nothing_open(doctype)` here and `engine.assert_single_open`, which
	filters on `doc.doctype` — so an undecided volunteer application has never
	had anything to say about a membership, and vice versa. This used to answer
	"is *anything* of yours open", checking volunteer first, and the wizard drew
	its "you have already applied" screen from that single answer. A volunteer
	applicant who then went to register as a member was refused a registration
	the server would have accepted, and the card's own "register as a member
	instead" link came straight back to the volunteer answer, so there was no way
	out of it. The screen was asking a question this endpoint could not tell it
	the answer to.

	Keyed by the wizard path that files each kind rather than by doctype: the
	caller is a screen choosing between two roads, and the doctype travels inside
	each entry for anything that needs it.
	"""
	_assert_signed_in()

	from vmmsx.approvals.services import contract

	answer: dict[str, dict | None] = {}

	for path, doctype in REGISTRATION_PATHS:
		name = _open_registration(doctype)

		answer[path] = (
			{
				"doctype": doctype,
				"name": name,
				"path": path,
				"state": frappe.db.get_value(doctype, name, contract.STATE_FIELD),
				# What the approver said, when they sent it back for something.
				#
				# An application returned to Draft is waiting on the applicant,
				# and until this was here the applicant was the one person not
				# told why: the email carried the reason and the portal did not,
				# so anybody who deleted the email had no way back to it. Read
				# off the document's own audit trail, exactly as the email reads
				# it, so the two cannot say different things.
				"reason": _latest_decision_reason(doctype, name),
				# Draft means two opposite things and the portal was reading them
				# as one. A registration nobody has sent yet is a Draft, and so is
				# one an approver sent back — and the dashboard told somebody who
				# had not finished their own form that "your branch has asked for
				# something", about an application no branch had ever seen.
				#
				# The audit trail is what separates them: the engine records a
				# decision *before* it moves the state back, so a returned
				# application always has at least one, and a never-submitted draft
				# never does. Answered here rather than inferred from `reason`,
				# because an approver may send something back without typing one.
				"reviewed": _has_been_reviewed(doctype, name),
			}
			if name
			else None
		)

	return answer


def _latest_decision_reason(doctype: str, name: str) -> str:
	"""The last thing an approver wrote on this application, or nothing.

	The engine appends a decision row and then moves the state, in that order and
	in one save, so the last row is the decision that caused the state the caller
	is looking at. Same read as `notifications/services/lifecycle._latest_reason`,
	which is what puts it in the email.
	"""
	rows = frappe.get_all(
		"VMMS Approval Decision",
		filters={"parent": name, "parenttype": doctype},
		fields=["reason"],
		order_by="idx desc",
		limit_page_length=1,
	)

	return (rows[0].get("reason") or "") if rows else ""


def _has_been_reviewed(doctype: str, name: str) -> bool:
	"""Has this registration ever been in front of an approver?

	The one question that tells a draft nobody has submitted apart from a draft
	an approver returned, and both of those are `approval_state == "Draft"`. The
	engine appends a decision row and only then moves the state, so the presence
	of a single row is the whole answer.
	"""
	return bool(frappe.db.exists("VMMS Approval Decision", {"parent": name, "parenttype": doctype}))


def _assert_nothing_open(doctype: str) -> None:
	"""Refuse a second self-registration while the caller's first is undecided.

	**The engine already enforces this**, in `engine.assert_single_open`, and
	that is the authoritative check because it governs every door into an
	approval rather than this one. This is the same rule asked *before the
	insert*, and it exists for a reason worth stating: `_register` creates the
	document and only then submits it, so a refusal that arrives at submission
	has already left a Draft on the register. Over HTTP that draft is rolled back
	with the request, but relying on the framework's error handling to undo a
	write is not the same as not writing it, and anything that calls this
	endpoint outside a request would keep the orphan.

	So the wizard's second attempt is turned away with nothing created, and the
	engine's check stays exactly where it is for every other path.

	`_open_registration` is the shared answer, so this refusal and the sentence
	the wizard shows on arrival cannot disagree.
	"""
	existing = _open_registration(doctype)

	if not existing:
		return

	frappe.throw(
		_(
			"You already have an application with us that has not been decided yet ({0}). Wait for"
			" your branch to review it, or withdraw it from your portal, before starting another."
		).format(frappe.bold(existing)),
		frappe.ValidationError,
		title=_("Application Already Open"),
	)


def _register(
	values: dict,
	answers: dict | None = None,
	accepted=None,
	*,
	draft_only: bool = False,
):
	"""Insert a self-registration, down the same road a Web Form takes.

	The flag is the point. `intake.SELF_REGISTRATION_FLAG` is documented as the
	way "a caller that means it and is not a form" says so, and setting it hands
	this insert to the machinery both governed controllers already run in
	`before_insert` / `on_update`: the Red Profile is claimed or created, the
	identity buffer is emptied onto it, the person is placed, and `submit_once`
	puts the record into motion. **The SPA therefore registers through exactly
	the same code as the desk**, rather than through a parallel implementation
	that would have to be kept in step with it.

	**The elevation, and why it is this narrow.** A person registering for the
	first time holds no role in this society — that is what registering means —
	so the `create` permission on the governed doctype cannot be theirs, and a
	society that granted it to every signed-in user would have opened its
	register far wider than this. Frappe's own Web Form has exactly this problem
	and resolves it exactly this way (`web_form.py::accept` inserts with
	`ignore_permissions=True`), which is why registration works on the desk at
	all and did not work here.

	It is safe *because of the caller*, not because of this line. The two
	endpoints below name no person: the record can only ever attach to the
	Red Profile carrying the session's own login, resolved by core through a
	unique column, so there is no argument to tamper with. Everything the record
	must satisfy still runs untouched — ACC-02's anchor and ACC-03's permitted
	levels in `validate()`, identification and residency in
	`application.assert_ready()`, and the whole approval engine in `submit`.
	Nothing here bypasses a business rule; it bypasses a role check that the one
	person entitled to make this call could not possibly hold.
	"""
	document = frappe.get_doc(values)

	# Before the insert, so the society's own answers and the declarations the
	# applicant accepted are part of the record from the moment it exists rather
	# than a second write that could fail on its own.
	questions.apply(document, answers)
	_apply_declarations(document, accepted)

	document.flags[intake.SELF_REGISTRATION_FLAG] = True
	if draft_only:
		document.flags[intake.DRAFT_ONLY_FLAG] = True
	document.insert(ignore_permissions=True)

	# After it, because a file can only be tied to a document that has a name.
	questions.anchor_files(document)
	secure_row_files(document, "guardian_consents", GUARDIAN_CONSENT_FILE_FIELDS)

	return document


def _apply_declarations(document, accepted) -> None:
	"""Record what was agreed to — but only where the form actually asked.

	`declarations.apply` writes a row for every declaration shown on the doctype,
	accepted or not, because *"we asked and they said no" and "we never asked"
	are different facts about a consent register*. That rule is what makes the
	distinction here necessary rather than fussy.

	`VMMS Membership` carries one declaration and it is about uploaded evidence,
	so the ordinary member registration does not show it. Calling `apply` on that
	path would stamp every Gateway membership with a refusal of a declaration
	nobody was ever shown — recording the second fact as the first, which is
	precisely the confusion the module is built to avoid.

	So `None` means "this door does not ask", and an empty list still means "we
	asked and they ticked nothing" — which is what the volunteer wizard sends
	when somebody declines everything, and it must keep recording the refusals.
	"""
	if accepted is None:
		return

	declarations.apply(document, accepted)


def rows_from(supplied, allowed: tuple[str, ...], file_fields: tuple[str, ...] = ()) -> list[dict]:
	"""Child-table rows from a caller, filtered to what they may set.

	**Public, because both registration doors need it.** The self-service
	endpoints below and the clerk's `api/volunteer.py::apply_to_volunteer` shape
	the same rows the same way — a coordinator entering a paper application is
	as unable to verify a guardian's consent as the applicant is, and one
	allow-list is what makes that true of both rather than of whichever was
	written first.

	**An allow-list rather than a denial list**, because the fields that must not
	arrive from a caller are precisely the ones nobody thinks about: a field
	added to the doctype next year is refused by this by default, and would have
	been accepted by a list of things to strip. `GUARDIAN_CONSENT_FIELDS` records
	which three are missing and why.

	A JSON body arrives parsed; a form-encoded one arrives as a string. Both are
	ordinary ways to call a whitelisted method, so neither is an error.

	Rows that are entirely empty are dropped rather than stored — a form with a
	spare blank row at the bottom is a browser artefact, not an answer.
	"""
	if isinstance(supplied, str):
		supplied = frappe.parse_json(supplied)

	if not supplied:
		return []

	rows = []

	for entry in supplied:
		if not isinstance(entry, dict):
			continue

		row = {field: entry.get(field) for field in allowed if entry.get(field) is not None}

		for field in file_fields:
			if row.get(field):
				row[field] = evidence.assert_uploaded(row[field], field.replace("_", " "))

		if _has_content(row):
			rows.append(row)

	return rows


def _has_content(row: dict) -> bool:
	"""Did somebody actually type anything into this row?

	**Tickboxes do not count**, and that is the whole subtlety. A checkbox always
	carries a value — a blank emergency contact still arrives with "may contact"
	set one way or the other — so counting it would make every empty row look
	answered and store a contact with nobody's name on it.
	"""
	return any(cstr(value).strip() for value in row.values() if not isinstance(value, bool))


def secure_row_files(document, table: str, file_fields: tuple[str, ...]) -> None:
	"""Anchor and privatise every uploaded file on one child table.

	Runs after the insert, because a file can only be tied to a document that has
	a name — the same reason `questions.anchor_files` runs there. `evidence.secure`
	is the shared implementation; what is here is the walk over the rows and
	repointing each one at the URL the file ended up at.
	"""
	moved = False

	for row in document.get(table) or []:
		for field in file_fields:
			current = row.get(field)

			if not current:
				continue

			secured = evidence.secure(document, current)

			if secured and secured != current:
				row.set(field, secured)
				frappe.db.set_value(row.doctype, row.name, field, secured, update_modified=False)
				moved = True

	if moved:
		frappe.clear_document_cache(document.doctype, document.name)


def _doctype_for_path(path: str) -> str:
	"""The governed doctype behind one public registration path."""
	for candidate, doctype in REGISTRATION_PATHS:
		if path == candidate:
			return doctype

	frappe.throw(
		_("{0} is not a registration path.").format(frappe.bold(path)),
		frappe.ValidationError,
		title=_("Unknown Registration"),
	)


def _editable_registration(path: str):
	"""The caller's own open registration, provided it is currently editable."""
	from vmmsx.approvals import states
	from vmmsx.approvals.services import contract

	doctype = _doctype_for_path(path)
	name = _open_registration(doctype)

	if not name:
		return None

	document = frappe.get_doc(doctype, name)

	if contract.state(document) != states.DRAFT:
		frappe.throw(
			_(
				"Your {0} registration is already under review. It can only be edited if an"
				" approver sends it back for more information."
			).format(_(path)),
			frappe.ValidationError,
			title=_("Registration Is Under Review"),
		)

	return document


def _save_existing_draft(document, values: dict, answers: dict | None, accepted=None):
	"""Replace the applicant-owned portion of one already-authorised draft.

	`declarations.apply` is the one thing here that does not replace what it
	finds: an acceptance already standing is carried forward with its original
	timestamp and wording, because a consent is an act performed at a moment and
	saving the form again is not that moment. See its own docstring.
	"""
	with intake.as_system():
		document.update(values)
		questions.apply(document, answers)
		_apply_declarations(document, accepted)
		document.save()

	questions.anchor_files(document)
	secure_row_files(document, "guardian_consents", GUARDIAN_CONSENT_FILE_FIELDS)

	return document


def _answers_dict(document) -> dict:
	"""The wizard shape for the answer rows stored on a registration."""
	return {
		row["question"]: row["file_url"] if row["is_file"] else row["value"]
		for row in questions.answers_of(document)
	}


def _row_dtos(document, table: str, fields: tuple[str, ...]) -> list[dict]:
	"""Child rows as plain dicts, through the same allow-list that accepts them.

	Reading and writing share the tuple deliberately: a field the wizard is not
	allowed to send is a field it is not handed back either, so there is no shape
	it can round-trip that the server would then refuse.

	Dates are stringified because a wizard puts them straight into a date input,
	and a `datetime.date` reaching JSON is a shape the browser has to unpick.
	"""
	return [{field: _plain(row.get(field)) for field in fields} for row in document.get(table) or []]


def _plain(value):
	"""One stored value as something JSON and an HTML input both understand."""
	if value is None:
		return None

	if hasattr(value, "isoformat"):
		return str(getdate(value))

	return value


def _registration_dto(document, path: str) -> dict:
	"""The caller's editable registration, field by field, for wizard resume."""
	from vmmsx.approvals import states
	from vmmsx.approvals.services import contract

	state = contract.state(document)
	common = {
		"doctype": document.doctype,
		"name": document.name,
		"path": path,
		"state": state,
		"can_edit": state == states.DRAFT,
		"reason": _latest_decision_reason(document.doctype, document.name),
		"reviewed": _has_been_reviewed(document.doctype, document.name),
		"geo_node": document.get("geo_node"),
		"answers": _answers_dict(document),
	}

	if path == "volunteer":
		common.update(
			{
				"skills": [row.skill for row in document.get("skills") or [] if row.skill],
				"languages": [row.language for row in document.get("languages") or [] if row.language],
				"availability": [
					row.availability_slot
					for row in document.get("availability") or []
					if row.availability_slot
				],
				"motivation": [row.motivation for row in document.get("motivation") or [] if row.motivation],
				"prior_experience": document.get("prior_experience") or "",
				# The keys the applicant has already accepted, which is the shape
				# `save_my_volunteer_draft` takes back — so resuming a wizard
				# re-ticks exactly what was ticked, and `declarations.apply`
				# recognises those acceptances as standing and leaves them frozen.
				"declarations": [
					row["declaration"] for row in declarations.accepted_of(document) if row["accepted"]
				],
				"emergency_contacts": _row_dtos(document, "emergency_contacts", EMERGENCY_CONTACT_FIELDS),
				"is_minor": bool(document.get("is_minor")),
				# The applicant's own half of the guardian record. The reviewer's
				# three fields are deliberately absent, the same way they are
				# absent from what this endpoint accepts: a wizard has no use for
				# them and no business round-tripping them.
				"guardian_consents": _row_dtos(document, "guardian_consents", GUARDIAN_CONSENT_FIELDS),
			}
		)
	else:
		from vmmsx.member.services import membership as membership_service
		from vmmsx.member.services import proof

		common.update(
			{
				"membership_type": document.get("membership_type"),
				"membership_status": document.get("membership_status"),
				"membership_source": membership_service.source(document),
				"proof_attachment": document.get("proof_attachment"),
				# The claim as it stands, so a proof an approver sent back opens
				# with what was submitted rather than an empty form somebody has
				# to fill in from memory. `None` for an ordinary membership.
				#
				# There is no `verified` counterpart here, and its absence is the
				# same one `guardian_consents` has on the volunteer side: this is
				# what the *applicant's* form round-trips, and the society's
				# verification is neither theirs to see on it nor theirs to send
				# back.
				"claimed": proof.claimed_dto(document),
				"declarations": [
					row["declaration"] for row in declarations.accepted_of(document) if row["accepted"]
				],
			}
		)

	return common


@frappe.whitelist()
def my_registration(path: str) -> dict | None:
	"""Load the caller's own open volunteer or member registration for resume."""
	_assert_signed_in()
	doctype = _doctype_for_path(path)
	name = _open_registration(doctype)

	return _registration_dto(frappe.get_doc(doctype, name), path) if name else None


@frappe.whitelist()
def save_my_volunteer_draft(
	geo_node: str,
	country_of_citizenship: str | None = None,
	residency_type: str | None = None,
	home_geo_node: str | None = None,
	country_of_residence: str | None = None,
	residence_address: str | None = None,
	id_type: str | None = None,
	id_number: str | None = None,
	skills: list | None = None,
	languages: list | None = None,
	availability: list | None = None,
	motivation: list | None = None,
	prior_experience: str | None = None,
	first_name: str | None = None,
	last_name: str | None = None,
	phone: str | None = None,
	gender: str | None = None,
	date_of_birth: str | None = None,
	profile_photo: str | None = None,
	answers: dict | None = None,
	declarations_accepted: list | dict | None = None,
	emergency_contacts: list | None = None,
	guardian_consents: list | None = None,
) -> dict:
	"""Create or replace the caller's volunteer draft without routing it.

	The three new arguments are the applicant's own halves of Phase 1's records.
	None of them is checked for completeness here — a draft is allowed to be
	half-finished, which is the whole reason drafts exist. The emergency contact
	and the guardian consent are checked at *approval*
	(`application.assert_approvable`) and the declarations at submission
	(`declarations.assert_accepted`).

	`guardian_consents` cannot carry the reviewer's verification: see
	`GUARDIAN_CONSENT_FIELDS`.
	"""
	_assert_signed_in()

	from vmmsx.api.volunteer import selector_rows

	profile = intake.for_user(
		frappe.session.user,
		{
			key: value
			for key, value in {
				"first_name": first_name,
				"last_name": last_name,
				"phone": phone,
				"gender": gender,
				"date_of_birth": date_of_birth,
			}.items()
			if value
		},
	)

	if not profile:
		frappe.throw(_("Your account could not be matched to a person record."), frappe.ValidationError)

	_write_profile(
		profile,
		{
			"first_name": first_name,
			"last_name": last_name,
			"phone": phone,
			"gender": gender,
			"date_of_birth": date_of_birth,
			"profile_photo": profile_photo,
			"country_of_citizenship": country_of_citizenship,
			"residency_type": residency_type,
			"home_geo_node": home_geo_node,
			"country_of_residence": country_of_residence,
			"residence_address": residence_address,
		},
		id_type=id_type,
		id_number=id_number,
	)

	values = {
		"geo_node": geo_node,
		"skills": selector_rows(skills, "skill"),
		"languages": selector_rows(languages, "language"),
		"availability": selector_rows(availability, "availability_slot"),
		"motivation": selector_rows(motivation, "motivation"),
		"prior_experience": prior_experience,
		"emergency_contacts": rows_from(emergency_contacts, EMERGENCY_CONTACT_FIELDS),
		"guardian_consents": rows_from(
			guardian_consents, GUARDIAN_CONSENT_FIELDS, GUARDIAN_CONSENT_FILE_FIELDS
		),
	}
	document = _editable_registration("volunteer")

	if document:
		document = _save_existing_draft(document, values, answers, declarations_accepted)
	else:
		document = _register(
			{"doctype": APPLICATION_DOCTYPE, "red_profile": profile, **values},
			answers=answers,
			accepted=declarations_accepted,
			draft_only=True,
		)

	return _registration_dto(document, "volunteer")


@frappe.whitelist()
def save_my_member_draft(
	membership_type: str,
	geo_node: str,
	first_name: str | None = None,
	last_name: str | None = None,
	phone: str | None = None,
	gender: str | None = None,
	date_of_birth: str | None = None,
	profile_photo: str | None = None,
	answers: dict | None = None,
) -> dict:
	"""Create or replace the caller's membership draft without starting payment or review."""
	_assert_signed_in()
	profile = intake.for_user(
		frappe.session.user,
		{
			key: value
			for key, value in {
				"first_name": first_name,
				"last_name": last_name,
				"phone": phone,
				"gender": gender,
				"date_of_birth": date_of_birth,
			}.items()
			if value
		},
	)

	if not profile:
		frappe.throw(_("Your account could not be matched to a person record."), frappe.ValidationError)

	_write_profile(
		profile,
		{
			"first_name": first_name,
			"last_name": last_name,
			"phone": phone,
			"gender": gender,
			"date_of_birth": date_of_birth,
			"profile_photo": profile_photo,
		},
	)

	values = {"membership_type": membership_type, "geo_node": geo_node}
	document = _editable_registration("member")

	if document:
		if document.get("payment_transaction") and document.membership_type != membership_type:
			frappe.throw(
				_("The membership type cannot be changed after a payment request has been created."),
				frappe.ValidationError,
				title=_("Membership Type Locked"),
			)
		document = _save_existing_draft(document, values, answers)
	else:
		document = _register(
			{
				"doctype": MEMBERSHIP_DOCTYPE,
				"membership_type": membership_type,
				"geo_node": geo_node,
				**_intake_fields(first_name, last_name, phone, gender, date_of_birth),
			},
			answers=answers,
			draft_only=True,
		)

	return _registration_dto(document, "member")


@frappe.whitelist()
def submit_my_registration(path: str) -> dict:
	"""Submit the caller's own saved draft and route it through its normal lifecycle."""
	_assert_signed_in()
	document = _editable_registration(path)

	if not document:
		frappe.throw(
			_("Save your registration before submitting it."),
			frappe.ValidationError,
			title=_("No Draft Registration"),
		)

	with intake.as_system():
		if path == "volunteer":
			from vmmsx.volunteer.services import application as application_service

			result = application_service.submit(document)
		else:
			from vmmsx.member.services import membership as membership_service

			result = membership_service.submit(document)

	return result


@frappe.whitelist()
def register_as_volunteer(
	geo_node: str,
	country_of_citizenship: str | None = None,
	residency_type: str = "Local",
	home_geo_node: str | None = None,
	country_of_residence: str | None = None,
	residence_address: str | None = None,
	id_type: str | None = None,
	id_number: str | None = None,
	skills: list | None = None,
	languages: list | None = None,
	availability: list | None = None,
	motivation: list | None = None,
	prior_experience: str | None = None,
	first_name: str | None = None,
	last_name: str | None = None,
	phone: str | None = None,
	gender: str | None = None,
	date_of_birth: str | None = None,
	profile_photo: str | None = None,
	answers: dict | None = None,
	declarations_accepted: list | dict | None = None,
	emergency_contacts: list | None = None,
	guardian_consents: list | None = None,
) -> dict:
	"""Register the caller as a volunteer, and put the application into motion.

	The self-service twin of `api/volunteer.py::apply_to_volunteer`, and it asks
	for the same things the React volunteer journey asks for. `assert_ready()`
	refuses a submission with no
	identification and no completed residency answer whichever door it came
	through.

	`skills`, `languages`, `availability` and `motivation` are plain lists of
	keys — the shape `application_options` hands out — not the child-table rows
	those fields store internally.

	`answers` is the society's own questions, keyed by the opaque question name
	`application_options` handed out. Every value in it is re-checked against the
	question that asked for it, so a choice the browser was not offered is
	refused here rather than stored.

	`profile_photo` is a fact about the *person*, so it lands on the Red Profile
	rather than on this application — see `_adopt_photo`, which is also why it
	travels with the registration instead of following it.

	`declarations_accepted` is the keys of the declarations the applicant ticked.
	Every required one must be there or `assert_ready` refuses the submission,
	and what is stored is the wording as it stood at this moment — see
	`registration/services/declarations.py`.

	`emergency_contacts` and `guardian_consents` are accepted here but not
	insisted on: they are conditions of *approval*, not of submission, so an
	applicant can send their application in and the branch can chase the consent
	form. The reviewer's own verification fields cannot be set from here — see
	`GUARDIAN_CONSENT_FIELDS`.
	"""
	_assert_signed_in()
	_assert_nothing_open(APPLICATION_DOCTYPE)

	from vmmsx.api.volunteer import selector_rows
	from vmmsx.volunteer.services import application as application_service
	from vmmsx.volunteer.services import society

	profile = intake.for_user(
		frappe.session.user,
		{
			key: value
			for key, value in {
				"first_name": first_name,
				"last_name": last_name,
				"phone": phone,
				"gender": gender,
				"date_of_birth": date_of_birth,
			}.items()
			if value
		},
	)

	if not profile:
		frappe.throw(
			_("Your account could not be matched to a person record."),
			frappe.ValidationError,
			title=_("No Profile"),
		)

	_write_profile(
		profile,
		{
			"country_of_citizenship": country_of_citizenship or society.default_citizenship_country(),
			"residency_type": residency_type,
			"home_geo_node": home_geo_node,
			"country_of_residence": country_of_residence,
			"residence_address": residence_address,
		},
		id_type=id_type,
		id_number=id_number,
	)

	application = _register(
		{
			"doctype": APPLICATION_DOCTYPE,
			"red_profile": profile,
			"geo_node": geo_node,
			"skills": selector_rows(skills, "skill"),
			"languages": selector_rows(languages, "language"),
			"availability": selector_rows(availability, "availability_slot"),
			"motivation": selector_rows(motivation, "motivation"),
			"prior_experience": prior_experience,
			"emergency_contacts": rows_from(emergency_contacts, EMERGENCY_CONTACT_FIELDS),
			"guardian_consents": rows_from(
				guardian_consents, GUARDIAN_CONSENT_FIELDS, GUARDIAN_CONSENT_FILE_FIELDS
			),
		},
		answers=answers,
		accepted=declarations_accepted,
	)

	# Registration only fills a missing portrait. Replacing a portrait already
	# held by the society is an explicit profile correction, not an application
	# side effect.
	_adopt_photo(profile_photo)

	# `submit_once` has already run from `on_update`. This is the idempotent
	# re-ask that turns the insert into the status DTO the sibling endpoint
	# returns, so both doors answer in the same shape.
	return application_service.submit(application)


@frappe.whitelist()
def register_as_member(
	membership_type: str,
	geo_node: str,
	first_name: str | None = None,
	last_name: str | None = None,
	phone: str | None = None,
	gender: str | None = None,
	date_of_birth: str | None = None,
	profile_photo: str | None = None,
	answers: dict | None = None,
) -> dict:
	"""Register the caller as a member, and put the membership into motion.

	The self-service twin of `api/member.py::apply_for_membership`, asking for
	what the `register-as-a-member` Web Form asks for. The member satellite is
	created by the controller's own `before_insert`, inside the same narrow
	elevation the profile write uses, so nothing here has to know it exists.

	`profile_photo` lands on the Red Profile rather than on the membership, for
	the reason `_adopt_photo` sets out.

	`membership_source` and `proof_attachment` are deliberately absent. They are
	how a *clerk* enrols somebody who paid before this system existed, and an
	applicant asserting their own proof of payment is not a thing this endpoint
	is willing to let happen. Somebody proving a membership they already hold goes
	through `register_existing_membership` below, which is built around that
	assertion being a claim rather than a fact.
	"""
	_assert_signed_in()
	_assert_nothing_open(MEMBERSHIP_DOCTYPE)

	from vmmsx.member.services import membership as membership_service

	membership = _register(
		{
			"doctype": MEMBERSHIP_DOCTYPE,
			"membership_type": membership_type,
			"geo_node": geo_node,
			**_intake_fields(first_name, last_name, phone, gender, date_of_birth),
		},
		answers=answers,
	)

	_adopt_photo(profile_photo)

	return membership_service.submit(membership)


@frappe.whitelist()
def register_existing_membership(
	membership_type: str,
	geo_node: str,
	proof_attachment: str,
	proof_claimed_start_date: str | None = None,
	proof_claimed_expiry_date: str | None = None,
	proof_membership_number: str | None = None,
	proof_registered_at: str | None = None,
	proof_reference_number: str | None = None,
	declarations_accepted: list | dict | None = None,
) -> dict:
	"""Ask the society to recognise a membership the caller already holds.

	**The endpoint `register_as_member` refuses to be, and the reason its refusal
	stands.** That one will not accept `membership_source` or `proof_attachment`
	because an applicant asserting their own proof of payment must not settle the
	fee question by saying so. Nothing here changes that. What is different is
	that every fact this endpoint accepts lands in a *claimed* field, none of
	which decides anything: `proof.assert_verified` refuses the approval until
	somebody at the society has read the evidence and recorded the dates
	themselves, and `membership.activate` reads only what they recorded. The
	applicant's assertion never becomes the society's.

	**No identity arguments, and that is not an omission.** The ordinary
	registration takes a name and a date of birth because it may be the first
	thing somebody ever does here. A person proving an existing membership is
	signed in and already known — the agreed scope prefills their details
	read-only — so there is nothing for this door to accept and nothing for it to
	overwrite. It reads `my_profile()` on the way in and writes to it never.

	**The plan is carried, not chosen.** It arrives from the plan the caller
	selected and is locked on the form; changing it means going back to the plan
	list, which is a different membership being claimed.

	A returned submission comes back through this same endpoint. `_editable_
	registration` finds the draft an approver sent back and replaces the
	applicant's half of it, so a correction is the same act as the original with
	the same history behind it, rather than a second membership.
	"""
	_assert_signed_in()

	from vmmsx.member.services import membership as membership_service

	attachment = evidence.assert_uploaded(proof_attachment, _("proof of membership"))

	if not attachment:
		frappe.throw(
			_("Upload the document that proves your membership before submitting this."),
			frappe.MandatoryError,
			title=_("Proof Required"),
		)

	# Required at *this* door specifically, rather than by `proof.has_claim`.
	# What makes a proof a claim is that somebody asserted a period for the
	# society to check, and a clerk's desk entry legitimately asserts none — so
	# the rule cannot live in the service, which serves both. Without it here, a
	# self-service submission with the date left out would slip through as a
	# clerk-style entry and quietly collect a fresh period starting today, which
	# is the exact outcome this whole endpoint exists to prevent.
	if not proof_claimed_start_date:
		frappe.throw(
			_("Tell us when you originally joined. It is on the document you are uploading."),
			frappe.MandatoryError,
			title=_("Start Date Needed"),
		)

	# The claim, through an allow-list built from the same tuple that reads it
	# back. The four verified fields are not in `CLAIM_FIELDS` and so cannot be
	# named here whatever a browser sends — the same property `rows_from` gives
	# the guardian's verification.
	claim = _claim_from(
		{
			"proof_claimed_start_date": proof_claimed_start_date,
			"proof_claimed_expiry_date": proof_claimed_expiry_date,
			"proof_membership_number": proof_membership_number,
			"proof_registered_at": proof_registered_at,
			"proof_reference_number": proof_reference_number,
		}
	)

	values = {
		"doctype": MEMBERSHIP_DOCTYPE,
		"membership_type": membership_type,
		"geo_node": geo_node,
		"membership_source": membership_service.SOURCE_PROOF,
		"proof_attachment": attachment,
		**claim,
	}

	document = _editable_registration("member")

	if document:
		if membership_service.source(document) != membership_service.SOURCE_PROOF:
			frappe.throw(
				_(
					"You have a membership application open that is not a proof of an existing"
					" membership. Finish or withdraw that one first."
				),
				frappe.ValidationError,
				title=_("Application Already Open"),
			)

		document = _save_existing_draft(document, values, None, accepted=declarations_accepted)
	else:
		_assert_nothing_open(MEMBERSHIP_DOCTYPE)
		document = _register(values, accepted=declarations_accepted)

	# After the insert or the save, because a file can only be tied to a document
	# that has a name — and the URL changes when the file is moved out of the
	# public directory, so what `secure` returns is what gets stored.
	_secure_proof(document)

	# Elevated for `_register`'s reason, and stated here because the correction
	# path is where it stops being implicit: a fresh insert carries
	# `ignore_permissions` on the document it returns, and a draft reloaded from
	# the register does not. `submit_my_registration` wraps its submit the same
	# way and for the same reason — an applicant holds no role on the doctype
	# they are applying to, which is what applying means.
	with intake.as_system():
		return membership_service.submit(document)


def _claim_from(supplied: dict) -> dict:
	"""The applicant's claim, filtered to the fields a claim is allowed to have."""
	from vmmsx.member.services import proof

	return {
		field: supplied[field]
		for field in proof.CLAIM_FIELDS
		if supplied.get(field) not in (None, "")
	}


def _secure_proof(document) -> None:
	"""Anchor the uploaded proof to the membership and take it off the open web.

	`evidence.secure` is the shared implementation and this is one call, but it
	is worth its own function for what the assignment does: making a file private
	*moves* it, so the membership has to store the URL that comes back rather
	than the one it was given. A caller that skipped this line would leave
	somebody's membership certificate on a guessable public path forever.

	**And it reloads afterwards, which is not optional.** Attaching a file to a
	document touches that document's own row, so the copy in memory is a version
	behind the moment this returns — and the next thing every caller does is
	`membership.submit()`, which saves. Without the reload that save is refused
	with a timestamp mismatch, which reads to an applicant as their registration
	failing for no reason at all.
	"""
	secured = evidence.secure(document, document.get("proof_attachment"))

	if secured and secured != document.get("proof_attachment"):
		frappe.db.set_value(
			document.doctype, document.name, "proof_attachment", secured, update_modified=False
		)

	document.reload()
