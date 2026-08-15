import { useContext, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, geoPath } from "../lib/format";
import type {
	Candidate,
	CandidateSearch,
	DeploymentDetail,
	DeploymentRequestRow,
	DeploymentSummary,
	GeoNode,
	RosterRow,
	TermsOfReference,
} from "../portal/types";
import { INPUT, Labelled, MineToggle, ProjectList, TermsList } from "./Projects";
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
	StateBadge,
	cx,
} from "../ui/primitives";

/**
 * The deployments console — who is going, who was asked, and who could go.
 *
 * **Everything here is the coordinator's door**, checked on the server by
 * permission, which brings core's geo scoping with it. The listing is
 * `frappe.get_list`, so a coordinator sees deployments anchored in their own
 * area and nothing on this screen widens that: the status filter narrows a
 * result that was already bounded before it was applied. Somebody holding no
 * Geo Assignment sees an empty console, which is the honest answer.
 *
 * **Matching is a search, not a roster.** `find_candidates` answers who *could*
 * go — deployable, certified, in area — and adding one of them is a second,
 * separate act. The two are drawn apart on purpose: a list that added people as
 * you browsed it would make "who fits" and "who is going" the same question,
 * and they are not.
 *
 * **Adding and inviting are different verbs and are drawn as two buttons.**
 * `add_participant` is a coordinator saying somebody is going; `invite` is a
 * question that person can answer. A decline does not take anybody off the
 * roster — `is_participant` is untouched by a reply — so a declined row still
 * shows, and removing them is the coordinator's own act on the desk. The screen
 * says that rather than implying an answer did more than it did.
 */
export default function AdminDeployments() {
	const [tab, setTab] = useState<"projects" | "terms" | "deployments" | "requests">("projects");

	return (
		<>
			<PageHeading title={<EditableText k="admin.deployments.heading" fallback="Deployments" />} />

			<div className="mb-4 flex flex-wrap gap-2">
				{(
					[
						// The order the records have to exist in: a programme, the terms
						// written under it, the deployment run against those, and the
						// requests that ask for one. Landing on Projects rather than on
						// Deployments is deliberate — it is the first thing a coordinator
						// setting this up has to make, and the two tabs after it read as
						// steps rather than as separate registers.
						["projects", "Projects"],
						["terms", "Terms of Reference"],
						["deployments", "Deployments"],
						["requests", "Requests"],
					] as const
				).map(([key, label]) => (
					<button
						key={key}
						type="button"
						onClick={() => setTab(key)}
						className={cx(
							"rounded-full border px-3.5 py-1.5 text-[12px] font-semibold transition",
							tab === key
								? "border-navy bg-navy text-white"
								: "border-hairline-strong bg-white text-slate-body hover:border-navy hover:text-navy",
						)}
					>
						{label}
					</button>
				))}
			</div>

			{tab === "projects" && <ProjectList />}
			{tab === "terms" && <TermsList />}
			{tab === "deployments" && <DeploymentList />}
			{tab === "requests" && <RequestList />}
		</>
	);
}

/* ------------------------------------------------------------- deployments */

const STATUSES = ["", "Planned", "Active", "Completed", "Cancelled"];

