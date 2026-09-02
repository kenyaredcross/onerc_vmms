# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What a society screens an opening on, added to HRMS's `Job Opening`.

HRMS advertises a post: title, department, description, a closing date and a
salary band. It has nowhere to write down what the society will *accept* — the
qualification, the years, the licences, the documents, the questions — and so a
recruiter reading fifty applications holds all of that in their head and applies
it differently on Friday than on Monday. These fields are that standard, written
on the opening itself where everybody answering it can see it.

**Ported from `onerc_vmms`, fieldname for fieldname.** The old app carried this
as a `custom/job_opening.json` fixture. The names here are identical to it on
purpose — data written under the old app reads back unchanged, and so does any
report or client script that named a field. That is a deliberate exception to
this app's `vmms_` prefix convention (see `setup/project_fields.py`, which
explains the convention): parity was the point of the port, and a prefix would
have bought consistency at the cost of the only thing the port was for.

**Every field is a Custom Field owned by vmmsx.** HRMS's source is not edited.

**Installed on every migrate, not once by a patch**, for the reason
`setup/project_fields.py` gives and one more of its own: three of these fields
point at doctypes that belong to apps vmmsx does not require — `Location` is
ERPNext's, `Designation Skill` is HRMS's, `Certification` is the LMS's — and a
site that installs one of those next year should get the field then. A patch
runs once per site by name and could not. Each such field carries `requires`,
naming the doctype it needs; when that doctype is absent the field is skipped and
the *next* field's anchor is walked back past it, so a gap in the middle never
leaves the rest of the tab floating at the bottom of the form.

**Dormant when HRMS is absent.** vmmsx does not declare `hrms` in
`required_apps` — a society running volunteering without a recruitment module is
ordinary, not half-installed, which is the same rule `hr/services/openings.py`
and the Buzz seam follow. On such a site `install()` returns having done nothing.

**A second block, added later and under the prefix.** `VMMS_FIELDS` below is
*not* part of the port: it is what the volunteering side of this app needs from
an opening — whether the post is employment or volunteering at all, which branch
owns it, which programme and deployment it belongs to, and the attributes a
coordinator searches the volunteer register by. Those are new, so they carry the
`vmms_` prefix the port itself was exempted from, and they name **vmmsx's own**
vocabularies rather than HRMS's and the LMS's: `VMMS Skill` and
`VMMS Certification Type` are what `volunteer/services/capabilities.py` can
actually search on, and a desired attribute nothing can search by is a label.

**Desired is desired.** None of them rejects anybody. `matching.candidates` reads
the same vocabularies to *rank*, and the agreed direction for this doctype is the
same one deployment matching already follows: an attribute narrows a search where
a coordinator asks it to and never decides on its own.

