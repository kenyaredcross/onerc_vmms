# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""MEM-01 — the payment seam. All money leaves through onerc_payments.

This module is the only place in the Member module that knows a payment exists,
and even here it knows nothing about a gateway. It calls
`onerc_payments.api.v1.payment.initiate_payment()` and then waits to be called
back. There is no M-Pesa in this file, no STK push, no shortcode, no callback
URL, and no branch on which driver is active — swapping M-Pesa for a bank
transfer is a setting in the payments app and changes nothing here.

**The import is deliberately lazy.** vmmsx declares `required_apps =
["onerc_core"]` and not payments: a society running membership with no fees
should not be forced to install a payment gateway. So the import happens inside
the call that needs it, and a zero-fee type never reaches it.

**Confirmation is the universal contract.** `record_confirmation()` is what the
membership's `on_payment_confirmed` hook calls, and it is deliberately ignorant
of which driver confirmed: the Manual driver, an admin pressing confirm on a
bank transfer, is a first-class path and the one the tests run on. Receipt
enrichment is separate and optional — see `record_receipt()`.
"""

import frappe
from frappe import _
from frappe.utils import flt, now_datetime

from vmmsx.member.services import identity, society

SOURCE_APP = "vmmsx"
DIRECTION_INBOUND = "Inbound"

# The app that owns money. vmmsx does not declare it in `required_apps` — a
# society running fee-free membership should not be made to install a gateway —
# so its absence is a real, supportable state that has to be handled rather than
# crashed on.
PAYMENTS_APP = "onerc_payments"


def is_available() -> bool:
	"""Is the payments app installed on this site?

	Asked of `frappe.get_installed_apps()`, deliberately, rather than by trying
	the import and catching `ImportError`. Two reasons: an app can be present on
	disk in the bench and not installed on *this* site, which is the case that
	actually bites; and a question answered by an exception cannot be asked at
	configuration time, where the useful error belongs.
	"""
	return PAYMENTS_APP in frappe.get_installed_apps()


def assert_available(what: str) -> None:
	"""Throw a clear error if money is needed and the payments app is not here.

	`what` names the thing that needs it, so the message says which membership
	type or which application ran into this rather than just naming the app.
	"""
	if is_available():
		return

	frappe.throw(
		_(
			"{0} needs a payment to be collected, but the {1} app is not installed on this site."
			" Install it, or set the membership type's fee to zero."
		).format(frappe.bold(what), frappe.bold(PAYMENTS_APP)),
		frappe.ValidationError,
		title=_("Payments App Not Installed"),
	)


def fee(membership_type) -> dict:
	"""What this type costs, and in what currency.

	The currency falls back to the society's configured one. Neither the amount
	nor the currency is ever assumed in code — a society with no fee and a
	society charging in a currency this developer has never heard of are the
	same code path.
	"""
	return {
		"amount": flt(membership_type.fee_amount),
		"currency": membership_type.fee_currency or society.default_currency(),
	}


def is_payable(membership_type) -> bool:
	"""Does this type charge anything at all?"""
	return fee(membership_type)["amount"] > 0


def is_settled(membership, membership_type) -> bool:
	"""Has this membership's money requirement been met?

	A type with no fee is settled the moment it exists — "nothing to pay" and
	"paid" have to mean the same thing to activation, or a free membership would
	wait forever for a payment nobody was ever going to make.
	"""
	if not is_payable(membership_type):
		return True

	return bool(membership.paid_on)


def request(membership, membership_type) -> dict | None:
	"""Ask onerc_payments to collect this membership's fee. Idempotent.

	Returns the payments app's response, or None when there is nothing to
	collect or a transaction is already outstanding. Re-requesting would leave a
	member with two live payment requests for one membership, which is a
	support call, not a feature.

	**Which way the fee is collected is the applicant's answer, checked here.**
	`membership.payment_method` is what they chose on the form; it is validated
	against what the society actually offers rather than trusted, because it
	arrived from a browser and a name that is not on the society's list would
	otherwise reach the payments app as a gateway request. A membership with no
	method on it — one entered at a desk, or created before anybody was asked —
	falls back to the society's first offered method, and then to the payments
	app's own active gateway, which is what this did before anybody was asked at
	all.

	**This file still knows nothing about a gateway.** It passes a name through
	and does not read it: there is no M-Pesa here, no STK push and no branch on
	which driver is active, and swapping one for another remains a setting in the
	payments app. MEM-01 is unchanged.
	"""
	if not is_payable(membership_type):
		return None

	if membership.payment_transaction:
		return None

	# Checked before the import, so an uninstalled payments app produces a clean
	# refusal naming what is missing rather than a ModuleNotFoundError surfacing
	# as a 500 at the applicant's first click. The membership type's own
	# validation should have caught this long before anybody applied; this is
	# the second line, for a type that was configured while the app was still
	# installed and is being used after it was removed.
	assert_available(f"{membership.doctype} {membership.name}")

	# Imported here, not at module scope: a fee-free society need not install
	# the payments app at all, and this is the only line that would break if it
	# were absent.
	from onerc_payments.api.v1.payment import initiate_payment

	member = frappe.get_doc("VMMS Member", membership.member)
	person = identity.read(member, ("full_name", "email", "phone"))
	charge = fee(membership_type)

	chosen = _chosen_method(membership)

	response = initiate_payment(
		amount=charge["amount"],
		currency=charge["currency"],
		direction=DIRECTION_INBOUND,
		source_app=SOURCE_APP,
		source_doctype=membership.doctype,
		source_document=membership.name,
		payer_name=identity.display_name(member),
		payer_phone=person.get("phone"),
		payer_email=person.get("email"),
		metadata=frappe.as_json({"membership_type": membership_type.name, "geo_node": membership.geo_node}),
		# None means "whatever the payments app has active", which is exactly
		# what this call did before a method could be chosen.
		gateway=chosen,
	)

	membership.payment_transaction = response.get("transaction_id")

	if chosen:
		# Recorded so a coordinator can see what the applicant asked for even
		# after the transaction has been reconciled by hand onto another
		# gateway. What actually collected the money is the payments app's fact
		# and is read live — see `settlement`.
		membership.payment_method = chosen

	return response


def _chosen_method(membership) -> str | None:
	"""Which of the society's offered methods this fee should go through.

	Three answers in order, and the middle one is the reason this is a function:

	1. **What the applicant chose**, if the society still offers it. Checked
	   rather than trusted — the value came from a form.
	2. **The society's own first choice**, for a membership created without
	   anybody being asked: a desk entry, a renewal, or a record made before this
	   question existed. `methods.default()` reads the top of the society's list,
	   which is their statement of what they would rather people used.
	3. **None**, which the payments app reads as its own active gateway. That is
	   what every fee did before this, so a site with no methods configured is
	   not a site that stops taking money.
	"""
	from vmmsx.member.services import methods

	asked = (membership.get("payment_method") or "").strip()

	if asked and methods.is_offered(asked):
		return asked

	return methods.default()


def record_confirmation(membership, amount=None, receipt=None, transaction_id=None) -> bool:
	"""Record that the fee was paid. Returns whether anything changed.

	Called from the membership's `on_payment_confirmed` hook, which the payments
	app invokes on whichever document the transaction named. Idempotent: a
	gateway that retries, or an admin who presses confirm twice, records one
	payment.

	The amount is deliberately *recorded, not verified*: reconciling what was
	paid against what was owed is the payments app's job, and a second opinion
	here would be a second answer to a question that already has one.
	"""
	if membership.paid_on:
		# Already settled. Take a receipt if this call carries one and the
		# earlier one did not — that is the late-receipt case, and it is the
		# only thing a repeat confirmation may still contribute.
		return _absorb_receipt(membership, receipt)

	if transaction_id and membership.payment_transaction != transaction_id:
		membership.payment_transaction = transaction_id

	_absorb_receipt(membership, receipt)

	membership.paid_on = now_datetime()

	if amount is not None:
		membership.add_comment(
			"Comment",
			_("Payment of {0} confirmed via {1}.").format(flt(amount), transaction_id or _("(no reference)")),
		)

	# Always a change: this call is what set paid_on, and paid_on is what
	# activation waits on.
	return True


def record_receipt(membership, receipt=None, transaction_id=None) -> bool:
	"""Attach a late-arriving gateway receipt. Returns whether anything changed.

	Pure enrichment, and optional by design. Some gateways deliver a receipt
	number only on a callback that lands after the payment was already resolved;
	others — the Manual driver among them — may never deliver one separately at
	all. Nothing about activation, validity or the certificate's existence
	depends on this ever being called.
	"""
	changed = _absorb_receipt(membership, receipt)

	if transaction_id and not membership.payment_transaction:
		membership.payment_transaction = transaction_id
		changed = True

	return changed


# --- reading the money picture back ---------------------------------------


# What this module is willing to surface from a transaction, named explicitly so
# that a new field on the payments app's doctype never starts leaking through a
# vmmsx DTO. The same discipline `identity._READABLE` applies to Red Profile,
# for the same reason: the other app owns that record and may add anything to it.
_TRANSACTION_FIELDS = (
	"gateway",
	"status",
	"amount",
	"currency",
	"gateway_receipt",
	"gateway_reference",
	"transaction_date",
)


def settlement(membership, membership_type=None) -> dict:
	"""How this membership's fee was satisfied — read live, copied nowhere.

	The coordinator's answer to "has this person paid, and how do I know". It is
	assembled at the moment of asking from three places, none of which is a
	duplicate of another:

	    the membership   which channel was used, and the transaction reference
	                     the gateway handed back when the fee was requested
	    the type         what was owed, and in what currency
	    the transaction  what the gateway actually did — **read live**, from
	                     `onerc_payments`, because that app owns the payment

	**The gateway is never stored here and must not be.** Which driver collected
	a fee is the payments app's fact, and it can change after the event: a
	transaction reconciled by hand, a receipt that arrived late, a gateway
	renamed. A copy on the membership would be a second answer that goes stale
	silently, and MEM-01 is explicit that money lives on the other side of this
	seam. So `gateway` and `gateway_status` below come out of the transaction on
	every call and are forgotten again.

	**The payments app being absent is ordinary, not an error.** vmmsx does not
	declare it in `required_apps` — a society running fee-free membership should
	not be made to install a gateway — so `live` reports whether the live half
	could be read at all, and every field it would have filled stays None. A
	fee-free membership on a site with no payments app still returns a complete,
	honest settlement picture saying nothing was owed.

	**Proof-of-Membership answers the same question from a different place.** A
	pre-rollout member's fee was paid before this system existed, so there is no
	transaction to read and never will be; `source` says so, and the evidence is
	the attachment an approver verified. Who that approver was is an approval
	fact rather than a payment one, and it is added by the dossier from the
	decision trail rather than guessed at here.
	"""
	from vmmsx.member.services import membership as membership_service

	membership_type = membership_type or membership_service.type_of(membership)
	charge = fee(membership_type)
	proof = membership_service.is_proof(membership)

	picture = {
		"source": membership_service.source(membership),
		"is_proof": proof,
		"settled": proof or is_settled(membership, membership_type),
		"payable": is_payable(membership_type),
		"fee_amount": charge["amount"],
		"fee_currency": charge["currency"],
		# Stored on the membership because the membership asked for them: the
		# reference the gateway returned when the fee was requested, and the
		# receipt it reported afterwards. Neither is a copy of anything — see
		# `record_confirmation` and `record_receipt`.
		"transaction": membership.payment_transaction,
		"receipt": membership.payment_receipt,
		"paid_on": membership.paid_on,
		"proof_attachment": membership.get("proof_attachment"),
		# Filled below, from the payments app, or left None.
		"live": False,
		"gateway": None,
		"gateway_status": None,
		"gateway_receipt": None,
		"gateway_reference": None,
		"amount_paid": None,
		"currency_paid": None,
		"transaction_date": None,
	}

	if proof or not membership.payment_transaction or not is_available():
		return picture

	return {**picture, **_transaction_picture(membership.payment_transaction)}


def _transaction_picture(transaction_id: str) -> dict:
	"""The live half: what the payments app says about this transaction.

	Read with `frappe.db.get_value` and so without a permission check on the
	payments app's doctype, which is deliberate and is the narrowest form the
	read can take. The justification is that entitlement was already
	established: every caller reaches here having been admitted to *this
	membership* by `api/member.py::_readable`, which is Frappe's roles plus
	core's geo scoping plus the holder's own bypass. What comes back is the
	payment for that one membership and nothing else — the transaction is looked
	up by the reference the membership itself stores, so there is no argument a
	caller could supply to reach somebody else's. Requiring a second grant on
	`OneRC Payment Transaction` would mean handing every membership clerk read
	access to the society's entire payment ledger in order to show one receipt.

	A missing row is ordinary rather than an error: a transaction can be purged,
	and a membership whose payment record has gone still has to render.
	"""
	row = frappe.db.get_value("OneRC Payment Transaction", transaction_id, _TRANSACTION_FIELDS, as_dict=True)

	if not row:
		return {}

	return {
		"live": True,
		# The society's own word for the gateway where it set one, falling back
		# to the record's name. Read live for the same reason as everything else
		# here: renaming a gateway renames it on every screen at once.
		"gateway": _gateway_label(row.gateway),
		"gateway_status": row.status,
		"gateway_receipt": row.gateway_receipt,
		"gateway_reference": row.gateway_reference,
		"amount_paid": row.amount,
		"currency_paid": row.currency,
		"transaction_date": row.transaction_date,
	}


def _gateway_label(gateway: str | None) -> str | None:
	"""What to call the gateway that collected this, or None.

	`label` is the payments app's display field and `gateway_name` is its
	docname; a gateway with no label shows its name rather than an empty cell.
	"""
	if not gateway:
		return None

	return frappe.db.get_value("OneRC Payment Gateway", gateway, "label") or gateway


def _absorb_receipt(membership, receipt: str | None) -> bool:
	"""Take a receipt the record does not already have. Never overwrite a good one."""
	if not receipt or membership.payment_receipt == receipt:
		return False

	if membership.payment_receipt:
		# A different receipt for a payment we already have one for. Recorded as
		# a comment rather than silently replacing evidence.
		membership.add_comment("Comment", _("A second receipt was reported: {0}.").format(receipt))

		return False

	membership.payment_receipt = receipt

	return True
