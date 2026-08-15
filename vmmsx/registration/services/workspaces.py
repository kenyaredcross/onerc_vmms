# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""The three desk surfaces of the self-service journey, as native Workspaces.

A Frappe Workspace is a record, so these are configuration rather than a UI this
app wrote: no page, no template, no bundle. What is *code* is the shape — which
surface exists, what it offers and in what order — because that is the journey
and it is the same for every national society. What is *configuration* is the
role each one is shown to, and no role name appears anywhere in this file.

    Registration      the two registration forms, and nothing else. What a
                      brand-new account sees.
    My Volunteering   somebody's own volunteer record, applications, time logs
                      and certifications.
    My Membership     somebody's own memberships, and their own certificate.

**A workspace naming no role is visible to every desk user on the site.** That is
Frappe's own rule — `Workspace.is_permitted()` falls back to blocked modules when
`roles` is empty — and it is why `install()` refuses to build a surface whose role
a society has not configured. An unconfigured setting must not put a public
registration page in front of the whole society, so the failure direction is the
same fail-closed one the scope roles take.

**Why they sort before everything else.** The desk opens on the first workspace a
user is permitted to see, ordered by `sequence_id`. Every workspace shipped by
Frappe and by the other apps on a bench carries no roles at all, so they are
visible to any desk user, and a freshly approved volunteer would otherwise land
on whichever of them happened to sort first. These three carry negative sequence
ids so that the surface built for this person is the one they arrive at. It does
not hide anything: a society that wants a genuinely narrow desk uses Frappe's own
Module Profile to block the modules its volunteers have no business in, which is
a site policy and not vmmsx's to impose.

