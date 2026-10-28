import unittest
from unittest.mock import MagicMock, patch

import frappe

from . import event_payments as payments


def reject(message, *args, **kwargs):
	raise frappe.ValidationError(message)


class TestEventPaymentCompletion(unittest.TestCase):
	def setUp(self):
		self.fake = MagicMock()
		self.fake.throw.side_effect = reject
		self.invoice = frappe._dict(
			name="INV-1",
			event_booking="BOOK-1",
			company="Bomet",
			currency="KES",
			grand_total=1000,
			docstatus=1,
			outstanding_amount=0,
		)
		self.booking = MagicMock()
		self.booking.name = "BOOK-1"
		self.booking.docstatus = 0
		self.booking.company = "Bomet"
		self.booking.currency = "KES"
		self.booking.total_amount = 1000
		self.booking.attendees = [frappe._dict(name="A-1"), frappe._dict(name="A-2")]
		self.booking.get.side_effect = lambda field: getattr(self.booking, field, None)
		self.booking.meta.has_field.return_value = False
		self.tickets = 0
		self.fake.get_doc.return_value = self.booking
		self.fake.db.get_value.return_value = self.invoice
		self.fake.db.count.side_effect = lambda *a, **k: self.tickets
		self.booking.submit.side_effect = self.issue_tickets
		p = patch.multiple(payments, frappe=self.fake, _=lambda value: value)
		p.start()
		self.addCleanup(p.stop)

	def issue_tickets(self):
		self.booking.docstatus = 1
		self.tickets += len(self.booking.attendees)

	def test_paid_booking_submits_once_and_issues_attendee_tickets(self):
		payments.confirm_event_booking(self.invoice)
		self.assertEqual(self.tickets, 2)
		self.booking.submit.assert_called_once()

	def test_repeat_confirmation_reuses_existing_tickets(self):
		payments.confirm_event_booking(self.invoice)
		payments.confirm_event_booking(self.invoice)
		self.assertEqual(self.tickets, 2)
		self.booking.submit.assert_called_once()

	def test_unpaid_invoice_cannot_issue_tickets(self):
		self.invoice.outstanding_amount = 1000
		with self.assertRaises(frappe.ValidationError):
			payments.confirm_event_booking(self.invoice)
		self.booking.submit.assert_not_called()

	def test_cancelled_booking_cannot_be_reopened_by_callback(self):
		self.booking.docstatus = 2
		with self.assertRaises(frappe.ValidationError):
			payments.confirm_event_booking(self.invoice)
		self.booking.submit.assert_not_called()

	def test_draft_booking_with_existing_tickets_is_not_submitted_again(self):
		self.tickets = 1
		with self.assertRaises(frappe.ValidationError):
			payments.confirm_event_booking(self.invoice)
		self.booking.submit.assert_not_called()

	def test_submitted_booking_with_missing_tickets_requires_review(self):
		self.booking.docstatus = 1
		self.tickets = 1
		with self.assertRaises(frappe.ValidationError):
			payments.confirm_event_booking(self.invoice)
		self.booking.submit.assert_not_called()

	def test_booking_company_must_match_invoice_company(self):
		self.booking.company = "Nairobi"
		with self.assertRaises(frappe.ValidationError):
			payments.confirm_event_booking(self.invoice)
		self.booking.submit.assert_not_called()

	def test_booking_amount_must_match_invoice_total(self):
		self.booking.total_amount = 500
		with self.assertRaises(frappe.ValidationError):
			payments.confirm_event_booking(self.invoice)
		self.booking.submit.assert_not_called()
