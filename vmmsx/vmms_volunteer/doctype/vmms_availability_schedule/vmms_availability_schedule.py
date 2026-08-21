# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Availability Schedule — when a volunteer can actually serve.

**Why this exists next to the availability a volunteer already declares.** The
register has carried `VMMS Volunteer.availability` since the beginning: a
Table MultiSelect of the society's own named slots, so somebody can say
"Weekends" or "On-call". That is a *label*, and `capabilities.search` filters on
it, which is the right shape for the question "who describes themselves as a
weekend volunteer". It cannot answer the question a deployment asks, which is
"this runs from the 3rd to the 10th of September — is this person free then".

This is that answer: a weekly pattern of day-and-window rows, plus the period
over which the pattern holds. `volunteer/services/availability.py` reads it and
turns it into a yes or a no about a real span of dates.

**A pattern, not a calendar.** A schedule expanded into one dated row per day
would be tens of thousands of rows per volunteer per year, all of them stale the
moment somebody's Tuesdays change. The pattern is small, a person can fill it in
once, and the expansion happens in the reader where it costs nothing.

**One per volunteer.** `volunteer` is the docname and it is unique. A society
keeping several schedules per person would have to decide which one a deployment
asks, and every answer to that is a rule somebody has to remember.

**What it deliberately does not do.** It holds no dated exceptions — "away the
first week of March" — and no public-holiday calendar. `available_on_holidays`
is carried and shown to a coordinator rather than matched on, because reading a
holiday calendar means knowing which country's, and that is a question this app
has not been asked yet. Saying so here is better than a filter that silently
means something different in two societies.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class VMMSAvailabilitySchedule(Document):
	def validate(self):
		self.validate_period()
		self.validate_pattern()

	def validate_period(self):
		"""A pattern cannot stop holding before it starts.

		Both dates are optional — most people mean "from now on, indefinitely" —
		so this only has an opinion when the volunteer has given both.
		"""
		if not (self.valid_from and self.valid_to):
			return

		if getdate(self.valid_to) >= getdate(self.valid_from):
			return

		frappe.throw(
			_("This schedule is set to stop on {0}, before it starts on {1}.").format(
				frappe.bold(frappe.format(self.valid_to, {"fieldtype": "Date"})),
				frappe.bold(frappe.format(self.valid_from, {"fieldtype": "Date"})),
			),
			frappe.ValidationError,
			title=_("Schedule Ends Before It Begins"),
		)

	def validate_pattern(self):
		"""One row per day-and-window pair. Two would be two answers to one question.

		Checked on the parent because Frappe does not call a child controller's
		`validate`. A duplicate is harmless to the reader — being free twice is
		being free — but it makes the grid lie about how much somebody offered,
		and a volunteer looking at their own availability should see what they set.
		"""
		seen = set()

		for row in self.available_days or []:
			pair = (row.day, row.availability_slot)

			if pair in seen:
				frappe.throw(
					_("{0} {1} is listed twice. List each window once per day.").format(
						frappe.bold(_(row.day)), frappe.bold(row.availability_slot)
					),
					frappe.DuplicateEntryError,
					title=_("Listed Twice"),
				)

			seen.add(pair)
