# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What comes back from WhatsApp, and the one thing this app does about it.

The society's number can be replied to. It is a phone number, and a person who
receives a message on WhatsApp can simply type back — there is no way to build
this channel such that they cannot. That leaves a question every broadcast
system has to answer, and this app answers it narrowly and says so:

**Replies are read for one word and then dropped.** A reply that is an opt-out
takes the number off the list. Everything else is acknowledged and goes no
further — it is not stored, not shown to a coordinator, and not answered. That
is a deliberate limit rather than an oversight: a reply inbox is a place people
expect somebody to be, and promising one that nobody is staffing is worse than
having none. If the society wants two-way WhatsApp later, this endpoint is where
it starts, and the decision to staff it should be made before it is built.

**The address is public, so nothing here trusts the caller.** It is
`allow_guest`, because the gateway is another container and holds no login on
this site. What it holds instead is a token the society set on both sides, sent
as a header, compared in constant time, and required before a single field of
the body is read.

**An unrecognised body is acknowledged, not refused.** open-wa retries a webhook
it could not deliver, so answering an error to a payload this app does not
understand would mean the same unreadable message arriving every few seconds for
as long as the retry budget lasts. It is logged once and accepted.
"""

import hmac

import frappe

from vmmsx.notifications.services import whatsapp

#: The header the gateway is configured to send. open-wa lets a webhook carry
#: arbitrary headers, which is the documented mechanism; it does not document a
#: signature scheme, so a shared secret on a header of our own naming is the
#: honest thing to build rather than a signature that is guessed at.
TOKEN_HEADER = "X-Vmms-Token"

#: The gateway's event names. Only the first is acted on.
EVENT_MESSAGE = "message.received"


@frappe.whitelist(allow_guest=True, methods=["POST"])
def inbound() -> dict:
	"""One event from the gateway. Answers plainly and reveals nothing.

	The same answer for a reply that opted somebody out, a reply that did not,
	and an event this app ignores. A webhook that reported which numbers are on
	the society's list would be a way to ask, one number at a time, who
	volunteers for the Red Cross — so it does not report.
	"""
	if not _authentic():
		# Deliberately not `PermissionError`. That renders a Frappe error page
		# with a traceback in some configurations, and this endpoint's answer to
		# anybody without the token should be four characters long.
		frappe.local.response["http_status_code"] = 401

		return {"ok": False}

	payload = _body()
	event = payload.get("event") or payload.get("type") or ""

	if event and event != EVENT_MESSAGE:
		return {"ok": True}

	sender, text = _reply(payload)

	if sender and _is_opt_out(text):
		whatsapp.record_opt_out(sender, source=whatsapp.OPT_OUT_REPLY, notes=text[:140])

	return {"ok": True}


def _authentic() -> bool:
	"""Does this call carry the society's webhook token?

	Compared with `hmac.compare_digest` rather than `==`, so the time the
	comparison takes does not depend on how much of the token was right. An
	unset token refuses everything: a site that has not configured the webhook
	has not opened it either.
	"""
	expected = whatsapp.settings().get_password("webhook_token", raise_exception=False)

	if not expected:
		return False

	presented = frappe.get_request_header(TOKEN_HEADER) or ""

	return hmac.compare_digest(str(expected), str(presented))


def _body() -> dict:
	"""The request body as a dictionary, whatever arrived."""
	try:
		data = frappe.request.get_json(force=True, silent=True) or {}
	except Exception:
		data = {}

	return data if isinstance(data, dict) else {}


def _reply(payload: dict) -> tuple[str, str]:
	"""The sender's number and what they wrote, dug out of the event.

	Read defensively across the few shapes the payload plausibly takes, because
	open-wa's published reference names the event but does not pin the body, and
	a parser written to one exact shape is one gateway upgrade away from
	silently ignoring every opt-out. Anything unrecognised answers empty, which
	the caller treats as "not an opt-out" — the safe direction is to keep
	somebody on the list and let them ask again, never to drop a reply we could
	have read.
	"""
	inner = payload.get("data") if isinstance(payload.get("data"), dict) else payload
	message = inner.get("message") if isinstance(inner.get("message"), dict) else inner

	sender = ""
	for key in ("from", "chatId", "chat_id", "author"):
		value = message.get(key)
		if isinstance(value, str) and value:
			sender = value
			break

	text = ""
	for key in ("body", "text", "content", "caption"):
		value = message.get(key)
		if isinstance(value, str) and value:
			text = value
			break

	if not sender and not text:
		frappe.log_error(
			title="WhatsApp reply in an unfamiliar shape",
			message=frappe.as_json(payload)[:2000],
		)

	return _number(sender), (text or "").strip()


def _number(sender: str) -> str:
	"""A gateway chat address back as a number the opt-out record can hold.

	`255712345678@c.us` is what arrives. A group address (`@g.us`) is answered
	empty: a group has no one number to take off a list, and treating one as a
	person would silently opt out whoever happened to be its identifier.
	"""
	if not sender.endswith(whatsapp.CHAT_SUFFIX):
		return ""

	return "+" + sender.removesuffix(whatsapp.CHAT_SUFFIX)


def _is_opt_out(text: str) -> bool:
	"""Is this reply nothing but a word that means stop?

	The whole message, not a word inside it. "Please stop the deployment on
	Tuesday" is a sentence about work, and a substring match would take its
	author off the list for writing it.
	"""
	words = whatsapp.settings().opt_out_keywords or ""
	stop = {word.strip().casefold() for word in words.splitlines() if word.strip()}

	return text.casefold() in stop


@frappe.whitelist()
def connection() -> dict:
	"""Whether the gateway is linked, for whoever is looking at the settings.

	Signed-in and permission-checked, unlike the webhook above: this one asks
	another container a question on the caller's behalf, and that is not
	something an anonymous request should be able to make this site do.
	"""
	frappe.has_permission(whatsapp.SETTINGS_DOCTYPE, ptype="read", throw=True)

	return whatsapp.session_state()


@frappe.whitelist()
def channel() -> dict:
	"""Everything the console's WhatsApp screen needs to draw itself, in one read.

	`connection()` above answers one question and asks the gateway to answer it,
	which is a network round trip to another container. This is the *page* load,
	and it deliberately does not make that call: a coordinator opening the
	channel to look at what was sent last week should not be waiting on a
	handshake with a phone. The screen asks `connection()` separately, so a
	gateway that is slow or down costs a status line rather than the screen.
	"""
	frappe.has_permission(whatsapp.SETTINGS_DOCTYPE, ptype="read", throw=True)

	config = whatsapp.settings()

	return {
		"installed": whatsapp.installed(),
		"configured": whatsapp.configured(),
		"can_send": whatsapp.available(),
		"enabled": bool(config.enabled),
		"gateway_url": config.gateway_url,
		"session_id": config.session_id,
		# The two limits that decide how a broadcast actually paces itself. On
		# the page because "why is this still sending" is the question they
		# answer, and a coordinator should not have to open the desk to find out.
		"pacing_seconds": config.pacing_seconds,
		"daily_limit": config.daily_limit,
		"opt_out_notice": config.opt_out_notice,
		"opt_out_count": frappe.db.count(whatsapp.OPT_OUT_DOCTYPE),
	}


@frappe.whitelist()
def broadcasts(limit: int = 20) -> dict:
	"""What has been sent on this channel, most recent first.

	`get_list`, so the caller's own permissions bound it. Counts come off the
	broadcast's own tallied fields rather than being recounted from the
	recipient table — the tally is what the sender wrote when it finished, and
	recounting could disagree with it on a broadcast still going out.
	"""
	rows = frappe.get_list(
		whatsapp.BROADCAST_DOCTYPE,
		fields=[
			"name",
			"title",
			"status",
			"audience",
			"geo_node",
			"scheduled_at",
			"sent_on",
			"creation",
			"addressed",
			"total_recipients",
			"total_sent",
			"total_failed",
			"total_skipped",
			"docstatus",
		],
		order_by="creation desc",
		limit_page_length=max(1, min(int(limit or 20), 60)),
	)

	return {
		"broadcasts": [
			{
				**row,
				"creation": str(row.get("creation") or ""),
				"scheduled_at": str(row.get("scheduled_at") or "") or None,
				"sent_on": str(row.get("sent_on") or "") or None,
				# A draft is waiting on somebody with submit rights, which is
				# the point of the channel's second pair of eyes. Said as a flag
				# so the screen names it rather than reading a docstatus.
				"awaiting_release": row.get("docstatus") == 0,
			}
			for row in rows
		]
	}


@frappe.whitelist()
def opt_outs(limit: int = 100) -> dict:
	"""Who has asked not to receive these, and how they asked.

	A register worth being able to read: the channel's whole promise is that
	replying STOP works, and a coordinator who cannot see the list has no way to
	check that it did. Phone numbers only — an opt-out record deliberately holds
	no name, because matching a number back to a person would make this list a
	way to ask who volunteers for the Red Cross.
	"""
	rows = frappe.get_list(
		whatsapp.OPT_OUT_DOCTYPE,
		fields=["name", "phone_number", "opted_out_on", "source", "notes"],
		order_by="opted_out_on desc",
		limit_page_length=max(1, min(int(limit or 100), 500)),
	)

	return {
		"opt_outs": [{**row, "opted_out_on": str(row.get("opted_out_on") or "")} for row in rows],
		"count": frappe.db.count(whatsapp.OPT_OUT_DOCTYPE),
	}
