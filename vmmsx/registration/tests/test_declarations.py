# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The four things an applicant agrees to, and why they cannot move afterwards.

The tests that matter here are the last three. Anybody can check that a required
box has to be ticked; what makes a consent register worth keeping is that the
wording somebody agreed to is still the wording on their record after the
society has rewritten it, after they have saved the form again, and after the
application has been decided.
"""

import frappe

from vmmsx.registration.services import declarations
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

DECLARATION_DOCTYPE = "VMMS Declaration"


class DeclarationTestCase(RegistrationTestCase):
	def restore_later(self, key: str) -> None:
		"""Put a declaration back the way this test found it.

		**Frappe rolls the test transaction back once per class, not per
		method**, and unittest runs methods in alphabetical order rather than
		the order they are written in. So a test that reworded a declaration
		left it reworded for every test whose name sorts after it — which here
		meant the snapshot assertions passing or failing on the strength of
		their own names. Restoring explicitly is the only thing that makes each
		of these a test of one thing.
		"""
		before = frappe.db.get_value(
			DECLARATION_DOCTYPE, key, ["body", "version", "is_active", "sequence"], as_dict=True
		)

		def put_back():
			frappe.db.set_value(DECLARATION_DOCTYPE, key, dict(before))
			frappe.clear_document_cache(DECLARATION_DOCTYPE, key)

		self.addCleanup(put_back)


class TestDeclarationsAreRequired(DeclarationTestCase):
	def test_the_society_ships_four_of_them_against_the_application(self):
		"""The installer ran, and it pointed them at the volunteer application."""
		shown = declarations.shown_on(fixtures.APPLICATION_DOCTYPE)

		self.assertEqual(len(shown), 4)
		self.assertTrue(all(row["is_required"] for row in shown))

	def test_an_application_with_nothing_accepted_cannot_be_submitted(self):
		user = fixtures.website_account("declines.everything")

		with fixtures.acting_as(user), self.assertRaises(frappe.MandatoryError) as refusal:
			fixtures.submit_volunteer_form(self.branch(), declarations_accepted=[])

		# The message names what is missing, because the applicant is the one
		# who has to go and fix it.
		self.assertIn("How we will use your information", str(refusal.exception))

	def test_accepting_only_some_of_them_is_still_refused(self):
		user = fixtures.website_account("declines.one")
		partial = fixtures.required_declarations()[:2]

		with fixtures.acting_as(user), self.assertRaises(frappe.MandatoryError):
			fixtures.submit_volunteer_form(self.branch(), declarations_accepted=partial)

	def test_a_deactivated_declaration_stops_being_required(self):
		"""Deactivating is the society's way out, and it takes effect at once."""
		key = fixtures.required_declarations()[0]
		self.restore_later(key)
		frappe.db.set_value(DECLARATION_DOCTYPE, key, "is_active", 0)
		frappe.clear_document_cache(DECLARATION_DOCTYPE, key)

		remaining = [row for row in fixtures.required_declarations() if row != key]
		user = fixtures.website_account("after.deactivation")

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch(), declarations_accepted=remaining)

		self.assertEqual(application.approval_state, "In Review")


class TestAcceptancesAreSnapshots(DeclarationTestCase):
	def test_the_text_agreed_to_is_stored_on_the_application(self):
		_, application = self.register_as_volunteer("snapshot.applicant")

		accepted = declarations.accepted_of(application)
		privacy = next(row for row in accepted if "How we will use" in row["title"])

		self.assertTrue(privacy["accepted"])
		self.assertTrue(privacy["accepted_on"])
		self.assertEqual(privacy["version"], "1")
		self.assertIn("consider your application", privacy["body"])

	def test_rewriting_the_declaration_does_not_rewrite_what_was_agreed(self):
		"""The whole point of the doctype. A consent nobody can restate.

		The society's legal officer reworks the privacy notice — new wording, new
		version — and the application decided last week must still show the words
		that applicant put their name to.
		"""
		_, application = self.register_as_volunteer("before.the.rewrite")

		key = next(
			row["declaration"]
			for row in declarations.accepted_of(application)
			if "How we will use" in row["title"]
		)

		self.restore_later(key)

		document = frappe.get_doc(DECLARATION_DOCTYPE, key)
		document.body = "<p>Entirely different wording, agreed to by nobody.</p>"
		document.version = "2"
		document.save()

		application.reload()
		stored = next(row for row in declarations.accepted_of(application) if row["declaration"] == key)

		self.assertEqual(stored["version"], "1")
		self.assertIn("consider your application", stored["body"])
		self.assertNotIn("agreed to by nobody", stored["body"])

	def test_saving_the_draft_again_does_not_move_the_acceptance(self):
		"""A consent is an act at a moment; re-saving a form is not that moment."""
		from vmmsx.api import registration as registration_api

		user = fixtures.website_account("resaves.the.draft")

		with fixtures.acting_as(user):
			first = registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				declarations_accepted=fixtures.required_declarations(),
			)
			original = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, first["name"]).declarations[0].accepted_on

			registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				prior_experience="Changed my mind about this bit",
				declarations_accepted=fixtures.required_declarations(),
			)
			again = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, first["name"]).declarations[0].accepted_on

		self.assertEqual(original, again)

	def test_unticking_and_reticking_records_a_new_acceptance(self):
		"""Withdrawing consent is real, and giving it again is a fresh act."""
		from vmmsx.api import registration as registration_api

		user = fixtures.website_account("changes.their.mind")
		required = fixtures.required_declarations()

		with fixtures.acting_as(user):
			draft = registration_api.save_my_volunteer_draft(
				geo_node=self.branch(), declarations_accepted=required
			)
			registration_api.save_my_volunteer_draft(geo_node=self.branch(), declarations_accepted=[])

			withdrawn = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, draft["name"])

			self.assertFalse(any(row.accepted for row in withdrawn.declarations))
			# The row survives with the tick cleared, because "we asked and they
			# said no" is a different fact from "we never asked".
			self.assertEqual(len(withdrawn.declarations), len(required))
			self.assertFalse(withdrawn.declarations[0].accepted_on)

			registration_api.save_my_volunteer_draft(geo_node=self.branch(), declarations_accepted=required)
			restored = frappe.get_doc(fixtures.APPLICATION_DOCTYPE, draft["name"])

		self.assertTrue(all(row.accepted for row in restored.declarations))
		self.assertTrue(restored.declarations[0].accepted_on)


