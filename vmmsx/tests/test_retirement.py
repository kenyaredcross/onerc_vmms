# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Nothing on this site still points at what was retired, and nothing was forked.

Two invariants, both of which are easy to satisfy on the day and easy to break
six months later, and neither of which produces an error when broken — which is
the only reason they are asserted rather than remembered.

**1. `VMMS Project` is gone, and gone completely.** Deleting a doctype does not
delete the things that named it. A Link field whose `options` still say
`VMMS Project` renders as a picker over nothing; a Property Setter or a Custom
Field naming it is metadata pointing at a table that is not there. The scan below
walks every place a doctype name can be written down and expects the retired one
in none of them.

**2. Every field this app adds to somebody else's doctype is a Custom Field.**
Locked decision 4: changes to standard ERPNext and HRMS doctypes are owned by
vmmsx through custom fields, child doctypes, fixtures, hooks, patches and
permission hooks — never by editing their source. A field added by editing
`erpnext/projects/doctype/project/project.json` would work perfectly until the
next `bench update` silently reverted it, taking the column and everybody's data
with it. The check is direct: every extension named in the installers has to be
a `Custom Field` row, and a standard field carrying one of those names would mean
somebody had forked upstream.
"""

import frappe
from frappe.tests import IntegrationTestCase

from vmmsx.setup import job_applicant_fields, job_opening_fields, project_fields

EXTRA_TEST_RECORD_DEPENDENCIES = []

RETIRED = "VMMS Project"


class TestTheRetiredProjectIsGone(IntegrationTestCase):
	def test_the_doctype_is_not_on_the_site(self):
		self.assertFalse(frappe.db.exists("DocType", RETIRED))

	def test_no_field_anywhere_links_to_it(self):
		"""A Link whose target does not exist is a picker over nothing."""
		offenders = frappe.get_all(
			"DocField", filters={"options": RETIRED}, fields=["parent", "fieldname"]
		)

		self.assertEqual(offenders, [])

	def test_no_custom_field_does_either(self):
		offenders = frappe.get_all(
			"Custom Field", filters={"options": RETIRED}, fields=["dt", "fieldname"]
		)

		self.assertEqual(offenders, [])

	def test_no_property_setter_still_names_it(self):
		self.assertEqual(frappe.get_all("Property Setter", filters={"doc_type": RETIRED}), [])

	def test_the_terms_of_reference_points_at_erpnexts_project(self):
		"""The link was repointed rather than blanked — `adopt_standard_project`
		says why."""
		self.assertEqual(
			frappe.get_meta("VMMS Terms of Reference").get_field("project").options, "Project"
		)

	def test_every_terms_of_reference_that_names_a_project_names_a_real_one(self):
		"""The migration's own result, asserted against the site rather than
		against the patch."""
		named = frappe.get_all(
			"VMMS Terms of Reference",
			filters=[["VMMS Terms of Reference", "project", "is", "set"]],
			pluck="project",
		)
		real = set(frappe.get_all("Project", pluck="name"))

		self.assertEqual([name for name in named if name not in real], [])


class TestUpstreamIsNotForked(IntegrationTestCase):
	"""Locked decision 4, asserted rather than remembered.

	Each case walks one installer's own field list, so adding a field to an
	installer without adding it as a Custom Field fails here rather than on the
	next `bench update`.
	"""

	def assert_all_custom(self, doctype: str, fieldnames: list[str]) -> None:
		meta = frappe.get_meta(doctype)
		custom = {
			row.fieldname
			for row in frappe.get_all("Custom Field", filters={"dt": doctype}, fields=["fieldname"])
		}

		for fieldname in fieldnames:
			field = meta.get_field(fieldname)

			if not field:
				# Skipped on purpose by an installer whose `requires` doctype is
				# not on this site. Absent is fine; forked is not.
				continue

			self.assertIn(
				fieldname,
				custom,
				f"{doctype}.{fieldname} is a standard field — upstream has been forked",
			)

	def test_erpnexts_project_is_extended_and_not_edited(self):
		self.assert_all_custom(
			project_fields.PROJECT_DOCTYPE, [field["fieldname"] for field in project_fields.FIELDS]
		)

	def test_hrms_job_opening_is_extended_and_not_edited(self):
		if not job_opening_fields.is_available():
			self.skipTest("HRMS is not installed on this site")

		self.assert_all_custom(
			job_opening_fields.OPENING_DOCTYPE,
			[field["fieldname"] for field in job_opening_fields.VMMS_FIELDS],
		)

	def test_hrms_job_applicant_is_extended_and_not_edited(self):
		if not job_applicant_fields.is_available():
			self.skipTest("HRMS is not installed on this site")

		self.assert_all_custom(
			job_applicant_fields.APPLICANT_DOCTYPE,
			[field["fieldname"] for field in job_applicant_fields.FIELDS],
		)

	def test_every_doctype_vmmsx_ships_belongs_to_a_vmmsx_module(self):
		"""The other half of the same rule: this app declares no doctype inside
		another app's module, which is how a fork starts looking like a feature.
		"""
		ours = set(frappe.get_all("Module Def", filters={"app_name": "vmmsx"}, pluck="name"))
		strays = frappe.get_all(
			"DocType",
			filters={"module": ("not in", ours), "custom": 0},
			or_filters={"name": ("like", "VMMS %")},
			fields=["name", "module"],
		)

		self.assertEqual([row["name"] for row in strays], [])
