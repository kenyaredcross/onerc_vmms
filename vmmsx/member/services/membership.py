# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The membership lifecycle — submit, activate, expire, cancel.

**Activation is a predicate, not a sequence.** A membership becomes active when
every requirement its type imposes has been met:

    approval settled?   asked of approval.py   — routed types need a person,
                                                 auto-on-payment types do not
    payment settled?    asked of payment.py    — fee-free types need nothing

Both are questions about *configuration*, never about which code path happened
to run, and that is what makes `try_activate()` safe to call after any event and
in any order. Payment can confirm before the approver looks, or after; the
approver can approve a free membership with no payment in sight. There is no
ordering bug to have, because there is no ordering.

**One trigger point.** `on_update` re-evaluates the predicate after every save,
so activation follows whatever just happened — an approval decision recorded by
the engine, a payment confirmed by a gateway callback — without either of them
needing to know that memberships activate. The logic itself lives in
`try_activate()`, an idempotent service anyone may call directly; the hook only
calls it.

**Proof-of-Membership is the same predicate, one input widened.** A pre-rollout
member paid before this system existed, so there is no gateway transaction to
confirm — `membership_source` records that an approver verified an attached
document instead, through the ordinary routed path. `_payment_settled()` is the
only place that knows this: a proof-sourced membership answers the money
question the moment its approval does, with no new activation rule and no
change to `payment.py`, which stays exactly what MEM-01 says it is.

**A lifetime membership is one that has no end date, and nothing more.** The
type's `is_lifetime` says so; `activate()` leaves `valid_to` empty rather than
computing an expiry, and every date-derived question in this module already
reads an empty `valid_to` as "no window to close". There is no lifetime status,
no lifetime branch in the activation predicate, and no sentinel date — see
`_valid_to()`.