**Schema only. Nothing grades against these yet.** `enable_autograding`,
`minimum_pass_score`, `is_knock_off` and the scoring columns on
`Job Application Screening Questions` are read by a scoring engine in the old app
that lives on `Job Applicant`, and that engine was not part of this port. The
fields are editable and they record the society's intent; no code in vmmsx acts
on them. The same goes for `duration`, which the old app filled in from
`posted_on` and `closes_on` in a `validate` hook: it is read-only and will stay
empty until something fills it.
"""

import json

import frappe

OPENING_DOCTYPE = "Job Opening"

# HRMS owns `Job Opening`. Asked of the installed-app list rather than by import,
# for the reason `hr/services/openings.py` sets out: an app can sit in the bench
# without being installed on *this* site, and that is the case that bites.
HRMS_APP = "hrms"

# The Link and Table targets that belong to apps vmmsx does not require. Named
# here so the three `requires` clauses below cannot spell them differently.
LOCATION_DOCTYPE = "Location"  # ERPNext
SKILL_DOCTYPE = "Designation Skill"  # HRMS
CERTIFICATION_DOCTYPE = "Certification"  # LMS

FIELDS = (
	{
		"fieldname": "opportunity_type",
		"label": "Opening Type",
		"fieldtype": "Select",
		"options": "\nInternal\nGuest",
		"insert_after": "job_title",
		"default": "Internal",
		"reqd": 1,
		"in_list_view": 1,
		"in_standard_filter": 1,
		"translatable": 1,
		"description": (
			"Whether this post is open to the society's own people or to anybody. Owned by vmmsx."
		),
	},
	{
		"fieldname": "profession",
		"label": "Profession",
		"fieldtype": "Link",
		"options": "Profession",
		"insert_after": "designation",
		"description": (
			"The trade or calling this post belongs to, from the society's own register."
			" Broader than Designation, which is the job title. Owned by vmmsx."
		),
	},
	# `job_opening_template` sat here in the old app as a Custom Field. HRMS ships
	# it as a standard field now, so it is not repeated — `install()` skips any
	# fieldname the doctype already has, whoever put it there.
	{
		"fieldname": "duration",
		"label": "Duration",
		"fieldtype": "Duration",
		"insert_after": "closes_on",
		"read_only": 1,
		"description": (
			"How long this opening stays advertised, from posting to closing. Nothing in"
			" vmmsx fills this in yet. Owned by vmmsx."
		),
	},
	{
		"fieldname": "job_location",
		"label": "Location",
		"fieldtype": "Link",
		"options": LOCATION_DOCTYPE,
		"insert_after": "company",
		"requires": LOCATION_DOCTYPE,
		"description": (
			"Where the work happens. HRMS's own `location` links to Branch and is hidden"
			" in favour of this one. Owned by vmmsx."
		),
	},
	{
		"fieldname": "screening_requirements",
		"label": "Requirements",
		"fieldtype": "Tab Break",
		"insert_after": "publish_salary_range",
	},
	{
		"fieldname": "enable_autograding",
		"label": "Enable Auto-Grading",
		"fieldtype": "Check",
		"insert_after": "screening_requirements",
		"description": (
			"Records that this opening is meant to be scored automatically. No code in vmmsx"
			" grades against it yet. Owned by vmmsx."
		),
	},
	{
		"fieldname": "disqualify_if_requirement_not_met",
		"label": "Disqualify if Requirement Not Met",
		"fieldtype": "Check",
		"insert_after": "enable_autograding",
	},
	{
		"fieldname": "column_break_unps0",
		"fieldtype": "Column Break",
		"insert_after": "disqualify_if_requirement_not_met",
	},
	{
		"fieldname": "minimum_pass_score",
		"label": "Minimum Pass Score",
		"fieldtype": "Float",
		"insert_after": "column_break_unps0",
	},
	{
		"fieldname": "minimum_education",
		"label": "Minimum Education",
		"fieldtype": "Section Break",
		"insert_after": "minimum_pass_score",
		"collapsible": 1,
	},
	{
		"fieldname": "minimum_qualification_level",
		"label": "Minimum Qualification Level",
		"fieldtype": "Select",
		"options": "\nPrimary\nSecondary / High School\nUndergraduate\nGraduate\nPostgraduate",
		"insert_after": "minimum_education",
		"translatable": 1,
	},
	{
		"fieldname": "allow_equivalent_experience",
		"label": "Allow Equivalent Experience",
		"fieldtype": "Check",
		"insert_after": "minimum_qualification_level",
	},
	{
		"fieldname": "column_break_rlcns",
		"fieldtype": "Column Break",
		"insert_after": "allow_equivalent_experience",
	},
	{
		"fieldname": "required_gpa__grade",
		"label": "Required GPA / Grade",
		"fieldtype": "Data",
		"insert_after": "column_break_rlcns",
		"translatable": 1,
	},
	{
		"fieldname": "column_break_617ar",
		"fieldtype": "Column Break",
		"insert_after": "required_gpa__grade",
	},
	{
		"fieldname": "preferred_field_of_study",
		"label": "Preferred Field of Study",
		"fieldtype": "Data",
		"insert_after": "column_break_617ar",
		"translatable": 1,
	},
	{
		"fieldname": "minimum_experience",
		"label": "Minimum Experience",
		"fieldtype": "Section Break",
		"insert_after": "preferred_field_of_study",
		"collapsible": 1,
	},
	{
		"fieldname": "minimum_years_of_experience",
		"label": "Minimum Years of Experience",
		"fieldtype": "Float",
		"insert_after": "minimum_experience",
	},
	{
		"fieldname": "column_break_vf32z",
		"fieldtype": "Column Break",
		"insert_after": "minimum_years_of_experience",
	},
	{
		"fieldname": "experience_area",
		"label": "Experience Area",
		"fieldtype": "Data",
		"insert_after": "column_break_vf32z",
		"description": "e.g., Software Development, Project Management",
		"translatable": 1,
	},
	{
		"fieldname": "column_break_ljgkc",
		"fieldtype": "Column Break",
		"insert_after": "experience_area",
	},
	{
		"fieldname": "disqualify_if_below_minimum",
		"label": "Disqualify if Below Minimum",
		"fieldtype": "Check",
		"insert_after": "column_break_ljgkc",
	},
	{
		"fieldname": "certifications__skills",
		"label": "Licences & Skills",
		"fieldtype": "Section Break",
		"insert_after": "disqualify_if_below_minimum",
		"collapsible": 1,
	},
	{
		"fieldname": "required_skills",
		"label": "Required Skills",
		"fieldtype": "Table",
		"options": SKILL_DOCTYPE,
		"insert_after": "certifications__skills",
		"requires": SKILL_DOCTYPE,
	},
	{
		"fieldname": "required_certification",
		"label": "Required Certification",
		"fieldtype": "Table",
		"options": CERTIFICATION_DOCTYPE,
		"insert_after": "required_skills",
		# The LMS's child table, and the LMS is not installed on every site that
		# runs vmmsx. Skipped where it is absent, and picked up on the migrate
		# after somebody installs it — which is the whole reason this installer
		# runs on every migrate rather than once in a patch.
		"requires": CERTIFICATION_DOCTYPE,
	},
	{
		"fieldname": "required_licences",
		"label": "Required Licences",
		"fieldtype": "Table",
		"options": "Personnel Licence",
		"insert_after": "required_certification",
	},
	{
		"fieldname": "required_attachments_section",
		"label": "Required Attachments",
		"fieldtype": "Section Break",
		"insert_after": "required_licences",
		"collapsible": 1,
	},
	{
		"fieldname": "required_attachments",
		"label": "Required Attachments",
		"fieldtype": "Table",
		"options": "Required Attachments",
		"insert_after": "required_attachments_section",
	},
	{
		"fieldname": "screening_questions_tab",
		"label": "Screening Questions",
		"fieldtype": "Tab Break",
		"insert_after": "required_attachments",
	},
	{
		"fieldname": "screening_questions_section",
		"fieldtype": "Section Break",
		"insert_after": "screening_questions_tab",
	},
	{
		"fieldname": "screening_questions",
		"label": "Screening Questions",
		"fieldtype": "Table",
		"options": "Job Application Screening Questions",
		"insert_after": "screening_questions_section",
	},
	{
		"fieldname": "notification_settings",
		"label": "Notification Settings",
		"fieldtype": "Tab Break",
		"insert_after": "screening_questions",
	},
	{
		"fieldname": "rejection_notification_settings",
		"label": "Rejection Notification Settings",
		"fieldtype": "Section Break",
		"insert_after": "notification_settings",
	},
	{
		"fieldname": "enable_automatic_rejection_notifications",
		"label": "Enable Automatic Rejection Notifications",
		"fieldtype": "Check",
		"insert_after": "rejection_notification_settings",
		"description": (
			"Records that unsuccessful applicants should be told. Nothing in vmmsx sends"
			" these yet. Owned by vmmsx."
		),
	},
	{
		"fieldname": "send_rejection_email_immediately",
		"label": "Send Rejection Email Immediately",
		"fieldtype": "Check",
		"insert_after": "enable_automatic_rejection_notifications",
		"description": "If checked, applicants are notified instantly when marked as Rejected.",
	},
	{
		"fieldname": "rejection_email_template",
		"label": "Rejection Email Template",
		"fieldtype": "Link",
		"options": "Email Template",
		"insert_after": "send_rejection_email_immediately",
		"mandatory_depends_on": "eval: doc.enable_automatic_rejection_notifications",
	},
	{
		"fieldname": "column_break_smu1t",
		"fieldtype": "Column Break",
		"insert_after": "rejection_email_template",
	},
	{
		"fieldname": "notify_unshortlisted_applicants_after",
		"label": "Notify Unshortlisted Applicants After",
		"fieldtype": "Int",
		"insert_after": "column_break_smu1t",
		"depends_on": "eval: !doc.send_rejection_email_immediately",
		"description": (
			"Number of days after the job closing date to automatically notify applicants"
			" who were not shortlisted."
		),
	},
	{
		"fieldname": "shortlisted_rejection_notification_date",
		"label": "Shortlisted Rejection Notification Date",
		"fieldtype": "Date",
		"insert_after": "notify_unshortlisted_applicants_after",
		"depends_on": "eval: !doc.send_rejection_email_immediately",
		"description": (
			"The date when notifications should be sent to shortlisted applicants who were"
			" not selected for the position."
		),
	},
)

# What the port changes about HRMS's own fields. Two shapes of decision:
#
# **The salary block goes.** A national society advertising a volunteer post has
# no band to publish, and a currency picker on a form nobody costs is a question
# with no answer. Hidden rather than deleted — HRMS still owns the columns, and a
# society that does pay for a post can unhide them from Customize Form.
#
# **`location` goes, `job_location` takes its place.** HRMS's own `location`
# links to Branch; `job_location` above links to ERPNext's Location. Both would
# be labelled "Location" on the same form, which is how a register ends up with
# half its openings placed in one and half in the other.
#
# `employment_type` keeps HRMS's field and takes the society's word for it. The
# old app spelled the label with a double space; corrected here.
#
# **One correction, not a faithful copy.** The old app typed its
# `mandatory_depends_on` setter as a `Check`, and `Meta.apply_property_setters`
# casts a `Check` with `cint()` — so the stored expression read back as `0` and
# the rule never fired on any site that ever loaded that fixture. It is `Data`
# here, which is what the property actually is.
# --- what the volunteering side needs ---------------------------------------
#
# Added after the port and under the prefix; see the module docstring. Installed
# by the same `install_fields()` walk, so the `requires` and anchor-walking rules
# apply to these as well.

PURPOSE_EMPLOYMENT = "Employment"
PURPOSE_VOLUNTEER = "Volunteer"
PURPOSES = (PURPOSE_EMPLOYMENT, PURPOSE_VOLUNTEER)

PURPOSE_FIELD = "vmms_purpose"

VMMS_FIELDS = (
	{
		"fieldname": PURPOSE_FIELD,
		"label": "Purpose",
		"fieldtype": "Select",
		"options": "\n".join(("", *PURPOSES)),
		"insert_after": "opportunity_type",
		"default": PURPOSE_EMPLOYMENT,
		"in_standard_filter": 1,
		"description": (
			"Whether this post is a job or a volunteering role. A volunteering one is applied"
			" for through the volunteer portal by an approved volunteer; an employment one keeps"
			" HRMS's ordinary public application behaviour, untouched. Owned by vmmsx."
		),
	},
	{
		"fieldname": "vmms_geo_node",
		"label": "Owning Geo Node",
		"fieldtype": "Link",
		"options": "Geo Node",
		"insert_after": PURPOSE_FIELD,
		"in_standard_filter": 1,
		"description": (
			"The branch or office recruiting for this post. Not Company, which is the legal"
			" entity: a national society is one Company with a hundred branches. Owned by vmmsx."
		),
	},
	{
		"fieldname": "vmms_project",
		"label": "Project",
		"fieldtype": "Link",
		"options": "Project",
		"insert_after": "vmms_geo_node",
		"description": "The programme of work this post belongs to. Owned by vmmsx.",
	},
	{
		"fieldname": "vmms_deployment",
		"label": "Deployment",
		"fieldtype": "Link",
		"options": "VMMS Deployment",
		"insert_after": "vmms_project",
		"description": (
			"The deployment this post staffs, where it staffs one. An accepted applicant on"
			" such an opening can be turned into a deployment assignment in one act. Owned by"
			" vmmsx."
		),
	},
	{
		"fieldname": "vmms_desired_section",
		"label": "Desired Attributes",
		"fieldtype": "Section Break",
		"insert_after": "required_licences",
		"collapsible": 1,
		"description": (
			"What would make somebody a good fit. Searched and shown; never a rejection —"
			" whether an applicant without one is right for the post is a coordinator's"
			" judgement, and an app that made it would be making it on a register that is"
			" half filled in."
		),
	},
	{
		"fieldname": "vmms_desired_skills",
		"label": "Desired Skills",
		"fieldtype": "Table MultiSelect",
		"options": "VMMS Skill Selector",
		"insert_after": "vmms_desired_section",
		"description": (
			"From the society's own skills register — the one the volunteer register is"
			" searchable by. Owned by vmmsx."
		),
	},
	{
		"fieldname": "vmms_desired_languages",
		"label": "Desired Languages",
		"fieldtype": "Table MultiSelect",
		"options": "VMMS Language Selector",
		"insert_after": "vmms_desired_skills",
		"description": "Languages that would help in this post. Owned by vmmsx.",
	},
	{
		"fieldname": "vmms_desired_certifications",
		"label": "Desired Certifications",
		"fieldtype": "Table",
		"options": "VMMS Deployment Requirement",
		"insert_after": "vmms_desired_languages",
		"description": (
			"From the society's own certification types. The same child table a terms of"
			" reference lists its requirements in, so one vocabulary answers both. Owned by"
			" vmmsx."
		),
	},
	{
		"fieldname": "vmms_availability_section",
		"label": "When",
		"fieldtype": "Section Break",
		"insert_after": "vmms_desired_certifications",
	},
	{
		"fieldname": "vmms_available_from",
		"label": "Needed From",
		"fieldtype": "Date",
		"insert_after": "vmms_availability_section",
		"description": "The first day somebody would be needed. Owned by vmmsx.",
	},
	{
		"fieldname": "vmms_available_to",
		"label": "Needed Until",
		"fieldtype": "Date",
		"insert_after": "vmms_available_from",
		"description": "The last day. Owned by vmmsx.",
	},
)


PROPERTIES = (
	("closes_on", "fieldtype", "Datetime", "Select"),
	("closes_on", "mandatory_depends_on", "eval: doc.status=='Open'", "Data"),
	("posted_on", "reqd", "1", "Check"),
	("employment_type", "label", "Opportunity Type", "Data"),
	("job_application_route", "hidden", "1", "Check"),
	("location", "hidden", "1", "Check"),
	("currency", "hidden", "1", "Check"),
	("lower_range", "hidden", "1", "Check"),
	("upper_range", "hidden", "1", "Check"),
	("salary_per", "hidden", "1", "Check"),
	("publish_salary_range", "hidden", "1", "Check"),
)

# The form as the old app laid it out: identity and dates first, the society and
# where the work is second, the staffing references third, publishing fourth, and
# then the four tabs this port adds.
#
# **Filtered against the live doctype rather than written down as final.** HRMS's
# own field list has moved on since the fixture was captured — it has since
# dropped `section_break_16` and `column_break_20` and gained
# `prevent_duplicate_applicant` and a pay-details tab — so this is a preference,
# not a complete list. `_field_order()` keeps what exists, appends what this list
# has never heard of, and never drops a field off the form.
PREFERRED_ORDER = (
	"job_details_section",
	"job_title",
	"opportunity_type",
	"designation",
	"profession",
	"job_opening_template",
	"column_break_5",
	"status",
	"posted_on",
	"closes_on",
	"duration",
	"closed_on",
	"section_break_nngy",
	"company",
	"job_location",
	"column_break_dxpv",
	"employment_type",
	"department",
	"references_section",
	"staffing_plan",
	"planned_vacancies",
	"job_requisition",
	"vacancies",
	"section_break_6",
	"publish",
	"route",
	"publish_applications_received",
	"column_break_12",
	"job_application_route",
	"section_break_14",
	"description",
	"section_break_16",
	"currency",
	"lower_range",
	"upper_range",
	"column_break_20",
	"salary_per",
	"publish_salary_range",
	"screening_requirements",
	"enable_autograding",
	"disqualify_if_requirement_not_met",
	"column_break_unps0",
	"minimum_pass_score",
	"minimum_education",
	"minimum_qualification_level",
	"allow_equivalent_experience",
	"column_break_rlcns",
	"required_gpa__grade",
	"column_break_617ar",
	"preferred_field_of_study",
	"minimum_experience",
	"minimum_years_of_experience",
	"column_break_vf32z",
	"experience_area",
	"column_break_ljgkc",
	"disqualify_if_below_minimum",
	"certifications__skills",
	"required_skills",
	"required_certification",
	"required_licences",
	"required_attachments_section",
	"required_attachments",
	"screening_questions_tab",
	"screening_questions_section",
	"screening_questions",
	"notification_settings",
	"rejection_notification_settings",
	"enable_automatic_rejection_notifications",
	"send_rejection_email_immediately",
	"rejection_email_template",
	"column_break_smu1t",
	"notify_unshortlisted_applicants_after",
	"shortlisted_rejection_notification_date",
)


def is_available() -> bool:
	"""Is there a `Job Opening` on this site to add anything to?"""
	return HRMS_APP in frappe.get_installed_apps() and frappe.db.exists("DocType", OPENING_DOCTYPE)


def install() -> None:
	"""Create what is absent and touch nothing that is there."""
	if not is_available():
		return

	install_fields()
	install_properties()
	install_field_order()


def install_fields() -> None:
	"""The screening fields, in order, each guarded on its own.

	Guarded per field rather than per run, so a migrate interrupted half way
	finishes on the next one — and so an administrator who has retitled a label
	or rewritten a description keeps their edit.

	The guard is the doctype's own field list, not the Custom Field table: HRMS
	has since made `job_opening_template` a standard field, and a site is not
	improved by a Custom Field shadowing one that is already there.
	"""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	present = {df.fieldname for df in frappe.get_meta(OPENING_DOCTYPE).fields}

	# Fields skipped because the app that owns their Link or Table target is not
	# installed, mapped to the anchor they would have sat after. The next field
	# along walks the chain to find a position that exists, so an absent LMS
	# moves `required_licences` up under `required_skills` rather than leaving
	# every field after it to fall to the bottom of the form.
	skipped: dict[str, str | None] = {}

	# The port first, then what the volunteering side added, because the second
	# block's anchors name fields the first installs. One walk over both so the
	# skipped-anchor chain is shared: a field skipped in `FIELDS` still moves the
	# `VMMS_FIELDS` entry that would have sat after it.
	for field in (*FIELDS, *VMMS_FIELDS):
		spec = dict(field)
		fieldname = spec["fieldname"]
		requires = spec.pop("requires", None)

		anchor = spec.get("insert_after")
		while anchor in skipped:
			anchor = skipped[anchor]
		if anchor:
			spec["insert_after"] = anchor
		else:
			spec.pop("insert_after", None)

		if requires and not frappe.db.exists("DocType", requires):
			skipped[fieldname] = anchor
			continue

		if fieldname in present:
			continue

		create_custom_field(OPENING_DOCTYPE, spec, ignore_validate=True)
		present.add(fieldname)


def install_properties() -> None:
	"""What the port changes about HRMS's own fields — see `PROPERTIES`.

	Create-if-absent, like everything else here. A society that has unhidden the
	salary band because it does pay for a post keeps that decision through every
	later migrate.

	**A `fieldtype` setter is only half the change.** A Property Setter rewrites
	what the *meta* says a field is; the column keeps whatever type it was
	created with. Frappe reconciles the two in `db.updatedb`, and calls it from
	Customize Form — the only route it expects a fieldtype change to arrive by.
	Writing the record and stopping there leaves `closes_on` declared a Datetime
	over a `date` column, which does not error: it silently truncates the time
	off everything written to it. So the column is altered here too, and only
	when this run actually changed a fieldtype.
	"""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	retyped = False

	for fieldname, prop, value, property_type in PROPERTIES:
		if frappe.db.exists(
			"Property Setter", {"doc_type": OPENING_DOCTYPE, "field_name": fieldname, "property": prop}
		):
			continue

		make_property_setter(
			OPENING_DOCTYPE,
			fieldname,
			prop,
			value,
			property_type,
			validate_fields_for_doctype=False,
		)

		retyped = retyped or prop == "fieldtype"

	# Asked of the database rather than only of what this run happened to write,
	# so a site that took the setter from an earlier release without the column
	# behind it is repaired on its next migrate rather than staying wrong for
	# ever. Costs one `information_schema` read on every deploy.
	if retyped or any(
		_column_out_of_step(fieldname, value)
		for fieldname, prop, value, _type in PROPERTIES
		if prop == "fieldtype"
	):
		frappe.clear_cache(doctype=OPENING_DOCTYPE)
		frappe.db.updatedb(OPENING_DOCTYPE)


def _column_out_of_step(fieldname: str, fieldtype: str) -> bool:
	"""Does the column behind this field disagree with the type the meta claims?"""
	expected = (frappe.db.type_map.get(fieldtype) or (None,))[0]

	if not expected:
		return False

	for column in frappe.db.get_table_columns_description(f"tab{OPENING_DOCTYPE}"):
		if column.get("name") == fieldname:
			return not str(column.get("type") or "").lower().startswith(expected.lower())

	return False


def install_field_order() -> None:
	"""Lay the form out once, and never argue with an administrator about it after.

	The order is written in full only when the doctype has none, because
	reordering a form is exactly the sort of thing a society does through
	Customize Form and exactly the sort of thing it would not expect a migrate to
	undo.

	**Where one exists, fields missing from it are appended and nothing is
	moved.** A field order is a list of names, and a field that is not in it does
	not simply sit where it was declared — it falls to the bottom of the form, or
	disappears from it entirely depending on the layout around it. So a site that
	took its order last year and gained fields this year needs those names added,
	and that is a strictly additive edit: every position an administrator chose is
	still where they left it. Without this, `VMMS_FIELDS` would have been invisible
	on every site that had already migrated once.
	"""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	frappe.clear_cache(doctype=OPENING_DOCTYPE)

	existing = frappe.db.get_value(
		"Property Setter", {"doc_type": OPENING_DOCTYPE, "property": "field_order"}, "value"
	)
	order = _appended(json.loads(existing)) if existing else _field_order()

	if existing and order == json.loads(existing):
		return

	make_property_setter(
		OPENING_DOCTYPE,
		None,
		"field_order",
		json.dumps(order),
		"Data",
		for_doctype=True,
		validate_fields_for_doctype=False,
	)

	frappe.clear_cache(doctype=OPENING_DOCTYPE)


def _appended(order: list[str]) -> list[str]:
	"""An existing order with anything missing from it added at the end.

	Additive in both directions and neither destructive: a name in the order that
	is no longer a field is left alone rather than dropped, because it may belong
	to an app that is not installed today and will be tomorrow — which is exactly
	the case `requires` handles for the fields themselves.
	"""
	present = [df.fieldname for df in frappe.get_meta(OPENING_DOCTYPE).fields]
	named = set(order)

	return order + [fieldname for fieldname in present if fieldname not in named]


def _field_order() -> list[str]:
	"""`PREFERRED_ORDER`, narrowed to what exists, then everything else after it.

	Both halves matter. Narrowing drops the two section breaks HRMS has retired
	since the fixture was captured; appending catches the fields it has added
	since — `prevent_duplicate_applicant` and the pay-details tab — which a
	verbatim copy of the old order would have pushed to the end of the form
	without anybody noticing.
	"""
	present = [df.fieldname for df in frappe.get_meta(OPENING_DOCTYPE).fields]
	ordered = [fieldname for fieldname in PREFERRED_ORDER if fieldname in present]
	seen = set(ordered)

	return ordered + [fieldname for fieldname in present if fieldname not in seen]
