# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The analytics endpoint. One method, and it takes no scope.

Every guarantee worth stating is in `analytics/services/summary.py`, which this
is a two-line whitelist over: the scope is the session's and cannot be supplied,
each doctype is counted through its own registered role, and a caller holding
nothing gets zeroes rather than a refusal.

**One endpoint rather than six.** The screen draws the tiles, the breakdowns,
the trend and the coverage table together, and six requests would paint it in six
stages, each with its own spinner and its own chance of a partial answer that
reads as a complete one.

**`geo_node` narrows and cannot widen.** It is intersected with what the caller
already holds, so a branch coordinator naming the country still gets their
branch. A node that does not exist counts nothing, which is what a query string
somebody typed deserves.
"""

import frappe

from vmmsx.analytics.services import summary


@frappe.whitelist()
def branch_summary(geo_node: str | None = None, months: int | None = None) -> dict:
	"""Every figure the console's analytics screen draws, for the caller's area."""
	return summary.branch_summary(geo_node=geo_node, months=int(months or summary.MONTHS))


@frappe.whitelist()
def overview_registers() -> dict:
	"""Complete scoped chart inputs, independent of register-list page limits.

	**Read in a handful of queries, not one per person.** A national register is
	thousands of people, and asking for each one's gender separately made this
	the slowest call in the console. The people are still read through the
	scoped `get_list`; their profiles are read only after that, in batches.
	"""
	from frappe.utils import nowdate

	volunteers = summary._rows(
		"VMMS Volunteer",
		"home_geo_node",
		None,
		["name", "red_profile", "home_geo_node", "status", "joined_on"],
	)
	members = summary._rows(
		"VMMS Membership", "geo_node", None, ["name", "member", "geo_node", "membership_status", "valid_from"]
	)

	# Profile attributes are read only through a registration already admitted by core scope.
	member_profiles = _values("VMMS Member", {row.member for row in members if row.member}, "red_profile")
	genders = _values(
		"Red Profile",
		{row.red_profile for row in volunteers if row.red_profile} | {p for p in member_profiles.values() if p},
		"gender",
	)

	return {
		"as_of": nowdate(),
		"volunteers": [
			{
				"volunteer": row.name,
				"full_name": "",
				"geo_node": row.home_geo_node,
				"status": row.status,
				"joined_on": row.joined_on,
				"gender": genders.get(row.red_profile),
			}
			for row in volunteers
		],
		"members": [
			{
				"member": row.member,
				"full_name": "",
				"geo_node": row.geo_node,
				"status": row.membership_status,
				"valid_from": row.valid_from,
				"gender": genders.get(member_profiles.get(row.member)),
			}
			for row in members
		],
		"deployments": _overview_deployments(),
	}


# Names are read in pieces, so a national reader's `in (...)` list stays a size
# every database accepts.
_CHUNK = 1000


def _values(doctype: str, names: set, fieldname: str) -> dict:
	"""{name: fieldname} for these records, read in batches."""
	ordered = sorted(names)
	values: dict = {}

	for start in range(0, len(ordered), _CHUNK):
		values.update(
			frappe.get_all(
				doctype,
				filters={"name": ("in", ordered[start : start + _CHUNK])},
				fields=["name", fieldname],
				as_list=True,
			)
		)

	return values


def _overview_deployments() -> list[dict]:
	"""Every deployment in scope, with the roster only where the page uses it.

	The overview counts the people out on **active** deployments and nothing
	else from a roster, so only those rosters are read. The rest go out with an
	empty list rather than the hundreds of roster reads they used to cost.
	"""
	from vmmsx.deployment.services import participation

	rows = summary._rows(
		"VMMS Deployment",
		"geo_node",
		None,
		["name", "terms_of_reference", "geo_node", "status", "start_date", "end_date"],
	)
	terms = _values("VMMS Terms of Reference", {row.terms_of_reference for row in rows if row.terms_of_reference}, "tor_name")

	return [
		{
			"name": row.name,
			"tor_name": terms.get(row.terms_of_reference) or row.name,
			"geo_node": row.geo_node,
			"status": row.status,
			"start_date": row.start_date,
			"end_date": row.end_date,
			"participants": [
				{"volunteer": volunteer, "is_on_deployment": True}
				for volunteer in participation.participants_of(row.name)
			]
			if row.status == "Active"
			else [],
		}
		for row in rows
	]
