# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Membership fees into ERPNext's books: an invoice, settled, on the branch's cost centre.

When a fee is confirmed paid (`VMMS Membership.on_payment_confirmed`), this
raises a Sales Invoice for the member and settles it with a Payment Entry, both
submitted, both for the company in `VMMS Accounting Settings` and both carrying
the posting cost centre of the membership's branch (`geo_cost_center`). The
receivable nets to nothing; income and the receiving account each move by the
fee. Per-county figures come from the cost centre tree, not from a company per
county.

**Invoiced on payment, not on application.** An application that is never paid
leaves nothing to cancel.

**What is never posted.** A free membership; a membership proved from an
earlier system (its fee was paid before this system existed and is not income
now); a payment received before `posting_starts_on`; anything while posting is
switched off.

**One customer per member**, kept on `VMMS Member.customer`, so a member's
statement is one ERPNext customer.

**Never in the way of the payment.** Posting runs after the payment has been
recorded and the membership saved, in its own job after commit. A failure
(no account on the mode of payment, a closed period) marks the membership
`Failed` with the reason and is retried by the daily job or by staff; the
member is a member either way.

**Nothing paid is left out.** The daily job posts every paid fee that is due and
not in the books: one that failed, and one never tried because posting was off
when it was paid (from `posting_starts_on`) or because the job that should have
posted it never ran.

**Idempotent.** A membership that has a Payment Entry is posted. One that has an
invoice and no Payment Entry gets only the Payment Entry.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

SETTINGS = "VMMS Accounting Settings"
MEMBERSHIP = "VMMS Membership"
MEMBER = "VMMS Member"
MEMBERSHIP_LINK_FIELD = "vmms_membership"

POSTED = "Posted"
FAILED = "Failed"

# Who may post a fee by hand, and see the button that does it.
POSTERS = ("System Manager", "Accounts Manager")


def is_enabled() -> bool:
	if "erpnext" not in frappe.get_installed_apps():
		return False
	if not frappe.db.exists("DocType", SETTINGS):
		return False
	return bool(frappe.db.get_single_value(SETTINGS, "enabled"))


def queue(membership_name: str) -> None:
	"""Post after this request commits. Called from the payment confirmation."""
	if not is_enabled():
		return

	frappe.enqueue(
		"vmmsx.finance.services.membership_posting.post_quietly",
		queue="short",
		membership_name=membership_name,
		enqueue_after_commit=True,
		now=bool(frappe.flags.in_test),
		job_id=f"vmms-membership-posting::{membership_name}",
		deduplicate=True,
	)


def post_quietly(membership_name: str) -> None:
	"""The background entry point: never raises, a failure is recorded on the membership."""
	try:
		post(membership_name)
	except Exception:
		frappe.log_error(title=f"Membership posting failed: {membership_name}")


def why_not(membership) -> str | None:
	"""Why this membership is not due to be posted, or None when it is."""
	from vmmsx.member.services import membership as membership_service

	if not is_enabled():
		return "Posting membership payments to ERPNext is switched off."
	if membership_service.is_proof(membership):
		return "Proved from an earlier system."
	if not membership.paid_on:
		return "Not paid yet."
	if flt(_fee(membership)[0]) <= 0:
		return "Nothing to pay."
	starts = frappe.db.get_single_value(SETTINGS, "posting_starts_on")
	if starts and getdate(membership.paid_on) < getdate(starts):
		return "Paid before posting started."
	return None


def post(membership_name: str) -> dict:
	"""Raise and settle the invoice for one paid membership. Returns what was done."""
	membership = frappe.get_doc(MEMBERSHIP, membership_name)

	if membership.payment_entry and frappe.db.get_value("Payment Entry", membership.payment_entry, "docstatus") == 1:
		return {"posted": False, "reason": "Already posted.", **_names(membership)}

	reason = why_not(membership)
	if reason:
		return {"posted": False, "reason": reason, **_names(membership)}

	frappe.db.savepoint("vmms_membership_posting")
	try:
		settings = _settings()
		cost_center = _cost_center(membership.geo_node)
		customer = _customer(membership, settings)
		invoice = _invoice(membership, settings, customer, cost_center)
		entry = _payment_entry(membership, settings, invoice, cost_center)
	except Exception as error:
		frappe.db.rollback(save_point="vmms_membership_posting")
		_mark(membership, FAILED, note=plain(error))
		raise

	_mark(membership, POSTED, invoice=invoice.name, entry=entry.name)
	_link_transaction(membership, entry.name)

	return {"posted": True, "reason": None, "sales_invoice": invoice.name, "payment_entry": entry.name}


