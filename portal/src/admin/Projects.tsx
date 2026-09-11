import { type ReactNode, useContext, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage, termsPdfUrl } from "../lib/api";
import { formatDate, geoPath } from "../lib/format";
import type {
	DeploymentSummary,
	GeoNode,
	ProjectDossier,
	ProjectSummary,
	TermsApproach,
	TermsCertificationRequirement,
	TermsDocument,
	TermsItineraryRow,
	TermsVocabularies,
	TermsOfReference,
	TermsObjective,
	TermsOutput,
	TermsResource,
	TermsStakeholder,
} from "../portal/types";
import {
	MissionEditor,
	MissionView,
	RowEditor,
	blankResource,
	resourceColumns,
} from "./Mission";
import { GeoSelects, selectedNode } from "../ui/GeoSelects";
import {
	Button,
	ButtonLink,
	Card,
	Empty,
	ErrorNote,
	FormProgressTabs,
	type Crumb,
	PageHeading,
	Pill,
	SectionTitle,
	Spinner,
	StateBadge,
	cx,
} from "../ui/primitives";
import { FolderCard } from "../ui/patterns";
import { CrossMark, useSocietyBranding, type Branding } from "../ui/brand";

/**
 * The paperwork a deployment stands on: a programme of work, and the terms of
 * reference written under it.
 *
 * **Three registers, one order, four pages — and only the last three share a
 * hub.** A society opens a project, writes one or more terms of reference
 * under it, and deploys people against those. Each register is its own routed
 * page rather than a tab, because a project stands on its own — a society can
 * run one that never spins up a deployment or a terms of reference — and a URL
 * is what lets somebody link, bookmark or come back to one directly. That is
 * also why Projects is its own top-level console section at `/admin/projects`
 * rather than a card on `/admin/deployments`: nesting it there read as though a
 * project needed the other two to exist, which the data model has never
 * required (`VMMS Terms of Reference.project` is optional). The order the
 * records have to exist in still shows up in each form, which only offers what
 * already exists above it: the terms form lists the projects this person
 * opened, the deployment form lists the terms they wrote.
 *
 * **`mine` is on by default on both registers and it can only narrow.** The
 * server applies the owner filter on top of a result core's query condition has
 * already bounded to the caller's geo scope, so untick it and what appears is
 * their branch's, never the site's. `doc.owner` is the right question for these
 * two — it asks who *did the filing*, which is the same distinction
 * `deployment/services/invitation.py` draws when it decides who hears an answer.
 *
 * **Placement is `GeoSelects`, the one placement control in this app.** A
 * project is anchored at creation and not filled in later (ACC-02), so the form
 * cannot be submitted until the chain names a node; a terms of reference's
 * `geo_scope` is a different question — where the terms may be *used* — and is
 * optional, because a society that has not narrowed its terms means anywhere.
 */

/* ---------------------------------------------------------------- projects */

export function ProjectList() {
	const [searchParams] = useSearchParams();
	const [mine, setMine] = useState(true);
	const [creating, setCreating] = useState(() => searchParams.get("new") === "1");

	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: { count: number; projects: ProjectSummary[]; open_count: number };
	}>(API.branchProjects, { mine: mine ? 1 : 0 }, `admin:projects:${mine}`);

	const rows = data?.message?.projects ?? [];

	return (
		<>
			<PageHeading title="Projects" />

			<div className="mb-4 flex flex-wrap items-center gap-2">
				<MineToggle mine={mine} onChange={setMine} label="Only mine" />
				{(data?.message?.open_count ?? 0) > 0 && (
					<Pill tone="signal">{data?.message?.open_count} open</Pill>
				)}
				<div className="ml-auto">
					<Button onClick={() => setCreating((was) => !was)}>
						{creating ? "Close" : "New project"}
					</Button>
				</div>
			</div>

			{creating && (
				<div className="mb-5">
					<ProjectForm
						onCreated={() => {
							setCreating(false);
							void mutate();
						}}
					/>
				</div>
			)}

			{isLoading && <Spinner label="Loading projects…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{data && rows.length === 0 && (
				<Empty title="No projects yet">
					A project is the programme of work a terms of reference is written under. Open one, then
					write the terms people will be deployed against. If you hold no geo assignment this list
					is empty by design rather than by accident.
				</Empty>
			)}

			{rows.length > 0 && (
				<ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
					{rows.map((row) => (
						<li key={row.name}>
							{/* A project is a container — it holds terms of reference, and
							    those hold deployments — and the folder shape says so before
							    a word is read.

							    **The foot carries geography and period, not a TOR and
							    deployment count.** The approved design asks for those two
							    figures and `api/projects.py` does not return them:
							    `ProjectSummary` has no `tor_count` or `deployment_count`.
							    Counting them here would mean a request per folder, and
							    guessing them would be inventing a statistic. So the folder
							    shows what the endpoint actually knows, and the missing
							    counts are recorded as a backend gap rather than filled in
							    with a plausible number. */}
							<FolderCard
								to={`/admin/projects/${encodeURIComponent(row.name)}`}
								name={row.project_name}
								summary={row.summary}
								status={row.status}
								counts={
									<>
										{geoPath(row.geo_path) || "No location set"}
										{row.start_date ? ` · from ${formatDate(row.start_date)}` : ""}
									</>
								}
							/>
						</li>
					))}
				</ul>
			)}
		</>
	);
}

/**
 * One project in full: its own record, the terms of reference written under
 * it, and the deployments run under those.
 *
 * **Composed as one read, `api/deployment.py::get_project`**, for the reason
 * every other detail screen in this app is: a project, its terms and its
 * deployments read at three different instants could disagree with each other
 * in a way that would only show up as confusion later.
 *
 * **A project may have terms with no deployment yet, or none of either.** Both
 * lists say so honestly rather than looking like a screen that failed to load.
 */
