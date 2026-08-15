# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Putting the shipped terms of reference document on the site, once and never again.

The twin of `cards/services/templates.py`, and it follows the same two rules for
the same two reasons.

**`after_migrate` rather than a patch.** A patch runs once per site by name, so a
document shipped after a site had already migrated would never reach it, and a
society that installed vmmsx before this existed would have the print endpoint
and no template to render. Running on every migrate and creating only what is
absent reaches every site exactly once, whenever it happens to catch up.

**The write is additive, and that is the whole safety story.** The record is
created when the site has none by that key and is *never* edited again, so a
society that has rewritten its terms of reference — its own wording, its own
colours, a clause its legal office insists on — survives every deploy
afterwards. Same rule, same reason, as `content/services/blocks.py::seed` and
`notifications/services/welcome.py::install`.
"""

from pathlib import Path

import frappe

from vmmsx.deployment.services import tor_document

TEMPLATE_DOCTYPE = "VMMS Template"
CATEGORY_DOCTYPE = "VMMS Template Category"

CATEGORY_KEY = "deployment_document"
SEED_DIR = Path(frappe.get_app_path("vmmsx")) / "templating" / "seeds"
SEED_FILE = "terms_of_reference.html"

CONTEXT_KEYS = (
	"society_name, society_logo, tor_key, tor_name, purpose, responsibilities, notes,"
	" geo_scope_path, duration, approval_mode_label, status_label,"
	" mandatory_certifications, desirable_certifications, project_name, project_summary,"
	" project_period, project_geo_path, issued_on"
)


def install() -> dict:
	"""Create the category and the shipped terms of reference, if they are missing."""
	created = []

	if not frappe.db.exists(CATEGORY_DOCTYPE, CATEGORY_KEY):
		frappe.get_doc(
			{
				"doctype": CATEGORY_DOCTYPE,
				"category_key": CATEGORY_KEY,
				"category_name": "Deployment Document",
				"description": (
					"Paperwork a deployment produces, printed on the society's own letterhead."
					" Nothing in the code branches on this category."
				),
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		created.append(CATEGORY_KEY)

	if not frappe.db.exists(TEMPLATE_DOCTYPE, tor_document.TEMPLATE_KEY):
		frappe.get_doc(
			{
				"doctype": TEMPLATE_DOCTYPE,
				"template_key": tor_document.TEMPLATE_KEY,
				"template_name": "Terms of Reference",
				"template_category": CATEGORY_KEY,
				"subject": "Terms of Reference",
				"body": (SEED_DIR / SEED_FILE).read_text(),
				"output_format": "html",
				"is_active": 1,
				"description": (
					f"The default printed terms of reference. Context keys: {CONTEXT_KEYS}."
					" Edit freely: nothing in the code depends on this wording or these"
					" colours, and a section whose value is empty renders itself away."
				),
			}
		).insert(ignore_permissions=True)
		created.append(tor_document.TEMPLATE_KEY)

	return {"created": created}
