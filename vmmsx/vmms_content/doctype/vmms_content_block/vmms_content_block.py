# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Content Block — one editable slot on one screen.

Every heading, paragraph, button label and photograph in the product is one of
these, addressed by an opaque `content_key`. A component in the frontend names
the key it wants; what comes back is whatever the society has since written
there. That is what makes the wording configuration rather than source, and it
is why no screen in this app carries a hardcoded sentence.

Two things are enforced here rather than left to the frontend, because both are
about what this app *serves* and neither is the browser's business:

- **the text is text.** `text_value` is rendered as a string by the frontend, so
  a heading cannot smuggle markup into a page served to the public. Nothing in
  this controller needs to sanitise it; the guarantee lives in it never being
  treated as HTML.
- **the link goes somewhere sane.** `link_href` is refused on save unless it is
  a path within this site or an ordinary http, https, mailto or tel address. A
  `javascript:` URI in an editable field is a stored cross-site scripting hole
  wearing a settings form, and the moment to refuse one is while its author is
  still looking at it.

The rule itself lives in `vmmsx/links.py`, not here. `VMMS Announcement` needs
the identical answer for the identical reason — an authorised person types a
destination, every reader clicks it — and a security rule kept in two places is
one rule and one that will go stale.
"""

from frappe.model.document import Document

from vmmsx import links


class VMMSContentBlock(Document):
	def validate(self):
		self.validate_link()

	def validate_link(self):
		"""Refuse a link that is neither site-relative nor a known-safe scheme."""
		self.link_href = links.assert_safe(self.link_href)
