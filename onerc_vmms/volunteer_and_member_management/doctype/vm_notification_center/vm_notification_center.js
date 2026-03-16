// Copyright (c) 2025, Kenya Red Cross Society and contributors
// For license information, please see license.txt

frappe.ui.form.on("VM Notification Center", {
	refresh(frm) {
		frm.trigger("showPartyChild");
		frm.trigger("fetchParties");
		initiliasePartyTypeField(frm);
		branchQuery(frm);
	},

	showPartyChild(frm) {
		frm.doc.__islocal
			? frm.set_df_property("parties", "hidden", 1)
			: frm.set_df_property("parties", "hidden", 0);
	},
	fetchParties(frm) {
		if (!frm.doc.__islocal) {
			frm.add_custom_button("Fetch Parties", () => {
				frappe.dom.freeze("Fetching Parties...");
				frappe.call({
					doc: frm.doc,
					method: "get_party_list",
					freeze: true,
					freeze_message: "Fetching Parties...",
					callback: (r) => {
						frappe.dom.unfreeze();

						console.log("parties", r);

						frm.clear_table("parties");

						if (r.message && r.message.length) {
							r.message.forEach((party) => {
								const child = frm.add_child("parties");
								child.link_doctype = frm.doc.party_type;
								child.party_name = party.full_name;
								child.party = party.name;
								child.user = party.user_id;
								child.phone = party.phone;
							});
							frm.refresh_field("parties");
							frm.save();
						}
					},
				});
				frappe.dom.unfreeze();
			});
		}
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
	membership_region: (frm) => {
		frm.set_value("membership_branch", "");
		branchQuery(frm);
	},

	fetch_party_list: (frm) => {
		frm.trigger("get_party_list");
	},
});

const initiliasePartyTypeField = (frm) => {
	frm.set_query("party_type", () => {
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
