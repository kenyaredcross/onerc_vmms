# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The programme of work — ERPNext's `Project`, read and written this app's way.

A society does not deploy volunteers to "a deployment". It runs a programme — a
flood response, a vaccination campaign, a season of branch first aid duty —
writes one or more terms of reference under it, and deploys people against
those.

**That container is ERPNext's `Project`, not a doctype of ours.** `VMMS Project`
used to be, and it has been retired: it reimplemented a quarter of `Project`
under a different name and got no timesheet roll-up, no cost centre, no invoice
totals, no project dashboard and no connection to anything else on the site for
the trouble. What vmmsx adds is the handful of things ERPNext genuinely has no
field for — the owning Geo Node, the donor, the risks and assumptions — and
`setup/project_fields.py` is the whole of that list.

**Two placements, and they are not the same question.** `company` is ERPNext's
and stays ERPNext's: the legal entity the money runs through, of which a
national society has one. `vmms_geo_node` is ACC-02: the branch, region or
office that owns the programme, of which a society has hundreds. Core's geo
scoping filters the register on the second; the accounts roll up through the
first. Neither replaces the other and both are mandatory.

**Who may open a programme where.** A coordinator may file one at a node their
own live access already covers, and nowhere else — checked on the server, in
`assert_may_anchor`, because a filtered picker is a convenience and not a
control. Somebody holding exactly one assignment gets that node filled in for
them; somebody holding several is asked, because guessing which of a person's
areas they meant is how a programme ends up in the wrong register. An
unrestricted user is unrestricted, which is the same exemption every other
scoped door in this app grants.

**A project decides nothing about a deployment.** It is the container a terms of
reference is written under, and containment is the whole of the relationship: a
Completed project keeps every deployment already run under it, and closing one
is not a way to stop work that is already in the field. The one rule this module
holds is `assert_open`, which stops a *new* terms of reference being written
under a programme that has ended.

**A deployment reaches its project through its terms.** There is no second link
and there must not be one: two paths to the same answer are two answers as soon
as somebody edits one of them.

**The statuses are ERPNext's four, not four of ours.** Open, On hold, Completed,
Cancelled. There is deliberately no transition table here, unlike the state
machines this app owns: `Project.status` is a standard field that ERPNext's own
screens, its `set_project_status` endpoint and a society's own native Workflow
may all move, and a private grammar layered over it would be a rule half the
site did not know about. What this module keeps is the closed set — a status
outside it is a typo, not a lifecycle — and one predicate, `is_open`, that says
which of the four still takes new work.
"""

import frappe
from frappe import _
from frappe.utils import getdate

from vmmsx.deployment.services import society
from vmmsx.setup.project_fields import GEO_NODE_FIELD

PROJECT_DOCTYPE = "Project"

# ERPNext's own four, spelled here so nothing in this app types one as a string
# literal and so a rename upstream fails loudly in one place.
STATUS_OPEN = "Open"
STATUS_ON_HOLD = "On hold"
STATUS_COMPLETED = "Completed"
STATUS_CANCELLED = "Cancelled"

STATUSES = (STATUS_OPEN, STATUS_ON_HOLD, STATUS_COMPLETED, STATUS_CANCELLED)

# Which of the four still take new terms of reference. **On hold does not**, and
# that is the deliberate reading: a society that has paused a programme has said
# so, and writing new work under a paused programme is the thing pausing it was
# supposed to stop. Restarting it is one field away and takes nothing with it.
OPEN_STATUSES = (STATUS_OPEN,)


def read(name: str):
	"""The project record, through the document cache. Treat as read-only."""
	return frappe.get_cached_doc(PROJECT_DOCTYPE, name)


# --- the status ------------------------------------------------------------


def assert_status(status: str | None) -> None:
	"""Throw unless `status` is one of ERPNext's four."""
	if status in STATUSES:
		return

	frappe.throw(
		_("{0} is not a project status. Expected one of: {1}.").format(
			frappe.bold(status), ", ".join(STATUSES)
		),
		frappe.ValidationError,
		title=_("Unknown Project Status"),
	)


