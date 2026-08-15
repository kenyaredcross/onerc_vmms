# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Member — the person's membership identity, and nothing about the person.

This record holds a link to a Red Profile and its own derived state. It holds no
name, no email and no phone, and it must not acquire them: core owns identity,
and a second copy of a person is a second answer to who they are. Read those
through `vmmsx.member.services.identity`, which reads Red Profile every time.

The record is a **satellite** in core's Design 2 sense: its existence and status
are the truth of somebody's membership, and the row on their Red Profile's
affiliation index is a summary written from here through `set_affiliation()`.
Nothing anywhere reads that row back to decide anything.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class VMMSMember(Document):
	def validate(self):
		self.validate_profile()

	def validate_profile(self):
		if not self.red_profile:
			frappe.throw(
				_("A member is always a person core already knows. Link a Red Profile."),
				frappe.MandatoryError,
				title=_("No Red Profile"),
			)

	def on_trash(self):
		"""Tell core the satellite is going, so it can drop the derived row.

		`rebuild_affiliations` rather than a removal call: core has exactly one
		removal path, driven by what the registered providers claim, and this app
		deleting a row directly would be a second one.

		**Timing is the whole difficulty here, and it is why this must be
		`on_trash` and not `after_delete`.** Frappe deletes in this order:

		    on_trash  →  check_if_doc_is_linked  →  (row deleted)  →  after_delete

		The affiliation row holds a Dynamic Link to this member, so if the row
		still exists when the link check runs, the delete is refused with
		`LinkExistsError` — and `after_delete` never happens. The row therefore
		has to go during `on_trash`, before that check.

		But at `on_trash` this member is still in the database, so the provider
		would look it up, still claim it, and core would rightly keep the row.
		`_being_trashed` is how the provider is told to stop speaking for a
		member that is on its way out. It is a request-scoped mark, cleared in a
		`finally`, and it is the only thing standing between "delete a member"
		and a deadlock between the link check and the index.
		"""
		from onerc_core.identity.services.affiliation import rebuild_affiliations

		profile = self.red_profile

		if not (profile and frappe.db.exists("Red Profile", profile)):
			return

		_being_trashed().add(self.name)

		try:
			rebuild_affiliations(profile)
		finally:
			_being_trashed().discard(self.name)


def _being_trashed() -> set[str]:
	"""Members currently inside their own `on_trash`, for this request only.

	Read by `vmmsx.member.affiliations.provide`. A flag rather than an argument
	because core calls the provider, not this app — there is nowhere to pass it.
	"""
	if not hasattr(frappe.local, "vmms_members_being_trashed"):
		frappe.local.vmms_members_being_trashed = set()

	return frappe.local.vmms_members_being_trashed
