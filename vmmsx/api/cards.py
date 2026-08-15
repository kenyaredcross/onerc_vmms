# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Cards: the holder's own, and the one question a stranger may ask about it.

Three endpoints, two audiences.

**The possessive pair take no arguments.** `my_volunteer_card` and
`my_member_card` resolve the caller through core's `Red Profile.user` and can
only ever answer for the session's own records. A caller cannot name anybody, so
there is no check here to get wrong. Same shape as `my_memberships`,
`my_volunteer` and `approvals.my_queue`.

**`verify` is this app's fourth `allow_guest` endpoint**, after
`content.surface`, `society.branding` and `locations.published`, and it earns
the same way they do: it answers a question somebody has *before they have an
account*. A steward on a gate holding somebody's card has no login and never
will, and "is this card genuine" is unanswerable without one otherwise.

It is bounded exactly as the other three are, by a value on a document rather
than by a condition in code: the opaque `card_token`. Not the docname, which is
printed in a sequence and would let anybody walk the register by counting; and
not a search, because there is no parameter here but the token. What it returns
is `verify_dto`, which is every field a person holding the card can already read
off the card, and nothing else — no email, no phone, no identification, no
history, and no second call that would offer any.
"""

import frappe
from frappe import _

from vmmsx.cards.services import token
from vmmsx.member.services import card as member_card
from vmmsx.member.services import certificate
from vmmsx.volunteer.services import card as volunteer_card

VOLUNTEER_DOCTYPE = "VMMS Volunteer"
MEMBERSHIP_DOCTYPE = "VMMS Membership"

# The doctypes a token is allowed to resolve to. Named here rather than searched
# for, so this can never become a way to reach an arbitrary record that has
# grown a field of the same name.
CARD_DOCTYPES = (VOLUNTEER_DOCTYPE, MEMBERSHIP_DOCTYPE)


@frappe.whitelist()
def my_volunteer_card() -> dict | None:
	"""The caller's own volunteer card, rendered. None if they have no record.

	None rather than a refusal, because "you are not a volunteer" is an ordinary
	answer for somebody looking at their own profile, not an error.
	"""
	volunteer = _my_volunteer()

	if not volunteer:
		return None

	volunteer_card.assert_holds(volunteer)

	return _card_dto(volunteer_card.render_card(volunteer), volunteer.name, VOLUNTEER_DOCTYPE)


@frappe.whitelist()
def my_member_card() -> dict | None:
	"""The caller's own member card, for their active membership. None if none."""
	membership = _my_membership()

	if not membership:
		return None

	certificate.assert_active(membership)

	return _card_dto(member_card.render_card(membership), membership.name, MEMBERSHIP_DOCTYPE)


@frappe.whitelist()
def download_my_card(kind: str):
	"""The caller's own card as a PDF download.

	`kind` selects between the two through a dispatch table rather than a chain
	of comparisons, the same shape `announce._URGENCY` and `member.approval._BEGIN`
	use. An unknown kind reaches nothing.
	"""
	entry = _CARDS.get(kind)

	if not entry:
		frappe.throw(
			_("There is no card of that kind."), frappe.ValidationError, title=_("Unknown Card")
		)

	content, filename = _my_pdf(entry)

	frappe.local.response.filename = filename
	frappe.local.response.filecontent = content
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def download_card(kind: str, name: str):
	"""Somebody else's card as a PDF, for a coordinator reprinting one.

	The companion to `download_my_card`, and the differences are the point.

	**It names a record, so it needs a check the possessive one does not.** That
	check is `read`, not `write`: printing a card that already exists is not
	changing anything, and requiring write here would refuse a coordinator whose
	job is to hand somebody a replacement. It is the ordinary permission layer,
	so core's geo scoping comes with it and a card outside the caller's own area
	is not reachable by naming it.

	**Not a fifth `allow_guest`.** `verify` is the stranger's endpoint and it is
	bounded by an unguessable token; this one is bounded by a role and a scope,
	and hands back the whole rendered card rather than what is printed on the
	front. The two must not be confused: the reason `verify` can be public is
	precisely that it discloses less than this does.

	The same `_CARDS` dispatch table `download_my_card` uses, so an unknown kind
	reaches nothing here either.
	"""
	entry = _CARDS.get(kind)

	if not entry:
		frappe.throw(
			_("There is no card of that kind."), frappe.ValidationError, title=_("Unknown Card")
		)

	doc = frappe.get_doc(entry["doctype"], name)
	doc.check_permission("read")

	entry["assert_holds"](doc)

	frappe.local.response.filename = entry["filename"](doc)
	frappe.local.response.filecontent = entry["pdf"](doc)
	frappe.local.response.type = "pdf"


