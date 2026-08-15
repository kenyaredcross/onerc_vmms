# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The form builder's endpoints: who may work them, and what they refuse.

`registration/services/questions.py` is already tested for what a society may
ask and what an applicant may answer. This is the layer above it — `api/
questions.py`, the console screen's half — and the properties worth holding are
different ones:

1. **It is the administrator's, and it says so with a doctype rather than a
   role.** `VMMS Application Question` ships granting `System Manager` alone and
   `staff/services/permissions.py` deliberately never hands it to a scope role,
   so a coordinator running a register is refused. A question changes what every
   future applicant is asked; that is not the same act as running a register.

2. **It names no registration.** `targets()` derives the answerable doctypes
   from the schema, so the two this app ships are two rows rather than two
   branches, and a third would appear on its own.

3. **There is no delete, and retiring is not deleting.** Every answer already
   given stays on the application it was part of.

4. **A question cannot be moved between registrations**, which would orphan
   every answer already given under it.

5. **The controller still decides what is valid.** The endpoint saves through
   the document, so a Select with no choices is refused here exactly as on the
   desk — rather than the screen being the only thing standing in the way.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.api import questions as api
from vmmsx.registration.services import questions

EXTRA_TEST_RECORD_DEPENDENCIES = []

APPLICATION = "VMMS Volunteer Application"
MEMBERSHIP = "VMMS Membership"

PREFIX = "QBUILD"


class BuilderTestCase(IntegrationTestCase):
	"""An administrator, and somebody who runs a register but not the forms."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# A role with desk access and a real grant on an unrelated doctype, so
		# this user is a plausible coordinator rather than a user with nothing.
		# The question doctype is deliberately *not* among what they hold.
		cls.role = f"{PREFIX} Coordinator"

		if not frappe.db.exists("Role", cls.role):
			frappe.get_doc(
				{"doctype": "Role", "role_name": cls.role, "desk_access": 1}
			).insert(ignore_permissions=True)

		cls.coordinator = f"{PREFIX.lower()}-coordinator@example.com"

		if not frappe.db.exists("User", cls.coordinator):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": cls.coordinator,
					"first_name": PREFIX,
					"send_welcome_email": 0,
					"user_type": "System User",
				}
			).insert(ignore_permissions=True)

		frappe.get_doc("User", cls.coordinator).add_roles(cls.role)
		frappe.clear_cache(user=cls.coordinator)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")

	def ask(self, label: str, field_type: str = "Data", **overrides):
		values = {
			"doctype": questions.QUESTION_DOCTYPE,
			"asked_on": APPLICATION,
			"question_label": label,
			"field_type": field_type,
			"is_active": 1,
		}
		values.update(overrides)

		return frappe.get_doc(values).insert(ignore_permissions=True)


class TestItIsTheAdministratorsScreen(BuilderTestCase):
	def test_a_coordinator_cannot_read_the_catalogue(self):
		"""Holding a society role is not holding this one.

		The refusal is the permission layer's, asked of the doctype, so nothing
		in the endpoint or the screen names a role.
		"""
		frappe.set_user(self.coordinator)

		with self.assertRaises(frappe.PermissionError):
			api.catalogue(APPLICATION)

	def test_a_coordinator_cannot_add_a_question(self):
		frappe.set_user(self.coordinator)

		with self.assertRaises(frappe.PermissionError):
			api.save_question(
				asked_on=APPLICATION, question_label="Anything at all", field_type="Data"
			)

	def test_a_coordinator_cannot_retire_a_question(self):
		question = self.ask("A question they must not touch")

		frappe.set_user(self.coordinator)

		with self.assertRaises(frappe.PermissionError):
			api.set_question_active(question.name, False)

	def test_the_administrator_may(self):
		"""The other half: the refusals above are about the role, not about a
		door that is shut to everybody."""
		answer = api.catalogue(APPLICATION)

		self.assertTrue(answer["can_edit"])

	def test_there_is_no_delete_endpoint(self):
		"""Asserted at the module, because the absence is the design.

		An answer already given was part of an application somebody decided.
		Retiring is the whole of "stop asking this", and a delete added later
		would take evidence out from under a decision.
		"""
		exposed = [
			name
			for name in dir(api)
			if not name.startswith("_") and callable(getattr(api, name))
		]

		self.assertFalse([name for name in exposed if "delete" in name or "remove" in name])


class TestItNamesNoRegistration(BuilderTestCase):
	def test_the_targets_are_derived_from_the_schema(self):
		"""Both registrations appear because they carry the answer table, not
		because this module lists them."""
		targets = {row["doctype"] for row in api.targets()["targets"]}

		self.assertIn(APPLICATION, targets)
		self.assertIn(MEMBERSHIP, targets)

	def test_every_target_actually_carries_the_answer_table(self):
		"""The derivation and `questions.asks()` are the same question, so a
		target this screen offers is one the applicant's side would honour."""
		for row in api.targets()["targets"]:
			self.assertTrue(questions.asks(row["doctype"]), row["doctype"])

	def test_the_field_types_come_from_the_doctype(self):
		"""Read from the Select rather than listed again, so a type added to the
		field appears in the builder without this file being edited."""
		offered = api.targets()["field_types"]
		options = frappe.get_meta(questions.QUESTION_DOCTYPE).get_field("field_type").options

		self.assertEqual(offered, [line for line in options.split("\n") if line.strip()])


