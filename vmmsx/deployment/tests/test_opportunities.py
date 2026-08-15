# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The opportunity board: what a volunteer may see, and what they may not.

`api/opportunities.py` is the one read in this module that does not go through
the permission layer, so the thing worth pinning down is not that it returns
rows — it is **which** rows it returns, and that the answer does not depend on
who is asking. Every test here is about the boundary rather than the shape:

* nothing at all until a society publishes it (`is_published` ships off);
* nothing until the approval has settled, so an advertisement is never a promise
  the society has not made;
* nothing whose window has closed;
* no `justification`, ever, because that field is written for the approver;
* and the same answer for a signed-in nobody as for a coordinator, because a
  notice board that varied by reader would be a scope wearing a board's name.

The last one is the reason the suite exists. It would be very easy for somebody
to "fix" the elevation later by swapping `get_all` for `get_list`, at which
point the board silently empties for exactly the people it is for, and no other
test in this app would notice.
"""

import frappe
from frappe.utils import add_days, today

from vmmsx.api import opportunities
from vmmsx.approvals import states
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class OpportunityTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		# Somebody with no role, no assignment and no scope anywhere: a volunteer
		# who has just been accepted, which is who the board is built for.
		cls.nobody = fixtures.make_user("board_reader")

	def advertise(self, geo_node: str | None = None, **overrides):
		"""A published request a society owes nobody an approval on.

		The default terms of reference use the `direct` mode, so this request is
		settled the moment it exists and sits at Draft forever — which is exactly
		the case a state comparison would have hidden, and the reason the board
		asks `request_service.is_settled` instead. It also fulfils itself on
		insert, so it arrives on the board already carrying a Planned deployment
		with nobody on it.
		"""
		terms = fixtures.make_terms_requiring()
		request = fixtures.make_request(
			terms.name,
			geo_node or self.society_a["branch"],
			is_published=1,
			**overrides,
		)

		return terms, request

	def routed(self, geo_node: str | None = None, **overrides):
		"""A published request that genuinely owes somebody a decision.

		`routed` terms with nothing submitted: unsettled, and therefore not an
		advertisement whatever the flag says.
		"""
		terms = fixtures.make_terms_requiring(approval_mode="routed")
		request = fixtures.make_request(
			terms.name,
			geo_node or self.society_a["branch"],
			is_published=1,
			**overrides,
		)

		return terms, request

	def names(self, **kwargs) -> set[str]:
		return {row["name"] for row in opportunities.browse(**kwargs)["opportunities"]}

	def card(self, name: str) -> dict:
		return next(row for row in opportunities.browse()["opportunities"] if row["name"] == name)


class TestPublicationIsTheWholeBoundary(OpportunityTestCase):
	def test_an_unpublished_request_is_not_on_the_board(self):
		terms = fixtures.make_terms_requiring()
		request = fixtures.make_request(terms.name, self.society_a["branch"])

		self.assertNotIn(request.name, self.names())

	def test_publishing_is_off_by_default(self):
		"""The field ships off, and off is the whole of the rule."""
		terms = fixtures.make_terms_requiring()
		request = fixtures.make_request(terms.name, self.society_a["branch"])

		self.assertFalse(request.is_published)

	def test_a_published_request_a_society_owes_nobody_an_approval_on_is_on_the_board(self):
		"""The `direct` case, and the one a state comparison silently loses.

		Such a request sits at Draft forever. Nothing is owed on it, so it is
		settled by definition, and the board has to say so.
		"""
		_, request = self.advertise()

		self.assertEqual(request.approval_state, states.DRAFT)
		self.assertIn(request.name, self.names())

	def test_a_published_request_awaiting_a_decision_is_not_on_the_board(self):
		"""An advertisement for work nobody has agreed to is a promise not made."""
		_, request = self.routed()

		self.assertNotIn(request.name, self.names())

	def test_a_published_request_that_was_rejected_is_not_on_the_board(self):
		_, request = self.routed()
		request.db_set("approval_state", states.REJECTED)

		self.assertNotIn(request.name, self.names())

	def test_a_published_request_that_was_withdrawn_is_not_on_the_board(self):
		"""Terminal and never settling, which is the same answer as rejected."""
		_, request = self.routed()
		request.db_set("approval_state", states.WITHDRAWN)

		self.assertNotIn(request.name, self.names())

	def test_work_whose_window_has_closed_is_not_on_the_board(self):
		_, request = self.advertise(
			needed_from=add_days(today(), -30), needed_until=add_days(today(), -1)
		)

		self.assertNotIn(request.name, self.names())

	def test_work_whose_deployment_is_finished_is_not_on_the_board(self):
		"""Whatever flag is still set on the request that asked for it."""
		_, request = self.advertise()
		frappe.db.set_value(
			fixtures.DEPLOYMENT_DOCTYPE, request.deployment, "status", "Completed"
		)

		self.assertNotIn(request.name, self.names())

	def test_work_whose_deployment_was_cancelled_is_not_on_the_board(self):
		_, request = self.advertise()
		frappe.db.set_value(
			fixtures.DEPLOYMENT_DOCTYPE, request.deployment, "status", "Cancelled"
		)

		self.assertNotIn(request.name, self.names())


class TestTheBoardIsTheSameForEverybody(OpportunityTestCase):
	def test_a_person_with_no_role_and_no_scope_sees_the_board(self):
		"""The case the elevation exists for, and the one a `get_list` would break."""
		_, request = self.advertise()

		with fixtures.acting_as(self.nobody):
			self.assertIn(request.name, self.names())

	def test_a_person_with_no_scope_sees_work_outside_any_area_they_hold(self):
		_, request = self.advertise(geo_node=self.society_b["ward"])

		with fixtures.acting_as(self.nobody):
			self.assertIn(request.name, self.names())


class TestWhatTheBoardSays(OpportunityTestCase):
	def test_the_justification_is_never_published(self):
		"""Written for the approver. Publishing a need is not publishing the case for it."""
		_, request = self.advertise(justification="Internal reasoning nobody outside should read.")

		row = self.card(request.name)

		self.assertNotIn("justification", row)
		self.assertNotIn("Internal reasoning", str(row))

	def test_the_card_carries_the_terms_place_dates_and_head_count(self):
		terms, request = self.advertise()

		row = self.card(request.name)

		self.assertEqual(row["terms_of_reference"], terms.name)
		self.assertEqual(row["geo_node"], self.society_a["branch"])
		self.assertEqual(row["volunteers_requested"], request.volunteers_requested)
		self.assertTrue(row["geo_path"])

	def test_a_deployment_with_nobody_on_it_yet_reports_an_empty_roster(self):
		"""Who goes is a coordinator's judgement, so a fresh deployment has nobody."""
		_, request = self.advertise()

		row = self.card(request.name)

		self.assertEqual(row["deployment"], request.deployment)
		self.assertEqual(row["deployment_status"], "Planned")
		self.assertEqual(row["places_filled"], 0)

	def test_the_roster_count_follows_the_deployment(self):
		_, request = self.advertise()
		profile = fixtures.make_profile()
		volunteer = fixtures.make_volunteer(profile, self.society_a["branch"])

		deployment = frappe.get_doc(fixtures.DEPLOYMENT_DOCTYPE, request.deployment)
		deployment.append("participants", {"volunteer": volunteer.name})
		deployment.save(ignore_permissions=True)

		self.assertEqual(self.card(request.name)["places_filled"], 1)


