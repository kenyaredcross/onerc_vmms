# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One person accepting one version of a declaration, outside an application.

Written by the portal's terms panel (`registration/services/consent.py`) when a
volunteer or member accepts wording they had not accepted yet: somebody brought
over from the old system, or a version published with "Ask everyone to accept
again". Acceptances made while registering stay on the application or
membership; both are read together when deciding what is still outstanding.

**Never edited.** A consent is an act at a moment against a particular text, so
the record is refused any change after it is written. A newer acceptance is a
new record; the old one is the history.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class VMMSConsent(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(_("A consent record cannot be changed once it is written."))
