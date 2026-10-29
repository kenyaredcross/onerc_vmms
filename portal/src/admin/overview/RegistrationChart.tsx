import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis } from "recharts";

export type Point = { month: string; volunteers: number; members: number };
type Kind = "all" | "volunteers" | "members";
export const dateLabel = (date: string, long = false) =>
	new Date(date + "T12:00:00").toLocaleDateString("en-GB", {
		month: long ? "long" : "short",
		year: "numeric",
	});
const series = [
	{ key: "volunteers", label: "Volunteer registrations", color: "#45688D", width: 1.4 },
	{ key: "activity", label: "Total registrations", color: "#6F8CA9", width: 1.25 },
	{ key: "members", label: "Membership registrations", color: "#011E41", width: 1.2 },
] as const;

/** Reference chart geometry with measured registration counts. */
export function RegistrationChart({ points: registrations, kind }: { points: Point[]; kind: Kind }) {
 const points=registrations.map(point=>({...point,date:new Date(point.month+"-01T12:00:00").getTime(),activity:point.volunteers+point.members}));
	const shown = series.filter((s) => s.key === "activity" || kind === "all" || s.key === kind);
	return (
		<div
			className="overview-chart reference-activity-chart"
			data-registration-chart
			data-points={points.length}
			role="group"
			aria-label="Member and volunteer registrations. Use the arrow keys on the chart to explore dates."
		>
			<div className="overview-legend reference-activity-legend">
				{shown.map((s) => (
					<span key={s.key}>
						<i className={`overview-swatch ${s.key === "activity" ? "intensity" : s.key}`} style={{ background: s.color }} />
						{s.label}
					</span>
				))}
			</div>
			<ResponsiveContainer width="100%" height={320} minWidth={0}>
				<ComposedChart data={points} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} accessibilityLayer>
					<defs>
						<linearGradient id="fillActivity" x1="0" y1="0" x2="0" y2="1">
							<stop offset="5%" stopColor="#6F8CA9" stopOpacity={0.36} />
							<stop offset="95%" stopColor="#6F8CA9" stopOpacity={0.04} />
						</linearGradient>
					</defs>
					<CartesianGrid vertical={false} stroke="#E7E7E7" strokeOpacity={0.5} />
					<XAxis
						dataKey="date"
						tickLine={false}
						axisLine={false}
						tickMargin={8}
						minTickGap={48}
						tick={{ fill: "#627083", fontSize: 12 }}
						tickFormatter={(value) =>
							new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric" })
						}
					/>
					<Tooltip
						cursor={false}
						content={({ active, payload, label }) =>
							active && payload?.length ? (
								<div className="overview-chart-tooltip reference-activity-tooltip" role="status">
									<strong>
										{new Date(Number(label)).toLocaleDateString("en-GB", {
											day: "numeric",
											month: "long",
											year: "numeric",
										})}
									</strong>
									{payload.map((entry) => (
										<span key={String(entry.dataKey)}>
											<i style={{ background: entry.color }} />
											{entry.name}
											<b>{Number(entry.value).toLocaleString("en-GB", { maximumFractionDigits: 1 })}</b>
										</span>
									))}
								</div>
							) : null
						}
					/>
					<Area
						dataKey="activity"
						name="Total registrations"
						type="natural"
						fill="url(#fillActivity)"
						stroke="#6F8CA9"
						strokeWidth={1.25}
						dot={false}
						fillOpacity={1}
						isAnimationActive={false}
					/>
					{(kind === "all" || kind === "volunteers") && (
						<Line
							dataKey="volunteers"
							name="Volunteer registrations"
							type="natural"
							stroke="#45688D"
							strokeWidth={1.4}
							dot={false}
							isAnimationActive={false}
						/>
					)}
					{(kind === "all" || kind === "members") && (
						<Line
							dataKey="members"
							name="Membership registrations"
							type="natural"
							stroke="#011E41"
							strokeWidth={1.2}
							dot={false}
							isAnimationActive={false}
						/>
					)}
				</ComposedChart>
			</ResponsiveContainer>
		</div>
	);
}
