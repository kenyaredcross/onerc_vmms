# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What vmmsx adds to HRMS's `Job Applicant`, and what it deliberately leaves alone.

HRMS owns the applicant: the name, the email, the CV, the status, the interview
rounds, the offer. **None of that is touched.** An employment application on this
site behaves exactly as HRMS built it, including the public web form, and that is
the point rather than an accident — a society running recruitment in HRMS should
not find its recruitment changed because it also runs volunteering.

What is added is everything a *volunteering* application needs and HRMS has
nowhere for:

1. **Who the applicant is in this system.** An approved volunteer applying for a
   volunteering role is already a person the society knows, with a Red Profile
   and a branch. Storing the two links is what lets an application be read back
   as "this volunteer applied" rather than as a name and an email that happen to
   match one.
2. **The answers.** HRMS has a cover letter and a CV; a society screening
   volunteers asks questions, and the answers have to sit with the questions as
   they were asked. `VMMS Application Answer` is that table.
3. **Withdrawal.** HRMS's statuses cover what the *society* decides — Open,
   Shortlisted, Hold, Accepted, Rejected — and have no word for the applicant
   changing their mind. Rejecting somebody who withdrew would put a decision the
   society never made into their record.
4. **What the application became.** An accepted volunteer on a deployment opening
   turns into a deployment assignment, and on a task-based opening into a task.
   Both links are recorded so the conversion is visible and cannot happen twice.

**Every field is a Custom Field owned by vmmsx**, prefixed, and installed on
every migrate for the reasons `setup/project_fields.py` and
`setup/job_opening_fields.py` both give. Dormant when HRMS is absent: a society
running volunteering without a recruitment module is ordinary, not
half-installed.
"""

import frappe

APPLICANT_DOCTYPE = "Job Applicant"
HRMS_APP = "hrms"

# HRMS's own statuses, spelled here so nothing in this app types one as a literal
# and so a rename upstream fails loudly in one place. vmmsx adds none of them:
# the withdrawal is a pair of fields beside the status, not a sixth value, so
# HRMS's own screens and reports keep working on a vocabulary they own.
STATUS_OPEN = "Open"
STATUS_SHORTLISTED = "Shortlisted"
STATUS_HOLD = "Hold"
STATUS_ACCEPTED = "Accepted"
STATUS_REJECTED = "Rejected"

VOLUNTEER_FIELD = "vmms_volunteer"
PROFILE_FIELD = "vmms_red_profile"
GEO_NODE_FIELD = "vmms_geo_node"
ANSWERS_FIELD = "vmms_answers"
WITHDRAWN_FIELD = "vmms_withdrawn_on"

FIELDS = (
	{
		"fieldname": "vmms_volunteering_section",
		"label": "Volunteering",
		"fieldtype": "Section Break",
		"insert_after": "status",
		"depends_on": f"eval:doc.{VOLUNTEER_FIELD}",
	},
	{
		"fieldname": VOLUNTEER_FIELD,
		"label": "Volunteer",
		"fieldtype": "Link",
		"options": "VMMS Volunteer",
		"insert_after": "vmms_volunteering_section",
		"read_only": 1,
		"in_standard_filter": 1,
		"description": (
			"The volunteer record behind this application, where the applicant is one of the"
			" society's own. Written when the application is made and never afterwards. Owned"
			" by vmmsx."
		),
	},
	{
		"fieldname": PROFILE_FIELD,
		"label": "Red Profile",
		"fieldtype": "Link",
		"options": "Red Profile",
		"insert_after": VOLUNTEER_FIELD,
		"read_only": 1,
		"description": "The identity record the name, email and phone were taken from. Owned by vmmsx.",
	},
	{
		"fieldname": "vmms_column_break_volunteering",
		"fieldtype": "Column Break",
		"insert_after": PROFILE_FIELD,
	},
	{
		"fieldname": GEO_NODE_FIELD,
		"label": "Geo Node",
		"fieldtype": "Link",
		"options": "Geo Node",
		"insert_after": "vmms_column_break_volunteering",
		"read_only": 1,
		"description": (
			"Where this application sits in the organisation, copied from the opening. Owned by"
			" vmmsx."
		),
	},
	{
		"fieldname": WITHDRAWN_FIELD,
		"label": "Withdrawn On",
		"fieldtype": "Datetime",
		"insert_after": GEO_NODE_FIELD,
		"read_only": 1,
		"description": (
			"When the applicant took the application back. Their decision, kept apart from the"
			" society's: rejecting somebody who withdrew would put a decision nobody made into"
			" their record. Owned by vmmsx."
		),
	},
	{
		"fieldname": "vmms_withdrawal_reason",
		"label": "Withdrawal Reason",
		"fieldtype": "Small Text",
		"insert_after": WITHDRAWN_FIELD,
		"read_only": 1,
		"depends_on": f"eval:doc.{WITHDRAWN_FIELD}",
		"description": "Their own words. Owned by vmmsx.",
	},
	{
		"fieldname": "vmms_answers_section",
		"label": "Screening Answers",
		"fieldtype": "Section Break",
		"insert_after": "vmms_withdrawal_reason",
		"depends_on": f"eval:doc.{ANSWERS_FIELD} && doc.{ANSWERS_FIELD}.length",
	},
	{
		"fieldname": ANSWERS_FIELD,
		"label": "Answers",
		"fieldtype": "Table",
		"options": "VMMS Application Answer",
		"insert_after": "vmms_answers_section",
		"description": (
			"What the applicant answered, with each question kept as it was asked. Owned by"
			" vmmsx."
		),
	},
	{
		"fieldname": "vmms_outcome_section",
		"label": "What It Became",
		"fieldtype": "Section Break",
		"insert_after": ANSWERS_FIELD,
		"depends_on": "eval:doc.vmms_deployment_assignment || doc.vmms_task",
	},
	{
		"fieldname": "vmms_deployment_assignment",
		"label": "Deployment Assignment",
		"fieldtype": "Link",
		"options": "VMMS Deployment Assignment",
		"insert_after": "vmms_outcome_section",
		"read_only": 1,
		"no_copy": 1,
		"description": (
			"The assignment this accepted application became. Written once; the conversion"
			" refuses to run twice. Owned by vmmsx."
		),
	},
	{
		"fieldname": "vmms_task",
		"label": "Task",
		"fieldtype": "Link",
		"options": "VMMS Task",
		"insert_after": "vmms_deployment_assignment",
		"read_only": 1,
		"no_copy": 1,
		"description": "The task this accepted application became. Owned by vmmsx.",
	},
)


def is_available() -> bool:
	"""Is HRMS installed on *this* site?

	`get_installed_apps` rather than an import, for the reason
	`hr/services/openings.py` gives: an app can sit in the bench without being
	installed on the site, and that is the case that actually bites.
	"""
	return HRMS_APP in frappe.get_installed_apps()


def install() -> None:
	"""Create what is absent and touch nothing that is there.

	Guarded per field, so a migrate interrupted half way finishes on the next one
	and an administrator's edited label survives.
	"""
	if not is_available():
		return

	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	present = {df.fieldname for df in frappe.get_meta(APPLICANT_DOCTYPE).fields}

	for field in FIELDS:
		if field["fieldname"] in present:
			continue

		create_custom_field(APPLICANT_DOCTYPE, dict(field), ignore_validate=True)
		present.add(field["fieldname"])
