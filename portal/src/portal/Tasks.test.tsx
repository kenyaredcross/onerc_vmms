import { fireEvent, screen, within } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { TaskDetail, TaskSummary } from "./types";

/**
 * The task workflow the brief pins down.
 *
 * A volunteer offers work as done and a coordinator signs it off — so the
 * portal never shows a "Complete" control, only "Submit for review". Coordinator
 * feedback and the volunteer's questions stay in the conversation whatever state
 * the task is in.
 *
 * **Two screens now, not one.** The approved concept splits the register from
 * the record: `/tasks` is the filterable table, `/tasks/:name` is the task's own
 * page and is where every verb lives. The assertions below are the same ones as
 * before; each is now made against the screen that owns the control.
 */

const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };
	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (path: string, _params?: unknown, swrKey?: string | null) => ({
			data: swrKey === null ? undefined : { message: reads.get(path) },
			error: null,
			isLoading: false,
			isValidating: false,
			mutate: () => Promise.resolve(undefined),
		}),
		useFrappeAuth: () => ({
			currentUser: "nigel@example.org",
			isLoading: false,
			logout: () => Promise.resolve(undefined),
		}),
	};
});

const { default: Tasks, TaskRecord } = await import("./Tasks");

function summary(over: Partial<TaskSummary> = {}): TaskSummary {
	return {
		name: "TASK-1",
		subject: "Household assessment forms — Kyela ward 4",
		status: "accepted",
		volunteer: "VOL-1",
		geo_node: "GEO-1",
		due_on: "2026-09-10",
		due_at: "2026-09-10 17:00:00",
		assigned_on: "2026-09-01",
		open_question: false,
		is_open: true,
		priority: "Normal",
		task_type: "Field evidence",
		percent_complete: 40,
		is_overdue: false,
		...over,
	};
}

function detail(over: Partial<TaskDetail> = {}): TaskDetail {
	return {
		...summary(over),
		description: "Complete section 4 on the listed forms.",
		deployment: null,
		project: null,
		batch: null,
		accepted_on: "2026-09-02",
		submitted_on: null,
		closed_on: null,
		completion_notes: null,
		planned_start: null,
		planned_end: null,
		response_deadline: null,
		expected_hours: null,
		actual_hours: null,
		checklist: [],
		checklist_outstanding: [],
		brief_files: [],
		depends_on: [],
		blocking: [],
		blocked_override_reason: null,
		where: {
			work: place(),
			meeting_point: place(),
			travel_instructions: null,
			local_contact: { name: null, phone: null },
			inherited_from: null,
		},
		outcome: null,
		final_evidence: null,
		return_reason: null,
		rework_count: 0,
		manager_rating: null,
		lessons_learned: null,
		decline_reason: null,
		reassigned_to_task: null,
		reassigned_from_task: null,
		reassignment_reason: null,
		thread: [
			{
				entry_type: "assigned",
				author: "Asha",
				posted_on: "2026-09-01",
				note: "Please start soon.",
				proof: null,
			},
			{
				entry_type: "returned",
				author: "Asha",
				posted_on: "2026-09-05",
				note: "Section 4 is blank on 22 forms.",
				proof: null,
			},
		],
		...over,
	};
}

function place() {
	return {
		name: null,
		address: null,
		latitude: null,
		longitude: null,
		has_point: false,
		located_on: null,
		map: null,
		directions: null,
	};
}

/** The record at its own address, the way the router mounts it. */
function record() {
	return mount(
		<Routes>
			<Route path="/tasks/:name" element={<TaskRecord />} />
		</Routes>,
		{ route: "/tasks/TASK-1" },
	);
}

beforeEach(() => {
	reads.clear();
	reads.set(API.myTasks, { volunteer: "VOL-1", tasks: [summary()] });
	reads.set(API.getTask, detail());
});

describe("the task workflow", () => {
	it("offers Submit for review and never a Complete control", () => {
		record();

		expect(screen.getByRole("button", { name: /submit for review/i })).toBeTruthy();
		expect(screen.queryByRole("button", { name: /^complete$/i })).toBeNull();
		expect(screen.queryByRole("button", { name: /mark complete/i })).toBeNull();
	});

	it("keeps coordinator feedback in the conversation", () => {
		record();

		// The conversation is one of the record's tabs.
		fireEvent.click(screen.getByRole("tab", { name: /messages & updates/i }));

		expect(screen.getByText(/changes requested/i)).toBeTruthy();
		expect(screen.getByText(/section 4 is blank/i)).toBeTruthy();
	});

	it("shows a submitted task as waiting on a coordinator, with no work controls", () => {
		reads.set(API.myTasks, { volunteer: "VOL-1", tasks: [summary({ status: "submitted" })] });
		reads.set(API.getTask, detail({ status: "submitted", is_open: false }));

		record();
		fireEvent.click(screen.getByRole("tab", { name: /outcome/i }));

		expect(screen.getByText(/you have offered this as done/i)).toBeTruthy();
		expect(screen.queryByRole("button", { name: /submit for review/i })).toBeNull();
	});

	it("will not offer a submission while a required checklist item is unticked", () => {
		reads.set(
			API.getTask,
			detail({
				checklist: [
					{
						idx: 1,
						item: "Photograph the completed forms",
						is_required: true,
						is_done: false,
						done_on: null,
						notes: null,
						evidence: null,
					},
				],
				checklist_outstanding: ["Photograph the completed forms"],
			}),
		);

		record();

		const submit = screen.getByRole("button", { name: /submit for review/i }) as HTMLButtonElement;
		expect(submit.disabled).toBe(true);
		expect(screen.getByText(/still unticked/i)).toBeTruthy();
	});
});

describe("the task register", () => {
	it("separates the views by the states the server owns", () => {
		mount(<Tasks />);

		const tablist = screen.getByRole("tablist", { name: /task status/i });
		for (const name of ["Active", "Clarifications", "Assigned", "Accepted", "Submitted", "Completed", "All"]) {
			expect(within(tablist).getByRole("tab", { name: new RegExp(name) })).toBeTruthy();
		}
	});

	it("gives every row a real address of its own", () => {
		mount(<Tasks />);

		const row = screen.getByRole("link", { name: /household assessment forms/i });
		expect(row.getAttribute("href")).toBe("/tasks/TASK-1");
	});
});
