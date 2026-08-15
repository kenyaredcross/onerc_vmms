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

	allowed = tuple(field for field in requested if field in _READABLE)
	values = frappe.db.get_value(PROFILE_DOCTYPE, volunteer.red_profile, allowed, as_dict=True)

	return dict(values or {})


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
