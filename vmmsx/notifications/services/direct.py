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

**In-app only for the person themselves, and the omission is deliberate.**
`announce.py` offers `also_email` because a broadcast is addressed to a branch's
whole roll, including people enrolled at a desk who have never signed in and are
reachable no other way. The events here are the opposite: every one of them is
about a record the person holds in this system, so they have a login by
construction, and whether a framework notification also arrives by mail is
already each user's own setting rather than something this app should decide for
them.

**A young volunteer's guardian is the exception, and it has to be.** They hold no
login, so a `Notification Log` row would reach nobody — the whole mechanism this
module is built on is unavailable for exactly the person a society has undertaken
to keep informed. So `about` names the volunteer an event concerns, and where
that person is a child today, their guardians are emailed a copy. Two properties
worth stating, because both are load-bearing:

1. **It does not depend on the volunteer having a login.** The callers that guard
   on `login_of(...)` and return early would otherwise drop the guardian along
   with the notification, and somebody enrolled at a branch from a paper form is
   precisely the case where a parent is the only person reachable at all.
2. **It is asked at send time, every time.** `guardian.emails_for_volunteer`
   answers for who is a child *today*. A society does not go on writing to
   somebody's parents after their eighteenth birthday.

The message is written to stand on its own rather than to link into the portal: a
guardian has nothing to sign in to, and a notification whose only content is a
link nobody can open is worse than no notification.
"""

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.utils import escape_html

# Frappe's own vocabulary for a `Notification Log` row, not a society's and not
# this app's. "Alert" is what `sla.py` raises an overdue approval as, and these
# are the same kind of thing: something happened to a record you hold.
ALERT = "Alert"


def tell(
	users: list[str], subject: str, doctype: str, name: str, about: str | None = None
) -> list[str]:
	"""Raise one notification per user, pointing at the record it is about.

	Returns the **logins** notified, unchanged by any of this: callers collect
	that list and report it as who was told in the app, and folding email
	addresses into it would make one list mean two things. An empty list is a
	real answer and not an error: an invitation to a volunteer with no login has
	nobody to notify, and refusing the invitation over it would make a login a
	precondition for being deployed.

	`about` names the **volunteer this event concerns**, where there is one, and
	is what puts a young volunteer's guardian in the loop. It is separate from
	`users` because they are different questions: `users` is who has a screen to
	show this on, and `about` is whose life it is. A message to a coordinator
	about somebody else's assignment passes no `about`, and rightly copies nobody.

	Queued rather than written inline, the same as `sla._notify`, because a
	notification is not the act the caller was asked to perform and an SMTP or
	websocket hiccup must not roll back the transition that caused it.
	"""
	recipients = sorted({user for user in users or [] if user})

	# Before the early return, deliberately. A volunteer with no login has no
	# in-app notification to raise and may still have a parent who must be told.
	_copy_guardians(about, subject)

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


def _copy_guardians(volunteer: str | None, subject: str) -> list[str]:
	"""Email a young volunteer's guardians a copy of what they were told.

	Returns the addresses written to — not for `tell`'s own return value, which
	stays a list of logins, but so a test can assert on it and a caller that
	wants to report it can ask directly.

	**Never raises.** The event that caused this — an assignment, a task, a change
	of plan — is the thing that matters, and a mail server having a bad afternoon
	must not roll it back. Same trade, and the same reasoning, as
	`lifecycle.notify`'s.
	"""
	if not volunteer:
		return []

	try:
		from vmmsx.registration.services import guardian

		addresses = guardian.emails_for_volunteer(volunteer)

		if not addresses:
			return []

		frappe.sendmail(
			recipients=addresses,
			subject=subject,
			message=_guardian_body(volunteer, subject),
			# Queued, like everything else this app sends.
			now=False,
		)

		return addresses
	except Exception:
		frappe.log_error(
			title="vmmsx: could not copy a guardian",
			message=frappe.get_traceback(),
		)

		return []


def _guardian_body(volunteer: str, subject: str) -> str:
	"""What a guardian reads: the event, whose it is, and why they have it.

	Deliberately short and deliberately free of links. The recipient has no
	account here, so a "view it in the portal" button would be an instruction they
	cannot follow; if they want to know more, the branch that wrote to them is who
	they will ask, and that is the right conversation.
	"""
	from vmmsx.registration.services import guardian

	red_profile = guardian.profile_of_volunteer(volunteer)
	person = (red_profile and frappe.db.get_value("Red Profile", red_profile, "full_name")) or _(
		"the young person you are the guardian of"
	)

	return "<p>{0}</p><p>{1}</p><p>{2}</p>".format(
		escape_html(subject),
		_("This message is about {0}.").format(frappe.bold(escape_html(person))),
		_(
			"You are receiving a copy because you are recorded as their parent or guardian."
			" If anything here is unexpected, please contact the branch."
		),
	)


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
