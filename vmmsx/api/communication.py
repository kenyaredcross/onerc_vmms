# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Addressing the people a branch is responsible for, on four channels.

One screen in the console, four ways of reaching the same audience, and the
audience is resolved once for all of them — `notifications/services/audience.py`,
which is what `VMMS Announcement`'s fan-out has always used. That single
resolver is the whole point: a coordinator who sends a notification and then
sends the same thing by SMS has reached the same people, and nothing about the
second send re-asks a question the first one answered.

    notification   an in-app `VMMS Notification` per person with a login
    email          the same words to everybody with an address, login or not
    sms            a Draft `SMS Campaign` filed with onerc_sms, for its own
                   approval workflow to release
    whatsapp       a draft `VMMS WhatsApp Broadcast`, for somebody with submit
                   permission to approve and a worker to pace out

The first two are `announce.publish()`, unchanged and already idempotent. The
third is `notifications/services/campaign.py`, which is the seam to a companion
app and sends nothing itself. The fourth is
`notifications/services/whatsapp.py`, the seam to the society's own open-wa
gateway, and it sends nothing from this request either.

**The two filed channels are filed for different reasons, and the difference is
worth keeping straight.** SMS is filed because the approval policy belongs to
another app and this one does not overrule it. WhatsApp is filed because a
broadcast on the society's own WhatsApp number is the one send here that can
cost the society the channel itself, and a second pair of eyes is cheap against
that. Neither is filed because filing is tidy.

**Scope is a check made once, at the top, on the anchor.** Every endpoint here
that reaches people takes a `geo_node` and asserts the caller may create an
announcement anchored there — which is `frappe.has_permission` on a doctype
`hooks.py` registers as scopeable, so it is core's geo scoping and the society's
own configured role, not a rule written here. Below that assertion the audience
resolver reads with `ignore_permissions`, deliberately and for the reason its own
docstring gives: which volunteers hear from their branch must not depend on the
geo scope of whichever coordinator happened to press send.

**Nothing here names a role, a branch or an audience.** `audience` is a closed
Select the announcement doctype owns; the geo node arrives from the same
cascading picker every other screen uses; and who may open the screen at all is
`staff/services/console.py`'s `communication` section, gated on the doctype.

