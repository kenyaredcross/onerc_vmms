# Copyright (c) 2025, Kenya Red Cross Society and contributors
# For license information, please see license.txt


import json
from datetime import datetime

import frappe
from frappe import _
from frappe.email import sendmail_to_system_managers
from frappe.model.document import Document
from frappe.utils import (
	add_months,
	add_years,
	flt,
	get_link_to_form,
	getdate,
	nowdate,
	random_string,
	today,
)

from ...utils.utils import log_throw_error
from ..vm_member.vm_member import create_member


class VMMembership(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Float
		company: DF.Link
		currency: DF.Link | None
		from_date: DF.Date
		member: DF.Link | None
		member_name: DF.Data | None
		member_since_date: DF.Date | None
		membership_type: DF.Link
		naming_series: DF.Literal["VM-MSH-.YYYY.-"]
		paid: DF.Check
		qr_code: DF.AttachImage | None
		status: DF.Literal["Draft", "Pending", "Active", "Rejected", "Expired"]
		to_date: DF.Date | None

	# end: auto-generated types
	def validate(self):
		self.validate_member()
		self.validate_life_member()

	def validate_life_member(self):
		membership_type = self.get_membership_type()
		if membership_type.billing_cycle == "One Off" and self.status == "Expired":
			frappe.throw(_("One Off type Membership cannot expire"))

	def get_membership_type(self) -> Document:
		doc_name = frappe.db.exists("VM Membership Type", self.membership_type)
		if not doc_name:
			frappe.throw(_("Membership Type Not found"), frappe.DoesNotExistError)
		return frappe.get_doc("VM Membership Type", doc_name)

	def validate_member(self):
		if not self.member or not frappe.db.exists("VM Member", self.member):
			# for web forms
			user_type = frappe.db.get_value("User", frappe.session.user, "user_type")
			if user_type == "Website User":
				self.create_member_from_website_user()
			else:
				frappe.throw(_("Please select a Member"))

		self._apply_membership_period_logic()

	def validate_membership_period(self):
		self._apply_membership_period_logic()
		self.save(ignore_permissions=True)

	def _apply_membership_period_logic(self):
		if not self.status == "Draft":
			return
		membership_type = frappe.get_doc("VM Membership Type", self.membership_type)

		invoices = frappe.get_all(
			"Sales Invoice",
			filters={"membership": self.name},
			fields=["name", "grand_total", "outstanding_amount", "posting_date"],
			order_by="posting_date asc",
		)

		if not invoices:
			if self.to_date and getdate(self.to_date) < getdate(today()):
				self.status = "Expired"
			return

		total_paid = 0
		for inv in invoices:
			if getdate(inv.posting_date) >= getdate(self.from_date):
				if inv.outstanding_amount == 0:
					total_paid += inv.grand_total

		cycle_amount = self.amount or membership_type.amount
		cycles = int(total_paid // cycle_amount) if cycle_amount else 0

		if cycles <= 0:
			if self.to_date and getdate(self.to_date) < getdate(today()):
				self.status = "Expired"
			return

		start_date = (
			today() if not self.from_date or getdate(self.from_date) < getdate(today()) else self.from_date
		)

		end_date = get_cycle_dates(start_date, membership_type.billing_cycle, cycles)

		self.to_date = end_date
		self.status = "Pending"

	def create_member_from_website_user(self):
		member_name = frappe.get_value("VM Member", dict(email_id=frappe.session.user))

		if not member_name:
			user = frappe.get_doc("User", frappe.session.user)
			member = frappe.get_doc(
				dict(
					doctype="VM Member",
					email_id=frappe.session.user,
					membership_type=self.membership_type,
					member_name=user.get_fullname(),
				)
			).insert(ignore_permissions=True)
			member_name = member.name

		if self.get("__islocal"):
			self.member = member_name

	@frappe.whitelist()
	def generate_invoice(self, save=True, with_payment_entry=False):
		member = frappe.get_doc("VM Member", self.member)
		if not member.customer:
			member = frappe.get_doc("VM Member", self.member)
			member.make_customer_and_link()
			member.reload()

		plan = frappe.get_doc("VM Membership Type", self.membership_type)
		settings = frappe.get_doc("VM Settings")

		invoice = make_invoice(self, member, plan)
		self.reload()

		if with_payment_entry:
			self.make_payment_entry(settings, invoice)

		if save:
			self.save(ignore_permissions=True)

		return invoice

	@frappe.whitelist()
	def initiate_payment(self, phone_number=None):
		member = frappe.get_doc("VM Member", self.member)
		if not member.customer:
			member = frappe.get_doc("VM Member", self.member)
			member.make_customer_and_link()
			member.reload()

		plan = frappe.get_doc("VM Membership Type", self.membership_type)

		payment_request, invoice = make_payment_request(self, member, plan, phone_number)
		self.reload()

		return payment_request, invoice

	def make_payment_entry(self, settings, invoice):
		if not settings.membership_payment_account:
			frappe.throw(
				_("You need to set <b>Payment Account</b> for Membership in {0}").format(
					get_link_to_form("VM Settings", "VM Settings")
				)
			)

		from erpnext.accounts.doctype.payment_entry.payment_entry import (
			get_payment_entry,
		)

		frappe.flags.ignore_account_permission = True
		pe = get_payment_entry(dt="Sales Invoice", dn=invoice.name, bank_amount=invoice.grand_total)
		frappe.flags.ignore_account_permission = False
		pe.paid_to = settings.membership_payment_account
		pe.reference_no = self.name
		pe.reference_date = getdate()
		pe.flags.ignore_mandatory = True
		pe.save()
		pe.submit()

		self.status = "Pending"

	@frappe.whitelist()
	def send_acknowlement(self):
		settings = frappe.get_doc("VM Settings")
		if not settings.send_email:
			frappe.throw(
				_("You need to enable <b>Send Acknowledge Email</b> in {0}").format(
					get_link_to_form("VM Settings", "VM Settings")
				)
			)

		member = frappe.get_doc("VM Member", self.member)
		if not member.email_id:
			frappe.throw(
				_("Email address of member {0} is missing").format(
					frappe.utils.get_link_to_form("VM Member", self.member)
				)
			)

		plan = frappe.get_doc("VM Membership Type", self.membership_type)
		email = member.email_id
		attachments = [
			frappe.attach_print(
				"VM Membership",
				self.name,
				print_format=settings.membership_print_format,
			)
		]

		if self.invoice and settings.send_invoice:
			attachments.append(
				frappe.attach_print(
					"Sales Invoice",
					self.invoice,
					print_format=settings.inv_print_format,
				)
			)

		email_template = frappe.get_doc("Email Template", settings.email_template)
		context = {"doc": self, "member": member}

		email_args = {
			"recipients": [email],
			"message": frappe.render_template(
				email_template.get("response"), context
			),  # nosemgrep: frappe-ssti -- template from admin-managed Email Template, not user input
			"subject": frappe.render_template(
				email_template.get("subject"), context
			),  # nosemgrep: frappe-ssti -- template from admin-managed Email Template, not user input
			"attachments": attachments,
			"reference_doctype": self.doctype,
			"reference_name": self.name,
		}

		if not frappe.flags.in_test:
			frappe.enqueue(
				method=frappe.sendmail,
				queue="short",
				timeout=300,
				is_async=True,
				**email_args,
			)
		else:
			frappe.sendmail(**email_args)

	def generate_and_send_invoice(self):
		self.generate_invoice(save=False)
		self.send_acknowlement()

	@frappe.whitelist()
	def approve_membership(self):
		if self.status == "Active":
			return self

		qr_data = make_qr_code(get_verification_url(self.name))

		qr_code_file = frappe.get_doc(
			{
				"doctype": "File",
				"content": qr_data,
				"attached_to_doctype": "VM Membership",
				"attached_to_name": self.name,
				"file_name": f"Membership-{self.name}-QR.png",
			}
		).save(ignore_permissions=True)

		self.qr_code = qr_code_file.file_url

		self.status = "Active"

		return self.save()


def make_qr_code(data: str) -> bytes:
	import io

	import qrcode
	from qrcode.image.styledpil import StyledPilImage
	from qrcode.image.styles.colormasks import RadialGradiantColorMask
	from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer

	qr = qrcode.QRCode(
		version=1,
		error_correction=qrcode.constants.ERROR_CORRECT_H,
		box_size=10,
		border=4,
	)
	qr.add_data(data)
	qr.make(fit=True)

	img = qr.make_image(
		image_factory=StyledPilImage,
		module_drawer=RoundedModuleDrawer(),
		color_mask=RadialGradiantColorMask(
			back_color=(255, 255, 255),
			center_color=(178, 24, 43),
			edge_color=(110, 0, 20),
		),
	)
	output = io.BytesIO()
	img.save(output, format="PNG")
	return output.getvalue()


def get_qr_token(membership_name: str) -> str:
	"""HMAC token proving the QR code was issued by this site (prevents forged QR codes)."""
	import hashlib
	import hmac

	from frappe.utils.password import get_encryption_key

	return hmac.new(get_encryption_key().encode(), membership_name.encode(), hashlib.sha256).hexdigest()[:32]


def verify_qr_token(membership_name: str, token: str) -> bool:
	import hmac

	if not membership_name or not token:
		return False
	return hmac.compare_digest(get_qr_token(membership_name), str(token))


def get_verification_url(membership_name: str) -> str:
	from urllib.parse import urlencode

	from frappe.utils import get_url

	query = urlencode({"membership": membership_name, "token": get_qr_token(membership_name)})
	return get_url(f"/vmms/verify-membership?{query}")


def parse_scanned_qr(scanned_data: str) -> tuple[str, str]:
	"""Extract membership name and token from a scanned verification URL."""
	from urllib.parse import parse_qs, urlparse

	try:
		query = parse_qs(urlparse(scanned_data or "").query)
		return query.get("membership", [""])[0], query.get("token", [""])[0]
	except ValueError:
		return "", ""


def get_cycle_dates(start_date, billing_cycle, cycles=1):
	"""Return end_date given start_date, billing cycle, and cycles count."""
	if billing_cycle == "Monthly":
		return add_months(start_date, cycles)
	elif billing_cycle == "Yearly":
		return add_years(start_date, cycles)
	elif billing_cycle == "One Off":
		return add_years(start_date, 100)
	else:
		frappe.throw(_("Unsupported billing cycle: {0}").format(billing_cycle))


def make_invoice(membership, member, plan):
	company = frappe.get_doc("Company", membership.company)

	# Get defaults from Company
	default_income_account = company.default_income_account
	default_expense_account = company.default_expense_account
	default_cost_center = company.cost_center

	# Get item doc to fetch its defaults
	item = frappe.get_doc("Item", plan.linked_item)

	income_account = item.get("income_account") or default_income_account
	expense_account = item.get("expense_account") or default_expense_account
	cost_center = item.get("cost_center") or default_cost_center

	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": member.customer,
			"currency": membership.currency,
			"company": membership.company,
			"membership": membership.name,
			"is_pos": 0,
			"items": [
				{
					"item_code": plan.linked_item,
					"rate": membership.amount,
					"qty": 1,
					"membership": membership.name,
					"income_account": income_account,
					"expense_account": expense_account,
					"cost_center": cost_center,
				}
			],
		}
	)

	# invoice.set_missing_values()
	invoice.insert(ignore_permissions=True)
	# invoice.submit()

	frappe.msgprint(_("Sales Invoice created successfully"))

	return invoice


