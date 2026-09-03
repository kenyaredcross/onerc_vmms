# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Application Answer — what one applicant said to one organization-specific question.

A child table on the registration itself, so an application carries its own
answers the way it carries its own decisions. The approver reads them off the
document in front of them rather than joining anything.

**Every answer is one column of text, and the type sits beside it.** A tick is
"1", a date is a date string, a number is its digits, and `field_type` says how
to read them. Five sparse columns would have been the alternative, and they
would have had to grow every time a society wanted a new kind of question.
`answer_file` is the single exception, because a file is a reference to
something the framework stores rather than a value.

**The label and the type are snapshots**, written when the answer is given and
never refreshed. Same rule as `VMMS Approval Decision.stage_label`: what an
applicant was asked is part of what they answered, and a society tidying its
wording next season must not silently restate a question somebody already
answered under different words.
"""

from frappe.model.document import Document


class VMMSApplicationAnswer(Document):
	pass
