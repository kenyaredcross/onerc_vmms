# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The membership certificate — a context, handed to the shared renderer.

This module is the *domain* half of certificate rendering, and it is deliberately
thin. It knows what a membership is and what a reader of a certificate would
want to see; it knows nothing about Jinja, escaping or output formats. Those
live in `vmmsx/templating`, which knows nothing about memberships. Between them
there is one dict.

**Which template renders is configuration.** The membership type's
`template_key` points at a `VMMS Template`. There is no default buried in this
file and no `if certificate:` anywhere — pointing a type at a different template
changes every certificate it issues, with no code change and no deployment.

**The receipt is optional enrichment.** A certificate renders whether or not a
gateway ever produced a receipt number: the context carries `payment_receipt`
only when there is one, and the shipped template shows that row only when it is
present. A society running on the Manual driver, which may never deliver a
separate receipt, gets a complete certificate all the same. The society's logo
is the same shape of optional: absent, the template renders without it.

**Who may print is two questions, and this module answers both.** The member it
belongs to — recognised through core's `Red Profile.user`, never through the
document's `owner`, which is the clerk who typed it — or whoever holds the role
the society named. An unresolved role refuses; it never grants. See `may_print`.

**Nothing about a certificate is stored.** It is derived from the membership at
the moment it is asked for, in HTML for a screen and in PDF for a download, and
a stored copy would only ever be a second answer waiting to go stale.
"""

import frappe
from frappe import _
from frappe.utils import format_date, now_datetime
from frappe.utils.pdf import get_pdf

from vmmsx.cards.services import assets
from vmmsx.member.services import identity, society
from vmmsx.templating.services import render

MEMBER_DOCTYPE = "VMMS Member"

# Logged whenever a print is refused, so a society can tell "the rule stopped
# them" from "the software is broken" without reading the source.
PRINT_REFUSED_LOG_TITLE = "Certificate print refused"


def context_for(membership, absolute_assets: bool = False) -> dict:
	"""Everything a membership certificate could want to say, as plain values.

	Flat and already formatted. The template is written by an administrator, so
	it is handed strings and lists rather than documents to walk — a context of
	live objects would invite templates to reach into the ORM, which is exactly
	what the sandbox exists to prevent.

	`absolute_assets` is the PDF path's flag and nothing else's. Off, the logo is
	whatever core stored — normally `/files/logo.png`, which a browser on this
	site resolves without help. On, it is rewritten to something that carries its
	own location: see `printable_asset()` for why a bare path is a trap for the
	PDF renderer and not for anything else.
	"""
	from onerc_core.geo.services import adapter

	from vmmsx.member.services import membership as membership_service

	membership_type = membership_service.type_of(membership)
	member = frappe.get_doc(MEMBER_DOCTYPE, membership.member)
	logo = society.logo()

	return {
		"member_name": identity.display_name(member),
		"member_id": member.name,
		"membership_id": membership.name,
		"membership_type": membership_type.membership_type_name,
		"membership_type_key": membership_type.membership_type_key,
		"geo_node": membership.geo_node,
		"geo_path": adapter.get_full_path(membership.geo_node) if membership.geo_node else "",
		"valid_from": format_date(membership.valid_from) if membership.valid_from else "",
		"valid_to": _valid_to_text(membership, membership_type),
		# The same fact as a flag, for a template that wants to say it its own
		# way — a different line, a seal, nothing at all.
		"is_lifetime": membership_service.is_lifetime(membership_type),
		"benefits": [row.benefit_name for row in membership_type.benefits if row.is_active],
		"society_name": society.society_name() or "",
		# The society's own mark, read from core's settings and never copied.
		# Empty is ordinary: a society that has not uploaded one gets a
		# certificate with no logo, and the shipped template guards on it.
		"society_logo": printable_asset(logo) if absolute_assets else logo,
		"issued_on": format_date(now_datetime()),
		# Present only when a gateway actually produced them. A template asking
		# for a receipt that never arrived renders the row away rather than an
		# empty box.
		"payment_receipt": membership.payment_receipt or "",
		"payment_transaction": membership.payment_transaction or "",
	}


def _valid_to_text(membership, membership_type) -> str:
	"""What the certificate says the end date is, including when there is none.

	A lifetime membership carries no `valid_to`, and an empty string beside the
	words "Valid to" reads as a value that failed to load rather than as a
	membership that never expires. The word goes into the *context* rather than
	into the shipped template so that a society which has already edited its own
	certificate gets it too: a template body is configuration this app does not
	reach into, and a fix that only lands on fresh installs is not a fix.

	Empty is still returned for a membership that has not activated — there is
	no end date because there is no beginning, and a certificate is refused for
	one of those anyway (`assert_active`).
	"""
	from vmmsx.member.services import membership as membership_service

	if membership_service.is_lifetime(membership_type):
		return _("Lifetime")

	return format_date(membership.valid_to) if membership.valid_to else ""


# --- who may print --------------------------------------------------------


def owner_user(membership) -> str | None:
	"""The login of the person this membership belongs to, or None.

	Resolved through the member's Red Profile, which is the *only* place this
	question has an answer. Not `membership.owner`: that is whoever created the
	record, and for a membership registered at a branch desk it is the clerk.
	Gating on it would give the clerk every certificate they ever typed and deny
	the member their own.

	None is ordinary — a member registered from a paper form has no login — and
	it means the same thing to the gate as any other mismatch: this session is
	not the holder.
	"""
	member = frappe.get_doc(MEMBER_DOCTYPE, membership.member)

	return identity.user_of(member)


def may_print(membership, user: str | None = None) -> bool:
	"""May `user` print this membership's certificate?

	Two ways in, and the order says which is the rule and which is the exception:

	1. **The holder.** The session user is the login on the member's Red Profile.
	2. **A role the society named**, in `vmms_certificate_print_role`. A
	   membership officer printing a card at a counter, and nothing wider.

	**An unresolved role is a refusal, never a grant.** Empty setting, a setting
	naming a role that has since been deleted — both mean the society has not
	said anybody else may print, and the certificate stays the member's alone.
	This is core's own `registry.resolve_role` discipline restated: the failure
	being designed against is a blank config quietly reading as "everyone", which
	would turn a fail-closed rule into an open door and look exactly like normal
	operation.

	Administrator and System Manager pass, through core's
	`has_unrestricted_scope` — the same framework exemption the scoping layers
	use, and not a society role this file invented.
	"""
	from onerc_core.access.services.scope import has_unrestricted_scope

	user = user or frappe.session.user

	if has_unrestricted_scope(user):
		return True

	holder = owner_user(membership)

	if holder and user == holder:
		return True

	role = _print_role()

	return bool(role) and role in frappe.get_roles(user)


def _print_role() -> str | None:
	"""The configured print role, or None — logging why there is none.

	Silence here is what a misconfiguration would hide behind: a society that set
	the field to a role somebody later deleted would see certificates stop
	printing for their whole membership office, with nothing anywhere saying so.
	"""
	role = society.certificate_print_role()

	if not role:
		return None

	if not frappe.db.exists("Role", role):
		frappe.log_error(
			title=PRINT_REFUSED_LOG_TITLE,
			message=(
				f"National Society Settings {society.PRINT_ROLE_FIELD!r} names role {role!r}, which"
				" does not exist. Nobody but the member can print a certificate until it is"
				" corrected."
			),
		)

		return None

	return role


def assert_printable(membership, user: str | None = None) -> None:
	"""Refuse unless this user may print this certificate. The gate.

	Called before anything is rendered, so a refused caller never causes a
	template to run, a file to be read or a PDF to be built.
	"""
	if may_print(membership, user):
		return

	user = user or frappe.session.user
	role = society.certificate_print_role()

	frappe.log_error(
		title=PRINT_REFUSED_LOG_TITLE,
		message=(
			f"{user} asked for the certificate of {membership.name} and is neither its holder nor a"
			f" holder of the configured print role ({role or 'unset'})."
		),
	)

	frappe.throw(
		_(
			"A membership certificate belongs to the member it names. You may print it if it is"
			" yours, or if the society has given you the role that prints them."
		),
		frappe.PermissionError,
		title=_("Not Your Certificate"),
	)


# --- rendering ------------------------------------------------------------


# `printable_asset` moved to `vmmsx/cards/services/assets.py` when the volunteer
# and member cards needed the same conversion. It was never about memberships —
# it takes a URL string and gives one back — and a second copy in the volunteer
# domain was the alternative. Re-exported under the name this module has always
# had, so every existing caller and its tests are untouched.
printable_asset = assets.printable_asset


def render_certificate(membership, absolute_assets: bool = False) -> dict:
	"""Render this membership's certificate through the shared render service.

	Returns whatever `render_template()` returns — template key, category,
	format, subject and body. This module adds no formatting of its own.

	`absolute_assets` is passed straight through to `context_for`; it is the PDF
	path asking for asset references it can actually resolve.
	"""
	return render.render_template(
		template_key_for(membership), context_for(membership, absolute_assets=absolute_assets)
	)


def template_key_for(membership) -> str:
	"""The template this membership's type renders through, refusing an unset one.

	Its own function because two callers need the same refusal — the API's
	rendered-HTML path and the PDF path — and a type with no template configured
	must fail the same way for both.
	"""
	from vmmsx.member.services import membership as membership_service

	membership_type = membership_service.type_of(membership)

	if not membership_type.template_key:
		frappe.throw(
			_(
				"Membership type {0} has no certificate template configured. Point its"
				" Certificate Template at a {1}."
			).format(frappe.bold(membership_type.membership_type_name), frappe.bold("VMMS Template")),
			frappe.MandatoryError,
			title=_("No Certificate Template"),
		)

	return membership_type.template_key


# --- the PDF --------------------------------------------------------------


def pdf_filename(membership) -> str:
	"""What the downloaded file is called. The opaque docname, never a person.

	A filename lands in a downloads folder, an email attachment and a support
	ticket, and it is the one part of a certificate that travels without its
	contents being opened. Naming it after the membership rather than the member
	keeps somebody's name out of all three.
	"""
	return f"membership-certificate-{membership.name}.pdf"


def pdf_for(membership, user: str | None = None) -> bytes:
	"""This membership's certificate as PDF bytes. Gated, then rendered.

	The order is the whole of the security here, and it is deliberate:

	1. **The gate first** — `assert_printable`. A refused caller never reaches a
	   template, never causes a file to be read, and never costs a PDF render.
	2. **Then the state check**, through `assert_active`: a membership that is
	   not active has no certificate, because a certificate is evidence of
	   membership and one issued for an application still under review would be
	   evidence of nothing.
	3. **Then render**, with `absolute_assets=True`, which is the only difference
	   between this and what the HTML endpoint returns.

	Nothing is stored. No File row is created, nothing is written to disk, and
	the bytes are handed straight back for the response to stream — a certificate
	is derived from the membership every time it is asked for, so a stored copy
	would only ever be a second answer waiting to go stale.
	"""
	assert_printable(membership, user)
	assert_active(membership)

	rendered = render_certificate(membership, absolute_assets=True)

	return get_pdf(rendered["body"])


def assert_active(membership) -> None:
	"""Refuse a certificate for a membership that is not active.

	Shared by the HTML and PDF paths so the two cannot come to disagree about
	what a certificate is evidence of.
	"""
	from vmmsx.member.services import membership as membership_service

	if membership.membership_status == membership_service.STATUS_ACTIVE:
		return

	frappe.throw(
		_("{0} is {1}. A certificate is issued for an active membership.").format(
			frappe.bold(membership.name), frappe.bold(_(membership.membership_status))
		),
		frappe.ValidationError,
		title=_("Not Active"),
	)
