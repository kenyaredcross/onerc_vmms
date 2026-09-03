# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One post somebody has held, paid or unpaid.

**Volunteering counts and the field names say nothing that excludes it.**
"Organization" and "Role" rather than "Employer" and "Job Title", because a
great many volunteer applicants have done the most relevant work of their lives
without being paid for it, and a form that only had room for employment would
have quietly told them so.

`is_current` rather than an empty `ended_on`, for the reason `VMMS Education`
gives about `is_ongoing`: not saying and still being there are different
answers."""

from frappe.model.document import Document


class VMMSWorkExperience(Document):
	pass
