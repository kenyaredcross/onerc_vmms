"""Membership and event accounting and confirmed STK recovery, owned by VMMS."""

import json
from ast import literal_eval
from datetime import datetime
from decimal import Decimal, InvalidOperation

import frappe
from frappe import _
from frappe.query_builder import DocType, Order
from frappe.utils import add_days, cint, flt, now_datetime

from ..utils.utils import system_session

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


# Provider callbacks have no Desk session; accounting requires verified server evidence.
@frappe.whitelist(allow_guest=True, methods=["POST"])  # nosemgrep: guest-whitelisted-method
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
	# Restore the caller identity after processing this provider callback.
	with system_session():
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
	# Provider confirmation must survive a later accounting rollback.
	frappe.db.commit()  # nosemgrep: frappe-manual-commit


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


def _verification_context(express):
	return {
		"checkout_request_id": express.checkout_request_id,
		"reference_doctype": express.reference_doctype,
		"reference_name": express.reference_name,
		"settings": express.settings,
		"amount": format(Decimal(str(express.amount)).normalize(), "f"),
	}


def _response_dict(value):
	# The connector stores Python dict representations; VMMS stores JSON.
	if not isinstance(value, str) or len(value) > 100_000:
		return {}
	try:
		result = json.loads(value)
	except (TypeError, ValueError):
		try:
			result = literal_eval(value)
		except (ValueError, SyntaxError, TypeError, RecursionError):
			return {}
	return result if isinstance(result, dict) else {}


def _is_verified_response(response, checkout):
	return (
		isinstance(response, dict)
		and bool(checkout)
		and str(response.get("ResultCode")) == "0"
		and response.get("CheckoutRequestID") == checkout
	)


def _get_stored_verification(express):
	output = _response_dict(
		frappe.db.get_value(
			"Integration Request",
			{
				"integration_request_service": CONFIRMATION_SERVICE,
				"reference_doctype": EXPRESS,
				"reference_docname": express.name,
			},
			"output",
		)
	)
	response = output.get("verified_query")
	if not _is_verified_response(response, express.checkout_request_id):
		return None
	context = output.get("verified_context")
	if context is not None:
		return response if context == _verification_context(express) else None
	# Older VMMS confirmations have no binding. Corroborate them with both
	# the original initiation and the successful server query, never a callback.
	settings = frappe.get_doc("Mpesa Settings", express.settings)
	host = "https://sandbox.safaricom.co.ke" if settings.sandbox else "https://api.safaricom.co.ke"
	logs = frappe.get_all(
		"Integration Request",
		filters={
			"integration_request_service": "Mpesa",
			"reference_doctype": EXPRESS,
			"reference_docname": express.name,
			"status": "Completed",
			"request_description": ["in", ["Mpesa STK Push", "VMMS Payment Verification"]],
		},
		fields=["request_description", "url", "data", "output"],
		order_by="creation asc",
		limit_page_length=200,
	)
	initiated = verified = False
	for log in logs:
		data, result = _response_dict(log.data), _response_dict(log.output)
		if str(data.get("BusinessShortCode")) != str(settings.business_shortcode):
			continue
		if log.url == host + "/mpesa/stkpush/v1/processrequest":
			try:
				amount_matches = Decimal(str(data.get("Amount"))) == Decimal(str(express.amount))
			except InvalidOperation:
				amount_matches = False
			initiated |= amount_matches and result.get("CheckoutRequestID") == express.checkout_request_id
		elif log.url == host + "/mpesa/stkpushquery/v1/query":
			verified |= data.get(
				"CheckoutRequestID"
			) == express.checkout_request_id and _is_verified_response(result, express.checkout_request_id)
	return response if initiated and verified else None


def _store_query_confirmation(express, response):
	# Keep a previously captured receipt; STK query responses do not include it.
	locked = frappe.get_doc(EXPRESS, express.name, for_update=True)
	_confirmation_log(
		express, {"verified_query": response, "verified_context": _verification_context(express)}
	)
	fields = {
		"result_code": "0",
		"result_desc": "Verified by M-Pesa; accounting pending",
	}
	if locked.status != "Completed":
		fields["status"] = "In Progress"
	frappe.db.set_value(EXPRESS, express.name, fields)
	# Persist verified evidence before entering the accounting savepoint.
	frappe.db.commit()  # nosemgrep: frappe-manual-commit


def _confirm_membership_payment(invoice):
	if not invoice.get("membership"):
		return
	if invoice.docstatus != 1 or flt(invoice.outstanding_amount) > 0:
		frappe.throw(_("Membership payment can only be recognized after full invoice settlement"))
	membership = frappe.get_doc("VM Membership", invoice.membership, for_update=True)
	if membership.company != invoice.company:
		frappe.throw(_("Membership and invoice must belong to the same company"))
	if not membership.paid:
		if membership.status == "Draft":
			membership.validate_membership_period()
		# Payment recognition does not approve, activate, or renew again.
		membership.db_set("paid", 1)


