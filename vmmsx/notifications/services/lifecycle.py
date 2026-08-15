# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Telling an applicant what just happened to their own application.

Before this module the app sent no transactional mail at all: `frappe.sendmail`
appeared once, in `announce.py`, and a person who registered heard nothing until
somebody told them in person. This is the other half of registration.

**Driven by the state change, not by the verb.** Every service that moves an
application is idempotent and several of them are called repeatedly on purpose —
`engine.submit` re-syncs a queue, `application.submit` is re-asked to turn an
insert into a DTO. Hanging an email off any of those would send it again every
time. So the trigger is `on_update` comparing the state Frappe already loaded
before the save with the state after it: a save that did not move the
application sends nothing, and a save that moved it sends exactly one message.
That is the same reasoning `direct.py` gives for its own exactly-once — the
transition is the thing that happens once, so notification follows the
transition.

**States are code, so dispatching on them is allowed.** `_ON_ENTERING` is keyed
by `states.py`'s closed set, the same shape as `announce._URGENCY` and
`member.approval._BEGIN`. The rule this app enforces is that nothing branches on
a **stage label**, which is a society's word; a state is ours and there are
seven of them forever.

**Nothing here knows what a volunteer is.** The domain hands over a `subject`
dict — who to write to, what they are called, what the society calls this kind
of application, and optionally a card to attach. A third kind of registration is
a third caller.

