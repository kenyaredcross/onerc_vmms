# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A society that issues no volunteer cards (Kenya), and the certificate that
carries the Fundamental Principles and the signatures a society uploads."""

from pathlib import Path

import frappe

from vmmsx.member.services import certificate
from vmmsx.member.tests.base import MemberTestCase
from vmmsx.patches import install_card_and_signature_settings as settings_patch
from vmmsx.templating.services import render
from vmmsx.volunteer.services import card, society

EXTRA_TEST_RECORD_DEPENDENCIES = []

SETTINGS = "National Society Settings"
SEED = Path(frappe.get_app_path("vmmsx")) / "templating" / "seeds" / "membership_certificate_principles.html"


class TestVolunteerCardSwitch(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		settings_patch.install_fields()

	def setUp(self):
		super().setUp()
		self.addCleanup(self.issue, True)

	def issue(self, value: bool) -> None:
		frappe.db.set_single_value(SETTINGS, society.ISSUES_CARDS_FIELD, int(value))

	def test_a_society_that_never_opened_the_setting_issues_cards(self):
		frappe.db.delete("Singles", {"doctype": SETTINGS, "field": society.ISSUES_CARDS_FIELD})

		self.assertTrue(card.issued())
		self.assertTrue(card.holds_card(frappe._dict(status=card.ACTIVE)))

	def test_switched_off_nobody_holds_one_and_the_server_refuses_it(self):
		self.issue(False)
		active = frappe._dict(status=card.ACTIVE)

		self.assertFalse(card.issued())
		self.assertFalse(card.holds_card(active))
		with self.assertRaises(frappe.ValidationError) as refused:
			card.assert_holds(active)
		self.assertIn("does not issue volunteer cards", str(refused.exception))


class TestPrinciplesCertificate(MemberTestCase):
	def render(self, **context) -> str:
		base = {
			"member_name": "Njeri Test",
			"membership_type": "Life Member",
			"benefits": ["Life Membership Certificate", "Invite to special events"],
			"society_name": "Kenya Red Cross Society",
			"society_logo": "",
			"enrolled_day": "22",
			"enrolled_month": "October",
			"enrolled_year": "2026",
			"signature_left": "",
			"signature_right": "",
			"signatory_left": "The Governor",
			"signatory_right": "Secretary General",
			"blackletter_font": "",
		}
		# Whitespace collapsed, so the assertions read the sentence and not the
		# template's indentation.
		return " ".join(render.render_string(SEED.read_text(), {**base, **context}).split())

	def test_the_title_and_the_wording_come_from_the_type_s_benefits(self):
		html = self.render()

		self.assertIn("Life Membership Certificate", html)
		self.assertIn("enrolled as a life member of the<br>Kenya Red Cross Society.", html)
		self.assertIn("KENYA RED CROSS SOCIETY", html)
		self.assertIn("THE FUNDAMENTAL PRINCIPLES", html)

	def test_a_type_with_no_certificate_benefit_is_named_after_the_type(self):
		html = self.render(benefits=["Invite to special events"], membership_type="Ordinary Member")

		self.assertIn("Ordinary Membership Certificate", html)
		self.assertIn("enrolled as an ordinary member of the", html)

	def test_with_neither_it_gets_the_plain_title(self):
		html = self.render(benefits=[], membership_type="")

		self.assertIn("Certificate of Membership", html)
		self.assertIn("enrolled as a member of the", html)

	def test_an_uploaded_signature_is_printed_and_a_missing_one_leaves_the_line_blank(self):
		html = self.render(signature_left="data:image/png;base64,AAAA")

		self.assertIn('src="data:image/png;base64,AAAA"', html)
		self.assertEqual(html.count("<img"), 1)

	def test_the_enrolment_date_is_split_for_the_certificate(self):
		self.assertEqual(
			certificate._enrolled("2026-10-22"),
			{"enrolled_day": "22", "enrolled_month": "October", "enrolled_year": "2026"},
		)
		self.assertEqual(certificate._enrolled(None)["enrolled_day"], "")
		self.assertIn('20<span class="mc-fill">26</span>', self.render())

	def test_the_signatures_are_read_from_the_settings(self):
		settings_patch.install_fields()
		frappe.db.set_single_value(SETTINGS, "vmms_certificate_signatory_left", "The Governor")
		self.addCleanup(frappe.db.set_single_value, SETTINGS, "vmms_certificate_signatory_left", None)

		context = certificate._signatures(absolute_assets=False)

		self.assertEqual(context["signatory_left"], "The Governor")
		self.assertEqual(context["signature_left"], "")
