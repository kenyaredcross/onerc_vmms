# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""What a signed-in volunteer or member still has to accept, and recording it.

The portal asks this on every visit and, when the answer is not empty, puts the
terms panel over the page until the person accepts or signs out.

**Who is asked what.** A person with a volunteer record (not Exited) is asked
the required declarations that apply to the volunteer application; a person with
a member record (not Terminated) is asked the ones that apply to the membership.
Somebody who is both is asked both. An applicant who is neither yet is asked
nothing here: the registration form already asks them.

**When a declaration is outstanding.** When the person has never accepted any
version of it — everybody brought over from the old system starts here, because
the old consent was not imported — or when a version newer than every one they
accepted was published with "Ask everyone to accept again". A version published
without that tick (a typo fixed) asks nobody.

**What counts as accepted.** The acceptances on the person's own applications
and memberships, made while registering, and the `VMMS Consent` records this
module writes. Read together, so somebody who registered last week is not asked
again for the same wording.
"""

import frappe
from frappe import _
from frappe.utils import cstr, now_datetime

from vmmsx.registration.services import declarations

CONSENT_DOCTYPE = "VMMS Consent"
VOLUNTEER_APPLICATION = "VMMS Volunteer Application"
MEMBERSHIP = "VMMS Membership"
REACCEPT_FIELD = "requires_reacceptance"


def profile_of(user: str | None) -> str | None:
	"""The caller's Red Profile, or None for a guest or somebody core has never met."""
	if not user or user == "Guest":
		return None

	return frappe.db.get_value("Red Profile", {"user": user}, "name")


def outstanding(user: str | None) -> list[dict]:
	"""The required declarations this person has still to accept, in form order.

	Each is the DTO the registration form draws (`declarations.shown_on`), with
	`updated` added: True when they accepted an earlier version, False when they
	never accepted any.
	"""
	profile = profile_of(user)
	if not profile:
		return []

	shown = [row for doctype in _governed(profile) for row in declarations.shown_on(doctype)]
	shown = [row for row in shown if row["is_required"]]
	if not shown:
		return []

	names = [row["name"] for row in shown]
	accepted = _accepted(profile, names)
	thresholds = _thresholds(names)
	published = _published_on(
		[row["declaration_version"] for rows in accepted.values() for row in rows if row["declaration_version"]]
	)

	return [
		{**row, "updated": bool(accepted.get(row["name"]))}
		for row in shown
		if not _satisfied(accepted.get(row["name"], []), thresholds.get(row["name"]), published)
	]


def accept(user: str | None, choices) -> list[dict]:
	"""Record acceptance of everything outstanding. Returns what is still outstanding.

	`choices` is the list of `{declaration, declaration_version}` the person
	ticked. Every outstanding declaration must be in it, at the version they were
	shown: if a newer version was published while they were reading, the
	acceptance is refused and the panel shows them the new wording instead.
	"""
	profile = profile_of(user)
	if not profile:
		frappe.throw(_("Sign in to accept the terms."), frappe.PermissionError)

	if isinstance(choices, str):
		choices = frappe.parse_json(choices)

	ticked = {
		cstr(row.get("declaration")): cstr(row.get("declaration_version")) or None
		for row in choices or []
		if isinstance(row, dict) and row.get("declaration")
	}

	pending = outstanding(user)

	if any(row["name"] not in ticked for row in pending):
		frappe.throw(_("Accept each declaration to continue."), frappe.ValidationError)

	if any(ticked[row["name"]] != row["declaration_version"] for row in pending):
		frappe.throw(
			_("These terms were updated while you were reading them. Please read the new version."),
			frappe.ValidationError,
		)

	moment = now_datetime()
	for row in pending:
		frappe.get_doc(
			{
				"doctype": CONSENT_DOCTYPE,
				"red_profile": profile,
				"user": user,
				"declaration": row["name"],
				"title": row["title"],
				"version": row["version"],
				"declaration_version": row["declaration_version"],
				"source": row["source"],
				"external_url": row["external_url"],
				"body_snapshot": row["body"],
				"accepted_on": moment,
			}
		).insert(ignore_permissions=True)

	return outstanding(user)


# --- the reads -------------------------------------------------------------


def _governed(profile: str) -> list[str]:
	"""The registration doctypes whose declarations this person is held to."""
	governed = []

	if frappe.db.exists("VMMS Volunteer", {"red_profile": profile, "status": ("!=", "Exited")}):
		governed.append(VOLUNTEER_APPLICATION)

	if frappe.db.exists("VMMS Member", {"red_profile": profile, "status": ("!=", "Terminated")}):
		governed.append(MEMBERSHIP)

	return governed


def _accepted(profile: str, names: list[str]) -> dict[str, list[dict]]:
	"""Every acceptance this person has made of `names`, wherever it was recorded."""
	found: dict[str, list[dict]] = {}

	def keep(rows):
		for row in rows:
			found.setdefault(row.declaration, []).append(row)

	if frappe.db.exists("DocType", CONSENT_DOCTYPE):
		keep(
			frappe.get_all(
				CONSENT_DOCTYPE,
				filters={"red_profile": profile, "declaration": ("in", names)},
				fields=["declaration", "declaration_version"],
			)
		)

	parents = {
		VOLUNTEER_APPLICATION: frappe.get_all(
			VOLUNTEER_APPLICATION, filters={"red_profile": profile}, pluck="name"
		),
		MEMBERSHIP: frappe.get_all(
			MEMBERSHIP,
			filters={
				"member": ("in", frappe.get_all("VMMS Member", filters={"red_profile": profile}, pluck="name") or [""])
			},
			pluck="name",
		),
	}
	for parenttype, owned in parents.items():
		if not owned:
			continue
		keep(
			frappe.get_all(
				"VMMS Declaration Acceptance",
				filters={
					"parenttype": parenttype,
					"parent": ("in", owned),
					"declaration": ("in", names),
					"accepted": 1,
				},
				fields=["declaration", "declaration_version"],
			)
		)

	return found


def _thresholds(names: list[str]) -> dict[str, tuple[str, object]]:
	"""For each declaration, its latest "accept again" version and when it was published.

	Absent for a declaration that has never had one, which means any acceptance
	of it, of any version, still stands.
	"""
	meta = frappe.get_meta(declarations.VERSION_DOCTYPE)
	if not meta.has_field(REACCEPT_FIELD):
		return {}

	rows = frappe.get_all(
		declarations.VERSION_DOCTYPE,
		filters={"declaration": ("in", names), "docstatus": 1, REACCEPT_FIELD: 1},
		fields=["name", "declaration", "published_on"],
		order_by="published_on asc, creation asc",
	)

	return {row.declaration: (row.name, row.published_on) for row in rows if row.published_on}


def _published_on(versions: list[str]) -> dict[str, object]:
	if not versions:
		return {}

	return {
		row.name: row.published_on
		for row in frappe.get_all(
			declarations.VERSION_DOCTYPE,
			filters={"name": ("in", sorted(set(versions)))},
			fields=["name", "published_on"],
		)
	}


def _satisfied(rows: list, threshold: tuple[str, object] | None, published: dict) -> bool:
	"""Has one of these acceptances been of the threshold version or a later one?

	The threshold version itself is matched by name rather than by time, so two
	versions stamped in the same second cannot stand in for each other.
	"""
	if not rows:
		return False

	if not threshold:
		return True

	version, since = threshold
	return any(
		row.declaration_version == version
		or (published.get(row.declaration_version) and published[row.declaration_version] > since)
		for row in rows
	)
