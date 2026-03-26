import frappe


@frappe.whitelist(allow_guest=True)
def get_app_bootstrap():
	settings = frappe.get_doc("National Society Settings", "National Society Settings")

	geo_levels = frappe.get_all(
		"Geo Level",
		filters={"is_active": 1},
		fields=["name", "level_name", "level_key", "level_order", "is_lowest_level"],
		order_by="level_order asc"
	)

	return {
		"organization": {
			"name": settings.organization_name,
			"short_name": settings.organization_short_name,
			"country": settings.country,
			"primary_color": settings.primary_color,
			"secondary_color": settings.secondary_color,
		},
		"labels": {
			"volunteer": settings.volunteer_label or "Volunteer",
			"member": settings.member_label or "Member",
			"branch": settings.branch_label or "Branch",
			"region": settings.region_label or "Region",
		},
		"geo": {
			"max_depth": settings.maximum_geographical_depth,
			"levels": geo_levels,
		}
	}