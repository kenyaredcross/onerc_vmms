import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mount } from "../test/harness";
import { ActivityTile, DatedRow, FolderCard, SearchField } from "./patterns";

describe("FolderCard", () => {
	it("is one link, so the whole card is reachable by keyboard", () => {
		mount(
			<FolderCard
				to="/admin/projects/PROJ-1"
				name="Emergency Preparedness 2026"
				summary="Flood response and rapid deployment support."
				status="Active"
				counts="Dodoma · from 1 Feb 2026"
			/>,
		);

		const link = screen.getByRole("link", { name: /Emergency Preparedness 2026/ });

		expect(link.getAttribute("href")).toBe("/admin/projects/PROJ-1");
	});

	it("shows the status as a word, not only a tint", () => {
		mount(<FolderCard to="/x" name="Water Safety" status="Planned" />);

		expect(screen.getByText("Planned")).toBeTruthy();
	});

	it("omits the summary line rather than rendering an empty paragraph", () => {
		const { container } = mount(<FolderCard to="/x" name="No summary" />);

		expect(container.querySelectorAll("p")).toHaveLength(0);
	});
});

describe("ActivityTile", () => {
	it("is a link when it has somewhere to go", () => {
		mount(<ActivityTile label="Open tasks" value={3} to="/tasks" />);

		expect(screen.getByRole("link").getAttribute("href")).toBe("/tasks");
	});

	it("is not a link when it is only context", () => {
		// A figure that cannot be acted on should not pretend to be clickable.
		mount(<ActivityTile label="Awaiting response" value={0} />);

		expect(screen.queryByRole("link")).toBeNull();
	});

	it("shows an em dash while loading rather than a misleading zero", () => {
		mount(<ActivityTile label="Hours served" value="—" />);

		expect(screen.getByText("—")).toBeTruthy();
	});
});

describe("DatedRow", () => {
	it("carries a machine-readable date as well as a human one", () => {
		const { container } = mount(
			<DatedRow iso="2026-08-26" day="26" month="Aug" title="Health outreach briefing" />,
		);

		expect(container.querySelector("time")?.getAttribute("datetime")).toBe("2026-08-26");
		expect(screen.getByText("Health outreach briefing")).toBeTruthy();
	});
});

describe("SearchField", () => {
	it("always has an accessible name, even with the label hidden", () => {
		mount(<SearchField value="" onChange={() => {}} label="Search projects" />);

		expect(screen.getByRole("searchbox", { name: "Search projects" })).toBeTruthy();
	});

	it("associates a visible label with its field", () => {
		mount(
			<SearchField
				id="q"
				value=""
				onChange={() => {}}
				label="Search by role or skill"
				showLabel
			/>,
		);

		expect(screen.getByLabelText("Search by role or skill")).toBeTruthy();
	});
});
