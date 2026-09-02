# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What a society insists on seeing before it lets somebody volunteer.

The floor has always been "some identification". What is new is the society's own
answer on top of it, held as vmmsx-owned Custom Fields on core's
`Identification Type` — so a branch that starts asking for a birth certificate
ticks a box on a record it already has, and no source file names a document.

Three of these tests are about the app doing *nothing*, which is the shipped
state and the one most easily broken by a later change: a society that has ticked
nothing must be exactly as unconstrained as it was before this existed.
"""

import frappe

from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

IDENTIFICATION_TYPE_DOCTYPE = "Identification Type"

REQUIRED_FIELD = "vmms_is_required_for_volunteers"
ATTACHMENT_FIELD = "vmms_requires_attachment"
MINIMUM_AGE_FIELD = "vmms_minimum_age"

BIRTH_CERTIFICATE = f"{fixtures.TEST_PREFIX}-birth-certificate"


def _rule(key: str, **values) -> str:
	"""An Identification Type carrying this society's rules for it."""
	if not frappe.db.exists(IDENTIFICATION_TYPE_DOCTYPE, key):
		frappe.get_doc(
			{
				"doctype": IDENTIFICATION_TYPE_DOCTYPE,
				"identification_type_key": key,
				"identification_type_name": key.replace(f"{fixtures.TEST_PREFIX}-", "")
				.replace("-", " ")
				.title(),
				"is_active": 1,
			}
		).insert()

	frappe.db.set_value(IDENTIFICATION_TYPE_DOCTYPE, key, values)
	frappe.clear_document_cache(IDENTIFICATION_TYPE_DOCTYPE, key)

	return key


class TestTheRulesAreInstalled(RegistrationTestCase):
	def test_the_three_custom_fields_exist_on_cores_doctype(self):
		"""Custom Fields vmmsx owns. Core's own JSON is not edited."""
		meta = frappe.get_meta(IDENTIFICATION_TYPE_DOCTYPE)

		for field in (REQUIRED_FIELD, ATTACHMENT_FIELD, MINIMUM_AGE_FIELD):
			self.assertTrue(meta.has_field(field), f"{field} is missing")
			self.assertTrue(
				frappe.db.exists("Custom Field", {"dt": IDENTIFICATION_TYPE_DOCTYPE, "fieldname": field}),
				f"{field} is not a Custom Field",
			)


class TestNothingRequiredMeansNothingRequired(RegistrationTestCase):
	def test_an_ordinary_registration_is_unaffected(self):
		"""The shipped state: no type is ticked, so the floor is the only rule."""
		_, application = self.register_as_volunteer("no.rules.configured")

		self.assertEqual(application.approval_state, "In Review")


