# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The opportunities board: which openings it shows, and what it does to them.

**This suite replaced `deployment/tests/test_opportunities.py`**, which tested a
board that no longer exists. That board read `VMMS Deployment Request` — the
society's internal record of needing people somewhere — and every test in it was
about the elevation over that doctype. `api/opportunities.py` was pointed at
HRMS's `Job Opening` and the old suite was left asserting against a shape the
endpoint had stopped returning, which is why all thirteen of its tests failed
without anybody's board actually being broken.

What is worth pinning down now is different, and it is two things.

**The boundary.** `published()` reads with `ignore_permissions=True`, because a
volunteer cannot hold read permission on `Job Opening` without being given an HR
role, and HRMS's own website listing serves the same rows to the same people
anyway. So the gate is not the permission layer — it is `publish` and `status`,
two flags that are the society's own decisions. That has to hold whoever is
asking, and it would be very easy for somebody to "fix" the elevation later by
swapping `get_all` for `get_list`, at which point the board silently empties for
exactly the people it is for.

**The rendering, which is where the real bug was.** HRMS stores a description as
Text Editor markup. The board used to alias it onto a field the screen rendered
as plain text, so every visitor read a wall of escaped
`<div class="ql-editor read-mode">` where the job description should have been.
The seam now serves two readings of that field — sanitised markup and a flat
excerpt — and both of them have properties that must not regress: the markup
must not carry a script, and the excerpt must not carry a tag.
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from vmmsx.api import opportunities
from vmmsx.hr.services import openings

EXTRA_TEST_RECORD_DEPENDENCIES = []

COMPANY = "Opening Board Test Society"
DEPARTMENT_A = "Health"
DEPARTMENT_B = "Logistics"
DESIGNATION = "Board Test Officer"


class OpeningsTestCase(IntegrationTestCase):
	"""One company, its departments and designations, made once per class.

	HRMS is installed on this bench, so nothing here mocks it away. The one test
	that needs it absent patches `frappe.get_installed_apps`, which is the exact
	surface `is_available()` reads — see `test_a_site_without_hrms`.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		if not openings.is_available():
			return

		cls.company = _company()
		cls.department_a = _department(DEPARTMENT_A, cls.company)
		cls.department_b = _department(DEPARTMENT_B, cls.company)
		cls.designation = _designation()

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()

		if not openings.is_available():
			self.skipTest("HRMS is not installed on this site")

		self.addCleanup(frappe.set_user, "Administrator")

	def opening(self, title: str, **overrides) -> str:
		"""One Job Opening, published and open unless a test says otherwise."""
		values = {
			"doctype": "Job Opening",
			"job_title": title,
			"company": self.company,
			"designation": self.designation,
			"department": self.department_a,
			"status": "Open",
			"publish": 1,
			"posted_on": add_days(today(), -365),
		}
		values.update(overrides)

		return frappe.get_doc(values).insert(ignore_permissions=True).name

	def titles(self, **kwargs) -> list[str]:
		return [row["title"] for row in openings.published(**kwargs)]


class TestWhatTheBoardShows(OpeningsTestCase):
	def test_a_published_open_opening_is_on_the_board(self):
		self.opening("Community Health Officer")

		self.assertIn("Community Health Officer", self.titles())

	def test_an_unpublished_opening_is_not(self):
		"""`publish` is what puts an opening in public at all. It ships off."""
		self.opening("Internal Only Post", publish=0)

		self.assertNotIn("Internal Only Post", self.titles())

	def test_an_opening_the_society_has_closed_is_not(self):
		"""`status` is the society's own word for whether it is still recruiting."""
		self.opening("Filled Post", status="Closed")

		self.assertNotIn("Filled Post", self.titles())

	def test_an_opening_whose_closing_date_has_passed_is_not(self):
		self.opening("Expired Post", closes_on=add_days(today(), -1))

		self.assertNotIn("Expired Post", self.titles())

	def test_an_opening_closing_today_still_is(self):
		"""The filter is `>= today`, so the last day is a day you can still apply."""
		self.opening("Closes Today", closes_on=today())

		self.assertIn("Closes Today", self.titles())

	def test_an_opening_with_no_closing_date_is_advertised_until_it_is_closed(self):
		"""`closes_on` is optional in HRMS, and its absence is not an omission.

		A society that left it empty is saying "until further notice". The date
		filter is ORed against its own absence for exactly this row, and getting
		that wrong excludes every opening nobody put a deadline on.
		"""
		self.opening("Open Ended Post", closes_on=None)

		self.assertIn("Open Ended Post", self.titles())


