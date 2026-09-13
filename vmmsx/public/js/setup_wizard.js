frappe.provide("vmmsx.setup");

frappe.setup.on("before_load", function () {
	// Keep these slides in the overall wizard until the *site* is complete.
	// Frappe marks each app complete as soon as its server task succeeds; if a
	// later app then fails, hiding our slides on refresh makes the combined
	// wizard appear to have lost part of its setup. The setup page itself already
	// redirects away once the whole site is complete, so no app-level guard is
	// needed here.
	frappe.setup.add_slide({
		name: "vmms-national-society",
		title: __("Tell us about your National Society"),
		help: __("This identity is used throughout VMMS, including the portal, messages and certificates."),
		fields: [
			{
				fieldname: "vmms_organization_name",
				label: __("Organization Name"),
				fieldtype: "Data",
				placeholder: __("Tanzania Red Cross Society"),
				reqd: 1,
			},
			{
				fieldname: "vmms_organization_short_name",
				label: __("Short Name"),
				fieldtype: "Data",
				placeholder: __("TRCS"),
				reqd: 1,
			},
			{
				fieldname: "vmms_logo",
				label: __("Logo"),
				fieldtype: "Attach Image",
				make_attachment_public: 1,
				// Setup-wizard controls have no frm, so ControlAttach only forwards
				// uploader defaults supplied through `options`. A society logo must be
				// public because it is rendered before login on the portal and emails.
				options: { make_attachments_public: 1, allow_toggle_private: false },
				description: __("Shown in the portal, emails and membership certificates."),
				reqd: 1,
			},
		],
		onload: function (slide) {
			slide.get_input("vmms_organization_name").on("input", function () {
				const initials = $(this)
					.val()
					.trim()
					.split(/\s+/)
					.filter(Boolean)
					.map((word) => word.charAt(0))
					.join("")
					.toUpperCase();
				slide.get_field("vmms_organization_short_name").set_value(initials);
			});
		},
	});

	frappe.setup.add_slide({
		name: "vmms-geography",
		title: __("Where does your Society operate?"),
		help: __("Build the hierarchy from the national level down. Add as many levels as your Society uses. You can edit these levels and add the actual places under each one later in VMMS Setup."),
		fields: [
			{ fieldname: "vmms_geo_hierarchy_editor", fieldtype: "HTML" },
			{ fieldname: "vmms_geo_levels_json", fieldtype: "Data" },
			{ fieldname: "vmms_application_anchor_order", fieldtype: "Data" },
		],
		onload: function (slide) {
			vmmsx.setup.make_geo_editor(slide);
		},
		validate: function () {
			return this.geo_editor?.validate() ?? false;
		},
	});
});

frappe.setup.welcome_page = "/desk/vmms-setup";

vmmsx.setup.make_geo_editor = function (slide) {
	const editor = slide.get_field("vmms_geo_hierarchy_editor").$wrapper;
	// Keep these as ordinary writable controls so FieldGroup includes them when
	// it collects a completed slide. A df marked `hidden` is presentation *and*
	// form state in Frappe, so values written into one can disappear when the
	// wizard later merges all app slides.
	slide.get_field("vmms_geo_levels_json").$wrapper.hide();
	slide.get_field("vmms_application_anchor_order").$wrapper.hide();
	let levels = [{ label: "National" }];
	let anchor = "1";

	const sync = () => {
		const json = JSON.stringify(levels);
		slide.get_field("vmms_geo_levels_json").set_value(json);
		slide.get_field("vmms_application_anchor_order").set_value(anchor);
		frappe.wizard.values.vmms_geo_levels_json = json;
		frappe.wizard.values.vmms_application_anchor_order = anchor;
		// `Slide.set_values()` replaces slide.values just before validation. Keep
		// this custom editor's values on the slide itself as well as on the two
		// controls, so later ERPNext slides cannot lose them during aggregation.
		slide.values = Object.assign(slide.values || {}, {
			vmms_geo_levels_json: json,
			vmms_application_anchor_order: anchor,
		});
	};

	const update_anchor_choices = () => {
		const select = editor.find(".vmms-anchor-select");
		const available = levels
			.map((row, index) => ({ index: String(index + 1), label: row.label.trim() }))
			.filter((row) => row.label);

		if (!available.some((row) => row.index === anchor)) {
			anchor = available.length ? available[available.length - 1].index : "";
		}
		select.empty();
		available.forEach((row) => select.append($("<option>").val(row.index).text(row.label)));
		select.val(anchor);
		sync();
	};

	const render = () => {
		editor.empty();
		const list = $("<div>").addClass("vmms-geo-levels").appendTo(editor);
		levels.forEach((row, index) => {
			const group = $("<div>").addClass("form-group").appendTo(list);
			$("<label>")
				.text(index === 0 ? __("Top level") : __("Level {0}", [index + 1]))
				.append(index === 0 ? $("<span>").addClass("text-danger").text(" *") : "")
				.appendTo(group);
			const line = $("<div>").addClass("d-flex gap-2").appendTo(group);
			$("<input>", { type: "text", value: row.label, placeholder: index === 0 ? __("National") : __("e.g. Region, County, Branch") })
				.addClass("form-control")
				.on("input", function () {
					levels[index].label = this.value;
					update_anchor_choices();
				})
				.appendTo(line);
			if (index > 0) {
				$("<button>", { type: "button", title: __("Remove level") })
					.addClass("btn btn-default btn-sm")
					.text(__("Remove"))
					.on("click", () => {
						levels.splice(index, 1);
						render();
					})
					.appendTo(line);
			}
		});

		$("<button>", { type: "button" })
			.addClass("btn btn-default btn-sm mb-4")
			.text(__("Add another level"))
			.on("click", () => {
				levels.push({ label: "" });
				render();
				editor.find(".vmms-geo-levels input").last().trigger("focus");
			})
			.appendTo(editor);

		const anchor_group = $("<div>").addClass("form-group").appendTo(editor);
		$("<label>")
			.text(__("Applications are made at"))
			.append($("<span>").addClass("text-danger").text(" *"))
			.appendTo(anchor_group);
		$("<select>")
			.addClass("form-control vmms-anchor-select")
			.on("change", function () {
				anchor = this.value;
				sync();
			})
			.appendTo(anchor_group);
		$("<p>")
			.addClass("help-box small text-muted mt-2")
			.text(__("Choose the level where volunteer and membership applications are registered, even if lower levels exist."))
			.appendTo(anchor_group);
		$("<div>")
			.addClass("alert alert-info mt-4")
			.text(__("This step creates the level structure only. After setup, open VMMS Setup → Geo Node to add your regions, counties, branches and other actual places. You can also return there to extend the hierarchy later."))
			.appendTo(editor);
		update_anchor_choices();
	};

	slide.geo_editor = {
		validate() {
			if (!levels.length || levels.some((row) => !row.label.trim())) {
				frappe.msgprint(__("Give every geographic level a name, or remove empty rows."));
				return false;
			}
			if (!anchor) {
				frappe.msgprint(__("Choose the level where applications are made."));
				return false;
			}
			sync();
			return true;
		},
	};
	render();
};
