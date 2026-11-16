# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The printed terms of reference takes the society's own layout and wording.

The shipped template now reads like the Kenya Red Cross paper it follows:
Title of Exercise, Location and Period at the head, then numbered Background,
Purpose, Objectives and Proposed Methodology. It leaves out the Authorisation
line where deployment requests are not routed for approval.
`deployment/services/templates.py` never rewrites a stored template, so a site
seeded before this keeps the old one until this patch runs.

**A template nobody has edited is replaced; an edited one is not.** A stored
body that is byte-for-byte a version this app shipped is still ours, and gets
the new one. Anything else is a society's own document: it keeps every word,
and only the Authorisation line, where it is still exactly as shipped, is
wrapped so that it disappears when it has nothing to say.
"""

import hashlib
from pathlib import Path

import frappe

# Every version of `templating/seeds/terms_of_reference.html` a site may hold
# unedited: the one shipped before this change, and the same with the
# Authorisation line already guarded, which one development site briefly had.
SHIPPED = {
	"f7e30b53e730f9d561e91d77f6c08a28fa0a060b902d915a0df704712081ff51",
	"be57362087f4b4bea9f7293880d717b2f0ea833868d404ebc9f7bb00713e1582",
}

OLD_LINE = "<tr><td>Authorisation</td><td>{{ approval_mode_label }}</td></tr>"
GUARDED_LINE = "{% if approval_mode_label %}" + OLD_LINE + "{% endif %}"


def fingerprint(body: str) -> str:
	return hashlib.sha256(body.replace("\r\n", "\n").strip().encode()).hexdigest()


def execute():
	from vmmsx.deployment.services import templates, tor_document

	key = tor_document.TEMPLATE_KEY
	body = frappe.db.get_value(templates.TEMPLATE_DOCTYPE, key, "body")

	if not body:
		return

	if fingerprint(body) in SHIPPED:
		seed = (Path(templates.SEED_DIR) / templates.SEED_FILE).read_text()
		frappe.db.set_value(templates.TEMPLATE_DOCTYPE, key, "body", seed, update_modified=False)
		return

	if OLD_LINE in body and GUARDED_LINE not in body:
		frappe.db.set_value(
			templates.TEMPLATE_DOCTYPE,
			key,
			"body",
			body.replace(OLD_LINE, GUARDED_LINE),
			update_modified=False,
		)
