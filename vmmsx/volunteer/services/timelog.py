# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Time logs — two structural kinds, one dispatch table, and one ownership rule.

A `VMMS Time Log` records that a volunteer served time somewhere on some day.
`log_type` says which *kind* of log it is, and that is the only field on the
record that changes what the server will accept:

    general       volunteering that stands on its own — training, an open day,
                  office support. It may never carry a deployment.
    deployment    time served on a specific deployment. It must name one, and
                  the volunteer must be on that deployment's roster.

**Why the kinds are code and the categories are configuration.** Each value of
`log_type` names a different validation rule, so a society adding a third value
would produce a log that nothing knows how to check — the same reason approval
*states* are code while approval *stages* are configuration. What a society
genuinely wants to vary is how it classifies volunteering for its own reporting,
and that is `VMMS Time Log Category`: an open vocabulary, extended freely, on
which **no code anywhere branches**.

**One dispatch table, not scattered comparisons.** `_VALIDATE` below is keyed by
the configuration value, exactly as `member/services/approval.py` keys `_BEGIN`
and `_SETTLED` by `approval_mode`. Adding a kind is adding an entry and writing
its rule; it is never adding an `if` to a caller. Outside this module nothing
compares `log_type` to anything.

**What every log shares, whatever its kind.** The geo anchor (ACC-02) and the
hours are checked *before* the dispatch, so a deployment log with no anchor is
refused for the anchor rather than for anything about deployments. Every log is
somewhere: an unplaced log is invisible to geo scoping and cannot be reported on
by the branch whose work it was.

**The ownership rule, which the deployment module finished.** A deployment log
names a `VMMS Deployment` and is accepted only if that deployment's roster lists
this volunteer. The check runs on the server, at save, on every path — the desk form,
the API, a script — because the point of it is that participation cannot be
fabricated by a caller who simply names a deployment. It is *ownership* scoping,
not geo scoping, and the difference is the substance: being correctly placed in
the right county does not make somebody a participant.

The rule itself, and the roster it reads, live in
`deployment/services/participation.py`. This module asks; it does not own the
answer, and it holds no second copy of what participation means.
"""

import frappe
from frappe import _
from frappe.utils import flt

TIME_LOG_DOCTYPE = "VMMS Time Log"

TYPE_GENERAL = "general"
TYPE_DEPLOYMENT = "deployment"
LOG_TYPES = (TYPE_GENERAL, TYPE_DEPLOYMENT)

# A log of no time is not a record of anything, and one claiming more hours than
# a day holds is a typo rather than a very long shift. Both are universal, which
# is why they are here and not in a setting.
MIN_HOURS = 0.0
MAX_HOURS = 24.0


def kind(log) -> str:
	"""The log's structural kind, refusing one nobody defined."""
	configured = log.get("log_type")

	if configured in LOG_TYPES:
		return configured

	frappe.throw(
		_("{0} is not a time log type. Expected one of: {1}.").format(
			frappe.bold(configured), ", ".join(LOG_TYPES)
		),
		frappe.ValidationError,
		title=_("Unknown Log Type"),
	)


def validate(log) -> None:
	"""Everything a time log must satisfy. Called from the controller's `validate`.

	The shared rules first, then the kind's own. Order matters: a deployment log
	with no geo anchor is refused for the anchor, because ACC-02 is a property of
	the record existing and outranks anything a particular kind asks for.
	"""
	assert_anchor(log)
	assert_hours(log)

	_VALIDATE[kind(log)](log)


def assert_anchor(log) -> None:
	"""ACC-02 — every log is somewhere, whatever kind of log it is.

	The mandatory flag on the field already refuses an empty anchor at the
	framework level; this repeats the refusal in the app's own words, so the
	rule is enforced by something that states it rather than only by a JSON
	attribute somebody could clear.
	"""
	if log.get("geo_node"):
		return

	frappe.throw(
		_(
			"A time log must be anchored to a Geo Node. Every log happened somewhere: an unplaced"
			" log is invisible to geo scoping and cannot be reported on by the branch whose work"
			" it was."
		),
		frappe.MandatoryError,
		title=_("Missing Geo Anchor"),
	)


def assert_hours(log) -> None:
	hours = flt(log.get("hours"))

	if MIN_HOURS < hours <= MAX_HOURS:
		return

	frappe.throw(
		_("A time log records more than {0} and at most {1} hours. This one records {2}.").format(
			MIN_HOURS, MAX_HOURS, hours
		),
		frappe.ValidationError,
		title=_("Implausible Hours"),
	)


# --- general --------------------------------------------------------------


def _general(log) -> None:
	"""A general log is volunteering that stands on its own.

	It may never name a deployment. If the time was served on a deployment then
	it is deployment time, and filing it as general would put it outside every
	rule that governs deployment time — the ownership check most of all.
	"""
	if not (log.get("deployment") or "").strip():
		return

	frappe.throw(
		_(
			"A general time log carries no deployment. General volunteering is by definition not"
			" deployment time: file this as a deployment log, or clear the deployment."
		),
		frappe.ValidationError,
		title=_("Deployment On A General Log"),
	)


# --- deployment: the ownership rule ---------------------------------------


