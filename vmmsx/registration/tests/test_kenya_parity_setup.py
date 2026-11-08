import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.registration.services import parity
from vmmsx.registration.tests import fixtures
from vmmsx.setup.registration_parity import (
	ID_PATTERNS,
	configure_kenya,
	drop_region_prefix,
	install_kenya_vocabularies,
)

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


class TestKenyaVocabularies(IntegrationTestCase):
	def test_the_old_sites_picker_values_are_installed_once(self):
		frappe.set_user("Administrator")
		install_kenya_vocabularies()

		for label in ("Health", "Nursing Council practicing licence", "OFA CERTFICATE", "Other"):
			self.assertTrue(frappe.db.exists("Personnel License Type", label), label)
		for code in ("kik", "luo", "kam", "oth", "ara", "rwa", "dad"):
			self.assertTrue(frappe.db.exists("Language", code), code)
		self.assertTrue(frappe.db.exists("Disability", "None"))
		self.assertTrue(frappe.db.exists("Profession", "Actuary"))
		for key, label in (("nemis_number", "NEMIS Number"), ("millitary_id", "Millitary ID")):
			self.assertEqual(
				frappe.db.get_value("Identification Type", key, "identification_type_name"), label
			)
			self.assertEqual(
				frappe.db.get_value("Identification Type", key, parity.ID_PATTERN_FIELD), ID_PATTERNS[key]
			)

		self.assertEqual(
			frappe.get_all(
				"VMMS Education Level", filters={"is_active": 1}, order_by="sequence asc", pluck="level_name"
			),
			["Primary", "Secondary / High School", "Undergraduate", "Graduate", "Postgraduate", "Others"],
		)

		again = install_kenya_vocabularies()
		self.assertEqual(set(again.values()), {0})

	def test_levels_off_the_old_list_are_switched_off_not_deleted(self):
		frappe.set_user("Administrator")
		if not frappe.db.exists("VMMS Education Level", "diploma"):
			frappe.get_doc(
				{
					"doctype": "VMMS Education Level",
					"level_key": "diploma",
					"level_name": "Diploma",
					"is_active": 1,
				}
			).insert()
		install_kenya_vocabularies()
		self.assertEqual(frappe.db.get_value("VMMS Education Level", "diploma", "is_active"), 0)

	def test_new_languages_are_not_offered_as_interface_languages(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Language", {"name": "kik"})
		install_kenya_vocabularies()
		self.assertEqual(frappe.db.get_value("Language", "kik", "enabled"), 0)

	def test_regions_lose_the_krcs_prefix_and_keep_their_key(self):
		frappe.set_user("Administrator")
		if not frappe.db.exists("Geo Level", "region"):
			frappe.get_doc(
				{
					"doctype": "Geo Level",
					"geo_level_key": "region",
					"geo_level_name": "Region",
					"geo_level_order": 2,
					"requires_parent": 0,
				}
			).insert()

		def region(label):
			return (
				frappe.get_doc({"doctype": "Geo Node", "geo_node_name": label, "geo_level": "region"})
				.insert()
				.name
			)

		coast = region("KRCS Regtest Coast Region")
		clash = region("KRCS Regtest Lake")
		holder = region("Regtest Lake")

		result = drop_region_prefix()

		self.assertIn(
			{"name": coast, "from": "KRCS Regtest Coast Region", "to": "Regtest Coast Region"},
			result["renamed"],
		)
		self.assertEqual(frappe.db.get_value("Geo Node", coast, "geo_node_name"), "Regtest Coast Region")
		self.assertIn({"name": clash, "label": "KRCS Regtest Lake", "taken_by": holder}, result["skipped"])
		self.assertEqual(frappe.db.get_value("Geo Node", clash, "geo_node_name"), "KRCS Regtest Lake")
		self.assertEqual(drop_region_prefix()["renamed"], [])
