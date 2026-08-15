# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The account-created email: it names the society, and it never eats an edit.

Two things are being protected, and they pull in opposite directions.

The **subject** is the reason this message is an `Email Template` rather than an
override of `frappe/templates/emails/new_user.html`. Frappe takes it from
`get_hooks("welcome_email")[-1]` — last app installed wins, and no app can ask
for a position — so on a bench with ERPNext the society's welcome email arrives
titled "Welcome to ERPNext". The setting this module writes is not contested by
anybody. A test that only rendered the body would have passed for the
implementation that shipped that subject.

The **overwrite rules** are the other half. `install()` runs on every migrate, so
a society that has rewritten its welcome message, or named a template of its
own, has to survive a deploy. Both are asserted by editing and re-running.

The rendering is Frappe's own `get_email_template`, not a re-implementation, so
what is asserted is what an actual welcome email would carry.
"""

import frappe
from frappe.email.doctype.email_template.email_template import get_email_template
from frappe.tests import IntegrationTestCase

from vmmsx.notifications.seeds import welcome_email
from vmmsx.notifications.services import welcome

EXTRA_TEST_RECORD_DEPENDENCIES = []

ARGS = {
	"first_name": "Fatou",
	"user": "fatou@example.test",
	"link": "http://example.test/update-password?key=probe",
	"site_url": "http://example.test",
	"created_by": "Administrator",
}


class TestInstallingTheWelcomeEmail(IntegrationTestCase):
	def setUp(self):
		super().setUp()

		if frappe.db.exists("Email Template", welcome_email.TEMPLATE_NAME):
			frappe.delete_doc("Email Template", welcome_email.TEMPLATE_NAME, force=True)

		frappe.db.set_single_value("System Settings", welcome.SETTING_FIELD, "")
		frappe.clear_document_cache("System Settings", "System Settings")

	def test_it_creates_the_template_and_points_the_site_at_it(self):
		result = welcome.install()

		self.assertEqual(result["template"], "created")
		self.assertEqual(result["setting"], "set")
		self.assertEqual(
			frappe.db.get_single_value("System Settings", welcome.SETTING_FIELD),
			welcome_email.TEMPLATE_NAME,
		)

	def test_running_it_twice_changes_nothing_the_second_time(self):
		welcome.install()

		self.assertEqual(welcome.install(), {"template": "exists", "setting": "exists"})

	def test_a_society_that_rewrote_the_message_keeps_every_word_of_it(self):
		welcome.install()

		theirs = "<p>Kaabo. An account has been made for you.</p>"
		frappe.db.set_value("Email Template", welcome_email.TEMPLATE_NAME, "response_html", theirs)
		frappe.clear_document_cache("Email Template", welcome_email.TEMPLATE_NAME)

		welcome.install()

		self.assertEqual(
			frappe.db.get_value("Email Template", welcome_email.TEMPLATE_NAME, "response_html"), theirs
		)

	def test_a_template_the_society_chose_for_itself_is_not_replaced(self):
		frappe.db.set_single_value("System Settings", welcome.SETTING_FIELD, "Some Society Template")
		frappe.clear_document_cache("System Settings", "System Settings")

		welcome.install()

		self.assertEqual(
			frappe.db.get_single_value("System Settings", welcome.SETTING_FIELD), "Some Society Template"
		)


class TestWhatTheMessageSays(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		if not frappe.db.exists("Email Template", welcome_email.TEMPLATE_NAME):
			welcome.install()

	def _rendered(self) -> dict:
		return get_email_template(welcome_email.TEMPLATE_NAME, dict(ARGS))

	def test_the_subject_carries_the_society_rather_than_a_product_name(self):
		"""The whole reason this is a record. See the module docstring."""
		from vmmsx.notifications.services.branding import lockup

		society = lockup()["brand_name"]
		subject = self._rendered()["subject"]

		if society:
			self.assertIn(society, subject)
		else:
			# An unnamed society still gets a subject that reads correctly, which
			# is the degradation every branded surface in this app takes.
			self.assertTrue(subject.strip())

		self.assertNotIn("ERPNext", subject)
		self.assertNotIn("Frappe", subject)

	def test_the_body_says_who_they_will_sign_in_as_and_where_to_set_a_password(self):
		message = self._rendered()["message"]

		self.assertIn(ARGS["user"], message)
		self.assertIn(ARGS["link"], message)

	def test_it_draws_no_mark_of_its_own(self):
		"""The lockup is `standard.html`'s job, once, around every message."""
		message = self._rendered()["message"]

		self.assertNotIn("<img", message)
