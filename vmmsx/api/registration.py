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

# The two disability fields, named once. They are Custom Fields on core's
# `Red Profile` rather than columns of it — see
# `patches/install_disability_fields.py` — which is why every read of them goes
# through `_disability()` below rather than naming the column in a query: a site
# between syncing this module and running that patch has the doctype and not yet
# the fields, and a `get_value` on a column that is not there raises.
DISABILITY_FIELD = "vmms_disability_status"
DISABILITY_NEEDS_FIELD = "vmms_disability_needs"

# The third of them, and the only one that is a table. Which disabilities a
# person has said they have, from core's own `Disability` register — see
# `patches/install_disability_vocabulary.py` for why the Select above stays the
# question and this stays optional beside it. Guarded on the meta everywhere the
# other two are, for the same reason: it is a Custom Field, and a site between
# sync and migrate does not have it.
DISABILITIES_FIELD = "vmms_disabilities"

# The child doctype behind that field, named here because every read of the
# table filters on it and core's `Disability` is what it links to.
SELECTOR_DOCTYPE = "VMMS Disability Selector"
DISABILITY_DOCTYPE = "Disability"

# What somebody has already done, installed on the same spine by
# `patches/install_background_fields.py`. One scalar and six tables.
#
# **Every one of them optional, and no completion rule reads any of them.** A
# volunteer application is not a job application: the whole block can be left
# empty and the registration is as valid as one that fills it in.
PROFESSION_FIELD = "vmms_profession"
OTHER_PROFESSION_FIELD = "vmms_other_profession"

# The six tables, keyed by the name a caller sends and the browser reads back.
# Each entry is the profile field it writes, the child fields a caller may set,
# and which of those hold a file URL rather than a value.
#
# **An allow-list per table rather than one shared list**, for the reason
# `rows_from` gives: a field added to one of these doctypes next year is refused
# by default here, and would have been accepted by a list of things to strip.
BACKGROUND_TABLES = {
	"education": (
		"vmms_education",
		("institution", "level", "qualification", "started_in", "finished_in", "is_ongoing", "attachment"),
		("attachment",),
	),
	"training": (
		"vmms_training",
		("course_name", "institution", "started_on", "completed_on", "remarks", "attachment"),
		("attachment",),
	),
	"work_experience": (
		"vmms_work_experience",
		("organization", "role", "started_on", "ended_on", "is_current", "summary"),
		(),
	),
	"licences": (
		"vmms_licences",
		(
			"license_type",
			"license_name",
			"institution",
			"qualification",
			"registration_no",
			"valid_from",
			"valid_to",
			"does_not_expire",
			"description",
			"attachment",
		),
		("attachment",),
	),
	"driving_licences": (
		"vmms_driving_licences",
		("licence_class", "licence_number", "valid_to", "attachment"),
		("attachment",),
	),
	"references": (
		"vmms_references",
		("reference_name", "position", "organization", "email", "phone", "relationship", "notes"),
		(),
	),
}

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
	# Whether somebody has a disability, and what would help. Person-owned like
	# everything else in this list and correctable by them for the same reason:
	# it is a fact about them, it changes, and the person it is about is the one
	# who knows. Installed by `patches/install_disability_fields.py`, which
	# records why it sits on core's spine rather than on the volunteer record.
	DISABILITY_FIELD,
	DISABILITY_NEEDS_FIELD,
	# What kind of work somebody does. A person fact like the rest of this list
	# and correctable by them for the same reason. The six background *tables*
	# beside it are not here — a table is not a scalar and `_write_profile`
	# handles them the way it handles identity documents.
	PROFESSION_FIELD,
	OTHER_PROFESSION_FIELD,
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

# What an applicant may say about one of their identity documents. A closed
# list, for the reason `rows_from` gives at length: these arrive as loose dicts
# from a browser and `is_primary` is decided by position rather than by the
# caller — the first document somebody lists is their main one, and a form that
# let a caller set the flag could produce a profile with two primaries or none.
#
# `attachment` is here because a society can insist on one. `Identification
# Type.vmms_requires_attachment` makes a copy of the document a condition of
# submission — `application._assert_identity_documents` refuses without it — and
# for as long as this list held only the pair, the only way to satisfy that rule
# was a clerk attaching the scan on the desk. An applicant who could not upload
# was told to add a file to a profile no screen would let them edit.
#
# The file is uploaded before the application exists, which is the same position
# a society's own `Attach` question is in, and it takes the same answer:
# `evidence.secure()` anchors it to the Red Profile and makes it private on the
# way in. Until then it belongs to the person who uploaded it, which is the
# right owner for a document not yet given to anybody.
#
# An attachment already on a profile still survives a rewrite that does not
# mention one — see `_identification_rows` — so a branch that scanned somebody's
# card does not lose it because they corrected the number beside it.
IDENTIFICATION_FIELDS = (
	"id_type",
	"id_number",
	"attachment",
)

