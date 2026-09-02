# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Declaration Acceptance — what one applicant agreed to, and when.

A child table on the registration itself, so an application carries its own
consents the way it carries its own answers and its own decisions. The approver
reads them off the document in front of them rather than joining anything.

**The title, the version and the whole text are snapshots**, written when the
declaration is accepted and never refreshed. This is the same rule
`VMMS Application Answer` applies to a question's wording and `VMMS Approval
Decision` applies to a stage's label, and here it is the entire point of the
record: a consent is worth nothing if the thing consented to can be rewritten
afterwards. A society that reworks its privacy notice next year changes what the
*next* applicant agrees to and touches nothing anybody has already agreed to.

The whole body is stored rather than a hash of it, because the question somebody
will eventually ask is "what exactly did this person agree to", and a hash can
only answer "not this". The cost is one text column per declaration per
application; the alternative is keeping every version of every declaration alive
forever so the hash has something to point at.

**Every field is read-only, including the tick.** An acceptance is a thing that
happened at a moment, recorded by `registration/services/declarations.py` on the
applicant's own behalf. Nothing about it is a coordinator's to edit afterwards —
an approver who thinks a consent is wrong returns the application for
correction, which is a decision with a reason on it.
"""

from frappe.model.document import Document


class VMMSDeclarationAcceptance(Document):
	pass
