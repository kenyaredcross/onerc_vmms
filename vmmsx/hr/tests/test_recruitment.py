# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The recruiter's side of an opening, and the four rules it must not lose.

`test_openings.py` covers the volunteer's board and `test_applications.py` the
applying. This is the third side — the console screens that advertise a post and
decide on the answers — and the properties worth pinning are the ones that would
break silently.

**The console writes `Job Opening`, and only the fields it owns.** `save()`
takes a payload from a browser and must never become a way to write an arbitrary
field on somebody else's doctype. The allow-list is the whole of that guarantee.

**`status` and `publish` are two different questions.** Whether the society is
still recruiting, and whether the advertisement is on the website. HRMS keeps
them apart; a screen that collapsed them would make "open but filled by
invitation" unrepresentable.

**A withdrawal is not a status.** It is a date vmmsx adds, so a withdrawn
application keeps whatever stage the society had reached — and cannot be moved
on, because the person is gone.

**Absent when HRMS is.** A society without it gets empty readers and refusing
writers, not tracebacks.
"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.hr.services import recruitment
from vmmsx.setup import job_applicant_fields as applicant_fields
from vmmsx.setup import job_opening_fields as opening_fields

COMPANY = "Recruitment Console Test Society"
DESIGNATION = "Console Test Officer"
LANGUAGES = ("con-en", "con-sw")


