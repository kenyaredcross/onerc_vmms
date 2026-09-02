import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import {
	ButtonLink,
	Empty,
	ErrorNote,
	NotBuilt,
	PageHeading,
	Pager,
	Spinner,
	cx,
	usePaged,
} from "../ui/primitives";
import type { Opportunity, VolunteerProfile } from "./types";

/**
 * The society's notice board: the posts it is recruiting for.
 *
 * **This reads HRMS's `Job Opening`**, through `api/opportunities.py` and the
 * seam in `vmmsx/hr/services/openings.py`. It used to read
 * `VMMS Deployment Request` — the society's internal record of needing people
 * somewhere — and everything this screen said was written for that: that there
 * was no Apply button and that a coordinator staffs a deployment by matching
 * volunteers to it.
 *
 * **All of that became untrue when the source changed, and this screen went on
 * saying it.** A job opening *is* answerable: HRMS owns the application form,
 * the duplicate check and the pipeline, and the seam has served an `apply_href`
 * to send somebody there the whole time. Worse, the old card rendered HRMS's
 * `description` — a Text Editor field, markup by construction — through a `<p>`
 * that escaped it, so every visitor read a wall of `<div class="ql-editor
 * read-mode">` where the job description should have been. Both faults were the
 * same fault: a screen left pointing at names that no longer meant what they
 * used to.
 *
 * **So the board advertises a post and offers a way to answer it.** Department,
 * designation, employment type, where it is held, when it closes, the
 * description as its author formatted it, and a button that goes to HRMS.
 *
 * **What it still does not do is apply on anybody's behalf.** There is no
 * application endpoint in vmmsx and there will not be one: HRMS owns every
 * record after "I want this", and a vmmsx form posting into that pipeline would
 * be a second implementation of rules that have to stay in step with HRMS's
 * forever. The button is a full navigation, not a fetch.
 *
 * **Deployments are not here any more either.** The old board carried a "My
 * deployments" tab because it was itself a deployment board. `MyDeployments` is
 * still exported — the sidebar's own Deployments page renders it — but a tab
 * about rosters on a screen about vacancies was two subjects sharing a heading.
 */

export default function Opportunities() {
	// What has been typed, and what has been asked. Kept apart so the endpoint is
	// called on submit rather than per keystroke: a search that fires per
	// character is a query per character, and the answer to a half-typed word is
	// noise on the screen.
	const [draft, setDraft] = useState("");
	const [search, setSearch] = useState("");
	const [department, setDepartment] = useState("");

	const facets = useFrappeGetCall<{
		message: { available: boolean; departments: Array<{ department: string; label: string }> };
	}>(API.opportunityFilters, undefined, "portal:opportunity_filters");

	const board = useFrappeGetCall<{
		message: { available: boolean; opportunities: Opportunity[] };
	}>(
		API.opportunitiesBrowse,
		{ search: search || undefined, department: department || undefined },
		// The key carries the query, so changing a facet refetches rather than
		// showing the previous answer under the new filter.
		`portal:opportunities:${search}:${department}`,
	);

	const rows = board.data?.message?.opportunities ?? [];
	const filtered = Boolean(search || department);

	// Is HRMS on this site at all? It travels with the rows rather than being a
	// second call, because the screen needs it at the moment it decides what to
	// draw: "the society is not recruiting" and "recruitment does not run on this
	// site" are different sentences to put in front of somebody.
	const available = board.data?.message?.available ?? true;

	// Eight to a page: four full rows of the two-column grid.
	const paged = usePaged(rows, 8);

	const clear = () => {
		setDraft("");
		setSearch("");
		setDepartment("");
	};

	return (
		<>
			<PageHeading
				title={<EditableText k="portal.opportunities.heading" fallback="Opportunities" />}
				trail={[{ label: "Home", to: "/dashboard" }, { label: "Opportunities" }]}
				actions={
					// The society's total, not the filtered one. "2 open" beside a
					// heading is a statement about the board; how many survived a
					// search is what the grid underneath already shows.
					available && !board.isLoading && rows.length > 0 && !filtered ? (
						<span className="rounded-full bg-blue/10 px-3.5 py-1.5 text-[12.5px] font-bold text-blue-press">
							{rows.length} open
						</span>
					) : undefined
				}
			/>

			{available && (
				<FilterBar
					draft={draft}
					setDraft={setDraft}
					onSearch={() => setSearch(draft.trim())}
					department={department}
					setDepartment={setDepartment}
					departments={facets.data?.message?.departments ?? []}
					filtered={filtered}
					onClear={clear}
				/>
			)}

			{board.isLoading && <Spinner label="Finding opportunities…" />}
			{board.error && <ErrorNote>{errorMessage(board.error)}</ErrorNote>}

			{/* Recruitment lives in HRMS. A site without it has no openings to show
			    and never will, which is a different answer from "nothing is open
			    today" and deserves to read like one. */}
			{!board.isLoading && !board.error && !available && (
				<NotBuilt
					what="The opportunities board"
					needs="It reads the society's job openings from its HR system, which is not installed on this site."
				/>
			)}

			{!board.isLoading && !board.error && available && rows.length === 0 && (
				<Empty
					icon={Icon.compass}
					title={filtered ? "Nothing matches that" : "No opportunities are open"}
				>
					{filtered
						? "Try a wider search, or clear the filters to see everything on the board."
						: "Your society advertises the posts it is recruiting for here. Nothing is open at the moment."}
				</Empty>
			)}

			{rows.length > 0 && (
				<>
					<div className="grid gap-4 lg:grid-cols-2">
						{paged.slice.map((row) => (
							<OpportunityCard key={row.name} row={row} />
						))}
					</div>

					<Pager
						page={paged.page}
						pageCount={paged.pageCount}
						onPage={paged.onPage}
						total={paged.total}
						noun="opportunities"
					/>
				</>
			)}
		</>
	);
}

