import { useContext, useEffect, useState, type ReactNode } from "react";
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
	DeploymentRequestRow,
	DeploymentSite,
	DeploymentSites,
	DeploymentSummary,
	OperationsDocumentsAnswer,
	OperationsSummary,
	FeedEntry,
	GeoNode,
	RosterRow,
	TermsOfReference,
} from "../portal/types";
import { INPUT, Labelled, MineToggle } from "./Projects";
import { GeoSelects, selectedNode } from "../ui/GeoSelects";
import { MultiCombo } from "../ui/form";
import { MapLegend, OperationsMap } from "./OperationsMap";
import { HoverCard } from "../ui/HoverCard";
import {
	Avatar,
	Button,
	ButtonLink,
	Card,
	type Crumb,
	Empty,
	ErrorNote,
	Cell,
	Meter,
	PageHeading,
	Pill,
	Row,
	SectionLabel,
	SectionLink,
	SectionTitle,
	Skeleton,
	Spinner,
	StatGrid,
	StatTile,
	StateBadge,
	Table,
	cx,
} from "../ui/primitives";
import { Icon } from "../ui/icons";
import { exceptionsFor } from "./counts";

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
 * The operations command centre: what is running, where it is, and what needs
 * intervention.
 *
 * **Every figure here is a scoped server aggregate.** The previous version
 * derived its tiles from one capped page of `branch_deployments` and carried a
 * footnote saying so; a footnote is not a fix, because the number is read and
 * the footnote is not. `operations_summary` counts across the whole of the
 * caller's scope inside `frappe.get_list`, and says `capped` when even that hit
 * its ceiling — at which point this screen calls the figures a floor rather than
 * a total.
 *
 * **The map is of deployments, not of areas.** `deployment_sites` returns each
 * readable deployment with the coordinates on its own record, so a pin can be
 * selected and the panel beside it can show the mission picture: the terms, the
 * coordinator, the two places, the control times, the readiness of the roster.
 * Deployments nobody has located are counted in `unplotted` and named in the
 * list, never dropped.
 *
 * **The status filters name the doctype's own six.** Suspended and Closed Out
 * are among them, which they were not before: a filter that silently returned
 * nothing for a real value is worse than no filter, because an empty list reads
 * as "there are none".
 */
