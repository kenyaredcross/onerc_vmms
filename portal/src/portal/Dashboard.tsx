import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableImage, EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { branchPath, formatClock, formatDate, formatHours } from "../lib/format";
import { firstName, useSession } from "../lib/session";
import { Icon } from "../ui/icons";
import { AvailabilityNudge } from "./chrome/AvailabilityNudge";
import {
	Card,
	Empty,
	ErrorNote,
	SectionHead,
	Skeleton,
	StatTile,
	StatusBadge,
	StatusChip,
	cx,
} from "./ui/kit";
import type {
	DeploymentInvitation,
	EventCard,
	MembershipRow,
	MyTimeLogs,
	OpenRegistration,
	TaskSummary,
	VolunteerProfile,
} from "./types";

/**
 * The volunteer's front page.
 *
 * **One page, six standings, and the live record decides which.** The approved
 * concept draws home differently for somebody who has not started, somebody
 * mid-application, somebody waiting on a branch, somebody who has been asked
 * for a correction, and an active volunteer. Every one of those is a fact this
 * app already holds — an open registration and its state, a volunteer record, a
 * membership — so the page reads them rather than asking anybody which they
 * are.
 *
 * **The most important next action, first.** A deployment request waiting on an
 * answer, or a task a coordinator has sent back — whichever is live sits at the
 * top of the left column. Then what is coming, then the record this person
 * holds down the right.
 *
 * **Nothing is offered twice.** Somebody who already holds an approved
 * volunteer record is never shown "register as a volunteer"; somebody whose
 * membership application is with a branch is never invited to apply again.
 * Every read is possessive and takes no argument, so there is no permission
 * check in this file to get wrong.
 */
