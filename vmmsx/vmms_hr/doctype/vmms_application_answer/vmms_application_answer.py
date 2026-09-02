# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One answer to one screening question, with the question kept beside it.

**The question is snapshotted, not referenced**, and that is the whole reason
this row carries four read-only fields it could have looked up. A society edits
its screening questions — reworded, reordered, retired — and an application
decided next March against wording that changed in January would otherwise read
as an answer to a question nobody asked. `VMMS Application Answer` keeps the
question as it stood at the moment somebody answered it, which is the same rule
`VMMS Application Answer`'s namesake in the registration module follows and the
same one `VMMS Deployment Assignment` follows about its terms of reference.

`question_id` is the thread back to the live question where one still exists, so
a report can group ten years of answers by the thing they were about; the text
beside it is what a person reads.

An upload goes in `answer_file` and everything else in `answer`, as text. Two
fields rather than one because a private file has to be findable as a file —
`hr/services/application.py` moves each one into private storage and anchors it
to the application, and it cannot do that to a string that happens to look like
a path.
"""

from frappe.model.document import Document


class VMMSApplicationAnswer(Document):
	pass
