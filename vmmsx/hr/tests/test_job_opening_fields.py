# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The screening schema on HRMS's `Job Opening`, and the ways it can go quiet.

Every failure this suite is built around is a **silent** one. That is the whole
character of the port: nothing here throws when it goes wrong, so nothing here
gets noticed without a test asking.

**A missing `Module Def` skips a whole module.** Frappe writes those records in
`install_app` and nowhere else, so `VMMS HR` — added for this port, after the app
was installed everywhere — had none, and all six of its doctypes failed to sync
while `bench migrate` reported success. `patches/register_hr_module.py` closes
that, the eleventh instance of a pattern this app already had a name for; the
test here is that the doctypes are actually on the site, because the doctypes are
the only honest evidence that the patch and its cache rebuild both did their job.

**A Property Setter is not a column.** `closes_on` is widened from HRMS's Date to
a Datetime, and writing the Property Setter without calling `db.updatedb` leaves
the meta claiming Datetime over a `date` column, which does not error — it
truncates the time off everything written to it.

**A skipped field orphans the ones after it.** Three fields point at doctypes
owned by apps vmmsx does not require. When one is absent the field is skipped,
and the next field's anchor has to be walked back past it, or a section break
lands after a field that does not exist and the whole tab collapses to the bottom
of the form.

