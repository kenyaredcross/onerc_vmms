# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The doctype permissions a staff scope role needs, and not one more.

`staff/services/workspaces.py` puts a society's configured scope role onto a
workspace, so its holder sees the icon and the shortcut. That is visibility,
and it is a different question from whether the role can open what the
shortcut points at: every VMMS doctype ships with exactly one row in its own
permissions list, `System Manager`, because which society role gets anything
beyond that is configuration, and a literal in a doctype JSON is exactly what
this app does not do. Without this module, a "Volunteer Coordinator" a society
names would see the Volunteers workspace and get a permission error on every
shortcut in it.

Modeled on `registration/services/permissions.py`'s exact shape — the same
`add_permission` / `update_permission_property` pair, the same
create-if-missing idempotency — widened from "read, and nothing else" to
"read, write and create" for these, because a self-service volunteer looking at
their own hours is a different act from a coordinator who does this job, and a
staff scope role that could see but never touch its own module's records would
be a workspace of read-only dead ends.

**Not delete.** Deleting an operational record — a membership, a volunteer, a
deployment — stays an administrator's decision unless a society explicitly
widens it, by hand, through the ordinary Role Permissions Manager; this
installer never touches `delete` in either direction, exactly the way
`registration/services/permissions.py` never touches anything but `read`.

**`VMMS Volunteer Application` is read-only, and it is deliberately widened
past what geo scoping would give it.** `hooks.py`'s `onerc_scopeable_doctypes`
comment explains why core does not register it: "being a County Coordinator
does not make you this application's approver" is a statement about who may
*decide* one, not about who may *browse* the queue, and `api/approvals.py`'s
gate is what enforces the first and is unaffected by this grant. But because
it is not geo-scoped, a `read` grant here is nationwide rather than narrowed to
the holder's own assignment, unlike every other doctype this module touches —
a real widening, accepted because the Volunteers workspace has shown this
doctype as a shortcut since the cluster was built (`staff/tests/test_workspaces
.py::test_the_volunteers_child_covers_exactly_its_doctypes`) and a shortcut a
society already sees should not be a permission error.

**Terms of Reference is shared config.** It governs what a deployment request
may become, so whichever of the deployment or the deployment-request scope role
a society has configured may maintain it; a society naming only one of the two
still gets a usable Deployments workspace rather than one dead card in it.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property
from onerc_core.society.services import config

from vmmsx.registration.services import society as self_service

FULL = {"read": 1, "write": 1, "create": 1}
READ_ONLY = {"read": 1}


