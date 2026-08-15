# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The picker's scope guarantee. This suite tries to break it.

A supervisor putting volunteers on stipend paperwork must never be able to see,
name, or add somebody outside their own area. Every route in is tested:

1. **Browsing.** `candidates()` returns the in-scope register and nothing else.
2. **Searching.** A term narrows what is already in scope. It is asserted that a
   term matching an out-of-scope person exactly — their full name, their email —
   returns nothing, because a search that could reach outside the scope would be
   a way to read the register one guess at a time.
3. **Naming somebody outright.** `resolve()` is the stricter mode, and it is not
   a way around the check: an out-of-scope volunteer is refused, and refused with
   **the same message** as an identifier that matches nobody at all, so the
   refusal is not an oracle for whether an email is on the register.
4. **The write path.** `report.add_volunteer()` goes through the picker, so the
   refusal reaches the document rather than only the search box.
5. **Failing closed.** No scope role configured, no role permission, no
   assignment: each produces an empty picker, never an unfiltered one.
6. **No override exists.** The signatures are inspected: there is no `user`, no
   `nodes` and no `geo_node` parameter on any of it, which is why there is no
   check that could be forgotten.

The users here are never System Managers. That role is core's documented scope
bypass, and a test passing because of it would be asserting nothing.
"""

import inspect

import frappe

from vmmsx.api import stipend as stipend_api
from vmmsx.stipend.services import picker
from vmmsx.stipend.services import report as report_service
from vmmsx.stipend.tests import fixtures
from vmmsx.stipend.tests.base import StipendTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class PickerTestCase(StipendTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# A supervisor assigned at a branch: their scope is that branch and
		# everything beneath it, and nothing beside it.
		cls.njoro = cls.supervisor("stipend_supervisor", cls.society_a["branch"])
		cls.nobody = fixtures.make_user("stipend_unassigned")

		cls.inside = cls.make_person(cls.society_a["ward"], "Inside", "TheScope")
		cls.also_inside = cls.make_person(cls.society_a["branch"], "AtThe", "BranchItself")
		cls.outside = cls.make_person(cls.society_a["other_ward"], "Outside", "TheScope")
		cls.elsewhere = cls.make_person(cls.society_b["ward"], "Another", "SocietyEntirely")

	@classmethod
	def make_person(cls, node: str, first_name: str, last_name: str):
		profile = fixtures.make_profile(first_name, last_name)

		return fixtures.make_volunteer(profile, node)

	def email_for(self, volunteer) -> str:
		return frappe.db.get_value("Red Profile", volunteer.red_profile, "email")


class TestBrowsingIsScoped(PickerTestCase):
	def test_a_supervisor_sees_their_own_subtree(self):
		with fixtures.acting_as(self.njoro):
			found = self.candidate_names(picker.candidates())

		self.assertIn(self.inside.name, found)
		self.assertIn(self.also_inside.name, found)

	def test_a_supervisor_never_sees_a_sibling_branch(self):
		with fixtures.acting_as(self.njoro):
			found = self.candidate_names(picker.candidates())

		self.assertNotIn(self.outside.name, found)

	def test_a_supervisor_never_sees_another_society(self):
		with fixtures.acting_as(self.njoro):
			found = self.candidate_names(picker.candidates())

		self.assertNotIn(self.elsewhere.name, found)

	def test_the_count_reported_is_a_count_of_what_they_may_see(self):
		with fixtures.acting_as(self.njoro):
			result = picker.candidates()

		self.assertEqual(result["in_scope"], len(result["candidates"]))
		self.assertEqual(result["in_scope"], 2)

	def test_the_limit_is_reported_when_it_bit(self):
		with fixtures.acting_as(self.njoro):
			result = picker.candidates(limit=1)

		self.assertEqual(len(result["candidates"]), 1)
		self.assertTrue(result["truncated"])

	def test_what_is_not_filtered_on_is_declared(self):
		"""A list of candidates is never mistaken for a list of the right people."""
		with fixtures.acting_as(self.njoro):
			result = picker.candidates()

		self.assertTrue(result["pending_criteria"])
		self.assertTrue(all(row["why"] for row in result["pending_criteria"]))


class TestSearchingCannotReachOutside(PickerTestCase):
	"""The term narrows the scope. It never widens it."""

	def test_a_term_narrows_the_in_scope_list(self):
		with fixtures.acting_as(self.njoro):
			found = self.candidate_names(picker.candidates(search="Inside"))

		self.assertEqual(found, [self.inside.name])

	def test_an_out_of_scope_persons_exact_name_returns_nothing(self):
		with fixtures.acting_as(self.njoro):
			found = self.candidate_names(picker.candidates(search="Outside TheScope"))

		self.assertEqual(found, [])

	def test_an_out_of_scope_persons_exact_email_returns_nothing(self):
		with fixtures.acting_as(self.njoro):
			found = self.candidate_names(picker.candidates(search=self.email_for(self.outside)))

		self.assertEqual(found, [])

	def test_an_out_of_scope_volunteers_exact_docname_returns_nothing(self):
		with fixtures.acting_as(self.njoro):
			found = self.candidate_names(picker.candidates(search=self.outside.name))

		self.assertEqual(found, [])

	def test_an_in_scope_person_is_findable_by_email(self):
		with fixtures.acting_as(self.njoro):
			found = self.candidate_names(picker.candidates(search=self.email_for(self.inside)))

		self.assertEqual(found, [self.inside.name])


class TestNamingSomebodyOutrightIsScoped(PickerTestCase):
	"""The stricter mode, and the refusal that gives nothing away."""

	def test_an_in_scope_volunteer_resolves_by_docname(self):
		with fixtures.acting_as(self.njoro):
			self.assertEqual(picker.resolve(self.inside.name), self.inside.name)

	def test_an_in_scope_volunteer_resolves_by_email(self):
		with fixtures.acting_as(self.njoro):
			self.assertEqual(picker.resolve(self.email_for(self.inside)), self.inside.name)

	def test_an_in_scope_volunteer_resolves_by_red_profile(self):
		with fixtures.acting_as(self.njoro):
			self.assertEqual(picker.resolve(self.inside.red_profile), self.inside.name)

	def test_an_out_of_scope_volunteer_is_refused_by_docname(self):
		with fixtures.acting_as(self.njoro), self.assertRaises(frappe.PermissionError):
			picker.resolve(self.outside.name)

	def test_an_out_of_scope_volunteer_is_refused_by_email(self):
		with fixtures.acting_as(self.njoro), self.assertRaises(frappe.PermissionError):
			picker.resolve(self.email_for(self.outside))

	def test_the_refusal_is_the_same_message_as_for_somebody_who_does_not_exist(self):
		"""Otherwise the picker is an oracle for who is on the register."""
		with fixtures.acting_as(self.njoro):
			with self.assertRaises(frappe.PermissionError) as out_of_scope:
				picker.resolve(self.email_for(self.outside))

			with self.assertRaises(frappe.PermissionError) as nonexistent:
				picker.resolve("nobody.at.all@example.invalid")

		self.assertEqual(str(out_of_scope.exception), str(nonexistent.exception))
		self.assertIn(picker.UNRESOLVED_IDENTIFIER, str(out_of_scope.exception))

	def test_an_empty_identifier_is_refused_rather_than_matching_anybody(self):
		with fixtures.acting_as(self.njoro), self.assertRaises(frappe.PermissionError):
			picker.resolve("")

	def test_the_predicate_agrees_with_the_refusal(self):
		with fixtures.acting_as(self.njoro):
			self.assertTrue(picker.is_in_scope(self.inside.name))
			self.assertFalse(picker.is_in_scope(self.outside.name))

			with self.assertRaises(frappe.PermissionError):
				picker.assert_in_scope(self.outside.name)


class TestTheWritePathIsScoped(PickerTestCase):
	"""The refusal reaches the document, not only the search box."""

	def setUp(self):
		super().setUp()
		self.report = fixtures.make_report(self.society_a["ward"])

	def test_an_in_scope_volunteer_can_be_added(self):
		with fixtures.acting_as(self.njoro):
			self.assertTrue(report_service.add_volunteer(self.report, self.inside.name))

		self.assertEqual(report_service.volunteers_of(self.report), [self.inside.name])

	def test_an_out_of_scope_volunteer_cannot_be_added(self):
		with fixtures.acting_as(self.njoro), self.assertRaises(frappe.PermissionError):
			report_service.add_volunteer(self.report, self.outside.name)

	def test_nothing_is_appended_when_the_add_is_refused(self):
		with fixtures.acting_as(self.njoro):
			with self.assertRaises(frappe.PermissionError):
				report_service.add_volunteer(self.report, self.email_for(self.outside))

		self.assertEqual(report_service.volunteers_of(self.report), [])

	def test_adding_the_same_volunteer_twice_does_not_duplicate_them(self):
		with fixtures.acting_as(self.njoro):
			report_service.add_volunteer(self.report, self.inside.name)
			self.assertFalse(report_service.add_volunteer(self.report, self.inside.name))

		self.assertEqual(report_service.volunteers_of(self.report), [self.inside.name])

	def test_a_second_add_fills_in_what_it_supplies_without_erasing(self):
		with fixtures.acting_as(self.njoro):
			report_service.add_volunteer(self.report, self.inside.name, activity="Distribution")
			report_service.add_volunteer(self.report, self.inside.name, notes="Two shifts")

		row = self.report.volunteers[0]

		self.assertEqual(row.activity, "Distribution")
		self.assertEqual(row.notes, "Two shifts")


class TestItFailsClosed(PickerTestCase):
	"""Empty is never read as unfiltered, whichever piece is missing."""

	def test_a_user_with_no_assignment_sees_nobody(self):
		with fixtures.acting_as(self.nobody):
			self.assertEqual(self.candidate_names(picker.candidates()), [])

	def test_a_user_with_no_assignment_can_name_nobody(self):
		with fixtures.acting_as(self.nobody), self.assertRaises(frappe.PermissionError):
			picker.resolve(self.inside.name)

	def test_an_unconfigured_scope_role_closes_the_picker(self):
		"""No role resolves, so no scope resolves, so nobody is returned."""
		self.addCleanup(fixtures.set_volunteer_scope_role, fixtures.VOLUNTEER_SCOPE_ROLE)
		fixtures.set_volunteer_scope_role(None)

		with fixtures.acting_as(self.njoro):
			self.assertEqual(self.candidate_names(picker.candidates()), [])

			with self.assertRaises(frappe.PermissionError):
				picker.resolve(self.inside.name)

	def test_a_scope_role_naming_a_role_nobody_holds_closes_the_picker(self):
		self.addCleanup(fixtures.set_volunteer_scope_role, fixtures.VOLUNTEER_SCOPE_ROLE)
		fixtures.set_volunteer_scope_role(fixtures.make_role(f"{fixtures.TEST_PREFIX} Held By Nobody"))
		self.addCleanup(frappe.delete_doc, "Role", f"{fixtures.TEST_PREFIX} Held By Nobody", force=True)

		with fixtures.acting_as(self.njoro):
			self.assertEqual(self.candidate_names(picker.candidates()), [])


class TestThereIsNoScopeOverride(PickerTestCase):
	"""Asserted against the signatures, because prose about it is not a guarantee."""

	FORBIDDEN = ("user", "nodes", "geo_node", "scope", "ignore_permissions", "all_volunteers")

	def assert_no_override(self, function):
		parameters = set(inspect.signature(function).parameters)
		leaked = parameters & set(self.FORBIDDEN)

		self.assertEqual(leaked, set(), f"{function.__name__} can be told where to look")

	def test_the_service_takes_no_scope_argument(self):
		for function in (picker.candidates, picker.resolve, picker.is_in_scope, picker.assert_in_scope):
			self.assert_no_override(function)

	def test_the_endpoints_take_no_scope_argument(self):
		for function in (stipend_api.find_volunteers, stipend_api.resolve_volunteer):
			self.assert_no_override(function)

	def test_the_endpoint_is_scoped_the_same_way_the_service_is(self):
		with fixtures.acting_as(self.njoro):
			found = [row["volunteer"] for row in stipend_api.find_volunteers()["candidates"]]

		self.assertIn(self.inside.name, found)
		self.assertNotIn(self.outside.name, found)

	def test_the_endpoint_refuses_an_out_of_scope_volunteer_by_name(self):
		with fixtures.acting_as(self.njoro), self.assertRaises(frappe.PermissionError):
			stipend_api.resolve_volunteer(self.outside.name)
