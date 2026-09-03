# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Training somebody says they have done, in their own words.

**Not a `VMMS Certification`, and the difference is who is speaking.** A
certification is the *society's* record that it issued or recognised something,
carries an expiry, and feeds deployability. This is an applicant's claim about
their own past, made on a form, before anybody has checked it — and it must not
be able to make somebody deployable by being typed in.

So the two are separate tables on separate records and nothing converts one into
the other automatically. A branch that verifies a claim here issues a
certification, which is a decision somebody makes rather than a field that
copies itself."""

from frappe.model.document import Document


class VMMSDeclaredTraining(Document):
	pass
