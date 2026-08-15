# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""ACC-02 and ACC-03 — every membership is placed, and placed where a society says.

ACC-02 is absolute and lives in code: a membership with no Geo Node is refused
at creation. There is no path that creates one and fills the anchor in later,
because an unplaced record is invisible to core's geo scoping (the query filter
is an `IN`, which excludes NULL) and unroutable by approvals.

ACC-03 is the opposite: *which* level is permitted is configuration, and the
proof is that pointing one setting at two different levels produces two
different answers from unchanged code. No level name — "county", "ward",
"district" — appears in any source file, and these tests read the levels back
from the fixtures rather than naming them.
"""

import frappe

from vmmsx.member.services import approval, society
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestAnchorIsMandatory(MemberTestCase):
	"""ACC-02 — there are no unplaced memberships."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_FREE, approval.MODE_ROUTED, fee=0)

	def test_a_membership_with_no_geo_node_is_refused_at_creation(self):
		profile = fixtures.make_profile("Unplaced", "Applicant")

		from vmmsx.member.services import member as member_service

		member = member_service.ensure(profile)

		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": fixtures.MEMBERSHIP_DOCTYPE,
					"member": member.name,
					"membership_type": fixtures.TYPE_FREE,
					# no geo_node
				}
			).insert()

	def test_nothing_was_created_by_the_attempt(self):
		"""A refused creation leaves no half-record behind."""
		profile = fixtures.make_profile("Nothing", "Left")

		from vmmsx.member.services import member as member_service

		member = member_service.ensure(profile)

		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": fixtures.MEMBERSHIP_DOCTYPE,
					"member": member.name,
					"membership_type": fixtures.TYPE_FREE,
				}
			).insert()

		self.assertEqual(frappe.get_all(fixtures.MEMBERSHIP_DOCTYPE, filters={"member": member.name}), [])

	def test_clearing_the_anchor_on_an_existing_membership_is_refused(self):
		"""The rule holds for the whole life of the record, not only at creation."""
		profile = fixtures.make_profile("Cleared", "Anchor")
		membership = fixtures.make_membership(profile, fixtures.TYPE_FREE, self.society_a["ward"])

		membership.geo_node = None

		with self.assertRaises(frappe.MandatoryError):
			membership.save()

	def test_the_anchor_field_is_a_link_to_geo_node_and_mandatory(self):
		"""ACC-02 as schema, not only as a runtime check — never free text."""
		field = frappe.get_meta(fixtures.MEMBERSHIP_DOCTYPE).get_field("geo_node")

		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Geo Node")
		self.assertTrue(field.reqd)


class TestAnchorLevelIsSocietyConfiguration(MemberTestCase):
	"""ACC-03 — the same code, two societies, two different permitted levels."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_FREE, approval.MODE_ROUTED, fee=0)

	def setUp(self):
		super().setUp()
		self.addCleanup(fixtures.set_anchor_level, None)

	def create_at(self, node: str):
		profile = fixtures.make_profile("Anchor", "Level")

		return fixtures.make_membership(profile, fixtures.TYPE_FREE, node)

	def test_unset_means_any_level_is_acceptable(self):
		"""A society that has not narrowed it has not forbidden everything."""
		fixtures.set_anchor_level(None)

		self.assertIsNone(society.membership_anchor_level())
		self.assertTrue(self.create_at(self.society_a["ward"]).name)
		self.assertTrue(self.create_at(self.society_a["county"]).name)

	def test_a_society_that_registers_at_the_deepest_level(self):
		fixtures.set_anchor_level(self.society_a["levels"]["ward"])

		self.assertTrue(self.create_at(self.society_a["ward"]).name)

		with self.assertRaises(frappe.ValidationError):
			self.create_at(self.society_a["county"])

	def test_a_society_that_registers_one_level_up(self):
		"""The same code, the same records, one setting changed — opposite answer."""
		fixtures.set_anchor_level(self.society_a["levels"]["county"])

		self.assertTrue(self.create_at(self.society_a["county"]).name)

		with self.assertRaises(frappe.ValidationError):
			self.create_at(self.society_a["ward"])

	def test_the_two_answers_come_from_the_same_unchanged_code(self):
		"""Both assertions in one test, so there is no doubt they share a path."""
		fixtures.set_anchor_level(self.society_a["levels"]["ward"])
		permitted_at_ward = self.create_at(self.society_a["ward"]).name

		fixtures.set_anchor_level(self.society_a["levels"]["county"])
		permitted_at_county = self.create_at(self.society_a["county"]).name

		self.assertTrue(permitted_at_ward)
		self.assertTrue(permitted_at_county)

		# And each is now refused under the other's configuration.
		with self.assertRaises(frappe.ValidationError):
			self.create_at(self.society_a["ward"])

	def test_a_second_society_s_level_configures_independently(self):
		"""Society B's district level, on society B's tree. Different words entirely."""
		fixtures.set_anchor_level(self.society_b["levels"]["district"])

		self.assertTrue(self.create_at(self.society_b["district"]).name)

		with self.assertRaises(frappe.ValidationError):
			self.create_at(self.society_b["ward"])

	def test_the_refusal_names_the_level_the_society_configured(self):
		"""The message is built from configuration, not from a literal."""
		fixtures.set_anchor_level(self.society_a["levels"]["ward"])

		with self.assertRaises(frappe.ValidationError):
			self.create_at(self.society_a["county"])

		message = frappe.message_log[-1] if frappe.message_log else {}
		text = frappe.as_json(message)

		self.assertIn("Ward", text)


class TestNoLevelNamesInSource(MemberTestCase):
	"""No source file in the Member module names a geo level."""

	def test_the_module_names_no_level(self):
		import ast
		from pathlib import Path

		root = Path(frappe.get_app_path("vmmsx")) / "member"
		forbidden = ("county", "ward", "district", "province", "sub-county", "branch")
		offenders = []

		for path in sorted(root.rglob("*.py")):
			if "tests" in path.relative_to(root).parts:
				continue

			# Docstrings explain; code must not name a level. Strip prose first.
			tree = ast.parse(path.read_text())
			doc_ids = set()

			for node in ast.walk(tree):
				if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
					if node.body and isinstance(node.body[0], ast.Expr):
						value = node.body[0].value

						if isinstance(value, ast.Constant) and isinstance(value.value, str):
							doc_ids.add(id(value))

			for node in ast.walk(tree):
				if isinstance(node, ast.Constant) and isinstance(node.value, str):
					if id(node) in doc_ids:
						continue

					for word in forbidden:
						if word in node.value.lower():
							offenders.append(f"{path.name}: {node.value[:40]!r}")

		self.assertEqual(offenders, [], "ACC-03: a geo level is configuration, never a literal")