def outstanding(limit: int | None = 500) -> list[str]:
	"""Paid memberships whose fee is due in the books and is not there yet.

	Failed ones and never-tried ones alike. Narrowed in SQL to what `why_not`
	would let through, so the free memberships and the thousands proved from the
	old system are not read and set aside again every day.
	"""
	from vmmsx.member.services.membership import SOURCE_PROOF

	table = frappe.qb.DocType(MEMBERSHIP)
	query = (
		frappe.qb.from_(table)
		.select(table.name)
		.where(table.paid_on.isnotnull())
		.where(table.amount > 0)
		.where(table.accounting_status.isnull() | table.accounting_status.isin(["", FAILED]))
		.where(table.membership_source.isnull() | (table.membership_source != SOURCE_PROOF))
		.orderby(table.paid_on)
	)
	starts = frappe.db.get_single_value(SETTINGS, "posting_starts_on")
	if starts:
		query = query.where(table.paid_on >= getdate(starts))
	if limit:
		query = query.limit(limit)
	return [row[0] for row in query.run()]


def post_outstanding(limit: int | None = 500) -> dict:
	"""Daily, and from the setup script: post every fee that is due and missing.

	Returns how many were posted and which did not go, with why, so the script
	can report it. A failure is also recorded on its membership as always.
	"""
	result = {"posted": 0, "not_posted": {}}
	if not is_enabled():
		return result

	for name in outstanding(limit):
		try:
			done = post(name)
		except Exception as error:
			frappe.log_error(title=f"Membership posting failed: {name}")
			result["not_posted"][name] = plain(error)
		else:
			if done.get("posted"):
				result["posted"] += 1
			elif done.get("reason") != "Already posted.":
				result["not_posted"][name] = done.get("reason")
		frappe.db.commit()  # nosemgrep: one membership's books at a time
	return result


def can_post(membership) -> bool:
	"""May the person asking post this fee now? Drives the button on the review."""
	if membership.get("accounting_status") == POSTED:
		return False
	if not set(POSTERS) & set(frappe.get_roles()):
		return False
	return why_not(membership) is None


def attach_receipt(membership, receipt: str | None) -> bool:
	"""Put a gateway code that arrived after posting onto the fee's Payment Entry.

	The entry is posted moments after the payment is confirmed, and the status
	poll usually confirms an M-Pesa payment before Safaricom's callback brings the
	code, so the entry is often posted with the transaction's name as its
	reference. The reference is what an accountant matches against the M-Pesa
	statement, so it is brought up to date. It is not a ledger field (no GL row
	carries it), which is why changing it on a submitted entry is safe; a comment
	on the entry records the change.
	"""
	entry = membership.get("payment_entry")
	if not receipt or not entry:
		return False

	row = frappe.db.get_value("Payment Entry", entry, ["reference_no", "mode_of_payment", "docstatus"], as_dict=True)
	if not row or row.docstatus == 2 or row.reference_no == receipt:
		return False

	frappe.db.set_value(
		"Payment Entry",
		entry,
		{
			"reference_no": receipt,
			"remarks": _("Membership {0}, paid by {1}, reference {2}").format(
				membership.name, row.mode_of_payment, receipt
			),
		},
	)
	frappe.get_doc("Payment Entry", entry).add_comment(
		"Info",
		_("Reference changed from {0} to {1}: the gateway's code arrived after this entry was posted.").format(
			row.reference_no or "-", receipt
		),
	)
	return True


# --- the pieces ------------------------------------------------------------


