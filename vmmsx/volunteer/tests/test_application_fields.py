# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The volunteer application's data model: vocabularies, citizenship/residency,
identification, and Serving Branch defaulting.

Nothing here is mocked. Vocabularies are real `VMMS Skill` / `VMMS Motivation`
/ `VMMS Availability Slot` rows, citizenship reads the real National Society
Settings singleton, and geo comes from core's own fixtures — the same
arrangement every other suite in this module uses.
"""

import ast
from pathlib import Path

import frappe

from vmmsx.volunteer.services import application as application_service
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

SETTINGS_DOCTYPE = "National Society Settings"


def _two_countries() -> tuple[str, str]:
	rows = frappe.get_all("Country", limit=2, order_by="name", pluck="name")

	if len(rows) < 2:
		raise RuntimeError("This site needs at least two Country records for this suite to mean anything.")

	return rows[0], rows[1]


# --- 1. vocabularies are config ---------------------------------------------


class TestVocabulariesAreConfig(VolunteerTestCase):
	def test_the_seeds_installed(self):
		"""`patches.setup_volunteer_application_module` seeded a starting set."""
		self.assertTrue(frappe.db.exists("VMMS Skill", "first_aid"))
		self.assertTrue(frappe.db.exists("VMMS Motivation", "community_service"))
		self.assertTrue(frappe.db.exists("VMMS Availability Slot", "weekend_mornings"))

	def test_adding_a_skill_makes_it_selectable_with_no_code_change(self):
		"""A society writes a row; the application accepts it. That is the whole test."""
		skill = fixtures.make_skill(f"{fixtures.TEST_PREFIX}-brand-new-skill")
		profile = fixtures.make_profile("Newskill", "Applicant")

		application = fixtures.make_application(
			profile, self.society_a["ward"], skills=[{"skill": skill.name}]
		)

		self.assertEqual([row.skill for row in application.skills], [skill.name])

	def test_adding_a_motivation_and_an_availability_slot_the_same_way(self):
		motivation = fixtures.make_motivation(f"{fixtures.TEST_PREFIX}-brand-new-motivation")
		slot = fixtures.make_availability_slot(f"{fixtures.TEST_PREFIX}-brand-new-slot")
		profile = fixtures.make_profile("Newvocab", "Applicant")

		application = fixtures.make_application(
			profile,
			self.society_a["ward"],
			motivation=[{"motivation": motivation.name}],
			availability=[{"availability_slot": slot.name}],
		)

		self.assertEqual([row.motivation for row in application.motivation], [motivation.name])
		self.assertEqual([row.availability_slot for row in application.availability], [slot.name])

	def test_a_deactivated_vocabulary_entry_is_not_deleted(self):
		"""Deactivating narrows what is offered; it does not touch what already exists."""
		skill = fixtures.make_skill(f"{fixtures.TEST_PREFIX}-going-away")
		skill.is_active = 0
		skill.save()

		self.assertTrue(frappe.db.exists("VMMS Skill", skill.name))
		self.assertEqual(frappe.db.get_value("VMMS Skill", skill.name, "is_active"), 0)

	def test_languages_reuse_frappes_own_doctype(self):
		"""No VMMS Language doctype exists; the selector links straight to Language."""
		field = frappe.get_meta(fixtures.APPLICATION_DOCTYPE).get_field("languages")

		self.assertEqual(field.fieldtype, "Table MultiSelect")
		self.assertEqual(field.options, "VMMS Language Selector")
		self.assertEqual(frappe.get_meta("VMMS Language Selector").get_field("language").options, "Language")
		self.assertFalse(frappe.db.exists("DocType", "VMMS Language"))

	def test_a_language_the_site_is_not_translated_into_is_still_offered(self):
		"""`Language.enabled` is the wrong question, and the form must not ask it.

		It means "this site's interface is offered in this language". What a
		volunteer speaks is a different question, and Frappe ships its list with
		most rows off — Kiswahili among them — so filtering on the flag told a
		Kenyan applicant that half the country's language was not on the form.
		"""
		from vmmsx.api.volunteer import application_options

		disabled = frappe.get_all("Language", filters={"enabled": 0}, limit=1, pluck="name")

		if not disabled:
			self.skipTest("this site has every Language enabled, so there is nothing to prove")

		offered = {row["key"] for row in application_options()["languages"]}

		self.assertIn(disabled[0], offered)


# --- 2. structured capture is queryable -------------------------------------


class TestStructuredCaptureIsQueryable(VolunteerTestCase):
	def test_a_coordinator_can_filter_applications_by_skill(self):
		skill = fixtures.make_skill(f"{fixtures.TEST_PREFIX}-queryable-skill")
		other_skill = fixtures.make_skill(f"{fixtures.TEST_PREFIX}-other-skill")

		matching_profile = fixtures.make_profile("Matches", "Skill")
		other_profile = fixtures.make_profile("Has", "OtherSkill")

		matching = fixtures.make_application(
			matching_profile, self.society_a["ward"], skills=[{"skill": skill.name}]
		)
		fixtures.make_application(other_profile, self.society_a["ward"], skills=[{"skill": other_skill.name}])

		found = frappe.get_all(
			"VMMS Skill Selector",
			filters={"skill": skill.name, "parenttype": fixtures.APPLICATION_DOCTYPE},
			pluck="parent",
		)

		self.assertEqual(found, [matching.name])

	def test_languages_availability_and_motivation_are_each_queryable_the_same_way(self):
		slot = fixtures.make_availability_slot(f"{fixtures.TEST_PREFIX}-queryable-slot")
		profile = fixtures.make_profile("Queryable", "Availability")

		application = fixtures.make_application(
			profile, self.society_a["ward"], availability=[{"availability_slot": slot.name}]
		)

		found = frappe.get_all(
			"VMMS Availability Selector",
			filters={"availability_slot": slot.name, "parenttype": fixtures.APPLICATION_DOCTYPE},
			pluck="parent",
		)

		self.assertEqual(found, [application.name])


# --- 3. identification asymmetry --------------------------------------------


class TestIdentificationAsymmetry(VolunteerTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# Only the tests that expect submit() to actually succeed need a real,
		# resolvable workflow — engine.submit() throws for a doctype with none
		# configured at all. The refusal tests below never reach it: assert_ready()
		# throws first, inside application_service.submit(), before the engine is
		# asked anything.
		fixtures.make_workflow()
		fixtures.grant_doctype_access(fixtures.APPLICATION_DOCTYPE, fixtures.APPROVER_ROLE)
		cls.approver = fixtures.make_user("identification_approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])

	def test_submission_is_refused_without_identification(self):
		profile = fixtures.make_profile("No", "Identification")
		application = fixtures.make_application(profile, self.society_a["ward"], id_type=None, id_number=None)

		with self.assertRaises(frappe.MandatoryError):
			application_service.submit(application)

	def test_submission_is_refused_with_only_half_of_it(self):
		profile = fixtures.make_profile("Half", "Identification")
		id_type = fixtures.make_identification_type()
		application = fixtures.make_application(
			profile, self.society_a["ward"], id_type=id_type, id_number=None
		)

		with self.assertRaises(frappe.MandatoryError):
			application_service.submit(application)

	def test_submission_succeeds_and_writes_it_to_the_red_profile(self):
		profile = fixtures.make_profile("Has", "Identification")
		id_type = fixtures.make_identification_type()
		application = fixtures.make_application(
			profile, self.society_a["ward"], id_type=id_type, id_number="ID-ASYM-0001"
		)

		application_service.submit(application)

		rows = frappe.get_all(
			"Red Profile Identification",
			filters={"parent": profile, "parenttype": "Red Profile"},
			fields=["id_type", "id_number"],
		)

		self.assertEqual(rows, [{"id_type": id_type, "id_number": "ID-ASYM-0001"}])

	def test_submitting_twice_does_not_duplicate_the_row(self):
		"""`submit()` re-syncs an already-open application; the write must be idempotent."""
		profile = fixtures.make_profile("Resubmitted", "Applicant")
		id_type = fixtures.make_identification_type()
		application = fixtures.make_application(
			profile, self.society_a["ward"], id_type=id_type, id_number="ID-ASYM-0002"
		)

		application_service.submit(application)
		application.reload()
		application_service.submit(application)

		rows = frappe.get_all(
			"Red Profile Identification", filters={"parent": profile, "parenttype": "Red Profile"}
		)

		self.assertEqual(len(rows), 1)

	def test_a_red_profile_on_its_own_still_allows_none(self):
		"""The asymmetry: mandatory here, optional there. Both halves are tested."""
		profile = frappe.get_doc(
			{
				"doctype": "Red Profile",
				"first_name": "Bare",
				"last_name": "Profile",
				"email": f"bare.profile.{frappe.generate_hash(length=6)}@volunteer.test",
			}
		).insert()

		self.assertEqual(profile.identifications, [])


# --- 4. citizenship and residency -------------------------------------------


class TestCitizenshipAndResidency(VolunteerTestCase):
	def test_citizenship_defaults_from_the_societys_own_country(self):
		country, _ = _two_countries()
		frappe.db.set_single_value(SETTINGS_DOCTYPE, "country", country)
		frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)

		try:
			profile = fixtures.make_profile("Defaulted", "Citizen")
			application = frappe.get_doc(
				{
					"doctype": fixtures.APPLICATION_DOCTYPE,
					"red_profile": profile,
					"geo_node": self.society_a["ward"],
					"home_geo_node": self.society_a["ward"],
				}
			).insert()

			self.assertEqual(application.country_of_citizenship, country)
		finally:
			frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)

	def test_citizenship_is_freely_changeable(self):
		_, other_country = _two_countries()
		profile = fixtures.make_profile("Changed", "Citizen")

		application = fixtures.make_application(
			profile, self.society_a["ward"], country_of_citizenship=other_country
		)

		self.assertEqual(application.country_of_citizenship, other_country)

	def test_local_requires_home_area_not_a_country_of_residence(self):
		profile = fixtures.make_profile("Local", "Resident")

		application = fixtures.make_application(
			profile,
			self.society_a["ward"],
			residency_type="Local",
			home_geo_node=self.society_a["ward"],
		)

		self.assertEqual(application.residency_type, "Local")
		self.assertEqual(application.home_geo_node, self.society_a["ward"])
		self.assertIsNone(application.country_of_residence)
		self.assertIsNone(application.residence_address)

	def test_abroad_requires_country_and_address_not_a_home_area(self):
		_, other_country = _two_countries()
		profile = fixtures.make_profile("Abroad", "Resident")

		application = fixtures.make_application(
			profile,
			self.society_a["ward"],
			residency_type="Abroad",
			home_geo_node=None,
			country_of_residence=other_country,
			residence_address="123 Elsewhere Street",
		)

		self.assertEqual(application.residency_type, "Abroad")
		self.assertEqual(application.country_of_residence, other_country)
		self.assertEqual(application.residence_address, "123 Elsewhere Street")
		self.assertIsNone(application.home_geo_node)

	def test_abroad_cannot_submit_without_country_and_address(self):
		profile = fixtures.make_profile("Incomplete", "Abroad")
		application = fixtures.make_application(
			profile,
			self.society_a["ward"],
			residency_type="Abroad",
			home_geo_node=None,
			country_of_residence=None,
			residence_address=None,
		)

		with self.assertRaises(frappe.MandatoryError):
			application_service.submit(application)

	def test_local_cannot_submit_without_a_home_area(self):
		profile = fixtures.make_profile("Incomplete", "Local")
		application = fixtures.make_application(
			profile, self.society_a["ward"], residency_type="Local", home_geo_node=None
		)

		with self.assertRaises(frappe.MandatoryError):
			application_service.submit(application)

	def test_the_decoupling_a_local_citizen_of_elsewhere_and_an_abroad_citizen_of_here_both_save(self):
		"""Citizenship and residency are two questions, and neither implies the other."""
		home_country, elsewhere = _two_countries()

		local_foreigner = fixtures.make_profile("Local", "Foreigner")
		local_application = fixtures.make_application(
			local_foreigner,
			self.society_a["ward"],
			country_of_citizenship=elsewhere,
			residency_type="Local",
			home_geo_node=self.society_a["ward"],
		)

		abroad_citizen = fixtures.make_profile("Abroad", "Citizen")
		abroad_application = fixtures.make_application(
			abroad_citizen,
			self.society_a["ward"],
			country_of_citizenship=home_country,
			residency_type="Abroad",
			home_geo_node=None,
			country_of_residence=elsewhere,
			residence_address="1 Diaspora Way",
		)

		self.assertEqual(local_application.country_of_citizenship, elsewhere)
		self.assertEqual(local_application.residency_type, "Local")

		self.assertEqual(abroad_application.country_of_citizenship, home_country)
		self.assertEqual(abroad_application.residency_type, "Abroad")
		self.assertEqual(abroad_application.country_of_residence, elsewhere)


# --- 5. Serving Branch defaulting --------------------------------------------


class TestServingBranchDefaulting(VolunteerTestCase):
	def test_local_defaults_serving_branch_from_home_area(self):
		profile = fixtures.make_profile("Defaulting", "Serving")

		application = frappe.get_doc(
			{
				"doctype": fixtures.APPLICATION_DOCTYPE,
				"red_profile": profile,
				"country_of_citizenship": fixtures.test_country(),
				"residency_type": "Local",
				"home_geo_node": self.society_a["ward"],
			}
		).insert()

		self.assertEqual(application.geo_node, self.society_a["ward"])

	def test_a_coordinator_may_still_override_it(self):
		profile = fixtures.make_profile("Overriding", "Serving")

		application = frappe.get_doc(
			{
				"doctype": fixtures.APPLICATION_DOCTYPE,
				"red_profile": profile,
				"country_of_citizenship": fixtures.test_country(),
				"residency_type": "Local",
				"home_geo_node": self.society_a["ward"],
				"geo_node": self.society_a["other_ward"],
			}
		).insert()

		self.assertEqual(application.geo_node, self.society_a["other_ward"])

	def test_abroad_has_nothing_to_default_from_and_must_say_explicitly(self):
		_, other_country = _two_countries()
		profile = fixtures.make_profile("Abroad", "Serving")

		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": fixtures.APPLICATION_DOCTYPE,
					"red_profile": profile,
					"country_of_citizenship": fixtures.test_country(),
					"residency_type": "Abroad",
					"country_of_residence": other_country,
					"residence_address": "1 Away Street",
				}
			).insert()

	def test_abroad_saves_once_serving_branch_is_given_explicitly(self):
		_, other_country = _two_countries()
		profile = fixtures.make_profile("Abroad", "ServingExplicit")

		application = frappe.get_doc(
			{
				"doctype": fixtures.APPLICATION_DOCTYPE,
				"red_profile": profile,
				"country_of_citizenship": fixtures.test_country(),
				"residency_type": "Abroad",
				"country_of_residence": other_country,
				"residence_address": "1 Away Street",
				"geo_node": self.society_a["ward"],
			}
		).insert()

		self.assertEqual(application.geo_node, self.society_a["ward"])


# --- 6. no hardcoding --------------------------------------------------------


class TestNoHardcodedSocietyLiterals(VolunteerTestCase):
	"""Grep-shaped, and it has to catch what it claims.

	Country names, geo level names, and vocabulary keys are all society
	configuration. This scans the files this stage touched for literals that
	would mean one had leaked into executable logic — the same shape
	`test_delegation.py` already holds this module to, extended with the
	society words this stage introduces.
	"""

	SCANNED = (
		"vmmsx/volunteer/services/application.py",
		"vmmsx/volunteer/services/society.py",
		"vmmsx/vmms_volunteer/doctype/vmms_volunteer_application/vmms_volunteer_application.py",
		"vmmsx/api/volunteer.py",
		"vmmsx/api/geo.py",
	)

	# Concrete country and geo-level words that must never be compared against
	# in code. Deliberately including this suite's own fixture words: if one of
	# them ever appears in the scanned files it is a literal that leaked in from
	# a test, which is exactly as wrong as one written by hand.
	FORBIDDEN = (
		"Kenya",
		"Gambia",
		'"Region"',
		'"County"',
		'"Ward"',
		'"Branch"',
		"first_aid",
		"community_service",
	)

	def _code_only(self, path: Path) -> str:
		tree = ast.parse(path.read_text())
		docstrings = set()

		for node in ast.walk(tree):
			if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
				continue

			if node.body and isinstance(node.body[0], ast.Expr):
				value = node.body[0].value

				if isinstance(value, ast.Constant) and isinstance(value.value, str):
					docstrings.add(id(value))

		class StripDocstrings(ast.NodeTransformer):
			def visit_Expr(self, node):
				if isinstance(node.value, ast.Constant) and id(node.value) in docstrings:
					return None

				return node

		return ast.unparse(StripDocstrings().visit(tree))

	def test_none_of_the_scanned_files_name_a_literal_society_value(self):
		app_root = Path(frappe.get_app_path("vmmsx")).parent
		offenders = []

		for relative in self.SCANNED:
			path = app_root / relative
			code = self._code_only(path)

			for literal in self.FORBIDDEN:
				if literal in code:
					offenders.append(f"{relative}: {literal}")

		self.assertEqual(offenders, [], "a society-specific literal has leaked into executable logic")

	def test_the_scan_would_catch_one_that_was_really_there(self):
		"""Guard the scan itself: it must still see code, not just prose."""
		leaked = 'def f():\n\t"""Prose may say Kenya."""\n\tx = "Kenya"\n\treturn x\n'
		clean = 'def f():\n\t"""Prose may say Kenya freely."""\n\treturn 1\n'

		def code_only(source: str) -> str:
			tree = ast.parse(source)
			docstrings = {
				id(node.body[0].value)
				for node in ast.walk(tree)
				if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
				and node.body
				and isinstance(node.body[0], ast.Expr)
				and isinstance(node.body[0].value, ast.Constant)
			}

			class StripDocstrings(ast.NodeTransformer):
				def visit_Expr(self, inner):
					if isinstance(inner.value, ast.Constant) and id(inner.value) in docstrings:
						return None

					return inner

			return ast.unparse(StripDocstrings().visit(tree))

		self.assertIn("Kenya", code_only(leaked))
		self.assertNotIn("Kenya", code_only(clean))

	def test_citizenship_default_is_read_from_settings_not_a_constant(self):
		"""The positive half: the default really does come from configuration."""
		source = Path(frappe.get_app_path("vmmsx"), "volunteer", "services", "society.py").read_text()

		self.assertIn("default_citizenship_country", source)
		self.assertIn('config.settings().get("country")', source)

	def test_geo_levels_are_read_from_the_adapter_not_named(self):
		"""Home Area and Serving Branch both come from onerc_core's own ladder."""
		source = Path(frappe.get_app_path("vmmsx"), "api", "geo.py").read_text()

		self.assertIn("adapter.level_labels", source)
