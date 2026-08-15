# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Announcement Type — a society's own vocabulary for what it sends.

News, Alert, Advisory, Weather Warning, Recruitment Drive: whatever a society
actually calls the things it broadcasts. It is configuration, and **no code
anywhere branches on a value of it**, exactly as `VMMS Template Category` and
`VMMS Time Log Category` are configuration nothing branches on.

What *does* change behaviour is `urgency` on the announcement itself, which is a
closed Select owned by code. The two sit next to each other on the form on
purpose, and the distinction is the one this app draws everywhere: the closed
set is what the server is willing to reason about, and the open set is what a
society is free to invent. A society that adds a type called "Emergency" gets a
new label; it does not get new behaviour, and nothing silently starts emailing
because of the word.

The doctype is deliberately empty of logic. It exists to be a Link target, so
the desk offers a picker rather than a free-text field that accumulates four
spellings of "Advisory".
"""

from frappe.model.document import Document


class VMMSAnnouncementType(Document):
	pass
