import { act, fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { mount } from "../test/harness";

/** Raising a transfer from a volunteer's record: closed, and only for who may. */
const posted: Array<{ method: string; body: Record<string, unknown> }> = [];
let state: unknown;

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	const { createContext } = await import("react");

	const answer = (message: unknown) => ({
		data: { message },
		error: null,
		isLoading: false,
		mutate: () => Promise.resolve(undefined),
	});

	return {
		...actual.default,
		default: actual.default,
		FrappeContext: createContext({
			call: {
				get: () => Promise.resolve({ message: null }),
				post: (method: string, body: Record<string, unknown>) => {
					posted.push({ method, body });
					return Promise.resolve({ message: {} });
				},
			},
		}),
		FrappeProvider: ({ children }: { children: React.ReactNode }) => children,
		useFrappeGetCall: (method: string) =>
			method.endsWith("volunteer_transfer")
				? answer(state)
				: method.endsWith("county_map")
					? answer({ labels: { "C-BUNGOMA": "Bungoma", "C-NAKURU": "Nakuru" } })
					: answer(null),
		useFrappeAuth: () => ({ currentUser: "cc@example.org", isLoading: false }),
	};
});

const { MoveVolunteer } = await import("./MoveVolunteer");

beforeEach(() => {
	posted.length = 0;
	state = { branch: "C-BUNGOMA", can_raise: true, approved_by_branches: true, transfer: null };
});

describe("moving a volunteer from their record", () => {
	it("is closed until opened", () => {
		mount(<MoveVolunteer volunteer="VOL-1" name="Amina Otieno" />);

		expect(screen.getByRole("button", { name: /Move to another branch/ }).getAttribute("aria-expanded")).toBe("false");
		expect(screen.queryByLabelText(/Branch to move to/)).toBeNull();
	});

	it("raises a transfer for the branch, date and reason given", async () => {
		mount(<MoveVolunteer volunteer="VOL-1" name="Amina Otieno" />);
		fireEvent.click(screen.getByRole("button", { name: /Move to another branch/ }));

		const select = screen.getByLabelText(/Branch to move to/) as HTMLSelectElement;
		expect(Array.from(select.options).map((option) => option.value)).not.toContain("Bungoma");

		fireEvent.change(select, { target: { value: "Nakuru" } });
		fireEvent.change(screen.getByLabelText(/^From/), { target: { value: "2026-12-01" } });
		fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "Moved for work." } });
		expect(screen.getByText("Nakuru decides next. Amina Otieno is emailed.")).toBeTruthy();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Raise transfer" }));
		});

		expect(posted).toEqual([
			{
				method: "vmmsx.api.deployment.request_transfer",
				body: { volunteer: "VOL-1", to_geo_node: "C-NAKURU", effective_date: "2026-12-01", reason: "Moved for work." },
			},
		]);
	});

	it("reports a transfer already under way instead of offering another", () => {
		state = {
			branch: "C-BUNGOMA",
			can_raise: false,
			approved_by_branches: true,
			transfer: { name: "XFER-1", to_place: "Nakuru", waiting_on: "Nakuru" },
		};
		mount(<MoveVolunteer volunteer="VOL-1" name="Amina Otieno" />);
		fireEvent.click(screen.getByRole("button", { name: /Move to another branch/ }));

		expect(screen.getByText(/A transfer to Nakuru is already open, waiting for Nakuru/)).toBeTruthy();
		expect(screen.queryByRole("button", { name: "Raise transfer" })).toBeNull();
	});

	it("is not drawn for somebody who may not move them", () => {
		state = { branch: "C-BUNGOMA", can_raise: false, approved_by_branches: true, transfer: null };
		mount(<MoveVolunteer volunteer="VOL-1" name="Amina Otieno" />);

		expect(screen.queryByRole("button", { name: /Move to another branch/ })).toBeNull();
	});
});
