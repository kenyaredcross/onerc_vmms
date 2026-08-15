# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install the three settings the self-service journey reads.

All three are **Custom Fields vmmsx owns** on core's National Society Settings,
installed here rather than added to core's source: a product pushing its own
fields into the shared foundation's schema is how the foundation stops being
shared. This is the fourth patch to do it and it follows the same shape as the
scope-role and print-role patches before it.

    vmms_self_service_role        what a self-registered account holds until
                                  somebody approves it
    vmms_volunteer_member_role    granted to a volunteer's login when their
                                  application is accepted
    vmms_membership_member_role   granted to a member's login when a membership
                                  activates

**All three ship empty, and empty means nothing happens.** No role is granted,
and the landing surface is not installed. That is the same fail-closed direction
the scope roles take and it matters more here, not less: a Workspace carrying no
roles is visible to every desk user on the site, so guessing a default would put
a public registration page in front of the whole national society. A society
chooses the three roles, and `vmmsx.registration.services.workspaces.install()`
builds the surfaces that name them.

A separate patch from the module setups because a Frappe patch runs once per
site by name, and all of those have already run everywhere.
"""

import frappe

from vmmsx.member.services.society import MEMBER_ROLE_FIELD as MEMBERSHIP_MEMBER_ROLE_FIELD
from vmmsx.registration.services.society import SELF_SERVICE_ROLE_FIELD
from vmmsx.volunteer.services.society import MEMBER_ROLE_FIELD as VOLUNTEER_MEMBER_ROLE_FIELD
from vmmsx.volunteer.services.society import SCOPE_ROLE_FIELD as VOLUNTEER_SCOPE_ROLE_FIELD

SETTINGS_DOCTYPE = "National Society Settings"

FIELDS = (
	{
		"fieldname": VOLUNTEER_MEMBER_ROLE_FIELD,
		"label": "Volunteer Self-Service Role",
		"fieldtype": "Link",
		"options": "Role",
		"insert_after": VOLUNTEER_SCOPE_ROLE_FIELD,
		"description": (
			"The role granted to a volunteer's own login when their application is accepted. It is"
			" what lets somebody see their own volunteer record, their time logs and their"
			" certifications, and it is not the role that sees the register. Left empty, nothing is"
			" granted and an approved volunteer simply has no self-service view. A volunteer"
			" registered from a paper form has no login, and nothing is granted for them either."
			" Owned by vmmsx."
		),
	},
	{
		"fieldname": MEMBERSHIP_MEMBER_ROLE_FIELD,
		"label": "Member Self-Service Role",
		"fieldtype": "Link",
		"options": "Role",
		"insert_after": VOLUNTEER_MEMBER_ROLE_FIELD,
		"description": (
			"The role granted to a member's own login when one of their memberships activates. It"
			" is what lets somebody see their own memberships and print their own certificate, and"
			" it is not the role that sees every membership. Left empty, nothing is granted. A"
			" member registered from a paper form has no login, and nothing is granted for them"
			" either. Owned by vmmsx."
		),
	},
	{
		"fieldname": SELF_SERVICE_ROLE_FIELD,
		"label": "Self-Registration Role",
		"fieldtype": "Link",
		"options": "Role",
		"insert_after": MEMBERSHIP_MEMBER_ROLE_FIELD,
		"description": (
			"The role a person holds between creating a website account and being approved as"
			" anything. It carries one surface: the landing workspace offering the two"
			" registration forms. Point Portal Settings' Default Role at the same role so that"
			" self-registered accounts receive it. A role with desk access makes the account a"
			" System User, which is what allows a workspace to be shown at all. Left empty, the"
			" landing workspace is not installed. Owned by vmmsx."
		),
	},
)


def execute():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	for definition in FIELDS:
		if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": definition["fieldname"]}):
			continue

		create_custom_field(SETTINGS_DOCTYPE, definition, ignore_validate=True)
