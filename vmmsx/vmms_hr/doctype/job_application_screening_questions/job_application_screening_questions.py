# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Job Application Screening Questions — One question an opening puts to an applicant, and how it is scored.

A child table, and the richest of the three. `question_id` is the stable code the
dependency logic refers to — `depends_on_question` names another question by that
code rather than by row — so renumbering the grid never breaks a dependency.

`is_knock_off` and the scoring block are read by the auto-grading engine. **That
engine is not part of this app yet**: the fields exist and are editable, and
nothing in vmmsx grades against them. See `vmmsx/setup/job_opening_fields.py`.
"""

from frappe.model.document import Document


class JobApplicationScreeningQuestions(Document):
	pass
