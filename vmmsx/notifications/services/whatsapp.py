# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The WhatsApp seam — the only file in vmmsx that knows open-wa exists.

The console's Communication screen sends on four channels. The in-app copy and
the email are `VMMS Announcement`'s fan-out, which this app wrote. SMS is
`onerc_sms`'s, reached through `campaign.py`. This is the fourth, and it is a
seam in the same sense `volunteer/services/learning.py` is one: every name the
gateway owns is gathered in one block at the top, no other file in this app
names an open-wa route, and if the society moves to Meta's official API next
year this file is the diff.

**What is on the other side.** open-wa (`open-wa.org`) is a self-hosted gateway
the society runs itself — a container on their own infrastructure that holds a
WhatsApp Web session and exposes it over HTTP. It is not WhatsApp's own API and
it is not a vendor with an account: there is nothing to sign up for, and there
is no per-message bill. What there is instead is a phone number belonging to the
society, linked to that session, carrying the reputational and account risk of
everything sent through it. open-wa's own documentation is blunt about this —
*"there is always a non-zero risk of account restriction or ban"* — and every
design decision below is downstream of that sentence.

**Sending is queued, paced, and resumable. It is never synchronous.** The
console files a broadcast and returns; a background job walks the recipients one
at a time, sleeping between them, writing each outcome down as it goes. Three
different reasons, and all three are load-bearing:

1. *A request cannot hold a broadcast.* A branch of four thousand people at
   three seconds apart is three hours of sending. onerc_sms sends inline and one
   call per recipient, and a campaign to thousands times out; that is a known
   failure and there is no reason to reproduce it here.
2. *Pacing is the anti-ban measure.* Messages arriving in a burst from one
   number is the pattern that gets the number restricted. The delay and its
   jitter are settings, not constants, because the right value is a property of
   the society's number and its history rather than of this code.
3. *A half-sent broadcast must be finishable.* Every recipient is a row with its
   own status, and the job only picks up the ones still `Pending`. A worker that
   died at recipient nine hundred is restarted by submitting nothing and
   re-queueing: nobody is written to twice.

**One message at a time, deliberately, rather than the gateway's bulk route.**
open-wa offers `messages/send-bulk`, which takes the whole list and paces it
itself. It answers `202 Accepted` — the send is queued on the far side and the
per-recipient outcome never comes back. That is a better fit for a fire-and-
forget notifier and a worse one for this: a society that has just written to
four thousand volunteers should be able to see which of them it actually
reached, and a channel that cannot say is a channel whose numbers nobody should
trust. So the loop is ours, and every row is answered.

**The approver approves an upper bound.** Recipients are resolved and written
onto the broadcast when it is filed, for the reason `campaign.py` gives at
length: a query approved on Monday and dispatched on Friday reaches whoever
matches it on Friday, and the number of people a broadcast reaches is the thing
being approved. Opt-outs are then subtracted *again* at send time. That is not a
contradiction of the rule — subtraction can only shrink the list, never grow it,
so the figure the approver saw remains a ceiling, and somebody who asked to be
left alone on Thursday is left alone.

**Approval is the doctype's own submit permission.** No workflow, no second
engine. `VMMS WhatsApp Broadcast` is submittable, a draft is docstatus 0, and
submitting it is the act of approving it — which is exactly the shape onerc_sms
arrived at after its own workflow proved to be a state nothing could leave.
Announcements are deliberately *not* gated this way, because an advisory that
waits in a queue is not an advisory; a broadcast on the society's own WhatsApp
number is the opposite case, and the two differ in what a mistake costs.

