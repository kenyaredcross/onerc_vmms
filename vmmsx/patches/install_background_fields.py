# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What somebody has already done, on the spine that holds who they are.

The self-service registration asked for identity, placement, identity documents,
skills, languages, availability and motivation — and then, for everything a
person had actually *done*, one free-text box called "prior experience". A
society could not tell whether an applicant had a nursing qualification, a
driving licence, or anybody who would speak for them, except by reading a
paragraph. None of it could be counted, filtered, or put in front of a
coordinator deciding who to send.

This installs seven fields for it, and the shape of each one is argued in the
doctype it points at rather than here.

**Why they are on Red Profile and not on the application.** The same argument
`install_disability_fields` makes, and the one
`consolidate_person_facts_on_red_profile` already acted on for citizenship and
residence: a qualification is a fact about a person. It does not change when
somebody transfers branch, it should not be asked again when the same person
takes out a membership, and a copy on each satellite would be two answers to one
question that diverge the first time either is corrected.

That has a consequence worth stating plainly: **these are not a snapshot of what
was claimed at application.** Somebody who adds a licence in March and applies
again in August applies with the licence. If a society ever needs "what did they
tell us at the time", that is a separate record and the answers table is the
precedent for it.

**Every one of them is optional, and the completion rules did not move.** No
step gates on any of this and `assert_ready` gained nothing. A volunteer
application is not a job application: a society that turned "tell us about
yourself" into seven required tables would lose the applicants it most wants,
who are frequently the ones with the least of it to fill in.

**Two registers are reused rather than invented.** `Profession` and
`Personnel Licence` have been in this app since the recruitment work and were
wired only to Job Opening — one register describing what a *post* requires, now
also describing what a *person* holds. Both are the same facts in both places,
so a second copy of either would have been the mistake.

