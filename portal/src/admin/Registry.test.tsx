import { Route, Routes } from "react-router-dom";
import { act, fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";

/**
 * The two active registers.
 *
 * **The rule these hold is that "active" is the server's answer, not a control
 * somebody could clear.** The volunteer register asks for `status="Active"` and
 * the member register for `current_only=1` on every read, so a prospective
 * volunteer or an expired membership cannot appear here however the screen is
 * driven. Each of those is a state with its own workflow; none of them belongs
 * in the list a coordinator staffs from.
 *
 * **And that no figure on the page is a page's length.** The summary tiles come
 * from their own scoped aggregate endpoint. A headline computed from the current
 * filter would change when somebody typed in the search box, and would be
 * believed.
 *
 * **And that the summary card costs nothing until it is opened.** A register of
 * two hundred rows must not be two hundred dossier reads.
 */

const calls: Array<{ path: string; params: Record<string, unknown> | undefined }> = [];
const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };

	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (
			path: string,
			params?: Record<string, unknown>,
			swrKey?: string | null,
		) => {
			if (swrKey === null) {
				return {
					data: undefined,
					error: null,
					isLoading: false,
					isValidating: false,
					mutate: () => Promise.resolve(undefined),
				};
			}

			calls.push({ path, params });

			return {
				data: { message: reads.get(path) },
				error: null,
				isLoading: false,
				isValidating: false,
				mutate: () => Promise.resolve(undefined),
			};
		},
	};
});

const { MembersRegistry, VolunteersRegistry } = await import("./Registry");

const VOLUNTEER = {
	volunteer: "VOL-00042",
	red_profile: "RP-1",
	full_name: "Alex Mwangi",
	photo: null,
	status: "Active",
	joined_on: "2026-01-18",
	geo_node: "GEO-9",
	geo_path: "Geita Town — Geita — Tanzania Red Cross Society",
	deployable: true,
};

const MEMBERSHIP = {
	membership: "MEM-00981",
	member: "MBR-0001",
	full_name: "Alice Kilonzo",
	photo: null,
	membership_type: "annual",
	membership_type_name: "Annual",
	geo_node: "GEO-9",
	geo_path: "Geita — Tanzania Red Cross Society",
	membership_status: "Active",
	effective_status: "Active",
	lapsed: false,
	is_current: true,
	valid_from: "2026-01-01" as string | null,
	// A life membership has none, and a test overriding it to null is the case
	// this register has to render as "No expiry" rather than as a blank cell.
	valid_to: "2026-12-31" as string | null,
	membership_source: "Portal" as string | null,
};

function volunteers(rows = [VOLUNTEER]) {
	reads.set(API.findVolunteers, { count: rows.length, total: 1284, volunteers: rows });
	reads.set(API.volunteerRegisterSummary, {
		active: 1284,
		joined_month: 38,
		branches: 17,
		deployed: 212,
		deployments: 6,
		capped: false,
	});
}

function members(rows = [MEMBERSHIP]) {
	reads.set(API.findMembers, {
		count: rows.length,
		total: 3842,
		member_count: 3700,
		as_of: "2026-09-02",
		rows,
	});
	reads.set(API.memberRegisterSummary, {
		as_of: "2026-09-02",
		active: 3842,
		lifetime: 402,
		term: 3440,
		renewing: 118,
		renewal_window_days: 60,
		capped: false,
	});
	reads.set(API.membershipTypes, { types: [{ membership_type: "annual", membership_type_name: "Annual" }] });
}

function show(element: React.ReactNode, route: string) {
	return mount(
		<Routes>
			<Route path="*" element={element} />
		</Routes>,
		{ route },
	);
}

function argsFor(path: string) {
	return calls.filter((call) => call.path === path).at(-1)?.params;
}

beforeEach(() => {
	calls.length = 0;
	reads.clear();
});

