# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Society configuration the Stipend module reads. Four questions, no constants.

Every one of these is something a national society answers differently, and not
one of them may be a literal in a source file:

1. **Which geo level stipend paperwork is anchored at** — ACC-03. One society
   files progress reports out of its branches, another out of its wards.
   `vmms_stipend_anchor_level`. One setting governs the progress report and the
   payment form together, because they are two halves of the same period of work
   and anchoring them at different levels would leave a form unable to pair with
   the report it pays for.
2. **Which role may see progress reports** — `vmms_stipend_report_scope_role`.
3. **Which role may see payment forms** — `vmms_stipend_payment_scope_role`.
   Two questions rather than one, because they are two: a narrative of what a
   branch did over a month and the money paid for it are read by different
   people in most societies, and folding them into one setting would make that
   distinction impossible to express. Both are read by core at enforcement time
   through the `role_from_setting` registrations in `hooks.py`; they are named
   here only so the patch that installs them and the code that documents them
   agree on the spelling, and nothing in this module resolves one, because
   resolving it is core's.
4. **What currency the society pays in.** Read through core's `get_ui_config()`
   so a form gets the society's own answer and its fallbacks. **No currency code
   appears anywhere in this module**, and a society that has not set one gets a
   form with an empty currency rather than somebody else's.

The first three are **Custom Fields vmmsx owns** on core's National Society
Settings, installed by this app's own patches. Core's doctype is not edited: a
product pushing its fields into the shared foundation's source is how the
foundation stops being shared. The fourth is core's own field, read and never
written.

**Empty configuration means unconstrained, never forbidden.** A society that has
not named an anchor level has not thereby said stipend paperwork may exist
nowhere. The deliberate exception is the two scope roles, where empty means
*closed* — that is core's fail-closed behaviour, and it is the right direction
for records naming who was paid what.
"""

import frappe
from onerc_core.society.services import config

ANCHOR_LEVEL_FIELD = "vmms_stipend_anchor_level"

REPORT_SCOPE_ROLE_FIELD = "vmms_stipend_report_scope_role"
PAYMENT_SCOPE_ROLE_FIELD = "vmms_stipend_payment_scope_role"


def stipend_anchor_level() -> str | None:
	"""The Geo Level stipend paperwork must be anchored at, or None if unconstrained.

	Read through core's settings accessor so a site whose settings single has
	never been saved degrades to "unconstrained" instead of throwing, and read on
	every call so changing the setting takes effect without a restart.
	"""
	return config.settings().get(ANCHOR_LEVEL_FIELD) or None


def anchor_level_is_configured() -> bool:
	"""Whether the society has narrowed where stipend paperwork may be anchored."""
	return bool(stipend_anchor_level())


def assert_anchor_level(geo_node: str) -> None:
	"""Throw unless `geo_node` sits at the level this society permits (ACC-03).

	Geo is reached only through core's adapter: this app never queries the geo
	tables and never assumes a depth. With no level configured this is a no-op,
	which is what "the society has not narrowed it" has to mean.
	"""
	from frappe import _
	from onerc_core.geo.services import adapter

	required = stipend_anchor_level()

	if not (required and geo_node):
		return

	level = adapter.get_level(geo_node)

	if level["key"] == required:
		return

	labels = {row["key"]: row["name"] for row in adapter.level_labels()}

	frappe.throw(
		_("{0} is at {1} level. This society files stipend paperwork at {2} level.").format(
			frappe.bold(adapter.get_full_path(geo_node)),
			frappe.bold(level["name"]),
			frappe.bold(labels.get(required, required)),
		),
		frappe.ValidationError,
		title=_("Anchor Level Not Permitted"),
	)


def default_currency() -> str | None:
	"""The society's currency, for a payment form that has not been given one.

	Core's `get_ui_config()` rather than a raw field read, so this inherits its
	fallbacks. None when the society has not chosen one, and None is carried
	through to the form as an empty currency: an app that guessed here would put
	a number in front of somebody in a currency nobody chose.
	"""
	return config.get_ui_config()["locale"]["currency"]
