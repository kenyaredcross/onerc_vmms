// Copyright (c) 2025, Kenya Red Cross Society and contributors
// For license information, please see license.txt

frappe.ui.form.on("VM Membership Type", {
	refresh(frm) {},

	validate(frm) {
		if (frm.doc.age_requirement) {
			if (frm.doc.lower_age_limit >= frm.doc.upper_age_limit) {
				frappe.throw(__("Lower Age Limit must be less than Upper Age Limit"));
			}
		}
	},
});
