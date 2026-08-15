# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Lifetime membership — a type that confers a membership with no end date.

The failure this replaces is worth stating, because it is the one these tests
are shaped to catch coming back: a society that wanted a life membership had to
fake one with a large duration, and a large duration is still a duration. A
"life" membership seeded at 3650 days expires, silently, ten years after the
demonstration that sold it.

So `is_lifetime` is a field on the type, and everything downstream reads an
empty `valid_to`:

- the type's own `validate_duration()` stops asking a lifetime type for a
  duration, **and asks every other type for one exactly as before** — the
  relaxation is tied to the flag, not to the guardrail being softened;
- `activate()` leaves `valid_to` empty rather than computing an expiry;
- the daily `expire_lapsed()` sweep never selects a membership without an end
  date, which is asserted against a real sweep run alongside a real lapsed
  membership, so "it did not expire" cannot pass because nothing ran;
- renewal refuses, because a membership with no period has no period to buy;
- the certificate says the word rather than leaving a blank where a date goes.

Nothing here is mocked. The lifetime type is routed and free — the shape a
society actually confers a life membership in, and Kenya's own seeded one — so
every membership below activates through the real approval engine on a real
approver's decision.
"""

import frappe
from frappe.utils import add_days, format_date, getdate, today

from vmmsx.approvals import states
from vmmsx.approvals.services import engine
from vmmsx.member.services import approval, certificate
from vmmsx.member.services import dossier as dossier_service
from vmmsx.member.services import membership as membership_service
from vmmsx.member.services import renewal as renewal_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

# The ordinary type these tests measure the lifetime one against. Fee-bearing
# and auto-on-payment, so a membership on it activates and expires by the
# ordinary path with no approver involved.
ORDINARY_FEE = 750
ORDINARY_DAYS = 365

# Throwaway type keys for the validation suite, which needs types it may leave
# in a refused state. Kept distinct from the fixtures' shared keys so a failed
# insert never removes a type another test is relying on.
TYPE_SPARE = f"{fixtures.TEST_PREFIX}-lifetime-spare"
TYPE_REFUSED = f"{fixtures.TEST_PREFIX}-lifetime-refused"

# A template body that prints the two context values this feature adds to a
# certificate, so a rendering assertion is about what a society would actually
# see rather than about a dict.
CERTIFICATE_BODY = "Valid from {{ valid_from }} to {{ valid_to }} (lifetime: {{ is_lifetime }})"


class LifetimeTestCase(MemberTestCase):
	"""One lifetime type, one ordinary type, one approver who may decide both."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.approver = cls.scoped_user("lifetime_approver", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.approver, fixtures.APPROVER_ROLE, cls.society_a["county"])
		fixtures.make_workflow()
		fixtures.grant_membership_access(fixtures.APPROVER_ROLE)
		fixtures.make_template(body=CERTIFICATE_BODY)

		# Routed and free: the approval alone activates it, which is how a
		# society confers a life membership. `duration_days` is deliberately
		# left at the fixture's 365 so that the type's own validation is what
		# clears it — a test asserting zero would otherwise be asserting that
		# the fixture passed zero in.
		cls.lifetime_type = fixtures.make_type(
			fixtures.TYPE_LIFETIME, approval.MODE_ROUTED, fee=0, is_lifetime=1
		)
		cls.ordinary_type = fixtures.make_type(
			fixtures.TYPE_AUTO,
			approval.MODE_AUTO_ON_PAYMENT,
			fee=ORDINARY_FEE,
			duration_days=ORDINARY_DAYS,
		)

	# --- the two ways a membership becomes active -------------------------

	def activate_lifetime(self, handle: str = "Life"):
		"""A live lifetime membership, activated by a real approver's decision."""
		profile = fixtures.make_profile(handle, "Member")
		membership = fixtures.make_membership(profile, fixtures.TYPE_LIFETIME, self.society_a["ward"])
		result = membership_service.submit(membership)

		with fixtures.acting_as(self.approver):
			engine.decide(self.reload(result["name"]), states.DECISION_APPROVED)

		return self.reload(result["name"])

	def activate_ordinary(self, handle: str = "Ordinary"):
		"""A live ordinary membership, activated by a real confirmed payment."""
		profile = fixtures.make_profile(handle, "Member")
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])
		membership_service.submit(membership)

		row = self.reload(membership.name)
		row.on_payment_confirmed(amount=ORDINARY_FEE, transaction_id=row.payment_transaction)

		return self.reload(membership.name)


