# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Who else hears about it, when the person it concerns is a child.

A society that accepts sixteen-year-olds takes on an obligation its own
correspondence has to reflect: the parent or guardian who consented to the
volunteering is entitled to know what their child is being asked to do. Before
this module the society wrote to the young person and to nobody else, and the
guardian's details existed only as a row on an application that had already been
decided.

**Three questions, and they are separate on purpose.**

    who is this person's guardian     `of()`, from `VMMS Guardian`
    are they still a child            `is_minor()`, from the date of birth
    so what do we do about it         `emails_for()` / `phones_for()`

Nothing here decides *what* is sent. The notification services own that, and each
of them asks this module the same question in the same words — see
`lifecycle.notify`'s `cc`, `direct.tell`'s `about`, and `audience.emails`.

**The age is asked at the moment of sending, every time.** This is the rule that
matters most and the one that is easiest to get wrong. `is_minor` on an
application is frozen into the decision the moment it is approved; if the copy
rule read that flag, a society would go on writing to somebody's parents years
after they turned eighteen, which is a disclosure of an adult's business to a
third party and not a courtesy. So the question is asked against the date of
birth and the society's own age of majority, at send time, and the answer changes
by itself on a birthday. `volunteer/services/application.is_minor` already draws
this distinction for the approval gate and gives the argument in full.

**A society that has not set an age of majority copies nobody.** Same fail-open
direction as every other reader of that setting: guessing eighteen would be this
app inventing a law, and a society that has not configured minor handling has not
asked for its post to be copied to anybody.

