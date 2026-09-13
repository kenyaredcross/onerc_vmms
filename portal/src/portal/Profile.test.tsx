import { screen } from "@testing-library/react";
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

		expect(screen.getByText("Your application needs something from you")).toBeTruthy();
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
