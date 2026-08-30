import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { OpenRegistration } from "./types";

/**
 * The panel that tells somebody where their own registration stands.
 *
 * **"Draft" means two opposite things and this screen has to pick one.** A
 * registration nobody has submitted is a Draft; so is one an approver sent back
 * for more information. This panel read the state alone and chose the second
 * every time, so a person who had saved half a form and come back was told
 * "your application needs something from you — your branch has asked for
 * something", about an application no branch had ever seen. `reviewed` is the
 * server's answer to which one it is.
 *
 * **And in both cases there has to be a way back in.** The panel was the only
 * thing on the page that mentioned the application, and it named a document
 * reference and offered no link, so the form somebody was halfway through was
 * unreachable from the screen telling them about it. The link is now the panel's
 * whole answer to "what do I do next", and the reference is gone: a naming series
 * is how the desk finds the row, not how an applicant thinks about their own
 * application.
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

const Dashboard = (await import("./Dashboard")).default;

function registration(over: Partial<OpenRegistration> = {}): OpenRegistration {
	return {
		doctype: "VMMS Volunteer Application",
		name: "VAPP-00017",
		path: "volunteer",
		state: "Draft",
		...over,
	};
}

beforeEach(() => {
	reads.clear();
});

describe("a draft nobody has sent yet", () => {
	beforeEach(() => {
		reads.set(API.myOpenRegistrations, { volunteer: registration({ reviewed: false }) });
	});

	it("says the application is unfinished, not that the branch is waiting", () => {
		mount(<Dashboard />);

		expect(screen.getByText("Your application is not finished")).toBeTruthy();
		expect(screen.queryByText("Your application needs something from you")).toBeNull();
	});

	it("offers the way back into the form, on the road it was started on", () => {
		mount(<Dashboard />);

		const link = screen.getByRole("link", { name: /continue application/i });
		expect(link.getAttribute("href")).toBe("/join?path=volunteer");
	});

	it("does not read the document name back to the applicant", () => {
		mount(<Dashboard />);

		expect(screen.queryByText(/VAPP-00017/)).toBeNull();
		expect(screen.queryByText(/your reference is/i)).toBeNull();
	});
});

describe("a draft an approver sent back", () => {
	beforeEach(() => {
		reads.set(API.myOpenRegistrations, {
			volunteer: registration({
				reviewed: true,
				reason: "Send us your first-aid certificate.",
			}),
		});
	});

	it("says the branch has asked for something, and shows what", () => {
		mount(<Dashboard />);

		expect(screen.getByText("Your application needs something from you")).toBeTruthy();
		expect(screen.getByText("Send us your first-aid certificate.")).toBeTruthy();
	});

	it("still offers the way back in", () => {
		mount(<Dashboard />);

		expect(
			screen.getByRole("link", { name: /continue application/i }).getAttribute("href"),
		).toBe("/join?path=volunteer");
	});
});

describe("a registration that is with the branch", () => {
	it("offers no way to edit it, because there is nothing to edit", () => {
		reads.set(API.myOpenRegistrations, {
			volunteer: registration({ state: "In Review", reviewed: true }),
		});

		mount(<Dashboard />);

		expect(screen.getByText("Your application is under review")).toBeTruthy();
		expect(screen.queryByRole("link", { name: /continue application/i })).toBeNull();
	});
});
