# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The coordinator's member register — people, within the caller's own scope.

The list a membership office actually works from: who are the members here, at
which branch, current or lapsed, and until when. It exists because the answer
was not available anywhere — `VMMS Member` carries no branch and no dates, and
the desk's own list view of it shows a column of `MEM-#####` beside a column of
`RP-#####`, which is a register of docnames rather than of people.

**A row is a membership, not a member**, and that is deliberate. Branch and
validity are facts about a membership; a person holding memberships at two
branches has two of each, and collapsing them into one row would mean choosing
which branch to show and which to hide. So somebody enrolled at two branches
appears twice, once per branch, and `member_count` beside the rows says how many
distinct people are in front of you. That is the multi-branch model this module
is built on, stated in the shape of the output rather than in a comment.

Scope is the floor, not a filter
--------------------------------

`search()` ends in `frappe.get_list`, which runs core's permission query
condition for `VMMS Membership`; `frappe.get_all` would skip it and is not used
here. Every argument this function takes **narrows** that result and none of
them widens it, so a coordinator cannot reach a member outside their geo scope
by naming a branch, a type or a status. Naming a `geo_node` they hold no
authority over returns nothing, because the scope condition still applies
underneath the filter.

That is the whole of the access model here, and it is why this module is where
it is: the register reads memberships, which *are* geo-anchored and *are*
registered as scopeable in `hooks.py`. `VMMS Member` itself is not scopeable and
could not be — it holds no Geo Node, because a person is not at a place, their
membership is. A register built by listing members first and looking up their
branches afterwards would have had no floor at all.

If a society has not configured its membership scope role, core fails closed and
this returns nothing. That is the correct answer rather than a bug: the setting
ships empty precisely so that memberships are unreadable until somebody decides
who may read them.

Identity is read, never joined
------------------------------