**Nothing here reaches Frappe HR.** `hr._OUTBOUND` did not widen with this, for
the reason it did not widen for disability: what an applicant told a society
about themselves is not employment data.
"""

import frappe

PROFILE_DOCTYPE = "Red Profile"

# The field the block is anchored under — core's own last identity field before
# affiliations. Named once, because every field below chains off the one before
# it and the first of them has to start somewhere real.
ANCHOR = "vmms_disability_needs"

LEVEL_DOCTYPE = "VMMS Education Level"
CLASS_DOCTYPE = "VMMS Driving Licence Class"
PROFESSION_DOCTYPE = "Profession"

# key, label, sequence. ISCED-shaped, which is what a national society reports
# against — and, like every seeded vocabulary in this app, a starting point a
# society renames or deletes. `sequence` orders the picker and nothing else.
EDUCATION_LEVELS = (
	("none", "No formal schooling", 10),
	("primary", "Primary", 20),
	("secondary", "Secondary", 30),
	("vocational", "Vocational or technical", 40),
	("diploma", "Diploma", 50),
	("undergraduate", "Undergraduate degree", 60),
	("postgraduate", "Postgraduate degree", 70),
)

# key, label, what it covers. Deliberately generic: licence classes are national
# law, they differ country to country, and the doctype's own docstring says why
# this is a register rather than an enum.
DRIVING_CLASSES = (
	("motorcycle", "Motorcycle", "Two- and three-wheeled vehicles."),
	("light_vehicle", "Light vehicle", "Cars and small vans."),
	("light_truck", "Light truck", "Goods vehicles under the local weight limit."),
	("heavy_truck", "Heavy truck", "Goods vehicles above the local weight limit."),
	("minibus", "Minibus", "Passenger vehicles up to the local seat limit."),
	("bus", "Bus", "Large passenger vehicles."),
)

# ISCO-08 major groups, plus the two answers a form that only listed occupations
# would have had no room for. An international standard rather than one
# society's list, which is the whole reason this and not a hand-written twelve.
PROFESSIONS = (
	"Manager",
	"Professional",
	"Technician or associate professional",
	"Clerical support worker",
	"Service or sales worker",
	"Skilled agricultural, forestry or fishery worker",
	"Craft or related trades worker",
	"Plant or machine operator",
	"Elementary occupation",
	"Armed forces",
	"Student",
	"Not currently working",
)

# Ordered, because each one is inserted after the one before it and a set would
# put them on the profile in whatever order the dict happened to iterate.
FIELDS = (
	{
		"fieldname": "vmms_background_section",
		"label": "Background",
		"fieldtype": "Section Break",
		"description": (
			"What this person has already done — studied, trained, worked, and who will speak"
			" for them. All optional, all self-declared, none of it checked by anybody. Owned"
			" by vmmsx."
		),
	},
	{
		"fieldname": "vmms_profession",
		"label": "Profession",
		"fieldtype": "Link",
		"options": PROFESSION_DOCTYPE,
		"description": "What kind of work this person does, from the society's own register.",
	},
	{
		"fieldname": "vmms_education",
		"label": "Education",
		"fieldtype": "Table",
		"options": "VMMS Education",
	},
	{
		"fieldname": "vmms_training",
		"label": "Training and Courses",
		"fieldtype": "Table",
		"options": "VMMS Declared Training",
		"description": (
			"What this person says they have trained in. Not a certification: nothing here makes"
			" anybody deployable, and a branch that verifies a claim issues a VMMS Certification"
			" as a decision somebody makes."
		),
	},
	{
		"fieldname": "vmms_work_experience",
		"label": "Experience",
		"fieldtype": "Table",
		"options": "VMMS Work Experience",
	},
	{
		"fieldname": "vmms_licences",
		"label": "Professional Licences",
		"fieldtype": "Table",
		"options": "Personnel Licence",
		"description": (
			"Licences and registrations this person holds. The same table a Job Opening uses to"
			" say what a post requires — one shape, two questions."
		),
	},
	{
		"fieldname": "vmms_driving_licences",
		"label": "Driving Licence",
		"fieldtype": "Table",
		"options": "VMMS Driving Licence",
	},
	{
		"fieldname": "vmms_references",
		"label": "References",
		"fieldtype": "Table",
		"options": "VMMS Professional Reference",
		"description": (
			"Who will speak for this person. Not an emergency contact — that is who a society"
			" calls when something has gone wrong, and it lives on the application."
		),
	},
)


def execute():
	"""Seed the registers, then hang the fields off the profile.

	Registers first, so the pickers have something in them the moment the fields
	appear. Guarded per row and per field, so a run interrupted half way finishes
	on the next migrate rather than skipping the rest for ever.
	"""
	seed_levels()
	seed_driving_classes()
	seed_professions()
	install_fields()


def seed_levels() -> None:
	for key, label, sequence in EDUCATION_LEVELS:
		if frappe.db.exists(LEVEL_DOCTYPE, key):
			continue

		frappe.get_doc(
			{
				"doctype": LEVEL_DOCTYPE,
				"level_key": key,
				"level_name": label,
				"sequence": sequence,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)


def seed_driving_classes() -> None:
	for key, label, covers in DRIVING_CLASSES:
		if frappe.db.exists(CLASS_DOCTYPE, key):
			continue

		frappe.get_doc(
			{
				"doctype": CLASS_DOCTYPE,
				"class_key": key,
				"class_name": label,
				"description": covers,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)


def seed_professions() -> None:
	"""Only into an empty register.

	Unlike the two above, this one has been in the app since the recruitment work
	and a society may already have filled it with its own occupations. Seeding
	twelve standard groups beside a list somebody curated would leave a picker
	that offers the same job twice in two vocabularies — so this seeds a register
	nobody has touched, and otherwise leaves well alone.
	"""
	if not frappe.db.table_exists(PROFESSION_DOCTYPE) or frappe.db.count(PROFESSION_DOCTYPE):
		return

	for label in PROFESSIONS:
		frappe.get_doc({"doctype": PROFESSION_DOCTYPE, "__newname": label}).insert(ignore_permissions=True)


def install_fields() -> None:
	from frappe.custom.doctype.custom_field.custom_field import create_custom_field

	if not frappe.get_meta(PROFILE_DOCTYPE).has_field(ANCHOR):
		# `install_disability_fields` runs before this in patches.txt. The guard
		# is for a site that has run neither, where `insert_after` would name a
		# field that is not there and put the whole block somewhere arbitrary.
		return

	previous = ANCHOR

	for field in FIELDS:
		if frappe.db.exists("Custom Field", {"dt": PROFILE_DOCTYPE, "fieldname": field["fieldname"]}):
			previous = field["fieldname"]
			continue

		create_custom_field(PROFILE_DOCTYPE, dict(field, insert_after=previous), ignore_validate=True)
		previous = field["fieldname"]
