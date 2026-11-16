# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The one page a County Coordinator deploys from.

A title nobody else's open deployment has; who is needed; the location, with the
county's branch office as the meeting point; and the people asked or placed in
the same call — now, at a set time, or everybody the search matched.
"""

from unittest.mock import patch

import frappe
from frappe.utils import add_days, add_to_date, now_datetime, today

from vmmsx.api import deployment as api
from vmmsx.deployment.services import assignment, geocoding, map_links, matching, sending
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase


class OnePageTestCase(DeploymentTestCase):
	def setUp(self):
		super().setUp()
		self.terms = fixtures.make_terms_requiring()
		self.branch = self.society_a["branch"]

	def people(self, count: int, handle: str = "Asked") -> list[str]:
		return [
			fixtures.make_volunteer(fixtures.make_profile(f"{handle}{index}", "Person"), self.branch).name
			for index in range(count)
		]

	def set_up(self, title: str | None = None, **values):
		title = f"DEPTEST Floods Response {frappe.generate_hash(length=6)}" if title is None else title

		return api.create_deployment(
			terms_of_reference=self.terms.name,
			geo_node=self.branch,
			start_date=today(),
			end_date=add_days(today(), 7),
			title=title,
			**values,
		)


class TestEveryDeploymentHasItsOwnTitle(OnePageTestCase):
	def test_a_coordinator_must_give_a_title(self):
		with self.assertRaises(frappe.MandatoryError):
			self.set_up(title="  ")

	def test_two_open_deployments_cannot_share_a_title(self):
		tag = frappe.generate_hash(length=6)
		self.set_up(title=f"Marathon First Aid {tag}")

		with self.assertRaises(frappe.DuplicateEntryError):
			self.set_up(title=f"marathon  first aid {tag.upper()}")

	def test_another_county_may_use_the_same_title(self):
		title = f"County Show {frappe.generate_hash(length=6)}"
		self.set_up(title=title)

		elsewhere = api.create_deployment(
			terms_of_reference=self.terms.name,
			geo_node=self.society_a["other_branch"],
			start_date=today(),
			end_date=add_days(today(), 7),
			title=title,
		)

		self.assertEqual(elsewhere["deployment"]["title"], title)

	def test_a_finished_deployments_title_may_be_used_again(self):
		title = f"Annual Marathon {frappe.generate_hash(length=6)}"
		first = self.set_up(title=title)["deployment"]["name"]
		frappe.db.set_value(fixtures.DEPLOYMENT_DOCTYPE, first, "status", "Cancelled")

		self.assertTrue(self.set_up(title=title)["deployment"]["name"])

	def test_a_deployment_nobody_named_is_called_after_its_terms_and_month(self):
		first = fixtures.make_deployment(self.terms.name, self.branch)
		second = fixtures.make_deployment(self.terms.name, self.branch)

		self.assertTrue(first.title.startswith(self.terms.tor_name))
		self.assertIn(frappe.utils.formatdate(today(), "MMMM yyyy"), first.title)
		self.assertEqual(second.title, f"{first.title} (2)")


class TestPeopleAreAskedFromTheSamePage(OnePageTestCase):
	def test_asking_at_creation_raises_one_question_each(self):
		people = self.people(2)

		reply = self.set_up(mode=sending.ASK, volunteers=people)
		rows = frappe.get_all(
			fixtures.ASSIGNMENT_DOCTYPE,
			filters={"deployment": reply["deployment"]["name"]},
			pluck="status",
		)

		self.assertEqual(reply["sending"]["state"], "sent")
		self.assertEqual(sorted(rows), [assignment.STATUS_PENDING] * 2)

	def test_nobody_is_placed_without_accepting(self):
		"""A volunteer must accept: a coordinator cannot place them, at creation or after."""
		people = self.people(1, "Placed")

		with self.assertRaises(frappe.ValidationError):
			self.set_up(mode=sending.PLACE, volunteers=people)

		name = self.set_up()["deployment"]["name"]

		with self.assertRaises(frappe.ValidationError):
			api.send_to_volunteers(name, sending.PLACE, volunteers=people)

		self.assertFalse(frappe.db.exists(fixtures.ASSIGNMENT_DOCTYPE, {"volunteer": people[0]}))

	def test_saved_first_then_the_request_is_sent(self):
		"""The page's order, as the old tool's: save, then send the request to those selected."""
		people = self.people(2, "Saved")

		name = self.set_up()["deployment"]["name"]
		self.assertFalse(frappe.db.exists(fixtures.ASSIGNMENT_DOCTYPE, {"deployment": name}))

		sent = api.send_to_volunteers(name, sending.ASK, volunteers=people)
		rows = frappe.get_all(fixtures.ASSIGNMENT_DOCTYPE, filters={"deployment": name}, pluck="status")

		self.assertEqual(sent["state"], "sent")
		self.assertEqual(sorted(rows), [assignment.STATUS_PENDING] * 2)

	def test_who_is_needed_is_kept_on_the_deployment(self):
		skill = frappe.get_all("VMMS Skill", pluck="name", limit=1)

		reply = self.set_up(skills_needed=skill)

		self.assertEqual(reply["deployment"]["needs"]["skills"], skill)

	def test_select_all_asks_everybody_the_search_matched(self):
		self.people(3, "Everyone")

		with fixtures.acting_as("Administrator"):
			expected = len(matching.matching_names(self.terms.name, self.branch, as_of=today()))

		reply = self.set_up(mode=sending.ASK, select_all=1, criteria={})

		self.assertEqual(len(reply["sending"]["success"]) + len(reply["sending"]["failure"]), expected)


class TestASendTimeHoldsTheAsks(OnePageTestCase):
	def test_nobody_is_asked_before_the_send_time(self):
		people = self.people(2, "Waiting")
		later = add_to_date(now_datetime(), days=2)

		reply = self.set_up(mode=sending.ASK, volunteers=people, send_on=str(later))
		name = reply["deployment"]["name"]

		self.assertEqual(reply["sending"]["state"], "scheduled")
		self.assertFalse(frappe.db.exists(fixtures.ASSIGNMENT_DOCTYPE, {"deployment": name}))
		self.assertEqual(len(reply["deployment"]["sending"]["scheduled"]), 2)

	def test_the_asks_go_out_once_the_time_comes_and_only_once(self):
		people = self.people(2, "Monday")
		reply = self.set_up(
			mode=sending.ASK, volunteers=people, send_on=str(add_to_date(now_datetime(), days=1))
		)
		name = reply["deployment"]["name"]
		frappe.db.set_value(
			fixtures.DEPLOYMENT_DOCTYPE, name, "send_on", add_to_date(now_datetime(), minutes=-1)
		)

		sending.send_due()
		sending.send_due()

		self.assertEqual(frappe.db.count(fixtures.ASSIGNMENT_DOCTYPE, {"deployment": name}), 2)
		self.assertFalse(frappe.db.exists("VMMS Scheduled Ask", {"parent": name}))
		self.assertTrue(frappe.db.get_value(fixtures.DEPLOYMENT_DOCTYPE, name, "asks_sent_on"))

	def test_someone_taken_off_the_list_is_never_asked(self):
		keep, drop = self.people(2, "Choice")
		reply = self.set_up(
			mode=sending.ASK, volunteers=[keep, drop], send_on=str(add_to_date(now_datetime(), days=1))
		)
		name = reply["deployment"]["name"]

		api.unschedule_volunteer(name, drop)
		frappe.db.set_value(
			fixtures.DEPLOYMENT_DOCTYPE, name, "send_on", add_to_date(now_datetime(), minutes=-1)
		)
		sending.send_due()

		asked = frappe.get_all(fixtures.ASSIGNMENT_DOCTYPE, filters={"deployment": name}, pluck="volunteer")
		self.assertEqual(asked, [keep])


class TestTheChannelsAreTheDeploymentsChoice(OnePageTestCase):
	def setUp(self):
		super().setUp()
		self.started = now_datetime()

	def emails_for(self, deployment: str) -> int:
		"""Emails about this deployment's asks, written during this test."""
		asks = frappe.get_all(fixtures.ASSIGNMENT_DOCTYPE, filters={"deployment": deployment}, pluck="name")
		return frappe.db.count(
			"Email Queue",
			{"reference_name": ("in", asks or [""]), "creation": (">=", self.started)},
		)

	def test_an_ask_is_emailed_when_email_is_ticked(self):
		reply = self.set_up(mode=sending.ASK, volunteers=self.people(1, "Emailed"), notify_by_email=1)

		self.assertEqual(self.emails_for(reply["deployment"]["name"]), 1)

	def test_and_not_when_it_is_not(self):
		reply = self.set_up(mode=sending.ASK, volunteers=self.people(1, "Quiet"), notify_by_email=0)

		self.assertEqual(self.emails_for(reply["deployment"]["name"]), 0)


