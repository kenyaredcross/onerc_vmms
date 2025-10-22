// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Project", {
	refresh: function (frm) {
		frappe.call({
			method: "onerc_vmms.volunteer_and_member_management.utils.get_expense_and_advance_approvers",
			callback: function (r) {
				if (r.message) {
					frm.allowed_approvers = r.message;

					frm.set_query("expense_approver", function () {
						return {
							filters: {
								name: ["in", frm.allowed_approvers],
							},
						};
					});

					frm.set_query("advance_approver", function () {
						return {
							filters: {
								name: ["in", frm.allowed_approvers],
							},
						};
					});
				}
			},
		});
	},
});
