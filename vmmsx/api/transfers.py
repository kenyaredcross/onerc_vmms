# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Branch transfers, for the volunteer asking and the branches deciding.

The volunteer's three are possessive — they take no volunteer, so nobody can be
named but the caller. The console's list is the caller's own branches, in one
direction, read through the transfer's scoping. Deciding is the approval
engine's ordinary `api.approvals.decide`; nothing here decides anything.

See `deployment/services/transfer_requests.py` for the flow.
"""

import frappe
from frappe import _

from vmmsx.deployment.services import transfer_requests

DIRECTIONS = ("outgoing", "incoming")
SHOWS = ("open", "decided")


@frappe.whitelist()
def my_transfer() -> dict:
	"""The caller's open transfer (or the one decided in the last month), and
	whether they may ask for one here at all."""
	return {"transfer": transfer_requests.mine(), "can_request": transfer_requests.requests_open()}


@frappe.whitelist(methods=["POST"])
def request_my_transfer(to_geo_node: str, reason: str) -> dict:
	"""Ask to move to another branch. The caller's own branch decides first."""
	return transfer_requests.request_mine(to_geo_node, reason)


@frappe.whitelist(methods=["POST"])
def withdraw_my_transfer(name: str) -> dict:
	"""Take back the caller's own request before it is decided."""
	return transfer_requests.withdraw_mine(name)


@frappe.whitelist()
def branch_transfers(direction: str = "outgoing", show: str = "open") -> dict:
	"""Volunteers leaving the caller's branches, or joining them."""
	if direction not in DIRECTIONS or show not in SHOWS:
		frappe.throw(_("Unknown transfer list."), frappe.ValidationError)

	user = frappe.session.user

	if user == "Guest":
		raise frappe.PermissionError

	return {"direction": direction, "show": show, "rows": transfer_requests.rows_for(user, direction, show)}


@frappe.whitelist()
def volunteer_transfer(volunteer: str) -> dict:
	"""May the caller move this volunteer, and is a move already under way?"""
	frappe.has_permission("VMMS Volunteer", ptype="read", doc=volunteer, throw=True)

	return transfer_requests.for_volunteer(volunteer, frappe.session.user)


@frappe.whitelist()
def transfer_counts() -> dict:
	"""How many are open each way, and how many the caller can decide."""
	user = frappe.session.user

	if user == "Guest":
		raise frappe.PermissionError

	counts = {}

	for direction in DIRECTIONS:
		rows = transfer_requests.rows_for(user, direction, "open")
		counts[direction] = {"open": len(rows), "mine": sum(1 for row in rows if row["can_act"])}

	return counts
