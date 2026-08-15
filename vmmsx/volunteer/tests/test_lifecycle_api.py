# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The coordinator's acts over a volunteer's standing, and who may work them.

`volunteer.suspend`, `record_exit` and `reinstate` were idempotent services with
no way to reach them: `status` is derived and `read_only` on the doctype, so
there was no field to expose, and until now there was no endpoint and no button
either. Suspending somebody was a bench console call.

What these tests hold in place is not that the services work — `test_affiliations
.py` and `test_certification.py` already exercise those — but that **the door in
front of them is the right door**:

1. **The holder bypass does not follow the verbs.** `api/volunteer.py::_readable`
   admits the person a volunteer record is *about*, so that somebody can see
   their own standing without a society having to hand every volunteer a role
   over the register. `_writable` deliberately does not. Reusing the read helper
   for the acts would have let a suspended volunteer lift their own suspension,
   and it would have looked like reuse rather than like a hole.

2. **Geo scoping still applies**, because `_writable` is the ordinary permission
   layer and `VMMS Volunteer` is registered as scopeable. A coordinator cannot
   suspend somebody in another society by naming them.

3. **`can_act` tells the truth.** Both surfaces draw their buttons from it, so a
   flag that disagreed with the check the endpoint makes would mean a button
   that errors, or an act somebody may work and is never offered.

4. **Idempotence survives the endpoint.** The services are idempotent; a double
   click has to be too.

The last class covers `api/cards.py::download_card`, which is not a lifecycle
verb but is the same question about a different door: it names somebody else's
record, so it needs the check the possessive `download_my_card` does not. It
lives here because the scoped users above are exactly what testing that needs.
"""

import frappe

from vmmsx.api import cards as cards_api
from vmmsx.api import volunteer as api
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class LifecycleApiTestCase(VolunteerTestCase):
	"""A coordinator who may act, a bystander who may not, and a holder.

	Authority is arranged in `setUpClass` because Frappe rolls the test
	transaction back once per class: a method that granted a role would have
	granted it for every method after it.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.grant_doctype_access(fixtures.VOLUNTEER_DOCTYPE, fixtures.SCOPE_ROLE)

		# Holds the scope role, assigned over society A. May act there.
		cls.coordinator = fixtures.make_user("vlife_coordinator", [fixtures.SCOPE_ROLE])
		fixtures.make_assignment(cls.coordinator, fixtures.SCOPE_ROLE, cls.society_a["county"])

		# Holds the same role, but assigned over society B. Everything about them
		# is right except *where*, which is the point.
		cls.elsewhere = fixtures.make_user("vlife_elsewhere", [fixtures.SCOPE_ROLE])
		fixtures.make_assignment(cls.elsewhere, fixtures.SCOPE_ROLE, cls.society_b["district"])

	def make_volunteer(self, node: str | None = None):
		"""A volunteer nobody is logged in as."""
		profile = fixtures.make_profile("Standing", "Subject")

		return fixtures.make_volunteer(profile, node or self.society_a["ward"])

	def make_held_volunteer(self, handle: str):
		"""A volunteer *and* the login of the person it is about.

		The binding is `Red Profile.user`, which is how this app recognises a
		holder everywhere — never `doc.owner`, who is whoever filed the record.
		The user is given no scope role, because the whole question is what
		somebody reaches through being the subject of a record rather than
		through holding authority over it.
		"""
		user = fixtures.make_user(handle, [fixtures.APPLICANT_ROLE])
		profile = fixtures.make_profile("Holder", "Themselves", user=user)

		return user, fixtures.make_volunteer(profile, self.society_a["ward"])

	def status_of(self, volunteer: str) -> str:
		return frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, volunteer, "status")


