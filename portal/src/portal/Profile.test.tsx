import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { OpenRegistration } from "./types";

/**
 * What the profile page says to somebody who has no volunteer record.
 *
 * **It used to say one thing to three different people.** "You have no
 * volunteer record — your profile appears here once your branch has verified
 * your application" is only true of somebody who has actually sent one; to
 * everybody else it was a statement of fact with nothing to do about it, on the
 * page they opened because they wanted to volunteer. What separates them is
 * whether a registration is open and whether it has been sent.
 */
const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	// The SDK ships CommonJS: the real exports are the properties of `default`,
	// and spreading the namespace itself would hand back no named exports at all.
	const actual = (await importOriginal()) as { default: Record<string, unknown> };

	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (path: string, _params?: unknown, swrKey?: string | null) => ({
			data: swrKey === null ? undefined : { message: reads.get(path) },
			error: null,
			isLoading: false,
			isValidating: false,
			mutate: () => Promise.resolve(undefined),
		}),
		useFrappeAuth: () => ({
			currentUser: "amina@example.com",
			isLoading: false,
			logout: () => Promise.resolve(undefined),
		}),
	};
});

const Profile = (await import("./Profile")).default;

function registration(over: Partial<OpenRegistration> = {}): OpenRegistration {
	return {
		doctype: "VMMS Volunteer Application",
		name: "VAPP-00017",
		path: "volunteer",
		state: "Draft",
		...over,
	};
}

/** The way into the registration, wherever this page offers one. */
function wayIn() {
	return screen.queryByRole("link", { name: /volunteer|registration/i });
}

beforeEach(() => {
	reads.clear();
	reads.set(API.myVolunteer, null);
	reads.set(API.myOpenRegistrations, { volunteer: null, member: null });
});

describe("somebody who has never applied", () => {
	it("is offered the registration rather than told there is nothing here", () => {
		mount(<Profile />);

		expect(screen.getByText("You are not registered as a volunteer")).toBeTruthy();
		expect(wayIn()?.getAttribute("href")).toBe("/join?path=volunteer");
	});

	it("no longer promises a verification of an application nobody has sent", () => {
		mount(<Profile />);

		expect(screen.queryByText(/once your branch has verified your application/)).toBeNull();
	});
});

describe("somebody with a draft they have not sent", () => {
	it("says the answers are saved, and takes them back into the form", () => {
		reads.set(API.myOpenRegistrations, { volunteer: registration({ reviewed: false }) });

		mount(<Profile />);

		expect(screen.getByText("Your volunteer registration is unfinished")).toBeTruthy();
		expect(wayIn()?.getAttribute("href")).toBe("/join?path=volunteer");
	});
});

describe("somebody whose branch sent the application back", () => {
	it("says what was asked for, rather than that the form is unfinished", () => {
		reads.set(API.myOpenRegistrations, {
			volunteer: registration({ reviewed: true, reason: "Send us your first-aid certificate." }),
		});

		mount(<Profile />);

		expect(screen.getByText("Your branch has asked for changes")).toBeTruthy();
		expect(screen.getByText("Send us your first-aid certificate.")).toBeTruthy();
		expect(wayIn()).toBeTruthy();
	});
});

describe("somebody whose application is with the branch", () => {
	it("offers no second application, because the server would refuse it", () => {
		reads.set(API.myOpenRegistrations, {
			volunteer: registration({ state: "In Review", reviewed: true }),
		});

		mount(<Profile />);

		expect(screen.getByText("Your application is with your branch")).toBeTruthy();
		expect(wayIn()).toBeNull();
	});
});

describe("a volunteer's own profile", () => {
	const volunteer = {
		volunteer: "VOL-26-000001",
		red_profile: "RP-1",
		full_name: "Amina Otieno",
		email: "amina@example.com",
		phone: "0700000000",
		gender: "Female",
		date_of_birth: "1990-01-01",
		preferred_language: null,
		profile_photo: null,
		status: "Active",
		joined_on: "2026-11-09",
		exited_on: null,
		geo_node: "GEO-1",
		geo_path: "Nairobi",
		home_geo_node: "GEO-1",
		home_geo_path: "Nairobi",
		emergency_contacts: [],
		issues_card: false,
	};
	const person = {
		red_profile: "RP-1",
		first_name: "Amina",
		last_name: "Otieno",
		full_name: "Amina Otieno",
		email: "amina@example.com",
		phone: "0700000000",
		gender: "Female",
		date_of_birth: "1990-01-01",
		preferred_language: null,
		profile_photo: null,
		country_of_citizenship: "Kenya",
		citizenship_status: null,
		residency_type: "Local",
		home_geo_node: "GEO-1",
		country_of_residence: null,
		residence_address: null,
		identifications: [],
		disability_status: "No",
		disability_needs: null,
		disabilities: [],
		profession: null,
		other_profession: null,
		education: [],
		training: [],
		work_experience: [],
		licences: [],
		driving_licences: [],
		references: [],
		personal_details: {},
	};

	beforeEach(() => {
		reads.set(API.myVolunteer, volunteer);
		reads.set(API.myProfile, person);
		reads.set(API.myMemberships, []);
		reads.set(API.myProfileCompleteness, {
			percent: 67,
			done: 2,
			total: 3,
			items: [
				{ key: "phone", label: "Add your phone number", section: "details", done: true },
				{ key: "gender", label: "Choose your gender", section: "details", done: true },
				{ key: "emergency_contact", label: "Add an emergency contact", section: "emergency", done: false },
			],
		});
	});

	it("shows how complete it is, and lists only what is missing", () => {
		mount(<Profile />, { route: "/profile" });

		expect(screen.getByRole("button", { name: "67% complete" })).toBeTruthy();
		expect(screen.getByRole("button", { name: /Add an emergency contact/ })).toBeTruthy();
		expect(screen.queryByRole("button", { name: /Add your phone number/ })).toBeNull();
	});

	it("opens the one section that fixes a missing item", () => {
		mount(<Profile />, { route: "/profile" });

		fireEvent.click(screen.getByRole("button", { name: /Add an emergency contact/ }));

		expect(screen.getByRole("tab", { name: "Personal" }).getAttribute("aria-selected")).toBe("true");
		// The contact editor is open, and the other sections are not.
		expect(screen.getByLabelText(/Full name/)).toBeTruthy();
		expect(screen.queryByLabelText("First name")).toBeNull();
		expect(screen.getByRole("button", { name: "Edit Your details" })).toBeTruthy();
	});

	it("keeps transfers and certificates under Requests", () => {
		mount(<Profile />, { route: "/profile?tab=requests" });

		expect(screen.getByRole("tab", { name: "Requests" }).getAttribute("aria-selected")).toBe("true");
		expect(screen.queryByText("Placement")).toBeNull();
	});
});
