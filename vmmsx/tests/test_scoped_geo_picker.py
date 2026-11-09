"""A staff picker offers only the caller's own part of the tree.

`geo.browse(scoped=1)` narrows each rung to the nodes on the way down to the
caller's Geo Assignments or inside them. A Head of Region is offered their own
region and nothing beside it; national staff keep the whole tree; somebody with
no assignment is offered nothing. The public join form never passes `scoped`.
"""

import unittest
from unittest.mock import patch

from vmmsx.api import geo


def node(name, label, level):
	return {"name": name, "geo_node_name": label, "geo_level": level}


TREE = {
	"national": [node("east", "KRCS Lower Eastern", "region"), node("coast", "KRCS Coast", "region")],
	"east": [node("nairobi", "Nairobi", "county"), node("kitui", "Kitui", "county")],
	"coast": [node("mombasa", "Mombasa", "county")],
}
LABELS = [{"key": key, "name": key.title(), "order": index} for index, key in enumerate(("national", "region", "county"), 1)]


def browse(parent=None, scoped=None, reach=None):
	with (
		patch.object(geo.adapter, "level_labels", return_value=LABELS),
		patch.object(geo.adapter, "get_root_regions", return_value=[node("national", "Kenya", "national")]),
		patch.object(geo.adapter, "get_children", side_effect=lambda parent: TREE.get(parent, [])),
		patch.object(geo, "_reach", return_value=reach),
	):
		return [row["name"] for row in geo.browse(parent=parent, scoped=scoped)["nodes"]]


class ScopedBrowseTest(unittest.TestCase):
	HEAD_OF_EAST = {"national", "east", "nairobi", "kitui"}

	def test_a_regional_head_is_offered_only_their_region(self):
		self.assertEqual(browse(scoped=1, reach=self.HEAD_OF_EAST), ["national"])
		self.assertEqual(browse("national", scoped=1, reach=self.HEAD_OF_EAST), ["east"])
		self.assertEqual(browse("east", scoped=1, reach=self.HEAD_OF_EAST), ["nairobi", "kitui"])

	def test_somebody_with_no_assignment_is_offered_nothing(self):
		self.assertEqual(browse("national", scoped=1, reach=set()), [])

	def test_national_staff_keep_the_whole_tree(self):
		self.assertEqual(browse("national", scoped=1, reach=None), ["east", "coast"])

	def test_the_public_picker_is_not_narrowed(self):
		self.assertEqual(browse("national", reach=set()), ["east", "coast"])


class ReachTest(unittest.TestCase):
	def reach(self, anchors, national=False):
		ancestors = {"nairobi": [{"name": "east"}, {"name": "national"}], "east": [{"name": "national"}]}
		descendants = {"east": ["nairobi", "kitui"], "nairobi": []}
		with (
			patch("vmmsx.analytics.services.oversight.national_allowed", return_value=national),
			patch.object(geo, "_anchors", return_value=anchors),
			patch.object(geo.adapter, "get_ancestors", side_effect=lambda name: ancestors[name]),
			patch.object(geo.adapter, "get_descendants", side_effect=lambda name: descendants[name]),
		):
			return geo._reach("someone@example.org")

	def test_a_county_assignment_reaches_its_county_and_the_way_down_to_it(self):
		self.assertEqual(self.reach(["nairobi"]), {"national", "east", "nairobi"})

	def test_a_region_assignment_reaches_every_county_in_it(self):
		self.assertEqual(self.reach(["east"]), {"national", "east", "nairobi", "kitui"})

	def test_national_staff_are_not_narrowed(self):
		self.assertIsNone(self.reach([], national=True))
