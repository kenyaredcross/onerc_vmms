import { act, fireEvent, screen } from "@testing-library/react";
import { FrappeContext } from "frappe-react-sdk";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import type { PaymentProgress } from "../portal/types";
import { mount } from "../test/harness";
import { POLL_EVERY_MS, POLL_FOR, PhonePayment, spacedPhone } from "./PhonePayment";

/**
 * A membership fee paid on the phone: the page waits for M-Pesa, shows the
 * receipt once it arrives, and offers to send the prompt again when one ends
 * unpaid. It never asks for ever.
 */

function progress(overrides: Partial<PaymentProgress> = {}): PaymentProgress {
	return {
		membership: "MSHIP-1",
		membership_status: "Awaiting Payment",
		settled: false,
		status: "Pending",
		receipt: null,
		amount: 1000,
		currency: "KES",
		paid_from: null,
		paid_on: null,
		gateway: "M-Pesa",
		logo: "/assets/vmmsx/images/payments/mpesa.png",
		transaction: "PAY-1",
		failure: null,
		can_retry: false,
		...overrides,
	};
}

function panel(answers: PaymentProgress[], again?: PaymentProgress) {
	const post = vi.fn((method: string) => {
		if (method === API.payMembershipAgain) return Promise.resolve({ message: again });
		const next = answers.length > 1 ? answers.shift() : answers[0];
		return Promise.resolve({ message: next });
	});
	mount(
		<FrappeContext.Provider value={{ call: { post } } as never}>
			<PhonePayment membership="MSHIP-1" message="Check your phone and enter your M-Pesa PIN." phone="0712345678" />
		</FrappeContext.Provider>,
	);
	return post;
}

async function tick(ms: number) {
	await act(async () => {
		await vi.advanceTimersByTimeAsync(ms);
	});
}

describe("paying on the phone", () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});
	afterEach(() => {
		vi.useRealTimers();
	});

	it("waits for the payment, then shows the M-Pesa receipt", async () => {
		const post = panel([
			progress(),
			progress({
				settled: true,
				status: "Completed",
				receipt: "TJK4ABC123",
				paid_from: "254712345678",
				membership_status: "Awaiting Approval",
			}),
		]);
		await tick(0);

		expect(screen.getByText("Check your phone")).toBeTruthy();
		expect(screen.getByText("0712 345 678")).toBeTruthy();
		expect(screen.getByText(/^Check the amount is .*1,000\.$/)).toBeTruthy();
		expect(screen.getByText("Enter your PIN and confirm.")).toBeTruthy();
		expect(document.querySelector('img[src="/assets/vmmsx/images/payments/mpesa.png"]')).toBeTruthy();

		await tick(POLL_EVERY_MS);

		expect(screen.getByText("Payment received")).toBeTruthy();
		expect(screen.getByText("TJK4ABC123")).toBeTruthy();
		expect(screen.getByText(/from 0712 345 678/)).toBeTruthy();
		expect(screen.getByText("Your membership has gone to your branch for approval.")).toBeTruthy();
		expect(post).toHaveBeenCalledWith(API.membershipPayment, { name: "MSHIP-1" });
	});

	it("sends the prompt again after one ends unpaid", async () => {
		const post = panel(
			[progress({ status: "Failed", failure: "Request cancelled by user", can_retry: true })],
			progress({ message: "Check your phone and enter your M-Pesa PIN." }),
		);
		await tick(0);

		expect(screen.getByText("The payment did not go through")).toBeTruthy();
		expect(screen.getByText("Request cancelled by user")).toBeTruthy();

		fireEvent.change(screen.getByLabelText("Phone number to pay from"), { target: { value: "0722000111" } });
		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Send the payment request again" }));
		});

		expect(post).toHaveBeenCalledWith(API.payMembershipAgain, { name: "MSHIP-1", payer_phone: "0722000111" });
		expect(screen.getByText("Check your phone")).toBeTruthy();
	});

	it("stops asking after a while and offers to check again", async () => {
		const post = panel([progress()]);
		await tick(0);
		for (let poll = 0; poll < POLL_FOR + 2; poll += 1) await tick(POLL_EVERY_MS);

		expect(screen.getByText("We have not received your payment yet")).toBeTruthy();
		const asked = post.mock.calls.length;
		expect(asked).toBe(POLL_FOR);

		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Check again" }));
		});
		expect(post.mock.calls.length).toBe(asked + 1);
	});
});

describe("phone numbers as people read them", () => {
	it("turns the gateway's international form back into the local one", () => {
		expect(spacedPhone("254727118702")).toBe("0727 118 702");
		expect(spacedPhone("+254 727 118 702")).toBe("0727 118 702");
		expect(spacedPhone("0110123456")).toBe("0110 123 456");
	});

	it("leaves anything else as it came", () => {
		expect(spacedPhone("+44 20 7946 0958")).toBe("+44 20 7946 0958");
		expect(spacedPhone(null)).toBe("");
	});
});
