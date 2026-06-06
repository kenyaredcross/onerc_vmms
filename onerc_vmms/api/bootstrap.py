import frappe


@frappe.whitelist(allow_guest=True)
def get_app_bootstrap():
	try:
		org = frappe.get_single("National Society Settings")
	except Exception:
		org = frappe._dict()

	try:
		vmms = frappe.get_single("VMMS Settings")
	except Exception:
		vmms = frappe._dict()

	geo_levels = frappe.get_all(
		"Geo Level",
		filters={"is_active": 1},
		fields=["name", "geo_level_name", "geo_level_key", "geo_level_order", "is_lowest_level"],
		order_by="geo_level_order asc"
	)

	return {
		"organization": {
			"name": org.get("organization_name") or "OneRC",
			"short_name": org.get("organization_short_name") or "",
			"country": org.get("country") or "",
			"primary_color": org.get("primary_color") or "#EE2435",
			"secondary_color": org.get("secondary_color") or "#011E41",
			"accent_color": org.get("accent_color") or "",
			"logo": org.get("logo") or "",
			"website": org.get("official_website") or "",
			"telephone": org.get("telephone") or "",
		},
		"labels": {
			"volunteer": vmms.get("volunteer_label") or "Volunteer",
			"member": vmms.get("member_label") or "Member",
			"branch": vmms.get("branch_label") or "Branch",
			"region": vmms.get("region_label") or "Region",
		},
		"geo": {
			"levels": geo_levels,
			"root_label": org.get("root_geo_label") or "",
		},
		"features": {
			"membership_enabled": vmms.get("membership_enabled") or 0,
			"sms_enabled": org.get("sms_enabled") or 0,
			"public_feedback_enabled": org.get("enable_public_feedback") or 0,
			"public_incident_reporting": org.get("enable_public_incident_reporting") or 0,
		},
		"consent": {
			"biodata_text": vmms.get("consent_biodata_text") or "I consent to the use of my biodata for deployment purposes.",
			"volunteer_terms": vmms.get("terms_and_conditions_volunteer") or "",
			"membership_terms": vmms.get("terms_and_conditions_membership") or "",
		}
	}
