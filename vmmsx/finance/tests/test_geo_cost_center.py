"""ERPNext Cost Centers follow child Geo Nodes without moving posted activity."""

import frappe
from frappe.tests import IntegrationTestCase
from onerc_core.geo.tests import fixtures as geo_fixtures

from vmmsx.finance.services import geo_cost_center
from vmmsx.setup.geo_cost_center_fields import GROUP_FIELD, POSTING_FIELD

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestGeoCostCenters(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		companies = frappe.get_all("Company", filters={"is_group": 0}, pluck="name", limit=1)
		if not companies:
			raise AssertionError("Geo Cost Center integration tests need an ERPNext Company")
		cls.company = companies[0]
		frappe.db.set_single_value("Global Defaults", "default_company", cls.company)
		cls.root_cc = geo_cost_center._root(cls.company)
		key = f"VMMS-CC-{frappe.generate_hash(length=7)}"
		cls.levels = geo_fixtures.make_levels(key, ["National", "Region", "Branch"])
		cls.national = geo_fixtures.make_node("Cost Center Test National", cls.levels[0], is_group=True)

	def _node(self, label, level, parent, is_group=False):
		return frappe.get_doc(
			"Geo Node",
			geo_fixtures.make_node(label, level, parent, is_group=is_group),
		)

	def test_national_uses_company_root_and_child_gets_group_and_posting_leaf(self):
		national = frappe.get_doc("Geo Node", self.national)
		self.assertFalse(national.get(GROUP_FIELD))
		self.assertFalse(national.get(POSTING_FIELD))

		region = self._node("Region A", self.levels[1], self.national, is_group=True)
		group = frappe.get_doc("Cost Center", region.get(GROUP_FIELD))
		own = frappe.get_doc("Cost Center", region.get(POSTING_FIELD))
		self.assertEqual(group.company, self.company)
		self.assertEqual(group.parent_cost_center, self.root_cc)
		self.assertTrue(group.is_group)
		self.assertEqual(own.parent_cost_center, group.name)
		self.assertFalse(own.is_group)

		region.save()
		region.reload()
		self.assertEqual(region.get(GROUP_FIELD), group.name)
		self.assertEqual(region.get(POSTING_FIELD), own.name)
		self.assertEqual(frappe.db.count("Cost Center", {"cost_center_name": f"VMMS {region.name} Group"}), 1)

	def test_branch_can_be_added_below_region_and_reparented(self):
		first = self._node("Region B", self.levels[1], self.national, is_group=True)
		second = self._node("Region C", self.levels[1], self.national, is_group=True)
		branch = self._node("Branch B", self.levels[2], first.name)
		self.assertEqual(
			frappe.db.get_value("Cost Center", branch.get(GROUP_FIELD), "parent_cost_center"),
			first.get(GROUP_FIELD),
		)

		branch.parent_geo_node = second.name
		branch.save()
		self.assertEqual(
			frappe.db.get_value("Cost Center", branch.get(GROUP_FIELD), "parent_cost_center"),
			second.get(GROUP_FIELD),
		)
		self.assertEqual(
			frappe.db.get_value("Cost Center", branch.get(POSTING_FIELD), "parent_cost_center"),
			branch.get(GROUP_FIELD),
		)

	def test_deleting_an_empty_child_removes_its_cost_centers(self):
		region = self._node("Region D", self.levels[1], self.national, is_group=True)
		group, own = region.get(GROUP_FIELD), region.get(POSTING_FIELD)
		frappe.delete_doc("Geo Node", region.name)
		self.assertFalse(frappe.db.exists("Cost Center", own))
		self.assertFalse(frappe.db.exists("Cost Center", group))
