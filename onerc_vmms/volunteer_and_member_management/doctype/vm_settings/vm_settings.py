# Copyright (c) 2025, Kenya Red Cross Society and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from ...utils.utils import disable_energy_point_email_notifications


class VMSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.has_role.has_role import HasRole
		from frappe.types import DF

		allow_invoicing: DF.Check
		automate_membership_invoicing: DF.Check
		automate_membership_payment_entries: DF.Check
		billing_cycle: DF.Literal["Monthly", "Yearly"]
		billing_frequency: DF.Int
		brand_name: DF.Data | None
		company: DF.Link
		creation_user: DF.Link
		disable_energy_point_email_notifications: DF.Check
		email_template: DF.Link | None
		enable_automatic_rejection_notifications: DF.Check
		interview_roles: DF.TableMultiSelect[HasRole]
		inv_print_format: DF.Link | None
		logo: DF.AttachImage | None
		membership_debit_account: DF.Link | None
		membership_mode_of_payment: DF.Link | None
		membership_payment_account: DF.Link | None
		membership_print_format: DF.Link | None
		minimum_pass_score: DF.Percent
		notify_unshortlisted_applicants_after: DF.Int
		rejection_email_template: DF.Link | None
		send_email: DF.Check
		send_invoice: DF.Check
		send_rejection_email_immediately: DF.Check
	# end: auto-generated types

	def validate(self):
		if not self.disable_energy_point_email_notifications:
			return

		users = frappe.get_all("User", filters={"enabled": 1}, pluck="name")
		for user in users:
			disable_energy_point_email_notifications(user)
