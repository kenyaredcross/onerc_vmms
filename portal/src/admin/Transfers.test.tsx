import { act, fireEvent, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { mount } from "../test/harness";

/**
 * The console's branch transfers: incoming and outgoing, decided only by the
 * branch whose turn it is.
 */
const posted: Array<{ method: string; body: Record<string, unknown> }> = [];
let rows: unknown[] = [];

const row = (overrides: Record<string, unknown>) => ({
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
	waiting_on: "Mombasa",
	days_waiting: 3,
	decision_reason: "",
	is_effective: false,
	can_withdraw: true,
	can_act: true,
	...overrides,
});

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
			method.endsWith("transfer_counts")
				? answer({ incoming: { open: rows.length, mine: 1 }, outgoing: { open: 0, mine: 0 } })
				: method.endsWith("branch_transfers")
					? answer({ rows })
					: answer(null),
		useFrappeAuth: () => ({ currentUser: "cc@example.org", isLoading: false }),
	};
});

const Transfers = (await import("./Transfers")).default;

beforeEach(() => {
	posted.length = 0;
	rows = [row({})];
});

describe("branch transfers in the console", () => {
	it("says whose turn it is on a transfer that is not this person's to decide", () => {
		rows = [row({ can_act: false, waiting_on: "Bungoma" })];
		mount(<Transfers />, { route: "/admin/transfers?tab=incoming" });

		expect(screen.getByText("Amina Otieno")).toBeTruthy();
		expect(screen.getByText("Waiting for Bungoma")).toBeTruthy();
		expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
	});

	it("approves one that is theirs, through the approval engine", async () => {
		mount(<Transfers />, { route: "/admin/transfers?tab=incoming" });

		fireEvent.click(screen.getByRole("button", { name: "Approve" }));
		const dialog = screen.getByRole("dialog");
		expect(within(dialog).getByText("Amina Otieno moves from Bungoma to Mombasa.")).toBeTruthy();

		await act(async () => {
			fireEvent.click(within(dialog).getByRole("button", { name: "Approve" }));
		});

		expect(posted).toEqual([
			{
				method: "vmmsx.api.approvals.decide",
				body: { doctype: "VMMS Branch Transfer", name: "XFER-00001", decision: "Approved", reason: undefined },
			},
		]);
	});

	it("will not decline without a reason for the volunteer", async () => {
		mount(<Transfers />, { route: "/admin/transfers?tab=incoming" });

		fireEvent.click(screen.getByRole("button", { name: "Decline" }));
		const dialog = screen.getByRole("dialog");

		await act(async () => {
			fireEvent.click(within(dialog).getByRole("button", { name: "Decline" }));
		});
		expect(posted).toEqual([]);
		expect(within(dialog).getByText("Say why, so the volunteer knows.")).toBeTruthy();

		fireEvent.change(within(dialog).getByRole("textbox"), { target: { value: "No space this month." } });
		await act(async () => {
			fireEvent.click(within(dialog).getByRole("button", { name: "Decline" }));
		});

		expect(posted[0].body).toMatchObject({ decision: "Rejected", reason: "No space this month." });
	});

	it("says plainly when nobody is waiting", () => {
		rows = [];
		mount(<Transfers />, { route: "/admin/transfers?tab=outgoing" });

		expect(screen.getByText("Nobody is waiting to leave your branch")).toBeTruthy();
	});
});
