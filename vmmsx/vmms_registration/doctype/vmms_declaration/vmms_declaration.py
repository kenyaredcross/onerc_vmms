# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Declaration — something a society asks an applicant to agree to.

Four ship with the app — privacy and data processing, permission to contact,
use of personal and biographical data, and a declaration that what was submitted
is accurate — and a society may reword all four or add a fifth without anybody
writing code. That is the same bargain `VMMS Application Question` strikes, and
this doctype is deliberately its sibling: configuration here, a record on the
application, and the record snapshots what it was agreeing to.

**`applies_to` is a Link to DocType, not a Select of the two we ship.** Same
shape as `VMMS Application Question.asked_on` and `VMMS Approval Workflow.
workflow_for`, and for the same reason: this module names no registration.

**The wording lives in `VMMS Declaration Version`, and this row mirrors it.**
`version`, `body`, `source` and `external_url` are read-only here and re-derived
on every save as well as whenever a version is published or withdrawn — because
`read_only` is a form-level hint and the server stores whatever a script or an
API call puts in such a field. Derived means derived: a hand-edited body does not
survive the save that carried it, the same way `VMMS Volunteer Application.
is_minor` does not. They are kept on the row rather
than joined at read time so that a desk user opening a declaration sees what is
currently published, and so that every reader written before versions existed
went on working unchanged — the same "authored there, derived here" arrangement
this app uses for a deployment's dates.

This replaced an earlier rule that refused a changed `body` still wearing the old
version label. That rule was the best a single editable row could do, and it was
not enough: it stopped a *careless* rewording and could not stop a deliberate
one, and either way the wording it replaced was gone. Publishing is now an act
the framework itself freezes, and every wording a society has ever published
remains readable. See `VMMS Declaration Version`.

**A version may point at a page instead of holding words.** A society that
publishes its privacy notice on its own website says so on the version, and the
registration form links to it rather than reprinting it. What an acceptance can
then record is the address and the version label rather than the text, which is a
weaker record honestly kept — see the version doctype for why that is stated
rather than smoothed over.

**Deactivating is not deleting.** `is_active` stops the declaration being shown
to new applicants and leaves every acceptance already recorded in place. An
acceptance is part of an application somebody decided, and deleting it would
take the consent out from under a decision that has already been made.

**Readable by `All`, and that is deliberate.** This is the text a society asks
the public to agree to before it will consider them, so it is the least
sensitive record in the app and somebody deciding whether to register is
entitled to read it first. Writing is System Manager's. Contrast
`VMMS Declaration Acceptance`, which says who agreed to what and rides on the
application's own permissions.
"""

from frappe.model.document import Document


class VMMSDeclaration(Document):
	def validate(self):
		self.title = (self.title or "").strip()
		self._mirror_published_version()

	def _mirror_published_version(self) -> None:
		"""Re-read the published wording onto this row, discarding anything typed.

		Nothing happens on a declaration whose first version has not been
		published yet — that is the moment `declarations.install` and an
		administrator's own first save both pass through, and there is nothing to
		mirror from. From the first publication onwards these four fields are the
		version's answer and nobody else's.
		"""
		from vmmsx.registration.services import declarations

		values = declarations.published_values(self.name)

		if not values:
			self.version = (self.version or "").strip()

			return

		self.update(values)
