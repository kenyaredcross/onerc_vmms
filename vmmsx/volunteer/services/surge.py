# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The surge roster: professionals a branch can call on, once it has checked them.

A volunteer is put on the roster **by a coordinator, by hand**, under one
profession, after the coordinator has seen their professional licence. The
entry records what was checked (the licence number, who issued it, until when)
and who checked it, on which day. Nothing puts a person on the roster by itself
and nothing takes them off: a coordinator stands them down, with a reason, and
the entry is kept.

**Whether an entry is ready is derived, every time it is asked.** The same rule
`certification.py` follows for a lapse, for the same reasons. An entry stores
its licence's expiry date and nothing else about time; "ready", "licence
expires soon", "licence expired" and "not an active volunteer" are worked out
from that date and the volunteer's current standing at the moment of asking.
A suspended volunteer drops out of "ready" the moment they are suspended,
without any job noticing, and is back the moment they are reinstated.

**Scope is the floor.** Who may see an entry is who may see its volunteer: the
roster is read through `capabilities.search`, which ends in a scoped
`frappe.get_list` on `VMMS Volunteer`, and every act checks the volunteer with
`write` first. The entry doctype itself carries no geo anchor of its own, so a
volunteer who transfers branches takes their roster entries with them and no
second anchor can fall out of step.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today

ENTRY_DOCTYPE = "VMMS Surge Roster Entry"
VOLUNTEER_DOCTYPE = "VMMS Volunteer"
PROFESSION_DOCTYPE = "Profession"

STATUS_ACTIVE = "Active"
STATUS_STOOD_DOWN = "Stood Down"
VOLUNTEER_ACTIVE = "Active"

# The catch-all on the society's profession register. A roster grouped by
# profession has no use for an "Other" group, so it is refused.
OTHER_PROFESSION = "Other"

# How far ahead a licence expiry is called out, so a branch can ask for the
# renewed licence before the person drops off the ready list.
EXPIRING_WITHIN_DAYS = 60

READY = "ready"
EXPIRING = "expiring"
LICENCE_EXPIRED = "licence_expired"
NOT_ACTIVE = "volunteer_not_active"
STOOD_DOWN = "stood_down"

# What a row carries. Explicit, so a field added to the doctype later does not
# reach a screen nobody reviewed.
ENTRY_FIELDS = (
	"name",
	"volunteer",
	"profession",
	"status",
	"licence_number",
	"issuing_body",
	"licence_expiry",
	"licence_document",
	"checked_by",
	"checked_on",
	"notes",
	"stood_down_on",
	"stood_down_by",
	"stood_down_reason",
)


def standing(entry, volunteer_status: str | None, as_of=None) -> str:
	"""Where this entry stands today. Derived; never stored."""
	as_of = getdate(as_of or today())

	if entry.get("status") == STATUS_STOOD_DOWN:
		return STOOD_DOWN

	if volunteer_status != VOLUNTEER_ACTIVE:
		return NOT_ACTIVE

	expiry = entry.get("licence_expiry")

	if expiry and getdate(expiry) < as_of:
		return LICENCE_EXPIRED

	if expiry and getdate(expiry) <= add_days(as_of, EXPIRING_WITHIN_DAYS):
		return EXPIRING

	return READY


def is_ready(state: str) -> bool:
	"""Ready to be called on. A licence expiring soon is still a licence."""
	return state in (READY, EXPIRING)


def roster(
	geo_node: str | None = None,
	profession: str | None = None,
	search: str | None = None,
	as_of=None,
) -> dict:
	"""The roster inside the caller's scope, grouped by profession.

	Stood-down entries are left out: the roster is of people a branch can call
	on, and a stood-down entry is history, read on the volunteer's own record.
	"""
	from vmmsx.volunteer.services import capabilities

	as_of = getdate(as_of or today())
	volunteers = capabilities.search(geo_node=geo_node, search=search, limit=0)
	empty = {"as_of": str(as_of), "figures": _figures([]), "professions": [], "rows": []}

	if not volunteers:
		return empty

	filters = {"volunteer": ("in", volunteers), "status": STATUS_ACTIVE}
	every = frappe.get_all(
		ENTRY_DOCTYPE, filters=filters, fields=list(ENTRY_FIELDS), order_by="profession asc"
	)

	if not every:
		return empty

	people = _people({entry.volunteer for entry in every})
	all_rows = [_row(entry, people.get(entry.volunteer) or {}, as_of) for entry in every]
	rows = [row for row in all_rows if not profession or row["profession"] == profession]

	return {
		"as_of": str(as_of),
		# Over the whole roster in scope, so the tiles and the groups do not
		# shrink when one profession is chosen.
		"figures": _figures(all_rows),
		"professions": _groups(all_rows),
		"rows": sorted(rows, key=lambda row: (row["profession"], (row["full_name"] or "").lower())),
	}


