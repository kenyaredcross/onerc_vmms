import { useContext, useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage, termsPdfUrl } from "../lib/api";
import { branchPath, formatDate, formatHours } from "../lib/format";
import { Icon } from "../ui/icons";
import { OsmMap } from "./ui/OsmMap";
import {
	BackLink,
	Button,
	Card,
	Empty,
	ErrorNote,
	Facts,
	FactList,
	FolderCard,
	GroupLabel,
	Notice,
	PageHead,
	Spinner,
	StatusBadge,
	StatusChip,
	Tabs,
} from "./ui/kit";
import { Modal, useToast } from "./ui/overlays";
import type {
	BranchLocation,
	DeploymentInvitation,
	DeploymentSummary,
	MyAssignment,
	MyTimeLogs,
	TermsMission,
} from "./types";

/**
 * Being asked to go somewhere, what you have confirmed, and the durable record
 * of where you have served.
 *
 * **Most volunteers have one live request at a time**, so the waiting one is
 * the page's first and largest thing — the concept's assignment card, with the
 * reporting point drawn beside it. Reading and answering it is a page of its
 * own at `/deployments/requests/:assignment`, because accepting is accepting a
 * specific submitted terms of reference and that document deserves the room.
 *
 * **Possessive in, ownership-checked out.** `my_invitations` and
 * `my_deployments` take no argument; `respond_to_assignment` names a record and
 * the server checks it belongs to the caller's own volunteer record rather than
 * checking geo scope, which every volunteer would fail.
 *
 * **The archive is a record, not a trophy cabinet.** A closed mission keeps its
 * dates, its role, its terms and the service filed against it, drawn plainly.
 */
export default function Deployments() {
	const invitations = useFrappeGetCall<{
		message: {
			volunteer: string;
			waiting: DeploymentInvitation[];
			answered: DeploymentInvitation[];
		} | null;
	}>(API.myInvitations, undefined, "portal:my_invitations");

	const history = useFrappeGetCall<{
		message: { volunteer: string; deployments: (DeploymentSummary & { title: string })[] } | null;
	}>(API.myDeployments, undefined, "portal:my_deployments");

	const locations = usePublishedPoints();

	const answer = invitations.data?.message;
	const waiting = answer?.waiting ?? [];
	const answered = answer?.answered ?? [];
	const deployments = history.data?.message?.deployments ?? [];

	const today = new Date().toISOString().slice(0, 10);
	const confirmed = answered.filter(
		(row) => row.response === "Accepted" && (!row.end_date || row.end_date >= today),
	);

	const loading = invitations.isLoading && history.isLoading;

	const sorted = useMemo(
		() => [...deployments].sort((a, b) => (b.start_date || "").localeCompare(a.start_date || "")),
		[deployments],
	);

	return (
		<>
			<PageHead
				eyebrow="My service record"
				title={<EditableText k="portal.deployments.heading" fallback="Deployments" />}
				lead="Review current requests and find every deployment document in one place."
			/>

			{invitations.error && (
				<div className="mb-5">
					<ErrorNote>{errorMessage(invitations.error)}</ErrorNote>
				</div>
			)}

			{loading && <Spinner label="Loading your deployments…" />}

			{!loading && (
				<div className="space-y-8">
					{/* -------------------------------------------------- active request */}
					{waiting.length > 0 ? (
						<section>
							<GroupLabel>
								{waiting.length > 1
									? `${waiting.length} requests waiting on you`
									: "Waiting on your answer"}
							</GroupLabel>
							<div className="space-y-4">
								{waiting.map((row) => (
									<AssignmentCard
										key={row.assignment}
										invitation={row}
										location={locations(row.geo_node)}
									/>
								))}
							</div>
						</section>
					) : (
						<Card>
							<Empty framed={false} icon={Icon.truck} title="No deployment request right now">
								When a coordinator asks you to join a mission, it appears here with its terms of
								reference and its dates for you to accept or decline.
							</Empty>
						</Card>
					)}

					{/* ----------------------------------------------------- confirmed */}
					{confirmed.length > 0 && (
						<section>
							<GroupLabel>Confirmed</GroupLabel>
							<Card pad={false}>
								<ul className="divide-y divide-card-line">
									{confirmed.map((row) => (
										<li key={row.assignment}>
											<Link
												to={`/deployments/${encodeURIComponent(row.deployment)}`}
												className="flex items-center gap-3.5 px-[18px] py-3.5 transition hover:bg-canvas"
											>
												<span
													className="grid h-9 w-9 flex-none place-items-center rounded-lg bg-blue-soft text-blue-press"
													aria-hidden="true"
												>
													<Icon.truck size={16} />
												</span>
												<span className="min-w-0 flex-1">
													<strong className="block truncate text-[13px] font-semibold text-ink">
														{row.title ?? row.deployment}
													</strong>
													<span className="mt-0.5 block truncate text-[11.5px] text-muted">
														{[row.role, dateRange(row.start_date, row.end_date)]
															.filter(Boolean)
															.join(" · ")}
													</span>
												</span>
												<StatusBadge tone="success">Accepted</StatusBadge>
												<span aria-hidden="true" className="flex-none text-[18px] leading-none text-slate-faint">
													›
												</span>
											</Link>
										</li>
									))}
								</ul>
							</Card>
						</section>
					)}

					{/* ------------------------------------------------------- archive */}
					<section>
						<header className="mb-4 flex flex-wrap items-end justify-between gap-3">
							<div>
								<h2 className="font-display text-[17px] font-bold tracking-[-0.02em] text-ink">
									Deployment archive
								</h2>
								<p className="mt-1 text-[12px] text-slate-body">
									Closed missions remain in your service history.
								</p>
							</div>
						</header>

						{history.isLoading ? (
							<Spinner label="Loading your record…" />
						) : sorted.length === 0 ? (
							<Card>
								<Empty framed={false} icon={Icon.file} title="No missions on your record yet">
									Every deployment you serve on is kept here with its terms, its dates and the
									service filed against it.
								</Empty>
							</Card>
						) : (
							<div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
								{sorted.map((row) => (
									<FolderCard
										key={row.name}
										to={`/deployments/${encodeURIComponent(row.name)}`}
										kicker={`${row.start_date ? row.start_date.slice(0, 4) : "Undated"} mission file`}
										title={row.title}
										meta={branchPath(row.geo_path) || row.geo_node || undefined}
										foot={`${dateRange(row.start_date, row.end_date) ?? "Undated"} · ${row.status}`}
									/>
								))}
							</div>
						)}
					</section>
				</div>
			)}
		</>
	);
}