class TestTheLocation(OnePageTestCase):
	def test_a_coordinator_is_offered_only_their_own_county(self):
		level = frappe.db.get_value("Geo Node", self.branch, "geo_level")
		previous = frappe.db.get_single_value(fixtures.SETTINGS_DOCTYPE, fixtures.DEPLOYMENT_ANCHOR_SETTING)
		fixtures.set_deployment_anchor_level(level)

		try:
			coordinator = self.viewer("one_page_cc", fixtures.DEPLOYMENT_SCOPE_ROLE, self.branch)
			fixtures.grant_doctype_access(fixtures.DEPLOYMENT_DOCTYPE, fixtures.DEPLOYMENT_SCOPE_ROLE)

			with fixtures.acting_as(coordinator):
				mine = [row["name"] for row in api.deployment_setup()["counties"]]

			everyone = [row["name"] for row in api.deployment_setup()["counties"]]
		finally:
			fixtures.set_deployment_anchor_level(previous)

		self.assertEqual(mine, [self.branch])
		self.assertIn(self.society_a["other_branch"], everyone)

	def test_the_meeting_point_is_the_branch_office_when_ticked(self):
		office = frappe.get_doc(
			{
				"doctype": "VMMS Branch Location",
				"location_name": "DEPTEST Karura Branch Office",
				"geo_node": self.branch,
				"address": "Karura Road",
				"latitude": -1.2,
				"longitude": 36.8,
			}
		).insert(ignore_permissions=True)

		reply = self.set_up(meeting_at_branch_office=1)
		where = frappe.db.get_value(
			fixtures.DEPLOYMENT_DOCTYPE,
			reply["deployment"]["name"],
			["meeting_point", "meeting_address"],
			as_dict=True,
		)

		self.assertEqual(where.meeting_point, office.location_name)
		self.assertEqual(where.meeting_address, "Karura Road")

	def test_only_terms_covering_the_county_are_offered(self):
		elsewhere = fixtures.make_terms_requiring(geo_scope=self.society_a["other_branch"])

		offered = [row["name"] for row in api.branch_terms(covering=self.branch, active_only=1)["terms"]]

		self.assertIn(self.terms.name, offered)
		self.assertNotIn(elsewhere.name, offered)


