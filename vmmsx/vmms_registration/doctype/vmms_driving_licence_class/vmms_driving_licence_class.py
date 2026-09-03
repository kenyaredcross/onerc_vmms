# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The driving licence classes this society recognises.

**Deliberately not a fixed list.** Licence classes are national law and they are
not the same law twice: the categories a Kenyan licence carries are not the ones
a Tanzanian or a European one does. A hardcoded enum here would have been a
product that only works in the country it was written in, which is the thing
this app exists not to be.

Nothing branches on a class. It is recorded so a coordinator arranging transport
can read it, and matched against nothing."""

from frappe.model.document import Document


class VMMSDrivingLicenceClass(Document):
	pass
