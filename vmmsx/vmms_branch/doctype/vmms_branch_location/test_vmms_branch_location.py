# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A location's coordinates, and the public read boundary over it.

Two things are worth a test here and the rest of the doctype is fields.

**Half a coordinate is refused**, because Frappe stores an empty Float as `0.0`
rather than as nothing, so a latitude typed in with the longitude left blank
would be drawn confidently in the Gulf of Guinea rather than not drawn at all.

**`is_published` is the whole of the guest-read rule.** `api/locations.py::
published` is this app's third `allow_guest` endpoint, and what stops it
disclosing an office a society has not published is one filter and one DTO. Both
are asserted, because the endpoint reads with permissions bypassed and those two
are therefore the only things standing between a draft address and the public.
"""

import frappe

from vmmsx.api import locations as api
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

LOCATION_DOCTYPE = "VMMS Branch Location"


class TestBranchLocation(DeploymentTestCase):
	def setUp(self):
		super().setUp()

		self.branch = self.society_a["branch"]

	def make(self, **overrides):
		values = {
			"doctype": LOCATION_DOCTYPE,
			"location_name": "Branch office",
			"geo_node": self.branch,
			"address": "Off the main road",
			"notes": "Keys are with the caretaker.",
		}
		values.update(overrides)

		return frappe.get_doc(values).insert()

	# --- coordinates ------------------------------------------------------

	def test_a_pair_is_accepted(self):
		location = self.make(latitude=-1.2921, longitude=36.8219)

		self.assertTrue(location.has_point())

	def test_neither_is_accepted(self):
		location = self.make()

		self.assertFalse(location.has_point())

	def test_a_latitude_without_a_longitude_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.make(latitude=-1.2921)

	def test_a_longitude_without_a_latitude_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.make(longitude=36.8219)

	def test_a_latitude_off_the_earth_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.make(latitude=118.0, longitude=36.8219)

	def test_a_longitude_off_the_earth_is_refused(self):
		"""Almost always the two entered the wrong way round, which is a valid
		pair of numbers and a place in the wrong country."""
		with self.assertRaises(frappe.ValidationError):
			self.make(latitude=36.8219, longitude=-190.0)

	# --- the public read --------------------------------------------------

	def names(self, answer) -> list[str]:
		"""The docnames in an answer.

		Assertions here ask about membership rather than emptiness, because
		Frappe rolls the test transaction back once per class: a location
		another method published is still there when this one runs.
		"""
		return [row["name"] for row in answer["locations"]]

	def test_an_unpublished_location_is_not_served(self):
		location = self.make(is_published=0)

		self.assertNotIn(location.name, self.names(api.published()))

	def test_a_published_location_is_served(self):
		location = self.make(is_published=1, latitude=-1.2921, longitude=36.8219)

		self.assertIn(location.name, self.names(api.published()))

	def test_the_public_dto_carries_no_internal_notes(self):
		"""Absent rather than blanked, so a field added to the doctype later is
		not silently added to a public API."""
		location = self.make(is_published=1)

		row = next(row for row in api.published()["locations"] if row["name"] == location.name)

		self.assertNotIn("notes", row)
		self.assertNotIn("is_published", row)

	def test_bounds_are_none_when_nothing_is_pinned(self):
		"""No default centre and no fallback country: a map centred on a guess
		says something false, so the page draws none.

		Scoped to a node of its own, because bounds are a property of the whole
		answer and another method's pinned location would otherwise supply one.
		"""
		self.make(is_published=1, geo_node=self.society_b["region"])

		self.assertIsNone(api.published(geo_node=self.society_b["region"])["bounds"])

	def test_bounds_enclose_every_pin(self):
		"""Narrowed to one society, so the box is the box around these two."""
		where = self.society_b["region"]

		self.make(is_published=1, geo_node=where, latitude=-1.0, longitude=36.0)
		self.make(location_name="Warehouse", is_published=1, geo_node=where, latitude=-3.0, longitude=39.0)

		bounds = api.published(geo_node=where)["bounds"]

		self.assertEqual(bounds, {"south": -3.0, "north": -1.0, "west": 36.0, "east": 39.0})

	def test_narrowing_to_another_society_serves_nothing(self):
		location = self.make(is_published=1)

		answer = api.published(geo_node=self.society_b["region"])

		self.assertNotIn(location.name, self.names(answer))

	def test_narrowing_to_an_unknown_node_serves_nothing(self):
		self.make(is_published=1)

		self.assertEqual(api.published(geo_node="Geo Node That Was Never Created")["locations"], [])

	def test_the_coordinators_read_goes_through_the_permission_layer(self):
		"""The counterpart of the guest read, and the contrast is the point.

		`published` bypasses permissions and is bounded by `is_published`.
		`branch_locations` does not: it uses `frappe.get_list`, so a caller with
		no role on the doctype is refused outright rather than being handed a
		published subset through the back door.
		"""
		self.make(is_published=1)

		with fixtures.acting_as(fixtures.make_user("locations-nobody")):
			with self.assertRaises(frappe.PermissionError):
				api.branch_locations()
