# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Publishing an announcement, and the fan-out that follows.

**Idempotent, like every service in this app.** `publish()` may be called twice
and the second call observes that the work is done and returns the same answer.
That is not a nicety here: a fan-out to a national society is a long write, and
the realistic ways it gets called twice are a retried background job and
somebody pressing a button again because the first press appeared to do nothing.
Delivering an urgent advisory to fifty thousand people twice is a visible,
embarrassing failure, so the guarantee is structural rather than remembered.

The structure that provides it is `delivery.ensure()`: one notification per
(announcement, recipient) pair, checked before writing. The check is what makes
a *partial* fan-out safe to resume too, which matters more than the double-press
case: if a publish dies halfway through, running it again finishes it rather
than starting a second copy alongside the first.

**Urgency dispatches; type does not.** `_URGENCY` below is the one table keyed by
the closed Select, and it decides two things: whether email is offered by default
and how the notification is ranked in a reader's list. `announcement_type` is a
society's own vocabulary and is never read by this file at all.

**Email is a separate channel with separate reach.** The in-app copy needs a
login; the email needs an address. Those are different sets of people, and the
difference is the point: a member enrolled at a desk who has never signed in is
reachable only by email, and a volunteer who signed up online may have a login
and a bad address. So the two are resolved independently from the same set of
Red Profiles and neither is derived from the other.

**Publishing is one-way.** There is no unpublish. Copies already in people's
lists have been read, and a field that pretended to recall them would leave rows
nothing owned. An announcement sent in error is corrected by editing it, which
corrects it everywhere at once because the wording lives on the announcement and
was never copied onto the notifications.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, today

from vmmsx.notifications.services import audience, delivery

ANNOUNCEMENT_DOCTYPE = "VMMS Announcement"

STATUS_DRAFT = "Draft"
STATUS_PUBLISHED = "Published"

URGENCY_ROUTINE = "routine"
URGENCY_IMPORTANT = "important"
URGENCY_URGENT = "urgent"

# The dispatch table for the one field that changes behaviour.
#
# `email_by_default` is a default offered on the form, not a rule enforced here:
# whoever writes the announcement decides, and `also_email` is what this module
# actually reads. `rank` is what orders a reader's list, so an urgent advisory
# stays above a fortnight of routine news rather than sinking under it.
_URGENCY: dict[str, dict] = {
	URGENCY_ROUTINE: {"email_by_default": False, "rank": 0},
	URGENCY_IMPORTANT: {"email_by_default": True, "rank": 1},
	URGENCY_URGENT: {"email_by_default": True, "rank": 2},
}


def rank(urgency: str | None) -> int:
	"""How high this sits in a reader's list. Unknown urgency ranks lowest."""
	return _URGENCY.get(urgency or "", {}).get("rank", 0)


def emails_by_default(urgency: str | None) -> bool:
	"""Whether the email box should start ticked for this urgency."""
	return bool(_URGENCY.get(urgency or "", {}).get("email_by_default", False))


def is_live(announcement: dict) -> bool:
	"""Published, and not past its expiry.

	Expiry is a display rule and nothing else: the notification rows survive, so
	a society can still answer who was told what. This is the predicate that
	keeps a fortnight-old weather advisory out of somebody's list.
	"""
	if announcement.get("status") != STATUS_PUBLISHED:
		return False

	expires = announcement.get("expires_on")

	return not expires or str(expires) >= today()


def publish(doc) -> dict:
	"""Fan an announcement out to everybody it is addressed to. Idempotent.

	Takes a document rather than a name, the same as every other service in this
	app, so a caller that already loaded it does not load it again and a caller
	that has one in hand cannot pass a stale name.

	Returns what happened, which is worth having: `delivered` is how many people
	now hold a copy, and `created` is how many of those this call wrote. A second
	call reports the same `delivered` and a `created` of zero, which is the
	visible form of the idempotence guarantee.
	"""
	if doc.status != STATUS_PUBLISHED:
		frappe.throw(_("Set the announcement to Published before sending it."))

	if not doc.geo_node:
		# ACC-02 at the boundary. The field is mandatory on the doctype, so this
		# is the second line of defence rather than the first, and it is here
		# because a fan-out with no anchor would resolve the whole society.
		frappe.throw(_("An announcement must say which part of the society it comes from."))

	addressed = audience.profiles(doc.geo_node, doc.audience)
	reachable = audience.logins(addressed)

	created = 0

	for user in sorted(set(reachable.values())):
		if delivery.ensure(doc.name, user):
			created += 1

	delivered = delivery.count_for(doc.name)

	# `db_set` rather than a save: the fan-out must not re-enter the controller's
	# validate and re-run itself. Both fields are read-only on the form, so this
	# is the only thing that writes them.
	doc.db_set("delivered_count", delivered, update_modified=False)

	if not doc.published_on:
		doc.db_set("published_on", now_datetime(), update_modified=False)

	if doc.also_email:
		_email(doc, audience.emails(addressed))

	return {
		"announcement": doc.name,
		"addressed": len(addressed),
		"delivered": delivered,
		"created": created,
	}


def _email(doc, addresses: list[str]) -> None:
	"""The optional second channel.

	Queued rather than sent inline, because a national announcement is thousands
	of messages and a publish that blocks on an SMTP conversation per recipient
	is a publish that times out. `bcc` rather than `recipients`, so a society's
	whole membership list is not printed at the top of everybody's copy.

	The body is the announcement's plain text, and it stays plain: the same
	argument the doctype's own description makes. Somebody who may broadcast may
	broadcast, and that is not the same permission as running markup in a
	reader's mail client.
	"""
	if not addresses:
		return

	frappe.sendmail(
		recipients=[],
		bcc=addresses,
		subject=doc.title,
		content=frappe.utils.escape_html(doc.body or ""),
		# The bordered layout, which is what puts the society's lockup on a card
		# rather than loose above the text. The mark itself comes from
		# `notifications/services/branding.py` through this app's override of
		# Frappe's email template, so it is on every message the site sends and
		# not only this one — but an announcement is the one a member actually
		# looks at, so it gets the framed version.
		with_container=True,
		# The announcement, so a bounce or a complaint leads back to the record
		# that caused it rather than to nothing.
		reference_doctype=ANNOUNCEMENT_DOCTYPE,
		reference_name=doc.name,
		queue_separately=True,
	)
