import { useContext, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, formatHours } from "../lib/format";
import { Icon } from "../ui/icons";
import { Pill } from "../ui/primitives";
import {
	BackLink,
	Button,
	Card,
	Empty,
	ErrorNote,
	Facts,
	FilterPills,
	Meter,
	Notice,
	PageHead,
	SearchField,
	Spinner,
	Tabs,
	cx,
} from "./ui/kit";
import { ConfirmModal, useToast } from "./ui/overlays";
import { OsmMap } from "./ui/OsmMap";
import type { TaskChecklistItem, TaskDetail, TaskPlace, TaskSummary } from "./types";

/**
 * The work assigned to whoever is signed in.
 *
 * **Every method here is the volunteer's door**, checked by ownership on the
 * server: `my_tasks` takes no argument, and every verb re-asks that the task
 * belongs to the caller before it writes. Nothing in this file decides what
 * somebody may do — it draws the controls the state machine allows and the
 * server refuses anything it would not have offered.
 *
 * **Submitting is not completing, and the screen says so.** A volunteer offers
 * the work as done (`submit_task`); a coordinator signs it off. That is the
 * whole reason `submitted` is a state of its own, and there is no "Complete"
 * button anywhere here.
 *
 * **The list is a register and the task is a page.** The approved concept draws
 * the two apart — a table a person scans and filters, and a record at its own
 * address with the brief, the checklist, the evidence, the conversation and the
 * outcome. `/tasks/:name` is that address.
 */

/* ------------------------------------------------------------------ states */

const STATE_LABEL: Record<string, string> = {
	assigned: "Assigned",
	accepted: "Accepted",
	submitted: "Submitted",
	completed: "Completed",
	cancelled: "Cancelled",
	declined: "Declined",
	reassigned: "Reassigned",
};

/** The four the concept colours, plus the neutral tail of the closed set. */
const STATE_CHIP: Record<string, string> = {
	assigned: "bg-blue-soft text-blue-press",
	accepted: "bg-warning-soft text-warning",
	submitted: "bg-cal-cert-soft text-cal-cert",
	completed: "bg-success-soft text-success",
};

export function TaskStateBadge({ status }: { status: string }) {
	return (
		<span
			className={cx(
				"inline-flex w-max flex-none items-center justify-center whitespace-nowrap rounded-full px-2.5 py-1 text-[10.5px] font-bold",
				STATE_CHIP[status] ?? "bg-surface text-slate-strong",
			)}
		>
			{STATE_LABEL[status] ?? status}
		</span>
	);
}

/** The square mark at the head of a row — what kind of attention this needs. */
function StateMark({ row }: { row: TaskSummary }) {
	const tone = row.is_overdue
		? "bg-red-soft text-red-ink"
		: row.open_question
			? "bg-blue-soft text-blue-press"
			: row.status === "completed"
				? "bg-success-soft text-success"
				: row.status === "submitted"
					? "bg-cal-cert-soft text-cal-cert"
					: row.status === "accepted"
						? "bg-warning-soft text-warning"
						: "bg-blue-soft text-blue-press";

	const icon = row.is_overdue
		? Icon.bell
		: row.open_question
			? Icon.chat
			: row.status === "completed"
				? Icon.check
				: row.status === "submitted"
					? Icon.hourglass
					: Icon.check;

	return (
		<span className={cx("grid h-9 w-9 flex-none place-items-center rounded-lg", tone)} aria-hidden="true">
			{icon({ size: 16 })}
		</span>
	);
}

/* -------------------------------------------------------------------- list */

type FilterKey =
	| "active"
	| "questions"
	| "assigned"
	| "accepted"
	| "submitted"
	| "completed"
	| "all";

/**
 * Every filter is a server-supplied flag or a server-owned state name. None of
 * them is a rule invented on this screen.
 */
const MATCH: Record<FilterKey, (row: TaskSummary) => boolean> = {
	active: (row) => row.is_open,
	questions: (row) => row.open_question,
	assigned: (row) => row.status === "assigned",
	accepted: (row) => row.status === "accepted",
	submitted: (row) => row.status === "submitted",
	completed: (row) => row.status === "completed",
	all: () => true,
};