export default function Dashboard() {
	const { user } = useSession();

	const volunteer = useFrappeGetCall<{ message: VolunteerProfile | null }>(
		API.myVolunteer,
		undefined,
		"portal:my_volunteer",
	);
	const memberships = useFrappeGetCall<{ message: MembershipRow[] }>(
		API.myMemberships,
		undefined,
		"portal:my_memberships",
	);
	const logs = useFrappeGetCall<{ message: MyTimeLogs | null }>(
		API.myTimeLogs,
		undefined,
		"portal:my_time_logs",
	);
	const tasks = useFrappeGetCall<{ message: { volunteer: string; tasks: TaskSummary[] } | null }>(
		API.myTasks,
		{ include_closed: 0 },
		"portal:my_tasks:false",
	);
	const open = useFrappeGetCall<{ message: Record<string, OpenRegistration | null> }>(
		API.myOpenRegistrations,
		undefined,
		"portal:open_registrations",
	);
	const invitations = useFrappeGetCall<{
		message: {
			volunteer: string;
			waiting: DeploymentInvitation[];
			answered: DeploymentInvitation[];
		} | null;
	}>(API.myInvitations, undefined, "portal:my_invitations");
	const upcoming = useFrappeGetCall<{ message: { available: boolean; events: EventCard[] } }>(
		API.eventsUpcoming,
		undefined,
		"portal:events_upcoming",
	);

	const profile = volunteer.data?.message ?? null;
	const rows = memberships.data?.message ?? [];
	const time = logs.data?.message ?? null;
	const work = tasks.data?.message?.tasks ?? [];
	const waiting = invitations.data?.message?.waiting ?? [];
	const answered = invitations.data?.message?.answered ?? [];
	const events = upcoming.data?.message?.events ?? [];
	const openVolunteer = open.data?.message?.volunteer ?? null;
	const openMember = open.data?.message?.member ?? null;
	const pending = [openVolunteer, openMember].filter(Boolean) as OpenRegistration[];

	const request = waiting[0] ?? null;
	const attention = attentionTasks(work);
	const greeting = firstName(profile?.full_name?.trim() || user);
	const standing = standingOf(profile, rows, openVolunteer, openMember);

	// The concept's "choose a path" card, and the one rule that governs it: a
	// path is offered only where this person holds neither the record nor an
	// undecided application for it.
	const offerVolunteer = !profile && !openVolunteer;
	const offerMember = rows.length === 0 && !openMember;
	const settled = !volunteer.isLoading && !memberships.isLoading && !open.isLoading;

	return (
		<>
			<header className="mb-5 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
				<div className="min-w-0">
					<p className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-muted">
						{new Date().toLocaleDateString(undefined, {
							weekday: "long",
							day: "numeric",
							month: "long",
						})}
					</p>
					<h1 className="mt-2 font-display text-[28px] font-bold leading-[1.15] tracking-[-0.03em] text-ink sm:text-[31px]">
						{partOfDay()}
						{greeting ? (
							<>
								, <span className="text-red">{greeting}.</span>
							</>
						) : (
							"."
						)}
					</h1>
				</div>
				{settled && <StatusChip tone={standing.tone}>{standing.label}</StatusChip>}
			</header>

			<Welcome standing={standing.key} profile={profile} greeting={greeting} />

			{volunteer.error && (
				<div className="mb-5">
					<ErrorNote>{errorMessage(volunteer.error)}</ErrorNote>
				</div>
			)}

			<div className="flex flex-col gap-[22px] lg:grid lg:grid-cols-[minmax(0,1fr)_330px] lg:items-start">
				{/* ------------------------------------------------------------- left */}
				<div className="flex min-w-0 flex-col gap-[22px]">
					{pending.map((row) => (
						<Application key={row.name} row={row} />
					))}

					{/* Only where nothing is already in front of a branch: a person
					    mid-application is not choosing a path, they are finishing one. */}
					{settled && pending.length === 0 && (offerVolunteer || offerMember) && (
						<ChoiceCard offerVolunteer={offerVolunteer} offerMember={offerMember} />
					)}

					{profile && (
						<div className="grid gap-3.5 sm:grid-cols-3">
							<StatTile
								label="Open tasks"
								value={tasks.isLoading ? "—" : work.length}
								to="/tasks"
								linkLabel="View tasks"
							/>
							<StatTile
								label="Response needed"
								value={invitations.isLoading ? "—" : waiting.length}
								to="/deployments"
								linkLabel="Deployment requests"
								urgent={waiting.length > 0}
							/>
							<StatTile
								label="Verified service"
								value={logs.isLoading ? "—" : `${formatHours(time?.total_hours ?? 0)}h`}
								to="/hours"
								linkLabel="View hours"
							/>
						</div>
					)}

					{request && <Focus request={request} />}

					{/* Only for somebody who can have work. A task is assigned to a
					    volunteer record, so "nothing is waiting on you" over an empty
					    list is noise on the one screen a new arrival reads. */}
					{(profile || work.length > 0) && (
						<Card pad={false}>
							<SectionHead
								title="Needs your attention"
								link={{ to: "/tasks", label: "All tasks" }}
							/>
							<div>
								{tasks.isLoading ? (
									<div className="space-y-2 p-4">
										<Skeleton className="h-11" />
										<Skeleton className="h-11" />
									</div>
								) : attention.length > 0 ? (
									<ul className="divide-y divide-card-line">
										{attention.slice(0, 4).map((row) => (
											<li key={row.name}>
												<Link
													to={`/tasks/${encodeURIComponent(row.name)}`}
													className="flex items-center gap-3.5 px-[22px] py-3.5 transition hover:bg-canvas"
												>
													<span
														className={cx(
															"grid h-9 w-9 flex-none place-items-center rounded-lg",
															row.open_question || row.is_overdue
																? "bg-red-soft text-red-ink"
																: "bg-blue-soft text-blue-press",
														)}
														aria-hidden="true"
													>
														<Icon.check size={16} />
													</span>
													<span className="min-w-0 flex-1">
														<strong className="block truncate text-[13px] font-semibold text-ink">
															{row.subject}
														</strong>
														<span className="mt-0.5 block truncate text-[11.5px] text-muted">
															{taskMeta(row)}
														</span>
													</span>
													<StatusBadge state={row.status} />
												</Link>
											</li>
										))}
									</ul>
								) : (
									<Empty framed={false} icon={Icon.check} title="Nothing is waiting on you">
										A coordinator in your branch can assign you a piece of work, and it will arrive
										here and in your notifications.
									</Empty>
								)}
							</div>
						</Card>
					)}

					<Card pad={false}>
						<SectionHead
							title="Coming up near you"
							link={{ to: "/calendar", label: "View calendar →" }}
						/>
						<div>
							{upcoming.isLoading ? (
								<Skeleton className="m-4 h-28" />
							) : (
								<ComingUp events={events} work={work} deployments={answered} />
							)}
						</div>
					</Card>
				</div>

				{/* ------------------------------------------------------------ right */}
				<div className="flex flex-col gap-[22px]">
					<AvailabilityNudge />

					{settled && standing.key === "new" && <Checklist />}

					<Card pad={false}>
						<SectionHead title="Your record" />
						<RecordVolunteer
							profile={profile}
							applied={Boolean(openVolunteer)}
							loading={volunteer.isLoading}
						/>
						<RecordMembership
							rows={rows}
							applied={Boolean(openMember)}
							loading={memberships.isLoading}
						/>
						<RecordHours time={time} loading={logs.isLoading} />
					</Card>

					<Card pad={false}>
						<SectionHead title="Discover" />
						<Discover
							to="/opportunities"
							label={
								<EditableText
									k="portal.home.discover.opportunities"
									fallback="Browse opportunities"
								/>
							}
						/>
						<Discover
							to="/events"
							label={
								events.length > 0
									? `${events.length} ${events.length === 1 ? "event" : "events"} coming up`
									: "Upcoming events"
							}
						/>
						<Discover
							to="/stories"
							label={<EditableText k="portal.home.discover.stories" fallback="Volunteer stories" />}
						/>
					</Card>
				</div>
			</div>
		</>
	);
}