class TestWaitingAsksAreNeverStranded(OnePageTestCase):
	def test_clearing_the_send_time_sends_the_waiting_asks_at_the_next_run(self):
		people = self.people(2, "Cleared")
		reply = self.set_up(
			mode=sending.ASK, volunteers=people, send_on=str(add_to_date(now_datetime(), days=3))
		)
		name = reply["deployment"]["name"]

		api.update_deployment(name, send_on="")
		sending.send_due()

		self.assertEqual(frappe.db.count(fixtures.ASSIGNMENT_DOCTYPE, {"deployment": name}), 2)
		self.assertFalse(frappe.db.exists("VMMS Scheduled Ask", {"parent": name}))


class TestTheTitleIsWhatAVolunteerSees(OnePageTestCase):
	def test_their_history_names_the_deployment_not_its_terms(self):
		reply = self.set_up(title=f"DEPTEST Coast Floods {frappe.generate_hash(length=6)}")
		row = {**reply["deployment"]}

		self.assertEqual(api._titled(row)["title"], row["title"])

	def test_an_untitled_row_falls_back_to_the_terms_name(self):
		row = {"name": "DEP-X", "title": "DEP-X", "terms_of_reference": self.terms.name}

		self.assertEqual(api._titled(row)["title"], self.terms.tor_name)