describe("the active volunteer register", () => {
	it("always asks for active volunteers, with server paging", () => {
		volunteers();
		show(<VolunteersRegistry />, "/admin/registry/volunteers");

		expect(argsFor(API.findVolunteers)).toMatchObject({
			status: "Active",
			limit: 25,
			offset: 0,
		});
	});

	it("does not send the capability filters this register no longer has", () => {
		volunteers();
		show(<VolunteersRegistry />, "/admin/registry/volunteers");

		const args = argsFor(API.findVolunteers) ?? {};

		// Skills, languages and availability stay on the doctype and still drive
		// deployment matching. They are not this register's question.
		expect(args).not.toHaveProperty("skills");
		expect(args).not.toHaveProperty("languages");
		expect(args).not.toHaveProperty("availability");
	});

	it("carries a search term in from the URL, so the overview can hand one over", () => {
		volunteers();
		show(<VolunteersRegistry />, "/admin/registry/volunteers?q=Mwangi");

		expect(argsFor(API.findVolunteers)).toMatchObject({ search: "Mwangi", status: "Active" });
	});

	it("takes its headline figures from the aggregate endpoint, not from the page", () => {
		volunteers();
		show(<VolunteersRegistry />, "/admin/registry/volunteers");

		expect(calls.some((call) => call.path === API.volunteerRegisterSummary)).toBe(true);
		// 1,284 is the scoped register; the page holds one row.
		expect(screen.getByText("1,284")).toBeTruthy();
		expect(screen.getByText("212")).toBeTruthy();
	});

	it("draws a dash rather than a number where the server could not total", () => {
		volunteers();
		reads.set(API.volunteerRegisterSummary, {
			active: 1284,
			joined_month: 38,
			// Past the read ceiling. A number here would be wrong rather than
			// approximate.
			branches: null,
			deployed: 212,
			deployments: 6,
			capped: true,
		});

		show(<VolunteersRegistry />, "/admin/registry/volunteers");

		expect(screen.getByText("Branches represented")).toBeTruthy();
		expect(screen.getAllByText("—").length).toBeGreaterThan(0);
	});

	it("puts the reader back on the first page when the search narrows", async () => {
		volunteers();
		show(<VolunteersRegistry />, "/admin/registry/volunteers");

		const box = screen.getByLabelText("Search by name or volunteer number");
		await act(async () => {
			fireEvent.change(box, { target: { value: "Alex" } });
		});

		// The bug every hand-rolled pager has: somebody on page three who narrows
		// to four results left staring at an empty page three.
		expect(argsFor(API.findVolunteers)).toMatchObject({ offset: 0, search: "Alex" });
	});
});

describe("the active member register", () => {
	it("always asks for current memberships only", () => {
		members();
		show(<MembersRegistry />, "/admin/registry/members");

		expect(argsFor(API.findMembers)).toMatchObject({ current_only: 1, limit: 25, offset: 0 });
	});

	it("does not offer the recorded-status filter that would reach expired rows", () => {
		members();
		show(<MembersRegistry />, "/admin/registry/members");

		expect(argsFor(API.findMembers)).not.toHaveProperty("status");
	});

	it("shows the four approved summary blocks from the scoped aggregate", () => {
		members();
		show(<MembersRegistry />, "/admin/registry/members");

		expect(screen.getByText("Active memberships")).toBeTruthy();
		// "Term", not "Annual": the split is `VMMS Membership Type.is_lifetime`,
		// never a type's name — a society names its own types.
		expect(screen.getByText("Term memberships")).toBeTruthy();
		expect(screen.getByText("Life memberships")).toBeTruthy();
		expect(screen.getByText("Renewals approaching")).toBeTruthy();
		expect(screen.getByText("3,842")).toBeTruthy();
	});

	it("renders a life membership as having no expiry rather than a blank cell", () => {
		members([{ ...MEMBERSHIP, valid_to: null }]);
		show(<MembersRegistry />, "/admin/registry/members");

		expect(screen.getAllByText("No expiry").length).toBeGreaterThan(0);
	});
});

