import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, geoPath } from "../lib/format";
import { GeoSelects, selectedNode } from "../ui/GeoSelects";
import { Icon } from "../ui/icons";
import {
	ButtonLink,
	Empty,
	ErrorNote,
	PageHeading,
	Pager,
	Spinner,
	StateBadge,
	cx,
	usePaged,
} from "../ui/primitives";
import type { GeoNode, Opportunity, VolunteerProfile } from "./types";

/**
 * The society's notice board: work it has advertised, and what this person is
 * already committed to.
 *
 * **Everything on the Open tab was published on purpose.** `is_published` on
 * `VMMS Deployment Request` is the whole of the rule, and it ships off, so a
 * board that is empty is a society that has not advertised anything rather than
 * a screen that is broken. The empty state says which.
 *
 * **There is no Apply button, and its absence is the honest answer.** This app
 * has no record of a volunteer answering an advertisement: a coordinator matches
 * people to a need through `find_candidates` and adds them to a roster. Drawing
 * a button that wrote nowhere would be the thing the walkthrough rule exists to
 * prevent, so each card says how the work is actually staffed and the tab beside
 * it shows what came of it.
 *
 * **A card advertises the work, not how full it is.** `volunteers_requested` and
 * `places_filled` are both served and neither is drawn, which is the shape a job
 * opening has everywhere else: HR advertises the post and the description, never
 * the vacancy count. A progress bar reading "4 of 5 places filled" answers a
 * question the reader did not ask and tells most of them to look elsewhere,
 * when staffing here is a coordinator's match rather than a race to a form.
 *
 * **The location filter is the registration form's control.** One cascading set
 * of selects, from `geo.ladder` and `geo.browse`, filtering by subtree: pick a
 * region and see the region's work, keep going and see one branch's. There is
 * one answer in this app to what a society's hierarchy is.
 */

