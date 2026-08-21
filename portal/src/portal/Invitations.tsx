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
import type { DeploymentInvitation, MyAssignment } from "./types";

/**
 * Being asked to go somewhere, and answering.
 *
 * Rendered above the volunteer's deployment history on `/deployments`, because
 * the two are the same subject a day apart: what you are being asked to do, and
 * what you have done.
 *
 * **Accepting is accepting the terms of reference, and this screen shows them.**
 * There is no separate contract in this app — the terms *are* the contract,
 * which is why they are submittable and why the assignment records exactly which
 * document was put in front of this person. Asking somebody to agree to a title
 * would make the whole arrangement worthless, so the mission is one press away
 * and is fetched on demand: most people accept the branch duty they already
 * discussed by phone, and making every card carry a whole mission document would
 * cost everybody for the few who read it.
 *
 * **Possessive on the way in, ownership-checked on the way out.**
 * `my_invitations` takes no argument, so this list cannot be pointed at anybody
 * else. `respond_to_assignment` does name a record, and the server answers that
 * by checking the assignment belongs to the caller's own volunteer record rather
 * than by checking geo scope, which every volunteer would correctly fail.
 *
 * **An answer is final, and the screen says so before it is given.** The service
 * refuses to overwrite an accepted assignment with a decline: somebody has
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
							<li key={invitation.assignment}>
								<InvitationCard invitation={invitation} onAnswered={() => void mutate()} />
							</li>
						))}
					</ul>
				</div>
			)}

			{answered.length > 0 && (
				<div>
					<SectionLabel>Deployments you have answered</SectionLabel>

					<Card pad={false}>
						<div className="p-2">
							<List>
								{answered.map((invitation) => (
									<ListRow
										key={invitation.assignment}
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
		response === "Accepted"
			? "border-emerald-300 text-emerald-700 bg-emerald-50/60"
			: response === "Declined" || response === "Withdrawn"
				? "border-hairline-strong text-slate-body bg-page"
				: "border-amber-300 text-amber-700 bg-amber-50/60";

	return (
		<span
			className={cx(
				"inline-flex flex-none items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-[11px] font-bold",
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
	const [reading, setReading] = useState(false);
	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);

	const respond = async (accept: boolean) => {
		setBusy(accept ? "accept" : "decline");
		setFailure(null);

		try {
			await call.post(API.respondToAssignment, {
				assignment: invitation.assignment,
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
					{invitation.role === "leader" && (
						<p className="mt-1.5 text-[12px] font-semibold text-signal">
							You are being asked to lead this one.
						</p>
					)}
				</div>
				<ResponseBadge response={invitation.response} />
			</div>

			{invitation.notes && (
				<p className="mb-3 whitespace-pre-wrap text-[13px] leading-relaxed text-slate-strong">
					{invitation.notes}
				</p>
			)}

			<div className="mb-3 rounded-card border border-hairline bg-page px-4 py-3">
				<button
					type="button"
					aria-expanded={reading}
					onClick={() => setReading((was) => !was)}
					className="flex w-full items-center justify-between gap-3 text-left"
				>
					<span className="text-[12.5px] font-semibold text-ink">
						{reading ? "Hide the terms of reference" : "Read the terms of reference"}
					</span>
					<span className="text-[11.5px] font-semibold text-navy">{reading ? "Hide" : "Read"}</span>
				</button>

				<p className="mt-1 text-[11.5px] text-slate-faint">
					Accepting this is accepting these terms. They are what the society has written down about
					the mission, and they cannot be changed afterwards without your being asked again.
				</p>

				{reading && <Mission assignment={invitation.assignment} />}
			</div>

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
					{busy === "accept" ? "Sending…" : "Accept these terms"}
				</Button>
				<Button variant="quiet" disabled={busy !== null} onClick={() => void respond(false)}>
					{busy === "decline" ? "Sending…" : "I cannot go"}
				</Button>
			</div>

			<p className="mt-2 text-[11.5px] text-slate-faint">
				Whoever asked will be told either way. An answer cannot be changed here afterwards, so speak
				to them if it needs to.
			</p>
		</Card>
	);
}

/**
 * The mission a volunteer is being asked to agree to.
 *
 * **Fetched when it is opened, not with the card.** Most people accept work
 * they already discussed; loading a whole mission document for every invitation
 * on the page would make the common case pay for the careful one.
 *
 * The terms read here are the ones the *assignment* names, not whatever the
 * deployment currently points at. Those are the same today and need not be
 * tomorrow — that is the whole reason a terms of reference is submittable, and
 * what somebody is agreeing to is the document they were sent.
 */
