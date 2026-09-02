import { Route, Routes } from "react-router-dom";
import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { ApprovalStatus, PeopleSummary } from "../portal/types";

/**
 * The People overview.
 *
 * **The rule these hold is that no figure on this screen is computed here.**
 * Every total is a permission-scoped server aggregate; the queue breakdown is
 * the engine's own queue grouped by the doctype each row came from. A count
 * derived in the browser from a capped list would be believed and would be
 * wrong the moment the list was longer than one page.
 *
 * **And that a figure the server could not compute is absent, not approximate.**
 * The unique-person count needs the union of two registers' Red Profiles, which
 * is affordable at branch size and not at national size. Past the ceiling the
 * endpoint answers `null` and this screen must drop the block and say why.
 */

const calls: Array<{ path: string; params: Record<string, unknown> | undefined }> = [];
const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };

	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (path: string, params?: Record<string, unknown>, swrKey?: string | null) => {
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

const PeopleOverview = (await import("./PeopleOverview")).default;

function summary(over: Partial<PeopleSummary> = {}): PeopleSummary {
	return {
		queue: {
			"VMMS Volunteer Application": { waiting: 8, overdue: 2 },
			"VMMS Membership": { waiting: 4, overdue: 1 },
		},
		intake: [
			{
				kind: "volunteers",
				doctype: "VMMS Volunteer Application",
				readable: true,
				governed: true,
				in_review: 19,
				changes_requested: 2,
				waiting: 8,
				overdue: 2,
				breached: 3,
			},
			{
				kind: "members",
				doctype: "VMMS Membership",
				readable: true,
				governed: true,
				in_review: 7,
				changes_requested: 1,
				waiting: 4,
				overdue: 1,
				breached: 0,
			},
		],
		registers: [
			{ kind: "volunteers", doctype: "VMMS Volunteer", readable: true, active: 1284 },
			{ kind: "members", doctype: "VMMS Membership", readable: true, active: 3842 },
		],
		people: { unique: 4442, both: 684, volunteers: 1284, members: 3842, capped: false },
		...over,
	};
}

function queueRow(doctype: string, name: string, breached = false): ApprovalStatus {
	return {
		doctype,
		name,
		state: "In Review",
		is_open: true,
		is_terminal: false,
		geo_node: "GEO-1",
		geo_path: "Geita — Tanzania Red Cross Society",
		applicant: {
			doctype: "Red Profile",
			name: "RP-1",
			red_profile: "RP-1",
			full_name: name === "APP-1" ? "Faith Njeri" : "Alice Kilonzo",
			email: null,
			phone: null,
			photo: null,
		},
		stage: {
			name: "row-1",
			sequence: 1,
			label: "Branch review",
			required_role: "Approver",
			completion_rule: "single",
			can_reject: true,
			is_optional: false,
			entered_on: breached ? "2026-08-20" : "2026-08-30",
			due_on: "2026-08-25",
			is_breached: breached,
			days_overdue: breached ? 6 : 0,
			is_blocked: false,
		},
		can_act: true,
		approver_count: 1,
		approvers: null,
		escalated_to: null,
		allow_withdrawal: true,
		can_withdraw: false,
		decisions: [],
	} as ApprovalStatus;
}

function show() {
	return mount(
		<Routes>
			<Route path="*" element={<PeopleOverview />} />
		</Routes>,
		{ route: "/admin/people" },
	);
}

beforeEach(() => {
	calls.length = 0;
	reads.clear();
});

describe("the People overview", () => {
	it("reads its figures from the scoped aggregate endpoint", () => {
		reads.set(API.peopleSummary, summary());
		reads.set(API.myQueue, []);

		show();

		expect(calls.some((call) => call.path === API.peopleSummary)).toBe(true);
		// The endpoint takes no arguments, so there is nothing this app could
		// send that would widen the answer.
		expect(calls.find((call) => call.path === API.peopleSummary)?.params).toBeUndefined();
	});

	it("shows both register totals separately, as people-in-scope figures", () => {
		reads.set(API.peopleSummary, summary());
		reads.set(API.myQueue, []);

		show();

		expect(screen.getByText("Active volunteers in scope")).toBeTruthy();
		expect(screen.getByText("Active memberships in scope")).toBeTruthy();
		expect(screen.getAllByText("1,284").length).toBeGreaterThan(0);
		expect(screen.getAllByText("3,842").length).toBeGreaterThan(0);
	});

	it("shows the unique-person figure only when the server computed one", () => {
		reads.set(API.peopleSummary, summary());
		reads.set(API.myQueue, []);

		show();

		expect(screen.getByText("Unique active people")).toBeTruthy();
		expect(screen.getByText("4,442")).toBeTruthy();
		expect(screen.getByText(/684 hold both/)).toBeTruthy();
	});

	it("drops the block and says why when the server could not de-duplicate", () => {
		reads.set(
			API.peopleSummary,
			summary({
				people: { unique: null, both: null, volunteers: null, members: null, capped: true },
			}),
		);
		reads.set(API.myQueue, []);

		show();

		expect(screen.queryByText("Unique active people")).toBeNull();
		expect(screen.getByText(/counted from a truncated read would be wrong/)).toBeTruthy();
		// The two exact register totals are still there.
		expect(screen.getAllByText("1,284").length).toBeGreaterThan(0);
	});

	it("draws a dash for a register this reader may not open at all", () => {
		reads.set(
			API.peopleSummary,
			summary({
				registers: [
					{ kind: "volunteers", doctype: "VMMS Volunteer", readable: true, active: 1284 },
					// A membership clerk with no volunteer permissions, or the
					// other way round. Not being allowed to know is
					// indistinguishable, on a screen, from there being nothing to
					// know — so it is a dash, never a zero.
					{ kind: "members", doctype: "VMMS Membership", readable: false, active: null },
				],
			}),
		);
		reads.set(API.myQueue, []);

		show();

		// Scoped to the tile itself: the intake block below it legitimately
		// carries zeroes, and a page-wide search for "0" would find those.
		const tile = screen.getByText("Active memberships in scope").parentElement;

		expect(tile?.textContent).toContain("—");
		expect(tile?.textContent).not.toContain("0");
	});

	it("draws an intake-health row per door, with what is stuck in each", () => {
		reads.set(API.peopleSummary, summary());
		reads.set(API.myQueue, []);

		show();

		expect(screen.getByText("Intake health")).toBeTruthy();
		expect(screen.getAllByText("Volunteer applications").length).toBeGreaterThan(0);
		expect(screen.getAllByText("Membership applications").length).toBeGreaterThan(0);
		// In review across the scope, changes requested, and what is routed here.
		expect(screen.getByText("19")).toBeTruthy();
		expect(screen.getByText("3 overdue")).toBeTruthy();
	});

	it("tells an unreadable door apart from an ungoverned one", () => {
		reads.set(
			API.peopleSummary,
			summary({
				intake: [
					{
						kind: "volunteers",
						doctype: "VMMS Volunteer Application",
						// Governed, and not this reader's to see. Saying "not
						// configured" here would be plainly false.
						readable: false,
						governed: false,
						in_review: null,
						changes_requested: null,
						waiting: 0,
						overdue: 0,
						breached: null,
					},
				],
			}),
		);
		reads.set(API.myQueue, []);

		show();

		expect(screen.getByText("These applications are not in your permissions")).toBeTruthy();
		expect(screen.queryByText(/No approval workflow is configured/)).toBeNull();
	});

	it("says an ungoverned door is not governed rather than showing it as empty", () => {
		reads.set(
			API.peopleSummary,
			summary({
				intake: [
					{
						kind: "members",
						doctype: "VMMS Membership",
						readable: true,
						governed: false,
						in_review: null,
						changes_requested: null,
						waiting: 0,
						overdue: 0,
						breached: null,
					},
				],
			}),
		);
		reads.set(API.myQueue, []);

		show();

		// "Nothing to do" and "nobody has configured this" are different answers.
		expect(screen.getByText(/No approval workflow is configured/)).toBeTruthy();
		expect(screen.getByText("Not governed")).toBeTruthy();
	});

	it("orders the attention queue by breach first, then by how long it has waited", () => {
		reads.set(API.peopleSummary, summary());
		reads.set(API.myQueue, [
			queueRow("VMMS Membership", "MEM-1"),
			queueRow("VMMS Volunteer Application", "APP-1", true),
		]);

		show();

		const names = screen
			.getAllByRole("link")
			.map((link) => link.textContent ?? "")
			.filter((text) => text.includes("Faith Njeri") || text.includes("Alice Kilonzo"));

		expect(names[0]).toContain("Faith Njeri");
		expect(screen.getByText("6 days over")).toBeTruthy();
	});

	it("routes each attention row to its own registration's queue", () => {
		reads.set(API.peopleSummary, summary());
		reads.set(API.myQueue, [queueRow("VMMS Membership", "MEM-1")]);

		show();

		expect(
			screen.getAllByRole("link", { name: /Alice Kilonzo/ })[0].getAttribute("href"),
		).toBe("/admin/queue/members/MEM-1");
	});

	it("offers a person search that hands the question to a register as a URL", () => {
		reads.set(API.peopleSummary, summary());
		reads.set(API.myQueue, []);

		show();

		// It navigates rather than searching in place: the register is the screen
		// with the paging, the filters and the permission-scoped read.
		expect(screen.getByText("Find a person")).toBeTruthy();
		expect(screen.getByLabelText(/Name or record number/)).toBeTruthy();
		expect(screen.getByRole("button", { name: "Search" })).toBeTruthy();
		expect(
			screen.getAllByRole("link", { name: /Volunteer register/ })[0].getAttribute("href"),
		).toBe("/admin/registry/volunteers");
	});

	it("says nothing is waiting rather than showing an empty table", () => {
		reads.set(API.peopleSummary, summary());
		reads.set(API.myQueue, []);

		show();

		expect(screen.getByText("Nothing is waiting on you")).toBeTruthy();
	});
});
