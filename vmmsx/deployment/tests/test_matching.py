# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""PART B — matching, and the one property it may never lose.

**A searcher can never be shown a volunteer they are not allowed to see.** Every
test in `TestScopeIsNeverLeaked` is written to break that, and each one attacks
it from a different direction: a volunteer who matches every attribute but sits
outside the searcher's area, a searcher with no scope at all, a searcher whose
society has not chosen a scope role, and a caller trying to widen their own area
through the arguments.

That last one is the shortest test in the file and the most important. It
asserts on the *signature*: there is no user parameter and no node parameter, so
there is no override to defend against. A service whose scope can only come from
the session cannot be talked out of it.

The criteria themselves are tested separately, and honestly. Certifications are
real, and the lapse is computed on the date being asked about, so those are
asserted against behaviour. Skills are not real, and `PENDING_CRITERIA` says so
in the response rather than in a comment somebody has to go and find.

**Each test builds its own terms of reference.** Frappe rolls the test
transaction back once per class, not per method, so a shared record that one
method added a requirement to would still carry it for the next.
"""

import ast
import inspect
from pathlib import Path

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.deployment.services import matching
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class MatchingTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_certification_type(fixtures.CERT_SWIFT_WATER, validity_days=365)
		fixtures.make_certification_type(fixtures.CERT_RADIO, validity_days=365)
		fixtures.make_certification_type(
			fixtures.CERT_LOGISTICS, validity_days=365, blocks_deployment_when_lapsed=0
		)

		# A searcher who holds the volunteer scope role at one branch only. Their
		# area is Karura and everything beneath it; Limuru is a sibling, so it is
		# outside by construction rather than by a filter somebody wrote.
		cls.searcher_user = cls.searcher("branch_searcher", cls.society_a["branch"])
		cls.national_user = cls.searcher("national_searcher", cls.society_a["region"])

	def volunteer_at(self, node: str, handle: str, certifications: tuple = ()):
		volunteer = fixtures.make_volunteer(fixtures.make_profile(handle, "Candidate"), node)

		for key in certifications:
			fixtures.make_certification(volunteer.name, key)

		return volunteer

	def search(self, user: str, terms: str, node: str, **kwargs):
		with fixtures.acting_as(user):
			return matching.candidates(terms, node, **kwargs)


class TestScopeIsNeverLeaked(MatchingTestCase):
	def test_an_out_of_scope_volunteer_is_never_returned(self):
		"""The headline. They match everything; they are still not returnable."""
		terms = fixtures.make_terms_requiring()
		inside = self.volunteer_at(self.society_a["branch"], "Inside")
		outside = self.volunteer_at(self.society_a["other_branch"], "Outside")

		names = self.candidate_names(self.search(self.searcher_user, terms.name, self.society_a["region"]))

		self.assertIn(inside.name, names)
		self.assertNotIn(outside.name, names)

	def test_an_out_of_scope_volunteer_matching_every_attribute_is_still_refused(self):
		"""Attributes cannot buy scope. This is the version with nothing else wrong.

		The out-of-scope volunteer holds every mandatory certification, is Active,
		and is anchored inside the *need's* subtree. The only thing that excludes
		them is the searcher's own area, which is exactly what has to be enough.
		The national searcher sees them, which is what proves the exclusion is
		about scope rather than about the volunteer being unsuitable.
		"""
		terms = fixtures.make_terms_requiring(mandatory=(fixtures.CERT_SWIFT_WATER,))
		outside = self.volunteer_at(self.society_a["other_branch"], "Perfect", (fixtures.CERT_SWIFT_WATER,))

		wide = self.search(self.national_user, terms.name, self.society_a["region"])
		self.assertIn(outside.name, self.candidate_names(wide))

		narrow = self.search(self.searcher_user, terms.name, self.society_a["region"])
		self.assertNotIn(outside.name, self.candidate_names(narrow))

	def test_a_searcher_with_no_assignment_gets_nothing(self):
		"""Fail closed. An empty scope is never read as unfiltered."""
		terms = fixtures.make_terms_requiring()
		self.volunteer_at(self.society_a["branch"], "Unseen")

		nobody = fixtures.make_user("holds_nothing")

		with fixtures.acting_as(nobody):
			result = matching.candidates(terms.name, self.society_a["region"])

		self.assertEqual(result["candidates"], [])
		self.assertEqual(result["considered"], 0)

	def test_an_unconfigured_scope_role_returns_nothing(self):
		"""A society that has not chosen the role has not thereby opened the register.

		Core logs the unresolved role; this asserts the consequence, which is that
		matching returns nobody rather than everybody.
		"""
		terms = fixtures.make_terms_requiring()
		self.volunteer_at(self.society_a["branch"], "Alsounseen")

		fixtures.set_volunteer_scope_role(None)
		self.addCleanup(fixtures.set_volunteer_scope_role, fixtures.VOLUNTEER_SCOPE_ROLE)

		result = self.search(self.searcher_user, terms.name, self.society_a["region"])

		self.assertEqual(result["candidates"], [])

	def test_the_scope_cannot_be_supplied_by_a_caller(self):
		"""The signature is the guarantee. There is nothing to override.

		A `user=` or a `nodes=` parameter would be an argument by which a caller
		widened their own area, and the check stopping that would be one more
		thing to get right. This asserts there is nothing to get right, on the
		service and on the endpoint that exposes it.
		"""
		from vmmsx.api import deployment as api

		parameters = set(inspect.signature(matching.candidates).parameters)

		self.assertEqual(parameters, {"terms_of_reference", "geo_node", "as_of", "limit"})

		for signature in (parameters, set(inspect.signature(api.find_candidates).parameters)):
			self.assertNotIn("user", signature)
			self.assertNotIn("nodes", signature)
			self.assertNotIn("scope", signature)

	def test_the_need_narrows_a_wide_searcher_rather_than_widening_a_narrow_one(self):
		"""The answer is an intersection, and it is an intersection both ways."""
		terms = fixtures.make_terms_requiring()
		here = self.volunteer_at(self.society_a["post"], "Beneath")
		elsewhere = self.volunteer_at(self.society_a["other_post"], "Elsewhere")

		# A national searcher asking about one post gets that post only.
		narrowed = self.search(self.national_user, terms.name, self.society_a["post"])
		self.assertEqual(self.candidate_names(narrowed), [here.name])

		# A branch searcher asking about the whole region gets their branch only.
		widened = self.candidate_names(self.search(self.searcher_user, terms.name, self.society_a["region"]))
		self.assertIn(here.name, widened)
		self.assertNotIn(elsewhere.name, widened)

	def test_a_need_outside_the_searchers_area_returns_nothing(self):
		terms = fixtures.make_terms_requiring()
		self.volunteer_at(self.society_a["other_post"], "Faraway")

		result = self.search(self.searcher_user, terms.name, self.society_a["other_branch"])

		self.assertEqual(result["candidates"], [])

	def test_a_volunteer_in_another_society_is_never_reached(self):
		"""ACC-01: two disjoint subtrees, and no path between them."""
		terms = fixtures.make_terms_requiring()
		self.volunteer_at(self.society_b["ward"], "Otherside")

		result = self.search(self.national_user, terms.name, self.society_a["region"])

		self.assertEqual(
			[row for row in result["candidates"] if row["home_geo_node"] == self.society_b["ward"]], []
		)


class TestTheCriteriaThatAreReal(MatchingTestCase):
	def test_a_volunteer_without_a_mandatory_certification_is_not_a_candidate(self):
		terms = fixtures.make_terms_requiring(mandatory=(fixtures.CERT_SWIFT_WATER,))

		holder = self.volunteer_at(self.society_a["branch"], "Holds", (fixtures.CERT_SWIFT_WATER,))
		nonholder = self.volunteer_at(self.society_a["branch"], "Holdsnot")

		names = self.candidate_names(self.search(self.national_user, terms.name, self.society_a["branch"]))

		self.assertIn(holder.name, names)
		self.assertNotIn(nonholder.name, names)

	def test_a_lapsed_mandatory_certification_makes_somebody_non_deployable(self):
		"""Computed on read, from the date being asked about. Nothing was written."""
		terms = fixtures.make_terms_requiring(mandatory=(fixtures.CERT_SWIFT_WATER,))

		lapsed = self.volunteer_at(self.society_a["branch"], "Lapsed")
		fixtures.make_certification(
			lapsed.name, fixtures.CERT_SWIFT_WATER, completion_date=add_days(today(), -400)
		)

		names = self.candidate_names(self.search(self.national_user, terms.name, self.society_a["branch"]))

		self.assertNotIn(lapsed.name, names)

	def test_the_same_volunteer_reads_differently_on_a_different_date(self):
		"""The whole argument for deriving the lapse instead of storing it.

		One certification, one volunteer, two answers, no write in between.
		"""
		terms = fixtures.make_terms_requiring(mandatory=(fixtures.CERT_SWIFT_WATER,))

		volunteer = self.volunteer_at(self.society_a["branch"], "Expiring")
		fixtures.make_certification(
			volunteer.name, fixtures.CERT_SWIFT_WATER, completion_date=add_days(today(), -300)
		)

		soon = self.search(self.national_user, terms.name, self.society_a["branch"], as_of=today())
		later = self.search(
			self.national_user, terms.name, self.society_a["branch"], as_of=add_days(today(), 200)
		)

		self.assertIn(volunteer.name, self.candidate_names(soon))
		self.assertNotIn(volunteer.name, self.candidate_names(later))

	def test_a_lapse_of_a_type_the_society_does_not_treat_as_blocking_excludes_nobody(self):
		"""Whether a lapse costs anything is the certification type's configuration."""
		terms = fixtures.make_terms_requiring()

		volunteer = self.volunteer_at(self.society_a["branch"], "Softlapse")
		fixtures.make_certification(
			volunteer.name, fixtures.CERT_LOGISTICS, completion_date=add_days(today(), -400)
		)

		names = self.candidate_names(self.search(self.national_user, terms.name, self.society_a["branch"]))

		self.assertIn(volunteer.name, names)

	def test_a_suspended_volunteer_is_not_a_candidate(self):
		from vmmsx.volunteer.services import volunteer as volunteer_service

		terms = fixtures.make_terms_requiring()
		volunteer = self.volunteer_at(self.society_a["branch"], "Suspended")
		volunteer_service.suspend(volunteer, "Whatever this society decided.")

		names = self.candidate_names(self.search(self.national_user, terms.name, self.society_a["branch"]))

		self.assertNotIn(volunteer.name, names)

	def test_a_desirable_certification_ranks_rather_than_excludes(self):
		terms = fixtures.make_terms_requiring(desirable=(fixtures.CERT_RADIO,))

		plain = self.volunteer_at(self.society_a["branch"], "Aplain")
		ranked = self.volunteer_at(self.society_a["branch"], "Zranked", (fixtures.CERT_RADIO,))

		names = self.candidate_names(self.search(self.national_user, terms.name, self.society_a["branch"]))

		self.assertIn(plain.name, names)
		# Ranked first despite sorting after by name, which is what proves the
		# desirable requirement did something.
		self.assertEqual(names[0], ranked.name)

	def test_the_result_reports_what_it_matched_on(self):
		terms = fixtures.make_terms_requiring(
			mandatory=(fixtures.CERT_SWIFT_WATER,), desirable=(fixtures.CERT_RADIO,)
		)

		result = self.search(self.national_user, terms.name, self.society_a["branch"])

		self.assertEqual(result["required_certifications"], [fixtures.CERT_SWIFT_WATER])
		self.assertEqual(result["desirable_certifications"], [fixtures.CERT_RADIO])

	def test_a_candidate_row_says_why_it_qualified(self):
		terms = fixtures.make_terms_requiring(mandatory=(fixtures.CERT_SWIFT_WATER,))
		volunteer = self.volunteer_at(self.society_a["branch"], "Explained", (fixtures.CERT_SWIFT_WATER,))

		result = self.search(self.national_user, terms.name, self.society_a["branch"])
		row = next(row for row in result["candidates"] if row["volunteer"] == volunteer.name)

		self.assertTrue(row["is_candidate"])
		self.assertTrue(row["deployable"])
		self.assertEqual(row["missing_certifications"], [])
		self.assertEqual(row["blocking_reasons"], [])

	def test_a_limit_truncates_and_says_so(self):
		terms = fixtures.make_terms_requiring()

		for index in range(3):
			self.volunteer_at(self.society_a["branch"], f"Many{index}")

		result = self.search(self.national_user, terms.name, self.society_a["branch"], limit=1)

		self.assertEqual(len(result["candidates"]), 1)
		self.assertTrue(result["truncated"])


