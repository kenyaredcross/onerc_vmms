# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""An approval that resolved nobody becomes visible once somebody is finally there.

This suite exists because of a live failure. A society's approvers were placed
at one rung while its workflow resolved at another, so applications outside one
branch resolved nobody and were admitted to nobody at all — not the applicant,
not an approver, not an administrator, because the gate admits the people a
document routed to rather than whoever holds a role.

Granting the role afterwards fixed **authority** immediately: `engine.authorised`
recomputes from Geo Assignment on every call. It fixed the **queue** not at all,
because `my_queue` is built from ToDos written when a stage was entered, and none
had been written. That gap is what `resync_pending()` closes, and the assertion
that matters below is the one that was false in production.

Each test mints its own role and its own user. `base.py` explains why authority
is normally arranged in `setUpClass` — Frappe rolls back once per class, so a
grant inside a test outlives it — and this suite has to grant inside the test,
because the order of events *is* the thing under test: the application must
exist before the approver does. Unique names per test are what make that safe.
"""

import frappe

from vmmsx.approvals.services import assignment, engine, repair
from vmmsx.approvals.tests import fixtures
from vmmsx.approvals.tests.base import ApprovalTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestResyncLooksAtTheRightThings(ApprovalTestCase):
	def test_it_only_considers_states_still_awaiting_a_decision(self):
		"""A decided application must never be put back into somebody's inbox."""
		from vmmsx.approvals import states

		self.assertEqual(set(repair.PENDING), {states.SUBMITTED, states.IN_REVIEW})

		for settled in (states.APPROVED, states.REJECTED, states.WITHDRAWN, states.EXPIRED):
			self.assertNotIn(settled, repair.PENDING)

	def test_a_doctype_no_workflow_governs_reports_nothing(self):
		self.assertEqual(repair.resync_pending(doctype="VMMS Skill"), {})

	def test_it_answers_a_dict_rather_than_raising(self):
		"""It runs from `after_migrate`. A malformed document on one site must not
		fail a deploy for every other thing in the same migrate."""
		self.assertIsInstance(repair.resync_pending(), dict)


class TestAuthorityChangesReachTheQueue(ApprovalTestCase):
	"""The standing fix, and the reason it is not only wired to `after_migrate`.

	A society appoints and moves approvers between deploys, not on them. Wiring
	the re-sync to migrate alone meant the gate was correct the instant a Geo
	Assignment was saved and the queue stayed wrong until somebody happened to
	deploy — the worst shape a permission bug takes, because everything looks
	configured and nothing looks broken.
	"""

	def test_saving_a_geo_assignment_asks_for_a_resync(self):
		"""Wired in `hooks.py`, so appointing somebody rebuilds the queues."""
		assignment_hooks = frappe.get_hooks("doc_events").get("Geo Assignment") or {}

		self.assertEqual(
			assignment_hooks.get("on_update"),
			["vmmsx.approvals.services.repair.on_authority_changed"],
		)
		self.assertEqual(
			assignment_hooks.get("on_trash"),
			["vmmsx.approvals.services.repair.on_authority_changed"],
		)

	def test_granting_a_role_asks_for_one_too(self):
		"""Core reads Geo Assignment and `Has Role` together, so a role granted
		or revoked changes authority exactly as an assignment does."""
		user_hooks = frappe.get_hooks("doc_events").get("User") or {}

		self.assertIn(
			"vmmsx.approvals.services.repair.on_authority_changed",
			user_hooks.get("on_update") or [],
		)

	def test_there_is_a_daily_backstop(self):
		"""Under both hooks, for the ways authority changes without either firing
		— an assignment reaching its own `valid_to`, a restored backup."""
		self.assertIn(
			"vmmsx.approvals.services.repair.resync_pending",
			frappe.get_hooks("scheduler_events").get("daily") or [],
		)

	def test_the_hook_enqueues_rather_than_rebuilding_inline(self):
		"""Saving a Geo Assignment is core's act. It must not slow down, or fail,
		because a queue somewhere needed rebuilding."""
		import inspect

		source = inspect.getsource(repair.on_authority_changed)

		self.assertIn("frappe.enqueue", source)
		self.assertIn("enqueue_after_commit", source)


