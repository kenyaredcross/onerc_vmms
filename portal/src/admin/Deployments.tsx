import { useContext, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, geoPath } from "../lib/format";
import type {
	ApplicationOptions,
	AssignmentOutcome,
	Candidate,
	CandidateSearch,
	DeploymentDetail as DeploymentDetailDto,
	DeploymentFeed,
	DeploymentMapAnswer,
	DeploymentRequestRow,
	DeploymentSummary,
	FeedEntry,
	GeoNode,
	RosterRow,
	TermsOfReference,
} from "../portal/types";
import { INPUT, Labelled, MineToggle } from "./Projects";
import { GeoSelects, selectedNode } from "../ui/GeoSelects";
import { MultiCombo } from "../ui/form";
import { DeploymentMap } from "./DeploymentMap";
import { HoverCard } from "../ui/HoverCard";
import {
	Avatar,
	Button,
	ButtonLink,
	Card,
	type Crumb,
	Empty,
	ErrorNote,
	Meter,
	PageHeading,
	Pill,
	SectionLabel,
	SectionLink,
	SectionTitle,
	Skeleton,
	Spinner,
	StatGrid,
	StatTile,
	StateBadge,
	cx,
} from "../ui/primitives";
import { Icon } from "../ui/icons";
import { exceptionsFor, figuresFor } from "./counts";

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
 * **`/admin/deployments` is the dashboard, and the registers hang off it.**
 * Terms of Reference, Deployments and Requests are three independent registers,
 * each its own routed page, and a URL is what lets somebody link, bookmark or
 * come back to one directly. What the landing page adds on top is the thing a
 * manager actually opens it for: how many people are out, where, and how much
 * of what was asked for has been filled.
 *
 * **Projects is not a fourth.** It stands on its own at `/admin/projects`,
 * because a project can exist without ever needing a terms of reference or a
 * deployment — see `Projects.tsx`'s own docstring.
 *
 * **The roster is a register of documents, not a list of names.** Each person's
 * deployment is a `VMMS Deployment Assignment` with its own status, its own
 * URL, and a record of the exact submitted terms of reference they were asked to
 * accept. That is what lets this screen show who was asked and has not answered
 * apart from who is going, and it is what the volunteer's own accept/decline
 * page acts on.
 *
 * **Matching is a search, not a roster.** `find_candidates` answers who *could*
 * go — deployable, certified, in area, free on the days, and not already spoken
 * for — and putting one of them on is a second, separate act. The two are drawn
 * apart on purpose: a list that assigned people as you browsed it would make
 * "who fits" and "who is going" the same question, and they are not.
 *
 * **Asking and placing are different verbs and stay two buttons, in bulk too.**
 * Placing is a coordinator saying somebody is going; asking is a question that
 * person answers. Bulk does both, one at a time on the server, and reports which
 * ones did not take — because some will fail, and a screen that refused the whole
 * batch for one bad row would make a coordinator find it by bisection.
 */

/* -------------------------------------------------------------- dashboard */

/**
 * The landing page: what is running, where, and how full it is.
 *
 * **The area breakdown is a ranked list, not a map**, and that is a decision
 * rather than a shortcut. `Geo Node` carries no latitude or longitude — the only
 * coordinates in this app are on `VMMS Branch Location`, which is a building
 * rather than an area — so a point map would plot the branch offices of the
 * places with a published location and silently omit the rest. Worse, a *heat*
 * map of how many people are deployed where needs boundary polygons per node,
 * which is a far bigger data problem than points. Counting by area answers the
 * question the map was wanted for — where are our people — with data the app
 * actually holds, and it drills through to the deployments themselves.
 */
/**
 * The operational dashboard: what is running, who is out, and what needs doing.
 *
 * **Counting terminology is exact here, because the words are load-bearing.**
 *
 *   deployed now      an assignment is Assigned or Accepted *and* its
 *                     deployment is Active
 *   coming up         the same assignments, on a Planned deployment
 *   awaiting response  Pending — asked, no reply. Never counted as deployed.
 *   open positions    places_left on a deployment that is still running
 *
 * A person who was invited and has not answered is not somebody on a
 * deployment, and the two used to be added together on this screen.
 *
 * **Every figure below is derived from one page of the register, and says so.**
 * `branch_deployments` returns `count = len(rows)` with a page cap of 100 — it
 * is the size of the page, not the register — so nothing here is labelled as a
 * total. See the backend-gap note in the report: an aggregate endpoint is what
 * this screen actually wants.
 */
