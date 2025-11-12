// Copyright (c) 2025, Kenya Red Cross Society and contributors
// For license information, please see license.txt

frappe.listview_settings["Personnel Deployment Request"] = {
	formatters: {
		deployment_status(value) {
			if (!value) return "";

			const status_colors = {
				Pending: "orange",
				Accepted: "green",
				Rejected: "red",
				Cancelled: "gray",
			};

			const color = status_colors[value] || "darkgrey";

			return `<div class="list-row-col hidden-xs ellipsis">
				<span class="indicator-pill ${color} filterable no-indicator-dot ellipsis"
					data-filter="deployment_status,=,${value}"
					title="${frappe.utils.escape_html(value)}">
					<span class="ellipsis">${frappe.utils.escape_html(__(value))}</span>
				</span>
			</div>`;
		},
	},

	hide_name_column: false,
};