class TestTheBoardDoesNotVaryByReader(OpeningsTestCase):
	"""The reason the elevation is there, and the reason it must stay.

	`published()` reads with `ignore_permissions=True`. Swapping that for a
	permission-checked read would empty the board for volunteers — who cannot
	hold read permission on `Job Opening` without an HR role — while leaving it
	full for whoever made the change. No other test in this app would notice.
	"""

	def test_a_signed_in_nobody_sees_what_an_administrator_sees(self):
		self.opening("Visible To Everybody")

		as_admin = self.titles()

		nobody = _user("board.reader@openings.test")
		frappe.set_user(nobody)

		self.assertEqual(self.titles(), as_admin)

	def test_the_endpoints_are_not_open_to_guests(self):
		"""Not `allow_guest`, deliberately — the seam's own note says why.

		The three guest-readable endpoints in this app are each bounded by a flag
		on a document, and a fourth needs the same justification, which is a
		question somebody has *before* they have an account. HRMS publishes its
		own openings to the website for that audience.

		Asked of the decorator's own record rather than by calling as Guest: the
		framework populates `guest_methods` at import time from `allow_guest`, so
		this is the flag itself and not a re-enactment of what it causes.
		"""
		for endpoint in (opportunities.browse, opportunities.detail, opportunities.filters):
			self.assertNotIn(endpoint, frappe.guest_methods, endpoint.__name__)


class TestTheDescriptionIsRendered(OpeningsTestCase):
	"""The bug this suite exists for, in both of its halves."""

	MARKUP = (
		'<div class="ql-editor read-mode"><h2>Frappe Developer</h2>'
		"<p>We are looking for a <strong>motivated</strong> developer.</p>"
		"<ul><li>Build DocTypes</li><li>Write tests</li></ul></div>"
	)

	def card(self, title: str, description: str | None = MARKUP) -> dict:
		"""One described opening, read back through the seam.

		The title is a parameter and every caller passes a different one, because
		HRMS derives a unique `route` from it and Frappe rolls the test
		transaction back once per *class*: two methods reusing a title collide on
		that index rather than starting clean.
		"""
		return openings.detail(self.opening(title, description=description))

	def test_the_markup_survives_as_markup(self):
		"""A Text Editor field is markup by construction, not text to escape."""
		card = self.card("Markup Post")

		self.assertIn("<h2>", card["description_html"])
		self.assertIn("<li>", card["description_html"])

	def test_a_script_does_not_survive(self):
		"""Sanitised on the way out, so the endpoint never served it.

		A browser-side sanitiser is one an attacker can decline to run.
		"""
		name = self.opening(
			"Hostile Post",
			description='<p>Hello</p><script>alert(1)</script><img src=x onerror="alert(1)">',
		)
		card = openings.detail(name)

		self.assertNotIn("<script", card["description_html"].lower())
		self.assertNotIn("onerror", card["description_html"].lower())
		self.assertIn("Hello", card["description_html"])

	def test_the_excerpt_carries_no_markup_at_all(self):
		"""What a card draws, and it is drawn as text.

		This is the assertion that would have caught the original bug: the old
		board put the raw description through a text node, and an excerpt with a
		tag in it is that same mistake one layer down.
		"""
		summary = self.card("Excerpt Post")["summary"]

		self.assertNotIn("<", summary)
		self.assertNotIn("ql-editor", summary)
		self.assertIn("Frappe Developer", summary)

	def test_the_excerpt_collapses_the_editors_whitespace(self):
		"""HRMS stores the markup's indentation, and a naive strip keeps it."""
		name = self.opening(
			"Spaced Post",
			description="<p>One</p>\n\n\n        <p>Two</p>",
		)

		self.assertEqual(openings.detail(name)["summary"], "One Two")

	def test_a_long_description_is_cut_on_a_word(self):
		"""A summary that stops mid-syllable reads as a truncation bug."""
		name = self.opening("Long Post", description="<p>" + ("responsibility " * 60) + "</p>")
		summary = openings.detail(name)["summary"]

		self.assertTrue(summary.endswith("…"))
		self.assertLess(len(summary), 240)
		self.assertNotIn("respon…", summary)

	def test_an_opening_with_no_description_says_nothing_rather_than_None(self):
		"""Both readings are strings, always. A screen should not test for null."""
		card = self.card("Wordless Post", description=None)

		self.assertEqual(card["description_html"], "")
		self.assertEqual(card["summary"], "")