export function ProjectDetail() {
	const { name = "" } = useParams<{ name: string }>();

	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: ProjectDossier }>(
		API.getProject,
		{ name },
		`admin:project:${name}`,
	);

	if (isLoading) return <Spinner label="Loading project…" />;
	if (error) return <ErrorNote>{errorMessage(error)}</ErrorNote>;

	const dossier = data?.message;
	if (!dossier) return null;

	const { project, terms, deployments } = dossier;

	const trail: Crumb[] = [
		{ label: "Projects", to: "/admin/projects" },
		{ label: project.project_name },
	];

	return (
		<>
			<PageHeading title={project.project_name} trail={trail} />

			<div className="space-y-4">
					<Card>
						<div className="flex flex-wrap items-start justify-between gap-3">
							<div>
								<p className="text-[11px] font-semibold uppercase tracking-wide text-slate-faint">
									Project number {project.name}
								</p>
								<p className="text-[12px] text-muted">{geoPath(project.geo_path)}</p>
							<p className="mt-0.5 text-[12px] text-slate-faint">
								{project.start_date ? formatDate(project.start_date) : "No start date"}
								{project.end_date ? ` → ${formatDate(project.end_date)}` : ""}
							</p>
						</div>
						<StateBadge state={project.status} />
					</div>

					{project.summary && (
						<p className="mt-3 whitespace-pre-line text-[12.5px] text-muted">
							{project.summary}
						</p>
					)}

					{project.notes && (
						<p className="mt-2 whitespace-pre-line text-[12px] text-slate-faint">{project.notes}</p>
					)}

					<div className="mt-4 border-t border-card-line pt-3">
						<StatusRow project={project} onChanged={() => void mutate()} />
					</div>
				</Card>

				<Card>
					<div className="flex flex-wrap items-center justify-between gap-2">
						<SectionTitle>Terms of reference under this project ({terms.length})</SectionTitle>
						<Link
							to="/admin/deployments/terms?new=1"
							className="text-[12px] font-semibold text-ink hover:underline"
						>
							Write terms of reference
						</Link>
					</div>

					{terms.length === 0 ? (
						<p className="mt-2 text-[12.5px] text-slate-faint">
							No terms of reference written under this project yet.
						</p>
					) : (
						<ul className="mt-3 space-y-2">
							{terms.map((row) => (
								<TermsRow key={row.name} row={row} />
							))}
						</ul>
					)}
				</Card>

				<Card>
					<SectionTitle>Deployments under this project ({deployments.length})</SectionTitle>

					{deployments.length === 0 ? (
						<p className="mt-2 text-[12.5px] text-slate-faint">
							No deployments run under this project yet.
						</p>
					) : (
						<ul className="mt-3 space-y-2">
							{deployments.map((row) => (
								<DeploymentRow key={row.name} row={row} />
							))}
						</ul>
					)}
				</Card>
			</div>
		</>
	);
}

/**
 * A terms of reference as a card, linked from a project's or a deployment's page.
 *
 * **It says how much of the mission has been written.** A terms of reference is
 * a document with six parts now, and one that has a title and nothing else looks
 * identical to a finished one in a list of names. The counts come off
 * `section_counts`, which the server computes while the record is already loaded,
 * so saying so costs nothing.
 */
function TermsRow({ row, showProject }: { row: TermsOfReference; showProject?: boolean }) {
	const parts = [
		[row.section_counts?.objectives ?? 0, "objectives"],
		[row.section_counts?.itinerary ?? 0, "days planned"],
		[row.section_counts?.resources ?? 0, "resources"],
	] as const;

	const written = parts.filter(([count]) => count > 0);

	return (
		<li>
			<Link
				to={`/admin/deployments/terms/${encodeURIComponent(row.name)}`}
				className="block rounded-xl border border-card-line bg-white px-4 py-3 transition hover:border-card-line"
			>
				<div className="flex flex-wrap items-start justify-between gap-2">
					<span className="text-[13.5px] font-bold text-ink">{row.tor_name}</span>
					<div className="flex flex-wrap items-center gap-1.5">
						{row.is_draft && <Pill tone="signal">Draft</Pill>}
						{row.is_submitted && !row.is_active && <Pill tone="quiet">Retired</Pill>}
					</div>
				</div>

				{showProject && row.project_name && (
					<div className="mt-1 text-[11.5px] text-muted">{row.project_name}</div>
				)}

				<div className="mt-0.5 text-[11.5px] text-slate-faint">
					{row.geo_scope_path ? geoPath(row.geo_scope_path) : "Applies anywhere"}
					{row.requires_approver ? " · routed for approval" : ""}
				</div>

				{row.expected_start_date && (
					<div className="mt-0.5 text-[11.5px] text-slate-faint">
						{formatDate(row.expected_start_date)}
						{row.expected_end_date ? ` → ${formatDate(row.expected_end_date)}` : ""}
					</div>
				)}

				<div className="mt-1.5 text-[11.5px] text-muted">
					{written.length > 0
						? written.map(([count, label]) => `${count} ${label}`).join(" · ")
						: "Nothing written into it yet."}
				</div>
			</Link>
		</li>
	);
}

/** A deployment, linked from a project's or a terms of reference's own page. */
function DeploymentRow({ row }: { row: DeploymentSummary }) {
	return (
		<li>
			<Link
				to={`/admin/deployments/${encodeURIComponent(row.name)}`}
				className="block rounded-xl border border-card-line bg-white px-4 py-3 transition hover:border-card-line"
			>
				<div className="flex items-start justify-between gap-2">
					<span className="text-[13.5px] font-bold text-ink">
						{row.terms_of_reference || row.name}
					</span>
					<StateBadge state={row.status} />
				</div>
				<div className="mt-1 text-[11.5px] text-muted">{geoPath(row.geo_path)}</div>
				<div className="mt-0.5 text-[11.5px] text-slate-faint">
					{row.participant_count} on the roster
					{row.start_date ? ` · from ${formatDate(row.start_date)}` : ""}
				</div>
			</Link>
		</li>
	);
}

/**
 * ERPNext's own four, which is what `deployment/services/project.py::STATUSES`
 * holds and what `assert_status` refuses anything outside of. A `Project` is
 * ERPNext's doctype, not ours, so this vocabulary is not ours to invent — the
 * retired `VMMS Project` had its own words for these, and carrying them over is
 * what made every "Open a project" post fail on the server.
 */
const PROJECT_STATUSES = ["Open", "On hold", "Completed", "Cancelled"];

/**
 * Once a project is Completed or Cancelled it has ended, and that is the whole
 * of what stops a move. **Not `is_open`**, which answers a different question —
 * whether new terms of reference may be written under it — and which On hold
 * deliberately answers no to. Gating the buttons on it stranded a paused
 * programme with no way back, when restarting one is a single field.
 */
const TERMINAL_STATUSES = ["Completed", "Cancelled"];

