# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The learning seam: config-driven, contained, and driven through the real LMS.

Nothing here is mocked. The site has an LMS installed, so these tests create a
real `LMS Course` and a real `LMS Enrollment` and save it — which fires the real
`doc_events` hook registered in `hooks.py`. What is asserted afterwards is a
`VMMS Certification` of the mapped type with an expiry computed from that type's
configured validity period.

Three claims:

1. **Completing a mapped course awards the mapped certification**, with the
   right expiry, through the hook rather than through a call the test made.
2. **The mapping is configuration.** Repointing one row at a different
   `VMMS Certification Type` changes what the same course awards, with no code
   change — and an unmapped course awards nothing at all.
3. **The LMS stops at the seam.** Nothing outside `services/learning.py` and one
   line of `hooks.py` names an LMS doctype. That is asserted in
   `test_delegation.py`, against the source; here the behavioural half is
   asserted — the certification carries no LMS identifier and the seam resolves
   people through Red Profile rather than around it.
"""

import frappe
from frappe.utils import add_days, getdate, today

from vmmsx.volunteer.services import certification, learning
from vmmsx.volunteer.tests import fixtures
from vmmsx.volunteer.tests.base import VolunteerTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []

COURSE_DOCTYPE = "LMS Course"
ENROLLMENT_DOCTYPE = "LMS Enrollment"


class LearningTestCase(VolunteerTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()

		fixtures.make_certification_type(fixtures.CERT_FIRST_AID, validity_days=365)
		fixtures.make_certification_type(fixtures.CERT_PSYCHOSOCIAL, validity_days=90)

		cls.courses = []

	@classmethod
	def tearDownClass(cls):
		for course in cls.courses:
			if frappe.db.exists(COURSE_DOCTYPE, course):
				frappe.delete_doc(COURSE_DOCTYPE, course, force=True)

		super().tearDownClass()

	@classmethod
	def make_course(cls, title: str) -> str:
		"""A real course in the real learning system.

		Built to the learning system's own rules — it insists on an instructor,
		so it gets one. Nothing about the course is vmmsx's; the seam only ever
		reads its docname.
		"""
		course = frappe.get_doc(
			{
				"doctype": COURSE_DOCTYPE,
				"title": f"{fixtures.TEST_PREFIX} {title}",
				"published": 1,
				"description": "A course these tests complete.",
				"short_introduction": "A course these tests complete.",
				"instructors": [{"instructor": "Administrator"}],
			}
		).insert(ignore_permissions=True)

		cls.courses.append(course.name)

		return course.name

	def learner(self, handle: str):
		"""A volunteer who can log in — the seam resolves User → Red Profile → them."""
		user = fixtures.make_user(handle, [fixtures.APPLICANT_ROLE])
		profile = fixtures.make_profile("Learning", handle.title(), user=user)
		volunteer = fixtures.make_volunteer(profile, self.society_a["ward"])

		return {"user": user, "profile": profile, "volunteer": volunteer}

	def complete(self, user: str, course: str, progress: float = 100):
		"""Enrol and finish, through the learning system's own doctype.

		Saving this is what fires the hook. Nothing in the test calls the seam.
		"""
		enrollment = frappe.get_doc(
			{
				"doctype": ENROLLMENT_DOCTYPE,
				"member": user,
				"course": course,
				"progress": progress,
			}
		).insert(ignore_permissions=True)

		return enrollment


class TestCompletingAMappedCourseAwards(LearningTestCase):
	def test_the_hook_awards_the_mapped_certification(self):
		person = self.learner("hook_learner")
		course = self.make_course("First Aid")
		fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		self.complete(person["user"], course)

		held = certification.held(person["volunteer"].name)

		self.assertEqual(len(held), 1, "completing a mapped course awarded nothing")
		self.assertEqual(held[0]["certification_type"], fixtures.CERT_FIRST_AID)

	def test_the_expiry_comes_from_the_types_configured_validity(self):
		person = self.learner("expiry_learner")
		course = self.make_course("First Aid Expiry")
		fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		self.complete(person["user"], course)

		held = certification.held(person["volunteer"].name)[0]

		self.assertEqual(getdate(held["expiry_date"]), getdate(add_days(held["completion_date"], 365)))

	def test_the_certification_records_which_mapping_awarded_it(self):
		person = self.learner("provenance_learner")
		course = self.make_course("First Aid Provenance")
		mapping = fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		self.complete(person["user"], course)

		held = certification.held(person["volunteer"].name)[0]

		self.assertEqual(held["source_mapping"], mapping.name)

	def test_an_unfinished_course_awards_nothing(self):
		person = self.learner("partial_learner")
		course = self.make_course("First Aid Partial")
		fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		self.complete(person["user"], course, progress=60)

		self.assertEqual(certification.held(person["volunteer"].name), [])

	def test_finishing_it_later_awards_it_then(self):
		"""The hook fires on every save, so progress reaching the end is enough."""
		person = self.learner("later_learner")
		course = self.make_course("First Aid Later")
		fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		enrollment = self.complete(person["user"], course, progress=60)
		self.assertEqual(certification.held(person["volunteer"].name), [])

		enrollment.progress = 100
		enrollment.save(ignore_permissions=True)

		self.assertEqual(len(certification.held(person["volunteer"].name)), 1)

	def test_completing_the_same_course_twice_awards_one_certification(self):
		"""Idempotent, and it has to be: the hook fires on every save."""
		person = self.learner("repeat_learner")
		course = self.make_course("First Aid Repeat")
		fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		enrollment = self.complete(person["user"], course)
		enrollment.save(ignore_permissions=True)
		enrollment.save(ignore_permissions=True)

		self.assertEqual(len(certification.held(person["volunteer"].name)), 1)


class TestTheMappingIsConfiguration(LearningTestCase):
	def test_an_unmapped_course_awards_nothing(self):
		person = self.learner("unmapped_learner")
		course = self.make_course("Unmapped")

		self.complete(person["user"], course)

		self.assertEqual(
			certification.held(person["volunteer"].name),
			[],
			"a course nobody mapped awarded a certification",
		)

	def test_repointing_the_mapping_changes_what_the_same_course_awards(self):
		"""Zero code diff. The society's choice of certification is the mechanism."""
		course = self.make_course("Repointable")
		fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		first = self.learner("before_repoint")
		self.complete(first["user"], course)

		self.assertEqual(
			certification.held(first["volunteer"].name)[0]["certification_type"],
			fixtures.CERT_FIRST_AID,
		)

		# One field on one configuration record.
		fixtures.make_mapping(course, fixtures.CERT_PSYCHOSOCIAL)

		second = self.learner("after_repoint")
		self.complete(second["user"], course)

		self.assertEqual(
			certification.held(second["volunteer"].name)[0]["certification_type"],
			fixtures.CERT_PSYCHOSOCIAL,
		)

	def test_the_new_certification_carries_the_new_types_expiry(self):
		"""Repointing changes the validity period too, because the type carries it."""
		course = self.make_course("Repointable Expiry")
		fixtures.make_mapping(course, fixtures.CERT_PSYCHOSOCIAL)

		person = self.learner("repoint_expiry")
		self.complete(person["user"], course)

		held = certification.held(person["volunteer"].name)[0]

		self.assertEqual(getdate(held["expiry_date"]), getdate(add_days(held["completion_date"], 90)))

	def test_an_inactive_mapping_awards_nothing(self):
		course = self.make_course("Switched Off")
		fixtures.make_mapping(course, fixtures.CERT_FIRST_AID, is_active=0)

		person = self.learner("inactive_mapping")
		self.complete(person["user"], course)

		self.assertEqual(certification.held(person["volunteer"].name), [])

	def test_switching_a_mapping_off_does_not_revoke_what_it_awarded(self):
		"""It stops acting in future; it does not rewrite the past."""
		course = self.make_course("Switch Later")
		mapping = fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		person = self.learner("switch_later")
		self.complete(person["user"], course)

		self.assertEqual(len(certification.held(person["volunteer"].name)), 1)

		mapping.is_active = 0
		mapping.save()

		self.assertEqual(len(certification.held(person["volunteer"].name)), 1)


