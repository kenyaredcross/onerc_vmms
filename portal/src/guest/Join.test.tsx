import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type {
	ApplicationOptions,
	Declaration,
	GeoLevel,
	GeoNode,
	RedProfile,
} from "../portal/types";

/**
 * The registration wizard, as a member of the public walks it.
 *
 * **What these lock down is the shape of the road, not the styling of it.** The
 * screens somebody is asked to walk through, and what is written on them, are
 * the product here — a step that exists to be dismissed is a step that costs
 * every applicant a page — so the list is asserted rather than left to drift.
 *
 * **And that leaving a step saves, quietly.** Everything typed used to live in a
 * browser tab between one press of "Save draft" and the next, so a closed laptop
 * took six screens of answers with it. It happens on every step change now, and
 * says nothing when it does: an applicant did not ask for the save and is not
 * waiting to hear about it.
 */
const reads = new Map<string, unknown>();
const posted: Array<{ path: string; payload: Record<string, unknown> }> = [];
let currentUser: string | null = "amina@example.com";

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
			currentUser,
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
	id_types: [
		{
			key: "national-id",
			label: "National ID",
			description: null,
			is_required: false,
			requires_attachment: false,
			minimum_age: null,
		},
	],
	countries: ["Tanzania", "Kenya"],
	residency_types: ["Local", "Abroad"],
	citizenship_statuses: ["Citizen", "Non-citizen", "Refugee", "Migrant", "Other"],
	default_country_of_citizenship: "Tanzania",
	// Empty by default, so the suites about the older road walk exactly the road
	// they always walked. The consent tests below supply their own.
	declarations: [],
	minor_age: null,
	guardian_verification_methods: [],
};

/** The four a society actually ships, trimmed to two for a readable assertion. */
const DECLARATIONS: Declaration[] = [
	{
		name: "vmms-volunteer-privacy",
		title: "How we will use your information",
		version: "1",
		source: "Text",
		body: "<p>We record what you tell us so we can consider your application.</p>",
		external_url: null,
		declaration_version: "vmms-volunteer-privacy-1",
		is_required: true,
	},
	{
		name: "vmms-volunteer-accuracy",
		title: "Your declaration",
		version: "3",
		source: "Text",
		body: "<p>Everything here is true to the best of your knowledge.</p>",
		external_url: null,
		declaration_version: "vmms-volunteer-accuracy-3",
		is_required: true,
	},
];

/** The other way a society publishes a policy: on its own website. */
const LINKED_DECLARATION: Declaration[] = [
	{
		name: "vmms-volunteer-privacy",
		title: "Our privacy notice",
		version: "4",
		source: "Link",
		body: null,
		external_url: "https://example.redcross.org/privacy",
		declaration_version: "vmms-volunteer-privacy-4",
		is_required: true,
	},
];

const PROFILE: Partial<RedProfile> = {
	email: "amina@example.com",
	first_name: "Amina",
	last_name: "Otieno",
	date_of_birth: "1998-04-02",
	// Answered, so every walk below gets off the first step. The requirement
	// itself has its own suite — see "the disability question" — and this is a
	// person who has already been asked rather than a way around the rule.
	disability_status: "Prefer not to say",
};

