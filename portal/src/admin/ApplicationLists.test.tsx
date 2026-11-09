import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { API } from "../lib/api";
import { mount } from "../test/harness";

const { requests } = vi.hoisted(() => ({ requests: [] as Array<{path: string; params: Record<string, unknown>}> }));
vi.mock("frappe-react-sdk", async (original) => {
	const actual = (await original()) as {default: Record<string, unknown>};
	return {...actual.default, default: actual.default,
		useFrappeGetCall: (path: string, params: Record<string, unknown> = {}, key?: string | null) => {
			if (key !== null) requests.push({path, params});
			const offset = Number(params.offset ?? 0);
			const row = {name: offset ? "APP-26" : "APP-1", doctype: params.doctype, state: "In Review", is_open: true,
				is_terminal: false, geo_path: "Kenya · County", applicant: {full_name: offset ? "Second page applicant" : "Unassigned applicant"},
				stage: null, decisions: [], can_act: false, approvers: [], approver_count: 0, escalated_to: [], allow_withdrawal: false, can_withdraw: false};
			const message = path === API.myQueue ? [] : path === API.myCases ? {group: params.group, count: 1, total: 951, has_more: !offset, cases: [row]} : null;
			return {data: key === null ? undefined : {message}, isLoading: false, error: null};
		},
	};
});
const { VolunteerQueue, MembershipQueue } = await import("./ReviewQueue");
beforeEach(() => { requests.length = 0; });
describe("application lists without personal assignments", () => {
	it.each(["volunteer", "member"])("shows %s applications in review even with no personal assignments", (kind) => {
		mount(kind === "volunteer" ? <VolunteerQueue /> : <MembershipQueue />);
		expect(screen.getByText("Unassigned applicant")).toBeTruthy();
		expect(screen.getByText("951 applications")).toBeTruthy();
		expect(screen.queryByRole("link", {name: "Assigned to me"})).toBeNull();
		expect(requests.some((request) => request.path === API.myCases && request.params.group === "in_review")).toBe(true);
		expect(requests.some((request) => request.path === API.myQueue)).toBe(false);
	});
	it("loads the next scoped page", () => {
		mount(<VolunteerQueue />);
		// In review knows its total, so it pages by number like the registers.
		fireEvent.click(screen.getByRole("button", {name: "2"}));
		expect(screen.getByText("Second page applicant")).toBeTruthy();
		expect(requests.some((request) => request.path === API.myCases && request.params.offset === 25)).toBe(true);
	});
});
