import { useContext, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { Field, SelectInput, TextArea } from "../ui/form";
import { Button, Card, SectionTitle } from "../ui/primitives";
import type { BranchTransfer } from "./types";

/**
 * Moving to another branch, from the volunteer's own profile.
 *
 * Three states, one card: nothing asked (a button), asked and waiting (whose
 * turn it is, and a way to take it back), and decided in the last month (what
 * happened, and why when it was declined). The branch they are leaving decides
 * first, then the branch they are joining — the card says which one it is
 * waiting for rather than explaining the rule.
 *
 * `?transfer=<place>` opens the form with that branch chosen: the branch
 * directory's "Ask to move here" sends people here.
 */
export function TransferCard({ branch, active }: { branch: string | null; active: boolean }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [params, setParams] = useSearchParams();
	const requested = params.get("transfer");

	const mine = useFrappeGetCall<{ message: { transfer: BranchTransfer | null; can_request: boolean } }>(
		API.myTransfer,
		undefined,
		"portal:my_transfer",
	);
	const places = useFrappeGetCall<{ message: { labels: Record<string, string> } }>(
		API.countyMap,
		undefined,
		"locations:county_map",
	);

	const [open, setOpen] = useState(false);
	const [to, setTo] = useState(requested ?? "");
	const [reason, setReason] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	useEffect(() => {
		if (requested && mine.data?.message?.can_request) {
			setOpen(true);
			setTo(requested);
		}
	}, [requested, mine.data]);

	const labels = useMemo(() => places.data?.message?.labels ?? {}, [places.data]);
	const choices = useMemo(
		() =>
			Object.entries(labels)
				.filter(([name]) => name !== branch)
				.sort(([, a], [, b]) => a.localeCompare(b)),
		[labels, branch],
	);

	const transfer = mine.data?.message?.transfer ?? null;
	// Only where somebody decides a transfer. A society that applies them
	// directly would move the volunteer the moment they pressed the button.
	const canRequest = active && Boolean(mine.data?.message?.can_request);
	const waiting = transfer && transfer.transfer_status === "Pending";

	const send = async () => {
		if (!to) return setFailure("Choose the branch you would like to move to.");
		if (!reason.trim()) return setFailure("Say why you would like to move.");

		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.requestMyTransfer, { to_geo_node: to, reason: reason.trim() });
			setOpen(false);
			setReason("");
			if (requested) {
				const next = new URLSearchParams(params);
				next.delete("transfer");
				setParams(next, { replace: true });
			}
			await mine.mutate();
		} catch (error) {
			setFailure(errorMessage(error, "Your request was not sent."));
		} finally {
			setBusy(false);
		}
	};

	const withdraw = async () => {
		if (!transfer) return;

		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.withdrawMyTransfer, { name: transfer.name });
			await mine.mutate();
		} catch (error) {
			setFailure(errorMessage(error, "Your request was not withdrawn."));
		} finally {
			setBusy(false);
		}
	};

	if (mine.isLoading) return null;
	if (!canRequest && !transfer) return null;

	return (
		<Card>
			<SectionTitle>Branch transfer</SectionTitle>

			{transfer && waiting ? (
				<div>
					<p className="text-[13.5px] text-ink">
						You asked to move from {transfer.from_place} to {transfer.to_place}.
					</p>
					<p className="mt-1 text-[13px] text-muted">
						{transfer.waiting_on ? `Waiting for ${transfer.waiting_on}.` : "Waiting for a decision."}
					</p>
					<div className="mt-4">
						<Button variant="quiet" onClick={() => void withdraw()} busy={busy}>
							Withdraw request
						</Button>
					</div>
				</div>
			) : open && canRequest ? (
				<div className="space-y-4">
					<Field label="Branch to move to" htmlFor="transfer-to" required>
						<SelectInput
							id="transfer-to"
							value={labels[to] ?? ""}
							onChange={(label) => setTo(choices.find(([, text]) => text === label)?.[0] ?? "")}
							options={choices.map(([, text]) => text)}
							placeholder="Choose a branch"
						/>
					</Field>
					<Field label="Reason" htmlFor="transfer-reason" required>
						<TextArea id="transfer-reason" value={reason} onChange={setReason} rows={3} />
					</Field>
					<p className="text-[12.5px] text-muted">
						Your branch decides first, then the branch you are moving to. We will email you.
					</p>
					<div className="flex flex-wrap gap-2">
						<Button onClick={() => void send()} busy={busy}>
							Send request
						</Button>
						<Button variant="quiet" onClick={() => setOpen(false)} disabled={busy}>
							Cancel
						</Button>
					</div>
				</div>
			) : (
				<div>
					{transfer && <Decided transfer={transfer} />}
					{canRequest && (
						<div className={transfer ? "mt-4" : undefined}>
							<Button variant="soft" onClick={() => setOpen(true)}>
								Request a transfer
							</Button>
						</div>
					)}
				</div>
			)}

			{failure && <p className="mt-3 text-[12.5px] text-action">{failure}</p>}
		</Card>
	);
}

function Decided({ transfer }: { transfer: BranchTransfer }) {
	if (transfer.is_effective) {
		return <p className="text-[13.5px] text-ink">You moved from {transfer.from_place} to {transfer.to_place}.</p>;
	}

	if (transfer.approval_state === "Approved") {
		return (
			<p className="text-[13.5px] text-ink">
				Your move to {transfer.to_place} was approved. It takes effect on {transfer.effective_date}.
			</p>
		);
	}

	if (transfer.approval_state === "Rejected") {
		return (
			<div>
				<p className="text-[13.5px] text-ink">Your request to move to {transfer.to_place} was not approved.</p>
				{transfer.decision_reason && (
					<p className="mt-1 text-[13px] text-muted">Reason: {transfer.decision_reason}</p>
				)}
			</div>
		);
	}

	return <p className="text-[13px] text-muted">You withdrew your request to move to {transfer.to_place}.</p>;
}
