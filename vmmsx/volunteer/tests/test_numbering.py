# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Record numbers in the old VMMS's formats.

A volunteer is `VOL-26-031710`, two-digit year and six digits from one counter
that carries on across years; a member is `VM-MEM-2026-01475` and a membership
`VM-MSH-2026-02594`, each counting afresh every year. `setup.numbering` installs
the volunteer's Document Naming Rule and raises counters, never lowering one.
"""

import re

import frappe
from frappe.model.naming import set_new_name
from frappe.utils import getdate, nowdate

from vmmsx.setup import numbering
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

YY = getdate(nowdate()).strftime("%y")
YYYY = getdate(nowdate()).strftime("%Y")


class TestNumbering(VolunteerTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		numbering.install()

	def rule(self) -> str:
		return numbering.volunteer_rule()

	def counter(self) -> int:
		return int(frappe.db.get_value("Document Naming Rule", self.rule(), "counter"))

	def new_volunteer(self, first_name: str) -> str:
		profile = fixtures.make_profile(first_name=first_name)
		return fixtures.make_volunteer(profile, self.society_a["ward"]).name

	def test_a_volunteer_is_numbered_like_the_old_system(self):
		self.assertRegex(self.new_volunteer("Numbered"), rf"^VOL-{YY}-\d{{6}}$")

	def test_the_volunteer_number_carries_on_from_the_counter(self):
		frappe.db.set_value("Document Naming Rule", self.rule(), "counter", 31709)

		self.assertEqual(self.new_volunteer("Continues"), f"VOL-{YY}-031710")
		self.assertEqual(self.counter(), 31710)

	def test_installing_again_leaves_the_rule_and_its_counter_alone(self):
		frappe.db.set_value("Document Naming Rule", self.rule(), "counter", 4242)
		numbering.install()

		self.assertEqual(frappe.db.count("Document Naming Rule", {"document_type": numbering.VOLUNTEER}), 1)
		self.assertEqual(self.counter(), 4242)

	def test_raising_never_lowers_a_counter(self):
		# Above every volunteer earlier methods left behind: the class rolls back
		# once, at the end, and raising also clears the highest number on the site.
		high = numbering.highest_volunteer_number() + 900
		frappe.db.set_value("Document Naming Rule", self.rule(), "counter", high)
		key = f"VM-MEM-{YYYY}-"
		numbering.raise_counters(volunteer_floor=100, series_floors={key: 0})
		self.assertEqual(self.counter(), high)

		numbering.raise_counters(volunteer_floor=high + 31709, series_floors={key: 1474})
		self.assertEqual(self.counter(), high + 31709)
		self.assertGreaterEqual(numbering.series_counter(key), 1474)

	def test_raising_clears_the_highest_number_already_on_the_site(self):
		name = self.new_volunteer("Highest")
		number = int(name.rsplit("-", 1)[1])
		frappe.db.set_value("Document Naming Rule", self.rule(), "counter", 0)

		after = numbering.raise_counters()

		self.assertEqual(after["volunteer"]["current"], number)

	def test_a_member_is_numbered_like_the_old_system(self):
		member = fixtures.make_member(fixtures.make_profile(first_name="Member"))

		self.assertRegex(member.name, rf"^VM-MEM-{YYYY}-\d{{5}}$")

	def test_a_membership_is_numbered_like_the_old_system(self):
		membership = frappe.new_doc("VMMS Membership")
		set_new_name(membership)

		self.assertRegex(membership.name, rf"^VM-MSH-{YYYY}-\d{{5}}$")

	def test_existing_numbers_are_not_mistaken_for_new_ones(self):
		self.assertIsNone(re.match(numbering.VOLUNTEER_NAME, "VOL-00042"))
		self.assertIsNone(numbering.SERIES["VMMS Member"].match("MEM-00042"))

	def _pin(self, doctype: str, value: str) -> None:
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter

		for prop in ("options", "default"):
			frappe.db.delete("Property Setter", {"doc_type": doctype, "field_name": "naming_series", "property": prop})
			make_property_setter(doctype, "naming_series", prop, value, "Text", validate_fields_for_doctype=False)

	def _pinned(self, doctype: str) -> str:
		return frappe.db.get_value(
			"Property Setter", {"doc_type": doctype, "field_name": "naming_series", "property": "options"}, "value"
		)

	def test_a_site_still_on_the_old_series_is_moved_onto_the_new_one(self):
		# What Frappe leaves on a site that had members before the change.
		self._pin("VMMS Member", "MEM-.#####")
		numbering.install()

		self.assertEqual(self._pinned("VMMS Member"), "VM-MEM-.YYYY.-.#####")
		member = fixtures.make_member(fixtures.make_profile(first_name="Pinned"))
		self.assertRegex(member.name, rf"^VM-MEM-{YYYY}-\d{{5}}$")

	def test_a_series_the_society_chose_is_left_alone(self):
		self._pin("VMMS Membership", "KRCS-MSH-.#####")
		numbering.install()

		self.assertEqual(self._pinned("VMMS Membership"), "KRCS-MSH-.#####")
		frappe.db.delete("Property Setter", {"doc_type": "VMMS Membership", "field_name": "naming_series"})
		frappe.clear_cache(doctype="VMMS Membership")