export default function Tasks() {
	const { data, error, isLoading } = useFrappeGetCall<{
		message: { volunteer: string; tasks: TaskSummary[] } | null;
	}>(API.myTasks, { include_closed: 1 }, "portal:my_tasks:true");

	const [filter, setFilter] = useState<FilterKey>("active");
	const [query, setQuery] = useState("");

	const answer = data?.message;
	const all = useMemo(() => answer?.tasks ?? [], [answer]);

	const counts = useMemo(
		() => ({
			active: all.filter(MATCH.active).length,
			questions: all.filter(MATCH.questions).length,
			assigned: all.filter(MATCH.assigned).length,
			accepted: all.filter(MATCH.accepted).length,
			submitted: all.filter(MATCH.submitted).length,
			completed: all.filter(MATCH.completed).length,
			all: all.length,
		}),
		[all],
	);

	const shown = useMemo(() => {
		const needle = query.trim().toLowerCase();
		return all
			.filter(MATCH[filter])
			.filter(
				(row) =>
					!needle ||
					row.subject.toLowerCase().includes(needle) ||
					row.name.toLowerCase().includes(needle) ||
					(row.task_type ?? "").toLowerCase().includes(needle),
			)
			.sort(
				(a, b) =>
					Number(b.open_question) - Number(a.open_question) ||
					Number(b.is_overdue) - Number(a.is_overdue) ||
					(a.due_on || "9999").localeCompare(b.due_on || "9999"),
			);
	}, [all, filter, query]);

	return (
		<>
			<PageHead
				eyebrow="Your work"
				title={<EditableText k="portal.tasks.heading" fallback="Tasks" />}
				lead="Open a task to see its full brief, checklist, evidence and activity history."
				actions={
					<Link
						to="/calendar"
						className="text-[12.5px] font-semibold text-blue transition-colors hover:text-blue-hover"
					>
						View deadlines in calendar →
					</Link>
				}
			/>

			{isLoading && <Spinner label="Loading your tasks…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && !answer && (
				<Empty icon={Icon.people} title="You do not have a volunteer record">
					Tasks are assigned to volunteers. Once your application is approved, anything a coordinator
					asks you to do appears here.
				</Empty>
			)}

			{answer && (
				<>
					<div className="mb-[18px] grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
						<Summary label="Assigned" value={counts.assigned} note="Waiting for your answer" />
						<Summary label="Accepted" value={counts.accepted} note="Work in progress" />
						<Summary label="Submitted" value={counts.submitted} note="Waiting for sign-off" />
						<Summary label="Clarifications" value={counts.questions} note="Waiting for a reply" />
						<Summary label="Completed" value={counts.completed} note="Coordinator approved" />
					</div>

					<div className="p-card overflow-hidden">
						<div className="flex flex-col gap-3 border-b border-card-line p-[18px] lg:flex-row lg:items-center lg:gap-5">
							<div className="lg:w-[320px] lg:flex-none">
								<SearchField
									value={query}
									onChange={setQuery}
									label="Search your tasks"
									placeholder="Search your tasks"
									hint={`${shown.length} showing`}
								/>
							</div>
							<div className="min-w-0 lg:flex-1">
								<FilterPills
									label="Task status"
									active={filter}
									onSelect={(key) => setFilter(key as FilterKey)}
									pills={[
										{ key: "active", label: "Active", count: counts.active },
										{ key: "questions", label: "Clarifications", count: counts.questions },
										{ key: "assigned", label: "Assigned", count: counts.assigned },
										{ key: "accepted", label: "Accepted", count: counts.accepted },
										{ key: "submitted", label: "Submitted", count: counts.submitted },
										{ key: "completed", label: "Completed", count: counts.completed },
										{ key: "all", label: "All", count: counts.all },
									]}
								/>
							</div>
						</div>

						{/* Three column sets, not two: at 1024 there is room for the type,
						    the due date and the state, and dropping the due date at a
						    width that could carry it is what makes a register useless. */}
						<div
							aria-hidden="true"
							className="hidden gap-3 border-b border-card-line bg-canvas px-4 py-2.5 text-[10px] font-bold uppercase tracking-[0.07em] text-muted lg:grid lg:grid-cols-[36px_minmax(0,1fr)_110px_100px_92px_56px] xl:grid-cols-[36px_minmax(0,1fr)_140px_120px_120px_100px_62px]"
						>
							<span className="col-span-2">Task</span>
							<span>Type</span>
							<span>Due</span>
							<span className="hidden xl:block">Progress</span>
							<span>Status</span>
							<span />
						</div>

						{shown.length === 0 ? (
							<Empty framed={false} icon={Icon.check} title={emptyTitle(filter, query)}>
								{query
									? "Try a different search, or another status."
									: filter === "active"
										? "A coordinator in your branch can assign you a piece of work, and it will arrive here and in your notifications."
										: "Nothing here yet."}
							</Empty>
						) : (
							<ul>
								{shown.map((row) => (
									<li key={row.name}>
										<TaskRow row={row} />
									</li>
								))}
							</ul>
						)}
					</div>
				</>
			)}
		</>
	);
}

function emptyTitle(filter: FilterKey, query: string): string {
	if (query) return "No matching tasks";
	if (filter === "active") return "Nothing is waiting on you";
	if (filter === "questions") return "No clarification is outstanding";
	if (filter === "completed") return "Nothing completed yet";
	return "No tasks here";
}

function Summary({ label, value, note }: { label: string; value: number; note: string }) {
	return (
		<div className="p-card p-[18px]">
			<span className="block text-[11.5px] text-slate-body">{label}</span>
			<strong className="mt-1.5 block font-display text-[24px] font-extrabold leading-none tracking-[-0.02em] text-ink tabular">
				{value}
			</strong>
			<small className="mt-1.5 block text-[11px] text-muted">{note}</small>
		</div>
	);
}

