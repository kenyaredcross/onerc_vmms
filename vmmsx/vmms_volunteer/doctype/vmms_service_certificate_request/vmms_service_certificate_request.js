frappe.ui.form.on("VMMS Service Certificate Request", {
	refresh(frm) {
		frm.disable_save();
		frm.fields_dict.request_help.$wrapper.html(
			`<div class="alert alert-info">${__("Members and volunteers submit requests from their portal profile. This form displays the submitted request and its review history.")} <a href="/portal/profile">${__("Open profile")}</a> · <a href="/portal/admin/queue/service-certificates">${__("Review requests")}</a></div>`
		);
		// Frappe hides empty read-only values by default. Keep the public request
		// fields visible here so a new or pending record still explains the form.
		for (const name of ["red_profile", "applicant_name", "geo_node", "request_date", "service_from", "service_to", "position", "service_summary", "review_note", "issued_on", "issued_by"]) {
			const control = frm.fields_dict[name];
			if (control && control.disp_status === "None" && !control.df.hidden) {
				control.disp_status = "Read";
				control.$wrapper.removeClass("hide-control");
				control.refresh_input();
			}
		}
		if (frappe.user_roles.includes("System Manager")) {
			frm.add_custom_button(__("Certificate settings"), () => frappe.set_route("Form", "VMMS Service Certificate Settings"));
		}
		if (!frm.is_new()) {
			frm.add_custom_button(__("Review in portal"), () => {
				window.location.href = `/portal/admin/queue/service-certificates?request=${encodeURIComponent(frm.doc.name)}`;
			});
			if (frm.doc.certificate_file) {
				frm.add_custom_button(__("Download certificate"), () => {
					window.open(`/api/method/vmmsx.api.service_certificate.download?name=${encodeURIComponent(frm.doc.name)}`);
				});
			}
		}
	},
});
