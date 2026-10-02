frappe.ui.form.on("VMMS Service Certificate Request", {
	refresh(frm) {
		frm.disable_save();
		if (!frm.is_new()) {
			frm.add_custom_button(__("Review in portal"), () => {
				window.location.href = `/portal/admin/queue/service-certificates?request=${encodeURIComponent(frm.doc.name)}`;
			});
		}
	},
});
