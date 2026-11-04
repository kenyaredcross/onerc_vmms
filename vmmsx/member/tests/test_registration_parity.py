"""Registration parity rules; isolated from gateway and site configuration."""

from datetime import date
from unittest import TestCase
from unittest.mock import Mock, patch

import frappe

from vmmsx.member.services import membership, payment


class TestRegistrationParity(TestCase):
	def setUp(self):
		translation = patch.object(membership, "_", side_effect=lambda message: message)
		translation.start()
		self.addCleanup(translation.stop)
		bold = patch("frappe.bold", side_effect=str)
		bold.start()
		self.addCleanup(bold.stop)

	def test_calendar_month_clamps_to_last_day_instead_of_thirty_days(self):
		plan = frappe._dict(is_lifetime=0, billing_cycle="Monthly", duration_days=30)
		self.assertEqual(str(membership._valid_to(plan, date(2028, 1, 31))), "2028-02-29")

	def test_calendar_year_preserves_leap_day_boundary(self):
		plan = frappe._dict(is_lifetime=0, billing_cycle="Yearly", duration_days=365)
		self.assertEqual(str(membership._valid_to(plan, date(2027, 3, 1))), "2028-03-01")

	def test_unconfigured_cycle_keeps_fixed_day_duration(self):
		plan = frappe._dict(is_lifetime=0, duration_days=30)
		self.assertEqual(str(membership._valid_to(plan, date(2028, 1, 31))), "2028-03-01")

	def test_one_off_is_lifetime(self):
		self.assertTrue(membership.is_lifetime(frappe._dict(billing_cycle="One Off", is_lifetime=0)))

	def test_age_rule_needs_a_date_of_birth(self):
		plan = frappe._dict(requires_age_requirement=1, lower_age_limit=18, upper_age_limit=30)
		with (
			patch("frappe.db", frappe._dict(get_value=lambda *args, **kwargs: None)),
			patch("frappe.throw", side_effect=frappe.ValidationError),
		):
			with self.assertRaises(frappe.ValidationError):
				membership.assert_age_eligibility(frappe._dict(member="member"), plan)

	def test_age_rule_accepts_inclusive_boundaries_and_rejects_outside(self):
		plan = frappe._dict(requires_age_requirement=1, lower_age_limit=18, upper_age_limit=30)
		for born, accepted in [
			("2008-11-02", True),
			("1996-11-02", True),
			("2008-11-03", False),
			("1995-11-02", False),
		]:
			with (
				self.subTest(born=born),
				patch("frappe.db", frappe._dict(get_value=Mock(side_effect=["profile", born]))),
				patch.object(membership, "today", return_value="2026-11-02"),
				patch("frappe.throw", side_effect=frappe.ValidationError),
			):
				if accepted:
					membership.assert_age_eligibility(frappe._dict(member="member"), plan)
				else:
					with self.assertRaises(frappe.ValidationError):
						membership.assert_age_eligibility(frappe._dict(member="member"), plan)

	def test_unrestricted_plan_does_not_require_birth_date(self):
		membership.assert_age_eligibility(
			frappe._dict(member="member"), frappe._dict(requires_age_requirement=0)
		)

	def test_payment_uses_payer_phone_without_changing_contact_phone(self):
		application = frappe._dict(member="member", payer_phone="+254711111111")
		plan = frappe._dict(fee_amount=600, fee_currency="KES")
		person = {"phone": "+254722222222", "email": "person@example.test"}
		with (
			patch.object(payment, "assert_available"),
			patch.object(payment, "_chosen_method", return_value=None),
			patch("frappe.get_doc", return_value=frappe._dict()),
			patch("vmmsx.member.services.identity.read", return_value=person),
			patch("vmmsx.member.services.identity.display_name", return_value="Test Person"),
			patch(
				"onerc_payments.api.v1.payment.initiate_payment", return_value={"transaction_id": "pay-test"}
			) as initiate,
		):
			application.doctype = "VMMS Membership"
			application.name = "test"
			application.membership_type = "test-plan"
			application.geo_node = "test-node"
			payment.request(application, plan)
		self.assertEqual(initiate.call_args.kwargs["payer_phone"], "+254711111111")
		self.assertEqual(person["phone"], "+254722222222")

	def test_gateway_duplicate_is_refused_before_another_payment(self):
		application = frappe._dict(member="member", membership_type="plan", geo_node="node", name="new")
		with (
			patch(
				"frappe.db",
				frappe._dict(
					get_value=lambda *args, **kwargs: None,
					get_values=lambda *args, **kwargs: [
						{"name": "held", "membership_status": "Active", "valid_to": None}
					],
				),
			),
			patch("frappe.get_cached_value", return_value="Plan"),
			patch("onerc_core.geo.services.adapter.get_full_path", return_value="Home"),
			patch("frappe.throw", side_effect=frappe.ValidationError),
		):
			with self.assertRaises(frappe.ValidationError):
				membership.assert_not_already_held(application)

	def test_recorded_fee_does_not_change_with_current_plan_price(self):
		application = frappe._dict(amount=500, currency="KES")
		self.assertEqual(
			payment.recorded_fee(application, frappe._dict(fee_amount=900, fee_currency="USD")),
			{"amount": 500, "currency": "KES"},
		)

	def test_recorded_zero_fee_remains_zero(self):
		self.assertEqual(
			payment.recorded_fee(
				frappe._dict(amount=0, currency="KES"), frappe._dict(fee_amount=900, fee_currency="USD")
			)["amount"],
			0,
		)

	def test_payment_falls_back_to_contact_phone_for_existing_records(self):
		application = frappe._dict(
			member="member", doctype="VMMS Membership", name="test", membership_type="plan", geo_node="node"
		)
		plan = frappe._dict(fee_amount=600, fee_currency="KES")
		with (
			patch.object(payment, "assert_available"),
			patch.object(payment, "_chosen_method", return_value=None),
			patch("frappe.get_doc", return_value=frappe._dict()),
			patch("vmmsx.member.services.identity.read", return_value={"phone": "+254722222222"}),
			patch("vmmsx.member.services.identity.display_name", return_value="Test Person"),
			patch(
				"onerc_payments.api.v1.payment.initiate_payment", return_value={"transaction_id": "pay-test"}
			) as initiate,
		):
			payment.request(application, plan)
		self.assertEqual(initiate.call_args.kwargs["payer_phone"], "+254722222222")

	def test_zero_fee_snapshot_stays_settled_after_the_plan_price_increases(self):
		self.assertTrue(
			payment.is_settled(
				frappe._dict(amount=0, currency="KES"), frappe._dict(fee_amount=600, fee_currency="KES")
			)
		)

	def test_positive_snapshot_does_not_become_free_if_the_plan_price_drops(self):
		self.assertFalse(
			payment.is_settled(
				frappe._dict(amount=600, currency="KES"), frappe._dict(fee_amount=0, fee_currency="KES")
			)
		)


class TestFreeFeeSnapshot(TestCase):
	def test_an_explicit_zero_fee_with_no_currency_does_not_become_a_later_price(self):
		application = frappe._dict(amount=0, currency=None, fee_snapshot_taken=1)
		self.assertEqual(
			payment.recorded_fee(application, frappe._dict(fee_amount=900, fee_currency="KES")),
			{"amount": 0, "currency": None},
		)