const TABS = [
	{ key: "open", label: "Open" },
	{ key: "mine", label: "My deployments" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function Opportunities() {
	const [tab, setTab] = useState<TabKey>("open");

	// What has been typed, and what has been asked. Kept apart so the endpoint is
	// called on submit rather than per keystroke: a search that fires per
	// character is a query per character, and the answer to a half-typed word is
	// noise on the screen.
	const [draft, setDraft] = useState("");
	const [search, setSearch] = useState("");
	const [terms, setTerms] = useState("");
	const [placeChain, setPlaceChain] = useState<GeoNode[]>([]);
	const [placeOpen, setPlaceOpen] = useState(false);

	const place = selectedNode(placeChain);

	const facets = useFrappeGetCall<{
		message: { terms: Array<{ key: string; label: string }>; count: number };
	}>(API.opportunityFilters, undefined, "portal:opportunity_filters");

	const board = useFrappeGetCall<{ message: { opportunities: Opportunity[]; count: number } }>(
		API.opportunitiesBrowse,
		{
			search: search || undefined,
			terms_of_reference: terms || undefined,
			geo_node: place?.name || undefined,
		},
		// The key carries the query, so changing a facet refetches rather than
		// showing the previous answer under the new filter.
		`portal:opportunities:${search}:${terms}:${place?.name ?? ""}`,
	);

	const rows = board.data?.message?.opportunities ?? [];
	const filtered = Boolean(search || terms || place);

	// Eight to a page: four full rows of the two-column grid. These cards are
	// tall — purpose, dates and requirements — so a page of them is already a
	// long scroll.
	const paged = usePaged(rows, 8);

	const clear = () => {
		setDraft("");
		setSearch("");
		setTerms("");
		setPlaceChain([]);
		setPlaceOpen(false);
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
					tab === "open" && !facets.isLoading ? (
						<span className="rounded-full bg-signal/10 px-3.5 py-1.5 font-display text-[12.5px] font-bold text-signal-dark">
							{facets.data?.message?.count ?? 0} open
						</span>
					) : undefined
				}
			/>

			<div className="mb-6 inline-flex gap-1 rounded-full border border-hairline bg-white p-1 shadow-card">
				{TABS.map((entry) => (
					<button
						key={entry.key}
						type="button"
						onClick={() => setTab(entry.key)}
						aria-pressed={tab === entry.key}
						className={cx(
							"flex-1 rounded-full px-5 py-2 font-display text-[12.5px] font-bold transition sm:flex-none",
							tab === entry.key
								? "bg-navy text-white shadow-card"
								: "text-slate-body hover:bg-page hover:text-navy",
						)}
					>
						{entry.label}
					</button>
				))}
			</div>

			{tab === "open" && (
				<>
					<FilterBar
						draft={draft}
						setDraft={setDraft}
						onSearch={() => setSearch(draft.trim())}
						terms={terms}
						setTerms={setTerms}
						termsOptions={facets.data?.message?.terms ?? []}
						place={place}
						placeChain={placeChain}
						setPlaceChain={setPlaceChain}
						placeOpen={placeOpen}
						setPlaceOpen={setPlaceOpen}
						filtered={filtered}
						onClear={clear}
					/>

					{board.isLoading && <Spinner label="Finding opportunities…" />}
					{board.error && <ErrorNote>{errorMessage(board.error)}</ErrorNote>}

					{!board.isLoading && !board.error && rows.length === 0 && (
						<Empty
							icon={Icon.compass}
							title={filtered ? "Nothing matches that" : "No opportunities are open"}
						>
							{filtered
								? "Try a wider search, or clear the filters to see everything on the board."
								: "Your society advertises deployments here when it needs volunteers. Nothing is published at the moment."}
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
			)}

			{tab === "mine" && <MyDeployments />}
		</>
	);
}

/* -------------------------------------------------------------- filter bar */

function FilterBar({
	draft,
	setDraft,
	onSearch,
	terms,
	setTerms,
	termsOptions,
	place,
	placeChain,
	setPlaceChain,
	placeOpen,
	setPlaceOpen,
	filtered,
	onClear,
}: {
	draft: string;
	setDraft: (value: string) => void;
	onSearch: () => void;
	terms: string;
	setTerms: (value: string) => void;
	termsOptions: Array<{ key: string; label: string }>;
	place: GeoNode | null;
	placeChain: GeoNode[];
	setPlaceChain: (chain: GeoNode[]) => void;
	placeOpen: boolean;
	setPlaceOpen: (open: boolean) => void;
	filtered: boolean;
	onClear: () => void;
}) {
	const field =
		"w-full bg-transparent text-[13px] text-ink outline-none placeholder:text-slate-faint";

	return (
		<div className="mb-6 rounded-panel bg-white p-2.5 shadow-card">
			<form
				onSubmit={(event) => {
					event.preventDefault();
					onSearch();
				}}
				className="grid gap-2 sm:grid-cols-[1.5fr_1fr_auto]"
			>
				<label className="control sm:border-r sm:border-hairline">
					<Icon.search size={15} className="flex-none text-slate-faint" />
					<span className="sr-only">Search opportunities</span>
					<input
						value={draft}
						onChange={(event) => setDraft(event.target.value)}
						placeholder="Search opportunities"
						className={field}
					/>
				</label>

				<label className="control">
					<Icon.tag size={15} className="flex-none text-slate-faint" />
					<span className="sr-only">Kind of work</span>
					<select
						value={terms}
						onChange={(event) => setTerms(event.target.value)}
						disabled={termsOptions.length === 0}
						className={cx(field, "cursor-pointer disabled:cursor-not-allowed")}
					>
						<option value="">All kinds of work</option>
						{termsOptions.map((row) => (
							<option key={row.key} value={row.key}>
								{row.label}
							</option>
						))}
					</select>
				</label>

				<div className="flex items-center gap-2">
					{/* The location filter opens rather than sitting expanded: it is a
					    stack of selects as deep as the society's hierarchy, and a
					    filter bar is not where that belongs until somebody wants it. */}
					<button
						type="button"
						onClick={() => setPlaceOpen(!placeOpen)}
						aria-expanded={placeOpen}
						className={cx(
							"inline-flex items-center gap-1.5 rounded-full border px-4 py-2.5 font-display text-[12.5px] font-bold transition",
							place
								? "border-navy bg-navy/5 text-navy"
								: "border-hairline-strong bg-white text-slate-strong hover:border-navy hover:text-navy",
						)}
					>
						<Icon.pin size={14} />
						<span className="max-w-[150px] truncate">{place?.label ?? "Anywhere"}</span>
					</button>

					<button
						type="submit"
						aria-label="Search"
						className="grid h-[42px] w-[42px] flex-none place-items-center rounded-full bg-signal text-white transition hover:bg-signal-dark"
					>
						<Icon.search size={16} />
					</button>
				</div>
			</form>

			{placeOpen && (
				<div className="rise-in mt-2 border-t border-hairline-soft px-3 pb-2 pt-4">
					<GeoSelects chain={placeChain} onChain={setPlaceChain} idPrefix="filter" />
				</div>
			)}

			{filtered && (
				<div className="mt-2 flex justify-end px-1">
					<button
						type="button"
						onClick={onClear}
						className="text-[11.5px] font-bold text-signal hover:underline"
					>
						Clear all filters
					</button>
				</div>
			)}
		</div>
	);
}

/* -------------------------------------------------------------------- card */

function OpportunityCard({ row }: { row: Opportunity }) {
	return (
		<article className="flex flex-col overflow-hidden rounded-card bg-white shadow-card transition duration-200 hover:shadow-lift">
			<div className="flex-1 p-5 sm:p-6">
				<div className="flex items-start justify-between gap-3">
					<h3 className="font-display text-[15.5px] font-extrabold leading-snug tracking-tight text-ink">
						<Link
							to={`/opportunities/${encodeURIComponent(row.name)}`}
							className="hover:text-navy"
						>
							{row.title}
						</Link>
					</h3>
					{/* The deployment's own status word, not one this screen invented.
					    A need with no deployment behind it yet is exactly that, and
					    says so rather than borrowing a status it does not have. */}
					<StateBadge state={row.deployment_status ?? "Not scheduled"} />
				</div>

				{row.purpose && (
					<p className="mt-2 line-clamp-3 text-[12.5px] leading-relaxed text-slate-body [overflow-wrap:anywhere]">
						{row.purpose}
					</p>
				)}

				<dl className="mt-4 space-y-1.5 text-[12px] text-slate-body">
					<div className="flex items-center gap-1.5">
						<Icon.pin size={13} className="flex-none text-slate-faint" />
						<dd className="truncate">{geoPath(row.geo_path)}</dd>
					</div>
					<div className="flex items-center gap-1.5">
						<Icon.calendar size={13} className="flex-none text-slate-faint" />
						<dd>
							{formatDate(row.needed_from)}
							{row.needed_until ? ` to ${formatDate(row.needed_until)}` : " onwards"}
						</dd>
					</div>
				</dl>

				{row.requirements.length > 0 && (
					<div className="mt-4">
						<p className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
							Certifications needed
						</p>
						<div className="mt-2 flex flex-wrap gap-1.5">
							{row.requirements.map((requirement) => (
								<span
									key={requirement.certification_type}
									title={requirement.notes ?? undefined}
									className={cx(
										"rounded-full border px-2.5 py-1 text-[11px] font-semibold",
										requirement.is_mandatory
											? "border-signal/30 bg-signal/5 text-signal-dark"
											: "border-hairline-strong bg-white text-slate-body",
									)}
								>
									{requirement.label}
									{!requirement.is_mandatory && " (desirable)"}
								</span>
							))}
						</div>
					</div>
				)}

			</div>

			{/* No button, and the sentence says why rather than leaving a card that
			    looks like it lost one. This app has no record of a volunteer
			    answering an advertisement; a coordinator staffs a deployment from
			    the volunteers who match it. */}
			<div className="flex flex-wrap items-center justify-between gap-3 border-t border-hairline-soft bg-page/60 px-5 py-3.5 sm:px-6">
				<p className="max-w-sm text-[11.5px] leading-relaxed text-slate-body">
					Your branch staffs this from volunteers whose record and certifications match it. Keep
					your training current and you are in the pool.
				</p>
				<Link
					to={`/opportunities/${encodeURIComponent(row.name)}`}
					className="inline-flex flex-none items-center gap-1.5 font-display text-[12.5px] font-bold text-navy hover:underline"
				>
					Full details
					<Icon.chevron size={13} className="-rotate-90" />
				</Link>
			</div>
		</article>
	);
}

/* --------------------------------------------------------- my deployments */

/**
 * What this volunteer has actually been deployed on.
 *
 * The other half of the board, and the honest counterpart of a jobs site's "my
 * applications": there are no applications, but there is a real answer to what
 * came of the society's needs for this person.
 *
 * Exported and self-contained, because the sidebar's own Deployments tab shows
 * exactly this and one implementation is better than two that drift. Both mounts
 * share the SWR key, so the second one costs no round trip.
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

	const rows = (deployments.data?.message?.deployments ?? []) as Array<Record<string, string>>;

	if (loading) return <Spinner label="Loading your deployments…" />;

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
						className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-hairline bg-white px-4 py-3"
					>
						<div className="min-w-0">
							<div className="font-display text-[13.5px] font-bold text-ink">
								{row.title || row.deployment_name || String(row.name ?? "")}
							</div>
							<div className="mt-0.5 text-[11.5px] text-slate-body">
								{geoPath(row.geo_path)}
								{row.start_date && ` · from ${formatDate(row.start_date)}`}
							</div>
						</div>
						<StateBadge state={row.status} />
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
 * the same three predicates over a single record that `browse` puts over the
 * set, so arriving with a guessed docname or following a link to a need a
 * society has since unpublished both answer with nothing.
 *
 * **Still no button, and this screen is where that is worth explaining
 * properly.** A card has room for one sentence about it; this has room for the
 * actual mechanism — a coordinator matches people to a need from the volunteers
 * whose record fits it, so the useful thing a reader can do is keep their
 * training current. `justification` is deliberately not here: it is written for
 * an approver, and advertising a need is not publishing the internal case
 * for it.
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
				className="mb-6 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-navy hover:underline"
			>
				<Icon.back size={14} />
				All opportunities
			</Link>

			{isLoading && <Spinner label="Loading…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && !row && (
				<Empty title="That opportunity is not on the board">
					It may have been filled, passed its dates, or been taken down. Everything currently
					advertised is on the opportunities page.
				</Empty>
			)}

			{row && <OpportunityBody row={row} />}
		</>
	);
}

function OpportunityBody({ row }: { row: Opportunity }) {
	return (
		<article className="mx-auto max-w-3xl">
			<div className="overflow-hidden rounded-feature bg-gradient-to-br from-navy via-navy to-signal/70 px-7 py-10 text-white shadow-hero sm:px-10 sm:py-12">
				<div className="flex flex-wrap items-center gap-2.5">
					<span className="rounded-full bg-white/15 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-white/80 backdrop-blur">
						Opportunity
					</span>
					<span className="rounded-full bg-white/15 px-3 py-1 text-[10px] font-bold text-white/80 backdrop-blur">
						{row.deployment_status ?? "Not scheduled"}
					</span>
				</div>

				<h1 className="mt-4 font-display text-[30px] font-extrabold leading-tight tracking-tight sm:text-[36px]">
					{row.title}
				</h1>

				{row.purpose && (
					<p className="mt-4 max-w-2xl text-[14.5px] leading-relaxed text-white/75">
						{row.purpose}
					</p>
				)}
			</div>

			<div className="mt-6 grid gap-5 sm:grid-cols-2">
				<Panel icon={<Icon.pin size={16} />} label="Where">
					{geoPath(row.geo_path)}
				</Panel>

				<Panel icon={<Icon.calendar size={16} />} label="When">
					{formatDate(row.needed_from)}
					{row.needed_until ? ` to ${formatDate(row.needed_until)}` : " onwards"}
				</Panel>
			</div>

			{row.responsibilities && (
				<section className="mt-5 rounded-panel border border-hairline bg-white p-6 shadow-card sm:p-7">
					<h2 className="font-display text-[15px] font-bold tracking-tight text-ink">
						What you would be doing
					</h2>
					{/* The terms of reference are plain text a society typed, so the
					    line breaks in them are the structure. Rendered as text and
					    split on newlines rather than as markup: nothing a society
					    writes into a form is trusted as HTML anywhere in this app. */}
					<ul className="mt-3 space-y-2">
						{row.responsibilities
							.split("\n")
							.map((line) => line.trim())
							.filter(Boolean)
							.map((line) => (
								<li key={line} className="flex gap-2.5 text-[13.5px] leading-relaxed text-slate-body">
									<span className="mt-[7px] h-1.5 w-1.5 flex-none rounded-full bg-signal" />
									{line}
								</li>
							))}
					</ul>
				</section>
			)}

			{row.requirements.length > 0 && (
				<section className="mt-5 rounded-panel border border-hairline bg-white p-6 shadow-card sm:p-7">
					<h2 className="font-display text-[15px] font-bold tracking-tight text-ink">
						Certifications
					</h2>
					<p className="mt-1.5 text-[12.5px] text-slate-body">
						Required ones are what a coordinator filters on. Desirable ones help.
					</p>

					<ul className="mt-4 space-y-2.5">
						{row.requirements.map((requirement) => (
							<li
								key={requirement.certification_type}
								className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-hairline px-4 py-3"
							>
								<div className="min-w-0">
									<div className="font-display text-[13.5px] font-bold text-ink">
										{requirement.label}
									</div>
									{requirement.notes && (
										<div className="mt-0.5 text-[11.5px] text-slate-body">{requirement.notes}</div>
									)}
								</div>
								<span
									className={cx(
										"flex-none rounded-full border px-2.5 py-1 text-[11px] font-bold",
										requirement.is_mandatory
											? "border-signal/30 bg-signal/5 text-signal-dark"
											: "border-hairline-strong bg-white text-slate-body",
									)}
								>
									{requirement.is_mandatory ? "Required" : "Desirable"}
								</span>
							</li>
						))}
					</ul>
				</section>
			)}

			<section className="mt-5 rounded-panel border border-hairline bg-page/60 p-6 sm:p-7">
				<h2 className="font-display text-[15px] font-bold tracking-tight text-ink">
					How you get on this
				</h2>
				<p className="mt-2 text-[13.5px] leading-relaxed text-slate-body">
					There is no button here, and that is deliberate: this society staffs a deployment by
					matching people to it, not by taking applications. A coordinator searches the
					volunteers placed in this area whose certifications are current, and adds them to the
					roster. Keeping your training in date and your record correct is what puts you in that
					search.
				</p>
				<div className="mt-4 flex flex-wrap gap-2.5">
					<ButtonLink to="/portal/training" variant="quiet">
						Check your training
					</ButtonLink>
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
		<div className="flex gap-3 rounded-panel border border-hairline bg-white p-5 shadow-card">
			<span className="mt-0.5 flex-none text-navy" aria-hidden="true">
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
