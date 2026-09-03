# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The Member API — explicit DTOs, and nothing that reaches a gateway.

Every endpoint names its arguments, checks permission through Frappe (which
brings core's geo scoping with it), and returns a dict this module builds field
by field. None of them returns a Document or a raw query result.

Approving a membership is deliberately **not** here. A routed membership is
acted on through `vmmsx/api/approvals.py`, the generic engine endpoint, because
the person-gate lives there and a second door into the same decision would be a
second place to get it wrong.

Two endpoints here are about a person rather than a record, and both take their
answer from the session rather than from an argument. `my_memberships()` accepts
nothing at all — a possessive endpoint that let a caller name the person would
be a general-purpose reader with a misleading name. `download_certificate()`
does take a membership, and gates it on who the caller *is*: the member it
belongs to, resolved through core's `Red Profile.user`, or whoever holds the
role the society configured.

**The holder reaches their own records without a doctype-read role.** `_readable`
below admits two callers: the person the membership belongs to, and anybody the
ordinary permission layer already allows. Before that, `download_certificate`
asked `check_permission("read")` first, so a member who was plainly entitled to
their own certificate — and whom `certificate.may_print` would have admitted —
was refused at the door by core's geo scoping, which fails closed for somebody
holding no scope role. That is correct for the register and wrong for the person
in it. The bypass is an identity match, not a scope, so it widens access to
exactly one person for exactly their own rows.
"""

import frappe

from vmmsx.member.services import certificate
from vmmsx.member.services import member as member_service
from vmmsx.member.services import membership as membership_service
from vmmsx.member.services import renewal as renewal_service
from vmmsx.registration.services import declarations, questions

MEMBERSHIP_DOCTYPE = "VMMS Membership"
MEMBER_DOCTYPE = "VMMS Member"


@frappe.whitelist()
def apply_for_membership(
	red_profile: str,
	membership_type: str,
	geo_node: str,
	membership_source: str | None = None,
	proof_attachment: str | None = None,
) -> dict:
	"""Create a membership and put it into motion.

	The Geo Node is required here, at creation, and not filled in later — ACC-02
	is a property of the record existing, not a step in a workflow.

	`membership_source` and `proof_attachment` are how a clerk enrols a
	pre-rollout member: somebody who paid before this system existed and has no
	gateway transaction to confirm. Left unset, a membership is the ordinary
	Gateway-sourced kind; the doctype's own `validate()` refuses a Proof source
	that names an auto-on-payment type or carries no attachment.
	"""
	frappe.has_permission(MEMBERSHIP_DOCTYPE, ptype="create", throw=True)

	member = member_service.ensure(red_profile)

	values = {
		"doctype": MEMBERSHIP_DOCTYPE,
		"member": member.name,
		"membership_type": membership_type,
		"geo_node": geo_node,
	}

	if membership_source:
		values["membership_source"] = membership_source

	if proof_attachment:
		values["proof_attachment"] = proof_attachment

	membership = frappe.get_doc(values)
	membership.insert()

	return membership_service.submit(membership)


@frappe.whitelist()
def verify_membership_proof(
	membership: str,
	proof_verified_start_date: str | None = None,
	proof_verified_expiry_date: str | None = None,
) -> dict:
	"""Record the dates an approver read off the uploaded evidence.

	**Verifying is not deciding, which is why this is here and approving is not.**
	The module docstring says approving a membership lives in `api/approvals.py`
	because the person-gate lives there and a second door into the same decision
	would be a second place to get it wrong. That argument is about the
	*decision*. Reading a date off a document and writing it down is a fact about
	the membership, like a receipt number or an attachment, and it belongs with
	the rest of them.

	It is also deliberately a **separate act from the approval**, in the ordinary
	order somebody actually works: open the proof, look at it, write down what it
	says, then decide. Folding the dates into the decide call would mean a
	coordinator could only correct a typo by re-deciding.

	`_writable` is the gate — the ordinary permission layer, which brings core's
	geo scoping with it, so this reaches only memberships the caller could already
	edit. The holder bypass in `_readable` is deliberately not used: this is the
	society writing down what it checked, and the one person who must never be
	able to do it is the applicant.
	"""
	from vmmsx.member.services import proof

	document = _writable(membership)

	if not membership_service.is_proof(document):
		frappe.throw(
			frappe._("There is nothing to verify on a membership that was paid for through the gateway."),
			frappe.ValidationError,
			title=frappe._("Not A Proof Of Membership"),
		)

	proof.verify(document, proof_verified_start_date, proof_verified_expiry_date)
	document.save()

	return membership_service.status(document)


@frappe.whitelist()
def geo_node_levels() -> dict:
	"""Geo Levels a new membership may anchor to (ACC-03), for the geo_node picker.

	Two configuration surfaces answer "which level" for a membership today, and
	both are enforced independently: National Society Settings'
	`vmms_membership_anchor_level` in `VMMSMembership.validate()`, on every
	save, and the governing `VMMS Approval Workflow`'s `allowed_anchor_levels`
	in `engine.submit()`, at Submit. A picker built from only one of them could
	still offer a level the other one goes on to reject, so this intersects
	them: whatever `levels` names is acceptable to *both* checks, and a Link
	field filtered to it can never pick-then-reject either way.

	`unconstrained` is True only when neither surface narrows it. Where both
	narrow it but agree on nothing at all, `levels` is empty — a
	misconfiguration a society has to resolve, and not this endpoint's place to
	guess past.
	"""
	from vmmsx.approvals.services import config as approval_config
	from vmmsx.member.services import society

	workflow_levels = approval_config.allowed_anchor_levels_for(MEMBERSHIP_DOCTYPE)
	settings_level = society.membership_anchor_level()

	if workflow_levels and settings_level:
		levels = [settings_level] if settings_level in workflow_levels else []
	elif workflow_levels:
		levels = workflow_levels
	elif settings_level:
		levels = [settings_level]
	else:
		levels = []

	return {"levels": levels, "unconstrained": not levels}


@frappe.whitelist()
def renew_membership(membership: str, membership_type: str | None = None) -> dict:
	"""Renew a lapsed membership: a NEW record for the same member and branch.

	Takes the *prior* membership's name and nothing that could name a person —
	`member` is never an argument here, only read off the prior record inside
	`renewal_service.renew` once entitlement is established. Entitlement is the
	same `_readable` gate every other endpoint here uses: the caller is the
	membership's own holder, or reaches it through the ordinary permission
	layer as an authorised coordinator within their geo scope. Either way the
	session decides who is asking; nobody can pass a member in and get a
	different answer.

	`membership_type` is optional and lets the renewal choose a different type
	than the one it replaces — a member moving from an ordinary to a life
	membership, say. Left unset, the renewal carries the same type forward.
	"""
	prior = _readable(membership)

	return renewal_service.renew(prior, membership_type=membership_type)


# --- the coordinator's acts -----------------------------------------------
#
# Two verbs over a membership's standing, wrapping services in
# `member/services/membership.py` that were already idempotent and already owned
# the write. `membership_status` is derived and `read_only` on the doctype, so
# there was no field to expose and no button anywhere: cancelling a membership
# was a bench console call.
#
# **Activation is deliberately absent.** It is not a verb somebody performs —
# `membership.try_activate()` is a predicate re-evaluated from `on_update`,
# asking whether approval and payment are both settled. An endpoint that forced
# it would be a way around both, which is exactly what MEM-02 exists to prevent.


@frappe.whitelist()
def cancel_membership(name: str, reason: str | None = None) -> dict:
	"""Withdraw a membership before or after activation. Idempotent."""
	return membership_service.cancel(_writable(name), reason)


@frappe.whitelist()
def expire_membership(name: str) -> dict:
	"""Close a membership whose validity has actually run out. Idempotent.

	The daily `expire_lapsed` sweep applied to one record now rather than
	tonight — and the guard below is what makes that description true rather
	than approximately true.

	**The date test is the sweep's, not the service's.** `membership.expire()`
	moves any Active membership to Expired; what stops the sweep closing a
	lifetime membership is a `valid_to is set` filter in *its own query*. So an
	endpoint calling the service directly would be a way to end a life
	membership, or to close a current one months early, without the reason that
	`cancel_membership` records and without anything in the history saying who
	decided it. `is_lapsed` is asked here instead: it is the same predicate the
	rest of the module derives standing from, and it answers False for a
	membership with no end date, which is exactly the case the sweep excludes.

	A coordinator who means to end a membership early wants `cancel_membership`,
	which is the verb that carries a reason.
	"""
	membership = _writable(name)

	if not membership_service.is_lapsed(membership):
		frappe.throw(
			frappe._("That membership has not run out, so it cannot be expired. Cancel it instead."),
			frappe.ValidationError,
			title=frappe._("Not Expired"),
		)

	return membership_service.expire(membership)


@frappe.whitelist()
def get_membership(name: str) -> dict:
	"""Where a membership stands. The status DTO, and who may move it.

	`can_act` rides along for the same reason it does on the dossier: the desk
	form draws its buttons from this one read and must not have to ask a second
	question to know which of them to draw. It is a fact about the caller rather
	than about the membership, which is why it is added here and not inside
	`membership_service.status()`.

	This one names the membership, so the flag is the *per-document* answer —
	exactly what `cancel_membership` and `expire_membership` will check when a
	button is pressed, geo scoping included.
	"""
	membership = _readable(name)

	return {**membership_service.status(membership), "can_act": _can_act(membership)}


@frappe.whitelist()
def get_review(name: str, as_of: str | None = None) -> dict:
	"""The whole of what an approver reads before deciding one membership.

	The membership counterpart of `api/volunteer.py::get_decision`, and it exists
	because the review queue had no way to show whose membership it was
	deciding: the volunteer application had a decision view and the membership
	did not, so an approver was offered approve and decline over a docname.

	**Ordinary read permission on the membership, through `_readable`.** Not a
	second door into one: whoever may open the membership may read this, and
	whether they may *decide* it is a different question the approval engine
	answers per document — `api/approvals.py::decide` re-asks it when a button is
	pressed, and holding a role has never been the same as being this
	membership's approver.
	"""
	from vmmsx.member.services import review

	return review.decision_dto(_readable(name), as_of=as_of)


@frappe.whitelist()
def get_certificate(name: str) -> dict:
	"""Render this membership's certificate from its type's configured template.

	Gated the same way the download is: a certificate belongs to the member it
	names, and reading its HTML is the same disclosure as printing it. Refused
	for a membership that is not active — a certificate is evidence of
	membership, and issuing one for an application still under review would make
	it evidence of nothing.

	Assets stay site-relative here. This body is for a browser on this site,
	which resolves `/files/...` perfectly well; the PDF path is where that
	becomes a problem and where it is solved.
	"""
	membership = _readable(name)

	certificate.assert_printable(membership)
	certificate.assert_active(membership)

	return certificate.render_certificate(membership)


@frappe.whitelist()
def download_certificate(membership: str):
	"""The certificate as a PDF, streamed to the caller. Returns nothing.

	Frappe's file-download contract: set `filename`, `filecontent` and `type` on
	the response and return None, and the framework sends the bytes with the
	right headers. No File row is created and nothing touches disk — see
	`certificate.pdf_for`, which explains why a certificate is never stored.

	The gate runs inside `pdf_for`, before any rendering, so a caller who may not
	have this certificate cannot make the server build one.
	"""
	doc = _readable(membership)
	pdf = certificate.pdf_for(doc)

	frappe.local.response.filename = certificate.pdf_filename(doc)
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"


@frappe.whitelist()
def download_my_certificate(membership: str | None = None):
	"""The logged-in member's own certificate, as a PDF. Returns nothing.

	The possessive companion to `download_certificate`, and the reason the self
	service workspace can carry a shortcut at all: a workspace shortcut is a
	static URL, and it cannot know a membership's name. This one answers from the
	session, exactly as `my_memberships` does.

	`membership` is optional and is a *narrowing*, never a widening: it selects
	among the caller's own active memberships and is refused for anybody else's,
	because it goes through the same gate as everything else here. Somebody
	holding one active membership needs no argument at all; somebody holding
	several is told so and told which, rather than being handed whichever came
	back first.
	"""
	active = _my_active_memberships()

	if not active:
		frappe.throw(
			frappe._(
				"You have no active membership. A certificate is issued for a membership that is active."
			),
			frappe.DoesNotExistError,
			title=frappe._("Nothing to Print"),
		)

	if membership:
		if membership not in active:
			# Refused as "not yours" rather than "not active", and deliberately:
			# distinguishing the two would let a caller learn which membership
			# names exist by watching the message change.
			frappe.throw(
				frappe._("That is not one of your active memberships."),
				frappe.PermissionError,
				title=frappe._("Not Your Certificate"),
			)

		chosen = membership
	elif len(active) == 1:
		chosen = active[0]
	else:
		frappe.throw(
			frappe._("You hold {0} active memberships. Ask for the one you want: {1}.").format(
				len(active), ", ".join(active)
			),
			frappe.ValidationError,
			title=frappe._("Which Membership"),
		)

	return download_certificate(chosen)


def _my_active_memberships() -> list[str]:
	"""The logged-in person's active memberships, by name. Empty for a visitor."""
	member = _my_member()

	if not member:
		return []

	return member_service.memberships(member, status=membership_service.STATUS_ACTIVE)


@frappe.whitelist()
def get_member(name: str) -> dict:
	"""Who a member is — assembled from Red Profile at the moment of asking.

	Owner-bypassed on the same rule as a membership: the person this record is
	about may read it without holding a role that reads everybody's.
	"""
	return member_service.profile_dto(_readable_member(name))


@frappe.whitelist()
def get_dossier(name: str, as_of: str | None = None) -> dict:
	"""Everything a coordinator needs about one member, in one read.

	The complete current picture plus the history behind it, so that deciding
	about somebody does not mean opening their Red Profile in one tab, each of
	their memberships in another, the payments app for a receipt and the
	approval trail for who verified it. Four blocks:

	    identity     who they are, live from core's Red Profile
	    standing     what they are — the derived status, and the branches
	                 carrying it
	    memberships  what they hold, at every branch this caller may see, each
	                 with its validity, its payment and its certificate
	    history      how they came to hold it — the approval trail, flattened

	**One call rather than four**, and that is not only about round trips: lapse,
	effective status and renewability are all comparisons against a date, and
	blocks compared against four different instants can contradict each other. A
	page showing a membership as lapsed beside a renew button that said "not yet"
	— because the two asked either side of midnight — would be wrong in the way
	that is hardest to notice. `as_of` is resolved once inside `dossier.build`
	and every derived answer on the screen is answered as at that moment.

	**Composed, never merged.** Each block is the DTO its own service builds,
	under its own key, so nothing re-derives anything and no block can quietly
	overwrite a field of another's.

	Permission is the ordinary read check on the member, through
	`_readable_member` — Frappe's roles, plus the holder's own bypass. The
	memberships block applies core's geo scoping on top of that, because
	`VMMS Membership` is scopeable and `VMMS Member` is not; see
	`dossier._visible_memberships`, which is where that floor is.
	"""
	from vmmsx.api import person
	from vmmsx.member.services import dossier

	member = _readable_member(name)

	return {
		**dossier.build(member, as_of=as_of),
		# Which of the society's registers this person is in — so the page can
		# say "also a volunteer" instead of sending a membership clerk to search
		# the other register for the name. Added here rather than inside `build`
		# for the same reason `can_act` is: the member module must not know the
		# volunteer module exists. See `api/person.py`.
		"registers": person.registers(member.red_profile),
		# Added here rather than inside `build`, because it is not a fact about
		# this member: it is a fact about who is asking, and authority in this
		# app is decided at the boundary rather than in a service. A surface
		# draws its buttons from this and decides nothing itself; see
		# `_can_act`. The holder reading their own dossier gets `False`, which
		# is the `_readable` / `_writable` split showing through to the screen.
		"can_act": _can_act(),
	}


@frappe.whitelist()
def find_members(
	geo_node: str | None = None,
	status: str | None = None,
	membership_type: str | None = None,
	current_only: bool = False,
	search: str | None = None,
	as_of: str | None = None,
	limit: int = 100,
	offset: int = 0,
) -> dict:
	"""The member register, **inside the caller's own scope**.

	The question a membership office actually asks: who are the members here,
	at which branch, current or lapsed, and until when — answered with people's
	names rather than with docnames.

	**Scope is not a filter this endpoint applies; it is the floor it stands
	on.** `register.search()` ends in `frappe.get_list`, which runs core's
	permission query condition for `VMMS Membership`. Every argument here
	narrows that result and none of them widens it, so a coordinator cannot
	reach a member outside their geo scope by naming a branch, a type or a
	status. Returns explicit rows built field by field, never the documents.
	"""
	from vmmsx.member.services import register

	return register.search(
		geo_node=geo_node,
		status=status,
		membership_type=membership_type,
		# By a person's name, their member docname or the membership's own —
		# see `register._matches`. It narrows the same scoped read.
		search=search,
		current_only=frappe.parse_json(current_only) if isinstance(current_only, str) else current_only,
		as_of=as_of,
		limit=limit,
		# Applied after `current_only`, inside the service. Paging in the query
		# would page through the unfiltered result and skip people between
		# pages; `register.search` states the argument in full.
		offset=offset,
	)


@frappe.whitelist()
def membership_type_pricing(membership_type: str | None = None) -> dict:
	"""What a membership type costs, for the form that is about to charge it.

	The walkthrough's papercut: somebody choosing a membership type on the desk
	was choosing between opaque names with no indication that one of them costs
	money. The fee is on the type record and was simply never shown at the
	moment of the decision.

	Read live on every call, because a fee is configuration a society changes
	and a stale price on a form is worse than no price. The currency falls back
	to the society's own through `payment.fee()`, so nothing here assumes one.

	`free` is reported as its own answer rather than left to a caller comparing
	an amount to zero: a free membership is a different thing to say on a form
	than "0.00", and a society that charges nothing should not have its forms
	quietly rendering a currency symbol beside a zero.

	Called with no type — the ordinary state of a form nobody has filled in yet
	— it answers `known: False` rather than throwing, so the client needs no
	special case.

	It carries the type's `description` and its active `benefits` for the same
	reason it carries the fee: a plan card that shows a price and nothing else
	is asking somebody to choose between names. Every word of both is the
	society's, written on the type record.
	"""
	from vmmsx.member.services import membership as membership_service
	from vmmsx.member.services import payment as payment_service

	if not membership_type:
		return {"known": False}

	if not frappe.db.exists("VMMS Membership Type", membership_type):
		return {"known": False}

	record = frappe.get_cached_doc("VMMS Membership Type", membership_type)
	charge = payment_service.fee(record)

	return {
		"known": True,
		"membership_type": record.name,
		"membership_type_name": record.membership_type_name,
		# Who the type is for, in the society's own words. The reference design
		# puts an eligibility line under the price ("open to ages 18-30"), and
		# that line is *this field* — a society writes it, because no age rule
		# exists on this doctype and inventing one in a browser bundle would be a
		# second answer nothing enforces.
		"description": record.description,
		"amount": charge["amount"],
		"currency": charge["currency"],
		"free": not payment_service.is_payable(record),
		"duration_days": record.duration_days,
		# What the type carries, which is the whole of what a chooser is choosing
		# between. Active rows only and in table order: a society orders its own
		# benefits, and a retired one is not part of the offer.
		"benefits": [
			{
				"key": row.benefit_key,
				"label": row.benefit_name or row.benefit_key,
				"description": row.description,
			}
			for row in record.benefits
			if row.is_active
		],
		# How long it lasts is the other half of what the form is choosing, and
		# for a lifetime type the honest answer is not a number of days. Said as
		# its own field so the form states it rather than rendering "0 days".
		"is_lifetime": membership_service.is_lifetime(record),
		"is_active": bool(record.is_active),
		# Whether a person will have to wait for somebody, which is the other
		# thing worth knowing at the moment of choosing. Asked of the service
		# that dispatches on it rather than by reading `approval_mode` here.
		"requires_approver": _requires_approver(record),
	}


@frappe.whitelist()
def membership_types() -> dict:
	"""Every membership type a person may currently join, priced.

	The list the pricing endpoint above always assumed the caller already had.
	A desk form gets it from a Link field's own query; a frontend has no such
	thing, and querying `VMMS Membership Type` directly from the browser would
	need read permission on a configuration doctype for everybody who might ever
	join. So the list is served here, built from the same
	`membership_type_pricing` that answers for one, which is what stops a price
	on a chooser from ever disagreeing with the price on the confirmation.

	Inactive types are excluded rather than flagged: a type a society has
	retired is not an option, and offering one greyed out invites the question
	of why.
	"""
	keys = frappe.get_all(
		"VMMS Membership Type",
		filters={"is_active": 1},
		pluck="name",
		order_by="fee_amount asc, membership_type_name asc",
	)

	return {
		"types": [membership_type_pricing(key) for key in keys],
		# The society's own questions for this registration. Served beside the
		# types because the wizard draws both in one pass, and a second round trip
		# for a list that is usually empty is a spinner for nothing.
		"questions": questions.asked_on(MEMBERSHIP_DOCTYPE),
		# What somebody proving an existing membership must agree to, with the
		# version and the exact wording they will be agreeing to — the same shape
		# the volunteer wizard reads, from the same service.
		#
		# Served here rather than from an endpoint of its own for the reason above
		# it, and served on this endpoint rather than a proof-only one because the
		# plan cards and the proof form are the same screen: the person choosing a
		# plan is one click from the form that needs this.
		"declarations": declarations.shown_on(MEMBERSHIP_DOCTYPE),
		# How this society will take the money, so the chooser and the way of
		# paying arrive together. Served here for the reason the questions above
		# it are: the wizard draws both in one pass, and a society that charges
		# nothing gets an empty list and no question about it.
		"payment_methods": payment_methods()["methods"],
	}


@frappe.whitelist()
def payment_methods() -> dict:
	"""The ways this society will take a membership fee.

	**Configuration, and deliberately readable by anybody who may join.** The
	rows come from `member/services/methods.py`, which intersects what the
	society ticked with what `onerc_payments` reports as active and able to take
	money in. Nothing here is a secret: it is the list of buttons on the form
	that asks somebody to pay, and a person cannot choose a way of paying they
	are not shown.

	What is *not* here is any credential, any shortcode and any callback URL.
	Those live in the payments app's own settings and this endpoint has never
	seen them — the DTO is built field by field for exactly that reason.

	Empty is ordinary and means one of three things, none of them an error: the
	payments app is not installed, the society has switched every method off, or
	nothing on this site charges a fee. A form reading this shows no payment
	question at all rather than an empty picker.
	"""
	from vmmsx.member.services import methods

	return {
		"methods": [
			{
				"gateway": row["gateway"],
				"label": row["label"],
				"description": row["description"],
				"instructions": row["instructions"],
			}
			for row in methods.offered()
		]
	}


def _requires_approver(membership_type) -> bool:
	"""Whether this type routes to a person, asked of MEM-02's own service."""
	from vmmsx.member.services import approval

	return approval.requires_approver(membership_type)


@frappe.whitelist()
def set_member_notes(name: str, notes: str | None = None) -> dict:
	"""The branch's own note about this member.

	The twin of `api/volunteer.py::set_volunteer_notes`, and it draws the same
	line: `VMMS Member.notes` has been on the doctype since it was written, no
	DTO carried it, and no screen could write one — so a note made at the desk
	was invisible on the register and a coordinator working from the console
	could not make one at all.

	**`_writable_member`, not `_readable_member`.** The read helper admits the
	person the record is about, which is right for reading their own standing
	and wrong here: a note a coordinator makes about somebody is not a note that
	person may rewrite.

	Blank clears it, deliberately.
	"""
	member = _writable_member(name)
	member.notes = (notes or "").strip()
	member.save()

	return {"member": member.name, "notes": member.notes}


def _writable_member(name: str):
	"""Load a member record the caller may **act on**, as a coordinator.

	The ordinary permission layer and nothing else — no holder bypass. The
	distinction is the one `api/volunteer.py::_writable` sets out at length: a
	person is entitled to see their own record and is not entitled to write the
	branch's notes about themselves.
	"""
	doc = frappe.get_doc(MEMBER_DOCTYPE, name)
	doc.check_permission("write")

	return doc


def _readable_member(name: str):
	"""Load a member record the caller is allowed to see. Two ways to be allowed.

	1. **It is theirs.** The session user is the login on this member's Red
	   Profile. A person is entitled to their own record, and requiring a
	   society to hand every member a role that reads the whole register in
	   order for them to see themselves in it would grant far more than it
	   withholds.
	2. **The ordinary permission layer**, which is Frappe's roles.

	**Recognised through `Red Profile.user`, never through `owner`.** They are
	different people: a member registered at a branch counter is owned by the
	clerk who typed it, so gating on `owner` would give the clerk a self-service
	view of everybody they ever enrolled and give the member nothing.

	**`VMMS Member` is deliberately not geo-scopeable**, and this is the one
	place that matters. It holds no Geo Node and could not: a person is not at a
	place, their membership is. So the geo floor is applied where the geo lives
	— on the memberships, inside the dossier — rather than pretended at here.
	"""
	from vmmsx.member.services import identity

	member = frappe.get_doc(MEMBER_DOCTYPE, name)
	user = frappe.session.user

	if user and user != "Guest" and identity.user_of(member) == user:
		return member

	member.check_permission("read")

	return member


@frappe.whitelist()
def my_memberships() -> list[dict]:
	"""Every membership held by the logged-in person, across every branch.

	**Derived from the session on every call, and it takes no arguments.** That
	is the point of the endpoint rather than an implementation detail: a
	`my_memberships(member)` that accepted a name would be an endpoint for
	reading *anybody's* memberships wearing a possessive name, and the check
	stopping that would be one more thing to get right. There is nothing to get
	right here — the caller cannot name somebody else, because the caller cannot
	name anybody. This is the shape `api/approvals.py::my_queue` uses.

	The chain is `User -> Red Profile.user -> VMMS Member.red_profile ->
	VMMS Membership.member`, and each link is unique or indexed in core's or this
	app's schema. Any break in it returns an empty list rather than an error:
	somebody logged in who is not a member of the society is an ordinary visitor,
	not a failure.

	**Every membership, at every geo node.** One person may hold memberships at
	several branches at once — that is a supported state, not an anomaly — so
	nothing here filters by node, takes a first row, or assumes a single answer.
	"""
	from frappe.utils import getdate, today

	member = _my_member()

	if not member:
		return []

	# Resolved once for the whole list rather than per row. Two memberships
	# derived either side of midnight would disagree about which of them had
	# lapsed, on one screen, for one person — the same rule the dossier follows.
	as_of = getdate(today())
	rows = []

	for name in member_service.memberships(member):
		membership = frappe.get_doc(MEMBERSHIP_DOCTYPE, name)
		rows.append(
			{
				**membership_service.status(membership),
				# Whether *this* caller could print it, asked of the same gate
				# the download uses rather than re-derived from the status. A UI
				# showing a button the server would refuse is worse than no
				# button.
				"certificate_available": certificate.may_print(membership)
				and membership.membership_status == membership_service.STATUS_ACTIVE,
				# Whether this membership has lapsed far enough to renew — the
				# "button only after expiry" behaviour, computed server-side so a
				# UI can show the renew action exactly when it would succeed.
				"renewable": renewal_service.is_renewable(membership, as_of=as_of),
			}
		)

	return rows


def _my_member() -> str | None:
	"""The VMMS Member record of whoever is logged in, or None.

	Two hops, both of them a lookup on a unique column: the Red Profile carrying
	this login, and the member satellite hanging off that profile. Neither is
	permitted to be ambiguous — core makes `Red Profile.user` unique and this app
	makes `VMMS Member.red_profile` unique — so there is no ordering or
	tie-breaking to specify.

	The Guest session is refused outright rather than being allowed to fall
	through to a profile lookup that would almost certainly find nothing: relying
	on "almost certainly" for an unauthenticated caller is not a check.
	"""
	user = frappe.session.user

	if not user or user == "Guest":
		return None

	profile = frappe.db.get_value("Red Profile", {"user": user}, "name")

	if not profile:
		return None

	return frappe.db.get_value(MEMBER_DOCTYPE, {"red_profile": profile}, "name")


def _readable(name: str):
	"""Load a membership the caller is allowed to see. Two ways to be allowed.

	1. **It is theirs.** The session user is the login on the member's Red
	   Profile. No role, no geo assignment, nothing else required: a person is
	   entitled to their own membership, and requiring a society to hand every
	   member a doctype-read role in order for them to see it would grant vastly
	   more than it withholds.
	2. **The ordinary permission layer**, which is Frappe's roles *and* core's
	   geo scoping, because `VMMS Membership` is registered as scopeable.

	**The holder is recognised through `Red Profile.user`, never through
	`owner`.** They are different people and often are: a membership registered
	at a branch counter is owned by the clerk who typed it. Gating on `owner`
	would hand the clerk every certificate they ever entered and deny the member
	their own. This is the same rule `certificate.owner_user()` states, and it is
	deliberately asked of the same function so the two cannot drift.

	**The bypass only ever widens, and only ever to one person.** It admits
	exactly the session user, for exactly the memberships that are theirs, and
	changes nothing about who else can read what. Core's scoping is untouched:
	nobody sees anybody else's record through this door, because the condition is
	an identity match rather than a scope.
	"""
	membership = frappe.get_doc(MEMBERSHIP_DOCTYPE, name)

	if _is_holder(membership):
		return membership

	membership.check_permission("read")

	return membership


def _writable(name: str):
	"""Load a membership the caller may **act on**, as a coordinator.

	The ordinary permission layer and nothing else: Frappe's roles plus core's
	geo scoping, because `VMMS Membership` is registered as scopeable.

	**Deliberately not `_readable`, and that is the whole point of it being a
	second function.** `_readable` admits the person the membership belongs to,
	which is right for reading a certificate and wrong for every verb behind
	this door. A member is entitled to see their own standing; they are not
	entitled to cancel their own membership outside whatever process the society
	has for that. Routing the acts through the read helper would have handed
	them exactly that, quietly, and it would have looked like reuse.

	**The gate is the membership, never the member.** `VMMS Member` is
	deliberately not geo-scopeable — a person is not at a place, their
	membership is — so gating an act on the member record would drop core's
	scoping entirely. Both verbs here act on memberships, so there is nothing to
	reconcile: the floor is where the geo is.

	Mirrors `api/tasks.py::_writable` and `api/volunteer.py::_writable`.
	"""
	membership = frappe.get_doc(MEMBERSHIP_DOCTYPE, name)
	membership.check_permission("write")

	return membership


def _can_act(membership=None) -> bool:
	"""May this caller work the acts above?

	`membership` is passed wherever the caller has one in hand, and then the
	question asked is exactly the one `_writable` enforces: Frappe's roles *and*
	core's geo scoping applied to that document.

	**Without one it is the doctype-level question, and that is weaker on
	purpose.** The member dossier draws a person who may hold memberships at
	several branches, and one flag cannot answer for all of them — a coordinator
	may act at one branch and not the next. So the dossier's flag means "this
	caller is somebody who acts on memberships at all", which is what decides
	whether the controls are drawn, and the endpoint re-asks per membership when
	one is pressed. A person shown a button they turn out not to hold for that
	branch gets a refusal rather than a silent no-op; drawing nothing for
	everybody would have been worse for the far commoner case.

	The flag decides what is *painted*; the endpoint is what holds. Same shape as
	`api/volunteer.py::_can_act` and as `can_edit` on a content surface.
	"""
	if membership is not None:
		return bool(frappe.has_permission(MEMBERSHIP_DOCTYPE, ptype="write", doc=membership))

	return bool(frappe.has_permission(MEMBERSHIP_DOCTYPE, ptype="write"))


def _is_holder(membership) -> bool:
	"""Is the session user the person this membership belongs to?

	The Guest session is refused before anything is looked up: an unauthenticated
	caller is nobody, and letting one fall through to a comparison that would
	"almost certainly" not match is not a check.
	"""
	user = frappe.session.user

	if not user or user == "Guest":
		return False

	return certificate.owner_user(membership) == user


# How many scoped memberships the register summary will read before it stops.
# A ceiling on work, not a page size: the figures below are derived per row
# because "current" is a comparison against a date and no query can be asked it.
_SUMMARY_CEILING = 20_000

# How soon a membership has to fall due to count as a renewal approaching.
_RENEWAL_WINDOW_DAYS = 60


@frappe.whitelist()
def register_summary(as_of: str | None = None) -> dict:
	"""The active member register's own figures, **inside the caller's scope**.

	Four aggregates over the whole scoped register rather than over a page of
	it, which is the entire reason this exists — a screen that labels its
	current page's length as "active memberships" will be believed, and will be
	wrong on every page after the first.

	    active       memberships that are current as at `as_of`
	    lifetime     of those, the ones whose type never expires
	    term         of those, the ones that do — the renewable ones
	    renewing     of the term ones, those falling due within the window

	**Life and term are read off `VMMS Membership Type.is_lifetime`, never off a
	type's name.** A society names its own membership types; "Annual" and "Life"
	are words one society happens to use and another does not, and code that
	compared them would break at the first society that called theirs something
	else. The flag is the fact.

	**Scope is the floor, not a filter.** `frappe.get_list` runs core's
	permission query condition for `VMMS Membership`; `frappe.get_all` is used
	below only to read the *type* vocabulary, which is configuration rather than
	somebody's record.

	`capped` says the read hit its ceiling, and a screen must present the figures
	as a floor rather than as a total when it does.
	"""
	from frappe.utils import add_days, getdate, today

	from vmmsx.member.services import membership as membership_service

	moment = getdate(as_of or today())
	horizon = add_days(moment, _RENEWAL_WINDOW_DAYS)

	rows = frappe.get_list(
		MEMBERSHIP_DOCTYPE,
		filters={"membership_status": "Active"},
		fields=["name", "membership_type", "valid_to", "membership_status"],
		limit_page_length=_SUMMARY_CEILING + 1,
	)

	capped = len(rows) > _SUMMARY_CEILING
	rows = rows[:_SUMMARY_CEILING]

	lifetime = _lifetime_types({row.get("membership_type") for row in rows})
	current = [row for row in rows if membership_service.is_current(frappe._dict(row), moment)]

	life = [row for row in current if row.get("membership_type") in lifetime]
	term = [row for row in current if row.get("membership_type") not in lifetime]

	return {
		"as_of": moment,
		"active": len(current),
		"lifetime": len(life),
		"term": len(term),
		"renewing": len(
			[
				row
				for row in term
				if row.get("valid_to") and moment <= getdate(row["valid_to"]) <= horizon
			]
		),
		"renewal_window_days": _RENEWAL_WINDOW_DAYS,
		"capped": capped,
	}


def _lifetime_types(keys: set) -> set:
	"""Which of these membership types never expire.

	Read from the type vocabulary, which is society configuration rather than
	anybody's record — the same footing `register._type_names_for` reads names
	on, and the reason this one read is not scoped.
	"""
	keys = {key for key in keys if key}

	if not keys:
		return set()

	return set(
		frappe.get_all(
			"VMMS Membership Type",
			filters={"name": ("in", sorted(keys)), "is_lifetime": 1},
			pluck="name",
		)
	)
