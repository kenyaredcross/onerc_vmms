# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Identity is core's, and the affiliation row is a derived index.

Two claims, both easy to violate quietly:

1. **`VMMS Member` duplicates nothing.** It has no name, email or phone field —
   not even a `fetch_from`, which is a stored copy wearing a different hat. A
   name corrected on Red Profile is corrected everywhere the same instant,
   because there is only one of it.
2. **The affiliation row is written and never read.** vmmsx writes it through
   `set_affiliation()`; nothing branches on it. The tests below assert the write
   *and* assert that deleting the row changes no decision — which is the only
   way to show it is not secretly load-bearing.
"""

import frappe

from vmmsx.member.affiliations import provide
from vmmsx.member.services import approval, identity
from vmmsx.member.services import member as member_service
from vmmsx.member.services import membership as membership_service
from vmmsx.member.tests import fixtures
from vmmsx.member.tests.base import MemberTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestIdentityIsNotDuplicated(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=300)

	def test_the_member_doctype_owns_no_identity_fields(self):
		"""The structural guarantee. A field added here would break this."""
		fieldnames = {field.fieldname for field in frappe.get_meta(fixtures.MEMBER_DOCTYPE).fields}

		for forbidden in ("first_name", "last_name", "full_name", "email", "phone", "member_name"):
			self.assertNotIn(forbidden, fieldnames, f"{forbidden} duplicates Red Profile")

	def test_no_field_fetches_identity_from_the_profile(self):
		"""`fetch_from` stores a copy, which is the thing being avoided."""
		for field in frappe.get_meta(fixtures.MEMBER_DOCTYPE).fields:
			self.assertFalse(field.get("fetch_from"), f"{field.fieldname} fetches — that is a stored copy")

	def test_the_name_is_read_from_red_profile(self):
		profile = fixtures.make_profile("Wanjiku", "Kamau")
		member = member_service.ensure(profile)

		self.assertEqual(identity.display_name(member), "Wanjiku Kamau")

	def test_correcting_the_profile_corrects_the_member_view_immediately(self):
		"""One copy of a person means no synchronisation step to forget."""
		profile = fixtures.make_profile("Missp", "Elled")
		member = member_service.ensure(profile)

		self.assertEqual(identity.display_name(member), "Missp Elled")

		person = frappe.get_doc("Red Profile", profile)
		person.first_name = "Corrected"
		person.save()

		self.assertEqual(identity.display_name(member), "Corrected Elled")

	def test_the_dto_assembles_identity_at_the_moment_of_asking(self):
		profile = fixtures.make_profile("Dto", "Person")
		member = member_service.ensure(profile)
		dto = member_service.profile_dto(member)

		self.assertEqual(dto["red_profile"], profile)
		self.assertEqual(dto["full_name"], "Dto Person")
		self.assertEqual(dto["email"], frappe.db.get_value("Red Profile", profile, "email"))


class TestAffiliationIsADerivedIndex(MemberTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=400)

	def active_membership(self):
		profile = fixtures.make_profile("Affil", "Case")
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])
		membership_service.submit(membership)
		fixtures.confirm_payment_through_manual_driver(self.reload(membership.name))

		return profile, membership.name

	def test_activation_writes_the_row_through_set_affiliation(self):
		profile, _membership = self.active_membership()
		rows = self.affiliation_rows(profile)

		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["affiliation_type"], member_service.MEMBER_AFFILIATION_KEY)
		self.assertEqual(rows[0]["status"], "Active")
		self.assertEqual(rows[0]["reference_doctype"], fixtures.MEMBER_DOCTYPE)

	def test_the_row_points_back_at_the_satellite_that_owns_it(self):
		profile, membership = self.active_membership()
		member = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership, "member")

		self.assertEqual(self.affiliation_rows(profile)[0]["reference_name"], member)

	def test_deleting_the_row_changes_no_decision(self):
		"""The proof that nothing reads it: throw it away, and nothing moves.

		If any logic branched on the affiliation row, wiping it would change what
		the module believes. The satellite is the truth, so it does not.
		"""
		profile, membership = self.active_membership()
		member = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership, "member")

		frappe.db.delete("Red Profile Affiliation", {"parent": profile})
		frappe.clear_document_cache("Red Profile", profile)

		self.assertEqual(self.affiliation_rows(profile), [])

		# Everything the module knows is unchanged.
		self.assertEqual(self.membership_status(membership), membership_service.STATUS_ACTIVE)
		self.assertEqual(self.member_status(member), "Active")
		self.assertEqual(
			member_service.derive_status(frappe.get_doc(fixtures.MEMBER_DOCTYPE, member)), "Active"
		)

	def test_the_index_is_reconstructable_from_the_satellite(self):
		"""Design 2's safety net: rebuild loses nothing."""
		from onerc_core.identity.services.affiliation import rebuild_affiliations

		profile, _membership = self.active_membership()
		before = self.affiliation_rows(profile)

		frappe.db.delete("Red Profile Affiliation", {"parent": profile})
		frappe.clear_document_cache("Red Profile", profile)

		rebuild_affiliations(profile)

		self.assertEqual(self.affiliation_rows(profile), before)

	def test_the_provider_declares_the_doctype_it_owns(self):
		"""Declared ownership is what makes core's removal safe."""
		profile, _membership = self.active_membership()
		declaration = provide(profile)

		self.assertEqual(declaration["reference_doctypes"], [fixtures.MEMBER_DOCTYPE])
		self.assertEqual(len(declaration["affiliations"]), 1)

	def test_the_provider_is_quiet_about_a_non_member(self):
		"""Ownership still declared, nothing claimed — how core learns a row is stale."""
		profile = fixtures.make_profile("Not", "AMember")
		declaration = provide(profile)

		self.assertEqual(declaration["reference_doctypes"], [fixtures.MEMBER_DOCTYPE])
		self.assertEqual(declaration["affiliations"], [])

	def test_the_provider_is_registered_with_core(self):
		"""Registration is inverted: core never imports vmmsx."""
		providers = frappe.get_hooks("onerc_affiliation_providers")

		self.assertIn("vmmsx.member.affiliations.provide", providers)

	def test_the_index_is_reconstructable_after_the_satellite_changes(self):
		"""Rebuild tracks the satellite rather than preserving what was there."""
		from onerc_core.identity.services.affiliation import rebuild_affiliations

		profile, membership = self.active_membership()
		member = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership, "member")

		frappe.db.set_value(fixtures.MEMBER_DOCTYPE, member, "status", "Lapsed")
		rebuild_affiliations(profile)

		self.assertEqual(self.visible_affiliations(profile)[0]["status"], "Ended")

	def test_a_prospective_member_is_indexed_as_pending_not_active(self):
		profile = fixtures.make_profile("Pending", "Case")
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])
		membership_service.submit(membership)

		rows = self.affiliation_rows(profile)

		self.assertEqual(rows[0]["status"], "Pending")