**A guardian with no email address is on the record and is not written to.** It
is not an error and it is not fixed here. Somebody enrolled at a branch from a
paper form may have given a phone number only, and refusing the notification —
or the deployment behind it — over a missing address would be the wrong trade in
exactly the way `lifecycle.notify` describes for the applicant's own address.
"""

import frappe
from frappe.utils import getdate, today

from vmmsx.registration.services import society as registration_society

GUARDIAN_DOCTYPE = "VMMS Guardian"
PROFILE_DOCTYPE = "Red Profile"
CONSENT_FIELD = "guardian_consents"

# What is copied from an application's consent row onto the standing record.
# An allow-list rather than a loop over the child table's fields, for the reason
# `proof.CLAIM_FIELDS` gives: a field added to the consent row next year does not
# silently start being copied onto a person.
_ADOPTED = (
	"guardian_name",
	"relationship",
	"phone",
	"email",
	"consent_given",
	"consent_date",
	"verification_method",
	"consent_evidence",
	"is_verified",
)


# --- who ------------------------------------------------------------------


def of(red_profile: str | None) -> list[dict]:
	"""The standing guardians recorded for this person, active ones only.

	Ordered oldest first, so a household with two guardians is addressed in the
	order the society recorded them rather than in whatever order the database
	felt like.
	"""
	if not red_profile:
		return []

	if not frappe.db.exists("DocType", GUARDIAN_DOCTYPE):
		# Mid-migrate on a site that has not synced this module yet. Nobody to
		# copy is the honest answer, and it keeps every notification working.
		return []

	return frappe.get_all(
		GUARDIAN_DOCTYPE,
		filters={"red_profile": red_profile, "is_active": 1},
		fields=["name", "guardian_name", "relationship", "phone", "email", "is_verified"],
		order_by="creation asc",
		ignore_permissions=True,
	)


def profile_of_volunteer(volunteer: str | None) -> str | None:
	"""The Red Profile behind a volunteer record, or None.

	The same walk `direct.login_of` makes and stops one hop earlier. Written here
	rather than reached for inline so that a caller cannot accidentally look for
	a person on a satellite that deliberately holds none.
	"""
	if not volunteer:
		return None

	return frappe.db.get_value("VMMS Volunteer", volunteer, "red_profile") or None


# --- still a child? -------------------------------------------------------


def is_minor(red_profile: str | None, reference=None) -> bool:
	"""Is this person below the age their society treats as adult, today?

	False when the society has set no age of majority, and false when nobody has
	recorded a date of birth. Both are "no rule fires", for the reasons the
	module docstring and `registration/services/society.minor_age` give.
	"""
	threshold = registration_society.minor_age()

	if not (threshold and red_profile):
		return False

	born = frappe.db.get_value(PROFILE_DOCTYPE, red_profile, "date_of_birth")
	age = _age(born, reference)

	return age is not None and age < threshold


def minors_among(red_profiles) -> set[str]:
	"""Which of these people are children today, in one query.

	The bulk form, for the audience resolvers: a national announcement resolves
	tens of thousands of profiles and asking `is_minor` per person would turn
	publishing into a timeout. Same rule, same threshold, one read.
	"""
	threshold = registration_society.minor_age()
	wanted = {name for name in (red_profiles or set()) if name}

	if not (threshold and wanted):
		return set()

	rows = frappe.get_all(
		PROFILE_DOCTYPE,
		filters={"name": ["in", sorted(wanted)], "date_of_birth": ["is", "set"]},
		fields=["name", "date_of_birth"],
		ignore_permissions=True,
	)

	return {
		row.name
		for row in rows
		if (age := _age(row.date_of_birth)) is not None and age < threshold
	}


def _age(born, reference=None) -> int | None:
	"""Whole years between a date of birth and a reference date, or None.

	The same calculation `volunteer/services/application._age_of` makes, against
	a bare date rather than an application, because this module asks it of a
	person who may never have filled one in.
	"""
	if not born:
		return None

	born = getdate(born)
	on = getdate(reference or today())

	return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


# --- so what do we do about it --------------------------------------------


def emails_for(red_profile: str | None, reference=None) -> list[str]:
	"""Addresses to copy on anything sent to this person. Empty for an adult."""
	if not is_minor(red_profile, reference):
		return []

	return sorted({(row.email or "").strip() for row in of(red_profile) if (row.email or "").strip()})


def phones_for(red_profile: str | None, reference=None) -> list[str]:
	"""Numbers to copy on anything texted to this person. Empty for an adult."""
	if not is_minor(red_profile, reference):
		return []

	return sorted({(row.phone or "").strip() for row in of(red_profile) if (row.phone or "").strip()})


def emails_for_volunteer(volunteer: str | None, reference=None) -> list[str]:
	"""The same answer, for a caller holding a volunteer record rather than a person."""
	return emails_for(profile_of_volunteer(volunteer), reference)


def emails_for_many(red_profiles, reference=None) -> list[str]:
	"""Every guardian address across a whole audience, deduplicated.

	Two queries whatever the size of the audience: one for who is a child, one
	for their guardians. Deduplicated and sorted for the reason
	`audience.phones` gives — a household with two young volunteers is written to
	once, and an audience built twice is the same audience.
	"""
	return _contacts_for_many(red_profiles, "email", reference)


def phones_for_many(red_profiles, reference=None) -> list[str]:
	"""Every guardian number across a whole audience, deduplicated."""
	return _contacts_for_many(red_profiles, "phone", reference)


def _contacts_for_many(red_profiles, field: str, reference=None) -> list[str]:
	minors = minors_among(red_profiles)

	if not minors:
		return []

	rows = frappe.get_all(
		GUARDIAN_DOCTYPE,
		filters={"red_profile": ["in", sorted(minors)], "is_active": 1, field: ["is", "set"]},
		pluck=field,
		ignore_permissions=True,
	)

	return sorted({(row or "").strip() for row in rows if (row or "").strip()})


# --- carrying an application's guardians onto the person ------------------


def adopt(application) -> list[str]:
	"""Copy an accepted application's guardian rows onto the person. Returns new names.

	**Called once, when the application produces a volunteer**, from the same
	seam that creates the volunteer record: the guardian becomes a standing fact
	about a person at the moment the society accepts that person, and not before.
	A draft's guardian is a claim on a form.

	**Idempotent, keyed on the guardian rather than on the application.** A person
	whose record already names this guardian — same name, same phone — gains
	nothing here, so re-running acceptance, or a second application from somebody
	who volunteered before, does not leave a society writing to the same parent
	twice. Matching on the phone number rather than the email because the phone is
	the required field: a guardian with no address is exactly the case that would
	otherwise be duplicated on every pass.

	**Never raises.** A guardian record that could not be written must not roll
	back somebody's acceptance. The consent rows stay on the application either
	way, so nothing is lost that cannot be recovered by a coordinator, and the
	failure is logged rather than swallowed silently.
	"""
	rows = application.get(CONSENT_FIELD) or []

	if not rows:
		return []

	red_profile = application.get("red_profile")

	if not red_profile:
		return []

	created = []

	for row in rows:
		if not (row.get("guardian_name") and row.get("phone")):
			# A half-filled row on a draft that was accepted anyway. Nothing to
			# write to, and a guardian record with no way to reach anybody is
			# worse than none.
			continue

		if _already_recorded(red_profile, row):
			continue

		try:
			document = frappe.get_doc(
				{
					"doctype": GUARDIAN_DOCTYPE,
					"red_profile": red_profile,
					"is_active": 1,
					"source_application": application.name,
					**{field: row.get(field) for field in _ADOPTED},
				}
			)

			document.insert(ignore_permissions=True)
			created.append(document.name)
		except Exception:
			frappe.log_error(
				title="vmmsx: could not record a guardian",
				message=frappe.get_traceback(),
			)

	return created


def _already_recorded(red_profile: str, row) -> bool:
	"""Does this person's record already name this guardian?"""
	return bool(
		frappe.db.exists(
			GUARDIAN_DOCTYPE,
			{
				"red_profile": red_profile,
				"guardian_name": row.get("guardian_name"),
				"phone": row.get("phone"),
			},
		)
	)