beforeEach(() => {
	reads.clear();
	posted.length = 0;
	currentUser = "amina@example.com";

	reads.set(API.myProfile, PROFILE);
	reads.set(API.myOpenRegistrations, { volunteer: null, member: null });
	reads.set(API.identityOptions, {
		genders: ["Female", "Male"],
		// Core's `Disability` register, two rows deep enough to tell a filtered
		// pick from a lucky first hit. `description` is the disability's type,
		// which is what the picker shows underneath each row.
		disabilities: [
			{ key: "Deafness", label: "Deafness", description: "Hearing" },
			{ key: "Low vision", label: "Low vision", description: "Vision" },
		],
		// The four registers the background step draws. The two name-only ones
		// come back as bare strings because the doctypes behind them have no
		// fields — the docname is the value.
		professions: ["Professional", "Student"],
		licence_types: ["Nursing"],
		education_levels: [
			{ key: "secondary", label: "Secondary", description: null },
			{ key: "diploma", label: "Diploma", description: null },
		],
		driving_licence_classes: [
			{ key: "light_vehicle", label: "Light vehicle", description: "Cars and small vans." },
		],
	});
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

function openAsGuest(route: string) {
	currentUser = "Guest";
	window.history.replaceState({}, "", route);
	return mount(<Join />, { route });
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

describe("the guest registration hand-off", () => {
	it("keeps a declared volunteer path visible through authentication", () => {
		openAsGuest("/join?path=volunteer");

		expect(screen.getByText("Volunteer registration")).toBeTruthy();
		expect(screen.getByText("You chose to register as a volunteer.", { exact: false })).toBeTruthy();
		expect(screen.getByText("Account").closest("li")?.getAttribute("aria-current")).toBe("step");
		expect(screen.getByRole("link", { name: "Sign in" }).getAttribute("href")).toBe(
			"/login?redirect-to=%2Fjoin%3Fpath%3Dvolunteer",
		);
		expect(screen.getByRole("link", { name: "Create an account" }).getAttribute("href")).toBe(
			"/login?redirect-to=%2Fjoin%3Fpath%3Dvolunteer#signup",
		);
	});

	it("names a declared member path instead of showing a generic bridge", () => {
		openAsGuest("/join?path=member&type=annual");

		expect(screen.getByText("Member registration")).toBeTruthy();
		expect(screen.getByText("You chose to register as a member.", { exact: false })).toBeTruthy();
		expect(screen.getByRole("link", { name: "Sign in" }).getAttribute("href")).toBe(
			"/login?redirect-to=%2Fjoin%3Fpath%3Dmember%26type%3Dannual",
		);
	});

	it("asks for a path before handing a bare entry to authentication", async () => {
		openAsGuest("/join");

		expect(screen.getByRole("heading", { name: "How would you like to join?" })).toBeTruthy();
		expect(screen.queryByRole("heading", { name: "Sign in to continue" })).toBeNull();

		fireEvent.click(screen.getByRole("radio", { name: /Volunteer/ }));

		expect(await screen.findByText("Volunteer registration")).toBeTruthy();
		expect(screen.getByRole("heading", { name: "Sign in to continue" })).toBeTruthy();
	});
});

describe("the road a volunteer walks", () => {
	it("asks where they would volunteer, not where they would serve", async () => {
		open();

		expect(await screen.findByText("Where you'd volunteer")).toBeTruthy();
		expect(screen.queryByText("Where you'd serve")).toBeNull();
	});

	/**
	 * A step is a heading and the controls under it, and nothing in between.
	 *
	 * Every screen used to carry a line of explanation beneath its title, and
	 * every one of them described the controls already on the page — "Answer each
	 * field in turn, the one below narrows to what sits inside your answer" over
	 * three selects that do exactly that.
	 */
	it("puts no line of explanation under a step's heading", async () => {
		open();

		await onTheIdentityStep();
		await goOn();

		expect(await screen.findByRole("heading", { name: "Where would you volunteer?" })).toBeTruthy();
		expect(screen.queryByText(/narrows to what sits inside your answer/)).toBeNull();
		expect(screen.queryByText(/reviewed by the people responsible/)).toBeNull();
		expect(screen.queryByText("The branch or area you want to volunteer with.")).toBeNull();
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

	it("says nothing about having done it", async () => {
		await reachTheFirstSavableStep();
		await goOn();

		await waitFor(() => expect(posted.length).toBe(1));
		expect(screen.queryByText("Draft saved")).toBeNull();
	});

	it("never shows the applicant a document reference", async () => {
		await reachTheFirstSavableStep();
		await goOn();

		await waitFor(() => expect(posted.length).toBe(1));
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


/**
 * The two screens Phase 1 added, and the one it deliberately does not draw.
 *
 * The consent step is built from records, so what is asserted is the *shape* — a
 * box per declaration, the society's own words on the page, the version beside
 * them because that is what gets stored — and never wording this file could have
 * written down itself.
 */

/**
 * A profile carrying an identification, so the walk can get past that step.
 *
 * The suites above stop two screens in and never need one. Anything reaching the
 * later steps does, because `complete("identification")` wants a type and a
 * number and the wizard prefills both from the profile.
 */
const IDENTIFIED: Partial<RedProfile> = {
	...PROFILE,
	identifications: [
		{
			id_type: "national-id",
			id_number: "TZ-12345678",
			attachment: null,
			is_primary: true,
		},
	],
};

/** A profile whose date of birth makes them a child under any age of majority. */
const YOUNG: Partial<RedProfile> = { ...IDENTIFIED, date_of_birth: "2014-01-01" };

/** Walk forward until a named step is drawn, pressing Continue as it goes. */
async function walkTo(heading: string) {
	open();
	await onTheIdentityStep();

	for (let press = 0; press < 8; press += 1) {
		if (screen.queryByRole("heading", { name: heading })) return;
		await goOn();
	}

	await screen.findByRole("heading", { name: heading });
}

describe("what a volunteer agrees to", () => {
	beforeEach(() => {
		reads.set(API.myProfile, IDENTIFIED);
	});

	it("draws no consent step for a society that has written no declarations", async () => {
		open();
		await onTheIdentityStep();

		expect(screen.queryByText("What you agree to")).toBeNull();
	});

	it("gives each declaration its own box, its own words and its own version", async () => {
		reads.set(API.applicationOptions, { ...OPTIONS, declarations: DECLARATIONS });

		await walkTo("Before you send this");

		expect(screen.getByText("How we will use your information")).toBeTruthy();
		expect(screen.getByText("Your declaration")).toBeTruthy();
		expect(
			screen.getByText("We record what you tell us so we can consider your application."),
		).toBeTruthy();
		expect(screen.getByText("Version 1")).toBeTruthy();
		expect(screen.getByText("Version 3")).toBeTruthy();
		expect(screen.getAllByRole("checkbox", { name: /I have read this and I agree/ })).toHaveLength(
			2,
		);
	});

	it("will not go on until every required box is ticked", async () => {
		reads.set(API.applicationOptions, { ...OPTIONS, declarations: DECLARATIONS });

		await walkTo("Before you send this");

		const boxes = screen.getAllByRole("checkbox", { name: /I have read this and I agree/ });

		expect(screen.getByRole("button", { name: "Continue" }).hasAttribute("disabled")).toBe(true);

		fireEvent.click(boxes[0]);
		expect(screen.getByRole("button", { name: "Continue" }).hasAttribute("disabled")).toBe(true);

		fireEvent.click(boxes[1]);
		expect(screen.getByRole("button", { name: "Continue" }).hasAttribute("disabled")).toBe(false);
	});

	it("links out to a policy the society publishes on its own website", async () => {
		// A national society whose legal team owns the privacy page will not keep
		// a second copy here. The form sends people to the page rather than
		// reprinting words it does not have.
		reads.set(API.applicationOptions, { ...OPTIONS, declarations: LINKED_DECLARATION });

		await walkTo("Before you send this");

		const link = screen.getByRole("link", { name: /Read our privacy notice/ });

		expect(link.getAttribute("href")).toBe("https://example.redcross.org/privacy");
		expect(link.getAttribute("target")).toBe("_blank");
		expect(screen.getByText("Version 4")).toBeTruthy();
		expect(
			screen.getAllByRole("checkbox", { name: /I have read this and I agree/ }),
		).toHaveLength(1);
	});

	it("sends the keys of what was ticked, not the text of it", async () => {
		reads.set(API.applicationOptions, { ...OPTIONS, declarations: DECLARATIONS });

		await walkTo("Before you send this");

		for (const box of screen.getAllByRole("checkbox", { name: /I have read this and I agree/ })) {
			fireEvent.click(box);
		}

		await goOn();

		await waitFor(() => expect(posted.length).toBeGreaterThan(0));
		expect(posted[posted.length - 1].payload.declarations_accepted).toEqual([
			"vmms-volunteer-privacy",
			"vmms-volunteer-accuracy",
		]);
	});
});

describe("who to call, and who says a minor may volunteer", () => {
	beforeEach(() => {
		reads.set(API.myProfile, IDENTIFIED);
	});

	it("asks for somebody to call, and lets the step be walked past", async () => {
		await walkTo("If something happens");

		expect(screen.getByLabelText(/^Their name/)).toBeTruthy();
		// A condition of approval, not of submission: the branch can chase it.
		expect(screen.getByRole("button", { name: "Continue" }).hasAttribute("disabled")).toBe(false);
	});

	it("refuses a contact that is missing any of the three the record insists on", async () => {
		await walkTo("If something happens");

		fireEvent.change(screen.getByLabelText(/^Their name/), { target: { value: "Mercy" } });

		expect(screen.getByRole("button", { name: "Continue" }).hasAttribute("disabled")).toBe(true);

		fireEvent.change(screen.getByLabelText(/^Phone number/), {
			target: { value: "+255700000001" },
		});

		// A name and a number are not a contact. `VMMS Emergency Contact` marks
		// the relationship mandatory too, and a row without it is refused by the
		// framework on the next autosave — so the step holds here rather than
		// letting somebody meet that refusal.
		expect(screen.getByRole("button", { name: "Continue" }).hasAttribute("disabled")).toBe(true);

		fireEvent.change(screen.getByLabelText(/^How you know them/), { target: { value: "Sister" } });

		expect(screen.getByRole("button", { name: "Continue" }).hasAttribute("disabled")).toBe(false);
	});

	it("sends nothing at all when the contact was left blank", async () => {
		await walkTo("If something happens");
		await goOn();

		await waitFor(() => expect(posted.length).toBeGreaterThan(0));
		expect(posted[posted.length - 1].payload.emergency_contacts).toEqual([]);
	});

	it("says nothing about a guardian for a society with no age of majority", async () => {
		reads.set(API.myProfile, YOUNG);

		await walkTo("If something happens");

		expect(screen.queryByText("A parent or guardian")).toBeNull();
	});

	it("asks for a guardian once the date of birth makes them a minor", async () => {
		reads.set(API.applicationOptions, { ...OPTIONS, minor_age: 18 });
		reads.set(API.myProfile, YOUNG);

		await walkTo("If something happens");

		expect(screen.getByText("A parent or guardian")).toBeTruthy();
		expect(screen.getByText(/Because you are under 18/)).toBeTruthy();
	});

	it("does not ask an adult for one", async () => {
		reads.set(API.applicationOptions, { ...OPTIONS, minor_age: 18 });

		await walkTo("If something happens");

		expect(screen.queryByText("A parent or guardian")).toBeNull();
	});

	it("copies the emergency contact across without merging the two records", async () => {
		reads.set(API.applicationOptions, { ...OPTIONS, minor_age: 18 });
		reads.set(API.myProfile, YOUNG);

		await walkTo("If something happens");

		fireEvent.change(screen.getByLabelText(/^Their name/), { target: { value: "Grace Otieno" } });
		fireEvent.change(screen.getByLabelText(/^How you know them/), { target: { value: "Mother" } });
		fireEvent.change(screen.getByLabelText(/^Phone number/), {
			target: { value: "+255700000002" },
		});

		fireEvent.click(screen.getByRole("button", { name: "Same as the person above" }));

		expect(
			(screen.getByLabelText(/^Parent or guardian's name/) as HTMLInputElement).value,
		).toBe("Grace Otieno");
		expect((screen.getByLabelText(/^How they are related to you/) as HTMLInputElement).value).toBe(
			"Mother",
		);

		await goOn();

		await waitFor(() => expect(posted.length).toBeGreaterThan(0));
		const payload = posted[posted.length - 1].payload as Record<string, unknown[]>;

		// Two records carrying the same person, never one record doing both jobs.
		expect(payload.emergency_contacts).toHaveLength(1);
		expect(payload.guardian_consents).toHaveLength(1);
	});

	it("never sends the reviewer's verification, whatever the form holds", async () => {
		reads.set(API.applicationOptions, { ...OPTIONS, minor_age: 18 });
		reads.set(API.myProfile, YOUNG);

		await walkTo("If something happens");

		fireEvent.change(screen.getByLabelText(/^Their name/), { target: { value: "Grace" } });
		fireEvent.change(screen.getByLabelText(/^How you know them/), { target: { value: "Mother" } });
		fireEvent.change(screen.getByLabelText(/^Phone number/), {
			target: { value: "+255700000002" },
		});
		fireEvent.click(screen.getByRole("button", { name: "Same as the person above" }));

		await goOn();

		await waitFor(() => expect(posted.length).toBeGreaterThan(0));
		const payload = posted[posted.length - 1].payload as Record<
			string,
			Array<Record<string, unknown>>
		>;

		expect(payload.guardian_consents[0]).not.toHaveProperty("is_verified");
		expect(payload.guardian_consents[0]).not.toHaveProperty("verified_by");
	});

	it("sends no guardian at all for an adult, whatever was typed", async () => {
		reads.set(API.applicationOptions, { ...OPTIONS, minor_age: 18 });

		await walkTo("If something happens");
		await goOn();

		await waitFor(() => expect(posted.length).toBeGreaterThan(0));
		expect(posted[posted.length - 1].payload.guardian_consents).toEqual([]);
	});
});

/**
 * More than one of the things a person actually has more than one of.
 *
 * `Red Profile` has always held a *table* of identifications and `VMMS
 * Emergency Contact` has always been a table, but this form asked for exactly
 * one of each — so a society that marks two document types required could not
 * be satisfied by the form that asks, and a household with two numbers worth
 * holding lost one of them at the door.
 */
describe("more than one of a thing", () => {
	beforeEach(() => {
		reads.set(API.myProfile, IDENTIFIED);
		reads.set(API.applicationOptions, {
			...OPTIONS,
			id_types: [
				...OPTIONS.id_types,
				{
					key: "passport",
					label: "Passport",
					description: null,
					is_required: false,
					requires_attachment: false,
					minimum_age: null,
				},
			],
		});
	});

	it("sends every identification, not only the first", async () => {
		await walkTo("Identification");

		fireEvent.click(screen.getByRole("button", { name: "Add another document" }));

		fireEvent.change(screen.getByLabelText("Another ID type"), {
			target: { value: "passport" },
		});
		// A regex, not the exact string: `Field` renders the required marker
		// inside the label, so the first row's accessible name carries a
		// trailing asterisk and the second's does not.
		const numbers = screen.getAllByLabelText(/^ID number/);
		fireEvent.change(numbers[1], { target: { value: "TZ-PASS-99" } });

		await goOn();

		await waitFor(() => expect(posted.length).toBeGreaterThan(0));
		expect(posted[posted.length - 1].payload.identifications).toEqual([
			{ id_type: "national-id", id_number: "TZ-12345678" },
			{ id_type: "passport", id_number: "TZ-PASS-99" },
		]);
	});

	it("does not offer a kind of document that is already listed", async () => {
		await walkTo("Identification");

		fireEvent.click(screen.getByRole("button", { name: "Add another document" }));

		const second = screen.getByLabelText("Another ID type") as HTMLSelectElement;
		const offered = Array.from(second.options).map((option) => option.value);

		expect(offered).toContain("passport");
		expect(offered).not.toContain("national-id");
	});

	it("sends every emergency contact somebody filled in", async () => {
		await walkTo("If something happens");

		fireEvent.change(screen.getByLabelText(/^Their name/), { target: { value: "Grace" } });
		fireEvent.change(screen.getByLabelText(/^How you know them/), { target: { value: "Mother" } });
		fireEvent.change(screen.getByLabelText(/^Phone number/), {
			target: { value: "+255700000002" },
		});

		fireEvent.click(screen.getByRole("button", { name: "Add another contact" }));

		fireEvent.change(screen.getAllByLabelText(/^Their name/)[1], { target: { value: "Juma" } });
		fireEvent.change(screen.getAllByLabelText(/^How you know them/)[1], {
			target: { value: "Brother" },
		});
		fireEvent.change(screen.getAllByLabelText(/^Phone number/)[1], {
			target: { value: "+255700000003" },
		});

		await goOn();

		await waitFor(() => expect(posted.length).toBeGreaterThan(0));
		const contacts = posted[posted.length - 1].payload.emergency_contacts as Array<
			Record<string, unknown>
		>;

		expect(contacts.map((row) => row.contact_name)).toEqual(["Grace", "Juma"]);
	});

	it("drops a spare blank contact rather than storing a nameless one", async () => {
		await walkTo("If something happens");

		fireEvent.change(screen.getByLabelText(/^Their name/), { target: { value: "Grace" } });
		fireEvent.change(screen.getByLabelText(/^How you know them/), { target: { value: "Mother" } });
		fireEvent.change(screen.getByLabelText(/^Phone number/), {
			target: { value: "+255700000002" },
		});
		fireEvent.click(screen.getByRole("button", { name: "Add another contact" }));

		await goOn();

		await waitFor(() => expect(posted.length).toBeGreaterThan(0));
		expect(
			(posted[posted.length - 1].payload.emergency_contacts as unknown[]).length,
		).toBe(1);
	});
});

/**
 * The disability question, which is required to be *answered* and not to be
 * answered a particular way.
 *
 * "Prefer not to say" satisfies it. That is the whole design: a society running
 * an inclusive programme has to know what adjustments to offer, and the way to
 * ask without coercing anybody is to make answering required and disclosure
 * optional.
 */
describe("the disability question", () => {
	beforeEach(() => {
		reads.set(API.myProfile, { ...PROFILE, disability_status: null });
	});

	it("will not leave the first step until it has an answer", async () => {
		open();
		await onTheIdentityStep();

		await goOn();

		// Still here: the step did not advance.
		expect(screen.getByRole("heading", { name: "About you" })).toBeTruthy();

		fireEvent.change(screen.getByLabelText(/^Do you have a disability\?/), {
			target: { value: "Prefer not to say" },
		});

		await goOn();

		expect(screen.queryByRole("heading", { name: "About you" })).toBeNull();
	});

	it("asks what would help only when somebody has said there is something", async () => {
		open();
		await onTheIdentityStep();

		expect(screen.queryByLabelText("Anything that would help")).toBeNull();

		fireEvent.change(screen.getByLabelText(/^Do you have a disability\?/), {
			target: { value: "Yes" },
		});

		expect(screen.getByLabelText("Anything that would help")).toBeTruthy();
	});

	it("sends the answer to the profile, not to the application", async () => {
		reads.set(API.myProfile, { ...IDENTIFIED, disability_status: null });

		open();
		await onTheIdentityStep();

		fireEvent.change(screen.getByLabelText(/^Do you have a disability\?/), {
			target: { value: "Yes" },
		});
		fireEvent.change(screen.getByLabelText("Anything that would help"), {
			target: { value: "A seat at briefings" },
		});

		// Nothing is written until there is enough answered to be a draft, which
		// is a name *and a branch* — so this walks past the placement step rather
		// than asserting on the step that asked the question.
		await goOn();
		await goOn();

		await waitFor(() => expect(posted.length).toBeGreaterThan(0));
		expect(posted[posted.length - 1].payload.disability_status).toBe("Yes");
		expect(posted[posted.length - 1].payload.disability_needs).toBe("A seat at briefings");
	});

	it("is not asked of a member, who is never sent anywhere", async () => {
		mount(<Join />, { route: "/join?path=member&type=annual" });
		await onTheIdentityStep();

		expect(screen.queryByLabelText(/^Do you have a disability\?/)).toBeNull();
	});
});

/**
 * Naming which one, from the society's own register.
 *
 * The question above stays the required one and stays the only thing that can
 * hold "Prefer not to say". This is the optional second disclosure underneath
 * it, and every test here is about that asymmetry: it appears only on "Yes",
 * nothing forces an answer, and changing the answer above takes it back.
 */
/**
 * The optional step: what somebody has already done.
 *
 * Seven person facts that used to be one free-text box. The thing every test
 * here is really guarding is that the step stayed *optional*: it sits between
 * two required steps, it has six tables on it, and the easy mistake would be for
 * one of them to start gating the wizard.
 */
describe("what you have already done", () => {
	beforeEach(() => {
		reads.set(API.myProfile, IDENTIFIED);
	});

	const onTheStep = () => walkTo("What you have already done");

	it("is drawn for a volunteer, between what they can do and who to call", async () => {
		await onTheStep();

		expect(screen.getByRole("heading", { name: "What you have already done" })).toBeTruthy();
	});

	it("is not drawn for a member, who is taking out a subscription", async () => {
		mount(<Join />, { route: "/join?path=member&type=annual" });
		await onTheIdentityStep();

		// Walked to the end rather than a fixed number of presses: the last step
		// says Submit, not Continue, and pressing past it would be a registration.
		while (screen.queryByRole("button", { name: "Continue" })) {
			expect(screen.queryByRole("heading", { name: "What you have already done" })).toBeNull();
			await goOn();
		}
	});

	it("lets somebody straight past it without filling in anything", async () => {
		await onTheStep();
		await goOn();

		// Gone, on the first press, with six empty tables behind it.
		expect(screen.queryByRole("heading", { name: "What you have already done" })).toBeNull();
	});

	it("will not stack a second blank row on an empty one", async () => {
		await onTheStep();

		const add = screen.getByRole("button", { name: "Add somewhere you studied" });
		fireEvent.click(add);

		// One row drawn, and the button that drew it now refuses until it says
		// something — otherwise a mis-click leaves blanks the server drops.
		expect(screen.getByLabelText(/^School or institution/)).toBeTruthy();
		expect((add as HTMLButtonElement).disabled).toBe(true);

		fireEvent.change(screen.getByLabelText(/^School or institution/), {
			target: { value: "Kibera Secondary" },
		});

		expect((add as HTMLButtonElement).disabled).toBe(false);
	});

	it("sends what was filled in, and nothing that was not", async () => {
		await onTheStep();

		fireEvent.click(screen.getByRole("button", { name: "Add somewhere you studied" }));
		fireEvent.change(screen.getByLabelText(/^School or institution/), {
			target: { value: "Kibera Secondary" },
		});
		fireEvent.change(screen.getByLabelText(/^Qualification/), {
			target: { value: "KCSE" },
		});

		fireEvent.click(screen.getByRole("button", { name: "Add a referee" }));
		fireEvent.change(screen.getByLabelText(/^Their name/), {
			target: { value: "Grace Wanjiru" },
		});

		await goOn();
		await waitFor(() => expect(posted.length).toBeGreaterThan(0));

		const background = posted[posted.length - 1].payload.background as Record<string, unknown[]>;

		expect(background.education).toEqual([
			expect.objectContaining({ institution: "Kibera Secondary", qualification: "KCSE" }),
		]);
		expect(background.references).toEqual([
			expect.objectContaining({ reference_name: "Grace Wanjiru" }),
		]);
		// Present and empty, not absent. The server reads an absent key as "leave
		// that table alone", so a form that omitted the untouched ones could never
		// empty them.
		expect(background.training).toEqual([]);
		expect(background.licences).toEqual([]);
	});

	it("opens with what the profile already holds", async () => {
		reads.set(API.myProfile, {
			...IDENTIFIED,
			profession: "Student",
			education: [
				{
					institution: "Kenyatta University",
					level: "undergraduate",
					qualification: "BSc Nursing",
					started_in: 2016,
					finished_in: 2020,
					is_ongoing: false,
					attachment: null,
				},
			],
		});

		await onTheStep();

		expect((screen.getByLabelText(/^School or institution/) as HTMLInputElement).value).toBe(
			"Kenyatta University",
		);
		expect((screen.getByLabelText(/^Profession/) as HTMLSelectElement).value).toBe("Student");
	});

	/**
	 * The two contradictions the step resolves rather than stores. Somebody who
	 * says they are still studying cannot also have finished in 2020, and the
	 * answer they just pressed is the one they mean.
	 */
	it("clears the finish year when somebody says they are still studying", async () => {
		await onTheStep();

		fireEvent.click(screen.getByRole("button", { name: "Add somewhere you studied" }));
		fireEvent.change(screen.getByLabelText(/^School or institution/), {
			target: { value: "Kenyatta University" },
		});
		fireEvent.change(screen.getByLabelText(/^Finished/), { target: { value: "2020" } });
		fireEvent.click(screen.getByLabelText("I am still studying here"));

		expect((screen.getByLabelText(/^Finished/) as HTMLInputElement).value).toBe("");
		expect((screen.getByLabelText(/^Finished/) as HTMLInputElement).disabled).toBe(true);
	});
});

describe("which disability, from the register", () => {
	const NAMED = /^Which ones, if you would like to say/;

	beforeEach(() => {
		reads.set(API.myProfile, { ...IDENTIFIED, disability_status: null });
	});

	/** The picker itself. By role, because the control carries both a visible
	    label and an `aria-label` and a text query matches each of them. */
	const picker = () => screen.getByRole("combobox", { name: NAMED });

	/** Open the picker and tick one row by its label. */
	const nameOne = (label: string) => {
		fireEvent.focus(picker());
		fireEvent.click(screen.getByRole("option", { name: new RegExp(label) }));
	};

	const disclose = () =>
		fireEvent.change(screen.getByLabelText(/^Do you have a disability\?/), {
			target: { value: "Yes" },
		});

	it("is drawn only once somebody has said there is something", async () => {
		open();
		await onTheIdentityStep();

		expect(screen.queryByRole("combobox", { name: NAMED })).toBeNull();

		disclose();

		expect(picker()).toBeTruthy();
	});

	it("does not hold the step up, because naming one was never required", async () => {
		open();
		await onTheIdentityStep();

		disclose();
		await goOn();

		// Past it, with nothing named. Answering the question was the rule; this
		// is the disclosure the rule deliberately does not demand.
		expect(screen.queryByRole("heading", { name: "About you" })).toBeNull();
	});

	it("sends the register's keys to the profile, beside the answer itself", async () => {
		open();
		await onTheIdentityStep();

		disclose();
		nameOne("Deafness");

		await goOn();
		await goOn();

		await waitFor(() => expect(posted.length).toBeGreaterThan(0));

		const payload = posted[posted.length - 1].payload;
		expect(payload.disability_status).toBe("Yes");
		expect(payload.disabilities).toEqual(["Deafness"]);
	});

	/**
	 * The one that would otherwise rot on the record. Somebody names two, thinks
	 * better of the whole question and answers "No" — the picker is not drawn at
	 * that point, so there is no screen on which they could take the two back.
	 * The form has to do it for them, and it has to *send* the emptying rather
	 * than omitting the field, which the server would read as "leave it alone".
	 */
	it("takes back what was named when the answer stops being yes", async () => {
		open();
		await onTheIdentityStep();

		disclose();
		nameOne("Deafness");

		fireEvent.change(screen.getByLabelText(/^Do you have a disability\?/), {
			target: { value: "No" },
		});

		await goOn();
		await goOn();

		await waitFor(() => expect(posted.length).toBeGreaterThan(0));

		const payload = posted[posted.length - 1].payload;
		expect(payload.disability_status).toBe("No");
		expect(payload.disabilities).toEqual([]);
	});

	it("opens with what the profile already holds", async () => {
		reads.set(API.myProfile, {
			...IDENTIFIED,
			disability_status: "Yes",
			disabilities: ["Low vision"],
		});

		open();
		await onTheIdentityStep();

		// Drawn without anybody answering anything, and already ticked.
		fireEvent.focus(picker());
		expect(
			screen.getByRole("option", { name: /Low vision/ }).getAttribute("aria-selected"),
		).toBe("true");
	});
});
