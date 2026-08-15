# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""BUZZ-02 — what the portal reads out of Buzz, and where it stops.

Two things are being protected here and they pull in opposite directions.

**The listing has to be right**, because the portal shows it to volunteers as
the society's own calendar: an unpublished event appearing is a leak, a finished
one appearing is clutter, and a multi-day event vanishing on its second morning
is the bug nobody notices until somebody misses a training.

**The listing has to stay a listing.** The seam reads title, date, venue,
category, image and route, and hands off. `test_delegation.py` already asserts
that no ticketing or attendee doctype is named anywhere in the app; what is
asserted here is the positive half — that the DTO carries a link to Buzz's own
page, so the handoff is a real destination rather than an intention.

Real Buzz events on a real bench. Skipped entirely, rather than mocked, on a
site without Buzz: a mocked Buzz would test this app's idea of Buzz's schema,
which is exactly the thing that goes stale.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from vmmsx.buzz.services import events, geo

EXTRA_TEST_RECORD_DEPENDENCIES = []

PREFIX = "EVTTEST"

HOST_DOCTYPE = "Event Host"


class EventFixtures(IntegrationTestCase):
	"""Real Buzz events on a real bench, shared by both readers.

	Fixtures only — no test lives here, so the classes below get the same idea of
	what a test event is without either of them re-running the other's suite.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		if not events.is_available():
			return

		from onerc_core.geo.tests import fixtures as geo_fixtures

		cls.region_level = geo_fixtures.make_level(f"{PREFIX}-1", "Region", 1)
		cls.branch_level = geo_fixtures.make_level(f"{PREFIX}-2", "Branch", 2, is_lowest=True)
		cls.region = geo_fixtures.make_node(f"{PREFIX} Region", cls.region_level, None)
		cls.branch = geo_fixtures.make_node(f"{PREFIX} Branch", cls.branch_level, cls.region)
		cls.elsewhere = geo_fixtures.make_node(f"{PREFIX} Elsewhere", cls.branch_level, cls.region)

		cls.host = frappe.get_doc({"doctype": HOST_DOCTYPE, "name": f"{PREFIX} Host"}).insert(
			ignore_permissions=True
		)

		cls.category = (
			frappe.db.get_value("Event Category", {"enabled": 1}, "name")
			or frappe.get_doc({"doctype": "Event Category", "name": f"{PREFIX} Category"})
			.insert(ignore_permissions=True)
			.name
		)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()

		if not events.is_available():
			self.skipTest("Buzz is not installed on this site")

		self.addCleanup(frappe.set_user, "Administrator")

	def make_event(self, title: str, **overrides) -> str:
		values = {
			"doctype": geo.EVENT_DOCTYPE,
			"title": f"{PREFIX} {title}",
			"start_date": add_days(today(), 3),
			"start_time": "09:00:00",
			"end_time": "16:00:00",
			"category": self.category,
			"host": self.host.name,
			"is_published": 1,
		}
		values.update(overrides)

		# `str` because Buzz names its events by autoincrement, so a docname off
		# the document is an int while the one the DTO carries is a string. The
		# fixture speaks the DTO's language, which is also the one a URL and a
		# whitelisted call arrive in.
		return str(frappe.get_doc(values).insert(ignore_permissions=True).name)

	def titles(self, **kwargs) -> list[str]:
		"""Only this fixture's events. The bench carries a society's real ones."""
		return [row["title"] for row in events.upcoming(**kwargs) if row["title"].startswith(PREFIX)]

	def one(self, name: str) -> dict:
		return next(row for row in events.upcoming(limit=events.MAX_ROWS) if row["event"] == name)

	def make_venue(self, label: str, address: str) -> str:
		"""Buzz makes a venue's address mandatory, so every one carries one."""
		return (
			frappe.get_doc({"doctype": events.VENUE_DOCTYPE, "name": f"{PREFIX} {label}", "address": address})
			.insert(ignore_permissions=True)
			.name
		)


