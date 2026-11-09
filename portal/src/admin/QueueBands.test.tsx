import { Route, Routes } from "react-router-dom";
import { act, fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { ApprovalStatus } from "../portal/types";

/**
 * The two application queues, and the four bands each of them navigates:
 * In review, Drafts, Changes requested and Closed.
 *
 * **The rule these hold is separation.** Volunteer applications and memberships
 * are two registers with two decision views, and the screens for them must never
 * cross: a coordinator opening the membership queue must not cause a single
 * request for volunteer applications, and the other way round. That is not
 * tidiness — `my_queue` on a national site returns hundreds of rows, and a page
 * that fetched both to show one would be paying for the other every time.
 *
 * **And exactness.** The bands are built from the seven states in `states.py`
 * and from decision history, on the server. Nothing here filters a list in the
 * browser, and nothing compares a stage label — a society names its own stages,
 * and the Python side has an AST test that fails the build when one reaches a
 * comparison.
 */

const calls: Array<{ path: string; params: Record<string, unknown> | undefined; key: unknown }> = [];
const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	// The SDK ships CommonJS, so the original namespace is `{ default, ... }`
	// and spreading it would hand back a module with no named exports at all —
	// `FrappeProvider` included, which the harness mounts.
	const actual = (await importOriginal()) as { default: Record<string, unknown> };

	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (
			path: string,
			params?: Record<string, unknown>,
			swrKey?: string | null,
		) => {
			// `swrKey === null` is how this codebase says "do not ask". Honoured,
			// so a screen that must never call the other registration's endpoint
			// fails here the same way it would fail in a browser — and the call is
			// not recorded, because it never happens.
			if (swrKey === null) {
				return {
					data: undefined,
					error: null,
					isLoading: false,
					isValidating: false,
					mutate: () => Promise.resolve(undefined),
				};
			}

			calls.push({ path, params, key: swrKey });

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

const { MembershipQueue, VolunteerQueue } = await import("./ReviewQueue");

function application(over: Partial<ApprovalStatus> = {}): ApprovalStatus {
	return {
		doctype: "VMMS Volunteer Application",
		name: "APP-0001",
		state: "In Review",
		is_open: true,
		is_terminal: false,
		geo_node: "GEO-1",
		geo_path: "Geita — Tanzania Red Cross Society",
		applicant: {
			doctype: "Red Profile",
			name: "RP-1",
			red_profile: "RP-1",
			full_name: "Asha Mwangi",
			email: "asha@example.com",
			phone: null,
			photo: null,
		},
		stage: {
			name: "row-1",
			sequence: 1,
			label: "Branch review",
			required_role: "Volunteer Approver",
			completion_rule: "single",
			can_reject: true,
			is_optional: false,
			entered_on: "2026-08-20",
			due_on: "2026-08-25",
			is_breached: false,
			days_overdue: 0,
			is_blocked: false,
		},
		can_act: true,
		approver_count: 1,
		approvers: ["approver@example.com"],
		escalated_to: null,
		allow_withdrawal: true,
		can_withdraw: false,
		decisions: [],
		...over,
	} as ApprovalStatus;
}

function show(element: React.ReactNode, route: string) {
	return mount(<Routes>
		<Route path="*" element={element} />
	</Routes>, { route });
}

beforeEach(() => {
	calls.length = 0;
	reads.clear();
});

describe("the two queues never touch each other's endpoints", () => {
	it("asks for volunteer applications only, on the volunteer page", () => {
		reads.set(API.myCases, { group: "in_review", count: 1, total: 1, cases: [application()] });

		show(<VolunteerQueue />, "/admin/queue/volunteers");

		const cases = calls.filter((call) => call.path === API.myCases);

		expect(cases).toHaveLength(1);
		expect(cases[0].params).toEqual({
			doctype: "VMMS Volunteer Application",
			group: "in_review",
			limit: 25,
			offset: 0,
		});
		// The other registration's doctype must not appear in any argument.
		expect(JSON.stringify(calls)).not.toContain("VMMS Membership");
	});

	it("asks for memberships only, on the membership page", () => {
		reads.set(API.myCases, { group: "in_review", count: 0, total: 0, cases: [] });

		show(<MembershipQueue />, "/admin/queue/members");

		expect(calls.find((call) => call.path === API.myCases)?.params).toEqual({
			doctype: "VMMS Membership",
			group: "in_review",
			limit: 25,
			offset: 0,
		});
		expect(calls.some((call) => call.path === API.myQueue)).toBe(false);
		expect(JSON.stringify(calls)).not.toContain("VMMS Volunteer Application");
	});
});

describe("the four bands", () => {
	it("opens on In review and offers no personal queue", () => {
		reads.set(API.myCases, { group: "in_review", count: 0, total: 0, cases: [] });

		show(<VolunteerQueue />, "/admin/queue/volunteers");

		expect(screen.getByRole("link", { name: "In review" }).getAttribute("aria-current")).toBe("page");
		expect(screen.queryByRole("link", { name: "Assigned to me" })).toBeNull();
		expect(screen.queryByRole("link", { name: "All applications" })).toBeNull();
	});

	it("reads drafts and changes from my_cases with their own groups", () => {
		reads.set(API.myCases, { group: "drafts", count: 0, cases: [] });

		show(<VolunteerQueue band="drafts" />, "/admin/queue/volunteers/drafts");
		show(<VolunteerQueue band="changes" />, "/admin/queue/volunteers/changes");

		const groups = calls.filter((call) => call.path === API.myCases).map((call) => call.params?.group);

		expect(groups).toEqual(["drafts", "changes"]);
		expect(calls.some((call) => call.path === API.myQueue)).toBe(false);
	});

	it("reads the closed band with the closed group, and narrows it by state", () => {
		reads.set(API.myCases, { group: "closed", count: 0, total: 0, cases: [] });

		show(<MembershipQueue band="closed" />, "/admin/queue/members/closed");

		expect(calls.find((call) => call.path === API.myCases)?.params).toEqual({
			doctype: "VMMS Membership",
			group: "closed",
			limit: 25,
			offset: 0,
		});

		fireEvent.click(screen.getByRole("button", { name: "Rejected" }));

		expect(calls.at(-1)?.params).toEqual({
			doctype: "VMMS Membership",
			group: "closed",
			limit: 25,
			offset: 0,
			state: "Rejected",
		});
		expect(screen.getByRole("button", { name: "Rejected" }).getAttribute("aria-pressed")).toBe("true");
	});

	it("offers all four bands as real routed links from every band", () => {
		reads.set(API.myCases, { group: "closed", count: 0, cases: [] });

		show(<VolunteerQueue band="closed" />, "/admin/queue/volunteers/closed");

		expect(screen.getByRole("link", { name: "In review" }).getAttribute("href")).toBe("/admin/queue/volunteers");
		expect(screen.getByRole("link", { name: "Drafts" }).getAttribute("href")).toBe(
			"/admin/queue/volunteers/drafts",
		);
		expect(screen.getByRole("link", { name: "Changes requested" }).getAttribute("href")).toBe(
			"/admin/queue/volunteers/changes",
		);
		// The one you are standing in is marked for assistive technology, not
		// only in colour.
		expect(screen.getByRole("link", { name: "Closed" }).getAttribute("aria-current")).toBe("page");
	});

	it("points each band at its own registration's routes", () => {
		reads.set(API.myCases, { group: "in_review", count: 0, cases: [] });

		show(<MembershipQueue />, "/admin/queue/members");

		expect(screen.getByRole("link", { name: "Changes requested" }).getAttribute("href")).toBe(
			"/admin/queue/members/changes",
		);
	});
});

describe("searching a queue", () => {
	it("asks the server, inside the band, once typing pauses", async () => {
		vi.useFakeTimers();
		reads.set(API.myCases, { group: "in_review", count: 0, total: 0, cases: [] });

		show(<VolunteerQueue />, "/admin/queue/volunteers");
		fireEvent.change(screen.getByRole("searchbox"), { target: { value: " Asha " } });
		await act(async () => vi.advanceTimersByTime(350));
		vi.useRealTimers();

		expect(calls.at(-1)?.params).toEqual({
			doctype: "VMMS Volunteer Application",
			group: "in_review",
			limit: 25,
			offset: 0,
			search: "Asha",
		});
		expect(screen.getByText("No applications match “Asha”.")).toBeTruthy();
	});
});

describe("what a row shows", () => {
	it("names the applicant rather than the docname, and links to the record", () => {
		reads.set(API.myCases, { group: "in_review", count: 1, total: 1, cases: [application()] });

		show(<VolunteerQueue />, "/admin/queue/volunteers");

		const link = screen.getAllByRole("link", { name: /Asha Mwangi/ })[0];

		expect(link.getAttribute("href")).toBe("/admin/queue/volunteers/APP-0001");
	});

	it("shows the stage label without ever comparing it", () => {
		reads.set(API.myCases, { group: "in_review", count: 1, total: 1, cases: [application()] });

		show(<VolunteerQueue />, "/admin/queue/volunteers");

		// Displayed verbatim. A society that renames this stage tomorrow changes
		// this cell and nothing else in the app.
		expect(screen.getByText("Branch review")).toBeTruthy();
	});

	it("counts the rows the caller may decide, without badging each one", () => {
		reads.set(API.myCases, {
			group: "in_review",
			count: 2,
			total: 2,
			cases: [application(), application({ name: "APP-0002", can_act: false })],
		});

		show(<VolunteerQueue />, "/admin/queue/volunteers");

		// Counted once in the heading; the rows carry no badge.
		expect(screen.queryByText("Your decision")).toBeNull();
		expect(screen.getByText("1 for your decision")).toBeTruthy();
	});

	it("calls a draft sent back for changes what it is, not Draft", () => {
		reads.set(API.myCases, {
			group: "changes",
			count: 2,
			cases: [
				application({ name: "APP-0003", state: "Draft", is_open: false, stage: null, sent_back: true }),
				application({ name: "APP-0004", state: "Draft", is_open: false, stage: null, sent_back: false }),
			],
		});

		show(<VolunteerQueue band="changes" />, "/admin/queue/volunteers/changes");

		// The tab is called Changes requested too, so read the rows themselves.
		const rows = screen.getAllByRole("row").map((row) => row.textContent ?? "");
		expect(rows.filter((text) => text.includes("Changes requested"))).toHaveLength(1);
		expect(rows.filter((text) => text.includes("Draft"))).toHaveLength(1);
	});

	it("reports an overdue row from the engine's own breach flag", () => {
		reads.set(API.myCases, {
			group: "in_review",
			count: 1,
			total: 1,
			cases: [application({ stage: { ...application().stage!, is_breached: true, days_overdue: 6 } })],
		});

		show(<VolunteerQueue />, "/admin/queue/volunteers");

		expect(screen.getByText("6 days over")).toBeTruthy();
		expect(screen.getByText("1 overdue")).toBeTruthy();
	});

	it("shows the exact state and the last decision in a closed band", () => {
		reads.set(API.myCases, {
			group: "closed",
			count: 1,
			cases: [
				application({
					state: "Rejected",
					is_open: false,
					is_terminal: true,
					stage: null,
					can_act: false,
					decisions: [
						{
							stage: "row-1",
							stage_sequence: 1,
							stage_label: "Branch review",
							approver: "approver@example.com",
							decision: "Rejected",
							reason: "Incomplete identification",
							decided_on: "2026-08-24",
						},
					],
				}),
			],
		});

		show(<VolunteerQueue band="closed" />, "/admin/queue/volunteers/closed");

		// One of the seven exact states, and the decision that produced it.
		expect(screen.getAllByText("Rejected").length).toBeGreaterThan(0);
		expect(screen.getByText("Branch review")).toBeTruthy();
	});
});