def is_open(doc) -> bool:
	"""Does this project still take new terms of reference?

	An unset status counts as Open, because that is ERPNext's own default for a
	project nobody has moved.
	"""
	return (doc.status or STATUS_OPEN) in OPEN_STATUSES


def set_status(doc, target: str, reason: str | None = None) -> dict:
	"""Move a project's status and save it. Idempotent.

	Idempotent because asking for the status a project already has writes nothing
	and records nothing — which is what makes a double-clicked button harmless.
	"""
	if doc.status == target:
		return dto(doc)

	assert_status(target)
	doc.status = target
	doc.save()

	if reason:
		doc.add_comment("Comment", _("{0}. {1}").format(_(target), reason))

	return dto(doc)


def assert_open(name: str) -> None:
	"""Throw unless new work may still be written under this project.

	Checked when a terms of reference is written under a project, and never
	afterwards. A closed project keeps everything already run under it, because
	ending a programme must not erase the record that it happened. Same rule, and
	the same reason, as `terms.assert_active`.
	"""
	if not name:
		return

	doc = read(name)

	if is_open(doc):
		return

	frappe.throw(
		_("{0} is {1} and cannot take new terms of reference.").format(
			frappe.bold(doc.project_name or doc.name), frappe.bold(_(doc.status))
		),
		frappe.ValidationError,
		title=_("Project Closed"),
	)


# --- who may put a programme where -----------------------------------------


def scope_role() -> str | None:
	"""The society's own role for this, or None if it has not named one.

	A project reuses the *deployment* scope role rather than naming a setting of
	its own, and `hooks.py` says why at the registration: a society that has said
	who may see its deployments has already answered who may see the programmes
	they belong to, and a second field would let the two disagree.
	"""
	from onerc_core.society.services import config

	return config.settings().get(society.DEPLOYMENT_SCOPE_ROLE_FIELD) or None


def authorised_nodes(user: str | None = None) -> list[str]:
	"""Nodes where this user holds live access, without their descendants.

	The *choices* a coordinator is offered, which is a narrower list than the
	nodes they may reach: somebody assigned at a region may read every branch
	under it, and filing a programme against a particular branch they were never
	given is a different act from reading it. Sorted so a picker is stable.

	Empty for an unrestricted user as well, and that is not a contradiction —
	they are not choosing from a list, they are unrestricted. `default_node`
	and `assert_may_anchor` both check that first.
	"""
	from onerc_core.access.services import scope

	role = scope_role()

	if not role:
		return []

	return sorted(scope.live_assignment_nodes(user or frappe.session.user, role))


def default_node(user: str | None = None) -> str | None:
	"""The node to fill in for this user, or None if there is no reliable one.

	*Reliable* is doing the work in that sentence. One live assignment is an
	answer; two are a question, and filling in whichever came back first would
	quietly file a programme in the wrong branch's register on a day somebody was
	not reading carefully. So several nodes produce no default at all and the
	screen asks.

	An unrestricted user gets None for the same reason: they can file anywhere,
	so there is nothing to infer.
	"""
	from onerc_core.access.services import scope

	if scope.has_unrestricted_scope(user or frappe.session.user):
		return None

	nodes = authorised_nodes(user)

	return nodes[0] if len(nodes) == 1 else None


