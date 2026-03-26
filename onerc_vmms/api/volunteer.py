import frappe


@frappe.whitelist()
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

	if geo_node:
		filters["home_geo_node"] = geo_node

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

	if skill:
		volunteers = filter_by_skill(volunteers, skill)

	if language:
		volunteers = filter_by_language(volunteers, language)

	total = frappe.db.count("Volunteer", filters=filters)

	return {
		"volunteers": volunteers,
		"total": total,
		"page": int(page),
		"page_size": int(page_size)
	}


def filter_by_skill(volunteers, skill):
	result = []
	for v in volunteers:
		has_skill = frappe.db.exists(
			"Volunteer Skill",
			{"parent": v["name"], "skill": ["like", f"%{skill}%"]}
		)
		if has_skill:
			result.append(v)
	return result


def filter_by_language(volunteers, language):
	result = []
	for v in volunteers:
		has_language = frappe.db.exists(
			"Volunteer Language",
			{"parent": v["name"], "language": language}
		)
		if has_language:
			result.append(v)
	return result