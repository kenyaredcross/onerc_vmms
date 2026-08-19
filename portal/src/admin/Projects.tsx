import { type ReactNode, useContext, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage, termsPdfUrl } from "../lib/api";
import { formatDate, geoPath } from "../lib/format";
import type {
	DeploymentSummary,
	GeoNode,
	ProjectDossier,
	ProjectSummary,
	TermsDocument,
	TermsOfReference,
} from "../portal/types";
import { GeoSelects, selectedNode } from "../ui/GeoSelects";
import {
	Button,
	ButtonLink,
	Card,
	Empty,
	ErrorNote,
	type Crumb,
	PageHeading,
	Pill,
	SectionTitle,
	Spinner,
	StateBadge,
	cx,
} from "../ui/primitives";

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
				<ul className="space-y-2.5">
					{rows.map((row) => (
						<li key={row.name}>
							<Card>
								<div className="flex flex-wrap items-start justify-between gap-3">
									<div>
										<Link
											to={`/admin/projects/${encodeURIComponent(row.name)}`}
											className="hover:underline"
										>
											<SectionTitle>{row.project_name}</SectionTitle>
										</Link>
										<p className="text-[12px] text-slate-body">{geoPath(row.geo_path)}</p>
										<p className="mt-0.5 text-[12px] text-slate-faint">
											{row.start_date ? formatDate(row.start_date) : "No start date"}
											{row.end_date ? ` → ${formatDate(row.end_date)}` : ""}
										</p>
									</div>
									<StateBadge state={row.status} />
								</div>

								{row.summary && (
									<p className="mt-3 whitespace-pre-line text-[12.5px] text-slate-body">
										{row.summary}
									</p>
								)}

								<div className="mt-4 flex flex-wrap items-center gap-2">
									<Link
										to={`/admin/projects/${encodeURIComponent(row.name)}`}
										className="text-[12px] font-semibold text-navy hover:underline"
									>
										Open project →
									</Link>
									<span className="text-[11.5px] text-slate-faint">{row.name}</span>
								</div>
							</Card>
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
							<p className="text-[12px] text-slate-body">{geoPath(project.geo_path)}</p>
							<p className="mt-0.5 text-[12px] text-slate-faint">
								{project.start_date ? formatDate(project.start_date) : "No start date"}
								{project.end_date ? ` → ${formatDate(project.end_date)}` : ""}
							</p>
						</div>
						<StateBadge state={project.status} />
					</div>

					{project.summary && (
						<p className="mt-3 whitespace-pre-line text-[12.5px] text-slate-body">
							{project.summary}
						</p>
					)}

					{project.notes && (
						<p className="mt-2 whitespace-pre-line text-[12px] text-slate-faint">{project.notes}</p>
					)}

					<div className="mt-4 border-t border-hairline pt-3">
						<StatusRow project={project} onChanged={() => void mutate()} />
					</div>
				</Card>

				<Card>
					<div className="flex flex-wrap items-center justify-between gap-2">
						<SectionTitle>Terms of reference under this project ({terms.length})</SectionTitle>
						<Link
							to="/admin/deployments/terms?new=1"
							className="text-[12px] font-semibold text-navy hover:underline"
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

/** A terms of reference, linked from a project's or a deployment's own page. */
function TermsRow({ row }: { row: TermsOfReference }) {
	return (
		<li>
			<Link
				to={`/admin/deployments/terms/${encodeURIComponent(row.name)}`}
				className="block rounded-card border border-hairline bg-white px-4 py-3 transition hover:border-hairline-strong"
			>
				<div className="flex items-start justify-between gap-2">
					<span className="text-[13.5px] font-bold text-ink">{row.tor_name}</span>
					{!row.is_active && <Pill tone="quiet">Retired</Pill>}
				</div>
				<div className="mt-0.5 text-[11.5px] text-slate-faint">
					{row.geo_scope_path ? geoPath(row.geo_scope_path) : "Applies anywhere"}
					{row.requires_approver ? " · routed for approval" : ""}
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
				className="block rounded-card border border-hairline bg-white px-4 py-3 transition hover:border-hairline-strong"
			>
				<div className="flex items-start justify-between gap-2">
					<span className="text-[13.5px] font-bold text-ink">
						{row.terms_of_reference || row.name}
					</span>
					<StateBadge state={row.status} />
				</div>
				<div className="mt-1 text-[11.5px] text-slate-body">{geoPath(row.geo_path)}</div>
				<div className="mt-0.5 text-[11.5px] text-slate-faint">
					{row.participant_count} on the roster
					{row.start_date ? ` · from ${formatDate(row.start_date)}` : ""}
				</div>
			</Link>
		</li>
	);
}

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
			{project.is_open ? (
				<div className="flex flex-wrap gap-2">
					{["Planned", "Active", "Completed", "Cancelled"]
						.filter((option) => option !== project.status)
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
				start_date: startDate || undefined,
				end_date: endDate || undefined,
			});
			setName("");
			setSummary("");
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
			<p className="mt-1 text-[12.5px] text-slate-body">
				The programme of work: a flood response, a vaccination campaign, a season of branch duty.
				The terms of reference people are deployed against are written under it.
			</p>

			<div className="mt-4 grid gap-4 sm:grid-cols-2">
				<Labelled label="Project" hint="What your society calls this programme.">
					<input className={INPUT} value={name} onChange={(e) => setName(e.target.value)} />
				</Labelled>

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

			<div className="mt-4">
				<Labelled label="Background" hint="Printed at the head of every terms of reference under it.">
					<textarea
						className={cx(INPUT, "min-h-[84px] resize-y")}
						value={summary}
						onChange={(e) => setSummary(e.target.value)}
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

export function TermsList() {
	const [searchParams] = useSearchParams();
	const [mine, setMine] = useState(true);
	const [creating, setCreating] = useState(() => searchParams.get("new") === "1");

	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: { count: number; terms: TermsOfReference[] };
	}>(API.branchTerms, { mine: mine ? 1 : 0 }, `admin:terms:${mine}`);

	const rows = data?.message?.terms ?? [];

	return (
		<>
			<PageHeading
				title="Terms of Reference"
				trail={[{ label: "Deployments", to: "/admin/deployments" }, { label: "Terms of Reference" }]}
			/>

			<div className="mb-4 flex flex-wrap items-center gap-2">
				<MineToggle mine={mine} onChange={setMine} label="Only mine" />
				<div className="ml-auto">
					<Button onClick={() => setCreating((was) => !was)}>
						{creating ? "Close" : "New terms of reference"}
					</Button>
				</div>
			</div>

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

			{isLoading && <Spinner label="Loading terms of reference…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{data && rows.length === 0 && (
				<Empty title="No terms of reference yet">
					A terms of reference is the specification a deployment is run against: what the work is,
					what a volunteer is expected to do, and what they must hold to do it. Write one, then set
					up a deployment under it.
				</Empty>
			)}

			{rows.length > 0 && (
				<ul className="space-y-2.5">
					{rows.map((row) => (
						<li key={row.name}>
							<Link
								to={`/admin/deployments/terms/${encodeURIComponent(row.name)}`}
								className="block rounded-card border border-hairline bg-white px-4 py-3 transition hover:border-hairline-strong"
							>
								<div className="flex items-start justify-between gap-2">
									<span className="text-[13.5px] font-bold text-ink">{row.tor_name}</span>
									{!row.is_active && <Pill tone="quiet">Retired</Pill>}
								</div>
								{row.project_name && (
									<div className="mt-1 text-[11.5px] text-slate-body">{row.project_name}</div>
								)}
								<div className="mt-0.5 text-[11.5px] text-slate-faint">
									{row.geo_scope_path ? geoPath(row.geo_scope_path) : "Applies anywhere"}
									{row.requires_approver ? " · routed for approval" : ""}
								</div>
							</Link>
						</li>
					))}
				</ul>
			)}
		</>
	);
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

	const { data, error, isLoading } = useFrappeGetCall<{ message: TermsDocument }>(
		API.getTerms,
		{ name },
		`admin:terms:doc:${name}`,
	);

	if (isLoading) return <Spinner label="Loading terms of reference…" />;
	if (error) return <ErrorNote>{errorMessage(error)}</ErrorNote>;
	if (!data?.message) return null;

	const { terms, document, deployments } = data.message;

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

	return (
		<>
			<PageHeading title={terms.tor_name} trail={trail} />

			<div className="space-y-4">
				<Card>
					<div className="flex flex-wrap items-center justify-between gap-2">
						<SectionTitle>Terms of reference</SectionTitle>
						<ButtonLink to={termsPdfUrl(name)}>Print as PDF</ButtonLink>
					</div>
					<p className="mt-1 text-[12px] text-slate-faint">
						On your society's letterhead. The same document the PDF is made from, so what you read
						here is what prints.
					</p>
				</Card>

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

				<Card>
					<SectionTitle>Deployments under these terms ({deployments.length})</SectionTitle>

					{deployments.length === 0 ? (
						<p className="mt-2 text-[12.5px] text-slate-faint">
							No deployment has been run under these terms yet.
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

function TermsForm({ onCreated }: { onCreated: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [torName, setTorName] = useState("");
	const [project, setProject] = useState("");
	const [purpose, setPurpose] = useState("");
	const [responsibilities, setResponsibilities] = useState("");
	const [duration, setDuration] = useState("");
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

	const options = (projects.data?.message?.projects ?? []).filter((row) => row.is_open);
	const node = selectedNode(chain);
	const ready = torName.trim();

	const create = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.createTerms, {
				tor_name: torName.trim(),
				project: project || undefined,
				purpose: purpose.trim() || undefined,
				responsibilities: responsibilities.trim() || undefined,
				geo_scope: node?.name ?? undefined,
				default_duration_days: duration ? Number(duration) : undefined,
			});
			setTorName("");
			setProject("");
			setPurpose("");
			setResponsibilities("");
			setDuration("");
			setChain([]);
			onCreated();
		} catch (problem) {
			setFailure(errorMessage(problem, "Those terms were not created."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card>
			<SectionTitle>Write a terms of reference</SectionTitle>
			<p className="mt-1 text-[12.5px] text-slate-body">
				What the work is and what a volunteer deployed to it is expected to do. Deployments point at
				it, and it prints on your society's letterhead.
			</p>

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

			<div className="mt-4">
				<Labelled label="Purpose" hint="What a deployment under these terms is for.">
					<textarea
						className={cx(INPUT, "min-h-[72px] resize-y")}
						value={purpose}
						onChange={(e) => setPurpose(e.target.value)}
					/>
				</Labelled>
			</div>

			<div className="mt-4">
				<Labelled
					label="Responsibilities"
					hint="What the volunteer is expected to do. One per line reads best on the printed document."
				>
					<textarea
						className={cx(INPUT, "min-h-[96px] resize-y")}
						value={responsibilities}
						onChange={(e) => setResponsibilities(e.target.value)}
					/>
				</Labelled>
			</div>

			<div className="mt-4 sm:w-1/2">
				<Labelled label="Usual duration (days)" hint="Optional. A planning figure, never a rule.">
					<input
						type="number"
						min="0"
						className={INPUT}
						value={duration}
						onChange={(e) => setDuration(e.target.value)}
					/>
				</Labelled>
			</div>

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

			{failure && (
				<div className="mt-4">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<div className="mt-5">
				<Button disabled={busy || !ready} onClick={() => void create()}>
					{busy ? "Writing…" : "Write terms of reference"}
				</Button>
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
					? "border-navy bg-navy text-white"
					: "border-hairline-strong bg-white text-slate-body hover:border-navy hover:text-navy",
			)}
		>
			{label}
		</button>
	);
}

export const INPUT =
	"w-full rounded-card border border-hairline-strong px-3 py-2.5 text-[13px] outline-none focus:border-navy";

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
