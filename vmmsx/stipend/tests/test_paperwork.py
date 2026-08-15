# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The paperwork itself: a period, a place, many volunteers, and a paired form.

What is asserted here:

1. **ACC-02.** Neither document can exist without a Geo Node. An unplaced record
   is invisible to geo scoping and unroutable, so it would exist with nobody able
   to see or act on it, and the refusal happens at creation rather than being a
   step somebody could skip.
2. **ACC-03.** *Which* level is a society's setting, and the same code refuses at
   one level and accepts at another with nothing changed but configuration.
3. **One report covers many volunteers.** That is what the child table is for,
   and the report is refused at submission if it covers nobody.
4. **The form is paired.** Its period is the report's, copied on every save, and
   its anchor is checked against the report's, so the two cannot describe
   different periods or different places.
5. **The currency is the society's**, and never a code written into this app.
"""

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.stipend.services import report as report_service
from vmmsx.stipend.tests import fixtures
from vmmsx.stipend.tests.base import StipendTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestTheGeoAnchorIsMandatory(StipendTestCase):
	"""ACC-02, on both documents, at creation."""

	def test_a_report_without_a_geo_node_is_refused(self):
		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_report(None)

	def test_nothing_is_saved_when_the_anchor_is_missing(self):
		before = frappe.db.count(fixtures.REPORT_DOCTYPE)

		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_report(None)

		self.assertEqual(frappe.db.count(fixtures.REPORT_DOCTYPE), before)

	def test_the_refusal_explains_what_an_unplaced_report_would_mean(self):
		"""The message is the rule, not a field name repeated back."""
		with self.assertRaises(frappe.MandatoryError) as caught:
			fixtures.make_report(None)

		self.assertIn("geo scoping", str(caught.exception).lower())

	def test_a_payment_form_without_a_geo_node_is_refused(self):
		report = fixtures.make_report(self.society_a["ward"])

		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_payment_form(report.name, None)

	def test_the_anchor_is_a_link_and_required_on_both_doctypes(self):
		"""Read from the schema, so a later edit that relaxed it fails here."""
		for doctype in (fixtures.REPORT_DOCTYPE, fixtures.PAYMENT_DOCTYPE):
			field = frappe.get_meta(doctype).get_field("geo_node")

			self.assertEqual(field.fieldtype, "Link", doctype)
			self.assertEqual(field.options, "Geo Node", doctype)
			self.assertTrue(field.reqd, doctype)


class TestTheAnchorLevelIsConfiguration(StipendTestCase):
	"""ACC-03. The same code, two societies, two answers, no source change."""

	def setUp(self):
		super().setUp()
		self.addCleanup(fixtures.set_stipend_anchor_level, None)

	def test_with_no_level_configured_any_level_is_accepted(self):
		fixtures.set_stipend_anchor_level(None)

		for node in (self.society_a["region"], self.society_a["branch"], self.society_a["ward"]):
			self.assertTrue(fixtures.make_report(node).name)

	def test_a_society_that_files_at_ward_level_refuses_a_branch(self):
		fixtures.set_stipend_anchor_level(self.society_a["levels"]["ward"])

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_report(self.society_a["branch"])

	def test_the_same_society_accepts_the_level_it_named(self):
		fixtures.set_stipend_anchor_level(self.society_a["levels"]["ward"])

		self.assertTrue(fixtures.make_report(self.society_a["ward"]).name)

	def test_another_society_with_another_ladder_files_at_its_own_level(self):
		"""No depth is assumed: the second society's district is its answer."""
		fixtures.set_stipend_anchor_level(self.society_b["levels"]["district"])

		self.assertTrue(fixtures.make_report(self.society_b["district"]).name)

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_report(self.society_b["ward"])

	def test_the_payment_form_is_held_to_the_same_level(self):
		"""One setting governs both, so a form cannot sit where its report may not."""
		fixtures.set_stipend_anchor_level(self.society_a["levels"]["ward"])
		report = fixtures.make_report(self.society_a["ward"])

		fixtures.set_stipend_anchor_level(self.society_a["levels"]["branch"])

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_payment_form(report.name, self.society_a["ward"])


