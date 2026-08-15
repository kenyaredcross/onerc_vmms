# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The coordinator's acts over a membership's standing, and who may work them.

`membership.cancel` and `membership.expire` were idempotent services with no way
to reach them: `membership_status` is derived and `read_only` on the doctype, so
there was no field to expose, and until now no endpoint and no button either.
Cancelling a membership was a bench console call.

Four things are held in place here:

1. **The holder bypass does not follow the verbs.** `api/member.py::_readable`
   admits the person a membership belongs to, so that somebody can see their own
   standing and print their own certificate without a society having to hand
   every member a role over the register. `_writable` deliberately does not.
   Reusing the read helper for the acts would have let a member cancel their own
   membership outside whatever process the society has for that, and it would
   have looked like reuse rather than like a hole.

2. **Geo scoping still applies.** `_writable` is the ordinary permission layer
   and `VMMS Membership` is registered as scopeable. The gate is deliberately on
   the membership rather than the member: `VMMS Member` is not scopeable — a
   person is not at a place, their membership is — so gating on the member would
   have dropped core's scoping entirely.

3. **Expire is not cancel with a different label.** The date test lives in
   `expire_lapsed`'s *query*, not in `expire()`, so an endpoint calling the
   service directly would end a lifetime membership or close a current one
   months early, with no reason recorded and nothing in the history saying who
   decided. `expire_membership` asks `is_lapsed` first. These tests are what
   stops that guard being quietly removed as redundant.

4. **`can_act` tells the truth**, because both surfaces draw their buttons from
   it.
"""

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.api import member as api
from vmmsx.member.services import approval
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

FEE = 500.0


class LifecycleApiTestCase(MemberTestCase):
	"""A coordinator who may act, one placed elsewhere, and a holder."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=FEE)
		fixtures.grant_membership_access(fixtures.SCOPE_ROLE)

		# Holds the scope role, assigned over society A. May act there.
		cls.coordinator = fixtures.make_user("mlife_coordinator", [fixtures.SCOPE_ROLE])
		fixtures.make_assignment(cls.coordinator, fixtures.SCOPE_ROLE, cls.society_a["county"])

		# Same role, wrong place.
		cls.elsewhere = fixtures.make_user("mlife_elsewhere", [fixtures.SCOPE_ROLE])
		fixtures.make_assignment(cls.elsewhere, fixtures.SCOPE_ROLE, cls.society_b["district"])

	# --- arrangement ------------------------------------------------------

	@classmethod
	def active(cls, profile: str | None = None, geo_node: str | None = None):
		"""An Active membership, submitted and paid through the real Manual driver."""
		profile = profile or fixtures.make_profile("Standing", "Subject")
		membership = fixtures.make_membership(
			profile, fixtures.TYPE_AUTO, geo_node or cls.society_a["ward"]
		)
		membership_service.submit(membership)
		row = frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)
		row.on_payment_confirmed(amount=FEE, transaction_id=row.payment_transaction)

		return frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

	@classmethod
	def lapsed(cls, membership, ended_days_ago: int = 1):
		"""`valid_to` has passed; `membership_status` has not moved yet.

		The window the daily sweep exists to close, and the only state in which
		`expire_membership` will act.
		"""
		frappe.db.set_value(
			fixtures.MEMBERSHIP_DOCTYPE,
			membership.name,
			"valid_to",
			add_days(getdate(today()), -ended_days_ago),
		)

		return frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

	def held(self, handle: str):
		"""A membership *and* the login of the person it belongs to.

		The binding is `Red Profile.user`, which is how this app recognises a
		holder everywhere — never `doc.owner`, who is the clerk that filed it.
		The user holds no scope role: the question is what somebody reaches by
		being the subject of a record rather than by holding authority over it.
		"""
		user = fixtures.make_user(handle, [fixtures.APPLICANT_ROLE])
		profile = fixtures.make_profile("Holder", "Themselves", user=user)

		return user, self.active(profile)

	def status_of(self, membership: str) -> str:
		return frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership, "membership_status")


class TestTheCoordinatorMayAct(LifecycleApiTestCase):
	def test_cancelling_moves_the_status(self):
		membership = self.active()

		with fixtures.acting_as(self.coordinator):
			api.cancel_membership(membership.name, reason="Requested by the member.")

		self.assertEqual(self.status_of(membership.name), "Cancelled")

	def test_cancelling_twice_is_the_same_as_cancelling_once(self):
		membership = self.active()

		with fixtures.acting_as(self.coordinator):
			api.cancel_membership(membership.name, reason="Requested.")
			api.cancel_membership(membership.name, reason="Requested again.")

		self.assertEqual(self.status_of(membership.name), "Cancelled")

	def test_expiring_a_lapsed_membership_closes_it(self):
		membership = self.lapsed(self.active())

		with fixtures.acting_as(self.coordinator):
			api.expire_membership(membership.name)

		self.assertEqual(self.status_of(membership.name), "Expired")

	def test_expiring_twice_is_the_same_as_expiring_once(self):
		membership = self.lapsed(self.active())

		with fixtures.acting_as(self.coordinator):
			api.expire_membership(membership.name)
			# The second call finds it already Expired rather than Active, so
			# `is_lapsed` is still true and the service simply does nothing.
			api.expire_membership(membership.name)

		self.assertEqual(self.status_of(membership.name), "Expired")


