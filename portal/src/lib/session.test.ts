import { describe, expect, it } from "vitest";

import { firstName, initials } from "./session";

/**
 * What to call somebody, and the several things that can be handed to the
 * function that decides.
 *
 * The greeting has three sources in descending order of authority — the
 * society's record of a person, the name on their login, and the login itself,
 * which is an email address. The last is the one this used to get every time,
 * because `api/registration.py::my_profile` answers `null` for anybody who has
 * signed up and not yet registered: a new volunteer's first morning on the
 * portal opened with "Good morning, amina.hassan91."
 *
 * The case rules are the part worth pinning down. Re-casing a shouted or
 * mumbled name is a kindness; re-casing one somebody deliberately capitalised
 * in the middle is misspelling their name on their own dashboard every morning.
 */
describe("the name in a greeting", () => {
	it("takes the first word of a full name", () => {
		expect(firstName("Amina Hassan")).toBe("Amina");
	});

	it("tidies a name that was shouted or mumbled", () => {
		expect(firstName("AMINA HASSAN")).toBe("Amina");
		expect(firstName("amina hassan")).toBe("Amina");
	});

	it("leaves a deliberately mixed-case name exactly as its owner wrote it", () => {
		expect(firstName("McKenzie Ford")).toBe("McKenzie");
		expect(firstName("DeSilva Rao")).toBe("DeSilva");
	});

	it("capitalises after an apostrophe as well as at the start", () => {
		expect(firstName("o'brien kelly")).toBe("O'Brien");
		expect(firstName("O’BRIEN KELLY")).toBe("O’Brien");
	});

	it("keeps a hyphenated given name whole", () => {
		expect(firstName("anne-marie dubois")).toBe("Anne-Marie");
	});

	it("reads an email address as a last resort, splitting on its punctuation", () => {
		// The separators a mailbox uses instead of the space it cannot have.
		expect(firstName("amina.hassan@example.com")).toBe("Amina");
		expect(firstName("amina_hassan@example.com")).toBe("Amina");
	});

	it("answers with nothing rather than something wrong when there is no name", () => {
		expect(firstName("")).toBe("");
		expect(firstName(null)).toBe("");
		expect(firstName(undefined)).toBe("");
		expect(firstName("   ")).toBe("");
	});
});

describe("the initials on an avatar", () => {
	it("takes the first letter of the first two words", () => {
		expect(initials("Amina Hassan")).toBe("AH");
	});

	it("has something to draw even for an address", () => {
		expect(initials("amina.hassan@example.com")).toBe("AH");
	});

	it("is empty when there is nothing to shorten", () => {
		expect(initials(null)).toBe("");
	});
});
