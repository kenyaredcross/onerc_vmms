# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Announcement — what a branch or the national society tells its people.

An alert, an advisory, a piece of news. It arrives in the notification list of
everybody the audience resolves to, and optionally as an email as well, and the
two channels reach deliberately different sets of people (see `announce.py`).

**The controller holds no rules of its own.** Everything is in
`vmmsx/notifications/services/`: `audience.py` answers who, `announce.py`
answers how, `delivery.py` owns one person's copies. Two lines of `validate` and
one of `on_update` is the whole of this file, in the shape `VMMS Time Log`
already set.

**The fan-out is on `on_update`, not `before_submit`.** `docstatus` is not used
here, the same as everywhere else in this app: an announcement's lifecycle is
its `status`. Hanging the fan-out on a save rather than on a single lifecycle
moment is what makes it survive the realistic sequences — a draft published, an
already-published announcement corrected, a publish that died halfway and is
saved again. Each of those calls `publish()` and `publish()` is idempotent, so
the second call through delivers nothing twice and finishes anything the first
left unfinished.

**Publishing is one-way and the controller enforces it.** An announcement people
have already read cannot be unsent, so `status` may not go back to Draft: the
copies would survive with nothing owning them, and a reader who saw an advisory
would have no way to know it had been withdrawn. Correcting the wording is the
supported path and it corrects it for everybody at once, because the wording
lives here and was never copied onto the notifications.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from vmmsx import links
from vmmsx.notifications.services import announce


class VMMSAnnouncement(Document):
	def validate(self):
		self.link_href = links.assert_safe(self.link_href)
		self.refuse_unpublish()

	def on_update(self):
		"""Deliver, if this is published. Safe on every save; see the docstring."""
		if self.status == announce.STATUS_PUBLISHED:
			announce.publish(self)

	def refuse_unpublish(self):
		"""A published announcement stays published.

		Read from the database rather than from `self._doc_before_save`, which is
		absent on paths that do not load the previous version, so the check holds
		for a script and a bulk edit as much as for the form.
		"""
		if self.is_new():
			return

		was = frappe.db.get_value(self.doctype, self.name, "status")

		if was == announce.STATUS_PUBLISHED and self.status != announce.STATUS_PUBLISHED:
			frappe.throw(
				_(
					"This announcement has already been sent and cannot be unsent. People are"
					" holding copies of it. Edit the wording to correct it, which corrects it"
					" for everybody, or set an expiry date to take it out of their lists."
				),
				frappe.ValidationError,
				title=_("Already Sent"),
			)
