import { useContext, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import type { BranchTransfer } from "../portal/types";
import { Field, SelectInput, TextArea, TextInput } from "../ui/form";
import { Icon } from "../ui/icons";
import { Button, cx } from "../ui/primitives";

interface Answer {
	branch: string | null;
	can_raise: boolean;
	approved_by_branches: boolean;
	transfer: BranchTransfer | null;
}

/**
 * Moving this volunteer to another branch, from their record.
 *
 * Kept closed at the foot of the notes tab on purpose: it is an occasional act,
 * and most transfers start with the volunteer asking from their own profile.
 * Drawn only for somebody who may raise one here — `can_raise`, the transfer's
 * own permission asked of where the volunteer is today — or when one is
 * already under way, which it then reports instead of offering a second.
 *
 * Raising it is the release: it goes straight to the branch they are moving
 * to, where the society routes transfers for approval.
 */
export function MoveVolunteer({ volunteer, name }: { volunteer: string; name: string }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const answer = useFrappeGetCall<{ message: Answer }>(
		API.volunteerTransfer,
		{ volunteer },
		`admin:volunteer:${volunteer}:transfer`,
	);
	const places = useFrappeGetCall<{ message: { labels: Record<string, string> } }>(
		API.countyMap,
		undefined,
		"locations:county_map",
	);

	const [expanded, setExpanded] = useState(false);
	const [to, setTo] = useState("");
	const [onDate, setOnDate] = useState(() => new Date().toISOString().slice(0, 10));
	const [reason, setReason] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const state = answer.data?.message;
	const labels = useMemo(() => places.data?.message?.labels ?? {}, [places.data]);
	const choices = useMemo(
		() =>
			Object.entries(labels)
				.filter(([node]) => node !== state?.branch)
				.sort(([, a], [, b]) => a.localeCompare(b)),
		[labels, state?.branch],
	);

	if (!state || (!state.can_raise && !state.transfer)) return null;

	const destination = labels[to] ?? "";

	const raise = async () => {
		if (!to) return setFailure("Choose the branch they are moving to.");
		if (!reason.trim()) return setFailure("Say why they are moving.");

		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.requestTransfer, {
				volunteer,
				to_geo_node: to,
				effective_date: onDate,
				reason: reason.trim(),
			});
			setReason("");
			setTo("");
			await answer.mutate();
		} catch (error) {
			setFailure(errorMessage(error, "The transfer was not raised."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<section className="mt-10 rounded-2xl border border-card-line bg-white">
			<button
				type="button"
				aria-expanded={expanded}
				aria-controls="move-volunteer"
				onClick={() => setExpanded(!expanded)}
				className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left"
			>
				<span>
					<span className="block text-[14px] font-bold text-ink">Move to another branch</span>
					<span className="block text-[12.5px] text-muted">Raise a branch transfer</span>
				</span>
				<Icon.chevron size={16} className={cx("flex-none text-muted transition", expanded && "rotate-180")} />
			</button>

			{expanded && (
				<div id="move-volunteer" className="border-t border-card-line px-5 py-5">
					{state.transfer ? (
						<p className="text-[13px] text-ink">
							A transfer to {state.transfer.to_place} is already open
							{state.transfer.waiting_on ? `, waiting for ${state.transfer.waiting_on}` : ""}.{" "}
							<Link to="/admin/transfers?tab=outgoing" className="font-semibold underline underline-offset-2">
								Open branch transfers
							</Link>
						</p>
					) : (
						<div className="space-y-4">
							<div className="grid gap-4 sm:grid-cols-2">
								<Field label="Branch to move to" htmlFor="move-to" required>
									<SelectInput
										id="move-to"
										value={destination}
										onChange={(label) => setTo(choices.find(([, text]) => text === label)?.[0] ?? "")}
										options={choices.map(([, text]) => text)}
										placeholder="Choose a branch"
									/>
								</Field>
								<Field label="From" htmlFor="move-on" required>
									<TextInput id="move-on" type="date" value={onDate} onChange={setOnDate} />
								</Field>
							</div>
							<Field label="Reason" htmlFor="move-reason" required>
								<TextArea id="move-reason" value={reason} onChange={setReason} rows={3} />
							</Field>
							<p className="text-[12.5px] text-muted">
								{state.approved_by_branches
									? `${destination || "The branch they are moving to"} decides next. ${name} is emailed.`
									: `${name} moves on that date. ${name} is emailed.`}
							</p>
							<Button variant="navy" onClick={() => void raise()} busy={busy}>
								Raise transfer
							</Button>
						</div>
					)}
					{failure && <p className="mt-3 text-[12.5px] text-action">{failure}</p>}
				</div>
			)}
		</section>
	);
}
