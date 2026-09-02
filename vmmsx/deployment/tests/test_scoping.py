# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Geo scoping for this module's three doctypes, asked of core rather than of us.

vmmsx registers `VMMS Deployment`, `VMMS Deployment Request` and
`VMMS Branch Transfer` with core through `onerc_scopeable_doctypes`, each naming
its role with `role_from_setting` rather than a literal. Everything below is a
test of that registration doing what it claims, and every verdict comes from
core's own enforcement layer, so what these tests observe is what a list view, a
document read and an API guard would each observe.

Three properties, and each has its own class:

* **Registered at all**, on the right field, with a settings-backed role. A
  registration naming a field the doctype does not have would throw at the point
  of use rather than at boot, and a literal role would hardcode exactly what the
  access model forbids.
* **Fails closed when the society has not chosen.** Empty is the shipped state
  for all three, and empty must mean nobody rather than everybody.
* **Separates the three questions.** A coordinator granted the deployment role
  does not thereby see requests or transfers, which is the whole reason there
  are three settings and not one.
"""

import frappe
from frappe.utils import add_days, today
from onerc_core.access.services import registry
from onerc_core.access.services.enforcement import is_in_scope

from vmmsx.deployment.services import society
from vmmsx.deployment.tests import fixtures
from vmmsx.deployment.tests.base import DeploymentTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

# (doctype, anchor field, settings field, the fixtures' role for it)
REGISTERED = (
	(
		fixtures.DEPLOYMENT_DOCTYPE,
		"geo_node",
		society.DEPLOYMENT_SCOPE_ROLE_FIELD,
		fixtures.DEPLOYMENT_SCOPE_ROLE,
	),
	(fixtures.REQUEST_DOCTYPE, "geo_node", society.REQUEST_SCOPE_ROLE_FIELD, fixtures.REQUEST_SCOPE_ROLE),
	(
		fixtures.TRANSFER_DOCTYPE,
		"from_geo_node",
		society.TRANSFER_SCOPE_ROLE_FIELD,
		fixtures.TRANSFER_SCOPE_ROLE,
	),
)


class ScopingTestCase(DeploymentTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		cls.terms = fixtures.make_terms()

		# One coordinator per question, each holding exactly one scope role, at
		# one branch. Anything they can see, they can see for one reason.
		cls.deployment_viewer = cls.viewer(
			"deployment_viewer", fixtures.DEPLOYMENT_SCOPE_ROLE, cls.society_a["branch"]
		)
		cls.request_viewer = cls.viewer(
			"request_viewer", fixtures.REQUEST_SCOPE_ROLE, cls.society_a["branch"]
		)
		cls.transfer_viewer = cls.viewer(
			"transfer_viewer", fixtures.TRANSFER_SCOPE_ROLE, cls.society_a["branch"]
		)


class TestTheRegistrationIsWellFormed(ScopingTestCase):
	def test_all_three_doctypes_are_registered(self):
		registered = set(registry.scoped_doctypes())

		for doctype, _field, _setting, _role in REGISTERED:
			self.assertIn(doctype, registered)

	def test_each_names_a_field_its_doctype_actually_has(self):
		"""`geo_node_field()` throws on a registration naming a field that is missing."""
		for doctype, field, _setting, _role in REGISTERED:
			self.assertEqual(registry.geo_node_field(doctype), field)

	def test_none_of_them_hardcodes_a_role(self):
		"""Which role sees what is a society's decision, so the registration names a setting."""
		for doctype, _field, setting, _role in REGISTERED:
			registration = registry.for_doctype(doctype)

			self.assertIsNone(registration.get("role"))
			self.assertEqual(registration.get("role_from_setting"), setting)

	def test_the_settings_fields_exist_and_are_owned_by_vmmsx(self):
		for _doctype, _field, setting, _role in REGISTERED:
			self.assertTrue(
				frappe.db.exists("Custom Field", {"dt": "National Society Settings", "fieldname": setting}),
				f"{setting} was not installed",
			)

	def test_the_transfer_is_anchored_on_the_branch_it_is_leaving(self):
		"""Stated as its own test because it is the design decision, not a detail.

		Anchoring on `from_geo_node` is what keeps a completed transfer visible to
		the branch that lost somebody, and it is where a routed transfer is
		approved by default.
		"""
		self.assertEqual(registry.geo_node_field(fixtures.TRANSFER_DOCTYPE), "from_geo_node")


