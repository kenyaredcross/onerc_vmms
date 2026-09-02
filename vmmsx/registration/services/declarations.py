# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What an applicant agreed to, asked and recorded.

The sibling of `questions.py`, and deliberately its twin in shape: configuration
in a doctype, a record on the registration, and the record snapshots what it was
about so that a decided application can always be read as it stood. Everything
that file says about why a society's own content lives in records rather than in
source applies here word for word.

**Nothing here names a registration.** `applies_to` is the governed doctype, the
same shape `VMMS Application Question.asked_on` and `VMMS Approval Workflow.
workflow_for` use, so the volunteer application and a future membership consent
are two callers of one service rather than two code paths.

**An acceptance is frozen the moment it is made.** This is the one rule that
differs from questions, and it is the reason this module exists rather than a
`field_type` of "Declaration" on a question. An answer may be revised while a
draft is open — somebody changes their mind about which languages they speak,
and the latest answer is the true one. A consent is not like that. It is an act
performed at a moment, against a particular text, and what makes it worth
anything is that neither the moment nor the text can move afterwards. So
`apply()` leaves a row that is already accepted exactly as it is: same
timestamp, same version, same wording. Withdrawing consent replaces the row;
re-giving it records a new acceptance against whatever the text says now.

**Declining is recorded, not merely absent.** A row is written for every
declaration the applicant was shown, whether or not they agreed to it. "We asked
and they said no" and "we never asked" are different facts about a consent
register, and only one of them can be reconstructed from silence.

**Required is checked at submission, not at insert.** A draft with an unticked
box is a person part-way through a form, and refusing to save it would lose them
the rest of what they typed. Same seam `assert_ready` already occupies for
identification and for the society's own questions.

**The wording is a separate record, and publishing it is an act.** A declaration
is the standing policy; `VMMS Declaration Version` is what it said on a given
day, and it is submittable so that published wording cannot be edited afterwards
by anybody, including whoever wrote it. A version may hold the words or point at
a page on the society's own website — a national society whose legal team owns
the web page will not maintain a second copy here — and an acceptance records
which of the two it was, because an address is a weaker record than the words and
the register should not imply otherwise.

