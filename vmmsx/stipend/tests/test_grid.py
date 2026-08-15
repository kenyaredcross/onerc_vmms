# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The daily attendance grid: what it answers, and what it refuses.

The grid is one row per volunteer per day. That shape was chosen for two
questions, and both are asserted here rather than argued for in a comment:

1. **What is payable to one volunteer for the period?** A sum over that
   volunteer's rows, computed on request and stored nowhere, so it cannot
   disagree with the rows it sums.
2. **Who attended on day X?** A filter on one column, working within a form and
   across every form the caller may read. This is the question a wide table —
   a column per day — cannot answer at all, and the reason the tall shape earns
   its keep.

The refusals are the rules that hold for every society: you cannot pay somebody
the report never mentioned, cannot pay for a day outside the period, cannot pay
somebody twice for one day, cannot pay a negative amount, and cannot pay a daily
stipend for a day somebody was absent.

**No amount is ever computed.** There is no rate anywhere in this module, and
`hours` is recorded and multiplied by nothing.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.stipend.services import attendance
from vmmsx.stipend.services import payment as payment_service
from vmmsx.stipend.services import report as report_service
from vmmsx.stipend.tests import fixtures
from vmmsx.stipend.tests.base import StipendTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class GridTestCase(StipendTestCase):
	def setUp(self):
		super().setUp()
		self.node = self.society_a["ward"]
		self.amina = self.volunteer_at(self.node, "Amina", "Grid")
		self.otieno = self.volunteer_at(self.node, "Otieno", "Grid")
		self.report = fixtures.make_report(self.node, [self.amina.name, self.otieno.name])

	def day(self, offset: int = 0):
		return add_days(today(), offset)

	def form(self, lines):
		return fixtures.make_payment_form(self.report.name, self.node, lines)


class TestTotalPayablePerVolunteer(GridTestCase):
	"""The first question the shape was chosen for."""

	def setUp(self):
		super().setUp()
		self.payment_form = self.form(
			[
				fixtures.line(self.amina.name, self.day(0), amount=500, hours=6),
				fixtures.line(self.amina.name, self.day(1), amount=500, hours=6),
				fixtures.line(self.amina.name, self.day(2), amount=250, hours=3),
				fixtures.line(self.otieno.name, self.day(0), amount=500, hours=6),
				fixtures.line(self.otieno.name, self.day(2), amount=0, attended=False),
			]
		)

	def test_each_volunteer_is_totalled_over_their_own_days(self):
		totals = {row["volunteer"]: row for row in attendance.per_volunteer(self.payment_form)}

		self.assertEqual(totals[self.amina.name]["total_payable"], 1250)
		self.assertEqual(totals[self.otieno.name]["total_payable"], 500)

	def test_days_recorded_and_days_attended_are_different_numbers(self):
		"""An absence is recorded, counted, and paid nothing."""
		totals = {row["volunteer"]: row for row in attendance.per_volunteer(self.payment_form)}

		self.assertEqual(totals[self.otieno.name]["days_recorded"], 2)
		self.assertEqual(totals[self.otieno.name]["days_attended"], 1)

	def test_hours_are_summed_and_never_multiplied_by_anything(self):
		totals = {row["volunteer"]: row for row in attendance.per_volunteer(self.payment_form)}

		self.assertEqual(totals[self.amina.name]["hours"], 15)
		self.assertEqual(totals[self.amina.name]["total_payable"], 1250)

	def test_the_form_total_is_the_sum_of_every_line(self):
		self.assertEqual(self.payment_form.total_payable, 1750)

	def test_the_total_is_derived_on_every_save_and_not_typed(self):
		"""A typed total is overwritten, because the rows are the truth."""
		self.payment_form.total_payable = 999999
		self.payment_form.save()

		self.assertEqual(self.reload_form(self.payment_form.name).total_payable, 1750)

	def test_removing_a_day_lowers_that_volunteers_total(self):
		payment_service.remove_line(self.payment_form, self.amina.name, self.day(2))
		self.payment_form.save()

		self.assertEqual(attendance.payable_to(self.payment_form, self.amina.name), 1000)
		self.assertEqual(self.reload_form(self.payment_form.name).total_payable, 1500)

	def test_a_volunteer_the_form_never_names_is_owed_nothing(self):
		other = self.volunteer_at(self.node, "Absent", "Entirely")

		self.assertEqual(attendance.payable_to(self.payment_form, other.name), 0)

	def test_no_per_volunteer_total_is_stored_anywhere(self):
		"""Derived on request. A stored one would one day disagree with the rows."""
		fieldnames = {field.fieldname for field in frappe.get_meta(fixtures.REPORT_VOLUNTEER_DOCTYPE).fields}

		self.assertNotIn("total_payable", fieldnames)
		self.assertNotIn("stipend_amount", fieldnames)


