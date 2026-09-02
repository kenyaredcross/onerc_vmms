# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Dense, deterministic presentation data for the Tanzania demo site.

This is the scale layer, not the lifecycle exemplar. ``tanzania_people`` and
``tanzania_deployments`` first create a smaller set through the public APIs so
the site contains complete approval and response trails. This module then adds
enough explicitly fictional historical data for registers, charts, filters and
branch comparisons to look lived in.

No mail is sent. Historical email-looking records are Communications marked as
sent; announcements are fanned out in-app with ``also_email`` disabled. Every
generated address uses the reserved ``example.invalid`` domain.
"""

from __future__ import annotations

import frappe
from frappe.utils import add_days, add_to_date, now_datetime, today

from vmmsx.seed import tanzania

PEOPLE = 240
DEPLOYMENTS_PER_PROJECT = 2
ASSIGNMENTS_PER_DEPLOYMENT = 8

FIRST_NAMES = (
	"Amina", "Baraka", "Chausiku", "Daudi", "Elia", "Faraja", "Grace", "Hamisi",
	"Imani", "Jabari", "Khadija", "Luka", "Mariam", "Neema", "Omari", "Pendo",
	"Rahma", "Salum", "Tumaini", "Upendo", "Victor", "Wema", "Yusra", "Zawadi",
)
LAST_NAMES = (
	"Amani", "Chacha", "Haule", "Juma", "Kalanga", "Kessy", "Kileo", "Kimaro",
	"Magesa", "Massawe", "Mbwana", "Mollel", "Mushi", "Mwakalebela", "Mwakasege",
	"Mwansasu", "Nnko", "Omary", "Selemani", "Shija",
)
PROJECT_THEMES = (
	("Community Health and First Aid", "Community first aid, household health promotion and referral."),
	("Flood Preparedness and Response", "Seasonal preparedness, early warning and relief readiness."),
	("Youth and School Safety", "Youth engagement, school safety clubs and practical preparedness."),
	("Blood Donor Mobilisation", "Community mobilisation and support for safe blood donation drives."),
	("Road Safety Outreach", "First aid readiness and road-safety awareness in busy communities."),
)
TASKS = (
	("Complete household assessment forms", "Visit the assigned households and submit the completed assessment summary."),
	("Check first aid post inventory", "Count consumables, flag shortages and confirm the response kit is ready."),
	("Mobilise community participants", "Contact local leaders and confirm attendance for the scheduled session."),
	("Prepare activity report", "Summarise attendance, work completed, issues and follow-up actions."),
	("Support volunteer briefing", "Help register participants and distribute the briefing materials."),
)
ANNOUNCEMENTS = (
	("Monthly volunteer briefing", "The monthly volunteer briefing and branch updates are now available."),
	("First aid refresher registration", "Registration is open for the next practical first aid refresher."),
	("Seasonal preparedness update", "Please review your availability and emergency contact details."),
	("Volunteer appreciation message", "Thank you for the time and care you continue to give your community."),
)


def main(commit: bool = True) -> dict:
	if not tanzania.national():
		frappe.throw("The Tanzania configuration is not present on this site.")

	nodes = _service_nodes()
	if not nodes:
		frappe.throw("No Tanzania branch or sub-branch Geo Nodes are available for demo data.")

	report = {}
	report["people"] = _people(nodes)
	volunteers = frappe.get_all(
		"VMMS Volunteer",
		filters={"notes": ["like", "[Tanzania scale demo]%"]},
		fields=["name", "home_geo_node", "red_profile"],
		order_by="name asc",
		limit_page_length=PEOPLE,
	)
	report["certifications"] = _certifications(volunteers)
	report["time_logs"] = _time_logs(volunteers)
	projects, terms, deployments = _portfolio(nodes)
	report["projects"] = len(projects)
	report["terms"] = len(terms)
	report["deployments"] = len(deployments)
	report["assignments"] = _assignments(deployments, volunteers)
	report["tasks"] = _tasks(volunteers, deployments)
	report["announcements"] = _announcements(nodes, volunteers)
	report["email_history"] = _communications(volunteers)

	if commit:
		frappe.db.commit()

	print("vmmsx Tanzania scale seed: " + ", ".join(f"{key}={value}" for key, value in report.items()))
	return report


def _service_nodes() -> list[str]:
	"""Use all 31 regional branches and every configured sub-branch."""
	nodes = list(filter(None, (tanzania.branch(label) for label in tanzania.REGIONS)))
	for parent, labels in tanzania.SUB_BRANCHES.items():
		for label in labels:
			node = tanzania.sub_branch(label, parent)
			if node:
				nodes.append(node)
	return sorted(set(nodes))


def _people(nodes: list[str]) -> int:
	from vmmsx.member.services import member as member_service
	from vmmsx.volunteer.services import volunteer as volunteer_service

	skills = frappe.get_all("VMMS Skill", pluck="name", order_by="name asc")
	availability = frappe.get_all("VMMS Availability Slot", pluck="name", order_by="name asc")
	membership_types = frappe.get_all(
		"VMMS Membership Type", filters={"is_active": 1}, pluck="name", order_by="name asc"
	)
	created = 0

	for index in range(1, PEOPLE + 1):
		first = FIRST_NAMES[(index - 1) % len(FIRST_NAMES)]
		last = LAST_NAMES[((index - 1) // len(FIRST_NAMES) + index * 7) % len(LAST_NAMES)]
		email = f"demo.person.{index:04d}@example.invalid"
		node = nodes[(index - 1) % len(nodes)]

		if not frappe.db.exists("User", email):
			frappe.get_doc({
				"doctype": "User", "email": email, "first_name": first, "last_name": last,
				"enabled": 0, "send_welcome_email": 0, "user_type": "Website User",
			}).insert(ignore_permissions=True)

		profile = frappe.db.get_value("Red Profile", {"user": email}, "name")
		if not profile:
			profile = frappe.get_doc({
				"doctype": "Red Profile", "first_name": first, "last_name": last,
				"email": email, "user": email, "phone": f"+2557009{index:05d}",
				"date_of_birth": f"{1978 + index % 25:04d}-{1 + index % 12:02d}-{1 + index % 27:02d}",
				"home_geo_node": node,
			}).insert(ignore_permissions=True).name

		volunteer = volunteer_service.ensure(profile, home_geo_node=node)
		changed = False
		if volunteer.status != "Active":
			volunteer.status = "Active"
			volunteer.joined_on = add_days(today(), -(45 + (index * 13) % 1400))
			changed = True
		if skills and not volunteer.skills:
			volunteer.set("skills", [{"skill": skills[index % len(skills)]}])
			changed = True
		if availability and not volunteer.availability:
			volunteer.set("availability", [{"availability_slot": availability[index % len(availability)]}])
			changed = True
		volunteer.notes = f"[Tanzania scale demo] Fictional presentation record {index:04d}."
		if changed or not volunteer.is_new():
			volunteer.save(ignore_permissions=True)

		if index <= 170:
			member = member_service.ensure(profile)
			if index % 19 == 0:
				member.db_set("status", "Lapsed", update_modified=False)
			else:
				member.db_set("status", "Active", update_modified=False)
			member.db_set("joined_on", add_days(today(), -(60 + index * 5)), update_modified=False)
			if membership_types and not frappe.db.exists("VMMS Membership", {"member": member.name}):
				status = "Expired" if index % 19 == 0 else ("Awaiting Approval" if index % 13 == 0 else "Active")
				doc = frappe.get_doc({
					"doctype": "VMMS Membership", "member": member.name,
					"membership_type": membership_types[index % len(membership_types)], "geo_node": node,
					"membership_source": "Gateway",
				}).insert(ignore_permissions=True)
				frappe.db.set_value("VMMS Membership", doc.name, {
					"membership_status": status,
					"approval_state": "Approved" if status in ("Active", "Expired") else "In Review",
					"valid_from": add_days(today(), -(60 + index * 5)),
					"valid_to": add_days(today(), -10) if status == "Expired" else add_days(today(), 300),
				}, update_modified=False)
		created += 1
	return created


def _certifications(volunteers: list[dict]) -> int:
	types = frappe.get_all("VMMS Certification Type", pluck="name", order_by="name asc")
	if not types:
		return 0
	count = 0
	for index, volunteer in enumerate(volunteers):
		for offset in range(1 + int(index % 4 == 0)):
			kind = types[(index + offset) % len(types)]
			if frappe.db.exists("VMMS Certification", {"volunteer": volunteer.name, "certification_type": kind}):
				continue
			frappe.get_doc({
				"doctype": "VMMS Certification", "volunteer": volunteer.name,
				"certification_type": kind, "completion_date": add_days(today(), -(40 + index * 3 + offset * 70)),
				"reference_number": f"TRCS-DEMO-{index + 1:04d}-{offset + 1}",
				"notes": "Fictional training history created for the presentation site.",
			}).insert(ignore_permissions=True)
			count += 1
	return count


def _time_logs(volunteers: list[dict]) -> int:
	categories = frappe.get_all("VMMS Time Log Category", pluck="name", order_by="name asc")
	count = 0
	for index, volunteer in enumerate(volunteers):
		for entry in range(3 + index % 5):
			activity_date = add_days(today(), -(8 + entry * 17 + index % 90))
			if frappe.db.exists("VMMS Time Log", {"volunteer": volunteer.name, "activity_date": activity_date}):
				continue
			frappe.get_doc({
				"doctype": "VMMS Time Log", "volunteer": volunteer.name,
				"geo_node": volunteer.home_geo_node, "log_type": "general",
				"log_category": categories[(index + entry) % len(categories)] if categories else None,
				"activity_date": activity_date, "hours": 2 + (index + entry) % 7,
				"notes": ("Supported community outreach, registration and follow-up activities. "
					"Fictional presentation history."),
			}).insert(ignore_permissions=True)
			count += 1
	return count


def _portfolio(nodes: list[str]) -> tuple[list[str], list[str], list[str]]:
	from vmmsx.deployment.services import project as project_service

	projects, terms, deployments = [], [], []
	for index, node in enumerate(nodes):
		label = frappe.db.get_value("Geo Node", node, "geo_node_name") or f"Area {index + 1}"
		theme, summary = PROJECT_THEMES[index % len(PROJECT_THEMES)]
		project_name = f"{label} {theme} 2026"
		# ERPNext's own Project; `VMMS Project` was retired for it. `notes` is the
		# story of the programme (what `summary` used to hold and what the printed
		# terms of reference puts at its head) and `vmms_planning_notes` the aside
		# beside the risks — see `setup/project_fields.py`.
		project = frappe.db.get_value("Project", {"project_name": project_name}, "name")
		if not project:
			project = frappe.get_doc({
				"doctype": "Project", "project_name": project_name, "status": "Open",
				"company": project_service.default_company(),
				"vmms_geo_node": node,
				"expected_start_date": add_days(today(), -180), "expected_end_date": add_days(today(), 180),
				"notes": summary,
				"vmms_planning_notes": "Fictional presentation programme with realistic branch activity.",
			}).insert(ignore_permissions=True).name
		projects.append(project)

		key = f"demo-{index + 1:03d}-{frappe.scrub(theme)[:28]}"
		tor = key if frappe.db.exists("VMMS Terms of Reference", key) else None
		if not tor:
			doc = frappe.get_doc({
				"doctype": "VMMS Terms of Reference", "tor_key": key, "tor_name": f"{label} Field Team",
				"project": project, "is_active": 1, "default_duration_days": 7, "geo_scope": node,
				"purpose": summary,
				"mission_background": ("<p>The branch requires a prepared volunteer team to support routine "
					"community work and respond quickly when local needs increase.</p>"),
				"responsibilities": ("Attend the briefing and follow the team leader.\nRecord activities accurately.\n"
					"Protect dignity, safety and confidentiality.\nSubmit a short end-of-mission report."),
				"approval_mode": "direct",
				"objectives": [{"objective": "Deliver the planned activity safely and reach the intended community."}],
				"expected_outputs": [{"output": "A completed activity register and branch summary report."}],
				# The mission period, the people and the days — the rest of what a
				# terms of reference has to say before its wording can be frozen.
				# See `deployment/services/terms.py::REQUIRED_AT_SUBMISSION`.
				"expected_start_date": add_days(today(), -180),
				"expected_end_date": add_days(today(), 180),
				"stakeholders": [
					{"designation": "Branch Coordinator"},
					{"designation": "Team Leader"},
				],
				"itinerary": [
					{"activity_date": add_days(today(), -180), "activity": "Team briefing and assignment",
						"person_responsible": "Team Leader"},
					{"activity_date": add_days(today(), -90), "activity": f"{label} field activity",
						"person_responsible": "Team Leader"},
					{"activity_date": add_days(today(), 180), "activity": "Debrief and hand over the record",
						"person_responsible": "Branch Coordinator"},
				],
				# Standing branch work resourced from the branch's own stock. Said
				# out loud, because an empty resources table has to be a deliberate
				# answer rather than one nobody got to.
				"has_no_resources": 1,
			})
			doc.insert(ignore_permissions=True)
			doc.submit()
			tor = doc.name
		terms.append(tor)

		for sequence in range(DEPLOYMENTS_PER_PROJECT):
			start = add_days(today(), -35 + index * 2 + sequence * 45)
			existing = frappe.db.get_value("VMMS Deployment", {
				"terms_of_reference": tor, "geo_node": node, "start_date": start,
			}, "name")
			if existing:
				deployments.append(existing)
				continue
			status = "Completed" if sequence == 0 else ("Active" if index % 3 else "Planned")
			deployment = frappe.get_doc({
				"doctype": "VMMS Deployment", "terms_of_reference": tor, "geo_node": node,
				"coordinator": frappe.session.user,
				"start_date": start, "end_date": add_days(start, 6), "status": status,
				"volunteers_required": ASSIGNMENTS_PER_DEPLOYMENT,
				"notes": f"{label} team deployment. Fictional presentation record.",
			}).insert(ignore_permissions=True)
			deployments.append(deployment.name)
	return projects, terms, deployments


def _assignments(deployments: list[str], volunteers: list[dict]) -> int:
	from vmmsx.deployment.services import assignment as assignment_service

	by_node = {}
	for volunteer in volunteers:
		by_node.setdefault(volunteer.home_geo_node, []).append(volunteer.name)
	all_volunteers = [row.name for row in volunteers]
	count = 0
	for index, name in enumerate(deployments):
		doc = frappe.get_doc("VMMS Deployment", name)
		# Prefer the local team, then fill from the wider register. Never cycle a
		# short local list: one volunteer may hold only one open assignment on a
		# deployment, and a duplicate would correctly be refused by the service.
		pool = list(dict.fromkeys((by_node.get(doc.geo_node) or []) + all_volunteers))
		start = (index * ASSIGNMENTS_PER_DEPLOYMENT) % len(pool)
		ordered = pool[start:] + pool[:start]
		for offset, volunteer in enumerate(ordered[:ASSIGNMENTS_PER_DEPLOYMENT]):
			if frappe.db.exists("VMMS Deployment Assignment", {"deployment": name, "volunteer": volunteer}):
				continue
			assignment_service.create(
				doc, volunteer, status="Assigned", role="leader" if offset == 0 else "member",
				notes="Fictional roster placement for presentation data.",
			)
			count += 1
	return count


def _tasks(volunteers: list[dict], deployments: list[str]) -> int:
	count = 0
	for index, volunteer in enumerate(volunteers[:180]):
		subject, description = TASKS[index % len(TASKS)]
		if frappe.db.exists("VMMS Task", {"volunteer": volunteer.name, "subject": subject}):
			continue
		status = ("assigned", "accepted", "submitted", "completed")[index % 4]
		assigned = add_to_date(now_datetime(), days=-(4 + index % 40))
		updates = [{"entry_type": "assigned", "author": "Administrator", "posted_on": assigned, "note": description}]
		if status != "assigned":
			updates.append({"entry_type": "accepted", "author": "Administrator", "posted_on": add_to_date(assigned, hours=6)})
		if status in ("submitted", "completed"):
			updates.append({"entry_type": "submitted", "author": "Administrator", "posted_on": add_to_date(assigned, days=2), "note": "Activity completed and report attached to the branch register."})
		if status == "completed":
			updates.append({"entry_type": "completed", "author": "Administrator", "posted_on": add_to_date(assigned, days=3), "note": "Reviewed and signed off by the coordinator."})
		frappe.get_doc({
			"doctype": "VMMS Task", "subject": subject, "volunteer": volunteer.name,
			"geo_node": volunteer.home_geo_node, "deployment": deployments[index % len(deployments)] if deployments and index % 2 == 0 else None,
			"description": description, "due_on": add_days(today(), 7 - index % 20), "status": status,
			"assigned_on": assigned, "accepted_on": add_to_date(assigned, hours=6) if status != "assigned" else None,
			"submitted_on": add_to_date(assigned, days=2) if status in ("submitted", "completed") else None,
			"closed_on": add_to_date(assigned, days=3) if status == "completed" else None,
			"completion_notes": "Activity completed and documented." if status in ("submitted", "completed") else None,
			"updates": updates,
		}).insert(ignore_permissions=True)
		count += 1
	return count


def _announcements(nodes: list[str], volunteers: list[dict]) -> int:
	from vmmsx.notifications.services import delivery

	users = {
		row.name: frappe.db.get_value("Red Profile", row.red_profile, "user")
		for row in volunteers
	}
	count = 0
	for index, (title, body) in enumerate(ANNOUNCEMENTS):
		full_title = f"{title} — demo {index + 1}"
		name = frappe.db.get_value("VMMS Announcement", {"title": full_title}, "name")
		if not name:
			doc = frappe.get_doc({
				"doctype": "VMMS Announcement", "title": full_title, "urgency": ("routine", "important", "urgent")[index % 3],
				"geo_node": nodes[index % len(nodes)], "audience": ("everyone", "volunteers", "members")[index % 3],
				"summary": body, "body": body + " This is fictional presentation content.",
				"status": "Published", "also_email": 0, "expires_on": add_days(today(), 45 + index * 10),
			}).insert(ignore_permissions=True)
			name = doc.name
		for volunteer in volunteers[index::4]:
			user = users.get(volunteer.name)
			if user:
				delivery.ensure(name, user)
		count += 1
	return count


def _communications(volunteers: list[dict]) -> int:
	count = 0
	for index, volunteer in enumerate(volunteers[:60]):
		recipient = frappe.db.get_value("Red Profile", volunteer.red_profile, "email")
		subject = f"TRCS demo activity update {index + 1:03d}"
		if frappe.db.exists("Communication", {"subject": subject, "recipients": recipient}):
			continue
		frappe.get_doc({
			"doctype": "Communication", "communication_type": "Communication",
			"communication_medium": "Email", "sent_or_received": "Sent", "status": "Linked",
			"subject": subject, "content": ("This is a fictional historical email for the presentation site. "
				"It was not delivered to an external mailbox."),
			"sender": "Administrator", "recipients": recipient,
			"reference_doctype": "VMMS Volunteer", "reference_name": volunteer.name,
		}).insert(ignore_permissions=True)
		count += 1
	return count
