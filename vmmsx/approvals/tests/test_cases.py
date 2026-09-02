# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The three bands a queue screen navigates, and why two of them are not queues.

`my_queue` answers one question — what is routed to *this user* right now — and
a queue screen asks three. The other two cannot be answered from ToDo rows at
all, and that is the point of `my_cases`:

- an application **sent back for corrections** has no approver. The engine
  returns it to Draft and clears the stage, so nobody holds an assignment on it
  and it is in nobody's queue. Reading it off ToDo would find nothing.
- a **closed** application has finished having an approver. Its assignments are
  closed with it.

So both bands are read off the governed doctype itself, through
`frappe.get_list` — which runs core's permission query condition, so the caller
sees their own areas and no further. These tests hold the two distinctions the bands are built on: a Draft that was
*returned* against a Draft that was never submitted, and the four terminal
states against the three open ones. The scope itself is proved against a real
scopeable doctype elsewhere — see the note at the foot of this file.
"""

import frappe

from vmmsx.api import approvals
from vmmsx.approvals import states
from vmmsx.approvals.services import engine
from vmmsx.approvals.tests import fixtures
from vmmsx.approvals.tests.base import ApprovalTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestMyCases(ApprovalTestCase):
	"""One stage, one approver, and every band read through the API."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.county = fixtures.make_user("cases_county", [fixtures.APPROVER_ROLE])
		fixtures.make_assignment(cls.county, fixtures.APPROVER_ROLE, cls.kenya["kiambu"])

		cls.workflow = fixtures.make_workflow(
			[fixtures.stage(1, fixtures.LABEL_COUNTY, fixtures.APPROVER_ROLE)]
		)

	# --- helpers ----------------------------------------------------------

	def names_in(self, group: str) -> set[str]:
		answer = approvals.my_cases(fixtures.APPROVABLE_DOCTYPE, group)

		self.assertEqual(answer["group"], group)
		self.assertEqual(answer["count"], len(answer["cases"]))

		return {case["name"] for case in answer["cases"]}

	def sent_back(self, title: str) -> str:
		"""An application the approver returned to its applicant."""
		application = self.application(title, self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.county):
			engine.decide(
				self.reload(application), states.DECISION_MORE_INFO, reason="Identification missing"
			)

		return application

	# --- the bands --------------------------------------------------------

	def test_the_actionable_band_is_exactly_my_queue(self):
		application = self.application("routed", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.county):
			cases = self.names_in(approvals.CASE_ACTIONABLE)
			queue = {row["name"] for row in approvals.my_queue(fixtures.APPROVABLE_DOCTYPE)}

		self.assertIn(application, cases)
		# Two answers to one question is how two answers come to disagree.
		self.assertEqual(cases, queue)

	def test_a_returned_application_is_in_changes_and_not_in_the_queue(self):
		application = self.sent_back("returned")

		self.assertEqual(self.state(application), states.DRAFT)

		with fixtures.acting_as(self.county):
			self.assertIn(application, self.names_in(approvals.CASE_CHANGES))
			# It has no approver at all now, so `my_queue` is the wrong instrument.
			self.assertEqual(approvals.my_queue(fixtures.APPROVABLE_DOCTYPE), [])

	def test_a_draft_nobody_ever_submitted_is_not_a_correction(self):
		never = self.application("never submitted", self.kenya["kihara"])
		returned = self.sent_back("returned twice")

		with fixtures.acting_as(self.county):
			changes = self.names_in(approvals.CASE_CHANGES)

		# Both are Draft. Only one of them is somebody waiting on the applicant,
		# and the decision history is the only thing that tells them apart.
		self.assertEqual(self.state(never), states.DRAFT)
		self.assertIn(returned, changes)
		self.assertNotIn(never, changes)

	def test_the_closed_band_is_the_four_terminal_states(self):
		approved = self.application("approved", self.kenya["kihara"])
		engine.submit(self.reload(approved))

		with fixtures.acting_as(self.county):
			engine.decide(self.reload(approved), states.DECISION_APPROVED)

		rejected = self.application("rejected", self.kenya["kihara"])
		engine.submit(self.reload(rejected))

		with fixtures.acting_as(self.county):
			engine.decide(self.reload(rejected), states.DECISION_REJECTED, reason="Not eligible")

		open_one = self.application("still open", self.kenya["kihara"])
		engine.submit(self.reload(open_one))

		with fixtures.acting_as(self.county):
			closed = self.names_in(approvals.CASE_CLOSED)

		self.assertEqual(self.state(approved), states.APPROVED)
		self.assertEqual(self.state(rejected), states.REJECTED)
		self.assertIn(approved, closed)
		self.assertIn(rejected, closed)
		self.assertNotIn(open_one, closed)

	def test_every_case_carries_the_engines_own_status_dto(self):
		application = self.application("dto", self.kenya["kihara"])
		engine.submit(self.reload(application))

		with fixtures.acting_as(self.county):
			engine.decide(self.reload(application), states.DECISION_APPROVED)
			case = approvals.my_cases(fixtures.APPROVABLE_DOCTYPE, approvals.CASE_CLOSED)["cases"][0]

		# The same shape the queue screen and the review screen already read, so
		# a history row and a live row cannot describe an application differently.
		self.assertEqual(case["state"], states.APPROVED)
		self.assertTrue(case["is_terminal"])
		self.assertFalse(case["is_open"])
		self.assertEqual(case["decisions"][-1]["decision"], states.DECISION_APPROVED)
		# Never a Document: an explicit DTO, keys reviewed one by one.
		self.assertNotIn("doctype_fields", case)

	# --- refusals ---------------------------------------------------------

	def test_an_ungoverned_doctype_is_refused_before_anything_is_read(self):
		with self.assertRaises(frappe.ValidationError):
			approvals.my_cases("User", approvals.CASE_CLOSED)

	def test_an_unknown_band_is_refused_rather_than_guessed(self):
		with self.assertRaises(frappe.ValidationError):
			approvals.my_cases(fixtures.APPROVABLE_DOCTYPE, "everything")

	def test_the_page_size_can_narrow_but_never_exceed_the_ceiling(self):
		for index in range(3):
			application = self.application(f"closed {index}", self.kenya["kihara"])
			engine.submit(self.reload(application))

			with fixtures.acting_as(self.county):
				engine.decide(self.reload(application), states.DECISION_APPROVED)

		with fixtures.acting_as(self.county):
			asked = approvals.my_cases(fixtures.APPROVABLE_DOCTYPE, approvals.CASE_CLOSED, limit=2)
			huge = approvals.my_cases(
				fixtures.APPROVABLE_DOCTYPE, approvals.CASE_CLOSED, limit=10_000
			)

		self.assertEqual(len(asked["cases"]), 2)
		# A caller cannot ask the server to read the whole table.
		self.assertLessEqual(len(huge["cases"]), approvals._CASE_CEILING)


# Scope itself is proved where a *scopeable* governed doctype exists: the
# stand-in doctype these tests use is registered with the approval engine but
# not with core's access registry, so `frappe.get_list` has no condition to
# apply to it and a scoping assertion here would pass for the wrong reason. See
# `vmmsx/member/tests/test_register_summary.py`, which asks `my_cases` the same
# question about `VMMS Membership` — governed *and* scoped — with core's
# enforcement unmocked.
