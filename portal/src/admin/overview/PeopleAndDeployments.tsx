import { MetricCard } from "../../ui/MetricCard";
import { Link } from "react-router-dom";
import { Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Icon } from "../../ui/icons";
import type { Registration } from "./RegistrationOverview";

export interface Deployment {
	name: string;
	tor_name: string;
	geo_node: string;
	status: string;
	start_date: string;
	end_date: string;
	participants: Array<{ volunteer: string; is_on_deployment: boolean }>;
}

export function PeopleAndDeployments({
	members,
	volunteers,
 deployments,
}: {
	members: Registration[];
 deployments:Deployment[];
	volunteers: Registration[];
}) {
	const profiles = new Map(
		volunteers.filter((row) => row.red_profile).map((row) => [row.red_profile, row.gender]),
	);
	// A missing profile stays unknown; never infer a person's gender from their name.
	const memberGenders = members.map(
		(row) => row.gender ?? (row.red_profile ? profiles.get(row.red_profile) : undefined),
	);
	const rows = deployments;
	const active = rows.filter((row) => row.status === "Active");
	const planned = rows.filter((row) => row.status === "Planned");
	const deployed = new Set(
		active.flatMap((row) =>
			row.participants.filter((person) => person.is_on_deployment).map((person) => person.volunteer),
		),
	).size;
	const statuses = ["Active", "Planned", "Suspended", "Completed", "Closed Out", "Cancelled"];
	const statusRows = [...new Set([...statuses, ...rows.map((row) => row.status)])].map((label) => ({
		label,
		value: rows.filter((row) => row.status === label).length,
	}));
	return (
		<div className="registration-overview overview-snapshot">
			<div className="overview-gender-grid">
				<GenderPanel kind="members" title="Member gender breakdown" values={memberGenders} />
				<GenderPanel
					kind="volunteers"
					title="Volunteer gender breakdown"
					values={volunteers.map((row) => row.gender)}
				/>
			</div>
			<section className="overview-panel overview-deployments" aria-labelledby="deployment-snapshot-heading">
				<div className="overview-panel-heading">
					<div>
						<h3 id="deployment-snapshot-heading">Deployment overview</h3>
						<p>A snapshot of field operations across your managed areas.</p>
					</div>
					<Link className="overview-control" to="/admin/deployments">
						View operations <Icon.arrow size={14} />
					</Link>
				</div>
				{(
					<>
						<div className="overview-deployment-metrics">
							<DeploymentMetric
								label="Active deployments"
								value={active.length}
								to="/admin/deployments/ongoing"
								icon="truck"
							/>
							<DeploymentMetric
								label="Planned deployments"
								value={planned.length}
								to="/admin/deployments/list"
								icon="calendar"
							/>
							<DeploymentMetric
								label="Volunteers on active deployments"
								value={deployed}
								to="/admin/deployments/ongoing"
								icon="people"
							/>
							<DeploymentMetric
								label="Awaiting close-out"
								value={rows.filter((row) => row.status === "Completed").length}
								to="/admin/deployments/past"
								icon="check"
							/>
						</div>
						<div className="overview-deployment-details">
							<div>
								<div className="overview-subheading">
									<h4>Deployments by status</h4>
									<span>{rows.length} total</span>
								</div>
								<BreakdownBars rows={statusRows} total={rows.length} label="Deployment status breakdown" />
							</div>
							<div>
								<div className="overview-subheading">
									<h4>Active in the field</h4>
									<Link to="/admin/deployments/ongoing">
										View all <Icon.arrow size={13} />
									</Link>
								</div>
								{active.length ? (
									<ul className="overview-active-deployments">
										{active.slice(0, 3).map((row) => (
											<li key={row.name}>
												<Link to={`/admin/deployments/${row.name}`}>
													<span className="overview-deployment-icon">
														<Icon.truck size={17} />
													</span>
													<span className="overview-deployment-name">
														<strong>{row.tor_name}</strong>
														<small>
															{row.geo_node} · {row.name}
														</small>
														<small>
															{shortDate(row.start_date)} – {shortDate(row.end_date)}
														</small>
													</span>
													<Icon.arrow size={15} />
												</Link>
											</li>
										))}
									</ul>
								) : (
									<p className="overview-empty">No active deployments at the moment.</p>
								)}
								<p className="overview-deployment-footnote">
									Volunteer count includes each person once across active deployments.
								</p>
							</div>
						</div>
					</>
				)}
			</section>
		</div>
	);
}

