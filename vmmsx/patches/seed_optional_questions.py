# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A library of questions a society can switch on, and none of them switched on.

The comparison that produced this list came from an older, single-society
product where blood group, allergies, insurance cover, internet access and
number of dependants were columns on the registration form. Every one of them is
a real thing some society asks. Not one of them is a thing *this* product should
decide every society asks, which is the whole distinction
`VMMS Application Question` exists to hold: the standard form is what a
volunteer registration is everywhere, and this is what one organization wants on
top of it.

**So they are seeded inactive, every one.** `is_active` is 0, which means
`questions.asked_on` does not return them and no applicant is ever shown one
until an administrator turns it on from the form builder. A society that seeded
these live would have shipped five questions nobody asked for, two of them
medical, into every registration on the site.

**Why seed them at all, then.** The form builder starts empty, and an empty
builder is a screen that tells an administrator they *can* write a question
without telling them what one looks like. These are worked examples with real
answer types, real help text and real grouping — the fastest way to understand
the feature is to switch one on and see where it lands.

**The two medical ones carry a warning in their own help text.** Blood group and
medical conditions are health data about identifiable people. They are stored in
the ordinary answers table, which is private evidence and readable by the
approvers a society routes an application to — and that is a decision a society
has to make deliberately, not one it should stumble into because a field was
already there. Core holds `blood_group` and `medical_conditions` back for a
gated extension for the same reason; nothing here touches those.

Volunteer applications only. A membership is a subscription, and a society that
wants a question on one can add it in the same builder.
"""

import frappe

QUESTION_DOCTYPE = "VMMS Application Question"
APPLICATION_DOCTYPE = "VMMS Volunteer Application"

HEALTH = "Health and safety"
PRACTICAL = "Getting you there"

# label, group, field_type, options, sequence, help_text
QUESTIONS = (
	(
		"What is your blood group?",
		HEALTH,
		"Select",
		"\nA+\nA-\nB+\nB-\nAB+\nAB-\nO+\nO-\nI do not know",
		10,
		"Health data. Switch this on only if your society has decided it needs it and has told"
		" applicants why — the answer is readable by whoever reviews the application.",
	),
	(
		"Is there anything about your health we should know before sending you somewhere?",
		HEALTH,
		"Small Text",
		None,
		20,
		"Allergies, conditions, medication. Health data — the same caution applies as to blood"
		" group. Leave it optional: an applicant who would rather tell somebody in person"
		" should be able to.",
	),
	(
		"Do you have your own health or accident cover?",
		HEALTH,
		"Select",
		"\nYes\nNo\nI am not sure",
		30,
		"Some societies insure volunteers themselves and need to know who is already covered."
		" Nothing in this product reads the answer.",
	),
	(
		"How reliable is your internet access?",
		PRACTICAL,
		"Select",
		"\nAlways online\nUsually\nSometimes\nRarely or never",
		40,
		"Worth asking if your branches coordinate over a phone. It is also the question that"
		" tells you which volunteers a WhatsApp channel will never reach.",
	),
	(
		"How many people depend on you?",
		PRACTICAL,
		"Int",
		None,
		50,
		"Asked by societies that pay a stipend or plan deployments away from home. Blank and"
		" zero mean different things, so leave it optional.",
	),
)


def execute():
	"""Insert what is absent, and never re-activate what somebody has retired.

	Matched on the question's own wording rather than on a docname, because these
	autoname from a series and there is nothing stable to look one up by. That is
	imperfect — an administrator who edits the wording gets a second copy on the
	next migrate — which is why the whole patch is skipped once any of them
	exists, rather than checked row by row.
	"""
	if not frappe.db.exists("DocType", QUESTION_DOCTYPE):
		return

	labels = [label for label, *_ in QUESTIONS]

	if frappe.db.exists(
		QUESTION_DOCTYPE, {"asked_on": APPLICATION_DOCTYPE, "question_label": ("in", labels)}
	):
		return

	for label, group, field_type, options, sequence, help_text in QUESTIONS:
		frappe.get_doc(
			{
				"doctype": QUESTION_DOCTYPE,
				"asked_on": APPLICATION_DOCTYPE,
				"question_label": label,
				"question_group": group,
				"field_type": field_type,
				"options": options,
				"sequence": sequence,
				"help_text": help_text,
				# Off. The whole point of the patch — see the module docstring.
				"is_active": 0,
				"is_required": 0,
			}
		).insert(ignore_permissions=True)
