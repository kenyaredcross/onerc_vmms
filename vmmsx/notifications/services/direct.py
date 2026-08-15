# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Telling one named person that one thing happened to them.

An announcement is a broadcast: somebody speaks for a branch and everybody
beneath it gets a copy. That is `announce.py`, and it is the wrong shape for
"your task was assigned" or "you have been invited to a deployment", which are
addressed to one person because one person is the only one they concern.

**This is not a third source in the feed.** `delivery._SOURCES` merges the
branch's announcements with Frappe's own `Notification Log`, where the approval
engine's assignments already land, and everything written here lands in the
second of those. So a task assignment appears in a volunteer's Notifications tab
without `delivery.py` gaining an entry, `unread()` gaining a term, or the DTO
gaining a field. The rule that a third source is a third entry is intact; this
is not a third source.

**Idempotence is the caller's, and it is real rather than delegated.** A
`Notification Log` row carries no natural key, so there is nothing here to check
before writing and no honest way to make `tell()` itself idempotent. What makes
the double-send impossible is that every caller is a state transition that has
already returned early: `task.accept()` on an accepted task, or
`invitation.respond()` on an answered invitation, both observe the work is done
and never reach this module. Notification follows the transition, so it happens
exactly as often as the transition does.

**In-app only, and the omission is deliberate.** `announce.py` offers `also_email`
because a broadcast is addressed to a branch's whole roll, including people
enrolled at a desk who have never signed in and are reachable no other way. The
events here are the opposite: every one of them is about a record the person
holds in this system, so they have a login by construction, and whether a
framework notification also arrives by mail is already each user's own setting
rather than something this app should decide for them.
"""

import frappe
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

# Frappe's own vocabulary for a `Notification Log` row, not a society's and not
# this app's. "Alert" is what `sla.py` raises an overdue approval as, and these
# are the same kind of thing: something happened to a record you hold.
ALERT = "Alert"


def tell(users: list[str], subject: str, doctype: str, name: str) -> list[str]:
	"""Raise one notification per user, pointing at the record it is about.

	Returns whoever was told, so a caller can report it rather than assume it.
	An empty list of users is a real answer and not an error: an invitation to a
	volunteer with no login has nobody to notify, and refusing the invitation
	over it would make a login a precondition for being deployed.

	Queued rather than written inline, the same as `sla._notify`, because a
	notification is not the act the caller was asked to perform and an SMTP or
	websocket hiccup must not roll back the transition that caused it.
	"""
	recipients = sorted({user for user in users or [] if user})

	if not recipients:
		return []

	enqueue_create_notification(
		recipients,
		{
			"type": ALERT,
			"document_type": doctype,
			"document_name": name,
			"subject": subject,
			"from_user": frappe.session.user,
		},
	)

	return recipients


def login_of(volunteer: str | None) -> str | None:
	"""The login behind a volunteer record, or None if there is not one.

	Two hops, both through core: a volunteer names a Red Profile, and core makes
	`Red Profile.user` unique. There is no third way to get from a person to a
	login in this app, and this is the only place the walk is written for
	notification purposes, so a caller cannot accidentally reach for an email
	field on a satellite that deliberately holds none.

	None for a volunteer enrolled at a desk who has never signed in. That is
	ordinary, not exceptional: `tell()` treats it as nobody to notify.
	"""
	if not volunteer:
		return None

	red_profile = frappe.db.get_value("VMMS Volunteer", volunteer, "red_profile")

	if not red_profile:
		return None

	return frappe.db.get_value("Red Profile", red_profile, "user") or None