/* ------------------------------------------------------------------ shared */

/**
 * Coordinates for a deployment location come from a published branch office
 * sharing its geo anchor — the one guest-readable source of a real point this
 * app has. A deployment with no matching office draws no map.
 */
function usePublishedPoints(): (node: string | null) => BranchLocation | null {
	const locations = useFrappeGetCall<{ message: { locations: BranchLocation[] } }>(
		API.publishedLocations,
		undefined,
		"portal:published_locations",
	);

	return useMemo(() => {
		const byNode = new Map<string, BranchLocation>();
		for (const loc of locations.data?.message?.locations ?? []) {
			if (loc.has_point && loc.latitude != null && loc.longitude != null && !byNode.has(loc.geo_node)) {
				byNode.set(loc.geo_node, loc);
			}
		}
		return (node: string | null) => (node ? (byNode.get(node) ?? null) : null);
	}, [locations.data]);
}

/* -------------------------------------------------- the waiting assignment */

/**
 * The concept's assignment card: what is being asked, and where to report,
 * side by side. The map is drawn only when a published office at the same geo
 * anchor carries real coordinates.
 */
function AssignmentCard({
	invitation,
	location,
}: {
	invitation: DeploymentInvitation;
	location: BranchLocation | null;
}) {
	const duration =
		invitation.start_date && invitation.end_date
			? dayCount(invitation.start_date, invitation.end_date)
			: null;

	const meta = [
		invitation.role || null,
		branchPath(invitation.geo_node) || invitation.geo_node || null,
		invitation.start_date
			? `${dateRange(invitation.start_date, invitation.end_date)}${
					duration ? ` (${duration} days)` : ""
				}`
			: null,
	].filter(Boolean);

	return (
		<div className="p-card grid overflow-hidden lg:grid-cols-[minmax(0,1fr)_330px]">
			<div className="min-w-0 p-6 sm:p-7">
				<div className="flex flex-wrap items-center gap-3">
					<StatusChip tone="warning">Awaiting your response</StatusChip>
					{invitation.invited_on && (
						<span className="text-[11.5px] text-muted">
							Invited {formatDate(invitation.invited_on)}
						</span>
					)}
				</div>

				<h2 className="mt-4 font-display text-[21px] font-bold leading-snug tracking-[-0.025em] text-ink">
					{invitation.title ?? invitation.deployment}
				</h2>
				{meta.length > 0 && (
					<p className="mt-1.5 text-[12.5px] font-medium text-blue">{meta.join(" · ")}</p>
				)}

				{invitation.notes && (
					<p className="mt-4 max-w-[640px] whitespace-pre-wrap text-[13px] leading-relaxed text-slate-body">
						{invitation.notes}
					</p>
				)}

				<Link
					to={`/deployments/requests/${encodeURIComponent(invitation.assignment)}`}
					className="mt-5 inline-flex items-center rounded-lg bg-rail px-4 py-2.5 text-[12.5px] font-bold text-white transition hover:bg-rail-soft"
				>
					Review request and TOR →
				</Link>
			</div>

			{location && location.latitude != null && location.longitude != null && (
				<div className="border-t border-card-line bg-canvas p-5 lg:border-l lg:border-t-0">
					<span className="block text-[10px] font-bold uppercase tracking-[0.1em] text-rail-label">
						Reporting point
					</span>
					<div className="mt-2.5">
						<OsmMap
							latitude={location.latitude}
							longitude={location.longitude}
							label={location.location_name}
							height={160}
						/>
					</div>
					<strong className="mt-3 block text-[12.5px] font-semibold text-ink">
						{location.location_name}
					</strong>
					{location.address && (
						<small className="mt-1 block text-[11.5px] text-slate-body">{location.address}</small>
					)}
					<small className="mt-1 block text-[11px] text-muted">
						Map data © OpenStreetMap contributors
					</small>
				</div>
			)}
		</div>
	);
}