class TestTheDTOIsExplicit(OpeningsTestCase):
	"""This crosses an app boundary, so what comes back is chosen field by field."""

	def test_it_carries_the_fields_the_board_draws(self):
		card = openings.detail(self.opening("Complete Post", closes_on=add_days(today(), 30)))

		for field in (
			"name",
			"title",
			"description_html",
			"summary",
			"department",
			"designation",
			"employment_type",
			"location",
			"places",
			"posted_on",
			"closes_on",
			"closing_soon",
			"href",
			"apply_href",
		):
			self.assertIn(field, card, field)

	def test_it_forwards_nothing_it_was_not_asked_for(self):
		"""HRMS's own model carries staffing plans and salary bands.

		Those are nobody's business on a public board, and the guard against them
		is that the DTO is built by hand rather than forwarded.
		"""
		card = openings.detail(self.opening("Salaried Post"))

		for leaked in ("lower_range", "upper_range", "currency", "staffing_plan", "owner"):
			self.assertNotIn(leaked, card, leaked)

	def test_the_old_deployment_names_are_gone(self):
		"""The aliases that caused the bug, asserted absent so they stay absent.

		`purpose` was the description under a name the screen rendered as text.
		Re-adding any of these to make an old screen work would put the wall of
		escaped markup straight back.
		"""
		card = openings.detail(self.opening("Aliased Post"))

		for alias in ("purpose", "responsibilities", "requirements", "geo_path", "needed_from"):
			self.assertNotIn(alias, card, alias)

	def test_an_opening_with_no_route_offers_nowhere_to_apply(self):
		"""Rather than a button leading to a 404. Same rule as the Buzz seam."""
		name = self.opening("Unrouted Post")
		frappe.db.set_value("Job Opening", name, "route", None)
		frappe.db.set_value("Job Opening", name, "job_application_route", None)

		self.assertIsNone(openings.detail(name)["apply_href"])

	def test_closing_soon_is_within_a_week_and_not_otherwise(self):
		soon = openings.detail(self.opening("Soon", closes_on=add_days(today(), 3)))
		later = openings.detail(self.opening("Later", closes_on=add_days(today(), 40)))

		self.assertTrue(soon["closing_soon"])
		self.assertFalse(later["closing_soon"])


class TestDetailAsksTheSameQuestionAsTheListing(OpeningsTestCase):
	def test_an_unpublished_opening_cannot_be_reached_by_naming_it(self):
		"""Guessing a docname buys nothing the listing did not already offer."""
		name = self.opening("Hidden Post", publish=0)

		self.assertIsNone(openings.detail(name))

	def test_a_closed_opening_answers_none_rather_than_raising(self):
		"""Following an old link is an ordinary thing to do."""
		name = self.opening("Withdrawn Post", status="Closed")

		self.assertIsNone(openings.detail(name))

	def test_a_docname_that_does_not_exist_answers_none(self):
		self.assertIsNone(openings.detail("HR-OPN-2026-99999"))


