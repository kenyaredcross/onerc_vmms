# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The society's sign-in page.

This module and its template *override* `frappe/www/login.py` and
`frappe/www/login.html`. Frappe's website resolver walks the installed apps in
reverse install order, so vmmsx's copy of a `www/` page is the one served — the
same mechanism `templates/emails/standard.html` already uses to put the
society's lockup on outgoing mail, and the only mechanism the framework offers
for this page: there is no hook for the layout of `/login`.

**Almost nothing is overridden, and that is the design.** The context below is
Frappe's own `get_context` called first and then added to. Everything it decides
still decides it: whether sign-up is disabled, whether a password may be used at
all, which OAuth providers are configured, whether LDAP is on, what the login
field is called on a site that permits mobile numbers, whether login by email
link is available, and the redirect that sends somebody already signed in
straight back where they came from. The template extends Frappe's for the same
reason and inherits its `script` block whole, so `login.js` — and with it
password login, forgotten password, sign-up, email-link login, LDAP and
two-factor — is the framework's code running unchanged.

What this app adds is a page: a panel carrying the society's mark and its own
sentences, and a form that looks like the rest of the product. See
`vmmsx/auth_page.py` for where the mark and the words come from.

**The one thing deliberately not drawn is a one-time code by SMS.** The design
asked for it and the framework has no such thing — SMS exists in Frappe only as
a *second* factor after a password, never as a way in on its own — so the slot
is absent rather than dead. Same rule as `<NotBuilt>` on the React side: a
control that looks like it works and does not is worse than no control.
"""

import frappe
from frappe.utils.oauth import get_oauth2_authorize_url
from frappe.www.login import get_context as framework_context

from vmmsx import auth_page
from vmmsx.registration.services.desk import PORTAL_HOME

no_cache = True


def get_context(context):
	"""Frappe's login context, plus the society's mark and this page's wording.

	Frappe's own `get_context` runs first and is allowed to raise: it is what
	redirects a visitor who is already signed in, and short-circuiting that would
	leave a signed-in person looking at a sign-in form.
	"""
	framework_context(context)
	context.update(auth_page.context())
	_point_social_logins_at_the_portal(context)

	return context


def _point_social_logins_at_the_portal(context) -> None:
	"""Give a social sign-in somewhere to land, when the URL named nowhere.

	**Signing in with Google took people to a permission error.** The password
	form has a fix for this already, and it is in the template: a signed-out
	visitor who reaches `/login` with no `?redirect-to` gets `last_visited`
	seeded with the portal, and `login.js` prefers it. A social sign-in never
	reaches that code. It leaves the browser for the provider and comes back
	through `frappe.utils.oauth.login_oauth_user`, which redirects **server
	side** to whatever `redirect_to` was stamped into the OAuth state when the
	button was rendered — and the framework stamps in the `redirect-to` query
	argument and nothing else. With none, `redirect_post_login` falls through to
	`get_default_path()`, which on a bench carrying several apps is `/apps`,
	which Frappe sends on to `/desk`: the one address a Website User cannot open.
	So the volunteer this whole product is for signed in successfully and landed
	on "Not Permitted".

	The fix is to stamp a destination rather than to intercept the return: the
	state is created when the authorize URL is built, which is here, and it is
	the last moment anything on this side of the round trip knows where the
	person came from.

	**Only when nothing was asked for.** A URL carrying `redirect-to` is somebody
	being sent back to a specific screen — `RequireAuth` does exactly that — and
	overwriting it would drop them on the dashboard instead of where they were
	going. Same two guards the template's `last_visited` seeding makes, for the
	same reason.

	**Staff land on the portal too, and that is the accepted cost.** Unlike the
	template's `last_visited` seeding — which the framework only consults for a
	Website User — `redirect_post_login` uses the stamped destination whoever
	signed in, and nothing on this side of an OAuth round trip knows which kind
	of account is coming back: the account may not exist yet. So a System Manager
	who signs in with Google and asked for nothing in particular arrives at the
	portal rather than at the desk. That is a page they can open, with the
	console and the desk both one click away in the sidebar, and it is traded
	against the alternative: every volunteer signing in with Google landing on a
	permission error. A member of staff who wants the desk asks for it, and the
	guard above leaves that URL alone.

	Never raises. A provider list this could not rewrite is a page that still
	takes a password, and a broken sign-in page is everybody locked out.
	"""
	try:
		if frappe.local.request and frappe.local.request.args.get("redirect-to"):
			return

		for provider in context.get("provider_logins") or []:
			# Rebuilt rather than patched: the destination lives in a cached
			# state token keyed by the URL's `state` argument, so the only way to
			# change it is to mint a new one. The token the first call created is
			# never used and expires on its own ten minutes later.
			provider["auth_url"] = get_oauth2_authorize_url(provider["name"], PORTAL_HOME)
	except Exception:
		frappe.log_error(title="vmmsx: could not point social sign-in at the portal")
