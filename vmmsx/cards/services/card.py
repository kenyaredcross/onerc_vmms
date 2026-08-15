# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The mechanics every card shares, and no card's contents.

A volunteer card and a member card are the same object with different words on
it: the society's lockup, who the holder is, where they belong, what the
society calls them, and a QR that lets somebody standing in front of them check
it. This module owns that shape. What goes in the fields is the domain's, in
`volunteer/services/card.py` and `member/services/card.py`, and what it *looks*
like is the society's, in a `VMMS Template` an administrator can rewrite.

**Nothing here names a volunteer or a membership**, the same rule
`vmmsx/templating` holds and for the same reason: the two domains are callers,
and a third kind of card is a third caller rather than an edit to this file.

**Nothing about a card is stored.** It is derived from the record every time it
is asked for, exactly as a certificate is, so a card shown on a screen and a
card printed to PDF are the same answer and neither can go stale. The one
persisted thing is the token, which is an identifier rather than a rendering.
"""

import frappe
from frappe import _
from frappe.utils import get_url
from frappe.utils.pdf import get_pdf

from vmmsx.cards.services import assets, qr, token
from vmmsx.templating.services import render

# Where a scanned card lands. A route rather than an API path, because the thing
# on the card is followed by a phone camera and has to render a page for a
# person, not JSON for a program. `hooks.py` sends it to the SPA.
VERIFY_ROUTE = "/verify"


def verify_url(card_token: str) -> str:
	"""The absolute address a QR on this card points at.

	Absolute because it is printed: a relative path is meaningless once the card
	is a piece of card in somebody's pocket.
	"""
	return get_url(f"{VERIFY_ROUTE}/{card_token}")


def frame(doc, absolute_assets: bool = False) -> dict:
	"""The half of a card's context that is the same for every kind of card.

	The society's lockup, the token, and the QR that carries it. Merged with
	whatever the domain adds, so a template always has these keys whatever it is
	rendering.

	`absolute_assets` is the PDF path asking for asset references it can resolve;
	see `assets.printable_asset` for why a bare path is a trap there and nowhere
	else. The QR is a data URI in both cases, because it is generated rather than
	stored and there is nothing to point at.
	"""
	from vmmsx.notifications.services import branding

	# The society's one answer about itself, read through the reader that already
	# exists rather than a fourth one. Never raises: an unconfigured society gets
	# a card with no logo, exactly as it gets an unbranded email.
	lockup = branding.lockup()
	logo = lockup.get("brand_logo") or ""
	card_token = token.ensure(doc)

	return {
		"society_name": lockup.get("brand_name") or "",
		"society_logo": assets.printable_asset(logo) if absolute_assets else logo,
		"card_token": card_token,
		"verify_url": verify_url(card_token),
		"verify_qr": qr.data_uri(verify_url(card_token)),
	}


def render_card(template_key: str, context: dict) -> dict:
	"""Render a card through the shared template service. Adds no formatting."""
	return render.render_template(template_key, context)


def pdf(template_key: str, context: dict) -> bytes:
	"""A rendered card as PDF bytes.

	Nothing is stored and no File row is created: the bytes are handed back for
	the response to stream or for an email to attach.
	"""
	return get_pdf(render_card(template_key, context)["body"])


def assert_template(template_key: str) -> None:
	"""Refuse early, and say which record is missing, when no template exists.

	Without this the failure surfaces from inside the render service as a
	missing-template error naming a key nobody recognises. A society that has
	never migrated far enough to seed its cards should be told which record to
	create.
	"""
	if frappe.db.exists("VMMS Template", {"template_key": template_key, "is_active": 1}):
		return

	frappe.throw(
		_("There is no active {0} template with the key {1}.").format(
			frappe.bold("VMMS Template"), frappe.bold(template_key)
		),
		frappe.DoesNotExistError,
		title=_("No Card Template"),
	)
