import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.api import registration
from vmmsx.patches import install_blood_groups
from vmmsx.registration.tests import fixtures

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestBloodGroups(IntegrationTestCase):
	def test_seed_is_idempotent_and_exposes_all_old_options(self):
		install_blood_groups.execute()
		before = {
			row.name: row.modified
			for row in frappe.get_all(install_blood_groups.DOCTYPE, fields=["name", "modified"])
		}
		install_blood_groups.execute()
		after = {
			row.name: row.modified
			for row in frappe.get_all(install_blood_groups.DOCTYPE, fields=["name", "modified"])
		}
		self.assertEqual(before, after)
		self.assertTrue(
			set(install_blood_groups.BLOOD_GROUPS) <= set(registration.identity_options()["blood_groups"])
		)

	def test_legacy_profile_values_are_retained_when_the_field_becomes_a_link(self):
		profile = fixtures.make_profile("Blood", "Group")
		frappe.db.set_value("Red Profile", profile, "vmms_blood_group", "Legacy result")
		install_blood_groups.execute()
		self.assertTrue(frappe.db.exists(install_blood_groups.DOCTYPE, "Legacy result"))
		self.assertEqual(frappe.db.get_value("Red Profile", profile, "vmms_blood_group"), "Legacy result")
		field = frappe.get_meta("Red Profile").get_field("vmms_blood_group")
		self.assertEqual((field.fieldtype, field.options), ("Link", install_blood_groups.DOCTYPE))

	def test_profile_accepts_configured_choices_and_rejects_unknown_new_values(self):
		install_blood_groups.execute()
		profile = frappe.get_doc("Red Profile", fixtures.make_profile("Blood", "Validation"))
		profile.vmms_blood_group = "A+"
		profile.save()
		profile.reload()
		self.assertEqual(profile.vmms_blood_group, "A+")
		profile.vmms_blood_group = "Not a configured blood group"
		with self.assertRaises(frappe.LinkValidationError):
			profile.save()