def _settings() -> frappe._dict:
	settings = frappe.get_cached_doc(SETTINGS)
	for field, label in (
		("company", "Company"),
		("income_account", "Membership income account"),
		("fee_item", "Membership fee item"),
	):
		if not settings.get(field):
			frappe.throw(_("Set the {0} in VMMS Accounting Settings.").format(_(label)))
	return settings


def _fee(membership) -> tuple[float, str | None]:
	"""What was owed: the fee recorded on the membership, else its type's."""
	from vmmsx.member.services import membership as membership_service, payment

	charge = payment.recorded_fee(membership, membership_service.type_of(membership))
	return flt(charge["amount"]), charge["currency"]


def _paid(membership) -> tuple[float, str | None, str | None, str | None]:
	"""What was received, by which gateway, from which phone, under which receipt."""
	from vmmsx.member.services import membership as membership_service, payment

	picture = payment.settlement(membership, membership_service.type_of(membership))
	gateway = None
	if membership.payment_transaction and payment.is_available():
		gateway = frappe.db.get_value("OneRC Payment Transaction", membership.payment_transaction, "gateway")
	amount = flt(picture.get("amount_paid")) or _fee(membership)[0]
	receipt = picture.get("gateway_receipt") or membership.payment_receipt or membership.payment_transaction
	return amount, gateway or (membership.get("payment_method") or None), picture.get("paid_from"), receipt


def _cost_center(geo_node: str | None) -> str:
	from vmmsx.finance.services import geo_cost_center
	from vmmsx.setup.geo_cost_center_fields import POSTING_FIELD

	if not geo_node:
		frappe.throw(_("The membership has no branch, so there is no cost centre to post to."))

	cost_center = frappe.db.get_value("Geo Node", geo_node, POSTING_FIELD)
	if not cost_center:
		geo_cost_center.sync_node(frappe.get_doc("Geo Node", geo_node))
		cost_center = frappe.db.get_value("Geo Node", geo_node, POSTING_FIELD)
	if not cost_center:
		frappe.throw(_("The branch {0} has no cost centre in ERPNext.").format(geo_node))
	return cost_center


def _customer(membership, settings) -> str:
	"""The member's own ERPNext customer, made the first time they pay."""
	member = frappe.get_doc(MEMBER, membership.member)
	if member.customer and frappe.db.exists("Customer", member.customer):
		return member.customer

	profile = frappe.db.get_value(
		"Red Profile", member.red_profile, ["full_name", "first_name", "last_name", "email", "phone"], as_dict=True
	) or frappe._dict()
	name = (profile.full_name or " ".join(filter(None, [profile.first_name, profile.last_name])) or member.name).strip()

	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": name,
			"customer_type": "Individual",
			"customer_group": settings.customer_group
			or frappe.db.get_single_value("Selling Settings", "customer_group")
			or _first("Customer Group"),
			"territory": settings.territory
			or frappe.db.get_single_value("Selling Settings", "territory")
			or _first("Territory"),
			"email_id": profile.email or None,
			"mobile_no": profile.phone or None,
		}
	)
	customer.flags.ignore_permissions = True
	customer.insert()

	member.db_set({"customer": customer.name, "customer_name": customer.customer_name}, update_modified=False)
	return customer.name


def _invoice(membership, settings, customer: str, cost_center: str):
	"""The invoice for this membership: the one already raised, else a new one."""
	if membership.sales_invoice:
		existing = frappe.get_doc("Sales Invoice", membership.sales_invoice)
		if existing.docstatus == 1:
			return existing

	amount, currency = _fee(membership)
	company_currency = frappe.get_cached_value("Company", settings.company, "default_currency")
	if currency and currency != company_currency:
		frappe.throw(
			_("The fee is in {0} and the company keeps its books in {1}.").format(currency, company_currency)
		)

	posting_date = getdate(membership.paid_on)
	type_name = frappe.db.get_value("VMMS Membership Type", membership.membership_type, "membership_type_name")
	branch = frappe.db.get_value("Geo Node", membership.geo_node, "geo_node_name") or membership.geo_node

	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": settings.company,
			"customer": customer,
			"posting_date": posting_date,
			"set_posting_time": 1,
			"due_date": posting_date,
			"currency": company_currency,
			"conversion_rate": 1,
			# The fee is the membership's, not a price list's; the list is only
			# named because ERPNext requires one on every selling document.
			"selling_price_list": _price_list(company_currency),
			"price_list_currency": company_currency,
			"plc_conversion_rate": 1,
			"ignore_pricing_rule": 1,
			"cost_center": cost_center,
			MEMBERSHIP_LINK_FIELD: membership.name,
			"remarks": _("Membership {0}").format(membership.name),
			"items": [
				{
					"item_code": settings.fee_item,
					"description": _("{0} membership, {1}").format(type_name or membership.membership_type, branch),
					"qty": 1,
					"rate": amount,
					"income_account": settings.income_account,
					"cost_center": cost_center,
				}
			],
		}
	)
	invoice.flags.ignore_permissions = True
	invoice.insert()
	invoice.submit()
	membership.db_set("sales_invoice", invoice.name, update_modified=False)
	return invoice