The names in this register come from Red Profile at the moment of asking, one
read for the whole page rather than one per row. Nothing is stored, nothing is
fetched onto a membership, and correcting somebody's name corrects it here on
the next refresh.
"""

import frappe
from frappe.utils import getdate, today

from vmmsx.member.services import membership as membership_service

MEMBERSHIP_DOCTYPE = "VMMS Membership"
MEMBER_DOCTYPE = "VMMS Member"
PROFILE_DOCTYPE = "Red Profile"

# How many scoped rows one search will read before paging them.
#
# The read is bounded here rather than by the caller's `limit` because
# `current_only` filters rows out *after* the query — see `search()`. It is a
# ceiling on work, not a page size, and a register that reaches it is a branch
# with more memberships than any coordinator scrolls through, which wants a
# report rather than a screen.
_READ_CEILING = 2000

# What the register reads off each membership. Named explicitly rather than
# fetched as documents: a register is a list of many rows, and pulling a full
# document per row to render four columns of it is both slower and a leak — the
# DTO below is built from exactly these and nothing else.
_ROW_FIELDS = (
	"name",
	"member",
	"membership_type",
	"geo_node",
	"membership_status",
	"valid_from",
	"valid_to",
	"membership_source",
)


def search(
	geo_node: str | None = None,
	status: str | None = None,
	membership_type: str | None = None,
	current_only: bool = False,
	as_of=None,
	limit: int = 100,
	offset: int = 0,
) -> dict:
	"""Members within the caller's scope, as rows a person can read.

	Every argument narrows; see the module docstring for why none of them can
	widen. `status` filters on the **stored** status because that is what the
	database can be asked about; `current_only` filters on the *effective* one,
	derived per row as at `as_of`, which is a question no query can answer and
	so is applied after the read.

	`as_of` is resolved once here and threaded into every row's derivation, the
	same rule the dossier follows and for the same reason.

	**Paging happens after that derived filter, not in the query, and it has to.**
	`current_only` removes rows the database already returned, so a `limit_start`
	handed to SQL would page through the *unfiltered* result and hand back short
	pages with rows missing between them — a pager that silently skips people.
	So the scoped read is taken up to a ceiling, the derivation runs, and only
	then is the page cut. `total` is the count after filtering, which is what the
	pager labels itself with.

	The ceiling is what bounds the read rather than `limit`. A register is a
	branch's membership list; reading it and slicing in Python is the honest cost
	of a filter no query can express.
	"""
	as_of = getdate(as_of or today())
	filters = {}

	if status:
		filters["membership_status"] = status

	if membership_type:
		filters["membership_type"] = membership_type

	if geo_node:
		# Through core's adapter, never a query against the geo tables: which
		# nodes sit beneath one is core's question and this app has no second
		# answer to it.
		from onerc_core.geo.services import adapter

		filters["geo_node"] = ("in", [geo_node, *adapter.get_descendants(geo_node)])

	# `get_list`, never `get_all` — this is the line the scope rests on.
	found = frappe.get_list(
		MEMBERSHIP_DOCTYPE,
		filters=filters,
		fields=list(_ROW_FIELDS),
		order_by="valid_to desc, creation desc",
		limit=_READ_CEILING,
	)

	# Resolved once for the whole read, not once per row — see `_names_for`.
	names = _names_for(found)
	type_names = _type_names_for(found)

	rows = [_row(record, as_of, names, type_names) for record in found]

	if current_only:
		rows = [row for row in rows if row["is_current"]]

	page = rows[offset : offset + limit] if limit else rows

	return {
		# The rows on this page. `total` is how many there are to page through,
		# and the two are named differently because a screen needs both: one
		# labels the table, the other labels the pager.
		"count": len(page),
		"total": len(rows),
		# Over everything matching rather than over the page — "how many people"
		# is a fact about the result, and counting only the visible page would
		# make the number change as somebody clicked through it.
		"member_count": len({row["member"] for row in rows}),
		"as_of": as_of,
		"rows": page,
	}


def _row(record, as_of, names: dict, type_names: dict) -> dict:
	"""One register row: enough to find somebody, and nothing more.

	Deliberately thinner than the dossier. A register is a list of people a
	coordinator is scanning, and handing back everybody's full payment and
	approval history to answer "who are the members here" would disclose far
	more than the question needs. Opening one of them is a second, checked read
	through `api/member.py::get_dossier`.

	The three derived values are computed by the same functions the dossier
	uses, so a membership is never listed as current here and shown as lapsed
	when somebody opens it.
	"""
	from onerc_core.geo.services import adapter

	# A plain namespace over the queried fields, so the derivations below can be
	# the same ones that take a document. Nothing on it is written.
	membership = frappe._dict(record)
	person = names.get(membership.member) or {}

	return {
		"membership": membership.name,
		"member": membership.member,
		"full_name": person.get("full_name") or membership.member,
		# None is ordinary and the surface draws initials — see `_names_for`.
		"photo": person.get("photo"),
		"membership_type": membership.membership_type,
		"membership_type_name": type_names.get(membership.membership_type) or membership.membership_type,
		"geo_node": membership.geo_node,
		"geo_path": adapter.get_full_path(membership.geo_node) if membership.geo_node else None,
		"membership_status": membership.membership_status,
		"effective_status": membership_service.effective_status(membership, as_of),
		"lapsed": membership_service.is_lapsed(membership, as_of),
		"is_current": membership_service.is_current(membership, as_of),
		"valid_from": membership.valid_from,
		"valid_to": membership.valid_to,
		"membership_source": membership.membership_source,
	}


def _names_for(records: list[dict]) -> dict:
	"""Every member's name and face, in two queries rather than two per row.

	The register is the one place in this module where the per-record identity
	read would actually hurt: a hundred rows is a hundred member lookups and a
	hundred profile lookups. So the hop from member to profile and the read of
	the profile are each done once for the whole page.

	**The photo is read here for the same reason the name is.** A register is a
	list somebody is scanning for a person they often already know, and a face
	is how they find them — so it is part of "enough to find somebody" rather
	than decoration added on top. It costs one more column on a query that was
	already running; it does not cost another query, and it must not be allowed
	to become one.

	Returns a dict of member docname to `{"full_name", "photo"}`. `photo` is a
	file URL on this site or None, and None is entirely ordinary: most people a
	branch registers from a paper form have never uploaded one.

	Still read live and still stored nowhere — this is a batching decision, not
	a caching one, and the values are discarded when the call returns.
	"""
	members = {record["member"] for record in records if record.get("member")}

	if not members:
		return {}

	profiles = dict(
		frappe.get_all(
			MEMBER_DOCTYPE,
			filters={"name": ("in", sorted(members))},
			fields=["name", "red_profile"],
			as_list=True,
		)
	)

	if not profiles:
		return {}

	people = {
		row.name: row
		for row in frappe.get_all(
			PROFILE_DOCTYPE,
			filters={"name": ("in", sorted(set(profiles.values())))},
			fields=["name", "full_name", "first_name", "last_name", "profile_photo"],
		)
	}

	return {
		member: {
			"full_name": _display_name(people.get(profile), profile),
			"photo": (people.get(profile) or {}).get("profile_photo"),
		}
		for member, profile in profiles.items()
	}


def _display_name(person, profile: str) -> str:
	"""What to call somebody in a list, falling back to the profile docname.

	The same rule `identity.display_name` applies to one member, applied here to
	a batch. It is repeated rather than called per row for the reason
	`_names_for` gives, and it must stay in step: a register showing a different
	name from the record it links to would be worse than showing a docname.
	"""
	if not person:
		return profile

	full = (person.get("full_name") or "").strip()

	if full:
		return full

	composed = " ".join(part for part in (person.get("first_name"), person.get("last_name")) if part)

	return composed.strip() or profile


def _type_names_for(records: list[dict]) -> dict:
	"""Each membership type's society-facing name, read once for the page.

	The key is what code refers to and the name is what a person reads, and a
	register showing `KRCS-ordinary` in the column a human scans is the same
	failure as showing them a docname.
	"""
	keys = {record["membership_type"] for record in records if record.get("membership_type")}

	if not keys:
		return {}

	return dict(
		frappe.get_all(
			"VMMS Membership Type",
			filters={"name": ("in", sorted(keys))},
			fields=["name", "membership_type_name"],
			as_list=True,
		)
	)