**A declaration added today is never applied backwards.** `assert_accepted`
reads the rows on the document, not the live declaration list, when deciding
whether an application that has already been submitted is complete — a society
adding a fifth declaration in March must not invalidate every application
submitted in February.
"""

import frappe
from frappe import _
from frappe.utils import cstr, now_datetime

from vmmsx.registration.seeds import declarations as seeds

DECLARATION_DOCTYPE = "VMMS Declaration"
VERSION_DOCTYPE = "VMMS Declaration Version"

# A version that holds its own wording, and one that points at a page the
# society publishes elsewhere. Two values, both ours, so a screen may branch on
# them — the rule this app enforces is that nothing branches on a *society's*
# word, and neither of these is one.
SOURCE_TEXT = "Text"
SOURCE_LINK = "Link"

# The field every registration carries its acceptances in. One name, so a
# doctype opts in by adding the table under it and this module needs no register
# of who has one. Same arrangement as `questions.ANSWER_FIELD`.
ACCEPTANCE_FIELD = "declarations"


def shows(doctype: str) -> bool:
	"""Does this doctype carry an acceptance table at all?

	Asked before anything else touches `doc.declarations`, so a registration that
	has not opted in is silently unaffected rather than throwing on a field it
	does not have.
	"""
	return bool(frappe.get_meta(doctype).get_field(ACCEPTANCE_FIELD))


def shown_on(doctype: str) -> list[dict]:
	"""The active declarations for `doctype`, in the order a form should draw them.

	An explicit DTO per declaration, built field by field, so a field added to
	the doctype does not silently become part of this app's API.
	"""
	if not frappe.db.exists("DocType", DECLARATION_DOCTYPE):
		# Mid-migrate on a site that has not synced this module yet. No
		# declarations is the honest answer, and it keeps registration working.
		return []

	rows = frappe.get_all(
		DECLARATION_DOCTYPE,
		filters={"applies_to": doctype, "is_active": 1},
		fields=[
			"name",
			"title",
			"version",
			"body",
			"source",
			"external_url",
			"is_required",
			"sequence",
		],
		order_by="sequence asc, creation asc",
	)

	# The mirror on the declaration answers *what* is published; this answers
	# *which record* published it, and an acceptance stores both. One query for
	# the whole list rather than one per declaration, because a form draws four
	# of these and a round trip each is four round trips for one screen.
	versions = _current_versions([row.name for row in rows])

	return [
		{
			"name": row.name,
			"title": row.title,
			"version": row.version,
			# `Text` for a declaration published before versions existed and not
			# yet migrated. Nothing here guesses at a URL, so the honest default
			# is the one that means "the wording is the record".
			"source": row.source or SOURCE_TEXT,
			"body": row.body,
			"external_url": row.external_url,
			"declaration_version": versions.get(row.name),
			"is_required": bool(row.is_required),
		}
		for row in rows
	]


def apply(doc, accepted) -> list[str]:
	"""Record what the applicant agreed to. Returns the keys now accepted.

	`accepted` may be a mapping of declaration name to something truthy, or a
	plain list of the names that were ticked — a set of checkboxes naturally
	produces the second, and a form that wants to say "shown and refused"
	explicitly has the first. Either may arrive as a JSON string, which is what
	a form-encoded call to a whitelisted method looks like.

	The table is rebuilt from the live declaration list rather than merged, so a
	declaration deactivated since the draft was started stops being shown. What
	is *not* rebuilt is an acceptance that already stands — see the module
	docstring.
	"""
	if not shows(doc.doctype):
		return []

	wanted = _wanted(accepted)
	standing = {row.declaration: row for row in doc.get(ACCEPTANCE_FIELD) or []}

	doc.set(ACCEPTANCE_FIELD, [])
	now_accepted = []

	for declaration in shown_on(doc.doctype):
		name = declaration["name"]
		is_accepted = name in wanted
		held = standing.get(name)

		if is_accepted and held and held.accepted:
			# Frozen. The applicant agreed to this text at this moment, and
			# neither the wording nor the timestamp is ours to refresh because
			# they saved the form again.
			doc.append(ACCEPTANCE_FIELD, _frozen(held))
			now_accepted.append(name)

			continue

		doc.append(
			ACCEPTANCE_FIELD,
			{
				"declaration": name,
				# Snapshots. See `VMMS Declaration Acceptance`: a consent is worth
				# nothing if the thing consented to can be rewritten afterwards.
				"title": declaration["title"],
				"version": declaration["version"],
				# The version record itself, so "which wording" is answerable by
				# opening a document rather than by matching a label against a
				# history somebody has to reconstruct.
				"declaration_version": declaration["declaration_version"],
				# What kind of record this is. A `Link` acceptance carries an
				# address and no words, and that difference has to survive on the
				# row — an empty `body_snapshot` beside a stored address is not a
				# snapshot that failed, it is the only snapshot there was to take.
				"source": declaration["source"],
				"body_snapshot": declaration["body"],
				"external_url": declaration["external_url"],
				"accepted": 1 if is_accepted else 0,
				"accepted_on": now_datetime() if is_accepted else None,
			},
		)

		if is_accepted:
			now_accepted.append(name)

	return now_accepted


def _wanted(accepted) -> set[str]:
	"""The set of declaration names the caller says were accepted."""
	if isinstance(accepted, str):
		accepted = frappe.parse_json(accepted)

	if not accepted:
		return set()

	if isinstance(accepted, dict):
		return {name for name, value in accepted.items() if _is_yes(value)}

	return {cstr(name) for name in accepted if cstr(name)}


def _is_yes(value) -> bool:
	"""Anything a form can put in a checkbox: True, "true", 1, "on"."""
	if isinstance(value, bool):
		return value

	return cstr(value).strip().lower() in ("1", "true", "yes", "on")


def _frozen(row) -> dict:
	"""One standing acceptance, copied forward unchanged."""
	return {
		"declaration": row.declaration,
		"title": row.title,
		"version": row.version,
		"declaration_version": row.declaration_version,
		"source": row.source,
		"body_snapshot": row.body_snapshot,
		"external_url": row.external_url,
		"accepted": 1,
		"accepted_on": row.accepted_on,
	}


def assert_accepted(doc) -> None:
	"""Refuse a submission that leaves a required declaration unaccepted.

	Reads the rows on the document against the declarations *currently* shown,
	which is right at submission and wrong afterwards: this runs on the way in,
	while the applicant is still the person who can fix it.
	"""
	if not shows(doc.doctype):
		return

	accepted = {row.declaration for row in doc.get(ACCEPTANCE_FIELD) or [] if row.accepted}

	missing = [
		declaration["title"]
		for declaration in shown_on(doc.doctype)
		if declaration["is_required"] and declaration["name"] not in accepted
	]

	if not missing:
		return

	frappe.throw(
		_("This application cannot be submitted until you have accepted {0}.").format(
			frappe.bold(", ".join(missing))
		),
		frappe.MandatoryError,
		title=_("Declaration Not Accepted"),
	)


def accepted_of(doc) -> list[dict]:
	"""What this applicant agreed to, as DTOs an approver's screen can render.

	Reads the snapshots on the rows rather than the declarations behind them, so
	an application decided last year still displays the text that was actually
	agreed to.
	"""
	if not shows(doc.doctype):
		return []

	return [
		{
			"declaration": row.declaration,
			"title": row.title,
			"version": row.version,
			"declaration_version": row.declaration_version,
			# `Text` for an acceptance recorded before versions existed. Those
			# all carry wording, which is what that value means.
			"source": row.source or SOURCE_TEXT,
			"body": row.body_snapshot,
			"external_url": row.external_url,
			"accepted": bool(row.accepted),
			"accepted_on": row.accepted_on,
		}
		for row in doc.get(ACCEPTANCE_FIELD) or []
	]


# --- which wording is current ---------------------------------------------


def current_version(declaration: str) -> str | None:
	"""The published version of one declaration, or None if none is published.

	**The most recently published one that has not been withdrawn.** Not the
	highest version label: those are a society's own words — "2", "2.1",
	"March 2027" — and ordering them would mean this app deciding that "10"
	comes after "9", which is true of integers and false of the labels people
	actually use. `published_on` is stamped by the framework at submit and is the
	only ordering here that means anything.

	A declaration whose only version is still a draft has none published, and
	that is a real state rather than an error: somebody is part-way through
	writing next year's privacy notice.
	"""
	rows = _current_versions([declaration])

	return rows.get(declaration)


def _current_versions(names: list[str]) -> dict[str, str]:
	"""The published version of each of `names`, in one query.

	Ordered oldest first so that the dictionary comprehension leaves the newest
	standing — the same trick, and the same reason, as building a lookup from a
	single ordered read rather than one query per row.
	"""
	if not names:
		return {}

	if not frappe.db.exists("DocType", VERSION_DOCTYPE):
		# Mid-migrate on a site that has not synced this doctype yet. The mirror
		# on the declaration still answers what is published, so registration
		# keeps working and the acceptance simply records no version record.
		return {}

	rows = frappe.get_all(
		VERSION_DOCTYPE,
		filters={"declaration": ["in", sorted(set(names))], "docstatus": 1},
		fields=["name", "declaration", "published_on"],
		order_by="published_on asc, creation asc",
	)

	return {row.declaration: row.name for row in rows}


def sync_mirror(declaration: str) -> dict | None:
	"""Copy the published version onto the declaration. Returns what it wrote.

	Called from `VMMS Declaration Version` on submit and on cancel, which are the
	only two moments the answer can change.

	**Saved through the document rather than written as columns**, and that is
	not incidental. `VMMS Declaration` is `track_changes`, so this leaves a
	`Version` row saying the published wording moved — which is exactly the event
	an audit of a consent register is looking for, and a `db.set_value` would
	have made it the one change to a policy that left no trace. It also keeps a
	single writer: the mirror is derived in the controller's `validate` and
	nowhere else, so this function does not have to know which four fields it is.
	`test_correction_and_audit.TestNothingWritesAroundTheDocument` is the test
	that asks for this, and it asked the right question.

	`None` where nothing is published — a declaration whose only version was
	cancelled keeps the wording it last showed rather than being blanked, so a
	society that withdraws a version in error has not thereby erased what
	applicants were reading five minutes ago. The withdrawal is visible on the
	version; blanking the mirror would make it visible as a hole.
	"""
	values = published_values(declaration)

	if not values:
		return None

	document = frappe.get_doc(DECLARATION_DOCTYPE, declaration)
	document.save(ignore_permissions=True)

	return values


def published_values(declaration: str) -> dict | None:
	"""What the declaration's mirror fields should say, or None if nothing is published.

	Split out of `sync_mirror` because the mirror has two writers and they need
	the same answer: the version doctype pushes it on submit and cancel, and the
	declaration's own `validate` pulls it on every save. The second is what makes
	the fields *derived* rather than merely marked read-only — `read_only` on a
	DocField is a form-level hint and the server will happily store whatever a
	script or an API call puts in one.
	"""
	name = current_version(declaration)

	if not name:
		return None

	version = frappe.db.get_value(
		VERSION_DOCTYPE, name, ["version", "source", "body", "external_url"], as_dict=True
	)

	return {
		"version": version.version,
		"source": version.source,
		"body": version.body,
		"external_url": version.external_url,
	}


def publish(declaration: str, version: str, body: str | None = None, external_url: str | None = None):
	"""Write a version and publish it in one act. Returns the version document.

	The shape both the installer and the migration patch need, and the shape a
	society's own tooling would want: creating a draft and leaving it unpublished
	is a thing somebody does at a form, not a thing a script means to do.

	`source` is inferred from which of the two was given rather than passed,
	because a caller supplying an address and a source of `Text` is a mistake with
	no sensible reading, and one fewer argument is one fewer way to make it.
	"""
	document = frappe.get_doc(
		{
			"doctype": VERSION_DOCTYPE,
			"declaration": declaration,
			"version": version,
			"source": SOURCE_LINK if external_url else SOURCE_TEXT,
			"body": body,
			"external_url": external_url,
		}
	)

	document.insert(ignore_permissions=True)
	document.submit()

	return document


# --- installation ---------------------------------------------------------


def install() -> dict:
	"""Seed the shipped declarations. Additive only, on every migrate.

	The rules and the reasoning are `notifications/services/lifecycle.py::
	install`'s: created when the site has none by that key, and **never** edited
	afterwards, so a society that has had its legal officer rewrite these keeps
	the rewrite through every deploy.

	Here rather than in a patch for that module's other reason — a patch runs
	once per site by name, so a declaration added in a later release would never
	reach a site that had already migrated. Additive by construction, so a run on
	a site that already has them all costs one `exists` call each. That is what
	carries the membership-proof declaration onto a site that migrated before it
	existed, with no patch of its own.

	**No `_upgrade_untouched` counterpart, deliberately.** The email templates
	can safely replace shipped wording nobody has edited, because a better
	acknowledgement is strictly better for everyone. These are consents: people
	have agreed to this exact text, `VMMS Declaration` refuses a body change that
	does not move the version, and an installer that quietly rewrote the wording
	on a deploy would be doing the one thing this whole module exists to prevent.
	Improved shipped wording reaches an existing site as a new key or not at all.
	"""
	created = []

	for declaration in seeds.DECLARATIONS:
		key = declaration["declaration_key"]

		if frappe.db.exists(DECLARATION_DOCTYPE, key):
			continue

		frappe.get_doc(
			{
				"doctype": DECLARATION_DOCTYPE,
				"declaration_key": key,
				# Named on the seed rather than assumed here. This function used
				# to hardcode the volunteer application, which was true of every
				# declaration that existed and stopped being true the moment the
				# membership proof needed one.
				"applies_to": declaration["applies_to"],
				"title": declaration["title"],
				"sequence": declaration["sequence"],
				"is_required": 1,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		# The wording is published rather than typed onto the row: the shipped
		# text is version 1 of this policy, and it earns the same frozen record
		# every later wording will get. `sync_mirror` on submit is what puts the
		# body back onto the declaration for every reader that expects it there.
		publish(key, seeds.INITIAL_VERSION, body=declaration["body"])

		created.append(key)

	return {"created": created}