# The one field in that list holding a file URL rather than a value, checked
# against this site's own upload paths before it is stored.
IDENTIFICATION_FILE_FIELDS = ("attachment",)

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

# How the applicant said they want to pay. A Custom Field on `VMMS Membership`,
# installed by `patches/install_membership_payment_methods.py`; named here so
# the endpoint and the patch agree on the spelling.
PAYMENT_METHOD_FIELD = "payment_method"


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
		**_disability(profile),
		**_background(profile),
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


def _disability(profile: str) -> dict:
	"""What this person said about disability, or nothing on a site mid-migrate.

	Read separately from the rest of the profile and guarded on the meta, for the
	reason `DISABILITY_FIELD` gives: these are Custom Fields, a site that has
	synced this module but not yet run the patch does not have them, and a form
	that raised there would be a registration nobody could open. Absent reads as
	unanswered, which is the honest answer.
	"""
	meta = frappe.get_meta(PROFILE_DOCTYPE)

	if not meta.has_field(DISABILITY_FIELD):
		return {"disability_status": None, "disability_needs": None, "disabilities": []}

	row = frappe.db.get_value(
		PROFILE_DOCTYPE, profile, [DISABILITY_FIELD, DISABILITY_NEEDS_FIELD], as_dict=True
	)

	return {
		"disability_status": (row or {}).get(DISABILITY_FIELD),
		"disability_needs": (row or {}).get(DISABILITY_NEEDS_FIELD),
		# Guarded separately from the two above it. The table arrived a patch
		# later than they did, so a site can genuinely have the Select and not
		# the table, and a read of a child table whose parent field does not
		# exist yet returns rows nobody can account for.
		"disabilities": _disabilities(profile) if meta.has_field(DISABILITIES_FIELD) else [],
	}


def _disabilities(profile: str) -> list[str]:
	"""The disabilities named on one profile, as the keys the register stores.

	Keys and not labels, because `Disability` autonames from `disability_name`
	and the docname is what a Link field holds, what the form sends back, and
	what `identity_options` offers. A society renaming a row renames the record,
	so a profile that chose it keeps pointing at it.
	"""
	rows = frappe.get_all(
		SELECTOR_DOCTYPE,
		filters={
			"parenttype": PROFILE_DOCTYPE,
			"parent": profile,
			"parentfield": DISABILITIES_FIELD,
		},
		fields=["disability"],
		order_by="idx asc",
	)

	return [row["disability"] for row in rows if row["disability"]]


def _background(profile: str) -> dict:
	"""What this person has already done, or empties on a site mid-migrate.

	Guarded on the meta for the reason `_disability` is: these are Custom Fields,
	a site that has synced this module and not yet run
	`install_background_fields` does not have them, and a read of a column that
	is not there raises — on the endpoint that draws the registration form, which
	would be a wizard nobody could open.

	Empty and absent read the same here, deliberately. Nothing in this block is
	required and nothing counts it, so there is no reader that needs to tell "has
	not been asked" from "has nothing to say" — which is exactly the distinction
	the disability Select exists to preserve and this block has no use for.
	"""
	meta = frappe.get_meta(PROFILE_DOCTYPE)

	if not meta.has_field(PROFESSION_FIELD):
		return {"profession": None, "other_profession": None, **{key: [] for key in BACKGROUND_TABLES}}

	fields = [PROFESSION_FIELD]
	if meta.has_field(OTHER_PROFESSION_FIELD):
		fields.append(OTHER_PROFESSION_FIELD)
	values = frappe.db.get_value(PROFILE_DOCTYPE, profile, fields, as_dict=True)
	background = {
		"profession": values.get(PROFESSION_FIELD),
		"other_profession": values.get(OTHER_PROFESSION_FIELD),
	}

	for key, (field, allowed, _files) in BACKGROUND_TABLES.items():
		background[key] = _background_rows_held(profile, field, allowed) if meta.has_field(field) else []

	return background