**Everybody with a number is addressable, minus the people who said no.** There
is no separate consent field. What there is instead is `VMMS WhatsApp Opt Out`,
an inbound webhook that writes to it when somebody replies STOP, and a line
appended to every broadcast telling people how. A channel that can be left is
the difference between a notification and a nuisance.
"""

import random
import time

import frappe
from frappe import _
from frappe.utils import cint, now_datetime, today

from vmmsx.notifications.services import audience

# --- the boundary ---------------------------------------------------------
#
# Every route, header and vocabulary term open-wa owns is gathered here, so the
# surface this app depends on can be read at a glance and swapped in one place.
# Below this block the module speaks only vmmsx's own vocabulary.

#: Everything the gateway serves lives under this prefix. Documented as part of
#: the base URL rather than as a route, so a society that puts the gateway
#: behind a path on their own domain still configures one address.
API_PREFIX = "/api"

#: open-wa authenticates on a header and refuses a query parameter. Keys carry a
#: rank — viewer, operator, admin — and sending needs at least `operator`.
API_KEY_HEADER = "X-API-Key"

#: A WhatsApp chat is addressed as the number's digits with this suffix, with no
#: leading plus. `+255 712 345 678` becomes `255712345678@c.us`.
CHAT_SUFFIX = "@c.us"

SESSION_ROUTE = "/sessions/{session}"
SEND_TEXT_ROUTE = "/sessions/{session}/messages/send-text"
CHECK_CONTACT_ROUTE = "/sessions/{session}/contacts/check/{number}"

#: The one session state that can send. The gateway also reports `created`,
#: `initializing`, `qr_ready`, `authenticating`, `action_required`,
#: `disconnected` and `failed`; all of them mean the same thing to this app,
#: which is "not now", and the raw word is passed through to whoever is looking
#: at the settings page rather than being translated into a guess.
SESSION_READY = "ready"

#: How long to wait on the gateway. It is a container on the society's own
#: network, so a slow answer means it is unwell rather than far away.
TIMEOUT = 30

# --- this app's own vocabulary ---------------------------------------------

SETTINGS_DOCTYPE = "VMMS WhatsApp Settings"
BROADCAST_DOCTYPE = "VMMS WhatsApp Broadcast"
RECIPIENT_DOCTYPE = "VMMS WhatsApp Recipient"
OPT_OUT_DOCTYPE = "VMMS WhatsApp Opt Out"

STATUS_DRAFT = "Draft"
STATUS_SCHEDULED = "Scheduled"
STATUS_SENDING = "Sending"
STATUS_SENT = "Sent"
STATUS_PARTLY_SENT = "Partly Sent"
STATUS_FAILED = "Failed"
STATUS_CANCELLED = "Cancelled"

RECIPIENT_PENDING = "Pending"
RECIPIENT_SENT = "Sent"
RECIPIENT_FAILED = "Failed"
RECIPIENT_SKIPPED = "Skipped"

OPT_OUT_REPLY = "Reply"
OPT_OUT_STAFF = "Staff"

#: The same rule the SMS channel applies, for the same reason. A number written
#: down without a country code is ambiguous, and the way to resolve the ambiguity
#: is to ask the person rather than to assume the society's own country and
#: message a stranger who happens to hold that number somewhere else.
INTERNATIONAL_PREFIX = "+"

#: Long enough to be a real international number. A four-digit short code and a
#: half-typed field both fail this, and both should.
MINIMUM_DIGITS = 8


# ------------------------------------------------------------------ settings


def settings():
	"""The society's gateway configuration, as a document."""
	return frappe.get_cached_doc(SETTINGS_DOCTYPE)


def installed() -> bool:
	"""Is this channel present on the site at all?

	Asked by doctype, the same graceful-absence contract `campaign.installed()`
	keeps. It is always true on a migrated site and the check stays because the
	console asks the same question of all four channels and should not have to
	know which of them are conditional.
	"""
	return bool(frappe.db.exists("DocType", BROADCAST_DOCTYPE))


def configured() -> bool:
	"""Has somebody filled in enough for a message to have anywhere to go?

	The address, the key and the session, and the switch turned on. Deliberately
	not a call to the gateway: this is asked on every load of the Communication
	screen, and a screen that makes an HTTP request to another container before
	it can draw its channel list is a screen that hangs when that container is
	down.
	"""
	if not installed():
		return False

	config = settings()

	return bool(
		config.enabled
		and (config.gateway_url or "").strip()
		and (config.session_id or "").strip()
		and config.get_password("api_key", raise_exception=False)
	)


