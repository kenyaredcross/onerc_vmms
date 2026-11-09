# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Telling a branch that a surge licence is running out.

Here rather than in the volunteer module on purpose: that module has no
scheduled job, so nothing it derives can go stale because a cron failed. This
job derives nothing and flips nothing — a licence's standing is still read off
its date on every view — it only sends a notice, which is this module's work.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today
NOTICE_EXPIRING = "Expiring"
NOTICE_EXPIRED = "Expired"
_NOTICE_RANK = {"": 0, NOTICE_EXPIRING: 1, NOTICE_EXPIRED: 2}
ROSTER_LINK = "/admin/registry/surge"


def notify_expiring(as_of=None) -> dict:
	"""Tell each branch's County Coordinator about licences running out. Daily.

	Two notices per licence, in the app only: one when it comes within
	`surge.EXPIRING_WITHIN_DAYS` (the moment the roster starts showing "expires
	soon"), and one on the day it expires. A day the scheduler missed is caught
	up the next day, and a licence first recorded already inside the window gets
	the first notice straight away.

	**Idempotent without remembering days.** Each entry carries which notice it
	was last sent and for which expiry date. Running twice sends nothing twice,
	and recording a renewed licence changes the date, which is all it takes for
	the notices to start again.

	**Who is told.** The holders of the society's volunteer role (County
	Coordinator in Kenya) at exactly the volunteer's serving branch. A branch
	with nobody in that role is told nothing; that gap is visible on the
	roster itself and fixed in Geo Assignment.
	"""
	from vmmsx.approvals.services import routing
	from vmmsx.notifications.services import direct
	from vmmsx.volunteer.services import identity, society, surge

	moment = getdate(as_of or today())
	horizon = add_days(moment, surge.EXPIRING_WITHIN_DAYS)
	role = frappe.db.get_single_value("National Society Settings", society.SCOPE_ROLE_FIELD)
	summary = {"checked": 0, "notified": 0, "nobody_to_tell": 0}

	entries = frappe.get_all(
		surge.ENTRY_DOCTYPE,
		filters={"status": surge.STATUS_ACTIVE, "licence_expiry": ("<=", horizon)},
		fields=["name", "volunteer", "profession", "licence_expiry", "expiry_notice", "expiry_notice_for"],
	)

	for entry in entries:
		summary["checked"] += 1
		expiry = getdate(entry.licence_expiry)
		due = NOTICE_EXPIRED if expiry <= moment else NOTICE_EXPIRING
		same_licence = entry.expiry_notice_for and getdate(entry.expiry_notice_for) == expiry
		already = (entry.expiry_notice or "") if same_licence else ""

		if _NOTICE_RANK[already] >= _NOTICE_RANK[due]:
			continue

		volunteer = frappe.get_doc("VMMS Volunteer", entry.volunteer)
		if (volunteer.status or "") != "Active":
			continue

		people = routing.holders_exactly_at(volunteer.get("home_geo_node"), role) if role else []
		if not people:
			# Not recorded: whoever is appointed to the branch next is told on
			# the next run.
			summary["nobody_to_tell"] += 1
			continue

		direct.tell(
			people,
			_expiry_subject(identity.display_name(volunteer), entry.profession, expiry, moment),
			surge.ENTRY_DOCTYPE,
			entry.name,
			link=ROSTER_LINK,
		)
		summary["notified"] += 1

		frappe.db.set_value(
			surge.ENTRY_DOCTYPE,
			entry.name,
			{"expiry_notice": due, "expiry_notice_for": expiry},
			update_modified=False,
		)

	return summary


def _expiry_subject(person: str, profession: str, expiry, moment) -> str:
	when = frappe.utils.format_date(expiry)

	if expiry < moment:
		return _("{0}'s {1} licence expired on {2}. Ask for the renewed licence.").format(person, profession, when)

	if expiry == moment:
		return _("{0}'s {1} licence expires today. Ask for the renewed licence.").format(person, profession)

	return _("{0}'s {1} licence expires on {2}. Ask for the renewed licence.").format(person, profession, when)
