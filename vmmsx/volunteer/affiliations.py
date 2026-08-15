# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""vmmsx's volunteer affiliation provider — the app's **second** registration.

Registered in `hooks.py` under `onerc_affiliation_providers`, alongside
`vmmsx.member.affiliations.provide`. Core never imports vmmsx; vmmsx registers
itself, and this is the whole of that registration for volunteering.

**Two providers, one profile, and why that is the interesting case.** A person
can be both a member and a volunteer, and core's rebuild calls every registered
provider and reconciles their answers together. Each provider declares only what
it owns — Member declares `VMMS Member`, this one declares `VMMS Volunteer` — and
core removes a row only when a registered provider owns its `reference_doctype`
and did not claim it. That is precisely what keeps the two independent: deleting
somebody's volunteer record makes this provider stop claiming a volunteer row,
and leaves the member row untouched because no provider that owns `VMMS Member`
declined to claim it. Removal is isolated by construction rather than by care.

`reference_doctypes` is therefore not a formality. Without it a deleted
volunteer would leave a row on their profile that core would never be entitled
to remove — core cannot distinguish "the satellite was deleted" from "the app
that owns it is not installed today", and it is right to leave the second one
alone.

The provider is deliberately quiet about people who are not volunteers. A
profile with no `VMMS Volunteer` returns an empty `affiliations` list with the
ownership still declared, which is how core learns that any volunteer row it
holds for them is stale.
"""

import frappe

from vmmsx.volunteer.services.volunteer import (
	VOLUNTEER_AFFILIATION_KEY,
	VOLUNTEER_DOCTYPE,
	affiliation_status,
)


def provide(profile: str) -> dict:
	"""Everything this app can say about `profile`'s volunteer affiliation.

	Reads the satellite, never core's index — rebuilding from the index would
	make the index its own source, which is the failure Design 2 exists to
	prevent.
	"""
	declaration = {"reference_doctypes": [VOLUNTEER_DOCTYPE], "affiliations": []}

	volunteer_name = frappe.db.get_value(VOLUNTEER_DOCTYPE, {"red_profile": profile}, "name")

	if not volunteer_name or _is_being_trashed(volunteer_name):
		# Either this profile has no volunteer, or the one it has is mid-deletion.
		# Both mean the same thing to core: ownership is still declared above,
		# nothing is claimed, so any volunteer row it holds is stale and may go.
		# The member row on the same profile is untouched by any of this.
		return declaration

	volunteer = frappe.get_doc(VOLUNTEER_DOCTYPE, volunteer_name)

	declaration["affiliations"].append(
		{
			"affiliation_type": VOLUNTEER_AFFILIATION_KEY,
			"status": affiliation_status(volunteer.status),
			"reference_doctype": VOLUNTEER_DOCTYPE,
			"reference_name": volunteer.name,
			"start_date": volunteer.joined_on,
			"end_date": volunteer.exited_on,
		}
	)

	return declaration


def _is_being_trashed(volunteer_name: str) -> bool:
	"""Is this volunteer inside its own `on_trash` right now?

	Set by `VMMSVolunteer.on_trash`, which has to get the derived row removed
	*before* Frappe's link check runs or the delete is refused with
	`LinkExistsError`. See the comment there — this is the read side of that
	handshake, and it is scoped to the request rather than being persistent
	state.
	"""
	return volunteer_name in getattr(frappe.local, "vmms_volunteers_being_trashed", ())