class TestTheQueueReopens(ApprovalTestCase):
	"""The production failure, reproduced and then repaired."""

	def _routed_to_nobody(self, handle: str):
		"""An application submitted while nobody held its role anywhere.

		Returns (document, role, the region above its anchor). The stage resolves
		nobody and there is nobody above to escalate to, which is exactly the
		state every application outside one branch was in.

		The role is minted per test rather than shared, because a grant made
		inside a test outlives it — see this module's docstring — and it is given
		write on the stand-in explicitly. `ensure_approvable_doctype` grants only
		the fixture's own three roles, and recording a decision saves the governed
		document, so a fresh role without this could resolve as an approver and
		still be refused at the point of deciding.
		"""
		from frappe.permissions import add_permission, update_permission_property

		role = fixtures.make_role(f"{fixtures.TEST_PREFIX} {handle} Approver")

		add_permission(fixtures.APPROVABLE_DOCTYPE, role, 0)
		for right in ("read", "write"):
			update_permission_property(fixtures.APPROVABLE_DOCTYPE, role, 0, right, 1)
		frappe.clear_cache(doctype=fixtures.APPROVABLE_DOCTYPE)

		fixtures.make_workflow([fixtures.stage(1, fixtures.LABEL_BRANCH, role)])

		name = fixtures.make_application(f"{handle} application", self.kenya["kihara"])
		doc = fixtures.load(name)
		engine.submit(doc)

		return fixtures.load(name), role, self.kenya["region"]

	def test_an_application_that_resolved_nobody_appears_once_somebody_holds_the_role(self):
		"""The assertion that was false in production."""
		doc, role, region = self._routed_to_nobody("Reopen")

		self.assertEqual(engine.authorised(doc)["approvers"], [])
		self.assertEqual(assignment.assignees(doc.doctype, doc.name), set())

		approver = fixtures.make_user("reopen-approver", [role])
		fixtures.make_assignment(approver, role, region)

		# Authority is live: the gate admits them with nothing re-run at all.
		self.assertIn(approver, engine.authorised(fixtures.load(doc.name))["approvers"])

		# The queue is not, and that is the bug rather than a detail.
		self.assertEqual(assignment.assignees(doc.doctype, doc.name), set())

		repair.resync_pending(doctype=doc.doctype)

		self.assertIn(approver, assignment.assignees(doc.doctype, doc.name))

	def test_running_it_twice_changes_nothing_the_second_time(self):
		doc, role, region = self._routed_to_nobody("Twice")
		approver = fixtures.make_user("twice-approver", [role])
		fixtures.make_assignment(approver, role, region)

		first = repair.resync_pending(doctype=doc.doctype)
		second = repair.resync_pending(doctype=doc.doctype)

		self.assertTrue(first, "the first run should have repaired something")
		self.assertEqual(second, {}, "the second run should be a no-op")

	def test_it_grants_nobody_anything(self):
		"""A repair that widened authority would be one worth fearing. The
		assignment follows the gate; it never leads it."""
		doc, _role, _region = self._routed_to_nobody("NoGrant")

		repair.resync_pending(doctype=doc.doctype)

		self.assertEqual(engine.authorised(fixtures.load(doc.name))["approvers"], [])
		self.assertEqual(assignment.assignees(doc.doctype, doc.name), set())

	def test_an_application_nobody_can_act_on_keeps_the_assignment_it_had(self):
		"""Clearing it would take the document out of the last approver's inbox to
		replace it with nothing, and `my_queue` re-checks routing before showing
		anything anyway."""
		doc, role, _region = self._routed_to_nobody("Keep")
		stranger = fixtures.make_user("keep-stranger", [role])
		assignment.sync(doc.doctype, doc.name, [stranger])

		repair.resync_pending(doctype=doc.doctype)

		self.assertIn(stranger, assignment.assignees(doc.doctype, doc.name))

	def test_a_decided_application_is_left_alone(self):
		"""Settled is settled: nothing about it belongs in a queue."""
		doc, role, region = self._routed_to_nobody("Decided")
		approver = fixtures.make_user("decided-approver", [role])
		fixtures.make_assignment(approver, role, region)

		repair.resync_pending(doctype=doc.doctype)
		with fixtures.acting_as(approver):
			engine.decide(fixtures.load(doc.name), "Approved")

		after = repair.resync_pending(doctype=doc.doctype)

		self.assertEqual(after, {})
		self.assertEqual(assignment.assignees(doc.doctype, doc.name), set())
