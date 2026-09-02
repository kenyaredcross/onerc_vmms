# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A document whoever set the work provided: a form, a map, a template.

**Deliberately not the same place as the volunteer's evidence.** What a
coordinator hands out and what a volunteer brings back are different things with
different authors and different audiences, and a single attachment list would
have made "here is the form to fill in" and "here is the filled-in form" look
identical in the one place somebody goes looking for either.

The volunteer's side lives on the thread (`VMMS Task Update.proof`), where each
piece of evidence sits with the note that explains it, plus `final_evidence` on
the task itself for the one that is the finished work.
"""

from frappe.model.document import Document


class VMMSTaskBriefFile(Document):
	pass
