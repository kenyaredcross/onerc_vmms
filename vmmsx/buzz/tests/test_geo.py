# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""BUZZ-01 — the geo-anchor seam, and its graceful absence.

**Nothing here is mocked for the "present" half.** Buzz really is installed on
this site, so these tests exercise the real `Buzz Event` doctype and the real
Custom Field the patch installs — the same discipline `test_learning.py` uses
for the LMS seam.

**Absence is mocked**, because the app really is installed here and a test
cannot uninstall it. `frappe.get_installed_apps()` is patched to the real list
minus `buzz`, exactly as `test_payments_absent.py` does for the payments seam —
both guards ask installed-apps rather than trying an import, so this is the
surface that actually needs to lie.
"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.buzz.services import geo
from vmmsx.patches import setup_buzz_seam

EXTRA_TEST_RECORD_DEPENDENCIES = []

TEST_PREFIX = "BUZZTEST"

HOST_DOCTYPE = "Event Host"


def without_buzz():
	"""Patch installed-apps to exclude Buzz, keeping everything else.

	The real list minus one entry, rather than a hand-written one: a
	hand-written list would also hide vmmsx and onerc_core from any framework
	code that happens to ask during the same call.
	"""
	remaining = [app for app in frappe.get_installed_apps() if app != geo.BUZZ_APP]

	return patch.object(frappe, "get_installed_apps", return_value=remaining)


class TestBuzzGeoSeam(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		if not geo.is_available():
			return

		from onerc_core.geo.tests import fixtures as geo_fixtures

		cls.level = geo_fixtures.make_level(f"{TEST_PREFIX}-1", "Region", 1, is_lowest=True)
		cls.node = geo_fixtures.make_node(f"{TEST_PREFIX} Region", cls.level, None)
		cls.host = frappe.get_doc({"doctype": HOST_DOCTYPE, "name": f"{TEST_PREFIX} Host"}).insert(
			ignore_permissions=True
		)
		cls.category = (
			frappe.db.get_value("Event Category", {}, "name")
			or frappe.get_doc({"doctype": "Event Category", "name": f"{TEST_PREFIX} Category"})
			.insert(ignore_permissions=True)
			.name
		)

		cls.events = []

	@classmethod
	def tearDownClass(cls):
		if geo.is_available():
			for event in cls.events:
				if frappe.db.exists(geo.EVENT_DOCTYPE, event):
					frappe.delete_doc(geo.EVENT_DOCTYPE, event, force=True)

			if frappe.db.exists(HOST_DOCTYPE, cls.host.name):
				frappe.delete_doc(HOST_DOCTYPE, cls.host.name, force=True)

			if frappe.db.exists("Geo Node", cls.node):
				frappe.delete_doc("Geo Node", cls.node, force=True)

			if frappe.db.exists("Geo Level", cls.level):
				frappe.delete_doc("Geo Level", cls.level, force=True)

		super().tearDownClass()

	def make_event(self, title: str, **overrides) -> str:
		values = {
			"doctype": geo.EVENT_DOCTYPE,
			"title": f"{TEST_PREFIX} {title}",
			"start_date": "2026-09-01",
			"start_time": "09:00:00",
			"end_time": "10:00:00",
			"category": self.category,
			"host": self.host.name,
		}
		values.update(overrides)

		event = frappe.get_doc(values).insert(ignore_permissions=True)
		self.events.append(event.name)

		return event.name

	# --- Buzz is really here on this bench ----------------------------------

	def test_buzz_is_installed_on_this_bench(self):
		"""If this fails, the rest of this class is testing the wrong thing."""
		self.assertTrue(geo.is_available())

	# --- the field ------------------------------------------------------------

	def test_the_custom_field_exists_on_the_event_doctype(self):
		self.assertTrue(
			frappe.db.exists("Custom Field", {"dt": geo.EVENT_DOCTYPE, "fieldname": geo.GEO_NODE_FIELD})
		)

	def test_the_field_is_a_link_to_geo_node_and_is_optional(self):
		field = frappe.get_meta(geo.EVENT_DOCTYPE).get_field(geo.GEO_NODE_FIELD)

		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, "Geo Node")
		self.assertFalse(field.reqd)

	# --- anchoring --------------------------------------------------------

	def test_an_event_can_be_anchored_and_the_anchor_is_readable(self):
		event = self.make_event("Anchored", geo_node=self.node)

		self.assertEqual(geo.geo_node_of(event), self.node)
		self.assertEqual(frappe.db.get_value(geo.EVENT_DOCTYPE, event, "geo_node"), self.node)

	def test_an_event_may_be_created_with_no_anchor_at_all(self):
		"""Optional means optional: Buzz's own flows never have to set this."""
		event = self.make_event("Unplaced")

		self.assertFalse(geo.geo_node_of(event))

	# --- graceful absence ---------------------------------------------------

	def test_the_mock_really_hides_buzz(self):
		self.assertTrue(geo.is_available())

		with without_buzz():
			self.assertNotIn(geo.BUZZ_APP, frappe.get_installed_apps())
			self.assertFalse(geo.is_available())

		self.assertTrue(geo.is_available())

	def test_the_patch_is_dormant_with_buzz_absent(self):
		"""No throw, and no attempt to touch a doctype it cannot see."""
		with without_buzz():
			setup_buzz_seam.execute()

	def test_geo_node_of_answers_none_rather_than_raising_when_buzz_is_absent(self):
		with without_buzz():
			self.assertIsNone(geo.geo_node_of("whatever"))

	def test_the_patch_is_still_idempotent_with_buzz_present(self):
		"""A second run, on the ordinary site, changes nothing and does not throw."""
		before = frappe.db.count(
			"Custom Field", filters={"dt": geo.EVENT_DOCTYPE, "fieldname": geo.GEO_NODE_FIELD}
		)

		setup_buzz_seam.execute()

		after = frappe.db.count(
			"Custom Field", filters={"dt": geo.EVENT_DOCTYPE, "fieldname": geo.GEO_NODE_FIELD}
		)

		self.assertEqual(before, after)