def available() -> bool:
	"""May this caller send on this channel — is it set up, and are they allowed?"""
	return configured() and bool(frappe.has_permission(BROADCAST_DOCTYPE, ptype="create"))


def session_state() -> dict:
	"""What the gateway says about the linked number, in words.

	Asked by the settings page and by nothing on the send path. Returns the
	gateway's own status word untranslated, alongside a sentence for somebody
	who is not going to look it up: `qr_ready` means a phone has to scan
	something, `disconnected` usually heals by itself, and `ready` is the only
	one that can send.
	"""
	if not configured():
		return {
			"connected": False,
			"status": "",
			"reason": _("This site has no WhatsApp gateway configured yet."),
		}

	ok, data, reason = _request("GET", SESSION_ROUTE)

	if not ok:
		return {"connected": False, "status": "", "reason": reason}

	status = (data or {}).get("status") or ""

	return {
		"connected": status == SESSION_READY,
		"status": status,
		"reason": "" if status == SESSION_READY else _session_reason(status),
	}


def _session_reason(status: str) -> str:
	"""What one of the gateway's session states means to somebody who has to fix it.

	A function rather than a module-level table, because every sentence in it goes
	through `_()` and translating at import time answers in whatever language the
	worker booted in rather than the one the reader is using.
	"""
	return {
		"created": _("The session exists but has not been started yet."),
		"initializing": _("The gateway is connecting. Give it a moment."),
		"qr_ready": _("Scan the code on the gateway's dashboard with the society's phone."),
		"authenticating": _("The code was scanned and the link is finishing."),
		"action_required": _("The gateway needs somebody to look at it before it can send."),
		"disconnected": _("The link dropped. It usually comes back on its own."),
		"failed": _("The link was refused. Stop the session and start it again."),
	}.get(status, "")


# ------------------------------------------------------------------- numbers


def chat_id(phone: str | None) -> str | None:
	"""One phone number as a WhatsApp address, or None if it is not one.

	The gateway wants digits and a suffix. Everything a human might type in
	between — spaces, dashes, brackets — is dropped, and the leading plus is
	dropped last because it is what proves the number was written with a country
	code in the first place.
	"""
	number = (phone or "").strip()

	if not number.startswith(INTERNATIONAL_PREFIX):
		return None

	digits = "".join(character for character in number if character.isdigit())

	if len(digits) < MINIMUM_DIGITS:
		return None

	return f"{digits}{CHAT_SUFFIX}"


def opted_out() -> set[str]:
	"""Every number that has asked not to be written to, as chat addresses.

	Returned as chat ids rather than as numbers so the comparison at send time
	is against the same string that would have been sent to, and a number
	recorded as `+255712345678` cannot fail to match one recorded as
	`255 712 345 678`.
	"""
	if not frappe.db.exists("DocType", OPT_OUT_DOCTYPE):
		return set()

	rows = frappe.get_all(OPT_OUT_DOCTYPE, pluck="phone_number", ignore_permissions=True)

	return {address for address in (chat_id(row) for row in rows) if address}


def record_opt_out(phone: str, source: str = OPT_OUT_REPLY, notes: str = "") -> bool:
	"""Write somebody down as not wanting these. Idempotent.

	Returns True if this call is what created the record. A second STOP from
	somebody who has already stopped is the ordinary state of a person pressing
	a button twice, not an error, and it answers False.
	"""
	address = chat_id(phone)

	if not address:
		return False

	number = _plain_number(address)

	if frappe.db.exists(OPT_OUT_DOCTYPE, {"phone_number": number}):
		return False

	frappe.get_doc(
		{
			"doctype": OPT_OUT_DOCTYPE,
			"phone_number": number,
			"opted_out_on": now_datetime(),
			"source": source,
			"notes": notes or "",
		}
		# Somebody asking to be left alone is not somebody who needs a login and
		# a role to be heard. The alternative is a request the system drops
		# because the person making it has no permission to make it.
	).insert(ignore_permissions=True)

	return True


def _plain_number(address: str) -> str:
	"""A chat address back as a number, for storing and for showing a person."""
	return INTERNATIONAL_PREFIX + address.removesuffix(CHAT_SUFFIX)


