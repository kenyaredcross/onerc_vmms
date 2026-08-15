# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Branch Location — a place the society can be found.

An office, a warehouse, a training centre, a clinic. It hangs off a Geo Node
like every other operational record, so a coordinator maintains the places in
their own area without anybody keeping a second list of which branch owns what.

**The controller holds the one rule the field descriptions cannot.** A coordinate
pair is either a point on the earth or it is nothing, and the two ways it can be
neither are worth refusing at save rather than discovering on a map: a latitude
outside its range, and half a pair. Half a pair is the more insidious of the two,
because Frappe stores an empty Float as `0.0` rather than as nothing, so a
location with a latitude typed in and a longitude left blank would be drawn
confidently in the Gulf of Guinea.

Everything else about this doctype is configuration. Whether a place appears on
the public map is `is_published`, a tick on this form, exactly as `is_public` on
a content surface is the whole of the guest-read rule there.
"""

import frappe
from frappe import _
from frappe.model.document import Document

# Decimal degrees. Not a society's business and not configuration: these are the
# bounds of the coordinate system, the same in every country.
LATITUDE_RANGE = (-90.0, 90.0)
LONGITUDE_RANGE = (-180.0, 180.0)


class VMMSBranchLocation(Document):
	def validate(self):
		self.assert_coordinates_paired()
		self.assert_coordinates_in_range()

	def has_point(self) -> bool:
		"""Is there a coordinate pair to draw?

		A Float left empty is `0.0`, so this asks whether either value is
		non-zero rather than whether either is set. The cost is that the one
		point on the earth at exactly 0, 0 cannot be recorded; it is in the
		Atlantic, and a society with an office there has a larger problem.
		"""
		return bool(self.latitude) or bool(self.longitude)

	def assert_coordinates_paired(self):
		"""Refuse half a coordinate."""
		if not self.has_point():
			return

		if self.latitude and self.longitude:
			return

		frappe.throw(
			_(
				"A location needs both a latitude and a longitude, or neither. One on its own"
				" cannot be put on a map, and it would be drawn somewhere it is not. Leave both"
				" empty to list this place without a pin."
			),
			frappe.ValidationError,
			title=_("Half A Coordinate"),
		)

	def assert_coordinates_in_range(self):
		"""Refuse a coordinate that is not on the earth.

		Almost always the two typed the wrong way round, which is why the message
		says so: a Kenyan branch entered as latitude 36 and longitude -1 is a
		valid pair of numbers and a place in Iraq.
		"""
		for value, label, (low, high) in (
			(self.latitude, _("Latitude"), LATITUDE_RANGE),
			(self.longitude, _("Longitude"), LONGITUDE_RANGE),
		):
			if value and not low <= value <= high:
				frappe.throw(
					_(
						"{0} must be between {1} and {2}. {3} is not a point on the earth."
						" Check the two have not been entered the wrong way round."
					).format(label, low, high, value),
					frappe.ValidationError,
					title=_("Off The Map"),
				)
