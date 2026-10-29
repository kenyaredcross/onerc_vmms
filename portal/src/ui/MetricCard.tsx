import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Icon } from "./icons";

/** Shared summary card, based on Overview's Total volunteers card. */
export function MetricCard({
	label,
	value,
	icon,
	badge,
	note,
	to,
	negative = false,
	noteClassName = "",
}: {
	label: ReactNode;
	value: ReactNode;
	icon?: ReactNode;
	badge?: ReactNode;
	note?: ReactNode;
	to?: string;
	negative?: boolean;
	noteClassName?: string;
}) {
	const body = (
		<>
			<span className="overview-metric-icon" aria-hidden="true">
				{icon ?? <Icon.trend size={19} />}
			</span>
			<span className="overview-metric-label">{label}</span>
			<div className="overview-metric-value">
				<strong>{value}</strong>
				{badge != null && (
					<span className={`overview-metric-badge ${negative ? "negative" : ""}`}>{badge}</span>
				)}
			</div>
			{note != null && <div className={`overview-metric-note ${noteClassName}`}>{note}</div>}
		</>
	);
	return to ? (
		<Link className="overview-metric" to={to}>
			{body}
		</Link>
	) : (
		<div className="overview-metric">{body}</div>
	);
}