class TestFiltering(OpeningsTestCase):
	def test_search_matches_the_title(self):
		self.opening("Warehouse Assistant")
		self.opening("Community Nurse")

		self.assertEqual(self.titles(search="Warehouse"), ["Warehouse Assistant"])

	def test_search_does_not_match_the_description(self):
		"""Deliberate: a `%like%` across Text Editor markup matches tag names.

		Searching "li" would return every opening with a bullet list in it.
		"""
		self.opening("Plain Title", description="<p>warehouse logistics</p>")

		self.assertNotIn("Plain Title", self.titles(search="warehouse"))

	def test_a_department_filter_narrows_to_that_department(self):
		self.opening("In Health")
		self.opening("In Logistics", department=self.department_b)

		self.assertEqual(self.titles(department=self.department_b), ["In Logistics"])

	def test_the_picker_offers_only_departments_with_something_open(self):
		"""A department with nothing open reads as a place to apply on a day
		when there is nothing to apply for.

		A department of its own, made here rather than reused: Frappe rolls the
		test transaction back once per class, so an opening another method in
		this class left behind is still on the board when this one runs, and
		asserting about `department_b` would be asserting about that.
		"""
		quiet = _department("Nothing Open Here", self.company)

		self.opening("Health Post")
		self.opening("Closed Post", department=quiet, status="Closed")

		offered = [row["department"] for row in openings.departments()]

		self.assertIn(self.department_a, offered)
		self.assertNotIn(quiet, offered)

	def test_the_listing_is_bounded_however_large_a_limit_is_asked_for(self):
		"""An unbounded read on a listing endpoint is how a query becomes an outage."""
		self.assertEqual(openings._bounded(10_000), openings.MAX_ROWS)
		self.assertEqual(openings._bounded(-5), 1)
		self.assertEqual(openings._bounded("not a number"), openings.MAX_ROWS)


class TestASiteWithoutHRMS(IntegrationTestCase):
	"""vmmsx does not declare `hrms` in `required_apps`, so this is ordinary.

	Absence is mocked, because HRMS really is installed on this bench. The patch
	targets `frappe.get_installed_apps`, which is the exact surface
	`is_available()` reads — the same shape `test_lms_absent.py` uses against the
	learning app, and for the same reason: the guard asks installed-apps rather
	than trying an import, so absence is answerable at configuration time.
	"""

	def without_hrms(self):
		from unittest.mock import patch

		remaining = [app for app in frappe.get_installed_apps() if app != openings.HRMS_APP]

		return patch.object(frappe, "get_installed_apps", return_value=remaining)

	def test_every_reader_answers_empty_rather_than_raising(self):
		with self.without_hrms():
			self.assertFalse(openings.is_available())
			self.assertEqual(openings.published(), [])
			self.assertEqual(openings.departments(), [])
			self.assertIsNone(openings.detail("HR-OPN-2026-00001"))

	def test_the_endpoint_says_so_rather_than_looking_like_an_empty_board(self):
		"""The screen draws two different sentences, so it needs two answers.

		"Nothing is open today" and "recruitment does not run here" are different
		things to tell somebody, and `available` travelling with the rows is what
		lets the board pick.
		"""
		with self.without_hrms():
			answer = opportunities.browse()

			self.assertFalse(answer["available"])
			self.assertEqual(answer["opportunities"], [])


# --- arrangement --------------------------------------------------------------


def _company() -> str:
	if frappe.db.exists("Company", COMPANY):
		return COMPANY

	return (
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": COMPANY,
				"default_currency": "TZS",
				"country": "Tanzania",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _department(label: str, company: str) -> str:
	"""HRMS suffixes a department with its company's abbreviation on insert."""
	existing = frappe.db.get_value(
		"Department", {"department_name": label, "company": company}, "name"
	)

	if existing:
		return existing

	return (
		frappe.get_doc(
			{"doctype": "Department", "department_name": label, "company": company}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _designation() -> str:
	if frappe.db.exists("Designation", DESIGNATION):
		return DESIGNATION

	return (
		frappe.get_doc({"doctype": "Designation", "designation_name": DESIGNATION})
		.insert(ignore_permissions=True)
		.name
	)


def _user(email: str) -> str:
	"""Somebody with no role, no assignment and no scope anywhere.

	A volunteer who has just been accepted, which is who the board is built for.
	"""
	if frappe.db.exists("User", email):
		return email

	return (
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": "Board",
				"last_name": "Reader",
				"send_welcome_email": 0,
				"user_type": "Website User",
			}
		)
		.insert(ignore_permissions=True)
		.name
	)
