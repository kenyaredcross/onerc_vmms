# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Reading a person — always from Red Profile, never from a copy.

`VMMS Member` stores no name, no email and no phone. It stores a link to a Red
Profile and nothing else about who the person is, because a second copy of a
person is a second answer to who they are, and the two diverge the first time
somebody corrects one of them.

So every display name, every payer email and every certificate greeting comes
through here, and here reads core. There is no `fetch_from` on the member either
— a fetched value is a stored copy wearing a different hat.

This module is read-only by construction: nothing in it writes to Red Profile.
Identity is core's to own; vmmsx borrows it.
"""

import frappe

PROFILE_DOCTYPE = "Red Profile"

# The fields this module is willing to surface. Named explicitly so a new field
# on core's Red Profile never starts leaking through a vmmsx DTO by accident.
#
# **`user` was added deliberately, and for one reason: to answer "is this
# person the logged-in person".** A membership certificate may be printed by the
# member it belongs to, and the only honest way to recognise them is core's
# `Red Profile.user` — the link between a human and a login, unique and
# nullable. The document's `owner` is not that person: a membership registered
# at a branch desk is owned by the clerk who typed it, and gating on `owner`
# would hand every member's certificate to whoever entered them and withhold it
# from the member.
#
# It is a login identifier, not a person-fact — nothing about who somebody is,
# only which account is theirs — and it is read by the print gate rather than
# rendered onto anything. The gated-sensitive set stays out; see the volunteer
# module's `_WITHHELD` for the names core holds back.
#
# **The last five were added deliberately, and the decision is recorded here
# rather than in a commit message.** A coordinator opening a member record was
# shown a docname and nothing else, and had to open the Red Profile in another
# tab to find out who they were looking at. The photo and the name confirm the
# right person; gender and date of birth are what a membership office is asked
# for constantly; nationality and citizenship status are core's own answer to
# where somebody is from, asked at a counter far more often than it is recorded.
#
# **Widening what this module reads is not widening what the record holds.** The
# member record gained no column, no `fetch_from` and no copy — every value here
# is read from Red Profile at the moment somebody looks and forgotten again.
# `member/tests/test_dossier.py` asserts exactly that: correcting any of these on
# a Red Profile leaves the member's stored row byte-identical.
#
# This is the same widening `volunteer/services/identity.py` made for the same
# reason, and the two lists are deliberately still separate — see that module's
# note on why sibling satellites must not share a reader.
_READABLE = (
	"full_name",
	"first_name",
	"last_name",
	"email",
	"phone",
	"home_geo_node",
	"user",
	"gender",
	"date_of_birth",
	"profile_photo",
	"preferred_language",
	"nationality",
	"citizenship_status",
)


def profile_name(member) -> str:
	"""The Red Profile docname behind a member."""
	return member.red_profile


def read(member, fields: tuple[str, ...] = _READABLE) -> dict:
	"""The person behind this member, as a plain dict of allowed fields.

	`get_value` rather than `get_doc`: a whole Red Profile carries its
	affiliation index, and that index is gated on read by core. Pulling the
	document here to take a name would step around a boundary this app has no
	business stepping around — see core's note on the read gate.
	"""
	allowed = tuple(field for field in fields if field in _READABLE)
	values = frappe.db.get_value(PROFILE_DOCTYPE, member.red_profile, allowed, as_dict=True)

	return dict(values or {})


def display_name(member) -> str:
	"""What to call this person on a certificate or in a queue.

	Falls back to the profile docname rather than rendering an empty string: a
	certificate with a blank name is worse than one naming a record.
	"""
	person = read(member, ("full_name", "first_name", "last_name"))
	full = (person.get("full_name") or "").strip()

	if full:
		return full

	composed = " ".join(part for part in (person.get("first_name"), person.get("last_name")) if part)

	return composed.strip() or member.red_profile


def user_of(member) -> str | None:
	"""The login behind this member, if they have one.

	Nullable by design in core: not everybody the society holds a record for can
	log in, and a member registered at a branch desk from a paper form ordinarily
	has no account at all. Callers must treat None as ordinary rather than as an
	error — and, in the print gate, as *nobody*: a member with no login is not
	somebody the session user could ever be.

	The mirror of `volunteer/services/identity.py::user_of`. The two are separate
	on purpose, for the reason that module's docstring gives: sibling satellites
	that share a reader acquire a dependency on each other, and what they must
	agree on is the *source*, which they do.
	"""
	return read(member, ("user",)).get("user") or None
