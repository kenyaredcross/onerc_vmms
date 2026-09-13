import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

/**
 * What a visitor reads, against what an administrator edits.
 *
 * The token substitution itself is covered in `tokens.test.ts`. What is worth a
 * mounted test is the *wiring*, because both ways of getting it wrong are
 * invisible until somebody looks at the running page: a slot that draws
 * `{country|your community}` at a visitor, or an editor whose box has already
 * had the country baked into it and saves that.
 */
const BLOCKS = {
	"landing.hero.headline": {
		key: "landing.hero.headline",
		label: "Hero headline",
		text: "Show up for {country|your community}.",
		href: "",
		image: null,
		image_alt: "",
		image_credit: "",
	},
};

let country = "Tanzania";

vi.mock("frappe-react-sdk", async (importOriginal) => {
	// The SDK ships CommonJS: the real exports hang off `default`, and spreading
	// the namespace would hand back a module with no named exports at all.
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	const { createContext } = await import("react");

	const rest = {
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
		// Answers by endpoint, so the provider's surface read and the society read
		// underneath it are told apart the way they are in the app.
		useFrappeGetCall: (method: string) => {
			if (method.endsWith("society.branding")) {
				return { data: { message: { name: "", short_name: "", country, logo: "", logo_dark: "" } }, ...rest };
			}

			return { data: { message: { surface: "landing", blocks: BLOCKS, can_edit: false } }, ...rest };
		},
		useFrappeAuth: () => ({ currentUser: null, isLoading: false, logout: () => Promise.resolve() }),
		useFrappeFileUpload: () => ({ upload: () => Promise.resolve({ file_url: "" }), loading: false }),
	};
});

const { mount } = await import("../test/harness");
const { EditableText } = await import("./Editable");

const headline = () => <EditableText k="landing.hero.headline" as="h1" />;

describe("a slot that quotes the society", () => {
	it("draws the value, not the token", () => {
		country = "Tanzania";
		mount(headline());

		expect(screen.getByRole("heading").textContent).toBe("Show up for Tanzania.");
	});

	it("falls back to the shipped words on a site with no country set", () => {
		country = "";
		mount(headline());

		expect(screen.getByRole("heading").textContent).toBe("Show up for your community.");
	});

	it("never leaves a brace on the page", () => {
		country = "Kenya";
		mount(headline());

		expect(screen.getByRole("heading").textContent).not.toContain("{");
	});
});
