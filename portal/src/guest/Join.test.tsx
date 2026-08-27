import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { ApplicationOptions, GeoLevel, GeoNode, RedProfile } from "../portal/types";

/**
 * The registration wizard, as a member of the public walks it.
 *
 * **What these lock down is the shape of the road, not the styling of it.** The
 * screens somebody is asked to walk through, and what is written on them, are
 * the product here — a step that exists to be dismissed is a step that costs
 * every applicant a page — so the list is asserted rather than left to drift.
 *
 * **And that leaving a step saves.** Everything typed used to live in a browser
 * tab between one press of "Save draft" and the next, so a closed laptop took
 * six screens of answers with it.
 */
const reads = new Map<string, unknown>();
const posted: Array<{ path: string; payload: Record<string, unknown> }> = [];

/**
 * A stubbed read is a path *and its arguments*.
 *
 * `geo.browse` is the reason. It is one endpoint asked once per rung — the top
 * of the tree with no parent, then the children of whatever was answered — and
 * a stub keyed on the path alone answers every rung with the same single node.
 * The picker takes a rung with one option rather than drawing it, so that stub
 * makes the chain grow a rung deeper on every render, for ever.
 */
function keyFor(path: string, params?: unknown): string {
	const given = (params ?? {}) as Record<string, unknown>;

	return Object.keys(given).length ? `${path}?${JSON.stringify(given)}` : path;
}

vi.mock("frappe-react-sdk", async (importOriginal) => {
	// The SDK ships CommonJS: the real exports hang off `default`, and spreading
	// the namespace would hand back a module with no named exports at all.
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	const { createContext } = await import("react");

	// `useContext` with no provider mounted returns the context's *default*
	// value, so a context created around the fake call object is how the wizard's
	// writes are captured without a transport.
	const call = {
		post: (path: string, payload: Record<string, unknown>) => {
			posted.push({ path, payload });
			return Promise.resolve({ message: { name: "VAPP-00017" } });
		},
		get: () => Promise.resolve({ message: null }),
		put: () => Promise.resolve({ message: null }),
		delete: () => Promise.resolve({ message: null }),
	};

	const NO_REQUEST = Symbol("no request");
	const answers = new Map<unknown, unknown>();

	const answer = (message: unknown) => {
		if (!answers.has(message)) {
			answers.set(message, {
				data: message === NO_REQUEST ? undefined : { message },
				error: null,
				isLoading: false,
				isValidating: false,
				mutate: () => Promise.resolve(undefined),
			});
		}

		return answers.get(message);
	};

	return {
		...actual.default,
		default: actual.default,
		FrappeContext: createContext({ call }),
		FrappeProvider: ({ children }: { children: React.ReactNode }) => children,
		// One object per answer, not one per render. SWR hands back a stable
		// `data` reference while nothing has changed, and several effects in this
		// wizard are keyed on it — a fresh object every render re-runs them
		// forever, which is a bug in the stub rather than in the screen.
		useFrappeGetCall: (path: string, params?: unknown, swrKey?: string | null) =>
			answer(swrKey === null ? NO_REQUEST : reads.get(keyFor(path, params))),
		useFrappeAuth: () => ({
			currentUser: "amina@example.com",
			isLoading: false,
			logout: () => Promise.resolve(undefined),
		}),
		useFrappeFileUpload: () => ({ upload: () => Promise.resolve({ file_url: "" }), loading: false }),
	};
});

const Join = (await import("./Join")).default;

const BRANCH: GeoNode = {
	name: "GEO-BRANCH",
	label: "Arusha",
	level: "branch",
	level_name: "Branch",
};

const LEVELS: GeoLevel[] = [{ key: "branch", name: "Branch", order: 1, is_lowest: true }];

const OPTIONS: ApplicationOptions = {
	questions: [],
	skills: [],
	languages: [],
	availability: [],
	motivations: [],
	id_types: [{ key: "national-id", label: "National ID", description: null }],
	countries: ["Tanzania", "Kenya"],
	residency_types: ["Local", "Abroad"],
	default_country_of_citizenship: "Tanzania",
};

const PROFILE: Partial<RedProfile> = {
	email: "amina@example.com",
	first_name: "Amina",
	last_name: "Otieno",
	date_of_birth: "1998-04-02",
};

