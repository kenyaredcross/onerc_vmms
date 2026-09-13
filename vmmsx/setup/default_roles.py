# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Wire VMMS's shipped roles without asking every society the same questions."""

import frappe

from vmmsx.member.services.society import MEMBER_ROLE_FIELD, PRINT_ROLE_FIELD
from vmmsx.registration.services.society import SELF_SERVICE_ROLE_FIELD
from vmmsx.setup.core_roles import (
	ROLE_APPLICANT,
	ROLE_MEMBER,
	ROLE_MEMBERSHIP_APPROVER,
	ROLE_VOLUNTEER,
	ROLE_VOLUNTEER_APPROVER,
)
from vmmsx.volunteer.services.society import MEMBER_ROLE_FIELD as VOLUNTEER_MEMBER_ROLE_FIELD
from vmmsx.volunteer.services.society import SCOPE_ROLE_FIELD as VOLUNTEER_SCOPE_ROLE_FIELD

SETTINGS_DOCTYPE = "National Society Settings"
MEMBERSHIP_SCOPE_ROLE_FIELD = "vmms_membership_scope_role"

DEFAULTS = {
	MEMBERSHIP_SCOPE_ROLE_FIELD: ROLE_MEMBERSHIP_APPROVER,
	VOLUNTEER_SCOPE_ROLE_FIELD: ROLE_VOLUNTEER_APPROVER,
	PRINT_ROLE_FIELD: ROLE_MEMBERSHIP_APPROVER,
	MEMBER_ROLE_FIELD: ROLE_MEMBER,
	VOLUNTEER_MEMBER_ROLE_FIELD: ROLE_VOLUNTEER,
	SELF_SERVICE_ROLE_FIELD: ROLE_APPLICANT,
}


def install() -> None:
	"""Fill blanks and hide standard wiring; explicit existing choices win."""
	meta = frappe.get_meta(SETTINGS_DOCTYPE)
	settings = frappe.get_single(SETTINGS_DOCTYPE)
	changed = False

	for fieldname, role in DEFAULTS.items():
		if not meta.has_field(fieldname) or settings.get(fieldname):
			continue
		settings.set(fieldname, role)
		changed = True

	if changed:
		settings.save(ignore_permissions=True)

	# These six values still exist as fields because the runtime access layer
	# resolves them in one consistent way. They are hidden configuration now,
	# though: all six point at roles vmmsx itself ships, so asking every society
	# to reproduce that wiring is setup ceremony rather than a policy choice.
	for fieldname in DEFAULTS:
		custom_field = frappe.db.get_value(
			"Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": fieldname}, "name"
		)
		if custom_field:
			frappe.db.set_value("Custom Field", custom_field, "hidden", 1)

	frappe.clear_cache(doctype=SETTINGS_DOCTYPE)