/* -------------------------------------------------------------- filter bar */

function FilterBar({
	draft,
	setDraft,
	onSearch,
	department,
	setDepartment,
	departments,
	filtered,
	onClear,
}: {
	draft: string;
	setDraft: (value: string) => void;
	onSearch: () => void;
	department: string;
	setDepartment: (value: string) => void;
	departments: Array<{ department: string; label: string }>;
	filtered: boolean;
	onClear: () => void;
}) {
	const field =
		"w-full bg-transparent text-[13px] text-ink outline-none placeholder:text-slate-faint";

	return (
		<div className="mb-6 rounded-2xl bg-white p-2.5 border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]">
			<form
				onSubmit={(event) => {
					event.preventDefault();
					onSearch();
				}}
				className="grid gap-2 sm:grid-cols-[1.5fr_1fr_auto]"
			>
				<label className="control sm:border-r sm:border-card-line">
					<Icon.search size={15} className="flex-none text-slate-faint" />
					<span className="sr-only">Search opportunities</span>
					<input
						value={draft}
						onChange={(event) => setDraft(event.target.value)}
						placeholder="Search by job title"
						className={field}
					/>
				</label>

				{/* Department, and not location. Where an opening is held is HRMS's
				    own Branch record, which is not a Geo Node: this app does not
				    have a second answer to where a job is and does not invent one
				    by mapping between the two. The old cascading geo filter here
				    was filtering a field that no longer arrives. */}
				<label className="control">
					<Icon.tag size={15} className="flex-none text-slate-faint" />
					<span className="sr-only">Department</span>
					<select
						value={department}
						onChange={(event) => setDepartment(event.target.value)}
						disabled={departments.length === 0}
						className={cx(field, "cursor-pointer disabled:cursor-not-allowed")}
					>
						<option value="">All departments</option>
						{departments.map((row) => (
							<option key={row.department} value={row.department}>
								{row.label}
							</option>
						))}
					</select>
				</label>

				<button
					type="submit"
					aria-label="Search"
					className="grid h-[42px] w-[42px] flex-none place-items-center justify-self-end rounded-full bg-blue text-white transition hover:bg-blue-press"
				>
					<Icon.search size={16} />
				</button>
			</form>

			{filtered && (
				<div className="mt-2 flex justify-end px-1">
					<button
						type="button"
						onClick={onClear}
						className="text-[11.5px] font-bold text-blue hover:underline"
					>
						Clear all filters
					</button>
				</div>
			)}
		</div>
	);
}

/* -------------------------------------------------------------------- card */

/**
 * One vacancy, as much of it as a card can hold.
 *
 * `summary` and not `description_html`: the server flattens the description to
 * one paragraph of plain text for exactly this, because a card wants two lines
 * and a job description is a page. Rendering the markup here and clamping it
 * would put a heading and half a bullet list in a 60-pixel box.
 */
