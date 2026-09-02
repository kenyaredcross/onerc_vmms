import { useContext, useState, type ReactNode } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { TaskState, Thread } from "../portal/Tasks";
import type { GeoNode, TaskDetail, TaskSummary } from "../portal/types";
import { GeoSelects, selectedNode } from "../ui/GeoSelects";
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

/**
 * Assigning work, chasing it, and signing it off.
 *
 * **Everything here is the coordinator's door**, checked by write permission on
 * the server, which brings core's geo scoping with it. A coordinator sees the
 * tasks anchored in their own area and no argument on this screen widens that:
 * the status filter and the volunteer filter narrow a result that was already
 * bounded before either was applied.
 *
 * **The two counts in the header are the ones worth acting on**, and they come
 * back with the listing rather than being counted in the browser: work somebody
 * has offered as done, and questions nobody has answered. Both are states a
 * volunteer is waiting in, which is why they are what the screen leads with.
 *
 * **Sign-off is a decision and is drawn as one.** A submitted task offers
 * approving it or sending it back with a reason, and the reason is required for
 * the second, because work returned without one teaches nobody anything.
 */
export default function AdminTasks() {
	const [status, setStatus] = useState<string>("");
	const [open, setOpen] = useState<string | null>(null);
	const [assigning, setAssigning] = useState(false);

	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: {
			count: number;
			tasks: TaskSummary[];
			awaiting_sign_off: number;
			awaiting_answer: number;
		};
	}>(API.branchTasks, status ? { status } : undefined, `admin:branch_tasks:${status}`);

	const answer = data?.message;
	const rows = answer?.tasks ?? [];

	return (
		<>
			<PageHeading
				title={<EditableText k="admin.tasks.heading" fallback="Tasks" />}
				actions={
					<>
						{(answer?.awaiting_sign_off ?? 0) > 0 && (
							<Pill tone="signal">{answer?.awaiting_sign_off} to sign off</Pill>
						)}
						{(answer?.awaiting_answer ?? 0) > 0 && (
							<Pill tone="navy">{answer?.awaiting_answer} question(s)</Pill>
						)}
						<Button onClick={() => setAssigning((was) => !was)}>
							{assigning ? "Close" : "Assign a task"}
						</Button>
					</>
				}
			/>

			{assigning && (
				<div className="mb-5">
					<AssignForm
						onAssigned={() => {
							setAssigning(false);
							void mutate();
						}}
					/>
				</div>
			)}

			<div className="mb-4 flex flex-wrap gap-2">
				{["", "assigned", "accepted", "submitted", "completed", "cancelled"].map((option) => (
					<button
						key={option || "all"}
						type="button"
						onClick={() => setStatus(option)}
						className={cx(
							"rounded-full border px-3.5 py-1.5 text-[12px] font-semibold capitalize transition",
							status === option
								? "border-blue bg-rail text-white"
								: "border-card-line bg-white text-muted hover:border-blue hover:text-ink",
						)}
					>
						{option || "All"}
					</button>
				))}
			</div>

			{isLoading && <Spinner label="Loading tasks…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{answer && rows.length === 0 && (
				<Empty title="No tasks here">
					Nothing in your area matches. Assign one above, or clear the filter. If you hold no geo
					assignment, this list is empty by design rather than by accident.
				</Empty>
			)}

			{rows.length > 0 && (
				<div className="grid gap-5 lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
					<ul className="space-y-2.5">
						{rows.map((row) => (
							<li key={row.name}>
								<button
									type="button"
									onClick={() => setOpen(row.name)}
									className={cx(
										"w-full rounded-xl border bg-white px-4 py-3 text-left transition",
										(open ?? rows[0]?.name) === row.name
											? "border-blue border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]"
											: "border-card-line hover:border-card-line",
									)}
								>
									<div className="flex items-start justify-between gap-2">
										<span className="text-[13.5px] font-bold text-ink">{row.subject}</span>
										<TaskState status={row.status} />
									</div>
									<div className="mt-1 text-[11.5px] text-muted">
										{row.volunteer}
										{row.due_on ? ` · due ${formatDate(row.due_on)}` : ""}
										{row.open_question && " · question waiting"}
									</div>
								</button>
							</li>
						))}
					</ul>

					<SupervisePane name={open ?? rows[0].name} onChanged={() => void mutate()} />
				</div>
			)}
		</>
	);
}