def for_volunteer(volunteer: str, as_of=None) -> list[dict]:
	"""Every entry this volunteer has had, stood-down ones included, newest first."""
	as_of = getdate(as_of or today())
	entries = frappe.get_all(
		ENTRY_DOCTYPE,
		filters={"volunteer": volunteer},
		fields=list(ENTRY_FIELDS),
		order_by="creation desc",
	)
	status = frappe.db.get_value(VOLUNTEER_DOCTYPE, volunteer, "status")

	return [_entry_dto(entry, standing(entry, status, as_of)) for entry in entries]


def on_roster(volunteers: list[str]) -> set[str]:
	"""Which of these volunteers have an active entry. For list badges."""
	if not volunteers:
		return set()

	return set(
		frappe.get_all(
			ENTRY_DOCTYPE,
			filters={"volunteer": ("in", volunteers), "status": STATUS_ACTIVE},
			pluck="volunteer",
		)
	)


def add(
	volunteer,
	profession: str | None,
	licence_number: str | None,
	issuing_body: str | None,
	licence_expiry: str | None = None,
	licence_document: str | None = None,
	notes: str | None = None,
):
	"""Put a checked professional on the roster. The caller has checked `write` on the volunteer."""
	if volunteer.status != VOLUNTEER_ACTIVE:
		frappe.throw(_("Only an active volunteer can be put on the surge roster."), frappe.ValidationError)

	profession = (profession or "").strip()

	if (
		not profession
		or profession == OTHER_PROFESSION
		or not frappe.db.exists(PROFESSION_DOCTYPE, profession)
	):
		frappe.throw(_("Choose the profession from the list."), frappe.ValidationError)

	if frappe.db.exists(
		ENTRY_DOCTYPE, {"volunteer": volunteer.name, "profession": profession, "status": STATUS_ACTIVE}
	):
		frappe.throw(
			_("This volunteer is already on the surge roster as {0}.").format(profession),
			frappe.ValidationError,
		)

	entry = frappe.get_doc(
		{
			"doctype": ENTRY_DOCTYPE,
			"volunteer": volunteer.name,
			"profession": profession,
			"status": STATUS_ACTIVE,
			"notes": (notes or "").strip() or None,
			**_licence(licence_number, issuing_body, licence_expiry, licence_document),
		}
	)
	entry.insert(ignore_permissions=True)
	_anchor_copy(entry)

	return entry


def renew(entry, licence_number, issuing_body, licence_expiry=None, licence_document=None):
	"""Record a renewed licence. The check is stamped again, by whoever checked it this time."""
	if entry.status != STATUS_ACTIVE:
		frappe.throw(_("This person has been stood down from the surge roster."), frappe.ValidationError)

	values = _licence(licence_number, issuing_body, licence_expiry, licence_document)

	if not values.get("licence_document"):
		# A renewal without a new copy keeps the copy already on file.
		values.pop("licence_document")

	entry.update(values)
	entry.save(ignore_permissions=True)
	_anchor_copy(entry)

	return entry


def stand_down(entry, reason: str | None):
	"""Take somebody off the roster. The entry is kept, with who did it and why."""
	reason = (reason or "").strip()

	if not reason:
		frappe.throw(_("Give a reason for standing this person down."), frappe.ValidationError)

	if entry.status == STATUS_STOOD_DOWN:
		return entry

	entry.update(
		{
			"status": STATUS_STOOD_DOWN,
			"stood_down_on": today(),
			"stood_down_by": frappe.session.user,
			"stood_down_reason": reason,
		}
	)
	entry.save(ignore_permissions=True)

	return entry


def professions_in_use() -> list[str]:
	"""Professions anybody on any roster holds, for the filter. Names only."""
	return frappe.get_all(
		ENTRY_DOCTYPE,
		filters={"status": STATUS_ACTIVE},
		pluck="profession",
		distinct=True,
		order_by="profession asc",
	)


