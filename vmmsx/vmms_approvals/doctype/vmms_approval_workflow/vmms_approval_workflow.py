# Copyright (c) 2026, Nigel and contributors
# For license information, please see license.txt

"""VMMS Approval Workflow — one per approvable doctype, and the guardrails.

Everything a national society may decide differently about an approval lives on
this record: the stages, the roles they need, how many approvers must act, how
long they have, which levels of the hierarchy an application may be anchored
at. Nothing a society may decide lives in a source file.

The validations below are the guardrails, and they are here rather than in the
engine on purpose: a workflow that cannot work should be impossible to *save*,
not merely impossible to run. An administrator finds out while looking at the
form, not months later when the first application will not move.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint

from vmmsx.approvals.services import contract, routing, sla

WORKFLOW_NAMING_SERIES = "AWF-.#####"

GEO_NODE_DOCTYPE = "Geo Node"


class VMMSApprovalWorkflow(Document):
	def autoname(self):
		# Opaque. `workflow_for` is the obvious candidate for a docname and is
		# exactly why it must not be one: a governed doctype can be renamed, and
		# mutable data never goes in a primary key.
		self.name = make_autoname(WORKFLOW_NAMING_SERIES)

	def validate(self):
		self.validate_governed_doctype()
		self.validate_anchor_field()
		self.validate_anchor_levels()
		self.validate_stages()
		self.validate_someone_can_reject()

	def validate_governed_doctype(self):
		"""The doctype must exist as a real, approvable document."""
		meta = frappe.get_meta(self.workflow_for)

		if meta.istable or meta.issingle:
			frappe.throw(
				_("{0} is a {1} and cannot carry an approval.").format(
					frappe.bold(self.workflow_for), _("child table") if meta.istable else _("single doctype")
				),
				title=_("Not an Approvable Doctype"),
			)

		contract.assert_approvable(self.workflow_for)

	def validate_anchor_field(self):
		"""ACC-02 — the anchor is a Link to Geo Node, and it is mandatory.

		Checked here because this is the only place that knows both the field
		name and the doctype. A workflow naming a field that is free text, or a
		field that may be left empty, would produce unplaced records: invisible
		to geo scoping and unroutable by approvals.
		"""
		field = frappe.get_meta(self.workflow_for).get_field(self.geo_node_field)

		if not field:
			frappe.throw(
				_("{0} has no field {1} to anchor on.").format(
					frappe.bold(self.workflow_for), frappe.bold(self.geo_node_field)
				),
				frappe.MandatoryError,
				title=_("Missing Geo Anchor Field"),
			)

		if field.fieldtype != "Link" or field.options != GEO_NODE_DOCTYPE:
			frappe.throw(
				_("{0}.{1} must be a Link to {2}, not {3}. An anchor is never free text.").format(
					frappe.bold(self.workflow_for),
					frappe.bold(self.geo_node_field),
					frappe.bold(GEO_NODE_DOCTYPE),
					frappe.bold(field.fieldtype),
				),
				title=_("Bad Geo Anchor Field"),
			)

		if not field.reqd:
			frappe.throw(
				_(
					"{0}.{1} must be mandatory. Every operational record is anchored to a Geo Node"
					" at creation — there are no unplaced records."
				).format(frappe.bold(self.workflow_for), frappe.bold(self.geo_node_field)),
				title=_("Anchor Not Mandatory"),
			)

	def validate_anchor_levels(self):
		"""ACC-03 — the permitted levels, listed once each."""
		seen = set()

		for row in self.allowed_anchor_levels or []:
			if row.geo_level in seen:
				frappe.throw(
					_("{0} is listed twice as an allowed anchor level.").format(frappe.bold(row.geo_level)),
					title=_("Duplicate Anchor Level"),
				)

			seen.add(row.geo_level)

	def validate_stages(self):
		if not self.stages:
			frappe.throw(
				_("A workflow needs at least one stage."), frappe.MandatoryError, title=_("No Stages")
			)

		sequences = set()

		for stage in self.stages:
			self.validate_sequence(stage, sequences)
			self.validate_routing(stage)
			self.validate_completion(stage)
			self.validate_clock(stage)

	def validate_sequence(self, stage, sequences: set):
		"""Order must be unambiguous. Gaps are fine; ties are not."""
		if cint(stage.sequence) < 1:
			frappe.throw(
				_("Stage {0} needs a sequence of 1 or more.").format(frappe.bold(stage.stage_label)),
				title=_("Invalid Stage Sequence"),
			)

		if stage.sequence in sequences:
			frappe.throw(
				_(
					"Two stages share sequence {0}. Order would depend on row order, which nothing may rely on."
				).format(frappe.bold(stage.sequence)),
				title=_("Duplicate Stage Sequence"),
			)

		sequences.add(stage.sequence)

	def validate_routing(self, stage):
		"""A rule, and whatever that rule needs to resolve anybody."""
		if stage.resolution_rule not in routing.RULES:
			frappe.throw(
				_("Stage {0}: {1} is not a resolution rule. Expected one of: {2}.").format(
					frappe.bold(stage.stage_label),
					frappe.bold(stage.resolution_rule),
					", ".join(routing.RULES),
				),
				title=_("Unknown Resolution Rule"),
			)

		if stage.resolution_rule == routing.RULE_AT_LEVEL and not stage.geo_level:
			frappe.throw(
				_("Stage {0} resolves at a level, so it needs a Geo Level.").format(
					frappe.bold(stage.stage_label)
				),
				frappe.MandatoryError,
				title=_("Missing Geo Level"),
			)

		if stage.resolution_rule == routing.RULE_FIXED_NODE and not stage.fixed_geo_node:
			frappe.throw(
				_("Stage {0} resolves at a fixed node, so it needs one.").format(
					frappe.bold(stage.stage_label)
				),
				frappe.MandatoryError,
				title=_("Missing Fixed Geo Node"),
			)

	def validate_completion(self, stage):
		if stage.completion_rule in routing.COMPLETION_RULES:
			return

		frappe.throw(
			_("Stage {0}: {1} is not a completion rule. Expected one of: {2}.").format(
				frappe.bold(stage.stage_label),
				frappe.bold(stage.completion_rule),
				", ".join(routing.COMPLETION_RULES),
			),
			title=_("Unknown Completion Rule"),
		)

	def validate_clock(self, stage):
		"""Every stage has an SLA, and every stage says what a breach does.

		The `all_of` rule gets one extra check. A stage that requires *every*
		resolved approver, is not optional, and does nothing on breach is a
		stage that can stop an application forever with nobody noticing — the
		exact failure this system is built to make impossible. Make it optional
		(skipped when nobody resolves) or give it an escalation.
		"""
		if cint(stage.sla_days) < 1:
			frappe.throw(
				_(
					"Stage {0} needs an SLA of at least one day. A stage with no clock is a queue nobody is watching."
				).format(frappe.bold(stage.stage_label)),
				title=_("Missing SLA"),
			)

		if stage.on_sla_breach not in sla.BREACH_ACTIONS:
			frappe.throw(
				_("Stage {0}: {1} is not a breach action. Expected one of: {2}.").format(
					frappe.bold(stage.stage_label),
					frappe.bold(stage.on_sla_breach),
					", ".join(sla.BREACH_ACTIONS),
				),
				title=_("Unknown Breach Action"),
			)

		requires_everyone = stage.completion_rule == routing.COMPLETION_ALL_OF

		if requires_everyone and not stage.is_optional and stage.on_sla_breach == sla.BREACH_NONE:
			frappe.throw(
				_(
					"Stage {0} needs every approver, is not optional, and does nothing when its SLA"
					" is breached — an application that reaches it can stall with nobody informed."
					" Make it optional or give it an escalation."
				).format(frappe.bold(stage.stage_label)),
				title=_("Stage Can Stall Silently"),
			)

	def validate_someone_can_reject(self):
		"""At least one stage must be able to say no.

		A workflow where every stage may only endorse is a workflow whose
		applications can only ever be approved — a rubber stamp with an audit
		trail, which is worse than no workflow at all because it looks like one.
		"""
		if any(stage.can_reject for stage in self.stages):
			return

		frappe.throw(
			_(
				"No stage of this workflow can reject, so an application could only ever be"
				" approved. At least one stage must be able to terminate it."
			),
			title=_("Nothing Can Reject"),
		)
