# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The volunteer satellite — and what it reports to core's affiliation index.

Design 2, from core's `CLAUDE.md`: **this satellite is the truth.** What makes
somebody an active volunteer of the society is a `VMMS Volunteer` record here
with an accepted application behind it. The row on their Red Profile's
affiliation table is a *derived summary* this module writes through
`set_affiliation()`.

Two rules follow, and both are tested:

1. **Nothing reads the row back.** Not deployability, not the application
   engine, not a DTO. Every question about whether somebody is a volunteer is
   answered from here. The row is allowed to be stale; if code branched on it,
   staleness would become a bug instead of an accepted property.
2. **The index is reconstructable.** `provide()` in
   `vmmsx/volunteer/affiliations.py` hands core everything it needs to rebuild
   this satellite's rows from scratch, so deleting every row and rebuilding
   loses nothing — and, because Member registers a provider too, rebuilding one
   person's index has to reconstruct *both* affiliations without either provider
   disturbing the other's row.

`status` is derived where it can be and explicit where it must be. Prospective
and Active are read off the applications below; Suspended and Exited are acts of
the society, and a derivation that quietly undid them would be a way of
un-suspending somebody by saving an unrelated record.
"""

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import getdate, today

from vmmsx import elevation
from vmmsx.approvals import states
from vmmsx.approvals.services import contract

# The affiliation vocabulary key this satellite owns. A key, not a society's
# label — core's config-vocabulary rule is explicit that a stable business key
# is what code refers to. The society's own word for a volunteer is terminology,
# and lives in National Society Settings.
VOLUNTEER_AFFILIATION_KEY = "volunteer"

VOLUNTEER_DOCTYPE = "VMMS Volunteer"
APPLICATION_DOCTYPE = "VMMS Volunteer Application"

STATUS_PROSPECTIVE = "Prospective"
STATUS_ACTIVE = "Active"
STATUS_SUSPENDED = "Suspended"
STATUS_EXITED = "Exited"

# The two a derivation must never overwrite. Both are things a society *did*,
# not things that follow from the record.
EXPLICIT_STATUSES = (STATUS_SUSPENDED, STATUS_EXITED)

# How this module's own status reads as an affiliation status. A translation
# between two closed vocabularies — core's and ours — not a society's choice.
_AFFILIATION_STATUS = {
	STATUS_PROSPECTIVE: "Pending",
	STATUS_ACTIVE: "Active",
	STATUS_SUSPENDED: "Suspended",
	STATUS_EXITED: "Ended",
}


def affiliation_status(volunteer_status: str) -> str:
	"""This module's status, as core's affiliation vocabulary calls it.

	The one translation point between the two vocabularies, so the provider and
	the reporter cannot drift into disagreeing about what Exited means.
	"""
	return _AFFILIATION_STATUS[volunteer_status]


def ensure(red_profile: str, home_geo_node: str | None = None):
	"""The volunteer record for a profile, created if this is their first.

	One volunteer per profile — the link is unique — so this is safe to call
	from anywhere that is about to accept somebody.

	`home_geo_node` is used **only when creating**. A person who is already a
	volunteer is not relocated by a later application: moving somebody's
	placement changes who can see them and who approves for them, and that is a
	deliberate act, not a side effect of applying again.

	**The insert bypasses permissions, and this is the justification.** There is
	no path anywhere in this app by which somebody becomes a volunteer other
	than an application the approval engine already gated: the API creates
	applications, never volunteers, and the register carries no field a caller
	supplies. The elevation is therefore not a shortcut around a check — the
	check happened, in `engine.decide`, against the person this document routed
	to. Requiring create permission here as well would mean a society had to
	grant every volunteer approver in the country write access to the register in
	order for approvals to work, which grants far more than it withholds.
	"""
	existing = frappe.db.get_value(VOLUNTEER_DOCTYPE, {"red_profile": red_profile}, "name")

	if existing:
		return frappe.get_doc(VOLUNTEER_DOCTYPE, existing)

	if not frappe.db.exists("Red Profile", red_profile):
		frappe.throw(
			_("Red Profile {0} does not exist. A volunteer is always a person core already knows.").format(
				frappe.bold(red_profile)
			),
			frappe.DoesNotExistError,
			title=_("Unknown Profile"),
		)

	volunteer = frappe.get_doc(
		{
			"doctype": VOLUNTEER_DOCTYPE,
			"red_profile": red_profile,
			"home_geo_node": home_geo_node,
		}
	)
	volunteer.insert(ignore_permissions=True)

	return volunteer


def applications(volunteer: str, state: str | None = None) -> list[str]:
	"""This volunteer's applications, optionally filtered by approval state."""
	filters = {"volunteer": volunteer}

	if state:
		filters[contract.STATE_FIELD] = state

	return frappe.get_all(APPLICATION_DOCTYPE, filters=filters, pluck="name")


