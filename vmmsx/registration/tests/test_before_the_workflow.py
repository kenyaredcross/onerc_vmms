# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Registering on a site whose society has not configured its approvals yet.

The engine's own tests prove the rule against a stand-in doctype. This proves it
where it actually reaches a person: the two public registration forms, on a site
installed this morning, whose administrator has not yet written a single
`VMMS Approval Workflow`.

**What it would otherwise do.** `engine.submit` used to read the workflow with
`config.for_doctype`, which throws, and the throw happened inside `on_update` on
the save that created the application — so the *registration itself* failed, and
the sentence a volunteer was shown was "No approval workflow is configured for
VMMS Volunteer Application. Create a VMMS Approval Workflow record for it." A
member of the public was being handed a configuration task, on a public form, in
the app's own words.

Now they are accepted and held, and the day somebody writes the workflow every
one of them lands in the right queue.
"""

import frappe

from vmmsx.approvals import states
from vmmsx.approvals.services import contract, repair
from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

WORKFLOW_DOCTYPE = "VMMS Approval Workflow"


class TestRegisteringBeforeTheWorkflowExists(RegistrationTestCase):
	def setUp(self):
		super().setUp()

		# The society this suite builds configures its workflows. This one takes
		# the two registration ones away again: the state a site is in between
		# `bench install-app` and whenever its administrator reaches the
		# approvals screen. Only those two — a workflow this suite did not write
		# is not this suite's to delete.
		for governed in (fixtures.APPLICATION_DOCTYPE, fixtures.MEMBERSHIP_DOCTYPE):
			existing = frappe.db.get_value(WORKFLOW_DOCTYPE, {"workflow_for": governed}, "name")

			if existing:
				frappe.delete_doc(WORKFLOW_DOCTYPE, existing, force=True)

	def configure(self):
		levels = [self.society["levels"]["county"], self.society["levels"]["branch"]]

		fixtures.make_workflows(levels)

	def state_of(self, doctype: str, name: str) -> str:
		return frappe.db.get_value(doctype, name, contract.STATE_FIELD)

	def queue_of(self, user: str, doctype: str) -> set[str]:
		return set(
			frappe.get_all(
				"ToDo",
				filters={
					"allocated_to": user,
					"reference_type": doctype,
					"status": ("in", ("Open", "Overdue")),
				},
				pluck="reference_name",
			)
		)

	def draft_values(self) -> dict:
		return {
			"geo_node": self.branch(),
			"first_name": "Amina",
			"last_name": "Otieno",
			"date_of_birth": fixtures.DEFAULT_DATE_OF_BIRTH,
			"country_of_citizenship": fixtures.test_country(),
			"residency_type": "Local",
			"home_geo_node": self.branch(),
			"id_type": fixtures.make_identification_type(),
			"id_number": f"{fixtures.TEST_PREFIX}-{frappe.generate_hash(length=8)}",
			"disability_status": "Prefer not to say",
			"declarations_accepted": fixtures.required_declarations(),
			"emergency_contacts": fixtures.emergency_contact(),
		}

	# --- the volunteer form ------------------------------------------------

	def test_a_volunteer_can_still_apply(self):
		_, application = self.register_as_volunteer("unset.volunteer")

		self.assertEqual(self.state_of(application.doctype, application.name), states.SUBMITTED)

	def test_their_application_is_not_approved_by_the_gap(self):
		"""Nobody becomes a volunteer because nobody configured who signs them off."""
		_, application = self.register_as_volunteer("unset.notapproved")

		self.assertNotEqual(self.state_of(application.doctype, application.name), states.APPROVED)
		self.assertFalse(frappe.db.get_value(application.doctype, application.name, "volunteer"))

	def test_writing_the_workflow_puts_it_in_the_approver_s_queue(self):
		_, application = self.register_as_volunteer("unset.routed")

		self.configure()
		repair.resync_pending(fixtures.APPLICATION_DOCTYPE)

		self.assertEqual(self.state_of(application.doctype, application.name), states.IN_REVIEW)
		self.assertIn(application.name, self.queue_of(self.approver, application.doctype))

	def test_and_it_can_then_be_approved_through_the_ordinary_gate(self):
		_, application = self.register_as_volunteer("unset.approved")

		self.configure()
		repair.resync_pending(fixtures.APPLICATION_DOCTYPE)
		status = self.approve(application.doctype, application.name)

		self.assertEqual(status["state"], states.APPROVED)
		self.assertTrue(frappe.db.get_value(application.doctype, application.name, "volunteer"))

	# --- the membership form -----------------------------------------------

	def test_a_member_can_still_apply(self):
		_, membership = self.register_as_member("unset.member", fixtures.TYPE_ROUTED)

		self.assertEqual(self.state_of(membership.doctype, membership.name), states.SUBMITTED)

	def test_their_membership_is_not_activated_by_the_gap(self):
		_, membership = self.register_as_member("unset.notactive", fixtures.TYPE_ROUTED)

		status = frappe.db.get_value(membership.doctype, membership.name, "membership_status")

		self.assertNotEqual(status, "Active")

	def test_writing_the_workflow_routes_the_membership_too(self):
		_, membership = self.register_as_member("unset.memberrouted", fixtures.TYPE_ROUTED)

		self.configure()
		repair.resync_pending(fixtures.MEMBERSHIP_DOCTYPE)

		self.assertEqual(self.state_of(membership.doctype, membership.name), states.IN_REVIEW)
		self.assertIn(membership.name, self.queue_of(self.approver, membership.doctype))

	# --- the draft path, which is how the wizard actually files ------------

	def test_a_saved_draft_can_still_be_submitted(self):
		"""The Join wizard saves first and submits second. Both halves, ungoverned."""
		from vmmsx.api import registration as registration_api

		user = fixtures.website_account("unset.draft")

		with fixtures.acting_as(user):
			draft = registration_api.save_my_volunteer_draft(**self.draft_values())
			status = registration_api.submit_my_registration("volunteer")

		self.assertEqual(draft["state"], states.DRAFT)
		self.assertEqual(status["approval_state"], states.SUBMITTED)

	# --- what the applicant is told ----------------------------------------

	def test_the_portal_shows_it_as_an_open_registration(self):
		"""Not a draft they never sent, and not an error. Sent, and waiting."""
		from vmmsx.api import registration as registration_api

		user, application = self.register_as_volunteer("unset.portal")

		with fixtures.acting_as(user):
			open_now = registration_api.my_open_registrations()

		self.assertEqual(open_now["volunteer"]["name"], application.name)
		self.assertEqual(open_now["volunteer"]["state"], states.SUBMITTED)
		self.assertFalse(open_now["volunteer"]["reviewed"])
