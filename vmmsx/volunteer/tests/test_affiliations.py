# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Two affiliation providers, one profile, and neither disturbing the other.

vmmsx now registers two providers with core: Member's and Volunteer's. A person
may be both, which makes this the first point in the build where core's rebuild
has more than one satellite app speaking about the same profile — and where the
removal rule has to be *isolating* rather than merely correct.

Core's rule is one sentence: **a row is deleted only when a registered provider
owns its `reference_doctype` and did not claim it.** Everything below is that
sentence being tested from the satellite side.

    a member and a volunteer          both rows present
    rebuild from live satellites      both rows reconstructed, nothing lost
    trash the volunteer               the volunteer row goes, the member row stays
    trash the member                  the member row goes, the volunteer row stays

The last two are the ones worth writing. A provider that removed too much would
quietly delete the other module's row; a provider that removed too little would
leave a row pointing at a satellite that no longer exists. Both are silent
failures that only surface when somebody reads a profile months later.

Everything is read through `read_gate.get_affiliations()` where the assertion is
about what a caller would see, because a direct child-table query bypasses the
gate by design — core says so explicitly.
"""

import frappe

from vmmsx.volunteer.services import volunteer as volunteer_service
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

MEMBER_KEY = "member"
VOLUNTEER_KEY = "volunteer"


class TwoProviderTestCase(VolunteerTestCase):
	"""A person who is both, built through each module's own service."""

	def both(self) -> dict:
		profile = fixtures.make_profile("Dual", "Affiliate")
		member = fixtures.make_member(profile)
		volunteer = fixtures.make_volunteer(profile, self.society_a["ward"])

		volunteer_service.refresh(volunteer.name)

		return {"profile": profile, "member": member.name, "volunteer": volunteer.name}


class TestBothProvidersAreRegistered(TwoProviderTestCase):
	def test_core_sees_two_providers_from_this_app(self):
		"""Read from the real hook, not from a fixture."""
		providers = list(frappe.get_hooks("onerc_affiliation_providers"))

		self.assertIn("vmmsx.member.affiliations.provide", providers)
		self.assertIn("vmmsx.volunteer.affiliations.provide", providers)

	def test_each_declares_only_what_it_owns(self):
		"""The declaration is what makes removal safe — and isolated."""
		from vmmsx.member.affiliations import provide as member_provide
		from vmmsx.volunteer.affiliations import provide as volunteer_provide

		person = self.both()

		self.assertEqual(member_provide(person["profile"])["reference_doctypes"], [fixtures.MEMBER_DOCTYPE])
		self.assertEqual(
			volunteer_provide(person["profile"])["reference_doctypes"], [fixtures.VOLUNTEER_DOCTYPE]
		)

	def test_neither_claims_the_other_type(self):
		"""Two providers claiming one affiliation type is refused by core.

		Asserted here rather than left to core's error, because the failure it
		prevents — one module's row being overwritten by another's — would be
		invisible until somebody read the profile.
		"""
		from vmmsx.member.affiliations import provide as member_provide
		from vmmsx.volunteer.affiliations import provide as volunteer_provide

		person = self.both()

		member_types = {row["affiliation_type"] for row in member_provide(person["profile"])["affiliations"]}
		volunteer_types = {
			row["affiliation_type"] for row in volunteer_provide(person["profile"])["affiliations"]
		}

		self.assertEqual(member_types, {MEMBER_KEY})
		self.assertEqual(volunteer_types, {VOLUNTEER_KEY})
		self.assertEqual(member_types & volunteer_types, set())


