import { createEvent, fireEvent, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mount } from "../test/harness";
import { Button, ButtonLink, StateBadge, Table, Row, Cell, appRoute } from "./primitives";

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

/**
 * The rule that decides whether a button navigates or routes.
 *
 * Held by test because getting it wrong is invisible in review and loud in use:
 * an in-app path rendered as a bare anchor drops the router's basename, and the
 * site answers the resulting address with its own "Page not found".
 */
describe("a button link stays inside the app unless the address leaves it", () => {
	it("routes an ordinary console path", () => {
		expect(appRoute("/admin/deployments/new")).toBe("/admin/deployments/new");
		expect(appRoute("/admin/deployments/terms?new=1")).toBe("/admin/deployments/terms?new=1");
		expect(appRoute("/dashboard")).toBe("/dashboard");
	});

	it("strips the app's older /portal prefix rather than navigating to it", () => {
		expect(appRoute("/portal/profile")).toBe("/profile");
		expect(appRoute("/portal")).toBe("/");
	});

	it("hands the site back its own addresses", () => {
		// A file response, the desk, another app, and the framework's login.
		expect(appRoute("/api/method/vmmsx.api.deployment.download_terms?name=T-1")).toBeNull();
		expect(appRoute("/app/event/EV-1")).toBeNull();
		expect(appRoute("/login")).toBeNull();
		expect(appRoute("/files/a.pdf")).toBeNull();
	});

	it("hands back anything with a scheme or no leading slash", () => {
		expect(appRoute("https://example.org")).toBeNull();
		expect(appRoute("//example.org")).toBeNull();
		expect(appRoute("mailto:someone@example.org")).toBeNull();
	});

	/**
	 * Both render an `<a>`, so the href proves nothing — the broken version
	 * produced exactly the same one. What separates them is the click: a router
	 * link cancels the browser's navigation and handles it in the app, and a
	 * plain anchor lets it through. Letting it through is the whole bug, because
	 * the address the browser then asks for carries no basename.
	 */
	const clickIsHandledInApp = (name: string) => {
		const link = screen.getByRole("link", { name });
		const click = createEvent.click(link, { button: 0, bubbles: true, cancelable: true });

		fireEvent(link, click);

		return click.defaultPrevented;
	};

	it("routes an in-app destination rather than reloading the site", () => {
		mount(<ButtonLink to="/admin/deployments/new">Create deployment</ButtonLink>, {
			route: "/admin/deployments",
		});

		expect(clickIsHandledInApp("Create deployment")).toBe(true);
	});

	it("still lets a site-level destination navigate for real", () => {
		mount(<ButtonLink to="/api/method/vmmsx.api.deployment.download_terms">Print as PDF</ButtonLink>);

		expect(clickIsHandledInApp("Print as PDF")).toBe(false);
	});
});
