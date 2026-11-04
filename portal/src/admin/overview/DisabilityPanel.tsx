import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { API } from "../../lib/api";
import { Icon } from "../../ui/icons";
import type { DisabilitySummary } from "../../portal/types";

const REGISTER = "/admin/registry/volunteers";

/**
 * Persons with disabilities among the active volunteers in this area.
 *
 * **Counts on the overview, names one step away.** Disability is sensitive
 * personal data, so this panel is told how many and of which kinds and nothing
 * more. The names open on the volunteer register, filtered by the same answer,
 * which is the ordinary scoped read every other list of people goes through.
 */
export function DisabilityPanel() {
	const { data, isLoading } = useFrappeGetCall<{ message: DisabilitySummary }>(
		API.disabilitySummary,
		undefined,
		"admin:overview:disability",
	);
	const figures = data?.message;

	if (isLoading || !figures) {
		return null;
	}

	const answered = figures.yes + figures.no + figures.prefer_not;
	const share = figures.active ? Math.round((figures.yes / figures.active) * 100) : 0;
	const answers = [
		{ label: "Have a disability", value: figures.yes, to: `${REGISTER}?disability=Yes` },
		{ label: "No disability", value: figures.no },
		{ label: "Prefer not to say", value: figures.prefer_not },
		{ label: "Not asked", value: figures.not_asked },
	];
	const kinds = [
		...figures.categories.map((row) => ({
			label: row.category,
			value: row.count,
			to: `${REGISTER}?disability_category=${encodeURIComponent(row.category)}`,
		})),
		...(figures.unspecified > 0 ? [{ label: "Kind not given", value: figures.unspecified }] : []),
	];

	return (
		<section className="overview-panel overview-disability" aria-labelledby="disability-heading">
			<div className="overview-panel-heading">
				<div>
					<h3 id="disability-heading">Persons with disabilities</h3>
					<p>Active volunteers in your area who said they have a disability.</p>
				</div>
				<span className="overview-summary-icon">
					<Icon.heart size={18} />
				</span>
			</div>

			<div className="overview-gender-total">
				<strong>{figures.yes}</strong>
				<span>
					{share}% of {figures.active} active volunteers
				</span>
			</div>

			<div className="overview-deployment-details">
				<div>
					<div className="overview-subheading">
						<h4>What volunteers answered</h4>
						<span>{answered} answered</span>
					</div>
					<Bars rows={answers} total={figures.active} label="Disability question answers" />
				</div>
				<div>
					<div className="overview-subheading">
						<h4>Kinds of disability</h4>
						<span>A person can have more than one</span>
					</div>
					{kinds.length ? (
						<Bars rows={kinds} total={figures.yes} label="Kinds of disability" />
					) : (
						<p className="overview-empty">No disabilities recorded in this area.</p>
					)}
				</div>
			</div>

			<div className="overview-breakdown-footer">
				<span>
					{figures.not_asked} of {figures.active} have not been asked
				</span>
				{figures.yes > 0 && (
					<Link to={`${REGISTER}?disability=Yes`}>
						View the list <Icon.arrow size={13} />
					</Link>
				)}
			</div>
		</section>
	);
}

function Bars({
	rows,
	total,
	label,
}: {
	rows: Array<{ label: string; value: number; to?: string }>;
	total: number;
	label: string;
}) {
	return (
		<figure className="overview-breakdown" aria-label={label}>
			<ul>
				{rows.map((row) => {
					const percent = total ? (row.value / total) * 100 : 0;
					const name = row.to && row.value > 0 ? <Link to={row.to}>{row.label}</Link> : <span>{row.label}</span>;

					return (
						<li key={row.label} data-category={row.label} data-count={row.value}>
							<div className="overview-breakdown-label">
								{name}
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
		</figure>
	);
}
