import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mount } from "../test/harness";
import { ReceiptSheet } from "./Receipt";
import type { MembershipReceipt } from "./types";

const PAID: MembershipReceipt = {
	receipt_number: "ACC-PAY-2026-00012",
	society: "Kenya Red Cross Society",
	logo: "/files/logo.png",
	paid_on: "2026-11-08 10:15:00",
	member: { name: "Amina Otieno", member_number: "VM-MEM-26-000123" },
	phone: "254711000222",
	membership: {
		name: "VM-MSH-2026-00045",
		type: "Ordinary member",
		branch: "Nairobi",
		valid_from: "2026-11-08",
		valid_to: "2027-11-07",
	},
	amount: 500,
	currency: "KES",
	method: "M-Pesa",
	by_phone: true,
	gateway_receipt: "TK8AB12CD3",
	transaction: "OPT-0001",
	sales_invoice: "ACC-SINV-2026-00012",
	payment_entry: "ACC-PAY-2026-00012",
	accounting_status: "Posted",
};

describe("a membership payment receipt", () => {
	it("names the payer, the membership, the amount and the M-Pesa code", () => {
		mount(<ReceiptSheet receipt={PAID} />);

		expect(screen.getByRole("article", { name: "Receipt ACC-PAY-2026-00012" })).toBeTruthy();
		expect(screen.getByText("Amina Otieno")).toBeTruthy();
		expect(screen.getByText("VM-MEM-26-000123")).toBeTruthy();
		expect(screen.getByText("254711000222")).toBeTruthy();
		expect(screen.getByText("Phone number")).toBeTruthy();
		expect(screen.queryByText(/received from/i)).toBeNull();
		expect(screen.queryByText(/phone that paid/i)).toBeNull();
		expect(screen.getByText("Ordinary member")).toBeTruthy();
		expect(screen.getByText("Nairobi")).toBeTruthy();
		expect(screen.getByText("M-Pesa code")).toBeTruthy();
		expect(screen.getByText("TK8AB12CD3")).toBeTruthy();
		expect(screen.getByText("ACC-SINV-2026-00012")).toBeTruthy();
		expect(screen.getByText(/500/)).toBeTruthy();
		expect(screen.getByText("Paid")).toBeTruthy();
	});

	it("leaves out the books when the fee has not been posted", () => {
		mount(
			<ReceiptSheet
				receipt={{ ...PAID, receipt_number: "R-VM-MSH-2026-00045", sales_invoice: null, payment_entry: null, accounting_status: null }}
			/>,
		);

		expect(screen.getByText("R-VM-MSH-2026-00045")).toBeTruthy();
		expect(screen.queryByText("Invoice")).toBeNull();
		expect(screen.queryByText("Payment entry")).toBeNull();
	});

	it("keeps the M-Pesa code line while the code is still on its way", () => {
		mount(<ReceiptSheet receipt={{ ...PAID, gateway_receipt: null }} />);

		expect(screen.getByText("M-Pesa code")).toBeTruthy();
		expect(screen.getByText("Not received yet")).toBeTruthy();
	});
});
