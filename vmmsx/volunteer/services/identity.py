# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Reading a person — always from Red Profile, never from a copy.

`VMMS Volunteer` stores no name, no email and no phone. It stores a link to a
Red Profile and nothing else about who the person is, because a second copy of a
person is a second answer to who they are, and the two diverge the first time
somebody corrects one of them. There is no `fetch_from` on the volunteer either:
a fetched value is a stored copy wearing a different hat.

So every display name, every queue entry and every field handed to HR comes
through here, and here reads core.

**Widening what this module reads is not widening what the record holds.** The
allow-list below grew, so the volunteer page can show a person rather than a
docname; the volunteer record gained no column, no `fetch_from` and no copy. The
two are independent, and the second is the invariant: every value below is read
from Red Profile at the moment somebody looks, and forgotten again.

**Why this is forty lines rather than an import from the Member module.** Member
has the same reader, and the obvious move is to share one. It is the wrong move:
Member and Volunteer are sibling satellites, and a volunteer module that stops
working when the member module is uninstalled has acquired a dependency on
something it has nothing to do with. What the two must agree on is the *source* —
Red Profile, core's spine — and they do, because neither of them reads anything
else. That is the agreement that matters; sharing the getter would add coupling
without adding it.

This module is read-only by construction: nothing in it writes to Red Profile.
Identity is core's to own; vmmsx borrows it.
"""

import frappe

PROFILE_DOCTYPE = "Red Profile"

# The fields this module is willing to surface. Named explicitly so a new field
# on core's Red Profile never starts leaking through a vmmsx DTO by accident.
#
# **The last four were added deliberately, and the decision is recorded here
# rather than in a commit message.** A coordinator opening a volunteer record
# was being shown a Red Profile docname and nothing else, and had to open the
# identity record in another tab to find out who they were looking at. Gender,
# date of birth, preferred language and the profile photo are what a volunteer
# page has to show to be a working surface: the photo and the name to confirm
# the right person, the language to know how to contact them, and the two HR
# facts because a volunteering office is asked for them constantly.
#
# The widening is exactly those four and is **not** a general opening. Two
# things follow from that and are tested:
#
# 1. `_WITHHELD` below stays out, whatever core adds to the spine.
# 2. Surfacing a field on a screen is not the same decision as pushing it into
#    another app's register. What vmmsx hands to Frappe HR is a separate,
#    narrower list — `hr._OUTBOUND` — and it did not widen with this. Before
#    this change the HR guarantee rested on gender and date of birth being
#    absent from *this* tuple; it now rests on the seam's own list, which is
#    where a promise about HR belongs.
#
# **The twelfth was added deliberately too, and it is the reason the guard
# exists.** `home_geo_node` on Red Profile is core's field for where a person
# *lives*. The coordinator's view has to show it, because "Home Area" and
# "Serving Branch" are different questions and a coordinator deciding who to
# send somewhere needs both — and the obvious way to show it was to copy it onto
# the volunteer, which would have been a second answer to where somebody lives,
# wrong the first time one of them was corrected. Reading it here instead is the
# whole point of the allow-list: surfacing a field of core's is cheap and safe,
# and storing one is neither. `VMMS Volunteer.home_geo_node` is a different
# field on a different doctype answering a different question (it is the
# Serving Branch, and the fieldname is historical); the two are never merged.
_READABLE = (
	"full_name",
	"first_name",
	"middle_name",
	"last_name",
	"email",
	"phone",
	"user",
	"gender",
	"date_of_birth",
	"preferred_language",
	"profile_photo",
	"home_geo_node",
	"country_of_citizenship",
	"citizenship_status",
	"residency_type",
	"country_of_residence",
	"residence_address",
	# **This is not the withheld one.** Core keeps `disability` off the spine for
	# a gated extension it has not built yet, and the line below still refuses
	# that name out loud. `vmms_disability_status` is a different field with a
	# different owner: it is vmmsx's own Custom Field, it holds an *answer* to a
	# question the applicant was asked and could decline — see
	# `patches/install_disability_fields.py` — and it is here because the branch
	# reviewing an application is the one who has to arrange the adjustment. The
	# free-text `vmms_disability_needs` is deliberately absent: it is what
	# somebody chose to write about themselves, it is read on the record by
	# whoever may open it, and a general reader has no use for it.
	"vmms_disability_status",
	# What kind of work this person does — vmmsx's own Custom Field, installed by
	# `patches/install_background_fields.py`. A scalar and a vocabulary key,
	# surfaced for the reason `home_geo_node` is: a coordinator deciding who to
	# ask about a health post wants to know who is a nurse, and the alternative
	# was copying it onto the volunteer record, where it would be a second answer
	# that goes stale. The six *tables* beside it are not here — an allow-list of
	# scalars is the wrong instrument for a child table, and `background()` below
	# is where those are read and where what is left out of them is argued.
	"vmms_profession",
	"vmms_other_profession",
)

# The sensitive set, named so that keeping it out is a decision this file states
# rather than an omission somebody has to notice. Core deliberately holds these
# off the identity spine for a later gated extension; the spelling here is core's
# own, from `red_profile`'s tests, so that the day they arrive this app is
# already refusing them by the right names.
#
# They are not merely absent from `_READABLE` — asking for one is refused, out
# loud. A caller that has been quietly handed a dict with the key missing goes on
# to render an empty field; a caller that is refused gets told that this is not
# vmmsx's data to surface.
_WITHHELD = ("blood_group", "medical_conditions", "next_of_kin", "disability")


def profile_name(volunteer) -> str:
	"""The Red Profile docname behind a volunteer."""
	return volunteer.red_profile


def read(volunteer, fields: tuple[str, ...] = _READABLE) -> dict:
	"""The person behind this volunteer, as a plain dict of allowed fields.

	`get_value` rather than `get_doc`: a whole Red Profile carries its
	affiliation index, and that index is gated on read by core. Pulling the
	document here to take a name would step around a boundary this app has no
	business stepping around — see core's note on the read gate.
	"""
	requested = tuple(fields)
	refused = [field for field in requested if field in _WITHHELD]

	if refused:
		raise PermissionError(
			f"{', '.join(sorted(refused))} is not vmmsx's to surface. The sensitive set belongs to"
			" core's gated extension; see _WITHHELD in vmmsx/volunteer/services/identity.py."
		)

	# The allow-list *and* the meta. One of the names in `_READABLE` is a Custom
	# Field rather than a column of core's doctype, and a site between syncing
	# this module and running its patch does not have it — asking `get_value`
	# for a column that is not there raises, and a volunteer page that will not
	# render because a migration is half done is worse than one missing a field.
	meta = frappe.get_meta(PROFILE_DOCTYPE)
	allowed = tuple(field for field in requested if field in _READABLE and meta.has_field(field))
	values = frappe.db.get_value(PROFILE_DOCTYPE, volunteer.red_profile, allowed, as_dict=True)

	return dict(values or {})


# The six background tables, and what a coordinator's screen is given of each.
#
# **Attachments are in none of them, deliberately.** Every one of these tables
# can carry a scanned certificate, and `registration._background_rows` makes each
# file private and anchors it to the Red Profile — so the people who can open one
# are the people who can read that profile, which a branch coordinator working
# from the console generally cannot. Handing out a URL that resolves to a refusal
# would be a link that looks like evidence and is not. A verifier opens the
# profile on the desk, which is where the files are.
#
# **Everything else is here, referees included.** A referee's phone number looks
# like the sensitive item to withhold, and withholding it would make the referee
# useless: the row exists precisely so that somebody deciding on an application
# can ring them. What governs this is who may read the dossier at all, which is
# the scope role — not a second filter inside it that quietly empties the field.
_BACKGROUND = {
	"education": ("institution", "level", "qualification", "started_in", "finished_in", "is_ongoing"),
	"training": ("course_name", "institution", "started_on", "completed_on", "remarks"),
	"work_experience": ("organization", "role", "started_on", "ended_on", "is_current", "summary"),
	"licences": (
		"license_type",
		"license_name",
		"institution",
		"registration_no",
		"valid_from",
		"valid_to",
		"does_not_expire",
	),
	"driving_licences": ("licence_class", "licence_number", "valid_to"),
	"references": ("reference_name", "position", "organization", "email", "phone", "relationship", "notes"),
}


def background(profile: str) -> dict:
	"""What this person said they have already done, read live off their profile.

	Six child tables on core's Red Profile — see
	`patches/install_background_fields.py` for why they live there. Read on every
	call and stored nowhere, exactly like the scalars in `_READABLE` above: a
	volunteer who corrects a qualification on their own profile page corrects it
	on every coordinator's screen the moment they save it.

	**Guarded on the meta, table by table.** These are Custom Fields, and a site
	that has synced this module without running the patch has the doctype and not
	the fields. A coordinator's screen that raised there would be a register
	nobody could open, over a block that is optional for everybody on it.

	**Nothing here has been checked by anybody.** It is what an applicant typed
	about themselves. The dossier carries it so a branch can decide what to
	verify, not as a statement that anything was verified — which is why a
	`VMMS Certification` is a separate record somebody has to issue.
	"""
	meta = frappe.get_meta(PROFILE_DOCTYPE)
	held = {}

	for key, fields in _BACKGROUND.items():
		field = f"vmms_{key}"

		if not meta.has_field(field):
			held[key] = []
			continue

		held[key] = frappe.get_all(
			meta.get_field(field).options,
			filters={"parenttype": PROFILE_DOCTYPE, "parent": profile, "parentfield": field},
			fields=list(fields),
			order_by="idx asc",
		)

	return held


def identifications(volunteer) -> list[dict]:
	"""The person's current identification rows, primary first and explicitly shaped."""
	rows = frappe.get_all(
		"Red Profile Identification",
		filters={
			"parent": volunteer.red_profile,
			"parenttype": PROFILE_DOCTYPE,
			"parentfield": "identifications",
		},
		fields=["id_type", "id_number", "attachment", "is_primary"],
		order_by="is_primary desc, idx asc",
	)

	id_types = [row.id_type for row in rows if row.id_type]
	labels = (
		dict(
			frappe.get_all(
				"Identification Type",
				filters={"name": ("in", id_types)},
				fields=["name", "identification_type_name"],
				as_list=True,
			)
		)
		if id_types
		else {}
	)

	return [
		{
			"id_type": row.id_type,
			"id_type_name": labels.get(row.id_type) or row.id_type,
			"id_number": row.id_number,
			"attachment": row.attachment,
			"is_primary": bool(row.is_primary),
		}
		for row in rows
		if row.id_type and row.id_number
	]


def display_name(volunteer) -> str:
	"""What to call this person in a queue or on a document.

	Falls back to the profile docname rather than rendering an empty string: a
	record naming a record is worse than nothing only if nothing were an option.
	"""
	person = read(volunteer, ("full_name", "first_name", "last_name"))
	full = (person.get("full_name") or "").strip()

	if full:
		return full

	composed = " ".join(part for part in (person.get("first_name"), person.get("last_name")) if part)

	return composed.strip() or volunteer.red_profile


def user_of(volunteer) -> str | None:
	"""The login behind this volunteer, if they have one.

	Nullable by design in core: not everybody with a profile can log in. Callers
	must treat None as ordinary rather than as an error.
	"""
	return read(volunteer, ("user",)).get("user") or None
