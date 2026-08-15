# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Turning a stored file reference into one a PDF renderer can actually follow.

**The trap this exists for.** An Attach Image stores a site-relative path,
`/files/logo.png`. That is correct for a browser, which resolves it against the
page it came from. A PDF renderer has no page: wkhtmltopdf is handed a string
of HTML and has nothing to resolve a leading slash against, so the logo
silently does not appear — no error, no warning, just a document with a gap
where the society's mark should be.

**A data URI rather than an absolute URL, deliberately.** Frappe's `get_pdf`
already runs `scrub_urls`, which would expand `/files/logo.png` into
`http://<site>/files/logo.png`, so an absolute URL is what you get for free if
you do nothing. It is also the fragile answer: it makes rendering depend on the
renderer reaching this site over HTTP — the right host, the right port, the
file public rather than private, and a web server actually up. `get_pdf`
additionally passes `disable-local-file-access`. A data URI needs none of that:
the bytes are in the document, so it renders identically on a laptop, in a
container with no ingress, and on a site behind authentication.

This was `member/services/certificate.py::printable_asset`, and it moved here
when the cards needed it too. It was never about memberships: it takes a URL
string and gives back a URL string. `certificate.py` still exposes the name, so
nothing that referred to it there had to change.
"""

import mimetypes
from base64 import b64encode

import frappe
from frappe.utils import get_url

ASSET_LOG_TITLE = "Printable asset could not be embedded"


def printable_asset(url: str) -> str:
	"""An asset reference that carries its own location, for the PDF renderer.

	`get_url()` is the fallback for the case the bytes cannot be read — a File
	row that has gone missing, or a value that was never a local file at all.
	Better a link that might resolve than a path that certainly will not.

	Anything already absolute, and any data URI, is returned untouched.
	"""
	if not url:
		return ""

	if url.startswith(("data:", "http://", "https://")):
		return url

	content, mimetype = asset_bytes(url)

	if content:
		return f"data:{mimetype};base64,{b64encode(content).decode()}"

	return get_url(url)


def asset_bytes(url: str) -> tuple[bytes | None, str]:
	"""The bytes behind a stored file URL, and what kind they are.

	Read through Frappe's own File lookup rather than by joining a path onto the
	site directory: a private file lives somewhere else entirely, and building
	that path here would be this app guessing at the framework's storage layout.

	Never raises. A logo that cannot be read is a cosmetic problem, and a
	document somebody is entitled to must not fail to print because of one.
	"""
	from frappe.core.doctype.file.utils import find_file_by_url

	try:
		found = find_file_by_url(url)
		content = found.get_content() if found else None
	except Exception:
		frappe.log_error(title=ASSET_LOG_TITLE, message=frappe.get_traceback())

		return None, ""

	if not content:
		return None, ""

	mimetype, _encoding = mimetypes.guess_type(url)

	return content, mimetype or "application/octet-stream"
