import { useContext, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import {
	Button,
	Card,
	Empty,
	ErrorNote,
	PageHeading,
	Pill,
	SectionTitle,
	Spinner,
	cx,
} from "../ui/primitives";
import type { TaskDetail, TaskSummary } from "./types";

/**
 * The work assigned to whoever is signed in.
 *
 * **Every method this screen calls is the volunteer's door**, checked by
 * ownership on the server: the task has to be assigned to the caller's own
 * volunteer record. `my_tasks` takes no argument at all, so the list cannot be
 * pointed at anybody else, and the four verbs each re-ask the same question
 * before they write. Nothing here decides what somebody may do; it draws
 * buttons from the state the server sent and the server refuses anything it
 * would not have offered.
 *
 * **The buttons follow the state machine in `task/services/states.py` and never
 * a label.** An assigned task can be accepted; an accepted one can be reported
 * on and submitted; a submitted one is waiting on a coordinator and offers
 * nothing but the thread. Asking a question is available whenever the task is
 * open, because a question does not move the task, which is exactly why it is a
 * flag on the record rather than a state of it.
 *
 * **Submitting is not completing, and the screen says so.** A volunteer offers
 * the work as done and a coordinator signs it off, which is the whole reason
 * `submitted` exists as a state of its own.
 */
export default function Tasks() {
	const [closed, setClosed] = useState(false);

	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: { volunteer: string; tasks: TaskSummary[] } | null;
	}>(API.myTasks, { include_closed: closed ? 1 : 0 }, `portal:my_tasks:${closed}`);

	const [open, setOpen] = useState<string | null>(null);
	const answer = data?.message;
	const rows = answer?.tasks ?? [];

	return (
		<>
			<PageHeading
				title={<EditableText k="portal.tasks.heading" fallback="Your tasks" />}
				trail={[{ label: "Home", to: "/dashboard" }, { label: "My tasks" }]}
				actions={
					<Button variant="soft" onClick={() => setClosed((was) => !was)}>
						<Icon.filter size={15} />
						{closed ? "Hide finished" : "Show finished"}
					</Button>
				}
			/>

			{isLoading && <Spinner label="Loading your tasks…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && !answer && (
				<Empty title="You do not have a volunteer record" icon={Icon.people}>
					Tasks are assigned to volunteers. Once your application has been approved, anything a
					coordinator asks you to do will appear here.
				</Empty>
			)}

			{answer && rows.length === 0 && (
				<Empty
					title={closed ? "Nothing here yet" : "Nothing is waiting on you"}
					icon={Icon.check}
				>
					A coordinator in your branch can assign you a piece of work, and it will arrive here and
					in your notifications.
				</Empty>
			)}

			{rows.length > 0 && (
				<div className="grid items-start gap-6 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
					{/* The chosen row is filled rather than outlined. An outline is what
					    every other row already is at rest, so "selected" as a heavier
					    outline is a difference somebody has to look for. */}
					<ul className="space-y-2">
						{rows.map((row) => {
							const current = (open ?? rows[0]?.name) === row.name;

							return (
								<li key={row.name}>
									<button
										type="button"
										onClick={() => setOpen(row.name)}
										aria-current={current ? "true" : undefined}
										className={cx(
											"w-full rounded-card px-4 py-3.5 text-left transition",
											current
												? "bg-navy text-white shadow-card"
												: "bg-white shadow-card hover:shadow-lift",
										)}
									>
										<div className="flex items-start justify-between gap-2.5">
											<span
												className={cx(
													"font-display text-[13.5px] font-bold",
													current ? "text-white" : "text-ink",
												)}
											>
												{row.subject}
											</span>
											<TaskState status={row.status} onDark={current} />
										</div>
										<div
											className={cx(
												"mt-1 text-[11.5px]",
												current ? "text-white/70" : "text-slate-body",
											)}
										>
											{row.due_on ? `Due ${formatDate(row.due_on)}` : "No due date"}
											{row.open_question && " · question waiting"}
										</div>
									</button>
								</li>
							);
						})}
					</ul>

					<TaskPane name={open ?? rows[0].name} onChanged={() => mutate()} />
				</div>
			)}
		</>
	);
}

/**
 * A task's state as a badge.
 *
 * Keyed off the closed set in `task/services/states.py`, which is code and the
 * same in every society, so colouring from it is safe in the way colouring from
 * an approval *stage* would not be. An unknown value falls back to neutral
 * rather than throwing the row away.
 */
const STATE_TONES: Record<string, string> = {
	assigned: "border-warning-line text-warning bg-warning-soft",
	accepted: "border-blue-line text-blue bg-blue-soft",
	submitted: "border-tint-sky/40 text-tint-sky bg-tint-sky-soft",
	completed: "border-success-line text-success bg-success-soft",
	cancelled: "border-hairline-strong text-slate-body bg-surface",
};