export function DeploymentsHub() {
	// One of the six statuses, or "" for the whole ongoing band. Held here and
	// passed to both the map and its list, so the pins and the text agree.
	const [status, setStatus] = useState("");
	const [selected, setSelected] = useState<string | null>(null);

	const summary = useFrappeGetCall<{ message: OperationsSummary }>(
		API.operationsSummary,
		undefined,
		"admin:operations:summary",
	);

	const sites = useFrappeGetCall<{ message: DeploymentSites }>(
		API.deploymentSites,
		status ? { status } : undefined,
		`admin:operations:sites:${status}`,
	);

	// The live operations list is the ongoing band itself, asked for as a set of
	// statuses rather than sieved out of an unfiltered page.
	const ongoing = useFrappeGetCall<{
		message: { count: number; total: number; deployments: DeploymentSummary[]; open_count: number };
	}>(
		API.branchDeployments,
		{ statuses: ONGOING_STATUSES, mine: 0 },
		"admin:operations:ongoing",
	);

	const figures = summary.data?.message;
	const map = sites.data?.message;
	const rows = map?.deployments ?? [];
	const live = ongoing.data?.message?.deployments ?? [];

	// The chosen deployment, or the first one that can be drawn. Resolved on
	// every render rather than stored, so a filter change that removes the
	// selection falls back rather than leaving the panel describing something
	// no longer on the map.
	const current =
		rows.find((row) => row.name === selected) ?? rows.find((row) => row.where.site.has_point) ?? null;

	const exceptions = exceptionsFor(live);

	return (
		<>
			<PageHeading
				title={<EditableText k="admin.deployments.dashboard" fallback="Operations overview" />}
				lead="Plan approved work, mobilise volunteers, and keep every running deployment under control."
				actions={
					<div className="flex flex-wrap gap-2">
						<ButtonLink to="/admin/deployments/terms">Review terms</ButtonLink>
						<ButtonLink to="/admin/deployments/new">Create deployment</ButtonLink>
					</div>
				}
			/>

			{(summary.error || sites.error || ongoing.error) && (
				<div className="mb-5">
					<ErrorNote>
						{errorMessage(summary.error || sites.error || ongoing.error)}
					</ErrorNote>
				</div>
			)}

			{/* ------------------------------------------------------ metric cards */}
			<StatGrid className="mb-5">
				<StatTile
					label="Ongoing deployments"
					value={summary.isLoading ? "—" : (figures?.ongoing ?? "—")}
					hint={
						figures
							? `${figures.people} ${figures.people === 1 ? "person" : "people"} currently assigned`
							: "Planned, active, suspended and closing out"
					}
					icon={Icon.people}
					tint="navy"
					to="/admin/deployments/ongoing"
				/>
				<StatTile
					label={`Starting in ${figures?.starting_soon_days ?? 14} days`}
					value={summary.isLoading ? "—" : (figures?.starting_soon ?? "—")}
					hint={
						figures && figures.unfilled_soon > 0
							? `${figures.unfilled_soon} ${figures.unfilled_soon === 1 ? "role" : "roles"} still unfilled`
							: "Every role filled"
					}
					icon={Icon.calendar}
					tint="sky"
					to="/admin/deployments/ongoing"
				/>
				<StatTile
					label="Invitations unanswered"
					value={summary.isLoading ? "—" : (figures?.pending ?? "—")}
					hint={
						figures && figures.pending > 0
							? "Asked, and nobody has replied yet"
							: "Nobody is waiting"
					}
					icon={Icon.hourglass}
					tint="amber"
				/>
				<StatTile
					label="Requests awaiting an outcome"
					value={summary.isLoading ? "—" : (figures?.requests_open ?? "—")}
					hint={
						figures?.requests === null
							? "Not in your permissions"
							: figures
								? `${figures.requests} in your area in total`
								: "Asks for volunteers against a terms of reference"
					}
					icon={Icon.inbox}
					tint="teal"
					to="/admin/deployments/requests"
				/>
			</StatGrid>

			{figures?.capped && (
				<p className="mb-5 -mt-2 text-[11px] leading-relaxed text-muted">
					Your scope holds more ongoing deployments than one request can total exactly, so these
					figures are a floor rather than a count.
				</p>
			)}

			{/* ---------------------------------------------------------- the map */}
			<Card pad={false} className="mb-5">
				<div className="flex flex-wrap items-start justify-between gap-3 border-b border-card-line px-5 py-4">
					<div>
						<SectionTitle>Deployment map</SectionTitle>
						<p className="mt-0.5 text-[11.5px] text-muted">
							Operational sites read from each deployment's own coordinates. Choose one for the
							mission picture.
						</p>
					</div>

					<StatusFilters current={status} onChange={(next) => { setStatus(next); setSelected(null); }} />
				</div>

				{sites.isLoading && (
					<div className="p-5">
						<Skeleton className="h-64" />
					</div>
				)}

				{!sites.isLoading && rows.length === 0 && (
					<div className="p-5">
						<Empty title="Nothing to plot">
							No deployment in your area matches this filter. Clear it, or raise one under
							Requests.
						</Empty>
					</div>
				)}

				{rows.length > 0 && (
					// `min-w-0` on both tracks, and it is load-bearing rather than
					// defensive: a grid item's `min-width` is `auto`, so a child
					// whose min-content is wide — a terms-of-reference key like
					// `safe_water_and_sanitation_support`, which has no break
					// opportunity in it — widens the whole column and the page
					// scrolls sideways on a phone. `truncate` cannot help until an
					// ancestor is allowed to be narrower than its content.
					<div className="grid items-start gap-4 p-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
						<div className="min-w-0">
							{/* The canvas draws nothing when nothing can be drawn, and an
							    empty gap where a map should be reads as a map that failed
							    to load. This says which it is, and what would fix it —
							    the coordinates are on each deployment's own record, and
							    a tree of operational sites is filled in over months. */}
							{(map?.plotted ?? 0) > 0 ? (
								<OperationsMap
									deployments={rows}
									selected={current?.name ?? null}
									onSelect={setSelected}
								/>
							) : (
								<div className="grid h-[380px] w-full place-items-center rounded-xl border border-dashed border-card-line bg-surface px-6 text-center">
									<div className="max-w-sm">
										<p className="text-[13px] font-semibold text-ink">
											Nothing here can be put on a map yet
										</p>
										<p className="mt-1.5 text-[12px] leading-relaxed text-muted">
											None of the {rows.length} deployment
											{rows.length === 1 ? "" : "s"} below carries a location. Add a
											deployment point to one — or let its address be looked up — and
											it appears here. Everything is still listed underneath.
										</p>
									</div>
								</div>
							)}

							<div className="mt-3 flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
								<MapLegend statuses={DEPLOYMENT_STATUSES} />
								<span className="text-[11px] text-muted">
									{map?.plotted ?? 0} plotted
									{(map?.unplotted ?? 0) > 0 && ` · ${map?.unplotted} without coordinates`}
								</span>
							</div>

							{/* The accessible equivalent of the map, and the keyboard
							    control for it: the canvas is aria-hidden because a
							    Leaflet map cannot be operated by keyboard, so every
							    deployment it draws — and every one it cannot — is a
							    real button here. */}
							<SiteList rows={rows} selected={current?.name ?? null} onSelect={setSelected} />
						</div>

						<div className="min-w-0">
							<SelectedDeployment row={current} />
						</div>
					</div>
				)}
			</Card>

			{/* -------------------------------------------- live operations + attention */}
			<div className="mb-5 grid items-start gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
				<Card pad={false} className="min-w-0">
					<div className="flex flex-wrap items-start justify-between gap-3 px-5 pb-3 pt-4">
						<div className="min-w-0">
							<SectionTitle>Live operations</SectionTitle>
							<p className="mt-0.5 text-[11.5px] text-muted">
								What is running, and what needs intervention.
							</p>
						</div>
						<SectionLink to="/admin/deployments/ongoing">View all</SectionLink>
					</div>

					{ongoing.isLoading && (
						<div className="px-5 pb-5">
							<Skeleton className="h-28" />
						</div>
					)}

					{!ongoing.isLoading && live.length === 0 && (
						<div className="px-5 pb-5">
							<Empty title="Nothing is running">
								No deployment in your area is planned, active, suspended or closing out.
							</Empty>
						</div>
					)}

					{live.length > 0 && (
						<ul className="divide-y divide-card-line border-t border-card-line">
							{live.slice(0, 6).map((row) => (
								<li key={row.name}>
									<OperationRow row={row} />
								</li>
							))}
						</ul>
					)}
				</Card>

				<Card pad={false} className="min-w-0">
					<div className="px-5 pb-3 pt-4">
						<SectionTitle>Operations attention</SectionTitle>
						<p className="mt-0.5 text-[11.5px] text-muted">
							Across terms, requests and the rosters themselves.
						</p>
					</div>

					<ul className="divide-y divide-card-line border-t border-card-line">
						<AttentionLink
							to="/admin/deployments/terms"
							tag="TOR"
							title={
								figures?.terms_awaiting
									? `${figures.terms_awaiting} terms awaiting approval`
									: figures?.terms === null
										? "Terms of reference are not in your permissions"
										: "No terms awaiting approval"
							}
							lead={
								figures?.terms === null
									? "Ask an administrator if you need to read them"
									: `${figures?.terms ?? 0} readable in your area`
							}
						/>
						<AttentionLink
							to="/admin/deployments/requests"
							tag="REQ"
							title={
								figures?.requests_open
									? `${figures.requests_open} requests awaiting an outcome`
									: figures?.requests === null
										? "Deployment requests are not in your permissions"
										: "No requests awaiting an outcome"
							}
							lead="Asks for volunteers against a terms of reference"
						/>
						<AttentionLink
							to="/admin/deployments/ongoing"
							tag="ROS"
							title={
								figures?.pending
									? `${figures.pending} invitations unanswered`
									: "Every invitation has been answered"
							}
							lead="Asked, with no reply yet"
						/>
						<AttentionLink
							to="/admin/deployments/documents"
							tag="DOC"
							title={
								figures?.closing_out
									? `${figures.closing_out} deployments in close-out`
									: "Nothing waiting on close-out"
							}
							lead="Completed, with the paperwork still to file"
						/>
					</ul>

					{exceptions.length > 0 && (
						<div className="border-t border-card-line px-4 py-3">
							<ul className="space-y-1">
								{exceptions.slice(0, 4).map((item, index) => (
									<li key={`${item.row.name}-${index}`}>
										<Link
											to={`/admin/deployments/${encodeURIComponent(item.row.name)}`}
											className="block rounded-lg px-3 py-2 transition hover:bg-surface"
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
												{/* A dot as well as the colour: a state is
												    never a hue alone. */}
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
					)}
				</Card>
			</div>

			<ReadinessStrip rows={live} loading={ongoing.isLoading} />
		</>
	);
}

/**
 * The doctype's own six statuses, named once for the filter and the legend.
 *
 * Code, not society configuration: `deployment/services/deployment.py` owns this
 * set and no society may add a seventh. Very much unlike an approval stage,
 * which is configuration and is compared nowhere in this app.
 */
const DEPLOYMENT_STATUSES = [
	"Planned",
	"Active",
	"Suspended",
	"Completed",
	"Closed Out",
	"Cancelled",
];

/** What "ongoing" means, matching `api/deployment.py::ONGOING_STATUSES` exactly. */
const ONGOING_STATUSES = ["Planned", "Active", "Suspended", "Completed"];

/** The map's status filter. Every one of the six, plus the whole ongoing band. */
function StatusFilters({
	current,
	onChange,
}: {
	current: string;
	onChange: (status: string) => void;
}) {
	return (
		<div role="group" aria-label="Filter the map by status" className="flex flex-wrap gap-1.5">
			{["", ...DEPLOYMENT_STATUSES].map((status) => (
				<button
					key={status || "ongoing"}
					type="button"
					onClick={() => onChange(status)}
					aria-pressed={current === status}
					className={cx(
						"rounded-full border px-3 py-1.5 text-[11.5px] font-semibold transition",
						current === status
							? "border-blue bg-blue-soft text-blue-press"
							: "border-card-line bg-white text-slate-strong hover:border-blue hover:text-ink",
					)}
				>
					{status || "Ongoing"}
				</button>
			))}
		</div>
	);
}

/**
 * Every deployment the map holds, as text.
 *
 * The accessible equivalent of the canvas, and the keyboard control for it —
 * which is why the ones that cannot be plotted are here too, marked as such. A
 * map that showed eight pins and a list of eight would leave the three
 * unlocated deployments invisible on both.
 */
function SiteList({
	rows,
	selected,
	onSelect,
}: {
	rows: DeploymentSite[];
	selected: string | null;
	onSelect: (name: string) => void;
}) {
	return (
		<div className="mt-3 max-h-56 overflow-y-auto rounded-xl border border-card-line">
			<ul className="divide-y divide-card-line">
				{rows.map((row) => {
					const located = row.where.site.has_point;

					return (
						<li key={row.name}>
							<button
								type="button"
								onClick={() => onSelect(row.name)}
								aria-current={row.name === selected ? "true" : undefined}
								className={cx(
									"flex w-full items-center gap-3 px-3.5 py-2.5 text-left transition",
									row.name === selected ? "bg-blue-soft" : "hover:bg-surface",
								)}
							>
								<span className="min-w-0 flex-1">
									<span className="block truncate text-[12.5px] font-semibold text-ink">
										{row.terms_of_reference || row.name}
									</span>
									<span className="mt-0.5 block truncate text-[11px] text-muted">
										{geoPath(row.geo_path)}
										{!located && " · no coordinates yet"}
									</span>
								</span>
								<span className="flex-none">
									<StateBadge state={row.status} />
								</span>
								<span className="tabular flex-none text-[11.5px] font-semibold text-muted">
									{row.participant_count}
								</span>
							</button>
						</li>
					);
				})}
			</ul>
		</div>
	);
}

/**
 * The selected deployment, in the detail a coordinator opens a map for.
 *
 * Every value is off the DTO the server built — the terms, the geo path, the
 * coordinator, the planned period, the two places, the local contact, the
 * readiness counts and the three control times. Nothing is derived here, so this
 * panel and the deployment's own page cannot describe it differently.
 */
function SelectedDeployment({ row }: { row: DeploymentSite | null }) {
	if (!row) {
		return (
			<Card className="h-full">
				<SectionTitle>Select a deployment</SectionTitle>
				<p className="mt-1.5 text-[12px] leading-relaxed text-muted">
					Choose one from the map or the list to inspect its site, schedule, coordinator, roster
					and readiness.
				</p>
			</Card>
		);
	}

	const site = row.where.site;
	const meeting = row.where.meeting_point;
	const contact = row.where.local_contact;
	const required = row.volunteers_required || 0;

	return (
		<Card className="h-full">
			<div className="flex flex-wrap items-start justify-between gap-2">
				<div className="min-w-0">
					<SectionTitle>{row.terms_of_reference || row.name}</SectionTitle>
					<p className="tabular mt-0.5 font-mono text-[11px] text-slate-faint">{row.name}</p>
				</div>
				<StateBadge state={row.status} />
			</div>

			<p className="mt-1.5 text-[11.5px] text-muted">{geoPath(row.geo_path)}</p>

			<div className="mt-3 flex flex-wrap gap-2">
				{site.map && (
					<a
						href={site.map}
						target="_blank"
						rel="noreferrer"
						className="rounded-full border border-card-line px-3 py-1.5 text-[11.5px] font-semibold text-slate-strong transition hover:border-blue hover:text-blue-press"
					>
						Open map ↗
					</a>
				)}
				{site.directions && (
					<a
						href={site.directions}
						target="_blank"
						rel="noreferrer"
						className="rounded-full border border-card-line px-3 py-1.5 text-[11.5px] font-semibold text-slate-strong transition hover:border-blue hover:text-blue-press"
					>
						Directions ↗
					</a>
				)}
			</div>

			<PanelSection title="Deployment">
				<PanelFact label="Terms of Reference" value={row.terms_of_reference} />
				<PanelFact
					label="Coordinator"
					value={row.coordinator_contact.full_name || row.coordinator_contact.user}
				/>
				<PanelFact label="Planned start" value={formatDate(row.planned_start ?? row.start_date)} />
				<PanelFact label="Planned end" value={formatDate(row.planned_end ?? row.end_date)} />
			</PanelSection>

			<PanelSection title="Places">
				<PanelFact
					label="Deployment point"
					value={site.name}
					detail={site.address ?? (site.has_point ? null : "No coordinates recorded yet")}
				/>
				<PanelFact label="Meeting point" value={meeting.name} detail={meeting.address} />
				<PanelFact label="Local contact" value={contact.name} detail={contact.phone} />
			</PanelSection>

			<PanelSection title="Readiness">
				<Meter
					label="On the deployment"
					value={row.participant_count}
					total={required || row.participant_count || 1}
					figure={
						<span className="text-[11.5px] font-semibold text-muted">
							{/* No requirement set is not the same as being full, so the
							    figure says which case this is rather than dividing by a
							    number the society never gave. */}
							{required
								? `${row.participant_count} of ${required}`
								: `${row.participant_count} assigned`}
						</span>
					}
					tint={required && row.participant_count >= required ? "teal" : "amber"}
				/>

				<div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
					<MiniFigure label="Unanswered" value={row.assignment_counts?.Pending ?? 0} />
					<MiniFigure label="Leaders" value={row.readiness.leaders} />
					<MiniFigure label="Briefed" value={row.readiness.briefed} />
					<MiniFigure label="Checked in" value={row.readiness.checked_in} />
				</div>
			</PanelSection>

			<PanelSection title="Control times">
				<PanelFact label="Briefing" value={formatDate(row.briefing_on)} />
				<PanelFact label="Check-in deadline" value={formatDate(row.check_in_deadline)} />
				<PanelFact label="Expected return" value={formatDate(row.expected_return)} />
			</PanelSection>

			{row.where.travel_notes && (
				<PanelSection title="Travel notes">
					<p className="whitespace-pre-line text-[12px] leading-relaxed text-slate-strong">
						{row.where.travel_notes}
					</p>
				</PanelSection>
			)}

			<Link
				to={`/admin/deployments/${encodeURIComponent(row.name)}`}
				className="mt-4 block border-t border-card-line pt-3 text-[12.5px] font-semibold text-blue-press hover:underline"
			>
				Open full deployment record →
			</Link>
		</Card>
	);
}

function PanelSection({ title, children }: { title: string; children: ReactNode }) {
	return (
		<section className="mt-4 border-t border-card-line pt-3">
			<h4 className="mb-2 text-[10.5px] font-bold uppercase tracking-[0.08em] text-muted">
				{title}
			</h4>
			{children}
		</section>
	);
}

/** One fact, drawn as absent when it is. */
function PanelFact({
	label,
	value,
	detail,
}: {
	label: string;
	value?: string | null;
	detail?: string | null;
}) {
	return (
		<div className="flex items-baseline justify-between gap-3 py-0.5">
			<span className="flex-none text-[11.5px] text-muted">{label}</span>
			<span className="min-w-0 text-right">
				<span className="block truncate text-[12px] font-semibold text-ink">{value || "—"}</span>
				{detail && <span className="block truncate text-[11px] text-slate-faint">{detail}</span>}
			</span>
		</div>
	);
}

function MiniFigure({ label, value }: { label: string; value: number }) {
	return (
		<div className="rounded-lg bg-surface px-2.5 py-2">
			<div className="text-[10px] uppercase tracking-[0.06em] text-muted">{label}</div>
			<div className="tabular mt-0.5 text-[15px] font-semibold text-ink">{value}</div>
		</div>
	);
}

/** One running deployment, as a row on the live list. */
function OperationRow({ row }: { row: DeploymentSummary }) {
	const pending = row.assignment_counts?.Pending ?? 0;
	const required = row.volunteers_required || 0;

	return (
		<Link
			to={`/admin/deployments/${encodeURIComponent(row.name)}`}
			className="flex items-center gap-3 px-5 py-3 transition hover:bg-surface"
		>
			<span className="flex-none">
				<StateBadge state={row.status} />
			</span>

			<span className="min-w-0 flex-1">
				<span className="block truncate text-[13px] font-semibold text-ink">
					{row.terms_of_reference || row.name}
				</span>
				<span className="mt-0.5 block truncate text-[11.5px] text-muted">
					{geoPath(row.geo_path)}
					{row.start_date ? ` · from ${formatDate(row.start_date)}` : ""}
				</span>
			</span>

			<span className="hidden flex-none text-right sm:block">
				<span className="block text-[10.5px] uppercase tracking-[0.06em] text-muted">
					{required ? "Filled" : "People"}
				</span>
				<span className="tabular block text-[12.5px] font-semibold text-ink">
					{required ? `${row.participant_count} / ${required}` : row.participant_count}
				</span>
			</span>

			<span className="flex-none text-right">
				<span className="block text-[10.5px] uppercase tracking-[0.06em] text-muted">
					Responses
				</span>
				<span
					className={cx(
						"tabular block text-[12.5px] font-semibold",
						pending > 0 ? "text-warning" : "text-ink",
					)}
				>
					{pending > 0 ? `${pending} pending` : "All in"}
				</span>
			</span>
		</Link>
	);
}

function AttentionLink({
	to,
	tag,
	title,
	lead,
}: {
	to: string;
	tag: string;
	title: string;
	lead: string;
}) {
	return (
		<li>
			<Link to={to} className="flex items-center gap-3 px-5 py-3 transition hover:bg-surface">
				<span
					aria-hidden="true"
					className="grid h-8 w-9 flex-none place-items-center rounded-lg bg-surface text-[10px] font-bold tracking-wide text-muted"
				>
					{tag}
				</span>
				<span className="min-w-0 flex-1">
					<span className="block truncate text-[12.5px] font-semibold text-ink">{title}</span>
					<span className="block truncate text-[11px] text-muted">{lead}</span>
				</span>
				<Icon.chevron size={14} className="-rotate-90 flex-none text-slate-faint" />
			</Link>
		</li>
	);
}

/**
 * The next operation to start, and how ready it is.
 *
 * One deployment rather than a summary of all of them, because readiness is a
 * question about a specific thing that is about to happen. Chosen as the
 * earliest-starting deployment that has not started yet; where nothing is
 * upcoming there is nothing to be ready for and the strip is not drawn.
 */
function ReadinessStrip({ rows, loading }: { rows: DeploymentSummary[]; loading: boolean }) {
	const next = [...rows]
		.filter((row) => row.status === "Planned" && row.start_date)
		.sort((left, right) => (left.start_date ?? "").localeCompare(right.start_date ?? ""))[0];

	if (loading || !next) return null;

	const required = next.volunteers_required || 0;
	const pending = next.assignment_counts?.Pending ?? 0;

	return (
		<Card>
			<div className="flex flex-wrap items-center gap-x-8 gap-y-4">
				<div className="min-w-0 flex-1 basis-[220px]">
					<SectionLabel>Next operation readiness</SectionLabel>
					<p className="mt-1 truncate text-[13px] font-semibold text-ink">
						{next.terms_of_reference || next.name}
					</p>
					<p className="mt-0.5 text-[11.5px] text-muted">
						{geoPath(next.geo_path)} · starts {formatDate(next.start_date)}
					</p>
				</div>

				<div className="min-w-0 flex-1 basis-[180px]">
					{required > 0 ? (
						<Meter
							label="Roles filled"
							value={next.participant_count}
							total={required}
							figure={
								<span className="text-[11.5px] font-semibold text-muted">
									{next.participant_count} / {required}
								</span>
							}
							tint={next.participant_count >= required ? "teal" : "amber"}
						/>
					) : (
						<p className="text-[12px] text-muted">
							{next.participant_count} on the roster
							<span className="text-slate-faint"> · no headcount set</span>
						</p>
					)}
				</div>

				<div className="flex-none">
					<SectionLabel>Invitations</SectionLabel>
					<p
						className={cx(
							"mt-1 text-[13px] font-semibold",
							pending > 0 ? "text-warning" : "text-success",
						)}
					>
						{pending > 0 ? `${pending} pending` : "All answered"}
					</p>
				</div>

				<Link
					to={`/admin/deployments/${encodeURIComponent(next.name)}`}
					className="flex-none text-[12.5px] font-semibold text-blue-press hover:underline"
				>
					Open operation →
				</Link>
			</div>
		</Card>
	);
}

/**
 * The operations document register: private files kept with the operational
 * record they belong to.
 *
 * **The scope is the parent record's, and that is the whole access model.** A
 * `File` is not geo-scopeable — it hangs off something that is — so the server
 * lists the readable projects, terms and deployments through
 * `frappe.get_list` and only reads files attached to *those*. A file whose
 * parent is outside the caller's areas is never named here.
 *
 * **An upload may only name a target the server handed back.** `targets` is the
 * subset the caller may *write*, computed server-side, so this screen offers
 * exactly what the server would accept rather than a list it composed itself and
 * an error afterwards. Everything goes up private.
 */
export function OperationsDocuments() {
	const [search, setSearch] = useState("");
	const [recordType, setRecordType] = useState("");
	const [target, setTarget] = useState("");
	const [uploading, setUploading] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const [done, setDone] = useState<string | null>(null);

	const documents = useFrappeGetCall<{ message: OperationsDocumentsAnswer }>(
		API.operationsDocuments,
		{ search, ...(recordType ? { doctype: recordType } : {}) },
		`admin:operations:documents:${search}:${recordType}`,
	);

	const answer = documents.data?.message;
	const targets = answer?.targets ?? [];
	const types = answer?.record_types ?? [];

	const upload = async (file: File) => {
		const selected = targets.find((item) => `${item.doctype}\n${item.name}` === target);

		if (!selected) {
			// The selection is kept: an error that also cleared the form would
			// make somebody choose the record again to read what went wrong.
			setDone(null);
			setFailure("Choose the operational record this file belongs to.");
			return;
		}

		setUploading(true);
		setFailure(null);
		setDone(null);

		try {
			const body = new FormData();
			body.append("file", file);
			// Private, always. An operational document is a plan, an assessment or
			// evidence, and none of those is public because somebody forgot a
			// checkbox.
			body.append("is_private", "1");
			body.append("doctype", selected.doctype);
			body.append("docname", selected.name);

			const response = await fetch("/api/method/upload_file", {
				method: "POST",
				body,
				credentials: "same-origin",
				headers: { "X-Frappe-CSRF-Token": window.csrf_token ?? "" },
			});

			if (!response.ok) throw new Error("The upload was refused.");

			await documents.mutate();
			setDone(`${file.name} was filed against ${shortDoctype(selected.doctype)} ${selected.name}.`);
		} catch (uploadError) {
			setFailure(errorMessage(uploadError, "That document could not be uploaded."));
		} finally {
			setUploading(false);
		}
	};

	return (
		<>
			<PageHeading
				title="Operations documents"
				lead="Private files attached to the project, terms of reference, or deployment they support."
				trail={[
					{ label: "Operations", to: "/admin/deployments" },
					{ label: "Operations documents" },
				]}
			/>

			<Card className="mb-5">
				<div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
					<Labelled
						label="Store against"
						hint="Only records you may write to are listed. The file inherits that record's permission scope."
					>
						<select
							className={INPUT}
							value={target}
							onChange={(event) => setTarget(event.target.value)}
						>
							<option value="">Choose a project, terms of reference, or deployment</option>
							{targets.map((item) => (
								<option
									key={`${item.doctype}:${item.name}`}
									value={`${item.doctype}\n${item.name}`}
								>
									{shortDoctype(item.doctype)} · {item.name}
								</option>
							))}
						</select>
					</Labelled>

					<label
						className={cx(
							"inline-flex cursor-pointer items-center justify-center gap-2 rounded-lg bg-rail px-4 py-2.5 text-[12.5px] font-bold text-white transition hover:bg-rail-soft",
							uploading && "pointer-events-none opacity-60",
						)}
					>
						<Icon.upload size={16} /> {uploading ? "Uploading…" : "Upload private file"}
						<input
							type="file"
							className="hidden"
							disabled={uploading}
							onChange={(event) => {
								const file = event.target.files?.[0];
								if (file) void upload(file);
								event.currentTarget.value = "";
							}}
						/>
					</label>
				</div>

				{failure && (
					<div className="mt-4">
						<ErrorNote>{failure}</ErrorNote>
					</div>
				)}

				{done && (
					<p className="mt-4 rounded-lg bg-success-soft px-3.5 py-2.5 text-[12px] font-semibold text-success">
						{done}
					</p>
				)}
			</Card>

			<Card pad={false}>
				<div className="flex flex-wrap items-center justify-between gap-3 border-b border-card-line px-5 py-4">
					<div>
						<SectionTitle>File library</SectionTitle>
						<p className="mt-1 text-[11.5px] text-slate-faint">
							{answer?.count ?? 0} files · private by default
						</p>
					</div>

					<div className="flex flex-wrap items-center gap-2">
						<label className="relative">
							<span className="sr-only">Record type</span>
							<select
								value={recordType}
								onChange={(event) => setRecordType(event.target.value)}
								className={cx(
									"appearance-none rounded-full border bg-white py-2 pl-4 pr-9 text-[12.5px] outline-none transition",
									recordType
										? "border-blue bg-blue-soft font-semibold text-blue-press"
										: "border-card-line text-slate-strong hover:border-blue",
								)}
							>
								<option value="">All record types</option>
								{types.map((doctype) => (
									<option key={doctype} value={doctype}>
										{shortDoctype(doctype)}
									</option>
								))}
							</select>
							<svg
								viewBox="0 0 24 24"
								width="12"
								height="12"
								fill="none"
								aria-hidden="true"
								className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-faint"
							>
								<path
									d="m6 9 6 6 6-6"
									stroke="currentColor"
									strokeWidth="2.2"
									strokeLinecap="round"
								/>
							</svg>
						</label>

						<div className="relative">
							<Icon.search
								className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-faint"
								size={15}
							/>
							<input
								type="search"
								className={`${INPUT} w-56 pl-9`}
								placeholder="Search files or records"
								aria-label="Search files or records"
								value={search}
								onChange={(event) => setSearch(event.target.value)}
							/>
						</div>
					</div>
				</div>

				{documents.isLoading && (
					<div className="p-5">
						<Skeleton className="h-32" />
					</div>
				)}

				{documents.error && (
					<div className="p-5">
						<ErrorNote>{errorMessage(documents.error)}</ErrorNote>
					</div>
				)}

				{!documents.isLoading && !documents.error && (answer?.files.length ?? 0) === 0 && (
					<Empty title="No operational files here">
						{search || recordType
							? "Nothing matches what you asked for. Clear the search or the record type."
							: "Upload the first plan, briefing, assessment, photograph, or report and attach it to the record it belongs to."}
					</Empty>
				)}

				{(answer?.files.length ?? 0) > 0 && (
					<Table head={["Document", "Attached to", "Record type", "Owner", "Updated", ""]}>
						{(answer?.files ?? []).map((file) => (
							<Row key={file.name}>
								<Cell>
									<span className="flex items-center gap-3">
										<span
											aria-hidden="true"
											className="grid h-9 w-9 flex-none place-items-center rounded-lg bg-surface text-ink"
										>
											<Icon.file size={17} />
										</span>
										<span className="min-w-0">
											<span className="block truncate text-[13px] font-semibold text-ink">
												{file.file_name}
											</span>
											<span className="mt-0.5 block text-[11px] text-slate-faint">
												{formatBytes(file.file_size)}
												{file.is_private ? " · Private" : " · Shared"}
											</span>
										</span>
									</span>
								</Cell>
								<Cell className="text-muted">{file.attached_to_name}</Cell>
								<Cell className="text-muted">{shortDoctype(file.attached_to_doctype)}</Cell>
								<Cell className="text-muted">{file.owner}</Cell>
								<Cell className="text-muted">{formatDate(file.modified)}</Cell>
								<Cell className="text-right">
									{/* A real link to the file rather than a script-driven
									    download: a private file is served by Frappe against
									    the same session, so whoever may read the record may
									    open it and nobody else can. */}
									<a
										href={file.file_url}
										target="_blank"
										rel="noreferrer"
										className="text-[12.5px] font-bold text-ink hover:underline"
									>
										Open
									</a>
								</Cell>
							</Row>
						))}
					</Table>
				)}
			</Card>
		</>
	);
}

function shortDoctype(doctype: string): string {
	return doctype.replace(/^VMMS /, "");
}

function formatBytes(size: number | null): string {
	if (!size) return "—";
	if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
	return `${(size / (1024 * 1024)).toFixed(1)} MB`;
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
	ongoing: { statuses: ONGOING_STATUSES, title: "Ongoing deployments" },
	// **Closed Out belongs here and was missing.** It is the status a mission
	// reaches once its paperwork is filed, and with it absent from both bands a
	// closed-out deployment appeared in no register at all — which is the worst
	// outcome a filter can have, because the list looks complete.
	past: { statuses: ["Completed", "Closed Out", "Cancelled"], title: "Past deployments" },
};

export type DeploymentScope = "ongoing" | "past";

/**
 * The operational columns a coordinator runs the day from.
 *
 * **Each column is a real deployment status, and none of them is invented
 * here.** The board used to be four made-up phases — Planning, Recruiting,
 * Ongoing, Close-out — mapped loosely onto two of the doctype's six statuses,
 * which meant a Suspended deployment appeared nowhere and a Closed Out one was
 * indistinguishable from a Completed one. These four are the doctype's own:
 *
 *     Mobilising   Planned — approved, being staffed, not started
 *     Running      Active — people are out
 *     Suspended    stopped, and not finished. Drawn as a warning, not hidden.
 *     Close-out    Completed and not yet Closed Out — the work is over and
 *                  the paperwork is not
 *
 * Closed Out and Cancelled are excluded, and they are the only two that are:
 * both are genuinely over, and both are in Past deployments where the record of
 * them is kept in full.
 *
 * **The band is the server's answer.** `branch_deployments` is asked for the
 * four statuses as a set, so this is the register rather than the members of the
 * band that happened to be on one page — and `total` beside it is honest about
 * how much of it is shown.
 */
export function DeploymentsOngoing() {
	const [mine, setMine] = useState(false);

	const { data, error, isLoading } = useFrappeGetCall<{
		message: {
			count: number;
			total: number;
			deployments: DeploymentSummary[];
			open_count: number;
		};
	}>(
		API.branchDeployments,
		{ statuses: ONGOING_STATUSES, mine: mine ? 1 : 0, limit: 100 },
		`admin:deployments:ongoing:${mine}`,
	);

	const answer = data?.message;
	const rows = answer?.deployments ?? [];

	const columns = ONGOING_COLUMNS.map((column) => ({
		...column,
		rows: rows.filter((row) => column.matches(row)),
	}));

	return (
		<>
			<PageHeading
				title="Ongoing deployments"
				lead="Mobilising, running, suspended and closing-out operations inside your scope."
				trail={[
					{ label: "Operations", to: "/admin/deployments" },
					{ label: "Ongoing deployments" },
				]}
				actions={<ButtonLink to="/admin/deployments/new">Create deployment</ButtonLink>}
			/>

			<div className="mb-4 flex flex-wrap items-center gap-2">
				<MineToggle mine={mine} onChange={setMine} label="Only mine" />
				{answer && (
					<Pill tone="page">
						{rows.length === answer.total
							? `${answer.total} ongoing`
							: `${rows.length} of ${answer.total} ongoing`}
					</Pill>
				)}
			</div>

			{isLoading && <Spinner label="Loading deployments…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{answer && rows.length === 0 && (
				<Empty title="Nothing is running">
					No deployment in your area is planned, active, suspended or waiting on close-out.
					Completed and cancelled ones are kept in Past deployments.
				</Empty>
			)}

			{rows.length > 0 && (
				<div className="grid items-start gap-4 lg:grid-cols-2 xl:grid-cols-4">
					{columns.map((column) => (
						<section key={column.key} aria-labelledby={`col-${column.key}`}>
							<div
								className={cx(
									"mb-2.5 flex items-center justify-between gap-2 rounded-lg px-3 py-2",
									column.tone,
								)}
							>
								<h2 id={`col-${column.key}`} className="text-[12px] font-bold">
									{column.label}
								</h2>
								<span className="tabular text-[12px] font-bold">{column.rows.length}</span>
							</div>

							<p className="mb-2.5 px-1 text-[11px] leading-relaxed text-muted">
								{column.lead}
							</p>

							{column.rows.length === 0 ? (
								<p className="rounded-xl border border-dashed border-card-line px-3 py-4 text-center text-[11.5px] text-slate-faint">
									Nothing here
								</p>
							) : (
								<ul className="space-y-2.5">
									{column.rows.map((row) => (
										<li key={row.name}>
											<DeploymentCard row={row} />
										</li>
									))}
								</ul>
							)}
						</section>
					))}
				</div>
			)}
		</>
	);
}

/**
 * The four columns, and the exact status each one is.
 *
 * `matches` is a predicate over the doctype's own status rather than a lookup
 * table keyed by a phase name, because "Completed but not Closed Out" is a
 * conjunction and there is no single status that means it. `is_closed_out` is
 * the server's own flag, not a string comparison here.
 */
const ONGOING_COLUMNS: Array<{
	key: string;
	label: string;
	lead: string;
	tone: string;
	matches: (row: DeploymentSummary) => boolean;
}> = [
	{
		key: "mobilising",
		label: "Mobilising",
		lead: "Approved and being staffed. Not started.",
		tone: "bg-blue-soft text-blue-press",
		matches: (row) => row.status === "Planned",
	},
	{
		key: "running",
		label: "Running",
		lead: "People are out in the field now.",
		tone: "bg-success-soft text-success",
		matches: (row) => row.status === "Active",
	},
	{
		key: "suspended",
		label: "Suspended",
		lead: "Stopped, and not finished. Somebody has to decide what happens next.",
		tone: "bg-warning-soft text-warning",
		matches: (row) => row.status === "Suspended",
	},
	{
		key: "closeout",
		label: "Close-out",
		lead: "The work is over and the paperwork is not.",
		tone: "bg-surface text-slate-strong",
		matches: (row) => row.status === "Completed" && !row.is_closed_out,
	},
];

/**
 * Past deployments: a shelf of closed mission files.
 *
 * **Folders, and navy ones, because this register is not the others.** Every
 * live register in this console is a white surface on the canvas — that is what
 * "work in progress" looks like here. A mission that is over is a different kind
 * of object: nothing on it will change again, and what a coordinator does with
 * it is *retrieve* it rather than act on it. So the past register is drawn as
 * what it is, a row of closed folders in the rail's own navy, and the difference
 * is legible from across the room without reading a single status.
 *
 * The navy is `bg-rail` — the same #011E41 the left-hand navigation is — so this
 * introduces no new colour. White text on it clears AA with enormous headroom,
 * which is the same reason the rail can carry white text.
 *
 * **A folder is still a link to the whole record.** Nothing is archived away
 * and nothing is read-only by virtue of being here: a closed mission file keeps
 * its TOR versions, its assignments, its hours, its evidence and its outcome,
 * and the folder opens onto all of it.
 */
export function PastDeployments() {
	const [mine, setMine] = useState(false);
	const [status, setStatus] = useState("");

	const band = SCOPES.past;

	const { data, error, isLoading } = useFrappeGetCall<{
		message: {
			count: number;
			total: number;
			deployments: DeploymentSummary[];
			open_count: number;
		};
	}>(
		API.branchDeployments,
		{
			...(status ? { status } : { statuses: band.statuses }),
			mine: mine ? 1 : 0,
			limit: 100,
		},
		`admin:deployments:past:${status}:${mine}`,
	);

	const answer = data?.message;
	const rows = answer?.deployments ?? [];

	return (
		<>
			<PageHeading
				title="Past deployments"
				lead="Each closed mission is kept as a complete file — its terms, its roster, its hours, its evidence and its outcome."
				trail={[
					{ label: "Operations", to: "/admin/deployments" },
					{ label: "Past deployments" },
				]}
			/>

			<div className="mb-5 flex flex-wrap items-center gap-2">
				{["", ...band.statuses].map((option) => (
					<button
						key={option || "all"}
						type="button"
						onClick={() => setStatus(option)}
						aria-pressed={status === option}
						className={cx(
							"rounded-full border px-3.5 py-1.5 text-[12px] font-semibold transition",
							status === option
								? "border-blue bg-blue-soft text-blue-press"
								: "border-card-line bg-white text-slate-strong hover:border-blue hover:text-ink",
						)}
					>
						{option || "All"}
					</button>
				))}
				<MineToggle mine={mine} onChange={setMine} label="Only mine" />
				{answer && (
					<Pill tone="page">
						{rows.length === answer.total
							? `${answer.total} mission ${answer.total === 1 ? "file" : "files"}`
							: `${rows.length} of ${answer.total} mission files`}
					</Pill>
				)}
			</div>

			{isLoading && <Spinner label="Loading mission files…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{answer && rows.length === 0 && (
				<Empty title="No mission files here">
					A deployment is filed here once it is completed, closed out or cancelled. Nothing is
					ever deleted: a stood-down operation is part of the record of what a branch planned
					and what happened to it.
				</Empty>
			)}

			{rows.length > 0 && (
				<ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					{rows.map((row) => (
						<li key={row.name}>
							<MissionFolder row={row} />
						</li>
					))}
				</ul>
			)}
		</>
	);
}

/**
 * One closed mission, as the folder it is.
 *
 * The tab is a real element rather than a background image, so it keeps its
 * shape at any width and inherits the same hover as the body. The whole card is
 * one link: a folder you have to aim at a corner of is a folder nobody opens.
 */
function MissionFolder({ row }: { row: DeploymentSummary }) {
	const filed = row.closed_out_on ?? row.actual_end ?? row.end_date;
	const assignments = row.assignment_counts?.total ?? 0;
	// The year the file is filed under, taken from the date it was actually
	// filed rather than from today: a mission closed in December stays a
	// December file in January.
	const year = filed ? new Date(filed).getFullYear() : null;

	return (
		<Link
			to={`/admin/deployments/${encodeURIComponent(row.name)}`}
			className="group block h-full pt-2.5 transition duration-200 hover:-translate-y-0.5"
		>
			<div className="relative h-full">
				{/* The tab. Behind the body and rising above it, so the two read as
				    one folded object rather than as a card with a flag on it. */}
				<span
					aria-hidden="true"
					className="absolute -top-2.5 left-0 h-4 w-[42%] rounded-t-[7px] bg-rail transition-colors group-hover:bg-rail-soft"
				/>

				<div className="relative flex h-full min-h-[186px] flex-col rounded-[11px] rounded-tl-none bg-rail px-4 pb-3.5 pt-4 shadow-[0_1px_2px_rgba(1,30,65,0.14)] transition duration-200 group-hover:bg-rail-soft group-hover:shadow-[0_14px_30px_rgba(1,30,65,0.22)]">
					{/* The fold along the top of the body, which is what stops the
					    tab and the body reading as two stacked rectangles. */}
					<span
						aria-hidden="true"
						className="absolute inset-x-0 top-0 h-px rounded-t-[11px] bg-white/20"
					/>

					{/* White at 60% on #011E41 is about 5.4:1 — clear of AA for
					    small text. The two faintest lines on this card were at 55%
					    and 50%, which is where that stops being true. */}
					<p className="text-[9.5px] font-bold uppercase tracking-[0.11em] text-white/60">
						{year ? `${year} mission file` : "Mission file"}
					</p>
					<p className="tabular mt-1 truncate font-mono text-[10.5px] text-white/60">
						{row.name}
					</p>

					<h3 className="mt-2.5 line-clamp-2 text-[14px] font-bold leading-snug text-white">
						{row.terms_of_reference || row.name}
					</h3>

					<p className="mt-1.5 line-clamp-2 text-[11.5px] leading-relaxed text-white/70">
						{geoPath(row.geo_path) || "No area recorded"}
					</p>

					<p className="mt-2 text-[11.5px] text-white/75">
						{assignments} {assignments === 1 ? "assignment" : "assignments"}
						{row.terms_of_reference ? " · terms of reference" : ""}
					</p>

					<div className="mt-auto flex items-center justify-between gap-2 border-t border-white/15 pt-2.5">
						<span className="flex min-w-0 items-center gap-1.5 text-[11px] font-semibold text-white/85">
							{/* A dot as well as the words: a state is never a hue alone,
							    and on this surface there is no hue to read anyway. */}
							<span
								aria-hidden="true"
								className={cx("h-1.5 w-1.5 flex-none rounded-full", FILED_TONES[row.status] ?? "bg-white/50")}
							/>
							<span className="truncate">{row.status}</span>
						</span>
						<span className="tabular flex-none text-[11px] text-white/70">
							{filed ? formatDate(filed) : "No date"}
						</span>
					</div>
				</div>
			</div>
		</Link>
	);
}

/**
 * The dot beside a filed mission's status.
 *
 * Three of the doctype's six can appear here, and each is a different kind of
 * ending: the work finished, the file was closed, or the operation was called
 * off. An unknown value gets the neutral dot rather than none, because a folder
 * with no marker at all reads as one that failed to load.
 */
const FILED_TONES: Record<string, string> = {
	Completed: "bg-warning-dot",
	"Closed Out": "bg-success-dot",
	Cancelled: "bg-danger-dot",
};

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
	// **The band is asked for as a set, not sieved out of an unfiltered page.**
	// `branch_deployments` takes `statuses` now, so "ongoing" is a question the
	// database answers rather than whichever members of the band happened to
	// land on the first page. `total` comes back with it and is the size of the
	// band inside the caller's scope, which is what the count line may say.
	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: {
			count: number;
			total: number;
			deployments: DeploymentSummary[];
			open_count: number;
		};
	}>(
		API.branchDeployments,
		{
			...(status ? { status } : band ? { statuses: band.statuses } : {}),
			mine: mine ? 1 : 0,
		},
		`admin:deployments:${scope ?? ""}:${status}:${mine}`,
	);

	const answer = data?.message;
	const rows = answer?.deployments ?? [];

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
								: "border-card-line bg-white text-muted hover:border-slate-faint hover:text-ink",
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
				{/* The badge is `flex-none` and the title may shrink, so a long
				    terms name in a narrow board column wraps rather than pushing
				    the status off the edge of the card. */}
				<div className="flex items-start justify-between gap-2">
					<span className="min-w-0 flex-1">
						<SectionTitle>{row.terms_of_reference || row.name}</SectionTitle>
					</span>
					<span className="flex-none">
						<StateBadge state={row.status} />
					</span>
				</div>
				<p className="mt-1 text-[11.5px] text-muted">{geoPath(row.geo_path)}</p>
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
								<span className="text-[12px] font-semibold text-muted">
									{row.participant_count} of {row.volunteers_required}
								</span>
							}
							tint={row.participant_count >= row.volunteers_required ? "teal" : "amber"}
						/>
					) : (
						<p className="text-[12px] text-muted">
							{row.participant_count} on the deployment
							<span className="text-slate-faint"> · no headcount set</span>
						</p>
					)}
				</div>

				{waiting > 0 && (
					<p className="mt-2 text-[11.5px] font-semibold text-blue">
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
	const [status, setStatus] = useState("Planned");
	const [emailTemplate, setEmailTemplate] = useState("");
	const [notes, setNotes] = useState("");
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const available = useFrappeGetCall<{ message: { terms: TermsOfReference[] } }>(
		API.branchTerms,
		{ mine: 1, active_only: 1 },
		"admin:terms:for-deployment",
	);
	const deploymentOptions = useFrappeGetCall<{
		message: { email_templates: Array<{ name: string; subject: string | null }> };
	}>(API.deploymentOptions, undefined, "admin:deployment:options");

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
				status,
				email_template: emailTemplate || undefined,
				notes: notes.trim() || undefined,
			});
			setTerms("");
			setStartDate("");
			setEndDate("");
			setRequired("");
			setStatus("Planned");
			setEmailTemplate("");
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
			<p className="mt-1 text-[12.5px] text-muted">
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

					<div className="mt-4 grid gap-4 sm:grid-cols-3">
						<Labelled
							label="Volunteers needed"
							hint="Optional. Leave it empty for no limit."
						>
							<input
								type="number"
								min="0"
								className={INPUT}
								value={required}
								onChange={(event) => setRequired(event.target.value)}
							/>
						</Labelled>
						<Labelled label="Status" hint="Where this deployment starts in its lifecycle.">
							<select className={INPUT} value={status} onChange={(event) => setStatus(event.target.value)}>
								{["Planned", "Active", "Completed", "Cancelled"].map((option) => (
									<option key={option} value={option}>
										{option}
									</option>
								))}
							</select>
						</Labelled>
						<Labelled label="Email template" hint="Optional wording for volunteer invitations.">
							<select
								className={INPUT}
								value={emailTemplate}
								onChange={(event) => setEmailTemplate(event.target.value)}
							>
								<option value="">Use the standard invitation</option>
								{(deploymentOptions.data?.message?.email_templates ?? []).map((template) => (
									<option key={template.name} value={template.name}>
										{template.name}
									</option>
								))}
							</select>
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
				lead="Choose the terms of reference first. The rest of the form follows from it."
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
							<p className="text-[12px] text-muted">{geoPath(deployment.geo_path)}</p>
							<p className="mt-0.5 text-[12px] text-slate-faint">
								{deployment.start_date ? formatDate(deployment.start_date) : "No start date"}
								{deployment.end_date ? ` → ${formatDate(deployment.end_date)}` : ""}
							</p>
						</div>
						<StateBadge state={deployment.status} />
					</div>

					{deployment.terms?.purpose && (
						<p className="mt-3 text-[12.5px] text-muted">{deployment.terms.purpose}</p>
					)}

					{(deployment.email_template || deployment.notes) && (
						<dl className="mt-3 grid gap-3 text-[12px] sm:grid-cols-2">
							{deployment.email_template && (
								<div>
									<dt className="text-slate-faint">Email template</dt>
									<dd className="font-semibold text-ink">{deployment.email_template}</dd>
								</div>
							)}
							{deployment.notes && (
								<div>
									<dt className="text-slate-faint">Notes</dt>
									<dd className="whitespace-pre-line text-muted">{deployment.notes}</dd>
								</div>
							)}
						</dl>
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

					<div className="mt-4 flex flex-wrap gap-2 border-t border-card-line pt-3.5">
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
							<span className="text-[12px] font-semibold text-muted">
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

								<ul className="mt-2 divide-y divide-card-line">
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
						<p className="mt-0.5 text-[11.5px] italic text-muted">“{row.response_note}”</p>
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
				<Labelled label="Search" hint="A name, or a record number.">
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
					options={vocabulary.data?.message?.skills ?? []}
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
					<div className="flex items-center justify-between gap-3 border-y border-card-line py-2.5">
						<label className="flex cursor-pointer items-center gap-2 text-[12px] font-semibold text-muted">
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

					<ul className="divide-y divide-card-line">
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
					<div className="sticky bottom-0 -mx-5 mt-1 flex flex-wrap items-center gap-2 border-t border-card-line bg-white/95 px-5 py-3 backdrop-blur sm:-mx-6 sm:px-6">
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
function Outcome({ outcome, onClose }: { outcome: AssignmentOutcome; onClose: () => void }) {
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
								{row.terms_of_reference || row.name}
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

			<div className="mt-3.5 rounded-xl border border-card-line bg-surface p-3">
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
									? "border-blue bg-rail text-white"
									: "border-card-line bg-white text-muted hover:border-blue",
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
	concern: "border-blue bg-blue",
	milestone: "border-blue bg-rail",
	status: "border-card-line bg-slate-faint",
	roster: "border-card-line bg-slate-faint",
};

function FeedRow({ entry }: { entry: FeedEntry }) {
	const dot = ENTRY_TONES[entry.entry_type] ?? "border-card-line bg-card-line";

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
				className="absolute bottom-0 left-[7px] top-4 w-px bg-card-line group-last:hidden"
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
					<p className="mt-0.5 text-[11.5px] font-semibold text-muted">{entry.subject}</p>
				)}

				{entry.note && (
					<p className="mt-1 whitespace-pre-line text-[12.5px] text-muted">{entry.note}</p>
				)}

				{entry.proof && (
					<img
						src={entry.proof}
						alt=""
						className="mt-2 max-h-48 rounded-xl border border-card-line object-cover"
					/>
				)}
			</div>
		</li>
	);
}

