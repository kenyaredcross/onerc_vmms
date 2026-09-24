import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mount } from "../test/harness";
import type { PricedType } from "../portal/types";
import { PlanCards } from "./PlanCards";

/**
 * The rules a society's own configuration is most likely to break.
 *
 * A society publishes as many membership types as it likes, at any fees, with
 * any number of benefits on each, and every one of those is a number this app
 * cannot predict. What is held here is what has to stay true at five and six
 * types as much as at three: the row is composed around the card that is this
 * person's, the endpoint's cheapest-first order survives everywhere else, and
 * no single type's benefit list is allowed to set the height of the grid.
 */

function plan(name: string, amount: number, extra: Partial<PricedType> = {}): PricedType {
	return {
		known: true,
		membership_type: name.toLowerCase(),
		membership_type_name: name,
		description: null,
		amount,
		currency: "TZS",
		free: false,
		is_lifetime: false,
		duration_days: 365,
		requires_approver: false,
		benefits: [],
		...extra,
	};
}

/** The card names in the order they are drawn, which is the order somebody reads. */
function drawn(): string[] {
	return screen.getAllByRole("heading", { level: 3 }).map((node) => node.textContent ?? "");
}

describe("the row is composed around the membership somebody holds", () => {
	const three = [plan("Ordinary", 10_000), plan("Family", 25_000), plan("Life", 200_000)];

	it("puts their own in the middle, wherever its fee would have put it", () => {
		mount(<PlanCards types={three} held={["life"]} />);

		expect(drawn()).toEqual(["Ordinary", "Life", "Family"]);
	});

	it("keeps the cheapest-first order around it", () => {
		const six = [
			plan("Ordinary", 10_000),
			plan("Youth", 12_000),
			plan("Family", 25_000),
			plan("Corporate", 90_000),
			plan("Life", 200_000),
			plan("Patron", 500_000),
		];

		mount(<PlanCards types={six} held={["patron"]} />);

		// Only the held card moved. Everything else still climbs.
		expect(drawn()).toEqual([
			"Ordinary",
			"Patron",
			"Youth",
			"Family",
			"Corporate",
			"Life",
		]);
	});

	it("moves nothing for somebody who holds none", () => {
		mount(<PlanCards types={three} held={[]} />);

		expect(drawn()).toEqual(["Ordinary", "Family", "Life"]);
	});

	it("moves nothing where there is no middle to move to", () => {
		const two = [plan("Ordinary", 10_000), plan("Life", 200_000)];

		mount(<PlanCards types={two} held={["life"]} />);

		expect(drawn()).toEqual(["Ordinary", "Life"]);
	});

	it("does not shuffle the row somebody is choosing from", () => {
		// The wizard's grid is two wide and tracks a selection. Cards that moved
		// as somebody chose would be a row reordering itself under the cursor.
		mount(
			<PlanCards types={three} held={["life"]} columns={2} selected={null} onSelect={() => {}} />,
		);

		expect(drawn()).toEqual(["Ordinary", "Family", "Life"]);
	});

	it("names the card for what it is rather than for what the reader did", () => {
		mount(<PlanCards types={three} held={["life"]} />);

		expect(screen.getByText("Current plan")).toBeTruthy();
	});
});

describe("no one type sets the height of the grid", () => {
	const many = plan("Patron", 500_000, {
		benefits: Array.from({ length: 8 }, (_, index) => ({
			key: `benefit-${index}`,
			label: `Benefit ${index}`,
			description: null,
		})),
	});

	it("shows the first few and says how many more there are", () => {
		mount(<PlanCards types={[many]} />);

		expect(screen.getByText("Benefit 4")).toBeTruthy();
		expect(screen.queryByText("Benefit 5")).toBeNull();
		expect(screen.getByText("and 3 more")).toBeTruthy();
	});

	it("says nothing about more where the whole list is shown", () => {
		const short = plan("Ordinary", 10_000, {
			benefits: [{ key: "one", label: "A membership card", description: null }],
		});

		mount(<PlanCards types={[short]} />);

		expect(screen.getByText("A membership card")).toBeTruthy();
		expect(screen.queryByText(/more$/)).toBeNull();
	});
});

describe("the fee is said in the unit people budget in", () => {
	it("divides a yearly fee into months, hedged", () => {
		mount(<PlanCards types={[plan("Ordinary", 24_000)]} />);

		expect(screen.getByText(/about .* a month/)).toBeTruthy();
	});

	it("says nothing monthly about a lifetime fee, which has no months", () => {
		mount(
			<PlanCards types={[plan("Life", 200_000, { is_lifetime: true, duration_days: 0 })]} />,
		);

		expect(screen.queryByText(/a month/)).toBeNull();
		expect(screen.getByText(/Paid once/)).toBeTruthy();
	});

	it("says nothing monthly about a fee that is already monthly", () => {
		mount(<PlanCards types={[plan("Monthly", 2_000, { duration_days: 30 })]} />);

		expect(screen.queryByText(/about/)).toBeNull();
	});
});
