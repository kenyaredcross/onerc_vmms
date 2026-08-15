# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""vmmsx's affiliation provider — how core rebuilds member rows from this app.

Registered in `hooks.py` under `onerc_affiliation_providers`. Core never imports
vmmsx; vmmsx registers itself, and this is the whole of that registration for
membership.

`reference_doctypes` is the **declared ownership**, and it is what makes removal
safe. Core deletes an index row only when a registered provider owns its
`reference_doctype` and did not claim it — that combination is the one case
where core can know the satellite is gone rather than merely absent. Declaring
`VMMS Member` here is therefore not a formality: without it, a deleted member
would leave a row on their profile that core would never be entitled to remove.

The provider is deliberately quiet about people who are not members. A profile
with no `VMMS Member` returns an empty `affiliations` list with the ownership
still declared, which is how core learns that any member row it holds for them
is stale.
"""

import frappe

from vmmsx.member.services.member import (
	MEMBER_AFFILIATION_KEY,
	MEMBER_DOCTYPE,
	affiliation_status,
)


def provide(profile: str) -> dict:
	"""Everything this app can say about `profile`'s membership affiliation.

	Reads the satellite, never core's index — rebuilding from the index would
	make the index its own source, which is the failure Design 2 exists to
	prevent.
	"""
	declaration = {"reference_doctypes": [MEMBER_DOCTYPE], "affiliations": []}

	member_name = frappe.db.get_value(MEMBER_DOCTYPE, {"red_profile": profile}, "name")

	if not member_name or _is_being_trashed(member_name):
		# Either this profile has no member, or the one it has is mid-deletion.
		# Both mean the same thing to core: ownership is still declared above,
		# nothing is claimed, so any member row it holds is stale and may go.
		return declaration

	member = frappe.get_doc(MEMBER_DOCTYPE, member_name)

	declaration["affiliations"].append(
		{
			"affiliation_type": MEMBER_AFFILIATION_KEY,
			"status": affiliation_status(member.status),
			"reference_doctype": MEMBER_DOCTYPE,
			"reference_name": member.name,
			"start_date": member.joined_on,
		}
	)

	return declaration


def _is_being_trashed(member_name: str) -> bool:
	"""Is this member inside its own `on_trash` right now?

	Set by `VMMSMember.on_trash`, which has to get the derived row removed
	*before* Frappe's link check runs or the delete is refused with
	`LinkExistsError`. See the comment there — this is the read side of that
	handshake, and it is scoped to the request rather than being persistent
	state.
	"""
	return member_name in getattr(frappe.local, "vmms_members_being_trashed", ())
