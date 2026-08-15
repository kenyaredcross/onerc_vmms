# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Event Attendance — one person saying they are going to one event.

**It is an intention, and it is deliberately not a booking.** The events app
owns registration, ticket types, coupons, payment and check in, and this app is
forbidden from reading any of it (`vmmsx/buzz/tests/test_delegation.py` fails
the build if a single file names one of those doctypes). So this record makes
no claim that a place has been held or a seat paid for. It says one thing: this
person told the society they intend to be there, and that is a fact the society
is entitled to keep because it is the one their own coordinators plan around.

Before this, the answer lived in `localStorage` on whichever browser gave it,
which meant a volunteer who said yes on a laptop arrived at a phone that had
never heard of it, and no coordinator could see any of it at all.

The one rule it carries is that a person holds **one** row per event. That is
what the service's idempotence rests on, and it is enforced here as well as
checked in `attendance.attend()` because the two protect against different
things: the service stops the ordinary double click cheaply, and this stops a
second row arriving by any other route, a desk insert and a data import
included.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class VMMSEventAttendance(Document):
	def validate(self):
		self.refuse_duplicate()

	def refuse_duplicate(self):
		"""One row per person per event, whatever its status.

		Including a cancelled one, deliberately. Somebody who withdraws and then
		says yes again is the same standing answer changing twice, not two
		answers, and a second row would make "is this person coming" a question
		with two records to reconcile.
		"""
		existing = frappe.db.exists(
			self.doctype,
			{
				"red_profile": self.red_profile,
				"event": self.event,
				"name": ["!=", self.name or ""],
			},
		)

		if existing:
			frappe.throw(
				_("This person has already answered for that event."),
				frappe.DuplicateEntryError,
			)
