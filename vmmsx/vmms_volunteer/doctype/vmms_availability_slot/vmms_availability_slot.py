# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Availability Slot — a society's own vocabulary of when a volunteer can serve.

Days, hours and shift patterns are society variable, so this is a doctype rather
than a `Select` a form built once and never revisited — a national society may
add a slot (school holidays, night shifts) or rename one without a code change.
It follows the exact shape of `VMMS Skill` and `VMMS Motivation` on purpose:
this module already has a proven pattern for "a society-editable multi-select
vocabulary", and giving availability its own bespoke shape would be a second
answer to a question this app has already answered twice.

An open set, extended freely, and **no code anywhere branches on a slot value**.
Seeded with a starting set by
`vmmsx.patches.setup_volunteer_application_module`; owned by the society from
the moment it lands.

**The hours are what let a slot answer a question rather than only label one.**
A volunteer picking "Weekends" off the register is describing themselves, and
`capabilities.search` filters on that. Giving the slot an opening and a closing
time lets `VMMS Availability Schedule` say "Saturday, Afternoons" and lets
`volunteer/services/availability.py` turn that into a yes or a no about a real
span of dates. They are optional: a society that has not filled them in keeps
every behaviour it had before, and simply cannot be asked the dated question.

The one rule below is about a slot being coherent with itself, never about any
particular society's hours.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_time


class VMMSAvailabilitySlot(Document):
	def validate(self):
		self.validate_hours()

	def validate_hours(self):
		"""A window cannot close before it opens.

		**An overnight window is two slots, not one row spanning midnight.** A
		society with a night shift writes "Night (evening)" ending at midnight and
		"Night (early)" starting at it, because a single row from 22:00 to 06:00
		would have to belong to two days at once — and a schedule row saying
		"Tuesday, Night" could then mean Tuesday evening, Wednesday morning, or
		both, with nothing on the record to say which. Refusing it here is what
		keeps `availability.py` able to answer without guessing.

		Only checked when the society has given both times. One on its own is
		half-configured rather than wrong, and the reader treats a slot without
		both as having no hours at all.
		"""
		if not (self.start_time and self.end_time):
			return

		if get_time(self.end_time) > get_time(self.start_time):
			return

		frappe.throw(
			_(
				"{0} is set to close at {1}, which is not after it opens at {2}. A window that runs"
				" past midnight is two slots — one ending at midnight and one starting at it —"
				" because a single row spanning it would belong to two days at once and nothing"
				" on the record could say which day a volunteer meant."
			).format(
				frappe.bold(self.slot_name or self.name),
				frappe.bold(frappe.format(self.end_time, {"fieldtype": "Time"})),
				frappe.bold(frappe.format(self.start_time, {"fieldtype": "Time"})),
			),
			frappe.ValidationError,
			title=_("Window Closes Before It Opens"),
		)