class TestVersionDiscipline(DeclarationTestCase):
	"""The wording is not editable here at all, and that replaced a weaker rule.

	This class used to assert that changing `body` without moving `version` was
	refused. That was the best a single editable row could do, and it was not
	enough on either side: it stopped a careless rewording and not a deliberate
	one, and either way the wording it replaced was destroyed. Wording now lives
	in `VMMS Declaration Version`, which is submittable, and these four fields on
	the declaration are a mirror of whichever version is published. See
	`test_declaration_versions.py` for the properties that replaced this one.
	"""

	def test_the_wording_cannot_be_edited_on_the_declaration(self):
		"""Derived, and derived means it does not survive the save that carried it.

		`read_only` is a form-level hint — the server stores whatever a script
		puts in such a field — so the guarantee is that `validate` re-reads the
		published version over the top. The same shape as
		`VMMS Volunteer Application.is_minor`.
		"""
		key = fixtures.required_declarations()[0]
		self.restore_later(key)

		before = frappe.db.get_value(DECLARATION_DOCTYPE, key, "body")

		document = frappe.get_doc(DECLARATION_DOCTYPE, key)
		document.body = "<p>Materially different wording.</p>"
		document.save()

		self.assertEqual(frappe.db.get_value(DECLARATION_DOCTYPE, key, "body"), before)

	def test_the_version_label_cannot_be_edited_here_either(self):
		"""Otherwise an acceptance could be stamped with a label naming no record."""
		key = fixtures.required_declarations()[0]
		self.restore_later(key)

		document = frappe.get_doc(DECLARATION_DOCTYPE, key)
		document.version = "99"
		document.save()

		self.assertEqual(frappe.db.get_value(DECLARATION_DOCTYPE, key, "version"), "1")

	def test_publishing_a_version_is_what_changes_the_wording(self):
		"""Against a declaration of this test's own, and deliberately not a shipped one.

		Publishing a second version of the privacy notice would change the
		version label every other application in this suite is stamped with —
		the interference this class's `restore_later` exists to prevent, which a
		new *version record* would defeat because restoring the mirror does not
		unpublish anything. Inactive, so it can never reach a form either.
		"""
		key = "suite-version-discipline"

		frappe.get_doc(
			{
				"doctype": DECLARATION_DOCTYPE,
				"declaration_key": key,
				"applies_to": fixtures.APPLICATION_DOCTYPE,
				"title": "Published rather than typed",
				"sequence": 900,
				"is_required": 0,
				"is_active": 0,
			}
		).insert(ignore_permissions=True)

		declarations.publish(key, "1", body="<p>As first published.</p>")
		declarations.publish(key, "2", body="<p>Materially different wording.</p>")

		row = frappe.db.get_value(DECLARATION_DOCTYPE, key, ["version", "body"], as_dict=True)

		self.assertEqual(row.version, "2")
		self.assertIn("Materially different", row.body)

	def test_editing_something_other_than_the_wording_still_works(self):
		"""Reordering the form is not a change to what anybody agreed to."""
		key = fixtures.required_declarations()[0]
		self.restore_later(key)

		document = frappe.get_doc(DECLARATION_DOCTYPE, key)
		document.sequence = 99
		document.save()

		self.assertEqual(frappe.db.get_value(DECLARATION_DOCTYPE, key, "sequence"), 99)
