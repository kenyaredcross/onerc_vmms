# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Which sections of the manager console this person may actually open.

The console used to draw all nine of its tabs for everybody, and its own
docstring gave the reason: hiding one would mean naming a society's coordinator
role in `portal/src/`, which the access model forbids. The premise was right and
the conclusion was wrong. The rule is that **no role name appears in the
frontend and no screen decides what somebody may do** — not that nothing may be
hidden. `can_edit` on a content surface and `can_act` on an approval already
answer the same shape of question server-side, and this is the third.

**A section is named by its doctypes, never by a role.** The gate is
`frappe.has_permission`, which resolves the society's own scope role through
core and brings its geo scoping with it. So a society that names a Deployment
Manager for `vmms_deployment_scope_role` gets a Deployments tab for exactly the
people holding it, and this file never learns what the role is called. That is
the same reason `staff/services/permissions.py` keys its grants off settings
fields rather than literals.

**Read is the gate, write is the buttons.** A tab appears when somebody may read
what is behind it; whether they may act is asked again, per action, by the
endpoint that performs it. Gating the tab on `write` would hide a register from
a coordinator whose job is to look things up.

**Some sections are not gated, and only appear once something else is.**
Overview, the review queue, events and analytics carry no register of their own:
the queue is `my_queue`, which is personal and answers for the caller alone;
analytics is scoped per doctype and reports honest zeroes where a society has
named no role; events is Buzz's published listing, which every signed-in person
already sees on their own portal. None of them is a reason to *give* somebody
the console, so they ride along with the gated sections rather than standing on
their own — which is what makes `available()` false for a volunteer who follows
a stale link, instead of handing them a shell full of empty screens.

