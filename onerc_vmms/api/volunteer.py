import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def get_volunteers(
	geo_node=None,
	skill=None,
	availability_status=None,
	volunteer_status="Active",
	language=None,
	page=1,
	page_size=20
):
	filters = {}

	if volunteer_status:
		filters["volunteer_status"] = volunteer_status

	if availability_status:
		filters["availability_status"] = availability_status

	# Skill filter: resolve to a set of matching volunteer names before pagination
	if skill:
		skilled_volunteers = frappe.get_all(
			"Volunteer Skill",
			filters={"skill": ["like", f"%{skill}%"]},
			fields=["parent"],
			pluck="parent"
		)
		if not skilled_volunteers:
			return {"volunteers": [], "total": 0, "page": int(page), "page_size": int(page_size)}
		filters["name"] = ["in", skilled_volunteers]

	# Language filter: resolve to a set of matching volunteer names before pagination
	if language:
		lang_volunteers = frappe.get_all(
			"Volunteer Language",
			filters={"language": language},
			fields=["parent"],
			pluck="parent"
		)
		if not lang_volunteers:
			return {"volunteers": [], "total": 0, "page": int(page), "page_size": int(page_size)}
		# Merge with any existing name filter
		if "name" in filters:
			filters["name"] = ["in", list(set(filters["name"][1]) & set(lang_volunteers))]
			if not filters["name"][1]:
				return {"volunteers": [], "total": 0, "page": int(page), "page_size": int(page_size)}
		else:
			filters["name"] = ["in", lang_volunteers]

	# Geo filter: include volunteers at this node and one level of children
	if geo_node:
		geo_volunteers = frappe.get_all(
			"Volunteer",
			filters={"home_geo_node": geo_node},
			pluck="name"
		)
		child_nodes = frappe.get_all(
			"Geo Node",
			filters={"parent_geo_node": geo_node, "is_active": 1},
			pluck="name"
		)
		if child_nodes:
			child_volunteers = frappe.get_all(
				"Volunteer",
				filters={"home_geo_node": ["in", child_nodes]},
				pluck="name"
			)
			geo_volunteers = list(set(geo_volunteers + child_volunteers))
		if not geo_volunteers:
			return {"volunteers": [], "total": 0, "page": int(page), "page_size": int(page_size)}
		if "name" in filters:
			merged = list(set(filters["name"][1]) & set(geo_volunteers))
			if not merged:
				return {"volunteers": [], "total": 0, "page": int(page), "page_size": int(page_size)}
			filters["name"] = ["in", merged]
		else:
			filters["name"] = ["in", geo_volunteers]

	total = frappe.db.count("Volunteer", filters=filters)
	offset = (int(page) - 1) * int(page_size)

	volunteers = frappe.get_all(
		"Volunteer",
		filters=filters,
		fields=[
			"name", "full_name", "primary_phone",
			"email_address", "home_geo_node",
			"volunteer_status", "availability_status",
			"photo", "gender"
		],
		limit=int(page_size),
		start=offset,
		order_by="full_name asc"
	)

	return {
		"volunteers": volunteers,
		"total": total,
		"page": int(page),
		"page_size": int(page_size)
	}


@frappe.whitelist(allow_guest=True)
def register_volunteer(data):
	import json
	if isinstance(data, str):
		data = json.loads(data)

	# Consent validation
	if not data.get("consent_to_use_of_bio_data"):
		frappe.throw(_("You must consent to the use of your biodata to register."))
	if not data.get("accepted_volunteer_terms"):
		frappe.throw(_("You must accept the Volunteer Terms and Conditions to register."))

	# Basic phone validation
	primary_phone = (data.get("primary_phone") or "").strip()
	if not primary_phone or len(primary_phone) < 7:
		frappe.throw(_("Please provide a valid primary phone number (at least 7 characters)."))

	# Email validation
	email_address = (data.get("email_address") or "").strip()
	if email_address:
		if not frappe.utils.validate_email_address(email_address):
			frappe.throw(_("Please provide a valid email address."))

	# Duplicate check
	if frappe.db.exists("Volunteer", {"primary_phone": primary_phone}):
		frappe.throw(_("A volunteer with this phone number already exists."))
	if email_address and frappe.db.exists("Volunteer", {"email_address": email_address}):
		frappe.throw(_("A volunteer with this email address already exists."))

	# Validate languages — skip any that don't exist as Language records
	raw_languages = data.get("languages", [])
	valid_languages = []
	for lang_row in raw_languages:
		lang_name = lang_row.get("language", "")
		if lang_name and frappe.db.exists("Language", lang_name):
			valid_languages.append(lang_row)
		elif lang_name:
			frappe.log_error(
				f"register_volunteer: language '{lang_name}' not found in Language master, skipping.",
				"Volunteer Registration"
			)

	doc = frappe.get_doc({
		"doctype": "Volunteer",
		"naming_series": "VOL-.YY.-.#####",
		"first_name": data.get("first_name"),
		"middle_name": data.get("middle_name"),
		"last_name": data.get("last_name"),
		"date_of_birth": data.get("date_of_birth"),
		"gender": data.get("gender"),
		"nationality": data.get("nationality"),
		"primary_phone": primary_phone,
		"email_address": email_address or None,
		"emergency_contact_name": data.get("emergency_contact_name"),
		"emergency_contact_relationship": data.get("emergency_contact_relationship"),
		"emergency_contact_phone": data.get("emergency_contact_phone"),
		"physical_address": data.get("physical_address"),
		"home_geo_node": data.get("home_geo_node"),
		"availability_status": data.get("availability_status"),
		"volunteer_status": "Draft",
		"consent_to_use_of_bio_data": 1,
		"accepted_volunteer_terms": 1,
		"skills": data.get("skills", []),
		"languages": valid_languages,
		"availability": data.get("availability", []),
	})

	doc.insert(ignore_permissions=True)

	return {"name": doc.name}
