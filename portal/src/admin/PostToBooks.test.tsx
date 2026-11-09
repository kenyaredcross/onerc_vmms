import { act, fireEvent, screen } from "@testing-library/react";
import { FrappeContext } from "frappe-react-sdk";
import { describe, expect, it, vi } from "vitest";

import { API } from "../lib/api";
import { mount } from "../test/harness";
import type { MembershipRow } from "../portal/types";
import { PostToBooks } from "./PostToBooks";

/**
 * Accounts staff post a paid fee to ERPNext from the membership review. The
 * button appears only when the server says the fee is due and not yet posted,
 * and a refusal is shown in its own words rather than swallowed.
 */

function panel(canPost: boolean, answer: unknown = { message: { posted: true } }) {
	const post = vi.fn(() => Promise.resolve(answer));
	const onPosted = vi.fn();
	const row = { name: "VM-MSH-1", can_post_to_books: canPost } as unknown as MembershipRow;
	mount(
		<FrappeContext.Provider value={{ call: { post } } as never}>
			<PostToBooks row={row} onPosted={onPosted} />
		</FrappeContext.Provider>,
	);
	return { post, onPosted };
}

describe("posting a fee to the books", () => {
	it("is not offered unless the server allows it", () => {
		panel(false);
		expect(screen.queryByRole("button", { name: "Post to accounts" })).toBeNull();
	});

	it("posts and refreshes the review", async () => {
		const { post, onPosted } = panel(true);
		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Post to accounts" }));
		});
		expect(post).toHaveBeenCalledWith(API.postMembershipPayment, { name: "VM-MSH-1" });
		expect(onPosted).toHaveBeenCalled();
	});

	it("shows why a posting did not go", async () => {
		panel(true, {
			message: { posted: false, reason: "Choose the ERPNext mode of payment for the payment method M-Pesa." },
		});
		await act(async () => {
			fireEvent.click(screen.getByRole("button", { name: "Post to accounts" }));
		});
		expect(screen.getByText(/Choose the ERPNext mode of payment/)).toBeTruthy();
	});
});
