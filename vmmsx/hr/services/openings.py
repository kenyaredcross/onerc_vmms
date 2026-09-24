# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Curated readings of published HRMS Job Openings for the portal board.

Only published, open, unexpired openings are shown. HRMS continues to own the
opening and applicant records; the portal supplies its own application page so
ordinary users do not need Job Opening read permission in the browser.
"""

from urllib.parse import quote

import frappe
from frappe.utils import getdate, today

HRMS_APP = "hrms"
OPENING_DOCTYPE = "Job Opening"

# A board is a board. An unbounded read on a listing endpoint is how a slow
# query becomes an outage.
MAX_ROWS = 60

# HRMS's own word for an opening the society is still recruiting for.
STATUS_OPEN = "Open"


def is_available() -> bool:
	"""Is HRMS installed on this site?"""
	return HRMS_APP in frappe.get_installed_apps()


def opening_url(route: str | None) -> str | None:
	"""HRMS's own public page for this opening, or None when it has no route.

	**`route` is the whole path, not a slug.** HRMS fills it in as
	`jobs/<company>/<title>` and serves the document there like any other
	website generator, so the page is that value with a leading slash and
	nothing else in front of it. This used to answer `/job_opening/<route>` —
	the doctype's name, which is not a URL on any site — and every card on the
	board and every button under it led to a 404.

	An opening with no route is one HRMS has not finished publishing, so there
	is nowhere to send anybody and the card renders without that link rather
	than with a broken one. Same rule as the Buzz seam's `event_url`.
	"""
	return f"/{route.strip('/')}" if route else None


def apply_url(opening: str, route: str | None) -> str:
	"""The portal's application page for this published opening.

	The HRMS web form queries Job Opening from the browser and can return 403 for
	ordinary applicants. The portal reads the curated opening and submits through
	an endpoint that checks publication and writes the existing HRMS applicant.
	"""
	return f"/portal/opportunities/{quote(opening, safe='')}/apply"


def published(search: str | None = None, department: str | None = None, limit: int = MAX_ROWS) -> list[dict]:
	"""Open, published job openings that have not closed, soonest closing first.

	`closes_on` is optional in HRMS, so an opening with no closing date is
	advertised until the society closes it by hand. That is the society's
	decision and not this reader's to second-guess, which is why the date filter
	is ORed against its own absence rather than excluding the row.
	"""
	if not is_available():
		return []

	rows = frappe.get_all(
		OPENING_DOCTYPE,
		filters=_filters(search, department),
		or_filters=_not_closed(),
		fields=[
			"name",
			"job_title",
			"route",
			"description",
			"department",
			"designation",
			"employment_type",
			"location",
			"vacancies",
			"posted_on",
			"closes_on",
			"job_application_route",
		],
		order_by="closes_on asc, posted_on desc",
		limit_page_length=_bounded(limit),
		# HRMS's own website listing reads published openings without a
		# permission check, and this serves the same rows to the same people.
		# The gate is `publish` and `status`, which are the society's decisions
		# on that document; requiring read permission on Job Opening would mean
		# granting every volunteer an HR role just to see what the society has
		# already put in public.
		ignore_permissions=True,
	)

	return [_as_card(row) for row in rows]


def detail(opening: str) -> dict | None:
	"""One published opening, with the description a card has no room for.

	Same boundary as the listing and only the boundary, so a caller who guesses
	a docname gets nothing back. Nothing about applicants is here.
	"""
	if not is_available():
		return None

	row = frappe.db.get_value(
		OPENING_DOCTYPE,
		{"name": opening, "publish": 1, "status": STATUS_OPEN},
		[
			"name",
			"job_title",
			"route",
			"description",
			"department",
			"designation",
			"employment_type",
			"location",
			"vacancies",
			"posted_on",
			"closes_on",
			"job_application_route",
		],
		as_dict=True,
	)

	if not row:
		return None
	if row.get("closes_on") and getdate(row.closes_on) < getdate(today()):
		return None

	return _as_card(row)


def departments() -> list[dict]:
	"""The departments with something open, for the picker.

	Only those actually recruiting, the same rule the Buzz seam applies to
	venues: a department with nothing open reads as a place to apply to on a day
	when there is nothing to apply for.
	"""
	if not is_available():
		return []

	rows = frappe.get_all(
		OPENING_DOCTYPE,
		filters=_filters(None, None),
		or_filters=_not_closed(),
		pluck="department",
		ignore_permissions=True,
	)

	return [{"department": name, "label": name} for name in sorted({row for row in rows if row})]


def _filters(search: str | None, department: str | None) -> list[list]:
	"""What the database is asked. Both gates are HRMS's own flags."""
	filters: list[list] = [
		[OPENING_DOCTYPE, "publish", "=", 1],
		[OPENING_DOCTYPE, "status", "=", STATUS_OPEN],
	]

	if department:
		filters.append([OPENING_DOCTYPE, "department", "=", department])

	if search:
		# The title only. `description` is a Text Editor field full of markup,
		# and a `%like%` across it matches tag names rather than words somebody
		# typed — the same reason the Buzz seam searches only an event's title.
		filters.append([OPENING_DOCTYPE, "job_title", "like", f"%{search.strip()}%"])

	return filters


