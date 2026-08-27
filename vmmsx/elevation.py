# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Running one write as the system, without signing the caller out.

Domain-agnostic infrastructure, deliberately outside every module package, for
the same reason `vmmsx/links.py` is: five modules needed the same three lines,
each kept its own copy, and the copies shared a bug that took a registration
wizard down.

**What the copies got wrong.** The obvious spelling of "become Administrator for
one save" is `frappe.set_user("Administrator")` and `frappe.set_user(previous)`
in a `finally`. It looks symmetrical and it is not, because `set_user` does more
than change the user:

    local.session.user = username
    local.session.sid  = username      # <- the live session id, overwritten
    local.session.data = _dict()       # <- csrf token and the rest, discarded

`frappe.local.session` **is** the live `Session.data` — `Session.__init__` binds
it — so restoring the user leaves the request holding a session whose `sid` is
an email address and whose `data` is empty. Nothing notices until the response
is on its way out: `app.sync_database()` queues `Session.update()`, which writes
`UPDATE tabSessions ... WHERE sid = <the email>` (no rows) and then
`frappe.cache.hset("session", <the real sid>, <the emptied data>)`. The next
request resumes from that cache entry, finds no user in it, and the person is a
Guest — signed out by having saved a draft, with every subsequent call answering
"Login to access".

So the restore has to put the whole session back, not just the user. That is all
this module does. It is not a permission model and it grants nothing on its own;
callers still justify their own elevation, as narrowly as they always did.

Administrator is a Frappe framework primitive, not a society role, so naming it
here is not the hardcoded-role rule being broken.
"""

from contextlib import contextmanager

import frappe

SYSTEM_USER = "Administrator"


@contextmanager
def as_system(user: str = SYSTEM_USER):
	"""Run the block as `user`, and hand the caller's session back intact.

	`sid`, `data` and `form_dict` are captured by reference and put back after
	`set_user` has replaced them, because the request that opened this block is
	still the request that has to answer — with the same login it arrived with.
	"""
	session = frappe.local.session
	previous = session.user
	sid = session.sid
	data = session.data
	form_dict = frappe.local.form_dict

	frappe.set_user(user)

	try:
		yield
	finally:
		frappe.set_user(previous)
		frappe.local.session.sid = sid
		frappe.local.session.data = data
		frappe.local.form_dict = form_dict