/** One task, with the coordinator's verbs on it. */
function SupervisePane({ name, onChanged }: { name: string; onChanged: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const { data, isLoading, mutate } = useFrappeGetCall<{ message: TaskDetail }>(
		API.getTask,
		{ name },
		`admin:task:${name}`,
	);

	const [note, setNote] = useState("");
	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);

	const task = data?.message;

	const act = async (label: string, method: string, args: Record<string, unknown>) => {
		setBusy(label);
		setFailure(null);

		try {
			await call.post(method, { name, ...args });
			setNote("");
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
				<div className="mb-4 flex flex-wrap items-start justify-between gap-3">
					<div>
						<h2 className="text-[19px] font-semibold tracking-tight text-ink">
							{task.subject}
						</h2>
						<p className="mt-1 font-mono text-[12px] text-slate-faint">
							{task.name} · {task.volunteer}
						</p>
					</div>
					<TaskState status={task.status} />
				</div>

				<p className="whitespace-pre-wrap border-y border-card-line py-4 text-[13.5px] leading-relaxed text-slate-strong">
					{task.description}
				</p>

				{task.completion_notes && (
					<div className="border-b border-card-line py-4">
						<SectionTitle>What they said when they finished</SectionTitle>
						<p className="whitespace-pre-wrap text-[13px] text-slate-strong">
							{task.completion_notes}
						</p>
					</div>
				)}

				{failure && (
					<div className="mt-4">
						<ErrorNote>{failure}</ErrorNote>
					</div>
				)}

				{task.is_open && (
					<div className="mt-4 space-y-3">
						<label
							className="block text-[10px] font-bold uppercase tracking-wider text-slate-faint"
							htmlFor="supervise-note"
						>
							Note {task.status === "submitted" ? "(required to send back)" : "(optional)"}
						</label>
						<textarea
							id="supervise-note"
							className="min-h-[76px] w-full resize-y rounded-xl border border-card-line px-3 py-2.5 text-[13px] outline-none focus:border-blue"
							value={note}
							onChange={(event) => setNote(event.target.value)}
						/>

						<div className="flex flex-wrap gap-2">
							{task.status === "submitted" && (
								<>
									<Button
										disabled={busy !== null}
										onClick={() =>
											act("sign-off", API.signOffTask, { note: note || undefined })
										}
									>
										{busy === "sign-off" ? "Approving…" : "Approve completion"}
									</Button>
									<Button
										variant="quiet"
										disabled={busy !== null || !note.trim()}
										onClick={() => act("back", API.sendTaskBack, { reason: note })}
									>
										{busy === "back" ? "Sending…" : "Send back for more work"}
									</Button>
								</>
							)}

							{task.open_question && (
								<Button
									variant="navy"
									disabled={busy !== null || !note.trim()}
									onClick={() => act("answer", API.answerTaskQuestion, { reply: note })}
								>
									{busy === "answer" ? "Sending…" : "Answer the question"}
								</Button>
							)}

							<Button
								variant="quiet"
								disabled={busy !== null}
								onClick={() =>
									act("chase", API.requestTaskProgress, { note: note || undefined })
								}
							>
								{busy === "chase" ? "Sending…" : "Request an update"}
							</Button>

							<Button
								variant="ghost"
								disabled={busy !== null}
								onClick={() => act("cancel", API.cancelTask, { reason: note || undefined })}
							>
								{busy === "cancel" ? "Cancelling…" : "Cancel task"}
							</Button>
						</div>
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
 * Assigning a task.
 *
 * **Placement is `GeoSelects`, the one placement control in this app**, and it
 * is optional here: leaving it empty anchors the task at the volunteer's own
 * branch, which is what a coordinator assigning work to somebody in front of
 * them means. The server does that fallback, not this form, and refuses rather
 * than guessing when the volunteer has no branch either.
 *
 * **The volunteer is searched for, not typed.** This form used to take a bare
 * docname, on the grounds that putting a register behind an autocomplete would
 * make assigning a task a way of browsing one. That reasoning does not survive
 * contact with the job: a coordinator assigning work knows the person, not
 * `VOL-00012`, and asking them to leave, open the registry, find the docname
 * and come back is asking them to do the computer's work. The concern it was
 * protecting against is answered where it should be — `find_volunteers` reads
 * through `frappe.get_list`, so the search can only ever return people the
 * caller could already open in the registry, and typing a name they may not
 * see returns nothing.
 */
function AssignForm({ onAssigned }: { onAssigned: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [volunteer, setVolunteer] = useState("");
	const [subject, setSubject] = useState("");
	const [description, setDescription] = useState("");
	const [dueOn, setDueOn] = useState("");
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const node = selectedNode(chain);
	const ready = volunteer.trim() && subject.trim() && description.trim();

	const assign = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.assignTask, {
				volunteer: volunteer.trim(),
				subject: subject.trim(),
				description: description.trim(),
				geo_node: node?.name ?? undefined,
				due_on: dueOn || undefined,
			});
			setVolunteer("");
			setSubject("");
			setDescription("");
			setDueOn("");
			setChain([]);
			onAssigned();
		} catch (assignError) {
			setFailure(errorMessage(assignError, "That task was not created."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card>
			<SectionTitle>Assign a task</SectionTitle>

			<div className="grid gap-4 sm:grid-cols-2">
				<Labelled label="Volunteer" hint="Search by name, or paste a record number.">
					<VolunteerPicker value={volunteer} onChange={setVolunteer} />
				</Labelled>

				<Labelled label="Due on" hint="Optional. Nothing is refused for being late.">
					<input
						type="date"
						className={INPUT}
						value={dueOn}
						onChange={(event) => setDueOn(event.target.value)}
					/>
				</Labelled>
			</div>

			<div className="mt-4">
				<Labelled label="Subject" hint="One line, as it appears in their list.">
					<input
						className={INPUT}
						value={subject}
						onChange={(event) => setSubject(event.target.value)}
					/>
				</Labelled>
			</div>

			<div className="mt-4">
				<Labelled label="What is being asked for" hint="The full brief.">
					<textarea
						className={cx(INPUT, "min-h-[96px] resize-y")}
						value={description}
						onChange={(event) => setDescription(event.target.value)}
					/>
				</Labelled>
			</div>

			<div className="mt-4">
				<p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-faint">
					Where this work belongs
				</p>
				<GeoSelects chain={chain} onChain={setChain} />
				<p className="mt-2 text-[12px] text-slate-faint">
					Leave this empty to anchor the task at the volunteer's own branch.
				</p>
			</div>

			{failure && (
				<div className="mt-4">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<div className="mt-5">
				<Button disabled={busy || !ready} onClick={() => void assign()}>
					{busy ? "Assigning…" : "Assign and notify"}
				</Button>
			</div>
		</Card>
	);
}

const INPUT =
	"w-full rounded-xl border border-card-line px-3 py-2.5 text-[13px] outline-none focus:border-blue";

function Labelled({
	label,
	hint,
	children,
}: {
	label: string;
	hint?: string;
	children: ReactNode;
}) {
	return (
		<label className="block">
			<span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-faint">
				{label}
			</span>
			{children}
			{hint && <span className="mt-1 block text-[11.5px] text-slate-faint">{hint}</span>}
		</label>
	);
}

/**
 * Find a volunteer by name, for somebody who knows the person and not the record.
 *
 * **The search is the scope.** `find_volunteers` reads through
 * `frappe.get_list`, so core's geo scoping is applied underneath every query
 * this makes: a coordinator sees the people they could already open in the
 * registry and nobody else, whatever they type. That is why an autocomplete
 * here is not a way of browsing a register — the register it can reach is
 * already theirs.
 *
 * A pasted docname still works, because `search` matches the volunteer's own
 * name as well as the person's. Somebody who arrives from the registry with
 * `VOL-00012` on their clipboard should not be made to type a name instead.
 *
 * The chosen volunteer is shown as what a person is called, with the record
 * number beside it rather than instead of it: the coordinator needs to be sure
 * they picked the right Fatoumata, and the number is what the server was told.
 */
function VolunteerPicker({
	value,
	onChange,
}: {
	value: string;
	onChange: (volunteer: string) => void;
}) {
	const [term, setTerm] = useState("");
	const [open, setOpen] = useState(false);

	// Only ask once there is something to narrow by. An empty search would pull
	// the whole of the caller's scope back on every keystroke to no purpose.
	const query = term.trim();
	const { data, isLoading } = useFrappeGetCall<{
		message: { count: number; volunteers: { volunteer: string; full_name: string; status: string; geo_path?: string }[] };
	}>(API.findVolunteers, { search: query, limit: 8 }, query.length >= 2 ? `admin:vol:${query}` : null);

	const rows = data?.message?.volunteers ?? [];
	const chosen = rows.find((row) => row.volunteer === value);

	if (value) {
		return (
			<div className="flex items-center gap-2 rounded-xl border border-card-line bg-surface px-3 py-2">
				<span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-ink">
					{chosen?.full_name || value}
					<span className="ml-2 font-normal text-slate-faint">{value}</span>
				</span>
				<button
					type="button"
					onClick={() => {
						onChange("");
						setTerm("");
					}}
					className="flex-none rounded px-2 py-1 text-[11px] font-bold text-muted hover:text-ink"
				>
					Change
				</button>
			</div>
		);
	}

	return (
		<div className="relative">
			<input
				className={INPUT}
				value={term}
				onChange={(event) => {
					setTerm(event.target.value);
					setOpen(true);
				}}
				onFocus={() => setOpen(true)}
				placeholder="Start typing a name"
				autoComplete="off"
			/>

			{open && query.length >= 2 && (
				<div className="absolute z-20 mt-1 w-full overflow-hidden rounded-xl border border-card-line bg-white shadow-lg">
					{isLoading && <p className="px-3 py-2 text-[12px] text-slate-faint">Searching…</p>}

					{!isLoading && !rows.length && (
						<p className="px-3 py-2 text-[12px] text-slate-faint">
							Nobody in your area matches that.
						</p>
					)}

					{rows.map((row) => (
						<button
							key={row.volunteer}
							type="button"
							onClick={() => {
								onChange(row.volunteer);
								setOpen(false);
							}}
							className="flex w-full items-baseline gap-2 px-3 py-2 text-left hover:bg-surface"
						>
							<span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-ink">
								{row.full_name || row.volunteer}
							</span>
							<span className="flex-none text-[11px] text-slate-faint">{row.volunteer}</span>
						</button>
					))}
				</div>
			)}
		</div>
	);
}
