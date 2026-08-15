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

from frappe.www.login import get_context as framework_context

from vmmsx import auth_page

no_cache = True


def get_context(context):
	"""Frappe's login context, plus the society's mark and this page's wording.

	Frappe's own `get_context` runs first and is allowed to raise: it is what
	redirects a visitor who is already signed in, and short-circuiting that would
	leave a signed-in person looking at a sign-in form.
	"""
	framework_context(context)
	context.update(auth_page.context())

	return context