def _background_rows_held(profile: str, field: str, allowed: tuple[str, ...]) -> list[dict]:
	"""One background table, read back in the shape a caller sends it.

	The same allow-list on the way out as on the way in, so the browser round
	trips exactly what it may set and a field it has no business seeing cannot
	arrive on a form that would then send it back.
	"""
	child = frappe.get_meta(PROFILE_DOCTYPE).get_field(field).options

	return frappe.get_all(
		child,
		filters={"parenttype": PROFILE_DOCTYPE, "parent": profile, "parentfield": field},
		fields=list(allowed),
		order_by="idx asc",
	)


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

	`disabilities` is here on the same argument and for the same field owner: it
	is core's `Disability` register, both registration paths hold the field it
	fills, and neither of them owns it. Empty on a site whose register has not
	been seeded or whose vocabulary patch has not run — which the form draws as
	"nothing configured" rather than as an error, because a society that has
	retired every row has said something and should be believed.
	"""
	return {
		"genders": [row["name"] for row in frappe.get_all("Gender", order_by="name asc")],
		"disabilities": _disability_vocabulary(),
		# The four the background block draws. Name-only registers come back as
		# plain lists; the two with a label and a description come back in the
		# `{key, label, description}` shape every picker in the portal takes.
		"professions": _names("Profession"),
		"licence_types": _names("Personnel License Type"),
		"education_levels": _configured("VMMS Education Level", "level_name", order="sequence asc"),
		"driving_licence_classes": _configured("VMMS Driving Licence Class", "class_name"),
	}


def _names(doctype: str) -> list[str]:
	"""A name-only register, as a plain list.

	`Profession` and `Personnel License Type` have no fields at all — the docname
	*is* the value, which is how they were built for recruitment and how a
	society already edits them. Both grant `All` read in their own source, so
	there is nothing to elevate past.
	"""
	if not frappe.db.table_exists(doctype):
		return []

	return [row["name"] for row in frappe.get_all(doctype, order_by="name asc")]


def _configured(doctype: str, label_field: str, *, order: str | None = None) -> list[dict]:
	"""An active-only vmmsx register, in the shape the portal's pickers take.

	Not called `_register`: this file already has one of those and it *creates a
	registration*, which is the opposite kind of noun. Shadowing it made every
	registration in the app raise the moment the options endpoint was read.

	The twin of `api/volunteer.py::_vocabulary` and deliberately not a call to
	it: that one hardcodes an alphabetical sort on the label, and an education
	level sorted alphabetically puts "Undergraduate degree" above "Vocational"
	and "Diploma" above "Primary". These registers carry their own order and it
	is the only thing `sequence` is for.
	"""
	if not frappe.db.table_exists(doctype):
		return []

	rows = frappe.get_all(
		doctype,
		filters={"is_active": 1},
		fields=["name", label_field, "description"],
		order_by=order or f"{label_field} asc",
	)

	return [
		{"key": row["name"], "label": row[label_field] or row["name"], "description": row["description"]}
		for row in rows
	]


def _disability_vocabulary() -> list[dict]:
	"""Core's `Disability` register as `{key, label, description}` rows.

	The same shape `api/volunteer.py::_vocabulary` returns, so a form draws this
	picker with the control it already draws skills and languages with. It is not
	that function because this register is core's rather than this product's: it
	has no `is_active` to filter on and no `description` to read, and its type is
	what a reader wants in the third slot — "Deafness" under "Hearing" tells
	somebody scanning a long list which part of it they are in.

	Elevated, and only here. Core ships both registers as System Manager only and
	`patches/install_disability_vocabulary.py` grants `All` read, but a site that
	has synced this module and not yet migrated has the endpoint without the
	grant — and an applicant who could not draw the control would be asked a
	question with no answers. A vocabulary says nothing about any person, which
	is the whole of why this is safe to read past a permission.
	"""
	if not frappe.db.table_exists(DISABILITY_DOCTYPE):
		return []

	rows = frappe.get_all(
		DISABILITY_DOCTYPE,
		fields=["name", "disability_name", "disability_type"],
		order_by="disability_type asc, disability_name asc",
		ignore_permissions=True,
	)

	return [
		{
			"key": row["name"],
			"label": row["disability_name"] or row["name"],
			"description": row["disability_type"],
		}
		for row in rows
	]


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
	disability_status: str | None = None,
	disability_needs: str | None = None,
	disabilities: list | None = None,
	profession: str | None = None,
	other_profession: str | None = None,
	background: dict | None = None,
	id_type: str | None = None,
	id_number: str | None = None,
	identifications: list | None = None,
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
		DISABILITY_FIELD: disability_status,
		DISABILITY_NEEDS_FIELD: disability_needs,
		PROFESSION_FIELD: profession,
		OTHER_PROFESSION_FIELD: other_profession,
	}

	_write_profile(
		profile,
		supplied,
		id_type=id_type,
		id_number=id_number,
		identifications=identifications,
		disabilities=disabilities,
		background=background,
	)

	return _profile_dto(profile)


def _write_profile(
	profile: str,
	supplied: dict,
	*,
	id_type: str | None = None,
	id_number: str | None = None,
	identifications: list | None = None,
	disabilities: list | None = None,
	background: dict | None = None,
) -> None:
	"""Write person-owned registration facts to one already-resolved profile.

	**Identity documents arrive two ways and mean the same thing.** `Red Profile`
	has always held a *table* of them — a passport and a national card are two
	documents, not two versions of one — but this endpoint only ever accepted one
	pair, so a society asking for two could not be satisfied through the form
	that asks. `identifications` is the list; `id_type`/`id_number` remain for the
	callers that send a single document and are folded into a one-row list.

	The two are never combined. A caller that sends the list has said what the
	whole set is, and a scalar arriving beside it would be a second opinion about
	the same table.

	**`background` is six more tables and one dict**, and it extends the same rule
	a level down: `None` leaves all six alone, and a key that is present replaces
	that one table while a key that is absent leaves it untouched. A browser
	asking about education sends `{"education": [...]}` and cannot empty
	somebody's references by omission.

	**`disabilities` is the second table and follows the same three-answer rule**
	— `None` leaves it alone, `[]` empties it, a list replaces it. It is written
	beside the Select rather than derived from it: clearing the list is not
	answering "No", and answering "No" is the caller's to send in
	`vmms_disability_status`. What this will not do is invent one from the other.
	"""

	meta = frappe.get_meta(PROFILE_DOCTYPE)

	changes = {
		field: value
		for field, value in supplied.items()
		# `has_field` as well as the allow-list, because two of the names in it
		# are Custom Fields rather than columns of core's doctype — see
		# `DISABILITY_FIELD`. A site that has synced this module and not yet run
		# the patch drops them rather than writing an attribute the save will not
		# persist and nobody will notice is missing.
		if field in SELF_EDITABLE_FIELDS and value is not None and meta.has_field(field)
	}

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

	documents = _identifications_supplied(identifications, id_type, id_number)
	identification_supplied = documents is not None

	# The same meta guard the scalars above get, and it has to be here as well as
	# there: `changes` filtered itself, and a table written straight onto the
	# document would raise on a site that has not run the vocabulary patch.
	disabilities_supplied = disabilities is not None and meta.has_field(DISABILITIES_FIELD)

	# A JSON body arrives parsed; a form-encoded one arrives as a string. Both
	# are ordinary ways to call a whitelisted method, so neither is an error —
	# the same rule `rows_from` applies one level down.
	if isinstance(background, str):
		background = frappe.parse_json(background)

	if not isinstance(background, dict):
		background = {}

	# Filtered to the tables this caller actually spoke about *and* this site
	# actually has — the same two guards, for the same two reasons.
	tables = {
		key: rows_from(rows, BACKGROUND_TABLES[key][1], BACKGROUND_TABLES[key][2])
		for key, rows in background.items()
		if key in BACKGROUND_TABLES and rows is not None and meta.has_field(BACKGROUND_TABLES[key][0])
	}

	if changes or identification_supplied or disabilities_supplied or tables:
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
				# `set`, not assignment. Assigning a list of plain dicts to a
				# Table field leaves them as dicts, and the next save reaches
				# `is_new()` on something that has no such method — `set` is what
				# builds each row into a child Document first.
				document.set("identifications", _identification_rows(document, documents))

			if disabilities_supplied:
				document.set(DISABILITIES_FIELD, _disability_rows(disabilities))

			for key, rows in tables.items():
				field, _allowed, files = BACKGROUND_TABLES[key]
				document.set(field, _background_rows(document, rows, files))

			document.save()

		frappe.clear_document_cache(PROFILE_DOCTYPE, profile)


def _disability_rows(supplied) -> list[dict]:
	"""The rows a `Table MultiSelect` of `Disability` stores, from plain keys.

	Filtered against the register rather than stored as sent. These arrive from
	a browser and land in a Link column: a key that names no row would either be
	refused by core's own link validation — turning a registration into an error
	about a vocabulary the applicant never chose from — or, on a site where that
	row is later deleted, sit there pointing at nothing. Silently dropping an
	unknown key is the same choice `_offered_method` makes below and for the same
	reason: the applicant has not been asked to account for the society's
	configuration.

	Duplicates collapse. Somebody saying "Deafness" twice has said it once.
	"""
	if isinstance(supplied, str):
		supplied = frappe.parse_json(supplied)

	keys = []

	for value in supplied or []:
		key = str(value or "").strip()

		if key and key not in keys:
			keys.append(key)

	if not keys:
		return []

	known = {
		row["name"]
		for row in frappe.get_all(
			DISABILITY_DOCTYPE, filters={"name": ("in", keys)}, fields=["name"], ignore_permissions=True
		)
	}

	return [{"disability": key} for key in keys if key in known]


def _background_rows(document, rows: list[dict], files: tuple[str, ...]) -> list[dict]:
	"""One background table's rows, with every attachment on them made private.

	`evidence.secure` anchors the file to this profile and takes it off the
	public path — a scanned certificate is somebody's document, and a file left
	on `/files/` is readable by anybody who guesses the URL. The profile already
	exists whenever this runs (it is resolved before `_write_profile` is called),
	so unlike `secure_row_files` there is nothing to wait for.

	`rows_from` has already dropped the empty rows and refused any file that was
	not uploaded to this site, so what arrives here is a real answer.
	"""
	if not files:
		return rows

	for row in rows:
		for field in files:
			if row.get(field):
				row[field] = evidence.secure(document, row[field]) or row[field]

	return rows


def _offered_method(payment_method: str | None) -> str | None:
	"""The chosen way to pay, if the society offers it. None otherwise.

	Silent about a value it does not recognise, deliberately. The alternative is
	an error on a registration form for a choice the applicant has not committed
	to yet, and the consequence of dropping it is that the fee goes through the
	society's own first choice — which is what happened for every membership
	before anybody was asked. What must never happen is an unchecked name
	reaching the payments app as a gateway, and that is what this stops.
	"""
	from vmmsx.member.services import methods

	chosen = (payment_method or "").strip()

	return chosen if chosen and methods.is_offered(chosen) else None


def _identifications_supplied(
	identifications: list | None,
	id_type: str | None,
	id_number: str | None,
) -> list[dict] | None:
	"""What the caller said about their documents, or None for "leave them".

	Three answers, and the difference between the last two matters:

	    None    the caller said nothing about identity documents. The table is
	            not touched — which is what makes a caller that sends three
	            unrelated fields safe.
	    []      the caller said they hold none. The table is emptied.
	    [rows]  the caller said this is the set. The table becomes it.

	A list and a scalar pair are never merged: a caller sending the list has
	described the whole table, and folding a stray `id_type` in beside it would
	add a document nobody listed.
	"""
	if identifications is not None:
		return _checked_identifications(
			rows_from(identifications, IDENTIFICATION_FIELDS, IDENTIFICATION_FILE_FIELDS)
		)

	if id_type is None and id_number is None:
		return None

	# The single-document form, kept for every caller that sends one. Half of a
	# pair is refused rather than stored: a type with no number is not a document
	# anybody can check, and a number with no type is not one anybody can read.
	if not (str(id_type or "").strip() and str(id_number or "").strip()):
		frappe.throw(
			_("Identification Type and Identification Number must be provided together."),
			frappe.MandatoryError,
			title=_("Incomplete Identification"),
		)

	return _checked_identifications([{"id_type": id_type, "id_number": id_number}])


def _checked_identifications(rows: list[dict]) -> list[dict]:
	"""Clean the supplied documents, and refuse the two that cannot be stored.

	**Half a document.** `rows_from` drops a row that is entirely empty, which is
	the spare blank at the bottom of a form and not an answer. A row with one of
	the two filled in is different: somebody meant to enter a document and did
	not finish, and storing a passport with no number would put an unusable row
	in front of an approver.

	**The same type twice.** `application._assert_identification_complete` keys
	what somebody holds by type, so two rows of one type is a set where one of
	them cannot be seen. A person has one national card; two rows saying so is a
	mistake in a form, not a second document.
	"""
	cleaned = []
	seen = set()

	for row in rows:
		kind = str(row.get("id_type") or "").strip()
		number = str(row.get("id_number") or "").strip()

		if not (kind and number):
			frappe.throw(
				_("Every identification needs both a type and a number."),
				frappe.MandatoryError,
				title=_("Incomplete Identification"),
			)

		if kind in seen:
			frappe.throw(
				_("{0} is listed twice. Each kind of identification is entered once.").format(
					frappe.bold(_identification_label(kind))
				),
				frappe.ValidationError,
				title=_("Repeated Identification"),
			)

		seen.add(kind)
		cleaned.append(
			{
				"id_type": kind,
				"id_number": number,
				# Carried rather than dropped, and left as None where the caller
				# sent nothing: `_identification_rows` reads None as "say nothing
				# about the copy" and keeps whatever the profile already held.
				"attachment": str(row.get("attachment") or "").strip() or None,
			}
		)

	return cleaned


def _identification_label(id_type: str) -> str:
	"""The society's own word for a document type, for an error message."""
	return frappe.db.get_value("Identification Type", id_type, "identification_type_name") or id_type


