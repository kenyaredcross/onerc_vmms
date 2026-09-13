import { describe, expect, it } from "vitest";

import { resolveTokens } from "./tokens";

/**
 * The browser's half of `vmmsx/content/services/tokens.py`, and the reason it
 * is tested separately rather than trusted to match: the two are the same rule
 * written twice, and a sentence that resolves on the sign-in page and prints
 * braces on the home page would be a bug nobody would think to look for.
 *
 * The cases are deliberately the same ones the Python suite covers.
 */
const KNOWN = { country: "Kenya", society: "Kenya Red Cross Society" };
const NOTHING = { country: "", society: "" };

describe("what a page's wording may quote", () => {
	it("puts the value in place of the token", () => {
		expect(resolveTokens("Show up for {country|your community}.", KNOWN)).toBe(
			"Show up for Kenya.",
		);
	});

	it("falls back to what follows the bar when there is no value", () => {
		expect(resolveTokens("Show up for {country|your community}.", NOTHING)).toBe(
			"Show up for your community.",
		);
	});

	it("leaves nothing behind for a token with neither a value nor a fallback", () => {
		expect(resolveTokens("Show up for {country}.", NOTHING)).toBe("Show up for .");
	});

	it("leaves a key it does not know exactly as it was written", () => {
		expect(resolveTokens("For {region|everyone}.", KNOWN)).toBe("For {region|everyone}.");
		expect(resolveTokens("Hello {name}", KNOWN)).toBe("Hello {name}");
	});

	it("resolves more than one token in a sentence", () => {
		expect(
			resolveTokens("{society|The Society} works across {country|the country}.", KNOWN),
		).toBe("Kenya Red Cross Society works across Kenya.");
	});

	it("leaves ordinary prose with a brace in it alone", () => {
		expect(resolveTokens("A {see the note} aside", KNOWN)).toBe("A {see the note} aside");
	});

	it("returns text with no braces untouched", () => {
		expect(resolveTokens("Nothing to do here", KNOWN)).toBe("Nothing to do here");
	});

	it("does not treat an empty string as a failure", () => {
		expect(resolveTokens("", KNOWN)).toBe("");
	});

	it("falls back when the society has answered nothing at all", () => {
		// What a page gets before `society:branding` has landed, and on a site
		// whose settings form nobody has opened.
		expect(resolveTokens("Show up for {country|your community}.", {})).toBe(
			"Show up for your community.",
		);
	});
});
