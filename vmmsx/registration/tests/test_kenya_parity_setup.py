import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.registration.tests import fixtures
from vmmsx.setup.registration_parity import configure_kenya

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestKenyaRegistrationSetup(IntegrationTestCase):
	def test_setup_keeps_the_observed_plan_age_bands_and_benefits(self):
		frappe.set_user("Administrator")
		settings = frappe.get_single("National Society Settings")
		settings.organization_name = "Registration parity test society"
		settings.organization_short_name = "PARITY"
		settings.country = "Kenya"
		settings.primary_language = "en"
		fixtures.make_role(fixtures.APPROVER_ROLE)
		settings.vmms_volunteer_scope_role = fixtures.APPROVER_ROLE
		settings.vmms_membership_scope_role = fixtures.APPROVER_ROLE
		settings.save()
		mapping = {
			label: f"REGTEST-kenya-{index}"
			for index, label in enumerate(
				["Youth In School", "Youth Out Of School", "Ordinary Member", "Life Member"]
			)
		}
		# Mapping isolates these seed records from any other test suite's plan names.
		result = configure_kenya(mapping)
		self.assertEqual(len(result["plans_created"]), 4)
		self.assertTrue(frappe.db.exists("Identification Type", "nemis_number"))
		self.assertTrue(frappe.db.exists("VMMS Driving Licence Class", "C2/C"))
		school = frappe.get_doc("VMMS Membership Type", mapping["Youth In School"])
		self.assertEqual((school.fee_amount, school.lower_age_limit, school.upper_age_limit), (100, 0, 18))
		self.assertEqual(school.billing_cycle, "Yearly")
		self.assertEqual(len(school.benefits), 3)
		life = frappe.get_doc("VMMS Membership Type", mapping["Life Member"])
		self.assertTrue(life.is_lifetime)
		self.assertEqual(len(life.benefits), 5)
		school.fee_amount = 123
		school.save()
		again = configure_kenya(mapping)
		self.assertEqual(again["plans_created"], [])
		self.assertEqual(frappe.db.get_value("VMMS Membership Type", school.name, "fee_amount"), 123)
		self.assertEqual(
			frappe.db.get_value("Supporting Document Type", "Good Conduct", "vmms_required_for_volunteers"), 1
		)
		self.assertEqual(
			frappe.db.get_value("Supporting Document Type", "CV", "vmms_required_for_volunteers"), 0
		)
		self.assertEqual(frappe.db.get_single_value("National Society Settings", "vmms_volunteer_min_age"), 7)

		self.assertEqual(
			frappe.db.get_single_value("National Society Settings", "vmms_volunteer_max_age"), 150
		)
		self.assertEqual(frappe.db.get_single_value("National Society Settings", "vmms_member_min_age"), 7)
		self.assertEqual(frappe.db.get_single_value("National Society Settings", "vmms_member_max_age"), 150)
