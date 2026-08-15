import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, geoPath } from "../lib/format";
import { Icon } from "../ui/icons";
import {
	Avatar,
	ButtonLink,
	Card,
	Empty,
	ErrorNote,
	List,
	ListRow,
	PageHeading,
	Pill,
	Ring,
	SectionLabel,
	SectionLink,
	Skeleton,
	Spinner,
	StatGrid,
	StatTile,
	StateBadge,
} from "../ui/primitives";
import type {
	MembershipRow,
	MyCertifications,
	MyTimeLogs,
	TaskSummary,
	VolunteerProfile,
} from "./types";

/**
 * The volunteer's own front page.
 *
 * Six independent questions, six independent requests, and each renders as soon
 * as its own answer arrives. A single combined endpoint would be faster by five
 * round trips and would mean the whole page waits on the slowest of the six;
 * worse, it would be a seventh DTO to keep in step with six that already exist.
 *
 * **Every one of these is a possessive endpoint that takes no arguments.**
 * Nothing on this page can be pointed at somebody else, which is why there is
 * no permission check in this file to get wrong.
 *
 * **The figures come first and the records under them.** A person opening this
 * page wants to know where they stand before they want to read anything, and
 * four numbers answer that in one glance where four cards do not. Each tile is
 * a link to the screen that owns it, because a figure somebody wants to act on
 * is a figure they will click.
 */
export default function Dashboard() {
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
	const certifications = useFrappeGetCall<{ message: MyCertifications | null }>(
		API.myCertifications,
		undefined,
		"portal:my_certifications",
	);
	const logs = useFrappeGetCall<{ message: MyTimeLogs | null }>(
		API.myTimeLogs,
		undefined,
		"portal:my_time_logs",
	);
	// Open work only. The same key the tasks screen uses for its default view, so
	// the two share one response rather than asking twice.
	const tasks = useFrappeGetCall<{ message: { volunteer: string; tasks: TaskSummary[] } | null }>(
		API.myTasks,
		{ include_closed: 0 },
		"portal:my_tasks:false",
	);

	// What the person has open and undecided. Somebody who has applied and is
	// waiting has nothing else on this page addressed to them — no volunteer
	// record yet, no membership, no training — so without this the dashboard
	// reads as though the application never happened.
	const open = useFrappeGetCall<{
		message: Record<
			string,
			{ doctype: string; name: string; path: string; state: string; reason?: string } | null
		>;
	}>(API.myOpenRegistrations, undefined, "portal:open_registrations");

	const pending = Object.values(open.data?.message ?? {}).filter(Boolean) as {
		doctype: string;
		name: string;
		path: string;
		state: string;
		reason?: string;
	}[];

	const profile = volunteer.data?.message ?? null;
	const rows = memberships.data?.message ?? [];
	const training = certifications.data?.message ?? null;
	const time = logs.data?.message ?? null;
	const work = tasks.data?.message?.tasks ?? [];

	const loading = volunteer.isLoading && memberships.isLoading;

	return (
		<>
			<PageHeading
				title={<EditableText k="portal.home.heading" fallback="Your dashboard" />}
				meta={profile?.geo_path ? geoPath(profile.geo_path) : undefined}
				lead={<EditableText k="portal.home.intro" />}
			/>

			{pending.map((row) => (
				<UnderReview key={row.name} row={row} />
			))}

			{volunteer.error && (
				<div className="mb-6">
					<ErrorNote>{errorMessage(volunteer.error)}</ErrorNote>
				</div>
			)}

			{/* Drawn for anybody with a volunteer record. Somebody who is a member
			    only has no hours, no training and no tasks, and four tiles reading
			    zero would be four ways of saying "this is not your screen". */}
			{profile && (
				<section className="mb-8">
					<SectionLabel>
						<EditableText k="portal.home.section.standing" fallback="Where you stand" />
					</SectionLabel>

					<StatGrid>
						<StatTile
							label="Hours given"
							value={logs.isLoading ? "—" : hours(time?.total_hours ?? 0)}
							hint={
								logs.isLoading
									? undefined
									: `${time?.log_count ?? 0} ${(time?.log_count ?? 0) === 1 ? "entry" : "entries"} filed`
							}
							icon={Icon.clock}
							tint="navy"
							to="/hours"
						/>

						<StatTile
							label="Certifications"
							value={certifications.isLoading ? "—" : (training?.certifications.length ?? 0)}
							hint={lapsedHint(training)}
							icon={Icon.award}
							tint="teal"
							to="/training"
						/>

						<StatTile
							label="Open tasks"
							value={tasks.isLoading ? "—" : work.length}
							hint={
								work.some((row) => row.open_question)
									? "A question of yours is unanswered"
									: overdue(work)
							}
							icon={Icon.check}
							tint="amber"
							to="/tasks"
						/>

						<StatTile
							label="Membership"
							value={memberships.isLoading ? "—" : (rows[0]?.membership_status ?? "None")}
							hint={
								rows[0]?.valid_to
									? `Valid until ${formatDate(rows[0].valid_to)}`
									: rows[0]?.is_lifetime
										? "Lifetime"
										: undefined
							}
							icon={Icon.card}
							tint="violet"
							to="/membership"
						/>
					</StatGrid>
				</section>
			)}

			{loading && <Spinner label="Loading your dashboard…" />}

			<div className="grid items-start gap-6 lg:grid-cols-3">
				<div className="space-y-8 lg:col-span-2">
					<section>
						<SectionLabel>
							<EditableText k="portal.home.section.volunteering" fallback="Volunteering" />
						</SectionLabel>
						<VolunteerCard profile={profile} loading={volunteer.isLoading} />
					</section>

					{profile && (
						<section>
							<SectionLabel action={work.length > 0 && <SectionLink to="/tasks">See all</SectionLink>}>
								<EditableText k="portal.home.section.tasks" fallback="What is waiting on you" />
							</SectionLabel>
							<TasksCard rows={work} loading={tasks.isLoading} />
						</section>
					)}

					<section>
						<SectionLabel action={<SectionLink to="/membership">Manage</SectionLink>}>
							<EditableText k="portal.home.section.membership" fallback="Membership" />
						</SectionLabel>
						<MembershipsCard rows={rows} loading={memberships.isLoading} />
					</section>
				</div>

				<div className="space-y-8">
					{(training || certifications.isLoading) && (
						<section>
							<SectionLabel>
								<EditableText k="portal.home.section.deployability" fallback="Deployability" />
							</SectionLabel>
							<DeployabilityCard training={training} loading={certifications.isLoading} />
						</section>
					)}

					<section>
						<SectionLabel>
							<EditableText k="portal.home.section.actions" fallback="Quick actions" />
						</SectionLabel>
						<QuickLinks volunteer={Boolean(profile)} />
					</section>
				</div>
			</div>
		</>
	);
}

