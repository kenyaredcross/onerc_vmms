# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Deployment — an actual deployment, and the roster that makes logs possible.

The controller enforces four things and delegates the rest.

**The anchor guardrails**, in `validate()`, which is the only place that runs
before a deployment can exist at all. ACC-02 first: a deployment with no Geo
Node is refused at creation rather than corrected later, because an unplaced
record is invisible to geo scoping and cannot be reported on by the branch whose
work it was. Then ACC-03, the society's own anchor level, read from settings on
every save so no level name appears in this file. Then the terms of reference's
own geo scope, which is the same shape of rule written by whoever wrote the
terms.

**The period is coherent** — an end before a start is a typo, and it is the kind
that quietly breaks every report that windows on dates.

**The roster is a set.** One row per volunteer. Two rows for the same person
would make "is this volunteer a participant" a question with two answers, and
the ownership rule that reads it would have to invent a tie-break.

**The status moves through a table, not by assignment.** The set is closed and
code owned, exactly as approval states are; `deployment.assert_transition`
refuses a move the table does not contain, so the lifecycle is a grammar rather
than a diagram somebody drew once.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from vmmsx.deployment.services import deployment as deployment_service
from vmmsx.deployment.services import society, terms

GEO_NODE_FIELD = "geo_node"


class VMMSDeployment(Document):
	def validate(self):
		self.validate_anchor()
		self.validate_period()
		self.validate_roster()
		self.validate_status()

	def validate_anchor(self):
		"""ACC-02, ACC-03, and the terms of reference's own scope.

		The mandatory flag on the field already refuses an empty anchor at the
		framework level; this repeats the refusal in the app's own words, so the
		rule is enforced by something that states it rather than only by a JSON
		attribute somebody could clear.
		"""
		if not self.get(GEO_NODE_FIELD):
			frappe.throw(
				_(
					"A deployment must be anchored to a Geo Node before it can exist. There are no"
					" unplaced records: an unplaced deployment cannot be seen by geo scoping and"
					" cannot be reported on by the branch whose work it was."
				),
				frappe.MandatoryError,
				title=_("Missing Geo Anchor"),
			)

		# Which level is permitted is society configuration, read from settings on
		# every save. No level name appears in this file.
		society.assert_deployment_anchor_level(self.get(GEO_NODE_FIELD))

		# And where these particular terms may be used is the terms' own answer.
		terms.assert_within_scope(self.terms_of_reference, self.get(GEO_NODE_FIELD))

	def validate_period(self):
		if not (self.start_date and self.end_date):
			frappe.throw(
				_("A deployment runs between two dates. Both are needed."),
				frappe.MandatoryError,
				title=_("Missing Period"),
			)

		if getdate(self.end_date) >= getdate(self.start_date):
			return

		frappe.throw(
			_("This deployment ends on {0}, before it starts on {1}.").format(
				frappe.bold(frappe.format(self.end_date, {"fieldtype": "Date"})),
				frappe.bold(frappe.format(self.start_date, {"fieldtype": "Date"})),
			),
			frappe.ValidationError,
			title=_("End Before Start"),
		)

	def validate_roster(self):
		"""Nothing to validate here any more, and the reason is worth leaving behind.

		This used to refuse a volunteer listed twice on `participants`, because two
		rows would give the ownership rule two answers. The roster is now a
		register of `VMMS Deployment Assignment` documents, and the same rule lives
		where it can be enforced against the database rather than against one
		unsaved list: `assignment.create` refuses a second *open* assignment for
		the same person, while deliberately allowing a settled one to be followed
		by a new one — asking again after a decline is a real thing a coordinator
		does, and it should produce a second record rather than overwrite what was
		said the first time.

		The child table is still on the doctype, hidden and read-only, until
		`vmmsx.patches.migrate_participants_to_assignments` has run everywhere.
		Nothing writes it.
		"""
		return

	def validate_status(self):
		"""The status is a closed set, and it moves through the transition table.

		On insert there is nothing to move from, so only the value is checked. On
		a later save the value before this one is read from the database rather
		than from the document, because the document is already carrying the new
		value by the time validation runs.
		"""
		deployment_service.assert_status(self.status)

		if self.is_new():
			return

		previous = frappe.db.get_value(self.doctype, self.name, "status")

		deployment_service.assert_transition(previous, self.status)
