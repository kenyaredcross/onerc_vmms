# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Society configuration the self-service journey reads. Two questions, no constants.

**Which role a self-registering account holds** — `vmms_self_service_role`. A
person who has just created a website account is not yet a volunteer and not yet
a member. They are somebody the society has heard from, and the only thing they
may do is fill in one of the two registration forms. The role that says so is a
society's to name, exactly like the scope roles and the certificate print role
before it, and it is a **Custom Field vmmsx owns** on core's National Society
Settings, installed by `patches/install_self_service_roles.py`. Core's doctype
is not edited.

**Empty means the landing surface is not installed** — not "everybody sees it".
This is the same fail-closed direction the scope roles take, for the same
reason: a workspace with no roles on it is visible to every desk user on the
site, so an unconfigured setting that installed one anyway would put a
registration page in front of the whole national society. `workspaces.install()`
refuses rather than guesses. See its docstring.

**The role needs desk access, and that is not an accident.** A Frappe Workspace
is a desk surface, and `User.set_system_user()` promotes an account to a System
User the moment it holds any role with `desk_access`. So the role a society names
here is what turns a self-registered website account into somebody who can be
shown a workspace at all. A society that would rather its applicants never reach
the desk simply leaves this empty and drives registration from the two web form
routes, which are ordinary portal pages and need none of this.

**At what age somebody stops needing a guardian** — `vmms_minor_age`. Here
rather than in `volunteer/services/society.py` because it is not a volunteering
question: the age of majority is a fact about a jurisdiction, it applies to
every registration a society runs, and putting it beside the volunteer settings
would mean the membership path eventually asking the volunteer module how old a
child is. Also a Custom Field vmmsx owns, installed by
`patches/install_identity_document_rules.py`.

**Empty means the guardian rules are off, not that everyone is a minor.** Same
fail-open direction as the anchor level and the employee provisioning flag, and
for the same reason: a society that has not configured minor handling has not
thereby said it accepts nobody. Guessing eighteen would be this app inventing a
law.
"""

import frappe
from frappe.utils import cint
from onerc_core.society.services import config

SELF_SERVICE_ROLE_FIELD = "vmms_self_service_role"
MINOR_AGE_FIELD = "vmms_minor_age"


def minor_age() -> int | None:
	"""The age this society treats as adult, or None if it has not said.

	Read through core's settings accessor so a site whose settings single has
	never been saved degrades to "not configured" instead of throwing, and read
	on every call so changing the setting takes effect without a restart.

	Zero and empty are the same answer — nobody is a minor — because an Int
	Custom Field that has never been filled in reads as 0, and a society cannot
	mean "the age of majority is zero".
	"""
	return cint(config.settings().get(MINOR_AGE_FIELD)) or None


def self_service_role() -> str | None:
	"""The role a self-registering account holds, or None if unconfigured.

	Resolved rather than read raw, exactly like the two member-facing role
	settings: a value naming a role somebody has since deleted answers None and
	is logged, rather than being handed to a caller that would then try to build
	a workspace pointing at a role that does not exist.

	Read through core's settings accessor, so a site whose settings single has
	never been saved degrades to "unconfigured" instead of throwing, and read on
	every call so changing the setting takes effect without a restart.
	"""
	return resolved_role(config.settings().get(SELF_SERVICE_ROLE_FIELD), SELF_SERVICE_ROLE_FIELD)


def resolved_role(field_value: str | None, setting: str) -> str | None:
	"""A configured role name, or None — saying out loud why there is none.

	Shared by every caller that turns one of this app's role settings into a
	real role, so that "the society never set it" and "the society set it to a
	role somebody has since deleted" are handled the same way and logged the
	same way. Silence is what a misconfiguration hides behind: a setting naming
	a deleted role would stop granting anybody anything, with nothing anywhere
	saying so.

	Returns None in both cases. Callers treat None as *do nothing*, never as
	*do it for everyone*.
	"""
	if not field_value:
		return None

	if not frappe.db.exists("Role", field_value):
		frappe.log_error(
			title="Self-service role missing",
			message=(
				f"National Society Settings {setting!r} names role {field_value!r}, which does not"
				" exist. Nothing will be granted, and any surface that depends on it stays"
				" uninstalled, until it is corrected."
			),
		)

		return None

	return field_value