/** Whole numbers stay whole; a half hour keeps its half. */
function hours(value: number): string {
	return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

/**
 * The line under the certifications figure.
 *
 * Says the thing worth acting on when there is one — a lapsed certification is
 * what stops a deployment — and otherwise says when the answer was computed,
 * which is the only other honest thing to put there.
 */
function lapsedHint(training: MyCertifications | null): string | undefined {
	if (!training) return undefined;

	const lapsed = training.certifications.filter((row) => row.lapsed).length;

	if (lapsed > 0) return `${lapsed} lapsed`;

	return training.certifications.length > 0 ? "All current" : undefined;
}

/** How many open tasks are past their due date, or nothing to say. */
function overdue(rows: TaskSummary[]): string | undefined {
	const today = new Date().toISOString().slice(0, 10);
	const late = rows.filter((row) => row.due_on && row.due_on < today).length;

	if (late > 0) return `${late} past its due date`;

	return rows.length > 0 ? "Nothing overdue" : undefined;
}

/* --------------------------------------------------------------- volunteer */

function VolunteerCard({
	profile,
	loading,
}: {
	profile: VolunteerProfile | null;
	loading: boolean;
}) {
	if (loading) {
		return (
			<Card>
				<div className="flex items-center gap-4">
					<Skeleton className="h-12 w-12 rounded-full" />
					<div className="flex-1 space-y-2">
						<Skeleton className="h-4 w-40" />
						<Skeleton className="h-3 w-56" />
					</div>
				</div>
				<div className="mt-6 grid gap-4 sm:grid-cols-2">
					<Skeleton className="h-10" />
					<Skeleton className="h-10" />
					<Skeleton className="h-10" />
					<Skeleton className="h-10" />
				</div>
			</Card>
		);
	}

	// Not a volunteer is an ordinary state, not an error: somebody may be a
	// member only, or may have just signed up. The endpoint returns null and
	// this is the invitation rather than an empty panel.
	if (!profile) {
		return (
			<Card>
				<Empty
					framed={false}
					title="You are not registered as a volunteer"
					icon={Icon.people}
					action={<ButtonLink to="/portal/join?path=volunteer">Become a volunteer</ButtonLink>}
				>
					Apply once, and your branch verifies your record. You can be a member and a volunteer at
					the same time.
				</Empty>
			</Card>
		);
	}

	return (
		<Card>
			<div className="flex flex-wrap items-center gap-4">
				<Avatar name={profile.full_name} size={48} />

				<div className="min-w-0 flex-1">
					<div className="truncate font-display text-[16px] font-extrabold tracking-tight text-ink">
						{profile.full_name || "Your record"}
					</div>
					<div className="mt-0.5 truncate text-[12px] text-slate-body">
						{geoPath(profile.geo_path) || "No serving branch recorded"}
					</div>
				</div>

				<StateBadge state={profile.status} />
			</div>

			<dl className="mt-6 grid gap-x-6 gap-y-5 border-t border-hairline-soft pt-5 sm:grid-cols-2">
				<Detail label="Serving branch" value={geoPath(profile.geo_path) || "—"} />
				<Detail label="Home area" value={geoPath(profile.home_geo_path) || "—"} />
				<Detail label="Joined" value={formatDate(profile.joined_on)} />
				<Detail label="Volunteer ID" value={profile.volunteer} mono />
			</dl>
		</Card>
	);
}

function Detail({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
	return (
		<div>
			<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">{label}</dt>
			<dd
				className={
					mono ? "mt-1.5 font-mono text-[12.5px] text-ink" : "mt-1.5 text-[13px] font-medium text-ink"
				}
			>
				{value}
			</dd>
		</div>
	);
}

/* -------------------------------------------------------------------- work */

/**
 * The open tasks, at most three.
 *
 * Three because this is a summary and the tasks screen is the list: a dashboard
 * that reproduces a whole screen has removed the reason to open it. The counter
 * beside the label says how many were left out.
 */
function TasksCard({ rows, loading }: { rows: TaskSummary[]; loading: boolean }) {
	if (loading) {
		return (
			<Card>
				<div className="space-y-3">
					<Skeleton className="h-11" />
					<Skeleton className="h-11" />
				</div>
			</Card>
		);
	}

	if (rows.length === 0) {
		return (
			<Card>
				<Empty framed={false} title="Nothing is waiting on you" icon={Icon.check}>
					A coordinator in your branch can assign you a piece of work, and it will arrive here and
					in your notifications.
				</Empty>
			</Card>
		);
	}

	const today = new Date().toISOString().slice(0, 10);

	return (
		<Card pad={false}>
			<div className="p-2">
				<List>
					{rows.slice(0, 3).map((row) => (
						<ListRow
							key={row.name}
							to="/tasks"
							lead={
								<span
									className="grid h-9 w-9 flex-none place-items-center rounded-control bg-tint-amber-soft text-tint-amber"
									aria-hidden="true"
								>
									<Icon.check size={17} />
								</span>
							}
							title={row.subject}
							meta={
								<>
									{row.due_on ? (
										<span className={row.due_on < today ? "font-semibold text-signal-dark" : undefined}>
											Due {formatDate(row.due_on)}
										</span>
									) : (
										"No due date"
									)}
									{row.open_question && " · question waiting"}
								</>
							}
							trailing={<StateBadge state={row.status} />}
						/>
					))}
				</List>
			</div>

			{rows.length > 3 && (
				<div className="border-t border-hairline-soft px-5 py-3">
					<Link to="/tasks" className="chev text-[12px] font-bold text-navy hover:text-signal">
						{rows.length - 3} more
					</Link>
				</div>
			)}
		</Card>
	);
}

/* -------------------------------------------------------------- membership */

function MembershipsCard({ rows, loading }: { rows: MembershipRow[]; loading: boolean }) {
	if (loading) {
		return (
			<Card>
				<Skeleton className="h-14" />
			</Card>
		);
	}

	if (rows.length === 0) {
		return (
			<Card>
				<Empty
					framed={false}
					title={
						<EditableText k="portal.membership.empty" fallback="You do not hold a membership yet." />
					}
					icon={Icon.card}
					action={
						<ButtonLink to="/portal/join?path=member" variant="soft">
							Become a member
						</ButtonLink>
					}
				>
					A membership is separate from volunteering. You may hold both.
				</Empty>
			</Card>
		);
	}

	return (
		<Card pad={false}>
			<div className="p-2">
				<List>
					{rows.map((row) => (
						<ListRow
							key={row.name}
							to="/membership"
							lead={
								<span
									className="grid h-9 w-9 flex-none place-items-center rounded-control bg-tint-violet-soft text-tint-violet"
									aria-hidden="true"
								>
									<Icon.card size={17} />
								</span>
							}
							title={row.membership_type_name || row.membership_type}
							meta={
								<>
									{geoPath(row.geo_path)}
									{row.valid_to && ` · until ${formatDate(row.valid_to)}`}
									{row.is_lifetime && " · lifetime"}
								</>
							}
							trailing={<StateBadge state={row.membership_status} />}
						/>
					))}
				</List>
			</div>
		</Card>
	);
}

/* ----------------------------------------------------------- deployability */

/**
 * Whether this person may be deployed today, and what is stopping them.
 *
 * Both come straight from `my_certifications`, which derives them from the same
 * function the coordinator's candidate matching uses. That is deliberate on the
 * server side and worth preserving here: a volunteer must never be told they
 * are ready by this card and then be absent from the list a coordinator sees.
 *
 * **The ring counts current certifications against held ones**, which is the
 * only proportion in the answer that means anything. It is not the reason
 * somebody is or is not deployable — that is `deployable`, stated in words
 * beside it — and the card would be lying if the ring were read as a score.
 */
function DeployabilityCard({
	training,
	loading,
}: {
	training: MyCertifications | null;
	loading: boolean;
}) {
	if (loading) {
		return (
			<Card>
				<Skeleton className="h-24" />
			</Card>
		);
	}

	if (!training) return null;

	const held = training.certifications.length;
	const current = training.certifications.filter((row) => !row.lapsed).length;

	return (
		<Card>
			<div className="flex items-center gap-4">
				<Ring
					value={current}
					total={held || 1}
					size={58}
					tint={training.deployable ? "teal" : "rose"}
				>
					{held > 0 ? `${current}/${held}` : "—"}
				</Ring>

				<div className="min-w-0">
					<div className="flex items-center gap-2">
						<span
							className={
								training.deployable
									? "h-2 w-2 flex-none rounded-full bg-emerald-500"
									: "h-2 w-2 flex-none rounded-full bg-signal"
							}
							aria-hidden="true"
						/>
						<span className="font-display text-[14.5px] font-bold text-ink">
							{training.deployable ? "Ready to deploy" : "Not deployable"}
						</span>
					</div>
					<p className="mt-1 text-[11.5px] text-slate-faint">
						{held > 0
							? `${current} of ${held} certifications current`
							: "No certifications recorded"}
					</p>
				</div>
			</div>

			{training.blocking_reasons.length > 0 && (
				<ul className="mt-5 space-y-2 border-t border-hairline-soft pt-4">
					{training.blocking_reasons.map((reason) => (
						<li
							key={reason}
							className="flex items-start gap-2.5 text-[12.5px] leading-relaxed text-slate-body"
						>
							<span className="mt-1.5 h-1 w-1 flex-none rounded-full bg-signal" aria-hidden="true" />
							{reason}
						</li>
					))}
				</ul>
			)}

			<div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-hairline-soft pt-4">
				<Pill tone="page">as of {formatDate(training.as_of)}</Pill>
				<Link to="/training" className="chev text-[12px] font-bold text-navy hover:text-signal">
					Your training
				</Link>
			</div>
		</Card>
	);
}

/* ---------------------------------------------------------------- shortcuts */

function QuickLinks({ volunteer }: { volunteer: boolean }) {
	// Logging time is only meaningful with a volunteer record behind it, and the
	// hours screen says so on arrival. Offering it here to somebody who has none
	// is a shortcut to being told no.
	const links = [
		volunteer && { to: "/hours", label: "Log hours", icon: Icon.clock },
		{ to: "/profile", label: "Update your details", icon: Icon.user },
		{ to: "/opportunities", label: "Find opportunities", icon: Icon.compass },
		{ to: "/events", label: "See what is on", icon: Icon.calendar },
	].filter(Boolean) as { to: string; label: string; icon: typeof Icon.clock }[];

	return (
		<Card pad={false}>
			<div className="p-2">
				<List>
					{links.map((link) => (
						<ListRow
							key={link.to}
							to={link.to}
							lead={
								<span
									className="grid h-9 w-9 flex-none place-items-center rounded-control bg-page text-slate-body"
									aria-hidden="true"
								>
									<link.icon size={17} />
								</span>
							}
							title={link.label}
							trailing={<Icon.chevron size={15} className="-rotate-90 text-slate-faint" />}
						/>
					))}
				</List>
			</div>
		</Card>
	);
}

/**
 * Where somebody's own application has got to.
 *
 * The gap this fills: between applying and being accepted there is a real wait,
 * and during it the dashboard had nothing on it addressed to the person at all
 * — no volunteer record yet, no membership, no training. Somebody who had just
 * filled in a long form saw a page that looked as though they had not. The
 * commonest support question after a registration is "did it go through", and
 * the product should answer it without being asked.
 *
 * **The state comes from the server, and the wording is a lookup rather than a
 * sentence built here.** `approval_state` is a closed set owned by
 * `approvals/states.py`, so a state without an entry falls back to the state's
 * own name — which is honest and slightly bare, rather than wrong.
 *
 * Draft is the one that matters most and reads least obviously: an approver who
 * asks for more information puts the application *back* to Draft, so a person
 * sitting at Draft after submitting is not half-finished, they are waited on.
 */
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

function UnderReview({
	row,
}: {
	row: { doctype: string; name: string; path: string; state: string; reason?: string };
}) {
	const copy = STATE_COPY[row.state] ?? {
		tone: "info" as const,
		title: `Your application is ${row.state.toLowerCase()}`,
		body: "",
	};

	const warn = copy.tone === "warn";

	return (
		<Card className={`mb-6 border-l-[3px] ${warn ? "border-l-amber-500" : "border-l-navy"}`}>
			<div className="flex items-start gap-4">
				<span
					className={`grid h-10 w-10 flex-none place-items-center rounded-control ${
						warn ? "bg-tint-amber-soft text-tint-amber" : "bg-tint-navy-soft text-tint-navy"
					}`}
					aria-hidden="true"
				>
					{warn ? <Icon.bell size={18} /> : <Icon.hourglass size={18} />}
				</span>

				<div className="min-w-0 flex-1">
					<div className="flex flex-wrap items-baseline justify-between gap-2">
						<h2 className="font-display text-[15px] font-bold tracking-tight text-ink">
							{copy.title}
						</h2>
						<StateBadge state={row.state} />
					</div>

					{copy.body && (
						<p className="mt-2 text-[13.5px] leading-relaxed text-slate-body">{copy.body}</p>
					)}

					{/* What the approver actually wrote. It went into the email and
					    nowhere else, so anybody who deleted the email had no way back to
					    it — and it is the one thing that says what to do next. */}
					{row.reason && (
						<blockquote className="mt-3 rounded-control border-l-2 border-hairline-strong bg-page px-4 py-3 text-[13px] leading-relaxed text-slate-body">
							{row.reason}
						</blockquote>
					)}

					<p className="mt-3 text-[12px] text-slate-faint">
						Your reference is <span className="font-semibold text-slate-body">{row.name}</span>
					</p>
				</div>
			</div>
		</Card>
	);
}