**A verbatim field order drops HRMS's newer fields.** The order was captured from
the old app when HRMS had a different field list. Copied as it stood it would
have pushed `prevent_duplicate_applicant` and the pay-details tab to the end of
the form, so `_field_order()` filters and appends rather than replaces.
"""

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.setup import job_opening_fields as opening_fields

OPENING = opening_fields.OPENING_DOCTYPE

# The doctypes the port brings with it, and the module they belong to. Named here
# rather than derived, so a doctype quietly moved to another module fails a test
# instead of moving.
PORTED_DOCTYPES = (
	"Profession",
	"Personnel License Type",
	"Personnel Licence",
	"Supporting Document Type",
	"Required Attachments",
	"Job Application Screening Questions",
)

MODULE = "VMMS HR"


class OpeningFieldsTestCase(IntegrationTestCase):
	def setUp(self):
		super().setUp()

		if not opening_fields.is_available():
			self.skipTest("HRMS is not installed on this site")

		self.meta = frappe.get_meta(OPENING)


class TestThePortedDoctypes(OpeningFieldsTestCase):
	def test_every_one_of_them_is_on_the_site(self):
		"""The evidence that `VMMS HR` has a Module Def, stated as what depends on it.

		A missing Module Def does not throw — it makes `sync_all` skip the
		module, and the only thing anybody sees afterwards is a Table field
		pointing at a doctype that is not there.
		"""
		for doctype in PORTED_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertTrue(frappe.db.exists("DocType", doctype), f"{doctype} did not sync")

	def test_they_belong_to_the_hr_module(self):
		for doctype in PORTED_DOCTYPES:
			with self.subTest(doctype=doctype):
				self.assertEqual(frappe.db.get_value("DocType", doctype, "module"), MODULE)

	def test_the_three_grids_are_child_tables(self):
		"""A Table field whose target is not `istable` renders as nothing at all."""
		for doctype in ("Personnel Licence", "Required Attachments", "Job Application Screening Questions"):
			with self.subTest(doctype=doctype):
				self.assertTrue(frappe.db.get_value("DocType", doctype, "istable"))

	def test_the_module_def_exists(self):
		self.assertTrue(frappe.db.exists("Module Def", MODULE))


class TestTheFieldsAreOnTheOpening(OpeningFieldsTestCase):
	def test_every_ungated_field_is_there(self):
		"""Everything the port promises, minus what a missing app legitimately gates."""
		for field in opening_fields.FIELDS:
			requires = field.get("requires")

			if requires and not frappe.db.exists("DocType", requires):
				continue

			with self.subTest(fieldname=field["fieldname"]):
				self.assertIsNotNone(
					self.meta.get_field(field["fieldname"]),
					f"{field['fieldname']} is not on {OPENING}",
				)

	def test_a_gated_field_is_absent_exactly_when_its_doctype_is(self):
		"""`required_certification` needs the LMS, and vmmsx does not require the LMS."""
		gated = [field for field in opening_fields.FIELDS if field.get("requires")]
		self.assertTrue(gated, "the gating mechanism has no fields left to gate")

		for field in gated:
			with self.subTest(fieldname=field["fieldname"]):
				self.assertEqual(
					bool(self.meta.get_field(field["fieldname"])),
					bool(frappe.db.exists("DocType", field["requires"])),
				)

	def test_the_anchor_chain_walks_back_past_a_skipped_field(self):
		"""`required_licences` sat after `required_certification` in the old app.

		On a site with no LMS that anchor does not exist, and a custom field
		whose `insert_after` names a missing field is placed at the end of the
		form — taking the section break, the attachments grid and both remaining
		tabs with it.
		"""
		anchor = frappe.db.get_value(
			"Custom Field", {"dt": OPENING, "fieldname": "required_licences"}, "insert_after"
		)

		self.assertIsNotNone(self.meta.get_field(anchor), f"required_licences sits after {anchor!r}")

	def test_it_does_not_shadow_a_field_hrms_already_ships(self):
		"""`job_opening_template` was a Custom Field in the old app and is standard now."""
		self.assertIsNotNone(self.meta.get_field("job_opening_template"))
		self.assertFalse(
			frappe.db.exists("Custom Field", {"dt": OPENING, "fieldname": "job_opening_template"})
		)

	def test_the_grids_point_at_doctypes_that_exist(self):
		"""A Table field is only as real as its target."""
		for field in opening_fields.FIELDS:
			if field["fieldtype"] != "Table":
				continue

			df = self.meta.get_field(field["fieldname"])

			if not df:
				continue

			with self.subTest(fieldname=field["fieldname"]):
				self.assertTrue(frappe.db.exists("DocType", df.options), f"{df.options} does not exist")


class TestWhatItChangesAboutHrmsOwnFields(OpeningFieldsTestCase):
	def test_the_salary_block_is_hidden(self):
		"""A volunteer post has no band to publish, and a currency picker no answer."""
		for fieldname in ("currency", "lower_range", "upper_range", "salary_per", "publish_salary_range"):
			with self.subTest(fieldname=fieldname):
				self.assertTrue(self.meta.get_field(fieldname).hidden)

	def test_hrms_own_location_gives_way_to_the_ported_one(self):
		"""Two fields labelled Location is how half a register ends up in each."""
		self.assertTrue(self.meta.get_field("location").hidden)

		if frappe.db.exists("DocType", opening_fields.LOCATION_DOCTYPE):
			self.assertFalse(self.meta.get_field("job_location").hidden)

	def test_employment_type_takes_the_societys_word(self):
		self.assertEqual(self.meta.get_field("employment_type").label, "Opportunity Type")

	def test_posted_on_is_required_and_closes_on_is_required_while_open(self):
		self.assertTrue(self.meta.get_field("posted_on").reqd)
		self.assertEqual(
			self.meta.get_field("closes_on").mandatory_depends_on, "eval: doc.status=='Open'"
		)

	def test_closes_on_is_a_datetime_in_the_meta_and_in_the_database(self):
		"""Both halves, because the first without the second truncates in silence."""
		self.assertEqual(self.meta.get_field("closes_on").fieldtype, "Datetime")
		self.assertFalse(opening_fields._column_out_of_step("closes_on", "Datetime"))


class TestTheFormOrder(OpeningFieldsTestCase):
	def setUp(self):
		super().setUp()

		self.order = json.loads(
			frappe.db.get_value("Property Setter", {"doc_type": OPENING, "property": "field_order"}, "value")
			or "[]"
		)

	def test_it_names_every_field_on_the_form_and_nothing_else(self):
		"""The captured order predates HRMS's current field list in both directions.

		It carries two section breaks HRMS has since retired, and it has never
		heard of `prevent_duplicate_applicant` or the pay-details tab. Filtering
		without appending would push those to the end of the form.
		"""
		on_form = [df.fieldname for df in self.meta.fields]

		self.assertCountEqual(self.order, on_form)

	def test_the_opening_reads_in_the_order_the_port_intends(self):
		"""Identity first, then the society, then publishing, then the new tabs."""
		self.assertEqual(self.order[:5], list(opening_fields.PREFERRED_ORDER[:5]))
		self.assertLess(self.order.index("screening_requirements"), self.order.index("screening_questions_tab"))
		self.assertLess(self.order.index("screening_questions_tab"), self.order.index("notification_settings"))


class TestRunningItAgainChangesNothing(OpeningFieldsTestCase):
	def test_a_second_install_adds_no_field_and_no_property_setter(self):
		"""It runs on every migrate, so it has to be worth nothing on most of them."""
		before = (
			frappe.db.count("Custom Field", {"dt": OPENING}),
			frappe.db.count("Property Setter", {"doc_type": OPENING}),
		)

		opening_fields.install()

		self.assertEqual(
			(
				frappe.db.count("Custom Field", {"dt": OPENING}),
				frappe.db.count("Property Setter", {"doc_type": OPENING}),
			),
			before,
		)

	def test_it_does_nothing_at_all_without_hrms(self):
		"""A society running volunteering without a recruitment module is ordinary.

		Patched at `frappe.get_installed_apps`, which is the exact surface
		`is_available()` reads — the same way `test_openings.py` mocks HRMS away.
		"""
		installed = [app for app in frappe.get_installed_apps() if app != opening_fields.HRMS_APP]
		before = frappe.db.count("Custom Field", {"dt": OPENING})

		with patch("frappe.get_installed_apps", return_value=installed):
			self.assertFalse(opening_fields.is_available())
			opening_fields.install()

		self.assertEqual(frappe.db.count("Custom Field", {"dt": OPENING}), before)