def role_grants(resolve: bool = True) -> list[tuple[str | None, dict]]:
	"""The (role, {doctype: rights}) table this installer works from.

	A list rather than a dict keyed by role: two scope-role settings a society
	names the same custom role would otherwise collide in a dict literal and
	silently lose one cluster's grants.

	`resolve=False` puts the *settings field* in the role slot instead of the
	role a society named, so a caller that only wants the doctypes can read them
	without a configured site. That caller is `staff/tests/test_console.py`,
	which checks this table against the section table in
	`staff/services/console.py`: a console section gated on a doctype no scope
	role is ever granted would be a tab only an administrator could open, and a
	society would have no way to hand it to anybody.
	"""
	from vmmsx.deployment.services import society as deployment_society
	from vmmsx.notifications.services import society as announcement_society
	from vmmsx.sms.services import society as sms_society
	from vmmsx.staff.services.workspaces import (
		BRANCH_LOCATION_SCOPE_ROLE_FIELD,
		MEMBERSHIP_SCOPE_ROLE_FIELD,
		TASK_SCOPE_ROLE_FIELD,
	)
	from vmmsx.stipend.services import society as stipend_society
	from vmmsx.volunteer.services import society as volunteer_society

	def holder(field: str) -> str | None:
		return _role(field) if resolve else field

	return [
		(
			holder(MEMBERSHIP_SCOPE_ROLE_FIELD),
			{
				"VMMS Member": FULL,
				"VMMS Membership": FULL,
				"VMMS Membership Type": FULL,
				"VMMS Membership Benefit": FULL,
			},
		),
		(
			holder(volunteer_society.SCOPE_ROLE_FIELD),
			{
				"VMMS Volunteer": FULL,
				"VMMS Certification": FULL,
				"VMMS Certification Type": FULL,
				"VMMS Course Mapping": FULL,
				"VMMS Time Log": FULL,
				# See the module docstring: read-only, and nationwide rather than
				# geo-narrowed, because core does not register this doctype.
				"VMMS Volunteer Application": READ_ONLY,
			},
		),
		(
			holder(deployment_society.DEPLOYMENT_SCOPE_ROLE_FIELD),
			# `Project` is ERPNext's, and it is the one standard doctype this table
			# grants on. It ships with `Projects Manager`, `Projects User` and
			# `Employee` rows of its own, which is a recruitment and accounting
			# audience rather than a volunteering one; a society's deployment
			# coordinator holds none of them. The grant is narrowed by core's geo
			# scoping like every other row here — `hooks.py` registers `Project` on
			# `vmms_geo_node` — so it widens who may open the programmes in their own
			# branch and nothing beyond it.
			{"Project": FULL, "VMMS Deployment": FULL, "VMMS Terms of Reference": FULL},
		),
		(
			holder(deployment_society.REQUEST_SCOPE_ROLE_FIELD),
			{"VMMS Deployment Request": FULL, "VMMS Terms of Reference": FULL},
		),
		(holder(deployment_society.TRANSFER_SCOPE_ROLE_FIELD), {"VMMS Branch Transfer": FULL}),
		(holder(stipend_society.REPORT_SCOPE_ROLE_FIELD), {"VMMS Stipend Progress Report": FULL}),
		(holder(stipend_society.PAYMENT_SCOPE_ROLE_FIELD), {"VMMS Stipend Payment Form": FULL}),
		# The volunteer holding a task needs none of this: their own portal reaches
		# it by ownership, through `api/tasks.py`, and never by role. This grant is
		# for the coordinator who assigns work and signs it off.
		# `VMMS Task Batch` rides on the same role for the reason `hooks.py` gives
		# at its scope registration: a coordinator who may see the tasks must be
		# able to open the record that explains why forty of them exist. `VMMS
		# Task Type` is the society's own vocabulary for this module, maintained
		# by the same people.
		(
			holder(TASK_SCOPE_ROLE_FIELD),
			{"VMMS Task": FULL, "VMMS Task Batch": FULL, "VMMS Task Type": FULL},
		),
		# `read` here is the desk's, and it is narrowed by geo scoping like every
		# other row in this table. What a signed-out visitor sees on the public map
		# is `is_published` on each location and has nothing to do with this grant.
		(holder(BRANCH_LOCATION_SCOPE_ROLE_FIELD), {"VMMS Branch Location": FULL}),
		# The one row here that grants on a doctype this app does not own. `SMS
		# Campaign` belongs to onerc_sms, an optional companion app — `_grant`'s
		# existing "skip a doctype that does not exist" guard is what keeps a site
		# without it unaffected, same as every other row on a site missing the
		# module it belongs to. Geo scoping is not this grant's job: it comes from
		# `SMS Campaign.resolve_from_doctype()` reading VMMS Volunteer/VMMS Member
		# with the campaign owner's own already-scoped permissions. See
		# `vmmsx/sms/services/society.py`.
		(holder(sms_society.SCOPE_ROLE_FIELD), {"SMS Campaign": FULL}),
		# Broadcasting. `VMMS Announcement` has been scopeable on its own
		# `geo_node` since the notification module was built — see `hooks.py` —
		# and until now no scope role was ever granted it, so the register was
		# an administrator's and the fan-out had no console surface at all. The
		# grant is what opens the Communication section; core's scoping is what
		# keeps a branch coordinator addressing their own branch and not the
		# country. `create` matters here more than anywhere else in this table:
		# composing is the whole of what the section does.
		#
		# The type beside it is read-only, and that asymmetry is deliberate: what
		# kinds of announcement a society has is a decision made once, and a
		# coordinator picking one from a list in the middle of composing should
		# not be able to invent a new kind by typing in the box.
		(
			holder(announcement_society.SCOPE_ROLE_FIELD),
			{"VMMS Announcement": FULL, "VMMS Announcement Type": READ_ONLY},
		),
	]


def install() -> dict:
	"""Grant every currently configured staff scope role its doctype permissions.

	Idempotent, and safe to re-run directly once a society changes one of the
	scope-role settings this reads:

	    bench --site <site> execute vmmsx.staff.services.permissions.install

	Called from `after_migrate`, right after the staff workspace cluster itself
	— a role only needs doctype permissions once something has shown it a
	shortcut to click. Reports doctype -> role granted, per role, so "nothing
	granted" is visible as an empty dict rather than silence.
	"""
	granted = {}
	for role, doctypes in role_grants():
		if not role:
			continue
		for doctype, rights in doctypes.items():
			if _grant(doctype, role, rights):
				granted.setdefault(role, []).append(doctype)

	return granted


def _role(field: str) -> str | None:
	"""A staff scope role setting, resolved the same way `staff/services/
	workspaces.py::_roles()` resolves it for workspace visibility — a value
	naming a role somebody has since deleted answers None rather than being
	handed to `add_permission`."""
	return self_service.resolved_role(config.settings().get(field), field)


def _grant(doctype: str, role: str, rights: dict) -> bool:
	"""Ensure `role` holds `rights` on `doctype`. Returns whether anything was added.

	Mirrors `registration/services/permissions.py::grant_read`, widened to more
	than one property: `add_permission` seeds the Custom DocPerm row once, and
	`update_permission_property` sets each named right explicitly every time a
	role's grant is (re-)installed, so a row an administrator edited by hand and
	then emptied is repaired rather than trusted. A right this installer never
	names — `delete` above all — is never touched, in either direction.
	"""
	if not frappe.db.exists("DocType", doctype):
		return False

	added = bool(add_permission(doctype, role, 0))

	for prop, value in rights.items():
		update_permission_property(doctype, role, 0, prop, value)

	frappe.clear_cache(doctype=doctype)

	return added