/* --------------------------------------------------------------- standing */

type StandingKey = "new" | "draft" | "review" | "action" | "active" | "member";

interface Standing {
	key: StandingKey;
	label: string;
	tone: "info" | "warning" | "danger" | "success" | "neutral";
}

/**
 * Where this person stands, from the records themselves.
 *
 * `reviewed` is the server's own answer to the one ambiguity: a `Draft` nobody
 * has submitted and a `Draft` an approver sent back are the same word for two
 * opposite situations.
 */
function standingOf(
	profile: VolunteerProfile | null,
	memberships: MembershipRow[],
	openVolunteer: OpenRegistration | null,
	openMember: OpenRegistration | null,
): Standing {
	const application = openVolunteer ?? openMember;

	if (application) {
		if (application.state === "Draft") {
			return application.reviewed
				? { key: "action", label: "Action required", tone: "danger" }
				: { key: "draft", label: "Application in progress", tone: "warning" };
		}
		return { key: "review", label: "Application under review", tone: "info" };
	}

	if (profile) return { key: "active", label: `${profile.status} volunteer`, tone: "success" };
	if (memberships.some((row) => row.is_active)) {
		return { key: "member", label: "Active member", tone: "success" };
	}
	if (memberships.length > 0) {
		return { key: "member", label: "Membership not active yet", tone: "warning" };
	}

	return { key: "new", label: "Registration not started", tone: "neutral" };
}

/* ---------------------------------------------------------------- welcome */

const WELCOME: Record<StandingKey, { eyebrow: string; lead: string; accent: string }> = {
	new: {
		eyebrow: "Welcome to your portal",
		lead: "Join as a volunteer, become a member, or do both. Choose a path and we will guide you step by step.",
		accent: "serve.",
	},
	draft: {
		eyebrow: "Welcome back",
		lead: "Pick up exactly where you stopped. Your profile, documents and completed answers are still here.",
		accent: "saved",
	},
	review: {
		eyebrow: "Your application is in",
		lead: "There is nothing you need to do right now. We will tell you as soon as the review moves forward, or if something is needed.",
		accent: "branch.",
	},
	action: {
		eyebrow: "A reviewer has replied",
		lead: "Your application has come back to you so you can correct what was asked for without starting again.",
		accent: "moving.",
	},
	active: {
		eyebrow: "Your volunteer workspace",
		lead: "Today's work, deployment requests, your readiness and your service record, together in one place.",
		accent: "impact",
	},
	member: {
		eyebrow: "Your member account",
		lead: "Your membership, the events you can join, and everything the society is doing near you.",
		accent: "member.",
	},
};

/** `[before the accent word, after it]`. The accent itself lives in `WELCOME`. */
const HEADLINE: Record<StandingKey, [string, string]> = {
	new: ["Start where your heart wants to", ""],
	draft: ["Your application is", " and waiting."],
	review: ["Your application is with your", ""],
	action: ["One update will keep your application", ""],
	active: ["Ready to make an", ", {name}?"],
	member: ["Thank you for standing with us as a", ""],
};