/**
 * `onDark` is the one concession to the selected row in the list, which is
 * filled navy. Every tone above is a dark ink on a pale wash and all five
 * disappear on it; on navy the badge keeps its shape and drops to one colour,
 * because the row is already saying which task you are looking at.
 */
export function TaskState({ status, onDark }: { status: string; onDark?: boolean }) {
	return (
		<span
			className={cx(
				"inline-flex flex-none items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-[11px] font-bold capitalize",
				onDark
					? "border-white/25 bg-white/10 text-white"
					: (STATE_TONES[status] ?? "border-hairline-strong text-slate-body bg-surface"),
			)}
		>
			<span className="h-1.5 w-1.5 flex-none rounded-full bg-current" aria-hidden="true" />
			{status}
		</span>
	);
}

/** One task in full: the brief, the thread, and whatever can be done to it. */
function TaskPane({ name, onChanged }: { name: string; onChanged: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const { data, isLoading, mutate } = useFrappeGetCall<{ message: TaskDetail }>(
		API.getTask,
		{ name },
		`portal:task:${name}`,
	);

	const [note, setNote] = useState("");
	const [proof, setProof] = useState<string | null>(null);
	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);

	const task = data?.message;

	const act = async (label: string, method: string, args: Record<string, unknown>) => {
		setBusy(label);
		setFailure(null);

		try {
			await call.post(method, { name, ...args });
			setNote("");
			setProof(null);
			await mutate();
			onChanged();
		} catch (actError) {
			setFailure(errorMessage(actError, "That did not go through."));
		} finally {
			setBusy(null);
		}
	};

	if (isLoading || !task) return <Card>{<Spinner label="Opening the task…" />}</Card>;

	return (
		<div className="space-y-4">
			<Card>
				<div className="mb-5 flex flex-wrap items-start justify-between gap-3">
					<div>
						<h2 className="font-display text-[20px] font-extrabold tracking-tight text-ink">
							{task.subject}
						</h2>
						<p className="mt-1.5 font-mono text-[12px] text-slate-faint">{task.name}</p>
					</div>
					<TaskState status={task.status} />
				</div>

				<p className="whitespace-pre-wrap border-y border-hairline-soft py-5 text-[13.5px] leading-relaxed text-slate-strong">
					{task.description}
				</p>

				<dl className="grid gap-4 py-5 sm:grid-cols-3">
					<Detail label="Due" value={task.due_on ? formatDate(task.due_on) : "No due date"} />
					<Detail label="Assigned" value={formatDate(task.assigned_on)} />
					<Detail
						label="Accepted"
						value={task.accepted_on ? formatDate(task.accepted_on) : "Not yet"}
					/>
				</dl>

				{task.status === "submitted" && (
					<p className="rounded-card bg-surface px-4 py-3.5 text-[12.5px] leading-relaxed text-slate-body">
						You have offered this as done. A coordinator has to sign it off before it is
						complete, and you will be notified either way.
					</p>
				)}

				{failure && (
					<div className="mt-4">
						<ErrorNote>{failure}</ErrorNote>
					</div>
				)}

				{task.is_open && (
					<div className="mt-4 space-y-3">
						<label
							className="block text-[12.5px] font-semibold text-slate-strong"
							htmlFor="task-note"
						>
							Note
						</label>
						<textarea
							id="task-note"
							className="min-h-[88px] w-full resize-y rounded-card border border-hairline-strong px-4 py-3 text-[13.5px] leading-relaxed outline-none transition focus:border-navy"
							value={note}
							onChange={(event) => setNote(event.target.value)}
							placeholder="What you want to say, or ask."
						/>

						<ProofUpload proof={proof} onProof={setProof} onError={setFailure} />

						<div className="flex flex-wrap gap-2">
							{task.status === "assigned" && (
								<Button
									disabled={busy !== null}
									onClick={() => act("accept", API.acceptTask, {})}
								>
									{busy === "accept" ? "Accepting…" : "Accept this task"}
								</Button>
							)}

							{task.status === "accepted" && (
								<>
									<Button
										disabled={busy !== null || !note.trim()}
										variant="navy"
										onClick={() =>
											act("progress", API.reportTaskProgress, {
												note,
												proof: proof ?? undefined,
											})
										}
									>
										{busy === "progress" ? "Sending…" : "Report progress"}
									</Button>
									<Button
										disabled={busy !== null}
										onClick={() =>
											act("submit", API.submitTask, {
												note: note || undefined,
												proof: proof ?? undefined,
											})
										}
									>
										{busy === "submit" ? "Sending…" : "Submit for review"}
									</Button>
								</>
							)}

							<Button
								variant="quiet"
								disabled={busy !== null || !note.trim()}
								onClick={() => act("ask", API.askAboutTask, { question: note })}
							>
								{busy === "ask" ? "Sending…" : "Ask a question"}
							</Button>
						</div>

						{task.open_question && (
							<p className="text-[12px] text-slate-faint">
								You have a question waiting for an answer. You can keep working in the
								meantime.
							</p>
						)}
					</div>
				)}
			</Card>

			<Card>
				<SectionTitle>What has happened</SectionTitle>
				<Thread thread={task.thread} />
			</Card>
		</div>
	);
}

