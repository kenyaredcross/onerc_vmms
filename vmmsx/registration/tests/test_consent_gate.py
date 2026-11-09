# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The portal's terms panel: who is asked to accept what, and when.

`consent.outstanding` is the whole decision. Somebody brought over from the old
system has a volunteer or member record and no acceptance of anything, so they
are asked. A version published with "Ask everyone to accept again" asks again; a
version published without it (a typo fixed) asks nobody. A volunteer is held to
the volunteer declarations and a member to the membership ones.

Every declaration here is this suite's own and every assertion is narrowed to
them, so the shipped declarations — which a fresh volunteer has also not
accepted — cannot move an answer.
"""

import frappe

from vmmsx.api import consent as consent_api
from vmmsx.registration.services import consent, declarations
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

VOLUNTEER_TERMS = "suite-gate-volunteer"
MEMBER_TERMS = "suite-gate-member"
OPTIONAL_TERMS = "suite-gate-optional"
OURS = {VOLUNTEER_TERMS, MEMBER_TERMS, OPTIONAL_TERMS}


class TestConsentGate(RegistrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		for key, applies_to, required in (
			(VOLUNTEER_TERMS, fixtures.APPLICATION_DOCTYPE, 1),
			(MEMBER_TERMS, fixtures.MEMBERSHIP_DOCTYPE, 1),
			(OPTIONAL_TERMS, fixtures.APPLICATION_DOCTYPE, 0),
		):
			if frappe.db.exists("VMMS Declaration", key):
				continue
			frappe.get_doc(
				{
					"doctype": "VMMS Declaration",
					"declaration_key": key,
					"applies_to": applies_to,
					"title": f"Terms {key}",
					"sequence": 950,
					"is_required": required,
					"is_active": 1,
				}
			).insert(ignore_permissions=True)
			declarations.publish(key, "1", body="<p>Version one.</p>")

	# --- people -------------------------------------------------------------

	def person(self, handle: str) -> tuple[str, str]:
		"""A login and the Red Profile behind it, as an import leaves them: nothing accepted."""
		user = fixtures.website_account(handle)
		profile = fixtures.make_profile("Gate", handle.replace(".", ""))
		frappe.db.set_value("Red Profile", profile, "user", user)
		return user, profile

	def volunteer(self, handle: str, status: str = "Active") -> str:
		user, profile = self.person(handle)
		frappe.get_doc(
			{
				"doctype": "VMMS Volunteer",
				"red_profile": profile,
				"status": status,
				"home_geo_node": self.branch(),
			}
		).insert(ignore_permissions=True)
		return user

	def member(self, handle: str, user_profile: tuple[str, str] | None = None) -> str:
		user, profile = user_profile or self.person(handle)
		frappe.get_doc({"doctype": "VMMS Member", "red_profile": profile, "status": "Active"}).insert(
			ignore_permissions=True
		)
		return user

	def asked(self, user: str) -> dict[str, dict]:
		return {row["name"]: row for row in consent.outstanding(user) if row["name"] in OURS}

	def accept_all(self, user: str):
		with fixtures.acting_as(user):
			pending = consent_api.my_outstanding_declarations()
			return consent_api.accept_my_declarations(
				frappe.as_json(
					[{"declaration": row["name"], "declaration_version": row["declaration_version"]} for row in pending]
				)
			)

	# --- who is asked -------------------------------------------------------

	def test_somebody_with_no_record_is_asked_nothing(self):
		user, _ = self.person("gate.nobody")

		self.assertEqual(consent.outstanding(user), [])
		self.assertEqual(consent.outstanding("Guest"), [])

	def test_an_imported_volunteer_is_asked_the_volunteer_terms(self):
		user = self.volunteer("gate.imported")

		asked = self.asked(user)

		self.assertEqual(set(asked), {VOLUNTEER_TERMS})
		self.assertFalse(asked[VOLUNTEER_TERMS]["updated"], "never accepted, so not 'updated'")

	def test_an_optional_declaration_is_never_forced(self):
		user = self.volunteer("gate.optional")

		self.assertNotIn(OPTIONAL_TERMS, self.asked(user))

	def test_a_member_is_asked_the_membership_terms(self):
		user = self.member("gate.member")

		self.assertEqual(set(self.asked(user)), {MEMBER_TERMS})

	def test_somebody_who_is_both_is_asked_both(self):
		user = self.volunteer("gate.both")
		profile = consent.profile_of(user)
		self.member("gate.both", (user, profile))

		self.assertEqual(set(self.asked(user)), {VOLUNTEER_TERMS, MEMBER_TERMS})

	def test_a_volunteer_who_left_is_not_asked(self):
		user = self.volunteer("gate.exited", status="Exited")

		self.assertEqual(self.asked(user), {})

	def test_accepting_while_registering_counts(self):
		"""Somebody who registered through the form is not asked again for the same wording."""
		user, application = self.register_as_volunteer("gate.registered")
		self.approve(fixtures.APPLICATION_DOCTYPE, application.name)

		shipped = set(fixtures.required_declarations())
		asked = {row["name"] for row in consent.outstanding(user)}

		self.assertTrue(shipped, "the suite expects shipped required declarations")
		self.assertFalse(asked & shipped)

	# --- accepting ----------------------------------------------------------

	def test_accepting_records_a_consent_and_lets_them_in(self):
		user = self.volunteer("gate.accepts")

		remaining = self.accept_all(user)

		self.assertEqual(remaining, [])
		row = frappe.get_all(
			"VMMS Consent",
			filters={"user": user, "declaration": VOLUNTEER_TERMS},
			fields=["version", "declaration_version", "body_snapshot", "accepted_on"],
		)
		self.assertEqual(len(row), 1)
		# The current version, whichever an earlier method in this class published:
		# the class shares one transaction.
		current = frappe.get_doc("VMMS Declaration", VOLUNTEER_TERMS)
		self.assertEqual(row[0].version, current.version)
		self.assertEqual(row[0].declaration_version, declarations.current_version(VOLUNTEER_TERMS))
		self.assertEqual(row[0].body_snapshot, current.body)
		self.assertTrue(row[0].accepted_on)

	def test_every_outstanding_declaration_must_be_ticked(self):
		user = self.volunteer("gate.partial")

		with fixtures.acting_as(user), self.assertRaisesRegex(frappe.ValidationError, "Accept each"):
			consent_api.accept_my_declarations(frappe.as_json([]))

		self.assertFalse(frappe.db.exists("VMMS Consent", {"user": user}))

	def test_a_version_published_while_reading_is_refused(self):
		user = self.volunteer("gate.stale")
		with fixtures.acting_as(user):
			shown = consent_api.my_outstanding_declarations()

		declarations.publish(VOLUNTEER_TERMS, "1.1", body="<p>Newer.</p>")

		with fixtures.acting_as(user), self.assertRaisesRegex(frappe.ValidationError, "updated while you were reading"):
			consent_api.accept_my_declarations(
				frappe.as_json(
					[{"declaration": row["name"], "declaration_version": row["declaration_version"]} for row in shown]
				)
			)

	def test_a_guest_cannot_accept(self):
		with self.assertRaises(frappe.PermissionError):
			consent.accept("Guest", [])

	def test_a_consent_cannot_be_changed(self):
		user = self.volunteer("gate.frozen")
		self.accept_all(user)
		record = frappe.get_doc("VMMS Consent", {"user": user, "declaration": VOLUNTEER_TERMS})

		record.version = "99"
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be changed"):
			record.save(ignore_permissions=True)

	# --- new versions -------------------------------------------------------

	def test_a_correction_asks_nobody_again(self):
		user = self.volunteer("gate.typo")
		self.accept_all(user)

		declarations.publish(VOLUNTEER_TERMS, "1.0.1", body="<p>Version one, spelt right.</p>")

		self.assertEqual(self.asked(user), {})

	def test_a_version_marked_accept_again_asks_everybody_again(self):
		user = self.volunteer("gate.reaccept")
		self.accept_all(user)

		declarations.publish(VOLUNTEER_TERMS, "2", body="<p>Version two.</p>", requires_reacceptance=True)

		asked = self.asked(user)
		self.assertEqual(set(asked), {VOLUNTEER_TERMS})
		self.assertTrue(asked[VOLUNTEER_TERMS]["updated"])
		self.assertEqual(asked[VOLUNTEER_TERMS]["declaration_version"], declarations.current_version(VOLUNTEER_TERMS))

		self.accept_all(user)
		self.assertEqual(self.asked(user), {})

		# And a typo fixed after it still asks nobody.
		declarations.publish(VOLUNTEER_TERMS, "2.0.1", body="<p>Version two, spelt right.</p>")
		self.assertEqual(self.asked(user), {})
