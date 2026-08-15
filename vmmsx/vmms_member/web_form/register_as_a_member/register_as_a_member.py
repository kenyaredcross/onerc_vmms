# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""No page context of its own. The form is the whole of it.

Frappe creates this module alongside a standard Web Form so a form *may* add
context. This one deliberately does not: everything the registration needs
happens server side, on the document, in `vmmsx/registration/services/intake.py`,
and a hook here would be a second place for it to live.
"""


def get_context(context):
	pass
