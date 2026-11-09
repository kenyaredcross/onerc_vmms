# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The surge roster, the profession filter and the disability figures.

A coordinator puts a professional on the roster by hand, after checking their
licence; the roster is read inside their scope and grouped by profession; an
entry's readiness is derived from the licence date and the volunteer's
standing. The register narrows by profession and by disability through the
same scoped read, and the overview is told how many, never who.
"""

from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.api import professions as professions_api
from vmmsx.api import surge as surge_api
from vmmsx.api import volunteer as volunteer_api
from vmmsx.notifications.services import licence_expiry
from vmmsx.volunteer.services import surge
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

NURSE = "VMMSX Test Nurse"
DOCTOR = "VMMSX Test Clinical Officer"
CATEGORY = "VMMSX Test Physical"
KIND = "VMMSX Test Wheelchair user"


def _profession(name: str) -> str:
	if not frappe.db.exists("Profession", name):
		frappe.get_doc({"doctype": "Profession", "__newname": name}).insert(ignore_permissions=True)

	return name


def _disability() -> str:
	if not frappe.db.exists("Disability Type", CATEGORY):
		frappe.get_doc({"doctype": "Disability Type", "disability_type": CATEGORY}).insert(
			ignore_permissions=True
		)

	if not frappe.db.exists("Disability", KIND):
		frappe.get_doc(
			{"doctype": "Disability", "disability_name": KIND, "disability_type": CATEGORY}
		).insert(ignore_permissions=True)

	return KIND


class SurgeTestCase(VolunteerTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.grant_doctype_access(fixtures.VOLUNTEER_DOCTYPE, fixtures.SCOPE_ROLE)
		_profession(NURSE)
		_profession(DOCTOR)
		_disability()

		cls.here = fixtures.make_user("surge_here")
		cls.elsewhere = fixtures.make_user("surge_elsewhere")
		fixtures.grant_volunteer_scope(cls.here, cls.society_a["region"])
		fixtures.grant_volunteer_scope(cls.elsewhere, cls.society_b["region"])

	def setUp(self):
		super().setUp()
		# Each test starts from an empty roster and no active volunteers: the
		# class shares one transaction, so another test's people are still here.
		frappe.db.delete(surge.ENTRY_DOCTYPE)
		frappe.db.set_value(
			fixtures.VOLUNTEER_DOCTYPE, {"status": "Active"}, "status", "Exited", update_modified=False
		)

	def volunteer_at(self, handle: str, node: str, status: str = "Active", **profile):
		name = fixtures.make_profile(handle, "Surge", **profile)
		volunteer = fixtures.make_volunteer(name, node)
		frappe.db.set_value(
			fixtures.VOLUNTEER_DOCTYPE, volunteer.name, "status", status, update_modified=False
		)

		return volunteer.name

	def add(self, volunteer: str, profession: str = NURSE, **licence):
		values = {
			"licence_number": "NCK-12345",
			"issuing_body": "Nursing Council of Kenya",
			"licence_expiry": add_days(today(), 365),
			**licence,
		}

		with fixtures.acting_as(self.here):
			return surge_api.add_to_surge_roster(volunteer, profession=profession, **values)

	def roster(self, user: str | None = None, **criteria) -> dict:
		with fixtures.acting_as(user or self.here):
			return surge_api.surge_roster(**criteria)


class TestPuttingSomebodyOnTheRoster(SurgeTestCase):
	def test_the_check_is_recorded_with_who_checked_it(self):
		volunteer = self.volunteer_at("Achieng", self.society_a["ward"])
		answer = self.add(volunteer)

		entry = frappe.get_doc(surge.ENTRY_DOCTYPE, answer["entry"])
		self.assertEqual(entry.status, surge.STATUS_ACTIVE)
		self.assertEqual(entry.checked_by, self.here)
		self.assertEqual(str(entry.checked_on), today())
		self.assertEqual(entry.licence_number, "NCK-12345")
		self.assertEqual(answer["surge"][0]["standing"], surge.READY)

	def test_only_an_active_volunteer_can_be_added(self):
		volunteer = self.volunteer_at("Kiprop", self.society_a["ward"], status="Suspended")

		with self.assertRaises(frappe.ValidationError) as refused:
			self.add(volunteer)

		self.assertIn("Only an active volunteer", str(refused.exception))

	def test_an_expired_licence_is_refused(self):
		volunteer = self.volunteer_at("Wekesa", self.society_a["ward"])

		with self.assertRaises(frappe.ValidationError) as refused:
			self.add(volunteer, licence_expiry=add_days(today(), -1))

		self.assertIn("already expired", str(refused.exception))

	def test_the_licence_number_and_issuer_are_required(self):
		volunteer = self.volunteer_at("Nduta", self.society_a["ward"])

		with self.assertRaises(frappe.ValidationError):
			self.add(volunteer, licence_number="  ")

		with self.assertRaises(frappe.ValidationError):
			self.add(volunteer, issuing_body="")

	def test_the_same_profession_cannot_be_added_twice(self):
		volunteer = self.volunteer_at("Mwangi", self.society_a["ward"])
		self.add(volunteer)

		with self.assertRaises(frappe.ValidationError) as refused:
			self.add(volunteer)

		self.assertIn("already on the surge roster", str(refused.exception))

	def test_other_is_not_a_roster_profession(self):
		volunteer = self.volunteer_at("Otieno", self.society_a["ward"])

		with self.assertRaises(frappe.ValidationError):
			self.add(volunteer, profession="Other")

	def test_a_coordinator_elsewhere_cannot_add_this_branch_s_volunteer(self):
		volunteer = self.volunteer_at("Chebet", self.society_a["ward"])

		with fixtures.acting_as(self.elsewhere), self.assertRaises(frappe.PermissionError):
			surge_api.add_to_surge_roster(
				volunteer,
				profession=NURSE,
				licence_number="NCK-1",
				issuing_body="Nursing Council of Kenya",
			)


class TestReadingTheRoster(SurgeTestCase):
	def test_it_is_grouped_by_profession_inside_the_scope(self):
		nurse = self.volunteer_at("Amina", self.society_a["ward"])
		officer = self.volunteer_at("Baraka", self.society_a["other_ward"])
		self.add(nurse)
		self.add(officer, profession=DOCTOR, licence_number="COC-9", issuing_body="Clinical Officers Council")

		roster = self.roster()
		groups = {group["profession"]: group["count"] for group in roster["professions"]}

		self.assertEqual(groups.get(NURSE), 1)
		self.assertEqual(groups.get(DOCTOR), 1)
		self.assertEqual({row["volunteer"] for row in roster["rows"]}, {nurse, officer})
		self.assertEqual(self.roster(self.elsewhere)["rows"], [])

	def test_choosing_a_profession_narrows_the_rows_not_the_figures(self):
		self.add(self.volunteer_at("Faith", self.society_a["ward"]))
		self.add(
			self.volunteer_at("Juma", self.society_a["ward"]),
			profession=DOCTOR,
			licence_number="COC-2",
			issuing_body="Clinical Officers Council",
		)

		roster = self.roster(profession=DOCTOR)

		self.assertEqual({row["profession"] for row in roster["rows"]}, {DOCTOR})
		self.assertEqual(roster["figures"]["on_roster"], 2)

	def test_readiness_follows_the_volunteer_and_the_licence(self):
		suspended = self.volunteer_at("Halima", self.society_a["ward"])
		expiring = self.volunteer_at("Imani", self.society_a["ward"])
		self.add(suspended)
		self.add(expiring, licence_expiry=add_days(today(), 10))
		frappe.db.set_value(fixtures.VOLUNTEER_DOCTYPE, suspended, "status", "Suspended")

		standing = {row["volunteer"]: row["standing"] for row in self.roster()["rows"]}

		self.assertEqual(standing[suspended], surge.NOT_ACTIVE)
		self.assertEqual(standing[expiring], surge.EXPIRING)

		figures = self.roster()["figures"]
		self.assertEqual(figures["needs_review"], 1)
		self.assertEqual(figures["expiring"], 1)

	def test_a_licence_past_its_date_needs_review(self):
		volunteer = self.volunteer_at("Kamau", self.society_a["ward"])
		answer = self.add(volunteer)
		frappe.db.set_value(surge.ENTRY_DOCTYPE, answer["entry"], "licence_expiry", add_days(today(), -3))

		row = self.roster()["rows"][0]
		self.assertEqual(row["standing"], surge.LICENCE_EXPIRED)
		self.assertFalse(row["ready"])

	def test_a_renewed_licence_is_ready_again_and_stamped_again(self):
		volunteer = self.volunteer_at("Lilian", self.society_a["ward"])
		answer = self.add(volunteer)
		frappe.db.set_value(surge.ENTRY_DOCTYPE, answer["entry"], "licence_expiry", add_days(today(), -3))

		with fixtures.acting_as(self.here):
			renewed = surge_api.renew_surge_licence(
				answer["entry"],
				licence_number="NCK-67890",
				issuing_body="Nursing Council of Kenya",
				licence_expiry=add_days(today(), 365),
			)

		self.assertEqual(renewed["surge"][0]["standing"], surge.READY)
		self.assertEqual(renewed["surge"][0]["licence_number"], "NCK-67890")

	def test_standing_down_needs_a_reason_and_keeps_the_entry(self):
		volunteer = self.volunteer_at("Moraa", self.society_a["ward"])
		answer = self.add(volunteer)

		with fixtures.acting_as(self.here), self.assertRaises(frappe.ValidationError):
			surge_api.stand_down_from_surge(answer["entry"], reason=" ")

		with fixtures.acting_as(self.here):
			after = surge_api.stand_down_from_surge(answer["entry"], reason="Moved abroad")

		self.assertEqual(after["surge"][0]["standing"], surge.STOOD_DOWN)
		self.assertEqual(after["surge"][0]["stood_down_reason"], "Moved abroad")
		self.assertEqual(self.roster()["rows"], [])

		# Stood down, so the same profession can be added again later.
		self.add(volunteer)

	def test_the_register_marks_who_is_on_the_roster(self):
		on = self.volunteer_at("Nekesa", self.society_a["ward"])
		off = self.volunteer_at("Oduor", self.society_a["ward"])
		self.add(on)

		with fixtures.acting_as(self.here):
			rows = volunteer_api.find_volunteers(status="Active")["volunteers"]

		marked = {row["volunteer"]: row["on_surge_roster"] for row in rows}
		self.assertTrue(marked[on])
		self.assertFalse(marked[off])


class TestTheProfessionFilter(SurgeTestCase):
	def test_the_register_narrows_by_profession_inside_the_scope(self):
		nurse = self.volunteer_at("Pendo", self.society_a["ward"], vmms_profession=NURSE)
		self.volunteer_at("Rotich", self.society_a["ward"], vmms_profession=DOCTOR)
		self.volunteer_at("Sang", self.society_b["ward"], vmms_profession=NURSE)

		with fixtures.acting_as(self.here):
			found = volunteer_api.find_volunteers(status="Active", profession=NURSE)

		self.assertEqual([row["volunteer"] for row in found["volunteers"]], [nurse])
		self.assertEqual(found["total"], 1)
		self.assertEqual(found["volunteers"][0]["profession"], NURSE)

	def test_the_options_are_the_professions_held_in_scope(self):
		self.volunteer_at("Tabitha", self.society_a["ward"], vmms_profession=NURSE)
		self.volunteer_at("Umi", self.society_a["ward"])
		self.volunteer_at("Victor", self.society_b["ward"], vmms_profession=DOCTOR)

		with fixtures.acting_as(self.here):
			options = volunteer_api.register_professions()

		held = {row["profession"] for row in options["professions"]}
		self.assertIn(NURSE, held)
		self.assertNotIn(DOCTOR, held)
		self.assertGreaterEqual(options["without"], 1)


class TestTheDisabilityFigures(SurgeTestCase):
	def test_counts_and_kinds_inside_the_scope_only(self):
		before = self.figures(self.here)

		with_kind = self.volunteer_at("Wanjiku", self.society_a["ward"], vmms_disability_status="Yes")
		self.name_disability(with_kind)
		self.volunteer_at("Yusuf", self.society_a["ward"], vmms_disability_status="Yes")
		self.volunteer_at("Zawadi", self.society_a["ward"], vmms_disability_status="No")
		self.volunteer_at("Abdi", self.society_b["ward"], vmms_disability_status="Yes")

		after = self.figures(self.here)

		self.assertEqual(after["yes"] - before["yes"], 2)
		self.assertEqual(after["no"] - before["no"], 1)
		self.assertEqual(after["unspecified"] - before["unspecified"], 1)
		kinds = {row["category"]: row["count"] for row in after["categories"]}
		self.assertEqual(kinds.get(CATEGORY), 1)
		self.assertNotIn("names", after)

	def test_the_register_lists_them_by_answer_and_by_kind(self):
		with_kind = self.volunteer_at("Bahati", self.society_a["ward"], vmms_disability_status="Yes")
		self.name_disability(with_kind)
		without_kind = self.volunteer_at("Cherono", self.society_a["ward"], vmms_disability_status="Yes")
		self.volunteer_at("Dida", self.society_a["ward"], vmms_disability_status="No")

		with fixtures.acting_as(self.here):
			any_kind = volunteer_api.find_volunteers(status="Active", disability="Yes")
			this_kind = volunteer_api.find_volunteers(status="Active", disability_category=CATEGORY)

		self.assertEqual({row["volunteer"] for row in any_kind["volunteers"]}, {with_kind, without_kind})
		self.assertEqual([row["volunteer"] for row in this_kind["volunteers"]], [with_kind])

	def figures(self, user: str) -> dict:
		with fixtures.acting_as(user):
			return volunteer_api.disability_summary()

	def name_disability(self, volunteer: str) -> None:
		profile = frappe.get_doc(
			"Red Profile", frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, volunteer, "red_profile")
		)
		profile.append("vmms_disabilities", {"disability": KIND})
		profile.save(ignore_permissions=True)


class TestAPastExpiryIsRefused(SurgeTestCase):
	def test_the_record_refuses_a_past_date_however_it_is_saved(self):
		volunteer = self.volunteer_at("Wanjala", self.society_a["ward"])
		entry = frappe.get_doc(surge.ENTRY_DOCTYPE, self.add(volunteer)["entry"])
		entry.licence_expiry = add_days(today(), -1)

		with self.assertRaises(frappe.ValidationError) as refused:
			entry.save(ignore_permissions=True)

		self.assertIn("already expired", str(refused.exception))

	def test_an_entry_whose_licence_has_since_run_out_still_saves(self):
		volunteer = self.volunteer_at("Chebet", self.society_a["ward"])
		name = self.add(volunteer)["entry"]
		frappe.db.set_value(surge.ENTRY_DOCTYPE, name, "licence_expiry", add_days(today(), -3))

		entry = frappe.get_doc(surge.ENTRY_DOCTYPE, name)
		entry.notes = "Asked for the renewed licence."
		entry.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value(surge.ENTRY_DOCTYPE, name, "notes"), "Asked for the renewed licence.")


class TestExpiryNotices(SurgeTestCase):
	COORDINATOR = "county.coordinator@example.com"

	def sweep(self, as_of=None) -> list[str]:
		"""Run the daily check and return the subjects that were sent."""
		with (
			patch.object(frappe.db, "get_single_value", return_value="County Coordinator"),
			patch(
				"vmmsx.approvals.services.routing.holders_exactly_at", return_value=[self.COORDINATOR]
			) as holders,
			patch("vmmsx.notifications.services.direct.tell") as tell,
		):
			licence_expiry.notify_expiring(as_of=as_of)

		for call in holders.call_args_list:
			self.assertEqual(call.args[1], "County Coordinator")

		for call in tell.call_args_list:
			self.assertEqual(call.args[0], [self.COORDINATOR])
			self.assertEqual(call.kwargs["link"], licence_expiry.ROSTER_LINK)

		return [call.args[1] for call in tell.call_args_list]

	def test_nothing_is_sent_for_a_licence_far_from_expiry(self):
		self.add(self.volunteer_at("Mutua", self.society_a["ward"]), licence_expiry=add_days(today(), 365))

		self.assertEqual(self.sweep(), [])

	def test_the_coordinator_is_told_once_as_it_comes_due_and_once_on_the_day(self):
		expiry = add_days(today(), 30)
		self.add(self.volunteer_at("Akinyi", self.society_a["ward"]), licence_expiry=expiry)

		first = self.sweep()
		self.assertEqual(len(first), 1)
		self.assertIn("licence expires on", first[0])
		self.assertEqual(self.sweep(), [], "the same notice is not sent twice")

		on_the_day = self.sweep(as_of=getdate(expiry))
		self.assertEqual(len(on_the_day), 1)
		self.assertIn("expires today", on_the_day[0])
		self.assertEqual(self.sweep(as_of=add_days(expiry, 1)), [])

	def test_a_missed_day_is_caught_up_with_one_notice(self):
		expiry = add_days(today(), 10)
		self.add(self.volunteer_at("Otieno", self.society_a["ward"]), licence_expiry=expiry)

		late = self.sweep(as_of=add_days(expiry, 2))

		self.assertEqual(len(late), 1)
		self.assertIn("expired on", late[0])

	def test_a_renewed_licence_starts_the_notices_again(self):
		volunteer = self.volunteer_at("Njoki", self.society_a["ward"])
		name = self.add(volunteer, licence_expiry=add_days(today(), 20))["entry"]
		self.assertEqual(len(self.sweep()), 1)

		with fixtures.acting_as(self.here):
			surge_api.renew_surge_licence(
				name,
				licence_number="NCK-2",
				issuing_body="Nursing Council of Kenya",
				licence_expiry=add_days(today(), 50),
			)

		self.assertEqual(len(self.sweep()), 1)

	def test_a_branch_with_nobody_to_tell_is_told_once_somebody_is_appointed(self):
		self.add(self.volunteer_at("Kerubo", self.society_a["ward"]), licence_expiry=add_days(today(), 15))

		with (
			patch.object(frappe.db, "get_single_value", return_value="County Coordinator"),
			patch("vmmsx.approvals.services.routing.holders_exactly_at", return_value=[]),
			patch("vmmsx.notifications.services.direct.tell") as tell,
		):
			summary = licence_expiry.notify_expiring()

		tell.assert_not_called()
		self.assertEqual(summary["nobody_to_tell"], 1)
		self.assertEqual(len(self.sweep()), 1)


class TestTheProfessionsPage(SurgeTestCase):
	def test_counts_professions_inside_the_scope_only(self):
		self.volunteer_at("Imani", self.society_a["ward"], vmms_profession=NURSE)
		self.volunteer_at("Jabali", self.society_a["ward"], vmms_profession=NURSE)
		self.volunteer_at("Kito", self.society_a["ward"])
		self.volunteer_at("Lulu", self.society_b["ward"], vmms_profession=DOCTOR)

		with fixtures.acting_as(self.here):
			summary = professions_api.summary()

		rows = {row["profession"]: row for row in summary["professions"]}
		self.assertEqual(rows[NURSE]["volunteers"], 2)
		self.assertEqual(rows[NURSE]["total"], 2)
		self.assertNotIn(DOCTOR, rows)
		self.assertGreaterEqual(summary["without"], 1)

	def test_lists_the_people_who_hold_one_profession(self):
		nurse = self.volunteer_at("Makena", self.society_a["ward"], vmms_profession=NURSE)
		self.volunteer_at("Nia", self.society_a["ward"], vmms_profession=DOCTOR)
		self.volunteer_at("Oloo", self.society_b["ward"], vmms_profession=NURSE)

		with fixtures.acting_as(self.here):
			found = professions_api.people(NURSE)

		self.assertEqual([row["volunteer"] for row in found["people"]], [nurse])
		self.assertEqual(found["total"], 1)
		self.assertIsNone(found["people"][0]["member"])

	def test_a_profession_must_be_named(self):
		with fixtures.acting_as(self.here), self.assertRaises(frappe.ValidationError):
			professions_api.people("  ")

