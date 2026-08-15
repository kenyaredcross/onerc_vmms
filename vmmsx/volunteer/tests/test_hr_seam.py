# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The HR seam: one link, one direction, and identity that does not cross it.

Frappe HR is installed on this site, so these tests run against the real
`Employee` doctype rather than a stand-in.

What is asserted:

1. **Direction.** The link is `VMMS Volunteer.employee` → `Employee`. vmmsx
   points at HR. HR does not point back, is not modified, and does not import
   this app.
2. **Provisioning respects the switch.** Off — the shipped state — nothing is
   created at all. On, an Employee HR already holds for that person is adopted
   rather than duplicated.
3. **Identity is read from Red Profile, never from Employee.** Including in the
   case that matters most: when the two disagree, the volunteer's name is Red
   Profile's answer, not HR's.
4. **vmmsx will not invent identity to satisfy HR's schema.** HR requires a
   gender and a date of birth. Core's Red Profile carries both, and vmmsx now
   *displays* both on the volunteer page — but `hr._OUTBOUND`, the list of what
   this seam hands over, names neither, so there is still nothing to give HR.
   Where HR refuses for want of them, the refusal is logged and the volunteer is
   unaffected — which is the correct outcome, not a gap. A society that wants HR
   records completes them in HR.
5. **Exactly one thing is read back, and it is not identity.** `hr._INBOUND` is
   an allow-list naming the Employee's department and nothing else, read so that
   stipend paperwork can record which head of department it will eventually
   route to. Asking for anything outside it is refused, and an unlinked
   volunteer reads back None rather than throwing.

