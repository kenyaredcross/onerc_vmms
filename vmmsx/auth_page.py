# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What the sign-in and set-password pages draw themselves from.

Two pages in `vmmsx/www/` share one panel, one stylesheet and one set of words,
so this is the single place that answers "whose page is this and what does it
say". Both pages are otherwise Frappe's own — each template *extends* the
framework's, overriding the layout blocks and inheriting the script, so every
authentication path on them (password, forgotten password, sign-up, login by
email link, LDAP, OAuth, two-factor) is the framework's code running unchanged.
This module never touches any of that. It supplies a mark and a paragraph.

**The lockup is the society's, never the product's.** Name and logo come from
core's `National Society Settings` through `get_ui_config()`, exactly as
`api/society.py::branding` reads them for the portal and
`notifications/services/branding.py` reads them for outgoing mail. Three readers
of one answer, and no fourth home for a society's identity.

`logo_dark` rather than `logo`, because the panel these are drawn on is navy;
core already falls back to `logo` for a society that uploaded only one mark.

**The words are content blocks.** Every sentence on either page belongs to the
`login` surface, so a society rewrites its own sign-in page from the desk rather
than asking for a deploy — the rule the whole `VMMS Content` module exists for.
There is no pencil on the page itself, and that is the one deliberate difference
from the React screens: these pages are served to somebody who has not signed
in, and an edit control drawn for a stranger is not an edit control.

**Nothing here may raise.** This runs while rendering the door to the site. A
society that has never opened the settings form, a `National Society Settings`
that will not load, a content surface nobody seeded — each has to produce a
plain page rather than a traceback, because the failure of a login page is
everybody locked out. Every value below is therefore optional, and every caller
in the templates has its own fallback wording.
"""

import frappe

from vmmsx.content.services import blocks as block_service
from vmmsx.registration.services.desk import PORTAL_HOME

#: The content surface both pages read. Public, because its wording is on a page
#: served to signed-out visitors; that flag is what `api/content.py::surface`
#: would consult if the React side ever asked for it, and it is the same rule
#: rather than a second one.
SURFACE = "login"


def context() -> dict:
	"""The society's mark, the page's wording, and the panel photograph."""
	society = _society()
	words, panel = _content()

	return {
		"society_name": society.get("name") or society.get("short_name") or "",
		"society_logo": society.get("logo_dark") or society.get("logo") or "",
		"portal_home": PORTAL_HOME,
		"words": words,
		"panel_image": panel.get("image") or "",
		"panel_image_alt": panel.get("image_alt") or "",
		"panel_image_credit": panel.get("image_credit") or "",
	}


def _society() -> dict:
	"""Core's answer about who this society is, or nothing at all.

	Deliberately broad and deliberately quiet, for the reason in the module
	docstring: the alternative to swallowing this is a site nobody can sign in
	to. An unbranded page still takes a password.
	"""
	try:
		from onerc_core.society.services.config import get_ui_config

		return get_ui_config()["society"]
	except Exception:
		frappe.log_error(title="vmmsx: could not read society branding for the sign-in page")
		return {}


def _content() -> tuple[dict, dict]:
	"""Every word of the `login` surface, keyed by content key, and the photo.

	`surface_dto` reads with `frappe.get_all`, which does not run the permission
	layer — the deliberate opposite of the rule analytics follows, and for the
	opposite reason. The caller here is a signed-out visitor by construction, and
	what is being read is the wording of the page they are already looking at.
	The read boundary is the page, not the query.

	Returns plain text keyed by content key, plus the panel block whole, because
	an image slot carries three fields the text map cannot hold.
	"""
	try:
		blocks = block_service.surface_dto(SURFACE)
	except Exception:
		frappe.log_error(title="vmmsx: could not read the sign-in page wording")
		return {}, {}

	words = {key: block["text"] for key, block in blocks.items() if block.get("text")}

	return words, blocks.get("login.panel.image") or {}