class TestTheCriteriaThatArePending(MatchingTestCase):
	"""What is not matched on is reported, not hidden.

	A candidate list that quietly omitted its own limitations would be read as
	"these are the people who fit", and somebody would deploy on that reading.
	"""

	def test_every_result_carries_the_pending_criteria(self):
		terms = fixtures.make_terms_requiring()
		result = self.search(self.national_user, terms.name, self.society_a["branch"])

		self.assertTrue(result["pending_criteria"])

		for row in result["pending_criteria"]:
			self.assertIn("criterion", row)
			self.assertIn("why", row)
			self.assertIn(row["status"], ("pending", "proposed"))

	def test_skills_are_named_as_pending_rather_than_faked(self):
		criteria = {row["criterion"]: row for row in matching.PENDING_CRITERIA}

		self.assertIn("skills", criteria)
		self.assertEqual(criteria["skills"]["status"], "pending")

	def test_no_free_text_declaration_is_read_by_the_matching_code(self):
		"""The negative half. A substring search on free text would be worse than nothing.

		Docstrings are stripped before the check: prose is allowed to explain what
		is deliberately not read, and a scan that flagged the sentence saying so
		would be unusable.
		"""
		source = Path(frappe.get_app_path("vmmsx"), "deployment", "services", "matching.py").read_text()
		code = _code_only(source)

		for field in ("declared_skills", "prior_experience", "motivation"):
			self.assertNotIn(field, code)