class TestBothAffiliationsCoexist(TwoProviderTestCase):
	def test_a_person_who_is_both_has_both_rows(self):
		person = self.both()

		self.assertEqual(self.affiliation_types(person["profile"]), {MEMBER_KEY, VOLUNTEER_KEY})

	def test_each_row_points_at_its_own_satellite(self):
		person = self.both()
		rows = {row["affiliation_type"]: row for row in self.affiliation_rows(person["profile"])}

		self.assertEqual(rows[MEMBER_KEY]["reference_doctype"], fixtures.MEMBER_DOCTYPE)
		self.assertEqual(rows[MEMBER_KEY]["reference_name"], person["member"])
		self.assertEqual(rows[VOLUNTEER_KEY]["reference_doctype"], fixtures.VOLUNTEER_DOCTYPE)
		self.assertEqual(rows[VOLUNTEER_KEY]["reference_name"], person["volunteer"])

	def test_both_are_visible_through_cores_read_gate(self):
		"""The path a caller actually uses, not a child-table query."""
		person = self.both()
		visible = {row["affiliation_type"] for row in self.visible_affiliations(person["profile"])}

		self.assertEqual(visible, {MEMBER_KEY, VOLUNTEER_KEY})


class TestRebuildReconstructsBoth(TwoProviderTestCase):
	"""Design 2's safety net, with two satellites answering instead of one."""

	def test_rebuilding_from_scratch_loses_nothing(self):
		"""Throw every row away and rebuild. Both must come back.

		This is the property that makes the index a derived thing rather than a
		source of truth: if a rebuild lost information, some row would have
		quietly become the only place that information lived.
		"""
		from onerc_core.identity.services.affiliation import rebuild_affiliations

		person = self.both()

		before = {
			(row["affiliation_type"], row["reference_doctype"], row["reference_name"])
			for row in self.affiliation_rows(person["profile"])
		}

		self._wipe_the_index(person["profile"])
		self.assertEqual(self.affiliation_rows(person["profile"]), [], "the wipe did not wipe")

		rebuild_affiliations(person["profile"])

		after = {
			(row["affiliation_type"], row["reference_doctype"], row["reference_name"])
			for row in self.affiliation_rows(person["profile"])
		}

		self.assertEqual(after, before)
		self.assertEqual(len(after), 2, "both providers should have been reconstructed")

	def test_the_rebuild_summary_names_both_owners(self):
		"""Core's own account of what it consulted."""
		from onerc_core.identity.services.affiliation import rebuild_affiliations

		person = self.both()
		summary = rebuild_affiliations(person["profile"])

		self.assertIn(fixtures.MEMBER_DOCTYPE, summary["owned_doctypes"])
		self.assertIn(fixtures.VOLUNTEER_DOCTYPE, summary["owned_doctypes"])
		self.assertGreaterEqual(summary["providers"], 2)

	def test_rebuilding_twice_changes_nothing_the_second_time(self):
		"""Idempotence, which is what lets a rebuild be run to reassure somebody."""
		from onerc_core.identity.services.affiliation import rebuild_affiliations

		person = self.both()

		rebuild_affiliations(person["profile"])
		second = rebuild_affiliations(person["profile"])

		self.assertFalse(second["changed"])
		self.assertEqual(second["written"], 0)
		self.assertEqual(second["removed"], 0)

	def _wipe_the_index(self, profile: str) -> None:
		"""Delete every row directly — the destructive half of the safety net.

		A direct query, deliberately, and the one place in these tests that is
		allowed one: the point is to destroy the index behind core's back and
		show that it can be rebuilt anyway.
		"""
		document = frappe.get_doc("Red Profile", profile)
		document.set("affiliations", [])
		document.flags.affiliations_from_service = True
		document.save(ignore_permissions=True)
		frappe.clear_document_cache("Red Profile", profile)