def make_payment_request(membership, member, plan, phone_number=None):
	try:
		invoice = None
		mop = frappe.db.get_value("VM Settings", "VM Settings", "membership_mode_of_payment")

		reusable_invoice = frappe.db.get_value(
			"Sales Invoice",
			{
				"membership": membership.name,
				"docstatus": ["!=", 2],
				"outstanding_amount": [">", 0],
			},
			"name",
		)
		invoice = (
			frappe.get_doc("Sales Invoice", reusable_invoice)
			if reusable_invoice
			else make_invoice(membership, member, plan)
		)

		payment_gateway = get_payment_gateway_from_mop(mop, membership.company)
		payment_gateway_account = frappe.db.get_value(
			"Payment Gateway Account",
			{"payment_gateway": payment_gateway, "company": membership.company},
			"name",
		)
		payment_gateway_account = frappe.db.get_value(
			"Payment Gateway Account",
			{"is_default": 1, "currency": membership.currency},
			["name"],
		)

		if not payment_gateway_account:
			frappe.throw(
				_("Please set up a default Payment Gateway Account for currency {0}").format(
					membership.currency
				)
			)

		for stale_request in frappe.get_all(
			"Payment Request",
			filters={
				"reference_doctype": "Sales Invoice",
				"reference_name": invoice.name,
				"docstatus": 1,
				"outstanding_amount": [">", 0],
			},
			pluck="name",
		):
			frappe.get_doc("Payment Request", stale_request).cancel()

		payment_request = frappe.get_doc(
			{
				"doctype": "Payment Request",
				"payment_request_type": "Inward",
				"transaction_date": nowdate(),
				"party_type": "Customer",
				"status": "Initiated",
				"party": member.customer,
				"reference_doctype": "Sales Invoice",
				"reference_name": invoice.name,
				"mode_of_payment": mop,
				"payment_gateway": payment_gateway,
				"payment_gateway_account": payment_gateway_account,
				"outstanding_amount": invoice.outstanding_amount,
				"currency": membership.currency,
				"grand_total": membership.amount,
				"email_to": member.email_id,
				"payment_token": random_string(16),
				# "payment_gateway_account": payment_gateway_account,
				"subject": _("Payment Request for {0} Membership").format(plan.name),
				"message": _("Please pay {0} {1} to renew your membership.").format(
					membership.currency, membership.amount
				),
			}
		)

		if phone_number:
			payment_request.phone_number = phone_number

		payment_request.insert(ignore_permissions=True)
		payment_request.submit()

		frappe.msgprint(_("Payment Request created successfully"))
		return payment_request, invoice

	except frappe.ValidationError:
		raise

	except Exception as e:
		message = f"{e}\n\n{frappe.get_traceback()}"
		log = frappe.log_error(_("Error creating payment request for {0}").format(member.name), message)
		# Throw rather than return: every caller unpacks the result as a 2-tuple, and this
		# also lets the caller's rollback run instead of leaving a half-built payment.
		frappe.throw(_("Failed to create payment request. Please check the error log: {0}").format(log.name))