**Drift is a test, not a convention.** Every doctype named below is one
`staff/services/permissions.py` grants to some scope role; `staff/tests/
test_console.py` asserts that against both tables, so a module that gains a
doctype cannot gain a tab nobody can open, or a grant nobody can reach.
"""

import frappe

# The console's gated sections, in the order the sidebar draws them.
#
# `doctypes` is an *any* — a section opens if the person may read any one of
# them. The Registry is the case that shapes the rule: it lists volunteers and
# members side by side, and a society that has named a Volunteer Approver but no
# membership role should get the screen with one list filled and the other
# honestly empty, rather than no screen at all.
GATED_SECTIONS = (
	{"section": "registry", "doctypes": ("VMMS Volunteer", "VMMS Membership")},
	{"section": "tasks", "doctypes": ("VMMS Task",)},
	{"section": "deployments", "doctypes": ("VMMS Deployment", "VMMS Deployment Request")},
	{
		"section": "stipends",
		"doctypes": ("VMMS Stipend Progress Report", "VMMS Stipend Payment Form"),
	},
	# What the society took in and what it paid out, over the two registers that
	# are the only records of either. It reports on documents its readers can
	# already open one at a time — a membership's fee, a payment form's total —
	# so it is gated on those same two doctypes rather than on a money
	# permission this app does not have. A coordinator who may read neither has
	# no figures to be shown and does not get the tab.
	{
		"section": "finance",
		"doctypes": ("VMMS Membership", "VMMS Stipend Payment Form"),
	},
	{"section": "content", "doctypes": ("VMMS Content Block",)},
	# Addressing the people a branch is responsible for. Gated on the
	# announcement, which is scopeable on its own `geo_node`, so the tab appears
	# for whoever a society named in `vmms_announcement_scope_role` and the reach
	# of anything they send is bounded by their Geo Assignment rather than by
	# this list. SMS rides on the same gate rather than adding `SMS Campaign`
	# here: onerc_sms is optional, `sms_access()` below answers separately for
	# it, and the screen offers the channel only when both are true.
	{"section": "communication", "doctypes": ("VMMS Announcement",)},
)

# Sections with no register behind them. Drawn only when at least one gated
# section is — see the module docstring.
UNGATED_SECTIONS = ("overview", "queue", "events", "analytics")

# Sections gated on a doctype that **no configurable role is ever granted**, so
# they resolve to the administrator and to nobody else until a society
# deliberately widens them by hand.
#
# This is the deliberate exception to the rule `staff/tests/test_console.py`
# enforces for `GATED_SECTIONS` — that a gated doctype is one some installer
# hands to a scope role — and it is a separate tuple rather than an exemption
# inside that one so the exception is a thing you have to opt into rather than a
# test somebody weakened.
#
# The form builder is the case that shapes it. A question changes what every
# future applicant is asked and what an approver is shown; that is a different
# kind of act from running a register, and `staff/services/permissions.py`
# deliberately does not grant `VMMS Application Question` to any scope role. The
# framework exemption in this app's own rules covers it: `System Manager` is a
# framework primitive, not a society role, and naming the *doctype* here rather
# than the role is what keeps that true.
#
# **These stand on their own**, unlike the ungated ones: each has a register
# behind it, so somebody who may open it has a reason to be in the console even
# if they hold no scope role at all.
ADMIN_SECTIONS = ({"section": "questions", "doctypes": ("VMMS Application Question",)},)

# Sections whose register belongs to an **optional companion app**, and which
# therefore simply do not exist on a site that has not installed it.
#
# A third tuple rather than a fourth entry in `GATED_SECTIONS`, for the reason
# `sms_access()` gives below: every doctype named there is one
# `staff/tests/test_console.py` asserts exists on the site, which is a fair
# assumption for this app's own doctypes and not one it can make about HRMS's.
# vmmsx does not declare `hrms` in `required_apps` — a society running without
# it is ordinary, not half-installed — so `_readable` skipping a doctype the
# site does not have is the whole of the absence handling, and the tab is drawn
# for nobody.
#
# Unlike SMS this *is* a section: the screens behind it are vmmsx's own, and
# the recruiter never leaves the console for them. See `hr/services/openings.py`
# for why the record itself stays HRMS's.
COMPANION_SECTIONS = ({"section": "recruitment", "doctypes": ("Job Opening", "Job Applicant")},)

# The order the sidebar draws every section in, gated or not. Kept here rather
# than in the frontend so a society reading the list on the desk and a
# coordinator reading it in the sidebar are reading the same order.
ORDER = (
	"overview",
	"queue",
	# Beside the two application queues under People: an opening is the third
	# way somebody asks to join the society, and a recruiter clearing job
	# applications is doing the same shape of work as one clearing volunteer
	# applications.
	"recruitment",
	"registry",
	"tasks",
	"deployments",
	# The money reads before the paperwork that makes it: a coordinator opens
	# Finance to see the position and Stipends to act on one payment.
	"finance",
	"stipends",
	"events",
	"analytics",
	# After the registers and before the two configuration sections: it is a
	# thing somebody does *to* the people in those registers, so it reads in the
	# right order after them.
	"communication",
	"content",
	# Last, because it is the one a society touches least often: what the form
	# asks is decided once and then left alone for a year at a time.
	"questions",
)


def visible(user: str | None = None) -> list[str]:
	"""The console sections this person may open, in sidebar order.

	Empty when no gated section admits them, which is the whole of the
	"should this person have a console at all" question — see `available()`.
	"""
	user = user or frappe.session.user

	admitted = [entry["section"] for entry in GATED_SECTIONS if _readable(entry["doctypes"], user)]

	# Admin sections carry their own register, so one of them is reason enough to
	# be here. An administrator who has configured no scope role yet would
	# otherwise be shown no console at all on the very screen they need to set
	# the society up from.
	admitted += [entry["section"] for entry in ADMIN_SECTIONS if _readable(entry["doctypes"], user)]

	# A companion app's register is reason enough to be here too, the same
	# argument: somebody who may read the society's job openings has real work
	# in this console even if they hold none of its own scope roles.
	admitted += [entry["section"] for entry in COMPANION_SECTIONS if _readable(entry["doctypes"], user)]

	# The SMS side door is reason enough to be here too, the same argument as
	# ADMIN_SECTIONS just above: somebody holding only the society's configured
	# SMS role and none of the console's own scope roles still has a register
	# behind what they may do — onerc_sms's campaign builder — and must not be
	# bounced back to their own portal before the link to it ever renders. It
	# is not a `section` of its own, so it never joins `sections` below; it
	# only changes whether this function returns empty.
	if not admitted and not sms_access(user):
		return []

	sections = set(admitted) | set(UNGATED_SECTIONS)

	return [section for section in ORDER if section in sections]


def available(user: str | None = None) -> bool:
	"""May this person open the console at all?

	False for a volunteer, a member and anybody else holding none of the
	society's staff scope roles and no access to the SMS side door either. The
	console is not a screen they are shown empty; it is a place they are not
	sent.
	"""
	return bool(visible(user))


def sms_access(user: str | None = None) -> bool:
	"""May this person open onerc_sms's own campaign builder, on the desk?

	Not a `GATED_SECTIONS` entry, deliberately: every doctype named there is
	one `staff/tests/test_console.py` asserts *exists on the site*, a fair
	assumption for vmmsx's own doctypes and onerc_core's, and not one this app
	can make about `SMS Campaign` — it belongs to onerc_sms, an optional
	companion app vmmsx does not require. Rides alongside `has_desk_access()`
	in `api/console.py` instead: a side door into the framework's own form for
	whoever `staff/services/permissions.py` has granted it to, the same shape
	as the desk link itself, and for the same reason — nobody is shown a door
	that would give them a permission error at the other end.
	"""
	user = user or frappe.session.user

	return _readable(("SMS Campaign",), user)


def _readable(doctypes: tuple[str, ...], user: str) -> bool:
	"""May this person read any one of these?

	`frappe.has_permission` is asked rather than the settings fields being read
	here, so this file names no role and there is one answer to "may you" rather
	than two that can disagree. A doctype a site does not have is not an error:
	the same graceful-absence contract `_grant` keeps in
	`staff/services/permissions.py`.
	"""
	for doctype in doctypes:
		if not frappe.db.exists("DocType", doctype):
			continue

		if frappe.has_permission(doctype, ptype="read", user=user):
			return True

	return False
