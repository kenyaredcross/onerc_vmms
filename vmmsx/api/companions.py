# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The companion apps the portal offers a door to, and whether they are there.

Learning, chat and the service desk are not vmmsx's to build. A society running
this product alongside Frappe's LMS, Raven and Helpdesk wants those reachable
from the same sidebar as everything else, and a volunteer should not have to
know three URLs. So the portal shows a tab for each — and each tab is a real
navigation out of this app, not an embedding.

**The route is not written down here.** Every one of those apps already declares
itself through Frappe's `add_to_apps_screen` hook: its name, its title, where it
is mounted and how to ask whether this user may use it. Reading that is the
difference between a link that survives the LMS being remounted (its route is
`f"/{get_lms_path()}"`, a *setting*) and a link that quietly 404s the day
somebody changes it. vmmsx names the apps it offers a door to and nothing else.

**Absent is ordinary, not broken.** None of the three is in `required_apps`, and
a bench can carry an app that is not installed on *this* site — which is the
case that actually bites, and the reason this asks
`frappe.get_installed_apps()` rather than trying an import. A tab for an app
that is not installed is a tab that leads to a 404, so it is not drawn at all.
The same graceful-absence contract the payments, learning and Buzz seams already
keep.

**Permission is the app's own answer.** Each declares a `has_permission` method;
this calls it rather than guessing from roles. A society that has Helpdesk
installed for staff only should not show every volunteer a door into it, and the
app that owns the question is the one that gets to answer it.
"""

import frappe

# The companion apps the portal sidebar offers, in the order they appear.
#
# `app` is a Frappe app name, which is an identifier rather than a society's
# vocabulary, so naming it here is not the thing ACC-03 and the access model
# forbid. What is *not* here is any wording: `label_key` addresses a content
# block, so a society that calls its LMS "Training" renames the tab with the
# pencil on the page rather than by editing this file. The app's own declared
# title is the fallback when no block has been written.
COMPANIONS = (
	{"app": "lms", "label_key": "portal.nav.learning", "fallback": "Learning"},
	{"app": "raven", "label_key": "portal.nav.raven", "fallback": "Raven"},
	{"app": "helpdesk", "label_key": "portal.nav.helpdesk", "fallback": "Helpdesk"},
)


def _declared() -> dict[str, dict]:
	"""What each installed app says about itself on the apps screen.

	`frappe.get_hooks` already aggregates over the apps installed on this site,
	so an app sitting in the bench but not installed here simply does not
	appear. Keyed by app name; the last declaration wins, which matters to
	nobody because each of these apps declares exactly one.
	"""
	return {entry.get("name"): entry for entry in frappe.get_hooks("add_to_apps_screen") or []}


def _permitted(entry: dict) -> bool:
	"""Ask the app whether this user may use it.

	An app that declares no check is treated as open, which is Frappe's own
	reading of the field. A check that raises is treated as a refusal rather
	than allowed to take the sidebar down with it: one companion app in a bad
	state should cost its own tab, not the whole navigation.
	"""
	method = entry.get("has_permission")

	if not method:
		return True

	try:
		return bool(frappe.get_attr(method)())
	except Exception:
		frappe.log_error(title="Companion app permission check failed")

		return False


@frappe.whitelist()
def available() -> dict:
	"""The companion tabs this person should actually see.

	Returns the ones installed on this site and open to this user, each with the
	route the app declared for itself. The frontend draws what it is given and
	decides nothing: a tab absent from this list is a tab that does not exist,
	rather than one hidden by a check in a component.
	"""
	installed = set(frappe.get_installed_apps())
	declared = _declared()

	tabs = []

	for companion in COMPANIONS:
		app = companion["app"]

		if app not in installed:
			continue

		entry = declared.get(app)

		if not entry or not entry.get("route") or not _permitted(entry):
			continue

		tabs.append(
			{
				"app": app,
				"label_key": companion["label_key"],
				"fallback": entry.get("title") or companion["fallback"],
				"href": entry["route"],
			}
		)

	return {"apps": tabs}
