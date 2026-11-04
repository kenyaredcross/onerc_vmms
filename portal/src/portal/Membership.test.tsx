import { act, fireEvent, screen } from "@testing-library/react";
import { FrappeContext } from "frappe-react-sdk";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { MembershipRow, PricedType } from "./types";

/**
 * Switching membership type before the fee is paid.
 *
 * A membership paid by phone goes to nobody until the money arrives, so until
 * then the applicant may change their mind about the type. The server says
 * when (`can_change_type`); the plans offer the switch only then, and never
 * once the fee is paid or a prompt is open on the phone.
 */

const reads = new Map<string, unknown>();

vi.mock("frappe-react-sdk", async (importOriginal) => {
	const actual = (await importOriginal()) as { default: Record<string, unknown> };

	return {
		...actual.default,
		default: actual.default,
		useFrappeGetCall: (path: string, _params?: unknown, swrKey?: string | null) => ({
			data: swrKey === null || !reads.has(path) ? undefined : { message: reads.get(path) },
			error: null,
			isLoading: false,
			mutate: () => Promise.resolve(undefined),
		}),
	};
});

const Membership = (await import("./Membership")).default;

function plan(key: string, name: string, amount: number): PricedType {
	return {
		known: true,
		membership_type: key,
		membership_type_name: name,
		description: null,
		amount,
		currency: "KES",
		free: amount === 0,
		is_lifetime: false,
		duration_days: 365,
		billing_cycle: "Yearly",
		requires_approver: true,
		benefits: [],
	};
}

function membership(over: Partial<MembershipRow> = {}): MembershipRow {
	return {
		name: "MSHIP-02410",
		member: "MEM-00001",
		member_name: "STK Test",
		membership_type: "ordinary-member",
		membership_type_name: "Ordinary Member",
		membership_status: "Awaiting Payment",
		is_active: false,
		approval_state: "Submitted",
		approval_settled: false,
		payment_settled: false,
		requires_approver: true,
		is_lifetime: false,
		fee: { amount: 10, currency: "KES" },
		geo_node: "GEO-00001",
		geo_path: "Nairobi",
		valid_from: null,
		valid_to: null,
		paid_on: null,
		payment_receipt: null,
		payment_transaction: "PAY-2026-00002",
		membership_source: "New",
		certificate_available: false,
		renewable: false,
		awaits_gateway_payment: true,
		can_change_type: true,
		switchable_types: ["life-member"],
		...over,
	} as MembershipRow;
}

function show() {
	const post = vi.fn((path: string) =>
		Promise.resolve({
			message:
				path === API.membershipPayment
					? { status: "Failed", settled: false, can_retry: true, amount: 10, currency: "KES" }
					: {},
		}),
	);
	mount(
		<FrappeContext.Provider value={{ call: { post } } as never}>
			<Membership />
		</FrappeContext.Provider>,
	);
	return post;
}

beforeEach(() => {
	reads.clear();
	reads.set(API.membershipTypes, {
		types: [plan("ordinary-member", "Ordinary Member", 10), plan("life-member", "Life Member", 5000)],
		declarations: [],
	});
});

describe("an unpaid membership", () => {
	it("offers the other types, and marks the one already chosen", () => {
		reads.set(API.myMemberships, [membership()]);
		show();

		expect(screen.getByText("Your choice")).toBeTruthy();
		expect(screen.getAllByRole("button", { name: "Switch to this type" })).toHaveLength(1);
		expect(screen.getByText("Your fee is not paid yet. You can switch to another type before you pay.")).toBeTruthy();
		expect(screen.getByRole("link", { name: "Change membership type before you pay" })).toBeTruthy();
	});

	it("sends the type chosen for this membership", async () => {
		reads.set(API.myMemberships, [membership()]);
		const post = show();

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Switch to this type" }));
		});

		expect(post).toHaveBeenCalledWith(API.changeMembershipType, {
			name: "MSHIP-02410",
			membership_type: "life-member",
		});
	});
});

describe("a type the applicant is not eligible for", () => {
	it("is not offered as a switch", () => {
		reads.set(API.membershipTypes, {
			types: [
				plan("ordinary-member", "Ordinary Member", 10),
				plan("life-member", "Life Member", 5000),
				plan("youth-in-school", "Youth In School", 100),
			],
			declarations: [],
		});
		reads.set(API.myMemberships, [membership()]);
		show();

		expect(screen.getAllByRole("button", { name: "Switch to this type" })).toHaveLength(1);
		expect(screen.getByText("Not open to you")).toBeTruthy();
	});
});

describe("a membership that can no longer change type", () => {
	it("offers no switch once the server says no", () => {
		reads.set(API.myMemberships, [
			membership({ membership_status: "Awaiting Approval", awaits_gateway_payment: false, can_change_type: false }),
		]);
		show();

		expect(screen.queryByRole("button", { name: "Switch to this type" })).toBeNull();
		expect(screen.queryByRole("link", { name: /change membership type/i })).toBeNull();
		expect(screen.getAllByText("Application in").length).toBeGreaterThan(0);
	});
});
