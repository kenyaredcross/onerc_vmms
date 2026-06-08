import frappe


@frappe.whitelist()
def get_my_profile():
	user = frappe.session.user
	volunteer = frappe.db.get_value(
		"Volunteer", {"user_account": user}, "name"
	)
	if not volunteer:
		return None

	doc = frappe.get_doc("Volunteer", volunteer)

	return {
		"name": doc.name,
		"full_name": doc.full_name,
		"first_name": doc.first_name,
		"middle_name": doc.middle_name or "",
		"last_name": doc.last_name,
		"date_of_birth": str(doc.date_of_birth) if doc.date_of_birth else "",
		"gender": doc.gender or "",
		"nationality": doc.nationality or "",
		"primary_phone": doc.primary_phone or "",
		"email_address": doc.email_address or "",
		"photo": doc.photo or "",
		"volunteer_status": doc.volunteer_status or "",
		"availability_status": doc.availability_status or "",
		"membership_status": doc.membership_status or "",
		"home_geo_node": doc.home_geo_node or "",
		"current_geo_node": doc.current_geo_node or "",
		"branch_geo_node": doc.branch_geo_node or "",
		"physical_address": doc.physical_address or "",
		"emergency_contact_name": doc.emergency_contact_name or "",
		"emergency_contact_relationship": doc.emergency_contact_relationship or "",
		"emergency_contact_phone": doc.emergency_contact_phone or "",
		"skills": [
			{
				"skill": r.skill,
				"proficiency_level": r.proficiency_level,
				"years_of_experience": r.years_of_experience or 0,
			}
			for r in doc.skills
		],
		"languages": [
			{
				"language": r.language,
				"spoken_proficiency": r.spoken_proficiency,
				"written_proficiency": r.written_proficiency or "",
			}
			for r in doc.languages
		],
		"education": [
			{
				"institution": r.institution,
				"qualification": r.qualification,
				"field_of_study": r.field_of_study or "",
				"from_year": r.from_year or "",
				"to_year": r.to_year or "",
			}
			for r in doc.education
		],
		"experience": [
			{
				"employer": r.employer,
				"role_position": r.role_position or "",
				"from_date": str(r.from_date) if r.from_date else "",
				"to_date": str(r.to_date) if r.to_date else "",
			}
			for r in doc.work_experience
		],
		"trainings": [
			{
				"course_name": r.course_name,
				"provider": r.provider or "",
				"from_date": str(r.from_date) if r.from_date else "",
				"expiry_date": str(r.expiry_date) if r.expiry_date else "",
			}
			for r in doc.trainings
		],
		"availability": [
			{
				"availability_type": r.availability_type,
				"from_date": str(r.from_date) if r.from_date else "",
				"monday": r.monday or 0,
				"tuesday": r.tuesday or 0,
				"wednesday": r.wednesday or 0,
				"thursday": r.thursday or 0,
				"friday": r.friday or 0,
				"saturday": r.saturday or 0,
				"sunday": r.sunday or 0,
			}
			for r in doc.availability
		],
	}


@frappe.whitelist()
def update_volunteer_profile(section, data):
	import json
	if isinstance(data, str):
		data = json.loads(data)

	user = frappe.session.user
	volunteer = frappe.db.get_value(
		"Volunteer", {"user_account": user}, "name"
	)
	if not volunteer:
		frappe.throw("No volunteer profile found.")

	doc = frappe.get_doc("Volunteer", volunteer)

	if section == "personal":
		for field in ["first_name", "middle_name", "last_name",
					  "date_of_birth", "gender", "nationality",
					  "primary_phone", "email_address",
					  "emergency_contact_name",
					  "emergency_contact_relationship",
					  "emergency_contact_phone"]:
			if field in data:
				setattr(doc, field, data[field])

	elif section == "location":
		for field in ["home_geo_node", "current_geo_node",
					  "branch_geo_node", "physical_address"]:
			if field in data:
				setattr(doc, field, data[field])

	elif section == "skills":
		doc.skills = []
		for row in data.get("skills", []):
			doc.append("skills", {
				"skill": row.get("skill"),
				"proficiency_level": row.get("proficiency_level"),
				"years_of_experience": row.get("years_of_experience", 0),
			})

	elif section == "languages":
		doc.languages = []
		for row in data.get("languages", []):
			doc.append("languages", {
				"language": row.get("language"),
				"spoken_proficiency": row.get("spoken_proficiency"),
				"written_proficiency": row.get("written_proficiency", ""),
			})

	elif section == "professional":
		doc.education = []
		for row in data.get("education", []):
			doc.append("education", {
				"institution": row.get("institution"),
				"qualification": row.get("qualification"),
				"field_of_study": row.get("field_of_study", ""),
				"from_year": row.get("from_year") or None,
				"to_year": row.get("to_year") or None,
			})
		doc.work_experience = []
		for row in data.get("experience", []):
			doc.append("work_experience", {
				"employer": row.get("employer"),
				"role_position": row.get("role_position", ""),
				"from_date": row.get("from_date") or None,
				"to_date": row.get("to_date") or None,
			})
		doc.trainings = []
		for row in data.get("trainings", []):
			doc.append("trainings", {
				"course_name": row.get("course_name"),
				"provider": row.get("provider", ""),
				"from_date": row.get("from_date") or None,
				"expiry_date": row.get("expiry_date") or None,
			})

	elif section == "availability":
		if "availability_status" in data:
			doc.availability_status = data["availability_status"]
		doc.availability = []
		for row in data.get("availability", []):
			doc.append("availability", {
				"availability_type": row.get("availability_type"),
				"from_date": row.get("from_date") or None,
				"monday": row.get("monday", 0),
				"tuesday": row.get("tuesday", 0),
				"wednesday": row.get("wednesday", 0),
				"thursday": row.get("thursday", 0),
				"friday": row.get("friday", 0),
				"saturday": row.get("saturday", 0),
				"sunday": row.get("sunday", 0),
			})

	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return {"status": "ok"}