class RecruitmentTestCase(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		if not frappe.db.exists("Company", COMPANY):
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": COMPANY,
					"abbr": "RCTS",
					"default_currency": "TZS",
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Designation", DESIGNATION):
			frappe.get_doc({"doctype": "Designation", "designation_name": DESIGNATION}).insert(
				ignore_permissions=True
			)

		# The desired-languages multiselect is a table of Links, so the values
		# have to be real records — the same rule `MultiCombo` follows in the
		# browser, where typing filters and never sets.
		for language in LANGUAGES:
			if not frappe.db.exists("Language", language):
				frappe.get_doc(
					{"doctype": "Language", "language_code": language, "language_name": language.title()}
				).insert(ignore_permissions=True)

	def _opening(self, **overrides) -> str:
		# A unique title per opening, because HRMS derives the website `route`
		# from it and the column is unique. Two openings with one title inside a
		# class is an integrity error rather than a test failure, which is a
		# confusing thing to be handed.
		payload = {
			"job_title": f"Console test opening {frappe.generate_hash(length=6)}",
			"company": COMPANY,
			"designation": DESIGNATION,
			"status": "Open",
			opening_fields.PURPOSE_FIELD: opening_fields.PURPOSE_VOLUNTEER,
			**overrides,
		}

		return recruitment.save(payload)["name"]


class TestWhatTheConsoleMayWrite(RecruitmentTestCase):
	def test_it_creates_an_opening_and_reads_it_back(self):
		title = f"Community health outreach volunteer {frappe.generate_hash(length=6)}"
		doc = recruitment.detail(self._opening(job_title=title))

		self.assertEqual(doc["job_title"], title)
		self.assertEqual(doc["purpose"], opening_fields.PURPOSE_VOLUNTEER)

	def test_a_field_outside_the_allow_list_is_dropped_rather_than_written(self):
		"""The console posts the whole form back, so an unknown key is ordinary
		— but it must never reach the document. `naming_series` is the sharp
		case: writable on the doctype, and nobody's business from a browser."""
		name = self._opening(naming_series="EVIL-.####")

		self.assertFalse(frappe.db.get_value("Job Opening", name, "name").startswith("EVIL"))

	def test_an_unknown_key_does_not_refuse_the_save(self):
		"""A society that adds a custom field on the desk must not find this
		endpoint throwing at the form that still posts it."""
		name = self._opening(some_custom_field_a_society_added="whatever")

		self.assertTrue(frappe.db.exists("Job Opening", name))

	def test_the_multiselects_are_replaced_wholesale_not_appended(self):
		"""A child table edited by re-posting the list has to be cleared first,
		or every save doubles it."""
		first, second = LANGUAGES
		name = self._opening(vmms_desired_languages=[first])
		recruitment.save({"vmms_desired_languages": [first, second]}, name=name)
		recruitment.save({"vmms_desired_languages": [second]}, name=name)

		self.assertEqual(recruitment.detail(name)["vmms_desired_languages"], [second])


class TestStatusAndPublishAreDifferentQuestions(RecruitmentTestCase):
	def test_closing_an_opening_leaves_the_advertisement_alone(self):
		name = self._opening(publish=1)
		recruitment.set_status(name, "Closed")

		doc = recruitment.detail(name)

		self.assertEqual(doc["status"], "Closed")
		self.assertTrue(doc["is_published"])

	def test_unpublishing_leaves_the_society_still_recruiting(self):
		""" "Open, filled by invitation" is a real thing a society does."""
		name = self._opening(publish=1)
		recruitment.set_published(name, False)

		doc = recruitment.detail(name)

		self.assertEqual(doc["status"], "Open")
		self.assertFalse(doc["is_published"])

	def test_a_status_outside_the_closed_set_is_refused(self):
		name = self._opening()

		with self.assertRaises(frappe.ValidationError):
			recruitment.set_status(name, "Haunted")


class TestThePipeline(RecruitmentTestCase):
	def _applicant(self, opening: str, **overrides) -> str:
		return (
			frappe.get_doc(
				{
					"doctype": "Job Applicant",
					"applicant_name": "Console Test Applicant",
					"email_id": f"console.test.{frappe.generate_hash(length=6)}@example.tz",
					"job_title": opening,
					"status": applicant_fields.STATUS_OPEN,
					**overrides,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_the_pipeline_is_counted_per_opening(self):
		opening = self._opening()
		self._applicant(opening)
		self._applicant(opening, status=applicant_fields.STATUS_SHORTLISTED)

		row = next(entry for entry in recruitment.openings()["openings"] if entry["name"] == opening)

		self.assertEqual(row["pipeline"]["total"], 2)
		self.assertEqual(row["pipeline"][applicant_fields.STATUS_OPEN], 1)
		self.assertEqual(row["pipeline"][applicant_fields.STATUS_SHORTLISTED], 1)

	def test_an_applicant_moves_along_the_pipeline(self):
		opening = self._opening()
		applicant = self._applicant(opening)

		recruitment.set_applicant_status(applicant, applicant_fields.STATUS_SHORTLISTED)

		self.assertEqual(recruitment.applicant(applicant)["status"], applicant_fields.STATUS_SHORTLISTED)

	def test_a_withdrawn_application_keeps_its_stage_and_cannot_be_moved(self):
		"""Two halves of one rule.

		A withdrawal is a date, not a status, so the stage the society reached
		survives it — losing "we had shortlisted them" would lose the fact that
		the society had said yes before the person left. And moving somebody who
		has gone is a decision about nobody.
		"""
		opening = self._opening()
		applicant = self._applicant(
			opening,
			status=applicant_fields.STATUS_SHORTLISTED,
			**{applicant_fields.WITHDRAWN_FIELD: frappe.utils.now_datetime()},
		)

		doc = recruitment.applicant(applicant)

		self.assertEqual(doc["status"], applicant_fields.STATUS_SHORTLISTED)
		self.assertTrue(doc["is_withdrawn"])

		with self.assertRaises(frappe.ValidationError):
			recruitment.set_applicant_status(applicant, applicant_fields.STATUS_ACCEPTED)

	def test_the_curated_applicant_carries_no_recruiter_private_fields(self):
		"""`Job Applicant` holds a salary range and a rating. A volunteer
		coordinator is deciding on neither, and passing the whole document
		through would put a colleague's private note on this screen."""
		opening = self._opening()
		doc = recruitment.applicant(self._applicant(opening))

		for field in ("lower_range", "upper_range", "applicant_rating", "resume_link"):
			self.assertNotIn(field, doc)


class TestASiteWithoutHrms(RecruitmentTestCase):
	"""Graceful absence, the same contract `openings.py` keeps.

	`frappe.get_installed_apps` is patched because it is the exact surface
	`board.is_available()` reads — mocking anything else would be testing a
	different function from the one that ships.
	"""

	def _without_hrms(self):
		installed = [app for app in frappe.get_installed_apps() if app != "hrms"]

		return patch("frappe.get_installed_apps", return_value=installed)

	def test_the_readers_answer_empty(self):
		with self._without_hrms():
			self.assertEqual(recruitment.openings()["openings"], [])
			self.assertFalse(recruitment.openings()["available"])
			self.assertEqual(recruitment.applicants()["applicants"], [])
			self.assertFalse(recruitment.options()["available"])

	def test_the_writers_refuse_in_a_sentence(self):
		with self._without_hrms():
			with self.assertRaises(frappe.ValidationError):
				recruitment.save({"job_title": "Anything"})
