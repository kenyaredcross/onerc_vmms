import frappe
from frappe.modules.patch_handler import PatchType, get_patches_from_app
from frappe.tests import IntegrationTestCase

from vmmsx.patches import install_source_professions


class TestProfessionVocabulary(IntegrationTestCase):
	def test_exported_options_are_complete_and_normalized(self):
		names = install_source_professions.profession_names()
		self.assertEqual(len(names), 684)
		self.assertEqual(len({name.casefold() for name in names}), 684)
		self.assertTrue(all(name == " ".join(name.split()) for name in names))
		for name in ("Office Assistant", "Psychological Counsellor", "Supply. Chain Management"):
			self.assertIn(name, names)

	def test_seed_adds_missing_options_to_a_nonempty_register(self):
		custom = frappe.get_doc({"doctype": "Profession", "__newname": "_Test Custom Profession"}).insert()
		install_source_professions.execute()
		actual = set(frappe.get_all("Profession", pluck="name"))
		self.assertTrue(set(install_source_professions.profession_names()) <= actual)
		self.assertIn(custom.name, actual)

	def test_seed_is_idempotent_and_preserves_existing_records(self):
		install_source_professions.execute()
		before = {row.name: row.modified for row in frappe.get_all("Profession", fields=["name", "modified"])}
		install_source_professions.execute()
		after = {row.name: row.modified for row in frappe.get_all("Profession", fields=["name", "modified"])}
		self.assertEqual(before, after)

	def test_patch_runs_for_both_migrate_and_fresh_install(self):
		self.assertIn(
			"vmmsx.patches.install_source_professions",
			get_patches_from_app("vmmsx", PatchType.post_model_sync),
		)
