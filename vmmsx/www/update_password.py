# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The page the welcome email opens, and where a forgotten password is reset.

The other half of `vmmsx/www/login.py`, and it exists for one reason: a branded
email that hands somebody to an unbranded page has only moved the seam. The
welcome message carries the society's lockup, so the page its button opens
carries the same one.

Overridden the same way and as narrowly. Frappe's own `get_context` runs first,
and the template extends Frappe's — replacing the layout, inheriting the
`script` block whole. Every rule about what a password may be lives in that
script and in `frappe.core.doctype.user.user.update_password` behind it: the
strength meter, the confirmation match, the old-password requirement when there
is no key in the URL, the expiry of the key itself. None of it is reimplemented
here, because a second opinion about whether a password is acceptable is a way
for the two to disagree.
"""

from frappe.www.update_password import get_context as framework_context

from vmmsx import auth_page

no_cache = 1


def get_context(context):
	"""Frappe's set-password context, plus the society's mark and wording."""
	framework_context(context)
	context.update(auth_page.context())

	return context
