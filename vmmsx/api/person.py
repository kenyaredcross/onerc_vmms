# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Which of the society's registers one person appears in.

The question this answers
-------------------------

A coordinator opening `VOL-00042` is looking at a volunteer. The very next thing
they are asked at a counter is whether that person is also a member — and until
now the only way to find out was to leave the page, open the member register and
search for the name, which is exactly the tab-hopping the dossiers were built to
end. The same question runs the other way: a membership office looking at a
member wants to know whether this is somebody the branch already deploys.

Both registers hang off the same Red Profile, so the answer is a single hop from
the profile back down into each register. That is all this module is.

Why it lives in `api/` and not in either module
-----------------------------------------------

`volunteer/services/identity.py` states the rule and it is the right one:
Member and Volunteer are sibling satellites, and a volunteer module that stops
working when the member module is uninstalled has acquired a dependency on
something it has nothing to do with. So neither service may import the other,
and a "registers" block cannot be assembled inside either one.

The API layer is where composition across modules already happens — the
volunteer dossier composes the deployment module's roster, the member dossier
composes payments — so the cross-register question is assembled here, above both
satellites, and handed to each dossier as one more nested block. Each register
is described by a row of `_REGISTERS` rather than by code, so the day a third
register exists this file grows a row and nothing else changes.

Absent is ordinary, not broken
------------------------------

Most people in a society's records are in exactly one register. A `None` under
either key is the ordinary answer and every caller must render it as "not in
this register" rather than as a failure. A doctype the caller may not read at
all — a membership clerk with no volunteer permissions — is likewise `None`
rather than an exception taking the page down: not being allowed to know is
indistinguishable, on a screen, from there being nothing to know, and the
alternative is a member page that 500s for half the office.

Scope is the floor here too
---------------------------

Every read below is `frappe.get_list`, never `get_all`, so core's permission
query condition applies exactly as it does to the registers themselves. A
coordinator learns that this person is also a volunteer only if that volunteer
record is at a branch they were already entitled to see. Nothing here widens
anything: it is the register list asked about one profile.

That is also why the whitelisted endpoint may take a bare Red Profile docname.
It discloses nothing the register pages do not already disclose to the same
caller, and it discloses nothing at all about profiles whose records sit outside
their scope.
"""

import frappe

# The registers a person may appear in, in the order a screen should show them.
#
# `kind` is the word the frontend routes on (`/admin/registry/<kind>/<name>`),
# `doctype` is what to read, and `status_label` is what the status field is
# *called* on that register — a volunteer's "standing" and a member's "standing"
# happen to share a word, but the values do not, and nothing here compares them.
# The statuses are carried through as the register's own strings and are never
# re-derived, mapped or ranked in this file.
_REGISTERS = (
	{"kind": "volunteer", "doctype": "VMMS Volunteer", "label": "Volunteer"},
	{"kind": "member", "doctype": "VMMS Member", "label": "Member"},
)

_FIELDS = ("name", "status", "joined_on")


def registers(red_profile: str | None) -> dict:
	"""Every register this profile appears in that the caller may see.

	Keyed by `kind`, with `None` for a register the person is not in *or* that
	the caller may not read. The two are deliberately not distinguished: see the
	module docstring on why a screen must not be told the difference.

	One row per register, ordered oldest first, because somebody re-registered
	after an exit has two volunteer records and the first one is the one their
	history hangs off.
	"""
	found = {register["kind"]: None for register in _REGISTERS}

	if not red_profile:
		return found

	for register in _REGISTERS:
		doctype = register["doctype"]

		# Asked before the read rather than caught after it. `get_list` raises
		# on a doctype the caller has no read permission for, and one absent
		# permission must cost this block its row rather than the whole page.
		if not frappe.has_permission(doctype, "read"):
			continue

		rows = frappe.get_list(
			doctype,
			filters={"red_profile": red_profile},
			fields=list(_FIELDS),
			order_by="creation asc",
			limit_page_length=1,
		)

		if not rows:
			continue

		row = rows[0]

		found[register["kind"]] = {
			"kind": register["kind"],
			"label": register["label"],
			"name": row.get("name"),
			# The register's own word for where this person stands, passed
			# through. Never compared here — the two vocabularies are different
			# closed Selects owned by two different modules.
			"status": row.get("status"),
			"joined_on": row.get("joined_on"),
		}

	return found


@frappe.whitelist()
def get_registers(red_profile: str) -> dict:
	"""The same answer, for a screen that holds a profile rather than a dossier.

	The review queue is the caller this exists for. An approver deciding a
	volunteer application is looking at somebody who may already be a member of
	long standing, and that is decision-relevant — but the approval engine's own
	status DTO knows about applicants, not about registers, and teaching it would
	push both satellites' doctypes into the engine. One small extra read from the
	screen that needs it is the honest cost.
	"""
	return registers(red_profile)
