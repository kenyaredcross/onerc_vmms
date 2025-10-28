// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Personnel Terms of Reference", {
	refresh(frm) {
		if (!frm.doc.expected_start_date) {
			frm.set_value("expected_start_date", frappe.datetime.get_today());
		}
	},

	validate(frm) {
		if (frm.doc.expected_end_date && frm.doc.expected_start_date) {
			if (frm.doc.expected_end_date < frm.doc.expected_start_date) {
				frappe.msgprint(__("Expected End Date cannot be before Expected Start Date"));
				frappe.validated = false;
			}
		}
	},
});

frappe.ui.form.on("TOR Resources", {
	quantity(frm, cdt, cdn) {
		_calculate_total_cost(frm, cdt, cdn);
	},
	cost_per_day(frm, cdt, cdn) {
		_calculate_total_cost(frm, cdt, cdn);
	},
});

function _calculate_total_cost(frm, cdt, cdn) {
	const row = locals[cdt][cdn] || {};
	const qty = parseFloat(row.quantity) || 0;
	const cost = parseFloat(row.cost_per_day) || 0;
	const total = qty * cost;
	frappe.model.set_value(cdt, cdn, "total_cost", total);
	frm.refresh_field("resources");
}
