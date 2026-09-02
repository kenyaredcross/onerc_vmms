# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What an approver reads before deciding a membership.

The volunteer side of the house has had this since Part 4 —
`volunteer/services/application.py::decision_dto` — and the membership side did
not, which had one very visible consequence: a coordinator opening a membership
in the review queue was shown a docname, a stage and a set of approve/decline
buttons, and no name. There is no way to approve somebody you cannot identify,
so this module is the missing half.

**Composed out of what already exists, never re-derived.** Three blocks, each
the DTO whose own service owns it:

    applicant    `dossier.identity_dto` — the person, read live from Red
                 Profile, the same block the member's own page shows
    membership   `dossier.membership_dto` — the type, the validity, the branch,
                 the payment picture and the certificate gate, all derived as
                 at one `as_of`
    answers      `questions.answers_of` — what this society asked beyond the
                 standard form, off the application's own snapshots

Nothing here computes a status, a lapse or a settlement. If this module and the
member's dossier page ever disagreed about whether a membership was paid for,
that would be two implementations of one question, which is exactly what
composing rather than merging avoids.

**There is deliberately no "as written on the form" block, and the reason is
worth recording so it is not helpfully added.** `VMMS Membership` carries
`applicant_first_name` and its neighbours, and showing them beside the Red
Profile block — what a clerk typed, against what the society holds — looks like
exactly the comparison an approver wants. It is not available to make.
`registration/services/intake.py::clear_intake` blanks every one of those fields
on **every** save of the document, having first absorbed their values into the
Red Profile: they are a transport into identity, not a record of anything, and a
saved membership always holds `None` in all five. Reading them here would draw a
row of empty fields on every screen and imply the society had recorded nothing.
The one answer to who somebody is stays where the identity model puts it.

**Permission is the caller's, and it happens before this is reached.**
`api/member.py::get_review` loads the membership through `_readable` first;
nothing in this module checks anything, in the same way `decision_dto` does not.
"""

import frappe
from frappe.utils import getdate, today

from vmmsx.member.services import dossier, proof
from vmmsx.registration.services import declarations, questions

MEMBERSHIP_DOCTYPE = "VMMS Membership"
MEMBER_DOCTYPE = "VMMS Member"


def decision_dto(membership, as_of=None) -> dict:
	"""Everything an approver needs about one membership, in one read.

	`as_of` is resolved once here and handed down, the same discipline
	`dossier.build` keeps: lapse, effective status and renewability are all
	comparisons against a date, and a screen that asked them either side of
	midnight would contradict itself in the way that is hardest to notice.
	"""
	as_of = getdate(as_of or today())
	member = _member_of(membership)

	return {
		"name": membership.name,
		"member": membership.member,
		"as_of": as_of,
		# `None` only for a membership whose member record has been removed out
		# from under it, which the register should not allow and which a screen
		# must still survive rather than render as a crash.
		"applicant": dossier.identity_dto(member) if member else None,
		"membership": dossier.membership_dto(membership, as_of),
		# The attachment a proof-of-payment membership stands on. Surfaced at the
		# top level rather than left inside the payment picture because it is the
		# single thing the approver of such a membership is actually here to look
		# at, and burying it two levels down is how it gets missed.
		"proof_attachment": membership.proof_attachment,
		"membership_source": membership.membership_source,
		# The two halves of an existing-membership proof, side by side and never
		# merged. This is the one screen where the distinction has to be visible:
		# the approver is looking at a document, at what somebody said about it,
		# and at what they themselves have written down — and a single "dates"
		# block would collapse the first two into the third.
		#
		# `claimed` is None for a clerk's proof entry, which asserts nothing;
		# `verified` is None until somebody has looked. Both render as nothing.
		"claimed": proof.claimed_dto(membership),
		"verified": proof.verified_dto(membership),
		"declarations": declarations.accepted_of(membership),
		"answers": questions.answers_of(membership),
	}


def _member_of(membership):
	"""The member document behind a membership, or None.

	`get_doc` without a permission check, on purpose and by the same rule
	`dossier.build` follows: the caller has already been allowed to read the
	membership, and `VMMS Member` is deliberately not geo-scopeable — a person is
	not at a place. The gate that matters was passed at the endpoint.
	"""
	if not membership.member or not frappe.db.exists(MEMBER_DOCTYPE, membership.member):
		return None

	return frappe.get_doc(MEMBER_DOCTYPE, membership.member)
