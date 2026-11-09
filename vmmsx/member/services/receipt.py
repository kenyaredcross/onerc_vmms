# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A payment receipt for a membership fee: what the member prints, what staff check.

Assembled at the moment of asking from the membership, the payments app's
transaction (the M-Pesa code and the phone number it was paid from) and, where the fee was
posted, ERPNext's Sales Invoice and Payment Entry. Nothing here is stored.

**Only for money that came in through this system.** A membership proved from
an earlier system has no receipt here: its fee was paid before, somewhere else.
A free membership has nothing to receipt. An unpaid one is not receipted yet.

**The receipt number** is the Payment Entry's name once the fee is posted to
ERPNext, which is the number an accountant can look up. Before that (posting
switched off, or not yet run) it is the membership's own name with an `R-`
prefix, which is stable and unique.
"""

import frappe
from frappe import _
from frappe.utils import flt

from vmmsx.member.services import identity, membership as membership_service, methods, payment, society


def assert_receiptable(membership) -> None:
	if membership_service.is_proof(membership):
		frappe.throw(
			_("This membership was proved from an earlier system, so there is no payment receipt here."),
			frappe.DoesNotExistError,
		)
	if not membership.paid_on:
		frappe.throw(_("This membership fee has not been paid yet."), frappe.DoesNotExistError)
	if flt(payment.recorded_fee(membership, membership_service.type_of(membership))["amount"]) <= 0:
		frappe.throw(_("This membership was free, so there is nothing to receipt."), frappe.DoesNotExistError)


def build(membership) -> dict:
	"""Everything a receipt shows, for one paid membership."""
	assert_receiptable(membership)

	membership_type = membership_service.type_of(membership)
	picture = payment.settlement(membership, membership_type)
	member = frappe.get_doc("VMMS Member", membership.member)
	posted = membership.get("accounting_status") == "Posted" and membership.get("payment_entry")
	phone = picture.get("paid_from") or membership.get("payer_phone") or None
	valid_from, valid_to = membership_service.validity_window(membership)
	gateway = _gateway_of(membership)

	return {
		"receipt_number": membership.payment_entry if posted else f"R-{membership.name}",
		"society": society.society_name() or "",
		"logo": society.logo() or None,
		"paid_on": picture.get("transaction_date") or membership.paid_on,
		# Whose membership it is. Nobody pays into someone else's account here, so
		# the person is the member; the phone below is only the number the money
		# came from, which may be a second line or a parent's.
		"member": {
			"name": identity.display_name(member),
			"member_number": member.name,
		},
		"phone": phone,
		"membership": {
			"name": membership.name,
			"type": frappe.db.get_value("VMMS Membership Type", membership.membership_type, "membership_type_name")
			or membership.membership_type,
			"branch": frappe.db.get_value("Geo Node", membership.geo_node, "geo_node_name") or membership.geo_node,
			"valid_from": valid_from,
			"valid_to": valid_to,
		},
		"amount": flt(picture.get("amount_paid")) or flt(picture.get("fee_amount")),
		"currency": picture.get("currency_paid") or picture.get("fee_currency"),
		"method": methods.label_of(gateway) or picture.get("gateway"),
		# A phone-prompt method (M-Pesa) always has a confirmation code, so its
		# line is shown even while the code is still on its way.
		"by_phone": bool(methods.presentation_of(gateway)["by_phone"]),
		# The gateway's own confirmation code: the M-Pesa receipt number.
		"gateway_receipt": picture.get("gateway_receipt") or membership.payment_receipt or None,
		"transaction": membership.payment_transaction or None,
		"sales_invoice": membership.get("sales_invoice") if posted else None,
		"payment_entry": membership.get("payment_entry") if posted else None,
		"accounting_status": membership.get("accounting_status") or None,
	}


def _gateway_of(membership) -> str | None:
	if not membership.get("payment_transaction") or not frappe.db.table_exists("OneRC Payment Transaction"):
		return None
	return frappe.db.get_value("OneRC Payment Transaction", membership.payment_transaction, "gateway")

