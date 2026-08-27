# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The two-doctype write — one web form, a Red Profile and an application.

A native Frappe Web Form writes exactly one document. Registration needs two:
core's identity spine, and the vmmsx record that hangs off it. This module is
the seam between them, and it runs in `before_insert` on the governed doctype —
the only moment that is both after the form's values have landed on the document
and before the framework checks that `red_profile` (or `member`) is filled in.

**One Red Profile per login, ever.** The chain is `frappe.session.user ->
Red Profile.user`, and core makes that column unique. So somebody who registered
as a volunteer in March and comes back to register as a member in August is
*resolved*, not created again: `claim_profile()` finds the profile carrying their
login and returns it. There is no second identity to reconcile, and the affiliation
index on that one profile ends up carrying both rows — which is the whole point of
Design 2 and the reason both satellites register their own provider.

**Identity goes to Red Profile and stays there.** The form collects what a
profile needs, because a signup only ever captured a name and an email. Those
values are written onto the profile and then **cleared from the application**,
so a saved vmmsx record carries no name, no phone and no date of birth — the
same invariant the satellites have held from the start. The intake fields are a
transient buffer between an HTTP POST and core's spine, they are documented as
such on the doctype, and `tests/test_two_doctype_write.py` asserts they are empty
on every persisted record.

**The email is never taken from the form.** It is read from the `User` doing the
registering. An email on a public form is a claim about who you are; the login
is the site's own answer to that question, and it is the one that must win. This
is also what makes adoption safe: see `_adopt`.

**What is filled in and what is not.** A field core already knows is never
overwritten. Registration adds what the society does not have; it does not get to
contradict what it does. A person correcting their own name does it on their
profile, not by registering again.

