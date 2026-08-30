import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { BarRows, ColumnChart, type Column } from "../ui/chart";
import { Icon } from "../ui/icons";
import {
	Card,
	ErrorNote,
	PageHeading,
	SectionLabel,
	SectionLink,
	SectionTitle,
	Spinner,
	StatGrid,
	StatTile,
} from "../ui/primitives";
import type { ApprovalStatus } from "../portal/types";

/**
 * The coordinator screens that are either a summary of other screens or an
 * honest gap. Grouped in one file because none of them carries enough of its
 * own logic to earn a module.
 */

/* ---------------------------------------------------------------- overview */

export function Overview() {
	const queue = useFrappeGetCall<{ message: ApprovalStatus[] }>(
		API.myQueue,
		undefined,
		"admin:my_queue",
	);
	const members = useFrappeGetCall<{ message: { count: number; member_count: number } }>(
		API.findMembers,
		{ limit: 200 },
		"admin:find_members",
	);
	const volunteers = useFrappeGetCall<{ message: { count: number } }>(
		API.findVolunteers,
		{ limit: 200 },
		"admin:find_volunteers",
	);
	const analytics = useFrappeGetCall<{ message: OverviewSummary }>(
		API.branchSummary,
		{ months: 12 },
		"admin:overview_summary",
	);

	const waiting = queue.data?.message ?? [];
	const overdue = waiting.filter((row) => row.stage?.is_breached).length;
	const summary = analytics.data?.message;

	return (
		<>
			<PageHeading
				title={<EditableText k="admin.nav.overview" fallback="Overview" />}
				lead="A live view of the people, growth and activity across the areas you manage."
			/>

			<StatGrid className="mb-6">
				<StatTile
					label="Waiting on you"
					value={queue.isLoading ? "—" : waiting.length}
					icon={Icon.inbox}
					tint="navy"
					to="/admin/queue"
				/>
				<StatTile
					label="Past their SLA"
					value={queue.isLoading ? "—" : overdue}
					hint={overdue > 0 ? "Overdue for a decision" : undefined}
					icon={Icon.hourglass}
					tint="amber"
					to="/admin/queue"
				/>
				<StatTile
					label="Members in scope"
					value={members.isLoading ? "—" : (members.data?.message.member_count ?? "—")}
					icon={Icon.card}
					tint="violet"
					to="/admin/registry/members"
				/>
				<StatTile
					label="Volunteers in scope"
					value={volunteers.isLoading ? "—" : (volunteers.data?.message.count ?? "—")}
					icon={Icon.people}
					tint="teal"
					to="/admin/registry/volunteers"
				/>
			</StatGrid>

			{analytics.isLoading && <Spinner label="Building your regional picture…" />}
			{analytics.error && <ErrorNote>{errorMessage(analytics.error)}</ErrorNote>}

			{summary && (
				<div className="space-y-7">
					<section>
						<SectionLabel action={<SectionLink to="/admin/analytics">Explore analytics</SectionLink>}>
							Registration trend
						</SectionLabel>
						<div className="grid gap-4 lg:grid-cols-2">
							<ChartCard
								title="New volunteers"
								total={sumTrend(summary.trend, "volunteers")}
								columns={trendColumns(summary.trend, "volunteers")}
							/>
							<ChartCard
								title="New memberships"
								total={sumTrend(summary.trend, "members")}
								columns={trendColumns(summary.trend, "members")}
							/>
						</div>
					</section>

					<section>
						<SectionLabel>People across your area</SectionLabel>
						<div className="grid gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(280px,1fr)]">
							<Card>
								<div className="mb-5 flex flex-wrap items-end justify-between gap-3">
									<div>
										<SectionTitle>Geographic coverage</SectionTitle>
										<p className="text-[12.5px] text-slate-body">One level below your current management scope</p>
									</div>
									<div className="flex gap-4 text-[11px] font-semibold text-slate-body">
										<span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-sm bg-navy" />Volunteers</span>
										<span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-sm bg-blue" />Members</span>
									</div>
								</div>
								<GeoBars rows={summary.coverage} />
							</Card>

							<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
								<Card>
									<SectionTitle>Volunteer status</SectionTitle>
									<BarRows rows={breakdown(summary.volunteers.by_status)} />
								</Card>
								<Card>
									<SectionTitle>Membership status</SectionTitle>
									<BarRows rows={breakdown(summary.members.by_status)} />
								</Card>
							</div>
						</div>
					</section>

					<section>
						<SectionLabel>Needs attention</SectionLabel>
						<Card className="grid gap-5 sm:grid-cols-3">
							<Attention value={summary.tasks.open} label="Open tasks" />
							<Attention value={summary.tasks.awaiting_sign_off} label="Awaiting sign-off" />
							<Attention value={summary.tasks.overdue} label="Overdue tasks" urgent={summary.tasks.overdue > 0} />
						</Card>
					</section>
				</div>
			)}
		</>
	);
}

