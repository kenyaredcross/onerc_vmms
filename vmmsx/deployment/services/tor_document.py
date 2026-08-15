# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The printable terms of reference — the society's paper, not this app's.

The domain half of a rendered document, and the sibling of
`volunteer/services/card.py` and `member/services/certificate.py`: it builds one
dict and hands it to `vmmsx/templating`, which knows nothing about deployments.
Same split, same reason. **No sentence of a terms of reference is in this file**
— the wording is a `VMMS Template`, seeded once by `templates.install` and the
society's to rewrite afterwards.

**The letterhead is the society's own answer about itself**, read through
`notifications/services/branding.py::lockup` rather than a fourth reader of
`National Society Settings`. A society that has uploaded its mark gets it at the
head of every terms of reference it prints, without retyping anything; one that
has not gets the document with no masthead rather than a broken image.

**Two renders, one context.** The screen and the PDF differ in one thing: how an
image is referenced. `assets.printable_asset` embeds the logo as a data URI for
the PDF renderer, which has no session and cannot fetch a private file; the
browser is already authenticated and wants the ordinary path. That is
`absolute_assets`, and it is the only fork.

**Nothing here decides who may print.** `api/deployment.py` answers that with
the ordinary permission check, which brings core's geo scoping with it, and
answering it twice is how two answers come to disagree.
"""

import frappe
from frappe import _
from frappe.utils import format_date
from frappe.utils.pdf import get_pdf

from vmmsx.cards.services import assets
from vmmsx.deployment.services import terms
from vmmsx.templating.services import render

# The template these render through. The record it names carries every word of
# the document; this module carries none.
TEMPLATE_KEY = "terms_of_reference"

# How the two configured approval modes are described to a reader of the printed
# document. A label, not a branch: `approval.py` owns what the modes *do*, and
# this only writes down which one these terms chose. Keyed by the same closed
# vocabulary, so a mode without a sentence here is impossible rather than blank.
_MODE_LABELS = {
	"direct": "Fulfilled by the branch raising the request. No further authorisation is needed.",
	"routed": "A request under these terms is routed for approval before anyone is deployed.",
}


def context_for(terms_of_reference: str, absolute_assets: bool = False) -> dict:
	"""Everything the printed terms of reference could want to say, as plain values.

	Built from `terms.dto`, which is already the reviewed field list, plus the
	things only a printed document needs: the letterhead, the certification
	requirements in the society's own words rather than as keys, and the date it
	was put on paper.
	"""
	from vmmsx.notifications.services import branding

	detail = terms.dto(terms_of_reference)
	lockup = branding.lockup()
	logo = lockup.get("brand_logo") or ""

	return {
		"society_name": lockup.get("brand_name") or "",
		"society_logo": assets.printable_asset(logo) if absolute_assets else logo,
		"tor_key": detail["tor_key"],
		"tor_name": detail["tor_name"],
		"purpose": detail["purpose"] or "",
		"responsibilities": detail["responsibilities"] or "",
		"notes": frappe.db.get_value(terms.TERMS_DOCTYPE, terms_of_reference, "notes") or "",
		"geo_scope_path": detail["geo_scope_path"] or "",
		"duration": _duration_text(detail["default_duration_days"]),
		"approval_mode_label": _MODE_LABELS.get(detail["approval_mode"], ""),
		"status_label": _("Active") if detail["is_active"] else _("Withdrawn from new deployments"),
		"mandatory_certifications": _titles(detail["required_certifications"]),
		"desirable_certifications": _titles(detail["desirable_certifications"]),
		"issued_on": format_date(frappe.utils.now_datetime()),
		**_project_context(detail["project"]),
	}


def render_document(terms_of_reference: str, absolute_assets: bool = False) -> dict:
	"""These terms, rendered through the shared template service."""
	assert_template()

	return render.render_template(
		TEMPLATE_KEY, context_for(terms_of_reference, absolute_assets=absolute_assets)
	)


def pdf_for(terms_of_reference: str) -> bytes:
	"""These terms as PDF bytes. Nothing is stored and no File row is created."""
	assert_template()

	return get_pdf(render_document(terms_of_reference, absolute_assets=True)["body"])


def pdf_filename(terms_of_reference: str) -> str:
	"""The stable business key, which is already opaque and already the docname."""
	return f"terms-of-reference-{terms_of_reference}.pdf"


def assert_template() -> None:
	"""Refuse early, and name the record that is missing, when none is seeded.

	Without this the failure surfaces from inside the render service naming a key
	nobody recognises. Same guard, same wording, as `cards/services/card.py`.
	"""
	if frappe.db.exists(render.TEMPLATE_DOCTYPE, TEMPLATE_KEY):
		return

	frappe.throw(
		_("No terms of reference document is configured. Expected a {0} named {1}.").format(
			frappe.bold(render.TEMPLATE_DOCTYPE), frappe.bold(TEMPLATE_KEY)
		),
		frappe.DoesNotExistError,
		title=_("No Document Template"),
	)


# --- the parts a printed document needs and a DTO does not ------------------


def _project_context(project: str | None) -> dict:
	"""The programme's half of the letterhead. Empty strings where there is none.

	Empty rather than absent so the template's `{% if %}` guards read the same
	whether the terms belong to a project or not, and a society that runs
	standing duties gets a document with no programme line rather than one with a
	visibly unfilled placeholder.
	"""
	from vmmsx.deployment.services import project as project_service

	if not project or not frappe.db.exists(project_service.PROJECT_DOCTYPE, project):
		return {
			"project_name": "",
			"project_summary": "",
			"project_period": "",
			"project_geo_path": "",
		}

	detail = project_service.dto(project_service.read(project))

	return {
		"project_name": detail["project_name"] or "",
		"project_summary": detail["summary"] or "",
		"project_period": _period_text(detail["start_date"], detail["end_date"]),
		"project_geo_path": detail["geo_path"] or "",
	}


def _titles(certification_keys: list[str]) -> list[str]:
	"""A society's own words for each certification, in the order configured.

	Read one by one through the document cache rather than in a single query,
	because a terms of reference lists a handful of requirements and the cache is
	already warm from matching. A key whose type has since been deleted falls
	back to the key, which is honest: it is what the requirement actually says.
	"""
	titles = []

	for key in certification_keys or []:
		titles.append(
			frappe.db.get_value("VMMS Certification Type", key, "certification_type_name") or key
		)

	return titles


def _duration_text(days: int | None) -> str:
	"""How long work under these terms usually runs. Empty where nobody said."""
	if not days:
		return ""

	return _("{0} days").format(days) if days != 1 else _("1 day")


def _period_text(start: str | None, end: str | None) -> str:
	"""A project's dates as one line, however many of them are set."""
	if start and end:
		return f"{format_date(start)} to {format_date(end)}"

	if start:
		return _("From {0}").format(format_date(start))

	if end:
		return _("Until {0}").format(format_date(end))

	return ""
