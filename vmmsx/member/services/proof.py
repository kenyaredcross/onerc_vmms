# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Proving a membership you already hold — a claim, and what the society does with it.

A person who joined this society in 2014 has a card, a receipt or a certificate,
and no row in this system. `membership_source = Proof` and `proof_attachment`
have carried that case since MEM-01, but only from the *clerk's* side: somebody
at a branch typed the membership in and attached the evidence, and the fresh
validity period started the day it was approved. This module is the other side —
the member fills the form in themselves — and the whole of its design follows
from one difference between those two situations.

**A clerk is recording; an applicant is claiming.** When a coordinator enters a
pre-rollout member, the society is asserting the facts about its own register.
When somebody submits their own proof, they are asserting facts about a document
nobody at the society has looked at yet. Those are different epistemic acts and
they must not land in the same fields, because the second one, once stored
somewhere official-looking, is indistinguishable from the first.

So the claim and the verification are two separate sets of fields:

    proof_claimed_start_date     what the applicant says
    proof_claimed_expiry_date
    proof_membership_number
    proof_registered_at
    proof_reference_number

    proof_verified_start_date    what somebody at the society confirmed
    proof_verified_expiry_date   against the document, stamped with who and when
    proof_verified_by
    proof_verified_on

**Nothing copies one into the other.** Not this module, not the API, not the
review screen's initial values — the approver types the dates, having looked at
the evidence, and `verify()` is the only writer. A "copy the claim across"
convenience would make the two sets identical in the overwhelming majority of
cases and so make the distinction invisible exactly where it matters, which is
the one case where the claim was wrong.

**Only verified dates decide validity.** `membership.activate()` asks
`verified_validity()` and falls back to the fresh period when there is nothing
verified — which is the clerk path, where there is no claim to verify and the
existing behaviour is correct. A claimed date has never once reached
`valid_from`.

**A claim cannot be approved unverified.** If forgetting to fill the verified
dates in silently produced a fresh period, the split above would be advisory.
`assert_verified()` runs from the controller on the transition into Approved, in
the same seam and for the same reason as Phase 1's guardian consent gate: the
decision rolls back with a sentence the approver can act on.

