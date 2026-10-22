import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../../ui/icons";

/** Home's approved summary tile, kept local while other screens await review. */
export function HomeStatTile({ label, value, to, linkLabel }: {
	label: ReactNode;
	value: ReactNode;
	to: string;
	linkLabel: string;
}) {
	return <Link to={to} className="home-stat-tile">
		<span className="home-stat-icon" aria-hidden="true"><Icon.trend size={19} /></span>
		<span className="home-stat-label">{label}</span>
		<strong className="home-stat-value">{value}</strong>
		<span className="home-stat-link">{linkLabel} →</span>
	</Link>;
}