function DeploymentList() {
	const [status, setStatus] = useState("");
	const [mine, setMine] = useState(false);
	const [creating, setCreating] = useState(false);
	const [open, setOpen] = useState<string | null>(null);

	// `mine` defaults **off** here, unlike the two registers before it. A branch's
	// deployments are its shared record of work, and a coordinator looking one up
	// for somebody else is the ordinary case; a project and a terms of reference
	// are drafted by one person, which is why those two default the other way.
	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: { count: number; deployments: DeploymentSummary[]; open_count: number };
	}>(
		API.branchDeployments,
		{ ...(status ? { status } : {}), mine: mine ? 1 : 0 },
		`admin:deployments:${status}:${mine}`,
	);

	const answer = data?.message;
	const rows = answer?.deployments ?? [];

	return (
		<>
			<div className="mb-4 flex flex-wrap items-center gap-2">
				{STATUSES.map((option) => (
					<button
						key={option || "all"}
						type="button"
						onClick={() => setStatus(option)}
						className={cx(
							"rounded-full border px-3.5 py-1.5 text-[12px] font-semibold transition",
							status === option
								? "border-navy bg-navy text-white"
								: "border-hairline-strong bg-white text-slate-body hover:border-navy hover:text-navy",
						)}
					>
						{option || "All"}
					</button>
				))}
				{(answer?.open_count ?? 0) > 0 && (
					<Pill tone="signal">{answer?.open_count} still running</Pill>
				)}
				<MineToggle mine={mine} onChange={setMine} label="Only mine" />
				<div className="ml-auto">
					<Button onClick={() => setCreating((was) => !was)}>
						{creating ? "Close" : "New deployment"}
					</Button>
				</div>
			</div>

			{creating && (
				<div className="mb-5">
					<DeploymentForm
						onCreated={() => {
							setCreating(false);
							void mutate();
						}}
					/>
				</div>
			)}

			{isLoading && <Spinner label="Loading deployments…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{answer && rows.length === 0 && (
				<Empty title="No deployments here">
					Nothing in your area matches. Clear the filter, or raise a request under Requests. If you
					hold no geo assignment, this list is empty by design rather than by accident.
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
										"w-full rounded-card border bg-white px-4 py-3 text-left transition",
										(open ?? rows[0]?.name) === row.name
											? "border-navy shadow-card"
											: "border-hairline hover:border-hairline-strong",
									)}
								>
									<div className="flex items-start justify-between gap-2">
										<span className="text-[13.5px] font-bold text-ink">
											{row.terms_of_reference || row.name}
										</span>
										<StateBadge state={row.status} />
									</div>
									<div className="mt-1 text-[11.5px] text-slate-body">
										{geoPath(row.geo_path)}
									</div>
									<div className="mt-0.5 text-[11.5px] text-slate-faint">
										{row.participant_count} on the roster
										{row.start_date ? ` · from ${formatDate(row.start_date)}` : ""}
									</div>
								</button>
							</li>
						))}
					</ul>

					<DeploymentPane name={open ?? rows[0].name} onChanged={() => void mutate()} />
				</div>
			)}
		</>
	);
}

/**
 * Setting up a deployment directly, under terms that already exist.
 *
 * **The other way one comes into being is an approved request**, and that path
 * is untouched: this is the branch running its own duty rather than asking
 * anybody for people. The insert on the server is ordinary, so core's query
 * condition refuses a deployment anchored outside this coordinator's own area
 * and the refusal comes from the permission layer rather than from this form.
 *
 * **The terms list is what this person wrote**, because a deployment cannot be
 * set up under terms that do not exist yet and the tab before this one is where
 * they are written. Retired terms are filtered out here and refused on the
 * server too — `terms.assert_active` — so the two agree rather than the screen
 * offering something the save will reject.
 */