class TestOneReportCoversManyVolunteers(StipendTestCase):
	"""The shape of the report: one period, one narrative, a table of people."""

	def setUp(self):
		super().setUp()
		self.node = self.society_a["ward"]
		self.people = [self.volunteer_at(self.node, "Report", f"Person{index}") for index in range(3)]

	def test_a_report_holds_every_volunteer_it_names(self):
		report = fixtures.make_report(self.node, [person.name for person in self.people])

		self.assertEqual(len(report_service.volunteers_of(report)), 3)
		self.assertEqual(set(report_service.volunteers_of(report)), {person.name for person in self.people})

	def test_the_volunteers_are_a_child_table_and_not_a_link(self):
		"""Read from the schema: a link would mean one report per person."""
		field = frappe.get_meta(fixtures.REPORT_DOCTYPE).get_field("volunteers")

		self.assertEqual(field.fieldtype, "Table")
		self.assertEqual(field.options, fixtures.REPORT_VOLUNTEER_DOCTYPE)

	def test_the_same_volunteer_cannot_be_listed_twice(self):
		person = self.people[0].name

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_report(self.node, [person, person])

	def test_a_report_covering_nobody_cannot_be_submitted(self):
		"""A draft may be empty. Sending it up is where it has to be about somebody."""
		report = fixtures.make_report(self.node)

		with self.assertRaises(frappe.MandatoryError):
			report_service.submit(report)

	def test_a_report_covering_somebody_can_be(self):
		report = fixtures.make_report(self.node, [self.people[0].name])

		self.assertTrue(report_service.submit(report)["is_pending"])

	def test_a_period_that_runs_backwards_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_report(self.node, period_from=today(), period_to=add_days(today(), -1))

	def test_a_single_day_period_is_ordinary(self):
		"""From and to may be the same day: a society may file weekly or daily."""
		self.assertTrue(fixtures.make_report(self.node, period_from=today(), period_to=today()).name)


class TestThePaymentFormIsPairedWithTheReport(StipendTestCase):
	"""The form pays for a period somebody already described, in the same place."""

	def setUp(self):
		super().setUp()
		self.node = self.society_a["ward"]
		self.person = self.volunteer_at(self.node, "Paired", "Person")
		self.report = fixtures.make_report(self.node, [self.person.name])

	def test_a_form_takes_its_period_from_its_report(self):
		form = fixtures.make_payment_form(self.report.name, self.node)

		self.assertEqual(getdate(form.period_from), getdate(self.report.period_from))
		self.assertEqual(getdate(form.period_to), getdate(self.report.period_to))

	def test_a_corrected_report_period_is_adopted_on_the_next_save(self):
		"""Copied on every save, not fetched once, so the two cannot drift apart."""
		form = fixtures.make_payment_form(self.report.name, self.node)

		self.report.period_to = add_days(self.report.period_to, 7)
		self.report.save()

		form.save()

		self.assertEqual(getdate(form.period_to), getdate(self.report.period_to))

	def test_the_period_fields_are_read_only_on_the_form(self):
		meta = frappe.get_meta(fixtures.PAYMENT_DOCTYPE)

		for fieldname in ("period_from", "period_to", "total_payable", "currency"):
			self.assertTrue(meta.get_field(fieldname).read_only, fieldname)

	def test_a_form_anchored_somewhere_else_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			fixtures.make_payment_form(self.report.name, self.society_a["other_ward"])

	def test_a_form_naming_no_report_is_refused(self):
		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_payment_form(None, self.node)


class TestTheCurrencyIsTheSocietys(StipendTestCase):
	"""No currency code lives in this app. The society's answer is the answer.

	Including against the framework: Frappe pre-fills a field named `currency`
	from the site's Global Defaults, which is another app's answer for the whole
	site. A form takes the society's.
	"""

	def setUp(self):
		super().setUp()
		self.was = frappe.db.get_single_value("National Society Settings", "currency")
		self.currency = fixtures.a_currency(other_than=self.was)

		if not self.currency:
			self.skipTest("this site holds no second Currency to change the society's answer to")

		self.addCleanup(fixtures.set_currency, self.was)
		self.node = self.society_a["ward"]
		self.person = self.volunteer_at(self.node, "Currency", "Person")
		self.report = fixtures.make_report(self.node, [self.person.name])

	def test_a_form_adopts_the_configured_currency(self):
		fixtures.set_currency(self.currency)

		self.assertEqual(fixtures.make_payment_form(self.report.name, self.node).currency, self.currency)

	def test_the_society_beats_the_sites_global_default(self):
		"""The framework's pre-filled value is overwritten, not accepted."""
		fixtures.set_currency(self.currency)
		blank = frappe.new_doc(fixtures.PAYMENT_DOCTYPE)

		if not blank.currency:
			self.skipTest("this site has no global currency default for the society's answer to beat")

		self.assertNotEqual(blank.currency, self.currency)
		self.assertEqual(fixtures.make_payment_form(self.report.name, self.node).currency, self.currency)

	def test_an_unconfigured_society_gets_an_empty_currency_rather_than_a_guess(self):
		fixtures.set_currency(None)

		self.assertFalse(fixtures.make_payment_form(self.report.name, self.node).currency)

	def test_an_existing_forms_currency_is_not_rewritten_later(self):
		"""Its amounts were typed in it. A society changing its answer is not a repricing."""
		fixtures.set_currency(self.currency)
		form = fixtures.make_payment_form(self.report.name, self.node)

		fixtures.set_currency(self.was)
		form.save()

		self.assertEqual(form.currency, self.currency)

	def test_the_line_amount_is_denominated_in_the_forms_currency(self):
		"""Read from the schema: the child's Currency field points at the parent's."""
		field = frappe.get_meta(fixtures.LINE_DOCTYPE).get_field("stipend_amount")

		self.assertEqual(field.fieldtype, "Currency")
		self.assertEqual(field.options, "currency")