# --- the guardrail, relaxed for one case and no other ----------------------


class TestTheDurationGuardrail(LifetimeTestCase):
	def type_doc(self, key: str, **overrides):
		"""An unsaved membership type, with the previous one of that key removed.

		Built here rather than through `fixtures.make_type` because these tests
		need the *insert* to be the thing that raises, and a helper that
		inserted for them would swallow the refusal being asserted.
		"""
		if frappe.db.exists(fixtures.TYPE_DOCTYPE, key):
			frappe.delete_doc(fixtures.TYPE_DOCTYPE, key, force=True)

		values = {
			"doctype": fixtures.TYPE_DOCTYPE,
			"membership_type_key": key,
			"membership_type_name": key,
			"approval_mode": approval.MODE_ROUTED,
			"fee_amount": 0,
			"duration_days": 365,
			"is_active": 1,
		}
		values.update(overrides)

		return frappe.get_doc(values)

	def test_a_lifetime_type_saves_with_no_duration_at_all(self):
		"""The whole point: a type that never expires needs no duration."""
		record = self.type_doc(TYPE_SPARE, is_lifetime=1, duration_days=0).insert()

		self.assertTrue(record.is_lifetime)
		self.assertEqual(record.duration_days, 0)

	def test_a_lifetime_type_has_a_duration_it_was_given_cleared(self):
		"""The 3650-day fake, dropped rather than stored beside the flag.

		A lifetime flag next to a ten-year duration is two answers to how long
		the membership lasts, and whichever a reader found first would be the
		one they believed.
		"""
		record = self.type_doc(TYPE_SPARE, is_lifetime=1, duration_days=3650).insert()

		self.assertEqual(record.duration_days, 0)
		self.assertEqual(frappe.db.get_value(fixtures.TYPE_DOCTYPE, record.name, "duration_days"), 0)

	def test_a_normal_type_with_no_duration_is_still_refused(self):
		"""The guardrail is intact for every type that does expire."""
		with self.assertRaises(frappe.ValidationError):
			self.type_doc(TYPE_REFUSED, duration_days=0).insert()

		self.assertFalse(frappe.db.exists(fixtures.TYPE_DOCTYPE, TYPE_REFUSED))

	def test_a_normal_type_with_a_negative_duration_is_still_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.type_doc(TYPE_REFUSED, duration_days=-30).insert()

		self.assertFalse(frappe.db.exists(fixtures.TYPE_DOCTYPE, TYPE_REFUSED))

	def test_clearing_the_lifetime_flag_brings_the_guardrail_back(self):
		"""The relaxation is tied to the flag, not to the type having once held it.

		Without this, a type could be made lifetime, saved with no duration, and
		then switched back to an expiring type that lapses on the day it
		activates.
		"""
		record = self.type_doc(TYPE_SPARE, is_lifetime=1, duration_days=0).insert()

		record.is_lifetime = 0

		with self.assertRaises(frappe.ValidationError):
			record.save()


# --- activation ------------------------------------------------------------