function GenderPanel({
	kind,
	title,
	values,
}: {
	kind: "members" | "volunteers";
	title: string;
	values: Array<string | null | undefined>;
}) {
	const genders = values.map((value) => {
		const label = value?.trim();
		return !label
			? "Not provided"
			: label.toLowerCase() === "female"
				? "Female"
				: label.toLowerCase() === "male"
					? "Male"
					: label;
	});
	const labels = [
		...new Set(["Female", "Male", ...genders.filter((value) => value !== "Not provided"), "Not provided"]),
	];
	const navyShades = ["#011E41", "#45688D", "#6F8CA9", "#8EA5BE", "#A3B6CA"];
	const rows = labels.map((label, index) => ({
		label,
		value: genders.filter((value) => value === label).length,
		fill: label === "Not provided" ? "#B7C6D6" : navyShades[index % navyShades.length],
	}));
	const known = values.length - (rows.find((row) => row.label === "Not provided")?.value ?? 0);
	return (
		<section
			className="overview-panel overview-gender-panel"
			data-gender={kind}
			aria-labelledby={`gender-${kind}-heading`}
		>
			<div className="overview-panel-heading">
				<div>
					<h3 id={`gender-${kind}-heading`}>{title}</h3>
					<p>Recorded gender across your {kind === "members" ? "member" : "volunteer"} register.</p>
				</div>
				<span className="overview-summary-icon">
					<Icon.people size={18} />
				</span>
			</div>
			<div className="overview-gender-total">
				<strong>{values.length}</strong>
				<span>{kind} in scope</span>
			</div>
			<figure
				className="overview-gender-visual"
				aria-label={`${title}: ${rows.map((row) => `${row.label} ${row.value}`).join(", ")}`}
			>
				<div className="overview-gender-pie">
					{values.length ? (
						<ResponsiveContainer width="100%" height={220} minWidth={0}>
							<PieChart>
								<Pie
									data={rows.filter((row) => row.value > 0)}
									dataKey="value"
									nameKey="label"
									cx="50%"
									cy="50%"
									innerRadius={0}
									outerRadius={96}
									startAngle={90}
									endAngle={-270}
									stroke="#FFFFFF"
									strokeWidth={2}
									isAnimationActive={false}
								/>
								<Tooltip
									content={({ active, payload }) =>
										active && payload?.length ? (
											<div className="overview-gender-tooltip" role="status">
												<strong>{String(payload[0].name)}</strong>
												<span>
													{Number(payload[0].value)} {kind} ·{" "}
													{((Number(payload[0].value) / values.length) * 100).toFixed(0)}%
												</span>
											</div>
										) : null
									}
								/>
							</PieChart>
						</ResponsiveContainer>
					) : (
						<div className="overview-gender-empty">No records in this scope yet.</div>
					)}
				</div>
				<ul className="overview-gender-legend">
					{rows.map((row) => (
						<li key={row.label} data-category={row.label} data-count={row.value}>
							<span className="overview-gender-label">
								<i style={{ background: row.fill }} aria-hidden="true" />
								{row.label}
							</span>
							<span>
								<strong>{row.value}</strong>
								<small>{values.length ? ((row.value / values.length) * 100).toFixed(0) : 0}%</small>
							</span>
						</li>
					))}
				</ul>
			</figure>
			<div className="overview-breakdown-footer">
				<span>
					{known} of {values.length} have gender recorded
				</span>
				<Link to={`/admin/registry/${kind}`}>
					View {kind} <Icon.arrow size={13} />
				</Link>
			</div>
		</section>
	);
}

/** A shared 0–100% scale keeps the two register proportions comparable. */
function BreakdownBars({
	rows,
	total,
	label,
}: {
	rows: Array<{ label: string; value: number }>;
	total: number;
	label: string;
}) {
	return (
		<figure className="overview-breakdown" aria-label={label}>
			<div className="overview-breakdown-scale" aria-hidden="true">
				<span>0%</span>
				<span>50%</span>
				<span>100%</span>
			</div>
			<ul>
				{rows.map((row) => {
					const percent = total ? (row.value / total) * 100 : 0;
					return (
						<li key={row.label} data-category={row.label} data-count={row.value}>
							<div className="overview-breakdown-label">
								<span>{row.label}</span>
								<span>
									<strong>{row.value}</strong>
									<small>{percent.toFixed(0)}%</small>
								</span>
							</div>
							<div className="overview-breakdown-track" aria-hidden="true">
								<span style={{ width: `${percent}%` }} />
							</div>
						</li>
					);
				})}
			</ul>
			{!total && <figcaption className="overview-breakdown-empty">No records in this scope yet.</figcaption>}
		</figure>
	);
}

function DeploymentMetric({
	label,
	value,
	to,
	icon,
}: {
	label: string;
	value: number;
	to: string;
	icon: "truck" | "calendar" | "people" | "check";
}) {
	const Glyph = Icon[icon];
	return <MetricCard label={label} value={value} to={to} icon={<Glyph size={19} />} />;
}

function shortDate(value: string) {
	return value
		? new Date(value.slice(0, 10) + "T12:00:00").toLocaleDateString("en-GB", {
				day: "numeric",
				month: "short",
			})
		: "Date not set";
}
