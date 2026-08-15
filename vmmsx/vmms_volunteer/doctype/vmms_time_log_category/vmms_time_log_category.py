# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Time Log Category — a society's own vocabulary for its volunteering.

Training, community event, office support, whatever a society reports on. It is
an **open** set, extended freely, and **no code anywhere branches on a category
value** — which is exactly what distinguishes it from `log_type` on the time log
itself. `log_type` names a validation rule and is therefore code; a category
names nothing and is therefore configuration.

The controller is empty on purpose. There is nothing to validate: a society's
vocabulary is not this app's to have an opinion about.
"""

from frappe.model.document import Document


class VMMSTimeLogCategory(Document):
	pass