/**
 * The navy hero. Its photograph is a content block, so a society sets its own
 * and one that has not set anything gets the gradient rather than a broken
 * image or somebody else's picture.
 */
function Welcome({
	standing,
	profile,
	greeting,
}: {
	standing: StandingKey;
	profile: VolunteerProfile | null;
	greeting: string;
}) {
	const copy = WELCOME[standing];
	const [before, after] = HEADLINE[standing];

	return (
		<section className="relative mb-[22px] grid overflow-hidden rounded-2xl bg-rail text-white shadow-[0_12px_34px_rgba(1,30,65,0.10)] md:grid-cols-[1.05fr_0.95fr]">
			<div className="relative z-10 flex flex-col justify-center px-7 py-9 sm:px-10 sm:py-11">
				<p className="text-[10px] font-bold uppercase tracking-[0.14em] text-aqua">
					{standing === "active" && profile?.geo_path
						? `${branchPath(profile.geo_path)} · ${profile.volunteer}`
						: copy.eyebrow}
				</p>
				<h2 className="mt-3 max-w-[520px] font-display text-[30px] font-bold leading-[1.08] tracking-[-0.04em] sm:text-[38px]">
					{before} <em className="font-serif font-normal not-italic text-aqua">{copy.accent}</em>
					{after.replace("{name}", greeting || "there")}
				</h2>
				<p className="mt-4 max-w-[520px] text-[13.5px] leading-relaxed text-white/70">
					{copy.lead}
				</p>
			</div>

			<div className="relative min-h-[120px] md:min-h-[300px]">
				<EditableImage k="portal.home.hero.image" fill />
				<span
					aria-hidden="true"
					className="absolute inset-0 bg-gradient-to-t from-rail via-rail/40 to-transparent md:bg-gradient-to-r md:from-rail md:via-rail/25 md:to-transparent"
				/>
			</div>
		</section>
	);
}

/* ------------------------------------------------------------ choice card */

function ChoiceCard({
	offerVolunteer,
	offerMember,
}: {
	offerVolunteer: boolean;
	offerMember: boolean;
}) {
	return (
		<Card className="grid items-center gap-8 p-7 sm:p-9 lg:grid-cols-[0.88fr_1.12fr]">
			<div>
				<p className="text-[10px] font-bold uppercase tracking-[0.15em] text-red">Your next step</p>
				<h2 className="mt-3 font-display text-[24px] font-bold leading-[1.16] tracking-[-0.03em] text-ink">
					<EditableText
						k="portal.home.choice.heading"
						fallback="How would you like to get involved?"
					/>
				</h2>
				<p className="mt-3.5 max-w-[390px] text-[12.5px] leading-relaxed text-slate-body">
					{offerVolunteer && offerMember
						? "Give your time as a volunteer or become a member of the society. You can add the other path later."
						: offerVolunteer
							? "You are already a member. Volunteering is a separate record, and you may hold both."
							: "You already volunteer with us. Membership is a separate record, and you may hold both."}
				</p>
			</div>

			<div className="grid gap-3">
				{offerVolunteer && (
					<Path
						to="/join?path=volunteer"
						primary
						icon={<Icon.heart size={19} />}
						title="Register as a volunteer"
						note="Serve communities with your time and skills"
					/>
				)}
				{offerMember && (
					<Path
						to="/membership"
						primary={!offerVolunteer}
						icon={<Icon.people size={19} />}
						title="Become a member"
						note="Join and support our humanitarian mission"
					/>
				)}
			</div>
		</Card>
	);
}

