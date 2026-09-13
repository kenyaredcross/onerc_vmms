# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

import uuid
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.member.services.society import ANCHOR_LEVEL_FIELD as MEMBER_ANCHOR_FIELD
from vmmsx.setup import wizard
from vmmsx.volunteer.services.society import ANCHOR_LEVEL_FIELD as VOLUNTEER_ANCHOR_FIELD


class TestNationalSocietySetupWizard(IntegrationTestCase):
	def test_setup_writes_core_identity_levels_and_shared_application_anchor(self):
		token = uuid.uuid4().hex[:8]
		top = f"Wizard Country {token}"
		anchor = f"Wizard County {token}"

		wizard.setup_national_society(
			{
				"vmms_organization_name": f"Test Society {token}",
				"vmms_organization_short_name": f"TS{token[:3]}",
				"country": "Tanzania",
				"language": "English",
				"vmms_logo": "/files/test-society-logo.png",
				"vmms_geo_levels_json": frappe.as_json([{"label": top}, {"label": anchor}]),
				"vmms_application_anchor_order": "2",
			}
		)

		settings = frappe.get_single(wizard.SETTINGS_DOCTYPE)
		anchor_key = frappe.db.get_value("Geo Level", {"geo_level_name": anchor}, "name")

		self.assertEqual(settings.organization_name, f"Test Society {token}")
		self.assertEqual(settings.primary_language, "en")
		self.assertEqual(settings.logo, "/files/test-society-logo.png")
		self.assertEqual(settings.get(MEMBER_ANCHOR_FIELD), anchor_key)
		self.assertEqual(settings.get(VOLUNTEER_ANCHOR_FIELD), anchor_key)
		self.assertEqual(frappe.db.get_value("Geo Level", {"geo_level_name": top}, "requires_parent"), 0)
		self.assertEqual(frappe.db.get_value("Geo Level", anchor_key, "requires_parent"), 1)

	def test_at_least_one_level_is_required(self):
		with patch.object(wizard, "_already_configured", return_value=False):
			with self.assertRaises(frappe.ValidationError):
				wizard.setup_national_society({})

	def test_a_completed_vmms_stage_can_be_resumed_without_reposting_its_inputs(self):
		with patch.object(wizard, "_already_configured", return_value=True):
			wizard.setup_national_society({})