class TestLifetimeActivation(LifetimeTestCase):
	def test_a_lifetime_membership_activates_with_a_start_and_no_end(self):
		membership = self.activate_lifetime("Started")

		self.assertEqual(membership.membership_status, membership_service.STATUS_ACTIVE)
		self.assertEqual(membership.valid_from, getdate(today()))
		self.assertFalse(membership.valid_to)

	def test_no_end_date_is_stored_rather_than_a_far_future_placeholder(self):
		"""Read straight from the database, because a sentinel date would pass
		every assertion phrased as "not a year from now"."""
		membership = self.activate_lifetime("Nosentinel")

		self.assertIsNone(frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership.name, "valid_to"))

	def test_an_ordinary_membership_still_gets_its_computed_end_date(self):
		"""The regression half: relaxing the rule for one type changed no other."""
		membership = self.activate_ordinary("Unchanged")

		self.assertEqual(membership.membership_status, membership_service.STATUS_ACTIVE)
		self.assertEqual(membership.valid_from, getdate(today()))
		self.assertEqual(membership.valid_to, add_days(getdate(today()), ORDINARY_DAYS))

	def test_a_lifetime_membership_never_reads_as_lapsed(self):
		"""Asked about a date long past any duration a society could configure."""
		membership = self.activate_lifetime("Neverlapsed")
		far_future = add_days(getdate(today()), 365 * 200)

		self.assertFalse(membership_service.is_lapsed(membership, far_future))
		self.assertTrue(membership_service.is_current(membership, far_future))
		self.assertEqual(
			membership_service.effective_status(membership, far_future),
			membership_service.STATUS_ACTIVE,
		)


# --- the daily sweep -------------------------------------------------------


class TestTheDailyExpirySweep(LifetimeTestCase):
	"""The sweep, run for real, over a lapsed membership and a lifetime one.

	This class starts with no memberships at all — `MemberTestCase.setUpClass`
	clears them — which is what lets the summary counts below be exact. The
	assertion that matters is `checked`: the lifetime membership was never even
	*selected*, rather than selected and then skipped.
	"""

	def test_the_sweep_expires_the_lapsed_one_and_never_the_lifetime_one(self):
		lifetime = self.activate_lifetime("Sweepsurvivor")
		lapsed = self.activate_ordinary("Sweeptarget")

		# Backdate only the end date: the state the sweep exists to find.
		frappe.db.set_value(
			fixtures.MEMBERSHIP_DOCTYPE, lapsed.name, "valid_to", add_days(getdate(today()), -1)
		)

		summary = membership_service.expire_lapsed()

		self.assertEqual(summary, {"checked": 1, "expired": 1})
		self.assertEqual(self.membership_status(lapsed.name), membership_service.STATUS_EXPIRED)
		self.assertEqual(self.membership_status(lifetime.name), membership_service.STATUS_ACTIVE)
		self.assertIsNone(frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, lifetime.name, "valid_to"))

	def test_a_lifetime_membership_survives_a_sweep_run_far_in_the_future(self):
		"""No amount of elapsed time expires a membership with no end date."""
		lifetime = self.activate_lifetime("Futuresweep")

		membership_service.expire_lapsed(as_of=add_days(getdate(today()), 365 * 200))

		self.assertEqual(self.membership_status(lifetime.name), membership_service.STATUS_ACTIVE)


# --- renewal ---------------------------------------------------------------