beforeEach(() => {
	reads.clear();
	posted.length = 0;

	reads.set(API.myProfile, PROFILE);
	reads.set(API.myOpenRegistrations, { volunteer: null, member: null });
	reads.set(API.identityOptions, { genders: ["Female", "Male"] });
	reads.set(API.applicationOptions, OPTIONS);
	reads.set(API.volunteerGeoLevels, { levels: ["branch"], unconstrained: false });
	reads.set(API.geoLadder, { levels: LEVELS });
	// One node at the only rung: a choice between one thing is not a choice, so
	// the picker takes it and the branch is answered without anybody clicking.
	reads.set(API.geoBrowse, { nodes: [BRANCH] });
	// And nothing underneath it — this society's ladder ends at the branch.
	reads.set(keyFor(API.geoBrowse, { parent: BRANCH.name }), { nodes: [] });
});

function open() {
	return mount(<Join />, { route: "/join?path=volunteer" });
}

/**
 * Wait for the first screen to be drawn.
 *
 * By its heading, because "About you" is also the name of the rung in the rail
 * beside it — the same words twice on purpose, and only one of them is the page.
 */
function onTheIdentityStep() {
	return screen.findByRole("heading", { name: "About you" });
}

/** Press Continue, and let the autosave it triggers settle. */
async function goOn() {
	await act(async () => {
		fireEvent.click(screen.getByRole("button", { name: "Continue" }));
	});
}

describe("the road a volunteer walks", () => {
	it("asks where they would volunteer, not where they would serve", async () => {
		open();

		expect(await screen.findByText("Where you'd volunteer")).toBeTruthy();
		expect(screen.queryByText("Where you'd serve")).toBeNull();
	});

	it("has no step of its own for citizenship, and never asks where they live", async () => {
		open();

		await onTheIdentityStep();
		expect(screen.queryByText("Citizenship")).toBeNull();
		expect(screen.queryByText("Where you live")).toBeNull();
		expect(screen.queryByText("Citizenship and where you live")).toBeNull();
	});

	it("asks nationality on the page about the person", async () => {
		open();

		await onTheIdentityStep();
		expect(screen.getByText(/are you a citizen of/i)).toBeTruthy();
	});

	it("does not explain to somebody what their own profile is", async () => {
		open();

		await onTheIdentityStep();
		expect(screen.queryByText(/These are the details the Society holds for you/)).toBeNull();
	});
});

describe("leaving a step", () => {
	/**
	 * Walk as far as the first step that *can* be saved.
	 *
	 * A draft is a person and a branch, so nothing is written while the branch
	 * is still unanswered — leaving the identity screen saves nothing, and
	 * leaving the one after it saves everything answered so far.
	 */
	async function reachTheFirstSavableStep() {
		open();
		await onTheIdentityStep();
		await goOn();
	}

	it("writes nothing until there is enough answered to be a draft", async () => {
		await reachTheFirstSavableStep();

		expect(posted).toEqual([]);
	});

	it("saves the draft without being asked to", async () => {
		await reachTheFirstSavableStep();
		await goOn();

		await waitFor(() => expect(posted.length).toBe(1));
		expect(posted[0].path).toBe(API.saveMyVolunteerDraft);
		expect(posted[0].payload.geo_node).toBe(BRANCH.name);
	});

	it("says so briefly, and does not read a document reference back", async () => {
		await reachTheFirstSavableStep();
		await goOn();

		expect(await screen.findByText("Draft saved")).toBeTruthy();
		expect(screen.queryByText(/VAPP-00017/)).toBeNull();
		expect(screen.queryByText(/sign out and continue later/)).toBeNull();
	});

	it("infers where they live from where they would volunteer", async () => {
		await reachTheFirstSavableStep();
		await goOn();

		await waitFor(() => expect(posted.length).toBe(1));
		expect(posted[0].payload.residency_type).toBe("Local");
		expect(posted[0].payload.home_geo_node).toBe(BRANCH.name);
	});

	it("leaves a recorded residence abroad alone rather than rewriting it", async () => {
		reads.set(API.myProfile, {
			...PROFILE,
			residency_type: "Abroad",
			country_of_residence: "Kenya",
			residence_address: "12 Kimathi Street, Nairobi",
		});

		await reachTheFirstSavableStep();
		await goOn();

		await waitFor(() => expect(posted.length).toBe(1));
		expect(posted[0].payload).not.toHaveProperty("residency_type");
		expect(posted[0].payload).not.toHaveProperty("home_geo_node");
	});

	it("leaves a recorded home area alone, even applying to another branch", async () => {
		reads.set(API.myProfile, {
			...PROFILE,
			residency_type: "Local",
			home_geo_node: "GEO-ELSEWHERE",
		});
		reads.set(keyFor(API.geoChain, { node: "GEO-ELSEWHERE" }), { chain: [] });

		await reachTheFirstSavableStep();
		await goOn();

		await waitFor(() => expect(posted.length).toBe(1));
		expect(posted[0].payload.home_geo_node).toBe("GEO-ELSEWHERE");
	});
});
