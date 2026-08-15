# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The society's lockup, for the top of every message this site sends.

**The words in a notification are the site's; the mark around them is the
app's.** A society writes its own notification text on the desk — Frappe's own
`Notification` and `Email Template` doctypes are where a message says what it
says, and vmmsx does not hold a second copy of any of it. What this module adds
is the wrapper: the name and logo the society already uploaded to core's
`National Society Settings` appear above that text, so an email that came from
this system looks like it came from *them*.

That split is the whole design. Editing the wording is a content change and
needs no deploy; changing the mark is a settings change and needs no deploy
either. Neither is a string in a source file.

**Read through core's service, never off the doctype.** `get_ui_config()` is the
supported reader and its fallbacks are the contract, exactly as
`api/society.py::branding` reads it for the portal's lockup. Two readers of one
answer, not two answers.

**Empty is ordinary and must stay silent.** A fresh site has never had the
settings form opened, and core loads that Single with every field blank. Nothing
here invents a name, and the template draws no masthead at all rather than an
empty box or a broken image. A society that has not uploaded a mark gets the
plain email Frappe would have sent anyway, which is the correct degradation:
this feature adds identity, it does not gate delivery on it.
"""

import frappe


def lockup() -> dict:
	"""The society's name and logo, or empty strings, for an email masthead.

	Never raises. This runs inside the render of every outgoing message on the
	site — including password resets and Frappe's own system mail — so a society
	that has not been configured, a `National Society Settings` that does not
	load, or core being mid-migration must all produce a plain email rather than
	a traceback in the email queue. A message that arrives unbranded is a
	cosmetic problem; a message that never arrives is not.
	"""
	try:
		from onerc_core.society.services.config import get_ui_config

		society = get_ui_config()["society"]
	except Exception:
		# Deliberately broad, and deliberately silent. See the docstring: the
		# alternative to swallowing this is an unsent email.
		frappe.log_error(title="vmmsx: could not read society branding for email")
		return _EMPTY

	return {
		"brand_name": society.get("name") or society.get("short_name") or "",
		# `logo` rather than `logo_dark`: an email body is white in every client
		# that matters, so this is the light-surface mark for the same reason the
		# landing page uses it and the navy sidebar does not.
		"brand_logo": society.get("logo") or "",
	}


_EMPTY = {"brand_name": "", "brand_logo": ""}