/**
 * The conversation on a task, oldest first.
 *
 * `entry_type` is a closed vocabulary this app owns and it is shown, never
 * compared for anything but display. The note is rendered as a string: writing
 * on a record somebody else opens is not permission to run markup in their
 * browser, which is the same rule announcement bodies follow.
 */
export function Thread({ thread }: { thread: TaskDetail["thread"] }) {
	if (thread.length === 0) {
		return <p className="py-4 text-center text-[12.5px] text-slate-faint">Nothing yet.</p>;
	}

	return (
		<ol className="space-y-3">
			{thread.map((entry, index) => (
				<li key={index} className="rounded-card bg-surface px-4 py-3.5">
					<div className="flex flex-wrap items-baseline justify-between gap-2">
						<Pill tone="quiet">{entry.entry_type}</Pill>
						<span className="text-[11.5px] text-slate-faint">
							{entry.author} · {formatDate(entry.posted_on)}
						</span>
					</div>

					{entry.note && (
						<p className="mt-2 whitespace-pre-wrap text-[13px] leading-relaxed text-slate-strong">
							{entry.note}
						</p>
					)}

					{entry.proof && (
						<a href={entry.proof} target="_blank" rel="noreferrer" className="mt-2 block">
							<img
								src={entry.proof}
								alt="Attached as evidence"
								className="max-h-52 rounded-control border border-hairline object-cover"
							/>
						</a>
					)}
				</li>
			))}
		</ol>
	);
}

/**
 * A photograph, uploaded through Frappe's own endpoint.
 *
 * **Not a second upload endpoint.** `/api/method/upload_file` is the
 * framework's, it has already decided what this person may store and how large
 * it may be, and it is the one that gets patched. What comes back is a file URL
 * that travels to the task service as an ordinary value, exactly the way
 * `content.update_block` receives one.
 */
function ProofUpload({
	proof,
	onProof,
	onError,
}: {
	proof: string | null;
	onProof: (url: string | null) => void;
	onError: (message: string) => void;
}) {
	const [busy, setBusy] = useState(false);

	const upload = async (file: File) => {
		setBusy(true);

		try {
			const body = new FormData();
			body.append("file", file);
			body.append("is_private", "1");

			const response = await fetch("/api/method/upload_file", {
				method: "POST",
				body,
				headers: { "X-Frappe-CSRF-Token": window.csrf_token ?? "" },
			});

			if (!response.ok) throw new Error("The upload was refused.");

			const payload = (await response.json()) as { message?: { file_url?: string } };
			const url = payload.message?.file_url;

			if (!url) throw new Error("The upload came back without a file.");

			onProof(url);
		} catch (uploadError) {
			onError(errorMessage(uploadError, "That photograph could not be uploaded."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div className="flex flex-wrap items-center gap-3">
			<label className="inline-flex cursor-pointer items-center gap-2 rounded-full border border-hairline-strong bg-white px-4 py-2 font-display text-[12.5px] font-bold text-slate-strong transition hover:border-navy hover:text-navy">
				{busy ? "Uploading…" : proof ? "Replace photo" : "Attach a photo"}
				<input
					type="file"
					accept="image/*"
					className="hidden"
					onChange={(event) => {
						const file = event.target.files?.[0];
						if (file) void upload(file);
					}}
				/>
			</label>

			{proof && (
				<div className="flex items-center gap-2">
					<img src={proof} alt="" className="h-9 w-9 rounded-control object-cover" />
					<button
						type="button"
						className="text-[12px] font-semibold text-slate-faint hover:text-signal"
						onClick={() => onProof(null)}
					>
						Remove
					</button>
				</div>
			)}
		</div>
	);
}

function Detail({ label, value }: { label: string; value: string }) {
	return (
		<div>
			<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">{label}</dt>
			<dd className="mt-1.5 text-[13px] font-semibold text-ink">{value}</dd>
		</div>
	);
}
