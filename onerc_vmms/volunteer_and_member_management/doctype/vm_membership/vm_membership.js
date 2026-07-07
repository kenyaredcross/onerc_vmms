// Copyright (c) 2025, Kenya Red Cross Society and contributors
// For license information, please see license.txt

frappe.ui.form.on("VM Membership", {
	refresh: function (frm) {
		if (frm.doc.__islocal) return;

		if (!frm.is_new()) {
			if (frm.doc.status !== "Pending" && frm.doc.status !== "Active") {
				frm.add_custom_button("Request Payment", () => {
					frappe.prompt(
						[
							{
								fieldname: "phone_number",
								label: __("Phone Number"),
								fieldtype: "Data",
								reqd: 1,
								description: __("Enter the phone number for payment request"),
							},
						],
						(values) => {
							frm.call({
								doc: frm.doc,
								method: "initiate_payment",
								args: { phone_number: values.phone_number },
								freeze: true,
								freeze_message: __("Requesting Payment"),
								callback: function (r) {
									if (r.invoice) frm.reload_doc();
								},
							});
						},
						__("Enter Phone Number"),
						__("Request Payment")
					);
				});
			}
		}

		if (frm.doc.status !== "Pending" && frm.doc.status !== "Active") {
			!frm.doc.invoice &&
				frm.add_custom_button("Generate Invoice", () => {
					frm.call({
						doc: frm.doc,
						method: "generate_invoice",
						args: { save: true },
						freeze: true,
						freeze_message: __("Creating Membership Invoice"),
						callback: function (r) {
							if (r.invoice) frm.reload_doc();
						},
					});
				});
		}

		if (frm.doc.status === "Pending") {
			frm.add_custom_button("Approve Membership", () => {
				frm.call({
					doc: frm.doc,
					method: "approve_membership",
					freeze: true,
					freeze_message: __("Approving Membership"),
					callback: function (r) {
						frappe.msgprint(__("Membership Approved"));
						frm.reload_doc();
					},
				});
			});
		}
	},

	validate: (frm) => {
		validateMembership(frm);
	},

	membership_type: function (frm) {
		if (frm.doc.membership_type) {
			frappe.db.get_value(
				"VM Membership Type",
				frm.doc.membership_type,
				["amount", "currency", "billing_cycle"],
				(r) => {
					if (r) {
						r.billing_cycle === "One Off"
							? (frm.set_df_property("to_date", "reqd", 0),
							  frm.set_df_property("to_date", "hidden", 1))
							: (frm.set_df_property("to_date", "reqd", 1),
							  frm.set_df_property("to_date", "hidden", 0));

						frm.set_value("amount", r.amount);
						frm.set_value("currency", r.currency);
					}
				}
			);
		}
	},

	onload: function (frm) {
		frm.add_fetch("membership_type", "amount", "amount");
	},
});

function validateMembership(frm) {
	if (frm.doc.status === "Active" && !frm.doc.qr_code) {
		let messgae = "An Active Membership requires Approval. Please Approve it first";
		frappe.throw(__(messgae));
	}
}
