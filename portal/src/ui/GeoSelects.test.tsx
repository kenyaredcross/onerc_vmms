import { describe, expect, it } from "vitest";

import type { GeoNode } from "../portal/types";
import { selectedNode } from "./GeoSelects";

/**
 * A society that keeps geography below the level it records at — Kenya, whose 47
 * counties each carry sub-counties and whose `allowed_anchor_levels` names the
 * county alone. The picker draws a Sub-County rung for such a county, correctly,
 * because `geo.browse` returns children for it.
 */
const NATIONAL: GeoNode = {
	name: "GEO-00001",
	label: "Kenya Red Cross Society",
	level: "krcs-national",
	level_name: "National",
};
const COUNTY: GeoNode = {
	name: "GEO-00020",
	label: "Kisumu",
	level: "krcs-county",
	level_name: "County",
};
const SUB_COUNTY: GeoNode = {
	name: "GEO-00210",
	label: "Nyando",
	level: "krcs-sub-county",
	level_name: "Sub-County",
};

const COUNTY_ONLY = ["krcs-county"];

describe("selectedNode", () => {
	it("takes the answer when it is at a permitted level", () => {
		expect(selectedNode([NATIONAL, COUNTY], COUNTY_ONLY)).toBe(COUNTY);
	});

	it("reads a half-walked chain as nothing chosen", () => {
		expect(selectedNode([NATIONAL], COUNTY_ONLY)).toBeNull();
	});

	it("reads an empty chain as nothing chosen", () => {
		expect(selectedNode([], COUNTY_ONLY)).toBeNull();
	});

	it("keeps the county when an optional deeper rung is also answered", () => {
		/**
		 * The regression this function was rewritten for. Reading only the last
		 * entry meant answering the Sub-County rung un-chose the county: the
		 * placement step's guard saw null, Continue went dead, and the note
		 * underneath told somebody already below a county to keep going down to
		 * one. Recoverable only by blanking a dropdown.
		 */
		expect(selectedNode([NATIONAL, COUNTY, SUB_COUNTY], COUNTY_ONLY)).toBe(COUNTY);
	});

	it("still refuses a chain with no permitted rung anywhere in it", () => {
		expect(selectedNode([NATIONAL, SUB_COUNTY], COUNTY_ONLY)).toBeNull();
	});

	it("takes the deepest answer when the society constrains nothing", () => {
		expect(selectedNode([NATIONAL, COUNTY, SUB_COUNTY])).toBe(SUB_COUNTY);
		expect(selectedNode([NATIONAL, COUNTY, SUB_COUNTY], [])).toBe(SUB_COUNTY);
	});

	it("takes the deepest permitted rung when two levels are permitted", () => {
		/**
		 * Tanzania's shape: a volunteer may be recorded at a branch or at a
		 * sub-branch under it, and the deeper answer is the one that counts.
		 */
		expect(selectedNode([NATIONAL, COUNTY, SUB_COUNTY], ["krcs-county", "krcs-sub-county"])).toBe(
			SUB_COUNTY,
		);
	});
});
