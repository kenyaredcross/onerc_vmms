import { act, fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { mount } from "../test/harness";

/** A volunteer asking to move branch, from their own profile. */
const posted: Array<{ method: string; body: Record<string, unknown> }> = [];
let mine: unknown = null;
let canRequest = true;

const LABELS = { "C-BUNGOMA": "Bungoma", "C-MOMBASA": "Mombasa", "C-NAKURU": "Nakuru" };

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
			method.endsWith("my_transfer")
				? answer({ transfer: mine, can_request: canRequest })
				: method.endsWith("county_map")
					? answer({ labels: LABELS })
					: answer(null),
		useFrappeAuth: () => ({ currentUser: "amina@example.org", isLoading: false }),
	};
});

const { TransferCard } = await import("./TransferCard");

const pending = {
	name: "XFER-00001",
	volunteer: "VOL-1",
	volunteer_name: "Amina Otieno",
	from_geo_node: "C-BUNGOMA",
	from_place: "Bungoma",
	to_geo_node: "C-MOMBASA",
	to_place: "Mombasa",
	reason: "Moving for work.",
	effective_date: "2026-11-04",
	requested_by_volunteer: true,
	requested_on: "2026-11-01",
	transfer_status: "Pending",
	approval_state: "In Review",
	waiting_on: "Bungoma",
	days_waiting: 1,
	decision_reason: "",
	is_effective: false,
	can_withdraw: true,
};

beforeEach(() => {
	posted.length = 0;
	mine = null;
	canRequest = true;
});

describe("asking to move branch", () => {
	it("sends the branch chosen and the reason given", async () => {
		mount(<TransferCard branch="C-BUNGOMA" active />);

		fireEvent.click(screen.getByRole("button", { name: "Request a transfer" }));

		const select = screen.getByLabelText(/Branch to move to/) as HTMLSelectElement;
		const options = Array.from(select.options).map((option) => option.value);
		expect(options).not.toContain("Bungoma");

		fireEvent.change(select, { target: { value: "Nakuru" } });
		fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: "Family moved." } });

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Send request" }));
		});

		expect(posted).toEqual([
			{ method: "vmmsx.api.transfers.request_my_transfer", body: { to_geo_node: "C-NAKURU", reason: "Family moved." } },
		]);
	});

	it("opens with the branch chosen from the directory", () => {
		mount(<TransferCard branch="C-BUNGOMA" active />, { route: "/profile?transfer=C-MOMBASA" });

		expect((screen.getByLabelText(/Branch to move to/) as HTMLSelectElement).value).toBe("Mombasa");
	});

	it("says whose decision it is waiting for, and can be taken back", async () => {
		mine = pending;
		mount(<TransferCard branch="C-BUNGOMA" active />);

		expect(screen.getByText("You asked to move from Bungoma to Mombasa.")).toBeTruthy();
		expect(screen.getByText("Waiting for Bungoma.")).toBeTruthy();
		expect(screen.queryByRole("button", { name: "Request a transfer" })).toBeNull();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Withdraw request" }));
		});

		expect(posted[0]).toEqual({ method: "vmmsx.api.transfers.withdraw_my_transfer", body: { name: "XFER-00001" } });
	});

	it("is not offered where nobody decides a transfer", () => {
		canRequest = false;
		mount(<TransferCard branch="C-BUNGOMA" active />, { route: "/profile?transfer=C-MOMBASA" });

		expect(screen.queryByRole("button", { name: "Request a transfer" })).toBeNull();
		expect(screen.queryByLabelText(/Branch to move to/)).toBeNull();
	});

	it("gives the reason when it was declined", () => {
		mine = { ...pending, transfer_status: "Cancelled", approval_state: "Rejected", decision_reason: "No space." };
		mount(<TransferCard branch="C-BUNGOMA" active />);

		expect(screen.getByText("Your request to move to Mombasa was not approved.")).toBeTruthy();
		expect(screen.getByText("Reason: No space.")).toBeTruthy();
	});
});
