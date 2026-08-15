import { useContext, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import {
	Button,
	Card,
	ErrorNote,
	List,
	ListRow,
	Pill,
	SectionLabel,
	Spinner,
	cx,
} from "../ui/primitives";
import type { DeploymentInvitation } from "./types";

/**
 * Being asked to go somewhere, and answering.
 *
 * Rendered above the volunteer's deployment history on `/deployments`, because
 * the two are the same subject a day apart: what you are being asked to do, and
 * what you have done.
 *
 * **Possessive on the way in, ownership-checked on the way out.**
 * `my_invitations` takes no argument, so this list cannot be pointed at anybody
 * else. `respond_to_invitation` does name a deployment, and the server answers
 * that by checking the roster row belongs to the caller's own volunteer record
 * rather than by checking geo scope, which every volunteer would correctly
 * fail.
 *
 * **An answer is final, and the screen says so before it is given.** The service
 * refuses to overwrite an accepted invitation with a decline: somebody has
 * planned around the answer, and changing it silently underneath them is worse
 * than making the volunteer speak to them. So the buttons disappear once an
 * answer exists rather than staying there to be pressed again.
 *
 * **Declining does not need a reason, but the box is there.** Requiring one
 * would make "I cannot go" a small essay, and the branch mostly needs to know
 * they must find somebody else.
 */
export function Invitations() {
	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: {
			volunteer: string;
			waiting: DeploymentInvitation[];
			answered: DeploymentInvitation[];
		} | null;
	}>(API.myInvitations, undefined, "portal:my_invitations");

	const answer = data?.message;
	const waiting = answer?.waiting ?? [];
	const answered = answer?.answered ?? [];

	if (isLoading) return <Spinner label="Checking for invitations…" />;
	if (error) return <ErrorNote>{errorMessage(error)}</ErrorNote>;
	if (!answer || (waiting.length === 0 && answered.length === 0)) return null;

	return (
		<div className="mb-8 space-y-4">
			{waiting.length > 0 && (
				<div>
					<SectionLabel action={<Pill tone="signal">{waiting.length}</Pill>}>
						Waiting on your answer
					</SectionLabel>

					<ul className="space-y-3">
						{waiting.map((invitation) => (
							<li key={invitation.deployment}>
								<InvitationCard invitation={invitation} onAnswered={() => void mutate()} />
							</li>
						))}
					</ul>
				</div>
			)}

			{answered.length > 0 && (
				<div>
					<SectionLabel>Invitations you have answered</SectionLabel>

					<Card pad={false}>
						<div className="p-2">
							<List>
								{answered.map((invitation) => (
									<ListRow
										key={invitation.deployment}
										lead={
											<span
												className="grid h-9 w-9 flex-none place-items-center rounded-control bg-page text-slate-body"
												aria-hidden="true"
											>
												<Icon.truck size={17} />
											</span>
										}
										title={invitation.title ?? invitation.deployment}
										meta={formatDate(invitation.start_date)}
										trailing={<ResponseBadge response={invitation.response} />}
									/>
								))}
							</List>
						</div>
					</Card>
				</div>
			)}
		</div>
	);
}

function ResponseBadge({ response }: { response: string }) {
	const tone =
		response === "accepted"
			? "border-emerald-300 text-emerald-700 bg-emerald-50/60"
			: response === "declined"
				? "border-hairline-strong text-slate-body bg-page"
				: "border-amber-300 text-amber-700 bg-amber-50/60";

	return (
		<span
			className={cx(
				"inline-flex flex-none items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-[11px] font-bold capitalize",
				tone,
			)}
		>
			<span className="h-1.5 w-1.5 flex-none rounded-full bg-current" aria-hidden="true" />
			{response}
		</span>
	);
}

function InvitationCard({
	invitation,
	onAnswered,
}: {
	invitation: DeploymentInvitation;
	onAnswered: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [note, setNote] = useState("");
	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);

	const respond = async (accept: boolean) => {
		setBusy(accept ? "accept" : "decline");
		setFailure(null);

		try {
			await call.post(API.respondToInvitation, {
				deployment: invitation.deployment,
				// Sent as 1 / 0 rather than true / false: a whitelisted method
				// receives strings over HTTP, and `"false"` is a truthy one. The
				// server coerces it properly either way, and this is the half of
				// that pair the browser controls.
				accept: accept ? 1 : 0,
				note: note || undefined,
			});
			onAnswered();
		} catch (respondError) {
			setFailure(errorMessage(respondError, "That answer was not recorded."));
		} finally {
			setBusy(null);
		}
	};

	return (
		<Card>
			<div className="mb-3 flex flex-wrap items-start justify-between gap-3">
				<div>
					<h3 className="font-display text-[16px] font-extrabold tracking-tight text-ink">
						{invitation.title ?? invitation.deployment}
					</h3>
					<p className="mt-1 text-[12.5px] text-slate-body">
						{formatDate(invitation.start_date)}
						{invitation.end_date ? ` to ${formatDate(invitation.end_date)}` : ""}
					</p>
				</div>
				<ResponseBadge response={invitation.response} />
			</div>

			{invitation.notes && (
				<p className="mb-3 whitespace-pre-wrap text-[13px] leading-relaxed text-slate-strong">
					{invitation.notes}
				</p>
			)}

			{failure && (
				<div className="mb-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<label className="block">
				<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">
					Anything to say (optional)
				</span>
				<textarea
					className="min-h-[72px] w-full resize-y rounded-card border border-hairline-strong px-4 py-3 text-[13.5px] leading-relaxed outline-none transition focus:border-navy"
					value={note}
					onChange={(event) => setNote(event.target.value)}
					placeholder="If you cannot go, it helps to say why."
				/>
			</label>

			<div className="mt-4 flex flex-wrap gap-2">
				<Button disabled={busy !== null} onClick={() => void respond(true)}>
					{busy === "accept" ? "Sending…" : "Accept"}
				</Button>
				<Button variant="quiet" disabled={busy !== null} onClick={() => void respond(false)}>
					{busy === "decline" ? "Sending…" : "I cannot go"}
				</Button>
			</div>

			<p className="mt-2 text-[11.5px] text-slate-faint">
				Whoever asked will be told either way. An answer cannot be changed here afterwards, so
				speak to them if it needs to.
			</p>
		</Card>
	);
}
