# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The member card — the pocket-sized half of what the certificate says at length.

The domain half of a card, and the sibling of `volunteer/services/card.py`.
Both hand one dict to `vmmsx/cards/`, which knows nothing about either of them.

**A card is not a certificate, and this is not a second implementation of one.**
`certificate.py` renders the framed thing a member prints once and puts on a
wall; this renders the thing they carry. They differ in what belongs on them,
which is why the contexts differ, and they share `may_print` rather than
inventing a second answer to who is allowed one.

**Only an active membership has a card.** Delegated whole to
`certificate.assert_active`, so a membership under review, lapsed or cancelled
is refused a card for exactly the same reason and with exactly the same words
that refuse it a certificate.
"""

import frappe
from frappe import _
from frappe.utils import format_date

from vmmsx.cards.services import card
from vmmsx.member.services import certificate, identity

MEMBER_DOCTYPE = "VMMS Member"

# The template a member card renders through. See the volunteer twin: one kind
# of card, and its wording is entirely the society's in the record this names.
TEMPLATE_KEY = "member_card"


def _photo(member, absolute_assets: bool = False) -> str:
	"""The holder's photograph, or an empty string. See the volunteer twin.

	Takes the *member* rather than the membership: a photograph is a fact about
	the person, and a person holding memberships at two branches has one face.
	"""
	from vmmsx.cards.services import assets

	url = identity.read(member).get("profile_photo") or ""

	if not url:
		return ""

	return assets.printable_asset(url) if absolute_assets else url


def context_for(membership, absolute_assets: bool = False) -> dict:
	"""Everything a member card could want to say, as plain values."""
	from onerc_core.geo.services import adapter

	from vmmsx.member.services import membership as membership_service

	membership_type = membership_service.type_of(membership)
	member = frappe.get_doc(MEMBER_DOCTYPE, membership.member)

	return {
		**card.frame(membership, absolute_assets=absolute_assets),
		"card_kind": _("Member"),
		"holder_name": identity.display_name(member),
		# The twin of `volunteer/services/card.py::_photo`, and it is here rather
		# than only on the volunteer card because both render through one shared
		# template: a body that drew a portrait for one kind of card and left a
		# gap on the other would look like a fault rather than a decision. Read
		# live from Red Profile, stored nowhere, empty draws nothing.
		"holder_photo": _photo(member, absolute_assets=absolute_assets),
		"record_id": membership.name,
		"member_id": member.name,
		"membership_type": membership_type.membership_type_name,
		"status": membership.membership_status or "",
		"geo_node": membership.geo_node or "",
		"geo_path": adapter.get_full_path(membership.geo_node) if membership.geo_node else "",
		"valid_from": format_date(membership.valid_from) if membership.valid_from else "",
		# The certificate's own answer, reused rather than restated: a lifetime
		# membership has no end date, and "" beside the word "Valid to" reads as a
		# value that failed to load rather than as a membership that never ends.
		"valid_to": certificate._valid_to_text(membership, membership_type),
		"is_lifetime": membership_service.is_lifetime(membership_type),
		"issued_on": format_date(frappe.utils.now_datetime()),
	}


def render_card(membership, absolute_assets: bool = False) -> dict:
	"""This membership's card, rendered through the shared template service."""
	card.assert_template(TEMPLATE_KEY)

	return card.render_card(TEMPLATE_KEY, context_for(membership, absolute_assets=absolute_assets))


def pdf_for(membership) -> bytes:
	"""This membership's card as PDF bytes. Ungated, like the volunteer twin.

	Every caller answers the permission question in its own way and answering it
	twice is how two answers come to disagree. `api/cards.py` uses
	`certificate.may_print`, which is the society's existing answer to who may
	put a member's details on paper.
	"""
	card.assert_template(TEMPLATE_KEY)

	return card.pdf(TEMPLATE_KEY, context_for(membership, absolute_assets=True))


def pdf_filename(membership) -> str:
	"""The opaque docname, never a person. See the volunteer twin."""
	return f"member-card-{membership.name}.pdf"


def verify_dto(membership) -> dict:
	"""What somebody who scanned this card is told. Deliberately small.

	The same shape the volunteer card returns, so the verify page draws one
	answer and never asks which kind it got. Bounded to the question a person
	holding the card actually asked: who it names, where they belong, and whether
	it is still good.
	"""
	from onerc_core.geo.services import adapter

	from vmmsx.member.services import membership as membership_service

	member = frappe.get_doc(MEMBER_DOCTYPE, membership.member)
	membership_type = membership_service.type_of(membership)

	return {
		"kind": _("Member"),
		"holder_name": identity.display_name(member),
		"record_id": membership.name,
		"status": membership.membership_status or "",
		"is_current": membership.membership_status == membership_service.STATUS_ACTIVE,
		"geo_path": adapter.get_full_path(membership.geo_node) if membership.geo_node else "",
		"since": format_date(membership.valid_from) if membership.valid_from else "",
		"valid_to": certificate._valid_to_text(membership, membership_type),
	}
