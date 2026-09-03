# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Somebody who will speak for this person, and how to reach them.

**Not an emergency contact, and the two must never be conflated.**
`VMMS Emergency Contact` is who a society calls when something has gone wrong on
a deployment; this is who it calls before deciding whether to send somebody at
all. They are asked at different moments, read by different people, and a
society that merged them would be phoning a referee about an accident.

Neither field here is required beyond the name. A referee with no phone number
is a lead a branch can still follow, and a form that refused one would mostly be
refusing people whose referee is reachable some other way."""

from frappe.model.document import Document


class VMMSProfessionalReference(Document):
	pass
