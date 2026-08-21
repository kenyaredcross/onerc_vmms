# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""When a volunteer can serve, and what a deployment's dates make of it.

`matching.py` carried availability in `PENDING_CRITERIA` from the beginning:
"a structured selector on the volunteer register, but nothing here asks it a
question yet". `volunteer/services/availability.py` is the module that asks it,
and these are the claims it stands on.

The load-bearing one is that **silence is not a no**. A register where hardly
anybody has written a schedule must not read as a register where hardly anybody
is free, so the answer is three-way and `unknown` is a first-class one.
"""

import frappe

from vmmsx.volunteer.services import availability
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase


class AvailabilityTestCase(VolunteerTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.mornings = cls.slot("mornings", "Mornings", "08:00:00", "12:00:00")
		cls.afternoons = cls.slot("afternoons", "Afternoons", "13:00:00", "17:00:00")

	@classmethod
	def slot(cls, key: str, label: str, opens: str, closes: str) -> str:
		name = f"{fixtures.TEST_PREFIX}-{key}"

		if frappe.db.exists("VMMS Availability Slot", name):
			frappe.delete_doc("VMMS Availability Slot", name, force=True)

		return (
			frappe.get_doc(
				{
					"doctype": "VMMS Availability Slot",
					"slot_key": name,
					"slot_name": label,
					"is_active": 1,
					"start_time": opens,
					"end_time": closes,
				}
			)
			.insert()
			.name
		)

	def volunteer(self, first: str = "Ava", last: str = "Ilable") -> str:
		return fixtures.make_volunteer(fixtures.make_profile(first, last), self.society_a["ward"]).name

	def schedule(self, volunteer: str, *days, **kwargs) -> dict:
		"""A weekly pattern of (day, slot) pairs."""
		return availability.set_schedule(
			volunteer,
			days=[{"day": day, "availability_slot": slot} for day, slot in days],
			**kwargs,
		)


class TestTheSlotCarriesTheHours(AvailabilityTestCase):
	def test_a_window_that_closes_before_it_opens_is_refused(self):
		"""An overnight window is two slots, and the refusal says so.

		A single row from 22:00 to 06:00 would belong to two days at once, and a
		schedule row saying "Tuesday, Night" could then mean Tuesday evening,
		Wednesday morning, or both, with nothing on the record to say which.
		"""
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "VMMS Availability Slot",
					"slot_key": f"{fixtures.TEST_PREFIX}-overnight",
					"slot_name": "Overnight",
					"start_time": "22:00:00",
					"end_time": "06:00:00",
				}
			).insert()

	def test_a_slot_with_no_hours_is_still_ordinary(self):
		"""Every behaviour a society had before the hours existed still works."""
		slot = frappe.get_doc(
			{
				"doctype": "VMMS Availability Slot",
				"slot_key": f"{fixtures.TEST_PREFIX}-anytime",
				"slot_name": "Any time",
			}
		).insert()

		self.assertIsNone(slot.start_time)


class TestTheGridsColumns(AvailabilityTestCase):
	def test_only_windows_with_hours_are_columns(self):
		"""The seam between the two things this app calls availability.

		A day-scoped slot like "Weekend Mornings" is a fine tag to pick at intake
		and nonsense as a column in a grid whose rows are already the seven days.
		The hours are what promote a slot from a label to a schedulable window.
		"""
		labelled = (
			frappe.get_doc(
				{
					"doctype": "VMMS Availability Slot",
					"slot_key": f"{fixtures.TEST_PREFIX}-weekend-mornings",
					"slot_name": "Weekend Mornings",
					"is_active": 1,
				}
			)
			.insert()
			.name
		)

		columns = {row["name"] for row in availability.slots()}

		self.assertIn(self.mornings, columns)
		self.assertNotIn(labelled, columns)

	def test_the_columns_read_across_the_day(self):
		"""Sorted on the time itself, never on its string form.

		A Time comes back as a `timedelta`, whose string form has no leading zero,
		so `"8:00:00" > "12:00:00"` and the morning column would land at the end of
		the day.
		"""
		ordered = [row["name"] for row in availability.slots()]

		self.assertLess(ordered.index(self.mornings), ordered.index(self.afternoons))

	def test_a_retired_window_is_not_offered(self):
		retired = (
			frappe.get_doc(
				{
					"doctype": "VMMS Availability Slot",
					"slot_key": f"{fixtures.TEST_PREFIX}-retired",
					"slot_name": "Retired",
					"is_active": 0,
					"start_time": "06:00:00",
					"end_time": "08:00:00",
				}
			)
			.insert()
			.name
		)

		self.assertNotIn(retired, {row["name"] for row in availability.slots()})


class TestSilenceIsNotANo(AvailabilityTestCase):
	def test_a_volunteer_with_no_schedule_is_unknown(self):
		answer = availability.assess(self.volunteer(), "2026-09-05", "2026-09-06")

		self.assertEqual(answer["state"], availability.UNKNOWN)
		self.assertFalse(answer["is_available"])
		self.assertFalse(answer["is_unavailable"])
		self.assertFalse(answer["is_known"])

	def test_unknown_is_not_available(self):
		"""The two are different, and a caller has to choose between them.

		`is_available` is false for `unknown` on purpose: a caller who means "do
		not rule this person out" asks `not is_unavailable`, and having to pick
		one is what stops a screen quietly treating silence as a yes.
		"""
		answer = availability.assess(self.volunteer(), "2026-09-05", "2026-09-06")

		self.assertFalse(answer["is_available"])
		self.assertNotEqual(answer["state"], availability.AVAILABLE)

	def test_a_schedule_that_does_not_cover_the_dates_is_unknown_not_no(self):
		"""A pattern that expired describes nothing about these days."""
		volunteer = self.volunteer()
		self.schedule(volunteer, ("Saturday", self.mornings), valid_to="2026-01-31")

		answer = availability.assess(volunteer, "2026-09-05", "2026-09-05")

		self.assertEqual(answer["state"], availability.UNKNOWN)


class TestEveryDayHasToBeCovered(AvailabilityTestCase):
	def test_a_saturday_deployment_matches_a_saturday_volunteer(self):
		volunteer = self.volunteer()
		self.schedule(volunteer, ("Saturday", self.mornings))

		answer = availability.assess(volunteer, "2026-09-05", "2026-09-05")

		self.assertEqual(answer["state"], availability.AVAILABLE)
		self.assertEqual(answer["slots"], [self.mornings])

	def test_a_weekend_deployment_needs_both_days(self):
		"""Not "free on at least one of these days", which would put people on
		deployments they had said they could not do most of."""
		volunteer = self.volunteer()
		self.schedule(volunteer, ("Saturday", self.mornings))

		answer = availability.assess(volunteer, "2026-09-05", "2026-09-06")

		self.assertEqual(answer["state"], availability.UNAVAILABLE)
		self.assertEqual(answer["missing_days"], ["Sunday"])

	def test_the_refusal_names_the_days(self):
		"""A coordinator sees "not free on Sunday", not a bare no."""
		volunteer = self.volunteer()
		self.schedule(volunteer, ("Saturday", self.mornings))

		answer = availability.assess(volunteer, "2026-09-05", "2026-09-06")

		self.assertIn("Sunday", answer["why"])

	def test_a_deployment_of_a_week_or_more_needs_every_weekday(self):
		volunteer = self.volunteer()
		self.schedule(
			volunteer,
			*[(day, self.mornings) for day in availability.DAYS],
		)

		answer = availability.assess(volunteer, "2026-09-01", "2026-09-30")

		self.assertEqual(answer["state"], availability.AVAILABLE)

	def test_one_missing_weekday_sinks_a_long_deployment(self):
		volunteer = self.volunteer()
		self.schedule(
			volunteer,
			*[(day, self.mornings) for day in availability.DAYS if day != "Wednesday"],
		)

		answer = availability.assess(volunteer, "2026-09-01", "2026-09-30")

		self.assertEqual(answer["state"], availability.UNAVAILABLE)
		self.assertEqual(answer["missing_days"], ["Wednesday"])


class TestThePeriodTheScheduleHolds(AvailabilityTestCase):
	def test_a_schedule_with_no_period_holds_always(self):
		volunteer = self.volunteer()
		self.schedule(volunteer, ("Saturday", self.mornings))

		self.assertEqual(
			availability.assess(volunteer, "2030-09-07", "2030-09-07")["state"],
			availability.AVAILABLE,
		)

	def test_a_partial_overlap_is_not_a_yes(self):
		"""A pattern that expires halfway through a deployment does not describe it.

		Treating a partial overlap as a yes would put somebody on the second week
		of a fortnight they had said they were only free for the first of.
		"""
		volunteer = self.volunteer()
		self.schedule(
			volunteer,
			*[(day, self.mornings) for day in availability.DAYS],
			valid_to="2026-09-10",
		)

		answer = availability.assess(volunteer, "2026-09-05", "2026-09-20")

		self.assertEqual(answer["state"], availability.UNKNOWN)

	def test_a_schedule_ending_before_it_starts_is_refused(self):
		volunteer = self.volunteer()

		with self.assertRaises(frappe.ValidationError):
			self.schedule(
				volunteer,
				("Saturday", self.mornings),
				valid_from="2026-09-10",
				valid_to="2026-09-01",
			)


class TestWritingOne(AvailabilityTestCase):
	def test_writing_replaces_rather_than_merges(self):
		"""The one thing a grid of tick boxes has to be able to do is un-tick."""
		volunteer = self.volunteer()
		self.schedule(volunteer, ("Saturday", self.mornings), ("Sunday", self.mornings))

		after = self.schedule(volunteer, ("Saturday", self.mornings))

		self.assertEqual(len(after["days"]), 1)
		self.assertEqual(after["days"][0]["day"], "Saturday")

	def test_one_schedule_per_volunteer(self):
		volunteer = self.volunteer()
		self.schedule(volunteer, ("Saturday", self.mornings))
		self.schedule(volunteer, ("Sunday", self.mornings))

		self.assertEqual(frappe.db.count("VMMS Availability Schedule", {"volunteer": volunteer}), 1)

	def test_the_same_day_and_window_twice_is_refused(self):
		volunteer = self.volunteer()

		with self.assertRaises(frappe.DuplicateEntryError):
			self.schedule(volunteer, ("Saturday", self.mornings), ("Saturday", self.mornings))

	def test_a_volunteer_with_no_schedule_still_has_a_shape_to_render(self):
		"""The grid draws the same either way rather than testing for existence."""
		answer = availability.dto(self.volunteer())

		self.assertFalse(answer["exists"])
		self.assertEqual(answer["days"], [])


class TestThroughTheVolunteersOwnDoor(AvailabilityTestCase):
	def test_a_volunteer_writes_and_reads_their_own(self):
		"""The case an ordinary save gets wrong.

		A volunteer holds no Geo Assignment and no permission on their own
		schedule, so the permission layer refuses the only person whose answer
		this is. What admits them is that the endpoint takes no argument naming
		anybody, and this is the test that fails if the elevated save goes.
		"""
		from vmmsx.api import volunteer as api

		user = fixtures.make_user("scheduling-volunteer")
		volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Sched", "Uler", email=user, user=user),
			self.society_a["ward"],
		).name

		with fixtures.acting_as(user):
			api.set_my_availability(
				days=[{"day": "Saturday", "availability_slot": self.mornings}],
				available_on_holidays=1,
			)
			mine = api.my_availability()

		self.assertEqual(mine["volunteer"], volunteer)
		self.assertTrue(mine["available_on_holidays"])
		self.assertEqual(len(mine["days"]), 1)

	def test_the_society_windows_come_back_with_it(self):
		"""The screen is a grid of days against windows; it cannot draw its own columns."""
		from vmmsx.api import volunteer as api

		user = fixtures.make_user("reading-volunteer")
		fixtures.make_volunteer(
			fixtures.make_profile("Read", "Only", email=user, user=user),
			self.society_a["ward"],
		)

		with fixtures.acting_as(user):
			mine = api.my_availability()

		self.assertIn(self.mornings, {row["name"] for row in mine["slots"]})

	def test_unticking_holidays_over_http_is_not_a_tick(self):
		"""`"false"` is a truthy string, and this is the wrong field to get backwards."""
		from vmmsx.api import volunteer as api

		user = fixtures.make_user("holiday-volunteer")
		fixtures.make_volunteer(
			fixtures.make_profile("Holi", "Day", email=user, user=user),
			self.society_a["ward"],
		)

		with fixtures.acting_as(user):
			api.set_my_availability(days=[], available_on_holidays="true")
			api.set_my_availability(days=[], available_on_holidays="false")
			mine = api.my_availability()

		self.assertFalse(mine["available_on_holidays"])

	def test_somebody_who_is_not_a_volunteer_gets_none(self):
		from vmmsx.api import volunteer as api

		user = fixtures.make_user("not-a-volunteer")

		with fixtures.acting_as(user):
			self.assertIsNone(api.my_availability())


class TestTheTwoListsOfDaysStayInStep(AvailabilityTestCase):
	def test_the_doctype_and_the_module_name_the_same_seven_days(self):
		"""`DAYS` is indexed by `datetime.weekday()` and the Select is what a
		volunteer picks from. Reorder one and not the other and every schedule
		silently starts meaning a different day, with nothing else to notice."""
		availability.assert_days_match()
