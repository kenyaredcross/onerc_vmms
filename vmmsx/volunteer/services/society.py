# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Society configuration the Volunteer module reads. Five questions, no constants.

Every one of these is something a national society answers differently, and not
one of them may be a literal in a source file:

1. **Which geo level a volunteer is anchored at** — ACC-03. Kenya may place
   volunteers at county level, another society at ward, a third at branch.
   `vmms_volunteer_anchor_level`.
2. **Which role may see volunteer records, and where** — the role half of geo
   scoping. `vmms_volunteer_scope_role`, read by core at enforcement time
   through the `role_from_setting` registration in `hooks.py`. Named here only
   so the patch that installs it and the code that documents it agree on the
   spelling; nothing in this module resolves it, because resolving it is core's.
3. **Whether accepting a volunteer provisions an HR Employee** —
   `vmms_volunteer_provision_employee`, off by default. A society that does not
   run its volunteers through HR must not have Employee records appear.
4. **Which company a provisioned Employee belongs to** —
   `vmms_volunteer_employee_company`. HR cannot create an Employee without one
   and vmmsx has no business guessing it.
5. **Which role a volunteer's own login is granted on acceptance** —
   `vmms_volunteer_member_role`. Deliberately a different question from 2: one
   is who may see the register, the other is somebody being able to see
   themselves in it.

All five are **Custom Fields vmmsx owns** on core's National Society Settings,
installed by this app's own patches. Core's doctype is not edited: a product
pushing its fields into the shared foundation's source is how the foundation
stops being shared.

**Empty configuration means unconstrained or off, never forbidden or on.** A
society that has not named an anchor level has not thereby said volunteers may
exist nowhere; a society that has not switched provisioning on gets no Employees
rather than an error. The one deliberate exception is the scope role, where
empty means *closed* — that is core's fail-closed behaviour and it is the right
direction for a record holding personal data.
"""

import frappe
from onerc_core.society.services import config

ANCHOR_LEVEL_FIELD = "vmms_volunteer_anchor_level"
SCOPE_ROLE_FIELD = "vmms_volunteer_scope_role"
PROVISION_EMPLOYEE_FIELD = "vmms_volunteer_provision_employee"
EMPLOYEE_COMPANY_FIELD = "vmms_volunteer_employee_company"

# Which role a volunteer's own login is given when they are accepted, so that
# they can see their own record. A fifth society question, and the same shape as
# the four above: a Custom Field vmmsx owns, installed by
# `patches/install_self_service_roles.py`, empty by default. Empty means nothing
# is granted, never that everybody is.
MEMBER_ROLE_FIELD = "vmms_volunteer_member_role"


def volunteer_anchor_level() -> str | None:
	"""The Geo Level a volunteer must be anchored at, or None if unconstrained.

	Read through core's settings accessor so a site whose settings single has
	never been saved degrades to "unconstrained" instead of throwing, and read
	on every call so changing the setting takes effect without a restart.
	"""
	return config.settings().get(ANCHOR_LEVEL_FIELD) or None


def anchor_level_is_configured() -> bool:
	"""Whether the society has narrowed where a volunteer may be anchored."""
	return bool(volunteer_anchor_level())


def assert_anchor_level(geo_node: str) -> None:
	"""Throw unless `geo_node` sits at the level this society permits (ACC-03).

	Geo is reached only through core's adapter — this app never queries the geo
	tables and never assumes a depth. With no level configured this is a no-op,
	which is what "the society has not narrowed it" has to mean.
	"""
	from frappe import _
	from onerc_core.geo.services import adapter

	required = volunteer_anchor_level()

	if not (required and geo_node):
		return

	level = adapter.get_level(geo_node)

	if level["key"] == required:
		return

	labels = {row["key"]: row["name"] for row in adapter.level_labels()}

	frappe.throw(
		_("{0} is at {1} level. This society places volunteers at {2} level.").format(
			frappe.bold(adapter.get_full_path(geo_node)),
			frappe.bold(level["name"]),
			frappe.bold(labels.get(required, required)),
		),
		frappe.ValidationError,
		title=_("Anchor Level Not Permitted"),
	)


def provisions_employees() -> bool:
	"""Does this society want an HR record created alongside a volunteer?

	Off unless somebody switched it on. A society running volunteering without
	HR involvement is the ordinary case, and silently creating Employee records
	for it would put people into a payroll-shaped system nobody asked for.
	"""
	return bool(config.settings().get(PROVISION_EMPLOYEE_FIELD))


def employee_company() -> str | None:
	"""Which company a provisioned Employee is created under, if any is set."""
	return config.settings().get(EMPLOYEE_COMPANY_FIELD) or None


def volunteer_member_role() -> str | None:
	"""The role a volunteer's own login is granted, or None if unconfigured.

	Resolved rather than read raw: a setting naming a role somebody has since
	deleted is logged and answers None, because a self-service grant that
	silently stopped happening would look exactly like a society that had not
	configured one yet. Read on every call, so changing it takes effect without
	a restart.
	"""
	from vmmsx.registration.services import society as self_service

	return self_service.resolved_role(config.settings().get(MEMBER_ROLE_FIELD), MEMBER_ROLE_FIELD)


def society_name() -> str | None:
	"""The society's own name, for anything rendered to a person."""
	return config.settings().organization_name


def default_citizenship_country() -> str | None:
	"""The country a volunteer application defaults its citizenship question to.

	Core's own `country` on National Society Settings, not a Custom Field vmmsx
	owns: a Gambian society's applicants default to Gambia and a Kenyan
	society's to Kenya because that field already says so, and inventing a
	second vmmsx-owned copy of it would be a second place for the two to
	disagree. None on a site whose settings singleton has never named one,
	which is an unconfigured society rather than an error — the field on the
	application stays required and an administrator or the applicant fills it
	in by hand.
	"""
	return config.settings().get("country") or None