export function DeploymentsHub() {
	const terms = useFrappeGetCall<{ message: { count: number } }>(
		API.branchTerms,
		{ mine: 0 },
		"admin:hub:terms",
	);
	const deployments = useFrappeGetCall<{
		message: { count: number; open_count: number; deployments: DeploymentSummary[] };
	}>(API.branchDeployments, { mine: 0 }, "admin:hub:deployments");
	const requests = useFrappeGetCall<{ message: { count: number; requests: DeploymentRequestRow[] } }>(
		API.branchRequests,
		undefined,
		"admin:hub:requests",
	);

	const rows = deployments.data?.message?.deployments ?? [];
	const pendingRequests = (requests.data?.message?.requests ?? []).filter(
		(row) => !row.is_fulfilled && !row.is_refused,
	).length;

	// Where the people are comes from its own endpoint rather than being derived
	// from the listing above: it needs the geo tree's coordinates, which only the
	// server can join, and it counts across every deployment in scope rather than
	// the page this listing happened to fetch.
	const map = useFrappeGetCall<{ message: DeploymentMapAnswer }>(
		API.deploymentMap,
		undefined,
		"admin:hub:map",
	);

	// The arithmetic lives in `counts.ts` as pure functions — see its docstring
	// for the vocabulary, and `tests/counts.test.ts` for what holds it still.
	const figures = figuresFor(rows);
	const exceptions = exceptionsFor(rows);

	return (
		<>
			<PageHeading
				title={<EditableText k="admin.deployments.dashboard" fallback="Deployment dashboard" />}
				lead="Operations across your authorised geographic scope."
				actions={<ButtonLink to="/portal/admin/deployments/new">Create deployment</ButtonLink>}
			/>

			{deployments.error && (
				<div className="mb-5">
					<ErrorNote>{errorMessage(deployments.error)}</ErrorNote>
				</div>
			)}

			<StatGrid className="mb-5">
				<StatTile
					label="Deployed now"
					value={deployments.isLoading ? "—" : figures.deployedNow}
					hint={`Assigned or accepted, on ${figures.activeCount} active deployment${figures.activeCount === 1 ? "" : "s"}`}
					icon={Icon.people}
					tint="navy"
					to="/admin/deployments/ongoing"
				/>
				<StatTile
					label="Coming up"
					value={deployments.isLoading ? "—" : figures.comingUp}
					hint={`Confirmed on ${figures.plannedCount} planned deployment${figures.plannedCount === 1 ? "" : "s"}`}
					icon={Icon.calendar}
					tint="sky"
					to="/admin/deployments/ongoing"
				/>
				<StatTile
					label="Awaiting response"
					value={deployments.isLoading ? "—" : figures.awaitingResponse}
					hint={figures.awaitingResponse > 0 ? "Invited, no reply yet" : "Nobody is waiting"}
					icon={Icon.hourglass}
					tint="amber"
				/>
				<StatTile
					label="Positions open"
					value={deployments.isLoading ? "—" : figures.openPositions}
					hint={
						figures.requested > 0
							? `${figures.deployedNow + figures.comingUp} confirmed of ${figures.requested} requested`
							: "No requirement set"
					}
					icon={Icon.plus}
					tint="teal"
				/>
			</StatGrid>

			<p className="mb-5 -mt-2 text-[11px] leading-relaxed text-muted">
				Figures cover the most recent {figures.sampled} deployment
				{figures.sampled === 1 ? "" : "s"} in your scope, which is one page of the register rather
				than its full size.
			</p>

			<div className="mb-5 grid items-start gap-4 xl:grid-cols-3">
				<div className="xl:col-span-2">
					<WhereTheyAre answer={map.data?.message} loading={map.isLoading} />
				</div>

				<Card pad={false}>
					<div className="flex items-center justify-between gap-3 px-5 pb-3 pt-4">
						<SectionLabel>Needs attention</SectionLabel>
						<SectionLink to="/admin/deployments/ongoing">See all</SectionLink>
					</div>

					<div className="px-4 pb-4">
						{deployments.isLoading && <Skeleton className="h-28" />}

						{!deployments.isLoading && exceptions.length === 0 && (
							<p className="px-1 py-3 text-[12px] leading-relaxed text-muted">
								Nothing outstanding on this page. Rosters are filled and every invitation has
								been answered.
							</p>
						)}

						<ul className="space-y-1">
							{exceptions.slice(0, 6).map((item, index) => (
								<li key={`${item.row.name}-${index}`}>
									<Link
										to={`/admin/deployments/${encodeURIComponent(item.row.name)}`}
										className="block rounded-control px-3 py-2.5 transition hover:bg-surface"
									>
										<span className="block truncate text-[12.5px] font-medium text-ink">
											{item.row.terms_of_reference || item.row.name}
										</span>
										<span
											className={cx(
												"mt-0.5 flex items-center gap-1.5 text-[11px]",
												item.tone === "danger" ? "text-danger" : "text-warning",
											)}
										>
											{/* A dot as well as the colour: a state is never a hue
											    alone. */}
											<span
												aria-hidden="true"
												className="h-1.5 w-1.5 flex-none rounded-full bg-current"
											/>
											{item.text}
										</span>
									</Link>
								</li>
							))}
						</ul>
					</div>
				</Card>
			</div>

			<div className="grid gap-4 sm:grid-cols-3">
				<HubCard
					to="/admin/deployments/terms"
					newTo="/admin/deployments/terms?new=1"
					title="Terms of Reference"
					count={terms.data?.message?.count}
					lead="The mission: what the work is, what it will achieve, and what a volunteer must hold to do it."
				/>
				<HubCard
					to="/admin/deployments/ongoing"
					newTo="/admin/deployments/new"
					title="Ongoing deployments"
					count={deployments.data?.message?.open_count}
					detail={`${figures.runningCount} still running`}
					lead="Who is going, under which terms, and where."
				/>
				<HubCard
					to="/admin/deployments/requests"
					title="Requests"
					count={requests.data?.message?.count}
					detail={pendingRequests > 0 ? `${pendingRequests} awaiting an outcome` : undefined}
					lead="Asks for volunteers, and where each one's approval stands."
				/>
			</div>
		</>
	);
}

/**
 * Where this coordinator's people are — on a map, and as a ranked list.
 *
 * **Both, because neither is sufficient alone.** The map answers "where are most
 * of them" at a glance, which is the question a manager opens this page with. It
 * can only draw the areas whose geo node carries a point, and a tree is filled
 * in from the top down over months — so the list beside it carries *every* area,
 * plotted or not, and the panel says plainly how many the map left off. A map
 * showing four pins when there are eleven areas would otherwise read as "we only
 * work in four places".
 *
 * The list is also the accessible view: a Leaflet canvas is not operable by
 * keyboard in any meaningful way, so the map is `aria-hidden` and everything it
 * shows is in the list as text.
 */
function WhereTheyAre({ answer, loading }: { answer?: DeploymentMapAnswer; loading: boolean }) {
	const areas = answer?.areas ?? [];
	const most = areas[0]?.people ?? 0;
	const unplotted = answer?.unplotted ?? 0;

	return (
		<Card>
			<SectionTitle>Where they are</SectionTitle>
			<p className="mt-1 text-[12px] text-slate-faint">
				People on running deployments, by the area the work is anchored in. Circles are sized by how
				many, so two areas compare the way they look.
			</p>

			{loading && <Spinner label="Counting…" />}

			{!loading && areas.length === 0 && (
				<p className="mt-3 text-[12.5px] text-slate-faint">
					Nothing is running in your area at the moment.
				</p>
			)}

			{areas.length > 0 && (
				<div className="mt-4 grid gap-4 lg:grid-cols-2">
					<DeploymentMap areas={areas} />

					<div className="space-y-3.5">
						{areas.slice(0, 8).map((area, index) => (
							<Meter
								key={area.geo_node}
								label={area.geo_path ?? area.geo_node}
								value={area.people}
								total={most || 1}
								figure={
									<span className="text-[12px] font-semibold text-slate-body">
										{area.people} on {area.deployments}{" "}
										{area.deployments === 1 ? "deployment" : "deployments"}
									</span>
								}
								tint={(["navy", "teal", "violet", "amber", "sky", "rose"] as const)[index % 6]}
							/>
						))}

						{areas.length > 8 && (
							<p className="text-[11.5px] text-slate-faint">
								And {areas.length - 8} more {areas.length - 8 === 1 ? "area" : "areas"}.
							</p>
						)}
					</div>
				</div>
			)}

			{unplotted > 0 && (
				<p className="mt-3 border-t border-hairline pt-3 text-[11.5px] text-slate-faint">
					{unplotted} of these {areas.length} areas {unplotted === 1 ? "is" : "are"} not on the map:
					their place in the organisation carries no coordinates yet. Add a latitude and longitude to
					the Geo Node and it appears here.
				</p>
			)}
		</Card>
	);
}

