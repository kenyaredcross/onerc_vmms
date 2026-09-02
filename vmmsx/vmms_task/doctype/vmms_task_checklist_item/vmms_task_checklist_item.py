# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One thing that has to be done as part of a task.

Rows rather than a paragraph, because "did they do the third thing" is a
question a coordinator asks and a paragraph cannot answer.

`is_required` is the only field here that anything acts on: a task cannot be
submitted while a required item is unticked (`task.assert_checklist_complete`).
The optional ones are a prompt, not a gate — a checklist where every line was
mandatory would be a checklist people learn to tick without reading.

No rules live in this file. Frappe does not call a child controller's
`validate`, so a rule written here would look like it worked and quietly never
run; the parent stamps `done_on` and the parent refuses the submission.
"""

from frappe.model.document import Document


class VMMSTaskChecklistItem(Document):
	pass
