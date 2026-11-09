# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A volunteer application needs one education entry, with institution and level.

Required at submission, the moment the applicant can still supply it, and not at
approval: records imported from the old system arrive without one and a branch
must still be able to approve them.
"""

import frappe

from vmmsx.registration.tests import fixtures
from vmmsx.registration.tests.base import RegistrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []


class TestEducationRequired(RegistrationTestCase):
	def test_an_application_without_education_is_refused(self):
		with self.assertRaisesRegex(frappe.MandatoryError, "Add your education"):
			self.register_as_volunteer("edu.none", background={"education": []})

	def test_an_entry_without_a_level_is_refused(self):
		with self.assertRaisesRegex(frappe.MandatoryError, "Add your education"):
			self.register_as_volunteer(
				"edu.nolevel",
				background={"education": [{"institution": "Alliance High School", "level": None}]},
			)

	def test_an_entry_with_institution_and_level_is_enough(self):
		_, application = self.register_as_volunteer(
			"edu.given",
			background={"education": fixtures.education(qualification=None)},
		)

		self.assertIn(application.approval_state, ("Submitted", "In Review"))
