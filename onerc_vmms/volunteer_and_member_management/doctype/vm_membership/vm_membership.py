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
    get_link_to_form,
    getdate,
    nowdate,
    today,
)

from ..vm_member.vm_member import create_member


class VMMembership(Document):
    def validate(self):
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
        frappe.db.commit()

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
            today()
            if not self.from_date or getdate(self.from_date) < getdate(today())
            else self.from_date
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

        payment_request, invoice = make_payment_request(
            self, member, plan, phone_number
        )
        self.reload()

        return payment_request, invoice

    def make_payment_entry(self, settings, invoice):
        if not settings.membership_payment_account:
            frappe.throw(
                _(
                    "You need to set <b>Payment Account</b> for Membership in {0}"
                ).format(get_link_to_form("VM Settings", "VM Settings"))
            )

        from erpnext.accounts.doctype.payment_entry.payment_entry import (
            get_payment_entry,
        )

        frappe.flags.ignore_account_permission = True
        pe = get_payment_entry(
            dt="Sales Invoice", dn=invoice.name, bank_amount=invoice.grand_total
        )
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
            "message": frappe.render_template(email_template.get("response"), context),
            "subject": frappe.render_template(email_template.get("subject"), context),
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

        qr_data_to_encode = frappe._dict(
            {
                "membership": self.name,
                "member": self.member_name,
                "membership_type": self.membership_type,
                "status": self.status,
            }
        )
        qr_data = make_qr_code(qr_data_to_encode)

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

        return self.save(ignore_permissions=True)


def make_qr_code(data: dict[str, any]) -> bytes:

    import io

    import qrcode
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers.pil import HorizontalBarsDrawer

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage, module_drawer=HorizontalBarsDrawer()
    )
    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()


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
        mop = frappe.db.get_value(
            "VM Settings", "VM Settings", "membership_mode_of_payment"
        )
        if not frappe.db.exists(
            "Sales Invoice",
            {"membership": membership.name, "docstatus": ["!=", 2]},
        ):
            invoice = make_invoice(membership, member, plan)
        else:
            invoice_id = frappe.db.get_value(
                "Sales Invoice",
                {"membership": membership.name, "docstatus": ["!=", 2]},
                "name",
            )
            invoice = frappe.get_doc("Sales Invoice", invoice_id)

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
                _(
                    "Please set up a default Payment Gateway Account for currency {0}"
                ).format(membership.currency)
            )

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
                # "payment_gateway_account": payment_gateway_account,
                "subject": _("Payment Request for {0} Membership").format(plan.name),
                "message": _("Please pay {0} {1} to renew your membership.").format(
                    membership.currency, membership.amount
                ),
            }
        )

        if phone_number:
            payment_request.phone_number = phone_number

        payment_request.flags.ignore_validate = True
        payment_request.insert(ignore_permissions=True)
        payment_request.submit()

        frappe.msgprint(_("Payment Request created successfully"))
        return payment_request, invoice

    except Exception as e:
        message = "{0}\n\n{1}".format(e, frappe.get_traceback())
        log = frappe.log_error(
            _("Error creating payment request for {0}").format(member.name), message
        )
        frappe.msgprint(
            _(
                "Failed to create payment request. Please check the error log: {0}"
            ).format(log.name)
        )
        return None


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
    frappe.set_user(settings.creation_user)


@frappe.whitelist(allow_guest=True)
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
        message = "{0}\n\n{1}\n\n{2}: {3}".format(
            e, frappe.get_traceback(), _("Payment ID"), payment.id
        )
        log = frappe.log_error(
            message, _("Error creating membership entry for {0}").format(member.name)
        )
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
        from ...utils import get_company

        company = get_company()
    return company


def get_additional_notes(member, subscription):
    if type(subscription.notes) == dict:
        for k, v in subscription.notes.items():
            notes = "\n".join("{}: {}".format(k, v))

            # extract member name from notes
            if "name" in k.lower():
                member.update({"member_name": subscription.notes.get(k)})

            # extract pan number from notes
            if "pan" in k.lower():
                member.update({"pan_number": subscription.notes.get(k)})

        member.add_comment("Comment", notes)

    elif type(subscription.notes) == str:
        member.add_comment("Comment", subscription.notes)

    return member


def notify_failure(log):
    try:
        content = """
			Dear System Manager,
			Razorpay webhook for creating renewing membership subscription failed due to some reason.
			Please check the following error log linked below
			Error Log: {0}
			Regards, Administrator
		""".format(
            get_link_to_form("Error Log", log.name)
        )

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
    today = nowdate()
    memberships = frappe.get_all(
        "VM Membership",
        filters={
            "status": ["not in", ["Cancelled", "Expired"]],
            "to_date": ["<", today],
        },
        fields=["name"],
    )

    if not memberships:
        return

    for m in memberships:
        frappe.db.set_value("VM Membership", m.name, "status", "Expired")

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
        account_entry = next(
            (acc for acc in mop_doc.accounts if acc.company == company), None
        )
        if account_entry:
            payment_account = account_entry.default_account
            if frappe.db.exists(
                "Payment Gateway Account", {"payment_account": payment_account}
            ):
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
