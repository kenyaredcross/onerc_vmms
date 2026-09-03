import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { mount } from "../test/harness";

/**
 * Where the front door's controls actually lead.
 *
 * **The join buttons used to lead to a page whose only job was to send people
 * somewhere else.** A guest pressing "Become a volunteer" landed on `/join`,
 * which — having no session — could draw nothing but a "Sign in to continue"
 * card offering the same two links again. These lock the bridge out: a guest
 * goes straight to the auth page, on the sign-up panel, carrying where they
 * were going; somebody already signed in keeps the direct route into the
 * wizard, because they have the session the wizard was waiting for.
 */
let currentUser: string | null = null;

vi.mock("frappe-react-sdk", async (importOriginal) => {
	// The SDK ships CommonJS: the real exports hang off `default`, and spreading
	// the namespace would hand back a module with no named exports at all.
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	const { createContext } = await import("react");

	const stable = {
		data: undefined,
		error: null,
		isLoading: false,
		isValidating: false,
		mutate: () => Promise.resolve(undefined),
	};

	return {
		...actual.default,
		default: actual.default,
		FrappeContext: createContext({ call: { get: () => Promise.resolve({ message: null }) } }),
		FrappeProvider: ({ children }: { children: React.ReactNode }) => children,
		useFrappeGetCall: () => stable,
		useFrappeAuth: () => ({
			currentUser,
			isLoading: false,
			logout: () => Promise.resolve(undefined),
		}),
		useFrappeFileUpload: () => ({ upload: () => Promise.resolve({ file_url: "" }), loading: false }),
	};
});

const Landing = (await import("./Landing")).default;

/** Every control on the page that offers to start somebody's journey. */
const JOIN_CONTROLS = ["Join us", "Become a volunteer", "Explore membership", "Join us today"];

const hrefFor = (name: string) =>
	screen.getAllByRole("link", { name: new RegExp(`^${name}`) })[0].getAttribute("href");

describe("a guest is sent to sign up, not to a page that sends them to sign up", () => {
	beforeEach(() => {
		currentUser = null;
	});

	it("points every join control at the same auth page the header signs in with", () => {
		mount(<Landing />);

		for (const name of JOIN_CONTROLS) {
			const href = hrefFor(name);

			expect(href, name).toMatch(/^\/login\?redirect-to=/);
			// The sign-up panel, not the password form: these people have no
			// account yet.
			expect(href, name).toMatch(/#signup$/);
		}
	});

	it("carries which path was pressed through the round trip", () => {
		mount(<Landing />);

		// `redirect-to` is what Frappe stashes against the new account and the
		// verification link honours. Without it somebody who chose "Become a
		// volunteer" comes back to the front page having lost the choice.
		expect(decodeURIComponent(hrefFor("Become a volunteer") ?? "")).toContain(
			"/join?path=volunteer",
		);
		expect(decodeURIComponent(hrefFor("Explore membership") ?? "")).toContain("/join?path=member");
	});
});

describe("somebody already signed in keeps the direct route", () => {
	beforeEach(() => {
		currentUser = "amina@example.com";
	});

	it("opens the wizard rather than an auth page they do not need", () => {
		mount(<Landing />);

		// The header swaps to "Go to dashboard" once signed in, so only the
		// in-page calls to action remain.
		expect(hrefFor("Become a volunteer")).toBe("/join?path=volunteer");
		expect(hrefFor("Explore membership")).toBe("/join?path=member");
		expect(hrefFor("Join us today")).toBe("/join");
	});
});
