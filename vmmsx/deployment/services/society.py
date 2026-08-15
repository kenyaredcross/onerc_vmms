# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""Society configuration the Deployment module reads. Five questions, no constants.

Every one of these is something a national society answers differently, and not
one of them may be a literal in a source file:

1. **Which geo level a deployment is anchored at** — ACC-03. One society runs
   deployments out of its regions, another out of its branches.
   `vmms_deployment_anchor_level`. It governs `VMMS Deployment` and
   `VMMS Deployment Request` alike, because they are two views of the same piece
   of work and anchoring them at different levels would make a request unable to
   become the deployment it asked for.
2. **Which role may see deployments** — `vmms_deployment_scope_role`.
3. **Which role may see deployment requests** — `vmms_deployment_request_scope_role`.
4. **Which role may see branch transfers** — `vmms_branch_transfer_scope_role`.
   Three separate questions rather than one, because they are three: a society
   may well let every coordinator see what is being deployed near them while
   keeping who asked for what, and who is being moved between branches, narrower.
   All three are read by core at enforcement time through the `role_from_setting`
   registrations in `hooks.py`; they are named here only so the patch that
   installs them and the code that documents them agree on the spelling, and
   nothing in this module resolves one, because resolving it is core's.
5. **Whether a branch transfer needs authorising** —
   `vmms_transfer_approval_mode`. The one setting here that changes behaviour
   rather than access, and the one place a society says whether moving a
   volunteer between branches is somebody's decision or simply a correction.

All five are **Custom Fields vmmsx owns** on core's National Society Settings,
installed by this app's own patches. Core's doctype is not edited: a product
pushing its fields into the shared foundation's source is how the foundation
stops being shared.

**Empty configuration means unconstrained or off, never forbidden or on.** A
society that has not named an anchor level has not thereby said deployments may
exist nowhere, and one that has not chosen a transfer mode gets the mode that
changes nothing about how the app already behaved. The deliberate exception is
the three scope roles, where empty means *closed* — that is core's fail-closed
behaviour, and it is the right direction for records naming where people are and
where they are being sent.

**Where a level rule is not reinvented.** A branch transfer's destination has to
satisfy the level rule a *volunteer's placement* satisfies, not a deployment's,
so `transfer.py` calls the Volunteer module's own
`society.assert_anchor_level()`. Two settings meaning "where a volunteer may be
placed" would be one too many, and the day they disagreed a transfer would put
somebody somewhere they could not have been registered.
"""

import frappe
from onerc_core.society.services import config

ANCHOR_LEVEL_FIELD = "vmms_deployment_anchor_level"

DEPLOYMENT_SCOPE_ROLE_FIELD = "vmms_deployment_scope_role"
REQUEST_SCOPE_ROLE_FIELD = "vmms_deployment_request_scope_role"
TRANSFER_SCOPE_ROLE_FIELD = "vmms_branch_transfer_scope_role"

TRANSFER_APPROVAL_MODE_FIELD = "vmms_transfer_approval_mode"


def deployment_anchor_level() -> str | None:
	"""The Geo Level a deployment must be anchored at, or None if unconstrained.

	Read through core's settings accessor so a site whose settings single has
	never been saved degrades to "unconstrained" instead of throwing, and read on
	every call so changing the setting takes effect without a restart.
	"""
	return config.settings().get(ANCHOR_LEVEL_FIELD) or None


def assert_deployment_anchor_level(geo_node: str) -> None:
	"""Throw unless `geo_node` sits at the level this society permits (ACC-03).

	Geo is reached only through core's adapter: this app never queries the geo
	tables and never assumes a depth. With no level configured this is a no-op,
	which is what "the society has not narrowed it" has to mean.
	"""
	from frappe import _
	from onerc_core.geo.services import adapter

	required = deployment_anchor_level()

	if not (required and geo_node):
		return

	level = adapter.get_level(geo_node)

	if level["key"] == required:
		return

	labels = {row["key"]: row["name"] for row in adapter.level_labels()}

	frappe.throw(
		_("{0} is at {1} level. This society anchors deployments at {2} level.").format(
			frappe.bold(adapter.get_full_path(geo_node)),
			frappe.bold(level["name"]),
			frappe.bold(labels.get(required, required)),
		),
		frappe.ValidationError,
		title=_("Anchor Level Not Permitted"),
	)


def transfer_approval_mode() -> str:
	"""Whether a branch transfer is routed for approval, or simply applied.

	Returns one of `approval.MODES`. **Empty configuration reads as the direct
	mode**, and that is the shipped state: a society upgrading into this module
	should not discover that every branch transfer now throws for want of an
	approval workflow it has never been asked to create.

	It is nevertheless the mode most societies will want to change. Moving a
	volunteer between branches changes who can see them and who approves for
	them, which is a decision somebody should authorise rather than a correction
	anybody may type. Choosing `routed` here and creating one
	`VMMS Approval Workflow` for `VMMS Branch Transfer` is the whole of that.
	"""
	from vmmsx.deployment.services import approval

	return config.settings().get(TRANSFER_APPROVAL_MODE_FIELD) or approval.MODE_DIRECT