class TestItFailsClosed(ScopingTestCase):
	def test_an_unconfigured_role_denies_everybody(self):
		"""Empty is the shipped state, and empty means nobody rather than everybody."""
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"])

		fixtures.set_deployment_scope_role(None)
		self.addCleanup(fixtures.set_deployment_scope_role, fixtures.DEPLOYMENT_SCOPE_ROLE)

		self.assertFalse(
			is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, deployment.geo_node, self.deployment_viewer)
		)

	def test_a_user_holding_nothing_sees_nothing(self):
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"])
		nobody = fixtures.make_user("scopeless")

		self.assertFalse(is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, deployment.geo_node, nobody))

	def test_an_unplaced_record_is_inside_nobodys_scope(self):
		"""Which is why ACC-02 refuses one at creation rather than tolerating it."""
		self.assertFalse(is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, None, self.deployment_viewer))


class TestScopeIsSubtreeShaped(ScopingTestCase):
	def test_a_viewer_sees_their_node_and_everything_beneath_it(self):
		beneath = fixtures.make_deployment(self.terms.name, self.society_a["post"])
		at = fixtures.make_deployment(self.terms.name, self.society_a["branch"])

		self.assertTrue(is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, at.geo_node, self.deployment_viewer))
		self.assertTrue(is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, beneath.geo_node, self.deployment_viewer))

	def test_a_viewer_does_not_see_a_sibling_branch(self):
		elsewhere = fixtures.make_deployment(self.terms.name, self.society_a["other_branch"])

		self.assertFalse(is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, elsewhere.geo_node, self.deployment_viewer))

	def test_a_viewer_does_not_see_above_themselves(self):
		"""Scope grants downward. A branch coordinator is not a regional one."""
		above = fixtures.make_deployment(self.terms.name, self.society_a["region"])

		self.assertFalse(is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, above.geo_node, self.deployment_viewer))

	def test_a_viewer_does_not_see_another_society(self):
		"""ACC-01: two disjoint subtrees, and no path between them.

		Its own terms of reference, scoped to the other society, because a terms
		of reference now has to say where it applies and `self.terms` says society
		A. That is the rule working rather than an obstacle to this test: the
		deployment here is genuinely somebody else's, and it needs somebody else's
		specification to be run under.
		"""
		theirs = fixtures.make_terms(
			f"{fixtures.TEST_PREFIX}-tor-other-society", geo_scope=self.society_b["region"]
		)
		elsewhere = fixtures.make_deployment(theirs.name, self.society_b["ward"])

		self.assertFalse(is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, elsewhere.geo_node, self.deployment_viewer))


class TestTheThreeQuestionsAreSeparate(ScopingTestCase):
	"""Three settings because these are three questions, and holding one is not holding another."""

	def test_the_deployment_viewer_does_not_thereby_see_requests(self):
		request = fixtures.make_request(self.terms.name, self.society_a["branch"])

		self.assertTrue(
			is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, self.society_a["branch"], self.deployment_viewer)
		)
		self.assertFalse(is_in_scope(fixtures.REQUEST_DOCTYPE, request.geo_node, self.deployment_viewer))

	def test_the_request_viewer_does_not_thereby_see_transfers(self):
		volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Scoped", "Volunteer"), self.society_a["branch"]
		)
		transfer = fixtures.make_transfer(
			volunteer.name,
			self.society_a["other_branch"],
			effective_date=add_days(today(), 30),
		)

		self.assertFalse(is_in_scope(fixtures.TRANSFER_DOCTYPE, transfer.from_geo_node, self.request_viewer))

	def test_each_viewer_does_see_their_own(self):
		"""The positive half, without which the three tests above prove nothing."""
		volunteer = fixtures.make_volunteer(
			fixtures.make_profile("Seen", "Volunteer"), self.society_a["branch"]
		)
		transfer = fixtures.make_transfer(
			volunteer.name,
			self.society_a["other_branch"],
			effective_date=add_days(today(), 30),
		)
		request = fixtures.make_request(self.terms.name, self.society_a["branch"])
		deployment = fixtures.make_deployment(self.terms.name, self.society_a["branch"])

		self.assertTrue(is_in_scope(fixtures.DEPLOYMENT_DOCTYPE, deployment.geo_node, self.deployment_viewer))
		self.assertTrue(is_in_scope(fixtures.REQUEST_DOCTYPE, request.geo_node, self.request_viewer))
		self.assertTrue(is_in_scope(fixtures.TRANSFER_DOCTYPE, transfer.from_geo_node, self.transfer_viewer))
