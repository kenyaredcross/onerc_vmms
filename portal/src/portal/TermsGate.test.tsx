import { act, fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { mount } from "../test/harness";

/** The terms panel a volunteer meets when a required declaration is outstanding. */
let outstanding: unknown[] = [];
let afterAccept: unknown[] = [];
let acceptFails: unknown = null;
const accepted: Array<Record<string, unknown>> = [];
const loggedOut = vi.fn(() => Promise.resolve());

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	const { createContext, useState } = await import("react");

	return {
		...actual.default,
		default: actual.default,
		FrappeContext: createContext({ call: { get: () => Promise.resolve({ message: null }) } }),
		FrappeProvider: ({ children }: { children: React.ReactNode }) => children,
		useFrappeGetCall: (method: string) => {
			// eslint-disable-next-line react-hooks/rules-of-hooks
			const [data, setData] = useState<unknown>(
				method.endsWith("my_outstanding_declarations") ? outstanding : null,
			);
			return {
				data: { message: data },
				error: null,
				isLoading: false,
				mutate: (next?: { message: unknown }) => {
					setData(next ? next.message : outstanding);
					return Promise.resolve(next);
				},
			};
		},
		useFrappePostCall: () => ({
			loading: false,
			call: (body: Record<string, unknown>) => {
				accepted.push(body);
				return acceptFails ? Promise.reject(acceptFails) : Promise.resolve({ message: afterAccept });
			},
		}),
		useFrappeAuth: () => ({ currentUser: "amina@example.org", isLoading: false, logout: loggedOut }),
	};
});

const { TermsGate } = await import("./TermsGate");

const code = {
	name: "DECL-CODE",
	title: "Code of conduct",
	version: "2",
	source: "Text" as const,
	body: "<p>Treat everyone with respect.</p>",
	external_url: null,
	declaration_version: "DECL-CODE-V2",
	is_required: true,
	updated: true,
};

const privacy = {
	...code,
	name: "DECL-PRIVACY",
	title: "Privacy notice",
	version: "1",
	body: "<p>We keep your record safe.</p>",
	declaration_version: "DECL-PRIVACY-V1",
	updated: false,
};

beforeEach(() => {
	outstanding = [];
	afterAccept = [];
	acceptFails = null;
	accepted.length = 0;
	loggedOut.mockClear();
	document.getElementById("root")?.remove();
	const root = document.createElement("div");
	root.id = "root";
	document.body.appendChild(root);
});

describe("the terms panel", () => {
	it("draws nothing when there is nothing to accept", () => {
		mount(<TermsGate />);

		expect(screen.queryByRole("dialog")).toBeNull();
	});

	it("covers the portal with every outstanding declaration and no way to close it", () => {
		outstanding = [code, privacy];
		mount(<TermsGate />);

		const dialog = screen.getByRole("dialog", { name: "Accept the terms to continue" });
		expect(dialog).toBeTruthy();
		expect(screen.getByText("Code of conduct")).toBeTruthy();
		expect(screen.getByText("Privacy notice")).toBeTruthy();
		expect(screen.getByText(/Updated · Version 2/)).toBeTruthy();
		expect(screen.queryByRole("button", { name: "Close" })).toBeNull();
		expect(document.getElementById("root")?.inert).toBe(true);

		fireEvent.keyDown(window, { key: "Escape" });
		expect(screen.getByRole("dialog")).toBeTruthy();
	});

	it("holds Accept until every box is ticked, and says so", () => {
		outstanding = [code, privacy];
		mount(<TermsGate />);

		const go = screen.getByRole("button", { name: "Accept and continue" });
		expect(go.getAttribute("aria-disabled")).toBe("true");

		fireEvent.click(screen.getAllByRole("checkbox")[0]);
		fireEvent.click(go);

		expect(screen.getByRole("alert").textContent).toBe("Tick each declaration to continue.");
		expect(accepted).toHaveLength(0);
	});

	it("sends each declaration at the version shown, then lets the person in", async () => {
		outstanding = [code, privacy];
		mount(<TermsGate />);

		for (const box of screen.getAllByRole("checkbox")) fireEvent.click(box);
		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Accept and continue" }));
		});

		expect(JSON.parse(accepted[0].declarations as string)).toEqual([
			{ declaration: "DECL-CODE", declaration_version: "DECL-CODE-V2" },
			{ declaration: "DECL-PRIVACY", declaration_version: "DECL-PRIVACY-V1" },
		]);
		expect(screen.queryByRole("dialog")).toBeNull();
		expect(document.getElementById("root")?.inert).toBe(false);
	});

	it("brings in a version published while they read, unticked", async () => {
		outstanding = [code];
		acceptFails = {
			_server_messages: JSON.stringify([
				JSON.stringify({
					message: "These terms were updated while you were reading them. Please read the new version.",
				}),
			]),
		};
		mount(<TermsGate />);

		fireEvent.click(screen.getByRole("checkbox"));
		outstanding = [{ ...code, version: "3", declaration_version: "DECL-CODE-V3" }];
		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Accept and continue" }));
		});

		expect(screen.getByRole("alert").textContent).toMatch(/updated while you were reading/);
		expect(screen.getByText(/Version 3/)).toBeTruthy();
		expect((screen.getByRole("checkbox") as HTMLInputElement).checked).toBe(false);
	});

	it("offers signing out as the only other way", async () => {
		outstanding = [code];
		mount(<TermsGate />);

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
		});

		expect(loggedOut).toHaveBeenCalled();
	});
});
