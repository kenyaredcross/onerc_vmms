import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mount } from "../test/harness";
import { Button, StateBadge, Table, Row, Cell } from "./primitives";

/**
 * The accessibility floor, held by test rather than by review.
 *
 * Each of these is a rule the brief states and a rule that is easy to undo by
 * accident in a restyle: state is never colour alone, a destructive control
 * says what it destroys, an icon-only control has a name, and a register is a
 * real table.
 */

describe("state is never carried by colour alone", () => {
	it("prints the state as text next to its tint", () => {
		mount(<StateBadge state="Approved" />);

		// The word itself, not just a green pill.
		expect(screen.getByText("Approved")).toBeTruthy();
	});

	it("carries a shape as well as a hue", () => {
		const { container } = mount(<StateBadge state="Rejected" />);
		const dot = container.querySelector('[aria-hidden="true"]');

		expect(dot).not.toBeNull();
		expect(dot?.className).toContain("rounded-full");
	});

	it("renders an unknown state rather than dropping it", () => {
		// Society configuration can produce a state this file has no tone for.
		// Showing it in the neutral tone is right; showing nothing is not.
		mount(<StateBadge state="Some Society Stage" />);

		expect(screen.getByText("Some Society Stage")).toBeTruthy();
	});

	it("draws nothing at all when there is no state, rather than an empty pill", () => {
		const { container } = mount(<StateBadge state={null} />);

		expect(container.textContent).toBe("");
	});
});

describe("destructive actions", () => {
	it("are distinguishable without relying on colour", () => {
		const { container } = mount(<Button variant="danger">Delete draft</Button>);

		// A glyph as well as the red: the control still reads as destructive in
		// greyscale and in forced-colours mode, where backgrounds are dropped.
		expect(container.querySelector("svg")).not.toBeNull();
		expect(screen.getByRole("button", { name: "Delete draft" })).toBeTruthy();
	});
});

describe("a busy control", () => {
	it("says so to assistive technology and refuses a second click", () => {
		mount(
			<Button busy onClick={() => {}}>
				Save
			</Button>,
		);

		const button = screen.getByRole("button", { name: "Save" });

		expect(button.getAttribute("aria-busy")).toBe("true");
		expect((button as HTMLButtonElement).disabled).toBe(true);
	});

	it("keeps its label while in flight, so the button does not change width", () => {
		mount(<Button busy>Submit for review</Button>);

		expect(screen.getByRole("button", { name: "Submit for review" })).toBeTruthy();
	});
});

describe("registers are real tables", () => {
	it("uses table semantics with scoped column headers", () => {
		mount(
			<Table head={["Volunteer", "Hours"]} caption="Volunteers" align={["left", "right"]}>
				<Row>
					<Cell>Amina Njoroge</Cell>
					<Cell>48.5</Cell>
				</Row>
			</Table>,
		);

		// `getByRole("table")` only passes for a real <table>; a grid of divs
		// would fail here, which is the point.
		const table = screen.getByRole("table", { name: "Volunteers" });

		expect(table).toBeTruthy();
		expect(screen.getAllByRole("columnheader")).toHaveLength(2);
		expect(screen.getAllByRole("columnheader")[0].getAttribute("scope")).toBe("col");
	});

	it("right-aligns the columns that hold figures", () => {
		mount(
			<Table head={["Name", "Total"]} align={["left", "right"]}>
				<Row>
					<Cell>A</Cell>
					<Cell>1</Cell>
				</Row>
			</Table>,
		);

		expect(screen.getAllByRole("columnheader")[1].className).toContain("text-right");
	});
});
