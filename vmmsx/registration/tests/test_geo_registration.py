"""County selection does not require a region selection."""

import unittest
from unittest.mock import patch

from vmmsx.api import geo


class TestCountyRegistration(unittest.TestCase):
	def test_counties_from_all_regions_are_available_without_loading_lower_levels(self):
		def node(name, label, level):
			return {"name": name, "geo_node_name": label, "geo_level": level}

		tree = {
			"national": [
				node("west", "KRCS West Kenya", "region"),
				node("rift", "KRCS North Rift", "region"),
			],
			"west": [node("kisumu", "Kisumu", "county")],
			"rift": [node("turkana", "Turkana", "county")],
		}
		labels = [
			{"key": key, "name": key.title(), "order": index}
			for index, key in enumerate(("national", "region", "county", "ward"), 1)
		]
		with (
			patch.object(geo.adapter, "level_labels", return_value=labels),
			patch.object(
				geo.adapter, "get_root_regions", return_value=[node("national", "Kenya", "national")]
			),
			patch.object(geo.adapter, "get_children", side_effect=lambda parent: tree[parent]) as children,
		):
			result = geo.browse(level="county")
		self.assertEqual([row["name"] for row in result["nodes"]], ["kisumu", "turkana"])
		self.assertEqual(children.call_count, 3)
