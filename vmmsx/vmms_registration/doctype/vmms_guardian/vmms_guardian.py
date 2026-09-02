# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Guardian — the adult a young volunteer's post is copied to.

`VMMS Guardian Consent` is a row on an application: it is how a society decides
whether it may accept a minor at all, and once that decision is made it is part
of the record of the decision and must not move. This is a different record with
a different life. It is about the **person**, it survives the application being
decided, it can be corrected when a phone number changes without anybody editing
a decided document, and it is what the notification services read when they ask
who else should hear about something.

**Why it could not stay on the application.** Everything a young volunteer is
told after they are accepted — a deployment invitation, a task, a change to
arrangements, a membership decision — happens long after the application is
closed. Reading a guardian off a decided application at that point would mean
either treating that record as live configuration, or editing it, and both are
things this app deliberately does not do to a record of a decision. The guardian
is copied forward at acceptance and lives here afterwards. See
`registration/services/guardian.py::adopt`.

**Anchored on the Red Profile, not on the volunteer.** A minor may be a
volunteer, a member, or both, and a parent is the parent in all of them. Core's
Red Profile is the one answer to who a person is, so it is what a guardian hangs
off — the same anchor `VMMS Volunteer` and `VMMS Member` use, and for the same
reason.

**vmmsx-owned, and that follows the emergency contact.** Core holds
`next_of_kin` off the Red Profile spine for a later gated extension, and
`volunteer/services/identity.py::_WITHHELD` refuses it by name. A guardian is
adjacent to that, and the same question was already settled for the emergency
contact: this is a fact recorded for the purposes of *this* volunteering, held by
this app, and core's spine is not written to. If core's extension lands, this
record is still the one that answers "who do we copy", which is a different
question from "who is this person's next of kin".

**Two ticks, and the second is not the first repeated.** `consent_given` is what
the guardian said; `is_verified` is what somebody at the society did about it.
Identical in meaning to the application row it is copied from, kept identical on
purpose, and stamped the same way — `verified_by` and `verified_on` are the
answer to "who says so", so they are written here rather than typed.

**Being copied is not the same as having consented.** `is_active` and `email`
decide whether anything is sent; the consent fields record a decision that was
made once. A guardian who withdrew consent for the *volunteering* has not thereby
stopped being the person a society must copy while the young person is still
under age — that is what `is_active` is for, and it is a separate act.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class VMMSGuardian(Document):
	def validate(self):
		self.guardian_name = (self.guardian_name or "").strip()
		self.relationship = (self.relationship or "").strip()
		self.email = (self.email or "").strip()
		self.phone = (self.phone or "").strip()
		self._stamp_verification()

	def _stamp_verification(self) -> None:
		"""Record who verified this consent, the moment they say they have.

		The same rule as `VMMS Guardian Consent.stamp_verification`, called from
		`validate` here because this is a document in its own right rather than a
		child row Frappe never runs `validate` on. Idempotent: an already-stamped
		row keeps its original attribution, because the person who checked the
		consent is not the person who happened to save the record next.
		"""
		if not self.is_verified:
			# Withdrawn verification takes its attribution with it, so the record
			# never says somebody vouched for a consent no longer marked verified.
			self.verified_by = None
			self.verified_on = None

			return

		if self.verified_by:
			return

		self.verified_by = frappe.session.user
		self.verified_on = now_datetime()
