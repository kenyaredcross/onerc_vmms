import { describe, expect, it } from "vitest";

import { geoPath } from "./format";

/** A place is shown by its own name, never the region and society above it. */
describe("geoPath", () => {
	it("keeps only the place itself", () => {
		expect(geoPath("West Pokot — KRCS North Rift — Kenya Red Cross Society")).toBe("West Pokot");
		expect(geoPath("Baringo — KRCS South Rift — Kenya Red Cross Society")).toBe("Baringo");
	});

	it("names the society for a record placed at the society itself", () => {
		expect(geoPath("Kenya Red Cross Society")).toBe("Kenya Red Cross Society");
	});

	it("is empty when nothing is recorded", () => {
		expect(geoPath(null)).toBe("");
		expect(geoPath("")).toBe("");
	});
});