def _identification_rows(document, supplied: list[dict]) -> list[dict]:
	"""The table this profile should now hold, keeping what the applicant did not send.

	**An attachment is not the applicant's to lose.** A branch that scanned
	somebody's national card attached it on the desk, and a person correcting the
	number printed beside it is not asking for the scan to be deleted. So a
	document whose row arrives with nothing to say about its copy keeps the file
	already against it, matched on the *type*, which is what identifies a row —
	matching on the number as well made the promise in this paragraph false for
	the only edit anybody actually makes.

	**And it is now theirs to supply.** A society that ticked "Requires an
	Attachment" makes the copy a condition of submission, so the form asks for one
	and a row may arrive carrying it. A supplied file wins over the held one —
	that is somebody replacing a copy, deliberately — and it is anchored to this
	profile and made private on the way in, which is what makes it readable by the
	people who may read the profile and by nobody else.

	**The first row is the primary one.** Ordering is the applicant's statement
	of which document is their main one, and it is the only statement they make
	about it: the flag itself is not in the allow-list, so a caller cannot send a
	table with two primaries in it.
	"""
	# Keyed by type alone, which is the identity of a row: a person has one
	# national card, and `_checked_identifications` refuses a set that says
	# otherwise. It was keyed by the type *and* the number, which meant the one
	# case this is here to protect — somebody correcting the number printed on a
	# document a branch had already scanned — changed the key and dropped the
	# scan, silently, every time.
	held = {row.id_type: row.attachment for row in document.get("identifications") or [] if row.id_type}

	rows = []

	for index, row in enumerate(supplied):
		supplied_file = row.get("attachment")
		attachment = evidence.secure(document, supplied_file) if supplied_file else held.get(row["id_type"])

		rows.append(
			{
				"id_type": row["id_type"],
				"id_number": row["id_number"],
				"attachment": attachment,
				"is_primary": 1 if index == 0 else 0,
			}
		)

	return rows


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
				# How they said they want to pay, so resuming a draft re-selects
				# it rather than asking again. Empty on a site that has not
				# installed the field yet, which reads as "not chosen".
				"payment_method": document.get(PAYMENT_METHOD_FIELD) or "",
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
	citizenship_status: str | None = None,
	residency_type: str | None = None,
	home_geo_node: str | None = None,
	country_of_residence: str | None = None,
	residence_address: str | None = None,
	disability_status: str | None = None,
	disability_needs: str | None = None,
	disabilities: list | None = None,
	profession: str | None = None,
	other_profession: str | None = None,
	background: dict | None = None,
	id_type: str | None = None,
	id_number: str | None = None,
	identifications: list | None = None,
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
			"citizenship_status": citizenship_status,
			"residency_type": residency_type,
			"home_geo_node": home_geo_node,
			"country_of_residence": country_of_residence,
			"residence_address": residence_address,
			DISABILITY_FIELD: disability_status,
			DISABILITY_NEEDS_FIELD: disability_needs,
			PROFESSION_FIELD: profession,
			OTHER_PROFESSION_FIELD: other_profession,
		},
		id_type=id_type,
		id_number=id_number,
		identifications=identifications,
		disabilities=disabilities,
		background=background,
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
	payment_method: str | None = None,
	answers: dict | None = None,
	declarations_accepted: list | dict | None = None,
) -> dict:
	"""Create or replace the caller's membership draft without starting payment or review.

	`payment_method` is how the applicant said they want to pay, and it is stored
	rather than acted on: no fee is requested until submission. It is checked
	against what the society actually offers here as well as at the moment the
	fee is requested — `payment.request` re-asks, because a draft can sit for a
	fortnight and a society can stop offering a method in that time.
	"""
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

	# `None` leaves whatever the draft already carries — a form that sends four
	# fields must not blank a fifth. An unrecognised method is dropped rather
	# than refused: the applicant is still choosing, the fee has not been asked
	# for, and `payment.request` falls back to the society's own first choice.
	if payment_method is not None:
		values[PAYMENT_METHOD_FIELD] = _offered_method(payment_method)

	document = _editable_registration("member")

	if document:
		if document.get("payment_transaction") and document.membership_type != membership_type:
			frappe.throw(
				_("The membership type cannot be changed after a payment request has been created."),
				frappe.ValidationError,
				title=_("Membership Type Locked"),
			)
		document = _save_existing_draft(document, values, answers, declarations_accepted)
	else:
		document = _register(
			{
				"doctype": MEMBERSHIP_DOCTYPE,
				"membership_type": membership_type,
				"geo_node": geo_node,
				PAYMENT_METHOD_FIELD: _offered_method(payment_method),
				**_intake_fields(first_name, last_name, phone, gender, date_of_birth),
			},
			answers=answers,
			accepted=declarations_accepted,
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
	citizenship_status: str | None = None,
	residency_type: str = "Local",
	home_geo_node: str | None = None,
	country_of_residence: str | None = None,
	residence_address: str | None = None,
	disability_status: str | None = None,
	disability_needs: str | None = None,
	disabilities: list | None = None,
	profession: str | None = None,
	other_profession: str | None = None,
	background: dict | None = None,
	id_type: str | None = None,
	id_number: str | None = None,
	identifications: list | None = None,
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
			"citizenship_status": citizenship_status,
			"residency_type": residency_type,
			"home_geo_node": home_geo_node,
			"country_of_residence": country_of_residence,
			"residence_address": residence_address,
			DISABILITY_FIELD: disability_status,
			DISABILITY_NEEDS_FIELD: disability_needs,
			PROFESSION_FIELD: profession,
			OTHER_PROFESSION_FIELD: other_profession,
		},
		id_type=id_type,
		id_number=id_number,
		identifications=identifications,
		disabilities=disabilities,
		background=background,
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
	payment_method: str | None = None,
	answers: dict | None = None,
	declarations_accepted: list | dict | None = None,
) -> dict:
	"""Register the caller as a member, and put the membership into motion.

	The self-service twin of `api/member.py::apply_for_membership`, asking for
	what the `register-as-a-member` Web Form asks for. The member satellite is
	created by the controller's own `before_insert`, inside the same narrow
	elevation the profile write uses, so nothing here has to know it exists.

	`profile_photo` lands on the Red Profile rather than on the membership, for
	the reason `_adopt_photo` sets out.

	`declarations_accepted` is the keys of the declarations the applicant ticked,
	exactly as on the volunteer door. `VMMS Membership` has carried a
	`declarations` table since the feature was built and
	`member.membership_types` has served the wording for it, but no door took the
	answer — so a society that wrote a membership declaration had it shown and
	never recorded. What is stored is the wording as it stood at this moment; see
	`registration/services/declarations.py`.

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
			# Checked against what the society offers before it is stored, and
			# checked again by `payment.request` before any money is asked for.
			PAYMENT_METHOD_FIELD: _offered_method(payment_method),
			**_intake_fields(first_name, last_name, phone, gender, date_of_birth),
		},
		answers=answers,
		accepted=declarations_accepted,
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

	return {field: supplied[field] for field in proof.CLAIM_FIELDS if supplied.get(field) not in (None, "")}


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
