# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""One thing somebody studied, and where.

**Years rather than dates, and both optional.** A registration form that
demanded the day somebody started secondary school would be a form most people
abandon. `Int` and not `Date` for the same reason: the year is what anybody
remembers and the year is all any reader here needs.

**`is_ongoing` rather than an empty `finished_in`.** A blank end year means
"they did not say", and somebody still in school is a different fact — one a
coordinator planning around term time actually acts on. Nothing derives either
from the other.

Nothing in this app reads a level as a rank. See `VMMS Education Level`."""

from frappe.model.document import Document


class VMMSEducation(Document):
	pass
