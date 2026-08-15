# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The notification endpoints. Possessive, every one of them.

**None of them takes a person.** `my_notifications`, `unread_count` and
`mark_all_read` take no arguments at all, and `mark_read` takes a source and a
name that must already belong to the caller. That is the same shape as
`my_memberships`, `my_volunteer` and `approvals.my_queue`, and the reason is the
one `CLAUDE.md` gives: a caller who cannot name anybody cannot get a check
wrong. There is no admin variant of these — a coordinator wanting to know what
was sent reads the announcement, which is a scoped doctype and answers that
question with core's own enforcement.

Everything is dispatched by `notifications/services/delivery.py`, which merges
the two places notifications come from — the branch's own announcements, and
Frappe's `Notification Log` where the approval engine's assignments already
land. The merge is there rather than here so the endpoints stay four lines each
and the sources stay a dispatch table.

**Sending is not here.** An announcement is written and published on the desk,
where the geo scope role decides who may write one and from where. Whitelisting
a broadcast endpoint would put a second answer in front of that check, on the
one action in this app whose blast radius is every volunteer in the country.
"""

import frappe

from vmmsx.notifications.services import delivery


@frappe.whitelist()
def my_notifications(limit: int = 50) -> dict:
	"""Everything addressed to the signed-in person, most pressing first.

	`unread` travels with the rows so the sidebar badge and the list cannot
	disagree with each other, and it is counted rather than derived from the
	page — a person with sixty unread notifications should see sixty, not the
	fifty that fitted.
	"""
	return {
		"notifications": delivery.feed(limit=limit),
		"unread": delivery.unread(),
	}


@frappe.whitelist()
def unread_count() -> dict:
	"""Just the badge, for the chrome to poll without fetching the whole feed."""
	return {"unread": delivery.unread()}


@frappe.whitelist()
def mark_read(source: str, name: str) -> dict:
	"""Mark one notification read. Idempotent, and only ever one of your own.

	`source` says which of the merged sources the notification came from; the
	frontend passes back the pair it was given and constructs neither. A pair
	that names somebody else's notification, or nothing at all, reports
	`changed: false` rather than raising — the two are indistinguishable to a
	caller on purpose, so this cannot be used to find out whether a given
	notification exists.
	"""
	return {
		"changed": delivery.mark_read(source, name),
		"unread": delivery.unread(),
	}


@frappe.whitelist()
def mark_all_read() -> dict:
	"""Mark everything currently in the feed read. Returns how many changed."""
	return {
		"changed": delivery.mark_all_read(),
		"unread": delivery.unread(),
	}