**Elevation, and its justification.** A self-registering applicant holds no
permission on `Red Profile` and must not be given any — it is core's identity
spine and it holds every person the society knows. The profile is created *on
their behalf*, bound to *their own* login, from values they themselves supplied,
and nothing else on the site is touched. That is the narrowest possible reading
of "write one row for the person asking", and it is why the elevation wraps the
insert and nothing more.
"""

from contextlib import contextmanager

import frappe
from frappe import _

from vmmsx import elevation

PROFILE_DOCTYPE = "Red Profile"
USER_DOCTYPE = "User"

# The transient fields a registration form collects for core's spine. Present on
# both governed doctypes, consumed here, and cleared before the record is
# written. `applicant_email` is deliberately absent from this list and from the
# schema: the login is the identity.
INTAKE_FIELDS = {
	"applicant_first_name": "first_name",
	"applicant_last_name": "last_name",
	"applicant_phone": "phone",
	"applicant_gender": "gender",
	"applicant_date_of_birth": "date_of_birth",
}

# Set on a document to say "this insert is somebody registering themselves".
# A desk clerk enrolling a person from a paper form must never pick up the
# clerk's own profile, so the claim only runs when this is true — which it is
# for a native web form (Frappe's own `in_web_form` flag) or when a caller says
# so explicitly.
SELF_REGISTRATION_FLAG = "vmms_self_registration"

# Set once the registration path has put a document into motion, so the save the
# engine performs inside `submit` does not re-enter and submit it again.
SUBMITTING_FLAG = "vmms_registration_submitting"

# Set by the self-service draft endpoints. They still need the self-registration
# claim in `before_insert` — that is what binds the record to the caller's Red
# Profile — but, unlike a native Web Form, they explicitly have a later Submit
# button. Keeping this as a document flag makes the exception last for exactly
# one insert and keeps the ordinary Web Form and desk paths unchanged.
DRAFT_ONLY_FLAG = "vmms_registration_draft_only"

# Set by `claim_profile` when it actually claimed, so `submit_once` can tell a
# registration apart from an ordinary desk insert on the same doctype.
CLAIMED_FLAG = "vmms_registration_claimed"


@contextmanager
def as_system():
	"""Run one write as the system rather than as the applicant.

	Public, because the two controllers need the same elevation for the one
	other write registration performs — creating the member satellite — and a
	second private copy of this would be a second thing to audit.

	The mechanics are `vmmsx.elevation`, which is where the *session* is put
	back afterwards. A bare `set_user` round trip signs the applicant out — see
	that module for what it overwrites and when the damage surfaces.
	"""
	with elevation.as_system():
		yield


# --- is this somebody registering themselves? -----------------------------


def is_self_registration(doc) -> bool:
	"""Is this insert a person registering themselves, rather than a clerk?

	Two ways to be true, and they are the same statement made by two different
	callers. Frappe sets `in_web_form` for the duration of a web form submission,
	which is exactly the case this whole module exists for; the explicit flag is
	for a caller that means it and is not a form.

	A Guest is never self-registering: both forms require a login, because a
	registration has to belong to somebody.
	"""
	if frappe.session.user in ("Guest", None, ""):
		return False

	return bool(frappe.flags.get("in_web_form") or doc.flags.get(SELF_REGISTRATION_FLAG))


# --- the claim ------------------------------------------------------------


def claim_profile(doc) -> str | None:
	"""The Red Profile for whoever is registering, resolved or created.

	Returns the profile name, or None when this insert is not a self-registration
	at all — which is the ordinary desk path and must be left completely alone.

	The intake fields are consumed and cleared whether the profile was created or
	merely found, so a returning registrant leaves no more identity on their
	second application than on their first.
	"""
	if not is_self_registration(doc):
		return None

	values = _take_intake(doc)
	profile = for_user(frappe.session.user, values)

	if profile:
		doc.flags[CLAIMED_FLAG] = True

	return profile


def for_user(user: str, values: dict | None = None) -> str | None:
	"""The Red Profile carrying this login — found, adopted or created.

	Three outcomes, in the order they are tried:

	1. **Found.** A profile whose `user` is this login already exists. This is
	   the cross-registration case and it is the common one after the first
	   time. Nothing is created.
	2. **Adopted.** A profile with this person's email exists but carries no
	   login — a member the branch registered from paper who has now made
	   themselves an account. Binding the two is right: the alternative is core
	   refusing the insert on its unique email and the person being stuck.
	3. **Created.** Neither, so the society is meeting this person for the first
	   time.
	"""
	account = frappe.db.get_value(
		USER_DOCTYPE, user, ["name", "first_name", "last_name", "email"], as_dict=True
	)

	if not account:
		return None

	existing = frappe.db.get_value(PROFILE_DOCTYPE, {"user": user}, "name")

	if existing:
		_enrich(existing, values)

		return existing

	email = (account.email or account.name or "").strip().lower()
	adopted = _adopt(email, user)

	if adopted:
		_enrich(adopted, values)

		return adopted

	return _create(account, email, values)


def _adopt(email: str, user: str) -> str | None:
	"""Bind an existing, login-less profile with this email to this login.

	**Why this is safe.** The email is not the applicant's claim — it is read
	from the `User` record, and a Frappe account is reachable only by whoever
	controls that mailbox, because signup issues a random password and mails the
	link to set it. So "the login whose email is X" and "the person who can read
	X's mail" are the same person by the time this runs.

	**And why it stops short.** A profile already bound to a *different* login is
	never touched. That is two identities pointing at one person and it is an
	administrator's problem, not something a public form may resolve by
	overwriting whichever it found. The refusal says so.
	"""
	if not email:
		return None

	found = frappe.db.get_value(PROFILE_DOCTYPE, {"email": email}, ["name", "user"], as_dict=True)

	if not found:
		return None

	if found.user and found.user != user:
		frappe.throw(
			_(
				"A profile for this email address already belongs to another login. An"
				" administrator has to resolve that before you can register."
			),
			frappe.ValidationError,
			title=_("Profile Already Claimed"),
		)

	if not found.user:
		with as_system():
			frappe.db.set_value(PROFILE_DOCTYPE, found.name, "user", user)

		frappe.clear_document_cache(PROFILE_DOCTYPE, found.name)

	return found.name


def _create(account, email: str, values: dict | None) -> str:
	"""A new Red Profile for a person the society has not met.

	Names fall back to the account's own, because a Frappe signup puts the whole
	name it was given into `first_name` and leaves `last_name` empty. A profile
	with an empty `last_name` would be refused by core, so the fallback is not a
	nicety: it is what makes a registration that collected nothing still work.
	"""
	values = values or {}

	first_name = values.get("first_name") or account.first_name or email.split("@")[0]
	last_name = values.get("last_name") or account.last_name or first_name

	profile = {
		"doctype": PROFILE_DOCTYPE,
		"first_name": first_name,
		"last_name": last_name,
		"email": email,
		"user": account.name,
	}

	for field in ("phone", "gender", "date_of_birth"):
		if values.get(field):
			profile[field] = values[field]

	with as_system():
		return frappe.get_doc(profile).insert().name


def _enrich(profile: str, values: dict | None) -> None:
	"""Fill in what core does not know yet. Never overwrite what it does.

	The rule in one line: registration *adds*. Somebody re-registering with a
	different phone number is not how a phone number gets corrected — that is an
	edit on their own profile — and letting a form silently replace identity core
	already holds would make the spine's value depend on who filled in a form
	last.
	"""
	if not values:
		return

	current = frappe.db.get_value(
		PROFILE_DOCTYPE, profile, ["phone", "gender", "date_of_birth"], as_dict=True
	)

	if not current:
		return

	missing = {
		field: values[field]
		for field in ("phone", "gender", "date_of_birth")
		if values.get(field) and not current.get(field)
	}

	if not missing:
		return

	with as_system():
		frappe.db.set_value(PROFILE_DOCTYPE, profile, missing)

	frappe.clear_document_cache(PROFILE_DOCTYPE, profile)


def place(profile: str, geo_node: str | None) -> bool:
	"""Record where this person is, on their profile, if core does not know yet.

	`home_geo_node` is core's own field for a person's place in the tree, and a
	registration is the one moment somebody states it about themselves. Filled
	only when empty, by the same rule as everything else here.
	"""
	if not (profile and geo_node):
		return False

	if frappe.db.get_value(PROFILE_DOCTYPE, profile, "home_geo_node"):
		return False

	with as_system():
		frappe.db.set_value(PROFILE_DOCTYPE, profile, "home_geo_node", geo_node)

	frappe.clear_document_cache(PROFILE_DOCTYPE, profile)

	return True


# --- the transient buffer -------------------------------------------------


def _take_intake(doc) -> dict:
	"""Read the intake fields off the document and blank them in one pass.

	Blanked here rather than after the profile write, so there is no path — an
	exception in the middle, a caller that returns early — on which a value
	survives onto the saved record.
	"""
	values = {}

	for field, profile_field in INTAKE_FIELDS.items():
		if not doc.meta.has_field(field):
			continue

		value = doc.get(field)

		if value not in (None, ""):
			values[profile_field] = value

		doc.set(field, None)

	return values


def clear_intake(doc) -> None:
	"""Blank the intake fields, whatever happened. Belt and braces.

	Called from `validate` on both governed doctypes, so a record saved by any
	path at all — a desk user who typed into the section, an import, a future
	API — cannot persist identity onto a satellite. `_take_intake` has already
	blanked them on the registration path; this is the guarantee that does not
	depend on that path having run.
	"""
	for field in INTAKE_FIELDS:
		if doc.meta.has_field(field) and doc.get(field) not in (None, ""):
			doc.set(field, None)


# --- putting the registration into motion ---------------------------------


def submit_once(doc, submit) -> None:
	"""Put a self-registered document into motion, exactly once.

	**Why this exists at all.** A native web form calls `insert()` and stops.
	Every other way into this app — the API endpoints, a desk clerk following up
	— inserts and then calls the module's own `submit()`. A registration has no
	second step and nobody to press a button, so the document has to enter its
	lifecycle on the save that created it, or it sits at Draft forever with
	nothing routed to anybody.

	**Why it is scoped so tightly.** Only a document `claim_profile` actually
	claimed is submitted. An ordinary desk insert, an import and every existing
	test create a draft and submit it deliberately, and none of them may start
	behaving differently because this module now exists.

	`submit` is passed in rather than imported, so this file knows nothing about
	volunteering or membership — it knows that a registration has a next step and
	that its owner decides what that is.
	"""
	if not doc.flags.get(CLAIMED_FLAG) or doc.flags.get(SUBMITTING_FLAG) or doc.flags.get(DRAFT_ONLY_FLAG):
		return

	doc.flags[SUBMITTING_FLAG] = True

	try:
		# The applicant created their own record and may do so; what happens next
		# is the approval engine writing its own fields — state, stage, the queue
		# — on it. No applicant holds write permission on those, and none should:
		# the permission that matters was the create the web form performed, and
		# the engine's person-gate governs every decision after it.
		with as_system():
			submit(doc)
	finally:
		doc.flags[SUBMITTING_FLAG] = False