# --------------------------------------------------------------------- reach


def addresses(profiles: set[str]) -> list[str]:
	"""Chat addresses for these people, minus anybody who has opted out.

	Built from `audience.phones()` — the same list the SMS channel is built from,
	including a young volunteer's guardians and deduplicated the same way — so
	the two channels reach the same people out of one resolved audience and
	neither has its own idea of who has a number.
	"""
	if not profiles:
		return []

	stopped = opted_out()
	resolved = {
		address
		for address in (chat_id(number) for number in audience.phones(profiles))
		if address and address not in stopped
	}

	return sorted(resolved)


def reachable(geo_node: str, who: str) -> dict:
	"""How many of this audience can be written to on WhatsApp, and how many not.

	Both halves, for the reason `campaign.reachable` gives: a coordinator who can
	see that a third of their register has no usable number knows to go and
	collect them, and a screen reporting only the reachable figure hides exactly
	that. `opted_out` is reported separately from `unreachable` because they are
	different facts about a branch — one is missing data, the other is people
	who answered.
	"""
	addressed = audience.profiles(geo_node, who)
	stopped = opted_out()
	all_numbers = {
		address for address in (chat_id(number) for number in audience.phones(addressed)) if address
	}

	return {
		"addressed": len(addressed),
		"reachable": len(all_numbers - stopped),
		"unreachable": len(addressed) - len(all_numbers),
		"opted_out": len(all_numbers & stopped),
	}


# -------------------------------------------------------------------- filing


def draft(
	title: str,
	message: str,
	geo_node: str,
	who: str,
	scheduled_at=None,
) -> dict:
	"""File a broadcast to this audience, unsent. Returns what was filed.

	Nothing is dispatched here and nothing is dispatched by saving. The document
	is left at docstatus 0, which is what "draft" means in Frappe and what
	"waiting for approval" means in this channel, and submitting it — an act
	that needs submit permission on the doctype — is what releases it.

	`scheduled_at` is read at submission, not here: a broadcast approved after
	the moment it was scheduled for goes out on approval rather than being
	quietly dropped for having missed its slot.
	"""
	if not available():
		frappe.throw(
			_("WhatsApp is not available on this site."),
			frappe.PermissionError,
			title=_("No WhatsApp Channel"),
		)

	if not (message or "").strip():
		frappe.throw(_("A WhatsApp message needs something to say."), frappe.ValidationError)

	addressed = audience.profiles(geo_node, who)
	recipients = addresses(addressed)

	if not recipients:
		frappe.throw(
			_("Nobody in that audience can be reached on WhatsApp, so there is no broadcast to file."),
			frappe.ValidationError,
			title=_("No Recipients"),
		)

	broadcast = frappe.new_doc(BROADCAST_DOCTYPE)
	broadcast.title = title
	broadcast.message = message
	broadcast.geo_node = geo_node
	broadcast.audience = who
	broadcast.scheduled_at = scheduled_at or now_datetime()
	broadcast.status = STATUS_DRAFT
	broadcast.addressed = len(addressed)

	for address in recipients:
		broadcast.append(
			"recipients",
			{
				"phone": _plain_number(address),
				"chat_id": address,
				"delivery_status": RECIPIENT_PENDING,
			},
		)

	broadcast.total_recipients = len(recipients)
	# Inserted as the caller. Whether somebody may file a broadcast is a
	# permission question about them, and answering it here with elevated rights
	# would be this module deciding it on their behalf.
	broadcast.insert()

	return {
		"broadcast": broadcast.name,
		"recipients": len(recipients),
		"addressed": len(addressed),
		# Where to finish it. The desk, because approving is a submit and the
		# form is where a person can read the whole list before they do it.
		"url": f"/app/vmms-whatsapp-broadcast/{broadcast.name}",
	}