function Path({
	to,
	primary,
	icon,
	title,
	note,
}: {
	to: string;
	primary?: boolean;
	icon: ReactNode;
	title: string;
	note: string;
}) {
	return (
		<Link
			to={to}
			className={cx(
				"grid min-h-[76px] grid-cols-[42px_1fr_32px] items-center gap-3.5 rounded-2xl border px-4 py-2.5 transition hover:-translate-y-px hover:shadow-[0_8px_20px_rgba(1,30,65,0.07)] motion-reduce:hover:translate-y-0",
				primary ? "border-rail-soft bg-rail-soft text-white" : "border-card-line bg-white text-ink",
			)}
		>
			<span
				className="grid h-[42px] w-[42px] place-items-center rounded-xl bg-red text-white"
				aria-hidden="true"
			>
				{icon}
			</span>
			<span className="min-w-0">
				<strong className="block font-display text-[14px] font-bold tracking-[-0.01em]">
					{title}
				</strong>
				<small
					className={cx("mt-0.5 block text-[11px]", primary ? "text-white/60" : "text-slate-body")}
				>
					{note}
				</small>
			</span>
			<span
				aria-hidden="true"
				className={cx(
					"grid h-8 w-8 place-items-center rounded-full text-[15px]",
					primary ? "bg-white text-rail" : "bg-rail text-white",
				)}
			>
				→
			</span>
		</Link>
	);
}

/* ------------------------------------------------------------- checklist */

/** The concept's set-up ring, for somebody who has not started anything. */
function Checklist() {
	const steps = [
		{ label: "Account created", done: true },
		{ label: "Choose your path", done: false },
		{ label: "Complete registration", done: false },
		{ label: "Submit for review", done: false },
	];
	const done = steps.filter((step) => step.done).length;

	return (
		<Card className="p-[22px]">
			<div
				className="relative mb-4 grid h-[58px] w-[58px] place-items-center rounded-full text-blue"
				style={{
					background: `conic-gradient(currentColor ${(done / steps.length) * 360}deg, #E8EDF3 0)`,
				}}
				aria-hidden="true"
			>
				<span className="absolute inset-[6px] rounded-full bg-white" />
				<strong className="relative text-[12px] font-bold text-ink">
					{done}/{steps.length}
				</strong>
			</div>
			<h3 className="font-display text-[16px] font-bold tracking-[-0.02em] text-ink">
				Set up your record
			</h3>
			<p className="mt-2 text-[12px] leading-relaxed text-slate-body">
				Complete these steps to unlock opportunities matched to you.
			</p>
			<ul className="mt-5 space-y-3">
				{steps.map((step, index) => (
					<li key={step.label} className="flex items-center gap-2.5 text-[12px]">
						<span
							className={cx(
								"grid h-5 w-5 flex-none place-items-center rounded-full text-[10px] font-bold",
								step.done ? "bg-success text-white" : "bg-surface text-muted",
							)}
							aria-hidden="true"
						>
							{step.done ? "✓" : index + 1}
						</span>
						<span className={step.done ? "text-ink" : "text-slate-body"}>{step.label}</span>
					</li>
				))}
			</ul>
		</Card>
	);
}

/* ----------------------------------------------------------------- focus */

/** The one thing being asked of this person right now. */
function Focus({ request }: { request: DeploymentInvitation }) {
	const meta = [
		request.role || null,
		branchPath(request.geo_node) || request.geo_node || null,
		request.start_date
			? `${formatDate(request.start_date)}${
					request.end_date ? ` – ${formatDate(request.end_date)}` : ""
				}`
			: null,
	].filter(Boolean);

	return (
		<Card accent="danger" className="p-6 sm:p-7">
			<div className="flex flex-wrap items-start justify-between gap-x-5 gap-y-3">
				<div className="min-w-0">
					<p className="text-[10px] font-bold uppercase tracking-[0.15em] text-red">
						Your priority
					</p>
					<h3 className="mt-2.5 font-display text-[18px] font-bold leading-snug tracking-[-0.02em] text-ink">
						{request.title || request.deployment}
					</h3>
				</div>
				<span className="flex-none rounded-lg bg-red-soft px-2.5 py-1.5 text-[11px] font-bold text-red-ink">
					Awaiting your answer
				</span>
			</div>

			{meta.length > 0 && <p className="mt-2 text-[12px] text-slate-body">{meta.join(" · ")}</p>}
			{request.notes && (
				<p className="mt-2.5 line-clamp-2 max-w-2xl text-[12.5px] leading-relaxed text-slate-body">
					{request.notes}
				</p>
			)}

			<div className="mt-5 flex flex-wrap gap-2.5">
				<Link
					to={`/deployments/requests/${encodeURIComponent(request.assignment)}`}
					className="inline-flex min-h-[42px] items-center rounded-lg bg-rail px-4 text-[12.5px] font-bold text-white transition hover:bg-rail-soft"
				>
					Review invitation →
				</Link>
				<Link
					to="/tasks"
					className="inline-flex min-h-[42px] items-center rounded-lg border border-card-line bg-white px-4 text-[12.5px] font-bold text-ink transition hover:border-slate-faint"
				>
					See today's tasks
				</Link>
			</div>
		</Card>
	);
}