class TestTheFilters(OpportunityTestCase):
	def test_a_location_narrows_to_that_node_and_its_subtree(self):
		_, here = self.advertise(geo_node=self.society_a["post"])
		_, elsewhere = self.advertise(geo_node=self.society_a["other_branch"])

		found = self.names(geo_node=self.society_a["branch"])

		self.assertIn(here.name, found)
		self.assertNotIn(elsewhere.name, found)

	def test_a_location_includes_work_at_the_node_itself(self):
		"""`get_descendants` excludes the node; a filter on a branch must not."""
		_, request = self.advertise(geo_node=self.society_a["branch"])

		self.assertIn(request.name, self.names(geo_node=self.society_a["branch"]))

	def test_search_matches_the_terms_of_reference_by_name(self):
		terms, request = self.advertise()
		terms.db_set("tor_name", "Shoreline Flood Response")

		self.assertIn(request.name, self.names(search="Flood"))
		self.assertNotIn(request.name, self.names(search="Vaccination"))

	def test_search_and_the_kind_of_work_narrow_together(self):
		"""Both filter the same column. One must not silently replace the other."""
		terms, request = self.advertise()
		terms.db_set("tor_name", "Shoreline Flood Response")
		_, other = self.advertise()

		found = self.names(search="Flood", terms_of_reference=other.terms_of_reference)

		self.assertEqual(found, set())

	def test_the_facets_offer_only_what_is_actually_on_the_board(self):
		"""A filter that can only ever return nothing reads as a broken filter."""
		terms, _ = self.advertise()
		unused = fixtures.make_terms_requiring()

		offered = {row["key"] for row in opportunities.filters()["terms"]}

		self.assertIn(terms.name, offered)
		self.assertNotIn(unused.name, offered)

	def test_an_empty_board_offers_no_facet_at_all(self):
		"""Rather than an `IN ()` a framework may read as no filter and answer with everything."""
		frappe.db.set_value(
			fixtures.REQUEST_DOCTYPE, {"is_published": 1}, "is_published", 0, update_modified=False
		)

		answer = opportunities.filters()

		self.assertEqual(answer["count"], 0)
		self.assertEqual(answer["terms"], [])
