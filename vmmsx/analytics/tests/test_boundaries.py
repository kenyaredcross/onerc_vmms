# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Reading a society's boundary file: layers, matching, simplifying.

Small invented squares stand in for counties, so what is tested is the reading
and matching rules rather than anybody's map.
"""

import io
import json
import zipfile
from unittest.mock import patch

from frappe.tests import IntegrationTestCase

from vmmsx.analytics.services import boundaries


def square(west: float, south: float, size: float = 1.0) -> list:
	return [[[west, south], [west + size, south], [west + size, south + size], [west, south + size], [west, south]]]


def feature(properties: dict, polygon: list, kind: str = "Polygon") -> dict:
	return {"type": "Feature", "properties": properties, "geometry": {"type": kind, "coordinates": polygon}}


def collection(*features) -> dict:
	return {"type": "FeatureCollection", "features": list(features)}


UNITS = [
	{"name": "N-1", "label": "Elgeyo Marakwet", "code": "KE-COUNTY-028", "point": {"latitude": 1, "longitude": 35}},
	{"name": "N-2", "label": "Nandi", "code": "KE-COUNTY-029", "point": {"latitude": 0.2, "longitude": 35.1}},
	{"name": "N-3", "label": "Turkana", "code": "KE-COUNTY-023", "point": {"latitude": 3, "longitude": 35.5}},
]


class TestMatching(IntegrationTestCase):
	def layer(self, *features):
		return boundaries._layer(collection(*features))

	def test_an_exact_code_matches(self):
		layer = self.layer(feature({"code": "KE-COUNTY-029"}, square(35, 0)))
		self.assertEqual(set(boundaries._match([layer], UNITS)), {"N-2"})

	def test_trailing_digits_match_a_pcode(self):
		layer = self.layer(feature({"ADM1_PCODE": "KE028"}, square(35, 1)))
		self.assertEqual(set(boundaries._match([layer], UNITS)), {"N-1"})

	def test_a_longer_code_does_not_match_on_its_tail(self):
		"""A sub-county's KE028001 is not county 001."""
		layer = self.layer(feature({"ADM2_PCODE": "KE028001"}, square(35, 1)))
		units = [{**UNITS[0], "code": "KE-COUNTY-001"}]
		self.assertEqual(boundaries._match([layer], units), {})

	def test_a_name_matches_despite_punctuation(self):
		layer = self.layer(feature({"ADM1_EN": "Elgeyo-Marakwet"}, square(35, 1)))
		self.assertEqual(set(boundaries._match([layer], UNITS)), {"N-1"})

	def test_a_longer_name_matches_when_only_one_fits(self):
		layer = self.layer(feature({"name": "Nandi City"}, square(35, 0)))
		self.assertEqual(set(boundaries._match([layer], UNITS)), {"N-2"})

	def test_a_shared_start_matches_nothing(self):
		layer = self.layer(feature({"name": "Nandi North"}, square(35, 0)), feature({"name": "Nandi South"}, square(36, 0)))
		self.assertEqual(boundaries._match([layer], UNITS), {})

	def test_the_layer_matching_most_counties_wins(self):
		country = self.layer(feature({"ADM0_EN": "Kenya"}, square(33, -5, 10)))
		counties = self.layer(
			feature({"ADM1_PCODE": "KE028"}, square(35, 1)),
			feature({"ADM1_PCODE": "KE029"}, square(35, 0)),
		)
		self.assertEqual(set(boundaries._match([country, counties], UNITS)), {"N-1", "N-2"})

	def test_a_multipolygon_keeps_every_part(self):
		layer = self.layer(feature({"ADM1_PCODE": "KE023"}, [square(35, 3), square(37, 3)], "MultiPolygon"))
		self.assertEqual(len(boundaries._match([layer], UNITS)["N-3"]), 2)


class TestReading(IntegrationTestCase):
	def test_a_zip_is_read_layer_by_layer(self):
		buffer = io.BytesIO()

		with zipfile.ZipFile(buffer, "w") as archive:
			archive.writestr("ken_admin0.geojson", json.dumps(collection(feature({"ADM0_EN": "Kenya"}, square(33, -5, 10)))))
			archive.writestr("ken_admin1.geojson", json.dumps(collection(feature({"ADM1_PCODE": "KE029"}, square(35, 0)))))
			archive.writestr("readme.txt", "not a layer")

		self.assertEqual(len(boundaries._layers(buffer.getvalue())), 2)

	def test_simplifying_drops_points_on_a_straight_edge(self):
		edge = [(0, 0), (0.5, 0.0001), (1, 0), (1, 1), (0, 1), (0, 0)]
		self.assertNotIn((0.5, 0.0001), boundaries._simplify(edge))
		self.assertIn((1, 1), boundaries._simplify(edge))

	def test_no_file_draws_every_county_as_a_dot(self):
		with patch.object(boundaries, "_source", return_value=None), patch.object(boundaries, "_credit", return_value=None):
			result = boundaries.shapes(UNITS)

		self.assertFalse(result["has_file"])
		self.assertEqual([shape["path"] for shape in result["shapes"]], [None, None, None])

	def test_an_unmatched_county_is_still_drawn(self):
		layers = [boundaries._layer(collection(feature({"ADM1_PCODE": "KE028"}, square(35, 1))))]

		with patch.object(boundaries, "_source", return_value="/files/x.geojson"), patch.object(
			boundaries, "_cached_features", return_value=layers
		), patch.object(boundaries, "_credit", return_value="Boundaries: test"):
			result = boundaries.shapes(UNITS)

		paths = {shape["name"]: shape["path"] for shape in result["shapes"]}
		self.assertTrue(paths["N-1"].startswith("M"))
		self.assertIsNone(paths["N-2"])
		self.assertEqual((result["matched"], result["credit"]), (1, "Boundaries: test"))