def may_anchor(geo_node: str | None, user: str | None = None) -> bool:
	"""May this user own a programme at this node?

	**Core's own enforcement answers it**, through the same registration that
	filters the register — so "may I see a project here" and "may I file one
	here" cannot come apart. Asking the scope service directly would be a second
	scope model in a module that has none, which is exactly what
	`tests/test_delegation.py` fails the build over.

	The question is asked of the user's whole reachable scope — the node plus
	everything beneath each assignment — because somebody who runs a region
	genuinely does run its branches, and a regional coordinator unable to file a
	programme at one of their own branches would be a rule nobody could work
	with. `authorised_nodes` is the narrower list, and it is for offering choices
	rather than for refusing them.

	An unresolvable role, or none configured, means nobody's authority over a
	project can be established — and core answers False, which is the only safe
	direction: granting on "we could not tell" is how an access layer becomes
	decorative.
	"""
	from onerc_core.access.services import enforcement

	if not geo_node:
		from onerc_core.access.services import scope

		return scope.has_unrestricted_scope(user or frappe.session.user)

	return enforcement.is_in_scope(PROJECT_DOCTYPE, geo_node, user)


def assert_may_anchor(geo_node: str | None, user: str | None = None) -> None:
	"""Throw unless this user may own a programme at this node.

	**On the server, and not only in the picker.** A filtered dropdown is a
	convenience; the request behind it can name any node on the site, and this is
	the sentence that answers one that does.
	"""
	if may_anchor(geo_node, user):
		return

	from vmmsx.deployment.services.placement import geo_path

	choices = authorised_nodes(user)

	if choices:
		frappe.throw(
			_(
				"You can open a programme of work at {0}, and this one names {1}. Choose one of"
				" your own areas."
			).format(
				frappe.bold(", ".join(geo_path(node) or node for node in choices)),
				frappe.bold(geo_path(geo_node) or _("nowhere")),
			),
			frappe.PermissionError,
			title=_("Outside Your Area"),
		)

	frappe.throw(
		_(
			"You have not been given an area to open programmes of work in. Ask an administrator"
			" to place you in one before filing this."
		),
		frappe.PermissionError,
		title=_("No Area Assigned"),
	)


def on_validate(doc, method=None) -> None:
	"""ACC-02 for a programme of work, enforced on ERPNext's own doctype.

	Wired through `doc_events` in `hooks.py` rather than by editing ERPNext's
	controller, which is locked decision 4: a product pushing its rules into the
	shared source is how the source stops being shared.

	Two rules, and they are the same two `VMMS Deployment Request` states for
	itself. **It is somewhere** — said out loud here as well as by the custom
	field's mandatory flag, so a coordinator gets a sentence about placement
	rather than a field name. **It is somewhere you run** — checked only when the
	anchor is new or has moved, because re-checking it on every save would mean a
	coordinator whose assignment ends can no longer save a typo fix on a
	programme they filed last year, and because moving a programme to another
	branch is the act the rule is actually about.
	"""
	node = doc.get(GEO_NODE_FIELD)

	if not node:
		frappe.throw(
			_(
				"A programme of work must be anchored to a place in the organisation before it can"
				" be saved. An unplaced project cannot be seen by geo scoping, so it would exist"
				" with nobody able to open it."
			),
			frappe.MandatoryError,
			title=_("Missing Geo Anchor"),
		)

	before = doc.get_doc_before_save() if not doc.is_new() else None

	if before and before.get(GEO_NODE_FIELD) == node:
		return

	assert_may_anchor(node)


def default_company() -> str | None:
	"""The Company a new project belongs to when the caller names none.

	ERPNext makes Company mandatory and a society has one, so asking a
	coordinator for it on every screen is a question with a single possible
	answer. Read through ERPNext's own default rather than by picking a row, so a
	site that has set a global default gets it; a site with exactly one Company
	gets that one; and a site with several and no default gets `None`, which
	surfaces as ERPNext's own mandatory message rather than as a guess.
	"""
	default = frappe.defaults.get_defaults().get("company")

	if default and frappe.db.exists("Company", default):
		return default

	companies = frappe.get_all("Company", limit=2, pluck="name")

	return companies[0] if len(companies) == 1 else None


# --- creating one ----------------------------------------------------------