def release(broadcast: str) -> None:
	"""Queue an approved broadcast for sending.

	Called from the document's own `on_submit`. Queued on the long queue rather
	than run inline for the reason the module docstring gives at length: a
	branch of four thousand at three seconds apart is three hours of work, and
	nothing that takes three hours belongs in the request that asked for it.
	"""
	frappe.enqueue(
		"vmmsx.notifications.services.whatsapp.send",
		queue="long",
		timeout=_JOB_TIMEOUT,
		broadcast=broadcast,
		# After the commit, not before it. This is called from `on_submit`, inside
		# the transaction that is approving the broadcast; a worker that picked the
		# job up first would read docstatus 0, decide it had not been approved and
		# quietly send nothing to anybody.
		enqueue_after_commit=True,
		# One job per broadcast, so an approver pressing submit twice, or a
		# scheduled release landing on top of a manual one, does not put two
		# workers on the same list of people.
		job_id=f"vmmsx-whatsapp-{broadcast}",
		deduplicate=True,
	)


#: Long enough for a large branch at a slow pace, and finite so a wedged job is
#: eventually reaped rather than holding a worker for ever. A broadcast that runs
#: out of time stops with its sent rows recorded and is finished by re-queueing.
_JOB_TIMEOUT = 6 * 60 * 60


def send(broadcast: str) -> dict:
	"""Walk one broadcast's recipients and write to each of them. The job body.

	Resumable by construction: only rows still `Pending` are picked up, and each
	row is written down the moment it is answered rather than at the end. A
	worker killed at recipient nine hundred leaves nine hundred rows marked
	`Sent`, and re-queueing the same broadcast carries on from nine hundred and
	one.

	Never raises. A broadcast that could not be sent is a fact to be recorded on
	the broadcast — where the person who approved it will look — not a traceback
	in a worker log nobody is watching.
	"""
	doc = frappe.get_doc(BROADCAST_DOCTYPE, broadcast)

	if doc.docstatus != 1:
		# Somebody cancelled it between the approval and the worker picking it
		# up. That is a change of mind, and honouring it is the whole reason the
		# check is here rather than at the top of the loop only.
		return {"sent": 0, "failed": 0, "skipped": 0, "reason": "not approved"}

	state = session_state()

	if not state["connected"]:
		doc.db_set("status", STATUS_FAILED, update_modified=False)
		doc.add_comment("Comment", _("Not sent: {0}").format(state["reason"] or state["status"]))

		return {"sent": 0, "failed": 0, "skipped": 0, "reason": state["reason"]}

	doc.db_set("status", STATUS_SENDING, update_modified=False)

	config = settings()
	body = _compose(doc.message, config)
	pacing = max(cint(config.pacing_seconds), 0)
	jitter = bool(config.randomise_pacing)
	# Re-read here rather than trusted from filing time. See the module
	# docstring: the approved figure is a ceiling, and somebody who said no on
	# Thursday is not written to on Friday.
	stopped = opted_out()
	budget = _remaining_today(config)

	sent = failed = skipped = 0

	for row in doc.recipients:
		if row.delivery_status != RECIPIENT_PENDING:
			continue

		if row.chat_id in stopped:
			_mark(row, RECIPIENT_SKIPPED, error=_("Asked not to receive these."))
			skipped += 1
			continue

		if budget is not None and budget <= 0:
			# Stopped rather than failed. The rows are still `Pending`, so the
			# remainder goes out when the cap resets and the broadcast is
			# re-queued; marking them failed would lose people who were never
			# actually tried.
			break

		ok, data, reason = _request("POST", SEND_TEXT_ROUTE, {"chatId": row.chat_id, "text": body})

		if ok:
			_mark(row, RECIPIENT_SENT, message_id=(data or {}).get("messageId") or "")
			sent += 1

			if budget is not None:
				budget -= 1
		else:
			_mark(row, RECIPIENT_FAILED, error=reason)
			failed += 1

		if pacing:
			# Jittered, because a message every three seconds on the dot is a
			# machine and a message every two-to-four seconds is a person. This
			# is the anti-ban measure, and it is the reason this loop is not in
			# a hurry.
			time.sleep(random.uniform(pacing * 0.5, pacing * 1.5) if jitter else pacing)

	_finish(doc)

	return {"sent": sent, "failed": failed, "skipped": skipped, "reason": ""}


