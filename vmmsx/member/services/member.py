# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The member satellite — and what it reports to core's affiliation index.

Design 2, from core's `CLAUDE.md`: **this satellite is the truth.** What makes
somebody an active member of the society is a `VMMS Member` record here with an
active membership under it. The row on their Red Profile's affiliation table is
a *derived summary* this module writes through `set_affiliation()`.

Two rules follow, and both are tested:

1. **Nothing reads the row back.** Not activation, not the certificate, not the
   DTO. Every question about whether somebody is a member is answered from the
   memberships, here. The row is allowed to be stale; if code branched on it,
   staleness would become a bug instead of an accepted property.
2. **The index is reconstructable.** `provide()` in `vmmsx/member/affiliations.py`
   hands core everything it needs to rebuild this satellite's rows from scratch,
   so deleting every row and rebuilding loses nothing.

`member_status` is derived, never typed: it is a reading of the memberships
below it, recomputed by `refresh()` after anything that could change it.
"""

from contextlib import contextmanager

import frappe
from frappe import _

# The affiliation vocabulary key this satellite owns. A key, not a society's
# label — core's config-vocabulary rule is explicit that a stable business key
# is what code refers to (`affiliation_type_key == "member"`). The society's own
# word for a member is terminology, and lives in National Society Settings.
MEMBER_AFFILIATION_KEY = "member"

MEMBER_DOCTYPE = "VMMS Member"
MEMBERSHIP_DOCTYPE = "VMMS Membership"

STATUS_PROSPECTIVE = "Prospective"
STATUS_ACTIVE = "Active"
STATUS_LAPSED = "Lapsed"
STATUS_TERMINATED = "Terminated"

# How this module's own status reads as an affiliation status. A translation
# between two closed vocabularies — core's and ours — not a society's choice.
_AFFILIATION_STATUS = {
	STATUS_PROSPECTIVE: "Pending",
	STATUS_ACTIVE: "Active",
	STATUS_LAPSED: "Ended",
	STATUS_TERMINATED: "Ended",
}


def affiliation_status(member_status: str) -> str:
	"""This module's status, as core's affiliation vocabulary calls it.

	The one translation point between the two vocabularies, so the provider and
	the reporter cannot drift into disagreeing about what Lapsed means.
	"""
	return _AFFILIATION_STATUS[member_status]


def ensure(red_profile: str):
	"""The member record for a profile, created if this is their first.

	One member per profile — the link is unique — so this is safe to call from
	anywhere that is about to give somebody a membership.
	"""
	existing = frappe.db.get_value(MEMBER_DOCTYPE, {"red_profile": red_profile}, "name")

	if existing:
		return frappe.get_doc(MEMBER_DOCTYPE, existing)

	if not frappe.db.exists("Red Profile", red_profile):
		frappe.throw(
			_("Red Profile {0} does not exist. A member is always a person core already knows.").format(
				frappe.bold(red_profile)
			),
			frappe.DoesNotExistError,
			title=_("Unknown Profile"),
		)

	member = frappe.get_doc({"doctype": MEMBER_DOCTYPE, "red_profile": red_profile})
	member.insert()

	return member


def memberships(member: str, status: str | None = None) -> list[str]:
	"""This member's memberships, optionally filtered by operational status."""
	filters = {"member": member}

	if status:
		filters["membership_status"] = status

	return frappe.get_all(MEMBERSHIP_DOCTYPE, filters=filters, pluck="name")


def derive_status(member) -> str:
	"""What this member is, read from their memberships.

	Terminated is the one status the memberships cannot produce: it is an
	explicit act by the society, so a derivation must not quietly undo it.
	"""
	if member.status == STATUS_TERMINATED:
		return STATUS_TERMINATED

	if memberships(member.name, status="Active"):
		return STATUS_ACTIVE

	# Ever activated? A membership that reached a validity window is a
	# membership that once existed, so its holder has lapsed rather than never
	# having joined.
	ever = frappe.db.exists(MEMBERSHIP_DOCTYPE, {"member": member.name, "valid_from": ("is", "set")})

	return STATUS_LAPSED if ever else STATUS_PROSPECTIVE


def refresh(member_name: str) -> dict:
	"""Recompute the member's derived status and report it to core. Idempotent.

	Returns what it settled on. Called after any membership event; calling it
	twice writes nothing the second time, because `set_affiliation()` is itself
	idempotent and the status is derived from the same rows.
	"""
	member = frappe.get_doc(MEMBER_DOCTYPE, member_name)
	derived = derive_status(member)
	changed = False

	if member.status != derived:
		member.status = derived
		changed = True

	if derived == STATUS_ACTIVE and not member.joined_on:
		# Set once, at the first activation. A renewal must not move the date
		# somebody joined the society.
		member.joined_on = _first_activation(member.name)
		changed = True

	if changed:
		# Engine-written fields on a record whose permission was checked when it
		# was created; this also runs from a gateway callback with no session.
		member.save(ignore_permissions=True)

	report(member)
	granted = grant_self_service(member)

	return {"member": member.name, "status": derived, "changed": changed, "self_service_granted": granted}