/* ---------------------------------------------------------------- request */

type RequestChoice = "accept" | "decline" | null;

const DECLINE_REASONS = [
	"Not available on these dates",
	"Travel or location difficulty",
	"Health or personal circumstances",
	"Role is not suitable",
	"Other",
];

/**
 * The invitation, in full, with the terms somebody is being asked to accept.
 *
 * **Accepting is accepting these terms**, so the whole submitted document is on
 * the page rather than behind a link, and the confirmation modal says so once
 * more before the answer is sent.
 */
export function DeploymentRequest() {
	const { assignment = "" } = useParams();
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const navigate = useNavigate();
	const toast = useToast();
	const points = usePublishedPoints();

	const { data, error, isLoading } = useFrappeGetCall<{ message: MyAssignment }>(
		API.getMyAssignment,
		{ assignment },
		`portal:assignment:${assignment}`,
	);

	const [read, setRead] = useState(false);
	const [choice, setChoice] = useState<RequestChoice>(null);
	const [reason, setReason] = useState("");
	const [note, setNote] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	if (isLoading) return <Spinner page label="Opening the request…" />;

	const mission = data?.message;
	if (error || !mission) {
		return (
			<>
				<BackLink to="/deployments">My deployments</BackLink>
				<ErrorNote>{errorMessage(error, "That request could not be opened.")}</ErrorNote>
			</>
		);
	}

	const { assignment: row, terms, deployment } = mission;
	const location = points(deployment.geo_node ?? row.geo_node ?? null);
	// `Pending` is the one roster status that is still a question. Everything
	// else — Assigned, Accepted, Declined, Withdrawn — has been answered or
	// decided, and the panel says so rather than offering the buttons again.
	const answered = row.status !== "Pending";

	const coordinator = terms.stakeholders.find((s) =>
		(s.designation || "").toLowerCase().includes("coordinator"),
	);

	const duration =
		row.start_date && row.end_date ? dayCount(row.start_date, row.end_date) : null;

	const respond = async (accept: boolean) => {
		setBusy(true);
		setFailure(null);
		try {
			await call.post(API.respondToAssignment, {
				assignment,
				accept: accept ? 1 : 0,
				note: [accept ? null : reason, note].filter(Boolean).join(" — ") || undefined,
			});
			toast(accept ? "You have accepted this deployment." : "Your answer has been sent.");
			navigate("/deployments");
		} catch (e) {
			setFailure(errorMessage(e, "That answer was not recorded."));
			setChoice(null);
		} finally {
			setBusy(false);
		}
	};

	return (
		<>
			<BackLink to="/deployments">My deployments</BackLink>

			<header className="mb-5">
				{/* The concept carries a "respond by" deadline here. A deployment
				    assignment has no such field — see the report — so this states
				    what the record does hold: when the invitation was sent. */}
				<p className="text-[11.5px] font-bold uppercase tracking-[0.12em] text-muted">
					{row.invited_on ? `Invited ${formatDate(row.invited_on)}` : "Deployment request"}
				</p>
				<h1 className="mt-2 font-display text-[26px] font-bold leading-[1.15] tracking-[-0.025em] text-ink sm:text-[29px]">
					{terms.tor_name || deployment.name}
				</h1>
				<p className="mt-2 text-[12.5px] text-slate-body">
					{[
						deployment.name,
						row.role,
						row.start_date ? dateRange(row.start_date, row.end_date) : null,
					]
						.filter(Boolean)
						.join(" · ")}
				</p>
			</header>

			{failure && (
				<div className="mb-4">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<div className="grid grid-cols-1 items-start gap-[18px] lg:grid-cols-[minmax(0,1fr)_320px]">
				<div className="min-w-0 space-y-[18px]">
					<section className="rounded-xl bg-rail-soft p-6 text-white">
						<h2 className="font-display text-[16px] font-bold tracking-[-0.01em]">
							You have been selected
						</h2>
						<p className="mt-2 text-[12.5px] leading-relaxed text-white/70">
							{terms.purpose ||
								deployment.notes ||
								"Read the assignment and its Terms of Reference before responding."}
						</p>
						<dl className="mt-5 grid gap-4 border-t border-white/15 pt-5 sm:grid-cols-3">
							<Stat label="Duration" value={duration ? `${duration} days` : "To be confirmed"} />
							<Stat
								label="Reporting date"
								value={row.start_date ? formatDate(row.start_date) : "To be confirmed"}
							/>
							<Stat
								label="Location"
								value={
									branchPath(terms.geo_scope_path) ||
									branchPath(deployment.geo_node) ||
									deployment.geo_node ||
									"—"
								}
							/>
						</dl>
					</section>

					<Card>
						<h2 className="mb-4 font-display text-[15px] font-bold tracking-[-0.01em] text-ink">
							Your assignment
						</h2>
						<Facts
							columns={2}
							items={[
								{ label: "Role", value: row.role || "Volunteer" },
								coordinator
									? {
											label: "Reports to",
											value: [coordinator.designation, coordinator.full_name]
												.filter(Boolean)
												.join(" — "),
										}
									: null,
								{
									label: "Location",
									value:
										branchPath(terms.geo_scope_path) ||
										branchPath(deployment.geo_node) ||
										deployment.geo_node ||
										"—",
								},
								{
									label: "Dates",
									value: row.start_date
										? (dateRange(row.start_date, row.end_date) ?? "—")
										: "To be confirmed",
								},
							]}
						/>
					</Card>

					{terms.responsibilities && (
						<Card>
							<h2 className="mb-3 font-display text-[15px] font-bold tracking-[-0.01em] text-ink">
								What you will do
							</h2>
							<p className="whitespace-pre-line text-[12.5px] leading-relaxed text-slate-body">
								{terms.responsibilities}
							</p>
						</Card>
					)}

					<Card pad={false}>
						<div className="flex flex-wrap items-start justify-between gap-3 border-b border-card-line p-5">
							<div>
								<h2 className="font-display text-[15px] font-bold tracking-[-0.01em] text-ink">
									Terms of Reference
								</h2>
								<p className="mt-1 text-[11.5px] text-muted">
									{[terms.tor_key, terms.is_submitted ? "approved" : "draft"]
										.filter(Boolean)
										.join(" · ")}
								</p>
							</div>
							{terms.is_submitted && (
								<a
									href={termsPdfUrl(terms.name)}
									target="_blank"
									rel="noreferrer"
									className="text-[12px] font-bold text-blue hover:text-blue-hover"
								>
									Download PDF ↗
								</a>
							)}
						</div>

						<div className="p-5">
							<MissionTerms terms={terms} />
						</div>

						{!answered && (
							<label className="m-5 mt-0 flex items-start gap-3 rounded-lg border border-card-line bg-canvas p-4 text-[12px] leading-relaxed text-slate-strong">
								<input
									type="checkbox"
									checked={read}
									onChange={(event) => setRead(event.target.checked)}
									className="mt-0.5 h-4 w-4 flex-none accent-rail"
								/>
								<span>I have read and understood the Terms of Reference for this deployment.</span>
							</label>
						)}
					</Card>
				</div>

				<aside className="space-y-[18px] lg:sticky lg:top-[72px]">
					{location && location.latitude != null && location.longitude != null && (
						<Card pad={false}>
							<OsmMap
								latitude={location.latitude}
								longitude={location.longitude}
								label={location.location_name}
								height={180}
								className="rounded-b-none border-0 border-b border-card-line"
							/>
							<div className="p-4">
								<span className="block text-[10px] font-bold uppercase tracking-[0.1em] text-rail-label">
									Meeting and reporting point
								</span>
								<strong className="mt-1.5 block text-[12.5px] font-semibold text-ink">
									{location.location_name}
								</strong>
								{location.address && (
									<small className="mt-1 block text-[11.5px] text-slate-body">
										{location.address}
									</small>
								)}
								<a
									href={`https://www.openstreetmap.org/?mlat=${location.latitude}&mlon=${location.longitude}#map=15/${location.latitude}/${location.longitude}`}
									target="_blank"
									rel="noreferrer"
									className="mt-2 inline-block text-[11.5px] font-bold text-blue hover:text-blue-hover"
								>
									Open turn-by-turn directions ↗
								</a>
							</div>
						</Card>
					)}

					<Card>
						<span className="text-[10px] font-bold uppercase tracking-[0.1em] text-warning">
							Your response
						</span>
						<h2 className="mt-2 font-display text-[16px] font-bold tracking-[-0.01em] text-ink">
							{answered ? "You have answered" : "Can you take part?"}
						</h2>

						{answered ? (
							<>
								<p className="mt-2 text-[12.5px] leading-relaxed text-slate-body">
									You answered {row.responded_on ? formatDate(row.responded_on) : "this request"}.
								</p>
								<div className="mt-3">
									<StatusBadge state={row.status} />
								</div>
							</>
						) : (
							<>
								<p className="mt-2 text-[12.5px] leading-relaxed text-slate-body">
									Answer before the deadline. Whoever asked is told either way, and an answer
									cannot be changed here afterwards.
								</p>

								<label className="mt-4 block">
									<span className="mb-1.5 block text-[12px] font-semibold text-slate-strong">
										Anything to say (optional)
									</span>
									<textarea
										value={note}
										onChange={(event) => setNote(event.target.value)}
										placeholder="If you cannot go, it helps to say why."
										className="min-h-[68px] w-full resize-y rounded-xl border border-card-line px-3.5 py-2.5 text-[13px] leading-relaxed outline-none transition focus:border-blue"
									/>
								</label>

								<div className="mt-3 space-y-2">
									<Button
										className="w-full"
										disabled={!read || busy}
										onClick={() => setChoice("accept")}
									>
										Accept deployment
									</Button>
									<Button
										tone="quiet"
										className="w-full"
										disabled={busy}
										onClick={() => setChoice("decline")}
									>
										I cannot take part
									</Button>
								</div>

								{!read && (
									<p className="mt-2 text-[11px] text-muted">
										Tick the Terms of Reference above before accepting.
									</p>
								)}
							</>
						)}

						{coordinator && (
							<p className="mt-4 border-t border-card-line pt-4 text-[11.5px] leading-relaxed text-muted">
								Coordinator: {coordinator.full_name}
								{coordinator.phone_number ? ` · ${coordinator.phone_number}` : ""}
							</p>
						)}
					</Card>
				</aside>
			</div>

			<Modal
				open={choice === "accept"}
				onClose={() => setChoice(null)}
				title="Accept this deployment?"
				footer={
					<>
						<Button tone="quiet" onClick={() => setChoice(null)} disabled={busy}>
							Go back
						</Button>
						<Button busy={busy} onClick={() => void respond(true)}>
							Confirm acceptance
						</Button>
					</>
				}
			>
				<p>
					You confirm that you are available
					{row.start_date ? ` from ${dateRange(row.start_date, row.end_date)}` : ""} and agree to
					the Terms of Reference as they are written above.
				</p>
			</Modal>

			<Modal
				open={choice === "decline"}
				onClose={() => setChoice(null)}
				title="Decline this deployment?"
				footer={
					<>
						<Button tone="quiet" onClick={() => setChoice(null)} disabled={busy}>
							Cancel
						</Button>
						<Button tone="danger" busy={busy} disabled={!reason} onClick={() => void respond(false)}>
							Send decline response
						</Button>
					</>
				}
			>
				<p>
					Tell the coordinator why you cannot take part. This will not affect future
					opportunities.
				</p>
				<label className="mt-4 block">
					<span className="mb-1.5 block text-[12px] font-semibold text-slate-strong">Reason</span>
					<select
						value={reason}
						onChange={(event) => setReason(event.target.value)}
						className="w-full rounded-xl border border-card-line bg-white px-3.5 py-2.5 text-[13px] text-ink outline-none transition focus:border-blue"
					>
						<option value="">Select a reason</option>
						{DECLINE_REASONS.map((option) => (
							<option key={option} value={option}>
								{option}
							</option>
						))}
					</select>
				</label>
				<label className="mt-3 block">
					<span className="mb-1.5 block text-[12px] font-semibold text-slate-strong">
						Optional note
					</span>
					<textarea
						value={note}
						onChange={(event) => setNote(event.target.value)}
						placeholder="Add a short note for the coordinator"
						className="min-h-[68px] w-full resize-y rounded-xl border border-card-line px-3.5 py-2.5 text-[13px] leading-relaxed outline-none transition focus:border-blue"
					/>
				</label>
			</Modal>
		</>
	);
}

function Stat({ label, value }: { label: string; value: string }) {
	return (
		<div>
			<dt className="text-[10px] font-bold uppercase tracking-[0.09em] text-white/55">{label}</dt>
			<dd className="mt-1.5 text-[13px] font-semibold">{value}</dd>
		</div>
	);
}

/* ----------------------------------------------------------------- record */

type RecordTab = "overview" | "terms" | "documents" | "activity";

/**
 * One mission's permanent file: what it was, the terms it stood on, the
 * documents it produced and the service filed against it.
 *
 * Reachable for any deployment on this person's own record — the read behind it
 * is `my_deployments`, which is possessive, so a docname somebody guessed
 * answers with nothing.
 */
export function DeploymentRecord() {
	const { name = "" } = useParams();
	const points = usePublishedPoints();

	const history = useFrappeGetCall<{
		message: { volunteer: string; deployments: (DeploymentSummary & { title: string })[] } | null;
	}>(API.myDeployments, undefined, "portal:my_deployments");

	const invitations = useFrappeGetCall<{
		message: {
			volunteer: string;
			waiting: DeploymentInvitation[];
			answered: DeploymentInvitation[];
		} | null;
	}>(API.myInvitations, undefined, "portal:my_invitations");

	const logs = useFrappeGetCall<{ message: MyTimeLogs | null }>(
		API.myTimeLogs,
		undefined,
		"portal:my_time_logs",
	);

	const [tab, setTab] = useState<RecordTab>("overview");

	const row = history.data?.message?.deployments.find((d) => d.name === name) ?? null;
	const assignment =
		[
			...(invitations.data?.message?.answered ?? []),
			...(invitations.data?.message?.waiting ?? []),
		].find((a) => a.deployment === name) ?? null;

	const mission = useFrappeGetCall<{ message: MyAssignment }>(
		API.getMyAssignment,
		assignment ? { assignment: assignment.assignment } : undefined,
		assignment ? `portal:assignment:${assignment.assignment}` : null,
	);
	const terms = mission.data?.message?.terms ?? null;

	if (history.isLoading || invitations.isLoading) {
		return <Spinner page label="Opening the mission file…" />;
	}

	if (!row && !assignment) {
		return (
			<>
				<BackLink to="/deployments">My deployments</BackLink>
				<Empty icon={Icon.file} title="That deployment is not on your record">
					You can only open a mission you were assigned to. If you expected to find one here, ask
					your coordinator.
				</Empty>
			</>
		);
	}

	const title = row?.title ?? assignment?.title ?? name;
	const status = row?.status ?? assignment?.deployment_status ?? "";
	const start = row?.start_date ?? assignment?.start_date ?? null;
	const end = row?.end_date ?? assignment?.end_date ?? null;
	const location = points(row?.geo_node ?? assignment?.geo_node ?? null);

	const served = (logs.data?.message?.recent ?? [])
		.filter((log) => log.deployment === name)
		.reduce((sum, log) => sum + (log.hours || 0), 0);

	return (
		<>
			<BackLink to="/deployments">My deployments</BackLink>

			<header className="mb-5 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
				<div className="min-w-0">
					<h1 className="font-display text-[26px] font-bold leading-[1.15] tracking-[-0.025em] text-ink sm:text-[29px]">
						{title}
					</h1>
					<p className="mt-2 flex flex-wrap items-center gap-2.5 text-[12.5px] text-slate-body">
						{status && <StatusBadge state={status} />}
						<span>
							{[name, assignment?.role, dateRange(start, end)].filter(Boolean).join(" · ")}
						</span>
					</p>
				</div>
			</header>

			<Tabs
				tabs={[
					{ key: "overview", label: "Overview" },
					{ key: "terms", label: "Terms of Reference" },
					{ key: "documents", label: "Documents" },
					{ key: "activity", label: "Activity" },
				]}
				active={tab}
				onSelect={(key) => setTab(key as RecordTab)}
			/>

			<div className="grid grid-cols-1 items-start gap-[18px] lg:grid-cols-[minmax(0,1fr)_320px]">
				<div className="min-w-0 space-y-[18px]">
					{tab === "overview" && (
						<>
							<Card>
								<h2 className="mb-3 font-display text-[15px] font-bold tracking-[-0.01em] text-ink">
									The mission
								</h2>
								<p className="text-[12.5px] leading-relaxed text-slate-body">
									{terms?.purpose ??
										(mission.isLoading
											? "Loading the mission document…"
											: "This mission is retained as part of your verified service history.")}
								</p>
							</Card>

							{terms && terms.itinerary.length > 0 && (
								<Card>
									<h2 className="mb-3 font-display text-[15px] font-bold tracking-[-0.01em] text-ink">
										Schedule
									</h2>
									<dl className="space-y-2.5">
										{terms.itinerary.map((entry, index) => (
											<div key={index} className="flex flex-wrap gap-x-4 gap-y-1">
												<dt className="w-[120px] flex-none text-[12px] font-semibold text-ink">
													{entry.activity_date ? formatDate(entry.activity_date) : "—"}
												</dt>
												<dd className="min-w-0 flex-1 text-[12.5px] text-slate-body">
													{entry.activity}
													{entry.person_responsible ? ` (${entry.person_responsible})` : ""}
												</dd>
											</div>
										))}
									</dl>
								</Card>
							)}

							{terms && terms.stakeholders.length > 0 && (
								<Card>
									<h2 className="mb-3 font-display text-[15px] font-bold tracking-[-0.01em] text-ink">
										Contacts
									</h2>
									<ul className="divide-y divide-card-line">
										{terms.stakeholders.map((person, index) => (
											<li key={index} className="flex flex-wrap items-center justify-between gap-2 py-3">
												<span className="min-w-0">
													<strong className="block text-[12.5px] font-semibold text-ink">
														{person.full_name || person.designation}
													</strong>
													<small className="block text-[11.5px] text-muted">
														{person.designation}
													</small>
												</span>
												{person.phone_number && (
													<a
														href={`tel:${person.phone_number}`}
														className="text-[12px] font-bold text-blue hover:text-blue-hover"
													>
														{person.phone_number}
													</a>
												)}
											</li>
										))}
									</ul>
								</Card>
							)}
						</>
					)}

					{tab === "terms" && (
						<Card>
							<h2 className="mb-3 font-display text-[15px] font-bold tracking-[-0.01em] text-ink">
								Terms of Reference
							</h2>
							{mission.isLoading ? (
								<Spinner label="Loading the terms…" />
							) : terms ? (
								<>
									<MissionTerms terms={terms} />
									{terms.is_submitted && (
										<a
											href={termsPdfUrl(terms.name)}
											target="_blank"
											rel="noreferrer"
											className="mt-4 inline-flex items-center gap-2 text-[12px] font-bold text-blue hover:text-blue-hover"
										>
											<Icon.file size={14} /> Open the full terms of reference ↗
										</a>
									)}
								</>
							) : (
								<p className="text-[12.5px] text-muted">
									No terms of reference are attached to your assignment on this mission.
								</p>
							)}
						</Card>
					)}

					{tab === "documents" && (
						<Card>
							<h2 className="mb-2 font-display text-[15px] font-bold tracking-[-0.01em] text-ink">
								Documents
							</h2>
							<p className="mb-3 text-[12.5px] text-slate-body">
								Everything connected to this mission stays in its permanent file.
							</p>
							{terms?.is_submitted ? (
								<a
									href={termsPdfUrl(terms.name)}
									target="_blank"
									rel="noreferrer"
									className="flex items-center gap-3 border-t border-card-line py-3.5"
								>
									<span
										className="grid h-9 w-9 flex-none place-items-center rounded-lg bg-blue-soft text-[9px] font-bold text-blue-press"
										aria-hidden="true"
									>
										PDF
									</span>
									<span className="min-w-0 flex-1">
										<strong className="block truncate text-[12.5px] font-semibold text-ink">
											Terms of Reference — {terms.tor_name}
										</strong>
										<small className="block text-[11.5px] text-muted">{terms.tor_key}</small>
									</span>
									<span className="flex-none text-[11.5px] font-bold text-blue">Download</span>
								</a>
							) : (
								<p className="text-[12.5px] text-muted">
									No signed document has been published for this mission yet.
								</p>
							)}
						</Card>
					)}

					{tab === "activity" && (
						<Card>
							<h2 className="mb-3 font-display text-[15px] font-bold tracking-[-0.01em] text-ink">
								Activity
							</h2>
							<ol className="space-y-3">
								{assignment?.invited_on && (
									<Activity title="Invited to this mission" when={assignment.invited_on} />
								)}
								{assignment?.responded_on && (
									<Activity
										title={`You ${(assignment.response || "answered").toLowerCase()}`}
										when={assignment.responded_on}
									/>
								)}
								{start && <Activity title="Deployment started" when={start} />}
								{end && <Activity title="Deployment ended" when={end} />}
								{served > 0 && (
									<Activity
										title={`${formatHours(served)} service hours verified`}
										when={null}
										note="Hours are added once a coordinator verifies a completed deployment."
									/>
								)}
							</ol>
						</Card>
					)}
				</div>

				<aside className="space-y-[18px] lg:sticky lg:top-[72px]">
					{location && location.latitude != null && location.longitude != null && (
						<Card pad={false}>
							<OsmMap
								latitude={location.latitude}
								longitude={location.longitude}
								label={location.location_name}
								height={180}
								className="rounded-b-none border-0 border-b border-card-line"
							/>
							<div className="p-4">
								<span className="block text-[10px] font-bold uppercase tracking-[0.1em] text-rail-label">
									Reporting location
								</span>
								<strong className="mt-1.5 block text-[12.5px] font-semibold text-ink">
									{location.location_name}
								</strong>
								<a
									href={`https://www.openstreetmap.org/?mlat=${location.latitude}&mlon=${location.longitude}#map=13/${location.latitude}/${location.longitude}`}
									target="_blank"
									rel="noreferrer"
									className="mt-2 inline-block text-[11.5px] font-bold text-blue hover:text-blue-hover"
								>
									Get directions ↗
								</a>
							</div>
						</Card>
					)}

					<Card>
						<h2 className="mb-3.5 font-display text-[14px] font-bold tracking-[-0.01em] text-ink">
							Mission record
						</h2>
						<FactList
							items={[
								assignment?.role ? { label: "Role", value: assignment.role } : null,
								{ label: "Dates", value: dateRange(start, end) ?? "Undated" },
								{
									label: "Location",
									value: branchPath(row?.geo_path) || row?.geo_node || "—",
								},
								terms ? { label: "Terms of Reference", value: terms.tor_name } : null,
								{
									label: "Service hours",
									value:
										served > 0 ? (
											<span className="text-success">{formatHours(served)} hours verified</span>
										) : (
											"None recorded yet"
										),
								},
							]}
						/>
						<Link
							to="/hours"
							className="mt-4 inline-block text-[12px] font-bold text-blue hover:text-blue-hover"
						>
							Your service hours →
						</Link>
					</Card>

					{served === 0 && (
						<Notice>
							Service hours are added once a coordinator verifies a completed deployment. Nothing is
							missing from your record if this mission is still running.
						</Notice>
					)}
				</aside>
			</div>
		</>
	);
}

function Activity({
	title,
	when,
	note,
}: {
	title: string;
	when: string | null;
	note?: string;
}) {
	return (
		<li className="border-l-2 border-card-line pl-4">
			<strong className="block text-[12.5px] font-semibold text-ink">{title}</strong>
			{when && <span className="mt-0.5 block text-[11.5px] text-muted">{formatDate(when)}</span>}
			{note && <span className="mt-0.5 block text-[11.5px] text-muted">{note}</span>}
		</li>
	);
}

/* --------------------------------------------------------------- mission */

/** The submitted terms of reference, section by section, in its own words. */
function MissionTerms({ terms }: { terms: TermsMission }) {
	return (
		<div className="space-y-4">
			{terms.mission_background && (
				<Part title="Background">
					<div
						className="article-body text-[12.5px] leading-relaxed text-slate-body"
						// eslint-disable-next-line react/no-danger
						dangerouslySetInnerHTML={{ __html: terms.mission_background }}
					/>
				</Part>
			)}
			{terms.purpose && <Part title="Purpose">{terms.purpose}</Part>}
			{terms.responsibilities && (
				<Part title="Reporting and supervision">
					<span className="whitespace-pre-line">{terms.responsibilities}</span>
				</Part>
			)}
			{terms.objectives.length > 0 && (
				<Part title="Objectives">
					<ol className="list-decimal space-y-1 pl-4">
						{terms.objectives.map((row, i) => (
							<li key={i}>{row.objective}</li>
						))}
					</ol>
				</Part>
			)}
			{terms.expected_outputs.length > 0 && (
				<Part title="Key deliverables">
					<ul className="list-disc space-y-1 pl-4">
						{terms.expected_outputs.map((row, i) => (
							<li key={i}>{row.output}</li>
						))}
					</ul>
				</Part>
			)}
			{terms.itinerary.length > 0 && (
				<Part title="The plan, day by day">
					<ul className="space-y-1">
						{terms.itinerary.map((row, i) => (
							<li key={i}>
								<span className="font-semibold text-ink">
									{row.activity_date ? formatDate(row.activity_date) : "—"}
								</span>
								{row.activity_time ? ` ${row.activity_time.slice(0, 5)}` : ""} · {row.activity}
								{row.person_responsible ? ` (${row.person_responsible})` : ""}
							</li>
						))}
					</ul>
				</Part>
			)}
			{terms.stakeholders.length > 0 && (
				<Part title="Who you would be dealing with">
					<ul className="space-y-1">
						{terms.stakeholders.map((row, i) => (
							<li key={i}>
								<span className="font-semibold text-ink">{row.designation}</span>
								{row.full_name ? ` — ${row.full_name}` : ""}
								{row.phone_number ? ` · ${row.phone_number}` : ""}
							</li>
						))}
					</ul>
				</Part>
			)}
			{terms.resources.length > 0 && (
				<Part title="Support provided">
					<ul className="list-disc space-y-1 pl-4">
						{terms.resources.map((row, i) => (
							<li key={i}>
								{row.resource}
								{row.quantity ? ` — ${row.quantity}${row.unit ? ` ${row.unit}` : ""}` : ""}
							</li>
						))}
					</ul>
				</Part>
			)}
			<p className="text-[11px] text-slate-faint">
				{terms.tor_name} · {terms.tor_key}
			</p>
		</div>
	);
}

function Part({ title, children }: { title: string; children: ReactNode }) {
	return (
		<div className="border-t border-card-line pt-3.5 first:border-t-0 first:pt-0">
			<p className="text-[11px] font-bold uppercase tracking-[0.07em] text-rail-label">{title}</p>
			<div className="mt-1.5 text-[12.5px] leading-relaxed text-slate-body">{children}</div>
		</div>
	);
}

/* ------------------------------------------------------------------ utils */

function dayCount(from: string, to: string): number {
	const a = new Date(`${from}T00:00:00`).getTime();
	const b = new Date(`${to}T00:00:00`).getTime();
	if (Number.isNaN(a) || Number.isNaN(b)) return 0;
	return Math.max(1, Math.round((b - a) / 86_400_000) + 1);
}

/** A start–end date span, collapsed to one date when they are the same. */
function dateRange(from: string | null, to: string | null): string | null {
	if (!from) return null;
	if (!to || to === from) return formatDate(from);
	return `${formatDate(from)} – ${formatDate(to)}`;
}