def _mark(row, status: str, message_id: str = "", error: str = "") -> None:
	"""Write one recipient's outcome down immediately.

	Straight to the column rather than through the parent's save: the parent is
	submitted, saving it again from a worker would fight the docstatus rules,
	and a row written at the end of a three-hour loop is a row that is lost when
	the loop does not reach the end.
	"""
	frappe.db.set_value(
		RECIPIENT_DOCTYPE,
		row.name,
		{
			"delivery_status": status,
			"message_id": message_id,
			"error": (error or "")[:140],
			"sent_on": now_datetime(),
		},
		update_modified=False,
	)
	# Committed per row on purpose. The job is long and the point of writing
	# each outcome down as it happens is that a worker that dies has still
	# recorded who it reached.
	frappe.db.commit()


def _finish(doc) -> None:
	"""Count what happened and say so on the broadcast.

	Counted from the rows rather than from the loop's own tally, so a broadcast
	resumed after a restart reports its true totals instead of what this run
	did.
	"""
	counts = _tally(doc.name)
	pending = counts.get(RECIPIENT_PENDING, 0)
	sent = counts.get(RECIPIENT_SENT, 0)
	failed = counts.get(RECIPIENT_FAILED, 0)
	skipped = counts.get(RECIPIENT_SKIPPED, 0)

	if pending or (sent and failed):
		# Rows left pending means the run stopped early — the daily cap, or a
		# worker that did not reach the end. Either way there is more to do.
		status = STATUS_PARTLY_SENT
	elif failed:
		status = STATUS_FAILED
	elif sent or skipped:
		# A broadcast whose whole audience had opted out by the time it ran is
		# finished, not broken. Marking it failed would send somebody looking for
		# a fault that is not there; the totals beside it say nought sent and how
		# many were skipped, which is the honest account.
		status = STATUS_SENT
	else:
		status = STATUS_FAILED

	frappe.db.set_value(
		BROADCAST_DOCTYPE,
		doc.name,
		{
			"status": status,
			"total_sent": sent,
			"total_failed": failed,
			"total_skipped": skipped,
			"sent_on": now_datetime(),
		},
		update_modified=False,
	)
	frappe.db.commit()


def _tally(broadcast: str) -> dict[str, int]:
	"""How many of one broadcast's rows are in each state.

	Four counts rather than one grouped query, because Frappe refuses a raw SQL
	function in a `fields` list and the dict form buys nothing here: this runs once
	at the end of a broadcast, not once per recipient.
	"""
	return {
		status: frappe.db.count(
			RECIPIENT_DOCTYPE,
			{
				"parent": broadcast,
				"parenttype": BROADCAST_DOCTYPE,
				"delivery_status": status,
			},
		)
		for status in (RECIPIENT_PENDING, RECIPIENT_SENT, RECIPIENT_FAILED, RECIPIENT_SKIPPED)
	}


def _remaining_today(config) -> int | None:
	"""How many more messages the society is willing to send today, or None.

	None means uncapped, which is the shipped default and an honest one: the
	right number depends on how old the society's WhatsApp number is and what it
	has done before, and a figure invented here would be a guess presented as a
	safety measure.
	"""
	limit = cint(config.daily_limit)

	if limit <= 0:
		return None

	already = frappe.db.count(
		RECIPIENT_DOCTYPE,
		{
			"parenttype": BROADCAST_DOCTYPE,
			"delivery_status": RECIPIENT_SENT,
			"sent_on": [">=", today()],
		},
	)

	return max(limit - already, 0)


def _compose(message: str, config) -> str:
	"""The broadcast, plus the line that tells people how to stop it.

	Appended here rather than typed by the composer, so it cannot be forgotten on
	the one message somebody sends in a hurry. A society that has cleared the
	setting gets no line, which is their decision to make and the reason it is a
	field rather than a constant.
	"""
	notice = (config.opt_out_notice or "").strip()

	return f"{message.strip()}\n\n{notice}" if notice else message.strip()


