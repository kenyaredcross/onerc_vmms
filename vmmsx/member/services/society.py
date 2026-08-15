# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Society configuration this module reads — ACC-03, the fee currency, branding.

Questions a national society answers differently, and none of which may be a
constant in a source file:

1. **Which geo level a membership anchors at.** Kenya may register members at
   county level, another society at ward, a third at branch. This is ACC-03, and
   the answer lives on National Society Settings as
   `vmms_membership_anchor_level` — a Custom Field vmmsx adds through its own
   patch. Core's settings doctype is not edited: a product must not push its
   fields into the shared foundation's source, so the field is owned, installed
   and read from here.
2. **What currency a fee is in.** A membership type may state its own; where it
   does not, the society's configured currency answers, through core's
   `get_ui_config()` fallbacks rather than a literal.
3. **Its name and its logo**, which a certificate renders. Core's, read through
   the same accessor; vmmsx stores no copy of either.
4. **Who may print somebody else's certificate**, a role the society names.
5. **Which role a member's own login is granted** when a membership activates,
   so that they can see their own. A different question from who may see every
   membership, and answered by a different setting.

Empty configuration means *unconstrained*, never *forbidden* — a society that
has not named an anchor level has not thereby said memberships may exist
nowhere. **The print role is the one deliberate exception**: empty there means
*nobody but the member*, because a blank access rule that granted everybody
would be the most dangerous default in this file.
"""

import frappe
from onerc_core.society.services import config

ANCHOR_LEVEL_FIELD = "vmms_membership_anchor_level"

# Who, besides the member themselves, may print a membership certificate. A
# Custom Field vmmsx owns, installed by
# `patches/install_certificate_print_role.py`. Empty means only the holder.
PRINT_ROLE_FIELD = "vmms_certificate_print_role"

# Which role a member's own login is given when a membership activates, so that
# they can see their own. A Custom Field vmmsx owns, installed by
# `patches/install_self_service_roles.py`, empty by default. Empty means nothing
# is granted, never that everybody is.
MEMBER_ROLE_FIELD = "vmms_membership_member_role"


def membership_anchor_level() -> str | None:
	"""The Geo Level a membership must anchor at, or None if unconstrained.

	Read through core's settings accessor so a site whose settings single has
	never been saved degrades to "unconstrained" instead of throwing, and read
	on every call so changing the setting takes effect without a restart.
	"""
	return config.settings().get(ANCHOR_LEVEL_FIELD) or None


def default_currency() -> str | None:
	"""The society's currency, for a membership type that names none."""
	return config.get_ui_config()["locale"]["currency"]


def society_name() -> str | None:
	"""The society's own name, for rendering onto a certificate."""
	return config.settings().organization_name


def logo() -> str:
	"""The society's logo, as core stores it. Empty string when unset.

	`logo` is an Attach Image on core's settings, so the value is whatever the
	upload produced: normally a site-relative path like `/files/logo.png`, and
	occasionally an absolute URL if an administrator typed one.

	Returned raw and unresolved. A browser rendering a page on this site follows
	a relative path perfectly well, and turning it into something else here would
	make every reader pay for a problem only the PDF path has — see
	`certificate.context_for(absolute_assets=True)`, which is where that
	conversion belongs and where it is asked for explicitly.

	Empty rather than None so a template can say `{% if society_logo %}` without
	knowing which of the two it might have been handed.
	"""
	return config.settings().logo or ""


def certificate_print_role() -> str | None:
	"""The role a society lets print a certificate that is not the holder's own.

	`vmms_certificate_print_role`, a Custom Field vmmsx owns and installs. Empty
	is the shipped state and means *nobody but the member* — see
	`certificate.may_print()`, which treats an unresolved role as a refusal and
	never as a grant.

	Read on every call so a society changing it takes effect without a restart.
	"""
	return config.settings().get(PRINT_ROLE_FIELD) or None


def membership_member_role() -> str | None:
	"""The role a member's own login is granted, or None if unconfigured.

	Resolved rather than read raw: a setting naming a role somebody has since
	deleted is logged and answers None, because a self-service grant that
	silently stopped happening would look exactly like a society that had not
	configured one yet. Read on every call, so changing it takes effect without
	a restart.

	Deliberately a different question from `vmms_membership_scope_role`, which
	says who may see *everybody's* memberships. This one says who a person is
	allowed to be to themselves.
	"""
	from vmmsx.registration.services import society as self_service

	return self_service.resolved_role(config.settings().get(MEMBER_ROLE_FIELD), MEMBER_ROLE_FIELD)


def anchor_level_is_configured() -> bool:
	"""Whether the society has narrowed where a membership may be anchored."""
	return bool(membership_anchor_level())


def assert_anchor_level(geo_node: str) -> None:
	"""Throw unless `geo_node` sits at the level this society permits (ACC-03).

	Geo is reached only through core's adapter — this app never queries
	`tabGeo Node` and never assumes a depth. With no level configured this is a
	no-op, which is what "the society has not narrowed it" has to mean.
	"""
	from frappe import _
	from onerc_core.geo.services import adapter

	required = membership_anchor_level()

	if not (required and geo_node):
		return

	level = adapter.get_level(geo_node)

	if level["key"] == required:
		return

	labels = {row["key"]: row["name"] for row in adapter.level_labels()}

	frappe.throw(
		_("{0} is at {1} level. This society registers memberships at {2} level.").format(
			frappe.bold(adapter.get_full_path(geo_node)),
			frappe.bold(level["name"]),
			frappe.bold(labels.get(required, required)),
		),
		frappe.ValidationError,
		title=_("Anchor Level Not Permitted"),
	)