function DeploymentForm({ onCreated }: { onCreated: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [terms, setTerms] = useState("");
	const [startDate, setStartDate] = useState("");
	const [endDate, setEndDate] = useState("");
	const [notes, setNotes] = useState("");
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const available = useFrappeGetCall<{ message: { terms: TermsOfReference[] } }>(
		API.branchTerms,
		{ mine: 1, active_only: 1 },
		"admin:terms:for-deployment",
	);

	const options = available.data?.message?.terms ?? [];
	const node = selectedNode(chain);
	const ready = terms && startDate && endDate && node;

	const create = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.createDeployment, {
				terms_of_reference: terms,
				geo_node: node?.name,
				start_date: startDate,
				end_date: endDate,
				notes: notes.trim() || undefined,
			});
			setTerms("");
			setStartDate("");
			setEndDate("");
			setNotes("");
			setChain([]);
			onCreated();
		} catch (problem) {
			setFailure(errorMessage(problem, "That deployment was not created."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card>
			<SectionTitle>Set up a deployment</SectionTitle>
			<p className="mt-1 text-[12.5px] text-slate-body">
				Under terms that already exist. Volunteers are added to the roster afterwards, either
				directly or by invitation.
			</p>

			{options.length === 0 ? (
				<p className="mt-4 text-[12.5px] text-slate-faint">
					No active terms of reference yet. Write one under Terms of Reference first: a deployment
					points at the terms it is run against, and there is nothing to point at.
				</p>
			) : (
				<>
					<div className="mt-4 grid gap-4 sm:grid-cols-2">
						<Labelled label="Terms of reference" hint="What this deployment is run against.">
							<select
								className={INPUT}
								value={terms}
								onChange={(event) => setTerms(event.target.value)}
							>
								<option value="">Select…</option>
								{options.map((row) => (
									<option key={row.name} value={row.name}>
										{row.project_name ? `${row.project_name} — ${row.tor_name}` : row.tor_name}
									</option>
								))}
							</select>
						</Labelled>

						<div className="grid grid-cols-2 gap-3">
							<Labelled label="Starts" hint="Required.">
								<input
									type="date"
									className={INPUT}
									value={startDate}
									onChange={(event) => setStartDate(event.target.value)}
								/>
							</Labelled>
							<Labelled label="Ends" hint="Required.">
								<input
									type="date"
									className={INPUT}
									value={endDate}
									onChange={(event) => setEndDate(event.target.value)}
								/>
							</Labelled>
						</div>
					</div>

					<div className="mt-4">
						<Labelled label="Notes" hint="Optional. Anything about this deployment that is not a field.">
							<textarea
								className={cx(INPUT, "min-h-[72px] resize-y")}
								value={notes}
								onChange={(event) => setNotes(event.target.value)}
							/>
						</Labelled>
					</div>

					<div className="mt-4">
						<p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-faint">
							Where this deployment happens
						</p>
						<GeoSelects chain={chain} onChain={setChain} idPrefix="deployment" />
						<p className="mt-2 text-[12px] text-slate-faint">
							Required, and it must sit inside whatever scope the terms name. A deployment with
							no place in the organisation is unroutable and invisible.
						</p>
					</div>

					{failure && (
						<div className="mt-4">
							<ErrorNote>{failure}</ErrorNote>
						</div>
					)}

					<div className="mt-5">
						<Button disabled={busy || !ready} onClick={() => void create()}>
							{busy ? "Setting up…" : "Set up deployment"}
						</Button>
					</div>
				</>
			)}
		</Card>
	);
}

/** One deployment: its terms, its roster, and the coordinator's verbs on it. */
function DeploymentPane({ name, onChanged }: { name: string; onChanged: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const { data, isLoading, mutate } = useFrappeGetCall<{ message: DeploymentDetail }>(
		API.getDeployment,
		{ name },
		`admin:deployment:${name}`,
	);

	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);
	const [matching, setMatching] = useState(false);

	const deployment = data?.message;

	const act = async (label: string, method: string, args: Record<string, unknown>) => {
		setBusy(label);
		setFailure(null);

		try {
			await call.post(method, { name, ...args });
			await mutate();
			onChanged();
		} catch (problem) {
			setFailure(errorMessage(problem));
		} finally {
			setBusy(null);
		}
	};

	if (isLoading) return <Spinner label="Loading deployment…" />;
	if (!deployment) return null;

	return (
		<div className="space-y-4">
			<Card>
				<div className="flex flex-wrap items-start justify-between gap-3">
					<div>
						<SectionTitle>{deployment.terms?.tor_name || deployment.name}</SectionTitle>
						<p className="text-[12px] text-slate-body">{geoPath(deployment.geo_path)}</p>
						<p className="mt-0.5 text-[12px] text-slate-faint">
							{deployment.start_date ? formatDate(deployment.start_date) : "No start date"}
							{deployment.end_date ? ` → ${formatDate(deployment.end_date)}` : ""}
						</p>
					</div>
					<StateBadge state={deployment.status} />
				</div>

				{deployment.terms?.purpose && (
					<p className="mt-3 text-[12.5px] text-slate-body">{deployment.terms.purpose}</p>
				)}

				{(deployment.terms?.required_certifications?.length ?? 0) > 0 && (
					<div className="mt-3">
						<p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-faint">
							Required certifications
						</p>
						<div className="mt-1.5 flex flex-wrap gap-1.5">
							{deployment.terms?.required_certifications.map((key) => (
								<Pill key={key} tone="navy">
									{key}
								</Pill>
							))}
						</div>
					</div>
				)}

				{failure && (
					<div className="mt-3">
						<ErrorNote>{failure}</ErrorNote>
					</div>
				)}

				<div className="mt-4 flex flex-wrap gap-2">
					{["Planned", "Active", "Completed", "Cancelled"]
						.filter((option) => option !== deployment.status)
						.map((option) => (
							<Button
								key={option}
								variant="quiet"
								disabled={busy !== null}
								onClick={() =>
									void act(option, API.setDeploymentStatus, { status: option })
								}
							>
								{busy === option ? "Working…" : `Mark ${option.toLowerCase()}`}
							</Button>
						))}
				</div>
			</Card>

			<Card>
				<div className="flex flex-wrap items-center justify-between gap-2">
					<SectionTitle>Roster ({deployment.participants.length})</SectionTitle>
					<Button onClick={() => setMatching((was) => !was)}>
						{matching ? "Close" : "Find volunteers"}
					</Button>
				</div>

				{deployment.participants.length === 0 ? (
					<p className="mt-2 text-[12.5px] text-slate-faint">
						Nobody on this deployment yet. Find volunteers who fit its terms above.
					</p>
				) : (
					<ul className="mt-2 divide-y divide-hairline">
						{deployment.participants.map((row) => (
							<RosterEntry key={row.volunteer} row={row} />
						))}
					</ul>
				)}

				<p className="mt-3 text-[11.5px] text-slate-faint">
					An invitation is a question, not a roster change. Somebody who declines stays listed
					until a coordinator takes them off, because a decline must not invalidate a record of
					service that already happened.
				</p>
			</Card>

			{matching && (
				<CandidatePane
					deployment={deployment}
					busy={busy}
					onAdd={(volunteer, invite) =>
						act(
							invite ? `invite:${volunteer}` : `add:${volunteer}`,
							invite ? API.inviteVolunteer : API.addParticipant,
							{ volunteer },
						)
					}
				/>
			)}
		</div>
	);
}

/** One roster row, and what the person said if they were asked. */
function RosterEntry({ row }: { row: RosterRow }) {
	// Keyed off `response`, which is the doctype's own closed Select, not off a
	// label somebody typed. Blank never reaches here: it is drawn as "not asked",
	// which is a different fact from having been asked and not replied.
	const tone = row.response === "declined" ? "signal" : row.response === "accepted" ? "navy" : "page";

	return (
		<li className="flex flex-wrap items-center justify-between gap-2 py-2.5">
			<div>
				<span className="text-[13px] font-semibold text-ink">{row.volunteer}</span>
				<span className="ml-2 text-[11.5px] text-slate-faint">
					{row.joined_on ? `joined ${formatDate(row.joined_on)}` : "no join date"}
					{row.left_on ? ` · left ${formatDate(row.left_on)}` : ""}
				</span>
			</div>
			{row.response ? (
				<Pill tone={tone}>{row.response}</Pill>
			) : (
				<span className="text-[11.5px] text-slate-faint">not asked</span>
			)}
		</li>
	);
}

/**
 * Who could go. A search over the register bounded by the same scope as
 * everything else, ranked by the service, and truncated honestly.
 */
function CandidatePane({
	deployment,
	busy,
	onAdd,
}: {
	deployment: DeploymentDetail;
	busy: string | null;
	onAdd: (volunteer: string, invite: boolean) => void;
}) {
	const { data, error, isLoading } = useFrappeGetCall<{ message: CandidateSearch }>(
		API.findCandidates,
		{
			terms_of_reference: deployment.terms_of_reference,
			geo_node: deployment.geo_node,
			as_of: deployment.start_date ?? undefined,
			limit: 25,
		},
		`admin:candidates:${deployment.name}`,
	);

	const answer = data?.message;
	const onRoster = new Set(deployment.participants.map((row) => row.volunteer));

	return (
		<Card>
			<SectionTitle>Volunteers who fit these terms</SectionTitle>

			{isLoading && <Spinner label="Matching…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{answer && (
				<p className="mb-3 text-[11.5px] text-slate-faint">
					{answer.candidate_count} of {answer.considered} volunteers in your area are deployable
					and hold what these terms require
					{answer.as_of ? `, as of ${formatDate(answer.as_of)}` : ""}.
					{answer.truncated && " Showing the first 25."}
				</p>
			)}

			{answer && answer.candidates.length === 0 && (
				<Empty title="Nobody matches yet">
					No volunteer in your area is both deployable and holds every certification these terms
					require. Widen the terms, or record the certifications people have earned.
				</Empty>
			)}

			<ul className="divide-y divide-hairline">
				{(answer?.candidates ?? []).map((person) => (
					<CandidateRow
						key={person.volunteer}
						person={person}
						already={onRoster.has(person.volunteer)}
						busy={busy}
						onAdd={onAdd}
					/>
				))}
			</ul>
		</Card>
	);
}

