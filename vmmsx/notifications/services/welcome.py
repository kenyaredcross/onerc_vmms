# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Putting the society's welcome email on the site, and never on top of theirs.

Two writes, and the asymmetry between them is the whole of the design:

1. **The `Email Template` record** — created when the site has none by that
   name, and *never* edited afterwards. Same rule as
   `content/services/blocks.py::seed()`, for the same reason: this runs on every
   migrate, and a seed that refreshed itself would revert a society's rewritten
   welcome email every time somebody deployed.

2. **The pointer at it**, `System Settings.welcome_email_template` — set only
   when it is **empty**. A society that has already named a template of their
   own made that choice, and a migrate is not the moment to overrule it. Empty
   means unconfigured, a value means a decision, which is how every setting in
   this app behaves.

Wired into `after_migrate` rather than a patch, because a patch runs once per
site by name and could never seed a message improved in a later release onto a
site that had already run it.

**This changes an email the whole site sends**, not only vmmsx's own, because
Frappe has exactly one welcome email. That is the intent: on a site that exists
to be a national society's, the account-created message should be the society's
whoever created the account.
"""

import frappe

from vmmsx.notifications.seeds import welcome_email

TEMPLATE_DOCTYPE = "Email Template"
SETTINGS_DOCTYPE = "System Settings"
SETTING_FIELD = "welcome_email_template"


def install() -> dict:
	"""Seed the template and point the site at it. Idempotent, additive only."""
	return {"template": _ensure_template(), "setting": _point_at_template()}


def _ensure_template() -> str:
	"""Create the shipped welcome email if the site has none. Never edits one."""
	if frappe.db.exists(TEMPLATE_DOCTYPE, welcome_email.TEMPLATE_NAME):
		return "exists"

	frappe.get_doc(
		{
			"doctype": TEMPLATE_DOCTYPE,
			"__newname": welcome_email.TEMPLATE_NAME,
			"subject": welcome_email.SUBJECT,
			# `use_html` is what makes Frappe read `response_html` rather than the
			# Text Editor field. The body is hand-written HTML with Jinja in it, and
			# putting it through a rich-text field would let an editor's markup
			# normalisation rewrite the conditionals.
			"use_html": 1,
			"response_html": welcome_email.BODY,
		}
	).insert(ignore_permissions=True)  # An installer running as Administrator.

	return "created"


def _point_at_template() -> str:
	"""Name the template in System Settings, unless the site already names one."""
	current = frappe.db.get_single_value(SETTINGS_DOCTYPE, SETTING_FIELD)

	if current:
		return "exists" if current == welcome_email.TEMPLATE_NAME else f"left alone: {current}"

	if not frappe.db.exists(TEMPLATE_DOCTYPE, welcome_email.TEMPLATE_NAME):
		return "skipped: template missing"

	frappe.db.set_single_value(SETTINGS_DOCTYPE, SETTING_FIELD, welcome_email.TEMPLATE_NAME)
	frappe.clear_document_cache(SETTINGS_DOCTYPE, SETTINGS_DOCTYPE)

	return "set"
