# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What a policy said on the day, and the fact that nobody can change it later.

A declaration used to be one editable row: rewording it overwrote the wording it
replaced, and the only reason any history survived was that an acceptance
snapshotted the text. A society that corrected its privacy notice before anybody
applied lost the original completely.

The tests here are about the two properties that replaced that. **Published
wording is frozen** — not by a rule this app enforces, which is a rule somebody
can be talked into skipping, but by `docstatus`, which the framework itself
refuses to write past. And **a policy may be a link** rather than words, because
a national society whose legal team owns the privacy page on its own website will
not maintain a second copy here — with the register recording honestly that what
it holds in that case is an address and not the text.
"""

import frappe

from vmmsx.registration.services import declarations
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

DECLARATION_DOCTYPE = "VMMS Declaration"
VERSION_DOCTYPE = "VMMS Declaration Version"


class VersionTestCase(RegistrationTestCase):
	"""A declaration of this suite's own, torn down with the transaction.

	Deliberately not one of the four shipped ones. Those are what every other
	registration test submits against, and publishing a second version of the
	privacy notice here would change the version label every application in the
	suite is stamped with — the same interference `test_declarations.py` describes
	and solves by restoring what it touched.
	"""

	def make_declaration(self, key: str, body: str = "<p>Version one.</p>") -> str:
		frappe.get_doc(
			{
				"doctype": DECLARATION_DOCTYPE,
				"declaration_key": key,
				"applies_to": fixtures.APPLICATION_DOCTYPE,
				"title": "A policy of our own",
				"sequence": 900,
				"is_required": 0,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		declarations.publish(key, "1", body=body)

		return key

	def shown(self, key: str) -> dict | None:
		for row in declarations.shown_on(fixtures.APPLICATION_DOCTYPE):
			if row["name"] == key:
				return row

		return None


class TestPublishingIsWhatMakesWordingReal(VersionTestCase):
	def test_the_shipped_declarations_each_have_a_published_version(self):
		"""The installer publishes rather than typing the body onto the row."""
		for key in fixtures.required_declarations():
			self.assertIsNotNone(
				declarations.current_version(key),
				f"{key} has no published version",
			)

	def test_the_declaration_mirrors_what_is_published(self):
		key = self.make_declaration("suite-mirror-check")
		row = frappe.get_doc(DECLARATION_DOCTYPE, key)

		self.assertEqual(row.version, "1")
		self.assertEqual(row.source, declarations.SOURCE_TEXT)
		self.assertIn("Version one", row.body)

	def test_published_wording_cannot_be_edited(self):
		"""The guarantee, and it is the framework's rather than this app's."""
		key = self.make_declaration("suite-frozen")
		version = frappe.get_doc(VERSION_DOCTYPE, declarations.current_version(key))

		version.body = "<p>Quietly different.</p>"

		with self.assertRaises(frappe.exceptions.ValidationError):
			version.save(ignore_permissions=True)

	def test_a_second_version_supersedes_the_first_and_the_first_survives(self):
		key = self.make_declaration("suite-supersede")
		first = declarations.current_version(key)

		declarations.publish(key, "2", body="<p>Version two.</p>")

		self.assertNotEqual(declarations.current_version(key), first)
		self.assertIn("Version two", frappe.db.get_value(DECLARATION_DOCTYPE, key, "body"))

		# The whole point. The wording nobody is being shown any more is still
		# there to be read.
		self.assertIn("Version one", frappe.db.get_value(VERSION_DOCTYPE, first, "body"))

	def test_withdrawing_a_version_falls_back_to_the_one_before_it(self):
		key = self.make_declaration("suite-withdraw")
		second = declarations.publish(key, "2", body="<p>Version two.</p>")

		second.cancel()

		self.assertIn("Version one", frappe.db.get_value(DECLARATION_DOCTYPE, key, "body"))
		self.assertEqual(frappe.db.get_value(DECLARATION_DOCTYPE, key, "version"), "1")

	def test_two_versions_cannot_wear_the_same_label(self):
		"""And it is refused in words, not as a primary-key collision.

		The docname is built from the declaration and the version, so a repeat
		autonames to the same name as the row it repeats. The check has to notice
		that before the insert does, or an administrator gets "Duplicate entry
		for key PRIMARY" and no idea what to do about it.
		"""
		key = self.make_declaration("suite-duplicate-label")

		with self.assertRaises(frappe.DuplicateEntryError) as refusal:
			declarations.publish(key, "1", body="<p>Also version one.</p>")

		self.assertIn("version label of its own", str(refusal.exception))


class TestAPolicyMayBeALink(VersionTestCase):
	ADDRESS = "https://example.redcross.org/privacy"

	def test_a_link_version_is_served_as_a_link(self):
		key = self.make_declaration("suite-linked")
		declarations.publish(key, "2", external_url=self.ADDRESS)

		shown = self.shown(key)

		self.assertEqual(shown["source"], declarations.SOURCE_LINK)
		self.assertEqual(shown["external_url"], self.ADDRESS)

	def test_a_link_version_holds_no_body(self):
		"""One answer to what a version says, never two."""
		key = self.make_declaration("suite-linked-no-body")
		version = declarations.publish(key, "2", external_url=self.ADDRESS)

		self.assertFalse(version.body)

	def test_a_link_version_with_no_address_is_refused(self):
		key = self.make_declaration("suite-linked-empty")

		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": VERSION_DOCTYPE,
					"declaration": key,
					"version": "2",
					"source": declarations.SOURCE_LINK,
				}
			).insert(ignore_permissions=True)

	def test_a_text_version_with_no_wording_is_refused(self):
		key = self.make_declaration("suite-text-empty")

		with self.assertRaises(frappe.MandatoryError):
			frappe.get_doc(
				{
					"doctype": VERSION_DOCTYPE,
					"declaration": key,
					"version": "2",
					"source": declarations.SOURCE_TEXT,
				}
			).insert(ignore_permissions=True)


class TestWhatAnAcceptanceRecords(VersionTestCase):
	def application_of(self, handle: str):
		_, application = self.register_as_volunteer(handle)

		return application

	def test_an_acceptance_names_the_version_record_it_was_made_against(self):
		application = self.application_of("names.the.version")
		key = fixtures.required_declarations()[0]

		row = next(r for r in application.declarations if r.declaration == key)

		self.assertEqual(row.declaration_version, declarations.current_version(key))
		self.assertEqual(row.source, declarations.SOURCE_TEXT)

	def test_an_acceptance_against_a_link_records_the_address_and_no_wording(self):
		"""The honest record. An empty snapshot beside a stored address is not a
		snapshot that failed — it is the only snapshot there was to take."""
		key = self.make_declaration("suite-accepted-link")
		declarations.publish(key, "2", external_url=TestAPolicyMayBeALink.ADDRESS)

		application = self.application_of("accepts.a.link")
		row = next(r for r in application.declarations if r.declaration == key)

		self.assertEqual(row.source, declarations.SOURCE_LINK)
		self.assertEqual(row.external_url, TestAPolicyMayBeALink.ADDRESS)
		self.assertFalse(row.body_snapshot)

	def test_an_acceptance_keeps_its_wording_after_the_policy_is_reworded(self):
		"""The rule the whole module exists for, now with the superseded wording
		still readable on both sides of the comparison."""
		key = self.make_declaration("suite-reword-after")
		application = self.application_of("agreed.to.version.one")

		row = next(r for r in application.declarations if r.declaration == key)
		self.assertEqual(row.version, "1")

		declarations.publish(key, "2", body="<p>Version two.</p>")

		application.reload()
		row = next(r for r in application.declarations if r.declaration == key)

		self.assertEqual(row.version, "1")
		self.assertIn("Version one", row.body_snapshot)
