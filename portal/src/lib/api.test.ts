import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { errorMessage } from "./api";

/**
 * What a member of the public is allowed to be shown when the server fails.
 *
 * These exist because of a screenshot. The volunteer registration wizard drew
 * this under four dropdowns at once, in a form somebody had opened to sign up:
 *
 *     You are not permitted to access this resource. Login to access
 *     Function vmmsx.api.geo.browse is not whitelisted.
 *
 * Every screen in the portal turns its errors into words through this one
 * function, so the rule about which words survive is asserted here rather than
 * hoped for at eighty-five call sites.
 */

/** A thrown message as Frappe wraps it: JSON, inside JSON, inside HTML. */
function serverMessage(...messages: string[]): string {
	return JSON.stringify(messages.map((message) => JSON.stringify({ message })));
}

beforeEach(() => {
	vi.spyOn(console, "error").mockImplementation(() => undefined);
});

afterEach(() => {
	vi.restoreAllMocks();
});

describe("sentences somebody wrote for a person", () => {
	it("shows a message that came from frappe.throw", () => {
		expect(
			errorMessage({
				_server_messages: serverMessage(
					"You already have an application with us that has not been decided yet.",
				),
			}),
		).toBe("You already have an application with us that has not been decided yet.");
	});

	it("strips the markup Frappe wraps a thrown message in", () => {
		expect(errorMessage({ _server_messages: serverMessage("<b>Amina</b> cannot be empty.") })).toBe(
			"Amina cannot be empty.",
		);
	});

	it("passes over a machine sentence to reach a human one behind it", () => {
		expect(
			errorMessage({
				_server_messages: serverMessage(
					"Function vmmsx.api.geo.browse is not whitelisted.",
					"Choose a branch before continuing.",
				),
			}),
		).toBe("Choose a branch before continuing.");
	});
});

describe("sentences addressed to whoever wrote the endpoint", () => {
	it("never names an endpoint", () => {
		const shown = errorMessage({
			message: "Function vmmsx.api.geo.browse is not whitelisted.",
			exception: "frappe.exceptions.PermissionError",
		});

		expect(shown).toBe("Something went wrong.");
		expect(shown).not.toContain("vmmsx");
	});

	it("does not show a traceback, however it arrives", () => {
		expect(
			errorMessage({ _server_messages: serverMessage("Traceback (most recent call last): …") }),
		).toBe("Something went wrong.");
	});

	it("prefers the caller's own fallback to the framework's words", () => {
		expect(
			errorMessage({ httpStatusText: "Internal Server Error" }, "Your draft could not be saved."),
		).toBe("Your draft could not be saved.");
	});

	it("still hands the whole error to the console for whoever is debugging", () => {
		const error = { exception: "frappe.exceptions.ValidationError" };
		errorMessage(error);

		expect(console.error).toHaveBeenCalledWith("[vmms]", error);
	});
});

describe("the one machine failure worth naming", () => {
	it("tells somebody whose session has gone to sign in again", () => {
		expect(
			errorMessage({
				message: "You are not permitted to access this resource. Login to access",
				httpStatus: 403,
			}),
		).toBe("You have been signed out. Sign in again to carry on.");
	});

	it("recognises it from the exception type alone", () => {
		expect(errorMessage({ exc_type: "PermissionError" })).toBe(
			"You have been signed out. Sign in again to carry on.",
		);
	});
});
