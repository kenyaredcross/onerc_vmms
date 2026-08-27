# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The coordinator's complete view of one member, assembled at one instant.

What this module is for
-----------------------

A `VMMS Member` record is thin by design and must stay that way: it holds a link
to a Red Profile, a derived status and a joining date, and nothing else. That is
correct as a *schema* and useless as a *screen*. A coordinator opening it was
shown a docname where a person should be, and had to visit the Red Profile for
the name, each membership for the branch and dates, the payments app for the
receipt and the approval trail for who verified it — four other places to answer
one question about one person.

This assembles that answer. Nothing here is stored, and nothing here is new
truth: every block is read from the record that already owns it.

One call, one instant
---------------------

`build()` resolves `as_of` **once** and hands the same date to every derivation
below it. That is not a round-trip optimisation, it is a correctness rule: lapse,
effective status, renewability and the member's own standing are all comparisons
against a date, and blocks compared against four different instants can
contradict each other. A screen that showed a membership as lapsed beside a
renew button that said "not yet" — because the two asked either side of midnight
— would be wrong in the way that is hardest to notice and hardest to reproduce.

The rule extends into the nested DTOs, which is where it is easiest to lose: the
`renewable` flag inside each membership row is derived by `renewal.is_renewable`,
which defaults to today if nobody tells it otherwise. It is told otherwise here,
and `member/tests/test_dossier.py` pins that with a test that would pass if the
argument were dropped from the outer call and fail if it were dropped from the
inner one.

Living, historical, and whose record each fact lives on
-------------------------------------------------------

