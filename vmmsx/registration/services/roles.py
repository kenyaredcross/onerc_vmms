# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Granting a person the role their approval earned them. Names no role, ever.

When a volunteer application is approved, or a membership activates, the person
it belongs to should be able to see their own record. That is a *role*, and
which role it is belongs to the society — `vmms_volunteer_member_role` and
`vmms_membership_member_role`, each read by the module that owns it. This
service is handed the answer; it never asks the question and no role name
appears anywhere in this file.

Three properties, all of them tested:

1. **Idempotent.** Granting a role somebody already holds writes nothing and
   returns False. Acceptance and activation are both re-evaluated after every
   save, so this is called far more often than anything changes.
2. **Silent about people who cannot log in.** `Red Profile.user` is nullable by
   core's design — a volunteer registered from a paper form has no login — and
   that is the ordinary case, not an error. Nothing is granted and nothing is
   raised.
3. **Fail-closed on configuration.** An unset setting, or one naming a role
   somebody has since deleted, grants nothing and says so in the error log. It
   never falls back to a default, because a default here would be this app
   inventing a society's access policy.

**The elevation, and why it is here.** Adding a role writes to a `User`, and the
caller is an approver recording a decision or a payment gateway confirming a
transaction. Neither holds — or should hold — write permission on the site's
user accounts, and requiring it would mean a society had to grant User write
access to every membership approver in the country for a member to be able to
see their own certificate. Each elevation wraps exactly one write, the same
one-call shape `member/services/member.py::_as_system()` uses and for the same
reason: the moment it wraps two it stops being auditable at a glance.
Administrator is a Frappe framework primitive, not a society role.

**A User Permission is bounded or it is not written.** `scope_to` requires the
doctypes it applies to, because a permission with `apply_to_all_doctypes`
narrows every doctype linking to the allowed record, for that user, everywhere
and forever — and follows them into whatever else they do for the society. See
its docstring for the failure that shape causes.

**Granting a desk role changes what kind of account this is**, and that is the
mechanism rather than a side effect. `User.set_system_user()` reads the roles a
user holds and sets `user_type` to System User if any of them has `desk_access`.
That is what lets an approved volunteer be shown a Workspace, because a Workspace
is a desk surface and a Website User cannot reach one. A society that does not
want that leaves the settings empty and nothing here ever runs.
"""

from contextlib import contextmanager

import frappe

from vmmsx import elevation

USER_PERMISSION_DOCTYPE = "User Permission"

# Accounts that are never granted anything. Guest is not a person; Administrator
# already holds everything and re-saving it on every approval would be noise.
# Both are Frappe framework primitives, not society roles.
SKIP_USERS = ("Guest", "Administrator")


@contextmanager
def _as_system():
	"""Run one write as the system rather than as whoever triggered it.

	As narrow as it can be: it wraps a single `save()`, so it stays auditable at
	a glance. See the module docstring for why the caller cannot hold the
	permission itself.

	The mechanics are `vmmsx.elevation`: restoring the user is not enough on
	its own, because `set_user` overwrites the live session id and discards the
	session data with it, which signs the caller out one request later.
	"""
	with elevation.as_system():
		yield


def grant(user: str | None, role: str | None) -> bool:
	"""Give `user` the role `role`. Returns whether anything changed.

	Every reason to do nothing is a quiet False: no login, a framework account,
	no role configured, a role that no longer exists, a role already held. The
	one thing that is *not* quiet is a configured role that has gone missing —
	`society.resolved_role` logs that, because it looks exactly like a working
	system while granting nobody anything.
	"""
	if not user or user in SKIP_USERS:
		return False

	if not role or not frappe.db.exists("Role", role):
		return False

	if not frappe.db.exists("User", user):
		return False

	if role in frappe.get_roles(user):
		return False

	with _as_system():
		account = frappe.get_doc("User", user)
		account.add_roles(role)
		_apply_module_profile(user)

	# The role a user holds is read from a cache keyed on the user, and this
	# grant is normally followed in the same request by a check that reads it.
	frappe.clear_cache(user=user)

	return True


def _apply_module_profile(user: str) -> None:
	"""Give a freshly self-serviced login the clean desk — if nobody chose one yet.

	`vmmsx.staff.services.module_profile` installs "VMMS Only" from
	`after_migrate`; this only ever points a login at it, never builds it, so a
	site that has not migrated since that installer landed grants the role
	above and quietly skips this rather than failing the whole grant over a
	desk preference.

	**Only a blank field is filled.** A society that assigned this person a
	different Module Profile — or deliberately none — made that choice on
	purpose, and a role grant is not the moment to override it. This is the
	same "empty means unconfigured, an existing value is a decision" shape
	every setting in this app already follows.
	"""
	from vmmsx.staff.services import module_profile

	if frappe.db.get_value("User", user, "module_profile"):
		return

	if not frappe.db.exists("Module Profile", module_profile.PROFILE_NAME):
		return

	frappe.db.set_value("User", user, "module_profile", module_profile.PROFILE_NAME)
	frappe.clear_document_cache("User", user)


def scope_to(user: str | None, allow: str, for_value: str | None, applicable_for) -> list[str]:
	"""Narrow named list views to one record, through User Permissions.

	Frappe's own answer to "let them see only their own", and the reason a
	self-service workspace can point at ordinary desk list views at all: a
	`User Permission` allowing exactly one `VMMS Volunteer` filters a list of
	anything that links to one, without a line of query code.

	**`applicable_for` is required, and it is the whole safety of this
	function.** A User Permission with `apply_to_all_doctypes` narrows *every*
	doctype that links to the allowed record, for that user, everywhere on the
	site and forever. That is far more than a self-service surface asked for,
	and the damage is invisible until somebody who wears two hats — a
	registration clerk who is also a member, a coordinator who also volunteers —
	quietly stops being able to see other people's records in the job they were
	hired for. So one row is written per doctype the surface actually lists, and
	nothing else is touched.

	Returns the doctypes it narrowed. Idempotent, and quiet about a person with
	no login for the same reason `grant()` is.
	"""
	if not user or user in SKIP_USERS or not for_value:
		return []

	if not frappe.db.exists("User", user):
		return []

	narrowed = []

	for doctype in applicable_for:
		if not frappe.db.exists("DocType", doctype):
			continue

		existing = frappe.db.exists(
			USER_PERMISSION_DOCTYPE,
			{"user": user, "allow": allow, "for_value": for_value, "applicable_for": doctype},
		)

		if existing:
			continue

		with _as_system():
			frappe.get_doc(
				{
					"doctype": USER_PERMISSION_DOCTYPE,
					"user": user,
					"allow": allow,
					"for_value": for_value,
					"apply_to_all_doctypes": 0,
					"applicable_for": doctype,
				}
			).insert()

		narrowed.append(doctype)

	return narrowed


def holds(user: str | None, role: str | None) -> bool:
	"""Does this user hold this role? The predicate, for a screen or a test."""
	if not (user and role):
		return False

	return role in frappe.get_roles(user)