function Mission({ assignment }: { assignment: string }) {
	const { data, error, isLoading } = useFrappeGetCall<{ message: MyAssignment }>(
		API.getMyAssignment,
		{ assignment },
		`portal:assignment:${assignment}`,
	);

	if (isLoading) return <Spinner label="Loading the terms…" />;
	if (error) return <ErrorNote>{errorMessage(error)}</ErrorNote>;

	const terms = data?.message?.terms;

	if (!terms) return null;

	return (
		<div className="mt-3 space-y-3 border-t border-hairline pt-3">
			{terms.mission_background && (
				<Part title="Background">
					{/* The society's own rich text, written on the desk by a coordinator
					    and stored as markup. Inserted as markup for the same reason the
					    coordinator's own preview does: it is authored configuration on
					    the footing of an Email Template, not something typed into a
					    public form. */}
					<div
						className="prose-vmms text-[12.5px] leading-relaxed text-slate-body"
						// eslint-disable-next-line react/no-danger
						dangerouslySetInnerHTML={{ __html: terms.mission_background }}
					/>
				</Part>
			)}

			{terms.purpose && <Part title="Purpose">{terms.purpose}</Part>}

			{terms.objectives.length > 0 && (
				<Part title="Objectives">
					<ol className="list-decimal space-y-1 pl-4">
						{terms.objectives.map((row, index) => (
							<li key={index}>{row.objective}</li>
						))}
					</ol>
				</Part>
			)}

			{terms.expected_outputs.length > 0 && (
				<Part title="What it should achieve">
					<ul className="list-disc space-y-1 pl-4">
						{terms.expected_outputs.map((row, index) => (
							<li key={index}>{row.output}</li>
						))}
					</ul>
				</Part>
			)}

			{terms.responsibilities && (
				<Part title="What you would be doing">
					<span className="whitespace-pre-line">{terms.responsibilities}</span>
				</Part>
			)}

			{terms.itinerary.length > 0 && (
				<Part title="The plan, day by day">
					<ul className="space-y-1">
						{terms.itinerary.map((row, index) => (
							<li key={index}>
								<span className="font-semibold text-ink">
									{row.activity_date ? formatDate(row.activity_date) : "—"}
								</span>
								{row.activity_time ? ` ${row.activity_time.slice(0, 5)}` : ""} · {row.activity}
								{row.person_responsible ? ` (${row.person_responsible})` : ""}
							</li>
						))}
					</ul>
				</Part>
			)}

			{terms.stakeholders.length > 0 && (
				<Part title="Who you would be dealing with">
					<ul className="space-y-1">
						{terms.stakeholders.map((row, index) => (
							<li key={index}>
								<span className="font-semibold text-ink">{row.designation}</span>
								{row.full_name ? ` — ${row.full_name}` : ""}
								{row.phone_number ? ` · ${row.phone_number}` : ""}
							</li>
						))}
					</ul>
				</Part>
			)}

			<p className="text-[11.5px] text-slate-faint">
				{terms.tor_name} · {terms.tor_key}
			</p>
		</div>
	);
}

function Part({ title, children }: { title: string; children: React.ReactNode }) {
	return (
		<div>
			<p className="text-[11px] font-bold uppercase tracking-wider text-slate-faint">{title}</p>
			<div className="mt-1 text-[12.5px] leading-relaxed text-slate-body">{children}</div>
		</div>
	);
}
