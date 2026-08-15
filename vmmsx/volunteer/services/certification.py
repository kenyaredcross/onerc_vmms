# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Certifications, and the one thing about them that is never stored: the lapse.

A held certification stores two dates. `completion_date` is entered by a human
or written by the learning seam. `expiry_date` is computed from it and the
type's configured validity period, recomputed on every save so that a society
lengthening a validity period brings the certifications already held along with
it.

**Whether a certification has lapsed is derived, every time it is asked.**

    lapsed  ==  expiry_date < the date you are asking about

There is no `lapsed` field on `VMMS Certification`, no `is_expired` flag, no
`status` column with "Lapsed" among its options, and no scheduled job that flips
anything. `is_lapsed()` below is the whole mechanism, and it takes an `as_of`
date so that the same certification reads as valid yesterday and lapsed tomorrow
without a single write in between.

That is not a stylistic preference. A stored flag has three failure modes this
design does not have: it is wrong between midnight and whenever the job runs; it
is wrong for every historical question ("was this volunteer certified on the day
of the deployment?"); and it is silently wrong forever if the job stops. A
deployment decision taken against a flag that a cron job forgot to set is
exactly the kind of failure that only shows up in an inquiry afterwards.

If lapse **notifications** are ever wanted, that is a future scheduled sweep
that reads this function and sends messages. Even then the deployment decision
must keep reading `deployability()` rather than anything the sweep wrote down.

**No certification name appears anywhere in this file.** Which certifications a
society runs, how long they last, and whether a lapse blocks deployment are all
rows in `VMMS Certification Type`.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, today

CERTIFICATION_DOCTYPE = "VMMS Certification"
CERTIFICATION_TYPE_DOCTYPE = "VMMS Certification Type"

# What `held()` reads. Explicit, so a field added to the doctype later does not
# start appearing in DTOs nobody reviewed.
_HELD_FIELDS = (
	"name",
	"certification_type",
	"completion_date",
	"expiry_date",
	"source_mapping",
	"reference_number",
)


def type_of(certification):
	"""The certification's type record, read through the document cache."""
	return frappe.get_cached_doc(CERTIFICATION_TYPE_DOCTYPE, certification.certification_type)


def type_name(certification_type: str) -> str:
	"""The society's own word for this certification, for showing a person.

	Read live rather than copied onto the held certification, so a society
	relabelling a type relabels it everywhere at once and no history is
	rewritten. Falls back to the key, which is never blank, because a screen
	naming nothing is worse than one naming a record.

	One function rather than the same `get_cached_value` written out at each
	call site: `deployability()` builds a reason from it and both API endpoints
	put it in a DTO, and three copies of a lookup are three places for the
	answer to drift.
	"""
	return (
		frappe.get_cached_value(CERTIFICATION_TYPE_DOCTYPE, certification_type, "certification_type_name")
		or certification_type
	)


# --- expiry: computed on save ---------------------------------------------


def expiry_for(certification_type, completion_date):
	"""When a certification of this type, completed on this date, runs out.

	`None` when the type never expires, and `None` is meaningful: a
	certification with no expiry can never read as lapsed, which is what a
	society means by a qualification that does not need renewing.
	"""
	days = cint(certification_type.validity_days)

	if days <= 0 or not completion_date:
		return None

	return add_days(getdate(completion_date), days)


def apply_expiry(certification) -> None:
	"""Write the computed expiry onto the document. Called from `validate`.

	On every save rather than only on insert, so that a society correcting a
	type's validity period from 730 days to 365 has that correction reflected
	the next time each certification is touched, instead of leaving a population
	of certifications expiring on a rule nobody uses any more.
	"""
	certification.expiry_date = expiry_for(type_of(certification), certification.completion_date)


# --- lapse: derived, every time -------------------------------------------


def is_lapsed(certification, as_of=None) -> bool:
	"""Has this certification run out, as at `as_of` (default today)?

	Accepts a Document or a plain row dict, because callers have both and the
	answer must not depend on which one they happen to be holding.

	Nothing is written, cached, or remembered. Ask again tomorrow and the answer
	may differ; ask about a date last year and it will answer about last year.
	"""
	expiry = certification.get("expiry_date")

	if not expiry:
		return False

	return getdate(expiry) < getdate(as_of or today())


def held(volunteer: str) -> list[dict]:
	"""Every certification this volunteer holds, as plain rows."""
	return frappe.get_all(
		CERTIFICATION_DOCTYPE,
		filters={"volunteer": volunteer},
		fields=list(_HELD_FIELDS),
		order_by="expiry_date asc",
	)


def lapsed(volunteer: str, as_of=None) -> list[dict]:
	"""The subset of those that have run out, as at `as_of`.

	Filtered in Python through `is_lapsed()` rather than with a `expiry_date <`
	filter in the query. Both would give the same list today; only this one
	keeps a single definition of what lapsed means, so a future change to the
	rule cannot leave a query somewhere still applying the old one.
	"""
	return [row for row in held(volunteer) if is_lapsed(row, as_of)]


# --- what a lapse actually costs ------------------------------------------


def deployability(volunteer, as_of=None) -> dict:
	"""Whether this volunteer may be deployed, and why not if not.

	Derived on every call from two things: the volunteer's own status, and the
	certifications they hold. Nothing about this is stored anywhere, so it
	cannot be stale and there is no job that has to have run for it to be right.

	The rule the module exists to express: **a volunteer whose certification has
	lapsed is not deployable, and stays Active while that is true.** Lapsing is
	not a disciplinary event and does not end somebody's volunteering — it makes
	them ineligible for the work that needed the certification until they renew
	it. Conflating the two would mean a first-aid refresher falling due quietly
	removed somebody from the register.

	Which types count is configuration: `blocks_deployment_when_lapsed` on
	`VMMS Certification Type`. A society may hold a certification as a record
	rather than a requirement, and then its lapsing blocks nothing.
	"""
	from vmmsx.volunteer.services.volunteer import STATUS_ACTIVE

	as_of = getdate(as_of or today())
	blocking = [row for row in lapsed(volunteer.name, as_of) if _blocks_deployment(row)]
	reasons = []

	if volunteer.status != STATUS_ACTIVE:
		reasons.append(_("This volunteer is {0}, not {1}.").format(_(volunteer.status), _(STATUS_ACTIVE)))

	for row in blocking:
		reasons.append(
			_("{0} lapsed on {1}.").format(
				type_name(row["certification_type"]),
				frappe.format(row["expiry_date"], {"fieldtype": "Date"}),
			)
		)

	return {
		"volunteer": volunteer.name,
		"as_of": as_of,
		"status": volunteer.status,
		"deployable": not reasons,
		"lapsed_certifications": [row["name"] for row in lapsed(volunteer.name, as_of)],
		"blocking_certifications": [row["name"] for row in blocking],
		"reasons": reasons,
	}


def is_deployable(volunteer, as_of=None) -> bool:
	"""The deployability question as a predicate, for a caller that wants a bool."""
	return deployability(volunteer, as_of)["deployable"]


def blocks_deployment(certification_type: str) -> bool:
	"""Is a lapse of this type the kind that stops somebody being deployed?

	A property of the *type*, not of a held certification, and configuration
	rather than code: `blocks_deployment_when_lapsed` on `VMMS Certification
	Type`. A society may hold a certification as a record rather than a
	requirement, and then its lapsing blocks nothing.

	Public because the coordinator's view needs it per row, to say which lapse
	costs something and which is merely out of date. It reads the same field
	`deployability()` reads, so a certification flagged on the screen and a
	certification blocking a deployment cannot come apart.
	"""
	return bool(
		frappe.get_cached_value(
			CERTIFICATION_TYPE_DOCTYPE, certification_type, "blocks_deployment_when_lapsed"
		)
	)


def _blocks_deployment(row: dict) -> bool:
	"""The same question asked of a held row, for the filters above."""
	return blocks_deployment(row["certification_type"])


# --- writing one ----------------------------------------------------------


def record(volunteer: str, certification_type: str, completion_date, **fields):
	"""Create or update the volunteer's certification of this type. Idempotent.

	One row per volunteer per type: a renewal moves the completion date on the
	row that is already there rather than adding a second, so "which of these
	two is current" is a question the schema does not allow anybody to ask.

	Returns the certification document either way.

	**Both writes below bypass permissions, and this is the justification.** The
	caller that matters is the learning seam, which runs inside the learner's own
	save of another app's document: a volunteer finishing a course holds no write
	permission on the society's certification register, and should not need any
	in order to have finished a course. Nothing the learner supplied reaches a
	field — the type comes from a `VMMS Course Mapping` an administrator wrote,
	and the expiry is computed from that type's configured validity period. A
	human recording a certification by hand goes through the desk form and is
	checked normally; this path is the seam's.
	"""
	existing = frappe.db.get_value(
		CERTIFICATION_DOCTYPE,
		{"volunteer": volunteer, "certification_type": certification_type},
		"name",
	)

	values = {"completion_date": getdate(completion_date), **fields}

	if not existing:
		return frappe.get_doc(
			{
				"doctype": CERTIFICATION_DOCTYPE,
				"volunteer": volunteer,
				"certification_type": certification_type,
				**values,
			}
		).insert(ignore_permissions=True)

	certification = frappe.get_doc(CERTIFICATION_DOCTYPE, existing)
	changed = False

	for field, value in values.items():
		if certification.get(field) != value:
			certification.set(field, value)
			changed = True

	if changed:
		certification.save(ignore_permissions=True)

	return certification