function OpportunityCard({ row }: { row: Opportunity }) {
	return (
		<article className="flex flex-col overflow-hidden rounded-xl bg-white border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)] transition duration-200 hover:shadow-[0_2px_10px_rgba(30,50,73,0.07)]">
			<div className="flex-1 p-5 sm:p-6">
				<div className="flex items-start justify-between gap-3">
					<h3 className="text-[15.5px] font-semibold leading-snug tracking-tight text-ink">
						<Link to={`/opportunities/${encodeURIComponent(row.name)}`} className="hover:text-ink">
							{row.title}
						</Link>
					</h3>
					{/* Urgency, and only when there is some. A closing date is a fact
					    in the list below; "closes this week" is the one case where it
					    changes what somebody should do about it today. */}
					{row.closing_soon && (
						<span className="flex-none rounded-full bg-blue/10 px-2.5 py-1 text-[10.5px] font-bold text-blue-press">
							Closing soon
						</span>
					)}
				</div>

				<Tags row={row} />

				{row.summary && (
					<p className="mt-3 line-clamp-3 text-[12.5px] leading-relaxed text-muted [overflow-wrap:anywhere]">
						{row.summary}
					</p>
				)}

				<dl className="mt-4 space-y-1.5 text-[12px] text-muted">
					{row.location && (
						<div className="flex items-center gap-1.5">
							<Icon.pin size={13} className="flex-none text-slate-faint" />
							<dd className="truncate">{row.location}</dd>
						</div>
					)}
					<div className="flex items-center gap-1.5">
						<Icon.calendar size={13} className="flex-none text-slate-faint" />
						<dd>{closingLine(row)}</dd>
					</div>
					{row.places > 0 && (
						<div className="flex items-center gap-1.5">
							<Icon.people size={13} className="flex-none text-slate-faint" />
							<dd>
								{row.places} {row.places === 1 ? "vacancy" : "vacancies"}
							</dd>
						</div>
					)}
				</dl>
			</div>

			<div className="flex flex-wrap items-center justify-between gap-3 border-t border-card-line bg-surface/60 px-5 py-3.5 sm:px-6">
				<Link
					to={`/opportunities/${encodeURIComponent(row.name)}`}
					className="inline-flex flex-none items-center gap-1.5 text-[12.5px] font-bold text-ink hover:underline"
				>
					Full details
					<Icon.chevron size={13} className="-rotate-90" />
				</Link>

				<ApplyLink row={row} compact />
			</div>
		</article>
	);
}

/** Department, designation and employment type, as chips, skipping the empties. */
function Tags({ row }: { row: Opportunity }) {
	const tags = [row.department, row.designation, row.employment_type].filter(Boolean);

	if (!tags.length) return null;

	return (
		<div className="mt-2.5 flex flex-wrap gap-1.5">
			{tags.map((tag) => (
				<span
					key={tag}
					className="rounded-full border border-card-line bg-white px-2.5 py-1 text-[11px] font-semibold text-muted"
				>
					{tag}
				</span>
			))}
		</div>
	);
}

/**
 * The button, and the honest version of it.
 *
 * **A full navigation out of the SPA**, because HRMS's application form is
 * HRMS's page. `target="_blank"` with `rel="noopener"` so somebody who opens it,
 * reads the form and changes their mind still has the board behind them.
 *
 * **There is always somewhere to go.** The button used to point at the opening's
 * own page and only fall back to the application form, which meant an opening
 * whose page link was wrong had no working way to answer it — and the page link
 * *was* wrong: the seam built it out of the doctype's name. It now points at
 * HRMS's form for this opening, which exists wherever HRMS does.
 */
function ApplyLink({ row, compact = false }: { row: Opportunity; compact?: boolean }) {
	return (
		<a
			href={row.apply_href}
			target="_blank"
			rel="noopener noreferrer"
			className={cx(
				"inline-flex flex-none items-center gap-1.5 rounded-xl bg-blue font-bold text-white transition hover:bg-blue-press",
				compact ? "px-4 py-2 text-[12.5px]" : "px-5 py-2.5 text-[13px]",
			)}
		>
			Apply
			<Icon.external size={compact ? 13 : 14} />
		</a>
	);
}

/** "Closes 30 Sept 2026", or the posting date when the society set no closing date. */
function closingLine(row: Opportunity): string {
	if (row.closes_on) return `Closes ${formatDate(row.closes_on)}`;
	if (row.posted_on) return `Posted ${formatDate(row.posted_on)} · open until filled`;

	return "Open until filled";
}