**The affiliation row is written, never read.** `activate()` reports to core
through `set_affiliation()`; nothing in this module or any other reads that row
back to decide anything. This satellite is the truth (core's Design 2).
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, today

from vmmsx.approvals.services import contract
from vmmsx.member.services import approval, payment, proof
from vmmsx.registration.services import questions

MEMBER_DOCTYPE = "VMMS Member"
MEMBERSHIP_DOCTYPE = "VMMS Membership"

STATUS_DRAFT = "Draft"
STATUS_AWAITING_PAYMENT = "Awaiting Payment"
STATUS_AWAITING_APPROVAL = "Awaiting Approval"
STATUS_ACTIVE = "Active"
STATUS_EXPIRED = "Expired"
STATUS_CANCELLED = "Cancelled"

# The states from which a membership may still become active. A cancelled or
# expired one may not be revived by a late payment landing on it.
ACTIVATABLE = (STATUS_DRAFT, STATUS_AWAITING_PAYMENT, STATUS_AWAITING_APPROVAL)

ACTIVATION_FLAG = "vmms_membership_activating"

# Proof-of-Membership. Gateway is the ordinary path; Proof is a pre-rollout
# member whose fee was paid before this system existed, verified by an approver
# instead of a gateway. See _payment_settled() and assert_proof_consistent().
SOURCE_GATEWAY = "Gateway"
SOURCE_PROOF = "Proof"
SOURCES = (SOURCE_GATEWAY, SOURCE_PROOF)


def type_of(membership):
	"""The membership's type record, read through the document cache."""
	return frappe.get_cached_doc("VMMS Membership Type", membership.membership_type)


def source(membership) -> str:
	"""Which channel this membership's fee obligation was settled through."""
	return membership.get("membership_source") or SOURCE_GATEWAY


def is_proof(membership) -> bool:
	return source(membership) == SOURCE_PROOF


def is_lifetime(membership_type) -> bool:
	"""Does this type confer a membership that never ends?

	Takes the *type*, not the membership: whether a membership expires is a
	property of the configuration it was created under, and asking it of the
	type is what stops the answer from being reconstructed from whether
	`valid_to` happens to be empty. A membership that has not activated yet has
	no `valid_to` either, and it is not a lifetime one.
	"""
	return bool(membership_type.is_lifetime)


def assert_proof_consistent(membership) -> None:
	"""A proof-based membership names a routed type, and carries its evidence.

	Called from the doctype's own `validate()`, on every save — the same moment
	`validate_anchor()` enforces ACC-02. A proof marked against a type with no
	approver would have nobody to look at what was attached, so the combination
	is refused up front rather than left to sit unreachable in Awaiting Payment.
	"""
	if not is_proof(membership):
		return

	membership_type = type_of(membership)

	if approval.mode(membership_type) != approval.MODE_ROUTED:
		frappe.throw(
			_(
				"A proof-based membership needs an approver to verify what was attached, but"
				" membership type {0} activates on payment with no approver. Choose a routed"
				" membership type for a proof-based membership."
			).format(frappe.bold(membership_type.membership_type_name)),
			frappe.ValidationError,
			title=_("Proof Needs An Approver"),
		)

	if not membership.get("proof_attachment"):
		frappe.throw(
			_(
				"A proof-based membership needs the proof attached — a document or image showing"
				" it was paid for before this system existed."
			),
			frappe.MandatoryError,
			title=_("Proof Required"),
		)


def _payment_settled(membership, membership_type) -> bool:
	"""Has the money question been answered — by a gateway, or by verified proof?

	A proof-sourced membership's fee was paid before this system existed, so
	`payment.is_settled()` would wait on a `paid_on` that no gateway will ever
	set. `is_proof()` widens what counts as settled the same way a zero fee
	already does; `payment.py` itself is untouched and never asked about proof
	at all.
	"""
	return is_proof(membership) or payment.is_settled(membership, membership_type)


# --- submission -----------------------------------------------------------


def submit(membership) -> dict:
	"""Put a membership into motion: request its fee, start its approval.

	Idempotent. Called twice, the second call re-requests nothing and restarts
	nothing — `payment.request` refuses a second transaction and
	`approval.begin` hands an already-routed document back to the engine, which
	re-syncs the queue rather than restarting review.
	"""
	membership_type = type_of(membership)

	_assert_type_usable(membership_type)
	assert_not_already_held(membership)

	# Before the fee is requested, deliberately. A society's own questions are as
	# required as anything else on the form, and discovering that after a gateway
	# has been asked for money would leave a transaction against an application
	# that never went anywhere. A no-op until a society writes a question.
	questions.assert_answered(membership)

	# The same seam, for the same reason: everything required *to submit*. A
	# no-op unless this is somebody proving a membership they already hold — see
	# `proof.assert_claim_complete`.
	proof.assert_claim_complete(membership)

	# A proof-sourced membership was already paid for, outside this system —
	# there is nothing for a gateway to collect, so it never asks for one, even
	# when its type charges a fee.
	requested = None if is_proof(membership) else payment.request(membership, membership_type)

	_set_pending_status(membership, membership_type)

	membership.save()

	# After the save, so the engine reads and writes a persisted document —
	# engine.submit() saves it again itself.
	approval.begin(membership, membership_type)

	activated = try_activate(membership)

	if activated:
		return _with_payment(activated, requested)

	# Not active yet, but the person is now known to the society as a
	# prospective member. Reported to core's index so their profile shows the
	# application rather than nothing at all until somebody approves it.
	_sync_member(membership)

	return _with_payment(status(membership), requested)


def _with_payment(answer: dict, requested: dict | None) -> dict:
	"""Carry the gateway's own first words back to whoever submitted this.

	**The one thing only the gateway can say.** A person who has just sent a
	membership application needs to know what happens next, and what happens next
	depends entirely on which driver was asked: mobile money puts a prompt on
	their phone within seconds, a bank transfer needs an account number and a
	reference, a counter needs an office and opening hours. None of that is
	vmmsx's to write — `initiate_payment` returns the driver's own `message` and
	this hands it on unread.

	Absent when there was nothing to collect, when a transaction was already
	outstanding, or on a proof of an existing membership. A screen with no
	message says nothing rather than inventing one.
	"""
	if not requested:
		return answer

	return {
		**answer,
		"payment": {
			"transaction": requested.get("transaction_id"),
			"status": requested.get("status"),
			# The driver's own sentence. Never parsed, never matched against,
			# never translated — it is the gateway speaking to the payer.
			"message": requested.get("message") or "",
		},
	}


def _set_pending_status(membership, membership_type) -> None:
	"""What this membership is waiting for, in the society's own configuration."""
	if not _payment_settled(membership, membership_type):
		membership.membership_status = STATUS_AWAITING_PAYMENT
	elif not approval.is_settled(membership, membership_type):
		membership.membership_status = STATUS_AWAITING_APPROVAL


def _assert_type_usable(membership_type) -> None:
	if membership_type.is_active:
		return

	frappe.throw(
		_("Membership type {0} is not active and cannot take new memberships.").format(
			frappe.bold(membership_type.membership_type_name)
		),
		frappe.ValidationError,
		title=_("Inactive Membership Type"),
	)


def assert_not_already_held(membership) -> None:
	"""Refuse a proof of a membership this member already holds.

	**The gap this closes.** `engine.assert_single_open` refuses a second
	*undecided* membership per member; nothing refuses a second *active* one. The
	proof path reaches that state without anybody meaning to — a member who has
	forgotten they were recorded last year proves the membership they are already
	holding, and the society ends up with two live windows against one plan, two
	fees and two certificates for one person.

	**Scoped to proof, which is where the phase that asked for it put it.** The
	general case — an ordinary Gateway application for a plan somebody already
	holds — is the same defect and is *not* fixed here, deliberately. It is
	pre-existing, it is out of this phase's scope, and closing it means changing
	behaviour several other suites are built on. It is recorded for the
	integration and hardening phase rather than folded in silently.

	**Member, plan and branch — all three.** The scope was worded "the same member
	and plan", and the branch is here because this app has a multi-branch
	membership model that predates it and states itself out loud: `register.py`
	builds the coordinator's register a row per *membership* rather than per
	member, precisely so that "somebody enrolled at two branches appears twice,
	once per branch". A person may hold the same plan at the branch where they
	live and the branch where they work, and both are real memberships with their
	own fee and their own validity. Dropping the branch from this key would not
	tighten a duplicate rule; it would delete a feature that `test_dossier` and
	`test_renewal` both pin.

	**Current, not stored-Active.** A membership sitting at Active with a
	`valid_to` that has already passed is current in name only, in the ordinary
	window before the daily sweep notices. Asked through `is_current` so this and
	`renewal.is_renewable` agree by construction — and so that proving a
	membership that has lapsed leaves the person on the renewal path rather than
	locked out of it.

	At submission rather than at insert, for `assert_single_open`'s reason: a
	coordinator may have several drafts on their desk, and a draft is not a
	membership anybody holds.
	"""
	if not is_proof(membership):
		return

	if not membership.member or not membership.membership_type or not membership.geo_node:
		return

	held = frappe.get_all(
		MEMBERSHIP_DOCTYPE,
		filters={
			"member": membership.member,
			"membership_type": membership.membership_type,
			"geo_node": membership.geo_node,
			"membership_status": STATUS_ACTIVE,
			"name": ("!=", membership.name),
		},
		fields=["name", "membership_status", "valid_to"],
	)

	current = next((row for row in held if is_current(frappe._dict(row))), None)

	if not current:
		return

	# The place is named through core's adapter rather than in words. ACC-03: a
	# geo level is a society's configuration and never a literal in a source
	# file, and this message used to say "at this branch" — which is wrong on
	# every site that registers members at a county or a ward.
	# `member/tests/test_anchor.py::TestNoLevelNamesInSource` walks the AST and
	# fails the build over it.
	from onerc_core.geo.services import adapter

	frappe.throw(
		_(
			"This person already holds a current {0} membership at {1} ({2}). A second one"
			" would be two live memberships against the same plan in the same place. Renew that"
			" one when it expires, or cancel it first."
		).format(
			frappe.bold(frappe.get_cached_value(
				"VMMS Membership Type", membership.membership_type, "membership_type_name"
			)),
			frappe.bold(adapter.get_full_path(membership.geo_node)),
			frappe.bold(current["name"]),
		),
		frappe.ValidationError,
		title=_("Membership Already Held"),
	)


# --- activation -----------------------------------------------------------


def is_activatable(membership) -> bool:
	"""Has everything this membership's type requires been met?"""
	if membership.membership_status not in ACTIVATABLE:
		return False

	membership_type = type_of(membership)

	return approval.is_settled(membership, membership_type) and _payment_settled(membership, membership_type)


def try_activate(membership) -> dict | None:
	"""Activate if the predicate holds. Returns the status DTO, or None.

	The single entry point for becoming a member. Idempotent — an already-active
	membership fails `is_activatable` on its status and returns None.
	"""
	if not is_activatable(membership):
		return None

	return activate(membership)


def activate(membership) -> dict:
	"""Make it real: dates, member status, and the affiliation index.

	Validity is computed here rather than at creation because the clock starts
	when somebody actually becomes a member, not when they applied — an
	application that sat with an approver for three weeks must not lose three
	weeks of what it paid for.

	**One exception, and it is a decision somebody made rather than a rule.** A
	membership carrying dates an approver confirmed against uploaded evidence
	takes those instead, because the person did not become a member today — they
	became one in 2014 and are asking the society to record what it already knew.
	Nothing else can produce those dates: they are written only by
	`proof.verify()`, only from the review screen, and never from the applicant's
	claim. Every other membership in this app — an ordinary application, a
	renewal, a clerk's proof entry — has nothing there to read and reaches the
	fresh period below, unchanged.
	"""
	membership_type = type_of(membership)
	start, end = _validity(membership, membership_type)

	membership.membership_status = _activated_status(end)
	membership.valid_from = start
	membership.valid_to = end

	_save(membership)
	_sync_member(membership)

	return status(membership)


def _validity(membership, membership_type):
	"""The window this membership is being activated for: verified, or fresh."""
	verified = proof.verified_validity(membership, membership_type)

	if verified:
		return verified

	start = getdate(today())

	return start, _valid_to(membership_type, start)


def _activated_status(end) -> str:
	"""Active, unless the window being recorded has already closed.

	**A membership proved to have expired is recorded as Expired, not activated.**
	Somebody whose card lapsed in 2021 is telling the truth about a membership
	they no longer hold, and putting them on the register as Active for a period
	that ended years ago would state something false about today in order to
	record something true about the past. Expired says both.

	It costs nothing to reach from there: `renewal.is_renewable` opens from
	exactly this state, so the answer to "then what" is the renewal path that
	already exists, and the daily `expire_lapsed()` sweep finds nothing to do
	because this membership never spent a moment being wrongly Active.

	Unreachable on the fresh path — a period starting today has not closed — so
	in practice this only ever fires on a verified historical claim.
	"""
	if end and getdate(end) < getdate(today()):
		return STATUS_EXPIRED

	return STATUS_ACTIVE


def _valid_to(membership_type, start):
	"""When this membership ends, or None when it does not end at all.

	**A lifetime membership is stored as an empty `valid_to`, not as a distant
	date.** A placeholder in 2999 would be a lie the expiry sweep eventually
	acts on, and every screen would have to know which far-future date meant
	"forever". Empty already means the right thing everywhere it is read:
	`is_lapsed()` answers False, `expire_lapsed()` never selects it,
	`renewal.is_renewable()` finds nothing to renew from, and the desk renders
	the row as Lifetime.

	**`membership_status` stays Active.** A lifetime status value was
	considered and rejected: it would fork every `== STATUS_ACTIVE` comparison
	in this app — the certificate gate, the activation predicate, renewal, the
	dossier's standing — into a pair that each caller would have to remember to
	keep in step. Whether somebody is a member and whether their membership
	ends are two questions, and the second one is answered by `valid_to`.
	"""
	if is_lifetime(membership_type):
		return None

	return add_days(start, cint(membership_type.duration_days))


def expire(membership) -> dict:
	"""Close a membership whose validity has run out."""
	if membership.membership_status == STATUS_ACTIVE:
		membership.membership_status = STATUS_EXPIRED
		_save(membership)
		_sync_member(membership)

	return status(membership)


def cancel(membership, reason: str | None = None) -> dict:
	"""Withdraw a membership before or after activation."""
	if membership.membership_status != STATUS_CANCELLED:
		membership.membership_status = STATUS_CANCELLED
		_save(membership)
		membership.add_comment("Comment", _("Cancelled. {0}").format(reason or ""))
		_sync_member(membership)

	return status(membership)


def expire_lapsed(as_of=None) -> dict:
	"""Expire every active membership whose validity has passed. The daily job.

	Idempotent by construction: it only ever moves Active to Expired, so a
	second run the same day finds nothing left to move.

	**A membership with no end date is never selected.** That is stated as its
	own filter rather than left to SQL, where `valid_to < as_of` excludes a
	NULL only as a side effect of three-valued logic — true today, and exactly
	the kind of thing that changes under a query builder without anybody
	noticing that lifetime memberships started expiring overnight. The sweep
	says out loud that it only looks at memberships that have an end date.
	"""
	as_of = getdate(as_of or today())
	summary = {"checked": 0, "expired": 0}

	lapsed = frappe.get_all(
		"VMMS Membership",
		filters=[
			["membership_status", "=", STATUS_ACTIVE],
			["valid_to", "is", "set"],
			["valid_to", "<", as_of],
		],
		pluck="name",
	)

	summary["checked"] = len(lapsed)

	for name in lapsed:
		expire(frappe.get_doc("VMMS Membership", name))
		summary["expired"] += 1

	return summary


# --- what a membership is, as at a date -----------------------------------
#
# Derived on every read and stored nowhere, which is what makes asking about a
# date other than today meaningful at all. The mirror of
# `volunteer/services/certification.py::is_lapsed`, and deliberately the same
# shape: a stored `lapsed` flag would be a second answer that goes wrong
# silently at midnight and stays wrong until a job runs.


def is_lapsed(membership, as_of=None) -> bool:
	"""Has this membership's validity window closed as at `as_of`?

	A membership with no `valid_to` has no window to close, and there are two
	ways to be in that position: one that never activated has not lapsed, it
	has not started, and a lifetime one never will. False is the honest answer
	for both, and `effective_status` below is what distinguishes them — the
	first is still Draft or awaiting something, the second is Active.
	"""
	if not membership.valid_to:
		return False

	return getdate(membership.valid_to) < getdate(as_of or today())


def effective_status(membership, as_of=None) -> str:
	"""What this membership actually is as at `as_of`, which is not always what it says.

	There is an ordinary window in which the two differ: a membership whose
	`valid_to` has passed is still stored as Active until the daily
	`expire_lapsed()` job notices. A coordinator opening the record during that
	window must not be told the person is a current member, so the stored status
	is read through the same date comparison `renewal.is_renewable` already
	makes — the two now agree by construction rather than by coincidence.

	**Nothing is written.** This does not expire anything, and calling it does
	not bring the sweep forward; it reports. `expire()` remains the only thing
	that moves a membership to Expired, so there is still exactly one writer.
	"""
	if membership.membership_status == STATUS_ACTIVE and is_lapsed(membership, as_of):
		return STATUS_EXPIRED

	return membership.membership_status


def is_current(membership, as_of=None) -> bool:
	"""Is this membership one somebody currently holds, as at `as_of`?"""
	return effective_status(membership, as_of) == STATUS_ACTIVE


# --- the lifecycle hook ---------------------------------------------------


def on_update(membership, method=None) -> None:
	"""Re-evaluate activation after any save. Registered in hooks.py.

	This is how an approval decision recorded by the engine, or a payment
	confirmed by a gateway callback, turns into an active membership without
	either of them knowing memberships exist. The flag stops the save inside
	`activate()` from re-entering.

	The state is read before activation and reported after it, for the two
	reasons the volunteer twin gives: `activate()` saves again and would erase
	the answer to "what did this save change", and the card attached to an
	approval only exists once the membership it describes is active.
	"""
	if membership.flags.get(ACTIVATION_FLAG):
		return

	before = membership.get_doc_before_save()
	previous = before.get(contract.STATE_FIELD) if before else None

	if not try_activate(membership):
		_resettle_pending_status(membership)

	_report(membership, previous)


def _resettle_pending_status(membership) -> None:
	"""Re-derive what a still-pending membership is waiting for.

	**The bug this fixes.** `_set_pending_status` ran only inside `submit()`, so
	the answer to "what is this waiting for" was computed once, at the moment of
	application, and never again. A member who paid at the branch counter before
	their branch had approved them stayed at **Awaiting Payment** — on their own
	portal, on the register, and on every screen that shows a membership status —
	with `paid_on` set on the record all along. Nothing recomputed it, because
	`on_update` only ever asked the stronger question: *can this activate yet?*
	When the answer was no, it did nothing at all.

	It went unnoticed because the common order hides it. Pay after approval and
	`try_activate` succeeds, which sets Active and skips the intermediate state
	entirely; pay before approval and the wrong label sits there until the
	approval lands. Only the second order shows it, and only in the window
	between the two.

	**Narrow on purpose.** It touches a membership only while it is in one of the
	two pending states — a Cancelled, Expired or Active membership is not waiting
	for anything and must not be dragged back into a queue — and it writes
	nothing when the derived status already matches. It runs inside the caller's
	save, so it costs no second write.
	"""
	if membership.membership_status not in (STATUS_AWAITING_PAYMENT, STATUS_AWAITING_APPROVAL):
		return

	before = membership.membership_status
	_set_pending_status(membership, type_of(membership))

	if membership.membership_status != before:
		membership.db_set(
			"membership_status", membership.membership_status, update_modified=False
		)


def report_payment(membership, amount=None, receipt=None) -> bool:
	"""Send the receipt for a fee that has just been confirmed.

	**The letter that was missing.** Every other message about a membership is
	keyed to an approval state, and a confirmed payment moves none: a membership
	that still needs an approver stayed exactly where it was, so somebody who had
	just paid heard nothing until a coordinator got round to them. This says the
	money arrived, gives them the reference to quote, and says plainly that the
	approval is still to come.

	The subject is built the way `_report` builds its own — same person, same
	guardian copy rule — with the amount formatted here because this is the only
	place that knows the currency.

	Never raises. `lifecycle.announce_payment` swallows its own failures; this
	guards the reads above it, because a member record that will not load must
	not roll back the payment that was just confirmed.
	"""
	try:
		from vmmsx.member.services import identity
		from vmmsx.notifications.services import lifecycle
		from vmmsx.registration.services import guardian

		member = frappe.get_doc(MEMBER_DOCTYPE, membership.member) if membership.member else None

		if not member:
			return False

		person = identity.read(member)
		charge = payment.fee(type_of(membership))

		return lifecycle.announce_payment(
			membership,
			{
				"email": person.get("email"),
				"phone": person.get("phone"),
				"name": identity.display_name(member),
				"kind": _("membership"),
				"geo_path": _geo_path(membership),
				"portal_path": "/portal/membership",
				# Formatted with the society's own currency rather than handed
				# over as a bare number: this letter is somebody's proof of what
				# they paid, and a figure with no unit on it proves nothing.
				"amount": frappe.utils.fmt_money(
					flt(amount) if amount is not None else charge["amount"],
					currency=charge["currency"],
				),
				"receipt": receipt or membership.get("payment_receipt") or "",
				"cc": guardian.emails_for(member.red_profile),
			},
		)
	except Exception:
		frappe.log_error(
			title="vmmsx: could not report a confirmed membership payment",
			message=frappe.get_traceback(),
		)

		return False


def _report(membership, previous: str | None) -> None:
	"""Tell the applicant what just happened to their membership.

	`lifecycle.notify` owns whether anything is sent; this owns who it is to and
	what goes with it. The sibling of `application._report`, and deliberately the
	same shape: two registrations, one set of messages, no second vocabulary for
	the same four events.
	"""
	from vmmsx.member.services import identity
	from vmmsx.notifications.services import lifecycle
	from vmmsx.registration.services import guardian

	member = frappe.get_doc(MEMBER_DOCTYPE, membership.member) if membership.member else None

	if not member:
		return

	person = identity.read(member)

	lifecycle.notify(
		membership,
		previous,
		contract.state(membership),
		{
			"email": person.get("email"),
			# As above, and for the same reason: the same four events, the same
			# nudge, one implementation of both.
			"phone": person.get("phone"),
			"name": identity.display_name(member),
			"kind": _("membership"),
			"geo_path": _geo_path(membership),
			"portal_path": "/portal/membership",
			"attachment": _card_attachment(membership),
			# The same copy rule as the volunteer application's, and it is the
			# same rule rather than a membership one: a child joining as a member
			# has the same parent as a child volunteering, and the question is
			# asked of the person either way.
			"cc": guardian.emails_for(member.red_profile),
		},
	)


def _geo_path(membership) -> str:
	"""Where this membership is anchored, in the society's own words."""
	from onerc_core.geo.services import adapter

	return adapter.get_full_path(membership.geo_node) if membership.geo_node else ""


def _card_attachment(membership) -> tuple[str, bytes] | None:
	"""The member's card, for the approval email. None unless it is active.

	Never raises: a card that could not be rendered must not stop somebody being
	told they have been accepted.
	"""
	if membership.membership_status != STATUS_ACTIVE:
		return None

	try:
		from vmmsx.member.services import card

		return card.pdf_filename(membership), card.pdf_for(membership)
	except Exception:
		frappe.log_error(
			title="vmmsx: could not build a member card for the approval email",
			message=frappe.get_traceback(),
		)

		return None


def _save(membership) -> None:
	"""Persist an activation-path change without re-entering `on_update`."""
	membership.flags[ACTIVATION_FLAG] = True

	try:
		# The membership's own fields here are engine-written and read-only to
		# users, and this runs on paths with no interactive session at all — a
		# gateway callback confirming a payment is the ordinary case. The
		# permission that matters was checked when the membership was created.
		membership.save(ignore_permissions=True)
	finally:
		membership.flags[ACTIVATION_FLAG] = False


# --- the member satellite and core's index --------------------------------


def _sync_member(membership) -> None:
	"""Push the member's derived state, then report it to core.

	The order matters: this satellite is the truth, so it is written first and
	core's affiliation index is refreshed from it afterwards.
	"""
	from vmmsx.member.services import member as member_service

	member_service.refresh(membership.member)


def status(membership) -> dict:
	"""Explicit DTO for one membership. Built field by field.

	Never the Document: that would leak every field on the record, including
	ones nobody reviewed, and turn a schema change into an API change.
	"""
	from onerc_core.geo.services import adapter

	from vmmsx.member.services import identity

	membership_type = type_of(membership)
	member = frappe.get_doc("VMMS Member", membership.member)

	return {
		"name": membership.name,
		"member": membership.member,
		# Read through Red Profile, never stored on the membership.
		"member_name": identity.display_name(member),
		"membership_type": membership.membership_type,
		"membership_type_name": membership_type.membership_type_name,
		"approval_mode": membership_type.approval_mode,
		"requires_approver": approval.requires_approver(membership_type),
		"membership_status": membership.membership_status,
		# Whether this membership is in force *now*, stated rather than left to be
		# derived from the status by whoever is reading. The six statuses are this
		# module's vocabulary and comparing against one of them is this module's
		# job: a browser bundle that wrote `status === "Active"` would be a second
		# copy of that vocabulary, and the screen that had it told somebody they
		# held a membership their branch had not approved yet.
		"is_active": membership.membership_status == STATUS_ACTIVE,
		"geo_node": membership.geo_node,
		"geo_path": adapter.get_full_path(membership.geo_node) if membership.geo_node else None,
		"valid_from": membership.valid_from,
		"valid_to": membership.valid_to,
		# Why `valid_to` is empty, which the date alone cannot say. A screen
		# reading this DTO renders "Lifetime" rather than a gap, and does not
		# have to infer it from a missing value.
		"is_lifetime": is_lifetime(membership_type),
		# Whether the window has closed, derived here as at today rather than
		# left for a reader to work out from `valid_to`. A surface offering to
		# expire a membership needs the same answer `api/member.py::
		# expire_membership` will give it, and deriving it twice in two places
		# is how the button and the endpoint come to disagree.
		"is_lapsed": is_lapsed(membership),
		"fee": payment.fee(membership_type),
		"payment_settled": _payment_settled(membership, membership_type),
		"approval_settled": approval.is_settled(membership, membership_type),
		"payment_transaction": membership.payment_transaction,
		"payment_receipt": membership.payment_receipt,
		"paid_on": membership.paid_on,
		"approval_state": membership.approval_state,
		"membership_source": source(membership),
		"proof_attachment": membership.get("proof_attachment"),
		# The two halves of an existing-membership proof, kept apart all the way
		# out to the caller. `None` on every membership that is not one, so a
		# screen renders nothing rather than a block of empty fields.
		"claimed": proof.claimed_dto(membership),
		"verified": proof.verified_dto(membership),
	}
