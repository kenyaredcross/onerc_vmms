# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One piece of work from a programme to somebody's hours, through every seam.

Every suite in this app tests one module against its own rules. This one tests
that the modules **meet**: a programme of work becomes a mission document, which
becomes a deployment, which becomes one person's assignment, which becomes the
tasks they were given and the hours they served — and, on the other branch, that
an advertised role becomes an application that becomes the same kind of work.

It is deliberately shallow at each step and complete across them. What it is for
is the failure no unit suite can see: two modules that each pass their own tests
while disagreeing about the record between them — a deployment that will not take
a terms of reference because a field was renamed, a task that cannot find the
place it inherits, an application that converts into an assignment nothing will
accept.

**Nothing here is mocked and nothing is inserted behind a service's back.** Each
step goes through the same verb a screen would call, so a step that fails here
fails for a coordinator too.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.deployment.services import assignment as assignment_service
from vmmsx.deployment.services import deployment as deployment_service
from vmmsx.deployment.services import project as project_service
from vmmsx.deployment.services import terms as terms_service
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase
from vmmsx.hr.services import application as application_service
from vmmsx.hr.services import openings
from vmmsx.setup import job_applicant_fields, job_opening_fields
from vmmsx.task.services import batch as batch_service
from vmmsx.task.services import states as task_states
from vmmsx.task.services import task as task_service

EXTRA_TEST_RECORD_DEPENDENCIES = []


class JourneyTestCase(DeploymentTestCase):
	def setUp(self):
		super().setUp()

		self.branch = self.society_a["branch"]

	def volunteer(self, handle: str | None = None):
		profile = fixtures.make_profile("Journey", handle or frappe.generate_hash(length=6))
		volunteer = fixtures.make_volunteer(profile, self.branch)

		if not frappe.db.get_value("Red Profile", profile, "email"):
			frappe.db.set_value(
				"Red Profile", profile, "email", f"{frappe.generate_hash(length=8)}@journey.test",
				update_modified=False,
			)

		return volunteer


class TestAProgrammeBecomesWorkSomebodyDid(JourneyTestCase):
	"""Project → terms of reference → deployment → assignment → task → hours."""

	def test_the_whole_chain_holds(self):
		# --- the programme ------------------------------------------------
		project = project_service.create(
			project_name=f"{fixtures.TEST_PREFIX} Flood Response {frappe.generate_hash(length=6)}",
			geo_node=self.branch,
			summary="The branch's response to this season's rains.",
			donor="Netherlands Red Cross",
			funding_status="Committed",
		)

		self.assertTrue(project_service.is_open(project))

		# --- the mission document written under it -------------------------
		terms = terms_service.create(
			tor_name=f"{fixtures.TEST_PREFIX} Reception Centre {frappe.generate_hash(length=6)}",
			project=project.name,
			geo_scope=self.branch,
			purpose="Running a reception centre for displaced households.",
			mission_background="<p>The low-lying wards flood every season.</p>",
			expected_start_date=today(),
			expected_end_date=add_days(today(), 6),
			objectives=[{"objective": "Receive every displaced family safely."}],
			expected_outputs=[{"output": "A daily register of who is at the centre."}],
			stakeholders=[{"designation": "Centre Manager"}],
			itinerary=[{"activity_date": today(), "activity": "Set up the centre"}],
			resources=[{"resource": "Sleeping mat", "quantity": 300, "unit_cost": 12000}],
		)

		# Complete, so it can be frozen; and the total is derived rather than typed.
		self.assertEqual(terms_service.missing_at_submission(terms), [])
		self.assertEqual(terms.resources[0].total_cost, 300 * 12000)

		terms_service.submit(terms.name)
		terms.reload()

		# --- the deployment run under it ------------------------------------
		deployment = deployment_service.create(
			terms_of_reference=terms.name,
			geo_node=self.branch,
			start_date=today(),
			end_date=add_days(today(), 6),
			volunteers_required=2,
			site_name="Kigamboni primary school",
			meeting_point="Branch office car park",
			travel_notes="The last two kilometres are unpaved.",
		)

		self.assertEqual(
			deployment_service.where_dto(deployment)["meeting_point"]["name"],
			"Branch office car park",
		)

		# --- one person's place on it ----------------------------------------
		volunteer = self.volunteer()
		invited = assignment_service.create(
			deployment, volunteer.name, status=assignment_service.STATUS_PENDING
		)
		assignment_service.respond(invited, accepted=True, note="Happy to help.")

		self.assertEqual(invited.status, assignment_service.STATUS_ACCEPTED)
		self.assertEqual(
			deployment_service.status_dto(deployment)["assignment_counts"]["on_deployment"], 1
		)

		# --- the work they were given on it ----------------------------------
		task = task_service.assign(
			volunteer=volunteer.name,
			subject="Run the registration desk",
			description="Register every household arriving at the centre.",
			deployment=deployment.name,
			checklist=[{"item": "Open the register", "is_required": 1}],
		)

		# The task inherits the deployment's place rather than repeating it.
		self.assertEqual(
			task_service.where_dto(task)["work"]["name"], "Kigamboni primary school"
		)

		task_service.accept(task)
		task_service.tick(task, index=1)
		task_service.submit(task, "Desk ran all week.", hours=30)
		task_service.sign_off(task, outcome="Two hundred households registered.")

		self.assertEqual(task.status, task_states.COMPLETED)

		# --- what happened on the day, and closing it out ---------------------
		assignment_service.record_attendance(
			invited, assignment_service.STATUS_PARTICIPATED, hours=30
		)

		# **Reloaded, and the reason is worth writing down.** A deployment's feed
		# is a child table on the deployment, so every roster event — an
		# acceptance, an attendance record — writes the deployment's own row. A
		# caller holding one across those events is holding a version behind, and
		# the next save of it is refused on the timestamp. An endpoint never sees
		# this because it loads the document per request; a script that walks a
		# whole journey in one transaction, like this one, does.
		deployment.reload()

		deployment_service.set_status(deployment, deployment_service.STATUS_COMPLETED)
		deployment_service.close_out(deployment, lessons="Two desks next time.")

		self.assertEqual(deployment.status, deployment_service.STATUS_CLOSED_OUT)
		self.assertEqual(
			assignment_service.counts_for(deployment.name)["attended"], 1
		)

		# --- and the programme still owns all of it ---------------------------
		self.assertEqual(
			frappe.db.get_value("VMMS Terms of Reference", terms.name, "project"), project.name
		)


