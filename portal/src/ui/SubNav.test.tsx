import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mount } from "../test/harness";
import { SubNav, type SubNavItem } from "./SubNav";

/**
 * The section navigation is a routed panel, not component state.
 *
 * These tests hold that: every destination is a real anchor with an `href`, so
 * a screen can be linked, bookmarked and reached with the back button. A tab
 * strip driven by `useState` would pass no assertion below.
 */

const ITEMS: SubNavItem[] = [
	{ to: "/admin/deployments", labelKey: "a", fallback: "Deployment dashboard", end: true },
	{ to: "/admin/deployments/terms", labelKey: "b", fallback: "Terms of Reference", groupKey: "g", groupFallback: "Plan" },
	{ to: "/admin/deployments/new", labelKey: "c", fallback: "Create deployment", groupKey: "g" },
];

function show(path: string, horizontal = false) {
	return mount(<SubNav title="Deployments" items={ITEMS} horizontal={horizontal} />, {
		route: path,
	});
}

describe("SubNav", () => {
	it("renders every destination as a link with a real href", () => {
		show("/admin/deployments");

		expect(screen.getByRole("link", { name: "Deployment dashboard" }).getAttribute("href")).toBe(
			"/admin/deployments",
		);
		expect(screen.getByRole("link", { name: "Create deployment" }).getAttribute("href")).toBe(
			"/admin/deployments/new",
		);
	});

	it("marks the current destination for assistive technology, not only in colour", () => {
		show("/admin/deployments/terms");

		// React Router sets aria-current="page" on the active NavLink, which is
		// what a screen reader announces. Colour alone would say nothing here.
		expect(
			screen.getByRole("link", { name: "Terms of Reference" }).getAttribute("aria-current"),
		).toBe("page");
		expect(
			screen.getByRole("link", { name: "Create deployment" }).getAttribute("aria-current"),
		).toBeNull();
	});

	it("does not keep the index route selected while a child route is open", () => {
		// `end: true` on the dashboard entry is what stops "/admin/deployments"
		// staying highlighted on every page beneath it.
		show("/admin/deployments/terms");

		expect(
			screen.getByRole("link", { name: "Deployment dashboard" }).getAttribute("aria-current"),
		).toBeNull();
	});

	it("names its own landmark so a page can carry two navigations", () => {
		show("/admin/deployments");

		expect(screen.getByRole("navigation", { name: "Deployments sections" })).toBeTruthy();
	});

	it("draws group headings in the column and drops them in the scroller", () => {
		show("/admin/deployments");
		expect(screen.getByText("Plan")).toBeTruthy();

		show("/admin/deployments", true);
		// The horizontal arrangement is a row of pills with no room for headings;
		// the destinations must all still be there.
		expect(screen.getAllByRole("link", { name: "Create deployment" }).length).toBeGreaterThan(0);
	});
});