# --- internals -------------------------------------------------------------


def _licence(licence_number, issuing_body, licence_expiry, licence_document) -> dict:
	"""The checked licence, validated. Stamps who checked it and when."""
	number = (licence_number or "").strip()
	issuer = (issuing_body or "").strip()

	if not number:
		frappe.throw(_("Enter the licence number."), frappe.ValidationError)

	if not issuer:
		frappe.throw(_("Enter who issued the licence."), frappe.ValidationError)

	expiry = getdate(licence_expiry) if licence_expiry else None

	if expiry and expiry < getdate(today()):
		frappe.throw(
			_("This licence has already expired. Ask for the renewed licence."),
			frappe.ValidationError,
		)

	return {
		"licence_number": number,
		"issuing_body": issuer,
		"licence_expiry": expiry,
		"licence_document": licence_document or None,
		"checked_by": frappe.session.user,
		"checked_on": today(),
	}


def _anchor_copy(entry) -> None:
	"""Attach the uploaded licence copy to this entry, private.

	The copy is uploaded before the entry exists, unattached and owned by the
	coordinator who chose it. Only that person's own unattached upload is
	anchored, so naming somebody else's file here does not reach it.
	"""
	if not entry.licence_document:
		return

	file_name = frappe.db.get_value(
		"File",
		{
			"file_url": entry.licence_document,
			"owner": frappe.session.user,
			"attached_to_doctype": ("is", "not set"),
		},
		"name",
	)

	if file_name:
		frappe.db.set_value(
			"File",
			file_name,
			{"attached_to_doctype": entry.doctype, "attached_to_name": entry.name, "is_private": 1},
		)


def _people(volunteers: set[str]) -> dict:
	"""Name, photo, standing and branch for each volunteer, read once each."""
	from vmmsx.places import place_name
	from vmmsx.volunteer.services import identity

	people = {}

	for name in volunteers:
		volunteer = frappe.get_doc(VOLUNTEER_DOCTYPE, name)
		people[name] = {
			"full_name": identity.display_name(volunteer),
			"photo": identity.read(volunteer, ("profile_photo",)).get("profile_photo"),
			"phone": identity.read(volunteer, ("phone",)).get("phone"),
			"volunteer_status": volunteer.status,
			"branch": place_name(volunteer.get("home_geo_node")),
		}

	return people


def _row(entry, person: dict, as_of) -> dict:
	state = standing(entry, person.get("volunteer_status"), as_of)

	return {**_entry_dto(entry, state), **person}


def _entry_dto(entry, state: str) -> dict:
	return {
		"entry": entry.name,
		"volunteer": entry.volunteer,
		"profession": entry.profession,
		"status": entry.status,
		"standing": state,
		"ready": is_ready(state),
		"licence_number": entry.licence_number,
		"issuing_body": entry.issuing_body,
		"licence_expiry": str(entry.licence_expiry) if entry.licence_expiry else None,
		"licence_document": entry.licence_document,
		"checked_by": _user_name(entry.checked_by),
		"checked_on": str(entry.checked_on) if entry.checked_on else None,
		"notes": entry.notes,
		"stood_down_on": str(entry.stood_down_on) if entry.stood_down_on else None,
		"stood_down_by": _user_name(entry.stood_down_by),
		"stood_down_reason": entry.stood_down_reason,
	}


def _figures(rows: list[dict]) -> dict:
	return {
		"on_roster": len(rows),
		"people": len({row["volunteer"] for row in rows}),
		"ready": sum(1 for row in rows if row["ready"]),
		"expiring": sum(1 for row in rows if row["standing"] == EXPIRING),
		"needs_review": sum(1 for row in rows if row["standing"] in (LICENCE_EXPIRED, NOT_ACTIVE)),
	}


def _groups(rows: list[dict]) -> list[dict]:
	groups: dict[str, dict] = {}

	for row in rows:
		group = groups.setdefault(
			row["profession"], {"profession": row["profession"], "count": 0, "ready": 0}
		)
		group["count"] += 1
		group["ready"] += int(row["ready"])

	return sorted(groups.values(), key=lambda group: (-group["count"], group["profession"]))


def _user_name(user: str | None) -> str | None:
	if not user:
		return None

	return frappe.utils.get_fullname(user) or user

