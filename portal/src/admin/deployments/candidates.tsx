import { useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../../lib/api";
import { formatDate, geoPath } from "../../lib/format";
import type {
	ApplicationOptions,
	AssignmentOutcome,
	Candidate,
	CandidateSearch,
	DeploymentDetail as DeploymentDetailDto,
	DeploymentSummary,
	SendingResult,
} from "../../portal/types";
import { INPUT, Labelled } from "../Projects";
import { MultiCombo } from "../../ui/form";
import { HoverCard } from "../../ui/HoverCard";
import { Avatar, Button, Card, ConfirmDialog, Empty, ErrorNote, Pill, SectionTitle, cx } from "../../ui/primitives";

/* -------------------------------------------------------------- candidates */

/**
 * Selecting volunteers, laid out like the old Deployment Request Tool's
 * "Quick Filters" so a coordinator who used it finds the same filters in the
 * same places: qualifications, where people live, and availability.
 *
 * **Nothing is fetched until "Find volunteers" is pressed.** Every filter runs
 * on the server over the whole county in one query (`matching.matching_names`),
 * so the count is the true number of people who fit, not the size of a page.
 * The list comes back fifty at a time, best first.
 *
 * **Ticks stay across pages and across searches.** Somebody picked from one
 * search stays picked when the filters change, because choosing a team is
 * often three searches long. "Select all" is different: it means everybody the
 * last search matched, and the server asks the same question again when the
 * people are sent, so the number on the button is the number asked.
 *
 * **Skills, professions and languages are also what the deployment needs**:
 * the new-deployment page saves them on the record (`onNeeds`), and the
 * deployment's own page starts its search from them.
 */

export interface Needs {
	skills: string[];
	professions: string[];
	languages: string[];
}

export const NO_NEEDS: Needs = { skills: [], professions: [], languages: [] };

/** Every quick filter. The lists match "any of these"; the lists together, all of them. */
export interface Filters extends Needs {
	certification_types: string[];
	availability_slots: string[];
	residence_counties: string[];
	residence_sub_counties: string[];
	residence_wards: string[];
	search: string;
	only_available: boolean;
	exclude_conflicts: boolean;
	surge_only: boolean;
}

function filtersFrom(needs: Needs = NO_NEEDS): Filters {
	return {
		...NO_NEEDS,
		...needs,
		certification_types: [],
		availability_slots: [],
		residence_counties: [],
		residence_sub_counties: [],
		residence_wards: [],
		search: "",
		only_available: false,
		exclude_conflicts: false,
		surge_only: false,
	};
}

/** The filters a search ran with, as the server takes them — sent again with "select all". */
export type Criteria = Omit<Filters, "search" | "only_available" | "exclude_conflicts" | "surge_only"> & {
	search?: string;
	only_available: 0 | 1;
	exclude_conflicts: 0 | 1;
	surge_only: 0 | 1;
};

function criteriaOf(filters: Filters): Criteria {
	return {
		...filters,
		search: filters.search.trim() || undefined,
		only_available: filters.only_available ? 1 : 0,
		exclude_conflicts: filters.exclude_conflicts ? 1 : 0,
		surge_only: filters.surge_only ? 1 : 0,
	};
}

/** One person picked, as the selected list and the send popup show them. */
export interface Picked {
	volunteer: string;
	full_name: string | null;
	/** Where they belong, as a place name: "Nairobi". */
	place: string | null;
}

export interface Selection {
	/** Ticked one by one. Empty while `everyone` is on. */
	volunteers: string[];
	/** Everybody the last search matched. */
	everyone: boolean;
	criteria: Criteria | null;
	count: number;
	/** Those picked one by one, in the order they were ticked. Empty while `everyone` is on. */
	people: Picked[];
}

export const NOTHING_SELECTED: Selection = { volunteers: [], everyone: false, criteria: null, count: 0, people: [] };

/** What to send for a selection: the names, or "everyone matching" and the filters. */
export function selectionParams(selection: Selection) {
	return selection.everyone
		? { select_all: 1, criteria: selection.criteria }
		: { volunteers: selection.volunteers };
}

const PAGE = 50;

type ListFilter = Exclude<keyof Filters, "search" | "only_available" | "exclude_conflicts" | "surge_only">;
type Option = { key: string; label: string };

interface PlaceRow {
	county: string | null;
	sub_county: string | null;
	ward: string | null;
}

/** Distinct, sorted options from one column of the residence rows. */
function placeOptions(rows: PlaceRow[], column: keyof PlaceRow): Option[] {
	return [...new Set(rows.map((row) => row[column]).filter((value): value is string => Boolean(value)))]
		.sort((a, b) => a.localeCompare(b))
		.map((value) => ({ key: value, label: value }));
}

/**
 * The quick filters, in the old tool's three columns.
 *
 * Sub-county narrows to the counties of residence chosen, and ward to the
 * sub-counties chosen, as the old tool's did. Where-they-live choices are only
 * places the county's own volunteers wrote down, so nothing offered is empty.
 */
function QuickFilters({
	filters,
	onFilters,
	geoNode,
	professions,
}: {
	filters: Filters;
	onFilters: (next: Filters) => void;
	geoNode: string | null;
	professions: string[];
}) {
	const vocabulary = useFrappeGetCall<{ message: ApplicationOptions }>(
		API.applicationOptions,
		undefined,
		"admin:application_options",
	);
	const choices = useFrappeGetCall<{
		message: { places: PlaceRow[]; certification_types: Option[] };
	}>(API.volunteerFilters, { geo_node: geoNode ?? undefined }, geoNode ? `admin:volunteer-filters:${geoNode}` : null);

	const places = choices.data?.message?.places ?? [];
	const inCounties = filters.residence_counties.length
		? places.filter((row) => row.county && filters.residence_counties.includes(row.county))
		: places;
	const inSubCounties = filters.residence_sub_counties.length
		? inCounties.filter((row) => row.sub_county && filters.residence_sub_counties.includes(row.sub_county))
		: inCounties;

	const pick = (field: ListFilter) => (key: string) => {
		const list = filters[field];
		onFilters({ ...filters, [field]: list.includes(key) ? list.filter((value) => value !== key) : [...list, key] });
	};
	const check = (field: "only_available" | "exclude_conflicts" | "surge_only") => (on: boolean) =>
		onFilters({ ...filters, [field]: on });

	const combo = (field: ListFilter, label: string, options: Option[], empty?: string) => (
		<MultiCombo
			id={`filter-${field}`}
			label={label}
			options={options}
			selected={filters[field]}
			onToggle={pick(field)}
			empty={empty}
		/>
	);

	const nothingRecorded = geoNode ? "None recorded for this county." : "Choose the county first.";

	return (
		<div className="grid gap-6 lg:grid-cols-3">
			<FilterColumn title="Qualifications">
				{combo("skills", "Skills", vocabulary.data?.message?.skills ?? [])}
				{combo(
					"professions",
					"Professions",
					professions.map((name) => ({ key: name, label: name })),
				)}
				{combo(
					"certification_types",
					"Certifications",
					choices.data?.message?.certification_types ?? [],
					"No certifications are set up yet.",
				)}
				{combo("languages", "Languages", vocabulary.data?.message?.languages ?? [])}
			</FilterColumn>

			<FilterColumn title="Residence">
				{combo("residence_counties", "County of residence", placeOptions(places, "county"), nothingRecorded)}
				{combo("residence_sub_counties", "Sub-county", placeOptions(inCounties, "sub_county"), nothingRecorded)}
				{combo("residence_wards", "Ward", placeOptions(inSubCounties, "ward"), nothingRecorded)}
			</FilterColumn>

			<FilterColumn title="Availability">
				{combo("availability_slots", "Availability", vocabulary.data?.message?.availability ?? [])}
				<div className="space-y-2.5 pt-1">
					<Check
						checked={filters.only_available}
						onChange={check("only_available")}
						label="Only those free on the deployment dates"
					/>
					<Check
						checked={filters.exclude_conflicts}
						onChange={check("exclude_conflicts")}
						label="Leave out those already deployed on these dates"
					/>
					<Check checked={filters.surge_only} onChange={check("surge_only")} label="Surge roster only" />
				</div>
			</FilterColumn>
		</div>
	);
}

function FilterColumn({ title, children }: { title: string; children: ReactNode }) {
	return (
		<div className="space-y-3">
			<p className="text-[11px] font-bold uppercase tracking-wider text-slate-faint">{title}</p>
			{children}
		</div>
	);
}

function Check({ checked, onChange, label }: { checked: boolean; onChange: (on: boolean) => void; label: string }) {
	return (
		<label className="flex cursor-pointer items-start gap-2.5 text-[13px] text-ink">
			<input
				type="checkbox"
				className="mt-0.5 h-4 w-4 flex-none accent-navy"
				checked={checked}
				onChange={(event) => onChange(event.target.checked)}
			/>
			{label}
		</label>
	);
}

/**
 * The filters, the search and the list. The buttons that act on the selection
 * belong to whoever draws this, through `footer`, because the new-deployment
 * page and a running deployment's page send people in different ways.
 */
export function VolunteerFinder({
	terms,
	geoNode,
	startDate,
	endDate,
	deployment,
	initialNeeds,
	onNeeds,
	professions,
	held,
	onSelection,
	clearKey = 0,
	footer,
}: {
	terms: string | null;
	geoNode: string | null;
	startDate: string | null;
	endDate: string | null;
	/** A deployment that already exists: its own open people are left out. */
	deployment?: string;
	/** Where the filters start — a running deployment's saved needs. */
	initialNeeds?: Needs;
	/** Told whenever skills, professions or languages change. */
	onNeeds?: (needs: Needs) => void;
	professions: string[];
	/** Why the search cannot run yet, and how to show the person where. */
	held?: { note: string; point: () => void } | null;
	onSelection: (selection: Selection) => void;
	/** Changing this clears the ticks — after the people have been sent. */
	clearKey?: number;
	footer?: (selection: Selection) => ReactNode;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [filters, setFilters] = useState<Filters>(() => filtersFrom(initialNeeds));

	const [answer, setAnswer] = useState<CandidateSearch | null>(null);
	const [ran, setRan] = useState<{ key: string; criteria: Criteria } | null>(null);
	const [offset, setOffset] = useState(0);
	const [looking, setLooking] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const [heldNote, setHeldNote] = useState<string | null>(null);

	const [picked, setPicked] = useState<Map<string, Picked>>(new Map());
	const [everyone, setEveryone] = useState(false);

	const criteria = useMemo(() => criteriaOf(filters), [filters]);
	const context = { terms, geoNode, startDate, endDate };
	const key = JSON.stringify([context, criteria]);
	const stale = ran !== null && ran.key !== key;

	const tellNeeds = useRef(onNeeds);
	tellNeeds.current = onNeeds;
	const needsKey = JSON.stringify([filters.skills, filters.professions, filters.languages]);
	useEffect(() => {
		tellNeeds.current?.({ skills: filters.skills, professions: filters.professions, languages: filters.languages });
		// The key is the needs' identity; the arrays are rebuilt on every change.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [needsKey]);

	// Another county, other terms or other dates is another list of people:
	// what was ticked for the old one may not be sent to the new one.
	const place = JSON.stringify(context);
	const lastPlace = useRef(place);
	useEffect(() => {
		if (lastPlace.current === place) return;
		lastPlace.current = place;
		setPicked(new Map());
		setEveryone(false);
		setAnswer(null);
		setRan(null);
	}, [place]);

	useEffect(() => {
		if (clearKey === 0) return;
		setPicked(new Map());
		setEveryone(false);
		setAnswer(null);
		setRan(null);
	}, [clearKey]);

	const total = answer?.candidate_count ?? 0;
	const selection: Selection = everyone
		? { volunteers: [], everyone: true, criteria: ran?.criteria ?? null, count: total, people: [] }
		: {
				volunteers: [...picked.keys()],
				everyone: false,
				criteria: null,
				count: picked.size,
				people: [...picked.values()],
			};

	const report = useRef(onSelection);
	report.current = onSelection;
	const selectionKey = `${everyone}:${total}:${[...picked.keys()].join()}`;
	useEffect(() => {
		report.current(selection);
		// The key is the selection's identity; the object is rebuilt every render.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [selectionKey]);

	const run = async (from: number, using: Criteria, runKey: string) => {
		// No terms (a TOR still to be attached) is no certificate question.
		if (!geoNode) return;

		setLooking(true);
		setFailure(null);

		try {
			const reply = await call.get<{ message: CandidateSearch }>(API.findCandidates, {
				// Sent empty rather than left out: the endpoint takes it by position.
				terms_of_reference: terms ?? "",
				geo_node: geoNode,
				as_of: startDate || undefined,
				start_date: startDate || undefined,
				end_date: endDate || undefined,
				deployment,
				limit: PAGE,
				offset: from,
				...using,
			});

			setAnswer(reply.message);
			setRan({ key: runKey, criteria: using });
			setOffset(from);
		} catch (problem) {
			setFailure(errorMessage(problem, "The list could not be loaded. Try again."));
		} finally {
			setLooking(false);
		}
	};

	const find = () => {
		if (held) {
			setHeldNote(held.note);
			held.point();
			return;
		}

		setHeldNote(null);
		setEveryone(false);
		void run(0, criteria, key);
	};

	const rows = answer?.candidates ?? [];
	const pageAllPicked = rows.length > 0 && rows.every((row) => picked.has(row.volunteer));

	const pickedOf = (person: Candidate): Picked => ({
		volunteer: person.volunteer,
		full_name: person.full_name,
		place: geoPath(person.geo_path) || null,
	});

	const toggle = (person: Candidate) =>
		setPicked((current) => {
			const next = new Map(current);
			next.has(person.volunteer) ? next.delete(person.volunteer) : next.set(person.volunteer, pickedOf(person));
			return next;
		});

	const unpick = (volunteer: string) =>
		setPicked((current) => {
			const next = new Map(current);
			next.delete(volunteer);
			return next;
		});

	return (
		<div>
			<QuickFilters filters={filters} onFilters={setFilters} geoNode={geoNode} professions={professions} />

			<div className="mt-5 flex flex-wrap items-end gap-3 border-t border-card-line pt-4">
				<div className="w-full sm:w-[320px]">
					<Labelled label="Name" hint="A name, email or volunteer number.">
						<input
							type="search"
							className={INPUT}
							value={filters.search}
							onChange={(event) => setFilters({ ...filters, search: event.target.value })}
							onKeyDown={(event) => {
								if (event.key === "Enter") {
									event.preventDefault();
									find();
								}
							}}
						/>
					</Labelled>
				</div>
				<div className="flex flex-wrap items-center gap-2 pb-[22px]">
					<Button held={Boolean(held)} busy={looking} onClick={find}>
						{answer && !stale ? "Find again" : "Find volunteers"}
					</Button>
					<Button variant="quiet" onClick={() => setFilters(filtersFrom())}>
						Clear filters
					</Button>
				</div>
			</div>

			{heldNote && held && <p className="mt-2 text-[12px] font-semibold text-signal">{heldNote}</p>}

			<SelectedList
				people={[...picked.values()]}
				everyone={everyone}
				total={total}
				onRemove={unpick}
				onClear={() => {
					setEveryone(false);
					setPicked(new Map());
				}}
			/>

			{stale && !looking && (
				<p className="mt-2 text-[12px] text-muted">The filters have changed. Find volunteers again to update the list.</p>
			)}

			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			{answer?.register_readable === false && (
				<div className="mt-4">
					<Empty title="You cannot see the volunteer register">
						Ask an administrator for access to volunteers in this county.
					</Empty>
				</div>
			)}

			{answer && answer.register_readable !== false && (
				<>
					<p className="mt-4 text-[13px] font-semibold text-ink">
						{total === 1 ? "1 volunteer matches" : `${total.toLocaleString()} volunteers match`}
						<span className="font-normal text-slate-faint">
							{answer.as_of ? ` · certificates checked for ${formatDate(answer.as_of)}` : ""}
						</span>
					</p>

					{total === 0 ? (
						<div className="mt-3">
							<Empty title="No one matches">Remove a filter, or choose fewer options in one.</Empty>
						</div>
					) : (
						<>
							<div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-y border-card-line py-2.5">
								<label className="flex cursor-pointer items-center gap-2 text-[12px] font-semibold text-muted">
									<input
										type="checkbox"
										className="h-4 w-4 accent-navy"
										checked={everyone || pageAllPicked}
										disabled={everyone}
										onChange={() =>
											setPicked((current) => {
												const next = new Map(current);
												for (const row of rows) {
													pageAllPicked ? next.delete(row.volunteer) : next.set(row.volunteer, pickedOf(row));
												}
												return next;
											})
										}
									/>
									Select this page
								</label>

								<div className="flex flex-wrap items-center gap-3 text-[12px]">
									{everyone ? (
										<span className="font-semibold text-ink">All {total.toLocaleString()} selected</span>
									) : (
										<span className="text-slate-faint">{picked.size} selected</span>
									)}
									{!everyone && total > rows.length && !stale && (
										<button
											type="button"
											className="font-semibold text-blue hover:text-blue-hover"
											onClick={() => setEveryone(true)}
										>
											Select all {total.toLocaleString()}
										</button>
									)}
									{(everyone || picked.size > 0) && (
										<button
											type="button"
											className="font-semibold text-slate-faint hover:text-ink"
											onClick={() => {
												setEveryone(false);
												setPicked(new Map());
											}}
										>
											Clear
										</button>
									)}
								</div>
							</div>

							<ul className="divide-y divide-card-line">
								{rows.map((person) => (
									<CandidateRow
										key={person.volunteer}
										person={person}
										already={false}
										picked={everyone || picked.has(person.volunteer)}
										locked={everyone}
										onToggle={() => toggle(person)}
									/>
								))}
							</ul>

							{total > PAGE && (
								<div className="flex items-center justify-between gap-3 border-t border-card-line pt-3 text-[12px] text-muted">
									<span>
										{offset + 1}–{offset + rows.length} of {total.toLocaleString()}
									</span>
									<div className="flex gap-2">
										<Button
											variant="quiet"
											disabled={looking || offset === 0 || !ran}
											onClick={() => ran && void run(Math.max(0, offset - PAGE), ran.criteria, ran.key)}
										>
											Previous
										</Button>
										<Button
											variant="quiet"
											disabled={looking || offset + rows.length >= total || !ran}
											onClick={() => ran && void run(offset + PAGE, ran.criteria, ran.key)}
										>
											Next
										</Button>
									</div>
								</div>
							)}
						</>
					)}
				</>
			)}

			{footer?.(selection)}
		</div>
	);
}

/**
 * Who has been selected so far, kept in view while the coordinator searches —
 * across pages and across searches — so the people the request goes to are
 * never only a count.
 */
function SelectedList({
	people,
	everyone,
	total,
	onRemove,
	onClear,
}: {
	people: Picked[];
	everyone: boolean;
	total: number;
	onRemove: (volunteer: string) => void;
	onClear: () => void;
}) {
	if (!everyone && people.length === 0) return null;

	return (
		<section className="mt-4 rounded-xl border border-card-line bg-surface px-4 py-3" aria-label="Selected volunteers">
			<div className="flex flex-wrap items-center justify-between gap-2">
				<p className="text-[12.5px] font-bold text-ink">
					Selected volunteers ({everyone ? total.toLocaleString() : people.length})
				</p>
				<button type="button" className="text-[12px] font-semibold text-slate-faint hover:text-ink" onClick={onClear}>
					Clear
				</button>
			</div>

			{everyone ? (
				<p className="mt-1.5 text-[12.5px] text-muted">All {total.toLocaleString()} volunteers who match the filters.</p>
			) : (
				<ul className="mt-2 flex flex-wrap gap-1.5">
					{people.map((person) => (
						<li
							key={person.volunteer}
							className="inline-flex items-center gap-1.5 rounded-full border border-card-line bg-white py-1 pl-3 pr-1.5 text-[12px] text-ink"
						>
							{person.full_name || person.volunteer}
							<button
								type="button"
								aria-label={`Remove ${person.full_name || person.volunteer}`}
								className="grid h-5 w-5 place-items-center rounded-full text-slate-faint hover:bg-canvas hover:text-ink"
								onClick={() => onRemove(person.volunteer)}
							>
								×
							</button>
						</li>
					))}
				</ul>
			)}
		</section>
	);
}

/**
 * The confirmation before a deployment request goes out, as the old tool's
 * "Send request to N personnel?": the people it goes to, by name, and when.
 */
export function SendRequestDialog({
	open,
	selection,
	sendOn,
	busy,
	onSubmit,
	onCancel,
}: {
	open: boolean;
	selection: Selection;
	/** The deployment's future deployment date, if the request waits for it. */
	sendOn: string | null;
	busy: boolean;
	onSubmit: () => void;
	onCancel: () => void;
}) {
	const count = selection.count;
	const later = Boolean(sendOn && new Date(sendOn.replace(" ", "T")) > new Date());

	return (
		<ConfirmDialog
			open={open}
			title="Send deployment request"
			confirmLabel="Submit"
			tone="primary"
			busy={busy}
			onConfirm={onSubmit}
			onCancel={onCancel}
		>
			<p>
				{selection.everyone
					? `Send the deployment request to all ${count.toLocaleString()} volunteers who match the filters?`
					: count === 1
						? "Send the deployment request to this volunteer?"
						: `Send the deployment request to these ${count} volunteers?`}
			</p>
			{!selection.everyone && (
				<ul className="mt-3 max-h-[240px] divide-y divide-card-line overflow-y-auto rounded-lg border border-card-line">
					{selection.people.map((person) => (
						<li key={person.volunteer} className="flex items-baseline justify-between gap-3 px-3 py-2">
							<span className="font-semibold text-ink">{person.full_name || person.volunteer}</span>
							{person.place && <span className="text-[12px] text-slate-faint">{person.place}</span>}
						</li>
					))}
				</ul>
			)}
			<p className="mt-3 text-[12px] text-muted">
				{later ? `It will be sent on ${formatSendTime(sendOn)}. ` : ""}Each volunteer accepts or declines it.
			</p>
		</ConfirmDialog>
	);
}

/** A send time as a person reads it: "Monday 16 November, 08:00". */
export function formatSendTime(value: string | null | undefined): string {
	if (!value) return "";

	const date = new Date(value.replace(" ", "T"));
	if (Number.isNaN(date.getTime())) return value;

	return date.toLocaleString(undefined, {
		weekday: "long",
		day: "numeric",
		month: "long",
		hour: "2-digit",
		minute: "2-digit",
	});
}

/** What asking or placing did, in a sentence, with anybody it did not take for. */
export function SendingOutcome({ result, onClose }: { result: SendingResult; onClose?: () => void }) {
	let headline: string;
	let failures: AssignmentOutcome["failure"] = [];
	const people = (count: number) => `${count} ${count === 1 ? "volunteer" : "volunteers"}`;

	if (result.state === "scheduled") {
		headline = `The deployment request will be sent to ${people(result.count)} on ${formatSendTime(result.send_on)}.`;
	} else if (result.state === "queued") {
		headline = `Sending the deployment request to ${people(result.count)}. You will get a notification when it is done.`;
	} else {
		const done = result.success?.length ?? 0;
		failures = result.failure ?? [];
		headline = `Deployment request sent to ${people(done)}${failures.length ? `. ${failures.length} could not be sent:` : "."}`;
	}

	return (
		<div className="mt-4 rounded-xl border border-card-line bg-surface px-4 py-3.5" role="status">
			<div className="flex items-start justify-between gap-3">
				<p className="text-[13px] font-bold text-ink">{headline}</p>
				{onClose && (
					<button
						type="button"
						onClick={onClose}
						className="text-[11.5px] font-semibold text-slate-faint hover:text-ink"
					>
						Dismiss
					</button>
				)}
			</div>

			{failures.length > 0 && (
				<ul className="mt-2.5 space-y-1.5">
					{failures.map((row) => (
						<li key={row.volunteer} className="text-[12px] text-muted">
							<span className="font-semibold text-ink">{row.full_name}</span> — {row.reason}
						</li>
					))}
				</ul>
			)}
		</div>
	);
}

/**
 * Selecting more people for a deployment that already exists.
 *
 * Starts from what the deployment says it needs; the coordinator may widen or
 * narrow that for this search without changing the deployment. The request
 * follows the deployment's own sending choices — at its future deployment
 * date, if one is still ahead, and by the channels it ticked.
 *
 * **Only a request, never a placement** (user, Nov 2026): the volunteer must
 * accept, so the coordinator sends a deployment request and confirms who it
 * goes to first.
 */
export function CandidatePane({
	deployment,
	professions,
	onAssigned,
}: {
	deployment: DeploymentDetailDto;
	professions: string[];
	onAssigned: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [selection, setSelection] = useState<Selection>(NOTHING_SELECTED);
	const [clearKey, setClearKey] = useState(0);
	const [confirming, setConfirming] = useState(false);
	const [busy, setBusy] = useState(false);
	const [result, setResult] = useState<SendingResult | null>(null);
	const [failure, setFailure] = useState<string | null>(null);

	const sendOn = deployment.sending?.send_on ?? null;

	const send = async () => {
		setBusy(true);
		setFailure(null);
		setResult(null);

		try {
			const reply = await call.post<{ message: SendingResult }>(API.sendToVolunteers, {
				name: deployment.name,
				mode: "ask",
				...selectionParams(selection),
			});

			setResult(reply.message);
			setClearKey((was) => was + 1);
			onAssigned();
		} catch (problem) {
			setFailure(errorMessage(problem, "The deployment request was not sent. Try again."));
		} finally {
			setBusy(false);
			setConfirming(false);
		}
	};

	const count = selection.count;

	return (
		<Card>
			<SectionTitle>Select volunteers</SectionTitle>
			<p className="mt-1 text-[12px] text-slate-faint">
				Volunteers in {geoPath(deployment.geo_path) || "this county"} who can be deployed and hold the
				certificates these terms require. Choose the filters, then find.
			</p>

			<ScheduledAsks deployment={deployment} onChanged={onAssigned} />

			<VolunteerFinder
				terms={deployment.terms_of_reference}
				geoNode={deployment.geo_node}
				startDate={deployment.start_date}
				endDate={deployment.end_date}
				deployment={deployment.name}
				initialNeeds={deployment.needs ?? NO_NEEDS}
				professions={professions}
				onSelection={setSelection}
				clearKey={clearKey}
				footer={() =>
					count > 0 && (
						<div className="sticky bottom-0 -mx-5 mt-3 flex flex-wrap items-center gap-2 border-t border-card-line bg-white/95 px-5 py-3 backdrop-blur sm:-mx-6 sm:px-6">
							<Button busy={busy} onClick={() => setConfirming(true)}>
								{`Send deployment request to ${count}`}
							</Button>
						</div>
					)
				}
			/>

			<SendRequestDialog
				open={confirming}
				selection={selection}
				sendOn={sendOn}
				busy={busy}
				onSubmit={() => void send()}
				onCancel={() => setConfirming(false)}
			/>

			{result && <SendingOutcome result={result} onClose={() => setResult(null)} />}
			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}
		</Card>
	);
}

/** The people chosen to be asked at the send time, who have not been asked yet. */
function ScheduledAsks({ deployment, onChanged }: { deployment: DeploymentDetailDto; onChanged: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);

	const waiting = deployment.sending?.scheduled ?? [];
	if (waiting.length === 0) return null;

	const remove = async (volunteer: string) => {
		setBusy(volunteer);
		setFailure(null);

		try {
			await call.post(API.unscheduleVolunteer, { name: deployment.name, volunteer });
			onChanged();
		} catch (problem) {
			setFailure(errorMessage(problem, "That volunteer was not removed. Try again."));
		} finally {
			setBusy(null);
		}
	};

	return (
		<div className="mt-4 rounded-xl border border-card-line px-4 py-3.5">
			<p className="text-[12.5px] font-semibold text-ink">
				{waiting.length} {waiting.length === 1 ? "volunteer" : "volunteers"} will be asked on{" "}
				{formatSendTime(deployment.sending?.send_on)}
			</p>
			<ul className="mt-2 divide-y divide-card-line">
				{waiting.map((row) => (
					<li key={row.volunteer} className="flex items-center justify-between gap-3 py-2 text-[12.5px]">
						<span className="text-ink">{row.full_name}</span>
						<button
							type="button"
							disabled={busy !== null}
							onClick={() => void remove(row.volunteer)}
							className="text-[11.5px] font-semibold text-slate-faint hover:text-ink disabled:opacity-50"
						>
							{busy === row.volunteer ? "Removing…" : "Remove"}
						</button>
					</li>
				))}
			</ul>
			{failure && (
				<div className="mt-2">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}
		</div>
	);
}

export function Toggle({
	on,
	onChange,
	label,
}: {
	on: boolean;
	onChange: (value: boolean) => void;
	label: string;
}) {
	return (
		<button
			type="button"
			aria-pressed={on}
			onClick={() => onChange(!on)}
			className={cx(
				"rounded-full border px-3.5 py-1.5 text-[12px] font-semibold transition",
				on
					? "border-blue bg-rail text-white"
					: "border-card-line bg-white text-muted hover:border-blue hover:text-ink",
			)}
		>
			{label}
		</button>
	);
}

/**
 * What the bulk act actually did, per person.
 *
 * **The failures are the point.** Some of them will not take — already
 * assigned, deployment full, terms retired since — and the server wraps each
 * insert in its own savepoint precisely so the rest can succeed. A screen that
 * showed only a count would leave a coordinator to work out which by opening
 * the roster and comparing.
 */
export function Outcome({ outcome, onClose }: { outcome: AssignmentOutcome; onClose: () => void }) {
	return (
		<div className="mb-4 rounded-xl border border-card-line bg-surface px-4 py-3.5">
			<div className="flex items-start justify-between gap-3">
				<p className="text-[13px] font-bold text-ink">
					{outcome.raised} of {outcome.requested} assigned
					{outcome.refused > 0 ? `, ${outcome.refused} not` : ""}
				</p>
				<button
					type="button"
					onClick={onClose}
					className="text-[11.5px] font-semibold text-slate-faint hover:text-ink"
				>
					Dismiss
				</button>
			</div>

			{outcome.failure.length > 0 && (
				<ul className="mt-2.5 space-y-1.5">
					{outcome.failure.map((row) => (
						<li key={row.volunteer} className="text-[12px] text-muted">
							<span className="font-semibold text-ink">{row.full_name}</span> — {row.reason}
						</li>
					))}
				</ul>
			)}
		</div>
	);
}

/**
 * One candidate: enough to decide by, with the rest a hover away.
 *
 * The row carries what the search already fetched — name, place, whether they
 * are free, whether they clash. The card behind the name adds the things worth
 * one lazy call for the person you are actually considering: how many
 * deployments they have been on and which. Fetching that for every row would
 * undo the work that made this search cheap.
 */
export function CandidateRow({
	person,
	already,
	picked,
	locked = false,
	onToggle,
}: {
	person: Candidate;
	already: boolean;
	picked: boolean;
	/** Ticked by "select all", so not ticked or unticked one at a time. */
	locked?: boolean;
	onToggle: () => void;
}) {
	return (
		<li className={cx("flex flex-wrap items-center gap-3 py-3", already && "opacity-60")}>
			<input
				type="checkbox"
				className="h-4 w-4 flex-none accent-navy"
				checked={picked}
				disabled={already || locked}
				onChange={onToggle}
				aria-label={`Select ${person.full_name}`}
			/>

			<Avatar name={person.full_name} photo={person.photo} size={34} />

			<div className="min-w-0 flex-1">
				<HoverCard
					label={<span className="text-[13px] font-semibold text-ink">{person.full_name}</span>}
				>
					{() => <CandidateCard person={person} />}
				</HoverCard>

				<div className="text-[11.5px] text-slate-faint">
					{geoPath(person.geo_path)}
					{person.desirable_certifications_held.length > 0 &&
						` · also holds ${person.desirable_certifications_held.join(", ")}`}
				</div>

				<div className="mt-1 flex flex-wrap gap-1.5">
					<AvailabilityPill person={person} />
					{person.clash.is_clashing && (
						<Pill tone="signal">
							Already on {person.clash.deployments.length}{" "}
							{person.clash.deployments.length === 1 ? "deployment" : "deployments"}
						</Pill>
					)}
				</div>
			</div>

			{already && (
				<span className="text-[11.5px] font-semibold text-slate-faint">Already on it</span>
			)}
		</li>
	);
}

/** The three-way availability answer as one chip, with the reason on hover. */
export function AvailabilityPill({ person }: { person: Candidate }) {
	const free = person.availability;

	if (free.is_available) {
		return <Pill tone="navy">Free these days</Pill>;
	}

	if (free.is_unavailable) {
		return <Pill tone="signal">Not free on {free.missing_days.join(", ")}</Pill>;
	}

	// Unknown is drawn quietly on purpose. Most registers will have almost
	// nobody filled in for a long time after this ships, and a loud warning on
	// every row would train coordinators to ignore the one that matters.
	return <Pill tone="quiet">Availability not set</Pill>;
}

/**
 * The card behind a candidate's name: who they are and where they have been.
 *
 * Fetched on open, one volunteer at a time. `deployments_of_volunteer` is the
 * coordinator's endpoint and geo-scopes what it returns, so a candidate who
 * served somewhere this coordinator cannot see reads as fewer deployments rather
 * than as an error — which is the correct answer, if a slightly modest one.
 */
export function CandidateCard({ person }: { person: Candidate }) {
	const { data, isLoading } = useFrappeGetCall<{
		message: { deployments: DeploymentSummary[] };
	}>(
		API.deploymentsOfVolunteer,
		{ volunteer: person.volunteer },
		`admin:candidate:history:${person.volunteer}`,
	);

	const history = data?.message?.deployments ?? [];

	return (
		<div>
			<div className="flex items-center gap-2.5">
				<Avatar name={person.full_name} photo={person.photo} size={40} />
				<div className="min-w-0">
					<p className="text-[13.5px] font-bold text-ink">{person.full_name}</p>
					<p className="text-[11.5px] text-slate-faint">{geoPath(person.geo_path)}</p>
				</div>
			</div>

			<dl className="mt-3 grid grid-cols-2 gap-2 border-t border-card-line pt-3 text-[11.5px]">
				<div>
					<dt className="text-slate-faint">Deployments</dt>
					<dd className="text-[15px] font-bold text-ink">
						{isLoading ? "…" : history.length}
					</dd>
				</div>
				<div>
					<dt className="text-slate-faint">Status</dt>
					<dd className="font-semibold text-ink">{person.status}</dd>
				</div>
			</dl>

			{person.desirable_certifications_held.length > 0 && (
				<div className="mt-2.5">
					<p className="text-[11px] font-semibold uppercase tracking-wide text-slate-faint">
						Also holds
					</p>
					<div className="mt-1 flex flex-wrap gap-1">
						{person.desirable_certifications_held.map((key) => (
							<Pill key={key} tone="navy">
								{key}
							</Pill>
						))}
					</div>
				</div>
			)}

			{history.length > 0 && (
				<div className="mt-2.5">
					<p className="text-[11px] font-semibold uppercase tracking-wide text-slate-faint">
						Been on
					</p>
					<ul className="mt-1 space-y-0.5">
						{history.slice(0, 4).map((row) => (
							<li key={row.name} className="truncate text-[11.5px] text-muted">
								{row.title || row.terms_of_reference || row.name}
								{row.start_date ? ` · ${formatDate(row.start_date)}` : ""}
							</li>
						))}
					</ul>
				</div>
			)}

			<p className="mt-2.5 border-t border-card-line pt-2 text-[11.5px] text-muted">
				{person.availability.why}
			</p>

			{person.clash.is_clashing && (
				<p className="mt-1.5 text-[11.5px] font-semibold text-blue">
					Already committed to {person.clash.deployments.map((row) => row.deployment).join(", ")}{" "}
					over these dates.
				</p>
			)}
		</div>
	);
}
