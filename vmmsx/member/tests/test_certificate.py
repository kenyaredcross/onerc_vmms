# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The membership certificate — domain context in, shared renderer out.

The Member module's half of templating is a context dict and nothing else. These
tests prove the join: which template renders is configuration on the membership
type, the context carries values read from Red Profile and core's geo adapter,
and the receipt appears only when a gateway actually produced one.
"""

import frappe

from vmmsx.member.services import approval, certificate
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

ALT_TEMPLATE_KEY = f"{fixtures.TEST_PREFIX}-alt-certificate"


class TestCertificate(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=600)

	def tearDown(self):
		super().tearDown()

		if frappe.db.exists(fixtures.TEMPLATE_DOCTYPE, ALT_TEMPLATE_KEY):
			frappe.delete_doc(fixtures.TEMPLATE_DOCTYPE, ALT_TEMPLATE_KEY, force=True)

	def active_membership(self, receipt: str | None = None):
		profile = fixtures.make_profile("Cert", "Holder")
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])
		membership_service.submit(membership)

		row = self.reload(membership.name)
		row.on_payment_confirmed(amount=600, receipt=receipt, transaction_id=row.payment_transaction)

		return self.reload(membership.name)

	def test_the_context_reads_the_name_from_red_profile(self):
		membership = self.active_membership()
		context = certificate.context_for(membership)

		self.assertEqual(context["member_name"], "Cert Holder")

	def test_the_context_carries_the_geo_path_from_core_s_adapter(self):
		from onerc_core.geo.services import adapter

		membership = self.active_membership()
		context = certificate.context_for(membership)

		self.assertEqual(context["geo_path"], adapter.get_full_path(membership.geo_node))

	def test_the_context_carries_the_type_s_active_benefits(self):
		membership = self.active_membership()

		self.assertEqual(certificate.context_for(membership)["benefits"], ["Clinic access"])

	def test_it_renders_through_the_configured_template(self):
		membership = self.active_membership()
		result = certificate.render_certificate(membership)

		self.assertEqual(result["template_key"], fixtures.TEMPLATE_KEY)
		self.assertIn("Cert Holder", result["body"])

	def test_pointing_the_type_at_another_template_changes_the_certificate(self):
		"""No code change — one Link field on the type."""
		membership = self.active_membership()
		before = certificate.render_certificate(membership)

		fixtures.make_template(ALT_TEMPLATE_KEY, body="ALTERNATE // {{ member_name }}")
		frappe.db.set_value(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO, "template_key", ALT_TEMPLATE_KEY)
		frappe.clear_document_cache(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO)

		after = certificate.render_certificate(membership)

		self.assertNotEqual(before["body"], after["body"])
		self.assertEqual(after["body"], "ALTERNATE // Cert Holder")
		self.assertEqual(after["template_key"], ALT_TEMPLATE_KEY)

		frappe.db.set_value(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO, "template_key", fixtures.TEMPLATE_KEY)
		frappe.clear_document_cache(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO)

	def test_editing_the_template_body_changes_the_certificate(self):
		membership = self.active_membership()
		before = certificate.render_certificate(membership)

		template = frappe.get_doc(fixtures.TEMPLATE_DOCTYPE, fixtures.TEMPLATE_KEY)
		template.body = "REVISED :: {{ member_name }}"
		template.save()
		frappe.clear_document_cache(fixtures.TEMPLATE_DOCTYPE, fixtures.TEMPLATE_KEY)

		after = certificate.render_certificate(membership)

		self.assertNotEqual(before["body"], after["body"])
		self.assertIn("REVISED", after["body"])

	def test_a_receipt_appears_only_when_a_gateway_produced_one(self):
		without = certificate.context_for(self.active_membership())
		self.assertEqual(without["payment_receipt"], "")

		with_receipt = certificate.context_for(self.active_membership(receipt="MPESA-XYZ"))
		self.assertEqual(with_receipt["payment_receipt"], "MPESA-XYZ")

	def test_a_certificate_renders_fine_with_no_receipt_at_all(self):
		"""Manual driver, no receipt, complete certificate."""
		membership = self.active_membership()
		result = certificate.render_certificate(membership)

		self.assertTrue(result["body"])
		self.assertIn("Cert Holder", result["body"])

	def test_a_type_with_no_template_says_so_clearly(self):
		membership = self.active_membership()
		frappe.db.set_value(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO, "template_key", None)
		frappe.clear_document_cache(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO)

		with self.assertRaises(frappe.MandatoryError):
			certificate.render_certificate(membership)

		frappe.db.set_value(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO, "template_key", fixtures.TEMPLATE_KEY)
		frappe.clear_document_cache(fixtures.TYPE_DOCTYPE, fixtures.TYPE_AUTO)

	def test_the_api_refuses_a_certificate_for_an_inactive_membership(self):
		"""A certificate is evidence of membership, not of an application."""
		from vmmsx.api import member as member_api

		profile = fixtures.make_profile("Not", "Yet")
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])
		membership_service.submit(membership)

		with self.assertRaises(frappe.ValidationError):
			member_api.get_certificate(membership.name)