def _payment_entry(membership, settings, invoice, cost_center: str):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	amount, gateway, _phone, receipt = _paid(membership)
	mode = _mode_of_payment(gateway)
	account = _account_of(mode, settings.company)

	entry = get_payment_entry("Sales Invoice", invoice.name, party_amount=amount, bank_account=account, bank_amount=amount)
	entry.mode_of_payment = mode
	entry.posting_date = getdate(membership.paid_on)
	entry.reference_no = receipt or membership.name
	entry.reference_date = getdate(membership.paid_on)
	entry.cost_center = cost_center
	entry.set(MEMBERSHIP_LINK_FIELD, membership.name)
	entry.remarks = _("Membership {0}, paid by {1}, reference {2}").format(membership.name, mode, entry.reference_no)
	entry.flags.ignore_permissions = True
	entry.insert()
	entry.submit()
	return entry


def _mode_of_payment(gateway: str | None) -> str:
	"""The ERPNext mode of payment the society mapped this gateway to."""
	from vmmsx.member.services import methods

	rows = frappe.get_single(methods.SETTINGS_DOCTYPE).get(methods.METHODS_FIELD) or []
	for row in rows:
		if gateway and row.gateway == gateway and row.get("mode_of_payment"):
			return row.mode_of_payment

	frappe.throw(
		_("Choose the ERPNext mode of payment for the payment method {0} in National Society Settings.").format(
			gateway or _("(none recorded)")
		)
	)


def _account_of(mode: str, company: str) -> str:
	account = frappe.db.get_value(
		"Mode of Payment Account", {"parent": mode, "company": company}, "default_account"
	)
	if not account:
		frappe.throw(_("Set the default account for {0} in the mode of payment {1}.").format(company, mode))
	return account


def _mark(membership, status: str, invoice: str | None = None, entry: str | None = None, note: str = "") -> None:
	values = {"accounting_status": status, "accounting_note": note}
	if invoice:
		values["sales_invoice"] = invoice
	if entry:
		values["payment_entry"] = entry
	membership.db_set(values, update_modified=False)


def _link_transaction(membership, entry: str) -> None:
	from vmmsx.member.services import payment

	if membership.payment_transaction and payment.is_available():
		meta = frappe.get_meta("OneRC Payment Transaction")
		if meta.has_field("erpnext_payment_entry"):
			frappe.db.set_value(
				"OneRC Payment Transaction", membership.payment_transaction, "erpnext_payment_entry", entry,
				update_modified=False,
			)


def _names(membership) -> dict:
	return {"sales_invoice": membership.get("sales_invoice"), "payment_entry": membership.get("payment_entry")}


def _price_list(currency: str) -> str | None:
	default = frappe.db.get_single_value("Selling Settings", "selling_price_list")
	if default:
		return default
	return frappe.db.get_value("Price List", {"selling": 1, "enabled": 1, "currency": currency}, "name") or frappe.db.get_value(
		"Price List", {"selling": 1, "enabled": 1}, "name"
	)


def _first(doctype: str) -> str | None:
	return frappe.db.get_value(doctype, {"is_group": 0}, "name", order_by="lft asc")


def plain(error: Exception) -> str:
	from frappe.utils import strip_html

	return strip_html(str(error))[:500] or error.__class__.__name__