class TestIdentityCrossesThroughRedProfile(LearningTestCase):
	def test_a_learner_with_no_red_profile_awards_nothing(self):
		"""Somebody doing a course who is not in core's spine is not our business."""
		user = fixtures.make_user("no_profile_learner", [fixtures.APPLICANT_ROLE])
		course = self.make_course("No Profile")
		fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		before = frappe.db.count(fixtures.CERTIFICATION_DOCTYPE)
		self.complete(user, course)

		self.assertEqual(frappe.db.count(fixtures.CERTIFICATION_DOCTYPE), before)

	def test_a_profile_with_no_volunteer_awards_nothing(self):
		"""A member doing a course does not thereby become a volunteer."""
		user = fixtures.make_user("member_learner", [fixtures.APPLICANT_ROLE])
		fixtures.make_profile("Member", "Learner", user=user)
		course = self.make_course("Member Course")
		fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		before = frappe.db.count(fixtures.CERTIFICATION_DOCTYPE)
		self.complete(user, course)

		self.assertEqual(frappe.db.count(fixtures.CERTIFICATION_DOCTYPE), before)

	def test_the_seam_resolves_through_the_profile_not_around_it(self):
		person = self.learner("resolution_learner")

		self.assertEqual(
			learning.volunteer_for_user(person["user"]),
			person["volunteer"].name,
		)
		self.assertIsNone(learning.volunteer_for_user("nobody@nowhere.invalid"))