def derive_status(volunteer) -> str:
	"""What this volunteer is, read from their applications.

	Suspended and Exited are the two statuses the applications cannot produce:
	both are explicit acts by the society, so a derivation must not quietly
	undo one by finding an old approved application still lying there.
	"""
	if volunteer.status in EXPLICIT_STATUSES:
		return volunteer.status

	if applications(volunteer.name, state=states.APPROVED):
		return STATUS_ACTIVE

	return STATUS_PROSPECTIVE


def refresh(volunteer_name: str) -> dict:
	"""Recompute the volunteer's derived status and report it to core. Idempotent.

	Returns what it settled on. Called after any application event; calling it
	twice writes nothing the second time, because `set_affiliation()` is itself
	idempotent and the status is derived from the same rows.
	"""
	volunteer = frappe.get_doc(VOLUNTEER_DOCTYPE, volunteer_name)
	derived = derive_status(volunteer)
	changed = False

	if volunteer.status != derived:
		volunteer.status = derived
		changed = True

	if derived == STATUS_ACTIVE and not volunteer.joined_on:
		# Set once, at the first acceptance. A second application years later
		# must not move the date somebody started volunteering.
		volunteer.joined_on = getdate(today())
		changed = True

	if changed:
		# Engine-written fields on a record whose permission was checked when it
		# was created; this also runs from an approver's decision, and an
		# approver holds no write permission on the volunteer register.
		volunteer.save(ignore_permissions=True)

	report(volunteer)
	granted = grant_self_service(volunteer)

	return {
		"volunteer": volunteer.name,
		"status": derived,
		"changed": changed,
		"self_service_granted": granted,
	}


def grant_self_service(volunteer) -> bool:
	"""Let an active volunteer see themselves. Idempotent, and silent otherwise.

	**Which role is a society's answer**, read from `vmms_volunteer_member_role`
	on every call. No role name appears in this file, and an unset or deleted
	setting grants nothing rather than falling back to something invented here.

	**Only an active volunteer.** Prospective is somebody whose application is
	still open, and Exited is somebody who has stopped: neither is a person who
	should be handed a view of the register's self-service surface. The grant is
	not withdrawn on exit, deliberately — taking a role away is an act with
	consequences elsewhere on a site, and it belongs to a society's off-boarding
	rather than to a status derivation that runs on every save.

	**Nobody to grant to is ordinary.** `Red Profile.user` is nullable by core's
	design, and a volunteer the branch registered from a paper form has no login.
	Nothing happens and nothing is raised.

	The User Permissions alongside the role are what make the grant mean *their
	own*: the self-service workspace points at two ordinary desk lists, and each
	is narrowed to this volunteer's own rows. **Only those two.** A permission
	applying to every doctype would follow this person into whatever else they do
	for the society, and a coordinator who also volunteers would quietly stop
	seeing anybody else's records. `roles.scope_to` requires the list for exactly
	that reason.
	"""
	from vmmsx.registration.services import permissions, roles

	if volunteer.status != STATUS_ACTIVE:
		return False

	from vmmsx.volunteer.services import identity, society

	user = identity.user_of(volunteer)

	if not user:
		return False

	granted = roles.grant(user, society.volunteer_member_role())
	roles.scope_to(
		user,
		VOLUNTEER_DOCTYPE,
		volunteer.name,
		applicable_for=permissions.SELF_SERVICE_READABLE,
	)

	return granted


# --- the explicit acts ----------------------------------------------------


def suspend(volunteer, reason: str | None = None) -> dict:
	"""Stop somebody volunteering without ending their relationship. Idempotent."""
	return _set_explicit_status(volunteer, STATUS_SUSPENDED, reason)


def record_exit(volunteer, on_date=None, reason: str | None = None) -> dict:
	"""The person has stopped volunteering. Terminal, and idempotent."""
	if volunteer.status != STATUS_EXITED:
		volunteer.exited_on = getdate(on_date or today())

	return _set_explicit_status(volunteer, STATUS_EXITED, reason)


def reinstate(volunteer, reason: str | None = None) -> dict:
	"""Undo a suspension or an exit, and let the derivation take over again.

	The status is cleared back to whatever the applications say rather than set
	to Active: somebody reinstated with no approved application behind them is
	Prospective, and pretending otherwise would make the satellite disagree with
	its own evidence.
	"""
	volunteer.status = STATUS_PROSPECTIVE
	volunteer.exited_on = None
	volunteer.save(ignore_permissions=True)

	if reason:
		volunteer.add_comment("Comment", _("Reinstated. {0}").format(reason))

	return refresh(volunteer.name)


def _set_explicit_status(volunteer, status: str, reason: str | None) -> dict:
	if volunteer.status == status:
		return {"volunteer": volunteer.name, "status": status, "changed": False}

	volunteer.status = status
	# The status field is read-only to users by design — it is derived state —
	# so the service that owns it is the thing that writes it.
	volunteer.save(ignore_permissions=True)
	volunteer.add_comment("Comment", _("{0}. {1}").format(_(status), reason or ""))

	report(volunteer)

	return {"volunteer": volunteer.name, "status": status, "changed": True}


# --- core's index ---------------------------------------------------------


