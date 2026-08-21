# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What the landing page is allowed to ask for before anybody has signed in.

The public home page draws two things it used to have typed into it: how many
volunteers the society has, and what is on soon. Both are now reads, and a read
served to a signed-out visitor is the kind of change worth a suite of its own —
not because either answer is sensitive, but because "guest-readable" is a
property that has to be *decided* each time rather than inherited from the
endpoint next door.

So three things are asserted here:

* **the figure is the register's**, counting the people who are currently
  volunteers and nobody else, and approximated on the way out so a public page
  never publishes an exact headcount;
* **the teaser is a teaser**, capped at three, with no way to ask it for the
  society's whole calendar;
* **both are guest-readable and their neighbours are not**, checked against
  Frappe's own registry rather than by calling them, because the decorator is
  the thing under test.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.api import events as events_api
from vmmsx.api import society
from vmmsx.buzz.services import events as seam
from vmmsx.buzz.tests.test_events import PREFIX, EventFixtures
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase


class TestAPublicFigureIsApproximate(IntegrationTestCase):
	"""The rounding rule, on its own and away from the database.

	It is a rule about what a society is willing to claim in public, so the
	table below is the specification rather than an illustration of it: every
	boundary in `approximate` has a case either side of it.
	"""

	def test_nobody_on_the_register_says_nothing_at_all(self):
		"""Not "0". The strip drops the slot rather than announcing a nought on
		the front page, the same as an unfilled statistic."""
		self.assertEqual(society.approximate(0), "")

	def test_a_negative_count_is_treated_as_nobody(self):
		"""Impossible from `frappe.db.count`, and still not a reason to render a
		minus sign on a national society's home page."""
		self.assertEqual(society.approximate(-3), "")

	def test_a_small_society_is_counted_exactly_and_claims_no_more(self):
		"""Eleven volunteers rounded to "10+" would be both less true and less
		impressive. Below fifty the figure is simply the figure."""
		self.assertEqual(society.approximate(1), "1")
		self.assertEqual(society.approximate(11), "11")
		self.assertEqual(society.approximate(49), "49")

	def test_fifty_is_where_rounding_starts(self):
		self.assertEqual(society.approximate(50), "50+")
		self.assertEqual(society.approximate(58), "50+")

	def test_hundreds_round_to_ten(self):
		self.assertEqual(society.approximate(284), "280+")
		self.assertEqual(society.approximate(999), "990+")

	def test_thousands_round_to_a_hundred(self):
		self.assertEqual(society.approximate(1_000), "1,000+")
		self.assertEqual(society.approximate(1_284), "1,200+")
		self.assertEqual(society.approximate(9_999), "9,900+")

	def test_ten_thousand_and_up_rounds_to_a_thousand(self):
		self.assertEqual(society.approximate(10_000), "10,000+")
		self.assertEqual(society.approximate(41_300), "41,000+")

	def test_it_only_ever_rounds_down(self):
		"""The claim has to be true on the day it is read. A figure rounded up is
		a society saying it has people it does not have."""
		for count in (50, 51, 284, 1_284, 41_300):
			self.assertLessEqual(int(society.approximate(count).rstrip("+").replace(",", "")), count)


