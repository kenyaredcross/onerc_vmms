import { describe, expect, it } from "vitest";

import { isShortMapLink, pointIn } from "./mapLinks";

/** What a coordinator pastes from Google Maps in the browser, read into a pin. */
describe("reading a point from what was pasted", () => {
	it("reads coordinates copied by right-clicking the map", () => {
		expect(pointIn("-1.29207, 36.82195")).toEqual({ latitude: -1.29207, longitude: 36.82195 });
		expect(pointIn("  -0.0917 34.768 ")).toEqual({ latitude: -0.0917, longitude: 34.768 });
	});

	it("prefers a place's own pin over the map view's centre", () => {
		const url =
			"https://www.google.com/maps/place/Kenyatta+Ave/@-1.2833,36.8167,17z/data=!3m1!4b1!4m6!3m5!1s0x0:0x0!8m2!3d-1.28333!4d36.81667";

		expect(pointIn(url)).toEqual({ latitude: -1.28333, longitude: 36.81667 });
	});

	it("reads the map view and the search forms", () => {
		expect(pointIn("https://www.google.com/maps/@-4.0435,39.6682,15z")).toEqual({
			latitude: -4.0435,
			longitude: 39.6682,
		});
		expect(pointIn("https://maps.google.com/?q=-1.3,36.8")).toEqual({ latitude: -1.3, longitude: 36.8 });
		expect(pointIn("https://www.google.com/maps/search/?api=1&query=0.5143%2C35.2698")).toEqual({
			latitude: 0.5143,
			longitude: 35.2698,
		});
	});

	it("finds nothing in words, and nothing out of range", () => {
		expect(pointIn("Kenyatta National Hospital")).toBeNull();
		expect(pointIn("120, 36.8")).toBeNull();
	});

	it("knows a phone's share link must be followed on the server", () => {
		expect(isShortMapLink("https://maps.app.goo.gl/AbCdEf123")).toBe(true);
		expect(isShortMapLink("https://www.google.com/maps/@-1.2,36.8,15z")).toBe(false);
		expect(isShortMapLink("not a link")).toBe(false);
	});
});
