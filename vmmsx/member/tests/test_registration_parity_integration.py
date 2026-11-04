"""Member registration retains legacy payment, eligibility and duplicate rules."""

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.member.services import approval, membership, payment, renewal
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestMembershipRegistrationParity(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.plan = fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=600, fee_currency="KES")
		cls.other_plan = fixtures.make_type(fixtures.TYPE_ROUTED, approval.MODE_ROUTED, fee=1000)

	def apply(self, **kwargs):
		profile = fixtures.make_profile(
			"Parity", "Applicant", date_of_birth="1990-01-01", phone="+254722222222"
		)
		return profile, fixtures.make_membership(profile, self.plan.name, self.society_a["ward"], **kwargs)

	def test_another_number_can_pay_without_replacing_the_persons_phone(self):
		profile, record = self.apply(payer_phone="+254711111111")
		membership.submit(record)
		record.reload()
		transaction = frappe.get_doc("OneRC Payment Transaction", record.payment_transaction)
		self.assertEqual(transaction.phone_number, "254711111111")
		self.assertEqual(frappe.db.get_value("Red Profile", profile, "phone"), "+254722222222")
		self.assertEqual(record.payer_phone, "+254711111111")

	def test_pending_registration_blocks_another_plan_at_the_same_anchor(self):
		profile, first = self.apply()
		membership.submit(first)
		second = fixtures.make_membership(profile, self.other_plan.name, self.society_a["ward"])
		with self.assertRaises(frappe.ValidationError):
			membership.submit(second)
		self.assertFalse(second.payment_transaction)

	def test_current_membership_blocks_a_second_gateway_membership(self):
		profile, first = self.apply()
		membership.submit(first)
		fixtures.confirm_payment_through_manual_driver(first.reload())
		second = fixtures.make_membership(profile, self.plan.name, self.society_a["ward"])
		with self.assertRaises(frappe.ValidationError):
			membership.submit(second)
		self.assertFalse(second.payment_transaction)

	def test_another_anchor_still_allows_membership(self):
		profile, first = self.apply()
		membership.submit(first)
		fixtures.confirm_payment_through_manual_driver(first.reload())
		second = fixtures.make_membership(profile, self.plan.name, self.society_a["other_ward"])
		membership.submit(second)
		self.assertTrue(second.payment_transaction)

	def test_expired_period_can_be_renewed_without_weakening_duplicate_checks(self):
		_profile, first = self.apply()
		membership.submit(first)
		fixtures.confirm_payment_through_manual_driver(first.reload())
		frappe.db.set_value(
			fixtures.MEMBERSHIP_DOCTYPE, first.name, "valid_to", add_days(getdate(today()), -1)
		)
		result = renewal.renew(first.reload())
		self.assertEqual(
			frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, result["name"], "renews"), first.name
		)

	def test_age_limited_plan_refuses_missing_birth_date_before_payment(self):
		plan = fixtures.make_type(
			f"{fixtures.TEST_PREFIX}-parity-age",
			approval.MODE_AUTO_ON_PAYMENT,
			fee=600,
			requires_age_requirement=1,
			lower_age_limit=18,
			upper_age_limit=30,
		)
		profile = fixtures.make_profile("Unknown", "Birthday", date_of_birth=None)
		record = fixtures.make_membership(profile, plan.name, self.society_a["ward"])
		with self.assertRaises(frappe.MandatoryError):
			membership.submit(record)
		self.assertFalse(record.payment_transaction)

	def test_age_limited_plan_refuses_ineligible_person_before_payment(self):
		plan = fixtures.make_type(
			f"{fixtures.TEST_PREFIX}-parity-age-outside",
			approval.MODE_AUTO_ON_PAYMENT,
			fee=600,
			requires_age_requirement=1,
			lower_age_limit=0,
			upper_age_limit=6,
		)
		profile = fixtures.make_profile("Adult", "Applicant", date_of_birth="1990-01-01")
		record = fixtures.make_membership(profile, plan.name, self.society_a["ward"])
		with self.assertRaises(frappe.ValidationError):
			membership.submit(record)
		self.assertFalse(record.payment_transaction)

	def test_agreed_amount_and_currency_are_persisted(self):
		_profile, record = self.apply()
		membership.submit(record)
		record.reload()
		self.assertEqual(record.amount, 600)
		self.assertEqual(record.currency, "KES")
		self.assertEqual(
			payment.recorded_fee(record, frappe._dict(fee_amount=900, fee_currency="USD"))["amount"], 600
		)

	def test_invalid_age_configuration_is_rejected_when_saved(self):
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_type(
				f"{fixtures.TEST_PREFIX}-parity-age-invalid",
				approval.MODE_ROUTED,
				requires_age_requirement=1,
				lower_age_limit=30,
				upper_age_limit=18,
			)