@contextmanager
def _as_system():
	"""Run one index write as the system rather than as whoever triggered it.

	Core's `set_affiliation()` saves the Red Profile **without** bypassing
	permissions, and says so deliberately: it asks a satellite that must write
	on an unprivileged user's behalf to "arrange for that explicitly rather than
	have core quietly bypass the check for every caller". This is that
	arrangement, and it is as narrow as it can be — it wraps exactly one call,
	writing exactly one derived row.

	It is the same one-call pattern as `member/services/member.py::_as_system()`,
	deliberately not widened: the moment it wraps two calls it stops being
	auditable at a glance.

	The alternative is worse. Acceptance is triggered by an approver approving.
	An approver has no business holding write permission on somebody's identity
	record, and requiring it would mean a society had to grant Red Profile write
	access to every volunteer approver in the country for the index to update.

	Administrator is a Frappe framework primitive, not a society role, so naming
	it here is not the hardcoded-role rule being broken.

	The mechanics are `vmmsx.elevation`: restoring the user is not enough on
	its own, because `set_user` overwrites the live session id and discards the
	session data with it, which signs the caller out one request later.
	"""
	with elevation.as_system():
		yield


def report(volunteer) -> str | None:
	"""Write this satellite's row on core's affiliation index.

	The only way this module touches that table. Nothing reads it back.
	"""
	from onerc_core.identity.services.affiliation import set_affiliation

	if not frappe.db.exists("Affiliation Type", VOLUNTEER_AFFILIATION_KEY):
		# The vocabulary has not been installed on this site. Reporting is an
		# index update, not the truth, so a missing type must not stop somebody
		# becoming a volunteer — it is logged and the satellite stands alone.
		frappe.logger().warning(
			f"vmmsx: Affiliation Type {VOLUNTEER_AFFILIATION_KEY!r} is missing;"
			f" skipped indexing {volunteer.name}"
		)

		return None

	with _as_system():
		return set_affiliation(
			profile=volunteer.red_profile,
			affiliation_type=VOLUNTEER_AFFILIATION_KEY,
			status=_AFFILIATION_STATUS[volunteer.status],
			reference_doctype=VOLUNTEER_DOCTYPE,
			reference_name=volunteer.name,
			start_date=volunteer.joined_on,
			end_date=volunteer.exited_on,
		)


# --- the DTO --------------------------------------------------------------


def profile_dto(volunteer, as_of=None) -> dict:
	"""Who this volunteer is, read from Red Profile at the moment of asking.

	Explicit, and assembled here rather than stored: the volunteer record holds
	no identity of its own, so this is the only place a name or an email can come
	from, and it is always current.

	Gender, date of birth, preferred language, the photo and the home area are
	here because the volunteer page shows them — see the note on
	`identity._READABLE`, which is where that widening was decided. They are read
	on every call and written nowhere: correcting somebody's date of birth on
	their Red Profile corrects it on every volunteer page in the society the
	moment it is saved, because there is no copy to go and update.

	**Placement comes back as two named nodes, not one.** `capabilities.placement()`
	returns the Serving Branch this record is anchored on *and* the Home Area
	read off the profile, under names that cannot be confused. `geo_path` keeps
	meaning what it has always meant here — the anchor's path — so nothing that
	already reads this DTO changed underneath.

	`as_of` is passed straight through to the deployability derivation and
	defaults to today, which is what every existing caller wants. It exists
	because the coordinator's view resolves one date for the whole page and hands
	it to every block: without it, this DTO's embedded deployability would answer
	about today while the page's own deployability block answered about the date
	that was asked for, and one screen would carry two answers to one question.
	"""
	from vmmsx.volunteer.services import capabilities, certification, hr, identity

	person = identity.read(volunteer)

	return {
		"volunteer": volunteer.name,
		"red_profile": volunteer.red_profile,
		"full_name": identity.display_name(volunteer),
		"email": person.get("email"),
		"phone": person.get("phone"),
		"gender": person.get("gender"),
		"date_of_birth": person.get("date_of_birth"),
		"preferred_language": person.get("preferred_language"),
		"profile_photo": person.get("profile_photo"),
		"identifications": identity.identifications(volunteer),
		# What kind of work they do, and what they have already done. Read live
		# off Red Profile like the rest of the identity above it, and stored
		# nowhere — see `identity.background` for what is left out of it and why.
		"profession": person.get("vmms_profession"),
		"background": identity.background(volunteer.red_profile),
		"status": volunteer.status,
		"joined_on": volunteer.joined_on,
		"exited_on": volunteer.exited_on,
		# The coordinator's own note about this person. On the doctype since it
		# was written and in no DTO until now, so a branch that recorded
		# something on the desk could not read it back on the register — and
		# nobody working from the console could write one at all.
		"notes": volunteer.notes,
		**capabilities.placement(volunteer),
		# Derived on every read, never stored. See certification.py.
		"deployability": certification.deployability(volunteer, as_of=as_of),
		# The HR seam reports the link and nothing else — no employment data
		# crosses back into this app.
		"employee": hr.linked_employee(volunteer),
	}