function TaskRow({ row }: { row: TaskSummary }) {
	return (
		<Link
			to={`/tasks/${encodeURIComponent(row.name)}`}
			className="grid grid-cols-[36px_minmax(0,1fr)_auto] items-center gap-3 border-b border-card-line px-4 py-3.5 transition last:border-b-0 hover:bg-blue-soft/40 lg:grid-cols-[36px_minmax(0,1fr)_110px_100px_92px_56px] xl:grid-cols-[36px_minmax(0,1fr)_140px_120px_120px_100px_62px]"
		>
			<StateMark row={row} />

			<span className="min-w-0">
				<span className="block truncate text-[10px] font-bold uppercase tracking-[0.06em] text-blue">
					{row.name}
					{row.task_type ? ` · ${row.task_type}` : ""}
				</span>
				<strong className="mt-1 block truncate text-[13px] font-semibold text-ink">
					{row.subject}
				</strong>
				<span className="mt-0.5 flex flex-wrap items-center gap-2 text-[11.5px] text-slate-body">
					{row.assigned_on ? `Assigned ${formatDate(row.assigned_on)}` : "Assigned"}
					{row.open_question && (
						<span className="rounded-full bg-blue-soft px-1.5 py-0.5 text-[9.5px] font-bold uppercase tracking-[0.05em] text-blue-press">
							Clarification pending
						</span>
					)}
					{row.priority && row.priority !== "Normal" && (
						<span className="rounded-full bg-surface px-1.5 py-0.5 text-[9.5px] font-bold uppercase tracking-[0.05em] text-slate-strong">
							{row.priority}
						</span>
					)}
				</span>
			</span>

			<span className="hidden min-w-0 truncate text-[12px] text-ink lg:block">
				{row.task_type || "—"}
			</span>

			<span
				className={cx(
					"hidden truncate text-[12px] lg:block",
					row.is_overdue ? "font-semibold text-red-ink" : "text-ink",
				)}
			>
				{row.due_on ? formatDate(row.due_on) : "No due date"}
			</span>

			<span className="hidden xl:block">
				<Meter value={row.percent_complete} label={`${row.subject} progress`} />
			</span>

			<span className="max-lg:justify-self-end">
				<TaskStateBadge status={row.status} />
			</span>

			<span
				aria-hidden="true"
				className="hidden whitespace-nowrap text-[11.5px] font-bold text-blue lg:block"
			>
				Open →
			</span>
		</Link>
	);
}

/* ------------------------------------------------------------------ record */

type RecordTab = "overview" | "checklist" | "thread" | "outcome";

/**
 * One task at its own address.
 *
 * Everything drawn here is on the server's own DTO. Nothing is inferred: the
 * controls follow `status` and `is_open`, the submit gate follows
 * `checklist_outstanding`, the blocked notice follows `blocking`, and the map
 * is drawn only where the place carries `has_point`.
 */