class TestWhoAttendedOnADay(GridTestCase):
	"""The second question, and the one a wide table could not answer."""

	def setUp(self):
		super().setUp()
		self.payment_form = self.form(
			[
				fixtures.line(self.amina.name, self.day(0), amount=500),
				fixtures.line(self.otieno.name, self.day(0), amount=500),
				fixtures.line(self.amina.name, self.day(3), amount=500),
				fixtures.line(self.otieno.name, self.day(3), amount=0, attended=False),
			]
		)

	def test_a_day_returns_the_people_who_were_there(self):
		self.assertEqual(
			attendance.attended_on(self.payment_form, self.day(0)),
			sorted([self.amina.name, self.otieno.name]),
		)

	def test_a_day_somebody_was_absent_returns_only_the_others(self):
		self.assertEqual(attendance.attended_on(self.payment_form, self.day(3)), [self.amina.name])

	def test_a_day_with_no_lines_returns_nobody_rather_than_everybody(self):
		self.assertEqual(attendance.attended_on(self.payment_form, self.day(5)), [])

	def test_the_dto_separates_attended_from_absent(self):
		answer = payment_service.attendance_on(self.payment_form, self.day(3))

		self.assertEqual(answer["attended"], [self.amina.name])
		self.assertEqual(answer["absent"], [self.otieno.name])

	def test_the_question_can_be_asked_of_the_whole_register(self):
		"""Across forms, which is the query the tall shape exists for."""
		second_report = fixtures.make_report(self.society_a["other_ward"], [self.amina.name])
		second_form = fixtures.make_payment_form(
			second_report.name,
			self.society_a["other_ward"],
			[fixtures.line(self.amina.name, self.day(0), amount=100)],
		)

		forms = {row["payment_form"] for row in attendance.register_on(self.day(0))}

		self.assertIn(self.payment_form.name, forms)
		self.assertIn(second_form.name, forms, "the register-wide question did not cross forms")

	def test_the_register_question_ignores_days_nobody_worked(self):
		self.assertEqual(attendance.register_on(self.day(5)), [])