class TestAPointFromWhatWasPasted(OnePageTestCase):
	def test_coordinates_and_google_maps_addresses_are_read(self):
		self.assertEqual(map_links.point_in("-1.29207, 36.82195"), {"latitude": -1.29207, "longitude": 36.82195})
		self.assertEqual(
			map_links.point_in(
				"https://www.google.com/maps/place/X/@-1.2833,36.8167,17z/data=!3m1!8m2!3d-1.28333!4d36.81667"
			),
			{"latitude": -1.28333, "longitude": 36.81667},
		)
		self.assertIsNone(map_links.point_in("Kenyatta National Hospital"))

	def test_only_googles_short_links_are_ever_fetched(self):
		with patch.object(map_links.requests, "get", side_effect=AssertionError("fetched")) as fetch:
			self.assertIsNone(map_links.follow("https://example.com/somewhere"))
			self.assertIsNone(map_links.follow("http://localhost:8000/api/method/frappe.ping"))

		fetch.assert_not_called()

	def test_a_short_link_is_followed_to_its_point(self):
		class Answer:
			def __init__(self, location):
				self.headers = {"Location": location}
				self.text = ""

		with patch.object(
			map_links.requests,
			"get",
			return_value=Answer("https://www.google.com/maps/place/X/@-4.04,39.66,17z"),
		):
			self.assertEqual(
				map_links.follow("https://maps.app.goo.gl/AbC123"), {"latitude": -4.04, "longitude": 39.66}
			)


class TestThePlaceSearchStaysInTheSocietysCountry(OnePageTestCase):
	PHOTON = {
		"features": [
			{"geometry": {"coordinates": [36.81, -1.30]}, "properties": {"name": "Upper Hill", "countrycode": "KE"}},
			{"geometry": {"coordinates": [-77.0, 38.9]}, "properties": {"name": "Upper Hill", "countrycode": "US"}},
			{"geometry": {"coordinates": [36.82, -1.29]}, "properties": {"name": "Upper Hill Road"}},
		]
	}

	def shaped(self, shape: str):
		return patch.dict(frappe.conf, {geocoding.SHAPE_KEY: shape})

	def test_an_answer_from_another_country_is_dropped(self):
		with self.shaped(geocoding.PHOTON), patch.object(geocoding, "country_code", return_value="ke"):
			places = geocoding._read(self.PHOTON, limit=6)

		self.assertEqual([place["longitude"] for place in places], [36.81, 36.82])

	def test_each_provider_is_asked_for_the_society_country_only(self):
		near = {"latitude": -1.28, "longitude": 36.82}

		with patch.object(geocoding, "country_code", return_value="ke"):
			with self.shaped(geocoding.NOMINATIM):
				self.assertEqual(geocoding._params("Upper Hill", 6, near)["countrycodes"], "ke")
			with self.shaped(geocoding.GOOGLE):
				self.assertEqual(geocoding._params("Upper Hill", 6, near)["components"], "country:KE")
			with self.shaped(geocoding.PHOTON):
				photon = geocoding._params("Upper Hill", 6, near)

		self.assertEqual((photon["lat"], photon["lon"]), (-1.28, 36.82))
		self.assertEqual(photon["limit"], geocoding.COUNTRY_FETCH)

	def test_a_society_with_no_country_searches_everywhere(self):
		with self.shaped(geocoding.NOMINATIM), patch.object(geocoding, "country_code", return_value=None):
			self.assertNotIn("countrycodes", geocoding._params("Upper Hill", 6))

	def test_the_country_is_the_one_on_the_societys_settings(self):
		with patch("vmmsx.volunteer.services.society.default_citizenship_country", return_value="Kenya"):
			self.assertEqual(geocoding.country_code(), "ke")


