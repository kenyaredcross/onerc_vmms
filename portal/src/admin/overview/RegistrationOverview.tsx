import { MetricCard as Metric } from "../../ui/MetricCard";
import { useState } from "react";
import { RegistrationChart, dateLabel, type Point } from "./RegistrationChart";
import { Link } from "react-router-dom";
import { Icon } from "../../ui/icons";

export interface Registration {
	full_name: string;
	red_profile?: string;
	gender?: string | null;
	volunteer?: string;
	member?: string;
	joined_on?: string;
	valid_from?: string;
	geo_node: string;
	status: string;
}
type Kind = "all" | "volunteers" | "members";
const registrationDate = (row: Registration) => (row.volunteer ? row.joined_on : row.valid_from) ?? "";

/** Counts registrations, not unique people: a person can hold both roles. */
function monthlyRegistrations(volunteers: Registration[], members: Registration[], asOf: string): Point[] {
	const end = new Date(asOf + "T12:00:00");
	return Array.from({ length: 12 }, (_, i) => {
		const date = new Date(end.getFullYear(), end.getMonth() - 11 + i, 1, 12);
		const month = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
		const count = (rows: Registration[]) =>
			rows.filter((row) => registrationDate(row).startsWith(month) && registrationDate(row) <= asOf).length;
		return { month, volunteers: count(volunteers), members: count(members) };
	});
}

export function RegistrationOverview({
	volunteers,
	members,
	asOf,
}: {
	volunteers: Registration[];
	members: Registration[];
	asOf: string;
}) {
	const [period, setPeriod] = useState(3);
	const [kind, setKind] = useState<Kind>("all");
	const trend = monthlyRegistrations(volunteers, members, asOf);
	const points = trend.slice(-period);
	const total = (rows: Point[]) => rows.reduce((sum, row) => sum + row.volunteers + row.members, 0);
	const latest = total(trend.slice(-2, -1));
	const previous = total(trend.slice(-3, -2));
	const growth = previous ? ((latest - previous) / previous) * 100 : null;
	const count = (key: "volunteers" | "members") => points.reduce((sum, point) => sum + point[key], 0);
	return (
		<div className="registration-overview">
			<div className="overview-metrics">
				<Metric
					label="Total volunteers"
					value={volunteers.length.toLocaleString()}
					icon={<Icon.people size={19} />}
					badge={`+${count("volunteers")} joined`}
					note={`New registrations in the last ${period} months`}
					to="/admin/registry/volunteers"
				/>
				<Metric
					label="Total members"
					value={members.length.toLocaleString()}
					icon={<Icon.card size={19} />}
					badge={`+${count("members")} joined`}
					note={`New memberships in the last ${period} months`}
					to="/admin/registry/members"
				/>
				<Metric
					label="New registrations"
					value={total(points).toLocaleString()}
					icon={<Icon.user size={19} />}
					badge={`${period} months`}
					note="Volunteer and membership registrations"
				/>
				<Metric
					label="Monthly registration growth"
					value={growth === null ? "—" : `${growth > 0 ? "+" : ""}${growth.toFixed(1)}%`}
					icon={<Icon.trend size={19} />}
					badge={growth === null ? "No baseline" : growth < 0 ? "↓ Month on month" : "↑ Month on month"}
					negative={growth !== null && growth < 0}
					note={`${dateLabel(trend.at(-2)!.month + "-01")}: ${latest} · ${dateLabel(trend.at(-3)!.month + "-01")}: ${previous}`}
				/>
			</div>
			<section className="overview-panel overview-activity" aria-labelledby="registrations-heading">
				<div className="overview-panel-heading">
					<div>
						<h3 id="registrations-heading">Member &amp; volunteer activity</h3>
						<p>Member and volunteer activity for the last {period} months</p>
					</div>
					<div className="overview-controls">
						<select
							aria-label="Registration period"
							value={period}
							onChange={(event) => setPeriod(Number(event.target.value))}
						>
							<option value="3">3 months</option>
							<option value="6">6 months</option>
							<option value="12">12 months</option>
						</select>
						<select
							aria-label="Registration type"
							value={kind}
							onChange={(event) => setKind(event.target.value as Kind)}
						>
							<option value="all">Members &amp; volunteers</option>
							<option value="volunteers">Volunteers only</option>
							<option value="members">Members only</option>
						</select>
						<Link className="overview-control" to="/admin/analytics">
							View report <Icon.arrow size={14} />
						</Link>
					</div>
				</div>
				<RegistrationChart points={points} kind={kind} />
				<div className="overview-chart-footer">
					<span>
						{dateLabel(points[0].month + "-01")} – {dateLabel(asOf)}{" "}
						<span className="overview-partial">· Recorded registrations</span>
					</span>
					<span>Members and volunteers may overlap.</span>
				</div>
			</section>
		</div>
	);
}
