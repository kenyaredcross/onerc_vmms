import { useContext, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import type { BranchTransfer } from "../portal/types";
import { Button, Card, ConfirmDialog, Empty, ErrorNote, PageHeading, Pill, Spinner, Tabs, cx } from "../ui/primitives";

type Direction = "incoming" | "outgoing";
type Show = "open" | "decided";

/**
 * Volunteers moving between branches, from where this coordinator sits.
 *
 * **Two lists because a transfer asks two branches two different things.** The
 * branch a volunteer is leaving is asked to release them; the branch they are
 * joining is asked to take them. Outgoing is the first, Incoming the second,
 * and each row says whose turn it is. Approve is offered only on a row that is
 * this person's to decide — `can_act`, the engine's own answer — so an incoming
 * transfer is visible from the moment it is asked for, and decidable from the
 * moment it is released.
 */
export default function Transfers() {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [params, setParams] = useSearchParams();
	const counts = useFrappeGetCall<{ message: Record<Direction, { open: number; mine: number }> }>(
		API.transferCounts,
		undefined,
		"admin:transfers:counts",
	);
	const mine = counts.data?.message;
	// Open on whichever list has something waiting on this person; Incoming when
	// neither does, because that is the one a coordinator is asked about most.
	const fallback: Direction = mine && mine.outgoing.mine > 0 && mine.incoming.mine === 0 ? "outgoing" : "incoming";
	const direction = (params.get("tab") as Direction) || fallback;
	const show = (params.get("show") as Show) || "open";

	const list = useFrappeGetCall<{ message: { rows: BranchTransfer[] } }>(
		API.branchTransfers,
		{ direction, show },
		`admin:transfers:${direction}:${show}`,
	);

	const set = (key: string, value: string) => {
		const next = new URLSearchParams(params);
		next.set(key, value);
		setParams(next, { replace: true });
	};

	const refresh = () => {
		void list.mutate();
		void counts.mutate();
	};

	const rows = list.data?.message?.rows ?? [];

	return (
		<>
			<PageHeading
				eyebrow={<EditableText k="admin.people.eyebrow" fallback="People" />}
				title={<EditableText k="admin.transfers.heading" fallback="Branch transfers" />}
			/>

			<div className="mb-5 flex flex-wrap items-center justify-between gap-3">
				<Tabs
					active={direction}
					onSelect={(key) => set("tab", key)}
					tabs={[
						{ key: "incoming", label: "Incoming", count: mine?.incoming.open },
						{ key: "outgoing", label: "Outgoing", count: mine?.outgoing.open },
					]}
				/>
				<Tabs
					active={show}
					onSelect={(key) => set("show", key)}
					tabs={[
						{ key: "open", label: "Waiting" },
						{ key: "decided", label: "Decided" },
					]}
				/>
			</div>

			{list.isLoading ? (
				<Spinner label="Loading transfers…" />
			) : list.error ? (
				<ErrorNote>{errorMessage(list.error)}</ErrorNote>
			) : rows.length === 0 ? (
				<Empty title={emptyTitle(direction, show)} />
			) : (
				<ul className="space-y-3">
					{rows.map((row) => (
						<li key={row.name}>
							<TransferRow row={row} direction={direction} call={call} onDecided={refresh} />
						</li>
					))}
				</ul>
			)}
		</>
	);
}

function emptyTitle(direction: Direction, show: Show): string {
	if (show === "decided") return "No transfers decided yet";
	return direction === "incoming" ? "Nobody is waiting to join your branch" : "Nobody is waiting to leave your branch";
}

function TransferRow({
	row,
	direction,
	call,
	onDecided,
}: {
	row: BranchTransfer;
	direction: Direction;
	call: FrappeConfig["call"];
	onDecided: () => void;
}) {
	const [asking, setAsking] = useState<"approve" | "decline" | null>(null);
	const [reason, setReason] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const decide = async () => {
		if (asking === "decline" && !reason.trim()) {
			setFailure("Say why, so the volunteer knows.");
			return;
		}

		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.decide, {
				doctype: "VMMS Branch Transfer",
				name: row.name,
				decision: asking === "approve" ? "Approved" : "Rejected",
				reason: reason.trim() || undefined,
			});
			setAsking(null);
			setReason("");
			onDecided();
		} catch (error) {
			setFailure(errorMessage(error, "That decision was not recorded."));
		} finally {
			setBusy(false);
		}
	};

	const approveText =
		direction === "outgoing"
			? `${row.volunteer_name} is released to ${row.to_place}. ${row.to_place} decides next.`
			: `${row.volunteer_name} moves from ${row.from_place} to ${row.to_place}.`;

	return (
		<Card>
			<div className="flex flex-wrap items-start justify-between gap-3">
				<div className="min-w-0">
					<Link
						to={`/admin/registry/volunteers/${encodeURIComponent(row.volunteer)}`}
						className="text-[15.5px] font-semibold tracking-tight text-ink hover:underline"
					>
						{row.volunteer_name}
					</Link>
					<p className="mt-0.5 text-[13px] text-slate-body">
						{row.from_place} <span aria-hidden="true">→</span>
						<span className="sr-only">to</span> {row.to_place}
					</p>
				</div>
				<Status row={row} />
			</div>

			{row.reason && <p className="mt-3 whitespace-pre-wrap text-[13px] leading-relaxed text-ink">{row.reason}</p>}

			<p className="mt-2 text-[12px] text-muted">
				{row.requested_by_volunteer ? "Asked for by the volunteer" : "Raised by the branch"}
				{row.requested_on ? ` · ${row.requested_on}` : ""}
				{row.decision_reason && row.approval_state === "Rejected" ? ` · Reason: ${row.decision_reason}` : ""}
			</p>

			{row.can_act && (
				<div className="mt-4 flex flex-wrap gap-2 border-t border-card-line pt-4">
					<Button variant="navy" onClick={() => setAsking("approve")}>
						Approve
					</Button>
					<Button variant="quiet" onClick={() => setAsking("decline")}>
						Decline
					</Button>
				</div>
			)}

			{failure && !asking && <p className="mt-3 text-[12.5px] text-action">{failure}</p>}

			<ConfirmDialog
				open={asking !== null}
				title={asking === "approve" ? "Approve this transfer?" : "Decline this transfer?"}
				confirmLabel={asking === "approve" ? "Approve" : "Decline"}
				tone={asking === "approve" ? "navy" : "primary"}
				busy={busy}
				onConfirm={() => void decide()}
				onCancel={() => {
					setAsking(null);
					setFailure(null);
				}}
			>
				{asking === "approve" ? (
					<p>{approveText}</p>
				) : (
					<label className="block">
						<span className="mb-1.5 block text-[12.5px] font-semibold text-ink">Reason</span>
						<textarea
							value={reason}
							onChange={(event) => setReason(event.target.value)}
							rows={3}
							className="w-full rounded-lg border border-card-line px-3 py-2 text-[13px] text-ink outline-none focus:border-blue"
						/>
						<span className="mt-1 block text-[12px] text-muted">The volunteer is sent this.</span>
					</label>
				)}
				{failure && <p className="mt-2 text-[12.5px] text-action">{failure}</p>}
			</ConfirmDialog>
		</Card>
	);
}

function Status({ row }: { row: BranchTransfer }) {
	if (row.is_effective) return <Pill tone="navy">Moved</Pill>;
	if (row.approval_state === "Rejected") return <Pill tone="quiet">Declined</Pill>;
	if (row.transfer_status === "Cancelled") return <Pill tone="quiet">Withdrawn</Pill>;
	if (row.approval_state === "Approved") return <Pill tone="signal">Approved · moves {row.effective_date}</Pill>;

	return (
		<span className={cx("text-right text-[12.5px]", row.can_act ? "font-semibold text-ink" : "text-muted")}>
			{row.can_act ? "Waiting for you" : row.waiting_on ? `Waiting for ${row.waiting_on}` : "Waiting"}
			{row.days_waiting > 0 && (
				<span className="block text-[11.5px] font-normal text-muted">
					{row.days_waiting} {row.days_waiting === 1 ? "day" : "days"}
				</span>
			)}
		</span>
	);
}
