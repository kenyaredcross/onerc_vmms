# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One class on somebody's driving licence.

A row per class rather than a multi-select, because the classes on one licence
do not all expire together and a copy of the document belongs beside the class
it evidences.

**Read by nobody as a permission.** Holding a class here does not make somebody
deployable as a driver and no matching code consults it: that is a decision a
coordinator makes, having looked. A field that quietly authorised somebody to
drive a vehicle would be the wrong place for it to happen."""

from frappe.model.document import Document


class VMMSDrivingLicence(Document):
	pass
