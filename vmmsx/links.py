# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Where this app is willing to send somebody, decided in one place.

Domain-agnostic infrastructure, deliberately outside every module package, for
the same reason `vmmsx/templating/` sits outside `member/`: two unrelated
features need the same answer, and two copies of a security rule are one rule
and one stale rule waiting to be found.

The two callers today are `VMMS Content Block`, where an administrator writes
the destination of a button on the public landing page, and `VMMS Announcement`,
where somebody writes the destination of a broadcast that reaches everybody the
branch serves. Both are fields an authorised person types a URL into and every
reader then clicks, which is exactly the shape of a stored cross-site scripting
hole, and the moment to refuse one is while its author is still looking at it.

**Refused by default rather than by name.** `javascript:`, `data:` and
`vbscript:` are the schemes this exists to exclude, but naming them would mean
the next scheme nobody thought of is allowed. Anything outside the allow-list is
refused instead, so the failure mode of an unfamiliar scheme is a refusal rather
than a hole.
"""

from urllib.parse import urlparse

import frappe
from frappe import _

# Schemes a visitor may be sent to.
ALLOWED_SCHEMES = frozenset({"http", "https", "mailto", "tel"})


def is_safe(href: str) -> bool:
	"""Is this somewhere this app may send a reader?

	Site-relative paths pass, and are checked before parsing because
	`/portal/join` has no scheme and is the ordinary case. `//evil.example` is
	not site-relative — it is a protocol-relative address to another host — and
	is deliberately excluded by the second test.
	"""
	href = (href or "").strip()

	if not href:
		return True

	if href.startswith("/") and not href.startswith("//"):
		return True

	# Anchors and query-only links stay on the page the reader is already on.
	if href.startswith("#") or href.startswith("?"):
		return True

	return urlparse(href).scheme.lower() in ALLOWED_SCHEMES


def assert_safe(href: str, title: str | None = None) -> str:
	"""Return the trimmed link, or throw with a message its author can act on.

	The message says what *is* accepted rather than what was wrong, because
	somebody who has just pasted a tracking URL with a scheme they did not look
	at needs to know the shape of a working answer.
	"""
	href = (href or "").strip()

	if is_safe(href):
		return href

	frappe.throw(
		_(
			"{0} is not a link this app may send a reader to. Use a path beginning with /,"
			" or an address beginning with http://, https://, mailto: or tel:."
		).format(href),
		frappe.ValidationError,
		title=title or _("Unsafe Link"),
	)
