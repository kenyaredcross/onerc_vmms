# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Uploaded evidence is private, and it is private because the server made it so.

The failure this suite exists to catch is quiet and permanent: a file uploaded to
`/files/` is served to anybody who has the URL, with no permission check
anywhere — the framework does not consult `attached_to_doctype` for a public
file. An applicant's birth certificate behind a guessable path is not a bug that
shows up on a screen.

So the rule cannot be a DocField property. A desk `Attach` field already uploads
privately by default (`make_attachment_public` is the framework's switch and
nothing in this app sets it), but the portal uploads through the file API where
the *browser* names the privacy and then posts back a URL. `evidence.secure` is
the answer to both, and these tests drive the portal path because that is the
half that was exposed.
"""

import frappe

from vmmsx.registration.services import evidence, questions
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

QUESTION_DOCTYPE = "VMMS Application Question"


def _public_upload(name: str, content: bytes = b"a scanned letter") -> str:
	"""A file the browser chose to upload publicly. The state under test."""
	document = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": name,
			"content": content,
			"is_private": 0,
		}
	).insert(ignore_permissions=True)

	return document.file_url


class TestTheUrlIsAClaim(RegistrationTestCase):
	def test_a_url_on_another_server_is_refused(self):
		"""Otherwise this field points the approver's browser wherever the
		applicant likes — the same rule `links.py` applies to a content block."""
		with self.assertRaises(frappe.ValidationError):
			evidence.assert_uploaded("https://evil.example/letter.pdf", "Consent Evidence")

	def test_a_path_that_is_not_an_upload_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			evidence.assert_uploaded("/etc/passwd", "Consent Evidence")

	def test_both_of_this_sites_upload_paths_are_accepted(self):
		"""Public is accepted and then made private, rather than refused.

		Refusing it would leave the public copy on disk *and* cost the applicant
		their answer, which is worse on both counts.
		"""
		self.assertEqual(evidence.assert_uploaded("/files/a.pdf", "x"), "/files/a.pdf")
		self.assertEqual(evidence.assert_uploaded("/private/files/a.pdf", "x"), "/private/files/a.pdf")

	def test_nothing_is_an_acceptable_answer(self):
		self.assertEqual(evidence.assert_uploaded(None, "x"), "")


class TestAnsweredFilesAreMadePrivate(RegistrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.question = (
			frappe.get_doc(
				{
					"doctype": QUESTION_DOCTYPE,
					"asked_on": fixtures.APPLICATION_DOCTYPE,
					"question_label": "A letter from your area chief",
					"field_type": "Attach",
					"is_required": 1,
					"sequence": 1,
					"is_active": 1,
				}
			)
			.insert()
			.name
		)

	def test_a_publicly_uploaded_answer_ends_up_private_and_anchored(self):
		"""The whole point. The browser chose public; the server did not."""
		user = fixtures.website_account("uploads.publicly")

		with fixtures.acting_as(user):
			url = _public_upload("chief-letter.txt")
			self.assertTrue(url.startswith("/files/"))

			application = fixtures.submit_volunteer_form(self.branch(), answers={self.question: url})

		stored = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name).custom_answers[0]

		self.assertTrue(stored.answer_file.startswith("/private/files/"))

		record = frappe.db.get_value(
			"File",
			{"file_url": stored.answer_file},
			["is_private", "attached_to_doctype", "attached_to_name"],
			as_dict=True,
		)

		self.assertTrue(record.is_private)
		self.assertEqual(record.attached_to_doctype, fixtures.APPLICATION_DOCTYPE)
		self.assertEqual(record.attached_to_name, application.name)

	def test_the_row_is_repointed_at_where_the_file_actually_went(self):
		"""Making a file private moves it. A row still holding the old URL would
		be a link to a stale public copy."""
		user = fixtures.website_account("repointed.row")

		with fixtures.acting_as(user):
			url = _public_upload("moved-letter.txt")
			application = fixtures.submit_volunteer_form(self.branch(), answers={self.question: url})

		stored = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name).custom_answers[0]

		self.assertNotEqual(stored.answer_file, url)
		self.assertFalse(frappe.db.exists("File", {"file_url": url}))

	def test_a_file_already_private_is_left_alone(self):
		"""The ordinary case on every re-save, and it must cost nothing."""
		user = fixtures.website_account("already.private")

		with fixtures.acting_as(user):
			private = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": "already-private.txt",
					"content": b"already private",
					"is_private": 1,
				}
			).insert(ignore_permissions=True)

			application = fixtures.submit_volunteer_form(
				self.branch(), answers={self.question: private.file_url}
			)

		stored = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name).custom_answers[0]

		self.assertEqual(stored.answer_file, private.file_url)

	def test_anchoring_twice_changes_nothing(self):
		"""`anchor_files` runs after every save of a draft."""
		user = fixtures.website_account("anchored.twice")

		with fixtures.acting_as(user):
			url = _public_upload("twice.txt")
			application = fixtures.submit_volunteer_form(self.branch(), answers={self.question: url})

		document = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name)
		first = document.custom_answers[0].answer_file

		questions.anchor_files(document)

		self.assertEqual(document.custom_answers[0].answer_file, first)


class TestGuardianEvidenceIsMadePrivate(RegistrationTestCase):
	def test_a_publicly_uploaded_consent_form_ends_up_private(self):
		user = fixtures.website_account("guardian.evidence")

		with fixtures.acting_as(user):
			url = _public_upload("signed-consent.txt")
			application = fixtures.submit_volunteer_form(
				self.branch(),
				applicant_date_of_birth=fixtures.minor_date_of_birth(16),
				guardian_consents=fixtures.guardian_consent(consent_evidence=url),
			)

		stored = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name).guardian_consents[0]

		self.assertTrue(stored.consent_evidence.startswith("/private/files/"))
		self.assertTrue(frappe.db.get_value("File", {"file_url": stored.consent_evidence}, "is_private"))

	def test_evidence_on_somebody_elses_server_is_refused(self):
		user = fixtures.website_account("guardian.offsite")

		with fixtures.acting_as(user), self.assertRaises(frappe.ValidationError):
			fixtures.submit_volunteer_form(
				self.branch(),
				applicant_date_of_birth=fixtures.minor_date_of_birth(16),
				guardian_consents=fixtures.guardian_consent(
					consent_evidence="https://evil.example/consent.pdf"
				),
			)


class TestNobodyElseCanReadIt(RegistrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.question = (
			frappe.get_doc(
				{
					"doctype": QUESTION_DOCTYPE,
					"asked_on": fixtures.APPLICATION_DOCTYPE,
					"question_label": "Your medical letter",
					"field_type": "Attach",
					"is_required": 0,
					"sequence": 2,
					"is_active": 1,
				}
			)
			.insert()
			.name
		)

	def test_another_applicant_cannot_reach_it(self):
		"""A private file inherits the application's permissions, and a second
		website account holds nothing on somebody else's application."""
		owner = fixtures.website_account("evidence.owner")

		with fixtures.acting_as(owner):
			url = _public_upload("medical.txt")
			application = fixtures.submit_volunteer_form(self.branch(), answers={self.question: url})

		stored = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name).custom_answers[0]
		name = frappe.db.get_value("File", {"file_url": stored.answer_file}, "name")

		stranger = fixtures.website_account("evidence.stranger")

		with fixtures.acting_as(stranger):
			self.assertFalse(frappe.has_permission("File", doc=name, ptype="read"))

	def test_the_approver_it_routed_to_can(self):
		"""The other half. Anchoring is what makes it readable by the right
		people — a private file with no parent belongs to its uploader alone."""
		owner = fixtures.website_account("evidence.for.approver")

		with fixtures.acting_as(owner):
			url = _public_upload("for-approver.txt")
			application = fixtures.submit_volunteer_form(self.branch(), answers={self.question: url})

		stored = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, application.name).custom_answers[0]
		name = frappe.db.get_value("File", {"file_url": stored.answer_file}, "name")

		with fixtures.acting_as(self.approver):
			self.assertTrue(frappe.has_permission("File", doc=name, ptype="read"))
