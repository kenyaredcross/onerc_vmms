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

from vmmsx.registration.services import intake, questions

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

UPLOAD_PREFIXES = ("/files/", "/private/files/")

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
			"home_geo_node",
		],
		as_dict=True,
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
		# Served because `update_my_profile` already accepts it: a form that can
		# set a photograph and cannot read back the one already on file would show
		# an empty control to somebody who has had a portrait on their card for a
		# year, and the obvious way to fix that is to upload it again.
		"profile_photo": person.profile_photo,
		# Where core last recorded this person as living. **Read-only here**, and
		# it is not a field `update_my_profile` accepts: it is written by a
		# registration, not typed into one.
		#
		# It is served for one reason — a second registration should not ask
		# somebody to walk a cascading picker down to the branch they already told
		# this society they belong to. The wizard opens its placement step with
		# this node's chain already filled in and every rung still changeable, so
		# the answer is a *suggestion* rather than a decision made for them.
		"home_geo_node": person.home_geo_node,
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
	}

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
					_("{0} was not uploaded to this site.").format(
						frappe.bold(_(meta.get_label(field)))
					),
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

	if changes:
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
			document.save()

		frappe.clear_document_cache(PROFILE_DOCTYPE, profile)

	return _profile_dto(profile)


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


def _register(values: dict, answers: dict | None = None):
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

	# Before the insert, so the society's own answers are part of the record from
	# the moment it exists rather than a second write that could fail on its own.
	questions.apply(document, answers)

	document.flags[intake.SELF_REGISTRATION_FLAG] = True
	document.insert(ignore_permissions=True)

	# After it, because a file can only be tied to a document that has a name.
	questions.anchor_files(document)

	return document


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
) -> dict:
	"""Register the caller as a volunteer, and put the application into motion.

	The self-service twin of `api/volunteer.py::apply_to_volunteer`, and it asks
	for the same things the `register-as-a-volunteer` Web Form asks for, because
	they are the same registration: `assert_ready()` refuses a submission with no
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
	"""
	_assert_signed_in()
	_assert_nothing_open(APPLICATION_DOCTYPE)

	from vmmsx.api.volunteer import selector_rows
	from vmmsx.volunteer.services import application as application_service

	application = _register(
		{
			"doctype": APPLICATION_DOCTYPE,
			"geo_node": geo_node,
			"country_of_citizenship": country_of_citizenship,
			"residency_type": residency_type,
			"home_geo_node": home_geo_node,
			"country_of_residence": country_of_residence,
			"residence_address": residence_address,
			"id_type": id_type,
			"id_number": id_number,
			"skills": selector_rows(skills, "skill"),
			"languages": selector_rows(languages, "language"),
			"availability": selector_rows(availability, "availability_slot"),
			"motivation": selector_rows(motivation, "motivation"),
			"prior_experience": prior_experience,
			**_intake_fields(first_name, last_name, phone, gender, date_of_birth),
		},
		answers=answers,
	)

	# After the insert, because the profile this writes to is the one the insert
	# just claimed or created.
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
	is willing to let happen.
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