class TestRemovalIsIsolated(TwoProviderTestCase):
	"""One provider's satellite going away must not disturb the other's row."""

	def test_trashing_the_volunteer_removes_only_the_volunteer_row(self):
		person = self.both()

		frappe.delete_doc(fixtures.VOLUNTEER_DOCTYPE, person["volunteer"])

		self.assertEqual(self.affiliation_types(person["profile"]), {MEMBER_KEY})

	def row_for(self, profile: str, affiliation_type: str) -> dict:
		"""The one index row of this type, failing loudly if it is not there."""
		rows = [row for row in self.affiliation_rows(profile) if row["affiliation_type"] == affiliation_type]

		self.assertEqual(len(rows), 1, f"expected exactly one {affiliation_type} row, got {len(rows)}")

		return rows[0]

	def test_the_surviving_member_row_is_untouched_not_merely_present(self):
		"""Present but rewritten would be just as wrong, and harder to notice."""
		person = self.both()
		before = self.row_for(person["profile"], MEMBER_KEY)

		frappe.delete_doc(fixtures.VOLUNTEER_DOCTYPE, person["volunteer"])

		self.assertEqual(self.row_for(person["profile"], MEMBER_KEY), before)

	def test_trashing_the_member_removes_only_the_member_row(self):
		"""The mirror image — and the half that proves the first is not a fluke."""
		person = self.both()

		frappe.delete_doc(fixtures.MEMBER_DOCTYPE, person["member"])

		self.assertEqual(self.affiliation_types(person["profile"]), {VOLUNTEER_KEY})

	def test_the_surviving_volunteer_row_is_untouched(self):
		person = self.both()
		before = self.row_for(person["profile"], VOLUNTEER_KEY)

		frappe.delete_doc(fixtures.MEMBER_DOCTYPE, person["member"])

		self.assertEqual(self.row_for(person["profile"], VOLUNTEER_KEY), before)

	def test_trashing_both_leaves_nothing_behind(self):
		person = self.both()

		frappe.delete_doc(fixtures.VOLUNTEER_DOCTYPE, person["volunteer"])
		frappe.delete_doc(fixtures.MEMBER_DOCTYPE, person["member"])

		self.assertEqual(self.affiliation_types(person["profile"]), set())

	def test_the_removal_is_visible_through_the_read_gate_too(self):
		"""What a caller sees, not only what the table holds."""
		person = self.both()

		frappe.delete_doc(fixtures.VOLUNTEER_DOCTYPE, person["volunteer"])

		visible = {row["affiliation_type"] for row in self.visible_affiliations(person["profile"])}

		self.assertEqual(visible, {MEMBER_KEY})

	def test_a_volunteer_only_person_is_unaffected_by_any_of_this(self):
		"""Guards the pairs above: removal works with one provider claiming too."""
		profile = fixtures.make_profile("Volunteer", "Only")
		volunteer = fixtures.make_volunteer(profile, self.society_a["ward"])
		volunteer_service.refresh(volunteer.name)

		self.assertEqual(self.affiliation_types(profile), {VOLUNTEER_KEY})

		frappe.delete_doc(fixtures.VOLUNTEER_DOCTYPE, volunteer.name)

		self.assertEqual(self.affiliation_types(profile), set())


class TestTheSatelliteIsTheTruth(TwoProviderTestCase):
	def test_the_status_on_the_row_follows_the_satellite(self):
		"""The row is written from the satellite, never the other way round."""
		person = self.both()
		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, person["volunteer"])

		rows = {row["affiliation_type"]: row for row in self.affiliation_rows(person["profile"])}
		self.assertEqual(
			rows[VOLUNTEER_KEY]["status"], volunteer_service.affiliation_status(volunteer.status)
		)

		volunteer_service.record_exit(volunteer, reason="Moved away.")

		rows = {row["affiliation_type"]: row for row in self.affiliation_rows(person["profile"])}
		self.assertEqual(rows[VOLUNTEER_KEY]["status"], "Ended")
		self.assertEqual(rows[MEMBER_KEY]["status"], "Pending", "the member row moved with it")

	def test_an_edited_row_is_corrected_by_a_rebuild_rather_than_believed(self):
		"""The row is allowed to be stale; it is never allowed to be authoritative."""
		from onerc_core.identity.services.affiliation import rebuild_affiliations

		person = self.both()

		frappe.db.set_value(
			"Red Profile Affiliation",
			{"parent": person["profile"], "affiliation_type": VOLUNTEER_KEY},
			"status",
			"Ended",
		)
		frappe.clear_document_cache("Red Profile", person["profile"])

		rebuild_affiliations(person["profile"])

		rows = {row["affiliation_type"]: row for row in self.affiliation_rows(person["profile"])}
		volunteer = frappe.get_doc(fixtures.VOLUNTEER_DOCTYPE, person["volunteer"])

		self.assertEqual(
			rows[VOLUNTEER_KEY]["status"], volunteer_service.affiliation_status(volunteer.status)
		)
