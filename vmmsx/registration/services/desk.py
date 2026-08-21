# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""A volunteer, a member and an applicant belong in the portal, not on the desk.

Three roles a society names — `vmms_self_service_role`,
`vmms_volunteer_member_role`, `vmms_membership_member_role` — are the ones its
own people hold: somebody who has made an account, somebody an approver
accepted, somebody whose membership activated. This service makes each of them
a **portal role**: no desk access, and a home page inside the SPA.

**This reverses an earlier decision, deliberately, and the reasoning it
replaces is worth keeping.** The self-service journey in this package is built
out of Frappe Workspaces, and a Workspace is a desk surface: `User
.set_system_user()` reads the roles an account holds and promotes it to System
User the moment one of them has `desk_access`. So desk access was switched on
*in order that* an approved volunteer could be shown the "My Volunteering"
workspace. That was correct while the desk was the only self-service surface
there was. It is not correct now that `portal/` exists and is the surface these
people are actually sent to, because the cost of the promotion is that a
volunteer can open `/app`, browse doctype list views, and land on the desk after
signing in — a whole administrative interface handed to somebody whose entire
business with this site is their own record.

**The desk surfaces are not removed, and that is not an oversight.** The three
workspaces and the two Web Forms in this package stay installed and keep
working: a registration clerk with a desk role of their own still uses them to
file a paper application, which is exactly the case `intake.py` distinguishes
from a person registering themselves. What changes is who is *made* a desk user.
A society that wants its volunteers on the desk after all reverses this by
ticking `desk_access` on the role, and nothing here fights that on the next
migrate — see `close()`.

**Three things have to be true together**, which is why they are one service:

1. the role does not grant desk access, so a new account is never promoted;
2. accounts already promoted are demoted. Frappe does this itself when
   `desk_access` changes on a saved Role — `Role.update_user_type_on_change()`
   re-evaluates every user holding it and keeps anybody who holds a *staff* role
   as well, which is the correct answer for a coordinator who also volunteers;
3. the role has a home page in the portal. Without it, `get_home_page()` falls
   through to `Portal Settings.default_portal_home`, which on a site set up for
   the desk says `/desk` — and a Website User sent to `/desk` gets a permission
   error for a front door. A per-role home page is also the right granularity:
   the coordinator's roles are untouched and still land on the desk.

