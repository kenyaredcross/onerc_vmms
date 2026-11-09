# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A paid membership runs from its payment, and its receipt is only its holder's.

The receipt page is `/receipt/<membership>`, so the id is in the address bar and
anybody can type another one. These prove that changing it shows nothing: not to
another member, not to one in the same branch, not to a guest. Staff the
membership is routed to still read it, because the branch needs the M-Pesa code.
"""

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.api import member as member_api
from vmmsx.member.services import membership as membership_service
from vmmsx.member.services import receipt
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestReceiptAndValidity(RegistrationTestCase):
	def paid_membership(self, handle: str):
		user, membership = self.register_as_member(
			handle,
			fixtures.TYPE_AUTO,
			payer_phone="+254711000222",
			applicant_last_name=handle.split(".")[-1].title(),
		)
		fixtures.confirm_payment_through_manual_driver(membership)
		membership.reload()
		return user, membership

	# --- validity -----------------------------------------------------------

	def test_validity_runs_from_the_payment_not_the_approval(self):
		_, membership = self.register_as_member("validity.late", fixtures.TYPE_AUTO, applicant_last_name="Late")
		paid = add_days(today(), -20)
		membership.db_set("paid_on", f"{paid} 09:30:00")
		membership.reload()

		membership_service.activate(membership)
		membership.reload()

		duration = frappe.db.get_value(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO, "duration_days")
		self.assertEqual(getdate(membership.valid_from), getdate(paid))
		self.assertEqual(getdate(membership.valid_to), getdate(add_days(paid, duration)))

	def test_a_receipt_before_approval_already_shows_the_window(self):
		_, membership = self.register_as_member("validity.pending", fixtures.TYPE_AUTO, applicant_last_name="Pending")
		paid = add_days(today(), -3)
		membership.db_set({"paid_on": f"{paid} 12:00:00", "valid_from": None, "valid_to": None})
		membership.reload()

		shown = receipt.build(membership)["membership"]

		self.assertEqual(getdate(shown["valid_from"]), getdate(paid))
		self.assertTrue(shown["valid_to"])

	# --- the receipt address ------------------------------------------------

	def test_the_holder_opens_their_own_receipt(self):
		user, membership = self.paid_membership("receipt.holder")

		with fixtures.acting_as(user):
			shown = member_api.membership_receipt(membership.name)

		self.assertEqual(shown["membership"]["name"], membership.name)

	def test_another_member_in_the_same_branch_cannot_open_it_by_changing_the_id(self):
		_, theirs = self.paid_membership("receipt.theirs")
		neighbour, mine = self.paid_membership("receipt.neighbour")
		self.assertEqual(mine.geo_node, theirs.geo_node, "both joined the same branch")

		with fixtures.acting_as(neighbour), self.assertRaises(frappe.PermissionError):
			member_api.membership_receipt(theirs.name)

	def test_a_guest_cannot_open_a_receipt(self):
		_, membership = self.paid_membership("receipt.guest")

		with fixtures.acting_as("Guest"), self.assertRaises(frappe.PermissionError):
			member_api.membership_receipt(membership.name)

	def test_a_made_up_id_gives_nothing_away(self):
		user, _ = self.paid_membership("receipt.guesser")

		with fixtures.acting_as(user), self.assertRaises(frappe.PermissionError) as missing:
			member_api.membership_receipt("VM-MSH-0000-99999")

		_, theirs = self.paid_membership("receipt.real")
		with fixtures.acting_as(user), self.assertRaises(frappe.PermissionError) as real:
			member_api.membership_receipt(theirs.name)

		self.assertEqual(str(missing.exception), str(real.exception), "a real id and a made-up one look the same")

	def test_the_branch_approver_reads_it(self):
		_, membership = self.paid_membership("receipt.staff")

		with fixtures.acting_as(self.approver):
			shown = member_api.membership_receipt(membership.name)

		self.assertTrue(shown["gateway_receipt"])

	def test_a_member_cannot_post_a_payment_to_the_books(self):
		user, membership = self.paid_membership("receipt.poster")

		with fixtures.acting_as(user), self.assertRaises(frappe.PermissionError):
			member_api.post_membership_payment(membership.name)