def _not_closed() -> list[list]:
	"""Still open by date, or carrying no closing date at all.

	ORed, because `closes_on` is optional in HRMS. An opening with no date is
	advertised until somebody closes it, which is the society saying "until
	further notice" rather than an omission for this reader to correct.
	"""
	return [
		[OPENING_DOCTYPE, "closes_on", ">=", today()],
		[OPENING_DOCTYPE, "closes_on", "is", "not set"],
	]


def _bounded(limit: int) -> int:
	try:
		value = int(limit)
	except (TypeError, ValueError):
		return MAX_ROWS

	return max(1, min(value, MAX_ROWS))


def _as_card(row: dict) -> dict:
	"""One opening, built field by field.

	An explicit DTO rather than the row, for the reason `CLAUDE.md` gives and
	which applies doubly here: this comes from *another app's* schema, which this
	one neither controls nor reviews, and HRMS's own model carries salary bands
	and staffing plans that are nobody's business on a public board. Nothing is
	forwarded that was not chosen here.

	`href` is HRMS's own page for the opening and `apply_href` is HRMS's
	application form for it — see `opening_url` and `apply_url`, which is where
	both addresses are built and where the reasoning for each one lives.

	**This used to carry a second set of names.** Every field the old deployment
	board read — `purpose`, `responsibilities`, `requirements`, `geo_path`,
	`needed_from`, `deployment_status` — was aliased here so the source could
	change without the screen changing in the same breath. That was a stopgap and
	it did real damage: `purpose` fed a `<p>` that rendered text, HRMS's
	`description` is Text Editor markup, and the board showed every reader a wall
	of escaped `<div class="ql-editor">`. The screen now reads the names below,
	so the aliases are gone rather than quietly wrong.
	"""
	closes = row.get("closes_on")
	posted = row.get("posted_on")
	page = opening_url(row.get("route"))
	description = row.get("description") or ""

	return {
		"name": row.get("name"),
		"opening": row.get("name"),
		"title": row.get("job_title") or "",
		# Both readings of the same field, decided here rather than in a browser.
		# A card wants a two-line excerpt and a detail page wants the formatting
		# an HR officer applied — headings, bullets, emphasis — and neither can be
		# derived from the other on the client without shipping a parser.
		"description_html": _safe_html(description),
		"summary": _excerpt(description),
		"department": row.get("department") or "",
		"designation": row.get("designation") or "",
		"employment_type": row.get("employment_type") or "",
		"location": row.get("location") or "",
		"places": row.get("vacancies") or 0,
		"posted_on": str(posted)[:10] if posted else "",
		# Both cut to the date, and `closes_on` deliberately so. HRMS declares it
		# a Date, but `setup/job_opening_fields.py` widens it to a Datetime — the
		# society's closing time is a real fact — and the whole of that time was
		# reaching the board as `2026-09-10 00:00:00`. A closing *date* is what a
		# card says, and the browser's own date parser is not reliable on a
		# space-separated datetime.
		"closes_on": str(closes)[:10] if closes else "",
		"closing_soon": bool(closes and (getdate(closes) - getdate(today())).days <= 7),
		"href": page,
		"apply_href": apply_url(row.get("name"), row.get("job_application_route")),
	}


def _safe_html(description: str) -> str:
	"""HRMS's rich-text description, cleaned of anything that could execute.

	**The app's rule is that nothing a society types is trusted as HTML, and this
	is not an exception to it — it is the other half of it.** The rule exists
	because a plain-text field rendered as markup is an injection; a Text Editor
	field is markup by construction, written through a rich-text control by an HR
	officer who chose the headings and the bullet list on purpose. Rendering that
	as text is not the safe reading of it, it is simply the wrong one, and it is
	what put `<div class="ql-editor read-mode">` on the board in front of every
	visitor.

	So it is sanitised instead, with Frappe's own `sanitize_html` — the same
	function the framework runs over user HTML before it renders it anywhere
	else. Scripts, event handlers, iframes and styles do not survive it. Done
	here rather than in the browser because a client-side sanitiser is one an
	attacker can simply not run: the endpoint must never have served the markup.
	"""
	if not description:
		return ""

	from frappe.utils.html_utils import sanitize_html

	return sanitize_html(description)


def _excerpt(description: str, limit: int = 220) -> str:
	"""The same description as one paragraph of plain text, for a card.

	Tags stripped and whitespace collapsed, because HRMS's editor stores the
	indentation of the markup and a naive strip leaves an excerpt that begins
	with eleven blank lines. Cut on a word boundary: a summary that stops
	mid-syllable reads as a truncation bug rather than as an excerpt.
	"""
	if not description:
		return ""

	from frappe.utils import strip_html_tags

	text = " ".join(strip_html_tags(description).split())

	if len(text) <= limit:
		return text

	return text[:limit].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
