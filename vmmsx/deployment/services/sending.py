# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Asking people to join a deployment: now, at a set time, or in the background.

The old Deployment Request Tool's three sending choices, on the deployment
itself rather than on a separate tool record:

* **Which channels.** `notify_by_email` and `notify_by_sms` on the deployment.
  The portal notification is always raised by the assignment's own
  `after_insert`; this module adds the email and the text beside it, and only for
  an ask — a placement records something already arranged and tells nobody.
* **When.** With `send_on` in the future, the chosen people are written to
  `scheduled_asks` and told nothing. `send_due`, every five minutes, raises
  their asks once the time has come. Without one, they are asked straight away.
* **How many at once.** Asking or placing more than `BACKGROUND_FROM` people
  runs as a background job, so a coordinator asking a whole county is not left
  watching a request time out; the job tells them when it has finished.

**`assignment.deploy` does the asking in every case.** One savepoint per
person, and a report of who did not take, so none of the three paths has its
own idea of what asking somebody means.
"""

import frappe
from frappe import _
from frappe.utils import get_datetime, get_url, now_datetime

from vmmsx.deployment.services import assignment

DEPLOYMENT_DOCTYPE = "VMMS Deployment"

ASK = "ask"
PLACE = "place"
MODES = (ASK, PLACE)

# Above this many people, asking runs in the background. Fifty is a page of the
# candidate list: a coordinator ticking people by hand never waits on a job,
# and one pressing "select all" on a county always does.
BACKGROUND_FROM = 50


def send(deployment_doc, volunteers: list[str], mode: str) -> dict:
	"""Ask or place these people on this deployment, now, later or in the background.

	Returns what happened in a shape a screen can say in one line: `sent` with
	the `assignment.deploy` report, `scheduled` with the count and the time, or
	`queued` with the count.
	"""
	if mode not in MODES:
		frappe.throw(_("Choose whether to ask these volunteers or place them."), frappe.ValidationError)

	people = list(dict.fromkeys(volunteer for volunteer in volunteers or [] if volunteer))

	if not people:
		return {"state": "sent", "success": [], "failure": []}

	if mode == ASK and is_scheduled(deployment_doc):
		return schedule(deployment_doc, people)

	status = assignment.STATUS_PENDING if mode == ASK else assignment.STATUS_ASSIGNED

	if len(people) > BACKGROUND_FROM:
		frappe.enqueue(
			"vmmsx.deployment.services.sending.deploy_in_background",
			queue="long",
			deployment=deployment_doc.name,
			volunteers=people,
			status=status,
			coordinator=frappe.session.user,
			enqueue_after_commit=True,
		)
		return {"state": "queued", "count": len(people)}

	return {"state": "sent", **assignment.deploy(deployment_doc, people, status=status)}


def is_scheduled(deployment_doc) -> bool:
	"""A send time still ahead of us. One already past sends straight away."""
	return bool(deployment_doc.get("send_on")) and get_datetime(deployment_doc.send_on) > now_datetime()


def schedule(deployment_doc, volunteers: list[str]) -> dict:
	"""Hold these asks until the deployment's send time. Nobody is told yet.

	Somebody already waiting, or already on the roster, is not added twice:
	`assignment.create` would refuse them at the send time anyway, and a
	coordinator seeing "12 scheduled" should be looking at twelve people.
	"""
	waiting = {row.volunteer for row in deployment_doc.get("scheduled_asks") or []}
	on_roster = set(
		frappe.get_all(
			assignment.ASSIGNMENT_DOCTYPE,
			filters={
				"deployment": deployment_doc.name,
				"status": ("in", assignment.OPEN_STATUSES),
			},
			pluck="volunteer",
		)
	)
	added = [volunteer for volunteer in volunteers if volunteer not in waiting | on_roster]

	for volunteer in added:
		deployment_doc.append("scheduled_asks", {"volunteer": volunteer})

	deployment_doc.asks_sent_on = None
	deployment_doc.save()

	return {"state": "scheduled", "count": len(added), "send_on": deployment_doc.send_on}


def unschedule(deployment_doc, volunteer: str) -> None:
	"""Take one person off the scheduled list before the time comes."""
	deployment_doc.set(
		"scheduled_asks",
		[row for row in deployment_doc.get("scheduled_asks") or [] if row.volunteer != volunteer],
	)
	deployment_doc.save()


def send_due() -> None:
	"""Raise every scheduled ask whose time has come. Every five minutes.

	A deployment whose send time was cleared while people were waiting sends
	them now: no time means straight away, and nobody chosen is left unasked.

	Idempotent: a deployment's rows are cleared and `asks_sent_on` stamped
	together with its asks being raised, so a second run finds nothing. One
	deployment failing is logged and does not stop the others.
	"""
	due = frappe.db.sql(
		"""select distinct deployment.name
		from `tabVMMS Deployment` deployment
		join `tabVMMS Scheduled Ask` waiting
			on waiting.parent = deployment.name and waiting.parenttype = 'VMMS Deployment'
		where (deployment.send_on is null or deployment.send_on <= %s)""",
		now_datetime(),
		pluck=True,
	)

	# A savepoint per deployment, not a commit: the scheduler commits the job,
	# and one deployment failing rolls back only its own asks.
	for name in due:
		try:
			frappe.db.savepoint("scheduled_asks")
			_send_scheduled(name)
		except Exception:
			frappe.db.rollback(save_point="scheduled_asks")
			frappe.log_error(title=f"vmmsx: scheduled asks for {name} were not sent", message=frappe.get_traceback())


def _send_scheduled(name: str) -> None:
	from vmmsx.deployment.services import deployment as deployment_service

	deployment_doc = frappe.get_doc(DEPLOYMENT_DOCTYPE, name)
	people = [row.volunteer for row in deployment_doc.get("scheduled_asks") or []]

	# A deployment cancelled or finished while its asks were waiting asks nobody.
	if deployment_doc.status in deployment_service.OPEN_STATUSES and people:
		report = _as(deployment_doc.coordinator, lambda: assignment.deploy(deployment_doc, people))
		_tell_coordinator(deployment_doc, report)

	frappe.db.delete("VMMS Scheduled Ask", {"parent": name, "parenttype": DEPLOYMENT_DOCTYPE})
	frappe.db.set_value(DEPLOYMENT_DOCTYPE, name, "asks_sent_on", now_datetime(), update_modified=False)


def deploy_in_background(deployment: str, volunteers: list[str], status: str, coordinator: str) -> None:
	"""The background half of `send`: ask or place, then tell whoever pressed the button."""
	deployment_doc = frappe.get_doc(DEPLOYMENT_DOCTYPE, deployment)
	report = _as(coordinator, lambda: assignment.deploy(deployment_doc, volunteers, status=status))
	_tell_coordinator(deployment_doc, report)


def _as(user: str | None, work):
	"""Do this as the coordinator, so their scope and their name are on every row.

	A job runs as Administrator; a deployment asked for at 08:00 by a scheduler
	should still be asked for *by* the coordinator who chose the people, and be
	held to the same scope they were.
	"""
	previous = frappe.session.user

	try:
		if user and frappe.db.exists("User", user):
			frappe.set_user(user)
		return work()
	finally:
		frappe.set_user(previous)


def _tell_coordinator(deployment_doc, report: dict) -> None:
	from vmmsx.notifications.services import direct

	asked, missed = len(report.get("success") or []), len(report.get("failure") or [])
	subject = (
		_("{0}: {1} volunteers added, {2} could not be added").format(deployment_doc.title, asked, missed)
		if missed
		else _("{0}: {1} volunteers added").format(deployment_doc.title, asked)
	)
	direct.tell([deployment_doc.coordinator], subject, DEPLOYMENT_DOCTYPE, deployment_doc.name)


# --- the email and the text beside the portal notification ------------------


def notify_ask(assignment_doc) -> None:
	"""Email and text the volunteer about an ask, by the deployment's channels.

	Called from the assignment's `after_insert`, after the portal notification.
	Never raises: a mail server or SMS gateway being down must not undo the ask.
	"""
	try:
		deployment_doc = frappe.get_cached_doc(DEPLOYMENT_DOCTYPE, assignment_doc.deployment)
		person = _person(assignment_doc.volunteer)

		if not person:
			return

		link = get_url(f"/portal/deployments/requests/{assignment_doc.name}")

		if deployment_doc.get("notify_by_email") and person.get("email"):
			_email(deployment_doc, assignment_doc, person, link)

		if deployment_doc.get("notify_by_sms") and person.get("phone"):
			from vmmsx.notifications.services import sms

			sms.tell(
				person["phone"],
				_("Kindly confirm whether you can join {0} from {1}: {2}").format(
					deployment_doc.title,
					frappe.format_value(assignment_doc.start_date, {"fieldtype": "Date"}),
					link,
				),
			)
	except Exception:
		frappe.log_error(title="vmmsx: could not email or text a deployment ask", message=frappe.get_traceback())


def _person(volunteer: str) -> dict | None:
	profile = frappe.db.get_value("VMMS Volunteer", volunteer, "red_profile")

	if not profile:
		return None

	return frappe.db.get_value("Red Profile", profile, ["full_name", "email", "phone"], as_dict=True)


def _email(deployment_doc, assignment_doc, person: dict, link: str) -> None:
	context = {
		"volunteer_name": person.get("full_name") or "",
		"deployment_title": deployment_doc.title,
		"start_date": frappe.format_value(assignment_doc.start_date, {"fieldtype": "Date"}),
		"end_date": frappe.format_value(assignment_doc.end_date, {"fieldtype": "Date"}),
		"site_name": deployment_doc.get("site_name") or "",
		"meeting_point": deployment_doc.get("meeting_point") or "",
		"link": link,
	}

	if deployment_doc.get("email_template"):
		from frappe.email.doctype.email_template.email_template import get_email_template

		rendered = get_email_template(deployment_doc.email_template, context)
		subject, message = rendered["subject"], rendered["message"]
	else:
		subject = _("You have been asked to join {0}").format(deployment_doc.title)
		message = _(
			"<p>Dear {volunteer_name},</p>"
			"<p>You have been asked to join <strong>{deployment_title}</strong>, from {start_date} to {end_date}.</p>"
			"<p><a href=\"{link}\">Accept or decline on the portal</a>.</p>"
		).format(**{key: frappe.utils.escape_html(value) for key, value in context.items()})

	frappe.sendmail(
		recipients=[person["email"]],
		subject=subject,
		message=message,
		reference_doctype=assignment_doc.doctype,
		reference_name=assignment_doc.name,
		now=False,
	)
