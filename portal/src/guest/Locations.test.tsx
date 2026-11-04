import { act, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { mount } from "../test/harness";

/**
 * The public branch directory: headquarters first, a county found by map,
 * search or position, its regional office beside it, and a way to join it.
 */
let currentUser: string | null = null;
let standing: unknown = { volunteer: null, memberships: [] };

const branch = (overrides: Record<string, unknown>) => ({
	address: "",
	latitude: null,
	longitude: null,
	has_point: false,
	phone: "",
	email: "",
	opening_hours: "",
	photo: "",
	county: "",
	county_label: "",
	region: "",
	region_label: "",
	is_headquarters: false,
	is_regional: false,
	...overrides,
});

const LOCATIONS = [
	branch({ name: "LOC-HQ", location_name: "Society Headquarters", geo_node: "ROOT", is_headquarters: true }),
	branch({
		name: "LOC-B",
		location_name: "Bungoma Branch Office",
		geo_node: "C-BUNGOMA",
		county: "C-BUNGOMA",
		county_label: "Bungoma",
		region: "R-NORTH",
		region_label: "North Rift",
		phone: "0700 000 000",
		latitude: 0.56,
		longitude: 34.56,
		has_point: true,
	}),
	branch({
		name: "LOC-M",
		location_name: "Mombasa Branch Office",
		geo_node: "C-MOMBASA",
		county: "C-MOMBASA",
		county_label: "Mombasa",
		region: "R-COAST",
		region_label: "Coast",
		latitude: -4.04,
		longitude: 39.66,
		has_point: true,
	}),
	branch({
		name: "LOC-R",
		location_name: "North Rift Regional Office",
		geo_node: "R-NORTH",
		region: "R-NORTH",
		region_label: "North Rift",
		is_regional: true,
	}),
];

const SHAPES = {
	view_box: "0 0 1000 1000",
	shapes: [
		{ name: "C-BUNGOMA", path: "M0,0L10,0L10,10Z", centre: [5, 5] },
		{ name: "C-MOMBASA", path: "M20,20L30,20L30,30Z", centre: [25, 25] },
	],
	has_file: true,
	credit: null,
	labels: { "C-BUNGOMA": "Bungoma", "C-MOMBASA": "Mombasa" },
	regions: { "C-BUNGOMA": "R-NORTH", "C-MOMBASA": "R-COAST" },
};

vi.mock("frappe-react-sdk", async (importOriginal) => {
	// The SDK ships CommonJS: the real exports hang off `default`.
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	const { createContext } = await import("react");

	const answer = (message: unknown) => ({
		data: { message },
		error: null,
		isLoading: false,
		isValidating: false,
		mutate: () => Promise.resolve(undefined),
	});

	return {
		...actual.default,
		default: actual.default,
		FrappeContext: createContext({ call: { get: () => Promise.resolve({ message: null }) } }),
		FrappeProvider: ({ children }: { children: React.ReactNode }) => children,
		useFrappeGetCall: (method: string) =>
			method.endsWith("my_standing")
				? answer(standing)
				: method.endsWith("county_map")
				? answer(SHAPES)
				: method.endsWith("locations.published")
					? answer({ count: LOCATIONS.length, locations: LOCATIONS })
					: answer(null),
		useFrappeAuth: () => ({ currentUser, isLoading: false, logout: () => Promise.resolve(undefined) }),
	};
});

const { Directory } = await import("./Locations");

const search = (text: string) => {
	const box = screen.getByRole("combobox");
	fireEvent.focus(box);
	fireEvent.change(box, { target: { value: text } });
	fireEvent.keyDown(box, { key: "Enter" });
};

describe("the branch directory", () => {
	beforeEach(() => {
		currentUser = null;
		standing = { volunteer: null, memberships: [] };
	});

	it("shows headquarters until a county is chosen, and lists no branches", () => {
		mount(<Directory />);

		expect(screen.getByText("Society Headquarters")).toBeTruthy();
		expect(screen.queryByText("Bungoma Branch Office")).toBeNull();
	});

	it("finds a county by search and shows its branch with the regional office", () => {
		mount(<Directory />);

		search("bung");

		expect(screen.getByText("Bungoma Branch Office")).toBeTruthy();
		expect(screen.getByText("Regional office · North Rift")).toBeTruthy();
		expect(screen.getByText("North Rift Regional Office")).toBeTruthy();
		expect(screen.queryByText("Society Headquarters")).toBeNull();
	});

	it("chooses a county from the map", () => {
		mount(<Directory />);

		fireEvent.click(screen.getByRole("button", { name: /^Mombasa:/ }));

		expect(screen.getByText("Mombasa Branch Office")).toBeTruthy();
		// Coast has no regional office recorded, so none is drawn.
		expect(screen.queryByText(/Regional office/)).toBeNull();
	});

	it("sends a guest to sign up, carrying the branch they chose", () => {
		mount(<Directory />);
		search("bung");

		const href = screen.getByRole("link", { name: "Volunteer here" }).getAttribute("href") ?? "";

		expect(href).toMatch(/^\/login\?redirect-to=.*#signup$/);
		expect(decodeURIComponent(href)).toContain("/join?path=volunteer&branch=C-BUNGOMA");
	});

	it("opens the form directly, with the branch, for somebody signed in", () => {
		currentUser = "amina@example.com";
		mount(<Directory />);
		search("bung");

		expect(screen.getByRole("link", { name: "Become a member" }).getAttribute("href")).toBe(
			"/join?path=member&branch=C-BUNGOMA",
		);
	});
});

describe("somebody who already belongs", () => {
	beforeEach(() => {
		currentUser = "amina@example.com";
	});

	it("marks a volunteer's own branch instead of offering to join it", () => {
		standing = {
			volunteer: { status: "Active", branch: "C-BUNGOMA", branch_label: "Bungoma" },
			memberships: [],
		};
		mount(<Directory />);
		search("bung");

		expect(screen.getByText("Your branch")).toBeTruthy();
		expect(screen.queryByRole("link", { name: "Volunteer here" })).toBeNull();
		expect(screen.getByRole("link", { name: "Become a member" })).toBeTruthy();
	});

	it("does not offer a volunteer a second application at another branch", () => {
		standing = {
			volunteer: { status: "Active", branch: "C-BUNGOMA", branch_label: "Bungoma", can_request_transfer: true },
			memberships: [],
		};
		mount(<Directory />);
		search("momb");

		expect(screen.queryByRole("link", { name: "Volunteer here" })).toBeNull();
		expect(screen.getByText(/You volunteer with Bungoma\./)).toBeTruthy();
		expect(screen.getByRole("link", { name: "Ask to move here" }).getAttribute("href")).toBe(
			"/profile?transfer=C-MOMBASA",
		);
	});

	it("marks a branch the person is already a member of", () => {
		standing = {
			volunteer: null,
			memberships: [{ branch: "C-BUNGOMA", branch_label: "Bungoma", status: "Active" }],
		};
		mount(<Directory />);
		search("bung");

		expect(screen.getByText("You're a member here")).toBeTruthy();
		expect(screen.queryByRole("link", { name: "Become a member" })).toBeNull();
		expect(screen.getByRole("link", { name: "Volunteer here" })).toBeTruthy();
	});

	it("says a membership still being joined is being processed", () => {
		standing = {
			volunteer: null,
			memberships: [{ branch: "C-BUNGOMA", branch_label: "Bungoma", status: "Awaiting Payment" }],
		};
		mount(<Directory />);
		search("bung");

		expect(screen.getByText("Your membership here is being processed")).toBeTruthy();
	});
});

describe("finding the nearest branch", () => {
	const original = navigator.geolocation;

	afterEach(() => {
		Object.defineProperty(navigator, "geolocation", { value: original, configurable: true });
	});

	it("chooses the county of the nearest pinned branch", () => {
		Object.defineProperty(navigator, "geolocation", {
			configurable: true,
			value: {
				getCurrentPosition: (success: PositionCallback) =>
					success({ coords: { latitude: 0.6, longitude: 34.7 } } as GeolocationPosition),
			},
		});
		mount(<Directory />);

		act(() => {
			fireEvent.click(screen.getByRole("button", { name: "Find my nearest branch" }));
		});

		expect(screen.getByText("Bungoma Branch Office")).toBeTruthy();
		expect(within(screen.getByRole("status")).getByText(/Nearest to you: Bungoma Branch Office/)).toBeTruthy();
	});

	it("says so plainly when the position cannot be had", () => {
		Object.defineProperty(navigator, "geolocation", {
			configurable: true,
			value: {
				getCurrentPosition: (_: PositionCallback, failure: PositionErrorCallback) =>
					failure({ code: 1 } as GeolocationPositionError),
			},
		});
		mount(<Directory />);

		act(() => {
			fireEvent.click(screen.getByRole("button", { name: "Find my nearest branch" }));
		});

		expect(screen.getByText(/Search for your county instead/)).toBeTruthy();
	});
});