**Preview before send, from the same resolver as the send.** `preview()` is not
a convenience: a broadcast is the one act in this product that cannot be undone,
and a number a coordinator can read before pressing anything is what makes "this
is going to 4,300 people" a decision rather than a discovery.
"""

import frappe
from frappe import _

from vmmsx.notifications.services import announce, audience, campaign, whatsapp

ANNOUNCEMENT_DOCTYPE = "VMMS Announcement"

#: The channels this screen offers, as the frontend names them. A closed set the
#: server owns, dispatched rather than branched on — the rule `audience.py`
#: states for its own `_RESOLVERS` table.
CHANNEL_NOTIFICATION = "notification"
CHANNEL_EMAIL = "email"
CHANNEL_SMS = "sms"
CHANNEL_WHATSAPP = "whatsapp"


@frappe.whitelist()
def options() -> dict:
	"""What the Communication screen can offer this person, before they compose.

	The audiences and urgencies come off the doctype's own Selects rather than
	being listed here, the same rule `api/questions.py::targets` follows for
	field types: a value added to the field appears on the screen without this
	file being edited.

	`channels` is per-caller rather than per-site. Notification and email are
	this app's own and are available to anybody who may open the screen; SMS
	depends on a companion app being installed *and* on onerc_sms's own
	permissions admitting them, so a coordinator without it sees two channels
	rather than a third that would refuse them. WhatsApp is the same shape for a
	different reason — it needs a gateway the society has actually stood up and
	linked to a phone — and it is answered without calling that gateway, so a
	container that is down slows nobody's screen down.
	"""
	_assert_may_read()

	meta = frappe.get_meta(ANNOUNCEMENT_DOCTYPE)

	sms_templates = []
	sms_source_doctypes = []
	if campaign.available() and frappe.has_permission("SMS Template", ptype="read"):
		sms_templates = frappe.get_list(
			"SMS Template",
			fields=["name", "template_name", "category", "message"],
			order_by="template_name asc",
		)
	if campaign.available():
		for doctype in (
			"VMMS Volunteer",
			"VMMS Member",
			"VMMS Volunteer Application",
			"VMMS Membership",
		):
			if frappe.db.exists("DocType", doctype) and frappe.has_permission(doctype, ptype="read"):
				sms_source_doctypes.append({"value": doctype, "label": doctype.removeprefix("VMMS ")})

	return {
		"audiences": _select_options(meta, "audience"),
		"urgencies": _select_options(meta, "urgency"),
		# The society's own vocabulary for what kind of thing this is. Named by
		# the docname, because the doctype is `autoname: prompt` — what a society
		# typed *is* the name, and there is no separate label field to read.
		# Disabled types are left out: a vocabulary somebody retired should stop
		# being offered without every announcement filed under it changing.
		"types": frappe.get_all(
			"VMMS Announcement Type",
			filters={"enabled": 1},
			fields=["name", "description"],
			order_by="name asc",
		),
		"channels": {
			CHANNEL_NOTIFICATION: True,
			CHANNEL_EMAIL: True,
			CHANNEL_SMS: campaign.available(),
			CHANNEL_WHATSAPP: whatsapp.available(),
		},
		"sms_templates": sms_templates,
		"sms_source_doctypes": sms_source_doctypes,
		# Whether they may actually send, asked of the same check `send` makes.
		# The screen draws its button from this and decides nothing itself.
		"can_send": bool(frappe.has_permission(ANNOUNCEMENT_DOCTYPE, ptype="create")),
	}


@frappe.whitelist()
def preview(geo_node: str, who: str) -> dict:
	"""How many people this would reach, per channel, before anything is sent.

	Four counts from one resolved set, because they are genuinely four different
	numbers and a screen that showed one of them would mislead: `notification`
	needs a login, `email` needs an address, `sms` needs a number with a country
	code, `whatsapp` needs that same number minus everybody who has asked to be
	left alone, and the people who have each are four overlapping sets. Somebody
	enrolled at a branch counter years ago may be reachable only by phone.

	`whatsapp` is the only one of the four that can be smaller than `sms` for a
	reason that is not missing data: somebody who replied STOP is deliberately
	not in it, and that gap is the channel working.

	`addressed` is the size of the audience itself — the honest denominator, and
	the number that makes a low reach visible as a data problem rather than as a
	small branch.
	"""
	_assert_may_address(geo_node)

	addressed = audience.profiles(geo_node, who)

	return {
		"geo_node": geo_node,
		"audience": who,
		"addressed": len(addressed),
		CHANNEL_NOTIFICATION: len(set(audience.logins(addressed).values())),
		CHANNEL_EMAIL: len(audience.emails(addressed)),
		CHANNEL_SMS: campaign.reachable(geo_node, who)["reachable"] if campaign.installed() else 0,
		CHANNEL_WHATSAPP: whatsapp.reachable(geo_node, who)["reachable"] if whatsapp.configured() else 0,
	}


@frappe.whitelist()
def send(
	title: str,
	body: str,
	geo_node: str,
	who: str,
	channels: list | str,
	urgency: str = "routine",
	announcement_type: str | None = None,
	summary: str | None = None,
	expires_on: str | None = None,
	link_label: str | None = None,
	link_href: str | None = None,
	sms_message: str | None = None,
	sms_template: str | None = None,
	sms_scheduled_at: str | None = None,
	sms_source_type: str = "VMMS Audience",
	sms_source_doctype: str | None = None,
	sms_phone_field: str | None = None,
	sms_filters: list | str | None = None,
	sms_csv_file: str | None = None,
	sms_phone_numbers: str | None = None,
	whatsapp_message: str | None = None,
	whatsapp_scheduled_at: str | None = None,
) -> dict:
	"""Compose and send on every channel asked for. Returns what each one did.

	**One announcement, whichever of the first two channels were chosen.** The
	in-app copy and the email are two reaches of one published announcement —
	`also_email` is the flag `announce.publish()` reads — so a society that sent
	both has one record of having said it, not two that can be edited apart.
	Choosing email alone publishes the announcement too: it is still the record,
	and the in-app fan-out reaching nobody is a consequence of the audience, not
	something to suppress.

	**SMS is a separate document and deliberately so.** It is another app's, it
	is not sent by this call, and its wording is usually not the announcement's
	— 160 characters is a different piece of writing from a notice. `sms_message`
	is that wording; falling back to the summary or the body is a convenience,
	not a merge.

	**WhatsApp is a separate document for the same reason and a different one.**
	Its wording is its own — a WhatsApp message is read on a phone in a thread
	beside messages from family, and an announcement's formal register reads
	oddly there — and it is filed rather than sent because approving it is a
	submit somebody else performs. `whatsapp_message` is that wording, with the
	same fallback and the same caveat.

	The report names each channel and what happened, including the channels that
	were not asked for, so a screen can say "notification: 412, email: 380, sms:
	not sent" rather than leaving a reader to infer silence.
	"""
	_assert_may_address(geo_node)

	chosen = set(frappe.parse_json(channels) if isinstance(channels, str) else (channels or []))

	if not chosen:
		frappe.throw(_("Choose at least one way to reach them."), frappe.ValidationError)

	unknown = chosen - {CHANNEL_NOTIFICATION, CHANNEL_EMAIL, CHANNEL_SMS, CHANNEL_WHATSAPP}

	if unknown:
		# Refused rather than ignored: a channel the caller believes it asked for
		# and this endpoint silently dropped is a message somebody thinks they
		# sent.
		frappe.throw(
			_("{0} is not a channel this society can send on.").format(
				frappe.bold(", ".join(sorted(unknown)))
			),
			frappe.ValidationError,
			title=_("Unknown Channel"),
		)

	report: dict = {"announcement": None, "sms": None, "whatsapp": None}

	if chosen & {CHANNEL_NOTIFICATION, CHANNEL_EMAIL}:
		announcement = _publish(
			title=title,
			body=body,
			geo_node=geo_node,
			who=who,
			urgency=urgency,
			announcement_type=announcement_type,
			summary=summary,
			expires_on=expires_on,
			link_label=link_label,
			link_href=link_href,
			also_email=CHANNEL_EMAIL in chosen,
		)
		report["announcement"] = announcement
		# The in-app channel reached nobody when it was not asked for, which is a
		# different statement from "it failed", and the screen says which.
		report["notification_sent"] = CHANNEL_NOTIFICATION in chosen
		report["email_sent"] = CHANNEL_EMAIL in chosen

	if CHANNEL_SMS in chosen:
		report["sms"] = campaign.draft(
			name=title,
			message=(sms_message or summary or body or "").strip(),
			geo_node=geo_node,
			who=who,
			template=sms_template,
			scheduled_at=sms_scheduled_at,
			source_type=sms_source_type,
			source_doctype=sms_source_doctype,
			phone_field=sms_phone_field,
			filters=frappe.parse_json(sms_filters) if isinstance(sms_filters, str) else sms_filters,
			csv_file=sms_csv_file,
			phone_numbers=sms_phone_numbers,
		)

	if CHANNEL_WHATSAPP in chosen:
		report["whatsapp"] = whatsapp.draft(
			title=title,
			message=(whatsapp_message or summary or body or "").strip(),
			geo_node=geo_node,
			who=who,
			scheduled_at=whatsapp_scheduled_at,
		)

	return report


def _publish(
	title: str,
	body: str,
	geo_node: str,
	who: str,
	urgency: str,
	announcement_type: str | None,
	summary: str | None,
	expires_on: str | None,
	link_label: str | None,
	link_href: str | None,
	also_email: bool,
) -> dict:
	"""Write the announcement and fan it out. The document's own save, always.

	`insert()` runs the controller's `validate()` and Frappe's permission check,
	so an announcement this endpoint would not be allowed to create is refused
	by the framework as well as by the assertion at the top — defence in depth
	rather than duplication, the same shape `api/questions.py` describes.
	"""
	doc = frappe.new_doc(ANNOUNCEMENT_DOCTYPE)
	doc.title = title
	doc.summary = summary or ""
	doc.body = body
	doc.geo_node = geo_node
	doc.audience = who
	doc.urgency = urgency
	doc.announcement_type = announcement_type or None
	doc.link_label = link_label or ""
	doc.link_href = link_href or ""
	doc.expires_on = expires_on or None
	doc.also_email = 1 if also_email else 0
	# Published on the way in rather than saved as a draft and published by a
	# second call: this endpoint *is* the act of sending, and a half-state
	# between the two would be a record of something nobody meant to keep.
	doc.status = announce.STATUS_PUBLISHED
	doc.insert()

	return announce.publish(doc)


def _select_options(meta, fieldname: str) -> list[str]:
	"""The values of a Select field, in the order the doctype declares them."""
	field = meta.get_field(fieldname)

	return [
		option.strip() for option in ((field.options if field else "") or "").split("\n") if option.strip()
	]


def _assert_may_read() -> None:
	frappe.has_permission(ANNOUNCEMENT_DOCTYPE, ptype="read", throw=True)


def _assert_may_address(geo_node: str) -> None:
	"""May this caller address that part of the society?

	**Asked of a document, not of the doctype.** `frappe.has_permission` with a
	`doc` runs core's geo scoping against the anchor, which is the whole of the
	question — holding the announcement role does not make somebody entitled to
	address a branch on the other side of the country. Asking the doctype alone
	would answer "yes, they may create announcements" and let them anchor one
	anywhere.

	The document is built and never saved. That is not a trick: a permission
	check needs something to check against, and constructing the exact record
	the caller is proposing is the most honest thing to hand it.
	"""
	if not geo_node:
		frappe.throw(
			_("Say which part of the society this is coming from."),
			frappe.ValidationError,
			title=_("No Branch Chosen"),
		)

	proposed = frappe.new_doc(ANNOUNCEMENT_DOCTYPE)
	proposed.geo_node = geo_node

	if not frappe.has_permission(ANNOUNCEMENT_DOCTYPE, ptype="create", doc=proposed):
		frappe.throw(
			_("You cannot send to that part of the society."),
			frappe.PermissionError,
			title=_("Out of Your Area"),
		)
