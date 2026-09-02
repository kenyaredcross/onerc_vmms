# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One WhatsApp broadcast, and the approval that releases it.

**Submitting is approving.** There is no workflow and no second engine: a draft
is docstatus 0, submitting needs submit permission on this doctype, and
`on_submit` is the only route to a message leaving the building. onerc_sms
arrived at the same shape after its own native workflow turned out to hold
approved campaigns at a docstatus that could never be submitted; this starts
where that ended up.

**The recipient list is frozen when the broadcast is filed.** It is written by
`whatsapp.draft()` and read-only on the form, because the number of people a
broadcast reaches is the thing being approved and a list that re-resolved itself
at send time would make the approval meaningless. Opt-outs are subtracted again
during the send, which can only shrink it.

**Nothing is sent from here.** `on_submit` queues; the sending is
`whatsapp.send`, on a worker, and it can take hours. A controller that sent
inline would be a request that times out halfway through a branch.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

from vmmsx.notifications.services import whatsapp


class VMMSWhatsAppBroadcast(Document):
	def validate(self):
		self.validate_message()
		self.validate_recipients()

	def validate_message(self):
		if not (self.message or "").strip():
			frappe.throw(_("A WhatsApp broadcast needs something to say."))

	def validate_recipients(self):
		"""Refuse a broadcast with nobody in it, while it is still a draft.

		Caught on the form rather than at send time, the argument
		`SMSCampaign.validate_filters` makes for its own early check: an empty
		list is a mistake somebody can fix in a second now, and a submitted
		broadcast that reaches nobody is a thing they have to go and explain
		later.
		"""
		if not self.recipients:
			frappe.throw(_("This broadcast has nobody to go to."))

		self.total_recipients = len(self.recipients)

	def on_submit(self):
		"""Approved. Queue it, or hold it until the time it was filed for.

		The comparison is against `now_datetime()` and not against the filing
		time, so a broadcast approved on Friday for a Wednesday that has already
		passed goes out on approval instead of waiting a week for a moment that
		will not come again.
		"""
		if self.scheduled_at and get_datetime(self.scheduled_at) > now_datetime():
			self.db_set("status", whatsapp.STATUS_SCHEDULED, update_modified=False)

			return

		whatsapp.release(self.name)

	def on_cancel(self):
		"""Stop what has not gone yet. What has gone has gone.

		A cancelled broadcast keeps every row it already sent, marked as sent,
		because a record of who was written to is exactly what somebody
		cancelling in a hurry will need afterwards. The worker checks the
		docstatus before each pass and stops on its own.

		Cancelled rather than Failed. Nothing went wrong here — somebody changed
		their mind — and a register where the two look the same is one nobody can
		use to answer why a branch never heard anything.
		"""
		self.db_set("status", whatsapp.STATUS_CANCELLED, update_modified=False)
