# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Renewal — a NEW membership record, never an edit of the old one.

Renewing is applying again: same member, same branch, a new (or freely chosen)
membership type, for a new period. The prior membership is left exactly as it
was — still Expired, still holding its own valid_from/valid_to — and the new
record carries a `renews` Link back to it, so the chain ("2027 renews 2026") is
traceable without either row having to change.

**No new payment or activation logic.** The renewal record is put into motion
through `membership.submit()`, the exact function a first application goes
through: `payment.request()` asks for its fee, `approval.begin()` starts
whatever its type's approval_mode requires, and `on_payment_confirmed` /
`try_activate()` settle it exactly as they would any other membership. A
renewal is not a special kind of membership; it is an ordinary membership that
happens to name what it replaces.

**Renewable only once a membership is no longer current.** Renewing an active
membership early would create two live periods for the same branch and reopen
the early-payment/refund problem MEM-01's activation predicate was built to
avoid — a membership is a single validity window with a single fee attached to
it, and stacking a second one on top of a live one has no clean way to unwind
if the first is later cancelled or refunded. So renewal opens only once a
membership is effectively past its validity: `membership_status` is Expired
outright, or it is still Active in the database but its own `valid_to` has
already passed — the ordinary window between a membership actually lapsing and
the daily `expire_lapsed()` job noticing.
"""

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.utils import getdate, today

from vmmsx.member.services import certificate
from vmmsx.member.services import membership as membership_service

MEMBERSHIP_DOCTYPE = "VMMS Membership"


# --- the after-expiry-only rule --------------------------------------------


def is_lifetime(membership) -> bool:
	"""Is this a membership that never ends? Asked of its type, not its dates."""
	return membership_service.is_lifetime(membership_service.type_of(membership))


def is_renewable(membership, as_of=None) -> bool:
	"""Is this membership past its validity, and so eligible to be renewed?

	True for two states, and no others: Expired outright, or Active with a
	`valid_to` that has already passed — the pre-expire-job window, where the
	membership is current in name only. A still-current Active membership, a
	Draft, or one Awaiting Payment or Approval is not renewable: there is
	nothing yet to renew *from*.

	**A lifetime membership is never renewable**, and that is checked first,
	against the type. It would come out false anyway — an active lifetime
	membership has no `valid_to` for the comparison below to find — but only by
	accident of the date test, and a lifetime membership that somebody moved to
	Expired by hand would then read as renewable. Renewal buys another period,
	and a membership with no period has none to buy.

	**`as_of` exists so that a page asking several date-derived questions gets
	one answer to all of them.** Left unset it is today, which is what every
	caller wanted before it existed and still wants. The coordinator's dossier
	resolves one date for the whole screen and hands it here: without that, a
	membership could be shown as lapsed by the row that derives lapse and as not
	yet renewable by the button beside it, because the two asked on either side
	of midnight. That is the nested-derivation bug this parameter closes, and
	`member/tests/test_dossier.py` pins it.
	"""
	if is_lifetime(membership):
		return False

	if membership.membership_status == membership_service.STATUS_EXPIRED:
		return True

	if membership.membership_status == membership_service.STATUS_ACTIVE:
		return bool(membership.valid_to) and getdate(membership.valid_to) < getdate(as_of or today())

	return False


def assert_renewable(membership) -> None:
	"""Refuse a renewal attempt on a membership that is still current.

	Deliberate: paying to renew a membership that has not lapsed yet raises an
	early-payment/refund problem this module does not try to solve. The refusal
	is the solution.
	"""
	if is_renewable(membership):
		return

	# Two refusals rather than one, because they are different facts. "Not yet"
	# invites somebody to come back later; a lifetime membership has no later.
	if is_lifetime(membership):
		frappe.throw(
			_(
				"{0} is a lifetime membership. It has no end date, so there is no period to renew"
				" and nothing to renew it for."
			).format(frappe.bold(membership.name)),
			frappe.ValidationError,
			title=_("Nothing To Renew"),
		)

	frappe.throw(
		_(
			"{0} is still current and has not lapsed. Renewal is only available once a membership"
			" has expired, so that a renewal never overlaps the period it replaces."
		).format(frappe.bold(membership.name)),
		frappe.ValidationError,
		title=_("Not Yet Renewable"),
	)


# --- the renewal itself -----------------------------------------------------


def renew(prior, membership_type: str | None = None) -> dict:
	"""Renew `prior`: a brand-new membership, same member, same branch.

	`prior` is a loaded, permission-checked document — this function trusts
	nothing about *who* is asking beyond what its caller already established by
	handing it a document at all. `member` and `geo_node` are read off `prior`
	and never accepted as arguments, so there is nothing here a caller could
	pass to renew somebody else's membership under a different name. The type
	defaults to the prior membership's own, matching MEM-02's document contract
	either way: `membership.submit()` reads whichever type ends up on the new
	record and dispatches on its `approval_mode`, exactly as it does for a
	first application.

	Two ways to be entitled to write the new row, mirroring the two ways
	`api/member.py::_readable` admits a caller to read the prior one:

	1. **The holder, renewing their own.** A self-service member holds no
	   create permission on VMMS Membership — there is no web form here to lean
	   on for a bypass the way first registration has
	   (`registration/services/intake.py`), because renewal is an API action,
	   not a page. The elevation below is scoped exactly as narrowly as that
	   one is: it writes one new membership, for the same member and the same
	   branch `prior` already named, and nothing else. The caller's entitlement
	   to *this* action was already established by whatever proved them the
	   holder of `prior` (`api/member.py::_is_holder`, asked through the same
	   `certificate.owner_user` this module asks).
	2. **An authorised coordinator**, exactly as `apply_for_membership` admits
	   a clerk: an ordinary, checked `create` permission on VMMS Membership. No
	   elevation — a coordinator who cannot create a membership cannot renew
	   one either.
	"""
	assert_renewable(prior)

	renewal = frappe.get_doc(
		{
			"doctype": MEMBERSHIP_DOCTYPE,
			"member": prior.member,
			"membership_type": membership_type or prior.membership_type,
			"geo_node": prior.geo_node,
			"renews": prior.name,
		}
	)

	if _is_holder(prior):
		with _as_renewing_member():
			# See point 1 above: elevation scoped to exactly one new row, for
			# exactly the member and branch `prior` already named.
			renewal.insert(ignore_permissions=True)

			return membership_service.submit(renewal)

	frappe.has_permission(MEMBERSHIP_DOCTYPE, ptype="create", throw=True)
	renewal.insert()

	return membership_service.submit(renewal)


def _is_holder(membership) -> bool:
	"""Is the session user the person `membership` belongs to?

	Asked of `certificate.owner_user`, the same function `api/member.py`'s own
	holder check uses, so the two cannot drift into disagreeing about who a
	membership belongs to.
	"""
	user = frappe.session.user

	if not user or user == "Guest":
		return False

	return certificate.owner_user(membership) == user


@contextmanager
def _as_renewing_member():
	"""Run one renewal's creation and submission as the system.

	Justified narrowly, the same way `member.py::_as_system()` and
	`registration/services/intake.py::as_system()` are: a self-service member
	holds no create or write permission on VMMS Membership, and requiring one
	just to renew their own membership would mean handing every member a
	doctype-level grant in order to do the one thing this endpoint exists for.
	The block this wraps writes exactly one membership, for exactly the member
	and branch the entitlement check already proved this caller may act for.
	"""
	previous = frappe.session.user
	frappe.set_user("Administrator")

	try:
		yield
	finally:
		frappe.set_user(previous)