/** The four statuses, minus the one it already has. Terminal ones move nowhere. */
function StatusRow({ project, onChanged }: { project: ProjectSummary; onChanged: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);

	const move = async (status: string) => {
		setBusy(status);
		setFailure(null);

		try {
			await call.post(API.setProjectStatus, { name: project.name, status });
			onChanged();
		} catch (problem) {
			setFailure(errorMessage(problem));
		} finally {
			setBusy(null);
		}
	};

	return (
		<div>
			{!TERMINAL_STATUSES.includes(project.status) ? (
				<div className="flex flex-wrap gap-2">
					{PROJECT_STATUSES.filter((option) => option !== project.status)
						.map((option) => (
							<Button
								key={option}
								variant="quiet"
								disabled={busy !== null}
								onClick={() => void move(option)}
							>
								{busy === option ? "Working…" : `Mark ${option.toLowerCase()}`}
							</Button>
						))}
				</div>
			) : (
				<p className="text-[12px] text-slate-faint">
					This project is {project.status.toLowerCase()} and cannot be moved again. Everything
					already run under it stays exactly as it is; ending a programme does not erase the
					record that it happened.
				</p>
			)}

			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}
		</div>
	);
}

function ProjectForm({ onCreated }: { onCreated: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [name, setName] = useState("");
	const [summary, setSummary] = useState("");
	const [notes, setNotes] = useState("");
	const [status, setStatus] = useState("Open");
	const [startDate, setStartDate] = useState("");
	const [endDate, setEndDate] = useState("");
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const node = selectedNode(chain);
	const ready = name.trim() && node;

	const create = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.createProject, {
				project_name: name.trim(),
				geo_node: node?.name,
				summary: summary.trim() || undefined,
				notes: notes.trim() || undefined,
				status,
				start_date: startDate || undefined,
				end_date: endDate || undefined,
			});
			setName("");
			setSummary("");
			setNotes("");
			setStatus("Open");
			setStartDate("");
			setEndDate("");
			setChain([]);
			onCreated();
		} catch (problem) {
			setFailure(errorMessage(problem, "That project was not created."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card>
			<SectionTitle>Open a project</SectionTitle>
			<p className="mt-1 text-[12.5px] text-muted">
				The programme of work: a flood response, a vaccination campaign, a season of branch duty.
				The terms of reference people are deployed against are written under it.
			</p>

			<div className="mt-4 grid gap-4 sm:grid-cols-2">
				<Labelled label="Project" hint="What your society calls this programme.">
					<input className={INPUT} value={name} onChange={(e) => setName(e.target.value)} />
				</Labelled>

				<Labelled label="Status" hint="Where the project starts in its lifecycle.">
					<select className={INPUT} value={status} onChange={(e) => setStatus(e.target.value)}>
						{PROJECT_STATUSES.map((option) => (
							<option key={option} value={option}>
								{option}
							</option>
						))}
					</select>
				</Labelled>

			</div>

			<div className="mt-4 grid gap-4 sm:grid-cols-2">
				<div className="grid grid-cols-2 gap-3">
					<Labelled label="Starts" hint="Optional.">
						<input
							type="date"
							className={INPUT}
							value={startDate}
							onChange={(e) => setStartDate(e.target.value)}
						/>
					</Labelled>
					<Labelled label="Ends" hint="Optional.">
						<input
							type="date"
							className={INPUT}
							value={endDate}
							onChange={(e) => setEndDate(e.target.value)}
						/>
					</Labelled>
				</div>
			</div>

			<div className="mt-4 grid gap-4 sm:grid-cols-2">
				<Labelled label="Summary" hint="Printed at the head of every terms of reference under it.">
					<textarea
						className={cx(INPUT, "min-h-[84px] resize-y")}
						value={summary}
						onChange={(e) => setSummary(e.target.value)}
					/>
				</Labelled>
				<Labelled label="Notes" hint="Anything about this project that is not covered above.">
					<textarea
						className={cx(INPUT, "min-h-[84px] resize-y")}
						value={notes}
						onChange={(e) => setNotes(e.target.value)}
					/>
				</Labelled>
			</div>

			<div className="mt-4">
				<p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-faint">
					Where this project belongs
				</p>
				<GeoSelects chain={chain} onChain={setChain} idPrefix="project" />
				<p className="mt-2 text-[12px] text-slate-faint">
					Required. A project with no place in the organisation would be visible to nobody and
					reachable by nobody.
				</p>
			</div>

			{failure && (
				<div className="mt-4">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<div className="mt-5">
				<Button disabled={busy || !ready} onClick={() => void create()}>
					{busy ? "Opening…" : "Open project"}
				</Button>
			</div>
		</Card>
	);
}

/* ------------------------------------------------------- terms of reference */

/**
 * The terms of reference register, as a shelf of documents rather than a list
 * of rows.
 *
 * **A terms of reference *is* a document**, and that is why this register looks
 * like one. It is the thing a volunteer accepts when they take an assignment,
 * the thing a PDF is printed from on the society's letterhead, and the thing an
 * approver signs. A table of names and dates made it look like configuration; a
 * shelf of A5 pages, each carrying the society's own lockup, its reference, what
 * the mission is for, where it applies, when it expects to run and the stamp of
 * where its approval stands, makes it look like what it is — and makes the
 * *state* of each one legible from across the room, which was the practical
 * failure of the table.
 *
 * **The stamp is one of the seven exact states**, read off `approval_state`,
 * plus the submit state the doctype carries in `docstatus`. A society's stage
 * names appear nowhere here: a stage is configuration and this app compares none
 * of them.
 *
 * **The card is a summary; the document is the document.** The purpose excerpt
 * on the front is trimmed for the shelf, and opening one renders the markup the
 * server produced from the society's own template — the identical markup the PDF
 * is made from — so what is on the screen and what comes out of the printer
 * cannot drift. See `TermsDetail`.
 */
export function TermsList() {
	const [searchParams] = useSearchParams();
	const [mine, setMine] = useState(true);
	const [state, setState] = useState("");
	const [search, setSearch] = useState("");
	const [creating, setCreating] = useState(() => searchParams.get("new") === "1");

	const branding = useSocietyBranding();

	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: { count: number; terms: TermsOfReference[]; states: string[] };
	}>(
		API.branchTerms,
		{
			mine: mine ? 1 : 0,
			...(state ? { state } : {}),
			...(search.trim() ? { search: search.trim() } : {}),
		},
		`admin:terms:${mine}:${state}:${search.trim()}`,
	);

	const rows = data?.message?.terms ?? [];
	// The closed set comes from the server rather than being retyped here, so a
	// state added to `states.py` reaches this control without a frontend change.
	const states = data?.message?.states ?? [];

	return (
		<>
			<PageHeading
				title="Terms of Reference"
				lead="Approved scope, resources, schedule and accountability, written before a deployment begins."
				trail={[
					{ label: "Operations", to: "/admin/deployments" },
					{ label: "Terms of Reference" },
				]}
				actions={
					<Button onClick={() => setCreating((was) => !was)}>
						{creating ? "Close" : "Write terms"}
					</Button>
				}
			/>

			<Card className="mb-5">
				<div className="flex flex-wrap items-center gap-2.5">
					<div className="relative min-w-[220px] flex-1">
						<span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-faint">
							<svg viewBox="0 0 24 24" width="15" height="15" fill="none" aria-hidden="true">
								<circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
								<path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
							</svg>
						</span>
						<input
							type="search"
							value={search}
							onChange={(event) => setSearch(event.target.value)}
							placeholder="Search terms by name or reference"
							aria-label="Search terms by name or reference"
							className="w-full rounded-full border border-card-line bg-white py-2.5 pl-11 pr-4 text-[13.5px] outline-none transition placeholder:text-slate-faint focus:border-blue"
						/>
					</div>

					<label className="relative">
						<span className="sr-only">Approval state</span>
						<select
							value={state}
							onChange={(event) => setState(event.target.value)}
							className={cx(
								"appearance-none rounded-full border bg-white py-2.5 pl-4 pr-9 text-[13.5px] outline-none transition",
								state
									? "border-blue bg-blue-soft font-semibold text-blue-press"
									: "border-card-line text-slate-strong hover:border-blue",
							)}
						>
							<option value="">All approval states</option>
							{states.map((value) => (
								<option key={value} value={value}>
									{value}
								</option>
							))}
						</select>
						<svg
							viewBox="0 0 24 24"
							width="13"
							height="13"
							fill="none"
							aria-hidden="true"
							className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-faint"
						>
							<path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
						</svg>
					</label>

					<MineToggle mine={mine} onChange={setMine} label="Only mine" />
				</div>
			</Card>

			{creating && (
				<div className="mb-5">
					<TermsForm
						onCreated={() => {
							setCreating(false);
							void mutate();
						}}
					/>
				</div>
			)}

			{!creating && isLoading && <Spinner label="Loading terms of reference…" />}
			{!creating && error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!creating && data && rows.length === 0 && (
				<Empty title="No terms of reference here">
					A terms of reference is the specification a deployment is run against: what the work is,
					what a volunteer is expected to do, and what they must hold to do it. Write one, then
					set up a deployment under it.
				</Empty>
			)}

			{!creating && rows.length > 0 && (
				<ul className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
					{rows.map((row) => (
						<li key={row.name}>
							<TermsPaper row={row} branding={branding ?? null} />
						</li>
					))}
				</ul>
			)}
		</>
	);
}

/**
 * One terms of reference, drawn as the A5 page it becomes when printed.
 *
 * The proportion is real: `aspect-[148/210]` is A5, so a shelf of these has the
 * shape of a shelf of paper. The folded corner and the stamp are the two pieces
 * of ornament, and each is doing work — the fold says "document", and the stamp
 * says where the approval stands without the reader parsing a sentence.
 *
 * **The society's own name is on the letterhead, read from settings.** Not a
 * content block and not a constant: the same rule `BrandLockup` follows, so a
 * society that has named itself sees its own name and one that has not sees the
 * neutral line rather than somebody else's.
 */
function TermsPaper({ row, branding }: { row: TermsOfReference; branding: Branding | null }) {
	const stamp = stampFor(row);

	return (
		<Link
			to={`/admin/deployments/terms/${encodeURIComponent(row.name)}`}
			className="group relative flex aspect-[148/210] min-h-[420px] flex-col overflow-hidden rounded-[8px] border border-card-line bg-white px-5 pb-4 pt-5 shadow-[0_3px_10px_rgba(16,32,51,0.08)] transition duration-200 hover:-translate-y-1 hover:border-blue-line hover:shadow-[0_18px_34px_rgba(16,32,51,0.14)]"
		>
			{/* The folded corner. Decoration, and hidden from assistive technology
			    because it says nothing a screen reader needs. */}
			<span
				aria-hidden="true"
				className="absolute right-0 top-0 h-12 w-12 border-b border-l border-card-line bg-surface [clip-path:polygon(100%_0,0_0,100%_100%)]"
			/>

			<header className="flex items-center gap-2.5 pr-10">
				{branding?.logo ? (
					<img src={branding.logo} alt="" className="h-9 w-9 flex-none object-contain" />
				) : (
					<span
						aria-hidden="true"
						className="grid h-9 w-9 flex-none place-items-center rounded-full bg-blue-soft text-blue"
					>
						<CrossMark size={18} />
					</span>
				)}
				<span className="min-w-0">
					<span className="block truncate text-[11.5px] font-bold leading-tight text-ink">
						{branding?.name ?? "Terms of Reference"}
					</span>
					<span className="block text-[9.5px] text-muted">
						Operations Directorate
					</span>
				</span>
			</header>

			<span aria-hidden="true" className="mt-3 block h-[3px] w-1/3 bg-red" />
			<span aria-hidden="true" className="mb-4 block h-[3px] w-full bg-rail" />

			<p className="text-[9.5px] font-bold uppercase tracking-[0.16em] text-red-ink">
				Terms of Reference
			</p>
			<p className="tabular mt-1 truncate font-mono text-[10px] text-slate-faint">
				{row.tor_key || row.name}
			</p>

			<h3 className="mt-4 max-w-[82%] line-clamp-3 text-[17px] font-bold leading-snug text-ink">
				{row.tor_name}
			</h3>

			<em
				className={cx(
					"absolute right-5 top-[35%] z-10 -rotate-[7deg] rounded border-2 px-2.5 py-1 text-[10px] font-bold not-italic uppercase tracking-[0.09em] shadow-sm",
					stamp.tone,
				)}
			>
				{stamp.label}
			</em>

			{row.project_name && (
				<p className="mt-1.5 line-clamp-1 text-[11.5px] font-semibold text-muted">
					{row.project_name}
				</p>
			)}

			<dl className="mt-5 min-h-0 flex-1 space-y-3 overflow-hidden border-t border-card-line pt-4">
				{row.purpose && (
					<div>
						<dt className="text-[9px] font-bold uppercase tracking-[0.1em] text-muted">
							Purpose
						</dt>
						<dd className="mt-0.5 line-clamp-3 text-[11.5px] leading-relaxed text-slate-strong">
							{row.purpose}
						</dd>
					</div>
				)}
				<div>
					<dt className="text-[9px] font-bold uppercase tracking-[0.1em] text-muted">Area</dt>
					<dd className="mt-0.5 line-clamp-1 text-[11.5px] text-slate-strong">
						{row.geo_scope_path ? geoPath(row.geo_scope_path) : "Applies anywhere"}
					</dd>
				</div>
				<div>
					<dt className="text-[9px] font-bold uppercase tracking-[0.1em] text-muted">
						Expected period
					</dt>
					<dd className="mt-0.5 text-[11.5px] text-slate-strong">
						{row.expected_start_date
							? `${formatDate(row.expected_start_date)}${row.expected_end_date ? ` – ${formatDate(row.expected_end_date)}` : ""}`
							: row.default_duration_days
								? `${row.default_duration_days} ${row.default_duration_days === 1 ? "day" : "days"}, no dates set`
								: "No dates set"}
					</dd>
				</div>
			</dl>

			<footer className="mt-3 flex items-center justify-end border-t border-card-line pt-3">
				<span className="text-[11px] font-semibold text-blue-press group-hover:underline">
					{stamp.action} →
				</span>
			</footer>
		</Link>
	);
}

/**
 * What the stamp on a terms of reference says, and what opening it will do.
 *
 * Two facts decide it and neither is a stage label: `docstatus`, which is
 * whether the wording is still editable, and `approval_state`, which is one of
 * the seven in `states.py`. A society with no approval workflow configured for
 * terms has no `approval_state` at all, and "Submitted" is then the honest word
 * — the wording is frozen and nobody was asked, which is what that society
 * configured.
 */
function stampFor(row: TermsOfReference): { label: string; tone: string; action: string } {
	if (row.is_draft) {
		return {
			label: "Draft",
			tone: "border-slate-faint bg-white text-slate-strong",
			action: "Continue writing",
		};
	}

	if (row.is_cancelled) {
		return { label: "Cancelled", tone: "border-card-line bg-surface text-muted", action: "Open document" };
	}

	switch (row.approval_state) {
		case "Approved":
			return { label: "Approved", tone: "border-success-line bg-success-soft text-success", action: "Open document" };
		case "Submitted":
		case "In Review":
			return {
				label: "In review",
				tone: "border-warning-line bg-warning-soft text-warning",
				action: "Review document",
			};
		case "Rejected":
			return { label: "Rejected", tone: "border-danger-line bg-danger-soft text-danger", action: "Open document" };
		case "Withdrawn":
		case "Expired":
			return {
				label: row.approval_state,
				tone: "border-card-line bg-surface text-muted",
				action: "Open document",
			};
		default:
			// Frozen wording with no approval workflow governing it. Not "draft"
			// and not "approved": nobody was asked, because this society did not
			// ask for anybody to be.
			return {
				label: row.is_active ? "Submitted" : "Retired",
				tone: "border-card-line bg-surface text-slate-strong",
				action: "Open document",
			};
	}
}

/**
 * One terms of reference as the society's own document, and the deployments
 * run under it.
 *
 * The markup is the server's — the same `VMMS Template` render the PDF is built
 * from — so what is on the screen and what comes out of the printer are one
 * document rather than two that have to be kept in step. It carries the
 * society's lockup because `tor_document.py` reads the same
 * `National Society Settings` answer the emails and the cards read.
 */
export function TermsDetail() {
	const { name = "" } = useParams<{ name: string }>();
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: TermsDocument }>(
		API.getTerms,
		{ name },
		`admin:terms:doc:${name}`,
	);

	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	if (isLoading) return <Spinner label="Loading terms of reference…" />;
	if (error) return <ErrorNote>{errorMessage(error)}</ErrorNote>;
	if (!data?.message) return null;

	const { terms, document, deployments } = data.message;
	const documentState = stampFor(terms).label;

	const trail: Crumb[] = [
		{ label: "Deployments", to: "/admin/deployments" },
		...(terms.project
			? ([
					{
						label: terms.project_name ?? terms.project,
						to: `/admin/projects/${encodeURIComponent(terms.project)}`,
					},
				] as Crumb[])
			: ([{ label: "Terms of Reference", to: "/admin/deployments/terms" }] as Crumb[])),
		{ label: terms.tor_name },
	];

	const submit = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.submitTerms, { name });
			void mutate();
		} catch (problem) {
			setFailure(errorMessage(problem, "These terms were not submitted."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<>
			<PageHeading title={terms.tor_name} trail={trail} />

			<div className="space-y-4">
				<Card>
					<div className="flex flex-wrap items-start justify-between gap-3">
						<div>
							<div className="flex flex-wrap items-center gap-2">
								<SectionTitle>Terms of reference</SectionTitle>
								<StateBadge state={documentState} />
								{terms.is_submitted && !terms.is_active && <Pill tone="quiet">Retired</Pill>}
							</div>
							<p className="mt-1 max-w-2xl text-[12px] text-slate-faint">
								{terms.is_draft
									? "Still being written. Nobody can be deployed under a draft: accepting an assignment is accepting this wording, and wording that can still change is not something anybody can agree to. Submit it when it is finished."
									: "The wording is fixed. Everyone assigned under these terms agreed to exactly this text, so a change is an amendment — a new document — rather than an edit."}
							</p>
						</div>

						<div className="flex flex-wrap items-center gap-2">
							<ButtonLink to={termsPdfUrl(name)}>Print as PDF</ButtonLink>
							{terms.is_draft && (
								<Button disabled={busy} onClick={() => void submit()}>
									{busy ? "Submitting…" : "Submit"}
								</Button>
							)}
						</div>
					</div>

					<dl className="mt-4 grid gap-x-5 gap-y-2 border-t border-card-line pt-3 text-[12px] sm:grid-cols-2 lg:grid-cols-4">
						<div>
							<dt className="text-slate-faint">Reference</dt>
							<dd className="font-semibold text-ink">{terms.tor_key}</dd>
						</div>
						<div>
							<dt className="text-slate-faint">Expected period</dt>
							<dd className="font-semibold text-ink">
								{terms.expected_start_date ? formatDate(terms.expected_start_date) : "No start set"}
								{terms.expected_end_date ? ` → ${formatDate(terms.expected_end_date)}` : ""}
							</dd>
						</div>
						<div>
							<dt className="text-slate-faint">Usual duration</dt>
							<dd className="font-semibold text-ink">
								{terms.default_duration_days ? `${terms.default_duration_days} days` : "No usual length"}
							</dd>
						</div>
						<div>
							<dt className="text-slate-faint">Approval mode</dt>
							<dd className="font-semibold capitalize text-ink">{terms.approval_mode || "direct"}</dd>
						</div>
						<div>
							<dt className="text-slate-faint">Applies within</dt>
							<dd className="font-semibold text-ink">
								{terms.geo_scope_path ? geoPath(terms.geo_scope_path) : "Anywhere"}
							</dd>
						</div>
						{terms.amended_from && (
							<div>
								<dt className="text-slate-faint">Amended from</dt>
								<dd className="font-semibold text-ink">{terms.amended_from}</dd>
							</div>
						)}
					</dl>

					{failure && (
						<div className="mt-3">
							<ErrorNote>{failure}</ErrorNote>
						</div>
					)}
				</Card>

				{terms.is_draft ? (
					<MissionEditor terms={terms} onSaved={() => void mutate()} />
				) : (
					<>
						<Card className="overflow-x-auto">
							{/* The body is rendered by the server from a template a society
							    administrator edits on the desk, which is why it is inserted as
							    markup rather than as text. It is authored configuration on the
							    same footing as an Email Template, not a value somebody typed
							    into a public form. */}
							<div
								className="vmms-tor-preview"
								// eslint-disable-next-line react/no-danger
								dangerouslySetInnerHTML={{ __html: document }}
							/>
						</Card>

						<MissionView terms={terms} />
					</>
				)}

				<Card>
					<SectionTitle>Deployments under these terms ({deployments.length})</SectionTitle>

					{deployments.length === 0 ? (
						<p className="mt-2 text-[12.5px] text-slate-faint">
							{terms.is_draft
								? "None, and none can be run until these terms are submitted."
								: "No deployment has been run under these terms yet."}
						</p>
					) : (
						<ul className="mt-3 space-y-2">
							{deployments.map((row) => (
								<DeploymentRow key={row.name} row={row} />
							))}
						</ul>
					)}
				</Card>
			</div>
		</>
	);
}

const TERMS_FORM_STEPS = [
	{ key: "overview", label: "Overview & scope" },
	{ key: "roles", label: "Roles & outcomes" },
	{ key: "plan", label: "People & plan" },
	{ key: "resources", label: "Resources & eligibility" },
	{ key: "review", label: "Review & create" },
] as const;

type TermsFormStep = (typeof TERMS_FORM_STEPS)[number]["key"];

function TermsForm({ onCreated }: { onCreated: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [activeStep, setActiveStep] = useState<TermsFormStep>("overview");

	const [torName, setTorName] = useState("");
	const [project, setProject] = useState("");
	const [isActive, setIsActive] = useState(true);
	const [startsOn, setStartsOn] = useState("");
	const [endsOn, setEndsOn] = useState("");
	const [purpose, setPurpose] = useState("");
	const [background, setBackground] = useState("");
	const [responsibilities, setResponsibilities] = useState("");
	const [duration, setDuration] = useState("");
	const [approvalMode, setApprovalMode] = useState("direct");
	const [notes, setNotes] = useState("");
	const [stakeholders, setStakeholders] = useState<TermsStakeholder[]>([]);
	const [objectives, setObjectives] = useState<TermsObjective[]>([]);
	const [outputs, setOutputs] = useState<TermsOutput[]>([]);
	const [approach, setApproach] = useState<TermsApproach[]>([]);
	const [itinerary, setItinerary] = useState<TermsItineraryRow[]>([]);
	const [resources, setResources] = useState<TermsResource[]>([]);
	const [hasNoResources, setHasNoResources] = useState(false);
	const [requirements, setRequirements] = useState<TermsCertificationRequirement[]>([]);
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	// Only projects still open take new terms, which is the server's rule as
	// well: `project.assert_open` refuses one under a closed programme. Offering
	// a closed project here and refusing it on submit would be two answers.
	const projects = useFrappeGetCall<{ message: { projects: ProjectSummary[] } }>(
		API.branchProjects,
		{ mine: 1 },
		"admin:projects:for-terms",
	);
	const vocabularies = useFrappeGetCall<{ message: TermsVocabularies }>(
		API.torMethodologies,
		undefined,
		"admin:tor:vocabularies",
	);

	const methodOptions = useMemo(
		() =>
			(vocabularies.data?.message?.methodologies ?? []).map((row) => ({
				value: row.name,
				label: row.methodology_name,
			})),
		[vocabularies.data],
	);
	const certificationOptions = useMemo(
		() =>
			(vocabularies.data?.message?.certification_types ?? []).map((row) => ({
				value: row.name,
				label: row.certification_type_name,
			})),
		[vocabularies.data],
	);

	const vocabulary = vocabularies.data?.message;
	const defaultCurrency =
		resources.find((row) => row.currency)?.currency ?? vocabulary?.currencies?.[0] ?? "";

	const options = (projects.data?.message?.projects ?? []).filter((row) => row.is_open);
	const node = selectedNode(chain);
	const ready = torName.trim();
	const hasObjectives = objectives.some((row) => row.objective?.trim());
	const hasOutputs = outputs.some((row) => row.output?.trim());
	const hasPlan = itinerary.some((row) => row.activity?.trim());
	const hasResources = hasNoResources || resources.some((row) => row.resource?.trim());
	const overviewComplete = Boolean(torName.trim() && purpose.trim() && background.trim());
	const rolesComplete = Boolean(
		responsibilities.trim() && hasObjectives && hasOutputs,
	);
	const steps = TERMS_FORM_STEPS.map((step) => ({
		...step,
		complete:
			step.key === "overview"
				? overviewComplete
				: step.key === "roles"
					? rolesComplete
					: step.key === "plan"
						? hasPlan
						: step.key === "resources"
							? hasResources
							: overviewComplete && rolesComplete && hasPlan && hasResources,
	}));
	const stepIndex = TERMS_FORM_STEPS.findIndex((step) => step.key === activeStep);
	const openStep = (step: TermsFormStep) => {
		setActiveStep(step);
	};

	const create = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.createTerms, {
				tor_name: torName.trim(),
				project: project || undefined,
				is_active: isActive,
				purpose: purpose.trim() || undefined,
				mission_background: background.trim() || undefined,
				responsibilities: responsibilities.trim() || undefined,
				geo_scope: node?.name ?? undefined,
				expected_start_date: startsOn || undefined,
				expected_end_date: endsOn || undefined,
				default_duration_days: duration ? Number(duration) : undefined,
				approval_mode: approvalMode,
				has_no_resources: hasNoResources,
				notes: notes.trim() || undefined,
				stakeholders,
				objectives,
				expected_outputs: outputs,
				approach_methods: approach,
				itinerary,
				resources,
				required_certifications: requirements,
			});
			setTorName("");
			setProject("");
			setIsActive(true);
			setStartsOn("");
			setEndsOn("");
			setPurpose("");
			setBackground("");
			setResponsibilities("");
			setDuration("");
			setApprovalMode("direct");
			setNotes("");
			setStakeholders([]);
			setObjectives([]);
			setOutputs([]);
			setApproach([]);
			setItinerary([]);
			setResources([]);
			setRequirements([]);
			setChain([]);
			onCreated();
		} catch (problem) {
			setFailure(errorMessage(problem, "Those terms were not created."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card pad={false}>
			<div className="p-5">
				<SectionTitle>Write a terms of reference</SectionTitle>
				<p className="mt-1 text-[12.5px] text-muted">
					What the work is and what a volunteer deployed to it is expected to do. Deployments point at
					it, and it prints on your society's letterhead.
				</p>
			</div>

			<FormProgressTabs steps={steps} active={activeStep} onChange={openStep} />

			<div
				id={`form-section-${activeStep}`}
				role="tabpanel"
				className="p-5"
			>
				<h3 className="mb-4 text-[16px] font-semibold text-ink">
					{TERMS_FORM_STEPS[stepIndex].label}
				</h3>

			{activeStep === "overview" && <>

			<div className="mt-4 grid gap-4 sm:grid-cols-2">
				<Labelled label="Terms of reference" hint="What your society calls this piece of work.">
					<input className={INPUT} value={torName} onChange={(e) => setTorName(e.target.value)} />
				</Labelled>

				<Labelled
					label="Project"
					hint={
						options.length > 0
							? "The programme these terms are written under. Optional."
							: "Open a project first to group these terms under one."
					}
				>
					<select
						className={INPUT}
						value={project}
						onChange={(e) => setProject(e.target.value)}
						disabled={options.length === 0}
					>
						<option value="">No project</option>
						{options.map((row) => (
							<option key={row.name} value={row.name}>
								{row.project_name}
							</option>
						))}
					</select>
				</Labelled>
			</div>

			<div className="mt-4 grid gap-4 sm:grid-cols-2">
				<Labelled label="Availability" hint="Inactive terms take no new deployments or requests.">
					<span className="flex min-h-[38px] items-center gap-2 rounded-xl border border-card-line bg-white px-3 py-2 text-[13px] text-muted">
						<input
							type="checkbox"
							checked={isActive}
							onChange={(event) => setIsActive(event.target.checked)}
						/>
						Active for new work
					</span>
				</Labelled>
				<Labelled label="Approval mode" hint="Direct fulfils locally; routed requires approval.">
					<select
						className={INPUT}
						value={approvalMode}
						onChange={(event) => setApprovalMode(event.target.value)}
					>
						<option value="direct">Direct</option>
						<option value="routed">Routed</option>
					</select>
				</Labelled>
			</div>

			<div className="mt-4 grid gap-4 sm:grid-cols-3">
				<Labelled label="Expected start" hint="Optional deployment default.">
					<input
						type="datetime-local"
						className={INPUT}
						value={startsOn}
						onChange={(event) => setStartsOn(event.target.value)}
					/>
				</Labelled>
				<Labelled label="Expected end" hint="Must not precede the start.">
					<input
						type="datetime-local"
						className={INPUT}
						value={endsOn}
						onChange={(event) => setEndsOn(event.target.value)}
					/>
				</Labelled>
				<Labelled label="Usual duration (days)" hint="Zero means no usual length.">
					<input
						type="number"
						min="0"
						className={INPUT}
						value={duration}
						onChange={(event) => setDuration(event.target.value)}
					/>
				</Labelled>
			</div>

			<div className="mt-4">
				<Labelled label="Purpose" hint="What a deployment under these terms is for.">
					<textarea
						className={cx(INPUT, "min-h-[72px] resize-y")}
						value={purpose}
						onChange={(e) => setPurpose(e.target.value)}
					/>
				</Labelled>
			</div>
			</>}

			{activeStep === "overview" && (
			<div className="mt-4">
				<Labelled label="Mission background" hint="What happened, what is needed, and what has been done already.">
					<textarea
						className={cx(INPUT, "min-h-[120px] resize-y")}
						value={background}
						onChange={(event) => setBackground(event.target.value)}
					/>
				</Labelled>
			</div>
			)}

			<div className={activeStep === "roles" ? "mt-4" : "hidden"}>
				<Labelled
					label="Responsibilities"
					hint="What the volunteer is expected to do. One per line."
				>
					<textarea
						className={cx(INPUT, "min-h-[96px] resize-y")}
						value={responsibilities}
						onChange={(e) => setResponsibilities(e.target.value)}
					/>
				</Labelled>
			</div>

			<div className="space-y-6">
				<div className={activeStep === "plan" ? "" : "hidden"}>
				<RowEditor<TermsStakeholder>
					title="Stakeholders"
					lead="Who the mission deals with and how deployed volunteers can reach them."
					addLabel="Add a stakeholder"
					empty="Nobody named yet."
					rows={stakeholders}
					onChange={setStakeholders}
					blank={() => ({ designation: "", full_name: "", phone_number: "", email: "" })}
					columns={[
						{ key: "designation", label: "Designation", span: 4 },
						{ key: "full_name", label: "Name", span: 3 },
						{ key: "phone_number", label: "Phone number", span: 2 },
						{ key: "email", label: "Email", span: 3 },
					]}
				/>
				</div>

				<div className={activeStep === "roles" ? "" : "hidden"}>
				<RowEditor<TermsObjective>
					title="Objectives"
					lead="What this mission sets out to achieve, in printed order."
					addLabel="Add an objective"
					empty="No objectives written yet."
					rows={objectives}
					onChange={setObjectives}
					blank={() => ({ objective: "" })}
					columns={[{ key: "objective", label: "Objective", kind: "area" }]}
				/>
				</div>

				<div className={activeStep === "roles" ? "" : "hidden"}>
				<RowEditor<TermsOutput>
					title="Expected outputs"
					lead="What will exist, or be true, after the mission."
					addLabel="Add an output"
					empty="No outputs written yet."
					rows={outputs}
					onChange={setOutputs}
					blank={() => ({ output: "" })}
					columns={[{ key: "output", label: "Expected output", kind: "area" }]}
				/>
				</div>

				<div className={activeStep === "plan" ? "" : "hidden"}>
				<RowEditor<TermsApproach>
					title="Approach methodology"
					lead="How the work will be done, using your society's configured methodologies."
					addLabel="Add a method"
					empty="No approach described yet."
					rows={approach}
					onChange={setApproach}
					blank={() => ({ methodology: "", notes: "" })}
					columns={[
						{
							key: "methodology",
							label: "Methodology",
							kind: "select",
							span: 4,
							options: methodOptions,
						},
						{ key: "notes", label: "Notes", kind: "area", span: 8 },
					]}
				/>
				</div>

				<div className={activeStep === "plan" ? "" : "hidden"}>
				<RowEditor<TermsItineraryRow>
					title="Itinerary"
					lead="The dated plan for the mission."
					addLabel="Add an activity"
					empty="No itinerary yet."
					rows={itinerary}
					onChange={setItinerary}
					blank={() => ({
						activity_date: "",
						activity_time: "",
						activity: "",
						person_responsible: "",
					})}
					columns={[
						{ key: "activity_date", label: "Date", kind: "date", span: 3 },
						{ key: "activity_time", label: "Time", kind: "time", span: 2 },
						{ key: "activity", label: "Activity", kind: "area", span: 4 },
						{ key: "person_responsible", label: "Person responsible", span: 3 },
					]}
				/>
				</div>

				<div className={activeStep === "resources" ? "space-y-6" : "hidden"}>
				{/* The same nine columns the amend editor draws, from one
				    definition — see `resourceColumns`. Two grids for one child
				    table is two places for a column to go missing, which is
				    exactly what had happened to three of them. */}
				<RowEditor<TermsResource>
					title="Resources"
					lead="What is needed, when, in what quantity, at what cost, whose money it is, and from whom."
					addLabel="Add a resource"
					empty="No resources listed yet."
					rows={resources}
					onChange={setResources}
					blank={() => ({ ...blankResource(), currency: defaultCurrency })}
					columns={resourceColumns(vocabulary)}
				/>

				<Labelled
					label="Nothing needed"
					hint="A mission cannot be submitted with an empty resource list unless this says so."
				>
					<span className="flex min-h-[38px] items-center gap-2 rounded-xl border border-card-line bg-white px-3 py-2 text-[13px] text-muted">
						<input
							type="checkbox"
							checked={hasNoResources}
							onChange={(event) => setHasNoResources(event.target.checked)}
						/>
						This mission needs no resources
					</span>
				</Labelled>

				<RowEditor<TermsCertificationRequirement>
					title="Required certifications"
					lead="Mandatory rows filter candidates; desirable rows rank them higher."
					addLabel="Add a certification"
					empty="No certification requirements."
					rows={requirements}
					onChange={setRequirements}
					blank={() => ({
						certification_type: "",
						is_mandatory: true,
						requirement_notes: "",
					})}
					columns={[
						{
							key: "certification_type",
							label: "Certification type",
							kind: "select",
							span: 5,
							options: certificationOptions,
						},
						{ key: "is_mandatory", label: "Mandatory", kind: "check", span: 3 },
						{ key: "requirement_notes", label: "Notes", span: 4 },
					]}
				/>
				</div>
			</div>

			{activeStep === "review" && <div className="space-y-5">
				<div className="rounded-lg border border-card-line bg-surface/60 p-4">
					<p className="text-[12px] font-semibold text-ink">Ready to create this draft?</p>
					<p className="mt-1 text-[12px] leading-relaxed text-muted">
						Review the section tabs above. Red dots mark core information that is still missing;
						the draft can still be created now and completed before it is submitted for approval.
					</p>
				</div>
			<div>
				<Labelled label="Notes" hint="Anything about these terms that is not covered above.">
					<textarea
						className={cx(INPUT, "min-h-[84px] resize-y")}
						value={notes}
						onChange={(event) => setNotes(event.target.value)}
					/>
				</Labelled>
			</div>
			</div>}

			{activeStep === "overview" && (
			<div className="mt-4">
				<p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-faint">
					Where these terms may be used
				</p>
				<GeoSelects chain={chain} onChain={setChain} idPrefix="terms" />
				<p className="mt-2 text-[12px] text-slate-faint">
					Optional. Leave it empty and the terms apply anywhere; set it and a deployment anchored
					outside that branch and everything beneath it is refused.
				</p>
			</div>
			)}

			{failure && (
				<div className="mt-4">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<div className="mt-6 flex items-center justify-between gap-3 border-t border-card-line pt-4">
				<Button
					variant="quiet"
					disabled={stepIndex === 0}
					onClick={() => openStep(TERMS_FORM_STEPS[Math.max(0, stepIndex - 1)].key)}
				>
					← Back
				</Button>
				<p className="hidden text-[11.5px] text-slate-faint sm:block">
					Section {stepIndex + 1} of {TERMS_FORM_STEPS.length}
				</p>
				{activeStep === "review" ? (
					<Button disabled={busy || !ready} onClick={() => void create()}>
						{busy ? "Writing…" : "Create draft terms"}
					</Button>
				) : (
					<Button onClick={() => openStep(TERMS_FORM_STEPS[stepIndex + 1].key)}>
						Continue →
					</Button>
				)}
			</div>
			</div>
		</Card>
	);
}

/* ------------------------------------------------------------------ shared */

export function MineToggle({
	mine,
	onChange,
	label,
}: {
	mine: boolean;
	onChange: (value: boolean) => void;
	label: string;
}) {
	return (
		<button
			type="button"
			onClick={() => onChange(!mine)}
			className={cx(
				"rounded-full border px-3.5 py-1.5 text-[12px] font-semibold transition",
				mine
					? "border-blue bg-rail text-white"
					: "border-card-line bg-white text-muted hover:border-blue hover:text-ink",
			)}
		>
			{label}
		</button>
	);
}

export const INPUT =
	"w-full rounded-xl border border-card-line px-3 py-2.5 text-[13px] outline-none focus:border-blue";

export function Labelled({
	label,
	hint,
	children,
}: {
	label: string;
	hint?: ReactNode;
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
