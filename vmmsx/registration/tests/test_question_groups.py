# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Grouping the society's own questions — the tab a national society builds.

A society asks for things this product never anticipated, and until now it could
ask for them only as a flat list: thirty questions in a row on the form, and the
same thirty in a wall on the approver's screen. `question_group` is how a
society says *"these four belong together"* — "Health information", "Next of
kin" — and the two surfaces draw it as a section and as a tab respectively.

Four properties are under test, and each is written to fail if the property
stops holding rather than if the code changes shape:

1. **The group travels to both surfaces.** `asked_on` carries it to the form and
   `answers_of` carries it to the approver, so a society naming a group once
   gets it in both places.

2. **It is a snapshot, like the wording beside it.** A society that renames a
   group next year has not changed what an applicant was asked under, and an
   application decided last year still reads as it was asked. This is the same
   guarantee `question_label` and `field_type` already carry, extended to the
   third column.

3. **Nothing branches on the value.** "Health information" is a string a
   national society typed. This app never compares it, so there is no such thing
   as a group with behaviour attached — which is what lets a society invent one
   without a deploy.

4. **An empty group is not a group.** `groups()` reports what is in use, and
   ungrouped questions are not a group with an empty name — a surface drawing
   sections decides for itself what to call the rest.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.api import questions as api
from vmmsx.registration.services import questions

EXTRA_TEST_RECORD_DEPENDENCIES = []

APPLICATION = "VMMS Volunteer Application"

PREFIX = "QGROUP"
HEALTH = f"{PREFIX} Health information"
KIN = f"{PREFIX} Next of kin"


class QuestionGroupTestCase(IntegrationTestCase):
	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		self.addCleanup(frappe.set_user, "Administrator")

	def ask(self, label: str, group: str = "", **overrides):
		values = {
			"doctype": questions.QUESTION_DOCTYPE,
			"asked_on": APPLICATION,
			"question_label": label,
			"question_group": group,
			"field_type": "Data",
			"is_active": 1,
		}
		values.update(overrides)

		return frappe.get_doc(values).insert(ignore_permissions=True)

	def mine(self, rows: list[dict]) -> list[dict]:
		"""Only this suite's questions. The site has its own, seeded or added."""
		return [row for row in rows if row["label"].startswith(PREFIX)]


class TestTheGroupReachesBothSurfaces(QuestionGroupTestCase):
	def test_the_form_is_told_which_group_each_question_is_in(self):
		self.ask(f"{PREFIX} Blood group", HEALTH)
		self.ask(f"{PREFIX} Anything we should know", HEALTH)
		self.ask(f"{PREFIX} A question with no group")

		asked = {row["label"]: row["group"] for row in self.mine(questions.asked_on(APPLICATION))}

		self.assertEqual(asked[f"{PREFIX} Blood group"], HEALTH)
		self.assertEqual(asked[f"{PREFIX} Anything we should know"], HEALTH)
		# Ungrouped is an empty string rather than None, so every surface can
		# read it the same way without checking for two kinds of nothing.
		self.assertEqual(asked[f"{PREFIX} A question with no group"], "")

	def test_the_approver_reads_the_group_off_the_answer(self):
		question = self.ask(f"{PREFIX} Blood group", HEALTH)
		application = _draft()

		questions.apply(application, {question.name: "O+"})

		answered = {row["label"]: row for row in questions.answers_of(application)}

		self.assertEqual(answered[f"{PREFIX} Blood group"]["group"], HEALTH)
		self.assertEqual(answered[f"{PREFIX} Blood group"]["value"], "O+")

	def test_groups_in_use_are_reported_in_form_order(self):
		"""What a screen builds its tabs from, and what the builder offers.

		Order is the form's, not an alphabet: the groups come out in the order
		they were first met walking the questions, which is the order somebody
		fills the form in.
		"""
		self.ask(f"{PREFIX} Next of kin name", KIN, sequence=1)
		self.ask(f"{PREFIX} Blood group", HEALTH, sequence=2)
		self.ask(f"{PREFIX} Next of kin phone", KIN, sequence=3)
		self.ask(f"{PREFIX} Ungrouped", sequence=4)

		in_use = [group for group in questions.groups(APPLICATION) if group.startswith(PREFIX)]

		self.assertEqual(in_use, [KIN, HEALTH])

	def test_an_empty_group_is_not_a_group(self):
		"""Ungrouped questions do not produce a group with an empty name."""
		self.ask(f"{PREFIX} Ungrouped one")
		self.ask(f"{PREFIX} Ungrouped two")

		self.assertNotIn("", questions.groups(APPLICATION))


class TestTheGroupIsASnapshot(QuestionGroupTestCase):
	def test_renaming_a_group_does_not_rewrite_what_was_already_asked(self):
		"""The same guarantee the wording carries, extended to the group.

		A society reorganising its form in March must not change what an
		applicant answered in February — including which heading they answered it
		under, because that is part of what they were asked.
		"""
		question = self.ask(f"{PREFIX} Blood group", HEALTH)
		application = _draft()
		questions.apply(application, {question.name: "O+"})

		question.question_group = f"{PREFIX} Medical"
		question.save(ignore_permissions=True)

		answered = {row["label"]: row for row in questions.answers_of(application)}

		self.assertEqual(answered[f"{PREFIX} Blood group"]["group"], HEALTH)
		# And the live question did move, so this is a snapshot rather than a
		# write that failed.
		asked = {row["name"]: row["group"] for row in questions.asked_on(APPLICATION)}
		self.assertEqual(asked[question.name], f"{PREFIX} Medical")

	def test_an_application_answered_before_grouping_existed_still_reads(self):
		"""The migration case: an answer with no group is ordinary, not broken."""
		question = self.ask(f"{PREFIX} An old question")
		application = _draft()
		questions.apply(application, {question.name: "an old answer"})

		answered = {row["label"]: row for row in questions.answers_of(application)}

		self.assertEqual(answered[f"{PREFIX} An old question"]["group"], "")


class TestTheBuilderCanNameOne(QuestionGroupTestCase):
	"""The console's half — what a national society actually touches."""

	def test_a_group_can_be_set_and_changed_through_the_endpoint(self):
		row = api.save_question(
			asked_on=APPLICATION,
			question_label=f"{PREFIX} Blood group",
			field_type="Data",
			question_group=HEALTH,
		)

		self.assertEqual(row["group"], HEALTH)

		moved = api.save_question(
			name=row["name"],
			asked_on=APPLICATION,
			question_label=f"{PREFIX} Blood group",
			field_type="Data",
			question_group=f"  {KIN}  ",
		)

		# Trimmed, because two groups differing by a trailing space would draw
		# two tabs that read identically.
		self.assertEqual(moved["group"], KIN)

	def test_a_question_saved_without_a_group_has_none(self):
		row = api.save_question(
			asked_on=APPLICATION,
			question_label=f"{PREFIX} Ungrouped",
			field_type="Data",
		)

		self.assertEqual(row["group"], "")

	def test_the_builder_offers_the_groups_already_in_use(self):
		"""So nobody retypes "Health information" and gets it subtly wrong."""
		self.ask(f"{PREFIX} Blood group", HEALTH)

		offered = api.targets()["groups"]

		self.assertIn(HEALTH, offered)
		self.assertNotIn("", offered)


def _draft():
	"""A volunteer application in memory, for `apply` to write answers onto.

	Not inserted: `questions.apply` writes onto the document's child table and
	`answers_of` reads it back, neither of which needs the row to exist. Keeping
	it out of the database is what makes this suite about the questions rather
	than about the registration lifecycle.
	"""
	return frappe.new_doc(APPLICATION)