def grant_self_service(member) -> bool:
	"""Let an active member see their own memberships. Idempotent, else silent.

	**Which role is a society's answer**, read from `vmms_membership_member_role`
	on every call. No role name appears in this file, and an unset or deleted
	setting grants nothing rather than falling back to something invented here.

	**Only an active member**, which is a reading of their memberships and not a
	field anybody typed. The grant is not withdrawn when a membership lapses:
	taking a role away is an act with consequences elsewhere on a site, and a
	lapsed member is still refused a certificate by `certificate.assert_active`,
	which is where that rule belongs.

	**Nobody to grant to is ordinary.** A member the branch registered from a
	paper form has no login. Nothing happens and nothing is raised.

	**No User Permission is written here, deliberately.** The volunteer grant
	writes some, because its self-service workspace points at two ordinary desk
	lists that have to be narrowed. The member surface points at no doctype at
	all — every membership a person can see comes back through
	`api/member.py::my_memberships`, which answers from the session — so there is
	nothing to narrow, and writing one anyway would follow this person into
	whatever else they do for the society. A registration clerk who is also a
	member would quietly stop being able to see anybody else's membership, which
	is the failure `member/tests/test_certificate_print.py` exists to catch.
	"""
	from vmmsx.member.services import identity, society
	from vmmsx.registration.services import roles

	if member.status != STATUS_ACTIVE:
		return False

	user = identity.user_of(member)

	if not user:
		return False

	return roles.grant(user, society.membership_member_role())


@contextmanager
def _as_system():
	"""Run one index write as the system rather than as whoever triggered it.

	Core's `set_affiliation()` saves the Red Profile **without** bypassing
	permissions, and says so deliberately: it asks a satellite that must write
	on an unprivileged user's behalf to "arrange for that explicitly rather than
	have core quietly bypass the check for every caller". This is that
	arrangement, and it is as narrow as it can be — it wraps exactly one call,
	writing exactly one derived row.

	The alternative is worse. Activation is triggered by an approver approving,
	or by a gateway callback confirming a payment. Neither has any business
	holding write permission on somebody's identity record, and requiring it
	would mean a society had to grant Red Profile write access to every
	membership approver in the country in order for the index to update.

	Administrator is a Frappe framework primitive, not a society role, so naming
	it here is not the hardcoded-role rule being broken.
	"""
	previous = frappe.session.user
	frappe.set_user("Administrator")

	try:
		yield
	finally:
		frappe.set_user(previous)


def report(member) -> str | None:
	"""Write this satellite's row on core's affiliation index.

	The only way vmmsx touches that table. Nothing reads it back.
	"""
	from onerc_core.identity.services.affiliation import set_affiliation

	if not frappe.db.exists("Affiliation Type", MEMBER_AFFILIATION_KEY):
		# The vocabulary has not been installed on this site. Reporting is an
		# index update, not the truth, so a missing type must not stop somebody
		# becoming a member — it is logged and the satellite stands alone.
		frappe.logger().warning(
			f"vmmsx: Affiliation Type {MEMBER_AFFILIATION_KEY!r} is missing; skipped indexing {member.name}"
		)

		return None

	with _as_system():
		return set_affiliation(
			profile=member.red_profile,
			affiliation_type=MEMBER_AFFILIATION_KEY,
			status=_AFFILIATION_STATUS[member.status],
			reference_doctype=MEMBER_DOCTYPE,
			reference_name=member.name,
			start_date=member.joined_on,
		)


def _first_activation(member_name: str):
	"""The earliest validity start across this member's memberships."""
	starts = frappe.get_all(
		MEMBERSHIP_DOCTYPE,
		filters={"member": member_name, "valid_from": ("is", "set")},
		pluck="valid_from",
		order_by="valid_from asc",
		limit=1,
	)

	return starts[0] if starts else None


def profile_dto(member) -> dict:
	"""Who this member is, read from Red Profile at the moment of asking.

	Explicit, and assembled here rather than stored: the member record holds no
	identity of its own, so this is the only place a name or an email can come
	from, and it is always current.
	"""
	from vmmsx.member.services import identity

	person = identity.read(member)

	return {
		"member": member.name,
		"red_profile": member.red_profile,
		"full_name": identity.display_name(member),
		"email": person.get("email"),
		"phone": person.get("phone"),
		"status": member.status,
		"joined_on": member.joined_on,
	}
