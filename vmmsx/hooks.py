app_name = "vmmsx"
app_title = "Vmmsx"
app_publisher = "Nigel"
app_description = "Dynamic approach to the VMMS application"
app_email = "nigelnathan2@gmail.com"
app_license = "mit"

# Apps
# ------------------

# vmmsx is the operational layer on top of the shared OneRC foundation. Identity
# (Red Profile), geo (Geo Node and the adapter) and access (Geo Assignment,
# scope, approver routing) all live in onerc_core and are consumed from here —
# never reimplemented. Declaring the dependency is what stops this app from
# being installed onto a site where those doctypes do not exist.
required_apps = ["onerc_core"]

# Two icons, not one, because vmmsx serves two different desks and nobody
# should have to know a URL to reach either.
#
# The first is the staff desk built by `staff/services/workspaces.py` — System
# Manager plus whatever scope roles a society has layered on. The second is the
# self-service journey built by `registration/services/workspaces.py` —
# Registration, My Volunteering, My Membership — visible only to whichever
# roles a society has named for them, with no System Manager floor.
#
# `has_permission` for each is the workspace cluster's own Roles table, read
# through `has_desk_access()` / `has_self_service_access()` rather than
# re-resolving the underlying settings a second way — see those functions'
# docstrings. No `logo`: this app ships no icon asset, so the desk renders the
# framework's own alphabet-tile fallback rather than a broken image path.
#
# `/desk/...`, not `/app/...` — see `staff/services/workspaces.py`'s docstring
# on why the parent workspace's own shortcuts made the same switch.
add_to_apps_screen = [
	# **First, and that position is load-bearing.** `frappe.apps.get_route()`
	# resolves an app's default landing with `next(entry for entry in entries if
	# entry["name"] == app_name)` — the *first* entry wins — and
	# `get_default_path()` calls it to decide where a Website User goes after
	# signing in, ahead of `get_home_page()` and therefore ahead of everything
	# `registration/services/desk.py` arranges. So the portal has to be this
	# app's first answer to "where does vmmsx put somebody", or the society's own
	# people land on whichever other installed app happens to have a tile.
	#
	# `has_self_service_access` already records the other half of this: a tile is
	# where a login is *sent*, not merely something to click.
	{
		"name": app_name,
		"title": "VMMS Portal",
		"route": "/portal/dashboard",
		"has_permission": "vmmsx.registration.services.desk.has_portal_access",
	},
	{
		"name": app_name,
		"title": "VMMS",
		"route": "/desk/vmms",
		"has_permission": "vmmsx.staff.services.workspaces.has_desk_access",
	},
	{
		"name": "vmmsx-self-service",
		"title": "My VMMS",
		"route": "/desk/registration",
		"has_permission": "vmmsx.registration.services.workspaces.has_self_service_access",
	},
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/vmmsx/css/vmmsx.css"
# app_include_js = "/assets/vmmsx/js/vmmsx.js"

# include js, css files in header of web template
# web_include_css = "/assets/vmmsx/css/vmmsx.css"
# web_include_js = "/assets/vmmsx/js/vmmsx.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "vmmsx/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "vmmsx/public/icons.svg"

# Home Pages
# ----------

# The society's landing page is the site's front door, and everybody arriving at
# the bare domain is sent to it — signed in or not.
#
# **A redirect rather than the `home_page` hook**, which is the obvious tool and
# the wrong one here. `frappe.website.utils.get_home_page` only reaches app hooks
# for a guest: for anybody signed in it reads `Role.home_page` and Portal
# Settings first, and this site sets the latter to `/desk`. So the hook produced
# exactly half the rule — a visitor saw the landing page and a signed-in person
# was quietly sent somewhere else. `resolve_redirect` runs before any of that
# resolution, so it is the only place the answer is the same for everyone.
#
# The source matches the empty path: Frappe strips the slashes off a route
# before matching, so "/" is how you write "the site root".
website_redirects = [
	{"source": "/", "target": "/home"},
]

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# SPA deep-link routing: www/portal.html serves /portal itself; these rules send
# every sub-path to the same page so react-router owns the client-side routes.
#
# **/home is the same app under a second name**, because the public page needed
# an address a person could be told out loud and "/portal" is what the software
# calls itself. Serving it from a second www page would mean two copies of the
# shell, so the page is one and `main.tsx` reads which of the two roots it was
# mounted at. Both names stay live: /portal is in bookmarks and in the login
# redirect, and nothing is gained by breaking it.
#
# The SPA is *not* mounted at the bare site root, and that is not fastidiousness:
# /dashboard belongs to Buzz on this site and /profile to Frappe itself, so
# claiming the top level would take routes out from under two installed apps.
#
# **/verify is where a scanned card lands**, and it is a third name for the same
# page rather than a page of its own. What a steward scans is followed by a
# phone camera and has to render something a person can read, so it is a route
# and not an API path; the SPA's guest chunk draws it and asks
# `api/cards.py::verify` for the one answer it is allowed. Short because it is
# printed: the QR carries the whole URL and every character is modules on a card.
website_route_rules = [
	{"from_route": "/portal/<path:app_path>", "to_route": "portal"},
	{"from_route": "/home", "to_route": "portal"},
	{"from_route": "/home/<path:app_path>", "to_route": "portal"},
	{"from_route": "/verify/<path:app_path>", "to_route": "portal"},
]

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# One method, and it exists for one template: `templates/emails/standard.html`,
# this app's override of Frappe's email layout, which puts the society's own name
# and logo above whatever the site chose to say. Registering it here rather than
# reaching for `frappe.get_attr` in the template is what makes it callable in the
# sandboxed Jinja environment at all — and it keeps the crossing findable, the
# same argument the Buzz and payments seams make.
jinja = {"methods": ["vmmsx.notifications.services.branding.lockup"]}

# `welcome_email` — Frappe's hook for the subject of the account-created message
# — is deliberately **not** declared, and the reason is worth writing down so it
# is not helpfully added back. Frappe reads it as `get_hooks("welcome_email")[-1]`:
# the last app to declare it wins, hook order is installation order, and no app
# can ask for a position. On a bench with ERPNext installed after vmmsx, ERPNext
# answers, and the society's welcome email arrives titled "Welcome to ERPNext".
#
# The message is a seeded `Email Template` named in System Settings instead —
# `notifications/services/welcome.py`. That setting names one record and is not
# contested, and it carries the subject and the body together.

# Installation
# ------------

# before_install = "vmmsx.install.before_install"
#
# **Not optional, and not decoration.** Frappe does not run an app's patches on
# a fresh install — `install_app()` calls `set_all_patches_as_completed()`, which
# writes every line of `patches.txt` into the Patch Log without executing any of
# it. Everything this app keeps in a patch therefore never happened on a new
# site: the Custom Fields the access model reads, the Buzz geo anchor, the
# content surfaces, the society seed. See `vmmsx/install.py`, which runs them.
after_install = "vmmsx.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "vmmsx.uninstall.before_uninstall"
# after_uninstall = "vmmsx.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "vmmsx.utils.before_app_install"
# after_app_install = "vmmsx.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "vmmsx.utils.before_app_uninstall"
# after_app_uninstall = "vmmsx.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "vmmsx.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events
#
# The learning seam. `doc_events` is for reaching into *another* app's doctype,
# and this is the one place vmmsx does it: an enrollment whose progress reaches
# the end of a course may award a certification, if — and only if — a society
# wrote a `VMMS Course Mapping` for that course.
#
# The learning app is not modified, does not import vmmsx, and is not declared in
# `required_apps`: a society running volunteering without an LMS is ordinary, and
# on such a site this hook simply never fires. Everything the seam knows about
# the learning system is gathered in one block at the top of
# `vmmsx/volunteer/services/learning.py`; no other file in this app names an LMS
# doctype, and the line below is the only other place one is written down.
#
# The second entry is the framework's own `User`, and it adds no behaviour to it:
# it fills `redirect_url` on a brand-new *website* account so that setting a
# password from the welcome email lands in the portal rather than on a desk the
# account cannot open. Frappe consumes and clears the field on that first use.
# See `registration/services/desk.py::on_user_insert` for why this is a doc event
# rather than a copy of Frappe's sign-up endpoint.
doc_events = {
	"LMS Enrollment": {
		"on_update": "vmmsx.volunteer.services.learning.on_enrollment_update",
	},
	"User": {
		"after_insert": "vmmsx.registration.services.desk.on_user_insert",
		# Holding the role is half of authority — core reads Geo Assignment and
		# `Has Role` together — so granting or revoking one changes who may act
		# on an application just as surely as moving an assignment does.
		"on_update": "vmmsx.approvals.services.repair.on_authority_changed",
	},
	# **The queue follows authority, immediately.** Core's Geo Assignment is the
	# other half of "who may act here", and an approver appointed after an
	# application was submitted could decide it while it sat in nobody's queue —
	# they had the authority and no way to see the work. Re-syncing on migrate
	# fixed that for a deploy and left it broken for every appointment made
	# between deploys. See `repair.on_authority_changed`.
	"Geo Assignment": {
		"on_update": "vmmsx.approvals.services.repair.on_authority_changed",
		"on_trash": "vmmsx.approvals.services.repair.on_authority_changed",
	},
	# HRMS's own opening, and the one rule vmmsx adds to it: a screening question
	# set stops being editable once anybody has answered it. Wording and order
	# stay editable — `hr/services/application.py::assert_questions_unlocked` says
	# exactly what is frozen and why. HRMS's controller is not edited.
	"Job Opening": {
		"validate": "vmmsx.hr.services.application.on_opening_validate",
	},
	# The third doctype this app reaches into, and the only standard ERPNext one.
	# `Project` is the canonical programme of work here, and the two rules vmmsx
	# adds to it — it is anchored to a Geo Node, and to one the person filing it
	# actually runs — cannot live in ERPNext's controller without editing ERPNext.
	# Locked decision 4: custom fields, hooks and patches, never upstream source.
	"Project": {
		"validate": "vmmsx.deployment.services.project.on_validate",
	},
}

# Where signing in lands, and the only thing on this site that can decide it for
# everybody at once.
#
# `Role.home_page` is the ordinary answer and it is not sufficient here:
# `get_home_page()` takes the first role that carries one, in the order the
# `Has Role` rows happen to have been written, so a companion app that grants
# every new account a role of its own decides where this society's people land.
# Buzz does exactly that on this bench. `frappe.local.flags.home_page` is read
# ahead of that walk, and `make_session()` runs this hook before
# `set_user_info()` fills the redirect — so this is the one place the answer is
# the same for everyone. See `registration/services/desk.py::on_session_creation`,
# which carries the whole argument and the one exemption.
on_session_creation = "vmmsx.registration.services.desk.on_session_creation"

# Migration
# ---------
#
# The self-service surfaces are rebuilt from configuration on every migrate.
#
# They cannot be shipped as files the way a standard Workspace normally is: each
# one is shown to a role a *society* named in National Society Settings, and a
# workspace carrying no roles is visible to every desk user on the site. So the
# structure is code (`registration/services/workspaces.py`), the role is
# configuration, and the two are married here — which also means a society that
# changes one of those settings gets the surface rebuilt by a `bench migrate`
# rather than having to know a command.
#
# Both are idempotent and both do nothing at all when the settings are empty,
# which is the shipped state: no role, no surface, and no permission granted.
#
# The staff desk cluster (`staff/services/workspaces.py`) is a different shape
# on purpose: it is the admin-facing navigation for the app as a whole, not a
# per-person self-service surface, so its floor is System Manager and it is
# never "not installed" the way the three above can be. A society may still
# layer a narrower coordinator role onto one child by naming that doctype's own
# geo scope role in National Society Settings — see that module's docstring.
after_migrate = [
	# The Custom Fields vmmsx owns on ERPNext's `Project`: the owning Geo Node,
	# the donor block, and the risks and assumptions tables. **First**, and on
	# every migrate rather than once in a patch, because `onerc_scopeable_doctypes`
	# above names `vmms_geo_node` and core throws on every Project list view if
	# the registration points at a field that is not there. A patch runs once per
	# site by name and could not heal that; this can. See the module's docstring.
	"vmmsx.setup.project_fields.install",
	# The six roles every society's ladder needs — approver, approver, deployment
	# manager, volunteer, member, applicant — before anything below points a
	# setting at one of them. See the module docstring for why these six and not
	# a society-specific list: they are what `gambia.py` and `kenya.py` agree on
	# underneath their own extras, and a role a society still has to create in
	# Desk before Geo Assignment works is exactly the gap this closes.
	"vmmsx.setup.core_roles.install",
	"vmmsx.registration.services.workspaces.install",
	"vmmsx.registration.services.permissions.install",
	# The other half of the same decision, and the reason it is a service rather
	# than a patch is the reason the content grant is: it follows a society that
	# renames one of its roles. A volunteer, a member and somebody who has just
	# made an account hold portal roles — no desk access, and a home page inside
	# the SPA. The surfaces above stay installed for the clerk who files a paper
	# application; what this stops is the *applicant* being made a desk user.
	# See the module docstring, which sets out the decision it reverses.
	"vmmsx.registration.services.desk.install",
	# The third lever on where signing in lands, and the only one that reaches a
	# Website User: `LoginManager.set_user_info` asks `get_default_path()` before
	# it asks `get_home_page()` for those accounts, and `get_default_path()`
	# answers off the apps screen rather than off any role. Naming this app there
	# resolves to the first `add_to_apps_screen` entry above — the portal. Only
	# ever fills the setting when it is empty. See `desk.claim_default_app`.
	"vmmsx.registration.services.desk.claim_default_app",
	"vmmsx.staff.services.workspaces.install",
	# The staff-side counterpart of the self-service permissions install above:
	# grants each configured scope role read/write/create on the doctypes
	# behind its own workspace cluster, so a shortcut a coordinator can see is
	# never a permission error. Runs after the cluster itself for the same
	# reason the self-service install runs after its own workspaces.
	"vmmsx.staff.services.permissions.install",
	# Blocks every module that is not VMMS from a fresh desk, computed from the
	# workspace state the three installs above just produced. Create-if-missing,
	# never touched again once it exists — see its own module docstring.
	"vmmsx.staff.services.module_profile.install",
	# The role a society named as its page-content editor, granted read and write
	# on the content doctypes. Here rather than in the patch that installs the
	# setting, because a society that names a *different* role next year needs
	# the grant to follow, and a patch runs once. Does nothing while the setting
	# is empty, which is the shipped state.
	"vmmsx.content.services.permissions.install",
	# The shipped surfaces and editable slots, for the same reason and a sharper
	# one. `setup_content_module` seeded them, and a patch runs once per site by
	# name — so every slot added by a later release was missing on every existing
	# site, and the screen using it silently fell back to hardcoded wording with
	# no pencil on it. Additive and non-destructive by construction: `seed()`
	# never overwrites and `ensure_surface()` never edits, so a society's
	# rewritten home page survives every migrate untouched.
	"vmmsx.content.services.blocks.install_defaults",
	# The society's welcome email, as an Email Template the site is pointed at.
	# Here rather than in a patch for the same reason as the two above: a patch
	# runs once per site by name, so a message improved in a later release would
	# never reach a site that had already run it. Both writes are additive — the
	# record is never edited once it exists, and the setting is only filled when
	# it is empty.
	"vmmsx.notifications.services.welcome.install",
	# The two shipped card designs, as `VMMS Template` records. Here rather than
	# in a patch for the reason above it: a patch runs once per site by name, so
	# a site that migrated before cards existed would have the endpoints and no
	# template to render. Creates only what is absent, so a society that has
	# redesigned its card keeps it.
	"vmmsx.cards.services.templates.install",
	# The printed terms of reference, on the society's own letterhead. Same
	# additive rules and the same reason for being here rather than in a patch as
	# the card designs above.
	"vmmsx.deployment.services.templates.install",
	# The four messages an applicant gets about their own application: received,
	# approved, declined, and more information needed. Same additive rules as the
	# welcome email above, and here for the same reason.
	"vmmsx.notifications.services.lifecycle.install",
	# One row per gateway the payments app offers, so a society sees a list to
	# tick rather than an empty table. Here rather than only in its patch for the
	# reason above: a gateway added to the payments app after a site migrated
	# would otherwise never appear on the society's settings form. Additive and
	# non-destructive — a method a society unticked stays unticked — and a no-op
	# on a site with no payments app. Only the manual method arrives ticked; see
	# `methods.sync`.
	"vmmsx.member.services.methods.sync",
	# The four things a volunteer applicant agrees to: how their information is
	# used, permission to contact them, use of their personal details, and their
	# own declaration that what they submitted is true. Here rather than in a
	# patch for the reason the messages above are — a patch runs once per site by
	# name, so a declaration added in a later release would never reach a site
	# that had already migrated. Strictly create-if-absent: unlike the email
	# templates, shipped wording is never replaced on a deploy, because people
	# have agreed to this exact text. See the installer's own docstring.
	"vmmsx.registration.services.declarations.install",
	# Put every pending approval back in the inbox of whoever the gate admits
	# today. Authority is recomputed on every call, but the review queue is built
	# from ToDos written when a stage was entered — so a society that changes who
	# holds a role where has a queue that disagrees with its own access model
	# until something re-asks. A deploy is the one moment this app is guaranteed
	# to get to look. Grants nobody anything and moves no state; see the module
	# docstring for the failure it exists to end.
	"vmmsx.approvals.services.repair.resync_pending",
	# The geo anchor on Buzz's own event doctype. It is installed by a patch as
	# well, and needs to be here too because install order is not ours to
	# control: a site that installed vmmsx before Buzz ran that patch against an
	# absent app, where it correctly did nothing — and a patch is spent. Asked
	# again on every deploy, it installs the field the first time Buzz is really
	# there. Dormant and idempotent, so on every other deploy it costs one
	# `frappe.get_installed_apps()`.
	"vmmsx.patches.setup_buzz_seam.install_geo_anchor_field",
	# What a society screens an opening on, on HRMS's own `Job Opening`: the
	# qualification, the years, the licences, the documents and the questions.
	# Here for the same reason as the Buzz seam above and one more of its own —
	# three of the fields point at doctypes owned by ERPNext, HRMS and the LMS,
	# and a site that installs one of those next year should get the field then.
	# Dormant on a site with no HRMS. See the module docstring.
	"vmmsx.setup.job_opening_fields.install",
	# The other half of the HRMS seam: what a volunteering application carries on
	# HRMS's own `Job Applicant` — who the applicant is in this system, what they
	# answered, whether they withdrew, and what the application became. Dormant
	# where HRMS is not installed, like the block above.
	"vmmsx.setup.job_applicant_fields.install",
	# Seed the society named in this site's config, if it is not on the site
	# yet. Does nothing on every deploy after the first, and nothing at all on a
	# site that names no society. See the module docstring for why this is asked
	# from the site's own state rather than from a patch log.
	"vmmsx.setup.bootstrap.ensure_society",
]

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"vmmsx.tasks.all"
# 	],
# 	"daily": [
# 		"vmmsx.tasks.daily"
# 	],
# 	"hourly": [
# 		"vmmsx.tasks.hourly"
# 	],
# 	"weekly": [
# 		"vmmsx.tasks.weekly"
# 	],
# 	"monthly": [
# 		"vmmsx.tasks.monthly"
# 	],
# }

# The approval clock. An application rotting in an absent approver's queue is
# the number-one failure mode of a system like this, so both sweeps are
# scheduled rather than optional, and both are idempotent — running them twice
# in a day escalates nothing twice and expires nothing twice.
scheduler_events = {
	"daily": [
		"vmmsx.approvals.services.sla.sweep",
		"vmmsx.approvals.services.engine.expire_stale",
		# Memberships lapse on a date, so somebody has to notice the date
		# passing. Idempotent: it only moves Active to Expired.
		"vmmsx.member.services.membership.expire_lapsed",
		# A branch transfer arranged for next month has to happen next month, and
		# nothing else would notice the date arriving. Idempotent: it reads each
		# transfer's own state rather than remembering what it did yesterday, so
		# running it twice moves nobody twice.
		"vmmsx.deployment.services.transfer.apply_due",
		# The backstop under the two `doc_events` hooks above. Those catch the
		# ways authority normally changes; this catches every other way it can —
		# an assignment expiring on its own `valid_to` date, a role removed by a
		# script, a site restored from a backup. Idempotent and quiet: it reports
		# nothing on a day when nothing needed repairing, which is most days.
		"vmmsx.approvals.services.repair.resync_pending",
		# An invitation with an answer-by date that has passed is a question
		# nobody answered, and it has to stop looking like one still standing:
		# the place it holds is a place a coordinator could be filling. Only
		# touches invitations that carry a date — a society that sets none has
		# questions that stand until somebody answers them, which is what setting
		# none means. Idempotent: an expired row is no longer Pending.
		"vmmsx.deployment.services.assignment.expire_overdue",
		# Work that is past due and that nobody has been reminded about. Only ever
		# touches tasks carrying a reminder interval a society set — the shipped
		# state is zero, which sends nothing, because reminders nobody asked for
		# are how a system trains people to ignore it. Idempotent: a task
		# contacted inside its own interval is skipped, which is what
		# `last_contacted_on` is for.
		"vmmsx.task.services.task.chase_overdue",
	],
	# A WhatsApp broadcast approved on Monday and held until Thursday needs
	# somebody to notice Thursday arriving, and a daily sweep would send a
	# morning advisory in the middle of the night. Quarter-hourly is close enough
	# that "not before 14:00" means the afternoon, and coarse enough that the
	# sweep costs one indexed query most of the time. Idempotent twice over: it
	# only picks up submitted broadcasts still marked Scheduled, and the job it
	# queues is deduplicated on the broadcast's own name.
	"cron": {
		"*/15 * * * *": [
			"vmmsx.notifications.services.whatsapp.release_scheduled",
		]
	},
}

# Activation is re-evaluated after every save of a membership — that is how an
# approval decision recorded by the engine, or a payment confirmed by a gateway
# callback, becomes an active membership without either of them knowing that
# memberships activate. It is wired on the VMMS Membership controller's
# on_update rather than through doc_events: doc_events is for reaching into
# *another* app's doctype, and registering our own here as well would simply run
# the same service twice per save.

# Registrations vmmsx makes with onerc_core
# -----------------------------------------
#
# Core never imports this app; this app registers itself. The hooks are
# documented at the end of onerc_core/hooks.py.
#
# onerc_affiliation_providers — a satellite that makes someone a volunteer or a
# member reports it here so core can rebuild its affiliation index. The provider
# declares the doctypes it owns, which is what makes removal safe: core deletes
# a row only when a registered provider owns its reference_doctype and did not
# claim it.
#
# **Two providers now, and they are deliberately independent.** A person may be
# both a member and a volunteer; core calls every provider and reconciles their
# answers together. Because each declares only what it owns — Member declares
# VMMS Member, Volunteer declares VMMS Volunteer — deleting one satellite makes
# exactly one provider stop claiming, and the other provider's row survives
# because no owner of it declined to claim it. Isolation is a property of the
# declarations, not of anybody remembering to be careful.
onerc_affiliation_providers = [
	"vmmsx.member.affiliations.provide",
	"vmmsx.volunteer.affiliations.provide",
]

# onerc_scopeable_doctypes — declared per product doctype, once each doctype
# exists. The approval engine owns no records of its own to scope: it governs
# other apps' doctypes, and each of those declares itself.
#
# VMMS Membership is scoped on its ACC-02 anchor, `geo_node`, and names its role
# with `role_from_setting` rather than a literal: *which* of a society's roles
# may see membership records is that society's decision, and a literal here
# would hardcode exactly what the access model forbids. Core reads the named
# National Society Settings field at enforcement time.
#
# The field ships **empty**, which means no role resolves and core fails closed:
# until a society chooses the role, no non-administrator can read a membership.
# That is the intended pre-portal state — memberships carry personal data, and
# guessing a default would be this app inventing an access policy. Core logs
# every unresolved read, so the state is visible rather than silent, and the
# framework exemption means an administrator can always get in to set it.
#
# Installed by vmmsx.patches.install_membership_scope_role.
# VMMS Volunteer is registered the same way and for the same reasons, on its own
# ACC-02 anchor, `home_geo_node` — core's name for a person's place in the tree,
# and the field VMMSVolunteer.validate() makes mandatory. Its role setting ships
# empty too, and the volunteer register is if anything a stronger case for
# failing closed: it holds personal data about people the society has no
# employment relationship with.
#
# Installed by vmmsx.patches.install_volunteer_scope_role.
#
# What is *not* registered here is `VMMS Volunteer Application`. Its access is
# the approval engine's person-gate — who this specific document routed to, right
# now — and the engine already calls core's `guard` on the governed doctype
# before every decision. Scoping the application as well would put two different
# answers to "may you touch this" in front of one document.
#
# The Deployment module registers all three of its own doctypes, each on its own
# anchor and each naming its own settings field, for three separate reasons.
#
# `VMMS Deployment` is scoped on `geo_node`: it is the society's record of work
# done somewhere, and which branch may see it is exactly the question geo scoping
# answers.
#
# `VMMS Deployment Request` is scoped as well, and this is a deliberate
# difference from the volunteer application above. A request under terms of
# reference the society configured as `direct` never reaches the approval engine
# at all, so the person-gate is not an access model for it and scoping it is the
# only answer it has. Where a society does route one, the two agree by
# construction rather than competing: routing only ever names holders whose scope
# covers the node, which is the same property that lets `VMMS Membership` be both
# approvable and scopeable.
#
# `VMMS Branch Transfer` is scoped on `from_geo_node` — the branch the volunteer
# is leaving. That is where a routed transfer is approved by default, and it
# keeps the record visible to the branch it is about after the volunteer has
# moved on. The volunteer themselves moves to the new branch's scope the moment
# the transfer takes effect, because `VMMS Volunteer` is scoped on the field the
# transfer writes; nothing had to be built for that, and no history is rewritten
# to achieve it.
#
# All three settings fields ship **empty**, so core fails closed until a society
# chooses each role. Installed by vmmsx.patches.install_deployment_scope_roles.
onerc_scopeable_doctypes = [
	{
		"doctype": "VMMS Membership",
		"geo_node_field": "geo_node",
		"role_from_setting": "vmms_membership_scope_role",
	},
	{
		"doctype": "VMMS Volunteer",
		"geo_node_field": "home_geo_node",
		"role_from_setting": "vmms_volunteer_scope_role",
	},
	{
		"doctype": "VMMS Deployment",
		"geo_node_field": "geo_node",
		"role_from_setting": "vmms_deployment_scope_role",
	},
	# ERPNext's own `Project` is the programme of work, and vmmsx scopes it on the
	# Custom Field it owns — see `setup/project_fields.py`, which is also why that
	# installer runs on every migrate rather than once in a patch: a registration
	# naming a field that is not there makes every Project list view on the site
	# throw, and only an idempotent installer can heal that.
	#
	# It deliberately reuses the deployment scope role rather than naming a
	# settings field of its own. A project is the container a deployment is run
	# under, and a society that has said who may see its deployments has already
	# answered who may see the programmes they belong to; a second field would let
	# the two disagree, and a coordinator seeing work whose programme they cannot
	# open is the wrong side of that disagreement to land on. It needs no patch of
	# its own for the same reason — the setting it reads already exists.
	#
	# **This does narrow a standard doctype**, and that is the intended reading of
	# "Project is the canonical project record" on a volunteering site: a
	# programme belongs to a branch, and who may see a branch's work is the
	# question geo scoping exists to answer. An unanchored Project would be
	# invisible to everybody but an unrestricted user, which is why the anchor is
	# mandatory and `deployment/services/project.py::on_validate` says so in
	# words.
	{
		"doctype": "Project",
		"geo_node_field": "vmms_geo_node",
		"role_from_setting": "vmms_deployment_scope_role",
	},
	# `VMMS Deployment Assignment` reuses the deployment scope role, on the same
	# argument `VMMS Project` above reuses it: an assignment is one person's part
	# of a deployment, and a society that has said who may see its deployments has
	# already answered who may see the assignments raised under them. A second
	# field would let the two disagree, and a coordinator who can open a
	# deployment but not the roster on it is the wrong side of that disagreement.
	# It needs no patch for the same reason — the setting it reads already exists.
	#
	# Scoping it does not gate the volunteer answering their own: that goes
	# through `api/deployment.py::respond_to_assignment`, which establishes
	# ownership and then writes with `ignore_permissions`. A volunteer holds no
	# Geo Assignment at all, so scoping alone would refuse the one person
	# entitled to reply.
	{
		"doctype": "VMMS Deployment Assignment",
		"geo_node_field": "geo_node",
		"role_from_setting": "vmms_deployment_scope_role",
	},
	{
		"doctype": "VMMS Deployment Request",
		"geo_node_field": "geo_node",
		"role_from_setting": "vmms_deployment_request_scope_role",
	},
	{
		"doctype": "VMMS Branch Transfer",
		"geo_node_field": "from_geo_node",
		"role_from_setting": "vmms_branch_transfer_scope_role",
	},
	# The Stipend module registers both of its records, each on its own anchor and
	# each naming its own settings field.
	#
	# They are two registrations rather than one because they are two questions. A
	# progress report is a narrative of what a branch did over a period; a payment
	# form is what it paid for it. Most societies show those to different people,
	# and a single setting would make that impossible to express.
	#
	# Both are scoped on `geo_node`, held on each record rather than read through
	# the link between them, because core filters each doctype on a field of its
	# own and a form scoped through its report would be a form nobody could scope.
	# The two are checked against each other on every save, so holding the anchor
	# twice cannot mean holding two different answers.
	#
	# Neither is approvable in the engine's sense, and that is deliberate: stipend
	# approval is departmental (supervisor to head of department), the engine
	# resolves approvers by walking up the geo tree, and pointing one at the other
	# would route every report confidently to the wrong person. So geo scoping is
	# the whole of their access model today, and it is the honest one — it answers
	# who may *see* the paperwork, which is a question this app can answer.
	#
	# Both settings fields ship **empty**, so core fails closed until a society
	# chooses each role. Installed by vmmsx.patches.install_stipend_scope_roles.
	{
		"doctype": "VMMS Stipend Progress Report",
		"geo_node_field": "geo_node",
		"role_from_setting": "vmms_stipend_report_scope_role",
	},
	{
		"doctype": "VMMS Stipend Payment Form",
		"geo_node_field": "geo_node",
		"role_from_setting": "vmms_stipend_payment_scope_role",
	},
	# An announcement is scoped on the node it is sent *from*, and here geo
	# scoping is doing more work than it does anywhere else in this list.
	#
	# Elsewhere it answers who may read a record. Here it also answers who may
	# write one and from where, and writing one sends a message to every
	# volunteer and member beneath that node. Core's Geo Assignment is what stops
	# a branch coordinator from anchoring an announcement at the country and
	# addressing the whole society: the anchor has to sit inside the scope they
	# hold, which is the same check that governs everything else they touch.
	#
	# It is not approvable, deliberately. Routing a broadcast through the
	# approval engine would mean a weather advisory waiting in a queue, and the
	# thing that makes an advisory worth sending is that it goes now. The control
	# is who holds the role and where, decided before anybody writes anything,
	# rather than a review after they have.
	#
	# The settings field ships **empty**, so core fails closed until a society
	# chooses the role. Installed by vmmsx.patches.setup_notification_module.
	{
		"doctype": "VMMS Announcement",
		"geo_node_field": "geo_node",
		"role_from_setting": "vmms_announcement_scope_role",
	},
	# A WhatsApp broadcast is scoped exactly as an announcement is, and on
	# purpose it reuses the announcement's own settings field rather than naming
	# one of its own. The question both fields would answer is the same question
	# — who may speak for a branch to the people beneath it — and a society that
	# has answered it once should not be able to answer it two different ways by
	# accident. It is the argument `Project` makes for reusing the deployment
	# scope role, and it means this doctype needs no patch of its own: the
	# setting it reads already exists.
	#
	# Where it differs from an announcement is what happens after the scope check
	# passes. An announcement is published on the spot, because an advisory that
	# waits is not an advisory. A broadcast is filed at docstatus 0 and reaches
	# nobody until somebody with submit permission approves it — so here the geo
	# scope decides who may *propose* a broadcast and from where, and the submit
	# permission decides who may release one. Two different people, deliberately.
	{
		"doctype": "VMMS WhatsApp Broadcast",
		"geo_node_field": "geo_node",
		"role_from_setting": "vmms_announcement_scope_role",
	},
	# A task is scoped on the node the work belongs to, and geo scoping does the
	# same double duty here that it does for an announcement: it decides who may
	# read a task, and because the anchor has to sit inside the assigner's own
	# scope, it also decides where somebody may hand out work. A branch
	# coordinator assigns in their branch; they cannot anchor a task at the
	# country.
	#
	# What it deliberately does *not* decide is whether the volunteer holding the
	# task may see it. A volunteer holds no Geo Assignment, correctly, because the
	# register is not theirs to browse, and scoping their own work away from them
	# would be the access model refusing the one thing it should never refuse. That
	# question is ownership, answered in `api/tasks.py` against the task's own
	# `volunteer` field, and the two do not compete: scope governs the coordinator's
	# door, ownership governs the volunteer's, and neither is a way into the other.
	#
	# The settings field ships **empty**, so core fails closed until a society
	# chooses the role. Installed by vmmsx.patches.setup_task_module.
	{
		"doctype": "VMMS Task",
		"geo_node_field": "geo_node",
		"role_from_setting": "vmms_task_scope_role",
	},
	# A batch of work is scoped on its own anchor, reusing the task scope role for
	# the reason `VMMS Project` reuses the deployment one: a society that has said
	# who may see its tasks has already answered who may see the batch that made
	# them, and a second field would let the two disagree — leaving a coordinator
	# able to open forty tasks and not the record explaining why they exist. It
	# needs no patch for the same reason: the setting it reads already exists.
	{
		"doctype": "VMMS Task Batch",
		"geo_node_field": "geo_node",
		"role_from_setting": "vmms_task_scope_role",
	},
	# A branch location is scoped on the node whose place it is, so a coordinator
	# maintains the offices in their own area and nobody keeps a second list of
	# which branch owns what.
	#
	# This registration governs the desk only. What a signed-out visitor sees on
	# the public map is `is_published` on each location and nothing else, which is
	# the same division the content module draws between `is_public` on a surface
	# and the roles that may edit one. A location nobody published is invisible to
	# the map whatever role anybody holds; a location somebody published is served
	# to anybody, and no role is consulted.
	#
	# The settings field ships **empty**, so core fails closed for the desk half.
	# Installed by vmmsx.patches.setup_branch_module.
	{
		"doctype": "VMMS Branch Location",
		"geo_node_field": "geo_node",
		"role_from_setting": "vmms_branch_location_scope_role",
	},
]
#
# Approval routing is unaffected by any of this: the engine resolves approvers
# from the role named on each workflow stage, which is already configuration.

# Testing
# -------

# before_tests = "vmmsx.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "vmmsx.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "vmmsx.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "vmmsx.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["vmmsx.utils.before_request"]
# after_request = ["vmmsx.utils.after_request"]

# Job Events
# ----------
# before_job = ["vmmsx.utils.before_job"]
# after_job = ["vmmsx.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"vmmsx.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# Require all whitelisted methods to have type annotations
require_type_annotated_api_methods = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
