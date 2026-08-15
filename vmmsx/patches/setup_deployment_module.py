# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install what the Deployment module needs before a society can configure it.

Two Custom Fields on core's National Society Settings, both owned by vmmsx and
installed here. Core's doctype is not touched: a product pushing its own fields
into the shared foundation's schema is how the foundation stops being shared.

1. **The ACC-03 anchor-level field** for deployments and deployment requests.
   Left empty, which means "anchor anywhere" until a society narrows it.
2. **The branch-transfer approval mode.** Shipped **empty**, which reads as the
   direct mode: a site migrating into this module must not discover that every
   branch transfer now throws for want of an approval workflow it has never been
   asked to create. It is nevertheless the setting most societies will want to
   change, and the field's own description says so.

What is deliberately **not** here: any terms of reference. Those name real work
a society does, and this app has no business inventing one. A society writes its
own, which is the whole reason it is a doctype.

Every step checks before it writes, so re-running the patch changes nothing and
overwrites nothing an administrator has since edited.
"""

import frappe

from vmmsx.deployment.services.society import ANCHOR_LEVEL_FIELD, TRANSFER_APPROVAL_MODE_FIELD

SETTINGS_DOCTYPE = "National Society Settings"

# The last field the Volunteer stage installed. Ours are inserted after it, so
# the deployment settings sit together and below volunteering's rather than
# being scattered through the form in the order the patches happened to run.
VOLUNTEER_SCOPE_ROLE_FIELD = "vmms_volunteer_scope_role"


def execute():
	install_anchor_level_field()
	install_transfer_approval_mode_field()


def install_anchor_level_field() -> None:
	"""ACC-03 — where a society says its deployments may be anchored."""
	_custom_field(
		{
			"fieldname": ANCHOR_LEVEL_FIELD,
			"label": "Deployment Anchor Level",
			"fieldtype": "Link",
			"options": "Geo Level",
			"insert_after": VOLUNTEER_SCOPE_ROLE_FIELD,
			"description": (
				"ACC-03. The geo level a VMMS Deployment and a VMMS Deployment Request must be"
				" anchored at. Left empty, either may be anchored at any level; this narrows it, it"
				" does not enable it. One setting governs both, because they are two views of the"
				" same piece of work and anchoring them at different levels would leave a request"
				" unable to become the deployment it asked for. Owned by vmmsx."
			),
		}
	)


def install_transfer_approval_mode_field() -> None:
	"""Whether moving a volunteer between branches is somebody's decision."""
	_custom_field(
		{
			"fieldname": TRANSFER_APPROVAL_MODE_FIELD,
			"label": "Branch Transfer Approval",
			"fieldtype": "Select",
			"options": "\ndirect\nrouted",
			"insert_after": ANCHOR_LEVEL_FIELD,
			"description": (
				"Whether a VMMS Branch Transfer needs authorising. direct: the transfer takes effect"
				" on its effective date with no approver, which is what an empty value means and"
				" what this ships as, so that migrating into this module changes nothing. routed:"
				" the VMMS approval engine routes it to a resolved person, and the volunteer does"
				" not move until they approve. Most societies will want routed, because moving a"
				" volunteer between branches changes who can see them and who approves for them."
				" Choosing it requires one VMMS Approval Workflow governing VMMS Branch Transfer;"
				" by default that workflow routes from the branch the volunteer is leaving, and a"
				" society that would rather the receiving branch decide points the workflow's"
				" geo_node_field at to_geo_node instead. Owned by vmmsx."
			),
		}
	)


def _custom_field(definition: dict) -> None:
	"""Install one Custom Field on core's settings, once."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": definition["fieldname"]}):
		return

	create_custom_field(SETTINGS_DOCTYPE, definition, ignore_validate=True)