interface OverviewSummary {
	volunteers: { total: number; by_status: Record<string, number> };
	members: { total: number; by_status: Record<string, number> };
	tasks: { open: number; awaiting_sign_off: number; overdue: number };
	trend: Array<{ month: string; volunteers: number; members: number }>;
	coverage: Array<{ geo_node: string; label: string; volunteers: number; members: number }>;
}

function ChartCard({ title, total, columns }: { title: string; total: number; columns: Column[] }) {
	return (
		<Card>
			<div className="mb-4 flex items-start justify-between gap-4">
				<div>
					<SectionTitle>{title}</SectionTitle>
					<p className="text-[11.5px] text-slate-faint">Last 12 months</p>
				</div>
				<div className="text-right">
					<div className="font-display text-[28px] font-semibold leading-none tabular-nums text-ink">{total}</div>
					<div className="mt-1 text-[10px] font-bold uppercase tracking-wider text-slate-faint">total joined</div>
				</div>
			</div>
			<ColumnChart columns={columns} />
		</Card>
	);
}

function GeoBars({ rows }: { rows: OverviewSummary["coverage"] }) {
	if (!rows.length) return <p className="py-10 text-center text-[12.5px] text-slate-faint">No areas below this scope to compare.</p>;
	const max = Math.max(...rows.flatMap((row) => [row.volunteers, row.members]), 1);
	return (
		<div className="space-y-4">
			{rows.map((row) => (
				<div key={row.geo_node} className="grid gap-2 sm:grid-cols-[minmax(110px,0.65fr)_minmax(0,2fr)] sm:items-center">
					<div className="truncate text-[12.5px] font-semibold text-ink" title={row.label}>{row.label}</div>
					<div className="space-y-1.5">
						<GeoBar value={row.volunteers} max={max} tone="bg-navy" label="volunteers" />
						<GeoBar value={row.members} max={max} tone="bg-blue" label="members" />
					</div>
				</div>
			))}
		</div>
	);
}

function GeoBar({ value, max, tone, label }: { value: number; max: number; tone: string; label: string }) {
	return (
		<div className="flex items-center gap-2" title={`${value} ${label}`}>
			<div className="h-2.5 min-w-0 flex-1 overflow-hidden rounded-full bg-surface">
				<div className={`h-full rounded-full ${tone}`} style={{ width: value ? `max(${(value / max) * 100}%, 3px)` : 0 }} />
			</div>
			<span className="w-8 text-right text-[11.5px] font-bold tabular-nums text-slate-strong">{value}</span>
		</div>
	);
}

function Attention({ value, label, urgent = false }: { value: number; label: string; urgent?: boolean }) {
	return (
		<div className="flex items-center gap-3 sm:border-r sm:border-hairline sm:last:border-0">
			<div className={`grid h-11 w-11 place-items-center rounded-full font-display text-[18px] font-bold tabular-nums ${urgent ? "bg-danger-soft text-danger" : "bg-surface text-navy"}`}>{value}</div>
			<div className="text-[12.5px] font-semibold text-slate-strong">{label}</div>
		</div>
	);
}

function trendColumns(trend: OverviewSummary["trend"], key: "volunteers" | "members"): Column[] {
	return trend.map((point) => ({ label: monthLabel(point.month), title: monthLabel(point.month, true), value: point[key] }));
}

function monthLabel(month: string, long = false): string {
	const [year, index] = month.split("-");
	const date = new Date(Number(year), Number(index) - 1, 1);
	if (Number.isNaN(date.getTime())) return month;
	return date.toLocaleDateString(undefined, { month: long ? "long" : "short", year: long ? "numeric" : "2-digit" });
}

function sumTrend(trend: OverviewSummary["trend"], key: "volunteers" | "members"): number {
	return trend.reduce((total, point) => total + point[key], 0);
}

function breakdown(counts: Record<string, number>) {
	return Object.entries(counts).map(([label, value]) => ({ label, value }));
}

/* ---------------------------------------------- what used to live here */
//
// Deployments, Stipends, Events and Analytics were all `NotBuilt` blocks in this
// file. Each now has its own screen reading real endpoints:
//
//   admin/Deployments.tsx  — api/deployment.py: listings, roster, matching
//   admin/Stipends.tsx     — api/stipend.py: reports, payment forms, approval
//   admin/Events.tsx       — api/events.py, over Buzz's published events
//   admin/Analytics.tsx    — api/analytics.py
//
// Two honest gaps survived the move rather than being papered over, and both
// are stated on the screen that owns them: revenue is absent from Analytics
// because a society's income is `onerc_payments`' record, and deciding stipend
// paperwork is refused by the server because departmental routing does not
// exist. Neither is a missing screen, so neither is a `NotBuilt`.