The member module's version of the split `volunteer/services/capabilities.py`
draws, and the answer here is more one-sided than it is there:

    lives on the RED PROFILE        lives on the MEMBERSHIPS
    (core's, read live)             (the operational records, read live)
    ------------------------        ------------------------------------
    name, photo, contact            branch, type, validity, status
    gender, date of birth           payment, receipt, proof
    citizenship, residence          the approval trail
    home area

    lives on the MEMBER
    -------------------
    the derived status, and the date they first joined

**Almost nothing is the member's own**, and that is the finding rather than an
omission: a member *is* their memberships. So this module copies nothing onto
`VMMS Member` and reads everything through the service that owns it. Correct
somebody's phone number on their Red Profile, or a branch's name in the geo
tree, and every member screen in the society is right on next open, because
there is nothing anywhere to go and update.

Scope is the floor here too
---------------------------

The memberships block ends in `frappe.get_list`, so core's geo scoping applies
to it exactly as it applies to the register in `register.py`. A coordinator sees
every branch they are entitled to see and no others, which is what "across all
branches" has to mean for it to be safe to show anybody.

The derived status is deliberately **not** narrowed to that subset. It is
`member_service.derive_status()` — the same function `refresh()` writes the
stored field with, over all of this member's memberships — because that field is
already on the record the caller has just been allowed to open, and deriving a
second, scope-narrowed status here would put two answers to one question on one
screen. See `standing()` below, which says so again where it happens.
"""

import frappe
from frappe.utils import getdate, today

from vmmsx.member.services import certificate
from vmmsx.member.services import member as member_service
from vmmsx.member.services import membership as membership_service
from vmmsx.member.services import payment as payment_service
from vmmsx.member.services import renewal as renewal_service

MEMBERSHIP_DOCTYPE = "VMMS Membership"

# The decision a proof-of-membership verification records. Read from the engine's
# own child rows, never re-derived: the engine writes the word, and a second
# spelling here would be a second vocabulary.
DECISION_APPROVED = "Approved"


def build(member, as_of=None) -> dict:
	"""Everything a coordinator needs about one member, in one read.

	`member` is a loaded, permission-checked document — this function trusts
	nothing about who is asking beyond its caller having handed it one. See
	`api/member.py::get_dossier`, which is where that check happens.

	Composed, never merged: each block is the DTO its own service builds, under
	its own key, so nothing here re-derives anything and no block can quietly
	overwrite a field of another's.
	"""
	as_of = getdate(as_of or today())
	memberships = _visible_memberships(member, as_of)

	return {
		"member": member.name,
		"as_of": as_of,
		"identity": identity_dto(member),
		"standing": standing(member, memberships, as_of),
		"memberships": memberships,
		"history": history(memberships),
	}


# --- who they are ----------------------------------------------------------


def identity_dto(member) -> dict:
	"""The person, read from Red Profile at the moment of asking.

	Everything a coordinator needs to be sure they have the right person in
	front of them, and nothing this app stores. The member record holds no name,
	no contact detail and no `fetch_from`, so this is the only place any of it
	can come from — see `identity.py`, where the readable set is named and the
	widening that produced these fields is justified.

	The Home Area is core's `Red Profile.home_geo_node`: where somebody *lives*,
	which is a fact about the person rather than about their membership. It is
	resolved to a readable path through core's adapter and never confused with a
	membership's own branch, which is a different question answered per
	membership below.
	"""
	from onerc_core.geo.services import adapter

	from vmmsx.member.services import identity

	person = identity.read(member)
	home = person.get("home_geo_node")

	return {
		"member": member.name,
		"red_profile": member.red_profile,
		"full_name": identity.display_name(member),
		"email": person.get("email"),
		"phone": person.get("phone"),
		"gender": person.get("gender"),
		"date_of_birth": person.get("date_of_birth"),
		"preferred_language": person.get("preferred_language"),
		"profile_photo": person.get("profile_photo"),
		"country_of_citizenship": person.get("country_of_citizenship"),
		"citizenship_status": person.get("citizenship_status"),
		"residency_type": person.get("residency_type"),
		"home_geo_node": home,
		"home_geo_path": adapter.get_full_path(home) if home else None,
		"country_of_residence": person.get("country_of_residence"),
		"residence_address": person.get("residence_address"),
	}


# --- what they are ---------------------------------------------------------


def standing(member, memberships: list[dict], as_of) -> dict:
	"""The member's overall status, and the multi-branch picture behind it.

	**Derived by the same function that writes the stored field.**
	`member_service.derive_status()` is what `refresh()` calls, so what a
	coordinator reads here and what the record holds are one answer produced by
	one piece of code, not two that might drift. It is recomputed rather than
	read off the row so that it cannot be stale.

	**Active in one branch and Expired in another means Active**, which is
	`derive_status`'s own rule and not a second one restated here: a person who
	holds a current membership anywhere is a current member of the society. The
	counts below are what make that legible on the screen — a coordinator seeing
	"Active" above two memberships, one of which plainly expired last year,
	should not have to work out which of them is carrying the status.

	`current_count` and the counts beside it are over the memberships this
	caller may see. `status` is over all of them. The two are named differently
	because they are answers to different questions, and the block says which is
	which rather than leaving a reader to assume they match.
	"""
	current = [row for row in memberships if row["is_current"]]

	return {
		"status": member_service.derive_status(member),
		"joined_on": member.joined_on,
		"as_of": as_of,
		"visible_count": len(memberships),
		"current_count": len(current),
		"lapsed_count": len([row for row in memberships if row["lapsed"]]),
		# The branches this person is currently a member at, in the order the
		# memberships came back. A coordinator's first question about somebody
		# active in more than one place.
		"current_geo_paths": [row["geo_path"] for row in current if row["geo_path"]],
	}


# --- what they hold --------------------------------------------------------


def _visible_memberships(member, as_of) -> list[dict]:
	"""Every membership of this member's the caller may see, newest first.

	**`frappe.get_list`, never `frappe.get_all`.** The first runs core's
	permission query condition for `VMMS Membership` and the second does not, so
	this is where geo scoping reaches the dossier. A coordinator entitled to
	open somebody's member record does not thereby become entitled to read their
	membership at a branch on the other side of the country; the register in
	`register.py` is held to the same bar for the same reason, and both have a
	test whose whole job is to prove an out-of-scope row does not come back.

	Ordering is by validity and then creation so that the current membership is
	the one at the top, which is what somebody opening the record is looking for.
	"""
	names = frappe.get_list(
		MEMBERSHIP_DOCTYPE,
		filters={"member": member.name},
		pluck="name",
		order_by="valid_from desc, creation desc",
	)

	return [membership_dto(frappe.get_doc(MEMBERSHIP_DOCTYPE, name), as_of) for name in names]


def membership_dto(membership, as_of) -> dict:
	"""One membership as a coordinator needs to read it, derived as at `as_of`.

	Built field by field on top of `membership_service.status()`, which is the
	DTO the rest of this app already agrees on, so a membership never means one
	thing on the self-service page and another here. What this adds is the three
	things that are true only of a date — the lapse, the effective status and
	whether it can be renewed — plus the payment picture and the certificate
	gate, both asked of the services that own them.

	**`as_of` reaches `is_renewable` explicitly.** That call defaults to today,
	and letting it do so here is the nested-derivation bug this module's
	docstring describes: the row would report a lapse as at one date and a renew
	button as at another.
	"""
	from onerc_core.geo.services import adapter

	membership_type = membership_service.type_of(membership)
	base = membership_service.status(membership)

	return {
		**base,
		# Derived here, stored nowhere. See `membership.effective_status`.
		"effective_status": membership_service.effective_status(membership, as_of),
		"lapsed": membership_service.is_lapsed(membership, as_of),
		"is_current": membership_service.is_current(membership, as_of),
		"renewable": renewal_service.is_renewable(membership, as_of=as_of),
		"as_of": as_of,
		# The branch, under a name that cannot be confused with the Home Area on
		# the identity block above. `geo_path` from the base DTO keeps meaning
		# what it has always meant, so nothing that already reads it changed.
		"membership_geo_node": membership.geo_node,
		"membership_geo_path": adapter.get_full_path(membership.geo_node) if membership.geo_node else None,
		"duration_days": membership_type.duration_days,
		"payment": _payment_picture(membership, membership_type),
		"certificate": _certificate_access(membership, as_of),
	}


def _payment_picture(membership, membership_type) -> dict:
	"""How this membership was paid for, read live, with its verifier attached.

	`payment.settlement()` answers the money half and reaches into
	`onerc_payments` for the gateway and its receipt rather than reading a copy
	— see that function, which explains why a copy would be wrong.

	The verifier is added here rather than there because it is an approval fact,
	not a payment one: a proof-of-membership fee was settled outside this system
	entirely, and what stands in for a gateway is the person who looked at the
	attachment and approved it. Asking the money seam to read the approval trail
	would put a dependency between two modules that have no business knowing
	about each other.
	"""
	picture = payment_service.settlement(membership, membership_type)

	if not picture["is_proof"]:
		return picture

	verifier = _verified_by(membership)

	return {**picture, "verified_by": verifier["approver"], "verified_on": verifier["decided_on"]}


def _verified_by(membership) -> dict:
	"""Who approved this membership, and when. The latest approval, or nothing.

	Read from the engine's own decision rows through `contract`, never from a
	field on the membership: the membership stores no approver, and a copy would
	be one more thing to keep in step with a decision that can be superseded.
	"""
	from vmmsx.approvals.services import contract

	approvals = [row for row in contract.decisions(membership) if row.decision == DECISION_APPROVED]

	if not approvals:
		return {"approver": None, "decided_on": None}

	latest = max(approvals, key=lambda row: (row.decided_on or "", row.idx))

	return {"approver": latest.approver, "decided_on": latest.decided_on}


def _certificate_access(membership, as_of) -> dict:
	"""Whether this membership's certificate can be had, and by this caller.

	Two separate questions, and both are asked of the services that enforce
	them rather than re-derived:

	    `available`  is there a certificate at all — a membership that is not
	                 active has none, because a certificate is evidence of
	                 membership (`certificate.assert_active`'s rule)
	    `may_print`  may *this* caller have it — the holder, or the role the
	                 society configured (`certificate.may_print`)

	A screen offering a button the server would refuse is worse than no button,
	so the two are reported separately and the UI needs both.

	`configured` is the third failure this makes visible: a membership type with
	no template renders nothing, and a coordinator pressing a button that throws
	"no certificate template" should have been told so by the page instead.
	"""
	membership_type = membership_service.type_of(membership)

	return {
		# The effective status, not the stored one: a membership that lapsed
		# last night has no certificate this morning, and the page must not
		# offer one until the sweep gets round to it.
		"available": membership_service.is_current(membership, as_of),
		"may_print": certificate.may_print(membership),
		"configured": bool(membership_type.template_key),
	}


# --- how they came to hold it ----------------------------------------------


def history(memberships: list[dict]) -> list[dict]:
	"""The approval trail across every membership shown, newest decision first.

	One flat list rather than a trail nested inside each membership, because the
	question it answers is about the person: who has verified this member, and
	when. A coordinator scanning it is looking for the last time anybody checked
	anything, not for which record it hung off — so each row names its
	membership rather than being buried under it.

	**Read, never decided.** `stage_label` is passed through as the display
	string the engine snapshotted and nothing here compares it to anything;
	branching on a stage label is what `tests/test_no_stage_branching.py` walks
	the AST to forbid. Nothing here calls `engine.status()` either: that
	resolves approvers through core and needs a configured workflow, and a page
	showing who approved somebody last year must not stop rendering because the
	society is midway through rewriting this year's workflow.
	"""
	from vmmsx.approvals.services import contract

	rows = []

	for row in memberships:
		membership = frappe.get_doc(MEMBERSHIP_DOCTYPE, row["name"])

		for decision in contract.decisions(membership):
			rows.append(
				{
					"membership": membership.name,
					"membership_type_name": row["membership_type_name"],
					"geo_path": row["membership_geo_path"],
					"membership_source": row["membership_source"],
					"stage_label": decision.stage_label,
					"approver": decision.approver,
					"decision": decision.decision,
					"decided_on": decision.decided_on,
					"reason": decision.reason,
				}
			)

	# Newest first, with undated rows last rather than sorted as though they
	# happened at the beginning of time.
	return sorted(
		rows, key=lambda entry: (entry["decided_on"] is not None, entry["decided_on"]), reverse=True
	)
