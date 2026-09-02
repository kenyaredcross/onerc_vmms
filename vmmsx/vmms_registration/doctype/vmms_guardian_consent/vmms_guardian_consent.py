# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Guardian Consent — a parent's permission, and somebody's check of it.

Separate from `VMMS Emergency Contact` on purpose, and the separation survives
the very common case of one person filling both roles. A guardian consents; an
emergency contact is called. Those are different acts with different legal
weight, and merging them into one row with two tickboxes would mean a society
that withdrew one had silently withdrawn the other. The wizard offers to copy
the details across so nobody types a name twice — what it copies is values, into
a second record.

**Two ticks, not one, and the second is not the first repeated.**
`consent_given` is what the guardian said. `is_verified` is what a reviewer at
the society did about it: looked at the signed form, telephoned the number, met
them at the branch. An application can carry a claimed consent nobody has
checked yet — that is the ordinary state of a freshly submitted application —
and `application.assert_approvable` refuses approval until the second tick is
there.

**`verified_by` and `verified_on` are stamped rather than typed.** They are the
answer to "who says so", and a field somebody can type their colleague's name
into does not answer it. They are cleared again if verification is withdrawn, so
a stale attribution never outlives the tick it belonged to.

**The stamping is called by the parent, and it has to be.** Frappe runs
`validate` on the document being saved and never on its child rows —
`run_before_save_methods` calls `self.run_method("validate")` and nothing walks
`get_all_children()` for it. A `validate` on this class would therefore be dead
code that looked like a guarantee, which is the worst shape a rule can take. So
the rule is a named method and `VMMSVolunteerApplication.validate` calls it for
every row; keeping it here rather than inlining it there is what stops the
knowledge of what these fields mean from drifting away from the fields.

**The evidence attachment is private, and that is enforced rather than
declared.** There is no `is_private` property on a DocField — the framework's
own switch is `make_attachment_public`, whose *absence* is what makes the desk
upload private, and which is deliberately not set here or on any doctype in this
app. But the desk is only half the story: the portal uploads through the file
API and posts back a URL, and a URL is a claim. So the guarantee is
`registration/services/evidence.py::secure`, which anchors the file to this
document and makes it private on the server whichever way it arrived. For a
document about a child that is not a detail worth leaving to a browser.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class VMMSGuardianConsent(Document):
	def stamp_verification(self) -> None:
		"""Record who verified this consent, the moment they say they have.

		Called from the parent's `validate`, so it fires whichever way the
		application was saved — the desk form, the approver's screen, or a
		service. Idempotent: an already-stamped row keeps its original
		attribution, because the person who checked the consent is not the
		person who happened to save the application next.
		"""
		if not self.is_verified:
			# Withdrawn verification takes its attribution with it. Leaving the
			# name behind would leave the record saying somebody vouched for a
			# consent that is no longer marked as verified.
			self.verified_by = None
			self.verified_on = None

			return

		if self.verified_by:
			return

		self.verified_by = frappe.session.user
		self.verified_on = now_datetime()