class TestBuzzEventListing(EventFixtures):
	# --- what appears -------------------------------------------------------

	def test_a_published_upcoming_event_appears(self):
		self.make_event("Soon")

		self.assertIn(f"{PREFIX} Soon", self.titles())

	def test_an_unpublished_event_does_not(self):
		"""Published is Buzz's decision, and it is the whole visibility rule."""
		self.make_event("Hidden", is_published=0)

		self.assertNotIn(f"{PREFIX} Hidden", self.titles())

	def test_a_finished_event_does_not(self):
		self.make_event("Over", start_date=add_days(today(), -30))

		self.assertNotIn(f"{PREFIX} Over", self.titles())

	def test_an_event_under_way_still_does(self):
		"""The case a naive `start_date >= today` filter gets wrong.

		A four-day training that began yesterday is exactly what somebody is
		checking the page for on day two.
		"""
		self.make_event(
			"Running",
			start_date=add_days(today(), -1),
			end_date=add_days(today(), 2),
		)

		self.assertIn(f"{PREFIX} Running", self.titles())

	def test_a_single_day_event_today_appears_without_an_end_date(self):
		"""Buzz leaves `end_date` empty for a one-day event; the OR handles it."""
		self.make_event("Today", start_date=today(), end_date=None)

		self.assertIn(f"{PREFIX} Today", self.titles())

	def test_soonest_first(self):
		self.make_event("Later", start_date=add_days(today(), 20))
		self.make_event("Sooner", start_date=add_days(today(), 2))

		ours = self.titles()

		self.assertLess(ours.index(f"{PREFIX} Sooner"), ours.index(f"{PREFIX} Later"))

	# --- narrowing ----------------------------------------------------------

	def test_search_narrows_on_the_title(self):
		self.make_event("Findable First Aid")
		self.make_event("Unrelated")

		found = self.titles(search="Findable")

		self.assertIn(f"{PREFIX} Findable First Aid", found)
		self.assertNotIn(f"{PREFIX} Unrelated", found)

	def test_an_unplaced_event_is_shown_to_everybody(self):
		"""BUZZ-01 made the anchor optional, so absence cannot mean elsewhere.

		This is the deliberate reverse of ACC-02's rule for vmmsx's own records,
		and filtering unplaced events out would hide most of a society's calendar.
		"""
		self.make_event("Unplaced")

		self.assertIn(f"{PREFIX} Unplaced", self.titles(near=self.branch))

	def test_near_excludes_an_event_anchored_somewhere_else(self):
		self.make_event("Ours", **{geo.GEO_NODE_FIELD: self.branch})
		self.make_event("Theirs", **{geo.GEO_NODE_FIELD: self.elsewhere})

		found = self.titles(near=self.branch)

		self.assertIn(f"{PREFIX} Ours", found)
		self.assertNotIn(f"{PREFIX} Theirs", found)

	def test_near_a_parent_admits_events_beneath_it(self):
		self.make_event("Below", **{geo.GEO_NODE_FIELD: self.branch})

		self.assertIn(f"{PREFIX} Below", self.titles(near=self.region))

	# --- the DTO and the handoff -------------------------------------------

	def test_the_card_carries_a_link_to_buzz_rather_than_a_booking(self):
		"""The positive half of the delegation rule: browse here, book there."""
		name = self.make_event("Linked")
		card = self.one(name)

		route = frappe.db.get_value(geo.EVENT_DOCTYPE, name, "route")

		self.assertTrue(route, "publishing an event should have given it a route")
		self.assertEqual(card["href"], f"{events.EVENT_PATH}/{route}")

	def test_an_event_with_no_route_offers_nowhere_to_go(self):
		"""Better than a button pointing at a 404."""
		self.assertIsNone(events.event_url(None))
		self.assertIsNone(events.event_url(""))

	def test_the_dto_is_built_field_by_field(self):
		"""Another app's schema must not reach a caller through this one."""
		name = self.make_event("Shaped")
		card = self.one(name)

		self.assertEqual(
			set(card),
			{
				"event",
				"title",
				"summary",
				"category",
				"venue",
				"medium",
				"start_date",
				"end_date",
				"start_time",
				"end_time",
				"time_zone",
				"image",
				"geo_node",
				"href",
				"multi_day",
			},
		)

	def test_the_docname_is_a_string_whatever_buzz_names_its_events(self):
		"""Buzz's naming rule is Buzz's, and it stops at this boundary.

		`Buzz Event` is autoincrement-named, so the row carries an int where
		every other docname this app hands a caller is a string. Passing that on
		would make another app's naming rule part of this app's API — the same
		leak the field-by-field DTO exists to stop, one level down.
		"""
		card = self.one(self.make_event("Named"))

		self.assertIsInstance(card["event"], str)

	def test_a_single_day_event_reports_an_end_date_and_is_not_multi_day(self):
		"""Normalised here so no screen has to decide what an absent end means."""
		name = self.make_event("Oneday", start_date=add_days(today(), 4), end_date=None)
		card = self.one(name)

		self.assertEqual(card["end_date"], card["start_date"])
		self.assertFalse(card["multi_day"])

	def test_a_multi_day_event_says_so(self):
		name = self.make_event("Multi", start_date=add_days(today(), 4), end_date=add_days(today(), 6))

		self.assertTrue(self.one(name)["multi_day"])

	# --- the window, the place and the organisation -------------------------

	def test_a_date_window_narrows_both_ends(self):
		self.make_event("Soonish", start_date=add_days(today(), 2))
		self.make_event("Midway", start_date=add_days(today(), 20))
		self.make_event("Distant", start_date=add_days(today(), 60))

		found = self.titles(date_from=add_days(today(), 10), date_to=add_days(today(), 30))

		self.assertIn(f"{PREFIX} Midway", found)
		self.assertNotIn(f"{PREFIX} Soonish", found)
		self.assertNotIn(f"{PREFIX} Distant", found)

	def test_a_date_from_in_the_past_cannot_reach_backwards(self):
		"""The window narrows what is upcoming; it does not replace it. A picker
		that could ask for last year would turn this reader into something else."""
		self.make_event("Over", start_date=add_days(today(), -30))
		self.make_event("Ahead", start_date=add_days(today(), 3))

		found = self.titles(date_from="2020-01-01")

		self.assertIn(f"{PREFIX} Ahead", found)
		self.assertNotIn(f"{PREFIX} Over", found)

	def test_the_window_closes_on_the_start_so_a_long_event_is_not_lost(self):
		"""Asking `end_date` to fit as well would drop the four-day training
		somebody is looking for out of "what is on this week"."""
		self.make_event("Long", start_date=add_days(today(), 3), end_date=add_days(today(), 40))

		self.assertIn(f"{PREFIX} Long", self.titles(date_to=add_days(today(), 7)))

	def test_a_venue_narrows_to_one_place(self):
		here = self.make_venue("Somewhere", "1 Somewhere Street")
		self.make_event("AtVenue", venue=here)
		self.make_event("Elsewhere")

		found = self.titles(venue=here)

		self.assertIn(f"{PREFIX} AtVenue", found)
		self.assertNotIn(f"{PREFIX} Elsewhere", found)

	def test_a_host_narrows_to_one_organisation(self):
		self.make_event("OurEvent")

		self.assertIn(f"{PREFIX} OurEvent", self.titles(host=self.host.name))

	def test_the_pickers_offer_only_places_something_is_actually_on(self):
		"""A venue with nothing at it reads as a place to turn up to on a day
		nobody is there — unlike a category, where an empty option reads as a
		filter that lost one."""
		empty = self.make_venue("Unused", "Nowhere at all")
		busy = self.make_venue("Busy", "2 Busy Road")
		self.make_event("Held", venue=busy)

		offered = {row["venue"] for row in events.venues()}

		self.assertIn(busy, offered)
		self.assertNotIn(empty, offered)

	def test_the_host_picker_offers_a_host_with_an_event(self):
		self.make_event("Hosted")

		self.assertIn(self.host.name, {row["host"] for row in events.hosts()})

	def test_the_listing_is_bounded(self):
		"""An unbounded read on a listing endpoint is how a query becomes an outage."""
		self.assertEqual(events._bounded(10_000), events.MAX_ROWS)
		self.assertEqual(events._bounded(0), 1)
		self.assertEqual(events._bounded("not a number"), events.MAX_ROWS)

	def test_categories_are_offered_even_with_no_event_on_them(self):
		"""A filter that loses an option when its last event passes looks broken."""
		self.assertTrue(events.categories())
		self.assertTrue(all("category" in row and "label" in row for row in events.categories()))


