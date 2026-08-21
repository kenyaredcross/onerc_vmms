# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Terms of Reference — the mission document a deployment is run against.

A society writes one per piece of work it deploys volunteers to do: what the
situation is, what the mission is for, what it will achieve and leave behind,
how it will go about it, day by day, with what resources, and what a volunteer
must hold to take part. Every deployment and every request points at one.

**It is submittable, and that is the point.** Accepting a deployment assignment
is accepting these terms — there is no separate contract document, because the
terms *are* the contract. A document somebody has agreed to must not be editable
afterwards, so the wording is frozen on submit and a change is an amendment: a
new document, with its own key, which the deployments already run under the
original never see. `amended_from` records the chain.

**Retiring is not cancelling.** `is_active` is what a society un-ticks when it
stops using a piece of work, and it leaves every deployment run under it intact.
Cancelling a submitted document is for a terms of reference that should never
have existed, and `on_cancel` refuses it once anything points at it.

Four things on it are read by code, and each is a society's answer rather than
this app's:

    geo_scope               where these terms may be used. Empty means anywhere.
    approval_mode           whether a request under them needs an approver.
    required_certifications what a candidate must, or would ideally, hold.
    expected_start_date     what a deployment set up under them defaults to.

Nothing else here is read by anything. The background, the objectives, the
outputs, the approach, the itinerary, the stakeholders and the resources are all
for the people involved, and this app is careful not to develop opinions about
them.

The rules below are all about the document being coherent with itself, never
about any particular society's practice.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

from vmmsx.deployment.services import terms


class VMMSTermsofReference(Document):
	def validate(self):
		self.validate_requirements()
		self.validate_approval_mode()
		self.validate_period()
		self.validate_itinerary()
		self.price_resources()

	def validate_requirements(self):
		"""One row per certification type. Two would be two answers to one question.

		A terms of reference listing the same certification twice, once mandatory
		and once not, has no single answer to "is this required", and every reader
		would have to invent a tie-break. Refusing it here means no reader has to.
		"""
		seen = set()

		for row in self.required_certifications or []:
			if row.certification_type in seen:
				frappe.throw(
					_("{0} is listed twice in the requirements. List each certification once.").format(
						frappe.bold(row.certification_type)
					),
					frappe.DuplicateEntryError,
					title=_("Requirement Listed Twice"),
				)

			seen.add(row.certification_type)

	def validate_approval_mode(self):
		"""Refuse a mode nobody wrote a rule for, before anything depends on it.

		Checked here as well as at the point of use so that a society choosing a
		mode is told on the form, rather than on the first request raised under
		these terms.
		"""
		terms.assert_approval_mode(self)

	def validate_period(self):
		"""A mission cannot end before it starts.

		Both dates are optional — terms written for standing work have no mission
		window — so this only has an opinion when the society has given both.
		"""
		if not (self.expected_start_date and self.expected_end_date):
			return

		if getdate(self.expected_end_date) >= getdate(self.expected_start_date):
			return

		frappe.throw(
			_("This mission is set to end on {0}, before it begins on {1}.").format(
				frappe.bold(frappe.format(self.expected_end_date, {"fieldtype": "Datetime"})),
				frappe.bold(frappe.format(self.expected_start_date, {"fieldtype": "Datetime"})),
			),
			frappe.ValidationError,
			title=_("Mission Ends Before It Begins"),
		)

	def validate_itinerary(self):
		"""Every dated itinerary row falls inside the mission's own period.

		Checked on the parent rather than on the row, because a child row cannot
		see the mission's dates while it is being edited. Where the society has
		given no mission window there is nothing to be outside of, and this says
		nothing rather than inventing a bound.
		"""
		if not (self.expected_start_date and self.expected_end_date):
			return

		opens, closes = getdate(self.expected_start_date), getdate(self.expected_end_date)

		for row in self.itinerary or []:
			if not row.activity_date:
				continue

			if opens <= getdate(row.activity_date) <= closes:
				continue

			frappe.throw(
				_("Itinerary row {0} is dated {1}, outside this mission's period ({2} to {3}).").format(
					row.idx,
					frappe.bold(frappe.format(row.activity_date, {"fieldtype": "Date"})),
					frappe.format(opens, {"fieldtype": "Date"}),
					frappe.format(closes, {"fieldtype": "Date"}),
				),
				frappe.ValidationError,
				title=_("Itinerary Outside the Mission"),
			)

	def price_resources(self):
		"""Total each resource line from its own quantity and unit cost.

		Derived here rather than in the child controller because Frappe does not
		call a child's `validate`, so a rule written there would look like it
		worked and quietly never run. Recomputed on every save rather than only
		when blank: a stored total that can drift from the two numbers it came
		from is a total that eventually disagrees with them.
		"""
		for row in self.resources or []:
			row.total_cost = flt(row.quantity) * flt(row.unit_cost)

	def on_cancel(self):
		"""Refuse to cancel terms that something already points at.

		Cancelling is for a document that should never have existed. Once a
		deployment or a request has been raised under these terms, the way to stop
		offering them is to un-tick `is_active`, which keeps the history that
		cancelling would orphan. Frappe's own link check would catch the deployment
		on delete but not on cancel, so this is said explicitly.
		"""
		for doctype, label in (
			("VMMS Deployment", _("deployment")),
			("VMMS Deployment Request", _("request")),
		):
			count = frappe.db.count(doctype, {"terms_of_reference": self.name})

			if not count:
				continue

			frappe.throw(
				_(
					"{0} cannot be cancelled: {1} {2}(s) have been raised under it. To stop offering"
					" this work, un-tick Is Active instead — that keeps everything already run under"
					" these terms exactly as it is."
				).format(frappe.bold(self.tor_name or self.name), count, label),
				frappe.ValidationError,
				title=_("Terms Already In Use"),
			)