def get_member_based_on_subscription(subscription_id, email=None, customer_id=None):
	filters = {"subscription_id": subscription_id}
	if email:
		filters.update({"email_id": email})
	if customer_id:
		filters.update({"customer_id": customer_id})

	members = frappe.get_all("VM Member", filters=filters, order_by="creation desc")

	try:
		return frappe.get_doc("VM Member", members[0]["name"])
	except Exception:
		return None


def verify_signature(data, endpoint="VM Membership"):
	signature = frappe.request.headers.get("X-Razorpay-Signature")

	settings = frappe.get_doc("VM Settings")
	key = settings.get_webhook_secret(endpoint)

	controller = frappe.get_doc("Razorpay Settings")

	controller.verify_signature(data, signature, key)
	frappe.set_user(
		settings.creation_user
	)  # nosemgrep: frappe-setuser -- webhook; runs only after Razorpay signature verification


@frappe.whitelist(
	allow_guest=True
)  # nosemgrep: guest-whitelisted-method -- Razorpay webhook; signature-verified in process_request_data
def trigger_razorpay_subscription(*args, **kwargs):
	data = frappe.request.get_data(as_text=True)
	data = process_request_data(data)

	subscription = data.payload.get("subscription", {}).get("entity", {})
	subscription = frappe._dict(subscription)

	payment = data.payload.get("payment", {}).get("entity", {})
	payment = frappe._dict(payment)

	try:
		if not data.event == "subscription.charged":
			return

		member = get_member_based_on_subscription(subscription.id, payment.email)
		if not member:
			member = create_member(
				frappe._dict(
					{
						"fullname": payment.email,
						"email": payment.email,
						"plan_id": get_plan_from_razorpay_id(subscription.plan_id),
					}
				)
			)

			member.subscription_id = subscription.id
			member.customer_id = payment.customer_id

			if subscription.get("notes"):
				member = get_additional_notes(member, subscription)

		company = get_company_for_memberships()
		# Update Membership
		membership = frappe.new_doc("VM Membership")
		membership.update(
			{
				"company": company,
				"member": member.name,
				"status": "Current",
				"membership_type": member.membership_type,
				"currency": "INR",
				"paid": 1,
				"payment_id": payment.id,
				"from_date": datetime.fromtimestamp(subscription.current_start),
				"to_date": datetime.fromtimestamp(subscription.current_end),
				"amount": payment.amount / 100,  # Convert to rupees from paise
			}
		)
		membership.flags.ignore_mandatory = True
		membership.insert()

		# Update membership values
		member.subscription_start = datetime.fromtimestamp(subscription.start_at)
		member.subscription_end = datetime.fromtimestamp(subscription.end_at)
		member.subscription_status = "Active"
		member.flags.ignore_mandatory = True
		member.save()

		settings = frappe.get_doc("VM Settings")
		if settings.allow_invoicing and settings.automate_membership_invoicing:
			membership.reload()
			membership.generate_invoice(
				with_payment_entry=settings.automate_membership_payment_entries,
				save=True,
			)

	except Exception as e:
		message = f"{e}\n\n{frappe.get_traceback()}\n\n{_('Payment ID')}: {payment.id}"
		log = frappe.log_error(message, _("Error creating membership entry for {0}").format(member.name))
		notify_failure(log)
		return {"status": "Failed", "reason": e}

	return {"status": "Success"}


