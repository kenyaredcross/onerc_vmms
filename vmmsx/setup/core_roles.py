# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The six roles every society's ladder needs, so nobody hand-creates them.

`gambia.py` and `kenya.py` each carry their own `_roles()`, and diffing the two
tables is the proof: underneath GRCS's extra `Branch Coordinator` and `Stipend
Manager`, both societies define the same six — somebody reviewing volunteer
applications, somebody reviewing membership applications, somebody sending
people out on deployment, an approved volunteer, an approved member, and an
account that is none of those yet. That was previously a step the Gambia setup
guide asked a real administrator to do by hand, in Desk > Role List, before
anything else in the sequence — because nothing shipped them. This module ships
them, the same idempotent way a seed's own `_roles()` does, so a brand-new site
like Tanzania's has them the moment the app is installed.

**This creates records, not wiring, and that is deliberate.** Every module in
this app that reads a role reads it from a setting a society names —
`vmms_volunteer_scope_role`, `vmms_volunteer_member_role`, and so on — never a
literal in source, which is the rule `registration/services/desk.py` and
`volunteer/services/society.py` both state and this module does not break: a
society is free to point those settings at a role named something else
entirely, or to rename one of the six after the fact. What was missing was not
a choice of names — GRCS and Kenya independently reached for the same ones — it
was the six existing at all before an administrator can point anything at them.

**Idempotent, and additive only.** Checks before it writes, same as every seed;
never edits a role that already exists, so a society that has since changed a
description or the desk-access flag on one of these keeps its own edit.
"""

import frappe

from vmmsx.registration.services.desk import PORTAL_HOME

ROLE_VOLUNTEER_APPROVER = "Volunteer Approver"
ROLE_MEMBERSHIP_APPROVER = "Membership Approver"
ROLE_DEPLOYMENT_MANAGER = "Deployment Manager"
ROLE_VOLUNTEER = "Volunteer"
ROLE_MEMBER = "Member"
ROLE_APPLICANT = "Society Applicant"

# (name, description, desk_access)
ROLES = (
	(
		ROLE_VOLUNTEER_APPROVER,
		"Reviews volunteer applications within the area they are assigned to.",
		True,
	),
	(
		ROLE_MEMBERSHIP_APPROVER,
		"Reviews membership applications within the area they are assigned to.",
		True,
	),
	(
		ROLE_DEPLOYMENT_MANAGER,
		"Sends people out: deployments, deployment requests and branch transfers.",
		True,
	),
	(ROLE_VOLUNTEER, "An approved volunteer, with the self-service portal.", False),
	(ROLE_MEMBER, "An approved member, with the self-service portal.", False),
	(
		ROLE_APPLICANT,
		"Somebody who has made an account and not yet been approved as anything.",
		False,
	),
)


def install() -> list[dict]:
	"""Create each of the six core roles that does not already exist.

	Returns one row per role, saying what it did, so a `bench migrate` on a site
	that already has them reports `exists` rather than being silent about having
	run — the same reporting shape `gambia.py`'s own `_roles()` uses.
	"""
	rows = []

	for name, description, desk in ROLES:
		if frappe.db.exists("Role", name):
			rows.append({"role": name, "status": "exists"})
			continue

		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": name,
				"desk_access": int(desk),
				"home_page": None if desk else PORTAL_HOME,
				"description": description,
			}
		).insert(ignore_permissions=True)

		rows.append({"role": name, "status": "created"})

	return rows
