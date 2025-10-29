// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Project", {
	refresh: function (frm) {
		frm.set_query("terms_of_reference", function () {
			return {
				filters: [
					["expected_end_date", ">=", frappe.datetime.get_today()],
					["docstatus", "=", 1],
				],
			};
		});

		if (frm.doc.terms_of_reference) {
			apply_company_filters_from_tor(frm, frm.doc.terms_of_reference);
		}
	},

	terms_of_reference: function (frm) {
		apply_company_filters_from_tor(frm, frm.doc.terms_of_reference);
	},
});

function apply_company_filters_from_tor(frm, tor_name) {
	frappe.db.get_value("Personnel Terms of Reference", tor_name, ["company"]).then((r) => {
		if (!(r && r.message && r.message.company)) return;

		const torCompany = r.message.company;

		frappe.call({
			method: "onerc_vmms.volunteer_and_member_management.utils.get_company_descendants",
			args: { company: torCompany },
			callback: function (resp) {
				const allowedCompanies =
					resp && resp.message && resp.message.length
						? resp.message
						: torCompany
						? [torCompany]
						: [];

				frm.set_query("company", function () {
					if (allowedCompanies && allowedCompanies.length) {
						return { filters: [["name", "in", allowedCompanies]] };
					}
					return {};
				});

				if (frm.doc.company && !allowedCompanies.includes(frm.doc.company)) {
					frm.set_value("company", null);
				}

				frm.refresh_field("company");
			},
		});
	});
}