class TestMatchingForADocument(MatchingTestCase):
	def test_a_request_asks_about_the_day_the_work_starts(self):
		"""Not today. A request raised in March for June wants June's answer."""
		terms = fixtures.make_terms_requiring(mandatory=(fixtures.CERT_SWIFT_WATER,))

		volunteer = self.volunteer_at(self.society_a["branch"], "Expires")
		fixtures.make_certification(
			volunteer.name, fixtures.CERT_SWIFT_WATER, completion_date=add_days(today(), -300)
		)

		request = fixtures.make_request(
			terms.name,
			self.society_a["branch"],
			needed_from=add_days(today(), 200),
			needed_until=add_days(today(), 210),
		)

		with fixtures.acting_as(self.national_user):
			result = matching.candidates_for(request)

		self.assertNotIn(volunteer.name, self.candidate_names(result))

	def test_a_request_limits_to_the_number_it_asked_for(self):
		terms = fixtures.make_terms_requiring()

		for index in range(4):
			self.volunteer_at(self.society_a["branch"], f"Plenty{index}")

		request = fixtures.make_request(terms.name, self.society_a["branch"], volunteers_requested=2)

		with fixtures.acting_as(self.national_user):
			result = matching.candidates_for(request)

		self.assertEqual(len(result["candidates"]), 2)

	def test_a_deployment_asks_about_its_own_start_date(self):
		terms = fixtures.make_terms_requiring()
		volunteer = self.volunteer_at(self.society_a["branch"], "Available")

		deployment = fixtures.make_deployment(terms.name, self.society_a["branch"])

		with fixtures.acting_as(self.national_user):
			result = matching.candidates_for(deployment)

		self.assertEqual(result["as_of"], getdate(deployment.start_date))
		self.assertIn(volunteer.name, self.candidate_names(result))


def _code_only(source: str) -> str:
	"""The source with docstrings removed."""
	tree = ast.parse(source)
	docstrings = set()

	for node in ast.walk(tree):
		if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
			continue

		if node.body and isinstance(node.body[0], ast.Expr):
			value = node.body[0].value

			if isinstance(value, ast.Constant) and isinstance(value.value, str):
				docstrings.add(id(value))

	class StripDocstrings(ast.NodeTransformer):
		def visit_Expr(self, node):
			if isinstance(node.value, ast.Constant) and id(node.value) in docstrings:
				return None

			return node

	return ast.unparse(StripDocstrings().visit(tree))
