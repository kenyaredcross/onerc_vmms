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

/**
 * People Management's front page: what is waiting on you, what is stuck coming
 * in, and how many people are actually on the books here.
 *
 * **Every figure on this screen is a server aggregate over the caller's own
 * scope.** That is the rule the previous version broke: it asked each register
 * for one row and read the `total` off it, which is honest, and it counted the
 * queue by filtering an array in the browser, which is honest only while the
 * queue is short. Both are now one call to `people.summary`, computed inside
 * `frappe.get_list` so core's permission query condition is the floor rather
 * than something this screen applies on top.
 *
 * **The unique-people block is drawn only when the server could compute it.**
 * A person who is both a volunteer and a member is two records and one human
 * being, and the union of the two registers' Red Profiles is a column read
 * rather than a count — affordable at branch size and not at national size. The
 * endpoint bounds it and answers `null` past the ceiling; this screen then omits
 * the block rather than showing a number derived from a truncated read. A
 * missing figure is a smaller failure than a wrong one.
 *
 * **Nothing here compares a stage label.** Overdue comes from
 * `stage.is_breached`, which the approval engine derives from the society's own
 * configured SLA; the label beside it is displayed and never branched on.
 */
export default function PeopleOverview() {
	const summary = useFrappeGetCall<{ message: PeopleSummary }>(
		API.peopleSummary,
		undefined,
		"people:summary",
	);

	// The attention list itself, which is the queue's own rows rather than a
	// count of them: this panel names people, and a number cannot be clicked.
	const queue = useFrappeGetCall<{ message: ApprovalStatus[] }>(
		API.myQueue,
		undefined,
		"admin:my_queue",
	);

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
				title={<EditableText k="admin.people.heading" fallback="People in your care" />}
				lead="Review who is coming in, and work with the people already registered — inside the areas your Geo Assignments cover."
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
						queue.isLoading
							? "Loading your queue…"
							: kindBreakdown(waiting) || "Nothing is routed to you"
					}
					flag={totalOverdue > 0 ? `${totalOverdue} overdue` : undefined}
					icon={Icon.inbox}
				/>
				<PulseTile
					to="/admin/registry/volunteers"
					label="Active volunteers in scope"
					value={summary.isLoading ? null : (register("volunteers") ?? null)}
					detail="Standing and serving branch at a glance"
					action="Open register"
					icon={Icon.people}
				/>
				<PulseTile
					to="/admin/registry/members"
					label="Active memberships in scope"
					value={summary.isLoading ? null : (register("members") ?? null)}
					detail="Every branch-specific membership"
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
							<SectionTitle>Attention queue</SectionTitle>
							<p className="mt-0.5 text-[11.5px] text-muted">
								Routed to you specifically, oldest and most overdue first.
							</p>
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
							<Empty title="Nothing is waiting on you">
								Applications appear here when the approval engine routes one to you
								specifically, not to everybody who holds your role.
							</Empty>
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
				</div>
			</div>

			{/* --------------------------------------------------------- the lower */}
			<div className="grid items-start gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
				<Card pad={false} className="min-w-0">
					<div className="px-5 pb-3 pt-4">
						<SectionTitle>Intake health</SectionTitle>
						<p className="mt-0.5 text-[11.5px] text-muted">
							Every route into the society, with what is stuck in it visible.
						</p>
					</div>

					{summary.isLoading && (
						<div className="px-5 pb-5">
							<Skeleton className="h-24" />
						</div>
					)}

					{!summary.isLoading && (
						<ul className="divide-y divide-card-line border-t border-card-line">
							{(answer?.intake ?? []).map((door) => (
								<li key={door.doctype}>
									<IntakeRow door={door} />
								</li>
							))}
						</ul>
					)}
				</Card>

				<div className="min-w-0">
					<ActivePeople summary={answer} loading={summary.isLoading} />
				</div>
			</div>
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
		<Link
			to={to}
			className={cx(
				"group block rounded-xl border bg-white p-4 transition hover:border-blue",
				urgent ? "border-danger-line" : "border-card-line",
			)}
		>
			<div className="flex items-start gap-3">
				<span
					aria-hidden="true"
					className={cx(
						"grid h-9 w-9 flex-none place-items-center rounded-lg",
						urgent ? "bg-danger-soft text-danger" : "bg-blue-soft text-blue-press",
					)}
				>
					<Glyph size={17} />
				</span>

				<div className="min-w-0 flex-1">
					<div className="text-[11.5px] font-semibold uppercase tracking-[0.06em] text-muted">
						{label}
					</div>
					<div className="tabular mt-1 text-[26px] font-semibold leading-none text-ink">
						{value === null ? "—" : value.toLocaleString()}
					</div>
					<p className="mt-1.5 text-[11.5px] text-muted">{detail}</p>
				</div>

				{flag && (
					<span className="flex-none rounded-full bg-danger-soft px-2 py-1 text-[10.5px] font-bold text-danger">
						{flag}
					</span>
				)}
			</div>

			{action && (
				<span className="mt-3 block text-[12px] font-semibold text-blue-press group-hover:underline">
					{action} →
				</span>
			)}
		</Link>
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
					<span className="block truncate text-[12px] font-semibold text-ink">
						{row.stage.label}
					</span>
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
					{row.stage?.due_on ? `Due ${formatDate(row.stage.due_on)}` : "No SLA set"}
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

/* ----------------------------------------------------------- intake health */