function HubCard({
	to,
	newTo,
	title,
	count,
	detail,
	lead,
}: {
	to: string;
	newTo?: string;
	title: string;
	count?: number;
	detail?: string;
	lead: string;
}) {
	return (
		<Card className="relative">
			<Link to={to} className="block">
				<div className="flex items-start justify-between gap-3">
					<SectionTitle>{title}</SectionTitle>
					<span className="text-[22px] font-extrabold text-navy">{count ?? "—"}</span>
				</div>
				<p className="mt-1 text-[12.5px] text-slate-body">{lead}</p>
				{detail && <p className="mt-2 text-[11.5px] font-semibold text-slate-faint">{detail}</p>}
			</Link>
			{newTo && (
				<Link
					to={newTo}
					className="mt-3 inline-block text-[12px] font-semibold text-navy hover:underline"
				>
					+ New
				</Link>
			)}
		</Card>
	);
}

/* ------------------------------------------------------------- deployments */

const STATUSES = ["", "Planned", "Active", "Completed", "Cancelled"];

/**
 * Which statuses each routed view of the register covers.
 *
 * Two addresses over one register rather than a filter somebody has to set
 * again after every reload — "ongoing" and "past" are different questions a
 * coordinator asks, and each deserves a link they can send a colleague.
 *
 * **Cancelled is in `past`, not hidden.** A cancelled deployment is part of the
 * record of what a branch planned and what happened to it; a register that
 * quietly dropped them would make a stood-down operation look like one that
 * never existed.
 */
const SCOPES: Record<string, { statuses: string[]; title: string }> = {
	ongoing: { statuses: ["Planned", "Active"], title: "Ongoing deployments" },
	past: { statuses: ["Completed", "Cancelled"], title: "Past deployments" },
};

export type DeploymentScope = "ongoing" | "past";

