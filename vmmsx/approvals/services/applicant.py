# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Who an approval is *about*, for any governed doctype.

A review queue that lists `MSHIP-00042` and a stage label is not a queue
somebody can work. The first question an approver asks is whose application
this is, and until this module existed the answer was only available for one of
the two governed doctypes — `api/volunteer.py::get_decision` built it by hand
out of the volunteer application's own fields, and a membership arrived at the
same screen with a docname and nothing else.

**Resolved from the workflow, not from a list of doctypes.** `VMMS Approval
Workflow.applicant_field` already names the field that says who applied — it is
what `engine.py` reads to know whose reapplication cooldown to check — and the
two workflows on a full site point it at two different things:

    VMMS Volunteer Application . red_profile  ->  Red Profile
    VMMS Membership            . member       ->  VMMS Member -> Red Profile

So this module follows the link rather than knowing where it goes. One hop if
the field points at a Red Profile, two if it points at something that carries
one, and nothing at all if it points somewhere with no identity behind it —
which is not an error, it is a governed doctype whose subject is not a person.
A third registration governed next year is a third `applicant_field` and no
edit here.

**An unset `applicant_field` falls back to `owner`, and this is not an
invention.** `config.applicant_of()` has always read `workflow.applicant_field
or "owner"` for the re-application cooldown, and the doctype's own field
description says so out loud: *"Empty falls back to the document's owner."* The
same rule holds here, because the failure it prevents is the one this module
exists for — a society that configured a workflow without naming the applicant
field would otherwise get a review queue of docnames again, which is precisely
the state that was just fixed. A login is turned back into a person through
core's `Red Profile.user`, so what an approver reads is still a name and a face
rather than an email address.

**Read live, stored nowhere**, the same invariant `volunteer/services/
identity.py` and `member/services/identity.py` both keep: the application holds
a link and no copy of the name, so correcting a Red Profile corrects every queue
that shows it, and there is no second answer to who somebody is.

**The narrow set, and no more.** A queue row needs a name, a face and a way to
make contact; it does not need a date of birth. Those four fields are what this
returns, and widening the tuple is a decision somebody has to make here rather
than something that happens by pulling a whole document.
"""

import frappe

PROFILE_DOCTYPE = "Red Profile"

#: The field a satellite record carries to point at the person behind it. Both
#: `VMMS Volunteer` and `VMMS Member` use this name, which is core's convention
#: rather than this app's, and a doctype that does not have it simply resolves
#: to no profile.
PROFILE_FIELD = "red_profile"

#: What every document has, and what an unset `applicant_field` means. See the
#: module docstring and `config.applicant_of()`.
OWNER_FIELD = "owner"

#: What a queue row and a decision header are allowed to show. Deliberately
#: shorter than either identity module's `_READABLE`: this is the "which person
#: is this" set, not the dossier.
_SHOWN = ("full_name", "first_name", "last_name", "email", "phone", "profile_photo")


def of(doc, workflow) -> dict | None:
	"""The person this approval is about, or None when there is not one.

	`workflow` is the `VMMS Approval Workflow` governing `doc`, already loaded
	by whoever is asking — `engine.status()` has it in hand, and re-fetching it
	here would be a second read of a document the caller is holding.
	"""
	# The same fallback `config.applicant_of()` makes, spelled the same way, so
	# the cooldown and the queue never disagree about who applied.
	field = (workflow.applicant_field or "").strip() or OWNER_FIELD
	value = doc.get(field)

	if not value:
		return None

	subject = _link_target(doc.doctype, field)
	profile = _profile_of(subject, value) or _profile_of_login(field, value)

	if not profile:
		# A governed doctype whose applicant field points at something with no
		# identity behind it. The docname is the honest answer — better than an
		# empty header — and `full_name` is what every caller renders.
		return {
			"doctype": subject,
			"name": value,
			"red_profile": None,
			"full_name": value,
			"email": None,
			"phone": None,
			"photo": None,
		}

	person = frappe.db.get_value(PROFILE_DOCTYPE, profile, _SHOWN, as_dict=True) or {}

	return {
		"doctype": subject,
		"name": value,
		"red_profile": profile,
		"full_name": _display_name(person, profile),
		"email": person.get("email"),
		"phone": person.get("phone"),
		# Under `photo` rather than `profile_photo`, because what a screen draws
		# is an avatar and it should not have to know which doctype's field
		# spelling reached it.
		"photo": person.get("profile_photo"),
	}


def _link_target(doctype: str, field: str) -> str | None:
	"""What the applicant field links to, read off the schema.

	`None` for a field that is not a Link — a workflow may name a Data field,
	and the honest answer to "which doctype" is then that there isn't one.
	"""
	meta = frappe.get_meta(doctype).get_field(field)

	if not meta or meta.fieldtype != "Link":
		return None

	return meta.options


def _profile_of(subject: str | None, value: str) -> str | None:
	"""The Red Profile behind the applicant field's value. One hop, or two.

	The value *is* a profile when the field points straight at one; otherwise
	the linked record is asked for its own, and a record that carries no
	`red_profile` answers None rather than throwing. That last case is what
	keeps this working on a site whose third governed doctype is anchored on
	something other than a person.
	"""
	if not subject:
		return None

	if subject == PROFILE_DOCTYPE:
		return value

	if not frappe.get_meta(subject).get_field(PROFILE_FIELD):
		return None

	return frappe.db.get_value(subject, value, PROFILE_FIELD)


def _profile_of_login(field: str, value: str) -> str | None:
	"""A Red Profile found through core's `user` link, for the owner fallback.

	Only for `owner`, and deliberately not for any other field: a Data field
	that happens to hold something shaped like an email is not a claim about who
	anybody is, and searching profiles by it would turn a stray value into a
	name on an approver's screen.

	`None` when the login has no profile, which is ordinary — an administrator
	or a clerk filing on somebody's behalf is a real owner with no Red Profile
	of their own, and the docname fallback above is the honest answer there.
	"""
	if field != OWNER_FIELD:
		return None

	return frappe.db.get_value(PROFILE_DOCTYPE, {"user": value}, "name")


def _display_name(person: dict, profile: str) -> str:
	"""What to call somebody, falling back the way both identity modules do.

	A record naming a record is worse than nothing only if nothing were an
	option, and on a queue row it is not: an approver has to be able to tell two
	applications apart.
	"""
	full = (person.get("full_name") or "").strip()

	if full:
		return full

	composed = " ".join(
		part for part in (person.get("first_name"), person.get("last_name")) if part
	).strip()

	return composed or profile
