# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Volunteer Application — the approval engine's third consumer.

This controller is a thin shim: every default, reconciliation and guardrail
below is one call into `vmmsx.volunteer.services.application`, an idempotent
service anyone may call directly, so this file has nothing but the calls
themselves.

**The anchor guardrail.** ACC-02 is enforced in `validate()`, the only place
that runs before the record can exist at all. An application with no Geo Node is
refused at creation rather than corrected later, because an unplaced application
is invisible to geo scoping and unroutable by approvals — it would exist with
nobody able to see or act on it. *Which* levels are permitted is ACC-03, and it
belongs to the governing `VMMS Approval Workflow`, not here: the engine checks
`allowed_anchor_levels` at submission, so a society's answer lives in one place
for every approvable doctype rather than being restated per controller.

**Re-evaluating acceptance.** `on_update` calls the service after every save,
which is how a decision recorded by the approval engine becomes a volunteer
without the engine knowing volunteers exist. The logic is in
`application.try_accept()`, an idempotent service anyone may call directly; the
hook only calls it.

What is deliberately *not* here: any approval state change, any routing, any
notion of who may decide. Those belong to `vmmsx/approvals`, and the API action
that drives them is the generic `vmmsx/api/approvals.py`. There are no desk
workflow buttons on this doctype, and there is no second door into the decision.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from vmmsx.registration.services import intake
from vmmsx.volunteer.services import application as application_service

GEO_NODE_FIELD = "geo_node"


class VMMSVolunteerApplication(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from vmmsx.vmms_approvals.doctype.vmms_approval_decision.vmms_approval_decision import VMMSApprovalDecision
		from vmmsx.vmms_volunteer.doctype.vmms_availability_selector.vmms_availability_selector import VMMSAvailabilitySelector
		from vmmsx.vmms_volunteer.doctype.vmms_language_selector.vmms_language_selector import VMMSLanguageSelector
		from vmmsx.vmms_volunteer.doctype.vmms_motivation_selector.vmms_motivation_selector import VMMSMotivationSelector
		from vmmsx.vmms_volunteer.doctype.vmms_skill_selector.vmms_skill_selector import VMMSSkillSelector

		applicant_date_of_birth: DF.Date | None
		applicant_first_name: DF.Data | None
		applicant_gender: DF.Link | None
		applicant_last_name: DF.Data | None
		applicant_phone: DF.Data | None
		applied_on: DF.Date | None
		approval_decisions: DF.Table[VMMSApprovalDecision]
		approval_stage: DF.Data | None
		approval_stage_entered_on: DF.Datetime | None
		approval_state: DF.Literal["Draft", "Submitted", "In Review", "Approved", "Rejected", "Withdrawn", "Expired"]
		availability: DF.TableMultiSelect[VMMSAvailabilitySelector]
		country_of_citizenship: DF.Link
		country_of_residence: DF.Link | None
		geo_node: DF.Link
		home_geo_node: DF.Link | None
		id_number: DF.Data | None
		id_type: DF.Link | None
		languages: DF.TableMultiSelect[VMMSLanguageSelector]
		motivation: DF.TableMultiSelect[VMMSMotivationSelector]
		naming_series: DF.Literal["VAPP-.#####"]
		prior_experience: DF.SmallText | None
		red_profile: DF.Link
		residence_address: DF.SmallText | None
		residency_type: DF.Literal["Local", "Abroad"]
		skills: DF.TableMultiSelect[VMMSSkillSelector]
		volunteer: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		"""The two-doctype write, at the only moment it can happen.

		A native Web Form writes one document; a registration needs core's
		identity spine as well. `before_insert` is after the form's values have
		landed on this record and before the framework checks that
		`red_profile` is filled in, which is the only window in which this app
		can supply it.

		It does nothing at all unless this insert is somebody registering
		themselves. A coordinator entering an application from a paper form
		supplies the Red Profile, and must never have their own attached to it.
		"""
		# Citizenship defaults to the society's own country before anything else
		# runs, so the field's reqd check — which fires later in this same
		# insert — never sees it empty on an ordinary application.
		application_service.default_country_of_citizenship(self)

		profile = intake.claim_profile(self)

		if not profile:
			return

		if not self.red_profile:
			self.red_profile = profile

		# Where somebody says they *live*, recorded on their profile if core
		# does not know yet. Never overwritten.
		#
		# Home Area, not the anchor beside it: `Red Profile.home_geo_node` is
		# core's field for where a person lives, and this form now asks that
		# question directly rather than inferring it from where they offered to
		# serve. It falls back to the anchor for an applicant living abroad, who
		# gives no home area at all, because the branch they chose is the only
		# thing this app knows about where they are.
		intake.place(profile, self.get("home_geo_node") or self.get(GEO_NODE_FIELD))

	def validate(self):
		application_service.reconcile_residency(self)
		application_service.default_serving_branch(self)
		self.validate_anchor()
		application_service.assert_applicant(self)

		# Whatever path this save came down, no identity is stored here. The
		# registration path has already emptied these; this is the guarantee
		# that does not depend on it having run.
		intake.clear_intake(self)

	def validate_anchor(self):
		"""ACC-02 — placed, at creation, in the app's own words."""
		if self.get(GEO_NODE_FIELD):
			return

		frappe.throw(
			_(
				"An application must be anchored to a Geo Node before it can exist. There are no"
				" unplaced records: an unplaced application cannot be seen by geo scoping or routed"
				" to an approver, so it would exist with nobody able to act on it."
			),
			frappe.MandatoryError,
			title=_("Missing Geo Anchor"),
		)

	def on_update(self):
		"""Put a registration into motion, then re-evaluate acceptance.

		Both are idempotent services this hook only calls.

		`submit_once` exists because a web form has no second step: every other
		way into this app inserts and then submits deliberately, and a person
		filling in a public form has nobody to press the button. It acts only on
		a document `before_insert` actually claimed, so an ordinary desk insert
		still creates a draft and waits, exactly as it always has.

		Acceptance is `application.try_accept()` — an idempotent service callable
		from anywhere — and that is what keeps the lifecycle out of a single
		framework callback.
		"""
		intake.submit_once(self, application_service.submit)
		application_service.on_update(self)