class TestABatchOfWorkReachesEverybody(JourneyTestCase):
	"""Batch → forty tasks → each one its own conversation."""

	def test_a_batch_generates_work_that_is_then_independent(self):
		volunteers = [self.volunteer(), self.volunteer(), self.volunteer()]
		batch = frappe.get_doc(
			{
				"doctype": "VMMS Task Batch",
				"subject": "Household survey",
				"brief": "Visit every household on your list.",
				"geo_node": self.branch,
				"due_at": f"{add_days(today(), 7)} 17:00:00",
				"volunteers": [{"volunteer": row.name} for row in volunteers],
			}
		).insert()

		report = batch_service.generate(batch)

		self.assertEqual(report["created"], 3)

		# Each task is ordinary from the moment it exists: one person accepting
		# theirs moves nothing else.
		first = frappe.get_doc("VMMS Task", batch.volunteers[0].task)
		task_service.accept(first)

		counts = batch_service.counts(batch)

		self.assertEqual(counts["in_progress"], 1)
		self.assertEqual(counts["not_responded"], 2)

		# And the brief was copied, so tidying the batch changes nothing sent.
		batch.notes = "Chased the ward office."
		batch.save()
		first.reload()

		self.assertEqual(first.description, "Visit every household on your list.")


class TestAnAdvertisedRoleBecomesTheSameKindOfWork(JourneyTestCase):
	"""Opening → application → acceptance → assignment on a real deployment."""

	def setUp(self):
		super().setUp()

		if not openings.is_available():
			self.skipTest("HRMS is not installed on this site")

	def test_an_application_converts_into_a_place_on_a_deployment(self):
		terms = fixtures.make_terms(f"{fixtures.TEST_PREFIX}-tor-{frappe.generate_hash(length=6)}")
		deployment = fixtures.make_deployment(terms.name, self.branch)

		designation = "Journey Test Officer"

		if not frappe.db.exists("Designation", designation):
			frappe.get_doc(
				{"doctype": "Designation", "designation_name": designation}
			).insert(ignore_permissions=True)

		opening = frappe.get_doc(
			{
				"doctype": "Job Opening",
				"job_title": f"Reception Centre Volunteer {frappe.generate_hash(length=6)}",
				"company": fixtures.company(),
				"designation": designation,
				"status": "Open",
				"publish": 1,
				"posted_on": today(),
				job_opening_fields.PURPOSE_FIELD: job_opening_fields.PURPOSE_VOLUNTEER,
				"vmms_geo_node": self.branch,
				"vmms_deployment": deployment.name,
				"screening_questions": [
					{
						"question_id": "Q1",
						"question": "Which ward can you work in?",
						"question_type": "Text",
						"is_required": 1,
					}
				],
			}
		).insert(ignore_permissions=True)

		volunteer = self.volunteer()
		applicant = application_service.apply(
			opening.name, volunteer.name, answers={"Q1": "Kigamboni"}
		)

		self.assertEqual(applicant.get(job_applicant_fields.VOLUNTEER_FIELD), volunteer.name)

		applicant.status = job_applicant_fields.STATUS_ACCEPTED
		applicant.save(ignore_permissions=True)

		answer = application_service.convert(applicant)
		placed = frappe.get_doc(
			assignment_service.ASSIGNMENT_DOCTYPE, answer["deployment_assignment"]
		)

		# The person is on the deployment the opening was about, as a question
		# rather than a placement — and the terms they are being asked to agree to
		# came from the deployment, not from the advertisement.
		self.assertEqual(placed.deployment, deployment.name)
		self.assertEqual(placed.volunteer, volunteer.name)
		self.assertEqual(placed.status, assignment_service.STATUS_PENDING)
		self.assertEqual(placed.terms_of_reference, deployment.terms_of_reference)

		# And converting again changes nothing.
		self.assertTrue(application_service.convert(applicant)["already"])
