import { MetricCard } from "../ui/MetricCard";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { branchPath, formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import {
	Avatar,
	Card,
	Empty,
	ErrorNote,
	PageHeading,
	Pill,
	SectionLink,
	SectionTitle,
	Skeleton,
	cx,
} from "../ui/primitives";
import { QUEUES, type QueueKind, queueOf } from "./queues";
import type { ApprovalStatus, IntakeHealth, PeopleSummary } from "../portal/types";

/** Applications and active registers for the current manager. */
export default function PeopleOverview() {
	const summary = useFrappeGetCall<{ message: PeopleSummary }>(
		API.peopleSummary,
		undefined,
		"people:summary",
	);

	// The attention list itself, which is the queue's own rows rather than a
	// count of them: this panel names people, and a number cannot be clicked.
	const queue = useFrappeGetCall<{ message: ApprovalStatus[] }>(API.myQueue, undefined, "admin:my_queue");

	const answer = summary.data?.message;
	const waiting = queue.data?.message ?? [];
	const failure = summary.error || queue.error;

	// Ordered the way an approver works: what is already late, then what has been
	// waiting longest. Sorted here rather than server-side because this is a
	// presentation of the queue the engine already decided the membership of.
	const attention = [...waiting].sort((left, right) => {
		const late = Number(right.stage?.is_breached ?? false) - Number(left.stage?.is_breached ?? false);
		if (late !== 0) return late;

		return (left.stage?.entered_on ?? "").localeCompare(right.stage?.entered_on ?? "");
	});

	const totalWaiting = waiting.length;
	const totalOverdue = waiting.filter((row) => row.stage?.is_breached).length;
	const register = (kind: string) => answer?.registers.find((row) => row.kind === kind)?.active;

	return (
		<>
			<PageHeading
				title={<EditableText k="admin.people.heading" fallback="People Management" />}
				lead="Manage applications, volunteers and members."
			/>

			{failure && (
				<div className="mb-5">
					<ErrorNote>{errorMessage(failure, "People totals could not be loaded.")}</ErrorNote>
				</div>
			)}

			{/* ------------------------------------------------------------ pulse */}
			<div className="mb-5 grid gap-3 md:grid-cols-3">
				<PulseTile
					to="/admin/queue/volunteers"
					label="Waiting for your decision"
					value={queue.isLoading ? null : totalWaiting}
					urgent={totalOverdue > 0}
					detail={
						queue.isLoading ? "Loading your queue…" : kindBreakdown(waiting) || "No applications assigned"
					}
					flag={totalOverdue > 0 ? `${totalOverdue} overdue` : undefined}
					icon={Icon.inbox}
				/>
				<PulseTile
					to="/admin/registry/volunteers"
					label="Active volunteers"
					value={summary.isLoading ? null : (register("volunteers") ?? null)}
					detail="Volunteers in your assigned branches"
					action="Open register"
					icon={Icon.people}
				/>
				<PulseTile
					to="/admin/registry/members"
					label="Active members"
					value={summary.isLoading ? null : (register("members") ?? null)}
					detail="Members in your assigned branches"
					action="Open register"
					icon={Icon.card}
				/>
			</div>

			{/* ------------------------------------------------- attention + search */}
			{/* `min-w-0` on the tracks: a grid item's `min-width` is `auto`, so a
			    single long unbreakable value — an applicant's docname, a geo path
			    with no spaces in a rung — widens the whole column and the page
			    scrolls sideways on a phone. `truncate` cannot help until an
			    ancestor is allowed to be narrower than its content. */}
			<div className="mb-5 grid items-start gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
				<Card pad={false} className="min-w-0">
					<div className="flex flex-wrap items-start justify-between gap-3 px-5 pb-3 pt-4">
						<div className="min-w-0">
							<SectionTitle>Applications to review</SectionTitle>
							<p className="mt-0.5 text-[11.5px] text-muted">Overdue applications appear first.</p>
						</div>
						{totalWaiting > 0 && <SectionLink to="/admin/queue/volunteers">See all</SectionLink>}
					</div>

					{queue.isLoading && (
						<div className="px-5 pb-5">
							<Skeleton className="h-28" />
						</div>
					)}

					{!queue.isLoading && attention.length === 0 && (
						<div className="px-5 pb-5">
							<Empty title="No applications to review">Applications assigned to you will appear here.</Empty>
						</div>
					)}

					{attention.length > 0 && (
						<ul className="divide-y divide-card-line border-t border-card-line">
							{attention.slice(0, 6).map((row) => (
								<li key={`${row.doctype}:${row.name}`}>
									<AttentionRow row={row} />
								</li>
							))}
						</ul>
					)}
				</Card>

				<div className="min-w-0">
					<PersonSearch />
     {answer?.people && <p className="mt-3 text-[11.5px] text-muted">{answer.people.unique != null ? <><span>Unique active people</span>: <strong>{answer.people.unique.toLocaleString()}</strong> · <span>{answer.people.both ?? 0} hold both volunteer and member registrations.</span></> : answer.people.capped ? "A unique-person figure counted from a truncated read would be wrong." : null}</p>}
				</div>
			</div>

			<Card className="min-w-0">
				<SectionTitle>Applications overview</SectionTitle>
				<p className="mt-1 text-[12px] text-muted">Current applications in your assigned branches.</p>
				{summary.isLoading ? (
					<Skeleton className="mt-5 h-48" />
				) : (
					<IntakeChart doors={answer?.intake ?? []} />
				)}
			</Card>
		</>
	);
}

/* --------------------------------------------------------------- the pulse */

/** One headline figure, as a link to the screen it is a figure about. */
function PulseTile({
	to,
	label,
	value,
	detail,
	flag,
	action,
	urgent,
	icon: Glyph,
}: {
	to: string;
	label: string;
	/** `null` while the read is in flight. Zero is a real answer and is shown. */
	value: number | null;
	detail: string;
	flag?: string;
	action?: string;
	urgent?: boolean;
	icon: (props: { size?: number }) => React.ReactNode;
}) {
	return (
		<MetricCard
			to={to}
			label={label}
			value={value === null ? "—" : value.toLocaleString()}
			icon={<Glyph size={19} />}
			badge={flag}
			negative={urgent}
			note={
				<>
					{detail}
					{action && <span className="mt-3 block font-semibold text-blue-press">{action} →</span>}
				</>
			}
		/>
	);
}

/**
 * "8 volunteer · 4 membership", built from the queue's own rows.
 *
 * `queueOf` maps a governed doctype to the queue it belongs to, and it is the
 * one place in this app that names one. A doctype with no queue of its own is
 * left out rather than lumped in with whichever sorts first.
 */
function kindBreakdown(rows: ApprovalStatus[]): string {
	const counted = new Map<QueueKind, number>();

	for (const row of rows) {
		const kind = queueOf(row.doctype);
		if (kind) counted.set(kind, (counted.get(kind) ?? 0) + 1);
	}

	return [...counted]
		.map(([kind, count]) => `${count} ${QUEUES[kind].noun.replace(" applicant", "")}`)
		.join(" · ");
}

/* ------------------------------------------------------------- attention */

/** One application waiting on this reader, as a row they can open. */
function AttentionRow({ row }: { row: ApprovalStatus }) {
	const kind = queueOf(row.doctype);
	const to = kind ? `${QUEUES[kind].list}/${encodeURIComponent(row.name)}` : null;
	const late = row.stage?.is_breached;

	const body = (
		<>
			<Avatar name={row.applicant?.full_name} photo={row.applicant?.photo} size={34} />

			<span className="min-w-0 flex-1">
				<span className="block truncate text-[13px] font-semibold text-ink">
					{row.applicant?.full_name ?? row.name}
				</span>
				<span className="mt-0.5 block truncate text-[11.5px] text-muted">
					{kind ? QUEUES[kind].heading : row.doctype}
					{row.geo_path ? ` · ${branchPath(row.geo_path)}` : ""}
				</span>
			</span>

			{row.stage && (
				<span className="hidden min-w-0 flex-none sm:block">
					<span className="block text-[10.5px] uppercase tracking-[0.06em] text-muted">Stage</span>
					{/* Displayed, never compared: a stage label is a society's own
					    wording and this app holds no table of them. */}
					<span className="block truncate text-[12px] font-semibold text-ink">{row.stage.label}</span>
				</span>
			)}

			{/* Dropped on a phone: the name is what a coordinator is scanning for,
			    and a date that costs half of it is a bad trade. The overdue pill
			    beside it carries the urgency, which is the part that cannot wait
			    for the record to be opened. */}
			<span className="hidden flex-none sm:block">
				<span className="block text-[10.5px] uppercase tracking-[0.06em] text-muted">Waiting</span>
				<span className="tabular block text-[12px] font-semibold text-ink">
					{formatDate(row.stage?.entered_on ?? null)}
				</span>
			</span>

			{late ? (
				<span className="flex-none">
					<Pill tone="signal">{row.stage?.days_overdue} days over</Pill>
				</span>
			) : (
				<span className="hidden text-[11.5px] text-muted md:block">
					{row.stage?.due_on ? `Due ${formatDate(row.stage.due_on)}` : "No deadline set"}
				</span>
			)}
		</>
	);

	// A row whose doctype has no queue screen is still shown — it is genuinely in
	// this person's queue — but it is not a link to nowhere.
	if (!to) {
		return <div className="flex items-center gap-3 px-5 py-3">{body}</div>;
	}

	return (
		<Link to={to} className="flex items-center gap-3 px-5 py-3 transition hover:bg-surface">
			{body}
		</Link>
	);
}

/** Both application types use the same scale; assignments and overdue counts
 * overlap the review count, so they are annotations rather than extra bars. */
function IntakeChart({ doors }: { doors: IntakeHealth[] }) {
	const maximum = Math.max(1, ...doors.flatMap((door) => [door.in_review ?? 0, door.changes_requested ?? 0]));
	const ceiling = Math.ceil(maximum / 4) * 4;
	if (!doors.length) return <Empty title="No application data available" />;
	return (
		<div className="intake-chart">
			<div className="intake-legend" aria-hidden="true">
				<span>
					<i className="bg-blue" />
					In review
				</span>
				<span>
					<i className="bg-slate-faint" />
					Changes requested
				</span>
			</div>
			<ul className="intake-chart-rows">
				{doors.map((door) => {
					const kind = queueOf(door.doctype);
					const heading = kind ? QUEUES[kind].heading : door.doctype;
					const figures = [
						{ label: "In review", value: door.in_review, color: "bg-blue" },
						{ label: "Changes requested", value: door.changes_requested, color: "bg-slate-faint" },
					];
					return (
						<li key={door.doctype} className="intake-chart-row">
							<div className="intake-chart-label">
								{kind ? (
									<Link to={QUEUES[kind].list} className="font-semibold hover:underline">
										{heading} →
									</Link>
								) : (
									<strong>{heading}</strong>
								)}
								{door.governed && (
									<div className="mt-2 flex flex-wrap gap-2 text-[11.5px] text-muted">
										<span>{door.waiting} assigned to you</span>
										<span>·</span>
										<span>
											{door.breached == null ? "Overdue count unavailable" : `${door.breached} overdue`}
										</span>
									</div>
								)}
							</div>
							<div className="intake-chart-bars">
								{door.readable && door.governed ? (
									figures.map((figure) => (
										<div
											key={figure.label}
											className="intake-chart-series"
											aria-label={`${heading}: ${figure.label}, ${figure.value ?? "unavailable"}`}
										>
											<span className="sr-only">{figure.label}</span>
											<div className="intake-chart-track" aria-hidden="true">
												<span
													className={figure.color}
													style={{ width: `${((figure.value ?? 0) / ceiling) * 100}%` }}
												/>
											</div>
											<strong>{figure.value ?? "—"}</strong>
										</div>
									))
								) : (
									<p className="text-[12px] text-muted">
										{!door.readable
											? "You do not have access to these applications."
											: <><span>{door.awaiting_setup ?? 0} applications awaiting workflow setup.</span> <span>{door.awaiting_setup ? "Needs setup" : "Not governed"}</span></>}
									</p>
								)}
							</div>
						</li>
					);
				})}
			</ul>
			<div className="intake-chart-axis" aria-hidden="true">
				{Array.from({ length: 5 }, (_, i) => (
					<span key={i}>{(ceiling * i) / 4}</span>
				))}
			</div>
		</div>
	);
}

/* ------------------------------------------------------------ find a person */

/**
 * The way into either register by name.
 *
 * It navigates rather than searching in place, and that is the point: the
 * register is the screen with the paging, the filters and the permission-scoped
 * read, so this hands the question to it as a URL somebody can bookmark or send
 * on. Nothing here queries anything, so there is no second search with a second
 * idea of scope.
 */
function PersonSearch() {
	const navigate = useNavigate();
	const [term, setTerm] = useState("");
	const [where, setWhere] = useState<QueueKind>("volunteers");

	const registers: Array<{ kind: QueueKind; label: string; to: string; lead: string }> = [
		{
			kind: "volunteers",
			label: "Volunteer register",
			to: "/admin/registry/volunteers",
			lead: "Active volunteers, narrowed by branch",
		},
		{
			kind: "members",
			label: "Member register",
			to: "/admin/registry/members",
			lead: "Active memberships, by branch and type",
		},
	];

	const target = registers.find((row) => row.kind === where) ?? registers[0];

	return (
		<Card>
			<SectionTitle>Find a person</SectionTitle>
			<p className="mt-0.5 text-[11.5px] text-muted">Search volunteers and members.</p>

			<form
				className="mt-3"
				onSubmit={(event) => {
					event.preventDefault();
					const query = term.trim();
					navigate(query ? `${target.to}?q=${encodeURIComponent(query)}` : target.to);
				}}
			>
				<label className="block">
					<span className="mb-1.5 block text-[11.5px] font-semibold text-slate-strong">
						Name or record number
					</span>
					<div className="flex gap-2">
						<input
							type="search"
							value={term}
							onChange={(event) => setTerm(event.target.value)}
							placeholder="A name, or a record number"
							className="min-w-0 flex-1 rounded-lg border border-card-line bg-white px-3 py-2 text-[13px] outline-none transition placeholder:text-slate-faint focus:border-blue"
						/>
						<button
							type="submit"
							className="flex-none rounded-lg bg-rail px-4 py-2 text-[12.5px] font-bold text-white transition hover:bg-rail-soft"
						>
							Search
						</button>
					</div>
				</label>

				<fieldset className="mt-3">
					<legend className="sr-only">Which register to search</legend>
					<div className="flex gap-1.5">
						{registers.map((row) => (
							<label
								key={row.kind}
								className={cx(
									"cursor-pointer rounded-full border px-3 py-1.5 text-[11.5px] font-semibold transition",
									where === row.kind
										? "border-blue bg-blue-soft text-blue-press"
										: "border-card-line text-slate-strong hover:border-blue",
								)}
							>
								<input
									type="radio"
									name="register"
									className="sr-only"
									checked={where === row.kind}
									onChange={() => setWhere(row.kind)}
								/>
								{row.label}
							</label>
						))}
					</div>
				</fieldset>
			</form>

			<ul className="mt-4 space-y-1.5 border-t border-card-line pt-3">
				{registers.map((row) => (
					<li key={row.kind}>
						<Link to={row.to} className="block rounded-lg px-3 py-2 transition hover:bg-surface">
							<span className="block text-[12.5px] font-semibold text-ink">{row.label}</span>
							<span className="block text-[11px] text-muted">{row.lead}</span>
						</Link>
					</li>
				))}
			</ul>
		</Card>
	);
}
