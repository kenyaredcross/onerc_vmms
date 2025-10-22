// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Interview", {
	refresh(frm) {
		frappe.call({
			method: "onerc_vmms.volunteer_and_member_management.utils.get_interviewers",
			callback: function (r) {
				if (r.message) {
					frm.allowed_interviewers = r.message;

					frm.fields_dict["interview_details"].grid.get_field("interviewer").get_query =
						function () {
							return {
								filters: {
									name: ["in", frm.allowed_interviewers],
								},
							};
						};
				}
			},
		});
	},
});
