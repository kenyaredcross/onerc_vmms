# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Membership Type — the configuration record, and its guardrails.

Everything a national society decides differently about a kind of membership
lives here: the fee, the currency, how long it lasts, which certificate template
renders it, and — MEM-02 — whether it is routed to an approver or activates on
payment.

The validations are here rather than in the services on purpose: a type that
cannot work should be impossible to *save*, so an administrator finds out while
looking at the form rather than when the first applicant cannot be activated.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from vmmsx.member.services import payment
from vmmsx.member.services.approval import MODE_AUTO_ON_PAYMENT, MODES


class VMMSMembershipType(Document):
	def validate(self):
		self.validate_approval_mode()
		self.validate_duration()
		self.validate_fee()
		self.validate_payments_app()
		self.validate_benefits()

	def validate_approval_mode(self):
		"""MEM-02 — the mode must be one the code knows how to dispatch on."""
		if self.approval_mode in MODES:
			return

		frappe.throw(
			_("{0} is not an approval mode. Expected one of: {1}.").format(
				frappe.bold(self.approval_mode), ", ".join(MODES)
			),
			frappe.ValidationError,
			title=_("Unknown Approval Mode"),
		)

	def validate_duration(self):
		"""A duration of at least one day, unless this type never ends.

		`is_lifetime` is the one thing that relaxes this, and it relaxes it
		completely: a lifetime membership has no end date to compute, so a
		duration would be a number nothing reads. Every other type keeps the
		guardrail exactly as it was, because a zero or negative duration on a
		type that *does* expire produces a membership that lapses on the day it
		activates.

		The duration is **normalised to zero** rather than left at whatever the
		form last held. A stored 365 beside a lifetime flag is a second answer
		to how long the membership lasts, and a reader who found that one first
		would be told something the record does not do.
		"""
		if self.is_lifetime:
			self.duration_days = 0
			return

		if cint(self.duration_days) > 0:
			return

		frappe.throw(
			_(
				"A membership type needs a duration of at least one day, or {0} set for one that"
				" never expires."
			).format(frappe.bold(_("Is Lifetime"))),
			frappe.ValidationError,
			title=_("Invalid Duration"),
		)

	def validate_payments_app(self):
		"""A type that charges needs the app that collects. Checked at config time.

		The same principle as the ACC-02 anchor: a configuration that cannot work
		is refused while an administrator is looking at the form, not discovered
		by the first applicant when their click turns into a traceback.

		Deliberately **fee-scoped**. A zero-fee type collects nothing and never
		reaches the payments app at all, so a society running membership without
		fees must be able to configure it on a site with no gateway installed.
		Blocking those too would be the guard overreaching.
		"""
		if flt(self.fee_amount) <= 0:
			return

		payment.assert_available(self.membership_type_name or self.name)

	def validate_fee(self):
		"""A fee cannot be negative, and an auto-on-payment type needs one.

		The second rule is the one worth having. A type that activates on
		payment and charges nothing would have nothing to wait for and no
		approver either, so every application would activate the instant it was
		submitted — which may be what a society wants, but not by accident.
		"""
		if flt(self.fee_amount) < 0:
			frappe.throw(_("A fee cannot be negative."), frappe.ValidationError, title=_("Invalid Fee"))

		if self.approval_mode == MODE_AUTO_ON_PAYMENT and flt(self.fee_amount) <= 0:
			frappe.throw(
				_(
					"{0} activates on payment but charges nothing, so nothing would ever have to"
					" happen for a membership to become active. Give it a fee, or route it for"
					" approval instead."
				).format(frappe.bold(self.membership_type_name)),
				frappe.ValidationError,
				title=_("Nothing To Wait For"),
			)

	def validate_benefits(self):
		"""A benefit key identifies a benefit, so it may appear once."""
		seen = set()

		for row in self.benefits or []:
			if row.benefit_key in seen:
				frappe.throw(
					_("Benefit key {0} is listed twice.").format(frappe.bold(row.benefit_key)),
					frappe.ValidationError,
					title=_("Duplicate Benefit"),
				)

			seen.add(row.benefit_key)
