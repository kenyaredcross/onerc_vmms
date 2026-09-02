# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Returned for correction, corrected, resubmitted — and all of it on the record.

**No status value was added for "Returned for Correction", and these tests are
the argument for that.** The engine already models it: a `More info requested`
decision records a row with a mandatory reason and puts the application back to
`Draft`. What distinguishes a returned draft from one nobody has ever sent is
the presence of that decision row, which is exactly what
`api/registration._has_been_reviewed` reads. An eighth state would have been a
second answer to a question the audit trail already answers.

The second half of this file is about `Version`. Change tracking is on, but a
write that goes through `frappe.db.set_value` creates no version at all — so
"track_changes is ticked" is not the same claim as "the changes are tracked",
and the tests drive real portal calls rather than asserting on the flag.
"""

from contextlib import contextmanager
from typing import ClassVar

import frappe

from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class CorrectionTestCase(RegistrationTestCase):
	def return_for_correction(self, application, reason: str = "We need a clearer ID copy"):
		"""Send it back, through the real gate, as the person it routed to."""
		from vmmsx.api import approvals as approvals_api

		with fixtures.acting_as(self.approver):
			return approvals_api.decide(
				doctype=fixtures.APPLICATION_DOCTYPE,
				name=application.name,
				decision="More info requested",
				reason=reason,
			)


class TestReturningForCorrection(CorrectionTestCase):
	def test_it_goes_back_to_draft_rather_than_to_a_new_state(self):
		_, application = self.register_as_volunteer("returned.applicant")

		self.return_for_correction(application)
		application.reload()

		self.assertEqual(application.approval_state, "Draft")
		self.assertFalse(application.approval_stage)

	def test_a_reason_is_compulsory(self):
		"""The applicant is entitled to know what to fix."""
		from vmmsx.api import approvals as approvals_api

		_, application = self.register_as_volunteer("returned.without.reason")

		with fixtures.acting_as(self.approver), self.assertRaises(frappe.ValidationError):
			approvals_api.decide(
				doctype=fixtures.APPLICATION_DOCTYPE,
				name=application.name,
				decision="More info requested",
				reason=None,
			)

	def test_the_applicant_is_told_why_in_their_own_portal(self):
		"""Not only in the email. Somebody who deleted it still has a way back."""
		from vmmsx.api import registration as registration_api

		user, application = self.register_as_volunteer("reads.the.reason")

		self.return_for_correction(application, reason="Your ID copy is unreadable")

		with fixtures.acting_as(user):
			open_now = registration_api.my_open_registrations()["volunteer"]

		self.assertEqual(open_now["state"], "Draft")
		self.assertEqual(open_now["reason"], "Your ID copy is unreadable")
		self.assertTrue(open_now["reviewed"])

	def test_a_never_submitted_draft_is_not_confused_with_a_returned_one(self):
		"""Both are `Draft`, and the dashboard used to tell somebody who had not
		finished their own form that their branch had asked for something."""
		from vmmsx.api import registration as registration_api

		user = fixtures.website_account("never.submitted")

		with fixtures.acting_as(user):
			registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				declarations_accepted=fixtures.required_declarations(),
			)
			open_now = registration_api.my_open_registrations()["volunteer"]

		self.assertEqual(open_now["state"], "Draft")
		self.assertFalse(open_now["reviewed"])


class TestCorrectingAndResubmitting(CorrectionTestCase):
	def test_the_applicant_can_edit_and_send_it_back(self):
		from vmmsx.api import registration as registration_api

		user, application = self.register_as_volunteer("corrects.and.resubmits")

		self.return_for_correction(application)

		with fixtures.acting_as(user):
			registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				prior_experience="Added the detail the branch asked for",
				declarations_accepted=fixtures.required_declarations(),
				emergency_contacts=fixtures.emergency_contact(),
			)
			registration_api.submit_my_registration("volunteer")

		application.reload()

		self.assertEqual(application.approval_state, "In Review")
		self.assertEqual(application.prior_experience, "Added the detail the branch asked for")

	def test_the_history_of_both_rounds_survives(self):
		"""The correction request is not erased by the resubmission that answers
		it. Two decisions on one application is the record of what happened."""
		user, application = self.register_as_volunteer("keeps.its.history")

		self.return_for_correction(application, reason="First round: ID unreadable")

		from vmmsx.api import registration as registration_api

		with fixtures.acting_as(user):
			registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				declarations_accepted=fixtures.required_declarations(),
				emergency_contacts=fixtures.emergency_contact(),
			)
			registration_api.submit_my_registration("volunteer")

		self.approve(fixtures.APPLICATION_DOCTYPE, application.name, reason="Second round: fine")
		application.reload()

		decisions = [(row.decision, row.reason) for row in application.approval_decisions]

		self.assertEqual(len(decisions), 2)
		self.assertEqual(decisions[0], ("More info requested", "First round: ID unreadable"))
		self.assertEqual(decisions[1], ("Approved", "Second round: fine"))
		self.assertEqual(application.approval_state, "Approved")

	def test_a_returned_application_is_reviewed_from_the_first_stage_again(self):
		"""What earlier stages endorsed is not what is being resubmitted."""
		user, application = self.register_as_volunteer("restarts.review")

		self.return_for_correction(application)

		from vmmsx.api import registration as registration_api

		with fixtures.acting_as(user):
			registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				declarations_accepted=fixtures.required_declarations(),
				emergency_contacts=fixtures.emergency_contact(),
			)
			result = registration_api.submit_my_registration("volunteer")

		self.assertEqual(result["approval_state"], "In Review")

		queued = frappe.get_all(
			"ToDo",
			filters={
				"reference_type": fixtures.APPLICATION_DOCTYPE,
				"reference_name": application.name,
				"status": ("in", ("Open", "Overdue")),
			},
			pluck="allocated_to",
		)

		self.assertEqual(queued, [self.approver])

	def test_an_application_under_review_cannot_be_edited(self):
		"""Correcting is something an approver opens the door to, not something
		an applicant can do whenever they like."""
		from vmmsx.api import registration as registration_api

		user, _ = self.register_as_volunteer("cannot.edit.under.review")

		with fixtures.acting_as(user), self.assertRaises(frappe.ValidationError) as refusal:
			registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				declarations_accepted=fixtures.required_declarations(),
			)

		self.assertIn("under review", str(refusal.exception).lower())


class TestTheSameApproverMayDecideTheNextRound(CorrectionTestCase):
	"""The defect this suite found, kept found.

	A stage is a *row in a workflow*, not an instance of one, so a resubmitted
	application re-enters the same stage it was returned from. The engine
	refused a second decision at a stage the user had already decided —
	correctly, for one round — and that made the approver who asked for more
	information the one person who could not then approve the answer. On a
	single-stage workflow, which is what most societies run, that is everybody.

	The fix is in `contract.decisions_at`: a decision counts against the round
	the stage was last entered in. Both halves are asserted here, because a fix
	that let somebody decide twice in one round would pass the first test alone.
	"""

	def test_the_approver_who_sent_it_back_can_approve_the_resubmission(self):
		from vmmsx.api import registration as registration_api

		user, application = self.register_as_volunteer("second.round")

		self.return_for_correction(application, reason="Needs a clearer ID")

		with fixtures.acting_as(user):
			registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				declarations_accepted=fixtures.required_declarations(),
				emergency_contacts=fixtures.emergency_contact(),
			)
			registration_api.submit_my_registration("volunteer")

		self.approve(fixtures.APPLICATION_DOCTYPE, application.name, reason="Better")
		application.reload()

		self.assertEqual(application.approval_state, "Approved")

	def test_deciding_twice_in_one_round_is_still_refused(self):
		"""The guard the fix had to keep. Changing your mind is not a rewrite."""
		from vmmsx.api import approvals as approvals_api

		_, application = self.register_as_volunteer("decides.twice")

		self.approve(fixtures.APPLICATION_DOCTYPE, application.name, reason="Yes")

		with fixtures.acting_as(self.approver), self.assertRaises(frappe.ValidationError):
			approvals_api.decide(
				doctype=fixtures.APPLICATION_DOCTYPE,
				name=application.name,
				decision="Rejected",
				reason="Changed my mind",
			)

	def test_the_earlier_decision_is_still_in_the_trail(self):
		"""Scoped out of the *rule*, never out of the record."""
		from vmmsx.api import registration as registration_api

		user, application = self.register_as_volunteer("trail.intact")

		self.return_for_correction(application, reason="Round one")

		with fixtures.acting_as(user):
			registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				declarations_accepted=fixtures.required_declarations(),
				emergency_contacts=fixtures.emergency_contact(),
			)
			registration_api.submit_my_registration("volunteer")

		self.approve(fixtures.APPLICATION_DOCTYPE, application.name, reason="Round two")
		application.reload()

		self.assertEqual(
			[(row.decision, row.reason) for row in application.approval_decisions],
			[("More info requested", "Round one"), ("Approved", "Round two")],
		)


class TestTheAuditTrail(RegistrationTestCase):
	"""That a change leaves a `Version` behind — actually asked, not assumed.

	**Frappe suppresses versioning in tests**, and that is the whole difficulty
	here. `Document._save` sets `flags.ignore_version = frappe.in_test`
	(`frappe/model/document.py:824`), so a suite that counts `Version` rows
	counts zero however correct the code is — and a test asserting "zero equals
	zero" would sit here looking like coverage of the one thing Phase 0 found
	broken.

	So `frappe.in_test` is lowered around the call under test and restored
	afterwards. That switches off exactly one thing — Frappe's own test-mode
	shortcut — and leaves the endpoint, the permissions, the elevation and the
	document's own hooks running as they do in production.

	**And the mechanism is asserted separately**, in `TestNothingWritesAround
	TheDocument` below, because the failure this guards against is not "the
	framework stopped making versions". It is somebody reaching for
	`frappe.db.set_value` in a write path, which makes no version at all and
	looks entirely reasonable in review.
	"""

	def versions_of(self, doctype: str, name: str) -> int:
		return frappe.db.count("Version", {"ref_doctype": doctype, "docname": name})

	@contextmanager
	def versioning_on(self):
		"""Undo Frappe's test-mode suppression for the duration of one call."""
		previous = frappe.in_test
		frappe.in_test = False

		try:
			yield
		finally:
			frappe.in_test = previous

	def test_the_application_tracks_changes(self):
		self.assertTrue(frappe.get_meta(fixtures.APPLICATION_DOCTYPE).track_changes)

	def test_the_profile_tracks_changes(self):
		"""Red Profile is core's, and the trail depends on it staying on."""
		self.assertTrue(frappe.get_meta(fixtures.PROFILE_DOCTYPE).track_changes)

	def test_a_portal_edit_of_a_draft_leaves_a_version(self):
		from vmmsx.api import registration as registration_api

		user = fixtures.website_account("edits.their.draft")

		with fixtures.acting_as(user):
			draft = registration_api.save_my_volunteer_draft(
				geo_node=self.branch(),
				declarations_accepted=fixtures.required_declarations(),
			)

			before = self.versions_of(fixtures.APPLICATION_DOCTYPE, draft["name"])

			with self.versioning_on():
				registration_api.save_my_volunteer_draft(
					geo_node=self.branch(),
					prior_experience="Something new to record",
					declarations_accepted=fixtures.required_declarations(),
				)

		after = self.versions_of(fixtures.APPLICATION_DOCTYPE, draft["name"])

		self.assertGreater(after, before)

	def test_correcting_a_profile_from_the_portal_leaves_a_version(self):
		"""`update_my_profile` writes through the document, not around it.

		The elevation it runs inside changes who is acting and nothing about how
		the write is performed — which is exactly what this asserts.
		"""
		from vmmsx.api import registration as registration_api

		user, _ = self.register_as_volunteer("corrects.their.profile")
		profile = self.profile_of(user)

		before = self.versions_of(fixtures.PROFILE_DOCTYPE, profile)

		with fixtures.acting_as(user), self.versioning_on():
			registration_api.update_my_profile(phone="+254700009999")

		after = self.versions_of(fixtures.PROFILE_DOCTYPE, profile)

		self.assertGreater(after, before)
		self.assertEqual(frappe.db.get_value(fixtures.PROFILE_DOCTYPE, profile, "phone"), "+254700009999")

	def test_the_decision_itself_is_on_the_document(self):
		"""The approval trail is the decisions table rather than a Version diff:
		who acted, at which stage, when, and why."""
		_, application = self.register_as_volunteer("decision.recorded")

		self.approve(fixtures.APPLICATION_DOCTYPE, application.name, reason="Everything checks out")
		application.reload()

		row = application.approval_decisions[-1]

		self.assertEqual(row.approver, self.approver)
		self.assertEqual(row.decision, "Approved")
		self.assertEqual(row.reason, "Everything checks out")
		self.assertTrue(row.decided_on)
		self.assertTrue(row.stage_label)