class TestBuzzEventDetail(EventFixtures):
	"""The screen a card opens, behind exactly the boundary the card had.

	`detail()` reads the same document through the same `is_published` rule, so
	what is asserted here is only what the deeper read adds — the long copy, the
	host and the venue's address — and that it adds nothing else.
	"""

	def make_venue(self, label: str, address: str) -> str:
		return (
			frappe.get_doc({"doctype": events.VENUE_DOCTYPE, "name": f"{PREFIX} {label}", "address": address})
			.insert(ignore_permissions=True)
			.name
		)

	def test_the_detail_adds_the_page_copy_a_card_has_no_room_for(self):
		address = "12 Kairaba Avenue"
		name = self.make_event(
			"Deep", about="<p>What the day covers</p>", venue=self.make_venue("Hall", address)
		)

		full = events.detail(name)

		self.assertEqual(full["about"], "<p>What the day covers</p>")
		self.assertEqual(full["host"], self.host.name)
		self.assertEqual(full["venue_address"], address)

	def test_the_detail_is_the_card_plus_four_fields_and_no_more(self):
		"""Another app's schema must not reach a caller through the deeper read
		either — the listing's rule, asserted at the depth that has more of it."""
		name = self.make_event("Bounded")

		self.assertEqual(
			set(events.detail(name)) - set(self.one(name)),
			{"banner", "about", "host", "venue_address"},
		)

	def test_an_event_with_no_venue_is_ordinary(self):
		"""Buzz makes a venue's address mandatory but a venue optional, so the
		empty answer comes from an online event rather than from a placeless
		hall — and it is still an answer rather than a lookup on nothing."""
		name = self.make_event("Online", venue=None)

		self.assertEqual(events.detail(name)["venue_address"], "")

	def test_an_unpublished_event_is_not_served_by_docname(self):
		"""`is_published` is the whole rule at both depths, so guessing a
		docname buys nothing the listing did not already show."""
		name = self.make_event("Private", is_published=0)

		self.assertIsNone(events.detail(name))

	def test_an_old_link_is_answered_rather_than_raised_at(self):
		"""Following a dead link is an ordinary thing to do, and Buzz names its
		events by autoincrement — so a stale link carries a number that may now
		be nobody's, and a mistyped one carries something that is not a number
		at all. Neither is an error to put in front of somebody."""
		self.assertIsNone(events.detail("999999999"))
		self.assertIsNone(events.detail("not-a-docname"))


class TestBuzzAbsent(IntegrationTestCase):
	"""A site without Buzz is ordinary, and every reader answers empty.

	`frappe.get_installed_apps` is patched rather than the import broken, because
	that is the surface the seam actually reads — the same technique
	`member/tests/test_payments_absent.py` uses for the payments app.
	"""

	def without_buzz(self):
		from unittest.mock import patch

		remaining = [app for app in frappe.get_installed_apps() if app != geo.BUZZ_APP]

		return patch.object(frappe, "get_installed_apps", return_value=remaining)

	def test_the_readers_answer_empty_rather_than_raising(self):
		with self.without_buzz():
			self.assertFalse(events.is_available())
			self.assertEqual(events.upcoming(), [])
			self.assertEqual(events.categories(), [])

	def test_the_endpoint_says_buzz_is_absent_rather_than_showing_nothing(self):
		"""No events because Buzz is missing and no events because none are
		scheduled are different sentences to put in front of somebody."""
		from vmmsx.api import events as endpoint

		with self.without_buzz():
			answer = endpoint.upcoming()

			self.assertFalse(answer["available"])
			self.assertEqual(answer["events"], [])
