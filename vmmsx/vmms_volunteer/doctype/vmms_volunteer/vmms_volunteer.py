# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Volunteer — the person's volunteering identity, and nothing about them.

This record holds a link to a Red Profile, where it sits in the geo tree, what it
can currently do, and its own derived state. It holds no name, no email and no
phone, and it must not acquire them — not even as a `fetch_from`, which is a
stored copy wearing a different hat. Core owns identity, and a second copy of a
person is a second answer to who they are. Read those through
`vmmsx.volunteer.services.identity`, which reads Red Profile every time.

**What it does hold, and why that is not the same concession.** Skills,
languages, availability and placement are *volunteer-owned attributes*: facts
about somebody's volunteering that change while they volunteer. They are seeded
from the accepted application by
`volunteer/services/capabilities.py` and are the current truth from then on, so
a volunteer who learns to drive is recorded as being able to drive without
anybody rewriting the application they sent in years ago. Identity is the
opposite case: citizenship, residence and identification are person facts in
core, have exactly one home, and this record borrows them on every read. The
dividing line is ownership, not convenience.

The record is a **satellite** in core's Design 2 sense: its existence and status
are the truth of somebody's volunteering, and the row on their Red Profile's
affiliation index is a summary written from here through `set_affiliation()`.
Nothing anywhere reads that row back to decide anything.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from vmmsx.volunteer.services import society

GEO_NODE_FIELD = "home_geo_node"


class VMMSVolunteer(Document):
	def validate(self):
		self.validate_profile()
		self.validate_anchor()

	def validate_profile(self):
		if not self.red_profile:
			frappe.throw(
				_("A volunteer is always a person core already knows. Link a Red Profile."),
				frappe.MandatoryError,
				title=_("No Red Profile"),
			)

	def validate_anchor(self):
		"""ACC-02 and ACC-03 — placed, and placed where this society allows.

		The mandatory flag on the field already refuses an empty anchor at the
		framework level; this repeats the refusal in the app's own words so the
		rule is enforced by something that states it, not only by a JSON
		attribute somebody could clear.
		"""
		if not self.get(GEO_NODE_FIELD):
			frappe.throw(
				_(
					"A volunteer must be anchored to a Geo Node before they can exist. There are no"
					" unplaced records: an unplaced volunteer cannot be seen by geo scoping, because"
					" core's list filter is an IN and that excludes NULL."
				),
				frappe.MandatoryError,
				title=_("Missing Geo Anchor"),
			)

		# Which level is permitted is society configuration, read from settings
		# on every save. No level name appears in this file.
		society.assert_anchor_level(self.get(GEO_NODE_FIELD))

	def on_trash(self):
		"""Tell core the satellite is going, so it can drop the derived row.

		`rebuild_affiliations` rather than a removal call: core has exactly one
		removal path, driven by what the registered providers claim, and this app
		deleting a row directly would be a second one. It is also what makes the
		removal *isolated* — the member provider on the same profile is called by
		the same rebuild, still claims its row, and that row survives untouched.

		**Timing is the whole difficulty here, and it is why this must be
		`on_trash` and not `after_delete`.** Frappe deletes in this order:

		    on_trash  →  check_if_doc_is_linked  →  (row deleted)  →  after_delete

		The affiliation row holds a Dynamic Link to this volunteer, so if the row
		still exists when the link check runs, the delete is refused with
		`LinkExistsError` — and `after_delete` never happens. The row therefore
		has to go during `on_trash`, before that check.

		But at `on_trash` this volunteer is still in the database, so the provider
		would look it up, still claim it, and core would rightly keep the row.
		`_being_trashed` is how the provider is told to stop speaking for a
		volunteer that is on its way out. It is a request-scoped mark, cleared in
		a `finally`, and it is the only thing standing between "delete a
		volunteer" and a deadlock between the link check and the index.
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
	"""Volunteers currently inside their own `on_trash`, for this request only.

	Read by `vmmsx.volunteer.affiliations.provide`. A flag rather than an
	argument because core calls the provider, not this app — there is nowhere to
	pass it.
	"""
	if not hasattr(frappe.local, "vmms_volunteers_being_trashed"):
		frappe.local.vmms_volunteers_being_trashed = set()

	return frappe.local.vmms_volunteers_being_trashed
