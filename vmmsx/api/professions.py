# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The professions of a branch's people: how many hold each, and who they are.

Two questions a coordinator asks of their own area — "what skills do we have"
and "who are our nurses" — answered over **active volunteers** and **current
members** together. A person who is both counts once in each column and once in
the total.

**Scope is the floor, not a filter.** Both registers are read with
`frappe.get_list`, which runs core's permission query condition, so a County
Coordinator sees their county and a regional or national reader sees theirs.
Red Profiles are only read for people those scoped reads already returned.

**The profession is what the person chose from the society's list**, read live
off Red Profile and stored nowhere else. "Other" is its own row: the free text
behind it is one person's wording and would split one answer into many.
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

VOLUNTEER_DOCTYPE = "VMMS Volunteer"
MEMBERSHIP_DOCTYPE = "VMMS Membership"
MEMBER_DOCTYPE = "VMMS Member"
PROFILE_DOCTYPE = "Red Profile"
PROFESSION_FIELD = "vmms_profession"

_PAGE_CEILING = 200
_CHUNK = 500


@frappe.whitelist()
def summary() -> dict:
	"""Every profession held in the caller's area, with how many people hold it.

	    professions   [{profession, volunteers, members, total}], most held first
	    without       people in the area who have not given a profession
	    people        everybody counted, each person once
	"""
	people = _people_in_scope()
	professions = _profile_values(list(people), PROFESSION_FIELD)

	counts: dict[str, dict] = {}
	without = 0

	for profile, roles in people.items():
		profession = professions.get(profile)

		if not profession:
			without += 1
			continue

		row = counts.setdefault(profession, {"profession": profession, "volunteers": 0, "members": 0, "total": 0})
		row["total"] += 1
		row["volunteers"] += int(bool(roles.get("volunteer")))
		row["members"] += int(bool(roles.get("member")))

	return {
		"professions": sorted(counts.values(), key=lambda row: (-row["total"], row["profession"].lower())),
		"without": without,
		"people": len(people),
	}


@frappe.whitelist()
def people(profession: str, search: str | None = None, limit: int = 50, offset: int = 0) -> dict:
	"""The people in the caller's area who hold `profession`, by name.

	Each row says whether the person is an active volunteer, a current member or
	both, and links to whichever records they have.
	"""
	if not (profession or "").strip():
		frappe.throw(_("Name a profession."), frappe.ValidationError)

	scoped = _people_in_scope()
	holders = _holders(scoped, profession)

	details = _profile_details(sorted(holders))
	needle = (search or "").strip().lower()

	rows = []
	for profile in holders:
		person = details.get(profile, {})
		name = person.get("full_name") or profile
		if needle and needle not in name.lower():
			continue
		roles = scoped[profile]
		rows.append(
			{
				"red_profile": profile,
				"full_name": name,
				"photo": person.get("profile_photo"),
				"volunteer": roles.get("volunteer"),
				"member": roles.get("member"),
				"geo_node": roles.get("geo_node"),
			}
		)

	rows.sort(key=lambda row: row["full_name"].lower())

	start = max(0, cint(offset))
	size = max(1, min(cint(limit) or 50, _PAGE_CEILING))
	page = rows[start : start + size]

	from vmmsx.places import place_name

	for row in page:
		row["geo_path"] = place_name(row.pop("geo_node")) if row.get("geo_node") else None

	return {"profession": profession, "total": len(rows), "people": page}


# --- reading the area ---------------------------------------------------------


def _people_in_scope() -> dict[str, dict]:
	"""{red_profile: {volunteer, member, geo_node}} for everybody the caller may see.

	Active volunteers and current members, each read through the scoped listing.
	"""
	from vmmsx.member.services import membership as membership_service

	people: dict[str, dict] = {}

	if frappe.has_permission(VOLUNTEER_DOCTYPE, "read"):
		for row in frappe.get_list(
			VOLUNTEER_DOCTYPE,
			filters={"status": "Active"},
			# The serving branch is stored as `home_geo_node` on the volunteer
			# (see `capabilities.SERVING_BRANCH_FIELD`).
			fields=["name", "red_profile", "home_geo_node"],
			limit_page_length=0,
		):
			if row.red_profile:
				people.setdefault(row.red_profile, {}).update(
					{"volunteer": row.name, "geo_node": row.home_geo_node}
				)

	if frappe.has_permission(MEMBERSHIP_DOCTYPE, "read"):
		moment = getdate(today())
		memberships = [
			row
			for row in frappe.get_list(
				MEMBERSHIP_DOCTYPE,
				filters={"membership_status": "Active"},
				fields=["name", "member", "geo_node", "valid_to", "membership_status"],
				limit_page_length=0,
			)
			if row.member and membership_service.is_current(row, moment)
		]
		profiles = _member_profiles({row.member for row in memberships})

		for row in memberships:
			profile = profiles.get(row.member)
			if not profile:
				continue
			person = people.setdefault(profile, {})
			person["member"] = row.member
			person.setdefault("geo_node", row.geo_node)

	return people


def _member_profiles(members: set[str]) -> dict[str, str]:
	"""{VMMS Member: Red Profile}, for members a scoped read already returned."""
	found: dict[str, str] = {}

	for chunk in _chunks(sorted(members)):
		for name, profile in frappe.get_all(
			MEMBER_DOCTYPE, filters={"name": ("in", chunk)}, fields=["name", "red_profile"], as_list=True
		):
			if profile:
				found[name] = profile

	return found


def _profile_values(profiles: list[str], fieldname: str) -> dict:
	values: dict = {}

	for chunk in _chunks(profiles):
		for name, value in frappe.get_all(
			PROFILE_DOCTYPE, filters={"name": ("in", chunk)}, fields=["name", fieldname], as_list=True
		):
			values[name] = value

	return values


def _profile_details(profiles: list[str]) -> dict:
	details: dict = {}

	for chunk in _chunks(profiles):
		for row in frappe.get_all(
			PROFILE_DOCTYPE,
			filters={"name": ("in", chunk)},
			fields=["name", "full_name", "profile_photo"],
		):
			details[row.name] = row

	return details


def _holders(scoped: dict, profession: str) -> set[str]:
	"""Which of these people hold `profession`."""
	holders: set[str] = set()

	for chunk in _chunks(sorted(scoped)):
		holders.update(
			frappe.get_all(
				PROFILE_DOCTYPE,
				filters={PROFESSION_FIELD: profession, "name": ("in", chunk)},
				pluck="name",
			)
		)

	return holders


def _chunks(items: list[str]):
	for start in range(0, len(items), _CHUNK):
		yield items[start : start + _CHUNK]
