# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Saying you are coming, and the promises the record makes about it.

Four things are being protected, and they are the four the design rests on.

**Every verb is idempotent**, in the sense `CLAUDE.md` requires: a second call
observes the work is done and returns the same answer. Two presses of a button
on a slow connection is the ordinary case, not the pathological one.

**One row per person per event, whatever the answer.** A person who withdraws
and then changes their mind again has one standing answer, not three, or "is
this person coming" becomes a question with several records to reconcile.

**Withdrawing does not delete.** A branch that counted on somebody has to be
able to see the answer changed, rather than finding that it appears never to
have been given. Same principle as `deployment/services/invitation.py`.

**Nothing here can be pointed at anybody else.** The profile is derived from
the session in `my_profile()`, so the test that matters most is the one that
signs in as somebody else and finds a different diary.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.events.services import attendance

EXTRA_TEST_RECORD_DEPENDENCIES = []

PREFIX = "ATTTEST"
DOMAIN = "@attendance.test"

class TestAttendance(IntegrationTestCase):
	"""**Every test invents its own event identifiers.** The two people are built
	once for the suite, so a diary written by one test is still there when the
	next runs; sharing a fixed `EVENT_A` between them made the assertions depend
	on the order the runner happened to pick. Fresh identifiers per test mean
	each one asserts about answers it gave itself, which is what it meant to
	assert in the first place.

	The identifiers are stand-ins and are never looked up. The service holds
	identifiers and nothing else, which is what lets this suite run on a bench
	with no events app installed: what is under test is the society's own record
	of an answer, not the listing the answer points at. `api/events.py::attend`
	is where a real published event is required, and that check belongs to the
	endpoint rather than to the service.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.user = _make_user("amina")
		cls.other_user = _make_user("bakary")

		cls.profile = _make_profile("Amina", "Otieno", cls.user)
		cls.other_profile = _make_profile("Bakary", "Ceesay", cls.other_user)

	def setUp(self):
		frappe.set_user(self.user)
		self.addCleanup(frappe.set_user, "Administrator")

		self.event = _event()
		self.other_event = _event()

	# --- the session, and the fact that it cannot be named ------------------

	def test_the_profile_comes_from_the_session(self):
		self.assertEqual(attendance.my_profile(), self.profile)

		frappe.set_user(self.other_user)
		self.assertEqual(attendance.my_profile(), self.other_profile)

	def test_a_guest_has_no_profile(self):
		frappe.set_user("Guest")

		self.assertIsNone(attendance.my_profile())

	def test_no_function_takes_a_person(self):
		"""The guarantee is structural, so it is asserted structurally."""
		import inspect

		for name in ("attend", "cancel", "my_events", "is_attending", "my_profile"):
			signature = inspect.signature(getattr(attendance, name))

			for parameter in signature.parameters:
				self.assertNotIn(
					parameter,
					{"user", "profile", "red_profile", "person"},
					f"{name}() may not name a person",
				)

	# --- saying yes ---------------------------------------------------------

	def test_attending_records_the_answer(self):
		answer = attendance.attend(self.event)

		self.assertTrue(answer["attending"])
		self.assertEqual(answer["event"], self.event)
		self.assertIn(self.event, attendance.my_events())
		self.assertTrue(attendance.is_attending(self.event))

	def test_attending_twice_is_one_row(self):
		attendance.attend(self.event)
		attendance.attend(self.event)

		self.assertEqual(len(self._rows(self.event)), 1)
		self.assertIn(self.event, attendance.my_events())

	def test_a_second_row_is_refused_by_the_doctype_itself(self):
		"""Not only by the service. A desk insert has to be stopped too."""
		attendance.attend(self.event)

		with self.assertRaises(frappe.DuplicateEntryError):
			frappe.get_doc(
				{
					"doctype": attendance.ATTENDANCE_DOCTYPE,
					"red_profile": self.profile,
					"event": self.event,
					"status": attendance.ATTENDING,
				}
			).insert(ignore_permissions=True)

	# --- taking it back -----------------------------------------------------

	def test_cancelling_keeps_the_row(self):
		attendance.attend(self.event)
		answer = attendance.cancel(self.event)

		self.assertFalse(answer["attending"])
		self.assertNotIn(self.event, attendance.my_events())
		self.assertFalse(attendance.is_attending(self.event))

		# The record of having answered survives, which is the whole point.
		row = frappe.db.get_value(
			attendance.ATTENDANCE_DOCTYPE,
			{"red_profile": self.profile, "event": self.event},
			["name", "status"],
			as_dict=True,
		)

		self.assertIsNotNone(row)
		self.assertEqual(row.status, attendance.CANCELLED)

	def test_cancelling_twice_changes_nothing(self):
		attendance.attend(self.event)
		attendance.cancel(self.event)
		answer = attendance.cancel(self.event)

		self.assertFalse(answer["attending"])
		self.assertNotIn(self.event, attendance.my_events())
		self.assertEqual(len(self._rows(self.event)), 1)

	def test_cancelling_something_never_answered_is_not_an_error(self):
		answer = attendance.cancel(self.event)

		self.assertFalse(answer["attending"])
		self.assertEqual(
			self._rows(self.event),
			[],
			"withdrawing an answer nobody gave should not create one",
		)

	def test_changing_your_mind_back_reuses_the_row(self):
		attendance.attend(self.event)
		attendance.cancel(self.event)
		attendance.attend(self.event)

		self.assertEqual(len(self._rows(self.event)), 1)
		self.assertIn(self.event, attendance.my_events())

	# --- one person's answers are their own ---------------------------------

	def test_one_persons_answers_are_not_anothers(self):
		attendance.attend(self.event)

		frappe.set_user(self.other_user)
		self.assertNotIn(self.event, attendance.my_events())

		attendance.attend(self.other_event)
		self.assertIn(self.other_event, attendance.my_events())

		frappe.set_user(self.user)
		self.assertIn(self.event, attendance.my_events())
		self.assertNotIn(self.other_event, attendance.my_events())

	def test_two_people_may_answer_for_the_same_event(self):
		attendance.attend(self.event)

		frappe.set_user(self.other_user)
		attendance.attend(self.event)

		self.assertIn(self.event, attendance.my_events())
		self.assertEqual(
			len(
				frappe.get_all(
					attendance.ATTENDANCE_DOCTYPE,
					filters={"event": self.event, "status": attendance.ATTENDING},
					pluck="name",
				)
			),
			2,
			"one row per person per event, not one row per event",
		)

	# --- the refusals -------------------------------------------------------

	def test_a_login_with_no_profile_is_told_to_register(self):
		stranger = _make_user("stranger")
		frappe.set_user(stranger)

		with self.assertRaises(frappe.ValidationError):
			attendance.attend(self.event)

	def test_an_empty_event_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			attendance.attend("")

	# --- helpers ------------------------------------------------------------

	def _rows(self, event: str) -> list[str]:
		"""This person's rows for one event. Should never be more than one."""
		return frappe.get_all(
			attendance.ATTENDANCE_DOCTYPE,
			filters={"red_profile": self.profile, "event": event},
			pluck="name",
		)


def _event() -> str:
	"""An identifier no other test in this suite will have used."""
	return f"{PREFIX}-{frappe.generate_hash(length=8)}"


def _make_user(slug: str) -> str:
	email = f"{slug}.{frappe.generate_hash(length=6)}{DOMAIN}"

	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": slug.title(),
			"send_welcome_email": 0,
		}
	).insert(ignore_permissions=True)

	frappe.clear_cache(user=email)

	return email


def _make_profile(first_name: str, last_name: str, user: str) -> str:
	"""Core's identity spine. Built the way every other suite in this app builds it."""
	return (
		frappe.get_doc(
			{
				"doctype": "Red Profile",
				"first_name": first_name,
				"last_name": last_name,
				"email": user,
				"user": user,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)