describe("the floating person summary", () => {
	it("fetches nothing about a person until their card is opened", () => {
		volunteers();
		show(<VolunteersRegistry />, "/admin/registry/volunteers");

		// The whole point: a register of two hundred rows must not be two hundred
		// dossier reads to fill the four cards somebody actually opens.
		expect(calls.some((call) => call.path === API.volunteerDossier)).toBe(false);
	});

	it("opens on keyboard focus and fetches exactly that one person", async () => {
		volunteers();
		reads.set(API.volunteerDossier, {
			volunteer: "VOL-00042",
			identity: { phone: "+255 700 000 018", email: "alex@example.com" },
			time: { total_hours: 136 },
			deployments: [{ is_settled: true }, { is_settled: false }],
		});

		show(<VolunteersRegistry />, "/admin/registry/volunteers");

		const trigger = screen.getAllByRole("button", { name: /Alex Mwangi/ })[0];
		await act(async () => {
			fireEvent.focus(trigger);
		});

		expect(trigger.getAttribute("aria-expanded")).toBe("true");
		expect(screen.getByRole("dialog", { name: "Person summary" })).toBeTruthy();

		// One person, whichever way the hook re-rendered: the argument never
		// varies, which is what makes the SWR key serve the second look from
		// cache instead of asking again.
		const asked = calls.filter((call) => call.path === API.volunteerDossier);
		expect(asked.length).toBeGreaterThan(0);
		expect(new Set(asked.map((call) => JSON.stringify(call.params)))).toEqual(
			new Set(['{"name":"VOL-00042"}']),
		);
	});

	it("shows the approved facts, including the derived completed count", async () => {
		volunteers();
		reads.set(API.volunteerDossier, {
			volunteer: "VOL-00042",
			identity: { phone: "+255 700 000 018", email: "alex@example.com" },
			time: { total_hours: 136 },
			// One settled, one still running. Only the first is "completed", and
			// `is_settled` is the server's answer rather than a status compared here.
			deployments: [{ is_settled: true }, { is_settled: false }],
		});

		show(<VolunteersRegistry />, "/admin/registry/volunteers");

		await act(async () => {
			fireEvent.focus(screen.getAllByRole("button", { name: /Alex Mwangi/ })[0]);
		});

		// Twice on the page now: the register's own column, and the card.
		expect(screen.getAllByText("VOL-00042").length).toBe(2);
		expect(screen.getByText("136 verified")).toBeTruthy();
		expect(screen.getByText("1 completed")).toBeTruthy();
		// Reachable actions, drawn only where there is something behind them.
		expect(screen.getByRole("link", { name: "Call Alex Mwangi" })).toBeTruthy();
		expect(screen.getByRole("link", { name: "Email Alex Mwangi" })).toBeTruthy();
	});

	it("keeps the answer for a second look rather than asking twice", async () => {
		volunteers();
		reads.set(API.volunteerDossier, {
			volunteer: "VOL-00042",
			identity: {},
			time: { total_hours: 0 },
			deployments: [],
		});

		show(<VolunteersRegistry />, "/admin/registry/volunteers");

		const trigger = screen.getAllByRole("button", { name: /Alex Mwangi/ })[0];

		await act(async () => {
			fireEvent.focus(trigger);
		});
		await act(async () => {
			fireEvent.blur(trigger);
		});
		await act(async () => {
			fireEvent.focus(trigger);
		});

		// The SWR key is the docname, so re-opening the same person is free. The
		// mock records one call per render of the hook; what matters is that the
		// key never varies, which is what makes SWR serve it from cache.
		const keys = new Set(
			calls.filter((call) => call.path === API.volunteerDossier).map((call) => JSON.stringify(call.params)),
		);
		expect(keys.size).toBe(1);
	});

	it("closes on Escape and gives focus back to the trigger", async () => {
		volunteers();
		reads.set(API.volunteerDossier, {
			volunteer: "VOL-00042",
			identity: {},
			time: { total_hours: 0 },
			deployments: [],
		});

		show(<VolunteersRegistry />, "/admin/registry/volunteers");

		const trigger = screen.getAllByRole("button", { name: /Alex Mwangi/ })[0];

		// Click pins it, which is what stops a card closing while somebody reads it.
		await act(async () => {
			fireEvent.click(trigger);
		});
		expect(screen.getByRole("dialog", { name: "Person summary" })).toBeTruthy();

		await act(async () => {
			fireEvent.keyDown(document, { key: "Escape" });
		});

		expect(screen.queryByRole("dialog", { name: "Person summary" })).toBeNull();
		// Focus left on the document is focus somebody has to find again.
		expect(document.activeElement).toBe(trigger);
	});

	it("opens a member's card against the member, not the membership", async () => {
		members();
		reads.set(API.memberDossier, { member: "MBR-0001", identity: { phone: "+255 1" } });

		show(<MembersRegistry />, "/admin/registry/members");

		await act(async () => {
			fireEvent.focus(screen.getAllByRole("button", { name: /Alice Kilonzo/ })[0]);
		});

		// The dossier is the person's — it covers every branch they hold a
		// membership at — so it is keyed on the member.
		expect(calls.find((call) => call.path === API.memberDossier)?.params).toEqual({
			name: "MBR-0001",
		});
	});
});
