# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Install what the Stipend module needs before a society can configure it.

One Custom Field on core's National Society Settings, owned by vmmsx and
installed here. Core's doctype is not touched: a product pushing its own fields
into the shared foundation's schema is how the foundation stops being shared.

**The ACC-03 anchor-level field** for stipend paperwork. Left empty, which means
"anchor anywhere" until a society narrows it. One setting governs the progress
report and the payment form together, because they are two halves of the same
period of work and anchoring them at different levels would leave a form unable
to pair with the report it pays for.

What is deliberately **not** here: anything about who approves a stipend. The
chain is supervisor to head of department, departmental resolution does not
exist, and installing a settings field for a role nothing can resolve would be
this app inviting a society to configure a route that goes nowhere. See
`vmmsx/stipend/services/approval.py`.

Nor is a currency: the society already has one, on core's own settings, and the
payment form reads it. A second currency field would be a second answer.

Every step checks before it writes, so re-running the patch changes nothing and
overwrites nothing an administrator has since edited.
"""

import frappe

from vmmsx.stipend.services.society import ANCHOR_LEVEL_FIELD

SETTINGS_DOCTYPE = "National Society Settings"

# The last field the Deployment stage installed. Ours is inserted after it, so
# the stipend settings sit below deployment's rather than being scattered through
# the form in the order the patches happened to run.
TRANSFER_SCOPE_ROLE_FIELD = "vmms_branch_transfer_scope_role"


def execute():
	install_anchor_level_field()


def install_anchor_level_field() -> None:
	"""ACC-03 — where a society says its stipend paperwork may be filed."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if frappe.db.exists("Custom Field", {"dt": SETTINGS_DOCTYPE, "fieldname": ANCHOR_LEVEL_FIELD}):
		return

	create_custom_field(
		SETTINGS_DOCTYPE,
		{
			"fieldname": ANCHOR_LEVEL_FIELD,
			"label": "Stipend Anchor Level",
			"fieldtype": "Link",
			"options": "Geo Level",
			"insert_after": TRANSFER_SCOPE_ROLE_FIELD,
			"description": (
				"ACC-03. The geo level a VMMS Stipend Progress Report and a VMMS Stipend Payment"
				" Form must be anchored at. Left empty, either may be anchored at any level; this"
				" narrows it, it does not enable it. One setting governs both, because a payment"
				" form pays for the report it is paired with and the two are one place. Owned by"
				" vmmsx."
			),
		},
		ignore_validate=True,
	)
