frappe.ui.form.on("Attendance", {
	refresh(frm) {
		copy_from_pdr(frm);
	},
	personnel_deployment_request(frm) {
		copy_from_pdr(frm);
	},
});

async function copy_from_pdr(frm) {
	if (!frm.doc.personnel_deployment_request) return;
	const pdr = await frappe.db.get_doc(
		"Personnel Deployment Request",
		frm.doc.personnel_deployment_request
	);
	if (!pdr) return;
	copy_matching_fields(pdr, frm);
}

function copy_matching_fields(source_doc, frm) {
	const target_fields = frm.fields_dict;
	for (let field in source_doc) {
		if (target_fields[field] && frm.doc[field] !== source_doc[field]) {
			frm.set_value(field, source_doc[field]);
		}
	}
}