**Mounted onto the app it belongs to, same as the staff cluster.** `_sync()`
sets `app` to `"vmmsx"` on all three, and `hooks.py` gives them their own
apps-screen icon (a second one, alongside the staff cluster's) gated by
`has_self_service_access()` below — so a person who has just registered lands
on a real icon rather than needing to already know a URL.

**What a shortcut may point at, and why some of them are URLs.** Two different
reasons, and they are worth keeping apart.

`VMMS Volunteer` and `VMMS Membership` are registered with core as geo-scopeable,
and core fails closed: a volunteer holding no Geo Assignment sees an empty list,
correctly, because the register is not theirs to browse. Their *own* record is
reached through this app's owner-bypassed endpoints instead, so those shortcuts
are URLs. That reason is about **permission**.

`VMMS Time Log` and `VMMS Certification` are not geo-registered, so a DocType
shortcut works for either, narrowed to the person's own rows by the User
Permission the grant creates — and the time log shortcut is one. The
certification shortcut is a URL anyway, for a reason that is about **what can be
shown**: a list view can only display stored columns, and whether a certification
has lapsed is derived at the moment of asking and is deliberately not a column.
`my_certifications` computes it. The list view is still on the workspace's card,
because the records themselves are worth browsing; it is the *answer* that needs
an endpoint.
"""

import frappe
from frappe.utils.user import is_website_user

WORKSPACE_DOCTYPE = "Workspace"

LANDING = "Registration"
VOLUNTEER = "My Volunteering"
MEMBERSHIP = "My Membership"

# The published routes of the two native Web Forms. Named here because a
# shortcut has to point somewhere; they are the web forms' own `route`, and the
# forms are the source of truth for them.
VOLUNTEER_FORM_ROUTE = "/register-as-a-volunteer"
MEMBERSHIP_FORM_ROUTE = "/register-as-a-member"


def install() -> dict:
	"""Build or refresh the three surfaces. Idempotent, and safe to re-run.

	Called by the patch that installs the settings, by the Kenya seed once it has
	chosen the roles, and by nothing else automatically. A society that changes
	one of the three role settings afterwards re-runs it:

	    bench --site <site> execute vmmsx.registration.services.workspaces.install

	Reports what it did, per surface, so that "not installed" is visible as an
	answer rather than as silence.
	"""
	from vmmsx.member.services import society as member_society
	from vmmsx.registration.services import society as self_service
	from vmmsx.volunteer.services import society as volunteer_society

	return {
		LANDING: _sync(_landing(), self_service.self_service_role(), sequence=-1.0, module="Vmmsx"),
		VOLUNTEER: _sync(
			_volunteering(),
			volunteer_society.volunteer_member_role(),
			sequence=-3.0,
			module="VMMS Volunteer",
		),
		MEMBERSHIP: _sync(
			_membership(),
			member_society.membership_member_role(),
			sequence=-2.0,
			module="VMMS Member",
		),
	}


def _sync(spec: dict, role: str | None, sequence: float, module: str) -> str:
	"""Create or update one workspace for one configured role.

	Returns what happened, in a word, for the caller's report.

	**No role, no surface.** An unconfigured or deleted role means the workspace
	is not created, and an existing one is *removed* rather than left behind with
	its role stripped: a workspace whose `roles` table has been emptied is visible
	to everybody, so leaving one lying about would turn clearing a setting into
	the exact opposite of what clearing it means.
	"""
	label = spec["label"]
	exists = frappe.db.exists(WORKSPACE_DOCTYPE, label)

	if not role:
		if exists:
			frappe.delete_doc(WORKSPACE_DOCTYPE, label, force=True, ignore_permissions=True)

			return "removed: no role configured"

		return "skipped: no role configured"

	doc = frappe.get_doc(WORKSPACE_DOCTYPE, label) if exists else frappe.new_doc(WORKSPACE_DOCTYPE)

	doc.update(
		{
			"label": label,
			"title": label,
			"module": module,
			"icon": spec["icon"],
			"public": 1,
			# Not a standard workspace: these are built from configuration at
			# install time, not shipped as a file. `Workspace.on_update` exports
			# a standard one to disk in developer mode, and a surface whose roles
			# come from a society's settings has no business being written back
			# into this app's source.
			"standard": 0,
			# Mounts this workspace onto the VMMS self-service apps-screen icon
			# and its dock — see `has_self_service_access()` below and the
			# `add_to_apps_screen` entry in `hooks.py` that names it.
			"app": "vmmsx",
			"sequence_id": sequence,
			"content": frappe.as_json(spec["content"]),
		}
	)

	doc.set("roles", [{"role": role}])
	doc.set("shortcuts", spec["shortcuts"])
	doc.set("links", spec.get("links") or [])

	doc.save(ignore_permissions=True)

	return "updated" if exists else "created"


def has_self_service_access() -> bool:
	"""Whether the current user may open any of the three self-service surfaces.

	The `has_permission` gate named on vmmsx's second `add_to_apps_screen`
	entry — see `hooks.py`. Reads the Roles table of whichever of Registration,
	My Volunteering and My Membership are installed today, rather than
	re-resolving the three settings this module already turns into workspace
	roles in `install()`: a surface a society has not configured contributes no
	roles, exactly like a workspace `_sync()` removed for the same reason, so
	nothing here needs to ask "is it configured" separately from "does the
	Roles table say so". No System Manager floor, on purpose — unlike the staff
	cluster, these three carry only the one role a society named, and an
	administrator who holds no self-service role does not automatically get a
	tile for a journey that is not theirs.
	"""
	# A Website User cannot open a workspace at all, so offering them a tile that
	# routes to one is offering a permission error. This is not belt and braces:
	# `get_default_path()` reads the apps screen to decide where a person lands
	# *after signing in*, so a tile shown here is where a self-service login is
	# sent — and since `desk.py` made those roles portal roles, the honest answer
	# for anybody holding one is that this cluster is not theirs. The workspaces
	# themselves are untouched and still serve the clerk who has a desk role.
	if is_website_user():
		return False

	roles = frappe.get_all(
		"Has Role",
		filters={"parent": ["in", (LANDING, VOLUNTEER, MEMBERSHIP)], "parenttype": WORKSPACE_DOCTYPE},
		pluck="role",
	)

	return bool(set(roles) & set(frappe.get_roles()))


# --- the three surfaces ---------------------------------------------------


def _landing() -> dict:
	"""Exactly two actions, and nothing else.

	The whole of what somebody who has just made an account may do. It stays
	visible after they are approved, and that is deliberate rather than an
	oversight: registering for the *other* affiliation is the same two buttons,
	and a volunteer who later wants to become a member comes back here.
	"""
	shortcuts = [
		_url_shortcut("Register as a Volunteer", VOLUNTEER_FORM_ROUTE, "users"),
		_url_shortcut("Register as a Member", MEMBERSHIP_FORM_ROUTE, "badge"),
	]

	return {
		"label": LANDING,
		"icon": "edit",
		"shortcuts": shortcuts,
		"content": [
			_header("Register with the society"),
			_paragraph(
				"You have an account. Choose what you would like to register as. You may do both,"
				" now or later, and you will keep the same profile either way."
			),
			*_shortcut_blocks(shortcuts, col=6),
		],
	}


def _volunteering() -> dict:
	"""What a volunteer may see about themselves.

	The record and the applications are reached through this app's own endpoints,
	because the register is geo-scoped and a volunteer holds no scope. Time logs
	are an ordinary list view, narrowed to this person by the User Permission
	created alongside their role.

	Certifications are an endpoint rather than a list view, for a different
	reason than the register is: the list view works and is on the card below,
	but it can only show what is stored, and whether a certification has lapsed
	is not stored. `my_certifications` derives the lapse per row and the
	deployability above them at the moment of asking, which is the question
	somebody opening this workspace actually has.
	"""
	shortcuts = [
		_url_shortcut("My Volunteer Record", "/api/method/vmmsx.api.volunteer.my_volunteer", "user"),
		_url_shortcut("My Applications", f"{VOLUNTEER_FORM_ROUTE}/list", "file"),
		_doctype_shortcut("My Time Logs", "VMMS Time Log", "clock"),
		_url_shortcut("My Certifications", "/api/method/vmmsx.api.volunteer.my_certifications", "award"),
	]

	return {
		"label": VOLUNTEER,
		"icon": "users",
		"shortcuts": shortcuts,
		"links": [
			_card("Volunteering"),
			_link("VMMS Time Log"),
			_link("VMMS Certification"),
		],
		"content": [
			_header("My volunteering"),
			_paragraph(
				"Your own record with this society, and the applications behind it. Your"
				" certifications show what you hold, when each one runs out, and whether any has"
				" lapsed, which is worked out fresh every time you look rather than stored. A"
				" lapsed certification your society treats as a requirement means you are not"
				" deployable on it until you renew it; it does not end your volunteering."
			),
			*_shortcut_blocks(shortcuts, col=3),
			_card_block("Volunteering"),
		],
	}


def _membership() -> dict:
	"""What a member may see about themselves, and the certificate they may print."""
	shortcuts = [
		_url_shortcut("My Memberships", "/api/method/vmmsx.api.member.my_memberships", "badge"),
		_url_shortcut(
			"Download My Certificate",
			"/api/method/vmmsx.api.member.download_my_certificate",
			"printer",
		),
		_url_shortcut("My Registrations", f"{MEMBERSHIP_FORM_ROUTE}/list", "file"),
	]

	return {
		"label": MEMBERSHIP,
		"icon": "badge",
		"shortcuts": shortcuts,
		"content": [
			_header("My membership"),
			_paragraph(
				"Your memberships with this society, what they cover and when they run to. A"
				" certificate is issued for an active membership, and it is yours to print."
			),
			*_shortcut_blocks(shortcuts, col=4),
		],
	}


# --- block and row builders -----------------------------------------------


def _url_shortcut(label: str, url: str, icon: str) -> dict:
	return {"type": "URL", "label": label, "url": url, "icon": icon, "color": "Blue"}


def _doctype_shortcut(label: str, doctype: str, icon: str) -> dict:
	return {"type": "DocType", "label": label, "link_to": doctype, "icon": icon, "color": "Grey"}


def _card(label: str) -> dict:
	return {"type": "Card Break", "label": label, "link_count": 2, "hidden": 0}


def _link(doctype: str) -> dict:
	return {"type": "Link", "label": doctype, "link_type": "DocType", "link_to": doctype, "hidden": 0}


def _header(text: str) -> dict:
	return _block("header", {"text": f"<span class='h4'><b>{text}</b></span>", "col": 12})


def _paragraph(text: str) -> dict:
	return _block("paragraph", {"text": text, "col": 12})


def _shortcut_blocks(shortcuts: list[dict], col: int) -> list[dict]:
	return [_block("shortcut", {"shortcut_name": row["label"], "col": col}) for row in shortcuts]


def _card_block(label: str) -> dict:
	return _block("card", {"card_name": label, "col": 4})


def _block(kind: str, data: dict) -> dict:
	"""One content block, with a stable id.

	The id is derived from the block rather than generated, so re-running the
	installer produces byte-identical content and a workspace nobody edited shows
	no version history of changes that were not changes.
	"""
	import hashlib

	seed = f"{kind}:{sorted(data.items())}"

	return {"id": hashlib.sha1(seed.encode()).hexdigest()[:10], "type": kind, "data": data}
