# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The two auth pages render, and they depend on nothing this app does not own.

This suite exists because of an outage. `vmmsx/www/login.html` and
`update-password.html` imported `alert_banner` from Frappe's own
`templates/includes/login/macros.html`. That file landed in Frappe on
2026-07-20, six months after v16.0.0 was tagged, so it exists on `develop` and
nowhere else. The bench this app is developed on runs 17.0.0-dev and had it;
`pyproject.toml` pins `frappe = ">=16.0.0,<17.0.0"`, which is what Frappe Cloud
installs against, and production answered **500 on the sign-in page** — the one
page whose failure is everybody locked out, staff included.

Nothing about it was catchable locally, because locally it worked. So the guard
is not "does it render here" alone — that is the assertion that passed while
production was down. It is **what the templates are allowed to import**: the
only `{% from %}` in either file must resolve inside this app. A macro we own
cannot disappear underneath us when a site runs a different framework version.

`{% extends %}` is deliberately not covered by that rule. Both pages extend the
framework's own page and are meant to: that inheritance is what keeps
authentication Frappe's, and `frappe/www/login.html` has existed in every
version this app supports. The version-sensitive half is the DOM contract each
version's `login.js` expects, which is documented in `login.html`'s own header
and satisfied for both — asserted here as the markers each script looks for.
"""

import re
from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase

AUTH_PAGES = ("login.html", "update-password.html")

# Where a `{% from %}` in one of those pages is allowed to point. Anything else
# is a dependency on another app's internals, which is the bug this suite is
# named after.
OURS = "templates/includes/auth/"

FROM_IMPORT = re.compile(r"{%-?\s*from\s+[\"']([^\"']+)[\"']")


def www(name: str) -> Path:
	return Path(frappe.get_app_path("vmmsx")) / "www" / name


def render(route: str) -> str:
	"""The page as a signed-out visitor gets it, through the real website stack.

	A request object is built because `frappe/www/login.py::get_context` reads
	`redirect-to` off the query string, and a bare script has no request.
	"""
	from frappe.website.serve import get_response
	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	previous = getattr(frappe.local, "request", None)
	frappe.local.request = Request(EnvironBuilder(path=f"/{route}", method="GET").get_environ())

	try:
		response = get_response(route)
	finally:
		frappe.local.request = previous

	assert response.status_code == 200, f"/{route} answered {response.status_code}"

	return response.get_data(as_text=True)


class TestTheAuthPagesOwnTheirDependencies(IntegrationTestCase):
	def test_every_macro_import_resolves_inside_this_app(self):
		"""The regression itself. A template from another app is a template that
		can be absent on the framework version production actually runs."""
		for page in AUTH_PAGES:
			for imported in FROM_IMPORT.findall(www(page).read_text()):
				self.assertTrue(
					imported.startswith(OURS),
					f"{page} imports {imported!r}, which this app does not own",
				)

	def test_the_macro_they_import_is_really_there(self):
		"""Owning the path is not the same as the file existing."""
		for page in AUTH_PAGES:
			for imported in FROM_IMPORT.findall(www(page).read_text()):
				path = Path(frappe.get_app_path("vmmsx")) / imported

				self.assertTrue(path.exists(), f"{page} imports missing {imported}")


class TestBothPagesRenderForAStranger(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Guest")

	def test_the_sign_in_page_renders(self):
		self.assertIn("form-login", render("login"))

	def test_the_password_page_renders(self):
		self.assertTrue(render("update-password"))

	def test_the_sign_up_form_is_on_the_page(self):
		"""The path that was reported broken. Signing up is a section of the sign-in
		page rather than a page of its own, so a 500 here is a 500 for everybody."""
		body = render("login")

		self.assertIn("form-signup", body)
		self.assertIn("signup_email", body)

	def test_both_error_mechanisms_are_present(self):
		"""v17's `login.js` writes into `.login-error-banner .es-alert__title`;
		v16's replaces the text of `section:visible .btn-primary`. The page is
		inherited by whichever framework the site runs, so it carries both. See
		the contract note at the top of `login.html`."""
		body = render("login")

		self.assertIn("login-error-banner", body)
		self.assertIn("es-alert__title", body)
		self.assertIn("btn-primary", body)

	def test_every_submit_button_carries_both_hooks(self):
		"""`btn-primary` on its own would be a v16 page and `es-button` on its own
		a v17 one. Each submit button is both, or one version cannot report an
		error on it."""
		buttons = re.findall(r"<button[^>]*type=\"submit\"[^>]*>", www("login.html").read_text())

		self.assertTrue(buttons)
		for button in buttons:
			self.assertIn("es-button", button)
			self.assertIn("btn-primary", button)


class TestCreatingAnAccountEndsSomewhere(IntegrationTestCase):
	"""The panel that replaces the sign-up form, and the page owning its submit.

	`login.js` answers a successful sign-up by writing "Success" on the button
	and leaving the filled-in form on screen, which reads as though there is
	still something to do — and offers nothing at all when the mail does not
	arrive, because the framework has no resend for sign-up. This page therefore
	handles that one submit itself.

	What is asserted is the *seam*, not the behaviour: the two halves are on the
	page, the framework's endpoints are the ones being called, and the handler is
	bound where it can actually run first. A capture-phase listener bound
	anywhere but an ancestor would be one `login.js` beats to the event, and the
	symptom would be the old panel flashing back — which no render test would
	catch.
	"""

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Guest")

	def test_the_form_and_the_panel_that_replaces_it_are_both_there(self):
		body = render("login")

		self.assertIn("signup-start", body)
		self.assertIn("signup-sent", body)

	def test_the_panel_starts_hidden(self):
		"""Or a visitor arriving at `#signup` reads "check your email" before
		they have typed anything."""
		body = render("login")

		self.assertRegex(body, r"class=\"signup-sent hidden\"")

	def test_there_is_a_way_to_ask_for_another_link(self):
		body = render("login")

		self.assertIn("btn-resend-signup", body)
		self.assertIn("auth-cooldown", body)

	def test_the_page_calls_the_frameworks_own_endpoints(self):
		"""Account creation and password links stay Frappe's. An app-owned door
		onto either would be a second implementation of a rule with somebody's
		identity in it."""
		body = render("login")

		self.assertIn("frappe.core.doctype.user.user.sign_up", body)
		self.assertIn("frappe.core.doctype.user.user.reset_password", body)

	def test_the_submit_is_intercepted_where_it_can_win(self):
		"""On an ancestor, in the capture phase. `login.js` binds to the form
		itself, so an event stopped on the way down never reaches it."""
		source = www("login.html").read_text()

		self.assertRegex(source, r"document\.addEventListener\(\s*\n?\s*\"submit\"")
		self.assertIn("stopPropagation", source)

	def test_the_wording_is_the_societys_to_change(self):
		"""Every sentence on either half is a `login` surface block, the same rule
		the rest of the page follows."""
		source = www("login.html").read_text()

		for key in ("login.signup.sent_title", "login.signup.sent_body", "login.signup.pending_body"):
			self.assertIn(key, source)