/* ---------------------------------------------------------------- requests */

/**
 * Deployment requests: a branch asking for volunteers against a terms of
 * reference, and where each ask stands.
 *
 * **This is `VMMS Deployment Request`, not an invitation response.** The two
 * were once conflated on this screen and they are different records with
 * different lifecycles: a request is a branch asking a higher level for people,
 * and an invitation is one volunteer being asked whether they will go. The
 * volunteer's answer lives on `VMMS Deployment Assignment` and is shown on the
 * deployment's own page.
 *
 * **Deciding one is not here, and that is deliberate.** A routed request is
 * acted on from the review queue, through `api/approvals.py::decide`, because
 * the person-gate lives there — holding the role is not the same as being *this*
 * request's approver — and a second door into the same decision would be a
 * second place to get it wrong. This screen says which of five things is true of
 * a request and sends you to the queue when you are the one it is waiting on.
 */
export function RequestList() {
	const [search, setSearch] = useState("");

	const { data, error, isLoading } = useFrappeGetCall<{
		message: { count: number; requests: DeploymentRequestRow[] };
	}>(API.branchRequests, undefined, "admin:deployment_requests");

	const all = data?.message?.requests ?? [];
	const needle = search.trim().toLowerCase();

	// Narrowing what has already arrived, and labelled as such: the endpoint
	// returns one page of the caller's scoped register and this is a find within
	// it, never presented as a search of the register.
	const rows = needle
		? all.filter((row) =>
				[row.name, row.terms_of_reference, row.geo_path]
					.filter(Boolean)
					.some((value) => (value as string).toLowerCase().includes(needle)),
			)
		: all;

	return (
		<>
			<PageHeading
				title="Deployment requests"
				lead="Asks for volunteers against a terms of reference, and where each one's approval stands."
				trail={[
					{ label: "Operations", to: "/admin/deployments" },
					{ label: "Deployment requests" },
				]}
			/>

			<Card className="mb-5">
				<div className="relative">
					<span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-faint">
						<Icon.search size={15} />
					</span>
					<input
						type="search"
						value={search}
						onChange={(event) => setSearch(event.target.value)}
						placeholder="Find a request by reference, terms or area"
						aria-label="Find a request by reference, terms or area"
						className="w-full rounded-full border border-card-line bg-white py-2.5 pl-11 pr-4 text-[13.5px] outline-none transition placeholder:text-slate-faint focus:border-blue"
					/>
				</div>
				{all.length > 0 && (
					<p className="mt-2.5 text-[11px] text-muted">
						Searching the {all.length} most recent requests in your area, not the whole
						register.
					</p>
				)}
			</Card>

			{isLoading && <Spinner label="Loading requests…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{data && rows.length === 0 && (
				<Empty title={needle ? "No request matches" : "No requests in your area"}>
					A deployment request asks for volunteers against a terms of reference. Once raised, it
					appears here and routes to whoever its terms name.
				</Empty>
			)}

			<div className="space-y-3">
				{rows.map((row) => (
					<RequestCard key={row.name} row={row} />
				))}
			</div>
		</>
	);
}

