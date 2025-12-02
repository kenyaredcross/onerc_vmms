// Copyright (c) 2025, Kenya Red Cross Society and contributors
// For license information, please see license.txt

frappe.ui.form.on("VM Notification Center", {
	refresh(frm) {
		initiliasePartyTypeField(frm);
		branchQuery(frm);
	},

	party_type(frm) {
		initialiseRegionField(frm);
	},
	personnel_type(frm) {
		frm.trigger("get_party_list");
	},

	get_party_list: (frm) => {
		frm.call({
			method: "get_party_list",
			args: {
				personnel_type: frm.doc.personnel_type,
			},
		}).then((r) => {
			console.log("parties", r);
		});
	},

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
