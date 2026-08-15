# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The opportunities board: the society's published job openings.

**It reads HRMS's `Job Opening`**, through the seam in
`vmmsx/hr/services/openings.py`, which is the only file in this app that names
that doctype. This endpoint adds a DTO boundary and nothing else, the same shape
as `api/events.py` over the Buzz seam.

**What this replaced, and why.** The board used to read
`VMMS Deployment Request` — the society's own record of needing people
somewhere. That record is real and still does its job, but it was the wrong
thing to advertise: it is an internal staffing note, and there was no way for
anybody to answer one. The screen said so out loud, explaining that a
coordinator matches volunteers from the register instead, which is an honest
sentence and a poor advertisement. A society already running its recruitment in
HRMS has the opening, the application form and the pipeline there, so pointing
the board at it is what lets somebody actually apply.

**Browse here, apply there.** There is no application endpoint in this file and
there will not be one. HRMS owns the applicant record, the duplicate check and
everything after it, and each card's call to action is a full navigation to
HRMS's own page. A vmmsx endpoint wrapping any of that would be a second
implementation of a rule that has to stay in step with HRMS's forever.

**Signed in, deliberately.** Neither endpoint is `allow_guest`. The three
guest-readable endpoints in this app are `content.surface`, `society.branding`
and `locations.published`, each bounded by a flag on a document; a fourth needs
the same justification, which is a question somebody has *before* they have an
account. HRMS publishes its own openings to the website for that audience.

**HRMS absent is an ordinary state, not an error.** vmmsx does not declare
`hrms` in `required_apps`. On a site without it both endpoints answer empty and
the screen says so rather than showing a spinner forever.
"""

import frappe

from vmmsx.hr.services import openings as seam


@frappe.whitelist()
def browse(
	search: str | None = None,
	department: str | None = None,
	limit: int = 60,
) -> dict:
	"""Published, open job openings the society is recruiting for.

	`available` travels with the rows rather than being a second endpoint,
	because the screen needs it at the moment it decides what to draw: no
	openings because HRMS is not installed and no openings because the society
	is not recruiting are different sentences to put in front of somebody.
	"""
	return {
		"available": seam.is_available(),
		"opportunities": seam.published(search=search, department=department, limit=limit),
	}


@frappe.whitelist()
def detail(name: str) -> dict | None:
	"""One opening in full, for the screen a card opens.

	The same boundary as the listing — `publish` and `status`, both HRMS's own
	decisions — so naming a docname buys nothing a caller could not already see.
	None rather than an error for an opening that has closed: following an old
	link is an ordinary thing to do, and the screen says so.
	"""
	return seam.detail(name)


@frappe.whitelist()
def filters() -> dict:
	"""What the picker on the board offers.

	Departments only, and only those with something open. Where an opening is
	held is HRMS's `location`, which is its own Branch record rather than a Geo
	Node — this app does not have a second answer to where a job is, and does
	not invent one by mapping between the two.
	"""
	return {
		"available": seam.is_available(),
		"departments": seam.departments(),
	}
