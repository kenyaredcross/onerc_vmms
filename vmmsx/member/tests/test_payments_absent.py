# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A site with no payments app fails at configuration time, not at the first click.

vmmsx does not declare `onerc_payments` in `required_apps`, on purpose: a society
running membership without fees should not be made to install a payment gateway.
That makes "the payments app is not here" a real, supportable state — and before
this, a fee-bearing membership type could be saved on such a site perfectly
happily, then blow up with a raw `ModuleNotFoundError` the moment somebody
applied.

Same principle as the ACC-02 anchor: a configuration that cannot work is refused
while an administrator is looking at the form.

**Absence is mocked, because the app really is installed here.** These tests
patch `frappe.get_installed_apps` to return the real list minus
`onerc_payments`, which is exactly the surface the guards read — they ask
installed-apps rather than trying the import, so absence is a question that can
be asked at config time instead of an exception that can only happen at call
time.
"""

from unittest.mock import patch

import frappe

from vmmsx.member.services import approval, payment
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

TYPE_PAID = f"{fixtures.TEST_PREFIX}-absent-paid"
TYPE_FREE = f"{fixtures.TEST_PREFIX}-absent-free"


def without_payments():
	"""Patch installed-apps to exclude the payments app, keeping everything else.

	The real list minus one entry, rather than a hand-written list: patching in
	something like `["frappe"]` would also hide vmmsx and onerc_core from any
	framework code that happens to ask during the same call.
	"""
	remaining = [app for app in frappe.get_installed_apps() if app != payment.PAYMENTS_APP]

	return patch.object(frappe, "get_installed_apps", return_value=remaining)


class TestPaymentsAbsent(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()

	def tearDown(self):
		super().tearDown()

		for key in (TYPE_PAID, TYPE_FREE):
			if frappe.db.exists(fixtures.TYPE_DOCTYPE, key):
				frappe.delete_doc(fixtures.TYPE_DOCTYPE, key, force=True)

	# --- the mock itself --------------------------------------------------

	def test_the_mock_really_hides_the_app(self):
		"""A mock that did not work would make every test below vacuous."""
		self.assertIn(payment.PAYMENTS_APP, frappe.get_installed_apps())
		self.assertTrue(payment.is_available())

		with without_payments():
			self.assertNotIn(payment.PAYMENTS_APP, frappe.get_installed_apps())
			self.assertFalse(payment.is_available())

		# ...and it is put back afterwards.
		self.assertTrue(payment.is_available())

	def test_detection_does_not_depend_on_the_import_succeeding(self):
		"""The module is still importable under the mock — absence is a *setting*.

		If the guard detected absence by catching ImportError, this would be the
		test that exposed it: the import still works here, and the guard must
		still say the app is unavailable.
		"""
		with without_payments():
			self.assertFalse(payment.is_available())

			import onerc_payments.api.v1.payment as still_importable

			self.assertTrue(hasattr(still_importable, "initiate_payment"))

	# --- (a) config time ---------------------------------------------------

	def test_a_fee_bearing_type_refuses_to_save(self):
		with without_payments(), self.assertRaises(frappe.ValidationError):
			fixtures.make_type(TYPE_PAID, approval.MODE_AUTO_ON_PAYMENT, fee=500, template_key=None)

	def test_the_refusal_names_the_missing_dependency(self):
		"""The message has to tell an administrator what to install."""
		with without_payments(), self.assertRaises(frappe.ValidationError):
			fixtures.make_type(TYPE_PAID, approval.MODE_AUTO_ON_PAYMENT, fee=500, template_key=None)

		message = frappe.as_json(frappe.message_log[-1] if frappe.message_log else {})

		self.assertIn(payment.PAYMENTS_APP, message)

	def test_nothing_was_saved_by_the_refused_attempt(self):
		with without_payments(), self.assertRaises(frappe.ValidationError):
			fixtures.make_type(TYPE_PAID, approval.MODE_AUTO_ON_PAYMENT, fee=500, template_key=None)

		self.assertFalse(frappe.db.exists(fixtures.TYPE_DOCTYPE, TYPE_PAID))

	def test_a_zero_fee_type_still_saves(self):
		"""The guard is fee-scoped. Fee-free membership must remain configurable.

		This is the over-blocking test: a society with no gateway and no fees is
		a supported deployment, and refusing its types would make the guard worse
		than the bug.
		"""
		with without_payments():
			created = fixtures.make_type(TYPE_FREE, approval.MODE_ROUTED, fee=0, template_key=None)

		self.assertTrue(frappe.db.exists(fixtures.TYPE_DOCTYPE, created.name))

	# --- (b) call time -----------------------------------------------------

	def test_applying_raises_a_frappe_error_not_a_module_not_found(self):
		"""The headline for the runtime half.

		The type is created while the app is present — as it would have been —
		and only *then* does the app go away. The applicant gets a clean refusal
		rather than a traceback.
		"""
		fixtures.make_type(TYPE_PAID, approval.MODE_AUTO_ON_PAYMENT, fee=500)

		profile = fixtures.make_profile("Absent", "Payments")
		membership = fixtures.make_membership(profile, TYPE_PAID, self.society_a["ward"])

		with without_payments():
			with self.assertRaises(frappe.ValidationError) as caught:
				membership_service.submit(membership)

			self.assertNotIsInstance(caught.exception, ModuleNotFoundError)

	def test_the_call_time_refusal_also_names_the_app(self):
		fixtures.make_type(TYPE_PAID, approval.MODE_AUTO_ON_PAYMENT, fee=500)

		profile = fixtures.make_profile("Absent", "Named")
		membership = fixtures.make_membership(profile, TYPE_PAID, self.society_a["ward"])

		with without_payments(), self.assertRaises(frappe.ValidationError):
			membership_service.submit(membership)

		message = frappe.as_json(frappe.message_log[-1] if frappe.message_log else {})

		self.assertIn(payment.PAYMENTS_APP, message)

	def test_no_transaction_was_left_behind(self):
		"""A refused request must not leave a half-initiated payment."""
		fixtures.make_type(TYPE_PAID, approval.MODE_AUTO_ON_PAYMENT, fee=500)

		profile = fixtures.make_profile("Absent", "Clean")
		membership = fixtures.make_membership(profile, TYPE_PAID, self.society_a["ward"])

		with without_payments(), self.assertRaises(frappe.ValidationError):
			membership_service.submit(membership)

		self.assertFalse(self.reload(membership.name).payment_transaction)

	def test_a_free_type_applies_fine_with_no_payments_app(self):
		"""The seam is never reached, so its absence cannot matter."""
		# The approver first: creating them creates the Role, which the workflow
		# stage links to.
		approver = self.scoped_user("absent_approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(approver, fixtures.APPROVER_ROLE, self.society_a["county"])

		fixtures.make_workflow()
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.make_type(TYPE_FREE, approval.MODE_ROUTED, fee=0)

		profile = fixtures.make_profile("Absent", "FreeType")
		membership = fixtures.make_membership(profile, TYPE_FREE, self.society_a["ward"])

		with without_payments():
			membership_service.submit(membership)

		self.assertEqual(self.membership_status(membership.name), membership_service.STATUS_AWAITING_APPROVAL)

	# --- no regression to the working seam ---------------------------------

	def test_everything_still_works_with_payments_present(self):
		"""The guards must be invisible on an ordinary site."""
		fixtures.make_type(TYPE_PAID, approval.MODE_AUTO_ON_PAYMENT, fee=500)

		profile = fixtures.make_profile("Present", "Payments")
		membership = fixtures.make_membership(profile, TYPE_PAID, self.society_a["ward"])
		membership_service.submit(membership)

		self.assertTrue(self.reload(membership.name).payment_transaction)

		fixtures.confirm_payment_through_manual_driver(self.reload(membership.name))

		self.assertEqual(self.membership_status(membership.name), membership_service.STATUS_ACTIVE)

	def test_a_fee_bearing_type_saves_normally_when_the_app_is_there(self):
		created = fixtures.make_type(TYPE_PAID, approval.MODE_AUTO_ON_PAYMENT, fee=500)

		self.assertTrue(frappe.db.exists(fixtures.TYPE_DOCTYPE, created.name))
		self.assertTrue(payment.is_available())