class TestTheGridRefusesWhatCannotBePaid(GridTestCase):
	"""One rule per test, and each fails for its own reason."""

	def test_a_volunteer_who_is_not_on_the_report_cannot_be_paid(self):
		stranger = self.volunteer_at(self.node, "Stranger", "ToTheReport")

		with self.assertRaises(frappe.ValidationError) as caught:
			self.form([fixtures.line(stranger.name, self.day(0), amount=500)])

		self.assertIn("progress report", str(caught.exception).lower())

	def test_a_day_outside_the_period_cannot_be_paid(self):
		with self.assertRaises(frappe.ValidationError):
			self.form([fixtures.line(self.amina.name, self.day(30), amount=500)])

	def test_a_day_before_the_period_cannot_be_paid_either(self):
		with self.assertRaises(frappe.ValidationError):
			self.form([fixtures.line(self.amina.name, self.day(-5), amount=500)])

	def test_one_volunteer_cannot_have_two_lines_for_one_day(self):
		with self.assertRaises(frappe.ValidationError):
			self.form(
				[
					fixtures.line(self.amina.name, self.day(0), amount=500),
					fixtures.line(self.amina.name, self.day(0), amount=500),
				]
			)

	def test_two_volunteers_may_share_a_day(self):
		"""The rule is one line per volunteer per day, not one line per day."""
		self.assertTrue(
			self.form(
				[
					fixtures.line(self.amina.name, self.day(0), amount=500),
					fixtures.line(self.otieno.name, self.day(0), amount=500),
				]
			).name
		)

	def test_a_negative_amount_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.form([fixtures.line(self.amina.name, self.day(0), amount=-1)])

	def test_an_absence_cannot_carry_a_stipend(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			self.form([fixtures.line(self.amina.name, self.day(0), amount=500, attended=False)])

		self.assertIn("absent", str(caught.exception).lower())

	def test_an_absence_with_no_amount_is_ordinary(self):
		self.assertTrue(
			self.form([fixtures.line(self.amina.name, self.day(0), amount=0, attended=False)]).name
		)

	def test_a_line_with_no_day_is_refused(self):
		with self.assertRaises(frappe.MandatoryError):
			self.form([{"volunteer": self.amina.name, "stipend_amount": 500}])

	def test_nothing_is_saved_when_a_line_is_refused(self):
		before = frappe.db.count(fixtures.PAYMENT_DOCTYPE)

		with self.assertRaises(frappe.ValidationError):
			self.form([fixtures.line(self.amina.name, self.day(30), amount=500)])

		self.assertEqual(frappe.db.count(fixtures.PAYMENT_DOCTYPE), before)


class TestAddingALineThroughTheService(GridTestCase):
	"""The door a caller actually uses. Idempotent, and checked twice over."""

	def setUp(self):
		super().setUp()
		self.payment_form = self.form([])

	def test_a_day_is_recorded(self):
		self.assertTrue(
			payment_service.add_line(self.payment_form, self.amina.name, self.day(0), stipend_amount=400)
		)
		self.payment_form.save()

		self.assertEqual(attendance.payable_to(self.payment_form, self.amina.name), 400)

	def test_recording_the_same_day_twice_replaces_it_rather_than_doubling_it(self):
		payment_service.add_line(self.payment_form, self.amina.name, self.day(0), stipend_amount=400)
		payment_service.add_line(self.payment_form, self.amina.name, self.day(0), stipend_amount=600)
		self.payment_form.save()

		self.assertEqual(len(attendance.lines(self.payment_form)), 1)
		self.assertEqual(attendance.payable_to(self.payment_form, self.amina.name), 600)

	def test_an_unchanged_repeat_reports_that_it_changed_nothing(self):
		payment_service.add_line(self.payment_form, self.amina.name, self.day(0), stipend_amount=400)

		self.assertFalse(
			payment_service.add_line(self.payment_form, self.amina.name, self.day(0), stipend_amount=400)
		)

	def test_somebody_not_on_the_report_is_refused_before_anything_is_appended(self):
		stranger = self.volunteer_at(self.node, "Stranger", "ToTheService")

		with self.assertRaises(frappe.ValidationError):
			payment_service.add_line(self.payment_form, stranger.name, self.day(0), stipend_amount=400)

		self.assertEqual(attendance.lines(self.payment_form), [])

	def test_removing_a_day_that_is_not_there_changes_nothing(self):
		self.assertFalse(payment_service.remove_line(self.payment_form, self.amina.name, self.day(0)))


class TestTheReportCannotLeaveAFormPayingAGhost(GridTestCase):
	"""The one question that runs from the form back to the report."""

	def setUp(self):
		super().setUp()
		self.payment_form = self.form([fixtures.line(self.amina.name, self.day(0), amount=400)])

	def test_a_volunteer_being_paid_cannot_be_taken_off_the_report(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			report_service.remove_volunteer(self.report, self.amina.name)

		self.assertIn(self.payment_form.name, str(caught.exception))

	def test_a_volunteer_the_form_does_not_pay_can_be(self):
		self.assertTrue(report_service.remove_volunteer(self.report, self.otieno.name))

	def test_they_can_be_removed_once_their_days_are_off_the_form(self):
		payment_service.remove_line(self.payment_form, self.amina.name, self.day(0))
		self.payment_form.save()

		self.assertTrue(report_service.remove_volunteer(self.report, self.amina.name))

	def test_the_form_would_otherwise_have_been_left_unsaveable(self):
		"""The state this rule exists to prevent, demonstrated on the form itself."""
		self.report.volunteers = [row for row in self.report.volunteers if row.volunteer != self.amina.name]
		self.report.save()

		with self.assertRaises(frappe.ValidationError):
			self.reload_form(self.payment_form.name).save()


class TestTheGridIsTallAndNotWide(GridTestCase):
	"""The shape, asserted against the schema rather than described in a comment."""

	def test_a_line_is_keyed_by_a_volunteer_and_a_date(self):
		meta = frappe.get_meta(fixtures.LINE_DOCTYPE)

		self.assertEqual(meta.get_field("volunteer").fieldtype, "Link")
		self.assertEqual(meta.get_field("volunteer").options, fixtures.VOLUNTEER_DOCTYPE)
		self.assertEqual(meta.get_field("attendance_date").fieldtype, "Date")
		self.assertTrue(meta.get_field("attendance_date").reqd)

	def test_the_line_carries_no_day_columns(self):
		"""A column per day would put the calendar in the schema.

		Asserted as an exact set rather than a pattern match: anything added to
		this table is a deliberate decision about the grid's shape, and has to be
		made here as well as in the JSON.
		"""
		fieldnames = {
			field.fieldname
			for field in frappe.get_meta(fixtures.LINE_DOCTYPE).fields
			if field.fieldtype not in ("Section Break", "Column Break")
		}

		self.assertEqual(fieldnames, {"volunteer", "attendance_date", "attended", "hours", "stipend_amount"})

	def test_a_period_longer_than_any_guessed_column_count_still_works(self):
		"""Forty days. A wide table would have run out of columns; this does not."""
		long_report = fixtures.make_report(
			self.node, [self.amina.name], period_from=today(), period_to=add_days(today(), 39)
		)
		form = fixtures.make_payment_form(
			long_report.name,
			self.node,
			[fixtures.line(self.amina.name, self.day(offset), amount=100) for offset in range(40)],
		)

		self.assertEqual(len(attendance.lines(form)), 40)
		self.assertEqual(form.total_payable, 4000)
		self.assertEqual(attendance.attended_on(form, self.day(39)), [self.amina.name])
