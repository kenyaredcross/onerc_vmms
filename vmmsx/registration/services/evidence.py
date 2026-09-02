# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Files an applicant uploads about themselves, and what happens to them.

Domain-agnostic infrastructure, deliberately outside every module package, for
the same reason `vmmsx/links.py` sits outside them: two unrelated features need
the same answer, and two copies of a security rule are one rule and one stale
rule waiting to be found. The callers today are a society's own `Attach`
questions and a guardian's consent evidence; a membership proof is the next.

Two rules, and both of them exist because a browser is the one deciding where a
file goes.

**The URL is a claim, and it is checked.** An applicant uploads through the
framework's own file handler and posts back the URL it returned. Anything that
is not one of this site's own upload paths is refused, because a field that
accepted an arbitrary URL would point the approver's browser — and any screen
rendering the application — at somebody else's server. Same rule `links.py`
applies to a content block's href.

**Private is decided here, not hoped for.** A file uploaded to `/files/` is
served to anyone who has the URL, with no permission check anywhere: the
framework does not consult `attached_to_doctype` for a public file. An
applicant's birth certificate sitting behind a guessable path forever is the
failure this module closes. So a file is *made* private rather than required to
have been uploaded privately — refusing a public URL instead would leave the
public copy on disk and cost the applicant their answer as well.

**And it is decided on the server because the desk's answer does not reach the
portal.** A desk `Attach` field already uploads privately by default: the
framework's switch is `make_attachment_public`, and neither this app's doctypes
nor its fields set it. That covers a clerk at a branch and nobody else. The
portal uploads through the file API, where the browser names its own privacy,
so a rule that lived only in a DocField property would protect exactly the half
of the traffic that was never at risk.

**Through `File.save()`, never `db.set_value`.** Flipping `is_private` in the
database changes a flag and leaves the bytes in the public directory, still
served: only the document's own `on_update` moves the file and rewrites its URL.
Saving also writes a `Version`, and where a private document went is exactly
what an audit trail is for. Because the URL changes when the file moves, every
caller has to store what `secure()` returns rather than what it was given.
"""

import frappe
from frappe import _
from frappe.utils import cstr

FILE_DOCTYPE = "File"

# Where this site's own uploads land. Both are accepted and privacy is settled
# afterwards — see the module docstring.
UPLOAD_PREFIXES = ("/files/", "/private/files/")


def is_upload(url: str | None) -> bool:
	"""Does this look like a file uploaded to this site?"""
	return cstr(url).strip().startswith(UPLOAD_PREFIXES)


def assert_uploaded(url: str | None, label: str) -> str:
	"""Return the trimmed URL, or throw with a message naming the field.

	`label` is what the person filling in the form calls this thing, so the
	refusal reads as a sentence about their form rather than about a URL.
	"""
	value = cstr(url).strip()

	if not value or is_upload(value):
		return value

	frappe.throw(
		_("The file you gave for {0} was not uploaded to this site.").format(frappe.bold(label)),
		frappe.ValidationError,
		title=_("File Not Recognised"),
	)


def secure(doc, url: str | None) -> str:
	"""Anchor one uploaded file to `doc` and make it private. Returns its URL.

	The URL comes back because making a file private moves it, and a caller
	still holding the old one would have a link to a stale public copy.

	**Anchoring is what makes the file readable by the right people**, and it is
	half of the job rather than an afterthought. A private `File` with no
	`attached_to_doctype` belongs to whoever uploaded it and to System Manager
	and to nobody else, so an approver opening the application would see a
	filename and get a permission error clicking it. Attached to the document,
	the file inherits that document's own permissions — which are already the
	right answer: exactly the people who may read the application may read what
	was uploaded to it.

	Idempotent, and quiet in the ordinary case: a file already anchored here and
	already private is left completely alone, which is what every re-save of a
	draft hits.

	**A file anchored to some other document is never moved.** That is either an
	applicant reusing a URL they should not have, or a genuine second reference,
	and neither is something this function may resolve by stealing the file from
	whatever owns it. The URL is returned unchanged and the caller stores what it
	was given.

	Elevated, because the person this runs for is the applicant: they hold no
	permission on `File` beyond their own upload and none at all on the register
	they have just applied to join. The write is bounded to a file they own and
	have already uploaded, and it only ever *narrows* who can reach it — it hands
	an unattached file to the document's own permission rules, and takes a public
	file off the open web.
	"""
	value = cstr(url).strip()

	if not value:
		return ""

	found = frappe.db.get_value(
		FILE_DOCTYPE,
		{"file_url": value},
		["name", "attached_to_doctype", "attached_to_name", "is_private"],
		as_dict=True,
	)

	if not found:
		return value

	if found.attached_to_name and (
		found.attached_to_doctype != doc.doctype or found.attached_to_name != doc.name
	):
		return value

	if found.attached_to_name and found.is_private:
		return value

	document = frappe.get_doc(FILE_DOCTYPE, found.name)
	document.attached_to_doctype = doc.doctype
	document.attached_to_name = doc.name
	document.is_private = 1
	document.save(ignore_permissions=True)

	return document.file_url or value
