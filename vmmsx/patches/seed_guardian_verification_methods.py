# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Seed the ways a society can check that a guardian's consent is real.

A starting vocabulary a society then edits, exactly like the skills, motivations
and availability slots `setup_volunteer_application_module` seeds. Nothing under
`vmmsx/` branches on any key here — the reviewer ticks `is_verified` on
`VMMS Guardian Consent` and this row records what they did to earn the tick, so
a society may rename, deactivate or add to all four and no source file changes.

Idempotent by construction: each row is created only when its key is absent, so
re-running changes nothing and overwrites nothing an administrator has since
edited.
"""

import frappe

METHOD_DOCTYPE = "VMMS Guardian Verification Method"

METHODS = (
	(
		"in_person",
		"In Person",
		"The guardian came to the branch and gave consent in front of a member of staff.",
	),
	(
		"signed_form",
		"Signed Form",
		"A consent form signed by the guardian, uploaded or held on file at the branch.",
	),
	(
		"telephone",
		"Telephone",
		"A member of staff telephoned the guardian on the number given and confirmed consent.",
	),
	(
		"school_or_institution",
		"Through a School or Institution",
		"Consent passed on by a school, children's home or other institution responsible for the applicant.",
	),
)


def execute():
	install()


def install() -> list[str]:
	"""Create the absent methods. Returns what was created, for the caller's log."""
	created = []

	for key, name, description in METHODS:
		if frappe.db.exists(METHOD_DOCTYPE, key):
			continue

		frappe.get_doc(
			{
				"doctype": METHOD_DOCTYPE,
				"method_key": key,
				"method_name": name,
				"description": description,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		created.append(key)

	return created