class TestTheCatalogue(BuilderTestCase):
	def test_it_shows_retired_questions_too(self):
		"""Deliberately not `questions.asked_on`, which is the applicant's view.

		An administrator who could not see what they switched off would think
		they had deleted it and make a second one next year.
		"""
		retired = self.ask("Since withdrawn", is_active=0)

		names = [row["name"] for row in api.catalogue(APPLICATION)["questions"]]
		asked = [row["name"] for row in questions.asked_on(APPLICATION)]

		self.assertIn(retired.name, names)
		self.assertNotIn(retired.name, asked)

	def test_a_row_carries_how_many_answered_it(self):
		"""The number that makes "retire, never delete" legible."""
		question = self.ask("Counted")

		row = next(
			row for row in api.catalogue(APPLICATION)["questions"] if row["name"] == question.name
		)

		self.assertEqual(row["answer_count"], 0)

	def test_choices_are_split_the_same_way_the_service_splits_them(self):
		"""One answer to what a choice list is, so the builder's preview and the
		wizard's dropdown cannot disagree."""
		question = self.ask("Pick one", "Select", options="Kalokol\n \nLodwar\n")

		row = next(
			row for row in api.catalogue(APPLICATION)["questions"] if row["name"] == question.name
		)

		self.assertEqual(row["choices"], ["Kalokol", "Lodwar"])


class TestSaving(BuilderTestCase):
	def test_a_new_question_goes_to_the_end(self):
		"""Not to position zero, where it would silently reorder a form somebody
		already designed."""
		first = self.ask("Already here", sequence=0)

		added = api.save_question(
			asked_on=APPLICATION, question_label="Added later", field_type="Data"
		)

		self.assertGreater(added["sequence"], first.sequence)

	def test_the_controller_still_refuses_a_select_with_no_choices(self):
		"""Saved through the document, so `validate()` runs. Routing around it
		would let this screen create a question the wizard cannot draw."""
		with self.assertRaises(frappe.MandatoryError):
			api.save_question(
				asked_on=APPLICATION, question_label="Pick one", field_type="Select"
			)

	def test_a_question_cannot_be_moved_to_another_registration(self):
		"""It would orphan every answer already given: the answers live on the
		application, and they would become answers to a question not asked there."""
		question = self.ask("Stays where it is")

		with self.assertRaises(frappe.ValidationError):
			api.save_question(
				name=question.name,
				asked_on=MEMBERSHIP,
				question_label="Stays where it is",
				field_type="Data",
			)

	def test_editing_rewords_without_touching_the_registration(self):
		question = self.ask("Original wording")

		saved = api.save_question(
			name=question.name,
			asked_on=APPLICATION,
			question_label="Reworded",
			field_type="Data",
		)

		self.assertEqual(saved["label"], "Reworded")
		self.assertEqual(saved["asked_on"], APPLICATION)


class TestRetiring(BuilderTestCase):
	def test_retiring_stops_it_being_asked_and_deletes_nothing(self):
		question = self.ask("On its way out")

		api.set_question_active(question.name, False)

		self.assertTrue(frappe.db.exists(questions.QUESTION_DOCTYPE, question.name))
		self.assertNotIn(
			question.name, [row["name"] for row in questions.asked_on(APPLICATION)]
		)

	def test_it_can_be_asked_again(self):
		question = self.ask("Back on", is_active=0)

		api.set_question_active(question.name, True)

		self.assertIn(question.name, [row["name"] for row in questions.asked_on(APPLICATION)])


class TestReordering(BuilderTestCase):
	def test_the_whole_order_is_sent_and_applied(self):
		first = self.ask("One", sequence=0)
		second = self.ask("Two", sequence=1)

		api.reorder_questions(APPLICATION, [second.name, first.name])

		ordered = [row["name"] for row in api.catalogue(APPLICATION)["questions"]]

		self.assertLess(ordered.index(second.name), ordered.index(first.name))

	def test_a_name_from_another_registration_is_ignored(self):
		"""The screen and the server can disagree about what exists if somebody
		else has been editing. Ordering what is there is the right answer to
		that; throwing would make a stale tab unusable."""
		mine = self.ask("Mine")
		theirs = self.ask("Theirs", asked_on=MEMBERSHIP)

		api.reorder_questions(APPLICATION, [theirs.name, mine.name])

		self.assertEqual(
			frappe.db.get_value(questions.QUESTION_DOCTYPE, theirs.name, "asked_on"), MEMBERSHIP
		)