/* --------------------------------------------------------- my deployments */

/**
 * What this volunteer has actually been deployed on.
 *
 * No longer part of the opportunities board — a jobs board and a personal roster
 * are two subjects — but still exported and self-contained, because the
 * sidebar's Deployments page and `Discover` both render exactly this and one
 * implementation is better than two that drift. Both mounts share the SWR key,
 * so the second one costs no round trip.
 */
export function MyDeployments() {
	const volunteer = useFrappeGetCall<{ message: VolunteerProfile | null }>(
		API.myVolunteer,
		undefined,
		"portal:my_volunteer",
	);

	const profile = volunteer.data?.message ?? null;
	const loading = volunteer.isLoading;

	// Takes no argument: the server resolves the volunteer from the session, so
	// this cannot be pointed at anybody and there is no name to pass.
	const deployments = useFrappeGetCall<{ message: { deployments?: unknown[] } | null }>(
		API.myDeployments,
		undefined,
		"portal:my_deployments",
	);

	// Whether an application of theirs is already with the branch. Without it this
	// screen read "no volunteer record" as "never applied" and invited somebody
	// mid-review to apply a second time — which the server refuses. Same key the
	// dashboard uses, so it is one answer rather than two.
	const open = useFrappeGetCall<{ message: Record<string, unknown | null> }>(
		API.myOpenRegistrations,
		undefined,
		"portal:open_registrations",
	);

	const rows = (deployments.data?.message?.deployments ?? []) as Array<Record<string, string>>;

	if (loading) return <Spinner label="Loading your deployments…" />;

	if (!profile && open.data?.message?.volunteer) {
		return (
			<Empty title="Your application is still with your branch">
				Deployments are offered to volunteers whose record has been accepted. Yours appears here as
				soon as that happens.
			</Empty>
		);
	}

	if (!profile) {
		return (
			<Empty title="Register as a volunteer first">
				Deployments are offered to verified volunteers.
				<div className="mt-4">
					<ButtonLink to="/portal/join?path=volunteer">Become a volunteer</ButtonLink>
				</div>
			</Empty>
		);
	}

	return (
		<>
			{deployments.isLoading && <Spinner label="Loading your deployments…" />}
			{deployments.error && <ErrorNote>{errorMessage(deployments.error)}</ErrorNote>}

			{!deployments.isLoading && rows.length === 0 && (
				<Empty title="You have not been deployed yet">
					When your branch adds you to a deployment, it appears here.
				</Empty>
			)}

			<ul className="space-y-2.5">
				{rows.map((row) => (
					<li
						key={String(row.name ?? row.deployment)}
						className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-card-line bg-white px-4 py-3"
					>
						<div className="min-w-0">
							<div className="text-[13.5px] font-bold text-ink">
								{row.title || row.deployment_name || String(row.name ?? "")}
							</div>
							<div className="mt-0.5 text-[11.5px] text-muted">
								{row.geo_path}
								{row.start_date && ` · from ${formatDate(row.start_date)}`}
							</div>
						</div>
					</li>
				))}
			</ul>
		</>
	);
}

/* ------------------------------------------------------------------ detail */

/**
 * One advertisement in full.
 *
 * **The board's own boundary, re-asked.** `vmmsx.api.opportunities.detail` puts
 * the same two predicates over a single record that `browse` puts over the set
 * — `publish` and `status`, both HRMS's own decisions — so arriving with a
 * guessed docname or following a link to an opening the society has since closed
 * both answer with nothing.
 */
export function OpportunityDetail() {
	const { name = "" } = useParams();

	const { data, error, isLoading } = useFrappeGetCall<{ message: Opportunity | null }>(
		API.opportunityDetail,
		{ name },
		name ? `portal:opportunity:${name}` : null,
	);

	const row = data?.message ?? null;

	return (
		<>
			<Link
				to="/opportunities"
				className="mb-6 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-ink hover:underline"
			>
				<Icon.back size={14} />
				All opportunities
			</Link>

			{isLoading && <Spinner label="Loading…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && !row && (
				<Empty title="That opportunity is not on the board">
					It may have been filled, passed its closing date, or been taken down. Everything
					currently advertised is on the opportunities page.
				</Empty>
			)}

			{row && <OpportunityBody row={row} />}
		</>
	);
}

