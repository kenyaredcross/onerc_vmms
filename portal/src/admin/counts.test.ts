import { describe, expect, it } from "vitest";

import type { AssignmentCounts, DeploymentSummary } from "../portal/types";
import { exceptionsFor, figuresFor } from "./counts";

/**
 * The counting rules the deployment dashboard reports.
 *
 * These exist because the words are load-bearing. A person who was invited and
 * has not answered is not somebody on a deployment, and the two were once added
 * together on one tile — which reported people as being somewhere they had not
 * agreed to go.
 */

function counts(over: Partial<AssignmentCounts> = {}): AssignmentCounts {
	const base: AssignmentCounts = {
		Assigned: 0,
		Pending: 0,
		Accepted: 0,
		Declined: 0,
		Withdrawn: 0,
		on_deployment: 0,
		open: 0,
		total: 0,
	};

	return { ...base, ...over };
}

function deployment(over: Partial<DeploymentSummary> = {}): DeploymentSummary {
	return {
		name: "DEP-1",
		terms_of_reference: "TOR-1",
		geo_node: "GEO-1",
		geo_path: null,
		status: "Active",
		is_open: true,
		is_settled: false,
		is_closed_out: false,
		coordinator: null,
		start_date: null,
		end_date: null,
		planned_start: null,
		planned_end: null,
		briefing_on: null,
		check_in_deadline: null,
		expected_return: null,
		actual_start: null,
		actual_end: null,
		closed_out_on: null,
		volunteers_required: 0,
		email_template: null,
		participant_count: 0,
		assignment_counts: counts(),
		places_left: null,
		...over,
	};
}

describe("deployed now means assigned or accepted on an active deployment", () => {
	it("counts confirmed people on an active deployment", () => {
		const figures = figuresFor([
			deployment({ status: "Active", assignment_counts: counts({ on_deployment: 6 }) }),
		]);

		expect(figures.deployedNow).toBe(6);
		expect(figures.comingUp).toBe(0);
	});

	it("puts confirmed people on a planned deployment under coming up, not deployed", () => {
		const figures = figuresFor([
			deployment({ status: "Planned", assignment_counts: counts({ on_deployment: 4 }) }),
		]);

		expect(figures.deployedNow).toBe(0);
		expect(figures.comingUp).toBe(4);
	});

	it("never counts a pending invitation as somebody deployed", () => {
		const figures = figuresFor([
			deployment({
				status: "Active",
				assignment_counts: counts({ on_deployment: 2, Pending: 9 }),
			}),
		]);

		expect(figures.deployedNow).toBe(2);
		expect(figures.awaitingResponse).toBe(9);
	});

	it("ignores a completed deployment entirely", () => {
		const figures = figuresFor([
			deployment({
				status: "Completed",
				is_open: false,
				assignment_counts: counts({ on_deployment: 20 }),
			}),
		]);

		expect(figures.deployedNow).toBe(0);
		expect(figures.comingUp).toBe(0);
		expect(figures.runningCount).toBe(0);
	});
});

describe("open positions", () => {
	it("adds places left across running deployments", () => {
		const figures = figuresFor([
			deployment({ places_left: 3 }),
			deployment({ status: "Planned", places_left: 2 }),
		]);

		expect(figures.openPositions).toBe(5);
	});

	it("treats an unstated requirement as no shortfall rather than zero places", () => {
		// A deployment that never said how many people it needs is not full and
		// is not short. Reading null as 0 would quietly report it as staffed.
		const figures = figuresFor([deployment({ places_left: null, volunteers_required: 0 })]);

		expect(figures.openPositions).toBe(0);
		expect(figures.requested).toBe(0);
	});
});

describe("the sample size is carried, so nothing is labelled a register total", () => {
	it("reports how many rows the figures came from", () => {
		expect(figuresFor([deployment(), deployment(), deployment()]).sampled).toBe(3);
	});
});

describe("exceptions are facts off the row", () => {
	it("flags a running deployment with nobody on the roster", () => {
		const found = exceptionsFor([deployment({ assignment_counts: counts({ on_deployment: 0 }) })]);

		expect(found).toHaveLength(1);
		expect(found[0].text).toMatch(/Nobody on the roster/);
		expect(found[0].tone).toBe("danger");
	});

	it("flags unanswered invitations and pluralises honestly", () => {
		const one = exceptionsFor([
			deployment({ assignment_counts: counts({ on_deployment: 1, Pending: 1 }) }),
		]);
		const many = exceptionsFor([
			deployment({ assignment_counts: counts({ on_deployment: 1, Pending: 3 }) }),
		]);

		expect(one[0].text).toBe("1 invitation unanswered");
		expect(many[0].text).toBe("3 invitations unanswered");
	});

	it("flags a deployment starting within the week with places open", () => {
		const now = Date.parse("2026-08-24T00:00:00Z");
		const found = exceptionsFor(
			[
				deployment({
					start_date: "2026-08-27",
					places_left: 2,
					assignment_counts: counts({ on_deployment: 1 }),
				}),
			],
			now,
		);

		expect(found[0].text).toMatch(/Starts within the week/);
		expect(found[0].text).toMatch(/2 positions open/);
	});

	it("says nothing about a deployment starting well in the future", () => {
		const now = Date.parse("2026-08-24T00:00:00Z");
		const found = exceptionsFor(
			[
				deployment({
					start_date: "2026-12-01",
					places_left: 2,
					assignment_counts: counts({ on_deployment: 1 }),
				}),
			],
			now,
		);

		expect(found).toHaveLength(0);
	});

	it("leaves a closed deployment alone however short it was", () => {
		const found = exceptionsFor([
			deployment({ status: "Cancelled", is_open: false, places_left: 9 }),
		]);

		expect(found).toHaveLength(0);
	});

	it("raises more than one note for a deployment with more than one problem", () => {
		const now = Date.parse("2026-08-24T00:00:00Z");
		const found = exceptionsFor(
			[
				deployment({
					start_date: "2026-08-25",
					places_left: 4,
					assignment_counts: counts({ on_deployment: 0, Pending: 2 }),
				}),
			],
			now,
		);

		expect(found.map((item) => item.tone)).toEqual(["danger", "warning", "warning"]);
	});
});
