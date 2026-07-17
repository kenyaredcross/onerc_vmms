frappe.ui.form.on("Interview Round", {
	refresh(frm) {
		frappe.call({
			method: "onerc_vmms.volunteer_and_member_management.utils.utils.get_interviewers",
			callback: function (r) {
				if (r.message) {
					frm.allowed_interviewers = r.message;
					frm.set_query("interviewers", function () {
						return {
							filters: {
								name: ["in", frm.allowed_interviewers],
							},
						};
					});
				}
			},
		});
	},
});