/**
 * One request, and the one true sentence about where it stands.
 *
 * **Five states, and the screen never derives which one from a stage label.**
 * `requires_approver`, `approval.state`, `approval.can_act`, `is_refused` and
 * `is_fulfilled` are all the server's own answers; this only chooses which of
 * five sentences to print from them. That is the difference between a screen
 * that shows the workflow and one that re-implements it.
 */
function RequestCard({ row }: { row: DeploymentRequestRow }) {
	const standing = standingOf(row);

	return (
		<Card>
			<div className="flex flex-wrap items-start justify-between gap-3">
				<div className="min-w-0">
					<SectionTitle>{row.terms_of_reference || row.name}</SectionTitle>
					<p className="tabular mt-0.5 font-mono text-[11px] text-slate-faint">{row.name}</p>
					<p className="mt-1 text-[12px] text-muted">{geoPath(row.geo_path)}</p>
				</div>

				<div className="flex flex-wrap items-center gap-2">
					{row.approval ? (
						// One of the seven states in `states.py`. Shown, never compared
						// to decide what the controls are — `can_act` does that.
						<StateBadge state={row.approval.state} />
					) : (
						<Pill tone="quiet">No approver required</Pill>
					)}
					{row.is_published ? (
						<Pill tone="page">Published to volunteers</Pill>
					) : (
						<Pill tone="quiet">Not published</Pill>
					)}
				</div>
			</div>

			<dl className="mt-3 grid gap-x-5 gap-y-2 border-t border-card-line pt-3 text-[12px] sm:grid-cols-2 lg:grid-cols-4">
				<RequestFact label="Volunteers requested" value={row.volunteers_requested ?? "—"} />
				<RequestFact label="Needed from" value={formatDate(row.needed_from)} />
				<RequestFact label="Needed until" value={formatDate(row.needed_until)} />
				<RequestFact
					label="Current stage"
					// Displayed only. A society names its own stages and this app
					// holds no table of them.
					value={row.approval?.stage?.label ?? "—"}
					detail={
						row.approval?.stage?.entered_on
							? `Since ${formatDate(row.approval.stage.entered_on)}`
							: undefined
					}
				/>
			</dl>

			{row.justification && (
				<div className="mt-3 border-t border-card-line pt-3">
					<h4 className="mb-1 text-[10.5px] font-bold uppercase tracking-[0.08em] text-muted">
						Justification
					</h4>
					<p className="whitespace-pre-line text-[12.5px] leading-relaxed text-slate-strong">
						{row.justification}
					</p>
				</div>
			)}

			<div className="mt-3 flex flex-wrap items-center gap-3 border-t border-card-line pt-3">
				<span
					className={cx(
						"flex items-center gap-1.5 text-[12px] font-semibold",
						standing.tone,
					)}
				>
					{/* A dot as well as the colour: a state is never a hue alone. */}
					<span aria-hidden="true" className="h-1.5 w-1.5 flex-none rounded-full bg-current" />
					{standing.text}
				</span>

				{row.is_fulfilled && row.deployment && (
					<Link
						to={`/admin/deployments/${encodeURIComponent(row.deployment)}`}
						className="ml-auto text-[12px] font-semibold text-blue-press hover:underline"
					>
						Open deployment {row.deployment} →
					</Link>
				)}

				{/* The way to act on it, and it goes to the queue rather than
				    offering a second decision control here. */}
				{row.approval?.can_act && (
					<Link
						to="/admin/queue/volunteers"
						className="ml-auto text-[12px] font-semibold text-blue-press hover:underline"
					>
						Decide this in your review queue →
					</Link>
				)}
			</div>
		</Card>
	);
}