export function DeploymentList({ scope }: { scope?: DeploymentScope } = {}) {
	const [searchParams] = useSearchParams();
	const band = scope ? SCOPES[scope] : null;
	// Within a scoped view the filter starts on "all of this scope" and can be
	// narrowed to one of its statuses; the unscoped register keeps every status.
	const [status, setStatus] = useState("");
	const [mine, setMine] = useState(false);
	const [creating, setCreating] = useState(() => searchParams.get("new") === "1");

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
	const all = answer?.deployments ?? [];

	// **Narrowing a page of results, not the register.** The endpoint filters by
	// one status at a time, so a two-status band is assembled here from the
	// unfiltered page. That means a scoped view shows this page's members of the
	// band — it is deliberately *not* presented as a total anywhere, and the
	// count line below says "on this page" rather than naming a register size.
	// Filtering server-side by a status *set* is a backend gap; see the report.
	const rows = band && !status ? all.filter((row) => band.statuses.includes(row.status)) : all;

	const choices = band ? ["", ...band.statuses] : STATUSES;

	return (
		<>
			<PageHeading
				title={band ? band.title : "Deployments"}
				lead={
					scope === "ongoing"
						? "Planned and active deployments in your area."
						: scope === "past"
							? "Completed and cancelled deployments, kept in full."
							: undefined
				}
				trail={[
					{ label: "Deployments", to: "/admin/deployments" },
					{ label: band ? band.title : "Deployments" },
				]}
			/>

			<div className="mb-4 flex flex-wrap items-center gap-2">
				{choices.map((option) => (
					<button
						key={option || "all"}
						type="button"
						onClick={() => setStatus(option)}
						aria-pressed={status === option}
						className={cx(
							"rounded-full border px-3.5 py-1.5 text-[12px] font-medium transition",
							status === option
								? "border-blue bg-blue text-white"
								: "border-hairline-strong bg-white text-slate-body hover:border-slate-faint hover:text-ink",
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
				<ul className="grid gap-3 sm:grid-cols-2">
					{rows.map((row) => (
						<li key={row.name}>
							<DeploymentCard row={row} />
						</li>
					))}
				</ul>
			)}
		</>
	);
}

/**
 * One deployment as a card: where, when, and how much of what it asked for it
 * has actually got.
 *
 * The staffing line is the part worth having. A deployment that needs six and
 * has two is a different thing from one that needs six and has six, and a list
 * that showed only "2 on the roster" made a coordinator open each one to find
 * out which. Where the society has not said how many it needs, there is nothing
 * to be short of and the meter is not drawn rather than being drawn empty.
 */
function DeploymentCard({ row }: { row: DeploymentSummary }) {
	const waiting = row.assignment_counts?.Pending ?? 0;

	return (
		<Card className="h-full">
			<Link to={`/admin/deployments/${encodeURIComponent(row.name)}`} className="block">
				<div className="flex items-start justify-between gap-2">
					<SectionTitle>{row.terms_of_reference || row.name}</SectionTitle>
					<StateBadge state={row.status} />
				</div>
				<p className="mt-1 text-[11.5px] text-slate-body">{geoPath(row.geo_path)}</p>
				<p className="mt-0.5 text-[11.5px] text-slate-faint">
					{row.start_date ? formatDate(row.start_date) : "No start date"}
					{row.end_date ? ` → ${formatDate(row.end_date)}` : ""}
				</p>

				<div className="mt-3.5">
					{row.volunteers_required > 0 ? (
						<Meter
							label="Staffed"
							value={row.participant_count}
							total={row.volunteers_required}
							figure={
								<span className="text-[12px] font-semibold text-slate-body">
									{row.participant_count} of {row.volunteers_required}
								</span>
							}
							tint={row.participant_count >= row.volunteers_required ? "teal" : "amber"}
						/>
					) : (
						<p className="text-[12px] text-slate-body">
							{row.participant_count} on the deployment
							<span className="text-slate-faint"> · no headcount set</span>
						</p>
					)}
				</div>

				{waiting > 0 && (
					<p className="mt-2 text-[11.5px] font-semibold text-signal">
						{waiting} still to answer
					</p>
				)}
			</Link>
		</Card>
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
 * **The terms list is what this person wrote, and only the submitted ones.**
 * `terms.assert_offered` refuses a draft on the server — accepting an assignment
 * is accepting the wording, and wording that can still be edited is not wording
 * anybody can agree to — so offering a draft here and refusing it on submit
 * would be two answers to one question.
 *
 * **Choosing terms fills in the dates and the headcount.** A mission document
 * already says when it expects to run; making somebody retype that is how the
 * two come to disagree. Both stay editable, because the plan and the mission
 * are allowed to differ and the deployment's own dates are what govern.
 */
function DeploymentForm({ onCreated }: { onCreated: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [terms, setTerms] = useState("");
	const [startDate, setStartDate] = useState("");
	const [endDate, setEndDate] = useState("");
	const [required, setRequired] = useState("");
	const [notes, setNotes] = useState("");
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const available = useFrappeGetCall<{ message: { terms: TermsOfReference[] } }>(
		API.branchTerms,
		{ mine: 1, active_only: 1 },
		"admin:terms:for-deployment",
	);

	const options = (available.data?.message?.terms ?? []).filter((row) => row.is_offered);
	const node = selectedNode(chain);
	const ready = terms && startDate && endDate && node;

	const chooseTerms = (name: string) => {
		setTerms(name);

		const chosen = options.find((row) => row.name === name);

		if (!chosen) return;

		// Only fills what is still blank. A coordinator who has already typed a
		// date meant it, and having it overwritten by a picker is the kind of
		// small betrayal that makes people stop trusting a form.
		if (chosen.expected_start_date && !startDate) setStartDate(chosen.expected_start_date.slice(0, 10));
		if (chosen.expected_end_date && !endDate) setEndDate(chosen.expected_end_date.slice(0, 10));
	};

	const create = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.createDeployment, {
				terms_of_reference: terms,
				geo_node: node?.name,
				start_date: startDate,
				end_date: endDate,
				volunteers_required: required ? Number(required) : undefined,
				notes: notes.trim() || undefined,
			});
			setTerms("");
			setStartDate("");
			setEndDate("");
			setRequired("");
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
				Under a terms of reference that has been submitted. Volunteers are put on afterwards, either
				by placing them or by asking.
			</p>

			{options.length === 0 ? (
				<p className="mt-4 text-[12.5px] text-slate-faint">
					No submitted terms of reference yet. Write one under Terms of Reference and submit it
					first: a deployment is run against a mission, and a draft is not one anybody can be asked
					to agree to.
				</p>
			) : (
				<>
					<div className="mt-4 grid gap-4 sm:grid-cols-2">
						<Labelled label="Terms of reference" hint="The mission this deployment is run against.">
							<select
								className={INPUT}
								value={terms}
								onChange={(event) => chooseTerms(event.target.value)}
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

					<div className="mt-4 sm:w-1/2">
						<Labelled
							label="Volunteers needed"
							hint="Optional. Once this many are on it, the server refuses another — leave it empty and it is never full."
						>
							<input
								type="number"
								min="0"
								className={INPUT}
								value={required}
								onChange={(event) => setRequired(event.target.value)}
							/>
						</Labelled>
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

/**
 * One deployment: its mission, its leader, who is on it, what has happened, and
 * who could still be asked.
 *
 * **Everything about the deployment is on this page at once**, which is the
 * point of the screen. Somebody opening a running deployment wants to know what
 * is going on without navigating: the state, the staffing, the leader, the
 * roster split by what each person has said, and the account of what has
 * happened so far.
 */
/**
 * Creating a deployment, as a page of its own.
 *
 * The register still opens the same form inline — an existing habit worth
 * keeping — but the sub-navigation's "Create deployment" is a route, so the
 * flow can be linked to, bookmarked and returned to with the back button. Both
 * render one `DeploymentForm`; there is no second copy of the rules.
 */
export function DeploymentCreate() {
	const navigate = useNavigate();

	return (
		<>
			<PageHeading
				title="Create deployment"
				lead="A deployment is raised from a submitted terms of reference. Choose the mission first — the rest of the form follows from it."
				trail={[
					{ label: "Deployments", to: "/admin/deployments" },
					{ label: "Create deployment" },
				]}
			/>

			<DeploymentForm onCreated={() => navigate("/admin/deployments/ongoing")} />
		</>
	);
}

export function DeploymentDetail() {
	const { name = "" } = useParams<{ name: string }>();
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const { data, isLoading, mutate } = useFrappeGetCall<{ message: DeploymentDetailDto }>(
		API.getDeployment,
		{ name },
		`admin:deployment:${name}`,
	);

	const feed = useFrappeGetCall<{ message: DeploymentFeed }>(
		API.getDeploymentFeed,
		{ name },
		`admin:deployment:feed:${name}`,
	);

	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);
	const [matching, setMatching] = useState(false);

	const deployment = data?.message;

	const act = async (label: string, method: string, args: Record<string, unknown>) => {
		setBusy(label);
		setFailure(null);

		try {
			await call.post(method, args);
			await mutate();
			await feed.mutate();
		} catch (problem) {
			setFailure(errorMessage(problem));
		} finally {
			setBusy(null);
		}
	};

	if (isLoading) return <Spinner label="Loading deployment…" />;
	if (!deployment) return null;

	const trail: Crumb[] = [
		{ label: "Deployments", to: "/admin/deployments" },
		...(deployment.terms?.project
			? ([
					{
						label: deployment.terms.project_name ?? deployment.terms.project,
						to: `/admin/projects/${encodeURIComponent(deployment.terms.project)}`,
					},
				] as Crumb[])
			: ([{ label: "Deployments", to: "/admin/deployments/list" }] as Crumb[])),
		...(deployment.terms_of_reference
			? ([
					{
						label: deployment.terms?.tor_name ?? deployment.terms_of_reference,
						to: `/admin/deployments/terms/${encodeURIComponent(deployment.terms_of_reference)}`,
					},
				] as Crumb[])
			: []),
		{ label: deployment.name },
	];

	return (
		<>
			<PageHeading title={deployment.terms?.tor_name || deployment.name} trail={trail} />

			<div className="space-y-4">
				<Card>
					<div className="flex flex-wrap items-start justify-between gap-3">
						<div>
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

					<div className="mt-4 grid gap-4 sm:grid-cols-2">
						<Staffing deployment={deployment} />
						<Leadership deployment={deployment} />
					</div>

					{(deployment.terms?.required_certifications?.length ?? 0) > 0 && (
						<div className="mt-4">
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

					<div className="mt-4 flex flex-wrap gap-2 border-t border-hairline pt-3.5">
						{["Planned", "Active", "Completed", "Cancelled"]
							.filter((option) => option !== deployment.status)
							.map((option) => (
								<Button
									key={option}
									variant="quiet"
									disabled={busy !== null}
									onClick={() =>
										void act(option, API.setDeploymentStatus, { name, status: option })
									}
								>
									{busy === option ? "Working…" : `Mark ${option.toLowerCase()}`}
								</Button>
							))}
					</div>
				</Card>

				<Roster deployment={deployment} busy={busy} onAct={act} onFind={() => setMatching((was) => !was)} finding={matching} />

				{matching && (
					<CandidatePane
						deployment={deployment}
						onAssigned={() => {
							void mutate();
							void feed.mutate();
						}}
					/>
				)}

				<Feed
					deployment={deployment.name}
					answer={feed.data?.message}
					loading={feed.isLoading}
					onPosted={() => void feed.mutate()}
				/>
			</div>
		</>
	);
}

/** How many of the places this deployment asked for are taken. */
function Staffing({ deployment }: { deployment: DeploymentDetailDto }) {
	const counts = deployment.assignment_counts;

	return (
		<div>
			<p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-faint">Staffing</p>

			{deployment.volunteers_required > 0 ? (
				<div className="mt-2">
					<Meter
						label={deployment.places_left === 0 ? "Full" : `${deployment.places_left} still needed`}
						value={deployment.participant_count}
						total={deployment.volunteers_required}
						figure={
							<span className="text-[12px] font-semibold text-slate-body">
								{deployment.participant_count} of {deployment.volunteers_required}
							</span>
						}
						tint={deployment.places_left === 0 ? "teal" : "amber"}
					/>
				</div>
			) : (
				<p className="mt-2 text-[13px] font-semibold text-ink">
					{deployment.participant_count} on this deployment
					<span className="ml-1 text-[11.5px] font-normal text-slate-faint">
						· no headcount set, so it is never full
					</span>
				</p>
			)}

			<p className="mt-2 text-[11.5px] text-slate-faint">
				{counts?.Pending ?? 0} asked and waiting · {counts?.Declined ?? 0} declined ·{" "}
				{counts?.Withdrawn ?? 0} withdrawn
			</p>
		</div>
	);
}

/** Who leads this deployment in the field. */
function Leadership({ deployment }: { deployment: DeploymentDetailDto }) {
	const leader = deployment.participants.find((row) => row.is_leader && row.is_on_deployment);

	return (
		<div>
			<p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-faint">Leader</p>

			{leader ? (
				<div className="mt-2 flex items-center gap-2.5">
					<Avatar name={leader.full_name} photo={leader.photo} size={32} />
					<div>
						<p className="text-[13px] font-bold text-ink">{leader.full_name}</p>
						<p className="text-[11.5px] text-slate-faint">
							Updates and reports are addressed to them.
						</p>
					</div>
				</div>
			) : (
				<p className="mt-2 text-[12.5px] text-slate-faint">
					Nobody is leading this yet. Name one from the roster below — a deployment admits one, so
					that updates and reports have one person to be addressed to.
				</p>
			)}
		</div>
	);
}

/** The five statuses, grouped into the three things a coordinator does about them. */
const ROSTER_GROUPS = [
	{
		key: "going",
		title: "Going",
		statuses: ["Assigned", "Accepted"],
		lead: "On the deployment. These fill the places and these are whose time can be logged against it.",
	},
	{
		key: "asked",
		title: "Asked, waiting",
		statuses: ["Pending"],
		lead: "The question is in front of them. Nobody here holds a place yet.",
	},
	{
		key: "settled",
		title: "Not going",
		statuses: ["Declined", "Withdrawn"],
		lead: "Kept, never deleted — so the same person is not asked again next week having been forgotten.",
	},
] as const;

/**
 * Who is on this deployment, grouped by what each of them said.
 *
 * **Three groups rather than one list.** A flat roster with a status pill made
 * "who is actually coming" a thing a coordinator had to count by eye, and that
 * is the one number they need. Grouping also stops a declined row from looking
 * like a mistake: it is there on purpose, because a register that erased the
 * people who said no would have the same coordinator ask them again next week.
 */
function Roster({
	deployment,
	busy,
	onAct,
	onFind,
	finding,
}: {
	deployment: DeploymentDetailDto;
	busy: string | null;
	onAct: (label: string, method: string, args: Record<string, unknown>) => Promise<void>;
	onFind: () => void;
	finding: boolean;
}) {
	return (
		<Card>
			<div className="flex flex-wrap items-center justify-between gap-2">
				<SectionTitle>Roster ({deployment.participant_count})</SectionTitle>
				<Button onClick={onFind}>{finding ? "Close" : "Find volunteers"}</Button>
			</div>

			{deployment.participants.length === 0 ? (
				<p className="mt-2 text-[12.5px] text-slate-faint">
					Nobody on this deployment yet. Find volunteers who fit its terms above — you can place
					them, or ask them and let them answer.
				</p>
			) : (
				<div className="mt-4 space-y-5">
					{ROSTER_GROUPS.map((group) => {
						const rows = deployment.participants.filter((row) =>
							(group.statuses as readonly string[]).includes(row.status),
						);

						if (rows.length === 0) return null;

						return (
							<div key={group.key}>
								<p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-faint">
									{group.title} ({rows.length})
								</p>
								<p className="mt-0.5 text-[11.5px] text-slate-faint">{group.lead}</p>

								<ul className="mt-2 divide-y divide-hairline">
									{rows.map((row) => (
										<RosterEntry key={row.name} row={row} busy={busy} onAct={onAct} />
									))}
								</ul>
							</div>
						);
					})}
				</div>
			)}
		</Card>
	);
}

/** One person on the deployment, what they said, and the two acts open on them. */
function RosterEntry({
	row,
	busy,
	onAct,
}: {
	row: RosterRow;
	busy: string | null;
	onAct: (label: string, method: string, args: Record<string, unknown>) => Promise<void>;
}) {
	const tone =
		row.status === "Accepted"
			? "navy"
			: row.status === "Declined" || row.status === "Withdrawn"
				? "signal"
				: "page";

	return (
		<li className="flex flex-wrap items-center justify-between gap-3 py-3">
			<div className="flex min-w-0 items-center gap-2.5">
				<Avatar
					name={row.full_name}
					photo={row.photo}
					size={32}
					tone={row.is_leader ? "signal" : "navy"}
				/>
				<div className="min-w-0">
					<div className="flex flex-wrap items-center gap-1.5">
						<span className="text-[13px] font-semibold text-ink">{row.full_name}</span>
						{row.is_leader && row.is_on_deployment && <Pill tone="signal">Leader</Pill>}
					</div>
					<span className="text-[11.5px] text-slate-faint">
						{row.joined_on ? `joined ${formatDate(row.joined_on)}` : "no join date"}
						{row.left_on ? ` · left ${formatDate(row.left_on)}` : ""}
						{row.responded_on ? ` · answered ${formatDate(row.responded_on)}` : ""}
					</span>
					{row.response_note && (
						<p className="mt-0.5 text-[11.5px] italic text-slate-body">“{row.response_note}”</p>
					)}
				</div>
			</div>

			<div className="flex flex-wrap items-center gap-2">
				<Pill tone={tone}>{row.status}</Pill>

				{row.is_on_deployment && !row.is_leader && (
					<Button
						variant="quiet"
						disabled={busy !== null}
						onClick={() =>
							void onAct(`lead:${row.name}`, API.setAssignmentRole, {
								name: row.name,
								role: "leader",
							})
						}
					>
						{busy === `lead:${row.name}` ? "Naming…" : "Make leader"}
					</Button>
				)}

				{row.is_open && (
					<Button
						variant="quiet"
						disabled={busy !== null}
						onClick={() =>
							void onAct(`drop:${row.name}`, API.withdrawAssignment, { name: row.name })
						}
					>
						{busy === `drop:${row.name}` ? "Withdrawing…" : "Withdraw"}
					</Button>
				)}
			</div>
		</li>
	);
}

/* -------------------------------------------------------------- candidates */

/**
 * Who could go: a search over the register, bounded by the same scope as
 * everything else, ranked by the service, and truncated honestly.
 *
 * **Bounded before it is ranked, not after.** `find_candidates` only assesses
 * one page of the searcher's scope — see `matching.py`'s own docstring — so at
 * a branch or society with thousands of volunteers this stays fast by not
 * loading everyone first and filtering client-side. The search box, the skill
 * filter and the two toggles narrow the page fetched *before* certifications
 * are read.
 *
 * **Availability and clashes advise; they do not decide.** The server marks
 * each candidate free, not free, or unknown across the deployment's own days,
 * and names any other deployment of theirs that overlaps. Neither excludes
 * anybody by default: a register where hardly anybody has filled in a schedule
 * would otherwise read as a register where hardly anybody is free, and whether
 * somebody may serve on two things at once is a judgement about those two
 * things. The two toggles are how a coordinator who *has* decided says so.
 *
 * **Selection is bulk, and the two verbs stay apart.** Ticking people and
 * pressing one of two buttons is the whole interaction; the buttons are "Ask
 * them" and "Place them", because a coordinator who has already arranged it on
 * the phone is doing something different from one who is asking. The result is
 * a report, not a redirect: some of them will fail, and this says which.
 */
function CandidatePane({
	deployment,
	onAssigned,
}: {
	deployment: DeploymentDetailDto;
	onAssigned: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [searchInput, setSearchInput] = useState("");
	const [search, setSearch] = useState("");
	const [skills, setSkills] = useState<string[]>([]);
	const [onlyAvailable, setOnlyAvailable] = useState(false);
	const [excludeClashes, setExcludeClashes] = useState(false);
	const [picked, setPicked] = useState<Set<string>>(new Set());
	const [busy, setBusy] = useState<string | null>(null);
	const [outcome, setOutcome] = useState<AssignmentOutcome | null>(null);
	const [failure, setFailure] = useState<string | null>(null);

	// Debounced: a keystroke should narrow the search, not fire one request per
	// letter typed.
	useEffect(() => {
		const handle = setTimeout(() => setSearch(searchInput.trim()), 300);
		return () => clearTimeout(handle);
	}, [searchInput]);

	const vocabulary = useFrappeGetCall<{ message: ApplicationOptions }>(
		API.applicationOptions,
		undefined,
		"admin:application_options",
	);

	const { data, error, isLoading } = useFrappeGetCall<{ message: CandidateSearch }>(
		API.findCandidates,
		{
			terms_of_reference: deployment.terms_of_reference,
			geo_node: deployment.geo_node,
			as_of: deployment.start_date ?? undefined,
			start_date: deployment.start_date ?? undefined,
			end_date: deployment.end_date ?? undefined,
			only_available: onlyAvailable ? 1 : 0,
			exclude_conflicts: excludeClashes ? 1 : 0,
			limit: 25,
			search: search || undefined,
			skills: skills.length ? skills : undefined,
		},
		`admin:candidates:${deployment.name}:${search}:${skills.join()}:${onlyAvailable}:${excludeClashes}`,
	);

	const answer = data?.message;
	const rows = answer?.candidates ?? [];
	const onRoster = new Set(
		deployment.participants.filter((row) => row.is_open).map((row) => row.volunteer),
	);
	const selectable = rows.filter((row) => !onRoster.has(row.volunteer));
	const allPicked = selectable.length > 0 && selectable.every((row) => picked.has(row.volunteer));

	const toggle = (volunteer: string) =>
		setPicked((current) => {
			const next = new Set(current);
			next.has(volunteer) ? next.delete(volunteer) : next.add(volunteer);
			return next;
		});

	const assign = async (ask: boolean) => {
		setBusy(ask ? "ask" : "place");
		setFailure(null);
		setOutcome(null);

		try {
			const reply = await call.post<{ message: AssignmentOutcome }>(API.assignVolunteers, {
				name: deployment.name,
				volunteers: [...picked],
				ask: ask ? 1 : 0,
			});

			setOutcome(reply.message);
			setPicked(new Set());
			onAssigned();
		} catch (problem) {
			setFailure(errorMessage(problem, "Nobody was assigned."));
		} finally {
			setBusy(null);
		}
	};

	return (
		<Card>
			<SectionTitle>Volunteers who fit this mission</SectionTitle>
			<p className="mt-1 text-[12px] text-slate-faint">
				Deployable, holding what these terms require, and inside your own area. Whether they are free
				and whether they are already committed are shown, not enforced — unless you say so.
			</p>

			<div className="mt-3.5 grid gap-3 sm:grid-cols-2">
				<Labelled label="Search" hint="A name, or a volunteer's docname.">
					<input
						type="search"
						className={INPUT}
						value={searchInput}
						onChange={(event) => setSearchInput(event.target.value)}
						placeholder="Type a name…"
					/>
				</Labelled>
				<MultiCombo
					label="Skills"
					options={vocabulary.data?.message.skills ?? []}
					selected={skills}
					onToggle={(key) =>
						setSkills((current) =>
							current.includes(key) ? current.filter((value) => value !== key) : [...current, key],
						)
					}
				/>
			</div>

			<div className="mt-3 flex flex-wrap items-center gap-2">
				<Toggle
					on={onlyAvailable}
					onChange={setOnlyAvailable}
					label="Only those free on these days"
				/>
				<Toggle on={excludeClashes} onChange={setExcludeClashes} label="Hide clashes" />
			</div>

			{isLoading && <Spinner label="Matching…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{answer?.register_readable === false && (
				<Empty title="You cannot see the volunteer register">
					Staffing a deployment reads the register of volunteers, and that register is shown to
					whoever holds your society's volunteer role for the area. Your account runs deployments
					but has not been given that role, so there is nobody here to show — ask an administrator
					for it, and this panel fills in.
				</Empty>
			)}

			{answer && answer.register_readable !== false && (
				<p className="mb-3 mt-3 text-[11.5px] text-slate-faint">
					{answer.candidate_count} of this page's {answer.considered} volunteers matching your search
					are deployable and hold what these terms require
					{answer.as_of ? `, as of ${formatDate(answer.as_of)}` : ""}.
					{answer.truncated &&
						" There are more than shown here — narrow the search or the skill filter to see others."}
				</p>
			)}

			{outcome && <Outcome outcome={outcome} onClose={() => setOutcome(null)} />}
			{failure && (
				<div className="mb-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			{answer && answer.register_readable !== false && rows.length === 0 && (
				<Empty title="Nobody matches yet">
					No volunteer on this page is both deployable and holds every certification these terms
					require. Narrow or clear the search, loosen the two toggles, or widen the terms.
				</Empty>
			)}

			{rows.length > 0 && (
				<>
					<div className="flex items-center justify-between gap-3 border-y border-hairline py-2.5">
						<label className="flex cursor-pointer items-center gap-2 text-[12px] font-semibold text-slate-body">
							<input
								type="checkbox"
								className="h-4 w-4 accent-navy"
								checked={allPicked}
								onChange={() =>
									setPicked(
										allPicked ? new Set() : new Set(selectable.map((row) => row.volunteer)),
									)
								}
							/>
							Select all on this page
						</label>
						<span className="text-[11.5px] text-slate-faint">
							{picked.size} selected
						</span>
					</div>

					<ul className="divide-y divide-hairline">
						{rows.map((person) => (
							<CandidateRow
								key={person.volunteer}
								person={person}
								already={onRoster.has(person.volunteer)}
								picked={picked.has(person.volunteer)}
								onToggle={() => toggle(person.volunteer)}
							/>
						))}
					</ul>

					{/* The negative margins match `Card`'s own `p-5 sm:p-6`, so the bar
					    spans the card's full width and its inner padding lines the
					    buttons up with everything above them. Sticky, because a page of
					    twenty-five candidates puts the buttons below the fold exactly
					    when somebody has finished choosing. */}
					<div className="sticky bottom-0 -mx-5 mt-1 flex flex-wrap items-center gap-2 border-t border-hairline bg-white/95 px-5 py-3 backdrop-blur sm:-mx-6 sm:px-6">
						<Button disabled={busy !== null || picked.size === 0} onClick={() => void assign(true)}>
							{busy === "ask" ? "Asking…" : `Ask ${picked.size || ""}`.trim()}
						</Button>
						<Button
							variant="quiet"
							disabled={busy !== null || picked.size === 0}
							onClick={() => void assign(false)}
						>
							{busy === "place" ? "Placing…" : `Place ${picked.size || ""}`.trim()}
						</Button>
						<p className="text-[11.5px] text-slate-faint">
							Asking sends each person a question they answer. Placing records that they are
							going, which is what you want when it was already arranged.
						</p>
					</div>
				</>
			)}
		</Card>
	);
}

function Toggle({
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
					? "border-navy bg-navy text-white"
					: "border-hairline-strong bg-white text-slate-body hover:border-navy hover:text-navy",
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
function Outcome({ outcome, onClose }: { outcome: AssignmentOutcome; onClose: () => void }) {
	return (
		<div className="mb-4 rounded-card border border-hairline-strong bg-surface px-4 py-3.5">
			<div className="flex items-start justify-between gap-3">
				<p className="text-[13px] font-bold text-ink">
					{outcome.raised} of {outcome.requested} assigned
					{outcome.refused > 0 ? `, ${outcome.refused} not` : ""}
				</p>
				<button
					type="button"
					onClick={onClose}
					className="text-[11.5px] font-semibold text-slate-faint hover:text-navy"
				>
					Dismiss
				</button>
			</div>

			{outcome.failure.length > 0 && (
				<ul className="mt-2.5 space-y-1.5">
					{outcome.failure.map((row) => (
						<li key={row.volunteer} className="text-[12px] text-slate-body">
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
function CandidateRow({
	person,
	already,
	picked,
	onToggle,
}: {
	person: Candidate;
	already: boolean;
	picked: boolean;
	onToggle: () => void;
}) {
	return (
		<li className={cx("flex flex-wrap items-center gap-3 py-3", already && "opacity-60")}>
			<input
				type="checkbox"
				className="h-4 w-4 flex-none accent-navy"
				checked={picked}
				disabled={already}
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
function AvailabilityPill({ person }: { person: Candidate }) {
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
function CandidateCard({ person }: { person: Candidate }) {
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

			<dl className="mt-3 grid grid-cols-2 gap-2 border-t border-hairline pt-3 text-[11.5px]">
				<div>
					<dt className="text-slate-faint">Deployments</dt>
					<dd className="text-[15px] font-bold text-navy">
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
							<li key={row.name} className="truncate text-[11.5px] text-slate-body">
								{row.terms_of_reference || row.name}
								{row.start_date ? ` · ${formatDate(row.start_date)}` : ""}
							</li>
						))}
					</ul>
				</div>
			)}

			<p className="mt-2.5 border-t border-hairline pt-2 text-[11.5px] text-slate-body">
				{person.availability.why}
			</p>

			{person.clash.is_clashing && (
				<p className="mt-1.5 text-[11.5px] font-semibold text-signal">
					Already committed to {person.clash.deployments.map((row) => row.deployment).join(", ")}{" "}
					over these dates.
				</p>
			)}
		</div>
	);
}

/* -------------------------------------------------------------------- feed */

/**
 * What has happened on this deployment, in order.
 *
 * **Two sources, one list, and they stay distinguishable.** The deployment's
 * own log — notes, milestones, concerns, and the entries the server writes when
 * the status moves or somebody joins or leaves — merged at read time with the
 * task reports volunteers filed against tasks on this deployment. Merged rather
 * than copied, so there is one record of each report and it stays with the task
 * it belongs to. A coordinator reading "arrived at the camp" wants to know
 * whether that is the deployment's log or somebody's report, because the answer
 * changes who they would ask about it.
 */
function Feed({
	deployment,
	answer,
	loading,
	onPosted,
}: {
	deployment: string;
	answer?: DeploymentFeed;
	loading: boolean;
	onPosted: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [note, setNote] = useState("");
	const [kind, setKind] = useState("update");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const post = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.postDeploymentUpdate, {
				name: deployment,
				note: note.trim(),
				entry_type: kind,
			});
			setNote("");
			onPosted();
		} catch (problem) {
			setFailure(errorMessage(problem, "That update was not posted."));
		} finally {
			setBusy(false);
		}
	};

	const entries = answer?.entries ?? [];

	return (
		<Card>
			<SectionTitle>What has happened</SectionTitle>
			<p className="mt-1 text-[12px] text-slate-faint">
				This deployment's own log, and the task reports volunteers have filed against it.
			</p>

			<div className="mt-3.5 rounded-card border border-hairline bg-surface p-3">
				<textarea
					className={cx(INPUT, "min-h-[64px] resize-y bg-white")}
					value={note}
					onChange={(event) => setNote(event.target.value)}
					placeholder="What is going on?"
				/>

				<div className="mt-2.5 flex flex-wrap items-center gap-2">
					{[
						["update", "Update"],
						["milestone", "Milestone"],
						["concern", "Concern"],
					].map(([value, label]) => (
						<button
							key={value}
							type="button"
							onClick={() => setKind(value)}
							className={cx(
								"rounded-full border px-3 py-1 text-[11.5px] font-semibold transition",
								kind === value
									? "border-navy bg-navy text-white"
									: "border-hairline-strong bg-white text-slate-body hover:border-navy",
							)}
						>
							{label}
						</button>
					))}

					<div className="ml-auto">
						<Button disabled={busy || !note.trim()} onClick={() => void post()}>
							{busy ? "Posting…" : "Post"}
						</Button>
					</div>
				</div>

				{failure && (
					<div className="mt-2.5">
						<ErrorNote>{failure}</ErrorNote>
					</div>
				)}
			</div>

			{loading && <Spinner label="Loading the feed…" />}

			{!loading && entries.length === 0 && (
				<p className="mt-4 text-[12.5px] text-slate-faint">
					Nothing has been recorded yet. Status changes and roster changes write themselves in as
					they happen, so this fills up on its own once the deployment is running.
				</p>
			)}

			{entries.length > 0 && (
				<ol className="mt-4 space-y-0">
					{entries.map((entry, index) => (
						<FeedRow key={`${entry.source}-${entry.posted_on}-${index}`} entry={entry} />
					))}
				</ol>
			)}

			{answer?.truncated && (
				<p className="mt-3 text-[11.5px] text-slate-faint">
					Showing the most recent {entries.length} of {answer.count}.
				</p>
			)}
		</Card>
	);
}

/** The tone each kind of entry is drawn in. Display only; nothing branches on it. */
const ENTRY_TONES: Record<string, string> = {
	concern: "border-signal bg-signal",
	milestone: "border-navy bg-navy",
	status: "border-hairline-strong bg-slate-faint",
	roster: "border-hairline-strong bg-slate-faint",
};

function FeedRow({ entry }: { entry: FeedEntry }) {
	const dot = ENTRY_TONES[entry.entry_type] ?? "border-hairline-strong bg-hairline-strong";

	return (
		<li className="group relative flex gap-3 pb-4 pl-1 last:pb-0">
			{/* The rail, drawn per row rather than as one element behind the list,
			    so a row can be added or removed without anything measuring. It is
			    `group-last:hidden` rather than `last:hidden`: the span is always the
			    first child of its own row, so `last:` would never match — what has
			    to be last is the row, and `group` on the row is how a child asks
			    about it. */}
			<span
				aria-hidden="true"
				className="absolute bottom-0 left-[7px] top-4 w-px bg-hairline group-last:hidden"
			/>
			<span
				aria-hidden="true"
				className={cx("relative z-10 mt-1.5 h-[9px] w-[9px] flex-none rounded-full border", dot)}
			/>

			<div className="min-w-0 flex-1">
				<div className="flex flex-wrap items-baseline gap-x-2">
					<span className="text-[12.5px] font-semibold text-ink">
						{entry.author_name ?? entry.author}
					</span>
					<span className="text-[11px] uppercase tracking-wide text-slate-faint">
						{entry.entry_type}
					</span>
					{entry.source === "task" && <Pill tone="quiet">Task report</Pill>}
					<span className="ml-auto text-[11px] text-slate-faint">
						{entry.posted_on ? formatDate(entry.posted_on) : ""}
					</span>
				</div>

				{entry.subject && (
					<p className="mt-0.5 text-[11.5px] font-semibold text-slate-body">{entry.subject}</p>
				)}

				{entry.note && (
					<p className="mt-1 whitespace-pre-line text-[12.5px] text-slate-body">{entry.note}</p>
				)}

				{entry.proof && (
					<img
						src={entry.proof}
						alt=""
						className="mt-2 max-h-48 rounded-card border border-hairline object-cover"
					/>
				)}
			</div>
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
export function RequestList() {
	const { data, error, isLoading } = useFrappeGetCall<{
		message: { count: number; requests: DeploymentRequestRow[] };
	}>(API.branchRequests, undefined, "admin:deployment_requests");

	const rows = data?.message?.requests ?? [];

	return (
		<>
			<PageHeading
				title="Requests"
				trail={[{ label: "Deployments", to: "/admin/deployments" }, { label: "Requests" }]}
			/>

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
								{row.is_fulfilled && row.deployment && (
									<Link
										to={`/admin/deployments/${encodeURIComponent(row.deployment)}`}
										className="rounded-full bg-signal/10 px-3 py-1 text-[11px] font-semibold text-signal hover:underline"
									>
										Deployment {row.deployment}
									</Link>
								)}
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