def release_scheduled() -> int:
	"""Queue what is due and pick up what was left unfinished. Returns how many.

	Two kinds of broadcast, and the second is the half of the daily limit that
	would otherwise be missing. A broadcast that hit the cap stops with its
	remaining people still `Pending`; without a sweep that comes back for them,
	the cap would not delay those messages, it would silently cancel them.

	Idempotent twice over: the deduplicating job id in `release` stops a
	broadcast that is already running from being queued again, and a run with
	nothing left to do finds no pending rows and does nothing.
	"""
	due = frappe.get_all(
		BROADCAST_DOCTYPE,
		filters={
			"docstatus": 1,
			"status": STATUS_SCHEDULED,
			"scheduled_at": ["<=", now_datetime()],
		},
		pluck="name",
		ignore_permissions=True,
	)

	for broadcast in _unfinished():
		if broadcast not in due:
			due.append(broadcast)

	for broadcast in due:
		release(broadcast)

	return len(due)


def _unfinished() -> list[str]:
	"""Approved broadcasts that still have somebody waiting to be written to.

	Filtered on the status first and the rows second, so the ordinary case —
	nothing part-sent — costs one indexed query and no row scan. A broadcast
	whose remainder *failed* rather than never being tried has no pending rows
	and is correctly left alone, rather than being retried every quarter of an
	hour for ever.
	"""
	candidates = frappe.get_all(
		BROADCAST_DOCTYPE,
		filters={"docstatus": 1, "status": STATUS_PARTLY_SENT},
		pluck="name",
		ignore_permissions=True,
	)

	return [
		broadcast
		for broadcast in candidates
		if frappe.db.count(
			RECIPIENT_DOCTYPE,
			{
				"parent": broadcast,
				"parenttype": BROADCAST_DOCTYPE,
				"delivery_status": RECIPIENT_PENDING,
			},
		)
	]


# ---------------------------------------------------------------------- http


def _request(method: str, route: str, payload: dict | None = None, **parts) -> tuple[bool, dict, str]:
	"""One call to the gateway. Never raises; always says what happened.

	Returns `(ok, data, reason)`, the same shape `deployment/services/geocoding.py`
	settled on and for the same reason: every caller here is in the middle of
	something a person is waiting on, and an exception thrown from inside a
	three-hour loop would take the other three thousand nine hundred recipients
	with it. The reason is a sentence somebody can act on.
	"""
	config = settings()
	base = (config.gateway_url or "").strip().rstrip("/")
	key = config.get_password("api_key", raise_exception=False)
	path = route.format(session=(config.session_id or "").strip(), **parts)

	try:
		import requests

		answer = requests.request(
			method,
			f"{base}{API_PREFIX}{path}",
			json=payload,
			headers={API_KEY_HEADER: key, "Content-Type": "application/json"},
			timeout=TIMEOUT,
		)
	except Exception as problem:
		frappe.log_error(title="WhatsApp gateway unreachable", message=str(problem))

		return False, {}, _("The WhatsApp gateway could not be reached.")

	if answer.status_code >= 400:
		return False, {}, _gateway_reason(answer)

	try:
		return True, answer.json(), ""
	except ValueError:
		# A 2xx with a body that is not JSON. The send happened as far as the
		# gateway is concerned, and inventing a failure over an unreadable
		# receipt would re-send to somebody who has already been written to.
		return True, {}, ""


def _gateway_reason(answer) -> str:
	"""One refusal, as a sentence rather than as a status code.

	The gateway answers in NestJS's envelope — `statusCode`, `message`, `error` —
	and its `message` is a developer's sentence, so the ones that mean something
	operational are translated and the rest are reported by number. Nobody
	reading a delivery log should have to know what a 409 is.
	"""
	known = {
		401: _("The gateway rejected this site's API key."),
		403: _("WhatsApp refused the message, or the key is not allowed to send."),
		404: _("The gateway has no session by that name."),
		409: _("The WhatsApp session is not connected."),
		413: _("The message was too large to send."),
		429: _("The gateway is rate limiting; the message was not sent."),
		503: _("The gateway is busy or still starting up."),
	}

	if answer.status_code in known:
		return known[answer.status_code]

	return _("The gateway refused the message ({0}).").format(answer.status_code)
