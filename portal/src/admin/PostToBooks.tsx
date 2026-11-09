/*
 * Posting one paid membership fee to ERPNext by hand. For accounts staff.
 *
 * A paid fee normally reaches the books by itself, a moment after the payment
 * is confirmed, and the daily job sweeps up any that did not. This button is for
 * the one somebody is looking at now: a posting that failed and whose cause has
 * just been fixed, or a fee paid while posting was switched off.
 *
 * Drawn only when the server says `can_post_to_books` (paid, due, not yet
 * posted, and the reader is accounts staff). The endpoint asks again. A failure
 * comes back as a plain reason, which is shown here and also kept on the
 * membership as its "Not posted" note.
 */

import { useContext, useState } from "react";
import { FrappeContext, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import type { MembershipRow } from "../portal/types";
import { Button, ErrorNote } from "../ui/primitives";

interface PostResult {
	posted: boolean;
	reason?: string | null;
}

export function PostToBooks({ row, onPosted }: { row: MembershipRow; onPosted: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	if (!row.can_post_to_books) return null;

	const post = async () => {
		setBusy(true);
		setFailure(null);

		try {
			const response = await call.post<{ message: PostResult }>(API.postMembershipPayment, { name: row.name });
			const result = response?.message;
			if (result && !result.posted && result.reason) {
				setFailure(result.reason);
			}
			onPosted();
		} catch (error) {
			setFailure(errorMessage(error, "This fee was not posted."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div>
			<Button onClick={() => void post()} disabled={busy}>
				{busy ? "Posting…" : "Post to accounts"}
			</Button>
			<p className="mt-2 text-[12px] text-slate-faint">
				Raises the invoice and its payment in ERPNext, on this branch's cost centre.
			</p>
			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}
		</div>
	);
}
