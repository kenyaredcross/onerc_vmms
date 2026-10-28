"""Membership and event accounting and confirmed STK recovery, owned by VMMS."""

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, now_datetime

EXPRESS = "Mpesa Express Request"
CONFIRMATION_SERVICE = "VMMS M-Pesa Confirmation"


def _is_dry_run(value):
	# Form arguments may be strings. Ambiguous input must never enable posting.
	return value not in (False, 0, "0", "false")


def get_vmms_invoice(payment_request):
	if payment_request.reference_doctype != "Sales Invoice":
		return None
	invoice = frappe.get_doc("Sales Invoice", payment_request.reference_name)
	return invoice if invoice.get("membership") or invoice.get("event_booking") else None


def get_receiving_account(current_account, mode_of_payment, company, currency):
	fields = ["company", "account_currency", "disabled", "is_group"]
	account = current_account
	details = frappe.db.get_value("Account", account, fields, as_dict=True) if account else None
	if not details or details.company != company:
		account = frappe.db.get_value(
			"Mode of Payment Account", {"parent": mode_of_payment, "company": company}, "default_account"
		)
		details = frappe.db.get_value("Account", account, fields, as_dict=True) if account else None
	if (
		not details
		or details.company != company
		or details.account_currency != currency
		or details.disabled
		or details.is_group
	):
		frappe.throw(
			_("Configure a valid {0} receiving account for Company {1} in Mode of Payment {2}").format(
				currency, company, mode_of_payment
			)
		)
	return account


def get_existing_payment(payment_request, invoice):
	return frappe.db.get_value(
		"Payment Entry Reference",
		{
			"payment_request": payment_request.name,
			"reference_doctype": "Sales Invoice",
			"reference_name": invoice.name,
			"docstatus": 1,
			"parenttype": "Payment Entry",
		},
		"parent",
	) or frappe.db.get_value("Payment Entry", {"reference_no": payment_request.name, "docstatus": 1}, "name")


def validate_existing_payment(name, company):
	entries = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Payment Entry", "voucher_no": name, "is_cancelled": 0},
		fields=["company", "debit", "credit"],
	)
	debit = sum(flt(row.debit) for row in entries)
	credit = sum(flt(row.credit) for row in entries)
	if (
		len(entries) < 2
		or debit <= 0
		or abs(debit - credit) > 0.001
		or any(row.company != company for row in entries)
	):
		frappe.throw(
			_("The existing Payment Entry has incomplete or mismatched ledger entries; reconcile it first")
		)


def _find_vmms_request(checkout_request_id):
	if not isinstance(checkout_request_id, str) or not checkout_request_id or len(checkout_request_id) > 140:
		return None
	name = frappe.db.get_value(EXPRESS, {"checkout_request_id": checkout_request_id}, "name")
	if not name:
		return None
	express = frappe.get_doc(EXPRESS, name)
	if express.reference_doctype != "Payment Request":
		return None
	request = frappe.get_doc("Payment Request", express.reference_name)
	return express if get_vmms_invoice(request) else None


def _original_callback(**kwargs):
	from frappe_mpsa_payments.frappe_mpsa_payments.api.m_pesa_api import stk_push_callback as original

	return original(**kwargs)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def stk_push_callback(**kwargs):
	"""Override the existing callback URL for VM membership and event payments."""
	response = (kwargs.get("Body") or {}).get("stkCallback") or {}
	express = _find_vmms_request(response.get("CheckoutRequestID"))
	if not express or str(response.get("ResultCode")) != "0":
		return _original_callback(**kwargs)
	metadata = {
		item.get("Name"): item["Value"]
		for item in (response.get("CallbackMetadata") or {}).get("Item", [])
		if isinstance(item, dict) and "Value" in item
	}
	try:
		amount = Decimal(str(metadata.get("Amount")))
		valid_amount = amount.is_finite() and amount > 0 and amount == Decimal(str(express.amount))
	except InvalidOperation:
		valid_amount = False
	receipt = metadata.get("MpesaReceiptNumber")
	if not valid_amount or not isinstance(receipt, str) or not receipt or len(receipt) > 100:
		frappe.throw(_("M-Pesa confirmation does not match the initiated payment"))
	# This is the same system identity used by the provider callback. Posting
	# below additionally requires a successful server-to-server status query.
	frappe.set_user("Administrator")
	_store_confirmation(express, kwargs, metadata)
	_recover_confirmed_payment(express)