class TestTheVolunteerFigureCountsTheRegister(VolunteerTestCase):
	"""Which rows the figure is built from, on a real register.

	The status matters more than the arithmetic: `Prospective` has not been
	verified, `Suspended` is not serving and `Exited` has left, and a public
	figure counting any of them is a society overstating its strength. The
	counts are compared as *deltas* against what the bench already holds, so the
	suite says nothing about how many volunteers this site happens to have.
	"""

	def active(self) -> int:
		return frappe.db.count(society.VOLUNTEER_DOCTYPE, {"status": society.ACTIVE})

	def make(self, handle: str, status: str) -> None:
		"""One volunteer on the register, at a given status.

		Through the module's own fixtures rather than a bare insert, because a
		volunteer that is not a real person placed at a real branch is not a row
		`VMMS Volunteer` will accept — and a count built on rows the product
		refuses would prove nothing about the count on a live site.
		"""
		volunteer = fixtures.make_volunteer(fixtures.make_profile(handle, "Counted"), self.society_a["ward"])
		volunteer.status = status
		volunteer.save(ignore_permissions=True)

	def test_an_active_volunteer_is_counted(self):
		before = self.active()
		self.make("Active", society.ACTIVE)

		self.assertEqual(self.active(), before + 1)

	def test_everybody_else_on_the_register_is_not(self):
		before = self.active()

		for status in ("Prospective", "Suspended", "Exited"):
			self.make(status, status)

		self.assertEqual(self.active(), before)

	def test_the_endpoint_returns_the_approximated_count_and_nothing_else(self):
		answer = society.figures()

		self.assertEqual(set(answer), {"volunteers"})
		self.assertEqual(answer["volunteers"], society.approximate(self.active()))

	def test_the_exact_headcount_never_leaves_the_endpoint(self):
		"""The reason the rounding is on this side. A response carrying the real
		number would publish it whatever the page then did with it."""
		self.make("Exact", society.ACTIVE)
		exact = self.active()

		if exact < 50:
			self.skipTest("this bench's register is small enough to be reported exactly")

		self.assertNotIn(str(exact), society.figures()["volunteers"])


class TestTheEventTeaserStaysATeaser(EventFixtures):
	"""Three events for a stranger, and no way to ask for the fourth."""

	def test_it_answers_with_what_is_on(self):
		self.make_event("Teaser one")

		titles = [row["title"] for row in events_api.teaser()["events"]]

		self.assertTrue(titles)

	def test_it_stops_at_three_however_many_are_published(self):
		for index in range(5):
			self.make_event(f"Teaser {index}")

		self.assertLessEqual(len(events_api.teaser()["events"]), events_api.TEASER_ROWS)

	def test_it_takes_no_arguments(self):
		"""The cap is a constant rather than a default, so there is no limit for
		a caller to talk their way past."""
		import inspect

		self.assertEqual(list(inspect.signature(events_api.teaser).parameters), [])

	def test_it_says_whether_buzz_is_there_at_all(self):
		"""The page decides once what to draw. "No events because the app is
		absent" and "no events because none are scheduled" are different
		sentences and the answer carries both."""
		self.assertEqual(events_api.teaser()["available"], seam.is_available())

	def test_an_unpublished_event_is_not_teased(self):
		"""The boundary is Buzz's own `is_published`, the same flag its public
		pages read. Nothing here is disclosed that Buzz has not already."""
		self.make_event("Teaser secret", is_published=0)

		titles = [row["title"] for row in events_api.teaser()["events"]]

		self.assertNotIn(f"{PREFIX} Teaser secret", titles)


class TestOnlyTheLandingPageReadsAreOpenToStrangers(IntegrationTestCase):
	"""Which endpoints a signed-out visitor may call, asserted against Frappe's
	own registry.

	`frappe.guest_methods` is what `is_whitelisted` consults, so this is the
	decision itself rather than a description of it. The negative half is the
	half that matters: the events module has seven other endpoints and every one
	of them has to stay shut, or "browse here, join to see the rest" is a
	sentence the software does not actually mean.
	"""

	def assertOpen(self, function):
		self.assertIn(function, frappe.guest_methods, f"{function.__name__} should be guest-readable")

	def assertShut(self, function):
		self.assertNotIn(function, frappe.guest_methods, f"{function.__name__} must refuse a guest")

	def test_the_two_landing_reads_are_open(self):
		self.assertOpen(society.branding)
		self.assertOpen(society.figures)
		self.assertOpen(events_api.teaser)

	def test_the_rest_of_the_events_module_is_shut(self):
		for function in (
			events_api.upcoming,
			events_api.detail,
			events_api.attending,
			events_api.attend,
			events_api.cancel_attendance,
			events_api.calendar,
			events_api.filters,
		):
			self.assertShut(function)