class TestTheCoordinatorMayAct(LifecycleApiTestCase):
	def test_suspending_moves_the_status(self):
		volunteer = self.make_volunteer()

		with fixtures.acting_as(self.coordinator):
			api.suspend_volunteer(volunteer.name, reason="Under review.")

		self.assertEqual(self.status_of(volunteer.name), "Suspended")

	def test_suspending_twice_is_the_same_as_suspending_once(self):
		"""Idempotence has to survive the endpoint, not only the service.

		A double click is the ordinary case rather than the exotic one, and the
		second call must observe that the work is done and answer the same way.
		"""
		volunteer = self.make_volunteer()

		with fixtures.acting_as(self.coordinator):
			first = api.suspend_volunteer(volunteer.name, reason="Under review.")
			second = api.suspend_volunteer(volunteer.name, reason="Under review again.")

		self.assertTrue(first["changed"])
		self.assertFalse(second["changed"])
		self.assertEqual(self.status_of(volunteer.name), "Suspended")

	def test_reinstating_hands_the_question_back_to_the_applications(self):
		"""Reinstatement does not mean Active.

		The service clears the explicit status and lets the derivation run again,
		so somebody reinstated with no approved application behind them is
		Prospective. Asserting Active here would be asserting the bug.
		"""
		volunteer = self.make_volunteer()

		with fixtures.acting_as(self.coordinator):
			api.suspend_volunteer(volunteer.name, reason="Under review.")
			api.reinstate_volunteer(volunteer.name, reason="Review closed.")

		self.assertEqual(self.status_of(volunteer.name), "Prospective")

	def test_recording_an_exit_is_terminal_and_dated(self):
		volunteer = self.make_volunteer()

		with fixtures.acting_as(self.coordinator):
			api.record_volunteer_exit(volunteer.name, on_date="2026-03-01", reason="Moved away.")

		self.assertEqual(self.status_of(volunteer.name), "Exited")
		self.assertEqual(
			frappe.utils.getdate(
				frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, volunteer.name, "exited_on")
			),
			frappe.utils.getdate("2026-03-01"),
		)

	def test_an_exit_can_be_dated_when_it_happened(self):
		"""The date is accepted rather than assumed, and it is not today.

		An exit is often recorded after the fact; dating it the day somebody got
		round to the paperwork would misreport the hours and deployments either
		side of it.
		"""
		volunteer = self.make_volunteer()

		with fixtures.acting_as(self.coordinator):
			api.record_volunteer_exit(volunteer.name, on_date="2026-01-15", reason="Left.")

		self.assertNotEqual(
			frappe.utils.getdate(
				frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, volunteer.name, "exited_on")
			),
			frappe.utils.getdate(frappe.utils.today()),
		)


class TestTheHolderMayNotActOnThemselves(LifecycleApiTestCase):
	"""The regression this module exists for.

	`_readable` admits the holder and `_writable` does not. If the acts were ever
	routed through the read helper — which would look like reuse — every one of
	these would start passing silently in the wrong direction.
	"""

	def test_the_holder_can_read_their_own_dossier(self):
		"""The bypass is real, so the refusals below are about the verb.

		Without this, the refusal tests would pass even if the holder bypass had
		been deleted altogether, and they would be proving nothing.
		"""
		user, volunteer = self.make_held_volunteer("vlife_holder_reads")

		with fixtures.acting_as(user):
			dossier = api.get_dossier(volunteer.name)

		self.assertEqual(dossier["volunteer"], volunteer.name)

	def test_the_holder_cannot_suspend_themselves(self):
		user, volunteer = self.make_held_volunteer("vlife_holder_suspends")

		with fixtures.acting_as(user):
			with self.assertRaises(frappe.PermissionError):
				api.suspend_volunteer(volunteer.name, reason="I would rather not.")

		self.assertEqual(self.status_of(volunteer.name), "Prospective")

	def test_a_suspended_holder_cannot_lift_their_own_suspension(self):
		"""The case that would matter most if the gate were wrong."""
		user, volunteer = self.make_held_volunteer("vlife_holder_reinstates")

		with fixtures.acting_as(self.coordinator):
			api.suspend_volunteer(volunteer.name, reason="Under review.")

		with fixtures.acting_as(user):
			with self.assertRaises(frappe.PermissionError):
				api.reinstate_volunteer(volunteer.name, reason="I am fine now.")

		self.assertEqual(self.status_of(volunteer.name), "Suspended")

	def test_the_holder_cannot_record_their_own_exit(self):
		user, volunteer = self.make_held_volunteer("vlife_holder_exits")

		with fixtures.acting_as(user):
			with self.assertRaises(frappe.PermissionError):
				api.record_volunteer_exit(volunteer.name, reason="Goodbye.")

		self.assertEqual(self.status_of(volunteer.name), "Prospective")


class TestScopingStillApplies(LifecycleApiTestCase):
	"""`_writable` is the ordinary permission layer, so core's scoping comes with
	it. A coordinator whose role is right and whose place is wrong is refused."""

	def test_a_coordinator_cannot_suspend_outside_their_scope(self):
		volunteer = self.make_volunteer(self.society_a["ward"])

		with fixtures.acting_as(self.elsewhere):
			with self.assertRaises(frappe.PermissionError):
				api.suspend_volunteer(volunteer.name, reason="Not mine to decide.")

		self.assertEqual(self.status_of(volunteer.name), "Prospective")

	def test_a_coordinator_cannot_record_an_exit_outside_their_scope(self):
		volunteer = self.make_volunteer(self.society_a["ward"])

		with fixtures.acting_as(self.elsewhere):
			with self.assertRaises(frappe.PermissionError):
				api.record_volunteer_exit(volunteer.name, reason="Not mine to decide.")

		self.assertEqual(self.status_of(volunteer.name), "Prospective")


