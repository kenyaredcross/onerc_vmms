frappe.listview_settings["VM Membership"] = {
	onload: (listview) => {
		if (frappe.user_roles.includes("System Manager")) {
			addScanButton(listview);
		}

		listview.filter_area.add([[listview.doctype, "status", "!=", "Draft"]]);
	},
};

function addScanButton(listview) {
	const action = () => {
		const scanner = new frappe.ui.Scanner({
			dialog: true,
			multiple: false,
			on_scan: async (data) => {
				const { decodedText } = data;

				const response = await frappe.call({
					method: "onerc_vmms.volunteer_and_member_management.doctype.vm_membership.vm_membership.process_qr_scan",
					args: { scanned_data: decodedText },
				});

				if (response && response.message) {
					const d = response.message;

					const indicatorMap = {
						Active: "green",
						Pending: "orange",
						Expired: "red",
						Rejected: "red",
						Draft: "gray",
					};
					const color = indicatorMap[d.status] || "gray";
					const statusPill = `<span class="indicator-pill ${color}">${d.status}</span>`;

					frappe.msgprint({
						title: __("Membership Details"),
						message: `
							<table class="table table-bordered" style="margin-top:8px">
								<tr><td><b>${__("Membership")}</b></td><td>${d.membership_desk_link}</td></tr>
								<tr><td><b>${__("Member")}</b></td><td>${d.member_desk_link}</td></tr>
								<tr><td><b>${__("Membership Type")}</b></td><td>${d.membership_type}</td></tr>
								<tr><td><b>${__("Status")}</b></td><td>${statusPill}</td></tr>
							</table>`,
					});
				}
			},
		});

		scanner.stop_scan();
	};
	listview.page.add_inner_button("Scan QR", action);
}