def _finish_accounting(express):
	from .event_payments import confirm_event_booking, validate_event_booking

	express = frappe.get_doc(EXPRESS, express.name, for_update=True)
	request = frappe.get_doc("Payment Request", express.reference_name, for_update=True)
	invoice = get_vmms_invoice(request)
	if not invoice or invoice.docstatus == 2 or request.docstatus != 1 or express.docstatus != 1:
		frappe.throw(_("Only submitted VMMS payment requests can be recovered"))
	if (
		request.currency != "KES"
		or invoice.currency != "KES"
		or flt(express.amount) != flt(request.grand_total)
	):
		frappe.throw(_("M-Pesa amount differs from the payment request; reconciliation is required"))
	validate_event_booking(invoice)
	existing_payment = get_existing_payment(request, invoice)
	if not existing_payment:
		if express.transaction_id and frappe.db.exists(
			"Mpesa C2B Payment Register", {"transid": express.transaction_id, "docstatus": ["!=", 2]}
		):
			frappe.throw(
				_("This receipt already has a C2B record; reconcile it before creating another entry")
			)
		if request.currency != "KES" or flt(express.amount) != flt(request.outstanding_amount):
			frappe.throw(_("M-Pesa amount differs from the outstanding request; reconciliation is required"))
		if invoice.docstatus == 0:
			if not invoice.posting_date:
				frappe.throw(_("The invoice requires a posting date before recovery"))
			# Prevent delayed submission from replacing the invoice date with
			# today while leaving its due date and payment schedule in the past.
			invoice.set_posting_time = 1
			invoice.submit()
		request.create_payment_entry()
		existing_payment = get_existing_payment(request, invoice)
	invoice.reload()
	if not existing_payment or invoice.docstatus != 1 or flt(invoice.outstanding_amount) > 0:
		frappe.throw(_("The payment has not fully settled the invoice; reconciliation is required"))
	validate_existing_payment(existing_payment, invoice.company)
	allocations = frappe.get_all(
		"Payment Entry Reference",
		filters={
			"parent": existing_payment,
			"parenttype": "Payment Entry",
			"docstatus": 1,
			"reference_doctype": "Sales Invoice",
			"reference_name": invoice.name,
		},
		fields=["allocated_amount"],
	)
	if abs(sum(flt(row.allocated_amount) for row in allocations) - flt(express.amount)) > 0.001:
		frappe.throw(_("The existing payment allocation differs from the verified M-Pesa amount"))
	_confirm_membership_payment(invoice)
	confirm_event_booking(invoice)
	frappe.db.set_value("Payment Request", request.name, "status", "Paid")
	frappe.db.set_value(
		EXPRESS,
		express.name,
		{"status": "Completed", "result_desc": "Verified by M-Pesa; accounting completed"},
	)
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
	return {
		"status": "Completed",
		"payment_request": request.name,
		"payment_entry": existing_payment,
		"invoice": invoice.name,
		"membership": invoice.get("membership"),
		"event_booking": invoice.get("event_booking"),
	}


def _recover_confirmed_payment(express):
	response = _get_stored_verification(express)
	if response is None:
		try:
			response = _query_provider_status(express)
		except Exception:
			frappe.log_error(title="VMMS M-Pesa verification failed", message=frappe.get_traceback())
			frappe.db.set_value(
				EXPRESS, express.name, "result_desc", "M-Pesa verification pending; retry scheduled"
			)
			return {"status": "Unconfirmed"}
		if not _is_verified_response(response, express.checkout_request_id):
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
def recover_payment(name: str, dry_run: bool | str = True) -> dict:
	"""Finance-only recovery; defaults to inspection and never initiates a charge."""
	return _recover_payment(name, dry_run=dry_run)


@frappe.whitelist(methods=["POST"])
def recover_membership_payment(name: str, dry_run: bool | str = True) -> dict:
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
	express = DocType(EXPRESS)
	request = DocType("Payment Request")
	invoice = DocType("Sales Invoice")
	membership = DocType("VM Membership")
	scope = invoice.membership.isnotnull() & (invoice.membership != "")
	if payment_kind != "membership" and frappe.db.has_column("Sales Invoice", "event_booking"):
		event_scope = invoice.event_booking.isnotnull() & (invoice.event_booking != "")
		scope = event_scope if payment_kind == "event" else scope | event_scope
	elif payment_kind == "event":
		return []
	unrecognized_memberships = (
		frappe.qb.from_(membership)
		.select(membership.name)
		.where((membership.paid == 0) | membership.paid.isnull())
	)
	pending = (express.status == "In Progress") | (
		(express.status == "Completed") & invoice.membership.isin(unrecognized_memberships)
	)
	retry_window = express.creation >= (since or add_days(now_datetime(), -1))
	if since is None:
		retry_window |= express.result_code == "0"
	rows = (
		frappe.qb.from_(express)
		.join(request)
		.on((express.reference_doctype == "Payment Request") & (express.reference_name == request.name))
		.join(invoice)
		.on((request.reference_doctype == "Sales Invoice") & (request.reference_name == invoice.name))
		.select(express.name)
		.where(
			scope
			& (invoice.docstatus != 2)
			& (request.docstatus == 1)
			& (express.docstatus == 1)
			& pending
			& retry_window
		)
		.orderby(express.modified, express.name, order=Order.asc)
		.limit(max(1, min(cint(limit), 50)))
	).run(as_dict=True)
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
