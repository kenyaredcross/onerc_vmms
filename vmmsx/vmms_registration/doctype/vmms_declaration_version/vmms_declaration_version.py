# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Declaration Version — one wording of a policy, frozen once published.

`VMMS Declaration` is the standing thing: "our privacy notice", "our terms of
use". It has one row per purpose, a stable key, and it is what an acceptance
points at so that rewording never orphans what people have already agreed to.
This is the other half — **what that policy actually said, on a given day** —
and it exists because the previous arrangement could not answer that question.

**Before this, a rewording destroyed the wording it replaced.** The declaration
carried one `body` and one `version`, and editing them in place was the only way
to publish new wording. History survived only where somebody had already
accepted the old text, because the acceptance snapshotted it. A society that
corrected its privacy notice before anyone applied lost the original entirely,
and had no way to show a regulator what it had published in the meantime.

**Submittable, because that is exactly the guarantee wanted.** A draft version is
somebody's working copy and may be edited freely. Submitting it publishes it: the
framework itself refuses every further edit, so "what we published" stops being a
claim about who had access to the form. Superseding it is publishing the next
version, not editing this one, and both remain readable forever.

**A version is text, or it is a link, and never both.** Some societies hold their
privacy notice in this system; others publish it on their own website and want
the registration form to point at it — a national society whose legal team owns
the web page is not going to maintain a second copy here. `source` says which,
and the two fields are mutually exclusive rather than one field doing double
duty, so nothing has to guess whether an address in a text box was meant as a
link.

**What a `Link` version can promise is narrower, and it is recorded honestly.**
An acceptance against a `Text` version stores the words. An acceptance against a
`Link` version can only store the address and the version label, because the page
is not ours and may change without anybody here knowing. That is a real
difference in evidential weight and the register says so rather than implying the
two are equivalent: `VMMS Declaration Acceptance` keeps `source` alongside the
snapshot. Moving the page's contents is therefore a new version, and it is the
society's own discipline that makes it one.

**The parent's `body` and `version` are mirrors, not the record.** They are
read-only on the form and re-derived here on every submit and cancel, so a desk
user reading `VMMS Declaration` sees what is currently published without a join
and no reader in the app had to change. `declarations.current_version` is the one
place that decides which version is current, and it is the most recently
published one that has not been cancelled.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class VMMSDeclarationVersion(Document):
	def validate(self):
		self.version = (self.version or "").strip()
		self.external_url = (self.external_url or "").strip()
		self._assert_body_matches_source()
		self._assert_version_is_new()

	def on_submit(self):
		"""Publish. Stamp the moment, and re-derive the parent's mirror."""
		from vmmsx.registration.services import declarations

		self.db_set("published_on", now_datetime(), update_modified=False)
		declarations.sync_mirror(self.declaration)

	def on_cancel(self):
		"""Withdraw. The parent falls back to whatever is now the newest published.

		Cancelling is how a version published in error is taken out of use, and
		the mirror has to follow it — otherwise the declaration would go on
		showing wording the society has withdrawn, which is the failure this
		doctype exists to prevent, in the other direction.
		"""
		from vmmsx.registration.services import declarations

		declarations.sync_mirror(self.declaration)

	def _assert_body_matches_source(self) -> None:
		"""Whichever it is, it has to be there.

		Not `reqd` on either field, because `reqd` is unconditional and exactly
		one of these is wanted at a time. `depends_on` hides the other one on the
		form, but a hidden field is a browser's opinion and this is the rule.
		"""
		if self.source == "Link":
			if not self.external_url:
				frappe.throw(
					_("Give the address of the page this version points at, or hold the wording here instead."),
					frappe.MandatoryError,
					title=_("Page Address Needed"),
				)

			# The words are on the society's own site. Keeping a half-written
			# body alongside would leave two answers to what this version says.
			self.body = None

			return

		if not (self.body or "").strip():
			frappe.throw(
				_("Write the wording this version publishes, or point it at a page on your own website instead."),
				frappe.MandatoryError,
				title=_("Wording Needed"),
			)

		self.external_url = None

	def _assert_version_is_new(self) -> None:
		"""One version label per declaration, counting only what still stands.

		A cancelled version keeps its label out of the way — it was published and
		withdrawn, and reusing the label would make an acceptance stamped with it
		ambiguous. The docname is `{declaration}-{version}` so the framework
		would refuse an exact repeat anyway; this is here to say why, in words an
		administrator can act on, rather than as a duplicate-name error.

		**The "not me" clause is only applied to a record that already exists**,
		and leaving it on for a new one was a real bug rather than a nicety. The
		docname is built from exactly the two fields being checked, so a second
		version wearing the same label is autonamed to the *same* name as the
		first — and excluding `self.name` therefore excluded the very row it was
		looking for. The friendly message never fired and the framework's
		primary-key error surfaced instead.
		"""
		if not (self.declaration and self.version):
			return

		filters = {
			"declaration": self.declaration,
			"version": self.version,
			"docstatus": ["<", 2],
		}

		if not self.is_new():
			filters["name"] = ["!=", self.name]

		clash = frappe.db.exists(self.doctype, filters)

		if not clash:
			return

		frappe.throw(
			_("Version {0} of this declaration already exists. Give this one a version label of its own.").format(
				frappe.bold(self.version)
			),
			frappe.DuplicateEntryError,
			title=_("Version Already Published"),
		)
