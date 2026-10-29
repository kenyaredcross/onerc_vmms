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
	"""Complete scoped chart inputs, independent of register-list page limits."""
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
	def gender(profile):
		return frappe.db.get_value("Red Profile", profile, "gender") if profile else None

	return {
		"as_of": nowdate(),
		"volunteers": [
			{
				"volunteer": row.name,
				"full_name": "",
				"geo_node": row.home_geo_node,
				"status": row.status,
				"joined_on": row.joined_on,
				"gender": gender(row.red_profile),
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
				"gender": gender(frappe.db.get_value("VMMS Member", row.member, "red_profile")),
			}
			for row in members
		],
		"deployments": _overview_deployments(),
	}


def _overview_deployments() -> list[dict]:
	from vmmsx.deployment.services import participation

	names = summary._rows("VMMS Deployment", "geo_node", None, ["name"])
	rows = []
	for row in names:
		doc = frappe.get_doc("VMMS Deployment", row.name)
		rows.append(
			{
				"name": doc.name,
				"tor_name": frappe.db.get_value("VMMS Terms of Reference", doc.terms_of_reference, "tor_name")
				or doc.name,
				"geo_node": doc.geo_node,
				"status": doc.status,
				"start_date": doc.start_date,
				"end_date": doc.end_date,
				"participants": [
					{"volunteer": volunteer, "is_on_deployment": True}
					for volunteer in participation.participants_of(doc.name)
				],
			}
		)
	return rows