class TestARequiredDocument(RegistrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_rule(BIRTH_CERTIFICATE, **{REQUIRED_FIELD: 1})

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_value(
			IDENTIFICATION_TYPE_DOCTYPE, BIRTH_CERTIFICATE, {REQUIRED_FIELD: 0, ATTACHMENT_FIELD: 0}
		)
		super().tearDownClass()

	def test_an_applicant_without_it_cannot_submit(self):
		"""The applicant produced *an* identification, and not the one asked for."""
		user = fixtures.website_account("missing.the.certificate")

		with fixtures.acting_as(user), self.assertRaises(frappe.MandatoryError) as refusal:
			fixtures.submit_volunteer_form(self.branch())

		self.assertIn("Birth Certificate", str(refusal.exception))

	def test_producing_it_lets_the_submission_through(self):
		user = fixtures.website_account("has.the.certificate")

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(
				self.branch(),
				id_type=BIRTH_CERTIFICATE,
				id_number=f"{fixtures.TEST_PREFIX}-BC-0001",
			)

		self.assertEqual(application.approval_state, "In Review")

	def test_an_inactive_required_type_stops_being_insisted_on(self):
		frappe.db.set_value(IDENTIFICATION_TYPE_DOCTYPE, BIRTH_CERTIFICATE, "is_active", 0)
		frappe.clear_document_cache(IDENTIFICATION_TYPE_DOCTYPE, BIRTH_CERTIFICATE)
		self.addCleanup(frappe.db.set_value, IDENTIFICATION_TYPE_DOCTYPE, BIRTH_CERTIFICATE, "is_active", 1)

		user = fixtures.website_account("after.retirement")

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(self.branch())

		self.assertEqual(application.approval_state, "In Review")


class TestADocumentThatNeedsACopy(RegistrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_rule(BIRTH_CERTIFICATE, **{REQUIRED_FIELD: 1, ATTACHMENT_FIELD: 1})

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_value(
			IDENTIFICATION_TYPE_DOCTYPE, BIRTH_CERTIFICATE, {REQUIRED_FIELD: 0, ATTACHMENT_FIELD: 0}
		)
		super().tearDownClass()

	def test_a_number_on_its_own_is_refused(self):
		user = fixtures.website_account("number.but.no.copy")

		with fixtures.acting_as(user), self.assertRaises(frappe.MandatoryError) as refusal:
			fixtures.submit_volunteer_form(
				self.branch(),
				id_type=BIRTH_CERTIFICATE,
				id_number=f"{fixtures.TEST_PREFIX}-BC-0002",
			)

		self.assertIn("copy", str(refusal.exception).lower())


class TestAgeExemptsADocument(RegistrationTestCase):
	"""A card that is not issued until sixteen cannot be a condition of a
	fourteen-year-old volunteering, and a society that has said so on the type
	should not have to keep a second list of exceptions."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_rule(BIRTH_CERTIFICATE, **{REQUIRED_FIELD: 1, MINIMUM_AGE_FIELD: 16})

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_value(
			IDENTIFICATION_TYPE_DOCTYPE,
			BIRTH_CERTIFICATE,
			{REQUIRED_FIELD: 0, MINIMUM_AGE_FIELD: 0},
		)
		super().tearDownClass()

	def test_an_applicant_below_the_age_is_not_asked_for_it(self):
		user = fixtures.website_account("too.young.for.the.card")

		with fixtures.acting_as(user):
			application = fixtures.submit_volunteer_form(
				self.branch(), applicant_date_of_birth=fixtures.minor_date_of_birth(14)
			)

		self.assertEqual(application.approval_state, "In Review")

	def test_an_applicant_above_it_still_is(self):
		user = fixtures.website_account("old.enough.for.the.card")

		with fixtures.acting_as(user), self.assertRaises(frappe.MandatoryError):
			fixtures.submit_volunteer_form(self.branch())


class TestTheFormIsToldTheSameRules(RegistrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		_rule(BIRTH_CERTIFICATE, **{REQUIRED_FIELD: 1, ATTACHMENT_FIELD: 1, MINIMUM_AGE_FIELD: 16})

	@classmethod
	def tearDownClass(cls):
		frappe.db.set_value(
			IDENTIFICATION_TYPE_DOCTYPE,
			BIRTH_CERTIFICATE,
			{REQUIRED_FIELD: 0, ATTACHMENT_FIELD: 0, MINIMUM_AGE_FIELD: 0},
		)
		super().tearDownClass()

	def test_application_options_carries_the_rules_the_server_enforces(self):
		"""One reading, so the wizard cannot ask for less than the server wants.

		Both this endpoint and `application._required_document_types` read the
		same three fields off the same rows, which is what stops a form
		discovering the requirement only at submission.
		"""
		from vmmsx.api import volunteer as volunteer_api

		options = volunteer_api.application_options()
		rule = next(row for row in options["id_types"] if row["key"] == BIRTH_CERTIFICATE)

		self.assertTrue(rule["is_required"])
		self.assertTrue(rule["requires_attachment"])
		self.assertEqual(rule["minimum_age"], 16)

	def test_an_unruled_type_reports_nothing_in_particular(self):
		from vmmsx.api import volunteer as volunteer_api

		options = volunteer_api.application_options()
		plain = next(row for row in options["id_types"] if row["key"] == fixtures.make_identification_type())

		self.assertFalse(plain["is_required"])
		self.assertFalse(plain["requires_attachment"])
		self.assertIsNone(plain["minimum_age"])