/* --------------------------------------------------------------- helpers */

function partOfDay(): string {
	const hour = new Date().getHours();
	if (hour < 12) return "Good morning";
	if (hour < 18) return "Good afternoon";
	return "Good evening";
}

/** Tasks a coordinator has sent back, or that are past their due date. */
function attentionTasks(rows: TaskSummary[]): TaskSummary[] {
	const flagged = rows.filter(
		(row) => row.open_question || row.status === "assigned" || row.is_overdue,
	);
	return flagged.length > 0 ? flagged : rows;
}

function taskMeta(row: TaskSummary): string {
	if (row.open_question) return "A question of yours is unanswered";
	if (row.is_overdue && row.due_on) return `Overdue since ${formatDate(row.due_on)}`;
	if (row.due_on) return `Due ${formatDate(row.due_on)}`;
	return "No due date";
}

/* ------------------------------------------------------------- coming up */

interface DatedItem {
	iso: string;
	title: string;
	meta: string;
	to: string;
}

function ComingUp({
	events,
	work,
	deployments,
}: {
	events: EventCard[];
	work: TaskSummary[];
	deployments: DeploymentInvitation[];
}) {
	const today = new Date().toISOString().slice(0, 10);
	const items: DatedItem[] = [];

	for (const event of events) {
		if (!event.start_date || event.start_date < today) continue;
		items.push({
			iso: event.start_date,
			title: event.title,
			meta: [formatClock(event.start_time), event.venue || event.medium]
				.filter(Boolean)
				.join(" · "),
			to: `/events/${encodeURIComponent(event.event)}`,
		});
	}

	for (const task of work) {
		if (!task.due_on || task.due_on < today) continue;
		items.push({
			iso: task.due_on,
			title: task.subject,
			meta: "Task due",
			to: `/tasks/${encodeURIComponent(task.name)}`,
		});
	}

	for (const deployment of deployments) {
		if (
			deployment.response !== "Accepted" ||
			!deployment.start_date ||
			deployment.start_date < today
		)
			continue;
		items.push({
			iso: deployment.start_date,
			title: deployment.title ?? deployment.deployment,
			meta: "Deployment",
			to: `/deployments/${encodeURIComponent(deployment.deployment)}`,
		});
	}

	items.sort((a, b) => a.iso.localeCompare(b.iso));

	if (items.length === 0) {
		return (
			<Empty framed={false} icon={Icon.calendar} title="Nothing on the calendar yet">
				Registered events, dated tasks and accepted deployments appear here as they come up.
			</Empty>
		);
	}

	return (
		<ul className="divide-y divide-card-line">
			{items.slice(0, 4).map((item, index) => {
				const date = new Date(`${item.iso}T00:00:00`);
				return (
					<li key={`${item.to}-${index}`}>
						<Link
							to={item.to}
							className="grid min-h-[70px] grid-cols-[54px_1fr_auto] items-center gap-3.5 px-[22px] transition hover:bg-canvas"
						>
							<time dateTime={item.iso} className="grid text-center leading-none">
								<span className="font-display text-[18px] font-extrabold text-ink tabular">
									{String(date.getDate()).padStart(2, "0")}
								</span>
								<span className="mt-1 text-[9px] font-bold uppercase tracking-[0.12em] text-muted">
									{date.toLocaleDateString(undefined, { month: "short" })}
								</span>
							</time>
							<span className="min-w-0">
								<strong className="block truncate text-[12.5px] font-semibold text-ink">
									{item.title}
								</strong>
								<span className="mt-1 block truncate text-[11px] text-slate-body">{item.meta}</span>
							</span>
							<span aria-hidden="true" className="text-[18px] leading-none text-slate-faint">
								›
							</span>
						</Link>
					</li>
				);
			})}
		</ul>
	);
}

/* -------------------------------------------------------------- discover */