@frappe.whitelist(allow_guest=True)
def verify(token: str) -> dict:
	"""Is this card genuine, and is it still current? The whole public surface.

	Returns `{"found": False}` for a token that resolves to nothing, and says
	nothing more about it. A message distinguishing "no such card" from "a card
	that was withdrawn" would answer a question the reader did not ask and turn
	this into an oracle for testing guesses.
	"""
	found = _resolve(token)

	if not found:
		return {"found": False}

	doctype, name = found

	# Elevated, and this is the endpoint where that has to be said carefully. The
	# caller is a guest by design and holds no permission on either register. What
	# bounds this is not a role but the token: an unguessable value that only ever
	# resolves to the one record it was minted for, and the DTO below is built
	# field by field from what is already printed on the card in the reader's
	# hand. Nothing here can be pointed at a record the caller does not hold.
	doc = frappe.get_doc(doctype, name)

	return {"found": True, **_VERIFIERS[doctype](doc)}


# --- the dispatch tables --------------------------------------------------


# Everything that differs between the two kinds of card, in one table.
#
# One table rather than a pair per endpoint: the possessive download and the
# coordinator's download differ in *who they resolve* and in *what they check*,
# and in nothing else. Keeping the per-kind facts here means adding a third kind
# of card is adding a row, and it means the two doors can never disagree about
# what a volunteer card is.
#
# `assert_holds` is each domain's own precondition — a volunteer must actually
# hold a card, a membership must be active — and it runs on both doors, because
# it is a fact about the record rather than about the caller.
_CARDS = {
	"volunteer": {
		"doctype": VOLUNTEER_DOCTYPE,
		"mine": lambda: _my_volunteer(),
		"missing": lambda: _("You have no volunteer record."),
		"assert_holds": volunteer_card.assert_holds,
		"pdf": volunteer_card.pdf_for,
		"filename": volunteer_card.pdf_filename,
	},
	"member": {
		"doctype": MEMBERSHIP_DOCTYPE,
		"mine": lambda: _my_membership(),
		"missing": lambda: _("You have no active membership."),
		"assert_holds": certificate.assert_active,
		"pdf": member_card.pdf_for,
		"filename": member_card.pdf_filename,
	},
}


def _my_pdf(entry: dict) -> tuple[bytes, str]:
	"""The caller's own card of this kind, or an ordinary refusal.

	No permission check and none needed: `mine` resolves through the session and
	cannot be pointed at anybody, which is the property the possessive endpoints
	are built on.
	"""
	doc = entry["mine"]()

	if not doc:
		frappe.throw(entry["missing"](), frappe.DoesNotExistError)

	entry["assert_holds"](doc)

	return entry["pdf"](doc), entry["filename"](doc)

_VERIFIERS = {
	VOLUNTEER_DOCTYPE: volunteer_card.verify_dto,
	MEMBERSHIP_DOCTYPE: member_card.verify_dto,
}


# --- resolving the caller, and the token ----------------------------------


def _resolve(card_token: str):
	return token.holder(card_token, CARD_DOCTYPES)


def _card_dto(rendered: dict, name: str, doctype: str) -> dict:
	"""One rendered card, as an explicit dict.

	`html` is the body the shared renderer produced; the screen puts it on the
	page and adds nothing. The download link is built by the caller from `kind`,
	so no URL is written down in two places.
	"""
	return {
		"doctype": doctype,
		"name": name,
		"html": rendered["body"],
	}


def _my_volunteer():
	"""The caller's own volunteer record, or None.

	Delegated to `api/volunteer.py::_my_volunteer`, which is already the one
	answer to "which volunteer record is the session's" and already refuses the
	Guest session. A second resolution here would be a second place for that
	answer to drift.
	"""
	from vmmsx.api.volunteer import _my_volunteer as resolve

	name = resolve()

	return frappe.get_doc(VOLUNTEER_DOCTYPE, name) if name else None


def _my_membership():
	"""The caller's own active membership, the most recent if they hold several.

	`_my_member` is `api/member.py`'s own resolution, reused for the same reason.
	The ordering matters only for somebody who has renewed: the current card is
	the one that started most recently.
	"""
	from vmmsx.api.member import _my_member
	from vmmsx.member.services import membership as membership_service

	member = _my_member()

	if not member:
		return None

	name = frappe.db.get_value(
		MEMBERSHIP_DOCTYPE,
		{"member": member, "membership_status": membership_service.STATUS_ACTIVE},
		"name",
		order_by="valid_from desc",
	)

	return frappe.get_doc(MEMBERSHIP_DOCTYPE, name) if name else None
