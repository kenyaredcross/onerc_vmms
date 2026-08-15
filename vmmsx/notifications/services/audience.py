# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Who hears an announcement: a geo question and an affiliation question.

Two independent narrowings, resolved separately and then intersected, because
they answer different things and conflating them is how a broadcast reaches the
wrong county.

**Where** comes from core. The announcement's `geo_node` and everything beneath
it, resolved through `onerc_core.geo.services.adapter.get_descendants`. This
module never queries `tabGeo Node` and never assumes a depth: a national office
anchored at the root reaches the whole society and a ward reaches a ward,
without either being a special case anywhere in this file.

**Who** comes from a dispatch table keyed by `audience`, a closed Select the
server owns. Adding a fourth audience is adding an entry to `_RESOLVERS`, never
adding a branch. Each resolver answers a set of Red Profiles; the login is
looked up once at the end.

**A person is resolved once.** Somebody who is both a volunteer and a member of
the same branch appears in both resolvers and receives one notification, because
the resolvers return sets of profiles and the union is taken before anything is
written. Two copies of one advisory is the thing a person notices, and it is the
kind of bug that only shows up for exactly the people most involved in the
society.

**No login, no notification, and that is not an error.** A society's register
holds people who have never signed in: a member enrolled at a desk by a clerk
has a Red Profile and no `user`. There is nowhere to deliver an in-app
notification to them, so they are dropped from the fan-out rather than counted
as delivered. Email is the channel that reaches them, and `announce.py` sends it
against the profile's email address independently of this.
"""

from collections.abc import Callable

import frappe

from onerc_core.geo.services import adapter

PROFILE_DOCTYPE = "Red Profile"

VOLUNTEER_DOCTYPE = "VMMS Volunteer"
MEMBER_DOCTYPE = "VMMS Member"
MEMBERSHIP_DOCTYPE = "VMMS Membership"

# The states that mean somebody is currently part of the society. A suspended
# volunteer or a lapsed member is deliberately not written to: an announcement
# is addressed to the people a branch is responsible for right now, and somebody
# whose standing has ended should stop hearing from it without anybody having to
# remember to remove them from a list.
ACTIVE_VOLUNTEER = "Active"
ACTIVE_MEMBERSHIP = "Active"

AUDIENCE_EVERYONE = "everyone"
AUDIENCE_VOLUNTEERS = "volunteers"
AUDIENCE_MEMBERS = "members"


def within(geo_node: str) -> list[str]:
	"""The announcement's node and everything under it.

	Through core's adapter, the only way this app is allowed to ask a question
	about the geo tree. The node itself is included because a branch announcing
	something means its own people too, not only the ones below it.
	"""
	nodes = set(adapter.get_descendants(geo_node) or [])
	nodes.add(geo_node)

	return sorted(nodes)


def _volunteers(nodes: list[str]) -> set[str]:
	"""Red Profiles of active volunteers serving at or beneath these nodes.

	`home_geo_node` on the volunteer is the serving branch, which is the right
	field: an announcement from a branch is for the people who serve it, not for
	everybody who happens to live in the area and volunteers elsewhere. Core's
	Red Profile carries a `home_geo_node` too and it answers the other question.
	"""
	rows = frappe.get_all(
		VOLUNTEER_DOCTYPE,
		filters={"status": ACTIVE_VOLUNTEER, "home_geo_node": ["in", nodes]},
		pluck="red_profile",
		# Fanning out is the system acting, not a person reading a register. The
		# alternative is that which volunteers hear from their branch depends on
		# the geo scope of whoever happened to press publish, which would make an
		# announcement's reach silently narrower than the branch it came from.
		# Who may publish at all is the ordinary permission check on VMMS
		# Announcement, made before this is ever called.
		ignore_permissions=True,
	)

	return {row for row in rows if row}


def _members(nodes: list[str]) -> set[str]:
	"""Red Profiles of people holding an active membership at or beneath these.

	Through the membership rather than through `VMMS Member`, because the
	membership is the record that carries a place. The member satellite is the
	person, and a person is not anywhere in particular.
	"""
	members = frappe.get_all(
		MEMBERSHIP_DOCTYPE,
		filters={"membership_status": ACTIVE_MEMBERSHIP, "geo_node": ["in", nodes]},
		pluck="member",
		ignore_permissions=True,  # Same argument as `_volunteers`.
	)

	if not members:
		return set()

	rows = frappe.get_all(
		MEMBER_DOCTYPE,
		filters={"name": ["in", sorted(set(members))]},
		pluck="red_profile",
		ignore_permissions=True,  # Same argument as `_volunteers`.
	)

	return {row for row in rows if row}


def _everyone(nodes: list[str]) -> set[str]:
	return _volunteers(nodes) | _members(nodes)


# The dispatch table. One entry per value of the `audience` Select, and the
# reason this is a dict rather than a chain of comparisons is the rule the member
# module's `approval_mode` set: a closed set the server owns is dispatched, not
# branched, so the set of values and the set of behaviours cannot drift apart.
_RESOLVERS: dict[str, Callable[[list[str]], set[str]]] = {
	AUDIENCE_EVERYONE: _everyone,
	AUDIENCE_VOLUNTEERS: _volunteers,
	AUDIENCE_MEMBERS: _members,
}


def profiles(geo_node: str, audience: str) -> set[str]:
	"""Every Red Profile this announcement is addressed to.

	An unknown audience resolves to nobody rather than to everybody. The Select
	makes an unknown value hard to produce, but the failure modes are not
	symmetrical: delivering to no one is a message somebody notices is missing,
	and delivering to everyone is a message that cannot be recalled.
	"""
	resolve = _RESOLVERS.get(audience)

	if not resolve:
		return set()

	return resolve(within(geo_node))


def logins(profiles_: set[str]) -> dict[str, str]:
	"""Profile name to login, for the profiles that have one.

	One query rather than one per person: a national announcement resolves tens
	of thousands of profiles, and a round trip each would turn publishing into a
	timeout. Profiles with no login are absent from the result, which is what
	drops them from the in-app fan-out.
	"""
	if not profiles_:
		return {}

	rows = frappe.get_all(
		PROFILE_DOCTYPE,
		filters={"name": ["in", sorted(profiles_)], "user": ["is", "set"]},
		fields=["name", "user"],
		ignore_permissions=True,  # Same argument as `_volunteers`.
	)

	return {row.name: row.user for row in rows if row.user}


def emails(profiles_: set[str]) -> list[str]:
	"""Addresses for the same people, for the optional email channel.

	Read from the Red Profile, which is core's spine and the one answer to what
	somebody's address is. Deliberately independent of `logins()`: the whole
	point of the email channel is that it reaches the people the in-app list
	cannot, which is exactly the people with no login.
	"""
	if not profiles_:
		return []

	rows = frappe.get_all(
		PROFILE_DOCTYPE,
		filters={"name": ["in", sorted(profiles_)], "email": ["is", "set"]},
		pluck="email",
		ignore_permissions=True,  # Same argument as `_volunteers`.
	)

	return sorted({row for row in rows if row})
