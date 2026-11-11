"""How complete a volunteer's own profile is, item by item.

**The list is the registration's, not a second one.** Each item asks exactly the
question `application.assert_ready` asks at submission, by calling the same
check against a stand-in application that points at this person. A society that
starts requiring a document, or a rule that changes, changes this list with it:
there is nothing here to keep in step.

Two kinds of item are added on top, both things the registration form insists
on in the browser rather than at submission: a photograph and a phone number and
gender. And the emergency contact is read off the volunteer record, which is
where a volunteer keeps it once their application has closed.

What is **not** here: the society's own questions and declarations. They are
answers to one application, not facts about the person, and a volunteer cannot
change them from their profile.

Each item names the `section` of the profile page that fixes it, so the page can
take somebody straight to the one thing missing rather than to a whole form.
"""

import frappe
from frappe import _

from vmmsx.registration.services import parity
from vmmsx.volunteer.services import application as application_service

PROFILE_DOCTYPE = "Red Profile"

#: Fields the society's legacy-details policy adds, with the section each is
#: corrected in. Residence fields are folded into the residence item.
LEGACY_FIELDS = (
	("access_to_internet", "vmms_access_to_internet", "Say whether you have internet access", "other"),
	("profession", "vmms_profession", "Add your profession", "background"),
)
LEGACY_RESIDENCE_FIELDS = ("vmms_residence_county", "vmms_residence_sub_county", "vmms_residence_ward")


def of_volunteer(volunteer) -> dict:
	"""`{percent, done, total, items: [{key, label, section, done}]}`."""
	profile = frappe.get_doc(PROFILE_DOCTYPE, volunteer.red_profile)
	stand_in = frappe._dict(
		doctype="VMMS Volunteer Application",
		red_profile=profile.name,
		applicant_date_of_birth=None,
		emergency_contacts=volunteer.get("emergency_contacts") or [],
	)
	policy = parity.options()
	items = []

	def add(key, label, section, done):
		items.append({"key": key, "label": label, "section": section, "done": bool(done)})

	def passes(*checks) -> bool:
		for check in checks:
			try:
				check(stand_in)
			except frappe.ValidationError:
				return False
		return True

	add("photo", _("Add a photo"), "photo", profile.get("profile_photo"))
	add("phone", _("Add your phone number"), "details", profile.get("phone"))
	add("gender", _("Choose your gender"), "details", profile.get("gender"))
	add(
		"date_of_birth",
		_("Add your date of birth"),
		"details",
		passes(application_service._assert_date_of_birth),
	)
	add(
		"citizenship",
		_("Add your country of citizenship"),
		"citizenship",
		passes(application_service._assert_country_of_citizenship),
	)
	add(
		"identification",
		_("Add your ID document"),
		"identification",
		passes(application_service._assert_identification, application_service._assert_identity_documents),
	)
	add(
		"disability",
		_("Answer the disability question"),
		"disability",
		passes(application_service._assert_disability_answered),
	)

	residence = passes(application_service._assert_residency_complete)
	if residence and policy["collect_legacy_details"] and profile.get("residency_type") == "Local":
		residence = all(
			profile.get(field) for field in LEGACY_RESIDENCE_FIELDS if profile.meta.has_field(field)
		)
	add("residence", _("Add where you live"), "residence", residence)

	if policy["collect_legacy_details"]:
		for key, field, label, section in LEGACY_FIELDS:
			if profile.meta.has_field(field):
				add(key, _(label), section, profile.get(field))

	add(
		"education",
		_("Add your education"),
		"background",
		passes(application_service._assert_education_given),
	)

	held = profile.get(parity.TABLES["supporting_documents"][0]) if profile.meta.has_field(
		parity.TABLES["supporting_documents"][0]
	) else []
	missing = set(parity.missing_required_documents(held or [], policy["supporting_document_types"]))
	for document in policy["supporting_document_types"]:
		if document.get("is_required"):
			add(
				f"document:{document['key']}",
				_("Upload your {0}").format(document["label"]),
				"documents",
				document["key"] not in missing,
			)

	add(
		"emergency_contact",
		_("Add an emergency contact"),
		"emergency",
		passes(application_service._assert_emergency_contact_given),
	)

	done = sum(1 for item in items if item["done"])
	total = len(items)
	# Never rounded up to 100: a profile with one thing missing is not complete.
	percent = 100 if done == total else min(99, round(done * 100 / total))

	return {"percent": percent, "done": done, "total": total, "items": items}