def _confirmation_log(express, output):
	filters = {
		"integration_request_service": CONFIRMATION_SERVICE,
		"reference_doctype": EXPRESS,
		"reference_docname": express.name,
	}
	name = frappe.db.get_value("Integration Request", filters, "name")
	if name:
		previous = frappe.db.get_value("Integration Request", name, "output")
		try:
			previous = json.loads(previous or "{}")
		except (TypeError, ValueError):
			previous = {}
		if isinstance(previous, dict):
			output = {**previous, **output}
		frappe.db.set_value("Integration Request", name, "output", frappe.as_json(output))
	else:
		name = (
			frappe.get_doc(
				{
					"doctype": "Integration Request",
					**filters,
					"status": "Queued",
					"output": frappe.as_json(output),
					"is_remote_request": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	return name


def _store_confirmation(express, payload, metadata):
	locked = frappe.get_doc(EXPRESS, express.name, for_update=True)
	receipt = metadata["MpesaReceiptNumber"]
	if locked.transaction_id and locked.transaction_id != receipt:
		frappe.throw(_("A different M-Pesa receipt is already recorded for this checkout"))
	fields = {
		"transaction_id": receipt,
		"result_code": "0",
		"result_desc": "Callback received; verifying accounting",
	}
	if locked.status != "Completed":
		fields["status"] = "In Progress"
	if metadata.get("TransactionDate"):
		fields["transaction_date"] = datetime.strptime(str(metadata["TransactionDate"]), "%Y%m%d%H%M%S")
	frappe.db.set_value(EXPRESS, express.name, fields)
	_confirmation_log(express, {"callback_result": payload["Body"]["stkCallback"]})
	# Confirmation evidence must survive a subsequent failed accounting transaction.
	frappe.db.commit()


def _query_provider_status(express):
	from frappe_mpsa_payments.frappe_mpsa_payments.api.m_pesa_api import generate_request_password
	from frappe_mpsa_payments.frappe_mpsa_payments.api.process_request import process_request

	settings = frappe.get_doc("Mpesa Settings", express.settings)
	timestamp = now_datetime().strftime("%Y%m%d%H%M%S")
	responses = []

	def capture(response, *args, **kwargs):
		if isinstance(response, dict):
			responses.append(response)

	process_request(
		endpoint="/mpesa/stkpushquery/v1/query",
		settings_name=settings.name,
		payload={
			"BusinessShortCode": settings.business_shortcode,
			"Password": generate_request_password(settings, timestamp),
			"Timestamp": timestamp,
			"CheckoutRequestID": express.checkout_request_id,
		},
		success_callback=capture,
		error_callback=capture,
		request_description="VMMS Payment Verification",
		doctype=EXPRESS,
		document_name=express.name,
	)
	return responses[-1] if responses else {}


def _store_query_confirmation(express, response):
	# Keep a previously captured receipt; STK query responses do not include it.
	locked = frappe.get_doc(EXPRESS, express.name, for_update=True)
	_confirmation_log(express, {"verified_query": response})
	fields = {
		"result_code": "0",
		"result_desc": "Verified by M-Pesa; accounting pending",
	}
	if locked.status != "Completed":
		fields["status"] = "In Progress"
	frappe.db.set_value(EXPRESS, express.name, fields)
	frappe.db.commit()


def _finish_accounting(express):
	from frappe_mpsa_payments.utils.utils import handle_successful_transaction

	from .event_payments import confirm_event_booking, validate_event_booking

	express = frappe.get_doc(EXPRESS, express.name, for_update=True)
	request = frappe.get_doc("Payment Request", express.reference_name, for_update=True)
	invoice = get_vmms_invoice(request)
	if not invoice or request.docstatus != 1 or express.docstatus != 1:
		frappe.throw(_("Only submitted VMMS payment requests can be recovered"))
	validate_event_booking(invoice)
	existing_payment = get_existing_payment(request, invoice)
	if existing_payment:
		validate_existing_payment(existing_payment, invoice.company)
	else:
		if express.transaction_id and frappe.db.exists(
			"Mpesa C2B Payment Register", {"transid": express.transaction_id, "docstatus": ["!=", 2]}
		):
			frappe.throw(
				_("This receipt already has a C2B record; reconcile it before creating another entry")
			)
		if request.currency != "KES" or flt(express.amount) != flt(request.outstanding_amount):
			frappe.throw(_("M-Pesa amount differs from the outstanding request; reconciliation is required"))
		settings = frappe.get_doc("Mpesa Settings", express.settings)
		handle_successful_transaction(express, {}, settings, express.checkout_request_id)
	confirm_event_booking(invoice)
	frappe.db.set_value("Payment Request", request.name, "status", "Paid")
	frappe.db.set_value(EXPRESS, express.name, "status", "Completed")
	log_name = frappe.db.get_value(
		"Integration Request",
		{
			"integration_request_service": CONFIRMATION_SERVICE,
			"reference_doctype": EXPRESS,
			"reference_docname": express.name,
		},
		"name",
	)
	if log_name:
		frappe.db.set_value("Integration Request", log_name, "status", "Completed")
	if request.get("payment_token"):
		frappe.publish_realtime(
			"stk_payment_complete",
			{
				"status": "Completed",
				"expected_token": request.payment_token,
			},
			room="website",
			after_commit=True,
		)
	return {"status": "Completed", "payment_request": request.name}


def _recover_confirmed_payment(express):
	try:
		response = _query_provider_status(express)
	except Exception:
		frappe.log_error(title="VMMS M-Pesa verification failed", message=frappe.get_traceback())
		frappe.db.set_value(
			EXPRESS, express.name, "result_desc", "M-Pesa verification pending; retry scheduled"
		)
		return {"status": "Unconfirmed"}
	if (
		not express.checkout_request_id
		or str(response.get("ResultCode")) != "0"
		or response.get("CheckoutRequestID") != express.checkout_request_id
	):
		fields = {"result_desc": "M-Pesa settlement not yet verified"}
		if (
			response.get("CheckoutRequestID") == express.checkout_request_id
			and response.get("ResultCode") is not None
		):
			fields["result_code"] = str(response["ResultCode"])
		frappe.db.set_value(EXPRESS, express.name, fields)
		return {"status": "Unconfirmed"}
	_store_query_confirmation(express, response)
	frappe.db.savepoint("vmms_membership_payment")
	try:
		return _finish_accounting(express)
	except Exception:
		frappe.db.rollback(save_point="vmms_membership_payment")
		frappe.log_error(title="VMMS Payment Accounting Pending", message=frappe.get_traceback())
		return {"status": "Accounting Pending", "express_request": express.name}


@frappe.whitelist(methods=["POST"])
def recover_payment(name, dry_run=True):
	"""Finance-only recovery; defaults to inspection and never initiates a charge."""
	return _recover_payment(name, dry_run=dry_run)


@frappe.whitelist(methods=["POST"])
def recover_membership_payment(name, dry_run=True):
	return _recover_payment(name, dry_run=dry_run, payment_kind="membership")


def _recover_payment(name, dry_run=True, payment_kind=None):
	frappe.only_for(("Accounts Manager", "System Manager"))
	express = frappe.get_doc(EXPRESS, name)
	express.check_permission("read")
	if express.reference_doctype != "Payment Request":
		frappe.throw(_("This request is not for a VMMS invoice"))
	request = frappe.get_doc("Payment Request", express.reference_name)
	request.check_permission("write")
	invoice = get_vmms_invoice(request)
	if not invoice or (payment_kind == "membership" and not invoice.get("membership")):
		frappe.throw(_("This request does not match the requested VMMS payment type"))
	if _is_dry_run(dry_run):
		return {
			"status": "Inspection",
			"express_request": name,
			"invoice": invoice.name,
			"company": invoice.company,
			"amount": express.amount,
			"event_booking": invoice.get("event_booking"),
			"existing_payment": get_existing_payment(request, invoice),
			"receiving_account": get_receiving_account(
				request.payment_account, request.mode_of_payment, invoice.company, request.currency
			),
		}
	if not frappe.has_permission("Payment Entry", "create") or not frappe.has_permission(
		"Payment Entry", "submit"
	):
		frappe.throw(
			_("Payment Entry creation and submission permission is required"), frappe.PermissionError
		)
	return _recover_confirmed_payment(express)


def recover_pending_membership_payments(since=None, limit=20, dry_run=True):
	return recover_pending_payments(since=since, limit=limit, dry_run=dry_run, payment_kind="membership")


def recover_pending_payments(since=None, limit=20, dry_run=True, payment_kind=None):
	"""Bounded batch for the scheduler or bench execute; old backlogs require an explicit since."""
	frappe.only_for(("Accounts Manager", "System Manager"))
	if payment_kind not in (None, "membership", "event"):
		frappe.throw(_("Invalid VMMS payment type"))
	scope = "ifnull(si.membership,'')!=''"
	if payment_kind != "membership" and frappe.db.has_column("Sales Invoice", "event_booking"):
		event_scope = "ifnull(si.event_booking,'')!=''"
		scope = event_scope if payment_kind == "event" else f"({scope} or {event_scope})"
	elif payment_kind == "event":
		return []
	rows = frappe.db.sql(
		f"""
		select er.name from `tabMpesa Express Request` er
		join `tabPayment Request` pr on er.reference_doctype='Payment Request' and er.reference_name=pr.name
		join `tabSales Invoice` si on pr.reference_doctype='Sales Invoice' and pr.reference_name=si.name
		where {scope} and si.docstatus!=2 and pr.docstatus=1
		and er.docstatus=1 and er.status='In Progress'
		and (er.creation >= %(since)s or (%(include_confirmed)s=1 and er.result_code='0'))
		order by er.modified asc, er.name asc limit %(limit)s
	""",  # Only fixed, internal field expressions; all values remain bound parameters.
		{
			"since": since or add_days(now_datetime(), -1),
			"include_confirmed": int(since is None),
			"limit": max(1, min(cint(limit), 50)),
		},
		as_dict=True,
	)
	results = []
	for row in rows:
		try:
			result = _recover_payment(row.name, dry_run=dry_run, payment_kind=payment_kind)
			if not _is_dry_run(dry_run):
				frappe.db.commit()
			results.append({"express_request": row.name, **result})
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title="VMMS Payment Recovery", message=frappe.get_traceback())
			results.append({"express_request": row.name, "status": "Review Required"})
	return results


def retry_recent_payments():
	if "frappe_mpsa_payments" in frappe.get_installed_apps():
		recover_pending_payments(dry_run=False)