def process_request_data(data):
	try:
		verify_signature(data)
	except Exception as e:
		log = frappe.log_error(e, "Membership Webhook Verification Error")
		notify_failure(log)
		return {"status": "Failed", "reason": e}

	if isinstance(data, str):
		data = json.loads(data)
	data = frappe._dict(data)

	return data


def get_company_for_memberships():
	company = frappe.db.get_single_value("VM Settings", "company")
	if not company:
		from ...utils.utils import get_company

		company = get_company()
	return company


def get_additional_notes(member, subscription):
	if isinstance(subscription.notes, dict):
		for k, v in subscription.notes.items():
			notes = "\n".join(f"{k}: {v}")

			# extract member name from notes
			if "name" in k.lower():
				member.update({"member_name": subscription.notes.get(k)})

			# extract pan number from notes
			if "pan" in k.lower():
				member.update({"pan_number": subscription.notes.get(k)})

		member.add_comment("Comment", notes)

	elif isinstance(subscription.notes, str):
		member.add_comment("Comment", subscription.notes)

	return member


def notify_failure(log):
	try:
		content = """
			Dear System Manager,
			Razorpay webhook for creating renewing membership subscription failed due to some reason.
			Please check the following error log linked below
			Error Log: {}
			Regards, Administrator
		""".format(get_link_to_form("Error Log", log.name))

		sendmail_to_system_managers(
			"[Important] [ERPNext] Razorpay membership webhook failed , please check.",
			content,
		)
	except Exception:
		pass


