# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Explicit Kenya registration setup; never run implicitly on other societies.

Run after migrate on the intended Kenya site. Existing plan/workflow records are
preserved; supplied plan mappings make old names explicit rather than guessing.
The profile preserves audited source rules with explicitly agreed Kenya policy updates.
Actual approvers still require real Geo Assignments; no user is granted authority
by this installer.
"""

import json
import re
from pathlib import Path

import frappe

from vmmsx.registration.services import parity

DOCUMENTS = (
	("CV", False),
	("Good Conduct", True),
	("TOR", False),
	("PSEA course Completion Certificate", False),
	("Child Protection Course Certificate", False),
	("Mission Report", False),
	("Other", False),
)
# Keyed by the Identification Type each rule belongs to. The old site's type is
# spelled "Millitary ID", so `_seed_vocabularies` names it `millitary_id`.
ID_PATTERNS = {
	"national_id": r"\d{7,9}",
	"passport": r"[A-Za-z0-9]{6,9}",
	"millitary_id": r"[A-Za-z0-9\-]{5,20}",
	"alien_id": r"[A-Za-z0-9\-]{5,20}",
	"birth_certificate": r"[A-Za-z0-9\-]{6,20}",
	"nemis_number": r"\d{8,14}",
}
# Kenya's regions are named without the society's initials: "Coast Region",
# not "KRCS Coast Region". Only the leading prefix goes; the rest is kept as is.
REGION_PREFIX = re.compile(r"^KRCS\s+", re.IGNORECASE)


def configure_kenya(plan_mapping=None) -> dict:
	"""Install audited source rules without rewriting existing plans or workflows.

	`plan_mapping` is {old plan label: current plan key}. Mapped existing plans are
	left untouched and reported for explicit review; no fee/age changes are hidden.
	Caller must have setup authority. This is a local setup function, not an API.
	"""
	frappe.only_for("System Manager")
	from vmmsx.patches.install_registration_parity import execute

	execute()
	if isinstance(plan_mapping, str):
		plan_mapping = frappe.parse_json(plan_mapping)
	plan_mapping = plan_mapping or {}
	settings = frappe.get_single("National Society Settings")
	for role_field in ("vmms_volunteer_scope_role", "vmms_membership_scope_role"):
		if not settings.get(role_field) or not frappe.db.exists("Role", settings.get(role_field)):
			frappe.throw(
				"Configure the volunteer and membership scope roles in National Society Settings before applying Kenya registration policy."
			)

	for field, value in {
		"vmms_registration_collect_legacy_details": 1,
		"vmms_member_requires_identity": 1,
		"vmms_volunteer_min_age": 7,
		"vmms_volunteer_max_age": 150,
		"vmms_member_min_age": 7,
		"vmms_member_max_age": 150,
		# In Kenya a membership runs until it expires; it is never cancelled.
		"vmms_memberships_can_be_cancelled": 0,
	}.items():
		if settings.meta.has_field(field):
			settings.set(field, value)
	settings.save()
	install_document_types()
	vocabularies = _seed_vocabularies()
	_install_id_patterns()
	regions = drop_region_prefix()
	created, existing = [], []
	for source in json.loads(
		(Path(__file__).parents[1] / "registration/seeds/kenya_registration_plans.json").read_text()
	):
		label, amount, cycle = source["membership_type"], source["amount"], source["billing_cycle"]
		age_rule, lower, upper, template = (
			source["requires_age_requirement"],
			source["lower_age_limit"],
			source["upper_age_limit"],
			source["template"],
		)
		key = plan_mapping.get(label) or label.lower().replace(" ", "-")
		name = frappe.db.get_value("VMMS Membership Type", {"membership_type_key": key}, "name")
		if not name:
			name = frappe.db.get_value("VMMS Membership Type", {"membership_type_name": label}, "name")
		if name:
			existing.append({"name": name, "source": source})
			continue
		doc = frappe.get_doc(
			{
				"doctype": "VMMS Membership Type",
				"membership_type_key": key,
				"membership_type_name": label,
				"is_active": 1,
				"fee_amount": amount,
				"fee_currency": "KES",
				"billing_cycle": cycle,
				"is_lifetime": int(cycle == "One Off"),
				"duration_days": 0 if cycle == "One Off" else 365,
				"approval_mode": "routed",
				"requires_age_requirement": age_rule,
				"lower_age_limit": lower,
				"upper_age_limit": upper,
				"linked_item": source["linked_item"],
				"legacy_template": template,
				"membership_package": source["membership_package"],
				"template_key": "membership_certificate"
				if frappe.db.exists("VMMS Template", "membership_certificate")
				else None,
				"benefits": [
					{**benefit, "benefit_key": f"legacy-{index + 1}", "is_active": 1}
					for index, benefit in enumerate(source["benefits"])
				],
			}
		).insert()
		created.append(doc.name)
	workflows = []
	for doctype, applicant_field, role_field in (
		("VMMS Volunteer Application", "red_profile", "vmms_volunteer_scope_role"),
		("VMMS Membership", "member", "vmms_membership_scope_role"),
	):
		if frappe.db.exists("VMMS Approval Workflow", {"workflow_for": doctype}):
			continue
		role = settings.get(role_field)
		if not role or not frappe.db.exists("Role", role):
			continue
		workflow = frappe.get_doc(
			{
				"doctype": "VMMS Approval Workflow",
				"workflow_for": doctype,
				"geo_node_field": "geo_node",
				"applicant_field": applicant_field,
				"allow_withdrawal": 1,
				"stages": [
					{
						"sequence": 1,
						"stage_label": "Registration review",
						"required_role": role,
						"resolution_rule": "nearest_ancestor",
						"completion_rule": "any_of",
						"can_reject": 1,
						"is_optional": 0,
						"sla_days": 5,
						"on_sla_breach": "notify_only",
					}
				],
			}
		).insert()
		workflows.append(workflow.name)
	regional_stage = _regional_membership_stage()
	frappe.clear_document_cache("National Society Settings", "National Society Settings")
	return {
		"regional_membership_stage": regional_stage,
		"vocabularies_created": vocabularies,
		"regions": regions,
		"plans_created": created,
		"existing_plans_require_review": existing,
		"workflows_created": workflows,
		"requires_real_geo_assignments": True,
	}


def _regional_membership_stage() -> dict:
	"""Kenya's second membership approval: the Head of Region, after the county.

	Optional until a region has somebody assigned, so a site configured before
	its regional heads exist approves memberships at the county as before.
	Skipped, and said so, where the society has no region level.
	"""
	from vmmsx.setup import regional_approval, regional_oversight

	if not frappe.db.exists("Geo Level", "region"):
		return {"status": "skipped", "reason": "There is no region level."}

	regional_oversight.install()

	return regional_approval.add_membership_regional_stage()


def install_kenya_vocabularies() -> dict:
	"""The old VMMS's picker values, without the rest of `configure_kenya`.

	Professions, licence types, languages, disabilities (including the old
	"None"), identification types with their number rules, driving licence
	classes and the old reasons to join. Only missing values are added, so a
	rerun changes nothing and values added on the site later are kept. The two
	exceptions match the old form exactly: education levels and driving licence
	classes not on the old list are switched off (never deleted).

	`bench --site <site> execute vmmsx.setup.registration_parity.install_kenya_vocabularies`
	"""
	frappe.only_for("System Manager")
	created = _seed_vocabularies()
	created["id_patterns"] = len(_install_id_patterns())
	return created


def drop_region_prefix() -> dict:
	"""Rename regions still called "KRCS …" to the name after the prefix.

	Only the label changes. A Geo Node's docname is an opaque key, and every
	link, assignment and cost centre points at that key, so nothing that refers
	to a region moves. A region whose shorter name a sibling already holds is
	left alone and reported, never merged.
	"""
	frappe.only_for("System Manager")
	result = {"renamed": [], "skipped": []}
	if not frappe.db.exists("Geo Level", "region"):
		return result

	for name in frappe.get_all(
		"Geo Node",
		filters={"geo_level": "region", "geo_node_name": ("like", "KRCS %")},
		order_by="geo_node_name asc",
		pluck="name",
	):
		doc = frappe.get_doc("Geo Node", name)
		before = doc.geo_node_name
		label = REGION_PREFIX.sub("", before).strip()
		if not label or label == before:
			continue
		taken = frappe.get_all(
			"Geo Node",
			filters={
				"geo_node_name": label,
				"parent_geo_node": doc.parent_geo_node or ("is", "not set"),
				"name": ("!=", name),
			},
			pluck="name",
			limit=1,
		)
		if taken:
			result["skipped"].append({"name": name, "label": before, "taken_by": taken[0]})
			continue
		doc.geo_node_name = label
		doc.save()
		result["renamed"].append({"name": name, "from": before, "to": label})
	return result


def _install_id_patterns() -> list[str]:
	"""Give each Kenya ID type the old number rule, unless the site set its own."""
	installed = []
	for key, pattern in ID_PATTERNS.items():
		if frappe.db.exists("Identification Type", key):
			doc = frappe.get_doc("Identification Type", key)
			if not doc.get(parity.ID_PATTERN_FIELD):
				doc.set(parity.ID_PATTERN_FIELD, pattern)
				doc.save()
				installed.append(key)
	return installed


def _seed_vocabularies() -> dict:
	"""Add exact legacy picker values; never remove or rename existing choices."""
	data = json.loads(
		(Path(__file__).parents[1] / "registration/seeds/kenya_registration_vocabularies.json").read_text()
	)
	counts = {key: 0 for key in data}
	for label in data["professions"]:
		if not frappe.db.exists("Profession", label):
			frappe.get_doc({"doctype": "Profession", "__newname": label}).insert()
			counts["professions"] += 1
	# Personnel License Type is an ordinary register: more types are added on
	# the desk as they come up, and this only puts back the old site's four.
	for label in data["licence_types"]:
		if not frappe.db.exists("Personnel License Type", label):
			frappe.get_doc({"doctype": "Personnel License Type", "__newname": label}).insert()
			counts["licence_types"] += 1
	counts["driving_classes"] = install_driving_classes(data["driving_classes"])
	counts["education_levels"] = install_education_levels(data["education_levels"])
	for source in data["disabilities"]:
		label = source.get("disability_name") or source["name"]
		category = source.get("disability_category")
		if category and not frappe.db.exists("Disability Type", category):
			frappe.get_doc({"doctype": "Disability Type", "disability_type": category}).insert()
		if not frappe.db.exists("Disability", label):
			frappe.get_doc(
				{"doctype": "Disability", "disability_name": label, "disability_type": category}
			).insert()
			counts["disabilities"] += 1
	# Added switched off. `enabled` means "offered as a desk interface language",
	# and nothing is translated into Kikuyu or "Other". The registration picker
	# (`api.volunteer._languages`) lists every Language whatever the flag.
	for source in data["languages"]:
		if not frappe.db.exists("Language", source["name"]):
			frappe.get_doc(
				{
					"doctype": "Language",
					"language_code": source.get("language_code") or source["name"],
					"language_name": source.get("language_name") or source["name"],
					"enabled": 0,
				}
			).insert()
			counts["languages"] += 1
	for label in data["identification_types"]:
		key = label.lower().replace(" ", "_")
		if not frappe.db.exists("Identification Type", key):
			frappe.get_doc(
				{
					"doctype": "Identification Type",
					"identification_type_key": key,
					"identification_type_name": label,
					"is_active": 1,
				}
			).insert()
			counts["identification_types"] += 1
	for label in ("Humanitarian", "Skill Development", "Social Cohesion", "Personal"):
		key = "legacy-" + label.lower().replace(" ", "-")
		if not frappe.db.exists("VMMS Motivation", {"motivation_name": label}) and not frappe.db.exists(
			"VMMS Motivation", key
		):
			frappe.get_doc(
				{
					"doctype": "VMMS Motivation",
					"motivation_key": key,
					"motivation_name": label,
					"is_active": 1,
				}
			).insert()
	return counts


def install_document_types() -> None:
	"""The supporting documents Kenya asks volunteers for. Only Good Conduct is required."""
	frappe.only_for("System Manager")
	for label, required in DOCUMENTS:
		if frappe.db.exists("Supporting Document Type", label):
			doc = frappe.get_doc("Supporting Document Type", label)
		else:
			doc = frappe.get_doc({"doctype": "Supporting Document Type", "__newname": label})
		doc.set(parity.REQUIRED_DOCUMENT_FIELD, int(required))
		doc.set(parity.DOCUMENT_NAME_FIELD, int(label == "Other"))
		doc.save()


def install_education_levels(levels=None) -> int:
	"""The old VMMS's six education levels, under the old labels and in its order.

	Primary, Secondary and the two degrees keep their keys and take the old
	label, so a record already holding one is unchanged. Graduate and Others are
	added. Any other level is switched off rather than deleted, so a record that
	chose it still shows it; the form simply no longer offers it.
	"""
	frappe.only_for("System Manager")
	if levels is None:
		levels = json.loads(
			(
				Path(__file__).parents[1] / "registration/seeds/kenya_registration_vocabularies.json"
			).read_text()
		)["education_levels"]
	created = 0
	for index, source in enumerate(levels, start=1):
		key = source["name"]
		values = {"level_name": source["label"], "sequence": index * 10, "is_active": 1}
		if frappe.db.exists("VMMS Education Level", key):
			doc = frappe.get_doc("VMMS Education Level", key)
			doc.update(values)
			doc.save()
		else:
			frappe.get_doc({"doctype": "VMMS Education Level", "level_key": key, **values}).insert()
			created += 1
	listed = {source["name"] for source in levels}
	for key in frappe.get_all("VMMS Education Level", filters={"is_active": 1}, pluck="name"):
		if key not in listed:
			frappe.db.set_value("VMMS Education Level", key, "is_active", 0)
	return created


def install_driving_classes(classes=None) -> int:
	"""Kenya's driving licence classes (Traffic Driving Licences Rules, 2018).

	The listed classes are created or brought up to date; old classes are kept
	inactive so earlier records still show them. The generic placeholder classes
	every site starts with are switched off, because a Kenyan licence is held in
	these classes and not in "Light vehicle". Nothing is deleted.
	"""
	from vmmsx.patches.install_background_fields import DRIVING_CLASSES

	frappe.only_for("System Manager")
	if classes is None:
		classes = json.loads(
			(
				Path(__file__).parents[1] / "registration/seeds/kenya_registration_vocabularies.json"
			).read_text()
		)["driving_classes"]
	created = 0
	for source in classes:
		key = source["name"]
		values = {
			"class_name": source.get("class") or key,
			"description": source.get("description"),
			"is_active": int(source.get("is_active", 1)),
		}
		if frappe.db.exists("VMMS Driving Licence Class", key):
			doc = frappe.get_doc("VMMS Driving Licence Class", key)
			doc.update(values)
			doc.save()
		else:
			frappe.get_doc({"doctype": "VMMS Driving Licence Class", "class_key": key, **values}).insert()
			created += 1
	listed = {source["name"] for source in classes}
	for key, _label, _covers in DRIVING_CLASSES:
		if key not in listed and frappe.db.exists("VMMS Driving Licence Class", key):
			frappe.db.set_value("VMMS Driving Licence Class", key, "is_active", 0)
	return created
