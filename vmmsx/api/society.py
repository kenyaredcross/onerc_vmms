# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Who this society is, for the mark in the corner of every screen.

The portal's lockup is the society's own logo and its own name, and both live on
core's `National Society Settings`. They were previously two content blocks —
words an administrator typed into the page a second time — which meant a society
that had uploaded its logo and named itself in settings still saw the product's
placeholder mark until somebody retyped it. Identity has one home, the same rule
`VMMS Volunteer` follows about Red Profile.

**This is the app's second `allow_guest` endpoint, and the first was
`content.surface`.** That is worth stating rather than slipping in, because
"only one endpoint in this app serves a signed-out visitor" was a property worth
having. The justification here is the same shape as the content one and rests on
*what* is returned rather than on who is asking:

* the three fields below are a society's public identity — the name it trades
  under, the short form of it, and the logo it puts on its own website. There is
  no version of them that is private, and the landing page they are drawn on is
  already public;
* the whole of `get_ui_config()` is **not** returned, and must not be. That call
  is authenticated on purpose — it carries feature toggles, validation policy and
  theme tokens, which describe how a product behaves internally. This builds its
  answer field by field from the three that are branding, so widening it is a
  visible edit to this function rather than something that follows from a change
  in core.

**Read through core's service, never off the doctype.** `get_ui_config()` is the
supported reader and its *fallbacks* are the contract — `logo_dark` falling back
to `logo` is the one that matters here, because the sidebar is navy and the
landing page is white and a society that uploaded one mark should not have a
hole on one of them.
"""

import frappe


@frappe.whitelist(allow_guest=True)
def branding() -> dict:
	"""The society's name and marks. Three fields, and nothing else.

	Every value may be empty, and empty is ordinary: a fresh site has never had
	the settings form opened, and core's `settings()` loads a Single that was
	never saved with every field blank. The frontend draws its own placeholder
	mark in that case rather than a broken image, so nothing here invents a
	fallback that would put one society's name on another's screen.
	"""
	from onerc_core.society.services.config import get_ui_config

	society = get_ui_config()["society"]

	return {
		"name": society.get("name") or "",
		"short_name": society.get("short_name") or "",
		"logo": society.get("logo") or "",
		# Already falls back to `logo` in core. Named separately here because the
		# sidebar is dark and the landing page is not, and the caller is the only
		# one that knows which surface it is drawing on.
		"logo_dark": society.get("logo_dark") or "",
	}