def get_plan_from_razorpay_id(plan_id):
	plan = frappe.get_all(
		"VM Membership Type",
		filters={"razorpay_plan_id": plan_id},
		order_by="creation desc",
	)

	try:
		return plan[0]["name"]
	except Exception:
		return None


def set_expired_status():
	membership = frappe.qb.DocType("VM Membership")

	query = (
		frappe.qb.update(membership)
		.set(membership.status, "Expired")
		.set(membership.modified, frappe.utils.now())
		.set(membership.modified_by, frappe.session.user)
		.where(membership.to_date < nowdate())
		.where(membership.status.notin(["Rejected", "Expired"]))
	)

	one_off_types = frappe.get_all(
		"VM Membership Type",
		filters={"billing_cycle": "One Off"},
		pluck="name",
	)
	if one_off_types:
		query = query.where(membership.membership_type.notin(one_off_types))

	query.run()
	frappe.db.commit()


def get_last_membership(member):
	"""Returns last membership if exists"""
	last_membership = frappe.get_all(
		"VM Membership",
		"name,to_date,membership_type",
		dict(member=member, paid=1),
		order_by="to_date desc",
		limit=1,
	)

	if last_membership:
		return last_membership[0]


@frappe.whitelist()
def get_payment_gateway_from_mop(mode_of_payment: str, company: str) -> str:
	payment_gateway = None
	try:
		if not frappe.db.exists("Mode of Payment", mode_of_payment):
			return None
		mop_doc = frappe.get_doc("Mode of Payment", mode_of_payment)
		account_entry = next((acc for acc in mop_doc.accounts if acc.company == company), None)
		if account_entry:
			payment_account = account_entry.default_account
			if frappe.db.exists("Payment Gateway Account", {"payment_account": payment_account}):
				try:
					pg_account = frappe.get_doc(
						"Payment Gateway Account", {"payment_account": payment_account}
					)
					if pg_account and pg_account.payment_gateway:
						payment_gateway = pg_account.payment_gateway
				except Exception:
					pass
			else:
				default_pg_account = frappe.get_value(
					"Payment Gateway Account", {"is_default": 1}, "payment_gateway"
				)
				if default_pg_account:
					payment_gateway = default_pg_account
	except Exception:
		pass

	return payment_gateway


@frappe.whitelist()
def process_qr_scan(scanned_data: str) -> dict[str, str]:
	VM_DOC = "VM Membership"

	if not frappe.has_permission(VM_DOC, "read"):
		frappe.throw(_("You are not permitted to scan memberships"), frappe.PermissionError)

	membership_name, token = parse_scanned_qr(scanned_data)
	if not verify_qr_token(membership_name, token) or not frappe.db.exists(VM_DOC, membership_name):
		frappe.throw(_("Membership in QR Code is invalid"))

	try:
		membership_data: dict = frappe.db.get_value(
			VM_DOC,
			membership_name,
			["member", "member_name", "status", "membership_type"],
			as_dict=True,
		)
	except Exception:
		log_throw_error("Error fetching membership details")

	else:
		from frappe import get_desk_link

		if membership_data:
			membership_data["membership_desk_link"] = get_desk_link(VM_DOC, membership_name)
			membership_data["member_desk_link"] = get_desk_link("VM Member", membership_data["member"])

		return membership_data
