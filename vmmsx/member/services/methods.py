# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Which ways of paying a society will take, and what an applicant is offered.

**The society decides; the payments app supplies the list.** `onerc_payments`
knows what gateways exist on this site, which of them are active and which can
take money *in* — that is its register and vmmsx does not keep a second copy of
it. What vmmsx keeps is one decision per gateway: will this society offer it to
somebody joining. That decision is a row of `VMMS Payment Method` on core's
`National Society Settings`, written once by `sync()` and thereafter the
society's to change.

**Nothing here talks to a gateway.** The seam is still
`member/services/payment.py`, which is the only file in the Member module that
knows a payment exists. This module answers "what may be offered" and hands the
answer to a form; `payment.request()` still owns asking for the money.

**Manual is on by default, and that is a rule rather than an accident.** A
society that has bought no gateway integration at all still takes money — at a
branch counter, by bank transfer, in cash against a receipt — and the manual
driver is how that gets recorded. So a society that has never opened this screen
can still take a membership fee, which is the state every other setting in this
product ships in: empty narrows nothing.

**An absent payments app is ordinary.** vmmsx does not declare `onerc_payments`
in `required_apps` — a society running fee-free membership should not be made to
install a gateway — so every reader here answers empty rather than raising, the
same graceful-absence contract the Buzz, learning and payments seams keep.
"""

import frappe

SETTINGS_DOCTYPE = "National Society Settings"
GATEWAY_DOCTYPE = "OneRC Payment Gateway"

#: The Table Custom Field this module reads and writes. Installed by
#: `patches/install_membership_payment_methods.py`.
METHODS_FIELD = "vmms_payment_methods"

#: The gateway that means "somebody at the society will confirm this by hand" —
#: a bank transfer, a counter at a branch, cash against a receipt.
#:
#: Named because two rules turn on it, and for no other reason: it is seeded
#: first, so the method that works without any integration at all is the one a
#: society's list leads with, and it is the one this module will not let a
#: society end up without by accident. Nothing here branches on any other
#: gateway's name — adding a second card processor changes no line in this file.
MANUAL = "Manual"


def is_available() -> bool:
	"""Is the payments app installed, with a gateway register to read?"""
	from vmmsx.member.services import payment

	return payment.is_available() and frappe.db.table_exists(f"tab{GATEWAY_DOCTYPE}")


def offered() -> list[dict]:
	"""The ways an applicant may pay, in the order the society put them.

	Each row is one the society has ticked *and* the payments app still reports
	as active and able to take money in. Both halves are checked on every call
	and neither is cached: a gateway switched off in the payments app stops being
	offered here immediately, which is what somebody switching it off meant.

	A society that has never opened the settings form gets whatever the payments
	app offers, with the manual method among them. See the module docstring:
	empty narrows nothing, and a society cannot be left unable to take a fee
	because nobody filled in a form.
	"""
	if not is_available():
		return []

	live = {row["gateway"]: row for row in _live_gateways()}

	if not live:
		return []

	chosen = _configured()

	if not chosen:
		return list(live.values())

	return [
		{**live[row["gateway"]], "label": row["label"] or live[row["gateway"]]["label"], "instructions": row["instructions"]}
		for row in chosen
		if row["is_enabled"] and row["gateway"] in live
	]


def is_offered(gateway: str | None) -> bool:
	"""May an applicant choose this one? Asked before a fee is requested."""
	if not gateway:
		return False

	return any(row["gateway"] == gateway for row in offered())


def default() -> str | None:
	"""What to select when nobody has chosen, or None when nothing is offered.

	The first thing the society listed. Ordering on the settings form is the
	society's statement of what it would rather people used — a branch that takes
	M-Pesa and would prefer not to count cash puts M-Pesa at the top — and this
	is the only thing that reads it.
	"""
	rows = offered()

	return rows[0]["gateway"] if rows else None


def sync() -> dict:
	"""Give the society a row for every gateway the payments app offers.

	Additive and non-destructive, exactly like `content.blocks.seed`: a gateway
	with no row gets one, and a row that already exists is left alone whatever it
	says. That is what makes this safe to run on every migrate, and it is why a
	society that unticked a method keeps it unticked through the next deploy.

	A row whose gateway has since disappeared from the payments app is **not**
	deleted. It costs nothing — `offered()` intersects with what is live, so it
	is not shown to anybody — and deleting it would throw away the society's
	answer for a gateway that may be reinstated next week.
	"""
	if not is_available():
		return {"created": 0, "existed": 0}

	settings = frappe.get_single(SETTINGS_DOCTYPE)

	if not settings.meta.has_field(METHODS_FIELD):
		return {"created": 0, "existed": 0}

	held = {(row.gateway or "").strip() for row in settings.get(METHODS_FIELD) or []}
	created = 0

	for gateway in _manual_first(_live_gateways()):
		if gateway["gateway"] in held:
			continue

		settings.append(
			METHODS_FIELD,
			{
				"gateway": gateway["gateway"],
				"label": gateway["label"],
				# Everything the payments app has active is offered until a
				# society says otherwise. The manual method is called out in the
				# docstring because it is the one that must never arrive
				# unticked — a society with no gateway integration still takes
				# money — but the rule that ships everything enabled is the same
				# "empty narrows nothing" rule the rest of this product follows.
				"is_enabled": 1,
			},
		)
		created += 1

	if created:
		# Configuration written by a migration running as Administrator. The
		# society's own edits to this table go through the form and its
		# permissions, as they should.
		settings.save(ignore_permissions=True)

	return {"created": created, "existed": len(held)}


def _manual_first(gateways: list[dict]) -> list[dict]:
	"""Seed order: the method that always works, then the rest as they came.

	Only affects the order rows are *created* in, which is the order a society
	first sees them and — until they reorder the table — the order an applicant
	is offered them. See `default()`: the top of that list is what a form
	selects for somebody who has not chosen.
	"""
	return sorted(gateways, key=lambda row: row["gateway"] != MANUAL)


def _live_gateways() -> list[dict]:
	"""What the payments app says it can take money *in* with, right now.

	`supports_inbound` as well as `is_active`, because a gateway configured for
	paying volunteers their stipends is not a gateway a member can join through,
	and offering it would be a form asking somebody to pay by a route that only
	goes the other way.
	"""
	rows = frappe.get_all(
		GATEWAY_DOCTYPE,
		filters={"is_active": 1, "supports_inbound": 1},
		fields=["name", "label", "description"],
		order_by="name asc",
		# Another app's configuration register, read to find out what this
		# society may be offered. The caller is an applicant filling in a form
		# and holds no role on the payments app — requiring one would mean
		# granting every prospective member read access to the gateway
		# configuration in order to be shown two radio buttons.
		ignore_permissions=True,
	)

	return [
		{
			"gateway": row.name,
			"label": row.label or row.name,
			"description": row.description or "",
			"instructions": "",
		}
		for row in rows
	]


def _configured() -> list[dict]:
	"""The society's own rows, in the order they put them, or nothing.

	Read off the Single with `get_all` rather than by loading the document,
	because this is asked on every registration form and the settings record
	carries a great deal this has no business reading.
	"""
	if not frappe.get_meta(SETTINGS_DOCTYPE).has_field(METHODS_FIELD):
		return []

	rows = frappe.get_all(
		"VMMS Payment Method",
		filters={"parent": SETTINGS_DOCTYPE, "parentfield": METHODS_FIELD},
		fields=["gateway", "label", "is_enabled", "instructions"],
		order_by="idx asc",
		# The society's own configuration, read to draw its own registration
		# form. Same argument as `_live_gateways` above.
		ignore_permissions=True,
	)

	return [
		{
			"gateway": (row.gateway or "").strip(),
			"label": (row.label or "").strip(),
			"is_enabled": bool(row.is_enabled),
			"instructions": (row.instructions or "").strip(),
		}
		for row in rows
		if (row.gateway or "").strip()
	]
