# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Renewal — a new record, gated on lapse, reusing everything else.

Every membership built here goes through the real `submit()` / `on_update()` /
`on_payment_confirmed()` path, on the real Manual payment driver — renewal adds
no payment or activation code of its own, so if renewal worked by accident
through some shortcut, these tests would not tell the difference. They are
written so that they would.

Two helpers do the work of simulating time having passed, because these tests
cannot wait a year for a membership to actually lapse:

- `expire_naturally()` backdates a membership's whole period into the past and
  then calls the real `membership.expire()` — the state the daily
  `expire_lapsed()` job leaves behind.
- `still_active_but_past_valid_to()` backdates only `valid_to`, leaving
  `membership_status` at Active — the window *before* that job has run, which
  is deliberately still renewable.
"""

import frappe
from frappe.utils import add_days, format_date, getdate, today

from vmmsx.api import member as member_api
from vmmsx.member.services import approval, certificate
from vmmsx.member.services import membership as membership_service
from vmmsx.member.services import renewal as renewal_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

FEE = 600

# A society-named role, declared here rather than in fixtures.py because only
# this suite needs it — the same shape as test_certificate_print.py's own
# PRINT_ROLE. Nothing in renewal.py or api/member.py names it; it arrives as an
# ordinary Custom DocPerm grant, exactly as a society would configure one for a
# membership coordinator.
COORDINATOR_ROLE = f"{fixtures.TEST_PREFIX} Renewal Coordinator"


class RenewalTestCase(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=FEE)

	@classmethod
	def activate(cls, profile: str, geo_node: str):
		"""An Active membership, submitted and paid through the real Manual driver."""
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, geo_node)
		membership_service.submit(membership)
		row = frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)
		row.on_payment_confirmed(amount=FEE, transaction_id=row.payment_transaction)

		return frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

	@classmethod
	def expire_naturally(cls, membership, ended_days_ago: int = 10, duration_days: int = 365):
		"""A membership whose whole period is in the past, then formally expired —
		the state the daily expire_lapsed() job would leave it in."""
		valid_to = add_days(getdate(today()), -ended_days_ago)
		valid_from = add_days(valid_to, -duration_days)
		frappe.db.set_value(
			fixtures.MEMBERSHIP_DOCTYPE, membership.name, {"valid_from": valid_from, "valid_to": valid_to}
		)
		membership_service.expire(frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name))

		return frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)

	@classmethod
	def still_active_but_past_valid_to(cls, membership, ended_days_ago: int = 1):
		"""The pre-expire-job window: valid_to has passed, membership_status has not moved."""
		past = add_days(getdate(today()), -ended_days_ago)
		frappe.db.set_value(fixtures.MEMBERSHIP_DOCTYPE, membership.name, "valid_to", past)

		return frappe.get_doc(fixtures.MEMBERSHIP_DOCTYPE, membership.name)


# --- new record, renews link, prior untouched, normal activation -----------


class TestNewRecordModel(RenewalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Renew", "Newrecord")

	def test_renewing_creates_a_new_record_linked_to_the_prior(self):
		prior = self.expire_naturally(self.activate(self.profile, self.society_a["ward"]))

		result = renewal_service.renew(prior)

		self.assertNotEqual(result["name"], prior.name)

		new = self.reload(result["name"])
		self.assertEqual(new.renews, prior.name)
		self.assertEqual(new.member, prior.member)
		self.assertEqual(new.geo_node, prior.geo_node)
		self.assertEqual(new.membership_type, prior.membership_type)

	def test_the_prior_membership_is_unchanged_and_stays_expired(self):
		prior = self.expire_naturally(self.activate(self.profile, self.society_a["ward"]))
		before = (prior.membership_status, prior.valid_from, prior.valid_to, prior.payment_transaction)

		renewal_service.renew(prior)

		after = self.reload(prior.name)
		self.assertEqual(after.membership_status, membership_service.STATUS_EXPIRED)
		self.assertEqual(
			(after.membership_status, after.valid_from, after.valid_to, after.payment_transaction), before
		)

	def test_the_new_membership_activates_through_the_normal_payment_path(self):
		prior = self.expire_naturally(self.activate(self.profile, self.society_a["ward"]))

		result = renewal_service.renew(prior)
		new = self.reload(result["name"])

		# Not active yet — it has its own, unpaid fee to settle, exactly like a
		# first application on a fee-bearing auto_on_payment type.
		self.assertEqual(new.membership_status, membership_service.STATUS_AWAITING_PAYMENT)

		new.on_payment_confirmed(amount=FEE, transaction_id=new.payment_transaction)

		self.assertEqual(self.membership_status(new.name), membership_service.STATUS_ACTIVE)


# --- after-expiry-only -------------------------------------------------------


class TestAfterExpiryOnly(RenewalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Renew", "Timing")

	def test_a_current_membership_is_refused(self):
		current = self.activate(self.profile, self.society_a["ward"])

		with self.assertRaises(frappe.ValidationError):
			renewal_service.renew(current)

	def test_the_refusal_names_the_membership_and_changes_nothing(self):
		current = self.activate(self.profile, self.society_a["ward"])
		before = (current.membership_status, current.valid_from, current.valid_to)

		try:
			renewal_service.renew(current)
			self.fail("a current membership was renewed")
		except frappe.ValidationError as exception:
			self.assertIn(current.name, str(exception))

		after = self.reload(current.name)
		self.assertEqual((after.membership_status, after.valid_from, after.valid_to), before)

	def test_an_expired_membership_is_allowed(self):
		prior = self.expire_naturally(self.activate(self.profile, self.society_a["ward"]))

		result = renewal_service.renew(prior)

		self.assertTrue(result["name"])

	def test_an_active_but_past_valid_to_membership_is_allowed(self):
		"""The pre-expire-job window: current in name only."""
		prior = self.still_active_but_past_valid_to(self.activate(self.profile, self.society_a["ward"]))
		self.assertEqual(prior.membership_status, membership_service.STATUS_ACTIVE)

		result = renewal_service.renew(prior)

		self.assertTrue(result["name"])


# --- Period Model A -----------------------------------------------------


class TestPeriodModelA(RenewalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Renew", "Period")

	def test_the_renewed_period_starts_at_activation_with_no_stacking_or_overlap(self):
		prior = self.expire_naturally(self.activate(self.profile, self.society_a["ward"]))

		result = renewal_service.renew(prior)
		new = self.reload(result["name"])
		new.on_payment_confirmed(amount=FEE, transaction_id=new.payment_transaction)
		new = self.reload(new.name)

		self.assertEqual(new.valid_from, getdate(today()))
		self.assertEqual(new.valid_to, add_days(getdate(today()), 365))

		# No stacking: the new period starts from today's activation, not from
		# where the prior one's own valid_to already sat.
		self.assertNotEqual(getdate(new.valid_from), getdate(prior.valid_from))
		self.assertGreater(getdate(new.valid_from), getdate(prior.valid_to))


# --- multi-branch isolation, no duplicate active ----------------------------


class TestMultiBranchIsolation(RenewalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Renew", "Branches")

	def test_renewing_one_branch_leaves_another_branch_untouched(self):
		nairobi = self.expire_naturally(self.activate(self.profile, self.society_a["ward"]))
		mombasa = self.activate(self.profile, self.society_a["other_ward"])
		mombasa_before = (mombasa.membership_status, mombasa.valid_from, mombasa.valid_to)

		result = renewal_service.renew(nairobi)
		new = self.reload(result["name"])

		self.assertEqual(new.geo_node, nairobi.geo_node)
		self.assertNotEqual(new.geo_node, mombasa.geo_node)

		mombasa_after = self.reload(mombasa.name)
		self.assertEqual(
			(mombasa_after.membership_status, mombasa_after.valid_from, mombasa_after.valid_to),
			mombasa_before,
		)

	def test_exactly_one_active_membership_per_branch_after_renewal(self):
		nairobi = self.expire_naturally(self.activate(self.profile, self.society_a["ward"]))
		mombasa = self.activate(self.profile, self.society_a["other_ward"])
		member = nairobi.member

		result = renewal_service.renew(nairobi)
		new = self.reload(result["name"])
		new.on_payment_confirmed(amount=FEE, transaction_id=new.payment_transaction)

		def active_at(geo_node: str) -> int:
			return frappe.db.count(
				fixtures.MEMBERSHIP_DOCTYPE,
				{
					"member": member,
					"geo_node": geo_node,
					"membership_status": membership_service.STATUS_ACTIVE,
				},
			)

		self.assertEqual(active_at(nairobi.geo_node), 1, "the renewed branch should hold exactly one active")
		self.assertEqual(active_at(mombasa.geo_node), 1, "the untouched branch should be unaffected")


# --- payment reuse (structural: no new payment code) ------------------------


class TestPaymentReuse(RenewalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Renew", "Payer")

	def test_the_renewal_requests_its_own_transaction_through_the_real_gateway(self):
		"""A renewal's fee is a real OneRC Payment Transaction — the same request
		payment.request() makes for a first application, not a second answer."""
		prior = self.expire_naturally(self.activate(self.profile, self.society_a["ward"]))

		result = renewal_service.renew(prior)
		new = self.reload(result["name"])

		self.assertTrue(new.payment_transaction)
		self.assertNotEqual(new.payment_transaction, prior.payment_transaction)
		self.assertTrue(frappe.db.exists("OneRC Payment Transaction", new.payment_transaction))

	def test_confirming_the_renewals_payment_through_the_manual_driver_activates_it(self):
		prior = self.expire_naturally(self.activate(self.profile, self.society_a["ward"]))

		result = renewal_service.renew(prior)
		new = self.reload(result["name"])

		fixtures.confirm_payment_through_manual_driver(new)

		self.assertEqual(self.membership_status(new.name), membership_service.STATUS_ACTIVE)
		self.assertEqual(self.membership_status(prior.name), membership_service.STATUS_EXPIRED)


# --- the renewable flag ------------------------------------------------------


class TestRenewableFlag(RenewalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.user = cls.scoped_user("renew_flag_holder")
		cls.profile = fixtures.make_profile("Renew", "Flagged", user=cls.user)

		cls.current = cls.activate(cls.profile, cls.society_a["ward"])
		cls.expired = cls.expire_naturally(cls.activate(cls.profile, cls.society_a["other_ward"]))
		cls.past_due_active = cls.still_active_but_past_valid_to(
			cls.activate(cls.profile, cls.society_b["ward"])
		)

	def mine(self) -> dict:
		with fixtures.acting_as(self.user):
			rows = member_api.my_memberships()

		return {row["name"]: row for row in rows}

	def test_a_current_membership_is_not_renewable(self):
		self.assertFalse(self.mine()[self.current.name]["renewable"])

	def test_an_expired_membership_is_renewable(self):
		self.assertTrue(self.mine()[self.expired.name]["renewable"])

	def test_an_active_but_past_valid_to_membership_is_renewable(self):
		rows = self.mine()

		self.assertTrue(rows[self.past_due_active.name]["renewable"])
		self.assertEqual(
			rows[self.past_due_active.name]["membership_status"], membership_service.STATUS_ACTIVE
		)

	def test_the_flag_is_computed_server_side_on_every_row(self):
		"""Structural: the DTO always carries the key, so a UI never has to guess."""
		for row in self.mine().values():
			self.assertIn("renewable", row)


# --- entitlement: owner-bypass, coordinator, stranger -----------------------


class TestEntitlement(RenewalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.holder = cls.scoped_user("renew_holder")
		# Deliberately built with no scope grant and no role at all — an
		# ordinary logged-in person who is nobody to this membership.
		cls.stranger = fixtures.make_user("renew_stranger")
		cls.coordinator = cls.scoped_user("renew_coordinator", [COORDINATOR_ROLE])
		fixtures.grant_membership_access(COORDINATOR_ROLE)

		cls.profile = fixtures.make_profile("Renew", "Entitled", user=cls.holder)

	def setUp(self):
		super().setUp()
		# A fresh, renewable prior for every method, so one test's renewal
		# cannot leave the next with nothing left to renew.
		self.prior = self.expire_naturally(self.activate(self.profile, self.society_a["ward"]))

	def test_the_holder_can_renew_their_own_membership(self):
		with fixtures.acting_as(self.holder):
			result = member_api.renew_membership(self.prior.name)

		new = self.reload(result["name"])
		self.assertEqual(new.renews, self.prior.name)
		self.assertEqual(new.member, self.prior.member)

	def test_a_stranger_cannot_renew_someone_elses_membership(self):
		with fixtures.acting_as(self.stranger), self.assertRaises(frappe.PermissionError):
			member_api.renew_membership(self.prior.name)

	def test_an_authorised_coordinator_within_scope_can_renew(self):
		with fixtures.acting_as(self.coordinator):
			result = member_api.renew_membership(self.prior.name)

		new = self.reload(result["name"])
		self.assertEqual(new.member, self.prior.member)
		self.assertEqual(new.renews, self.prior.name)

	def test_the_endpoint_never_accepts_a_member_argument(self):
		"""Session-derived entitlement, structurally: there is no member to pass."""
		import inspect

		params = list(inspect.signature(member_api.renew_membership).parameters)

		self.assertNotIn("member", params)
		self.assertEqual(params, ["membership", "membership_type"])


# --- certificate for the renewed record --------------------------------------


class TestCertificateForRenewal(RenewalTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.profile = fixtures.make_profile("Renew", "Certificate")

	def test_the_renewed_membership_has_its_own_certificate_showing_its_own_period(self):
		prior = self.expire_naturally(self.activate(self.profile, self.society_a["ward"]))

		result = renewal_service.renew(prior)
		new = self.reload(result["name"])
		new.on_payment_confirmed(amount=FEE, transaction_id=new.payment_transaction)
		new = self.reload(new.name)

		self.assertEqual(new.membership_status, membership_service.STATUS_ACTIVE)

		context = certificate.context_for(new)

		self.assertEqual(context["membership_id"], new.name)
		self.assertNotEqual(context["membership_id"], prior.name)
		self.assertEqual(context["valid_from"], format_date(new.valid_from))
		self.assertEqual(context["valid_to"], format_date(new.valid_to))
		self.assertNotEqual(context["valid_to"], format_date(prior.valid_to))

		rendered = certificate.render_certificate(new)
		self.assertIn("Renew Certificate", rendered["body"])
