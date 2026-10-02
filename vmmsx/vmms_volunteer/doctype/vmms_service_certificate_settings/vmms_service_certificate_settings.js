frappe.ui.form.on("VMMS Service Certificate Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Preview certificate"), async () => {
			const { message } = await frappe.call({
				method: "vmmsx.api.service_certificate.preview",
				args: { configuration: frm.doc },
			});
			const frame = document.createElement("iframe");
			frame.title = __("Certificate preview");
			frame.setAttribute("sandbox", "");
			frame.style.cssText = "width:100%;height:720px;border:1px solid #ddd";
			frame.srcdoc = message.html;
			frm.fields_dict.preview.$wrapper.empty().append(frame);
			frm.scroll_to_field("preview");
		});
	},
});
