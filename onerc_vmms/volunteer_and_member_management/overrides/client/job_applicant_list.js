frappe.listview_settings["Job Applicant"] = {
	add_fields: ["status", "docstatus"],

	onload(listview) {
		listview.filter_area.add([[listview.doctype, "docstatus", "=", 1]]);
	},

	has_indicator_for_draft: true,

	get_indicator(doc) {
		const status_colors = {
			Open: "blue",
			Replied: "orange",
			Rejected: "red",
			Hold: "yellow",
			Accepted: "green",
		};

		if (doc.status) {
			return [doc.status, status_colors[doc.status] || "gray", `status,=,${doc.status}`];
		}
	},
};
