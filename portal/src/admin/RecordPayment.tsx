/*
 * Recording a membership fee that somebody handed over at a counter.
 *
 * **Why this exists at all.** A society taking cash at a branch could produce a
 * membership that reached Awaiting Payment and stopped there permanently:
 * `onerc_payments` ships the manual driver's confirmation as an API call with
 * no button on any form, and nothing in this product called it. The
 * registration wizard now tells an applicant "your membership starts once the
 * office has recorded it", and this is the office recording it.
 *
 * **It is not an activate button, and the distinction is the whole design.**
 * What it confirms is the *payment*, through the payments app, exactly as a
 * gateway callback would. Whether the membership then goes Active is re-derived
 * from approval and payment together by `membership.on_update`, so a type that
 * routes to an approver moves to Awaiting Approval and waits — which is the
 * correct outcome and not a half-finished one. The panel says so before the
 * button is pressed rather than leaving somebody to wonder why the badge did
 * not change. See `api/member.py::record_membership_payment`.
 *
 * **One component, two homes.** The review screen is where a coordinator lands
 * from the members queue and reads "Settled: Not yet"; the person page is where
 * they land from the register. Both need the same act with the same guards, and
 * a second copy is a second thing to keep in step with the endpoint.
 */

import { useContext, useState } from "react";
import { FrappeContext, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import type { MembershipRow } from "../portal/types";
import { Button, ErrorNote } from "../ui/primitives";

/**
 * Is there a fee here that somebody could still walk in and pay?
 *
 * Five separate answers and every one has to be yes, because each rules out a
 * different membership the button would be wrong on: one that costs nothing,
 * one nobody has been asked to pay yet, one already settled — by cash, by phone,
 * or by the proof a pre-rollout member attached — one that has been cancelled,
 * and a reader who is not the office. The endpoint re-asks all of them and says
 * which failed; this decides only what is painted.
 */
export function owesAFee(row: MembershipRow, canAct: boolean): boolean {
	return Boolean(
		canAct &&
			row.fee &&
			row.fee.amount > 0 &&
			row.payment_transaction &&
			!row.payment_settled &&
			row.membership_status !== "Cancelled",
	);
}

export function RecordPayment({
	row,
	canAct,
	onRecorded,
}: {
	row: MembershipRow;
	canAct: boolean;
	/** Refetch whatever this was drawn from. The status changes underneath it. */
	onRecorded: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [open, setOpen] = useState(false);
	const [receipt, setReceipt] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	if (!owesAFee(row, canAct)) return null;

	const record = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.recordMembershipPayment, { name: row.name, receipt });
			setOpen(false);
			setReceipt("");
			onRecorded();
		} catch (error) {
			setFailure(errorMessage(error, "That payment was not recorded."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div>
			<Button
				onClick={() => {
					setOpen(!open);
					setFailure(null);
				}}
			>
				Record the payment
			</Button>

			{open && (
				<div className="mt-4">
					<label className="block">
						<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
							Receipt or reference number
						</span>
						<input
							value={receipt}
							onChange={(event) => setReceipt(event.target.value)}
							className="w-full rounded-xl border border-card-line px-3 py-2 text-[14px]"
						/>
					</label>

					{/* Optional, and it says so rather than leaving somebody to find
					    out by pressing the button: a branch that took cash and wrote
					    nothing down has still taken the money, and a membership must
					    not sit unsettled for want of a field. */}
					<p className="mt-2 text-[12px] text-slate-faint">
						Optional. Recorded against the payment so the money can be traced back to this
						membership.
					</p>

					{/* What this does and does not do, before it is done. */}
					<p className="mt-2 text-[12px] text-slate-faint">
						{row.requires_approver && !row.approval_settled
							? "This records the fee only. The membership still needs its approver."
							: "The membership becomes active once this is recorded."}
					</p>

					{failure && (
						<div className="mt-3">
							<ErrorNote>{failure}</ErrorNote>
						</div>
					)}

					<div className="mt-3 flex gap-2">
						<Button onClick={() => void record()} disabled={busy}>
							{busy ? "Recording…" : "Record the payment"}
						</Button>
						<Button variant="ghost" onClick={() => setOpen(false)} disabled={busy}>
							Not yet
						</Button>
					</div>
				</div>
			)}
		</div>
	);
}