class TestNoLMSModelReachesOurDomain(LearningTestCase):
	def test_the_certification_carries_no_lms_identifier(self):
		"""Our record names our mapping, not the learning system's enrollment."""
		person = self.learner("no_leak_learner")
		course = self.make_course("No Leak")
		mapping = fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		self.complete(person["user"], course)

		held = frappe.get_doc(
			fixtures.CERTIFICATION_DOCTYPE, certification.held(person["volunteer"].name)[0]["name"]
		)

		self.assertEqual(held.source_mapping, mapping.name)
		self.assertNotIn("enrollment", {field.fieldname for field in held.meta.fields})

	def test_the_mapping_stores_the_course_as_data_not_as_a_link(self):
		"""A Link would be a schema dependency on the learning app."""
		field = frappe.get_meta(fixtures.MAPPING_DOCTYPE).get_field("external_course")

		self.assertEqual(field.fieldtype, "Data")
		self.assertFalse(field.options)

	def test_the_seam_reports_the_learning_system_honestly(self):
		self.assertEqual(learning.is_available(), "lms" in frappe.get_installed_apps())


class TestCatchingUp(LearningTestCase):
	def test_sync_awards_a_course_finished_before_the_mapping_existed(self):
		"""The case the hook cannot cover, and the reason `sync_volunteer` exists."""
		person = self.learner("catch_up_learner")
		course = self.make_course("Finished Early")

		# Finished with no mapping in place: the hook fires and awards nothing.
		self.complete(person["user"], course)
		self.assertEqual(certification.held(person["volunteer"].name), [])

		# The society writes the mapping afterwards.
		fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		summary = learning.sync_volunteer(person["volunteer"])

		self.assertEqual(len(summary["awarded"]), 1)
		self.assertEqual(
			certification.held(person["volunteer"].name)[0]["certification_type"],
			fixtures.CERT_FIRST_AID,
		)

	def test_sync_is_idempotent(self):
		person = self.learner("sync_twice_learner")
		course = self.make_course("Sync Twice")
		fixtures.make_mapping(course, fixtures.CERT_FIRST_AID)

		self.complete(person["user"], course)
		learning.sync_volunteer(person["volunteer"])
		learning.sync_volunteer(person["volunteer"])

		self.assertEqual(len(certification.held(person["volunteer"].name)), 1)

	def test_sync_for_a_volunteer_with_no_login_reads_nothing(self):
		profile = fixtures.make_profile("No", "Login")
		volunteer = fixtures.make_volunteer(profile, self.society_a["ward"])

		summary = learning.sync_volunteer(volunteer)

		self.assertEqual(summary["read"], 0)
		self.assertEqual(summary["awarded"], [])


class TestTheAwardedCertificationBehavesLikeAnyOther(LearningTestCase):
	def test_a_course_finished_long_ago_awards_a_lapsed_certification(self):
		"""The seam writes a date; the lapse is derived from it like any other."""
		person = self.learner("old_completion")
		course = self.make_course("Long Ago")
		mapping = fixtures.make_mapping(course, fixtures.CERT_PSYCHOSOCIAL)

		awarded = learning.record_completion(
			learner=person["user"],
			external_course=course,
			completed_on=add_days(today(), -200),
		)

		self.assertEqual(awarded["mapping"], mapping.name)

		held = frappe.get_doc(fixtures.CERTIFICATION_DOCTYPE, awarded["certification"])

		self.assertTrue(certification.is_lapsed(held))

		# Active, so that the deployability answer below is about the lapse and
		# not about the volunteer's own status.
		frappe.db.set_value(fixtures.VOLUNTEER_DOCTYPE, person["volunteer"].name, "status", "Active")
		person["volunteer"].reload()

		self.assertFalse(certification.is_deployable(person["volunteer"]))
