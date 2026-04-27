// Copyright (c) 2025, Kenya Red Cross Society and contributors
// For license information, please see license.txt

frappe.ui.form.on("VM Notification Center", {
	refresh(frm) {
		frm.trigger("clearDataTable");
		initialiseRecipientTypeField(frm);
		branchQuery(frm);
	},

	clearDataTable(frm) {
		let wrapper = frm.fields_dict["recipients"].$wrapper;
		wrapper.empty();
	},

	show_recpients(frm) {
		frm.trigger("fetchRecipients");
	},
	fetchRecipients(frm) {
		frappe.call({
			doc: frm.doc,
			method: "get_recipient_list",
			freeze: true,
			freeze_message: "Fetching Recipients...",
			callback: (r) => {
				let wrapper = frm.fields_dict["recipients"].$wrapper;
				wrapper.empty();

				let container = $("<div>").appendTo(wrapper)[0];
				new frappe.DataTable(container, {
					columns: [
						{
							name: "Recipient ID",
							width: 150,
							format: (value) => {
								if (!value) return "—";
								return `<a href="/app/${frm.doc.recipient_type.toLowerCase()}/${value}" target="_blank">${value}</a>`;
							},
						},
						{ name: "Recipient Name", width: 200 },
						{
							name: "Email",
							width: 200,
							format: (value) => {
								if (!value) return "—";
								return `<a href="/app/user/${value}" target="_blank">${value}</a>`;
							},
						},
						{ name: "Phone", width: 150 },
					],
					data: r.message.map((recipient) => [
						recipient.recipient_id,
						recipient.recipient_name,
						recipient.user,
						recipient.phone,
					]),
					inlineFilters: true,
					noDataMessage: "No recipients found",
					layout: "fluid",
					cellHeight: 35,
					disableReorderColumn: true,
				});
			},
			error: (err) => {
				frappe.dom.unfreeze();
				frappe.throw("An error occurred while fetching recipients.");
				console.error(err);
			},
			always: () => {
				frappe.dom.unfreeze();
			},
		});
	},

	party_type(frm) {
		initialiseRegionField(frm);
	},
	personnel_type(frm) {},

	buildFilterPayload: (filters) => {
		const payload = [];
		payload.push(filters);

		console.log("payload", payload);
	},
	region: (frm) => {
		frm.set_value("branch", "");
		branchQuery(frm);
	},
	county: (frm) => {
		frm.set_value("sub_county", "");
		frm.set_value("ward", "");
		frm.set_value("administrative_location", "");
		set_sub_county_filter(frm);
		set_ward_filter(frm);
		set_administrative_location_filter(frm);
	},
	sub_county: (frm) => {
		frm.set_value("administrative_location", "");
		set_administrative_location_filter(frm);
	},

	fetch_party_list: (frm) => {
		frm.trigger("get_party_list");
	},
});

const initialiseRecipientTypeField = (frm) => {
	frm.set_query("recipient_type", () => {
		return {
			filters: {
				name: ["in", ["Employee", "VM Member"]],
			},
		};
	});
};

const initialiseRegionField = (frm) => {
	let region = "";
	frm.doc.party_type && frm.doc.party_type == "Employee"
		? (region = "region")
		: (region = "membership_region");
	frm.set_query(region, () => {
		return {
			filters: [["organisation_type", "=", "Region"]],
		};
	});
};

const branchQuery = (frm) => {
	const filters = [["organisation_type", "=", "Branch"]];
	const regions = [];
	if (frm.doc.party_type && frm.doc.party_type == "Employee") {
		if (frm.doc.region && frm.doc.region.length) {
			frm.doc.region.forEach((region) => {
				regions.push(region.company);
			});
			filters.push(["parent_company", "in", regions]);
		}
	} else if (frm.doc.party_type && frm.doc.party_type == "VM Member") {
		if (frm.doc.membership_region && frm.doc.membership_region.length) {
			frm.doc.membership_region.forEach((region) => {
				regions.push(region.company);
			});
			filters.push(["parent_company", "in", regions]);
		}
	}
	let branch_field = "";
	frm.doc.party_type && frm.doc.party_type == "Employee"
		? (branch_field = "branch")
		: (branch_field = "membership_branch");
	frm.set_query(branch_field, () => {
		return {
			filters: filters,
		};
	});
};

const set_sub_county_filter = (frm) => {
	const counties = [];
	const filters = [];
	if (frm.doc.county && frm.doc.county.length) {
		frm.doc.county.forEach((county) => {
			counties.push(county.county);
		});
		filters.push(["county", "in", counties]);

		frm.set_query("sub_county", () => {
			return {
				filters: filters,
			};
		});
	}
};

const set_ward_filter = (frm) => {
	const counties = [];
	const filters = [];
	if (frm.doc.county && frm.doc.county.length) {
		frm.doc.county.forEach((county) => {
			counties.push(county.county);
		});
		filters.push(["county", "in", counties]);

		frm.set_query("ward", () => {
			return {
				filters: filters,
			};
		});
	}
};

const set_administrative_location_filter = (frm) => {
	const counties = [];
	const filters = [];
	const subCounties = [];
	if (frm.doc.county && frm.doc.county.length) {
		frm.doc.county.forEach((county) => {
			counties.push(county.county);
		});
		filters.push(["county", "in", counties]);

		frm.set_query("administrative_location", () => {
			return {
				filters: filters,
			};
		});
	}

	if (frm.doc.sub_county && frm.doc.sub_county.length) {
		frm.doc.sub_county.forEach((subCounty) => {
			subCounties.push(subCounty.sub_county);
		});
		filters.push(["sub_county", "in", subCounties]);

		frm.set_query("administrative_location", () => {
			return {
				filters: filters,
			};
		});
	}
};
