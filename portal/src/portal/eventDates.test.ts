import { describe, expect, it } from "vitest";

import { eventEnded } from "./eventDates";

describe("eventEnded", () => {
	const today = "2026-11-16";

	it("is true once the last day is behind us", () => {
		expect(eventEnded({ start_date: "2026-09-01", end_date: "2026-09-30" }, today)).toBe(true);
		expect(eventEnded({ start_date: "2026-11-15", end_date: "" }, today)).toBe(true);
	});

	it("is false on the last day and before it", () => {
		expect(eventEnded({ start_date: "2026-11-10", end_date: "2026-11-16" }, today)).toBe(false);
		expect(eventEnded({ start_date: "2026-12-19", end_date: "2026-12-19" }, today)).toBe(false);
	});

	it("is false for an event with no dates", () => {
		expect(eventEnded({ start_date: "", end_date: "" }, today)).toBe(false);
	});
});
