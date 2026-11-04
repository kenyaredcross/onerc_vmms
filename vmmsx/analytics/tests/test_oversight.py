# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Region and National tabs: what they lay out, what they count, who opens them.

The fixture tree is read as a small country: Highland at the top, Karura and
Limuru as its regions, and the posts beneath them as the counties volunteers
register at. Society B's Delta is another country entirely, so a count that
leaks across the top of the tree shows up as a wrong number.
"""

import unittest
from unittest.mock import patch

import frappe
from frappe.utils import add_years, nowdate

from vmmsx.analytics.services import oversight
from vmmsx.api import oversight as api
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase
from vmmsx.setup import regional_oversight
from onerc_core.geo.tests import fixtures as geo_fixtures

HEAD_ROLE = f"{fixtures.TEST_PREFIX} Head of Region"

# A Head of Region reads through onerc_core's reading role, which is applied per
# site from deploy/onerc_core-read-role/ rather than committed to onerc_core.
needs_reading_role = unittest.skipUnless(
	regional_oversight.core_reads_through_oversight_role(),
	"onerc_core has no reading role here: apply deploy/onerc_core-read-role/",
)
ASSET_DOCTYPE = "VMMS Branch Asset"


class TestOversight(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		a = cls.society_a
		cls.country = a["region"]
		cls.karura = a["branch"]
		cls.limuru = a["other_branch"]
		cls.ruaka = a["post"]
		cls.tigoni = a["other_post"]
		cls.banana = geo_fixtures.make_node("Banana", a["levels"]["post"], cls.karura)

		# The setting the reading role hangs off. `after_migrate` makes the field
		# on a real site; here it is made the same way, then pointed at a test role.
		regional_oversight.install()
		cls.previous_head_role = regional_oversight.role()
		fixtures.make_role(HEAD_ROLE)
		fixtures._set_setting(regional_oversight.ROLE_FIELD, HEAD_ROLE)
		# Another society's volunteer, placed before the anchor level is set: it
		# sits at a level of its own society's ladder, not this one's.
		cls.abroad = fixtures.make_volunteer(fixtures.make_profile("Delta", "Person"), cls.society_b["ward"]).name
		fixtures.set_volunteer_anchor_level(a["levels"]["post"])

		fixtures.grant_doctype_access(fixtures.VOLUNTEER_DOCTYPE, fixtures.VOLUNTEER_SCOPE_ROLE)
		cls.read_only(fixtures.VOLUNTEER_DOCTYPE)
		cls.read_only(ASSET_DOCTYPE)

		cls.ruaka_people = [
			fixtures.make_volunteer(fixtures.make_profile("Wanjiru", "Kamau", gender="Female", date_of_birth=add_years(nowdate(), -25)), cls.ruaka).name,
			fixtures.make_volunteer(fixtures.make_profile("Otieno", "Odhiambo", gender="Male", date_of_birth=add_years(nowdate(), -40)), cls.ruaka).name,
		]
		cls.banana_person = fixtures.make_volunteer(fixtures.make_profile("Achieng", "Auma", gender="Female"), cls.banana).name
		cls.tigoni_person = fixtures.make_volunteer(fixtures.make_profile("Kiprop", "Rotich"), cls.tigoni).name

		# An asset starts at zero and is stocked through its own transactions;
		# what is counted here is the result, so it is written directly.
		tents = frappe.get_doc(
			{"doctype": ASSET_DOCTYPE, "asset_name": "Tents", "geo_node": cls.ruaka, "is_active": 1}
		).insert(ignore_permissions=True)
		frappe.db.set_value(ASSET_DOCTYPE, tents.name, {"total_quantity": 10, "available_quantity": 7})

		cls.head = cls.viewer("oversight-head", HEAD_ROLE, cls.karura)
		cls.national = cls.viewer("oversight-national", fixtures.VOLUNTEER_SCOPE_ROLE, cls.country)
		cls.county = cls.viewer("oversight-county", fixtures.VOLUNTEER_SCOPE_ROLE, cls.ruaka)
		cls.nobody = fixtures.make_user("oversight-nobody")

	@classmethod
	def tearDownClass(cls):
		fixtures._set_setting(regional_oversight.ROLE_FIELD, cls.previous_head_role)
		super().tearDownClass()

	@classmethod
	def read_only(cls, doctype: str) -> None:
		from frappe.permissions import add_permission

		if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": HEAD_ROLE}):
			add_permission(doctype, HEAD_ROLE, 0)

		frappe.clear_cache(doctype=doctype)

	def row(self, overview: dict, name: str) -> dict:
		return next(row for row in overview["rows"] if row["name"] == name)

	# --- the region -----------------------------------------------------------

	@needs_reading_role
	def test_a_region_is_laid_out_county_by_county(self):
		with fixtures.acting_as(self.head):
			result = oversight.overview(self.karura)

		self.assertEqual([row["name"] for row in result["rows"]], [self.banana, self.ruaka])
		self.assertEqual(self.row(result, self.ruaka)["volunteers"], 2)
		self.assertEqual(self.row(result, self.banana)["volunteers"], 1)
		self.assertEqual(result["totals"]["volunteers"], 3)

	@needs_reading_role
	def test_materials_count_what_is_lent_out(self):
		with fixtures.acting_as(self.head):
			ruaka = self.row(oversight.overview(self.karura), self.ruaka)

		self.assertEqual((ruaka["materials_items"], ruaka["materials_total"], ruaka["materials_lent"]), (1, 10, 3))

	def test_the_head_of_region_cannot_count_a_region_they_do_not_hold(self):
		with fixtures.acting_as(self.head):
			result = oversight.overview(self.limuru)

		self.assertEqual(result["totals"]["volunteers"], 0)

	def test_a_head_of_region_is_told_when_their_access_is_not_on(self):
		with patch.object(regional_oversight, "core_reads_through_oversight_role", return_value=False):
			self.assertTrue(oversight.access_pending(self.head))
			self.assertFalse(oversight.access_pending(self.county))
			self.assertFalse(oversight.access_pending("Administrator"))

		with patch.object(regional_oversight, "core_reads_through_oversight_role", return_value=True):
			self.assertFalse(oversight.access_pending(self.head))

	def test_counts_inside_a_region_are_still_the_callers_scope(self):
		with fixtures.acting_as(self.county):
			result = oversight.overview(self.karura)

		self.assertEqual(self.row(result, self.ruaka)["volunteers"], 2)
		self.assertEqual(self.row(result, self.banana)["volunteers"], 0)

	@needs_reading_role
	def test_a_selected_county_gets_its_breakdowns(self):
		with fixtures.acting_as(self.head):
			result = oversight.overview(self.karura, self.ruaka)

		people = result["breakdown"]["volunteers"]
		self.assertEqual(result["selected"]["name"], self.ruaka)
		self.assertEqual(people["total"], 2)
		self.assertEqual({row["label"]: row["count"] for row in people["gender"]}, {"Female": 1, "Male": 1})
		ages = {row["label"]: row["count"] for row in people["age"]}
		self.assertEqual((ages["18–35"], ages["36–59"]), (1, 1))

	@needs_reading_role
	def test_a_place_outside_the_area_selects_nothing(self):
		with fixtures.acting_as(self.head):
			result = oversight.overview(self.karura, self.tigoni)

		self.assertIsNone(result["selected"])
		self.assertEqual(result["breakdown"]["volunteers"]["total"], 3)

	def test_an_area_that_is_a_county_is_drawn_as_that_county(self):
		with fixtures.acting_as(self.head):
			result = oversight.overview(self.ruaka)

		self.assertEqual([row["name"] for row in result["rows"]], [self.ruaka])

	# --- the country ----------------------------------------------------------

	def test_the_country_is_rolled_up_by_region(self):
		with fixtures.acting_as(self.national):
			result = oversight.overview(self.country)

		self.assertEqual({row["name"] for row in result["rows"]}, {self.karura, self.limuru})
		self.assertEqual(self.row(result, self.karura)["volunteers"], 3)
		self.assertEqual(self.row(result, self.limuru)["volunteers"], 1)
		self.assertEqual(len(result["units"]), 3)
		self.assertEqual(result["totals"]["volunteers"], 4)

	def test_another_country_is_never_counted(self):
		with fixtures.acting_as(self.national):
			result = oversight.overview(self.country)

		self.assertEqual(result["breakdown"]["volunteers"]["total"], 4)

	def test_a_region_without_a_head_is_flagged_nationally(self):
		with fixtures.acting_as(self.national):
			attention = oversight.overview(self.country)["attention"]

		self.assertEqual([row["name"] for row in attention["without_head"]], [self.limuru])

	# --- who opens which tab --------------------------------------------------------

	def test_a_head_of_region_opens_their_region_only(self):
		self.assertEqual([row["name"] for row in oversight.regions_for(self.head)], [self.karura])
		self.assertFalse(oversight.national_allowed(self.head))

		with fixtures.acting_as(self.head):
			self.assertEqual(api.region(area=self.limuru)["area"]["name"], self.karura)

			with self.assertRaises(frappe.PermissionError):
				api.national()

	def test_national_staff_may_open_any_region(self):
		self.assertTrue(oversight.national_allowed(self.national))
		self.assertTrue({self.karura, self.limuru} <= {row["name"] for row in oversight.regions_for(self.national)})

	def test_a_county_reader_opens_neither(self):
		for user in (self.county, self.nobody):
			self.assertEqual(oversight.regions_for(user), [])
			self.assertFalse(oversight.national_allowed(user))

			with fixtures.acting_as(user), self.assertRaises(frappe.PermissionError):
				api.region()

	def test_the_console_draws_the_tabs_for_the_right_people(self):
		from vmmsx.staff.services import console

		self.assertIn("region", console.visible(self.head))
		self.assertNotIn("national", console.visible(self.head))
		self.assertIn("national", console.visible(self.national))
		self.assertNotIn("region", console.visible(self.county))