function OpportunityBody({ row }: { row: Opportunity }) {
	return (
		<article className="mx-auto max-w-3xl">
			<div className="overflow-hidden rounded-2xl bg-gradient-to-br from-rail via-rail to-blue/70 px-7 py-10 text-white shadow-hero sm:px-10 sm:py-12">
				<div className="flex flex-wrap items-center gap-2.5">
					<span className="rounded-full bg-white/15 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-white/80 backdrop-blur">
						Opportunity
					</span>
					{row.employment_type && (
						<span className="rounded-full bg-white/15 px-3 py-1 text-[10px] font-bold text-white/80 backdrop-blur">
							{row.employment_type}
						</span>
					)}
					{row.closing_soon && (
						<span className="rounded-full bg-white px-3 py-1 text-[10px] font-bold text-blue-press">
							Closing soon
						</span>
					)}
				</div>

				<h1 className="mt-4 text-[30px] font-semibold leading-tight tracking-tight sm:text-[36px]">
					{row.title}
				</h1>

				{row.summary && (
					<p className="mt-4 max-w-2xl text-[14.5px] leading-relaxed text-white/75">
						{row.summary}
					</p>
				)}

				<div className="mt-7">
					<ApplyLink row={row} />
				</div>
			</div>

			<div className="mt-6 grid gap-5 sm:grid-cols-2">
				{row.department && (
					<Panel icon={<Icon.people size={16} />} label="Department">
						{row.department}
					</Panel>
				)}

				{row.designation && (
					<Panel icon={<Icon.award size={16} />} label="Designation">
						{row.designation}
					</Panel>
				)}

				{row.location && (
					<Panel icon={<Icon.pin size={16} />} label="Where">
						{row.location}
					</Panel>
				)}

				<Panel icon={<Icon.calendar size={16} />} label="Closing date">
					{row.closes_on ? formatDate(row.closes_on) : "Open until filled"}
				</Panel>

				{row.places > 0 && (
					<Panel icon={<Icon.inbox size={16} />} label="Vacancies">
						{row.places}
					</Panel>
				)}
			</div>

			{row.description_html && (
				<section className="mt-5 rounded-2xl border border-card-line bg-white p-6 border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)] sm:p-7">
					<h2 className="text-[15px] font-bold tracking-tight text-ink">
						About this role
					</h2>
					{/*
					 * The description as its author wrote it — headings, bullets,
					 * emphasis — and the one place in this app that renders markup
					 * from another app's field.
					 *
					 * **Safe because it arrived safe.** `openings._safe_html` puts it
					 * through Frappe's own `sanitize_html` before it is ever served,
					 * so there is no script, handler or iframe left to run by the time
					 * it reaches here. Sanitising in the browser instead would be a
					 * check an attacker can decline to perform.
					 *
					 * `.article-body` is the same class the stories page uses for the
					 * same reason, and its own comment says so: neither body is
					 * authored by this app, so neither can be assumed to fit.
					 */}
					<div
						className="article-body mt-3 text-[13.5px] leading-relaxed text-muted"
						dangerouslySetInnerHTML={{ __html: row.description_html }}
					/>
				</section>
			)}

			<section className="mt-5 rounded-2xl border border-card-line bg-surface/60 p-6 sm:p-7">
				<h2 className="text-[15px] font-bold tracking-tight text-ink">
					How to apply
				</h2>
				<p className="mt-2 text-[13.5px] leading-relaxed text-muted">
					Applying opens the Society's recruitment system, which is where this post is held and
					where your application will be read. Your volunteer record here is separate: keeping
					it and your training current is what puts you in a coordinator's search when a
					deployment needs somebody.
				</p>
				<div className="mt-4 flex flex-wrap items-center gap-2.5">
					<ApplyLink row={row} />
					<ButtonLink to="/portal/profile" variant="quiet">
						Your record
					</ButtonLink>
				</div>
			</section>
		</article>
	);
}

/** One labelled fact panel in the detail layout. */
function Panel({
	icon,
	label,
	children,
}: {
	icon: ReactNode;
	label: string;
	children: ReactNode;
}) {
	return (
		<div className="flex gap-3 rounded-2xl border border-card-line bg-white p-5 border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]">
			<span className="mt-0.5 flex-none text-ink" aria-hidden="true">
				{icon}
			</span>
			<div className="min-w-0">
				<div className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
					{label}
				</div>
				<div className="mt-1 text-[13.5px] leading-relaxed text-slate-strong">{children}</div>
			</div>
		</div>
	);
}