The source-level containment — that only `services/hr.py` names `Employee`, and
that no file anywhere names HR's employment model — is asserted in
`test_delegation.py`.
"""

import frappe

from vmmsx.volunteer.services import hr, identity
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

EMPLOYEE_DOCTYPE = "Employee"


class HRTestCase(VolunteerTestCase):
	def setUp(self):
		super().setUp()
		# Every test states the provisioning it wants; put it back afterwards so
		# the shipped-off default does not leak between them.
		self.addCleanup(fixtures.set_provisioning, False, None)

	def volunteer(self, handle: str, with_user: bool = True):
		user = fixtures.make_user(handle, [fixtures.APPLICANT_ROLE]) if with_user else None
		profile = fixtures.make_profile("HR", handle.title(), user=user)
		volunteer = fixtures.make_volunteer(profile, self.society_a["ward"])

		return {"user": user, "profile": profile, "volunteer": volunteer}

	def employee_count(self) -> int:
		return frappe.db.count(EMPLOYEE_DOCTYPE)

	def _company(self) -> str | None:
		return frappe.db.get_value("Company", {}, "name")

	def _make_employee(self, user: str | None, first_name: str) -> str:
		"""An Employee HR already holds, created by HR's own rules.

		Everything HR insists on is supplied here — including the gender and the
		date of birth that vmmsx does not hold — because this is HR's record,
		created the way HR creates one.
		"""
		company = self._company()

		if not company:
			# HR's Employee requires a Company, and on a site where ERPNext/HR
			# setup has not been completed there is none — and one cannot be
			# created either, because HR's own Company hook expects a field its
			# setup installs. That is a property of the site, not of this seam,
			# and it is skipped loudly rather than worked around: fabricating an
			# Employee past HR's own validation is precisely what this module
			# refuses to do in production.
			self.skipTest(
				"no Company on this site, so HR cannot hold an Employee record;"
				" complete ERPNext/HR setup to exercise the adoption and creation paths"
			)

		gender = frappe.db.get_value("Gender", {}, "name")

		if not gender:
			gender = (
				frappe.get_doc({"doctype": "Gender", "gender": "Other"}).insert(ignore_permissions=True).name
			)

		employee = frappe.get_doc(
			{
				"doctype": EMPLOYEE_DOCTYPE,
				"first_name": f"{fixtures.TEST_PREFIX} {first_name}",
				"company": company,
				"gender": gender,
				"date_of_birth": "1990-01-01",
				"date_of_joining": "2020-01-01",
				"status": "Active",
				"user_id": user,
			}
		).insert(ignore_permissions=True)

		self.addCleanup(frappe.delete_doc, EMPLOYEE_DOCTYPE, employee.name, force=True)

		return employee.name


class TestTheLinkPointsOneWay(HRTestCase):
	def test_the_volunteer_links_to_the_employee(self):
		"""The declared direction, read from the schema rather than asserted in prose."""
		field = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE).get_field("employee")

		self.assertIsNotNone(field, "the HR seam field is missing")
		self.assertEqual(field.fieldtype, "Link")
		self.assertEqual(field.options, EMPLOYEE_DOCTYPE)
		self.assertTrue(field.read_only, "the link is engine-written, not typed")

	def test_the_employee_does_not_link_back(self):
		"""HR knows nothing about vmmsx, which is what makes the seam removable."""
		offenders = [
			field.fieldname
			for field in frappe.get_meta(EMPLOYEE_DOCTYPE).fields
			if (field.options or "").startswith("VMMS ")
		]

		self.assertEqual(offenders, [], "HR has acquired a link into vmmsx")

	def test_the_link_is_nullable_and_empty_is_ordinary(self):
		person = self.volunteer("nullable")

		self.assertIsNone(hr.linked_employee(person["volunteer"]))
		self.assertFalse(frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE).get_field("employee").reqd)

	def test_the_read_surface_is_the_link_and_one_allow_listed_field(self):
		"""`linked_employee` returns a docname; `read_back` reads `hr._INBOUND` and no more.

		The allow-list is asserted rather than described, so widening it is a
		deliberate edit to this test as well as to the seam. Identity is not on
		it and must not become so: who somebody is stays Red Profile's answer.
		"""
		person = self.volunteer("read_surface")

		self.assertIn(hr.linked_employee(person["volunteer"]), (None,))
		self.assertEqual(hr._INBOUND, ("department",))

		for field in identity._READABLE:
			self.assertNotIn(field, hr._INBOUND, "identity must never be read back from HR")

	def test_reading_back_anything_outside_the_allow_list_is_refused(self):
		"""Refused out loud, rather than fetched because the caller asked nicely."""
		person = self.volunteer("read_back_refused")

		with self.assertRaises(PermissionError):
			hr.read_back(person["volunteer"], "employee_name")

	def test_an_unlinked_volunteer_reads_back_nothing_rather_than_throwing(self):
		"""No HR record is the ordinary case, not an error."""
		person = self.volunteer("read_back_unlinked")

		self.assertIsNone(hr.read_back(person["volunteer"], "department"))


class TestProvisioningRespectsTheSwitch(HRTestCase):
	def test_the_switch_ships_off(self):
		from vmmsx.volunteer.services import society

		fixtures.set_provisioning(False, None)

		self.assertFalse(society.provisions_employees())

	def test_with_the_switch_off_nothing_is_created(self):
		fixtures.set_provisioning(False, None)
		person = self.volunteer("switch_off")
		before = self.employee_count()

		outcome = hr.provision(person["volunteer"])

		self.assertEqual(outcome["outcome"], hr.OUTCOME_DISABLED)
		self.assertIsNone(outcome["employee"])
		self.assertEqual(self.employee_count(), before, "an Employee was created with the switch off")
		self.assertIsNone(hr.linked_employee(person["volunteer"]))

	def test_accepting_a_volunteer_with_the_switch_off_creates_no_employee(self):
		"""The end-to-end version: through acceptance, not through the service."""
		from vmmsx.volunteer.services import application as application_service

		fixtures.set_provisioning(False, None)
		fixtures.make_workflow()
		self.addCleanup(self._drop_workflow)

		person = self.volunteer("accept_off")
		before = self.employee_count()

		application = fixtures.make_application(person["profile"], self.society_a["ward"])
		result = application_service.submit(application)

		self.assertEqual(self.employee_count(), before)

		if result.get("hr"):
			self.assertEqual(result["hr"]["outcome"], hr.OUTCOME_DISABLED)

	def test_with_the_switch_on_but_no_company_nothing_is_created(self):
		"""HR cannot make one without a company and vmmsx will not guess one."""
		fixtures.set_provisioning(True, None)
		person = self.volunteer("no_company")
		before = self.employee_count()

		outcome = hr.provision(person["volunteer"])

		self.assertEqual(outcome["outcome"], hr.OUTCOME_NO_COMPANY)
		self.assertEqual(self.employee_count(), before)

	def test_the_skipped_provisioning_is_logged_rather_than_silent(self):
		"""A society that switched it on and is getting nothing must be able to see why."""
		fixtures.set_provisioning(True, None)
		person = self.volunteer("logged_skip")
		before = frappe.db.count("Error Log", {"method": hr.PROVISIONING_LOG_TITLE})

		hr.provision(person["volunteer"])

		self.assertGreater(
			frappe.db.count("Error Log", {"method": hr.PROVISIONING_LOG_TITLE}),
			before,
			"provisioning was skipped silently",
		)

	def test_provisioning_is_idempotent(self):
		person = self.volunteer("idempotent")
		employee = self._make_employee(person["user"], "Idempotent")

		fixtures.set_provisioning(True, self._company())
		hr.provision(person["volunteer"])

		second = hr.provision(person["volunteer"])

		self.assertEqual(second["outcome"], hr.OUTCOME_ALREADY_LINKED)
		self.assertEqual(second["employee"], employee)

	def _drop_workflow(self):
		existing = frappe.db.get_value(
			fixtures.WORKFLOW_DOCTYPE, {"workflow_for": fixtures.APPLICATION_DOCTYPE}, "name"
		)

		if existing:
			frappe.delete_doc(fixtures.WORKFLOW_DOCTYPE, existing, force=True)


class TestAdoptionBeatsDuplication(HRTestCase):
	def test_an_existing_hr_record_is_adopted_not_duplicated(self):
		"""A duplicate Employee is a worse outcome than no Employee."""
		person = self.volunteer("adopt")
		employee = self._make_employee(person["user"], "Adopt")

		fixtures.set_provisioning(True, self._company())
		before = self.employee_count()

		outcome = hr.provision(person["volunteer"])

		self.assertEqual(outcome["outcome"], hr.OUTCOME_ADOPTED)
		self.assertEqual(outcome["employee"], employee)
		self.assertEqual(self.employee_count(), before, "provisioning created a second Employee")

	def test_the_link_is_recorded_on_the_volunteer(self):
		person = self.volunteer("adopt_link")
		employee = self._make_employee(person["user"], "Adopt Link")

		fixtures.set_provisioning(True, self._company())
		hr.provision(person["volunteer"])

		self.assertEqual(
			frappe.db.get_value(fixtures.VOLUNTEER_DOCTYPE, person["volunteer"].name, "employee"),
			employee,
		)

	def test_adoption_matches_on_the_login_and_not_on_a_name(self):
		"""Two people share a name; matching identity by string links the wrong person."""
		person = self.volunteer("adopt_by_user")
		self._make_employee(None, person["volunteer"].red_profile)

		fixtures.set_provisioning(True, self._company())
		outcome = hr.provision(person["volunteer"])

		self.assertNotEqual(
			outcome["outcome"],
			hr.OUTCOME_ADOPTED,
			"an Employee with no user_id was matched by something other than the login",
		)


class TestIdentityNeverCrossesTheSeam(HRTestCase):
	def test_the_volunteer_holds_no_identity_field_of_its_own(self):
		"""Not a stored one, and not a fetched one either."""
		meta = frappe.get_meta(fixtures.VOLUNTEER_DOCTYPE)
		identity_names = ("first_name", "last_name", "full_name", "email", "phone", "employee_name")

		for fieldname in identity_names:
			self.assertIsNone(
				meta.get_field(fieldname), f"the volunteer has grown an identity field: {fieldname}"
			)

		self.assertEqual(
			[field.fieldname for field in meta.fields if field.fetch_from],
			[],
			"the volunteer fetches a field from somewhere — identity by another name",
		)

	def test_the_name_comes_from_red_profile(self):
		person = self.volunteer("named")
		expected = frappe.db.get_value("Red Profile", person["profile"], "full_name")

		self.assertEqual(identity.display_name(person["volunteer"]), expected)

	def test_it_is_red_profiles_answer_even_when_hr_disagrees(self):
		"""The case that decides it. Two records, one spine, and it is not HR's.

		The Employee is deliberately given a different name from the Red Profile,
		then linked. Everything this app reports about who the person is must
		still be the profile's answer.
		"""
		person = self.volunteer("disagreeing")
		employee = self._make_employee(person["user"], "Wrong Name From HR")

		fixtures.set_provisioning(True, self._company())
		hr.provision(person["volunteer"])
		person["volunteer"].reload()

		self.assertEqual(person["volunteer"].employee, employee)

		hr_name = frappe.db.get_value(EMPLOYEE_DOCTYPE, employee, "employee_name")
		profile_name = frappe.db.get_value("Red Profile", person["profile"], "full_name")

		self.assertNotEqual(hr_name, profile_name, "the fixture failed to make them disagree")
		self.assertEqual(identity.display_name(person["volunteer"]), profile_name)

	def test_the_dto_reports_the_link_and_the_profiles_identity(self):
		from vmmsx.volunteer.services import volunteer as volunteer_service

		person = self.volunteer("dto")
		employee = self._make_employee(person["user"], "DTO")

		fixtures.set_provisioning(True, self._company())
		hr.provision(person["volunteer"])
		person["volunteer"].reload()

		dto = volunteer_service.profile_dto(person["volunteer"])

		self.assertEqual(dto["employee"], employee)
		self.assertEqual(dto["full_name"], frappe.db.get_value("Red Profile", person["profile"], "full_name"))
		# No employment data anywhere in what this app hands out.
		self.assertEqual(
			{key for key in dto if key in ("salary", "designation", "department", "company")}, set()
		)


class TestVmmsxWillNotInventIdentity(HRTestCase):
	"""HR requires a gender and a date of birth. vmmsx passes on neither."""

	def test_vmmsx_does_not_send_the_two_fields_hr_insists_on(self):
		"""The premise, asserted so the tests below cannot pass for a stale reason.

		This assertion has now moved twice, and where it sits is the point. It
		first asserted that core's Red Profile held neither field; core added
		both to the identity spine, so that premise went. It then asserted that
		neither was in `identity._READABLE`; the volunteer page needs to display
		both, so that premise has gone too.

		What has not changed is the behaviour, because the guarantee was never
		really about what this app can *see*. It is about what it *sends*. That
		is `hr._OUTBOUND`, the list of fields this seam hands to an employment
		register, and pinning the assertion there is what keeps it true the next
		time somebody widens a display surface.
		"""
		self.assertNotIn("gender", hr._OUTBOUND)
		self.assertNotIn("date_of_birth", hr._OUTBOUND)

	def test_the_seam_sends_less_than_the_app_may_display(self):
		"""Showing a person-fact and exporting it are different decisions.

		If these two lists were ever the same list again, widening a card would
		silently widen what reaches payroll.
		"""
		self.assertTrue(set(hr._OUTBOUND) < set(identity._READABLE))

	def test_neither_field_reaches_hr_even_when_the_profile_has_one(self):
		"""Set them on the spine, and the seam still does not carry them.

		The read is narrowed rather than the result filtered, so `_create` never
		holds either value in the first place.
		"""
		person = self.volunteer("spine_has_them")
		gender = frappe.db.get_value("Gender", {}, "name") or (
			frappe.get_doc({"doctype": "Gender", "gender": "Other"}).insert(ignore_permissions=True).name
		)

		frappe.db.set_value(
			"Red Profile", person["profile"], {"gender": gender, "date_of_birth": "1990-01-01"}
		)

		outbound = identity.read(person["volunteer"], hr._OUTBOUND)

		self.assertNotIn("gender", outbound)
		self.assertNotIn("date_of_birth", outbound)

		# And the page still gets what the page was widened for, so this test
		# cannot start passing because the widening was quietly reverted.
		self.assertEqual(identity.read(person["volunteer"])["gender"], gender)

	def test_creating_an_employee_is_declined_rather_than_faked(self):
		"""HR refuses; vmmsx logs it and leaves the volunteer entirely alone.

		This is the seam working, not failing. Filling in a placeholder date of
		birth to get past HR's validation would be vmmsx inventing a fact about a
		person, which is exactly what the identity rule forbids.
		"""
		company = self._company()

		if not company:
			self.skipTest("no Company on this site")

		person = self.volunteer("not_invented")
		fixtures.set_provisioning(True, company)
		before = self.employee_count()

		outcome = hr.provision(person["volunteer"])

		self.assertEqual(outcome["outcome"], hr.OUTCOME_HR_REFUSED)
		self.assertEqual(self.employee_count(), before)
		self.assertIsNone(hr.linked_employee(person["volunteer"]))

	def test_the_refusal_does_not_fail_the_volunteer(self):
		"""An HR misconfiguration must not be able to fail an approval."""
		company = self._company()

		if not company:
			self.skipTest("no Company on this site")

		person = self.volunteer("unaffected")
		fixtures.set_provisioning(True, company)

		hr.provision(person["volunteer"])

		self.assertTrue(frappe.db.exists(fixtures.VOLUNTEER_DOCTYPE, person["volunteer"].name))
		self.assertIn("volunteer", self.affiliation_types(person["profile"]))

	def test_the_refusal_is_logged_with_hrs_own_complaint(self):
		company = self._company()

		if not company:
			self.skipTest("no Company on this site")

		person = self.volunteer("logged_refusal")
		fixtures.set_provisioning(True, company)
		before = frappe.db.count("Error Log", {"method": hr.PROVISIONING_LOG_TITLE})

		hr.provision(person["volunteer"])

		self.assertGreater(frappe.db.count("Error Log", {"method": hr.PROVISIONING_LOG_TITLE}), before)
