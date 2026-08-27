import { Route, Routes } from "react-router-dom";
import { act, fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { ApprovalStatus } from "../portal/types";

/**
 * The decision interface, which is the one screen in this app where a mistake
 * cannot be taken back from the screen itself.
 *
 * **The reads are stubbed here and nowhere else.** `test/harness` deliberately
 * lets requests fail, because what most components must get right is how they
 * render before anything arrives. This screen is the opposite case: what it
 * must get right is how it renders once a *particular* approval state has
 * arrived, and there is no way to put an application into "blocked, escalated,
 * at a stage that may not reject" without saying so.
 *
 * Only `useFrappeGetCall` is replaced. The provider, the router and the content
 * layer are the real ones.
 */
const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	// The SDK ships CommonJS, so the original namespace is `{ default, module.exports }`
	// and spreading it would hand back a module with no named exports at all —
	// `FrappeProvider` included, which the harness mounts. The real exports are
	// the properties of `default`.
	const actual = (await importOriginal()) as { default: Record<string, unknown> };

	return {
		...actual.default,
		default: actual.default,
		// `swrKey === null` is how this codebase says "do not ask". Honoured, so a
		// screen that must never call the other registration's endpoint fails here
		// the same way it would fail in a browser.
		useFrappeGetCall: (path: string, _params?: unknown, swrKey?: string | null) => ({
			data: swrKey === null ? undefined : { message: reads.get(path) },
			error: null,
			isLoading: false,
			isValidating: false,
			mutate: () => Promise.resolve(undefined),
		}),
	};
});

const ApplicationReview = (await import("./ReviewQueue")).default;

const STAGE: NonNullable<ApprovalStatus["stage"]> = {
	name: "row-1",
	sequence: 2,
	label: "Branch Review",
	required_role: "Volunteer Approver",
	completion_rule: "single",
	can_reject: true,
	is_optional: false,
	entered_on: "2026-08-20",
	due_on: "2026-08-25",
	is_breached: false,
	days_overdue: 0,
	is_blocked: false,
};

/** An application in review, carrying only what this screen reads from it. */
function status(overrides: Partial<ApprovalStatus> = {}): ApprovalStatus {
	return {
		doctype: "VMMS Volunteer Application",
		name: "APP-0001",
		state: "In Review",
		is_open: true,
		is_terminal: false,
		geo_node: "GEO-00053",
		geo_path: "Tanzania Red Cross Society › Geita",
		applicant: {
			doctype: "VMMS Red Profile",
			name: "RP-0001",
			red_profile: "RP-0001",
			full_name: "Asha Mwangi",
			email: "asha@example.com",
			phone: null,
			photo: null,
		},
		stage: STAGE,
		can_act: true,
		approver_count: 1,
		approvers: ["national@example.com"],
		escalated_to: [],
		allow_withdrawal: true,
		can_withdraw: false,
		decisions: [],
		...overrides,
	} as ApprovalStatus;
}

function open(state: ApprovalStatus) {
	reads.clear();
	reads.set(API.approvalStatus, state);
	reads.set(API.applicationDecision, {
		full_name: state.applicant?.full_name,
		applied_on: "2026-08-19",
		answers: [],
		skills: [],
		languages: [],
		availability: [],
		motivation: [],
	});

	return mount(
		<Routes>
			<Route path="/admin/queue/:kind/:name" element={<ApplicationReview />} />
		</Routes>,
		{ route: `/admin/queue/volunteers/${state.name}?tab=decision` },
	);
}

async function choose(label: RegExp) {
	await act(async () => screen.getByRole("button", { name: /Decide/ }).click());
	await act(async () => screen.getByRole("menuitem", { name: label }).click());
}

function give(reason: string) {
	fireEvent.change(screen.getByLabelText(/Reason/), { target: { value: reason } });
}

function submit(name: RegExp) {
	return screen.getByRole("button", { name }) as HTMLButtonElement;
}

describe("deciding on an application", () => {
	beforeEach(() => reads.clear());

	it("will not send a rejection without a reason, and says why", async () => {
		open(status());
		await choose(/Decline/);

		expect(submit(/Decline this volunteer applicant/).disabled).toBe(true);
		expect(screen.getByText(/Declining needs a reason/)).toBeTruthy();

		give("Not eligible this cycle.");
		expect(submit(/Decline this volunteer applicant/).disabled).toBe(false);
	});

	it("will not send an application back without telling the applicant what to fix", async () => {
		open(status());
		await choose(/Ask for more/);

		expect(submit(/Ask this volunteer applicant for more/).disabled).toBe(true);
		expect(screen.getByText(/Say what is missing/)).toBeTruthy();

		give("Attach a national ID.");
		expect(submit(/Ask this volunteer applicant for more/).disabled).toBe(false);
	});

	it("treats whitespace as no reason at all", async () => {
		open(status());
		await choose(/Decline/);

		give("   \n  ");
		expect(submit(/Decline this volunteer applicant/).disabled).toBe(true);
	});

	it("lets an approval through without one", async () => {
		open(status());
		await choose(/Approve/);

		expect(submit(/Approve this volunteer applicant/).disabled).toBe(false);
		expect(screen.getByText(/Reason \(optional\)/)).toBeTruthy();
	});

	it("offers no rejection at a stage that may only endorse", async () => {
		open(status({ stage: { ...STAGE, can_reject: false } }));

		await act(async () => screen.getByRole("button", { name: /Decide/ }).click());

		expect(screen.queryByRole("menuitem", { name: /Decline/ })).toBeNull();
		expect(screen.getByRole("menuitem", { name: /Approve/ })).toBeTruthy();
	});

	it("offers nothing at all to somebody this document is not routed to", () => {
		open(status({ can_act: false }));

		expect(screen.queryByRole("button", { name: /Decide/ })).toBeNull();
		expect(screen.getByText(/holding the role is not the same as being this document's/)).toBeTruthy();
	});

	/**
	 * Twenty-five of Tanzania's thirty-one branches have nobody holding the
	 * approver role at branch level, so the engine enters the stage blocked and
	 * escalates upward. Every other thing on this screen reads as an ordinary
	 * stage, and an approver who is not told cannot tell an unstaffed branch
	 * from a normal assignment.
	 */
	it("says so when the stage found nobody and escalated", () => {
		open(
			status({
				stage: { ...STAGE, is_blocked: true },
				escalated_to: ["national@example.com"],
			}),
		);

		const note = screen.getByText(/Nobody holds/);
		expect(note.textContent).toContain("Volunteer Approver");
		expect(note.textContent).toContain("national@example.com");
	});

	it("says nothing of the sort when the stage resolved somebody", () => {
		open(status());

		expect(screen.queryByText(/Nobody holds/)).toBeNull();
	});
});