function CandidateRow({
	person,
	already,
	busy,
	onAdd,
}: {
	person: Candidate;
	already: boolean;
	busy: string | null;
	onAdd: (volunteer: string, invite: boolean) => void;
}) {
	return (
		<li className="flex flex-wrap items-center justify-between gap-2 py-3">
			<div className="min-w-0">
				<span className="text-[13px] font-semibold text-ink">{person.full_name}</span>
				<div className="text-[11.5px] text-slate-faint">
					{geoPath(person.geo_path)}
					{person.desirable_certifications_held.length > 0 &&
						` · also holds ${person.desirable_certifications_held.join(", ")}`}
				</div>
			</div>

			{already ? (
				<span className="text-[11.5px] font-semibold text-slate-faint">On the roster</span>
			) : (
				<div className="flex gap-2">
					<Button
						variant="quiet"
						disabled={busy !== null}
						onClick={() => onAdd(person.volunteer, true)}
					>
						{busy === `invite:${person.volunteer}` ? "Asking…" : "Invite"}
					</Button>
					<Button disabled={busy !== null} onClick={() => onAdd(person.volunteer, false)}>
						{busy === `add:${person.volunteer}` ? "Adding…" : "Add"}
					</Button>
				</div>
			)}
		</li>
	);
}

/* ---------------------------------------------------------------- requests */