class TestALifetimeMembershipIsNeverRenewable(LifetimeTestCase):
	def test_the_renewable_flag_is_false_while_it_is_active(self):
		membership = self.activate_lifetime("Notrenewable")

		self.assertFalse(renewal_service.is_renewable(membership))

	def test_it_is_still_not_renewable_when_something_marks_it_expired(self):
		"""Proves the refusal is read off the type, not off an empty valid_to.

		An empty `valid_to` would make the date comparison in `is_renewable`
		answer False by accident. A lifetime membership somebody moved to
		Expired by hand is the case that tells the two apart, and without the
		type check it would come back renewable.
		"""
		membership = self.activate_lifetime("Forcedexpired")
		frappe.db.set_value(
			fixtures.MEMBERSHIP_DOCTYPE,
			membership.name,
			"membership_status",
			membership_service.STATUS_EXPIRED,
		)

		self.assertFalse(renewal_service.is_renewable(self.reload(membership.name)))

	def test_renewing_one_is_refused_and_writes_nothing(self):
		membership = self.activate_lifetime("Refusedrenewal")
		before = frappe.db.count(fixtures.MEMBERSHIP_DOCTYPE)

		with self.assertRaises(frappe.ValidationError):
			renewal_service.renew(membership)

		self.assertEqual(frappe.db.count(fixtures.MEMBERSHIP_DOCTYPE), before)

	def test_an_ordinary_lapsed_membership_is_still_renewable(self):
		"""The other half: nothing about renewal was narrowed for everyone else."""
		membership = self.activate_ordinary("Stillrenewable")
		frappe.db.set_value(
			fixtures.MEMBERSHIP_DOCTYPE, membership.name, "valid_to", add_days(getdate(today()), -1)
		)

		self.assertTrue(renewal_service.is_renewable(self.reload(membership.name)))


# --- what a person is shown ------------------------------------------------


class TestLifetimeReadsCorrectly(LifetimeTestCase):
	def test_the_certificate_says_lifetime_where_an_end_date_would_be(self):
		membership = self.activate_lifetime("Certificate")

		context = certificate.context_for(membership)

		self.assertTrue(context["is_lifetime"])
		self.assertEqual(context["valid_to"], "Lifetime")
		self.assertEqual(context["valid_from"], format_date(membership.valid_from))

	def test_the_rendered_certificate_carries_the_word_and_no_empty_gap(self):
		membership = self.activate_lifetime("Rendered")

		body = certificate.render_certificate(membership)["body"]

		self.assertIn("Lifetime", body)
		self.assertIn(format_date(membership.valid_from), body)

	def test_an_ordinary_certificate_still_prints_its_end_date(self):
		membership = self.activate_ordinary("Ordinarycert")

		context = certificate.context_for(membership)

		self.assertFalse(context["is_lifetime"])
		self.assertEqual(context["valid_to"], format_date(membership.valid_to))

	def test_the_status_dto_says_why_the_end_date_is_empty(self):
		"""`valid_to` empty plus `is_lifetime` true, which is what the desk reads.

		`vmms_member.js` renders the validity cell from exactly these two
		fields, so a screen shows "Lifetime" rather than a row that looks like
		it failed to load.
		"""
		membership = self.activate_lifetime("Statusdto")

		dto = membership_service.status(membership)

		self.assertTrue(dto["is_lifetime"])
		self.assertIsNone(dto["valid_to"])
		self.assertEqual(dto["membership_status"], membership_service.STATUS_ACTIVE)

	def test_the_dossier_row_shows_a_current_membership_with_nothing_to_renew(self):
		membership = self.activate_lifetime("Dossier")

		row = dossier_service.membership_dto(membership, getdate(today()))

		self.assertTrue(row["is_lifetime"])
		self.assertIsNone(row["valid_to"])
		self.assertEqual(row["effective_status"], membership_service.STATUS_ACTIVE)
		self.assertTrue(row["is_current"])
		self.assertFalse(row["lapsed"])
		self.assertFalse(row["renewable"])
		# No duration is the honest answer, and it is what the type stores.
		self.assertEqual(row["duration_days"], 0)

	def test_the_pricing_dto_says_lifetime_instead_of_a_number_of_days(self):
		"""What the membership form reads before somebody chooses a type."""
		from vmmsx.api import member as member_api

		lifetime = member_api.membership_type_pricing(fixtures.TYPE_LIFETIME)
		ordinary = member_api.membership_type_pricing(fixtures.TYPE_AUTO)

		self.assertTrue(lifetime["is_lifetime"])
		self.assertEqual(lifetime["duration_days"], 0)
		self.assertFalse(ordinary["is_lifetime"])
		self.assertEqual(ordinary["duration_days"], ORDINARY_DAYS)