Wired into `after_migrate` rather than a patch, for the reason the content
editor grant is: a patch runs once per site by name, and a society that names a
different self-service role next year needs the answer to follow it.
"""

import frappe

#: Where a self-service login lands after signing in. The portal's own dashboard
#: rather than `/portal`, which is the public landing page under a second name —
#: see the routing table in `portal/src/App.tsx` and the two roots in `main.tsx`.
PORTAL_HOME = "/portal/dashboard"

#: The one account this service leaves on the desk. `Administrator` is a
#: framework primitive rather than a society role — the same exemption
#: `staff/services/console.py` makes when it names a doctype instead of
#: `System Manager` — and it is the account a site is set up from, before any
#: society, any branch or any portal exists to land in.
DESK_ACCOUNT = "Administrator"

#: Where that one account goes. Named rather than left to the role walk, because
#: "leave the framework to decide" is what produced the bug this module fixes:
#: on a bench with a companion app granting every account a role with a home
#: page, the framework's answer for the Administrator is that app's dashboard.
DESK_HOME = "/app"

SETTINGS_DOCTYPE = "System Settings"
DEFAULT_APP_FIELD = "default_app"


def install() -> list[dict]:
	"""Make every configured self-service role a portal role. Idempotent.

	Returns one row per role, saying what it changed, so a `bench migrate` on a
	site that is already correct reports nothing changed rather than being
	silent about having run.
	"""
	return [close(role) for role in self_service_roles()]


def claim_default_app() -> dict:
	"""Make this app the landing for accounts the framework asks the apps screen about.

	Its own `after_migrate` step rather than a line inside `install()`, and for
	the reason `install_deployment_scope_roles` is its own patch: one function,
	one concern. `install()` answers "are the society's roles portal roles" and
	returns one row per role; this answers a question about the site.

	**The third of the three levers, and the one that reaches Website Users.**
	`close()` sets a role's home page and `on_session_creation` sets the session
	flag, and neither is consulted for a Website User: `LoginManager.set_user_info`
	reads `get_default_path() or "/" + get_home_page()`, and `get_default_path()`
	answers off the apps screen. With `System Settings.default_app` naming this
	app, that resolves through `frappe.apps.get_route("vmmsx")` to the first
	`add_to_apps_screen` entry — the portal — and every volunteer and member on
	the site lands on their own dashboard.

	**Only when it is empty**, which is the rule every setting in this module
	follows: a bench where somebody has deliberately made ERPNext the default app
	meant to, and a migrate is not the moment to overrule it. A site that wants
	this reversed clears or changes the setting by hand and nothing here fights
	it on the next migrate.
	"""
	# This package's own name, taken from the module path rather than typed: the
	# setting names an installed app, and there is exactly one right answer.
	app = __name__.split(".")[0]

	current = frappe.db.get_single_value(SETTINGS_DOCTYPE, DEFAULT_APP_FIELD)

	if current:
		return {"setting": DEFAULT_APP_FIELD, "status": "exists", "value": current}

	# `db_set` on the Single rather than a save: `System Settings.on_update`
	# rebuilds caches, reloads the scheduler's configuration and re-applies the
	# session-expiry policy, none of which this one field has anything to do
	# with, and all of which would run on every migrate of every site.
	frappe.db.set_single_value(SETTINGS_DOCTYPE, DEFAULT_APP_FIELD, app)
	frappe.clear_cache()

	return {"setting": DEFAULT_APP_FIELD, "status": "claimed", "value": app}


def self_service_roles() -> list[str]:
	"""The roles a society named for its own people, deduplicated.

	Read through each module's own resolver rather than off the settings
	document, so a setting naming a role somebody has since deleted answers
	nothing and is logged, exactly as it is everywhere else these three are
	read. A society that has named the same role twice gets it closed once.
	"""
	from vmmsx.member.services.society import membership_member_role
	from vmmsx.registration.services.society import self_service_role
	from vmmsx.volunteer.services.society import volunteer_member_role

	roles: list[str] = []

	for resolve in (self_service_role, volunteer_member_role, membership_member_role):
		role = resolve()

		if role and role not in roles:
			roles.append(role)

	return roles


def close(role: str) -> dict:
	"""Take the desk off one role and point it at the portal.

	**Only ever writes a field that is wrong.** `desk_access` is switched off
	when it is on; `home_page` is filled only when it is *empty*. The second is
	the "empty means unconfigured, a value is a decision" rule this app applies
	to every setting: a society that has pointed its volunteers at some other
	page of its own site meant to, and a migrate is not the moment to overrule
	it.

	The write goes through `save()` rather than `db_set` on purpose. The
	demotion of accounts already promoted is `Role.on_update` reacting to
	`desk_access` changing, and `db_set` would skip it — leaving the flag right
	and every existing volunteer still a System User, which is the failure this
	service exists to prevent and the one that looks fixed.
	"""
	if not frappe.db.exists("Role", role):
		return {"role": role, "status": "missing"}

	doc = frappe.get_doc("Role", role)
	changed = []

	if doc.desk_access:
		doc.desk_access = 0
		changed.append("desk_access")

	if not doc.home_page:
		doc.home_page = PORTAL_HOME
		changed.append("home_page")

	if not changed:
		return {"role": role, "status": "exists"}

	# An installer running as Administrator from `after_migrate`, writing a
	# framework record no society role has permission on. The elevation wraps one
	# save, the same shape as `roles.py::_as_system()`.
	doc.save(ignore_permissions=True)

	return {"role": role, "status": "closed", "changed": changed}


def on_session_creation(login_manager=None) -> None:
	"""Land every signed-in person in the portal, whatever else is installed.

	`close()` above points each self-service *role* at `PORTAL_HOME`, and that
	was the whole answer for as long as those roles were the only ones carrying
	a home page. On a real bench they are not, and the failure is worth writing
	down because nothing about it is visible from this app's own source.

	`frappe.website.utils.get_home_page()` walks `frappe.get_roles()` and takes
	the home page of the **first** role that has one. That order is the order the
	`Has Role` rows were written, not an order anybody chose. Buzz — installed
	here for events — grants `Buzz User` to every account from a `User`
	`after_insert` hook, so it is written *before* this app grants anything;
	`Buzz User` is a fixture carrying `home_page = /dashboard`; and Buzz
	redirects `/dashboard` to `/b`. The result was that every volunteer, member
	and coordinator on this site signed in and arrived in an events dashboard,
	and no amount of correctness on this app's own roles could out-vote it.

	**So the answer is the one lever that runs before the role walk.**
	`get_home_page()` returns `frappe.local.flags.home_page` ahead of everything
	else, and `LoginManager.set_user_info()` — which is what fills the
	`home_page` the login page redirects to — calls it after `make_session()`
	has run this hook. One request-local flag, set at the moment of signing in
	and never persisted.

	**Not a fixture edit, deliberately.** Blanking `Buzz User.home_page` would
	work until the next `bench migrate` re-imported Buzz's own fixture, and
	fighting another app's data every migrate is a repair that looks like a fix.
	Nothing here writes to Buzz, and Buzz's own users on a site without vmmsx are
	unaffected because this hook does not exist there.

	**`Administrator` gets the desk, named rather than left alone.** The obvious
	shape here is an early `return` for that one account, and it is wrong for the
	same reason the rest of this exists: falling through to the framework means
	falling through to the role walk, and the Administrator holds *every* role on
	the site — including the companion app's — so the account a society is
	configured from would land in an events dashboard. Saying `/app` is the
	honest version of "this one is not a portal person".

	Everybody else lands in the portal, coordinators included: being staff is a
	role somebody holds, not a thing they are instead of a volunteer, and the
	console is one link away from the dashboard.
	"""
	frappe.local.flags.home_page = (
		DESK_HOME if frappe.session.user == DESK_ACCOUNT else PORTAL_HOME
	)


def has_portal_access() -> bool:
	"""Is the portal this person's landing? The apps-screen tile's own gate.

	**A tile is where a login is sent, not merely something to click**, which is
	`has_self_service_access`'s observation and the reason this exists as a
	second, wider gate rather than reusing it. `frappe.apps.get_default_path()`
	reads the apps screen *before* `get_home_page()` for a Website User, so for
	those accounts it decides the landing outright and the session flag above
	never gets a say. With no vmmsx tile visible to them, the only app with one
	on this bench was a companion app — and every volunteer and member on the
	site signed in and arrived there.

	**Everybody except the desk account**, deliberately, and it is the same rule
	the flag applies: a coordinator has a portal too. The tile is the portal, so
	the answer to "may you open the portal" is "are you a person of this
	society", and the only account that is not is the framework's own.

	Guest is excluded because the apps screen is never drawn for one, and
	answering True would put a signed-out visitor's tile in a cache keyed on a
	session that has no person behind it.
	"""
	return frappe.session.user not in (DESK_ACCOUNT, "Guest")


def on_user_insert(doc, method=None) -> None:
	"""Send a brand-new website account to the portal after it sets a password.

	The second half of the welcome email. `templates/emails/new_user.html` sends
	somebody to `/update-password`, and when they set one the framework signs
	them in and redirects — to `User.redirect_url` if it has one, and otherwise
	to whatever `get_default_path()` says. On a bench with several apps installed
	that is `/apps`, which Frappe redirects to `/desk`, which is the one place
	this account cannot go. So the field exists for exactly this and is filled
	here.

	**Only a Website User, and only an empty field.** A desk account created by
	an administrator is left alone: their landing is the desk and the framework
	already handles it. A `redirect_url` somebody set deliberately is a decision,
	the same rule `close()` applies to a role's home page.

	The framework consumes it once — `reset_user_data()` blanks it as it reads it
	— and that is the right lifetime: it answers "where does this account go the
	first time", not "where does this person always go", which is what
	`Role.home_page` is for.

	**Wired on `doc_events`, and this is the second time this app reaches into
	another app's doctype.** The first is the learning seam. It is warranted for
	the same reason: `User` is the framework's, nothing about it is being changed,
	and the alternative would be a copy of Frappe's sign-up endpoint just to add
	one field to the document it creates.
	"""
	if doc.user_type != "Website User" or doc.redirect_url:
		return

	doc.db_set("redirect_url", PORTAL_HOME, update_modified=False)
