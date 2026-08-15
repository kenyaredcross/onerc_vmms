# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Membership — the operational record, and the payment seam's landing pad.

Three things live on this controller and nowhere else:

**The anchor guardrails.** ACC-02 and ACC-03 are enforced in `validate()`,
which is the only place that runs before a membership can exist at all. A
membership with no Geo Node is refused at creation rather than corrected later,
because an unplaced record is invisible to geo scoping and unroutable by
approvals — it would exist with nobody able to see or act on it.

**The Proof-of-Membership guardrail.** `validate_source()` refuses a proof
marked against a type with no approver, and a proof with nothing attached —
both in `member/services/membership.py::assert_proof_consistent`, alongside the
type it needs to ask.

**The payment hooks.** `onerc_payments` calls back into the source document by
name, guarded by `hasattr`, so the signatures below must match what that app
invokes exactly. They are verified against the live consumer
(`onerc_prequalification`'s Vendor Application):

    on_payment_confirmed(self, amount=None, receipt=None, transaction_id=None)
    on_payment_receipt(self, receipt=None, transaction_id=None)

Both are thin. They record a fact and save; activation is re-evaluated by
`membership.on_update`, which runs on every save and asks whether this
membership's *configuration* is satisfied. That is why a payment confirming
before an approver looks, and one confirming after, are the same code.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from vmmsx.member.services import membership as membership_service
from vmmsx.member.services import payment, society
from vmmsx.registration.services import intake

GEO_NODE_FIELD = "geo_node"


class VMMSMembership(Document):
	def before_insert(self):
		"""The two-doctype write, at the only moment it can happen.

		A native Web Form writes one document; a registration needs core's
		identity spine and this app's member satellite as well. `before_insert`
		is after the form's values have landed and before the framework checks
		that `member` is filled in, which is the only window in which this app
		can supply it.

		It does nothing at all unless this insert is somebody registering
		themselves. A clerk enrolling a person at a counter names the member,
		and must never have their own attached to it.

		**The satellite is created elevated, and narrowly.** `member.ensure()`
		inserts without bypassing permissions by design, so that a registration
		clerk needs a real grant. A self-registering applicant is not a clerk
		and holds nothing: the satellite is created on their behalf, for their
		own profile, inside the same one-call elevation the profile write uses.
		"""
		profile = intake.claim_profile(self)

		if not profile:
			return

		if not self.member:
			from vmmsx.member.services import member as member_service

			with intake.as_system():
				self.member = member_service.ensure(profile).name

		intake.place(profile, self.get(GEO_NODE_FIELD))

	def validate(self):
		self.validate_anchor()
		self.validate_member()
		self.validate_source()

		# Whatever path this save came down, no identity is stored here. The
		# registration path has already emptied these; this is the guarantee
		# that does not depend on it having run.
		intake.clear_intake(self)

	def validate_anchor(self):
		"""ACC-02 and ACC-03 — placed, and placed where this society allows.

		The mandatory flag on the field already refuses an empty anchor at the
		framework level; this repeats the refusal in the app's own words so the
		rule is enforced by something that states it, not only by a JSON
		attribute somebody could clear.
		"""
		if not self.get(GEO_NODE_FIELD):
			frappe.throw(
				_(
					"A membership must be anchored to a Geo Node before it can exist. There are no"
					" unplaced records: an unplaced membership cannot be seen by geo scoping or"
					" routed to an approver."
				),
				frappe.MandatoryError,
				title=_("Missing Geo Anchor"),
			)

		# Which level is permitted is society configuration, read from settings
		# on every save. No level name appears in this file.
		society.assert_anchor_level(self.get(GEO_NODE_FIELD))

	def validate_member(self):
		"""A membership always belongs to somebody core already knows."""
		if not self.member:
			frappe.throw(_("A membership needs a member."), frappe.MandatoryError, title=_("No Member"))

	def validate_source(self):
		"""Proof-of-Membership: routed-only, and proof requires proof.

		Skipped with no type chosen yet — the field's own mandatory flag refuses
		that case in its own words, and `membership_service.assert_proof_consistent`
		needs a type to ask its approval_mode.
		"""
		if not self.membership_type:
			return

		membership_service.assert_proof_consistent(self)

	def on_update(self):
		"""Put a registration into motion, then re-evaluate activation.

		Both are idempotent services this hook only calls.

		`submit_once` exists because a web form has no second step: every other
		way into this app inserts and then submits deliberately, and a person
		filling in a public form has nobody to press the button. It acts only on
		a document `before_insert` actually claimed, so an ordinary desk insert
		still creates a draft and waits, exactly as it always has.

		Activation is `membership.try_activate()` — an idempotent service
		callable from anywhere — and that is what keeps the lifecycle out of a
		single framework callback.
		"""
		intake.submit_once(self, membership_service.submit)
		membership_service.on_update(self)

	def after_delete(self):
		"""A deleted membership changes what its member is.

		`after_delete`, not `on_trash`: the member's status is *derived* from
		their memberships, and during `on_trash` this row is still in the
		database. Refreshing then would count the membership being deleted and
		leave the member Active — which is exactly what happened before the
		removal test existed to catch it.
		"""
		from vmmsx.member.services import member as member_service

		if self.member and frappe.db.exists("VMMS Member", self.member):
			member_service.refresh(self.member)

	# --- the onerc_payments contract --------------------------------------

	def on_payment_confirmed(self, amount=None, receipt=None, transaction_id=None):
		"""The universal payment contract — and the activation trigger.

		Called by `onerc_payments` when a transaction naming this document
		resolves to Completed, whichever driver resolved it. The Manual driver
		reaches here through `confirm_payment()`; M-Pesa reaches here through a
		callback or a status poll. This method cannot tell the difference and
		must not try to.

		Idempotent: a gateway that retries, or an administrator who presses
		confirm twice, records one payment and activates once.
		"""
		if not payment.record_confirmation(
			self, amount=amount, receipt=receipt, transaction_id=transaction_id
		):
			return

		# Saving re-enters on_update, which re-evaluates activation. A routed
		# membership that is not yet approved simply stays where it is.
		self.save(ignore_permissions=True)

	def on_payment_receipt(self, receipt=None, transaction_id=None):
		"""Optional enrichment — a gateway receipt that arrived late.

		Fired only when a receipt turns up *after* the payment was already
		confirmed, which is the ordinary case on M-Pesa and may never happen at
		all on the Manual driver. Nothing here activates anything, and a
		membership is fully functional if this method is never called: the
		certificate simply renders without a receipt line.
		"""
		if not payment.record_receipt(self, receipt=receipt, transaction_id=transaction_id):
			return

		self.save(ignore_permissions=True)
