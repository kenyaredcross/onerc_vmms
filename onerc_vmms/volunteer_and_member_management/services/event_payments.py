"""Confirm paid event bookings through their native submission and ticket hooks."""

import frappe
from frappe import _
from frappe.utils import flt


def validate_event_booking(invoice):
	if not invoice.get("event_booking"):
		return None
	booking = frappe.get_doc("Event Booking", invoice.event_booking, for_update=True)
	if booking.docstatus == 2:
		frappe.throw(_("The event booking is cancelled; reconcile this payment before proceeding"))
	if booking.get("company") and booking.company != invoice.company:
		frappe.throw(_("The event booking and invoice must belong to the same company"))
	if booking.currency != invoice.currency or flt(booking.total_amount) != flt(invoice.grand_total):
		frappe.throw(_("The event booking amount and currency must match the invoice"))
	if not booking.attendees:
		frappe.throw(_("The event booking has no attendees; review it before issuing tickets"))
	return booking


def confirm_event_booking(invoice):
	"""Submit once after settlement; never regenerate tickets on a retry."""
	if not invoice.get("event_booking"):
		return None
	settlement = frappe.db.get_value(
		"Sales Invoice", invoice.name, ["docstatus", "outstanding_amount"], as_dict=True
	)
	if not settlement or settlement.docstatus != 1 or flt(settlement.outstanding_amount) > 0:
		frappe.throw(_("Event tickets can only be issued after the invoice is fully settled"))
	booking = validate_event_booking(invoice)
	active_tickets = frappe.db.count("Event Ticket", {"booking": booking.name, "docstatus": ["!=", 2]})
	if booking.docstatus == 0:
		if active_tickets:
			frappe.throw(_("This draft booking already has tickets; review it before issuing more"))
		for field, value in _paid_fields(booking).items():
			setattr(booking, field, value)
		booking.flags.ignore_permissions = True
		# Event Booking.on_submit owns ticket creation, QR codes and notifications.
		booking.submit()
		booking.reload()
		if booking.currency != invoice.currency or flt(booking.total_amount) != flt(invoice.grand_total):
			frappe.throw(_("The booking amount changed during confirmation; reconcile the payment"))
	issued_tickets = frappe.db.count("Event Ticket", {"booking": booking.name, "docstatus": 1})
	active_tickets = frappe.db.count("Event Ticket", {"booking": booking.name, "docstatus": ["!=", 2]})
	if booking.docstatus != 1 or issued_tickets != len(booking.attendees) or active_tickets != issued_tickets:
		frappe.throw(
			_("The booking ticket count is inconsistent; review it without issuing duplicate tickets")
		)
	# Some versions keep payment flags on an already submitted booking. Updating
	# those flags must not run on_submit or generate another set of tickets.
	changes = {field: value for field, value in _paid_fields(booking).items() if booking.get(field) != value}
	if changes:
		booking.db_set(changes)
	return booking.name


def _paid_fields(booking):
	fields = {}
	for field, value in (("payment_status", "Paid"), ("status", "Confirmed")):
		if booking.meta.has_field(field):
			options = (booking.meta.get_field(field).options or "").splitlines()
			if value in options:
				fields[field] = value
	return fields
