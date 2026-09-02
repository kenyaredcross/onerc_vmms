# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Which ways of paying a society will take a membership fee.

One Custom Field on core's `National Society Settings` — a table of
`VMMS Payment Method` rows — plus one on `VMMS Membership`, recording which way
a particular applicant chose. Neither is an edit to another app's source: the
same shape as `install_identity_document_rules.py`, and for the same reason.

**Why the choice is a society's and not a developer's.** Before this, a
membership fee went through whatever single gateway was set as
`active_gateway` in the payments app, and an applicant was never asked. That is
wrong twice over. A society that takes both M-Pesa and bank transfer could offer
only one of them, and a person who has no mobile money account had no way to say
so — the form asked for money and then chose, on their behalf, a way of paying
they may not be able to use.

**The list is not written here.** It comes from `onerc_payments` — every gateway
it reports as active and able to take money in — and
`member/services/methods.py::sync` writes one row per gateway on migrate. The
society's decision is the tick beside each row. Nothing in this app names a
gateway except to seed the manual one first; see that module.

**The manual method is offered by default and can be turned off.** A society
that has bought no gateway integration still takes money at a branch counter,
and the manual driver is how that is recorded. Every seeded row arrives ticked,
which is the "empty narrows nothing" direction every other society setting in
this product takes — a society that has never opened the screen can still take a
fee, and turning one off is the deliberate act.

`payment_method` on the membership is a `Data` field rather than a Link for the
reason `VMMS Payment Method.gateway` gives: it names a record in an app vmmsx
does not require, and a Link to a doctype that is not on the site will not sync.
"""

import frappe

SETTINGS_DOCTYPE = "National Society Settings"
MEMBERSHIP_DOCTYPE = "VMMS Membership"

METHODS_FIELD = "vmms_payment_methods"
METHOD_FIELD = "payment_method"

SOCIETY_FIELDS = (
	{
		"fieldname": "vmms_membership_payments_section",
		"label": "Membership Payments",
		"fieldtype": "Section Break",
		"insert_after": "vmms_minor_age",
		"description": (
			"How this society takes a membership fee. The list below is every gateway the"
			" payments app has active; ticking one offers it to somebody joining. Owned by vmmsx."
		),
	},
	{
		"fieldname": METHODS_FIELD,
		"label": "Ways to Pay",
		"fieldtype": "Table",
		"options": "VMMS Payment Method",
		"insert_after": "vmms_membership_payments_section",
		"description": (
			"Rows are added automatically from the payments app. Untick one to stop offering it."
			" The order is the order an applicant sees, and the first is what the form selects"
			" for somebody who has not chosen. Owned by vmmsx."
		),
	},
)

MEMBERSHIP_FIELDS = (
	{
		"fieldname": METHOD_FIELD,
		"label": "Payment Method",
		"fieldtype": "Data",
		"insert_after": "payment_transaction",
		"read_only": 1,
		"description": (
			"Which of the society's ways of paying this applicant chose. Recorded when the fee is"
			" requested; the gateway that actually collected it is the payments app's fact and is"
			" read live from the transaction."
		),
	},
)


def execute():
	_install(SETTINGS_DOCTYPE, SOCIETY_FIELDS)
	_install(MEMBERSHIP_DOCTYPE, MEMBERSHIP_FIELDS)

	# Seed the rows now rather than waiting for the next migrate, so a society
	# that opens the settings form after this deploy finds the list already
	# there. Additive and non-destructive — see `methods.sync` — and silent on a
	# site with no payments app, which is an ordinary state.
	from vmmsx.member.services import methods

	methods.sync()


def _install(doctype: str, fields: tuple) -> None:
	"""Create what is absent and touch nothing that is there.

	Guarded per field rather than per patch, so a run interrupted half way
	finishes on the next migrate rather than skipping the rest for ever.
	"""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	for field in fields:
		if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]}):
			continue

		create_custom_field(doctype, dict(field), ignore_validate=True)
