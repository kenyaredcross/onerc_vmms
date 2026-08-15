# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Proof-of-Membership — a variant of the routed approval path, not a new one.

A pre-rollout member paid before this system existed and has no gateway
transaction to confirm. VMMS Membership carries a `proof_attachment` (Attach)
and a `membership_source` marker (`Gateway` | `Proof`); a proof-based
membership still goes through the exact routed approval path an ordinary
application does — the same engine, the same resolved approver, the same
gate. The approver's job is to look at what was attached and decide.

Nothing here reimplements routing, the state machine or the gate: every test
drives the real engine through `membership_service.submit()` and
`engine.decide()`, exactly as `test_approval_modes.py` does. The type used
below charges a fee on purpose — a pre-rollout member typically belongs to the
society's ordinary, fee-charging type, so a proof membership has to work on
one for the feature to fit the case it exists for. If it only worked on a
fee-free type, "no gateway transaction created" would be true by accident
rather than because proof bypassed it.
"""

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.approvals import states
from vmmsx.approvals.services import engine
from vmmsx.member.services import approval, certificate
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestProofOfMembership(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.approver = cls.scoped_user("proof_approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])
		fixtures.make_workflow()
		# An approver saves the membership when they decide, so the society's
		# role needs write access to it — same grant every routed test needs.
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.make_template()

		cls.proof_type = fixtures.make_type(fixtures.TYPE_PROOF, approval.MODE_ROUTED, fee=500)
		# auto_on_payment must charge something — a type that activates on
		# payment and charges nothing is refused by the type's own validation.
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=600)

	def apply_with_proof(self, attachment=None, **overrides):
		profile = fixtures.make_profile("Proof", "Applicant")
		membership = fixtures.make_membership(
			profile,
			fixtures.TYPE_PROOF,
			self.society_a["ward"],
			membership_source="Proof",
			proof_attachment=attachment if attachment is not None else fixtures.make_proof_file(),
			**overrides,
		)

		return membership_service.submit(membership)

	# --- activates with no payment ----------------------------------------

	def test_activates_via_routed_approval_with_no_payment(self):
		result = self.apply_with_proof()
		name = result["name"]

		self.assertEqual(self.membership_status(name), membership_service.STATUS_AWAITING_APPROVAL)
		self.assertEqual(self.approval_state(name), states.IN_REVIEW)
		self.assertFalse(frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, name, "payment_transaction"))

		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(name), states.DECISION_APPROVED)

		membership = self.reload(name)

		self.assertEqual(membership.membership_status, membership_service.STATUS_ACTIVE)
		self.assertEqual(membership.approval_state, states.APPROVED)
		# The whole point: a fee-bearing type, and still no gateway involved.
		self.assertFalse(membership.payment_transaction)
		self.assertFalse(membership.paid_on)

	def test_the_fresh_period_starts_at_approval_not_application(self):
		"""Period Model A — valid_from is the approval date, not a backdated one."""
		result = self.apply_with_proof()

		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(result["name"]), states.DECISION_APPROVED)

		membership = self.reload(result["name"])
		start = getdate(today())

		self.assertEqual(membership.valid_from, start)
		self.assertEqual(membership.valid_to, add_days(start, self.proof_type.duration_days))

	# --- source marker ------------------------------------------------------

	def test_source_marker_distinguishes_proof_from_gateway(self):
		proof_result = self.apply_with_proof()

		profile = fixtures.make_profile("Gateway", "Applicant")
		gateway_membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])
		gateway_result = membership_service.submit(gateway_membership)

		self.assertEqual(
			frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, proof_result["name"], "membership_source"),
			"Proof",
		)
		self.assertEqual(
			frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, gateway_result["name"], "membership_source"),
			"Gateway",
		)
		self.assertEqual(proof_result["membership_source"], "Proof")
		self.assertEqual(gateway_result["membership_source"], "Gateway")
		self.assertNotEqual(proof_result["membership_source"], gateway_result["membership_source"])

	def test_an_ordinary_membership_defaults_to_gateway_with_no_field_set(self):
		"""Nobody has to know the marker exists for the ordinary path to work."""
		profile = fixtures.make_profile("Default", "Source")
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])

		self.assertEqual(membership.membership_source, "Gateway")

	# --- rejection ------------------------------------------------------------

	def test_rejection_does_not_activate_a_proof_membership(self):
		result = self.apply_with_proof()

		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(result["name"]), states.DECISION_REJECTED, "Proof not acceptable")

		membership = self.reload(result["name"])

		self.assertEqual(membership.approval_state, states.REJECTED)
		self.assertNotEqual(membership.membership_status, membership_service.STATUS_ACTIVE)

	# --- wrong mode refused ----------------------------------------------------

	def test_proof_against_an_auto_on_payment_type_is_refused(self):
		profile = fixtures.make_profile("Wrong", "Mode")

		with self.assertRaises(frappe.ValidationError):
			fixtures.make_membership(
				profile,
				fixtures.TYPE_AUTO,
				self.society_a["ward"],
				membership_source="Proof",
				proof_attachment=fixtures.make_proof_file(),
			)

	# --- attachment ----------------------------------------------------------

	def test_a_proof_submission_with_no_attachment_is_refused(self):
		profile = fixtures.make_profile("No", "Attachment")

		with self.assertRaises(frappe.MandatoryError):
			fixtures.make_membership(
				profile,
				fixtures.TYPE_PROOF,
				self.society_a["ward"],
				membership_source="Proof",
			)

	def test_the_attachment_is_stored_and_visible_to_the_approver(self):
		attachment = fixtures.make_proof_file()
		result = self.apply_with_proof(attachment=attachment)

		with fixtures.acting_as(self.approver):
			membership = self.reload(result["name"])

			self.assertEqual(membership.proof_attachment, attachment)

	# --- certificate -----------------------------------------------------------

	def test_certificate_renders_for_a_proof_verified_membership(self):
		result = self.apply_with_proof()

		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(result["name"]), states.DECISION_APPROVED)

		membership = self.reload(result["name"])
		rendered = certificate.render_certificate(membership)

		self.assertTrue(rendered["body"])
		self.assertIn("Proof Applicant", rendered["body"])
