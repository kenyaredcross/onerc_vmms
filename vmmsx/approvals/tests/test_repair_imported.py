# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A membership carried over from the old VMMS keeps the state it came with.

An imported pending membership is Submitted with no stage: the same shape as one
`engine.park` held back before a workflow existed. The repair sweep routes parked
documents into review. Applied to an imported one, that would change the record
after the import, on the next daily run, migrate or Geo Assignment save.

These tests cover the decision rather than the routing, which `test_repair.py`
already covers. `_route` is replaced so that "routed" is a visible call rather
than a whole workflow, approver and member to build.
"""

from unittest.mock import patch

from frappe.tests import IntegrationTestCase

from vmmsx.approvals.services import repair

MEMBERSHIP = "VMMS Membership"


def _marker(value):
	"""Answer only the marker lookup; every other read goes to the database.

	Patching `get_value` outright would also intercept the reads Frappe makes to
	load the DocType itself.
	"""
	real = repair.frappe.db.get_value

	def get_value(doctype, filters=None, fieldname="name", *args, **kwargs):
		if doctype == MEMBERSHIP and fieldname == repair.IMPORTED_MARKERS[MEMBERSHIP]:
			return value
		return real(doctype, filters, fieldname, *args, **kwargs)

	return patch.object(repair.frappe.db, "get_value", side_effect=get_value)


class TestImportedRecordsKeepTheirState(IntegrationTestCase):
	def test_an_imported_parked_membership_is_not_routed(self):
		with (
			patch.object(repair, "_is_parked", return_value=True),
			_marker("VM-MSH-2025-00001"),
			patch.object(repair, "_route") as route,
		):
			self.assertFalse(repair._repair_one(MEMBERSHIP, "VM-MSH-2025-00001"))

		route.assert_not_called()

	def test_a_membership_made_in_this_app_is_still_routed(self):
		"""The exemption is the marker, not the doctype: parking still works for new ones."""
		with (
			patch.object(repair, "_is_parked", return_value=True),
			_marker(None),
			patch.object(repair, "_route", return_value=True) as route,
		):
			self.assertTrue(repair._repair_one(MEMBERSHIP, "VM-MSH-2026-09999"))

		route.assert_called_once_with(MEMBERSHIP, "VM-MSH-2026-09999")

	def test_the_marker_is_a_real_field_on_the_membership(self):
		"""A renamed field would silently turn the exemption off."""
		from frappe import get_meta

		for doctype, field in repair.IMPORTED_MARKERS.items():
			self.assertTrue(get_meta(doctype).has_field(field), f"{doctype}.{field}")

	def test_a_doctype_without_a_marker_is_never_treated_as_imported(self):
		with patch.object(repair.frappe.db, "get_value") as get_value:
			self.assertFalse(repair._is_imported("VMMS Volunteer Application", "anything"))

		get_value.assert_not_called()