/** One door into the society, and the three numbers that say whether it flows. */
function IntakeRow({ door }: { door: IntakeHealth }) {
	const kind = queueOf(door.doctype);
	const to = kind ? QUEUES[kind].list : null;
	const heading = kind ? QUEUES[kind].heading : door.doctype;

	const body = (
		<>
			<span className="min-w-0 flex-1 basis-full sm:basis-auto">
				<span className="block truncate text-[13px] font-semibold text-ink">{heading}</span>
				<span className="mt-0.5 block text-[11.5px] text-muted">
					{door.governed
						? "Through the society's configured approval stages"
						: door.readable
							? "No approval workflow is configured for this yet"
							: "These applications are not in your permissions"}
				</span>
			</span>

			<IntakeFigure label="In review" value={door.in_review} />
			<IntakeFigure label="Changes" value={door.changes_requested} />
			<IntakeFigure label="Yours" value={door.governed ? door.waiting : null} />

			{door.breached ? (
				<span className="flex-none">
					<Pill tone="signal">{door.breached} overdue</Pill>
				</span>
			) : (
				<span
					className={cx(
						"hidden flex-none text-[11.5px] font-semibold md:block",
						door.governed ? "text-success" : "text-muted",
					)}
				>
					{door.governed ? "Within SLA" : door.readable ? "Not governed" : "Not visible"}
				</span>
			)}
		</>
	);

	const shape = "flex flex-wrap items-center gap-x-4 gap-y-1.5 px-5 py-3.5 sm:flex-nowrap";

	if (!to) return <div className={shape}>{body}</div>;

	return (
		<Link to={to} className={cx(shape, "transition hover:bg-surface")}>
			{body}
		</Link>
	);
}

/**
 * One of the three numbers that say whether a door is flowing.
 *
 * **Shown on a phone too, laid out differently.** These used to disappear below
 * `sm`, which left the row saying only what the door was called — and the
 * numbers are the entire reason the block exists. On a narrow screen they sit
 * inline under the title instead of in a column of their own.
 */
function IntakeFigure({ label, value }: { label: string; value: number | null }) {
	return (
		<span className="flex flex-none items-baseline gap-1.5 sm:block sm:text-right">
			<span className="text-[10.5px] uppercase tracking-[0.06em] text-muted sm:block">
				{label}
			</span>
			{/* A dash for "the server could not say", never a zero: an ungoverned
			    doctype has no applications in review and also has no review. */}
			<span className="tabular text-[13px] font-semibold text-ink sm:block">{value ?? "—"}</span>
		</span>
	);
}

/* ---------------------------------------------------- active people in scope */

/**
 * The two registers counted as people rather than as records.
 *
 * Drawn only when the server could compute it. See this file's own docstring:
 * a figure derived from a truncated read is worse than a block that is not
 * there, so `capped` removes the block and says why in one line.
 */
function ActivePeople({ summary, loading }: { summary?: PeopleSummary; loading: boolean }) {
	const reach = summary?.people;
	const volunteers = summary?.registers.find((row) => row.kind === "volunteers")?.active ?? 0;
	const members = summary?.registers.find((row) => row.kind === "members")?.active ?? 0;

	return (
		<Card>
			<SectionTitle>Active people in scope</SectionTitle>
			<p className="mt-0.5 text-[11.5px] text-muted">Current registers, not applications.</p>

			{loading && <Skeleton className="mt-4 h-24" />}

			{!loading && reach && !reach.capped && reach.unique !== null && (
				<div className="mt-4 rounded-xl bg-surface px-4 py-3.5">
					<div className="text-[11.5px] font-semibold uppercase tracking-[0.06em] text-muted">
						Unique active people
					</div>
					<div className="tabular mt-1 text-[28px] font-semibold leading-none text-ink">
						{reach.unique.toLocaleString()}
					</div>
					<p className="mt-1.5 text-[11.5px] text-muted">
						{reach.both?.toLocaleString()} hold both a volunteer record and a membership, counted
						once through the Red Profile they share.
					</p>
				</div>
			)}

			{!loading && reach?.capped && (
				<p className="mt-4 rounded-xl bg-surface px-4 py-3 text-[11.5px] leading-relaxed text-muted">
					The unique-person figure is not shown here: your scope holds more records than can be
					de-duplicated in one request, and a number counted from a truncated read would be wrong
					rather than approximate. The two register totals below are exact.
				</p>
			)}

			<ul className="mt-4 space-y-2">
				<RegisterSplit
					to="/admin/registry/volunteers"
					label="Active volunteers"
					value={loading ? null : volunteers}
				/>
				<RegisterSplit
					to="/admin/registry/members"
					label="Active memberships"
					value={loading ? null : members}
				/>
			</ul>
		</Card>
	);
}

function RegisterSplit({ to, label, value }: { to: string; label: string; value: number | null }) {
	return (
		<li>
			<Link
				to={to}
				className="flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 transition hover:bg-surface"
			>
				<span className="text-[12.5px] font-medium text-slate-strong">{label}</span>
				<span className="tabular text-[15px] font-semibold text-ink">
					{value === null ? "—" : value.toLocaleString()}
				</span>
			</Link>
		</li>
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
			<p className="mt-0.5 text-[11.5px] text-muted">
				Searches only the records you are authorised to see.
			</p>

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
						<Link
							to={row.to}
							className="block rounded-lg px-3 py-2 transition hover:bg-surface"
						>
							<span className="block text-[12.5px] font-semibold text-ink">{row.label}</span>
							<span className="block text-[11px] text-muted">{row.lead}</span>
						</Link>
					</li>
				))}
			</ul>
		</Card>
	);
}