/**
 * Requests for volunteers, and where each one's approval stands.
 *
 * **Deciding one is not here.** A routed request is acted on from the review
 * queue, through `api/approvals.py`, because the person-gate lives there and a
 * second door into the same decision would be a second place to get it wrong.
 * This screen shows the state and sends you there.
 */
function RequestList() {
	const { data, error, isLoading } = useFrappeGetCall<{
		message: { count: number; requests: DeploymentRequestRow[] };
	}>(API.branchRequests, undefined, "admin:deployment_requests");

	const rows = data?.message?.requests ?? [];

	return (
		<>
			{isLoading && <Spinner label="Loading requests…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{data && rows.length === 0 && (
				<Empty title="No requests in your area">
					A deployment request asks for volunteers against a terms of reference. Raising one is a
					desk action; once raised, it appears here and routes to whoever its terms name.
				</Empty>
			)}

			<div className="space-y-3">
				{rows.map((row) => (
					<Card key={row.name}>
						<div className="flex flex-wrap items-start justify-between gap-3">
							<div>
								<SectionTitle>{row.terms_of_reference || row.name}</SectionTitle>
								<p className="text-[12px] text-slate-body">{geoPath(row.geo_path)}</p>
								<p className="mt-0.5 text-[12px] text-slate-faint">
									{row.volunteers_requested ?? 0} volunteer(s)
									{row.needed_from ? ` · from ${formatDate(row.needed_from)}` : ""}
									{row.needed_until ? ` to ${formatDate(row.needed_until)}` : ""}
								</p>
							</div>
							<div className="flex flex-wrap items-center gap-2">
								{row.approval ? (
									<StateBadge state={row.approval.state} />
								) : (
									<Pill tone="quiet">No approver required</Pill>
								)}
								{row.is_fulfilled && <Pill tone="signal">Deployment created</Pill>}
								{row.is_refused && <Pill tone="signal">Refused</Pill>}
							</div>
						</div>

						{row.approval && !row.approval.can_act && row.approval.is_open && (
							<p className="mt-2 text-[11.5px] text-slate-faint">
								Waiting on somebody else. Requests you can act on appear in your review queue.
							</p>
						)}
					</Card>
				))}
			</div>
		</>
	);
}