function Discover({ to, label }: { to: string; label: ReactNode }) {
	return (
		<Link
			to={to}
			className="flex min-h-[48px] items-center justify-between gap-3 border-b border-card-line px-[22px] text-[12.5px] font-semibold text-ink transition last:border-b-0 hover:bg-canvas"
		>
			{label}
			<span aria-hidden="true" className="text-muted">
				→
			</span>
		</Link>
	);
}

/* -------------------------------------------------------------- record */

function RecordBlock({ label, children }: { label: string; children: ReactNode }) {
	return (
		<div className="border-b border-card-line px-[22px] py-4 last:border-b-0">
			<div className="mb-2 text-[10px] font-bold uppercase tracking-[0.09em] text-rail-label">
				{label}
			</div>
			{children}
		</div>
	);
}

function RecordVolunteer({
	profile,
	applied,
	loading,
}: {
	profile: VolunteerProfile | null;
	applied: boolean;
	loading: boolean;
}) {
	if (loading) {
		return (
			<RecordBlock label="Volunteer">
				<Skeleton className="h-5 w-40" />
			</RecordBlock>
		);
	}

	if (!profile && applied) {
		return (
			<RecordBlock label="Volunteer">
				<p className="text-[12.5px] leading-relaxed text-slate-body">
					Your application is with your branch. Your volunteer record starts once somebody there
					accepts it.
				</p>
			</RecordBlock>
		);
	}

	if (!profile) {
		return (
			<RecordBlock label="Volunteer">
				<p className="text-[12.5px] leading-relaxed text-slate-body">
					You are not registered as a volunteer.
				</p>
				<Link
					to="/join?path=volunteer"
					className="mt-2 inline-block text-[12px] font-bold text-blue hover:text-blue-hover"
				>
					Become a volunteer
				</Link>
			</RecordBlock>
		);
	}

	return (
		<RecordBlock label="Volunteer">
			<div className="flex flex-wrap items-center gap-2">
				<StatusBadge state={profile.status} />
				<span className="font-mono text-[11.5px] text-muted">{profile.volunteer}</span>
			</div>
			{profile.geo_path && (
				<div className="mt-1.5 text-[12px] text-slate-body">{branchPath(profile.geo_path)}</div>
			)}
		</RecordBlock>
	);
}

function RecordMembership({
	rows,
	applied,
	loading,
}: {
	rows: MembershipRow[];
	applied: boolean;
	loading: boolean;
}) {
	if (loading) {
		return (
			<RecordBlock label="Memberships">
				<Skeleton className="h-5 w-44" />
			</RecordBlock>
		);
	}

	if (rows.length === 0) {
		return (
			<RecordBlock label="Memberships">
				<p className="text-[12.5px] leading-relaxed text-slate-body">
					{applied
						? "Your membership application is with your branch."
						: "You do not hold a membership yet."}
				</p>
				{!applied && (
					<Link
						to="/membership"
						className="mt-2 inline-block text-[12px] font-bold text-blue hover:text-blue-hover"
					>
						Become a member
					</Link>
				)}
			</RecordBlock>
		);
	}

	const primary = rows.find((row) => row.is_active) ?? rows[0];

	return (
		<RecordBlock label="Memberships">
			<div className="text-[13px] font-semibold text-ink">
				{primary.membership_type_name || primary.membership_type}
			</div>
			<div className="mt-0.5 text-[12px] text-slate-body">
				{[
					branchPath(primary.geo_path),
					primary.is_lifetime
						? "lifetime"
						: primary.valid_to
							? `valid to ${formatDate(primary.valid_to)}`
							: null,
					rows.length > 1 ? `+${rows.length - 1} more` : null,
				]
					.filter(Boolean)
					.join(" · ")}
			</div>
			<Link
				to="/membership"
				className="mt-2 inline-block text-[12px] font-bold text-blue hover:text-blue-hover"
			>
				Manage memberships
			</Link>
		</RecordBlock>
	);
}

