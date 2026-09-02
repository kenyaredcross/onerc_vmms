# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One person's notifications, from both places they come from.

A volunteer opening the Notifications tab expects to find two different kinds of
thing there, and they do not care that the two are stored differently:

1. **What their branch or the national society sent them** — an alert, an
   advisory, news. Those are `VMMS Announcement` fanned out into `VMMS
   Notification`, and they are the reason this module exists.
2. **What the system told them** — their volunteer application was approved,
   a membership needs renewing, something was assigned to them. Frappe already
   writes those to `Notification Log`, the approval engine's assignments among
   them, and building a second copy of that would mean the same event arriving
   twice or, worse, arriving in the tab nobody thought to look at.

So the feed is a merge, and the merge is dispatched rather than branched.
`_SOURCES` below holds one entry per source, each knowing how to read a page of
its own rows, how to turn one into the shared DTO, and how to mark one read. A
third source later is a third entry; no reader, no counter and no endpoint gains
a comparison.

**The source name is code-owned and opaque to the frontend.** A notification's
`id` is meaningless without the `source` beside it, and the two travel together
so `mark_read` can dispatch on the pair. The frontend passes back what it was
given and never constructs either.

**Reading somebody else's notification is not possible, rather than not
allowed.** Every query here is filtered on `frappe.session.user` and no function
in this module takes a user argument. That is the same shape as the possessive
endpoints in `api/member.py` and `api/volunteer.py`: a caller who cannot name a
person cannot get the check wrong.
"""

from collections.abc import Callable

import frappe
from frappe import _
from frappe.utils import now_datetime

NOTIFICATION_DOCTYPE = "VMMS Notification"
ANNOUNCEMENT_DOCTYPE = "VMMS Announcement"
LOG_DOCTYPE = "Notification Log"

SOURCE_ANNOUNCEMENT = "announcement"
SOURCE_SYSTEM = "system"

# A feed is a feed. Somebody who has not signed in for a year does not need
# their whole history in one response, and the screen offers no pagination
# because a notification older than the last few dozen is not a notification any
# more, it is a record.
PAGE = 50


# --------------------------------------------------------------------- write

def ensure(announcement: str, user: str) -> bool:
	"""One copy of this announcement for this person. Returns True if it wrote.

	The whole of the fan-out's idempotence, and the reason it is a lookup and
	not an insert-and-catch: a duplicate here is not an error to recover from,
	it is the ordinary state of a publish being retried, and the answer should
	be cheap rather than exceptional.
	"""
	if frappe.db.exists(
		NOTIFICATION_DOCTYPE, {"announcement": announcement, "recipient": user}
	):
		return False

	frappe.get_doc(
		{
			"doctype": NOTIFICATION_DOCTYPE,
			"announcement": announcement,
			"recipient": user,
			"delivered_on": now_datetime(),
			"is_read": 0,
		}
		# The system is delivering a message somebody with publish permission
		# already wrote and sent. The recipient has no permission to create their
		# own copy and must not need one, and the publisher is not acting on the
		# recipient's behalf. Who may broadcast at all was decided by the
		# ordinary permission check on VMMS Announcement before the fan-out ran.
	).insert(ignore_permissions=True)

	return True


def count_for(announcement: str) -> int:
	"""How many people hold a copy. Read back rather than counted up, so a
	resumed fan-out reports the true total instead of what this call wrote."""
	return frappe.db.count(NOTIFICATION_DOCTYPE, {"announcement": announcement})


# ---------------------------------------------------------------- the sources

def _announcement_rows(limit: int) -> list[dict]:
	"""This person's copies, with the announcement's wording read through the
	link rather than from a copy taken when it was sent."""
	rows = frappe.get_all(
		NOTIFICATION_DOCTYPE,
		filters={"recipient": frappe.session.user},
		fields=["name", "announcement", "is_read", "delivered_on"],
		order_by="delivered_on desc",
		limit_page_length=limit,
		# A person reading their own notifications. The filter is the session
		# user and no argument names anybody, so this cannot read another
		# person's list; requiring read permission on VMMS Notification would
		# mean granting every volunteer a role to see what was sent to them.
		ignore_permissions=True,
	)

	if not rows:
		return []

	announcements = {
		row.name: row
		for row in frappe.get_all(
			ANNOUNCEMENT_DOCTYPE,
			filters={"name": ["in", sorted({row.announcement for row in rows})]},
			fields=[
				"name",
				"title",
				"summary",
				"body",
				"urgency",
				"announcement_type",
				"geo_node",
				"status",
				"expires_on",
				"published_on",
				"link_label",
				"link_href",
			],
			ignore_permissions=True,  # Same argument as above.
		)
	}

	return [
		_as_announcement(row, announcements[row.announcement])
		for row in rows
		if row.announcement in announcements
	]


def _as_announcement(row: dict, announcement: dict) -> dict | None:
	"""One delivered announcement as the shared DTO, or None if it has expired.

	Built field by field, and filtered on `is_live` here rather than in the
	query, because expiry is a property of the announcement and the notification
	row knows nothing about it. Returning None is how a row drops out of the
	feed without being deleted: the record of having been told stays.
	"""
	from vmmsx.notifications.services import announce

	if not announce.is_live(announcement):
		return None

	return {
		"id": row.get("name"),
		"source": SOURCE_ANNOUNCEMENT,
		"title": announcement.get("title") or "",
		"summary": announcement.get("summary") or "",
		"body": announcement.get("body") or "",
		"urgency": announcement.get("urgency") or "",
		"rank": announce.rank(announcement.get("urgency")),
		"label": announcement.get("announcement_type") or "",
		"geo_node": announcement.get("geo_node") or "",
		"sent_on": str(announcement.get("published_on") or row.get("delivered_on") or ""),
		"read": bool(row.get("is_read")),
		"link_label": announcement.get("link_label") or "",
		"href": announcement.get("link_href") or "",
	}


def _system_rows(limit: int) -> list[dict]:
	"""What the framework told this person, including the approval engine's own
	assignments.

	`Notification Log` is already per-user and already filtered by `for_user`,
	so this adds the session filter and nothing else. The description is a Text
	Editor field written by whichever app raised it, so it is stripped to text
	before it goes anywhere near a page.
	"""
	rows = frappe.get_all(
		LOG_DOCTYPE,
		filters={"for_user": frappe.session.user},
		fields=["name", "subject", "type", "document_type", "document_name", "link", "read", "creation"],
		order_by="creation desc",
		limit_page_length=limit,
		# The framework's own list controllers read this doctype the same way,
		# for the same reason: a notification log entry belongs to the person it
		# names, and `for_user` is the session user here.
		ignore_permissions=True,
	)

	held = _still_held(rows)

	return [_as_system(row, held) for row in rows]


def _as_system(row: dict, held: set[tuple[str, str]] | None = None) -> dict | None:
	"""One framework notification as the shared DTO.

	Ranked at zero: the urgency vocabulary belongs to announcements, and
	inventing an urgency for a framework notification would be this app claiming
	to know how important another app's message is.
	"""
	return {
		"id": row.get("name"),
		"source": SOURCE_SYSTEM,
		"title": _title(row, held or set()),
		"summary": "",
		"body": "",
		"urgency": "",
		"rank": 0,
		"label": row.get("type") or "",
		"geo_node": "",
		"sent_on": str(row.get("creation") or ""),
		"read": bool(row.get("read")),
		"link_label": "",
		"href": row.get("link") or "",
	}


def _mark_announcement(name: str) -> bool:
	"""Mark one of this person's own copies read. Idempotent.

	The recipient filter is in the lookup, not checked afterwards: a name that
	belongs to somebody else simply does not match, and the caller is told the
	same thing they would be told about a name that does not exist.
	"""
	row = frappe.db.get_value(
		NOTIFICATION_DOCTYPE,
		{"name": name, "recipient": frappe.session.user},
		["name", "is_read"],
		as_dict=True,
	)

	if not row:
		return False

	if not row.is_read:
		frappe.db.set_value(
			NOTIFICATION_DOCTYPE,
			row.name,
			{"is_read": 1, "read_on": now_datetime()},
			update_modified=False,
		)

	return True


def _mark_system(name: str) -> bool:
	"""The same, for a framework notification."""
	row = frappe.db.get_value(
		LOG_DOCTYPE, {"name": name, "for_user": frappe.session.user}, ["name", "read"], as_dict=True
	)

	if not row:
		return False

	if not row.read:
		frappe.db.set_value(LOG_DOCTYPE, row.name, "read", 1, update_modified=False)

	return True


def _unread_announcements() -> int:
	return frappe.db.count(
		NOTIFICATION_DOCTYPE, {"recipient": frappe.session.user, "is_read": 0}
	)


def _unread_system() -> int:
	return frappe.db.count(LOG_DOCTYPE, {"for_user": frappe.session.user, "read": 0})


# The dispatch table. One entry per source; adding a third place notifications
# come from is adding a fourth key here and touching nothing else.
_SOURCES: dict[str, dict[str, Callable]] = {
	SOURCE_ANNOUNCEMENT: {
		"read_page": _announcement_rows,
		"mark_read": _mark_announcement,
		"unread": _unread_announcements,
	},
	SOURCE_SYSTEM: {
		"read_page": _system_rows,
		"mark_read": _mark_system,
		"unread": _unread_system,
	},
}


# ---------------------------------------------------------------- the readers

def feed(limit: int = PAGE) -> list[dict]:
	"""Everything addressed to the signed-in person, most pressing first.

	Sorted on urgency and then on time, so an urgent advisory sent on Monday
	stays above Thursday's routine news until it has been read, which is the
	whole behavioural difference the urgency field buys. Unread before read
	within the same rank, because a list where the thing you have already dealt
	with sits at the top is a list people stop opening.

	Each source is asked for a full page and the merged result is trimmed, which
	is deliberately simple: it costs one extra page of rows and it means a burst
	of framework notifications cannot push a branch's advisory out of the feed
	entirely.
	"""
	rows: list[dict] = []

	for source in _SOURCES.values():
		rows.extend(row for row in source["read_page"](limit) if row)

	rows.sort(key=lambda row: (not row["read"], row["rank"], row["sent_on"]), reverse=True)

	return rows[:limit]


def unread() -> int:
	"""The badge on the sidebar. Counted, never derived from `feed()`, so the
	number is right even when it is larger than one page."""
	return sum(source["unread"]() for source in _SOURCES.values())


def mark_read(source: str, name: str) -> bool:
	"""Mark one notification read, dispatching on where it came from.

	An unknown source is False rather than an exception: the pair comes back
	from a client, and a client sending nonsense should be told nothing
	happened, not handed a traceback.
	"""
	handler = _SOURCES.get(source)

	return bool(handler and handler["mark_read"](name))


def mark_all_read() -> int:
	"""Everything currently in the feed. Returns how many changed.

	Deliberately scoped to the feed rather than to the tables: "mark all read"
	means the list in front of somebody, and silently marking an expired
	announcement read would be answering a question nobody asked.
	"""
	changed = 0

	for row in feed():
		if not row["read"] and mark_read(row["source"], row["id"]):
			changed += 1

	return changed


def _plain(value: str | None) -> str:
	"""Strip markup from another app's field before it reaches a page.

	`Notification Log.subject` is written by whichever app raised the
	notification and this one does not control what goes in it. Stripping here
	rather than trusting the frontend keeps the guarantee on the server, which
	is where the content module already puts it for the same reason.
	"""
	if not value:
		return ""

	return frappe.utils.strip_html(value).strip()


# ------------------------------------------------------- saying it in English

# What each thing a person can be handed is *called* when it lands in their
# queue. The framework's own sentence for an assignment is written for a desk
# user looking at a document register — "Administrator assigned a new task VMMS
# Volunteer Application VAPP-00017 to you" — and every part of it is wrong for
# the audience this product has: the person who did the assigning is usually the
# engine rather than a colleague, "task" is this app's word for something else
# entirely, and a naming series is not a thing anybody recognises.
#
# So the feed says what arrived instead of who moved it. The doctype is the only
# input, which is why this is a table and not a branch: a doctype absent from it
# falls back to its own label with the product prefix taken off, so a new
# reviewable record reads sensibly on the day it is added and gets its own
# wording when somebody has a better word for it.
_QUEUE_NOUNS = {
	"VMMS Volunteer Application": "volunteer application",
	"VMMS Membership": "membership application",
	"VMMS Deployment Request": "deployment request",
	"VMMS Branch Transfer": "branch transfer request",
	"VMMS Stipend Payment Form": "stipend payment form",
	"VMMS Stipend Progress Report": "stipend progress report",
	"VMMS Task": "task",
	"VMMS Deployment": "deployment",
	"Job Applicant": "job application",
}

# The framework's word for the notification an assignment raises, on both the
# handing over and the taking back.
ASSIGNMENT = "Assignment"


def _noun(doctype: str | None) -> str:
	"""What to call this kind of record in a sentence.

	The fallback is the doctype's own label with the product prefix removed and
	lowercased, so `VMMS Deployment Update` reads as "deployment update" without
	anybody having to add a row above. `get_meta` rather than the raw name, so a
	society that renamed a doctype's label gets its own word.
	"""
	if not doctype:
		return "record"

	if doctype in _QUEUE_NOUNS:
		return _QUEUE_NOUNS[doctype]

	try:
		label = frappe.get_meta(doctype).get_label() or doctype
	except Exception:
		label = doctype

	return label.removeprefix("VMMS ").strip().lower() or "record"


def _still_held(rows: list[dict]) -> set[tuple[str, str]]:
	"""Which of these assignments the reader still has open, in one query.

	The framework raises the same notification `type` whether a document was
	handed to somebody or taken back off them, and the only difference is in the
	English of the subject — which is translated, and so is not something to
	pattern-match on. What is *not* translated is whether the reader still holds
	an open ToDo for that document, and that is the same fact the two sentences
	were reporting.

	One query for the whole page rather than one per row: a feed is fifty rows
	and fifty round trips to answer a question about wording would be a page
	load spent on a caption.
	"""
	wanted = {
		(row.get("document_type"), row.get("document_name"))
		for row in rows
		if row.get("type") == ASSIGNMENT and row.get("document_type") and row.get("document_name")
	}

	if not wanted:
		return set()

	open_rows = frappe.get_all(
		"ToDo",
		filters={
			"allocated_to": frappe.session.user,
			"status": ("in", ("Open", "Overdue")),
			"reference_type": ("in", sorted({doctype for doctype, _name in wanted})),
			"reference_name": ("in", sorted({name for _doctype, name in wanted})),
		},
		fields=["reference_type", "reference_name"],
		# The reader's own queue, filtered on the session user. The same
		# argument every other read in this module makes: no caller names a
		# person, so there is nobody else's list to reach.
		ignore_permissions=True,
	)

	return {(row.reference_type, row.reference_name) for row in open_rows} & wanted


def _title(row: dict, held: set[tuple[str, str]]) -> str:
	"""The one line this notification shows in the list.

	Only assignments are rewritten. Everything else in `Notification Log` was
	written by whichever app raised it — a mention, a share, an alert a society
	configured itself — and putting this app's words over somebody else's
	message would be worse than the sentence it replaced.
	"""
	if row.get("type") != ASSIGNMENT:
		return _plain(row.get("subject"))

	noun = _noun(row.get("document_type"))
	reference = (row.get("document_type"), row.get("document_name"))

	if reference in held:
		# "A new" rather than the reference, deliberately. The docname is on the
		# record this row links to, and a person reading a list wants to know
		# what turned up, not to memorise a series.
		return _("A new {0} has been added to your queue.").format(noun)

	return _("A {0} has been taken off your queue.").format(noun)
