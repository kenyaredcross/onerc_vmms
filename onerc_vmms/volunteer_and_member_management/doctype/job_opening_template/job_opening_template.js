// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Job Opening Template", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Job Application Screening Questions", {
	screening_questions_add: function (frm, cdt, cdn) {
		let row = frappe.get_doc(cdt, cdn);

		let table = frm.doc.screening_questions || [];

		let last_seq = 0;
		if (table.length > 1) {
			table.slice(0, -1).forEach((r) => {
				if (r.question_id && r.question_id.startsWith("Q")) {
					let num = parseInt(r.question_id.replace("Q", ""));
					if (!isNaN(num) && num > last_seq) last_seq = num;
				}
			});
		}

		row.question_id = "Q" + (last_seq + 1);

		frm.refresh_field("screening_questions");
	},
});