class TestNothingWritesAroundTheDocument(RegistrationTestCase):
	"""The registration write paths save documents; they do not poke columns.

	**This is the test that would actually have caught the Phase 0 finding.**
	`frappe.db.set_value` writes a column and creates no `Version` at all, so a
	line of it in a registration path silently takes a change out of the audit
	trail — and reads perfectly well in review. An AST walk is how this codebase
	already asserts its architectural rules (`test_no_stage_branching`,
	`test_delegation`), so it is how this one is asserted too.

	Three uses are permitted and named, each because the alternative is worse
	than the gap it leaves:

	- `intake._adopt` / `intake.place`, binding a login or a home node onto a
	  profile the caller may not otherwise touch.
	- `intake._enrich`, filling in blanks core does not have.
	- repointing a child row at a file that has just been moved, in
	  `questions.anchor_files` and `api/registration.secure_row_files` — the
	  `File` itself was saved properly and carries the version; this only
	  follows it.
	- `api/registration._secure_proof`, which is the same act on a parent field
	  rather than a child row: `evidence.secure` moved the membership-proof
	  attachment and the URL it came back with has to replace the one that was
	  given. Saving the document instead would be a second save of a record the
	  caller is about to submit, and it was a `TimestampMismatchError` on every
	  single submission until the reload beneath it was added. The `File` carries
	  the version; this only follows it.

	Anything else is a finding. The point is not that the three are ideal; it is
	that adding a fourth has to be a decision somebody makes on purpose.
	"""

	#: file:line of every `frappe.db.set_value` this app has justified in a
	#: registration write path. A new one fails this test until it is argued for
	#: here.
	PERMITTED: ClassVar[set[tuple[str, str]]] = {
		("registration/services/intake.py", "_adopt"),
		("registration/services/intake.py", "_enrich"),
		("registration/services/intake.py", "place"),
		("registration/services/questions.py", "anchor_files"),
		("api/registration.py", "secure_row_files"),
		("api/registration.py", "_secure_proof"),
	}

	WATCHED = (
		"registration/services/intake.py",
		"registration/services/questions.py",
		"registration/services/declarations.py",
		"registration/services/evidence.py",
		"api/registration.py",
	)

	def test_no_unjustified_column_write_in_a_registration_path(self):
		import ast
		from pathlib import Path

		root = Path(frappe.get_app_path("vmmsx"))
		found = []

		for relative in self.WATCHED:
			tree = ast.parse((root / relative).read_text(), filename=relative)

			for function in ast.walk(tree):
				if not isinstance(function, ast.FunctionDef):
					continue

				for node in ast.walk(function):
					if not isinstance(node, ast.Call):
						continue

					if _is_db_set_value(node) and (relative, function.name) not in self.PERMITTED:
						found.append(f"{relative}:{node.lineno} in {function.name}()")

		self.assertEqual(
			found,
			[],
			"a column write leaves no Version; save the document or justify it in PERMITTED",
		)


def _is_db_set_value(node) -> bool:
	"""`frappe.db.set_value(...)` or `frappe.db.set_single_value(...)`."""
	import ast

	target = node.func

	if not isinstance(target, ast.Attribute):
		return False

	return target.attr in ("set_value", "set_single_value")
