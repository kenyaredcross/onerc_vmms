# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The recruiter's door — advertising an opening and deciding on the answers.

The counterpart of `api/opportunities.py`, which is the volunteer's. Everything
here is checked by *write* or *read on the record named*, never by ownership:
these are acts on the society's own recruitment, not on a personal record, so
`api/opportunities.py`'s `_mine` rule is exactly the wrong one and is absent.

**Every method is a thin wrapper.** The rules — which fields the console may
write, what a curated applicant is, how the pipeline is counted — live in
`hr/services/recruitment.py`, so the endpoint list stays readable as an
inventory of what the screen can ask for.

**`convert` is not here.** Turning an accepted application into a deployment
assignment or a task already has a door, in `api/opportunities.py`, and it is
the coordinator's rather than the applicant's despite the module it sits in. A
second endpoint for it would be a second permission check on the same act.
"""

import frappe

from vmmsx.hr.services import recruitment


@frappe.whitelist()
def openings(
	search: str | None = None,
	status: str | None = None,
	purpose: str | None = None,
	limit: int = 100,
) -> dict:
	"""Every opening this person may read, with its pipeline counted."""
	return recruitment.openings(search=search, status=status, purpose=purpose, limit=limit)


@frappe.whitelist()
def opening(name: str) -> dict:
	"""One opening in full, as the console's form edits it."""
	return recruitment.detail(name)


@frappe.whitelist(methods=["POST"])
def save_opening(payload: dict | str, name: str | None = None) -> dict:
	"""Create an opening, or amend one. Returns the saved opening."""
	return recruitment.save(payload, name=name)


@frappe.whitelist(methods=["POST"])
def set_opening_status(name: str, status: str) -> dict:
	"""Open or close an opening — whether the society is still recruiting."""
	return recruitment.set_status(name, status)


@frappe.whitelist(methods=["POST"])
def set_opening_published(name: str, published: int | bool = 0) -> dict:
	"""Put the advertisement on the society's website, or take it off."""
	return recruitment.set_published(name, published)


@frappe.whitelist()
def applicants(
	opening: str | None = None,
	status: str | None = None,
	search: str | None = None,
	limit: int = 100,
) -> dict:
	"""The pipeline — everybody who has answered, across openings or within one."""
	return recruitment.applicants(opening=opening, status=status, search=search, limit=limit)


@frappe.whitelist()
def applicant(name: str) -> dict:
	"""One application, curated for the person deciding it."""
	return recruitment.applicant(name)


@frappe.whitelist(methods=["POST"])
def set_applicant_status(name: str, status: str) -> dict:
	"""Move somebody along the pipeline. HRMS's own status field."""
	return recruitment.set_applicant_status(name, status)


@frappe.whitelist()
def options() -> dict:
	"""Every list the opening form draws a control from, in one read."""
	return recruitment.options()
