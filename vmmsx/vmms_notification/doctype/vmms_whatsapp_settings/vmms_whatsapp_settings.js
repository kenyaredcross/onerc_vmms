// Copyright (c) 2026, Nigel and contributors
// For license information, please see license.txt

// Whether the gateway is actually linked is the one thing this form cannot show
// from its own fields, and it is the thing somebody filling it in most wants to
// know. Asked on a button rather than on load: it is a call to another
// container, and a settings form that hangs because a container is down is a
// settings form nobody can use to fix it.
frappe.ui.form.on("VMMS WhatsApp Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Check Connection"), () => {
			frappe.call({
				method: "vmmsx.api.whatsapp.connection",
				freeze: true,
				freeze_message: __("Asking the gateway…"),
				callback: ({ message }) => {
					if (!message) return;

					if (message.connected) {
						frappe.show_alert({ message: __("Connected."), indicator: "green" });
						return;
					}

					frappe.msgprint({
						title: __("Not Connected"),
						indicator: "orange",
						// The gateway's own status word alongside the sentence, because
						// the word is what its documentation and its dashboard both use
						// and somebody about to search for it needs the word.
						message: message.status
							? `${message.reason}<br><br>${__("Gateway status")}: <b>${message.status}</b>`
							: message.reason,
					});
				},
			});
		});
	},
});
