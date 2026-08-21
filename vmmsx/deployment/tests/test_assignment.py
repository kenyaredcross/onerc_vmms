# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The bulk act, the headcount, and the account a deployment keeps of itself.

`test_invitation.py` covers asking one person and their answering. This covers
the three things that only exist because the roster became a register of
documents:

* **`deploy()`** — one call, a savepoint per person, and a report saying which
  ones did not take and why. A bulk action that rolled the whole batch back for
  one bad row would make a coordinator find it by bisection.
* **The headcount cap** — with the row lock that stops two coordinators taking
  the same last place.
* **The feed** — a deployment's own account of itself, merged at read time with
  the task reports written against it.
"""

import frappe

from vmmsx.api import deployment as api
from vmmsx.deployment.services import assignment, feed
from vmmsx.deployment.services import deployment as deployment_service
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase


class AssignmentTestCase(DeploymentTestCase):
	def setUp(self):
		super().setUp()

		self.terms = fixtures.make_terms()
		self.branch = self.society_a["branch"]

	def volunteers(self, count: int) -> list[str]:
		return [
			fixtures.make_volunteer(fixtures.make_profile("Vol", f"Number{n}"), self.branch).name
			for n in range(count)
		]

	def deployment(self, **overrides):
		return fixtures.make_deployment(self.terms.name, self.branch, **overrides)


class TestTheBulkAct(AssignmentTestCase):
	def test_one_call_raises_one_assignment_each(self):
		people = self.volunteers(3)
		deployment = self.deployment()

		outcome = assignment.deploy(deployment, people)

		self.assertEqual(outcome["raised"], 3)
		self.assertEqual(outcome["refused"], 0)
		self.assertEqual(len(assignment.roster_of(deployment.name)), 3)

	def test_the_report_names_who_did_not_take_and_why(self):
		"""The whole point of the shape: a coordinator sees which ones failed.

		Rolling the batch back for one bad row would make them find it by
		bisection, and dropping it silently would be worse still.
		"""
		people = self.volunteers(2)
		deployment = self.deployment()

		assignment.create(deployment, people[0], status=assignment.STATUS_ASSIGNED)
		outcome = assignment.deploy(deployment, people, status=assignment.STATUS_ASSIGNED)

		self.assertEqual(outcome["raised"], 1)
		self.assertEqual(outcome["refused"], 1)
		self.assertEqual(outcome["failure"][0]["volunteer"], people[0])
		self.assertIn("already", outcome["failure"][0]["reason"].lower())

	def test_a_refusal_does_not_roll_back_the_others(self):
		people = self.volunteers(3)
		deployment = self.deployment()
		assignment.create(deployment, people[1], status=assignment.STATUS_ASSIGNED)

		assignment.deploy(deployment, people, status=assignment.STATUS_ASSIGNED)

		self.assertEqual(len(assignment.roster_of(deployment.name)), 3)

	def test_the_reason_is_a_sentence_not_markup(self):
		"""`frappe.throw` bolds names with HTML, which is right on a desk form and
		wrong in a list a React screen renders as text."""
		people = self.volunteers(1)
		deployment = self.deployment()
		assignment.create(deployment, people[0], status=assignment.STATUS_ASSIGNED)

		outcome = assignment.deploy(deployment, people)

		self.assertNotIn("<", outcome["failure"][0]["reason"])

	def test_the_report_carries_names_not_only_docnames(self):
		people = self.volunteers(1)
		deployment = self.deployment()

		outcome = assignment.deploy(deployment, people)

		self.assertTrue(outcome["success"][0]["full_name"])
		self.assertNotEqual(outcome["success"][0]["full_name"], people[0])

	def test_asking_and_placing_stay_two_verbs(self):
		"""Bulk must not collapse the distinction the app draws everywhere else."""
		people = self.volunteers(2)
		asked = self.deployment()
		placed = self.deployment()

		assignment.deploy(asked, people, status=assignment.STATUS_PENDING)
		assignment.deploy(placed, people, status=assignment.STATUS_ASSIGNED)

		self.assertEqual(assignment.counts_for(asked.name)["on_deployment"], 0)
		self.assertEqual(assignment.counts_for(placed.name)["on_deployment"], 2)

	def test_through_the_endpoint_with_a_json_list(self):
		"""Frappe hands a whitelisted method either a real list or the JSON it was sent."""
		people = self.volunteers(2)
		deployment = self.deployment()

		outcome = api.assign_volunteers(deployment.name, volunteers=frappe.as_json(people), ask=0)

		self.assertEqual(outcome["raised"], 2)

	def test_a_null_in_the_payload_is_not_a_failure_row(self):
		deployment = self.deployment()

		outcome = api.assign_volunteers(deployment.name, volunteers=frappe.as_json([None, ""]))

		self.assertEqual(outcome["requested"], 0)
		self.assertEqual(outcome["failure"], [])


class TestTheHeadcount(AssignmentTestCase):
	def test_placing_past_the_headcount_is_refused(self):
		people = self.volunteers(3)
		deployment = self.deployment(volunteers_required=2)

		outcome = assignment.deploy(deployment, people, status=assignment.STATUS_ASSIGNED)

		self.assertEqual(outcome["raised"], 2)
		self.assertEqual(outcome["refused"], 1)
		self.assertIn("already on it", outcome["failure"][0]["reason"].lower())

	def test_a_deployment_that_has_not_said_how_many_is_never_full(self):
		people = self.volunteers(4)
		deployment = self.deployment()

		outcome = assignment.deploy(deployment, people, status=assignment.STATUS_ASSIGNED)

		self.assertEqual(outcome["raised"], 4)

	def test_pending_questions_hold_no_place(self):
		"""Asking twenty to fill six is how a coordinator fills six."""
		people = self.volunteers(4)
		deployment = self.deployment(volunteers_required=1)

		outcome = assignment.deploy(deployment, people, status=assignment.STATUS_PENDING)

		self.assertEqual(outcome["raised"], 4)
		self.assertEqual(assignment.counts_for(deployment.name)["on_deployment"], 0)

	def test_places_left_is_reported_on_the_deployment(self):
		from vmmsx.deployment.services import deployment as deployment_service

		people = self.volunteers(1)
		deployment = self.deployment(volunteers_required=3)
		assignment.deploy(deployment, people, status=assignment.STATUS_ASSIGNED)

		row = deployment_service.status_dto(frappe.get_doc(deployment.doctype, deployment.name))

		self.assertEqual(row["participant_count"], 1)
		self.assertEqual(row["places_left"], 2)

	def test_places_left_is_none_when_no_headcount_was_set(self):
		"""None, not zero: a deployment that has not said needs no arithmetic."""
		from vmmsx.deployment.services import deployment as deployment_service

		deployment = self.deployment()

		row = deployment_service.status_dto(frappe.get_doc(deployment.doctype, deployment.name))

		self.assertIsNone(row["places_left"])

	def test_withdrawing_frees_a_place(self):
		people = self.volunteers(2)
		deployment = self.deployment(volunteers_required=1)
		assignment.deploy(deployment, people[:1], status=assignment.STATUS_ASSIGNED)

		assignment.withdraw(assignment.open_assignment(deployment.name, people[0]))
		outcome = assignment.deploy(deployment, people[1:], status=assignment.STATUS_ASSIGNED)

		self.assertEqual(outcome["raised"], 1)


class TestTheGrammar(AssignmentTestCase):
	def test_an_assignment_cannot_be_raised_as_an_answer(self):
		people = self.volunteers(1)
		deployment = self.deployment()

		with self.assertRaises(frappe.ValidationError):
			assignment.create(deployment, people[0], status=assignment.STATUS_ACCEPTED)

	def test_a_placed_assignment_cannot_become_a_decline(self):
		"""Nobody was asked, so there is no answer to record."""
		people = self.volunteers(1)
		deployment = self.deployment()
		row = assignment.create(deployment, people[0], status=assignment.STATUS_ASSIGNED)

		with self.assertRaises(frappe.ValidationError):
			assignment.respond(row, accepted=False)

	def test_the_desk_is_held_to_the_same_grammar_as_the_service(self):
		"""A status moved by hand from Declined to Accepted would be a volunteer's
		answer overwritten with nothing on the record to say it ever said otherwise."""
		people = self.volunteers(1)
		deployment = self.deployment()
		row = assignment.create(deployment, people[0], status=assignment.STATUS_PENDING)
		assignment.respond(row, accepted=False)

		row.reload()
		row.status = assignment.STATUS_ACCEPTED

		with self.assertRaises(frappe.ValidationError):
			row.save()

	def test_terms_retired_since_take_no_new_assignment(self):
		"""A deployment set up months ago must not ask somebody to agree to a
		specification the society has withdrawn."""
		people = self.volunteers(1)
		deployment = self.deployment()

		frappe.db.set_value(self.terms.doctype, self.terms.name, "is_active", 0)
		frappe.clear_document_cache(self.terms.doctype, self.terms.name)

		with self.assertRaises(frappe.ValidationError):
			assignment.create(deployment, people[0])

	def test_an_assignment_ending_before_it_starts_is_refused(self):
		people = self.volunteers(1)
		deployment = self.deployment()
		row = assignment.create(deployment, people[0])

		row.start_date, row.end_date = "2026-09-10", "2026-09-01"

		with self.assertRaises(frappe.ValidationError):
			row.save()


class TestTheLeader(AssignmentTestCase):
	def test_naming_a_leader_through_the_endpoint(self):
		people = self.volunteers(2)
		deployment = self.deployment()
		assignment.deploy(deployment, people, status=assignment.STATUS_ASSIGNED)

		row = assignment.roster_of(deployment.name)[0]
		api.set_assignment_role(row["name"], "leader")

		self.assertEqual(assignment.leader_of(deployment.name), row["volunteer"])

	def test_a_role_outside_the_two_is_refused(self):
		people = self.volunteers(1)
		deployment = self.deployment()
		row = assignment.create(deployment, people[0], status=assignment.STATUS_ASSIGNED)

		with self.assertRaises(frappe.ValidationError):
			assignment.set_role(row, "commander")

	def test_the_leader_is_listed_first(self):
		people = self.volunteers(3)
		deployment = self.deployment()
		assignment.deploy(deployment, people, status=assignment.STATUS_ASSIGNED)

		last = assignment.roster_of(deployment.name)[-1]
		assignment.set_role(frappe.get_doc(assignment.ASSIGNMENT_DOCTYPE, last["name"]), "leader")

		self.assertEqual(assignment.roster_of(deployment.name)[0]["volunteer"], last["volunteer"])

	def test_returning_a_leader_to_the_ranks_frees_the_post(self):
		people = self.volunteers(2)
		deployment = self.deployment()
		assignment.deploy(deployment, people, status=assignment.STATUS_ASSIGNED)
		first, second = assignment.roster_of(deployment.name)

		assignment.set_role(frappe.get_doc(assignment.ASSIGNMENT_DOCTYPE, first["name"]), "leader")
		assignment.set_role(frappe.get_doc(assignment.ASSIGNMENT_DOCTYPE, first["name"]), "member")
		assignment.set_role(frappe.get_doc(assignment.ASSIGNMENT_DOCTYPE, second["name"]), "leader")

		self.assertEqual(assignment.leader_of(deployment.name), second["volunteer"])


class TestTheFeed(AssignmentTestCase):
	def test_posting_an_update(self):
		deployment = self.deployment()

		feed.post(deployment, "Arrived at the camp.", entry_type="update")

		entries = feed.of(deployment.name)["entries"]

		self.assertEqual(entries[0]["note"], "Arrived at the camp.")
		self.assertEqual(entries[0]["source"], "deployment")

	def test_an_empty_update_is_refused(self):
		deployment = self.deployment()

		with self.assertRaises(frappe.ValidationError):
			feed.post(deployment, "   ")

	def test_nobody_writes_a_status_entry_by_hand(self):
		"""`status` and `roster` are this app's account of what it did. A person
		writing one would be putting a fact into the record that nothing did."""
		deployment = self.deployment()

		with self.assertRaises(frappe.ValidationError):
			feed.post(deployment, "Marked active.", entry_type="status")

	def test_the_author_and_the_time_come_from_the_session(self):
		"""A feed somebody could back-date or attribute to another person would be
		worse than no feed: it would look like a record."""
		deployment = self.deployment()

		entry = feed.post(deployment, "Something happened.")

		self.assertEqual(entry["author"], frappe.session.user)
		self.assertIsNotNone(entry["posted_on"])

	def test_a_status_change_writes_itself_into_the_feed(self):
		from vmmsx.deployment.services import deployment as deployment_service

		deployment = self.deployment()
		deployment_service.set_status(deployment, "Active", reason="The rains started.")

		kinds = [row["entry_type"] for row in feed.of(deployment.name)["entries"]]

		self.assertIn("status", kinds)

	def test_a_withdrawal_writes_itself_into_the_feed(self):
		people = self.volunteers(1)
		deployment = self.deployment()
		assignment.deploy(deployment, people, status=assignment.STATUS_ASSIGNED)

		assignment.withdraw(assignment.open_assignment(deployment.name, people[0]))

		kinds = [row["entry_type"] for row in feed.of(deployment.name)["entries"]]

		self.assertIn("roster", kinds)

	def test_a_volunteer_answering_does_not_fail_on_the_feed_entry(self):
		"""The case that forces the elevated save in `feed._append`.

		A volunteer holds no permission on the deployment register, so an ordinary
		save of the feed entry would turn a note-to-self into the reason their
		answer failed.
		"""
		user = fixtures.make_user("answering-volunteer")
		volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Ans", "Wering", email=user, user=user), self.branch
		).name

		deployment = self.deployment()
		row = assignment.create(deployment, volunteer, status=assignment.STATUS_PENDING)

		with fixtures.acting_as(user):
			api.respond_to_assignment(row.name, accept=1)

		self.assertEqual(
			assignment.open_assignment(deployment.name, volunteer).status,
			assignment.STATUS_ACCEPTED,
		)

	def test_task_reports_are_merged_in_rather_than_copied(self):
		"""One copy of each report, and it stays with the task it belongs to."""
		people = self.volunteers(1)
		deployment = self.deployment()
		assignment.deploy(deployment, people, status=assignment.STATUS_ASSIGNED)

		task = frappe.get_doc(
			{
				"doctype": "VMMS Task",
				"subject": "Register the households on the east side",
				"volunteer": people[0],
				"geo_node": self.branch,
				"deployment": deployment.name,
				"status": "assigned",
				"description": "Every household between the road and the river.",
			}
		).insert()
		task.append(
			"updates",
			{
				"entry_type": "progress",
				"author": frappe.session.user,
				"posted_on": frappe.utils.now_datetime(),
				"note": "Forty households done.",
			},
		)
		task.save()

		answer = feed.of(deployment.name)
		reports = [row for row in answer["entries"] if row["source"] == "task"]

		self.assertEqual(len(reports), 1)
		self.assertEqual(reports[0]["note"], "Forty households done.")
		self.assertEqual(reports[0]["task"], task.name)
		self.assertEqual(reports[0]["subject"], task.subject)

	def test_the_two_sources_stay_distinguishable(self):
		"""A coordinator reading "arrived at the camp" wants to know whether that
		is the deployment's own log or a volunteer's report against a task."""
		deployment = self.deployment()
		feed.post(deployment, "Arrived at the camp.")

		sources = {row["source"] for row in feed.of(deployment.name)["entries"]}

		self.assertEqual(sources, {"deployment"})

	def test_the_feed_reads_newest_first(self):
		deployment = self.deployment()
		feed.post(deployment, "First.")
		feed.post(frappe.get_doc(deployment.doctype, deployment.name), "Second.")

		entries = feed.of(deployment.name)["entries"]

		self.assertEqual(entries[0]["note"], "Second.")

	def test_reading_a_feed_needs_only_read_and_writing_needs_write(self):
		"""A feed anybody who could open the deployment could write to would not
		be a record of anything."""
		from frappe.permissions import add_permission, update_permission_property

		deployment = self.deployment()

		role = f"{fixtures.TEST_PREFIX} Feed Reader"
		fixtures.make_role(role)
		add_permission(fixtures.DEPLOYMENT_DOCTYPE, role, 0)
		update_permission_property(fixtures.DEPLOYMENT_DOCTYPE, role, 0, "read", 1)
		update_permission_property(fixtures.DEPLOYMENT_DOCTYPE, role, 0, "write", 0)
		frappe.clear_cache(doctype=fixtures.DEPLOYMENT_DOCTYPE)

		reader = fixtures.make_user("feed-reader")
		frappe.get_doc("User", reader).add_roles(role)
		fixtures.grant_scope(reader, fixtures.DEPLOYMENT_SCOPE_ROLE, self.branch)

		with fixtures.acting_as(reader):
			api.get_deployment_feed(deployment.name)

			with self.assertRaises(frappe.PermissionError):
				api.post_deployment_update(deployment.name, note="I should not be able to.")


class TestTheMap(AssignmentTestCase):
	"""Where this coordinator's people are, and the areas the map cannot draw.

	A geo tree is filled in from the top down over months, so most sites will
	have coordinates on some nodes and not others for a long time. The load-
	bearing claim is that an area with no point is still *counted* and still
	*listed* — it is simply absent from the pins, and the answer says how many
	were left off. A map that silently omitted them would under-report exactly
	where the gaps are.
	"""

	def area_node(self, label: str) -> str:
		"""A branch of this test's own, dropped when it ends.

		**Not the shared `self.branch`.** `IntegrationTestCase` rolls the
		transaction back once per *class*, not per method, so a deployment made by
		one method is still Active when the next one asks the map what is running —
		and a coordinate one method set is still on the node. Counting is exactly
		what this suite asserts on, so every method needs an area nothing else has
		touched.
		"""
		from onerc_core.geo.tests import fixtures as geo_fixtures

		# Deliberately **not** dropped in cleanup. The deployments made against it
		# live until the class-level rollback, so deleting the node would leave
		# them pointing at nothing — which is a state `deployment_map` now tolerates
		# but which no test should be manufacturing. A generated name is what keeps
		# the nodes from colliding; the rollback is what cleans them up.
		return geo_fixtures.make_node(
			f"{label}-{frappe.generate_hash(length=6)}",
			frappe.db.get_value("Geo Node", self.branch, "geo_level"),
			self.society_a["region"],
			is_group=True,
		)

	def place(self, node: str, latitude: float, longitude: float) -> None:
		frappe.db.set_value("Geo Node", node, {"latitude": latitude, "longitude": longitude})
		frappe.clear_document_cache("Geo Node", node)

	def running(self, node: str, people: list[str]):
		deployment = fixtures.make_deployment(self.terms.name, node)
		assignment.deploy(deployment, people, status=assignment.STATUS_ASSIGNED)
		deployment.reload()
		deployment_service.set_status(deployment, "Active")

		return deployment

	def area_for(self, node: str, **kwargs):
		return next(
			(row for row in api.deployment_map(**kwargs)["areas"] if row["geo_node"] == node),
			None,
		)

	def test_an_area_with_a_point_is_plotted(self):
		node = self.area_node("Plotted")
		self.place(node, -1.2921, 36.8219)
		self.running(node, self.volunteers(2))

		area = self.area_for(node)

		self.assertEqual(area["people"], 2)
		self.assertIn("latitude", area)

	def test_an_area_with_no_point_is_counted_and_reported(self):
		"""Counted, listed, and named in `unplotted` — never silently dropped."""
		node = self.area_node("Unplotted")
		self.running(node, self.volunteers(1))

		answer = api.deployment_map()
		area = next(row for row in answer["areas"] if row["geo_node"] == node)

		self.assertEqual(area["people"], 1)
		self.assertNotIn("latitude", area)
		self.assertGreaterEqual(answer["unplotted"], 1)

	def test_areas_are_ranked_busiest_first(self):
		here, there = self.area_node("Busier"), self.area_node("Quieter")
		self.running(here, self.volunteers(2))
		self.running(there, self.volunteers(1))

		counts = [row["people"] for row in api.deployment_map()["areas"] if row["geo_node"] in (here, there)]

		self.assertEqual(counts, sorted(counts, reverse=True))

	def test_a_question_nobody_answered_is_not_somebody_there(self):
		"""The count is Assigned plus Accepted. Pending holds no place."""
		node = self.area_node("Asked")
		deployment = fixtures.make_deployment(self.terms.name, node)
		assignment.deploy(deployment, self.volunteers(3), status=assignment.STATUS_PENDING)
		deployment.reload()
		deployment_service.set_status(deployment, "Active")

		area = self.area_for(node)

		self.assertEqual(area["people"], 0)
		self.assertEqual(area["waiting"], 3)

	def test_a_deployment_that_has_ended_is_not_on_the_map(self):
		"""It answers where people *are*, not where they have been."""
		node = self.area_node("Ended")
		deployment = self.running(node, self.volunteers(1))
		deployment.reload()
		deployment_service.set_status(deployment, "Completed")

		self.assertIsNone(self.area_for(node))

	def test_an_unknown_status_answers_with_nothing(self):
		"""The direction a filter should fail in."""
		self.running(self.area_node("Filtered"), self.volunteers(1))

		self.assertEqual(api.deployment_map(status="Postponed")["areas"], [])
