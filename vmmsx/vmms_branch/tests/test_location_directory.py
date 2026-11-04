# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The public directory's county and headquarters tags, and its map.

Kept outside the doctype folder: a doctype's own test module makes the
doctype's test records first, and none of that is needed here.
"""

import unittest.mock

import frappe

from vmmsx.api import locations as api
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

LOCATION_DOCTYPE = "VMMS Branch Location"


class TestLocationDirectory(DeploymentTestCase):
	def make(self, geo_node: str):
		return frappe.get_doc(
			{"doctype": LOCATION_DOCTYPE, "location_name": "Office", "geo_node": geo_node, "is_published": 1}
		).insert()

	def row(self, location) -> dict:
		return next(row for row in api.published()["locations"] if row["name"] == location.name)

	def test_a_location_is_tagged_with_its_county(self):
		"""The county is the place at the registration level that the location
		sits at or under: here the branch level, for an office at a post."""
		fixtures.set_volunteer_anchor_level(self.society_a["levels"]["branch"])
		location = self.make(self.society_a["post"])

		row = self.row(location)

		self.assertEqual((row["county"], row["is_headquarters"]), (self.society_a["branch"], False))

	def test_a_location_at_the_top_is_headquarters(self):
		location = self.make(self.society_a["region"])

		row = self.row(location)

		self.assertTrue(row["is_headquarters"])
		self.assertEqual(row["county"], "")

	def test_the_county_map_is_served_to_a_guest_without_figures(self):
		with fixtures.acting_as("Guest"):
			answer = api.county_map()

		self.assertIn("shapes", answer)
		self.assertFalse({"volunteers", "members", "waiting"} & set(answer))

	def test_a_location_between_the_top_and_the_counties_is_regional(self):
		"""Highland is the top here, so a regional office needs a level between
		it and the counties: the branch level is the region, the post the county."""
		fixtures.set_volunteer_anchor_level(self.society_a["levels"]["post"])
		location = self.make(self.society_a["branch"])

		row = self.row(location)

		self.assertTrue(row["is_regional"])
		self.assertEqual((row["region"], row["county"]), (self.society_a["branch"], ""))

	def test_the_map_says_which_region_each_county_is_in(self):
		fixtures.set_volunteer_anchor_level(self.society_a["levels"]["post"])

		from vmmsx.analytics.services import oversight

		with unittest.mock.patch.object(oversight, "national_area", return_value=self.society_a["region"]):
			regions = api.county_map()["regions"]

		self.assertEqual(regions[self.society_a["post"]], self.society_a["branch"])