def _deployment(log) -> None:
	"""A deployment log names a deployment, and its volunteer is on that deployment.

	Two refusals, in this order, because they are two different mistakes. A log
	with no deployment is incomplete. A log naming a deployment the volunteer was
	not on is false, and it is false in the particular way this check exists to
	prevent: anybody who can file a time log can type a deployment's docname, and
	nothing about being placed in the right part of the tree makes somebody a
	participant.

	The roster question is asked of `participation`, which owns it, and is
	answered from the database rather than from anything the caller supplied.
	Imported here rather than at module scope because the two modules refer to
	each other: the deployment module is the one that knows what participation
	means, and the volunteer module is the one that knows what a time log is.
	"""
	from vmmsx.deployment.services import participation

	deployment = (log.get("deployment") or "").strip()

	if not deployment:
		frappe.throw(
			_(
				"A deployment time log names the deployment the time was served on. Without it there"
				" is nothing to check the volunteer's participation against, and participation is"
				" what makes this kind of log different from a general one."
			),
			frappe.MandatoryError,
			title=_("No Deployment Named"),
		)

	participation.assert_participant(deployment, log.get("volunteer"))


# --- the dispatch table ---------------------------------------------------
#
# Keyed by the configuration value. A kind is added by adding a row here and
# writing its rule, and never by adding a branch to a caller.

_VALIDATE = {
	TYPE_GENERAL: _general,
	TYPE_DEPLOYMENT: _deployment,
}


# --- reading --------------------------------------------------------------


def hours_served(volunteer: str, since=None, until=None) -> float:
	"""Total hours this volunteer has logged, optionally over a window.

	Sums whatever kinds exist; it does not name one. Deployment logs joined the
	total the day they started saving, without this function changing, which is
	what a discriminator handled by dispatch rather than by comparison buys.
	"""
	filters = {"volunteer": volunteer}

	if since and until:
		filters["activity_date"] = ("between", (since, until))
	elif since:
		filters["activity_date"] = (">=", since)
	elif until:
		filters["activity_date"] = ("<=", until)

	# Summed in Python rather than with a SQL aggregate: the framework's query
	# builder refuses a function written as a string, and a volunteer's own logs
	# are not a set worth reaching past it for.
	return flt(sum(flt(hours) for hours in frappe.get_all(TIME_LOG_DOCTYPE, filters=filters, pluck="hours")))


def summary(volunteer: str, limit: int = 10) -> dict:
	"""What this volunteer has given, totalled and with the latest logs listed.

	The coordinator's view needs both halves of the question. A total answers
	"has this person actually turned up"; the recent logs answer "and are they
	still turning up", which a total covering ten years cannot.

	**The per-kind breakdown names no kind.** It is built by grouping whatever
	`log_type` values the rows carry, so it reports deployment and general time
	separately without this function comparing `log_type` to anything. That is
	the same discipline `hours_served()` states: the kinds are dispatched on in
	one table in this module and nowhere else. A society that never files a
	deployment log simply gets one key back rather than two.

	The total is `hours_served()` rather than a sum of the rows read below,
	because those are only the most recent few. Two different numbers called
	"hours" on one screen is exactly the confusion that makes a report useless.
	"""
	rows = frappe.get_all(
		TIME_LOG_DOCTYPE,
		filters={"volunteer": volunteer},
		fields=["log_type", "hours"],
	)

	by_type = {}

	for row in rows:
		by_type[row["log_type"]] = flt(by_type.get(row["log_type"], 0)) + flt(row["hours"])

	return {
		"volunteer": volunteer,
		"total_hours": hours_served(volunteer),
		"log_count": len(rows),
		"hours_by_type": by_type,
		"recent": recent(volunteer, limit=limit),
	}


def recent(volunteer: str, limit: int = 10) -> list[dict]:
	"""The latest logs this volunteer filed, as explicit rows. Built field by field.

	Never the documents. A log carries an anchor, a category and free-text notes,
	and a DTO that handed back rows straight from the ORM would turn every future
	field on the doctype into part of this app's API.
	"""
	return [
		{
			"name": row["name"],
			"log_type": row["log_type"],
			"log_category": row["log_category"],
			"deployment": row["deployment"],
			"geo_node": row["geo_node"],
			"activity_date": row["activity_date"],
			"hours": flt(row["hours"]),
			"notes": row["notes"],
		}
		for row in frappe.get_all(
			TIME_LOG_DOCTYPE,
			filters={"volunteer": volunteer},
			fields=[
				"name",
				"log_type",
				"log_category",
				"deployment",
				"geo_node",
				"activity_date",
				"hours",
				"notes",
			],
			order_by="activity_date desc, creation desc",
			limit_page_length=limit,
		)
	]


def log_dto(log) -> dict:
	"""One time log, as an explicit dict. Built field by field.

	Never the Document: that would leak every field on the record, including
	ones nobody reviewed, and turn a schema change into an API change.
	"""
	from onerc_core.geo.services import adapter

	return {
		"name": log.name,
		"volunteer": log.volunteer,
		"log_type": log.log_type,
		"log_category": log.log_category,
		"deployment": log.deployment,
		"geo_node": log.geo_node,
		"geo_path": adapter.get_full_path(log.geo_node) if log.geo_node else None,
		"activity_date": log.activity_date,
		"hours": flt(log.hours),
		"notes": log.notes,
	}