class TestCanActAgreesWithTheCheck(LifecycleApiTestCase):
	"""Both surfaces draw their buttons from this flag, so it has to answer the
	same question the endpoint answers. A flag that said yes where the act would
	be refused is a button that errors; one that said no where the act would
	succeed hides the verb from the person whose job it is."""

	def test_can_act_is_true_for_a_coordinator_who_may_act(self):
		volunteer = self.make_volunteer()

		with fixtures.acting_as(self.coordinator):
			dossier = api.get_dossier(volunteer.name)
			# Asserted against the act itself rather than only against the flag:
			# this is what makes the two agree rather than merely both being True.
			api.suspend_volunteer(volunteer.name, reason="Proving the flag.")

		self.assertTrue(dossier["can_act"])

	def test_can_act_is_false_for_the_holder(self):
		user, volunteer = self.make_held_volunteer("vlife_holder_flag")

		with fixtures.acting_as(user):
			dossier = api.get_dossier(volunteer.name)

			with self.assertRaises(frappe.PermissionError):
				api.suspend_volunteer(volunteer.name, reason="Proving the flag.")

		self.assertFalse(dossier["can_act"])


class TestReprintingSomebodyElsesCard(LifecycleApiTestCase):
	"""`api/cards.py::download_card` — the coordinator's door onto a card.

	The possessive `download_my_card` takes no record and needs no check. This
	one names a record, so the check that would otherwise be missing is written
	out. Only the refusals are asserted here: the gate runs before any rendering,
	so these are about the door rather than about the PDF, and what a card looks
	like is `cards/tests/` business.
	"""

	def test_a_coordinator_cannot_reach_a_card_outside_their_scope(self):
		volunteer = self.make_volunteer(self.society_a["ward"])

		with fixtures.acting_as(self.elsewhere):
			with self.assertRaises(frappe.PermissionError):
				cards_api.download_card("volunteer", volunteer.name)

	def test_an_unknown_kind_reaches_nothing(self):
		"""The dispatch table fails closed, like every other one in this app."""
		volunteer = self.make_volunteer()

		with fixtures.acting_as(self.coordinator):
			with self.assertRaises(frappe.ValidationError):
				cards_api.download_card("passport", volunteer.name)

	def test_a_volunteer_with_no_current_card_is_refused(self):
		"""`assert_holds` runs on this door too, because it is a fact about the
		record rather than about the caller: an exited volunteer's card is not
		reprintable by anybody."""
		volunteer = self.make_volunteer()

		with fixtures.acting_as(self.coordinator):
			api.record_volunteer_exit(volunteer.name, reason="Left.")

			with self.assertRaises(frappe.ValidationError):
				cards_api.download_card("volunteer", volunteer.name)

	def test_the_flag_the_screen_reads_and_the_door_agree(self):
		"""The property that matters, asserted in whichever direction it lands.

		`holds_card` on the dossier is what draws the reprint link; `assert_holds`
		is what the download enforces. If the flag is true the door must not
		refuse *for want of a card*, and if it is false the door must refuse. A
		test that only checked one direction would pass on a flag hardcoded to
		either value.
		"""
		volunteer = self.make_volunteer()

		with fixtures.acting_as(self.coordinator):
			holds = api.get_dossier(volunteer.name)["holds_card"]

			if holds:
				# It may still raise for want of a template on a bare bench, which
				# is not what this is about — only the "no current card" refusal
				# would contradict the flag.
				try:
					cards_api.download_card("volunteer", volunteer.name)
				except frappe.ValidationError as refusal:
					self.assertNotIn("no current card", str(refusal).lower())
			else:
				with self.assertRaises(frappe.ValidationError):
					cards_api.download_card("volunteer", volunteer.name)

	def test_exiting_takes_the_card_away(self):
		"""Whatever the volunteer's standing was, an exited one has no card."""
		volunteer = self.make_volunteer()

		with fixtures.acting_as(self.coordinator):
			api.record_volunteer_exit(volunteer.name, reason="Left.")

			self.assertFalse(api.get_dossier(volunteer.name)["holds_card"])

			with self.assertRaises(frappe.ValidationError):
				cards_api.download_card("volunteer", volunteer.name)