**A missing address is not an error.** Somebody enrolled at a branch desk from a
paper form may have no email at all, and refusing the state change over it would
make an address a precondition for being approved. It is the same asymmetry
`announce.py` documents between the in-app copy and the email: they reach
different people on purpose.
"""

import re

import frappe
from frappe.email.doctype.email_template.email_template import get_email_template
from frappe.utils import get_url

from vmmsx.approvals import states
from vmmsx.notifications.seeds import lifecycle_emails

TEMPLATE_DOCTYPE = "Email Template"

# Which shipped message announces arrival in which state. Keyed by the state
# being *entered*; a state with no entry here is one nobody is written to about.
#
# Draft is in the table and is the "more information requested" case: the engine
# returns an application to Draft when an approver asks for something, which is
# the one way an application goes backwards. Draft is also where an application
# starts, and `notify` guards that with `previous`: entering Draft from nothing
# is somebody opening a form, not a decision.
_ON_ENTERING = {
	states.IN_REVIEW: lifecycle_emails.RECEIVED,
	states.SUBMITTED: lifecycle_emails.RECEIVED,
	states.APPROVED: lifecycle_emails.APPROVED,
	states.REJECTED: lifecycle_emails.REJECTED,
	states.DRAFT: lifecycle_emails.MORE_INFO,
}

# Submitted normally resolves to In Review inside the same transaction, so both
# map to the acknowledgement and only one of them is ever the state a save ends
# in. Belt and braces against a workflow whose stages all resolve nobody.
_ACKNOWLEDGEMENTS = (states.SUBMITTED, states.IN_REVIEW)


def install() -> dict:
	"""Seed the four shipped messages. Additive only, on every migrate.

	The welcome email's rules, for the welcome email's reasons: created when the
	site has none by that name and **never** edited afterwards, so a society that
	has reworded its acknowledgement keeps it through every deploy. Here rather
	than in a patch because a patch runs once per site by name and could not
	reach a site that migrated before these existed.
	"""
	created = []

	for template in lifecycle_emails.TEMPLATES:
		if frappe.db.exists(TEMPLATE_DOCTYPE, template["name"]):
			continue

		frappe.get_doc(
			{
				"doctype": TEMPLATE_DOCTYPE,
				"__newname": template["name"],
				"subject": template["subject"],
				# `use_html` is what makes Frappe read `response_html` rather than
				# the Text Editor field, so the Jinja conditionals in the body are
				# not rewritten by a rich-text editor's markup normalisation.
				"use_html": 1,
				"response_html": template["body"],
			}
		).insert(ignore_permissions=True)

		created.append(template["name"])

	return {"created": created, "repaired": _repair_broken_greeting()}


# What a `str.format` over a Jinja frame left behind: `{{ holder_name }}`
# collapsed to a literal `{ holder_name }`, which Jinja never substitutes.
#
# **Matched with a regex rather than a substring, and that is not fastidious.**
# The correct form *contains* the broken one — `{{ holder_name }}` has
# `{ holder_name }` inside it from its second character — so a plain
# `str.replace` repairs a broken template on the first migrate and corrupts the
# repaired one into `{{{ holder_name }}}` on the second. This runs on every
# deploy, so "works once" is the one thing it may not be. The lookarounds say
# "a single brace with no brace beside it", which is true of the damage and
# false of the fix.
BROKEN_GREETING = re.compile(r"(?<!\{)\{ (holder_name|society_name) \}(?!\})")


def _repair_broken_greeting() -> list[str]:
	"""Put the applicant's name back into messages already seeded broken.

	The rule for these templates is that they are created once and never edited
	again, so a society that has reworded its acknowledgement keeps it. This is
	the one exception, and it is narrow enough to be safe: it rewrites exactly
	the literal `{ holder_name }` that this app shipped by mistake, and only
	where that literal is present. A society that has reworded the greeting has
	no such string and is not touched; a society that has not was sending
	**"Dear { holder_name },"** to every applicant, which is not wording anybody
	chose and not wording anybody would want kept.

	Editing rather than replacing, so the rest of a reworded body survives.
	"""
	repaired = []

	for name in frappe.get_all(TEMPLATE_DOCTYPE, pluck="name"):
		doc = frappe.get_doc(TEMPLATE_DOCTYPE, name)
		fields = {"response_html": doc.get("response_html"), "response": doc.get("response")}
		changed = False

		for field, value in fields.items():
			if not value:
				continue

			fixed = BROKEN_GREETING.sub(r"{{ \1 }}", value)

			if fixed != value:
				doc.set(field, fixed)
				changed = True

		if not changed:
			continue

		doc.save(ignore_permissions=True)
		repaired.append(name)

	return repaired


def notify(doc, previous: str | None, current: str | None, subject: dict) -> str | None:
	"""Send the one message this state change calls for. Returns which, or None.

	`previous` and `current` are the approval state before and after the save.
	Nothing is sent when they are equal, when the new state has no message, or
	when the applicant has no address.

	Never raises. A message that could not be built or queued must not roll back
	the approval it was reporting: somebody being approved matters, and the email
	about it is how they hear rather than the thing itself.
	"""
	try:
		template = _message_for(previous, current)

		if not template:
			return None

		recipient = (subject.get("email") or "").strip()

		if not recipient:
			return None

		# **Rendered here, not handed to `sendmail(template=...)`.** That argument
		# means a *file* under `templates/emails/`, which is exactly what these are
		# not: they are `Email Template` records precisely so a society can edit
		# them without a deploy. `get_email_template` is the framework's own way of
		# rendering one, and it returns the subject and the body already rendered
		# against the context.
		rendered = get_email_template(template, _context(doc, subject))

		frappe.sendmail(
			recipients=[recipient],
			subject=rendered["subject"],
			message=rendered["message"],
			attachments=_attachments(subject),
			# Queued, like every other message this app sends. An SMTP hiccup is
			# not a reason for an approval to fail.
			now=False,
			reference_doctype=doc.doctype,
			reference_name=doc.name,
		)

		return template
	except Exception:
		# Deliberately broad and deliberately swallowed. See the docstring: the
		# alternative is a decision that rolls back because a mail server blinked.
		frappe.log_error(
			title="vmmsx: could not send a registration email",
			message=frappe.get_traceback(),
		)

		return None


def _message_for(previous: str | None, current: str | None) -> str | None:
	"""Which shipped message announces this move, if any.

	Three refusals, each for a different wrong send:

	1. **No move.** An ordinary save that touched something else.
	2. **Into Draft from nothing.** That is a form being opened, not an approver
	   asking for more. Only a move *back* into Draft is the latter, and the only
	   state you can reach Draft from is In Review.
	3. **Between the two acknowledgement states.** Submitted resolves to In
	   Review in the same transaction, and both mean "we have it"; without this
	   an applicant would get the same acknowledgement twice.
	"""
	if previous == current:
		return None

	if current == states.DRAFT and previous != states.IN_REVIEW:
		return None

	if current in _ACKNOWLEDGEMENTS and previous in _ACKNOWLEDGEMENTS:
		return None

	return _ON_ENTERING.get(current or "")


def _context(doc, subject: dict) -> dict:
	"""What the templates render against, built field by field.

	An explicit dict and never the document: a message body is written by an
	administrator, and handing it a live document would let a template reach into
	the ORM from inside the sandbox.
	"""
	from vmmsx.notifications.services import branding

	lockup = branding.lockup()

	return {
		"holder_name": subject.get("name") or "",
		"kind": subject.get("kind") or "",
		"record_id": doc.name,
		"geo_path": subject.get("geo_path") or "",
		"reason": _latest_reason(doc),
		"portal_url": get_url(subject.get("portal_path") or "/portal/dashboard"),
		"society_name": lockup.get("brand_name") or "",
	}


def _latest_reason(doc) -> str:
	"""What the approver said, from the decision they just recorded.

	Read off the document's own audit trail rather than passed in, so the reason
	in the email is by construction the reason on the record. The last row is the
	decision that caused this state change: the engine appends one and then moves
	the state, in that order, in the same save.
	"""
	rows = doc.get("approval_decisions") or []

	return (rows[-1].reason or "") if rows else ""


def _attachments(subject: dict) -> list[dict] | None:
	"""The card, when the domain built one. Frappe's own attachment shape.

	Built by the caller rather than here, because only the domain knows whether
	the thing that was just approved has a card and what it looks like. A domain
	that has none passes nothing and the message goes without.
	"""
	card = subject.get("attachment")

	if not card:
		return None

	filename, content = card

	return [{"fname": filename, "fcontent": content}]