function RecordHours({ time, loading }: { time: MyTimeLogs | null; loading: boolean }) {
	if (loading) {
		return (
			<RecordBlock label="Service hours">
				<Skeleton className="h-5 w-32" />
			</RecordBlock>
		);
	}

	const total = time?.total_hours ?? 0;

	return (
		<RecordBlock label="Service hours">
			{total > 0 ? (
				<div className="text-[13px] text-ink">
					<span className="font-display text-[19px] font-extrabold tabular">
						{formatHours(total)}
					</span>{" "}
					<span className="text-slate-body">verified hours</span>
				</div>
			) : (
				<p className="text-[12.5px] leading-relaxed text-slate-body">
					No verified hours yet. Hours are added after a completed deployment is verified.
				</p>
			)}
			<Link
				to="/hours"
				className="mt-2 inline-block text-[12px] font-bold text-blue hover:text-blue-hover"
			>
				Service hours
			</Link>
		</RecordBlock>
	);
}

/* --------------------------------------------------------- application */

const STATE_COPY: Record<string, { tone: "info" | "warn"; title: string; body: string }> = {
	Submitted: {
		tone: "info",
		title: "Your application is in",
		body: "It has reached your branch and is waiting to be picked up for review.",
	},
	"In Review": {
		tone: "info",
		title: "Your application is under review",
		body: "Somebody at your branch is looking at it. You will be told as soon as there is a decision.",
	},
	Draft: {
		tone: "warn",
		title: "Your application needs something from you",
		body: "Your branch has asked for something before they can go further.",
	},
};

const UNSENT = {
	tone: "warn" as const,
	title: "Your application is not finished",
	body: "You have not sent this to your branch yet. Pick it up where you left off.",
};

/** The four stages a registration passes through, as the concept draws them. */
const STAGES = ["Submitted", "Branch review", "Next approval", "Activation"];

function stageIndex(state: string, unsent: boolean): number {
	if (unsent) return -1;
	if (state === "Submitted") return 0;
	if (state === "In Review" || state === "Draft") return 1;
	if (state === "Approved") return 3;
	return 1;
}

function Application({ row }: { row: OpenRegistration }) {
	const unsent = row.state === "Draft" && !row.reviewed;
	const copy = (unsent ? UNSENT : STATE_COPY[row.state]) ?? {
		tone: "info" as const,
		title: `Your application is ${row.state.toLowerCase()}`,
		body: "",
	};
	const warn = copy.tone === "warn";
	const at = stageIndex(row.state, unsent);

	return (
		<Card accent={warn ? "danger" : undefined} className="p-6 sm:p-7">
			<div className="flex items-start gap-4">
				<span
					className={cx(
						"grid h-10 w-10 flex-none place-items-center rounded-full",
						warn ? "bg-red-soft text-red-ink" : "bg-success-soft text-success",
					)}
					aria-hidden="true"
				>
					{warn ? <Icon.bell size={18} /> : <Icon.check size={18} />}
				</span>
				<div className="min-w-0 flex-1">
					<div className="flex flex-wrap items-baseline justify-between gap-2">
						<h2 className="font-display text-[17px] font-bold tracking-[-0.02em] text-ink">
							{copy.title}
						</h2>
						<StatusBadge state={row.state} />
					</div>
					{copy.body && (
						<p className="mt-2 text-[12.5px] leading-relaxed text-slate-body">{copy.body}</p>
					)}
					{row.reason && (
						<blockquote className="mt-3 rounded-lg border-l-[3px] border-l-warning bg-warning-soft px-4 py-3 text-[12.5px] leading-relaxed text-warning">
							{row.reason}
						</blockquote>
					)}
				</div>
			</div>

			{!unsent && (
				<ol className="mt-5 grid gap-2 border-t border-card-line pt-5 sm:grid-cols-4">
					{STAGES.map((stage, index) => (
						<li key={stage} className="flex items-center gap-2 text-[11.5px]">
							<span
								className={cx(
									"grid h-5 w-5 flex-none place-items-center rounded-full text-[10px] font-bold",
									index < at
										? "bg-success text-white"
										: index === at
											? "bg-blue text-white"
											: "bg-surface text-muted",
								)}
								aria-hidden="true"
							>
								{index < at ? "✓" : index + 1}
							</span>
							<span className={index <= at ? "font-semibold text-ink" : "text-muted"}>{stage}</span>
						</li>
					))}
				</ol>
			)}

			{row.state === "Draft" && (
				<Link
					to={`/join?path=${row.path}`}
					className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-rail px-4 py-2.5 text-[12.5px] font-bold text-white transition hover:bg-rail-soft"
				>
					Continue application
					<Icon.chevron size={13} className="-rotate-90" />
				</Link>
			)}
		</Card>
	);
}