def create(
	project_name: str,
	geo_node: str,
	start_date=None,
	end_date=None,
	summary: str | None = None,
	notes: str | None = None,
	status: str | None = None,
	company: str | None = None,
	donor: str | None = None,
	funding_reference: str | None = None,
	funding_status: str | None = None,
):
	"""Insert a project. An ordinary insert, deliberately.

	No elevation: core's query condition runs on the anchor, so a coordinator
	cannot read a programme outside their own area, and `assert_may_anchor`
	refuses one being *written* outside it. The refusal comes from the same
	permission layer that decides everything else about placement.

	`summary` is written to ERPNext's own `notes` — the story of the project,
	printed at the head of every terms of reference under it — and this app's
	`notes` to `vmms_planning_notes`, which is the planning caveat beside the
	risks and assumptions. Two fields, two purposes, and neither is a duplicate
	of the other; `dto` reads them back under the same two names.
	"""
	if not geo_node:
		# ACC-02 restated at the boundary rather than left to the mandatory check,
		# so a caller gets a sentence about placement instead of a field name.
		frappe.throw(
			_("A project must be anchored to a place in the organisation before it can be saved."),
			frappe.MandatoryError,
			title=_("Where Is This Project?"),
		)

	assert_may_anchor(geo_node)

	if status:
		assert_status(status)

	doc = frappe.get_doc(
		{
			"doctype": PROJECT_DOCTYPE,
			"project_name": project_name,
			"company": company or default_company(),
			GEO_NODE_FIELD: geo_node,
			"status": status or STATUS_OPEN,
			"expected_start_date": getdate(start_date) if start_date else None,
			"expected_end_date": getdate(end_date) if end_date else None,
			"notes": summary,
			"vmms_planning_notes": notes,
			"vmms_donor": donor,
			"vmms_funding_reference": funding_reference,
			"vmms_funding_status": funding_status,
		}
	)
	doc.insert()

	return doc


# --- describing one --------------------------------------------------------


def dto(doc) -> dict:
	"""One project, as an explicit dict. Built field by field.

	Never the Document: `Project` carries forty-odd fields, most of them
	accounting roll-ups nobody on a volunteering screen asked for, and handing
	the record over would turn every upstream schema change into a change to this
	app's API.

	The path is read through `placement.geo_path` rather than straight off the
	adapter, so a project whose anchor was deleted underneath it is one
	odd-looking row instead of a register that refuses to open. That module says
	why.

	`summary` is ERPNext's `notes` with its markup taken off. The field is a Text
	Editor because that is what ERPNext ships, and every reader of this key — a
	list row, a breadcrumb, the head of a printed terms of reference — wants a
	sentence rather than a fragment of HTML.
	"""
	from vmmsx.deployment.services.placement import geo_path

	return {
		"name": doc.name,
		"project_name": doc.project_name,
		"status": doc.status or STATUS_OPEN,
		"is_open": is_open(doc),
		"company": doc.company,
		"geo_node": doc.get(GEO_NODE_FIELD),
		"geo_path": geo_path(doc.get(GEO_NODE_FIELD)),
		"start_date": str(doc.expected_start_date) if doc.expected_start_date else None,
		"end_date": str(doc.expected_end_date) if doc.expected_end_date else None,
		"summary": frappe.utils.strip_html(doc.notes or "").strip() or None,
		"notes": doc.vmms_planning_notes,
		"priority": doc.priority,
		"percent_complete": frappe.utils.flt(doc.percent_complete),
		"project_type": doc.project_type,
		"donor": doc.vmms_donor,
		"funding_reference": doc.vmms_funding_reference,
		"funding_status": doc.vmms_funding_status,
		"risks": [
			{
				"risk": row.risk,
				"likelihood": row.likelihood,
				"impact": row.impact,
				"responsible": row.responsible,
				"mitigation": row.mitigation,
			}
			for row in (doc.get("vmms_risks") or [])
		],
		"assumptions": [
			{
				"assumption": row.assumption,
				"still_holds": bool(row.still_holds),
				"notes": row.notes,
			}
			for row in (doc.get("vmms_assumptions") or [])
		],
		"created_on": str(doc.creation) if doc.creation else None,
	}