/**
 * Which of the five things is true of this request.
 *
 * Ordered by finality: an outcome that has happened outranks one that is still
 * being waited for. Every input is a server-computed boolean or an exact state,
 * so nothing here re-implements the workflow.
 */
function standingOf(row: DeploymentRequestRow): { text: string; tone: string } {
	if (row.is_fulfilled) {
		return { text: "Fulfilled by a deployment", tone: "text-success" };
	}

	if (row.is_refused) {
		return { text: "Refused — no deployment will be raised from this", tone: "text-danger" };
	}

	if (!row.approval) {
		return {
			text: "Needs no approver — its terms are handled directly",
			tone: "text-muted",
		};
	}

	if (row.approval.can_act) {
		return { text: "Waiting on you, in your review queue", tone: "text-blue-press" };
	}

	if (row.approval.is_open) {
		return { text: "In review, waiting on somebody else", tone: "text-warning" };
	}

	return { text: `Decided: ${row.approval.state}`, tone: "text-muted" };
}

function RequestFact({
	label,
	value,
	detail,
}: {
	label: string;
	value: ReactNode;
	detail?: string;
}) {
	return (
		<div>
			<dt className="text-slate-faint">{label}</dt>
			<dd className="font-semibold text-ink">{value}</dd>
			{detail && <dd className="text-[11px] text-slate-faint">{detail}</dd>}
		</div>
	);
}
