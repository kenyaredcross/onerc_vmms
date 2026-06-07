import frappe


@frappe.whitelist()
def get_my_deployments():
	user = frappe.session.user
	volunteer = frappe.db.get_value(
		"Volunteer", {"user_account": user}, "name"
	)
	if not volunteer:
		return []

	rows = frappe.get_all(
		"Deployment Request Volunteer",
		filters={"volunteer": volunteer},
		fields=["name", "parent", "response", "response_date", "notified_at"],
		order_by="notified_at desc"
	)

	result = []
	for row in rows:
		dr = frappe.get_doc("Deployment Request", row.parent)
		tor = frappe.get_doc("Terms of Reference", dr.tor)
		result.append({
			"deployment_request": row.parent,
			"assignment_row": row.name,
			"response": row.response,
			"response_date": str(row.response_date) if row.response_date else None,
			"notified_at": str(row.notified_at) if row.notified_at else None,
			"mission_title": tor.title_of_mission,
			"mission_type": dr.deployment_type,
			"start_date": str(tor.start_date) if tor.start_date else None,
			"end_date": str(tor.end_date) if tor.end_date else None,
			"location": tor.location_description or "",
			"status": dr.status,
			"response_deadline": str(dr.response_deadline) if dr.response_deadline else None,
		})
	return result


@frappe.whitelist()
def get_deployment_detail(deployment_request):
	user = frappe.session.user
	volunteer = frappe.db.get_value(
		"Volunteer", {"user_account": user}, "name"
	)

	dr = frappe.get_doc("Deployment Request", deployment_request)
	tor = frappe.get_doc("Terms of Reference", dr.tor)

	my_row = next(
		(r for r in dr.volunteers if r.volunteer == volunteer), None
	)
	if not my_row:
		frappe.throw("You are not assigned to this deployment.")

	return {
		"deployment_request": dr.name,
		"assignment_row": my_row.name,
		"my_response": my_row.response,
		"response_deadline": str(dr.response_deadline) if dr.response_deadline else None,
		"message_from_manager": dr.message_to_volunteers or "",
		"mission": {
			"title": tor.title_of_mission,
			"type": dr.deployment_type,
			"start_date": str(tor.start_date) if tor.start_date else None,
			"end_date": str(tor.end_date) if tor.end_date else None,
			"duration_days": tor.duration_days,
			"location": tor.location_description or "",
			"background": tor.mission_background or "",
			"objectives": tor.objectives or "",
			"expected_output": tor.expected_output or "",
		},
		"itinerary": [
			{
				"date": str(r.date) if r.date else None,
				"start_time": str(r.start_time) if r.start_time else None,
				"end_time": str(r.end_time) if r.end_time else None,
				"activity": r.activity,
				"person_responsible": r.person_responsible,
				"venue": r.venue,
			}
			for r in tor.itinerary
		],
	}


@frappe.whitelist()
def respond_to_deployment(assignment_row, response, reason=None):
	if response not in ("Accepted", "Declined", "Withdrawn"):
		frappe.throw("Response must be Accepted, Declined, or Withdrawn.")

	user = frappe.session.user
	volunteer = frappe.db.get_value(
		"Volunteer", {"user_account": user}, "name"
	)

	row = frappe.get_doc("Deployment Request Volunteer", assignment_row)
	if row.volunteer != volunteer:
		frappe.throw("Not authorised to respond to this assignment.")

	row.response = response
	row.response_date = frappe.utils.now_datetime()
	if response == "Declined":
		row.decline_reason = reason or ""
	if response == "Withdrawn":
		row.withdrawal_reason = reason or ""
	row.save(ignore_permissions=True)

	dr = frappe.get_doc("Deployment Request", row.parent)
	dr.update_status_summary()
	dr.save(ignore_permissions=True)
	frappe.db.commit()

	return {"status": "ok", "response": response}


@frappe.whitelist()
def submit_daily_report(
	deployment_request, report_date, activities_completed,
	beneficiaries_reached=0, challenges_faced=None,
	support_needed=None, current_location=None, safety_status="Safe"
):
	user = frappe.session.user
	volunteer = frappe.db.get_value(
		"Volunteer", {"user_account": user}, "name"
	)
	if not volunteer:
		frappe.throw("No volunteer profile found for your account.")

	if frappe.db.exists("Daily Field Report", {
		"volunteer": volunteer,
		"deployment_request": deployment_request,
		"report_date": report_date
	}):
		frappe.throw("You have already submitted a report for this date.")

	doc = frappe.get_doc({
		"doctype": "Daily Field Report",
		"volunteer": volunteer,
		"deployment_request": deployment_request,
		"report_date": report_date,
		"activities_completed": activities_completed,
		"beneficiaries_reached": int(beneficiaries_reached or 0),
		"challenges_faced": challenges_faced or "",
		"support_needed": support_needed or "",
		"current_location": current_location or "",
		"safety_status": safety_status,
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"name": doc.name}
