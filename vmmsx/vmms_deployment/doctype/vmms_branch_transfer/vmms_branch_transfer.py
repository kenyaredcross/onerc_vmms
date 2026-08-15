# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Branch Transfer — a volunteer's placement moves, and nothing else does.

The whole record exists to change one field on one other record:
`VMMS Volunteer.home_geo_node`. Everything about the design follows from being
clear about what it must *not* change.

**History is not rewritten.** A volunteer who was deployed at their old branch
was deployed at their old branch. Their past deployments, their time logs and
their certifications keep the geo anchors they were saved with, and this module
never writes one of them. The consequence is the intended one and it falls out
of core's scope model rather than needing code: the old branch keeps seeing the
records anchored beneath it, because scope is a question about a record's own
anchor; the new branch sees the volunteer, because the volunteer's anchor is
what moved. See `deployment/services/transfer.py`, where the single write is.

**`from_geo_node` is snapshotted, not typed.** It is filled from the volunteer
at `before_insert` and is read-only thereafter, so a transfer says where
somebody actually came from rather than where whoever raised it believed they
were. It is also the ACC-02 anchor for scoping and for routing.

**Applying is a predicate, not a sequence.** `transfer.try_apply()` asks whether
approval is settled, whether the effective date has arrived, and whether it has
been applied already. All three are answered from the record and from
configuration, so it is safe to call after any event and in any order, and the
daily sweep that catches a future-dated transfer is the same function.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from vmmsx.deployment.services import transfer as transfer_service


class VMMSBranchTransfer(Document):
	def before_insert(self):
		"""Snapshot where the volunteer is now, before anybody can disagree about it."""
		transfer_service.snapshot_origin(self)

	def validate(self):
		self.validate_status()
		transfer_service.validate(self)

	def validate_status(self):
		"""An empty status reads as Pending, never as nothing.

		The field is read-only, so the desk never sends one, and a document built
		in code may not have set it. Defaulting here rather than relying on the
		JSON default means the invariant holds however the document was made.
		"""
		if not self.transfer_status:
			self.transfer_status = transfer_service.STATUS_PENDING

	def on_update(self):
		"""Re-evaluate whether the placement should move now. Idempotent."""
		transfer_service.try_apply(self)

	def on_trash(self):
		"""A transfer that moved somebody is not deletable.

		Deleting it would leave the volunteer at the new branch with no record of
		how they got there, which is exactly the history this module exists not to
		rewrite. A transfer that never took effect is ordinary to delete.
		"""
		if not self.applied_on:
			return

		frappe.throw(
			_(
				"This transfer has already moved {0} to {1}. It cannot be deleted, because deleting"
				" it would leave the volunteer where it put them with nothing recording why. Cancel"
				" a transfer that has not taken effect; raise another to move somebody back."
			).format(frappe.bold(self.volunteer), frappe.bold(self.to_geo_node)),
			frappe.PermissionError,
			title=_("Transfer Already Effective"),
		)