class TestTrashingTheSatelliteRemovesTheRow(MemberTestCase):
	"""The removal half of the round-trip — the direction that had code but no test.

	Reconstruction was already proven: delete the rows, rebuild, get them back.
	This is the other direction, and it is the one that can rot silently. A
	member who left the society but whose affiliation row survives is a person
	the index still calls a member, and nothing about the satellite would say so.

	Every assertion here is a **present → absent transition** on the same
	profile, read through core's gated accessor. Asserting only "absent at the
	end" would pass just as happily against a row that was never written.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_template()
		fixtures.make_type(fixtures.TYPE_AUTO, approval.MODE_AUTO_ON_PAYMENT, fee=450)

	def a_member(self):
		"""An active member, and the records behind them."""
		profile = fixtures.make_profile("Leaving", "Member")
		membership = fixtures.make_membership(profile, fixtures.TYPE_AUTO, self.society_a["ward"])
		membership_service.submit(membership)
		fixtures.confirm_payment_through_manual_driver(self.reload(membership.name))

		member = frappe.db.get_value(fixtures.MEMBERSHIP_DOCTYPE, membership.name, "member")

		return profile, member, membership.name

	def member_rows(self, profile: str) -> list[dict]:
		"""Only the rows this app owns, through core's supported read path."""
		return [
			row
			for row in self.visible_affiliations(profile)
			if row["affiliation_type"] == member_service.MEMBER_AFFILIATION_KEY
		]

	def trash(self, member: str, membership: str) -> None:
		"""Delete the satellite the way an administrator would.

		The membership goes first because it holds a Link to the member, and the
		framework will not delete a linked record. That deletion refreshes the
		member; the row is still there afterwards, which is what makes the next
		step the thing under test.
		"""
		frappe.delete_doc(fixtures.MEMBERSHIP_DOCTYPE, membership)
		frappe.delete_doc(fixtures.MEMBER_DOCTYPE, member)

	def test_the_row_is_present_and_then_absent(self):
		"""The headline: present before the trash, gone after it."""
		profile, member, membership = self.a_member()

		before = self.member_rows(profile)

		self.assertEqual(len(before), 1, "no row to remove — the test would prove nothing")
		self.assertEqual(before[0]["reference_name"], member)

		self.trash(member, membership)

		self.assertEqual(self.member_rows(profile), [], "the satellite is gone but its row survived")

	def test_deleting_the_membership_alone_does_not_remove_the_row(self):
		"""Isolates the cause: it is trashing the *member* that removes it.

		Without this, the test above could be passing because deleting the
		membership took the row with it, and `VMMS Member.on_trash` might never
		run at all.
		"""
		profile, _member, membership = self.a_member()

		frappe.delete_doc(fixtures.MEMBERSHIP_DOCTYPE, membership)

		rows = self.member_rows(profile)

		self.assertEqual(len(rows), 1, "the row vanished before the member was trashed")
		# Still a member record, so still indexed — but no longer active. With
		# their only membership gone the member derives back to Prospective,
		# which core's vocabulary calls Pending. Deleting a membership is not
		# the same event as one lapsing, and the index says so.
		self.assertEqual(rows[0]["status"], "Pending")
		self.assertNotEqual(rows[0]["status"], "Active")

	def test_the_profile_itself_survives(self):
		"""A person who stops being a member is still a person core knows."""
		profile, member, membership = self.a_member()

		self.trash(member, membership)

		self.assertTrue(frappe.db.exists("Red Profile", profile))

	def test_removal_is_driven_by_declared_ownership(self):
		"""Exercises the `reference_doctypes` path that makes removal safe.

		Core drops a row only when a registered provider *owns* its
		reference_doctype and did not claim it. With no provider registered
		nobody owns `VMMS Member`, so the same rebuild must leave the row alone —
		which is what stops core wiping an index it has no way to rebuild.

		Asserting both halves is the point: if the row disappeared here too,
		removal would not be ownership-driven at all.
		"""
		from onerc_core.identity.services.affiliation import rebuild_affiliations

		profile, member, membership = self.a_member()

		frappe.delete_doc(fixtures.MEMBERSHIP_DOCTYPE, membership)

		# A satellite that vanished *without* its cleanup running — a bad
		# migration, a direct delete. `ignore_on_trash` skips the handshake and
		# `force` skips the link check, leaving exactly the stale row core's
		# ownership rule exists to adjudicate.
		frappe.delete_doc(fixtures.MEMBER_DOCTYPE, member, ignore_on_trash=True, force=True)

		self.assertEqual(len(self.member_rows(profile)), 1, "no stale row to adjudicate")

		# Nobody registered owns VMMS Member, so core must leave the row alone —
		# it cannot tell "satellite deleted" from "owning app not installed".
		with self.patch_hooks({"onerc_affiliation_providers": []}):
			rebuild_affiliations(profile)

			self.assertEqual(
				len(self.member_rows(profile)), 1, "a row nobody owns was removed — core cannot rebuild it"
			)

		# With vmmsx's provider registered, the same rebuild removes it: the
		# owner was asked, and did not claim it.
		rebuild_affiliations(profile)

		self.assertEqual(self.member_rows(profile), [])