export function TaskRecord() {
	const { name = "" } = useParams();
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const toast = useToast();

	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: TaskDetail }>(
		API.getTask,
		{ name },
		`portal:task:${name}`,
	);

	const [tab, setTab] = useState<RecordTab>("overview");
	const [message, setMessage] = useState("");
	const [proof, setProof] = useState<string | null>(null);
	const [progress, setProgress] = useState<number | null>(null);
	const [progressNote, setProgressNote] = useState("");
	const [declining, setDeclining] = useState(false);
	const [declineReason, setDeclineReason] = useState("");
	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);

	const task = data?.message;

	const act = async (
		label: string,
		method: string,
		args: Record<string, unknown>,
		said?: string,
	) => {
		setBusy(label);
		setFailure(null);
		try {
			await call.post(method, { name, ...args });
			await mutate();
			if (said) toast(said);
			return true;
		} catch (e) {
			setFailure(errorMessage(e, "That did not go through."));
			return false;
		} finally {
			setBusy(null);
		}
	};

	if (isLoading) return <Spinner page label="Opening the task…" />;

	if (error || !task) {
		return (
			<>
				<BackLink to="/tasks">Back to tasks</BackLink>
				<ErrorNote>{errorMessage(error, "That task could not be opened.")}</ErrorNote>
			</>
		);
	}

	const blocked = task.blocking.length > 0;
	const outstanding = task.checklist_outstanding.length;
	const percent = progress ?? task.percent_complete;

	const tabs = [
		{ key: "overview", label: "Overview" },
		{
			key: "checklist",
			label: "Checklist & evidence",
			count: task.checklist.length || undefined,
		},
		{ key: "thread", label: "Messages & updates", count: task.thread.length || undefined },
		{ key: "outcome", label: "Outcome" },
	];

	return (
		<>
			<BackLink to="/tasks">Back to tasks</BackLink>

			<header className="mb-5 flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
				<div className="min-w-0">
					<div className="flex flex-wrap items-center gap-2.5">
						<TaskStateBadge status={task.status} />
						<span className="text-[11px] font-bold uppercase tracking-[0.07em] text-muted">
							{task.name}
						</span>
						{task.is_overdue && (
							<span className="rounded-full bg-red-soft px-2 py-1 text-[10.5px] font-bold text-red-ink">
								Overdue
							</span>
						)}
					</div>
					<h1 className="mt-2.5 font-display text-[26px] font-bold leading-[1.15] tracking-[-0.025em] text-ink sm:text-[29px]">
						{task.subject}
					</h1>
					<p className="mt-1.5 text-[12.5px] text-slate-body">
						{[task.task_type, task.deployment, task.project].filter(Boolean).join(" · ") ||
							"Your volunteer record"}
					</p>
				</div>

				<div className="flex flex-wrap gap-2 max-sm:w-full">
					{task.status === "assigned" && (
						<>
							<Button
								tone="quiet"
								disabled={busy !== null}
								onClick={() => setDeclining(true)}
								className="max-sm:flex-1"
							>
								Decline task
							</Button>
							<Button
								busy={busy === "accept"}
								disabled={busy !== null}
								onClick={() => void act("accept", API.acceptTask, {}, "Task accepted.")}
								className="max-sm:flex-1"
							>
								Accept task
							</Button>
						</>
					)}
					{task.status === "accepted" && (
						<Button
							busy={busy === "submit"}
							disabled={busy !== null || outstanding > 0}
							onClick={() =>
								void act(
									"submit",
									API.submitTask,
									{ note: message || undefined, proof: proof ?? undefined },
									"Sent for sign-off.",
								)
							}
							className="max-sm:flex-1"
						>
							Submit for review
						</Button>
					)}
				</div>
			</header>

			{failure && (
				<div className="mb-4">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			{task.status === "accepted" && outstanding > 0 && (
				<div className="mb-4">
					<Notice>
						{outstanding === 1
							? "One required checklist item is still unticked, so this cannot be submitted yet."
							: `${outstanding} required checklist items are still unticked, so this cannot be submitted yet.`}
					</Notice>
				</div>
			)}

			{blocked && (
				<div className="mb-4">
					<Notice>
						Waiting on {task.blocking.length === 1 ? "another task" : "other tasks"}:{" "}
						{task.blocking.map((row) => row.subject).join(", ")}.
					</Notice>
				</div>
			)}

			<Tabs tabs={tabs} active={tab} onSelect={(key) => setTab(key as RecordTab)} />

			<div className="grid grid-cols-1 items-start gap-[18px] lg:grid-cols-[minmax(0,1fr)_315px]">
				<div className="min-w-0 space-y-[18px]">
					{tab === "overview" && <Overview task={task} />}

					{tab === "checklist" && (
						<Checklist
							task={task}
							busy={busy}
							onTick={(index, done) =>
								void act(`tick-${index}`, API.tickTaskChecklist, { index, done: done ? 1 : 0 })
							}
						/>
					)}

					{tab === "thread" && (
						<Conversation
							task={task}
							busy={busy}
							message={message}
							onMessage={setMessage}
							proof={proof}
							onProof={setProof}
							onError={setFailure}
							percent={percent}
							onPercent={setProgress}
							progressNote={progressNote}
							onProgressNote={setProgressNote}
							onAsk={async () => {
								const sent = await act(
									"ask",
									API.askAboutTask,
									{ question: message },
									"Clarification sent.",
								);
								if (sent) {
									setMessage("");
									setProof(null);
								}
							}}
							onProgress={async () => {
								const sent = await act(
									"progress",
									API.reportTaskProgress,
									{ note: progressNote, percent, proof: proof ?? undefined },
									"Progress reported.",
								);
								if (sent) {
									setProgressNote("");
									setProgress(null);
									setProof(null);
								}
							}}
						/>
					)}

					{tab === "outcome" && <Outcome task={task} />}
				</div>

				<aside className="space-y-[18px] lg:sticky lg:top-[72px]">
					<Card>
						<h2 className="mb-3.5 font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
							Task details
						</h2>
						<Facts
							columns={2}
							items={[
								{ label: "Status", value: <TaskStateBadge status={task.status} /> },
								{ label: "Priority", value: task.priority || "—" },
								{ label: "Task type", value: task.task_type || "—" },
								{ label: "Assigned on", value: formatDate(task.assigned_on) },
								{ label: "Geo node", value: task.geo_node || "—" },
								{
									label: "Progress",
									value: (
										<span className="block max-w-[160px]">
											<Meter value={task.percent_complete} label="Task progress" />
										</span>
									),
								},
							]}
						/>
					</Card>

					{(task.deployment || task.project) && (
						<Card>
							<h2 className="mb-2 font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
								Related records
							</h2>
							{task.deployment && (
								<Related
									kind="Deployment"
									title={task.deployment}
									to={`/deployments/${encodeURIComponent(task.deployment)}`}
								/>
							)}
							{task.project && <Related kind="Project" title={task.project} />}
						</Card>
					)}

					<Notice>
						<strong className="block font-semibold text-ink">About task completion</strong>
						Submitting means you say the work is ready. The task becomes completed only after a
						coordinator signs it off.
					</Notice>
				</aside>
			</div>

			<ConfirmModal
				open={declining}
				title="Decline this task?"
				confirmLabel="Send decline"
				tone="danger"
				busy={busy === "decline"}
				onCancel={() => setDeclining(false)}
				onConfirm={async () => {
					const sent = await act(
						"decline",
						API.declineTask,
						{ reason: declineReason },
						"Your coordinator has been told.",
					);
					if (sent) {
						setDeclining(false);
						setDeclineReason("");
					}
				}}
			>
				<p>
					Your coordinator is told either way. Say why you cannot take it on — it helps them find
					somebody else.
				</p>
				<label className="mt-3 block">
					<span className="mb-1.5 block text-[12px] font-semibold text-slate-strong">Reason</span>
					<textarea
						value={declineReason}
						onChange={(event) => setDeclineReason(event.target.value)}
						className="min-h-[72px] w-full resize-y rounded-xl border border-card-line px-3.5 py-2.5 text-[13px] leading-relaxed outline-none transition focus:border-blue"
					/>
				</label>
			</ConfirmModal>
		</>
	);
}

function Related({ kind, title, to }: { kind: string; title: string; to?: string }) {
	const body = (
		<>
			<span className="block text-[10px] font-bold uppercase tracking-[0.07em] text-muted">
				{kind}
			</span>
			<strong className="mt-1 block truncate text-[12.5px] font-semibold text-ink">{title}</strong>
			{to && <span className="mt-1 block text-[11.5px] font-bold text-blue">Open →</span>}
		</>
	);

	return to ? (
		<Link to={to} className="block border-t border-card-line py-3 transition hover:bg-canvas">
			{body}
		</Link>
	) : (
		<div className="border-t border-card-line py-3">{body}</div>
	);
}

/* ---------------------------------------------------------------- overview */

function Overview({ task }: { task: TaskDetail }) {
	const where = task.where;
	const place = where.meeting_point.has_point ? where.meeting_point : where.work;

	return (
		<>
			<Card>
				<h2 className="mb-3 font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
					Description
				</h2>
				<p className="whitespace-pre-wrap text-[13px] leading-relaxed text-slate-body">
					{task.description || "No description was written for this task."}
				</p>
			</Card>

			<Card>
				<h2 className="mb-4 font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
					Schedule and expectations
				</h2>
				<Facts
					items={[
						{ label: "Planned start", value: formatDate(task.planned_start) },
						{ label: "Planned end", value: formatDate(task.planned_end) },
						{ label: "Due", value: task.due_on ? formatDate(task.due_on) : "No due date" },
						{ label: "Answer by", value: formatDate(task.response_deadline) },
						{
							label: "Expected hours",
							value: task.expected_hours ? formatHours(task.expected_hours) : "—",
						},
						{
							label: "Actual hours",
							value: task.actual_hours ? formatHours(task.actual_hours) : "—",
						},
					]}
				/>
			</Card>

			<Card>
				<h2 className="mb-4 font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
					Where the work is
				</h2>
				<Facts
					columns={2}
					items={[
						{ label: "Work location", value: placeLine(where.work) },
						{ label: "Meeting point", value: placeLine(where.meeting_point) },
						where.travel_instructions
							? { label: "Travel instructions", value: where.travel_instructions }
							: null,
						where.local_contact.name || where.local_contact.phone
							? {
									label: "Local contact",
									value: [where.local_contact.name, where.local_contact.phone]
										.filter(Boolean)
										.join(" · "),
								}
							: null,
					]}
				/>

				{/* Only where the server resolved a real point. A task with an
				    address and no coordinates draws the address and no map. */}
				{place.has_point && place.latitude != null && place.longitude != null && (
					<div className="mt-4">
						<OsmMap
							latitude={place.latitude}
							longitude={place.longitude}
							label={place.name ?? undefined}
							height={190}
						/>
						{place.directions && (
							<a
								href={place.directions}
								target="_blank"
								rel="noreferrer"
								className="mt-2 inline-block text-[12px] font-semibold text-blue hover:text-blue-hover"
							>
								Open turn-by-turn directions ↗
							</a>
						)}
					</div>
				)}

				{where.inherited_from && (
					<p className="mt-3 text-[11.5px] text-muted">
						Taken from the deployment {where.inherited_from}.
					</p>
				)}
			</Card>

			<Card>
				<h2 className="mb-3 font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
					Dependencies
				</h2>
				{task.blocking.length === 0 ? (
					<div className="flex items-center gap-3 rounded-xl border border-success-line bg-success-soft px-4 py-3 text-success">
						<span className="grid h-7 w-7 flex-none place-items-center rounded-full bg-white/70">
							<Icon.check size={14} />
						</span>
						<span>
							<strong className="block text-[12.5px] font-semibold">
								No blocking dependencies
							</strong>
							<span className="mt-0.5 block text-[11.5px]">
								{task.status === "assigned"
									? "You can begin this task after accepting it."
									: "Nothing is standing in front of this work."}
							</span>
						</span>
					</div>
				) : (
					<ul className="space-y-2">
						{task.blocking.map((row) => (
							<li
								key={row.name}
								className="flex items-center justify-between gap-3 rounded-xl border border-warning-line bg-warning-soft px-4 py-3"
							>
								<span className="min-w-0 text-[12.5px] font-semibold text-warning">
									{row.subject}
								</span>
								<TaskStateBadge status={row.status} />
							</li>
						))}
					</ul>
				)}
				{task.blocked_override_reason && (
					<p className="mt-3 text-[11.5px] text-muted">{task.blocked_override_reason}</p>
				)}
			</Card>
		</>
	);
}

function placeLine(place: TaskPlace): string {
	return [place.name, place.address].filter(Boolean).join(" — ") || "—";
}

/* --------------------------------------------------------------- checklist */

function Checklist({
	task,
	busy,
	onTick,
}: {
	task: TaskDetail;
	busy: string | null;
	onTick: (index: number, done: boolean) => void;
}) {
	const done = task.checklist.filter((row) => row.is_done).length;
	const required = task.checklist.filter((row) => row.is_required).length;

	return (
		<>
			<Card>
				<div className="mb-3 flex flex-wrap items-center justify-between gap-3">
					<h2 className="font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
						Checklist
					</h2>
					<span className="text-[11.5px] text-muted">
						{task.checklist.length === 0
							? "Nothing to tick"
							: `${done} of ${task.checklist.length} done · ${required} required`}
					</span>
				</div>

				{task.checklist.length === 0 ? (
					<p className="text-[12.5px] text-muted">
						This task has no checklist. Your coordinator set it as one piece of work.
					</p>
				) : (
					<ul className="divide-y divide-card-line">
						{task.checklist.map((row) => (
							<ChecklistRow
								key={row.idx}
								row={row}
								disabled={!task.is_open || busy !== null}
								busy={busy === `tick-${row.idx}`}
								onToggle={() => onTick(row.idx, !row.is_done)}
							/>
						))}
					</ul>
				)}
			</Card>

			<Card>
				<div className="mb-3 flex flex-wrap items-center justify-between gap-3">
					<h2 className="font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
						Briefing files
					</h2>
					<span className="text-[11.5px] text-muted">Provided by the coordinator</span>
				</div>
				{task.brief_files.length === 0 ? (
					<p className="text-[12.5px] text-muted">No briefing files were attached.</p>
				) : (
					<ul className="divide-y divide-card-line">
						{task.brief_files.map((file, index) => (
							<li key={index} className="py-3">
								<a
									href={file.file ?? undefined}
									target="_blank"
									rel="noreferrer"
									className="flex items-center gap-3"
								>
									<span
										className="grid h-9 w-9 flex-none place-items-center rounded-lg bg-blue-soft text-blue-press"
										aria-hidden="true"
									>
										<Icon.file size={16} />
									</span>
									<span className="min-w-0 flex-1">
										<strong className="block truncate text-[12.5px] font-semibold text-ink">
											{file.label || file.file || "Attachment"}
										</strong>
										{file.notes && (
											<span className="block truncate text-[11.5px] text-muted">{file.notes}</span>
										)}
									</span>
									<span className="flex-none text-[11.5px] font-bold text-blue">Open</span>
								</a>
							</li>
						))}
					</ul>
				)}
			</Card>

			{task.final_evidence && (
				<Card>
					<h2 className="mb-2 font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
						Final evidence
					</h2>
					<a
						href={task.final_evidence}
						target="_blank"
						rel="noreferrer"
						className="text-[12.5px] font-semibold text-blue hover:text-blue-hover"
					>
						Open the evidence you submitted ↗
					</a>
				</Card>
			)}
		</>
	);
}

function ChecklistRow({
	row,
	disabled,
	busy,
	onToggle,
}: {
	row: TaskChecklistItem;
	disabled: boolean;
	busy: boolean;
	onToggle: () => void;
}) {
	return (
		<li className="flex items-start gap-3 py-3">
			<input
				id={`check-${row.idx}`}
				type="checkbox"
				checked={row.is_done}
				disabled={disabled}
				onChange={onToggle}
				className="mt-0.5 h-4 w-4 flex-none accent-blue disabled:opacity-50"
			/>
			<label htmlFor={`check-${row.idx}`} className="min-w-0 flex-1 cursor-pointer">
				<span
					className={cx(
						"block text-[12.5px] leading-snug",
						row.is_done ? "text-muted line-through" : "font-medium text-ink",
					)}
				>
					{row.item}
				</span>
				<span className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-muted">
					{row.is_required ? "Required" : "Optional"}
					{row.done_on && <>· ticked {formatDate(row.done_on)}</>}
					{busy && <>· saving…</>}
				</span>
				{row.notes && <span className="mt-1 block text-[11.5px] text-slate-body">{row.notes}</span>}
			</label>
			{row.evidence && (
				<a
					href={row.evidence}
					target="_blank"
					rel="noreferrer"
					className="flex-none text-[11.5px] font-bold text-blue"
				>
					Evidence
				</a>
			)}
		</li>
	);
}

/* ------------------------------------------------------------- conversation */

/** Which side of the conversation an entry is. Display only; nothing branches on it. */
const COORDINATOR_ENTRIES = new Set([
	"assigned",
	"answer",
	"progress requested",
	"completed",
	"returned",
	"cancelled",
]);

const ENTRY_LABEL: Record<string, string> = {
	assigned: "Assigned",
	accepted: "Accepted",
	question: "Your question",
	answer: "Coordinator replied",
	"progress requested": "Coordinator asked for an update",
	progress: "Your update",
	submitted: "Submitted for review",
	completed: "Signed off",
	returned: "Changes requested",
	cancelled: "Cancelled",
	declined: "Declined",
};

function Conversation({
	task,
	busy,
	message,
	onMessage,
	proof,
	onProof,
	onError,
	percent,
	onPercent,
	progressNote,
	onProgressNote,
	onAsk,
	onProgress,
}: {
	task: TaskDetail;
	busy: string | null;
	message: string;
	onMessage: (value: string) => void;
	proof: string | null;
	onProof: (url: string | null) => void;
	onError: (message: string) => void;
	percent: number;
	onPercent: (value: number) => void;
	progressNote: string;
	onProgressNote: (value: string) => void;
	onAsk: () => void;
	onProgress: () => void;
}) {
	return (
		<>
			<Card pad={false}>
				<div className="flex items-center gap-3 border-b border-card-line px-5 py-4">
					<span
						className="grid h-10 w-10 flex-none place-items-center rounded-full bg-rail text-[12px] font-bold text-white"
						aria-hidden="true"
					>
						<Icon.chat size={17} />
					</span>
					<div className="min-w-0 flex-1">
						<span className="block text-[10px] font-bold uppercase tracking-[0.08em] text-blue">
							Task conversation
						</span>
						<h2 className="mt-0.5 font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
							You and your coordinator
						</h2>
						<p className="mt-0.5 text-[11.5px] text-muted">
							Every message here is kept on this task's record.
						</p>
					</div>
					{task.open_question && (
						<span className="flex-none rounded-full bg-blue-soft px-2.5 py-1 text-[10.5px] font-bold text-blue-press">
							Waiting for reply
						</span>
					)}
				</div>

				<div className="space-y-3 bg-canvas px-5 py-5">
					{task.thread.length === 0 ? (
						<p className="py-4 text-center text-[12.5px] text-muted">Nothing yet.</p>
					) : (
						<ol className="space-y-3">
							{task.thread.map((entry, index) => {
								const fromCoordinator = COORDINATOR_ENTRIES.has(entry.entry_type);
								const attention =
									entry.entry_type === "returned" || entry.entry_type === "progress requested";
								return (
									<li
										key={index}
										className={cx(
											"flex gap-2.5",
											fromCoordinator ? "flex-row" : "flex-row-reverse",
										)}
									>
										<span
											className={cx(
												"mt-0.5 grid h-7 w-7 flex-none place-items-center rounded-full text-[10px] font-bold",
												fromCoordinator ? "bg-blue-soft text-blue-press" : "bg-rail text-white",
											)}
											aria-hidden="true"
										>
											{fromCoordinator ? "C" : "Y"}
										</span>
										<div
											className={cx(
												// The concept's asymmetric bubble: the square corner points
												// at the speaker, so the two sides of the conversation read
												// apart at a glance.
												"w-[min(86%,560px)] rounded-xl px-3.5 py-3",
												fromCoordinator ? "rounded-tl-[4px]" : "rounded-tr-[4px]",
												attention
													? "border border-warning-line bg-warning-soft"
													: fromCoordinator
														? "border border-card-line bg-white"
														: "bg-rail-soft text-white",
											)}
										>
											<div className="flex flex-wrap items-baseline justify-between gap-2">
												<span
													className={cx(
														"text-[10.5px] font-bold uppercase tracking-[0.06em]",
														attention
															? "text-warning"
															: fromCoordinator
																? "text-blue-press"
																: "text-aqua",
													)}
												>
													{ENTRY_LABEL[entry.entry_type] ?? entry.entry_type}
												</span>
												<span
													className={cx(
														"text-[11px]",
														fromCoordinator || attention ? "text-slate-faint" : "text-white/60",
													)}
												>
													{entry.author} · {formatDate(entry.posted_on)}
												</span>
											</div>
											{entry.note && (
												<p
													className={cx(
														"mt-1.5 whitespace-pre-wrap text-[12.5px] leading-relaxed",
														fromCoordinator || attention ? "text-slate-body" : "text-white/85",
													)}
												>
													{entry.note}
												</p>
											)}
											{entry.proof && (
												<a href={entry.proof} target="_blank" rel="noreferrer" className="mt-2 block">
													<img
														src={entry.proof}
														alt="Attached as evidence"
														className="max-h-52 rounded-lg border border-card-line object-cover"
													/>
												</a>
											)}
										</div>
									</li>
								);
							})}
						</ol>
					)}
				</div>

				{task.is_open && (
					<div className="border-t border-card-line px-5 py-4">
						<label
							htmlFor="task-message"
							className="mb-1.5 block text-[12px] font-semibold text-slate-strong"
						>
							Message
						</label>
						<textarea
							id="task-message"
							value={message}
							onChange={(event) => onMessage(event.target.value)}
							placeholder="Write your clarification for the coordinator"
							className="min-h-[82px] w-full resize-y rounded-xl border border-card-line px-3.5 py-3 text-[13px] leading-relaxed outline-none transition focus:border-blue"
						/>
						<div className="mt-3 flex flex-wrap items-center justify-between gap-3">
							<ProofUpload proof={proof} onProof={onProof} onError={onError} />
							<Button
								tone="quiet"
								busy={busy === "ask"}
								disabled={busy !== null || !message.trim()}
								onClick={onAsk}
							>
								Send clarification
							</Button>
						</div>
						<p className="mt-2 text-[11px] text-muted">
							Sending a clarification marks this task as waiting for an answer. It does not submit
							the work.
						</p>
					</div>
				)}
			</Card>

			{task.status === "accepted" && (
				<Card>
					<h2 className="font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
						Report progress
					</h2>
					<p className="mt-1 text-[11.5px] text-muted">
						Progress is separate from a clarification and does not submit or complete the task.
					</p>

					<label className="mt-4 flex flex-wrap items-center gap-3 text-[12px] font-semibold text-slate-strong">
						<span>Your progress estimate</span>
						<input
							type="range"
							min={0}
							max={100}
							step={5}
							value={percent}
							onChange={(event) => onPercent(Number(event.target.value))}
							className="h-1.5 w-full max-w-[220px] accent-blue"
						/>
						<output className="w-10 text-right font-bold text-ink tabular">{percent}%</output>
					</label>

					<textarea
						value={progressNote}
						onChange={(event) => onProgressNote(event.target.value)}
						placeholder="Tell the coordinator how the work is going"
						className="mt-3 min-h-[76px] w-full resize-y rounded-xl border border-card-line px-3.5 py-3 text-[13px] leading-relaxed outline-none transition focus:border-blue"
					/>

					<div className="mt-3">
						<Button
							tone="quiet"
							busy={busy === "progress"}
							disabled={busy !== null || !progressNote.trim()}
							onClick={onProgress}
						>
							Report progress
						</Button>
					</div>
				</Card>
			)}
		</>
	);
}

/* ----------------------------------------------------------------- outcome */

function Outcome({ task }: { task: TaskDetail }) {
	return (
		<Card>
			<h2 className="mb-4 font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
				Completion and outcome
			</h2>

			{task.status === "submitted" && (
				<div className="mb-4">
					<Notice>
						You have offered this as done. A coordinator signs it off before it is complete — you
						will be notified either way.
					</Notice>
				</div>
			)}

			<Facts
				columns={2}
				items={[
					{ label: "Submitted on", value: formatDate(task.submitted_on) },
					{ label: "Closed on", value: formatDate(task.closed_on) },
					{ label: "Completion notes", value: task.completion_notes || "—" },
					{ label: "Outcome", value: task.outcome || "—" },
					{ label: "Times returned", value: String(task.rework_count) },
					{ label: "Last return reason", value: task.return_reason || "—" },
					task.decline_reason ? { label: "Reason for declining", value: task.decline_reason } : null,
					task.lessons_learned ? { label: "Lessons learned", value: task.lessons_learned } : null,
				]}
			/>
		</Card>
	);
}

/* ------------------------------------------------------------------ upload */

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
			const res = await fetch("/api/method/upload_file", {
				method: "POST",
				body,
				headers: { "X-Frappe-CSRF-Token": window.csrf_token ?? "" },
			});
			if (!res.ok) throw new Error("The upload was refused.");
			const payload = (await res.json()) as { message?: { file_url?: string } };
			const url = payload.message?.file_url;
			if (!url) throw new Error("The upload came back without a file.");
			onProof(url);
		} catch (e) {
			onError(errorMessage(e, "That photograph could not be uploaded."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div className="flex flex-wrap items-center gap-3">
			<label className="inline-flex cursor-pointer items-center gap-2 text-[12px] font-bold text-blue transition hover:text-blue-hover">
				<Icon.upload size={14} />
				{busy ? "Uploading…" : proof ? "Replace image" : "Attach image"}
				<input
					type="file"
					accept="image/*"
					className="sr-only"
					onChange={(event) => {
						const file = event.target.files?.[0];
						if (file) void upload(file);
					}}
				/>
			</label>
			{proof && (
				<span className="flex items-center gap-2">
					<img src={proof} alt="" className="h-8 w-8 rounded-lg object-cover" />
					<button
						type="button"
						className="text-[11.5px] font-semibold text-muted hover:text-danger"
						onClick={() => onProof(null)}
					>
						Remove
					</button>
				</span>
			)}
		</div>
	);
}

/* --------------------------------------------------------- console exports */

/**
 * The task-state badge and thread the **console** uses, kept here unchanged
 * because `admin/Tasks.tsx` imports both. The portal draws its own above; the
 * two exist because the console's grey shell and the portal's kit are separate
 * visual worlds.
 */
export function TaskState({ status, onDark }: { status: string; onDark?: boolean }) {
	const CONSOLE_TONES: Record<string, string> = {
		assigned: "border-warning-line text-warning bg-warning-soft",
		accepted: "border-blue-line text-blue bg-blue-soft",
		submitted: "border-tint-sky/40 text-tint-sky bg-tint-sky-soft",
		completed: "border-success-line text-success bg-success-soft",
		cancelled: "border-card-line text-muted bg-surface",
	};
	return (
		<span
			className={cx(
				"inline-flex flex-none items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-[11px] font-bold capitalize",
				onDark
					? "border-white/25 bg-white/10 text-white"
					: (CONSOLE_TONES[status] ?? "border-card-line text-muted bg-surface"),
			)}
		>
			<span className="h-1.5 w-1.5 flex-none rounded-full bg-current" aria-hidden="true" />
			{status}
		</span>
	);
}

export function Thread({ thread }: { thread: TaskDetail["thread"] }) {
	if (thread.length === 0) {
		return <p className="py-4 text-center text-[12.5px] text-slate-faint">Nothing yet.</p>;
	}
	return (
		<ol className="space-y-3">
			{thread.map((entry, index) => (
				<li key={index} className="rounded-xl bg-surface px-4 py-3.5">
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
								className="max-h-52 rounded-lg border border-card-line object-cover"
							/>
						</a>
					)}
				</li>
			))}
		</ol>
	);
}