class TestATorFromOutsideTheSystem(OnePageTestCase):
	"""As in the old tool: system terms, or the TOR attached as a file."""

	@staticmethod
	def paper_tor() -> bytes:
		"""A real one-page PDF: Frappe reads every uploaded PDF and refuses a broken one.

		Each one different, because Frappe gives files with the same bytes the same
		address, and one test's upload would then stand in for another's.
		"""
		from io import BytesIO

		from pypdf import PdfWriter

		writer = PdfWriter()
		writer.add_blank_page(width=72, height=72)
		writer.add_metadata({"/Title": frappe.generate_hash()})
		buffer = BytesIO()
		writer.write(buffer)

		return buffer.getvalue()

	def upload(self, owner: str = "Administrator", content: bytes | None = None) -> str:
		content = content or self.paper_tor()
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"tor-{frappe.generate_hash(length=6)}.pdf",
				"is_private": 1,
				"content": content,
			}
		)
		file.insert(ignore_permissions=True)
		frappe.db.set_value("File", file.name, "owner", owner)

		return file.file_url

	def attach(self, url: str, **values):
		values.setdefault("project", fixtures.make_project(self.branch))

		return api.create_deployment(
			terms_of_reference="",
			tor_attachment=url,
			geo_node=self.branch,
			start_date=today(),
			end_date=add_days(today(), 7),
			title=f"DEPTEST Paper TOR {frappe.generate_hash(length=6)}",
			**values,
		)

	def test_the_attachment_becomes_terms_of_its_own(self):
		url = self.upload()
		project = fixtures.make_project(self.branch)

		reply = self.attach(url, project=project)
		deployment = reply["deployment"]
		terms = frappe.get_doc("VMMS Terms of Reference", deployment["terms_of_reference"])

		self.assertEqual(terms.tor_attachment, url)
		self.assertEqual(terms.docstatus, 1)
		self.assertEqual(terms.project, project)
		self.assertEqual(terms.geo_scope, self.branch)
		self.assertEqual(terms.tor_name, deployment["title"])
		self.assertTrue(deployment["terms"]["is_attachment"])
		self.assertTrue(
			frappe.db.exists(
				"File",
				{"file_url": url, "attached_to_doctype": "VMMS Terms of Reference", "attached_to_name": terms.name},
			)
		)

	def test_it_asks_for_nothing_the_document_already_says(self):
		from vmmsx.deployment.services import terms

		record = frappe._dict(tor_attachment="/private/files/x.pdf", project=None, geo_scope=None)

		self.assertEqual(len(terms.missing_at_submission(record)), 4)

	def test_the_project_is_required(self):
		with self.assertRaises(frappe.MandatoryError):
			self.attach(self.upload(), project=None)

	def test_somebody_elses_file_is_refused(self):
		url = self.upload(owner="Guest")

		with self.assertRaises(frappe.ValidationError):
			self.attach(url)

	def test_a_file_already_on_another_record_is_refused(self):
		url = self.upload()
		self.attach(url)

		with self.assertRaises(frappe.ValidationError):
			self.attach(url)

	def test_not_where_the_society_approves_its_terms(self):
		with patch("vmmsx.deployment.services.terms.is_governed", return_value=True):
			with self.assertRaises(frappe.PermissionError):
				self.attach(self.upload())

	def test_the_tor_download_is_the_attached_file(self):
		signed = self.paper_tor()
		url = self.upload(content=signed)
		terms = self.attach(url)["deployment"]["terms_of_reference"]

		api.download_terms(terms)

		self.assertEqual(frappe.local.response.filecontent, signed)
		self.assertEqual(frappe.local.response.type, "pdf")

	def test_the_page_is_offered_every_open_project(self):
		project = fixtures.make_project(self.branch)

		setup = api.deployment_setup()

		self.assertIn(project, [row.name for row in setup["projects"]])
		self.assertTrue(setup["can_attach_terms"])


class TestTheSearchTakesWhatABrowserSends(OnePageTestCase):
	def test_every_list_may_arrive_as_text(self):
		"""A GET carries lists as JSON text; a list-only parameter refused the whole search."""
		from frappe.utils.typing_validations import transform_parameter_types

		sent = {field: "[]" for field in ("skills", "languages", "professions", *matching.LIST_FILTERS)}

		# Raises FrappeTypeError where a parameter takes lists but not text.
		transform_parameter_types(
			api.find_candidates, (), {"terms_of_reference": "", "geo_node": self.branch, **sent}, False
		)