class TestExpireIsNotCancel(LifecycleApiTestCase):
	"""The guard in `expire_membership`, and why removing it would be a bug.

	`membership.expire()` moves *any* Active membership to Expired. What stops
	the daily sweep closing a lifetime membership is a `valid_to is set` filter
	in the sweep's own query — not anything in the service. So the endpoint asks
	`is_lapsed` before it acts, and these tests are what keeps that from being
	tidied away as redundant.
	"""

	def test_a_current_membership_cannot_be_expired(self):
		membership = self.active()

		with fixtures.acting_as(self.coordinator):
			with self.assertRaises(frappe.ValidationError):
				api.expire_membership(membership.name)

		self.assertEqual(self.status_of(membership.name), "Active")

	def test_the_refusal_points_at_the_verb_that_would_work(self):
		"""A coordinator who meant to end it early needs to be told which verb
		does that, or they will assume the record cannot be ended at all."""
		membership = self.active()

		with fixtures.acting_as(self.coordinator):
			with self.assertRaises(frappe.ValidationError) as refusal:
				api.expire_membership(membership.name)

		self.assertIn("ancel", str(refusal.exception))

	def test_a_current_membership_can_still_be_cancelled(self):
		"""The other half: refusing to expire must not mean refusing to end."""
		membership = self.active()

		with fixtures.acting_as(self.coordinator):
			api.cancel_membership(membership.name, reason="Ended early, by request.")

		self.assertEqual(self.status_of(membership.name), "Cancelled")


class TestTheHolderMayNotActOnTheirOwn(LifecycleApiTestCase):
	"""The regression this module exists for. `_readable` admits the holder and
	`_writable` does not; if the acts were ever routed through the read helper,
	every one of these would start passing in the wrong direction."""

	def test_the_holder_can_read_their_own_membership(self):
		"""The bypass is real, so the refusals below are about the verb.

		Without this, the refusals would pass even if the holder bypass had been
		deleted altogether, and they would be proving nothing.
		"""
		user, membership = self.held("mlife_holder_reads")

		with fixtures.acting_as(user):
			dto = api.get_membership(membership.name)

		self.assertEqual(dto["name"], membership.name)

	def test_the_holder_cannot_cancel_their_own_membership(self):
		user, membership = self.held("mlife_holder_cancels")

		with fixtures.acting_as(user):
			with self.assertRaises(frappe.PermissionError):
				api.cancel_membership(membership.name, reason="I would rather not pay.")

		self.assertEqual(self.status_of(membership.name), "Active")

	def test_the_holder_cannot_expire_their_own_membership(self):
		user, membership = self.held("mlife_holder_expires")
		self.lapsed(membership)

		with fixtures.acting_as(user):
			with self.assertRaises(frappe.PermissionError):
				api.expire_membership(membership.name)

		self.assertEqual(self.status_of(membership.name), "Active")


class TestScopingStillApplies(LifecycleApiTestCase):
	def test_a_coordinator_cannot_cancel_outside_their_scope(self):
		membership = self.active(geo_node=self.society_a["ward"])

		with fixtures.acting_as(self.elsewhere):
			with self.assertRaises(frappe.PermissionError):
				api.cancel_membership(membership.name, reason="Not mine to decide.")

		self.assertEqual(self.status_of(membership.name), "Active")

	def test_a_coordinator_cannot_expire_outside_their_scope(self):
		membership = self.lapsed(self.active(geo_node=self.society_a["ward"]))

		with fixtures.acting_as(self.elsewhere):
			with self.assertRaises(frappe.PermissionError):
				api.expire_membership(membership.name)

		self.assertEqual(self.status_of(membership.name), "Active")


class TestCanActAgreesWithTheCheck(LifecycleApiTestCase):
	"""Both surfaces draw their buttons from this flag, so it has to answer the
	same question the endpoint answers."""

	def test_can_act_is_true_for_a_coordinator_who_may_act(self):
		membership = self.active()

		with fixtures.acting_as(self.coordinator):
			dto = api.get_membership(membership.name)
			# Asserted against the act itself, not only against the flag: this is
			# what makes the two agree rather than merely both being True.
			api.cancel_membership(membership.name, reason="Proving the flag.")

		self.assertTrue(dto["can_act"])

	def test_can_act_is_false_for_the_holder(self):
		user, membership = self.held("mlife_holder_flag")

		with fixtures.acting_as(user):
			dto = api.get_membership(membership.name)

			with self.assertRaises(frappe.PermissionError):
				api.cancel_membership(membership.name, reason="Proving the flag.")

		self.assertFalse(dto["can_act"])

	def test_the_status_dto_says_whether_the_window_has_closed(self):
		"""`is_lapsed` rides on the DTO so the button and the endpoint derive it
		once, server-side, rather than twice in two places."""
		current = self.active()
		lapsed = self.lapsed(self.active())

		with fixtures.acting_as(self.coordinator):
			self.assertFalse(api.get_membership(current.name)["is_lapsed"])
			self.assertTrue(api.get_membership(lapsed.name)["is_lapsed"])