**A membership proved to have already expired is recorded as Expired.** Somebody
whose 2019 card lapsed in 2021 is telling the truth and is not a current member,
and activating them for a period that ended years ago would put a live membership
on the register for a person who does not hold one. The honest record is the
expired one, and `renewal.is_renewable` already opens the renewal path from
exactly that state — so the answer to "then what" is one they already have.
"""

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, today

# What the applicant may put in the claim. An allow-list, and the same tuple the
# API accepts and the portal is handed back, for the reason
# `api/registration.py::rows_from` gives: a field added to the doctype next year
# is refused by this by default. The verified fields are absent, and that absence
# is the security property — no browser can name one.
CLAIM_FIELDS = (
	"proof_claimed_start_date",
	"proof_claimed_expiry_date",
	"proof_membership_number",
	"proof_registered_at",
	"proof_reference_number",
)

VERIFIED_FIELDS = (
	"proof_verified_start_date",
	"proof_verified_expiry_date",
	"proof_verified_by",
	"proof_verified_on",
)


def _lifetime(membership_type) -> bool:
	"""Asked of the module that owns the question, never of an empty date."""
	from vmmsx.member.services import membership as membership_service

	return membership_service.is_lifetime(membership_type)


def is_proof(membership) -> bool:
	from vmmsx.member.services import membership as membership_service

	return membership_service.is_proof(membership)


def has_claim(membership) -> bool:
	"""Is this a membership somebody is proving, rather than one a clerk entered?

	Keyed on the claimed start date rather than on `membership_source`, because
	both cases are proof-sourced and only one of them carries an assertion for
	somebody to check. The claimed start is the field that makes a claim a claim
	about a period, and `assert_claim_complete` refuses a self-service submission
	without it — so after submission it is present on every claim and on nothing
	else.
	"""
	return is_proof(membership) and bool(membership.get("proof_claimed_start_date"))


def is_verified(membership) -> bool:
	return bool(membership.get("proof_verified_start_date"))


# --- the submission gate ---------------------------------------------------


def assert_claim_complete(membership) -> None:
	"""Refuse a proof submission that does not say what is being claimed.

	Runs from `membership.submit()`, alongside the society's own questions and
	the declaration — the seam that governs everything required *to submit*, as
	distinct from everything required to approve.

	Only a claim is checked. A clerk's proof entry carries none and is untouched
	by every rule here, which is what keeps MEM-01's path exactly as it was.
	"""
	from vmmsx.member.services import membership as membership_service
	from vmmsx.registration.services import declarations

	if not has_claim(membership):
		return

	membership_type = membership_service.type_of(membership)

	# The declaration belongs to the evidence, so the gate does too. It is asked
	# here rather than from `submit()` directly because `VMMS Membership` carries
	# one declaration and it is about a document — an ordinary Gateway membership
	# is not making that statement and must not be refused for not making it.
	declarations.assert_accepted(membership)

	start = getdate(membership.proof_claimed_start_date)
	expiry = membership.get("proof_claimed_expiry_date")

	if _lifetime(membership_type):
		if expiry:
			frappe.throw(
				_(
					"{0} is a lifetime membership, so there is no expiry date to give. Leave it"
					" empty."
				).format(frappe.bold(membership_type.membership_type_name)),
				frappe.ValidationError,
				title=_("Lifetime Membership Has No Expiry"),
			)

		return

	if not expiry:
		frappe.throw(
			_(
				"Tell us when the membership you are proving runs to. {0} memberships run for a"
				" fixed period, so there is an expiry date on the document you uploaded."
			).format(frappe.bold(membership_type.membership_type_name)),
			frappe.MandatoryError,
			title=_("Expiry Date Needed"),
		)

	_assert_ordered(start, getdate(expiry), _("The dates you gave"))


def _assert_ordered(start, expiry, subject: str) -> None:
	"""A membership cannot end before it began."""
	if expiry > start:
		return

	frappe.throw(
		_("{0} end on {1}, which is on or before the start date of {2}.").format(
			subject, frappe.bold(expiry), frappe.bold(start)
		),
		frappe.ValidationError,
		title=_("Dates Out Of Order"),
	)


# --- the approval gate -----------------------------------------------------


def assert_verified(membership) -> None:
	"""Refuse to approve a claim nobody has checked against the evidence.

	Called from `VMMSMembership.validate` on the transition into Approved, the
	same seam and the same reason as Phase 1's guardian consent: it is a rule
	about *approving*, so it cannot live in `submit()`, and it must not go into
	the generic approval engine, which does not know what a membership is.
	"""
	from vmmsx.member.services import membership as membership_service

	if not has_claim(membership):
		return

	membership_type = membership_service.type_of(membership)

	if not membership.get("proof_verified_start_date"):
		frappe.throw(
			_(
				"Check the document that was uploaded and record the start date you can see on"
				" it before approving this. What the applicant told us is a claim, and it is the"
				" date you confirm that decides when this membership runs from."
			),
			frappe.MandatoryError,
			title=_("Proof Not Verified"),
		)

	start = getdate(membership.proof_verified_start_date)
	expiry = membership.get("proof_verified_expiry_date")

	if _lifetime(membership_type):
		return

	if not expiry:
		frappe.throw(
			_(
				"{0} memberships run for a fixed period, so record the expiry date you can see on"
				" the document before approving this."
			).format(frappe.bold(membership_type.membership_type_name)),
			frappe.MandatoryError,
			title=_("Verified Expiry Needed"),
		)

	_assert_ordered(start, getdate(expiry), _("The dates you confirmed"))


# --- what the society confirmed --------------------------------------------


def verify(membership, start_date=None, expiry_date=None) -> None:
	"""Record what an approver read off the evidence. The only writer of these fields.

	Stamps who and when, so a verified date is always attributable — the pair of
	facts Phase 1's guardian consent keeps for the same reason. Nothing is saved
	here; the caller owns the write, which keeps this callable from inside
	another save.

	A lifetime membership takes no expiry, and one supplied is dropped rather
	than refused: the type is the authority on whether a membership ends, and an
	approver who typed a date into a field the form should not have shown them
	has not made a mistake worth failing their decision over.
	"""
	from vmmsx.member.services import membership as membership_service

	membership_type = membership_service.type_of(membership)

	membership.proof_verified_start_date = getdate(start_date) if start_date else None
	membership.proof_verified_expiry_date = (
		getdate(expiry_date) if expiry_date and not _lifetime(membership_type) else None
	)
	membership.proof_verified_by = frappe.session.user
	membership.proof_verified_on = now_datetime()


def verified_validity(membership, membership_type):
	"""The validity window the society confirmed, or None if it confirmed none.

	`None` is what puts `membership.activate()` back on its ordinary path — the
	fresh period starting today — and that is the right answer for every
	membership except a verified claim: an ordinary application, a renewal, and a
	clerk's proof entry all have nothing here to read.

	Returned as a pair rather than written onto the document, so this module
	never touches `valid_from` / `valid_to`. There is one writer of those and it
	is `activate()`.
	"""
	if not is_verified(membership):
		return None

	start = getdate(membership.proof_verified_start_date)

	if _lifetime(membership_type):
		return start, None

	expiry = membership.get("proof_verified_expiry_date")

	return start, getdate(expiry) if expiry else None


# --- DTOs -------------------------------------------------------------------


def claimed_dto(membership) -> dict | None:
	"""What the applicant said, for the approver's screen and the returned form.

	`None` when there is no claim, so a caller renders nothing rather than a
	block of empty fields — the same rule `review.py` states about the intake
	fields it deliberately does not show.
	"""
	if not has_claim(membership):
		return None

	return {field: _plain(membership.get(field)) for field in CLAIM_FIELDS}


def verified_dto(membership) -> dict | None:
	"""What the society confirmed, and who confirmed it."""
	if not is_verified(membership):
		return None

	return {
		"proof_verified_start_date": _plain(membership.get("proof_verified_start_date")),
		"proof_verified_expiry_date": _plain(membership.get("proof_verified_expiry_date")),
		"proof_verified_by": membership.get("proof_verified_by"),
		"proof_verified_on": membership.get("proof_verified_on"),
		# Whether the confirmed window has already closed, answered here rather
		# than left to a screen comparing dates. The approver is entitled to know
		# before they approve that what they are about to record is an expired
		# membership, and `activate()` will reach the same conclusion through
		# `membership.is_lapsed` — deriving it twice in two places is how the
		# warning and the outcome come to disagree.
		"expired": _has_passed(membership.get("proof_verified_expiry_date")),
	}


def _has_passed(value) -> bool:
	return bool(value) and getdate(value) < getdate(today())


def _plain(value):
	"""A stored value as something JSON and a date input both understand."""
	if value is None:
		return None

	return str(getdate(value)) if hasattr(value, "isoformat") else value
