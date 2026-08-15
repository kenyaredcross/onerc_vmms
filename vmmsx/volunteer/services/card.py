# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The volunteer card — what a volunteer carries, and what a stranger may check.

The domain half of a card, deliberately thin. It knows what a volunteer is and
what belongs on the thing they show at a gate; it knows nothing about Jinja,
QR codes or PDFs, which are `vmmsx/cards/`, which in turn knows nothing about
volunteers. Between them there is one dict. Same split as
`member/services/certificate.py` and `vmmsx/templating`.

**Two audiences, two functions, and they are not the same data.**
`context_for` is what the holder sees on their own card, and it is theirs.
`verify_dto` is what somebody scanning the QR sees, and it is bounded to the
question they actually asked: is this card real, and is it still good. It
carries no email, no phone, no identification and no history, because the person
reading it has no account and did not ask any of that.

**A card is only for somebody the society has actually accepted.** An
application under review has no card, because a card is evidence of standing
and one issued for a decision nobody has taken yet would be evidence of
nothing. That is `assert_holds`, the volunteer equivalent of
`certificate.assert_active`.
"""

import frappe
from frappe import _
from frappe.utils import format_date

from vmmsx.cards.services import card
from vmmsx.volunteer.services import identity

VOLUNTEER_DOCTYPE = "VMMS Volunteer"

# The template a volunteer card renders through. A fixed key rather than a field
# on a record, because there is one kind of volunteer card; *what it says* is
# still entirely the society's, in the `VMMS Template` body this points at.
TEMPLATE_KEY = "volunteer_card"

# The one status a card is issued for. Read from the volunteer's own Select
# rather than assumed anywhere else in this module.
ACTIVE = "Active"


def _photo(volunteer, absolute_assets: bool = False) -> str:
	"""The holder's photograph, or an empty string.

	Read live from core's Red Profile through the same reader everything else
	about the person goes through — never copied onto the volunteer record,
	which owns no identity fields at all and must not start owning one because a
	card wanted it. Replace somebody's photograph on their profile and their
	next card carries the new one, with nothing anywhere to update.

	Empty is ordinary and the template draws nothing for it: a society that does
	not photograph its volunteers gets a card without a portrait rather than a
	broken image, which is the same contract `frame()` keeps for a society with
	no logo.
	"""
	from vmmsx.cards.services import assets

	url = identity.read(volunteer).get("profile_photo") or ""

	if not url:
		return ""

	return assets.printable_asset(url) if absolute_assets else url


def context_for(volunteer, absolute_assets: bool = False) -> dict:
	"""Everything a volunteer card could want to say, as plain values.

	Flat and already formatted, like the certificate's context and for the same
	reason: the template is written by an administrator, so it is handed strings
	rather than documents to walk. A context of live objects would invite
	templates to reach into the ORM, which is what the sandbox exists to prevent.
	"""
	from onerc_core.geo.services import adapter

	return {
		**card.frame(volunteer, absolute_assets=absolute_assets),
		# What the society calls this kind of card. In the context rather than
		# the template body so that a society which has already rewritten its
		# card still gets the word, the same argument `_valid_to_text` makes.
		"card_kind": _("Volunteer"),
		"holder_name": identity.display_name(volunteer),
		# The photograph on the card, read from core's Red Profile at the moment
		# of rendering and stored nowhere here — the same treatment the name
		# gets, for the same reason. It is in the *domain* context rather than in
		# `card.frame()` because a frame is what every card shares (the society's
		# lockup, the token, the QR) and whose face is on it is this domain's.
		#
		# `printable_asset` for the PDF path, exactly as the society's logo is
		# handled: a bare `/files/...` path is unresolvable to the PDF renderer,
		# which is a blank square on a printed card rather than an error anybody
		# would see.
		"holder_photo": _photo(volunteer, absolute_assets=absolute_assets),
		"record_id": volunteer.name,
		"status": volunteer.status or "",
		"geo_node": volunteer.home_geo_node or "",
		"geo_path": adapter.get_full_path(volunteer.home_geo_node) if volunteer.home_geo_node else "",
		"joined_on": format_date(volunteer.joined_on) if volunteer.joined_on else "",
		"issued_on": format_date(frappe.utils.now_datetime()),
	}


def render_card(volunteer, absolute_assets: bool = False) -> dict:
	"""This volunteer's card, rendered through the shared template service."""
	card.assert_template(TEMPLATE_KEY)

	return card.render_card(TEMPLATE_KEY, context_for(volunteer, absolute_assets=absolute_assets))


def pdf_for(volunteer) -> bytes:
	"""This volunteer's card as PDF bytes, rendered with resolvable assets.

	Ungated on purpose: every caller has already answered the permission
	question in its own way, and answering it twice in two different ways is how
	the two come to disagree. `api/cards.py` admits the holder and nobody else;
	the congratulations email is sent by the acceptance path to the person it
	just accepted.
	"""
	card.assert_template(TEMPLATE_KEY)

	return card.pdf(TEMPLATE_KEY, context_for(volunteer, absolute_assets=True))


def pdf_filename(volunteer) -> str:
	"""What the downloaded file is called. The opaque docname, never a person.

	A filename lands in a downloads folder, an email attachment and a support
	ticket, and it travels without its contents being opened. Naming it after the
	record rather than the volunteer keeps somebody's name out of all three.
	"""
	return f"volunteer-card-{volunteer.name}.pdf"


def holds_card(volunteer) -> bool:
	"""Is this volunteer somebody the society currently stands behind?"""
	return (volunteer.status or "") == ACTIVE


def assert_holds(volunteer) -> None:
	"""Refuse a card for a volunteer who is not active.

	Shared by the screen and the download so the two cannot come to disagree
	about who has one.
	"""
	if holds_card(volunteer):
		return

	frappe.throw(
		_("This volunteer record is {0}, so it has no current card.").format(
			frappe.bold(_(volunteer.status or "incomplete"))
		),
		frappe.ValidationError,
		title=_("No Current Card"),
	)


def verify_dto(volunteer) -> dict:
	"""What somebody who scanned this card is told. Deliberately small.

	**The whole of the public surface of a volunteer record**, and every field in
	it is one a person holding the card could already read off the card. The
	question being answered is "is this genuine and still current", so the answer
	is who it names, where they belong, and whether the society still stands
	behind it. Nothing else: no email, no phone, no identification, no deployment
	history, and no way to ask for any.

	`is_current` rather than the raw status as the headline, because the reader
	is deciding something and a vocabulary of society-specific statuses is not
	what they asked. The status is included beside it for a reader who wants the
	society's own word.
	"""
	from onerc_core.geo.services import adapter

	return {
		"kind": _("Volunteer"),
		"holder_name": identity.display_name(volunteer),
		"record_id": volunteer.name,
		"status": volunteer.status or "",
		"is_current": holds_card(volunteer),
		"geo_path": adapter.get_full_path(volunteer.home_geo_node) if volunteer.home_geo_node else "",
		"since": format_date(volunteer.joined_on) if volunteer.joined_on else "",
		# A membership has an end date and a volunteer record does not, so the key
		# is present and empty rather than absent: one shape for the verify page,
		# whichever kind of card was scanned.
		"valid_to": "",
	}
