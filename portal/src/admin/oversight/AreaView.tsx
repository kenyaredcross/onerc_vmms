import { useMemo, useState, type ReactNode } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";
import { useSearchParams } from "react-router-dom";

import { API, errorMessage } from "../../lib/api";
import { BarRows, ColumnChart, type Column } from "../../ui/chart";
import { Icon } from "../../ui/icons";
import { MetricCard } from "../../ui/MetricCard";
import {
	Button,
	ButtonLink,
	Card,
	Cell,
	Empty,
	ErrorNote,
	PageHeading,
	Row,
	SectionTitle,
	Spinner,
	Table,
	cx,
} from "../../ui/primitives";
import { AreaMap, type Shading } from "./AreaMap";
import type { AreaRow, Count, MapShapes, Overview } from "./types";

/**
 * A region, or the country, county by county.
 *
 * The questions this answers are a regional head's: which county is falling
 * behind, what is waiting on me, what do we have and where. So the page is
 * the same three things top to bottom: the area's totals, the map and the
 * table that compare its places, and the breakdowns of whichever place is
 * chosen. Choosing a county (on the map or in the table) narrows the
 * breakdowns and nothing else; the comparison always stays whole.
 *
 * `mode` is the only difference between the two tabs. On the national tab
 * the table compares regions, the map picks out the chosen region's counties,
 * and clicking a county chooses its region.
 *
 * Every figure is the server's and is the reader's own scope. The chosen place
 * is in the address, so a view can be sent to a colleague.
 */
type Mode = "region" | "national";

type SortKey = keyof Pick<
	AreaRow,
	"label" | "volunteers" | "members" | "new_30d" | "expiring_60d" | "waiting" | "oldest_days" | "with_applicant" | "materials_lent" | "deployments"
>;

const COLUMNS: Array<{ key: SortKey; label: string }> = [
	{ key: "volunteers", label: "Volunteers" },
	{ key: "members", label: "Members" },
	{ key: "new_30d", label: "New, 30 days" },
	{ key: "expiring_60d", label: "Ending, 60 days" },
	{ key: "waiting", label: "Waiting for approval" },
	{ key: "oldest_days", label: "Oldest (days)" },
	{ key: "with_applicant", label: "With the applicant" },
	{ key: "materials_lent", label: "Materials lent out" },
	{ key: "deployments", label: "Deployments" },
];

export function AreaView({ mode, title }: { mode: Mode; title: ReactNode }) {
	const [params, setParams] = useSearchParams();
	const place = params.get("place") || undefined;
	const area = params.get("area") || undefined;

	const args = mode === "region" ? { area, place } : { place };
	const { data, error, isLoading } = useFrappeGetCall<{ message: Overview }>(
		mode === "region" ? API.oversightRegion : API.oversightNational,
		args,
		`admin:oversight:${mode}:${area ?? ""}:${place ?? ""}`,
		{ keepPreviousData: true },
	);
	const map = useFrappeGetCall<{ message: MapShapes }>(API.oversightMapShapes, undefined, "admin:oversight:map");

	const view = data?.message;

	const choose = (next: { place?: string | null; area?: string | null }) => {
		const updated = new URLSearchParams(params);

		for (const [key, value] of Object.entries(next)) {
			if (value) updated.set(key, value);
			else updated.delete(key);
		}

		setParams(updated, { replace: true });
	};

	if (isLoading && !view) return <Spinner label="Counting…" />;
	if (error) return <ErrorNote>{errorMessage(error)}</ErrorNote>;
	if (!view) return null;

	if (!view.area) {
		return (
			<>
				<PageHeading title={title} />
				<Empty title="No regions yet">
					Regions appear here once the society's places have been set up with a level under the country.
				</Empty>
			</>
		);
	}

	const unit = mode === "region" ? "County" : "Region";
	const chosen = view.selected_totals;
	const scopeName = view.selected?.label ?? view.area.label;

	return (
		<>
			<PageHeading
				title={title}
				meta={<>Figures as of {formatDate(view.as_of)}</>}
				actions={
					<div className="flex flex-wrap items-center gap-2">
						{mode === "region" && (view.areas?.length ?? 0) > 1 && (
							<label className="flex items-center gap-2 text-[13px] text-muted">
								Region
								<select
									className="rounded-lg border border-card-line bg-white px-3 py-2 text-[13px] text-ink"
									value={view.area.name}
									onChange={(event) => choose({ area: event.target.value, place: null })}
								>
									{view.areas?.map((option) => (
										<option key={option.name} value={option.name}>
											{option.label}
										</option>
									))}
								</select>
							</label>
						)}
						<Button variant="quiet" onClick={() => exportRows(view, unit)}>
							<Icon.download size={15} /> Download table
						</Button>
					</div>
				}
			/>

			<div className="space-y-5">
				<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
					<MetricCard label="Active volunteers" value={view.totals.volunteers} icon={<Icon.people size={19} />} />
					<MetricCard
						label="Active members"
						value={view.totals.members}
						icon={<Icon.card size={19} />}
						note={view.totals.expiring_60d ? `${view.totals.expiring_60d} ending in the next 60 days` : undefined}
					/>
					<MetricCard
						label="Waiting for approval"
						value={view.totals.waiting}
						icon={<Icon.hourglass size={19} />}
						note={
							view.totals.waiting_late
								? `${view.totals.waiting_late} past the deadline · oldest ${view.totals.oldest_days} days`
								: "None past the deadline"
						}
					/>
					<MetricCard
						label="Waiting on the applicant"
						value={view.totals.with_applicant}
						icon={<Icon.chat size={19} />}
						note="Sent back for more information"
					/>
					<MetricCard
						label="Materials lent out"
						value={view.totals.materials_lent}
						icon={<Icon.tag size={19} />}
						note={`Of ${view.totals.materials_total} held`}
					/>
				</div>

				<div className="grid gap-4 lg:grid-cols-5">
					<Card className="lg:col-span-3">
						<SectionTitle>{mode === "region" ? `${view.area.label} on the map` : "Every county"}</SectionTitle>
						{map.data?.message ? (
							<MapFor mode={mode} view={view} shapes={map.data.message} onChoose={(name) => choose({ place: name && name !== view.selected?.name ? name : null })} />
						) : map.error ? (
							<p className="py-8 text-center text-[12.5px] text-slate-faint">The map could not be drawn.</p>
						) : (
							<Spinner label="Drawing the map…" />
						)}
					</Card>

					<Attention mode={mode} view={view} />
				</div>

				<section>
					<div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
						<SectionTitle>{mode === "region" ? "Counties" : "Regions"}</SectionTitle>
						<span className="text-[12px] text-slate-faint">Choose a {unit.toLowerCase()} to see its breakdowns below.</span>
					</div>
					<Comparison
						rows={view.rows}
						unit={unit}
						selected={view.selected?.name}
						onChoose={(name) => choose({ place: name === view.selected?.name ? null : name })}
					/>
				</section>

				<section className="space-y-4">
					<div className="flex flex-wrap items-center justify-between gap-3">
						<h3 className="text-[18px] font-semibold text-ink">
							{view.selected ? scopeName : `All of ${view.area.label}`}
						</h3>
						{view.selected && (
							<Button variant="ghost" onClick={() => choose({ place: null })}>
								Show all of {view.area.label}
							</Button>
						)}
					</div>

					{chosen && (
						<div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
							<Figure label="Volunteers" value={chosen.volunteers} />
							<Figure label="Members" value={chosen.members} />
							<Figure label="Waiting for approval" value={chosen.waiting} />
							<Figure label="Active deployments" value={chosen.deployments} />
						</div>
					)}

					<Breakdowns view={view} />
				</section>
			</div>
		</>
	);
}

/* --------------------------------------------------------------------- map */

const SHADINGS: Array<Shading & { key: string }> = [
	{ key: "volunteers", label: "Active volunteers", value: (row) => row.volunteers },
	{ key: "members", label: "Active members", value: (row) => row.members },
	{ key: "waiting", label: "Waiting for approval", value: (row) => row.waiting },
	{ key: "materials", label: "Materials lent out", value: (row) => row.materials_lent },
];

function MapFor({
	mode,
	view,
	shapes,
	onChoose,
}: {
	mode: Mode;
	view: Overview;
	shapes: MapShapes;
	onChoose: (name: string) => void;
}) {
	const [shadeBy, setShadeBy] = useState(SHADINGS[0].key);
	const figures = useMemo(() => new Map(view.units.map((row) => [row.name, row])), [view.units]);
	const counties = useMemo(() => new Set(view.units.map((row) => row.name)), [view.units]);
	const regionOf = useMemo(() => {
		const lookup = new Map<string, string>();
		for (const row of view.rows) for (const county of row.counties ?? []) lookup.set(county, row.name);
		return lookup;
	}, [view.rows]);

	if (mode === "region") {
		return (
			<AreaMap
				shapes={shapes}
				figures={figures}
				highlight={counties}
				active={counties}
				chosen={new Set(view.selected ? [view.selected.name] : [])}
				onSelect={onChoose}
				label={`Map of the counties, with ${view.area?.label} picked out`}
				highlightLabel={view.area?.label ?? "This region"}
			/>
		);
	}

	const chosenRegion = view.rows.find((row) => row.name === view.selected?.name);
	const shading = SHADINGS.find((option) => option.key === shadeBy) ?? SHADINGS[0];

	return (
		<>
			<label className="mb-3 flex items-center gap-2 text-[13px] text-muted">
				Shade counties by
				<select
					className="rounded-lg border border-card-line bg-white px-3 py-1.5 text-[13px] text-ink"
					value={shading.key}
					onChange={(event) => setShadeBy(event.target.value)}
				>
					{SHADINGS.map((option) => (
						<option key={option.key} value={option.key}>
							{option.label}
						</option>
					))}
				</select>
			</label>
			<AreaMap
				shapes={shapes}
				figures={figures}
				highlight={new Set(chosenRegion ? chosenRegion.counties : counties)}
				active={counties}
				chosen={new Set()}
				onSelect={(county) => {
					const region = regionOf.get(county);
					if (region) onChoose(region === view.selected?.name ? "" : region);
				}}
				label="Map of the counties"
				highlightLabel={chosenRegion ? chosenRegion.label : "Every region"}
				shading={shading}
			/>
		</>
	);
}

/* --------------------------------------------------------------- attention */

function Attention({ mode, view }: { mode: Mode; view: Overview }) {
	const { attention } = view;
	const late = attention.late.slice(0, 5);

	return (
		<Card className="lg:col-span-2">
			<SectionTitle>Needs attention</SectionTitle>

			<div className="space-y-5 text-[13px]">
				{attention.mine > 0 && (
					<div className="flex items-center justify-between gap-3 rounded-lg bg-blue-soft px-3.5 py-3">
						<span className="text-ink">
							<strong className="font-semibold">{attention.mine}</strong> waiting for your decision
						</span>
						<ButtonLink to="/admin/queue/members/assigned" variant="primary">
							Open
						</ButtonLink>
					</div>
				)}

				<div>
					<h4 className="mb-1.5 font-semibold text-ink">Past the approval deadline</h4>
					{late.length ? (
						<ul className="divide-y divide-card-line">
							{late.map((row) => (
								<li key={row.name} className="flex justify-between gap-3 py-1.5">
									<span className="text-ink">{row.label}</span>
									<span className="tabular-nums text-muted">
										{row.count} · oldest {row.oldest_days} days
									</span>
								</li>
							))}
						</ul>
					) : (
						<p className="text-muted">Nothing is past its deadline.</p>
					)}
				</div>

				{mode === "national" && (
					<div>
						<h4 className="mb-1.5 font-semibold text-ink">Regions with no head assigned</h4>
						{attention.without_head.length ? (
							<p className="text-muted">{attention.without_head.map((row) => row.label).join(", ")}</p>
						) : (
							<p className="text-muted">Every region has a head.</p>
						)}
					</div>
				)}

				<div>
					<h4 className="mb-1.5 font-semibold text-ink">
						{mode === "national" ? "Regions with a county nobody approves for" : "Counties with nobody to approve"}
					</h4>
					{attention.without_approver.length ? (
						<p className="text-muted">{attention.without_approver.map((row) => row.label).join(", ")}</p>
					) : (
						<p className="text-muted">Every county has an approver.</p>
					)}
				</div>
			</div>
		</Card>
	);
}

/* -------------------------------------------------------------- comparison */

function Comparison({
	rows,
	unit,
	selected,
	onChoose,
}: {
	rows: AreaRow[];
	unit: string;
	selected?: string;
	onChoose: (name: string) => void;
}) {
	const [sort, setSort] = useState<{ key: SortKey; down: boolean }>({ key: "label", down: false });

	const sorted = useMemo(() => {
		const copy = [...rows];
		copy.sort((a, b) => {
			const order = sort.key === "label" ? a.label.localeCompare(b.label) : (a[sort.key] as number) - (b[sort.key] as number);
			return sort.down ? -order : order;
		});
		return copy;
	}, [rows, sort]);

	const header = (key: SortKey, label: string) => (
		<button
			type="button"
			className="inline-flex items-center gap-1 uppercase tracking-[0.07em] hover:text-ink"
			onClick={() => setSort({ key, down: sort.key === key ? !sort.down : key !== "label" })}
			aria-label={`Sort by ${label}`}
		>
			{label}
			{sort.key === key && <span aria-hidden="true">{sort.down ? "↓" : "↑"}</span>}
		</button>
	);

	return (
		<Table
			head={[header("label", unit), ...COLUMNS.map((column) => header(column.key, column.label))]}
			align={["left", ...COLUMNS.map(() => "right" as const)]}
			minWidth={1040}
			caption={`${unit} by ${unit.toLowerCase()}`}
		>
			{sorted.map((row) => (
				<Row key={row.name}>
					<Cell>
						<button
							type="button"
							onClick={() => onChoose(row.name)}
							aria-pressed={row.name === selected}
							className={cx(
								"text-left font-semibold underline-offset-2 hover:underline",
								row.name === selected ? "text-action" : "text-ink",
							)}
						>
							{row.label}
						</button>
						{row.has_approver === false && (
							<span className="ml-2 text-[11px] font-medium text-action">No approver</span>
						)}
					</Cell>
					{COLUMNS.map((column) => (
						<Cell key={column.key} className="text-right tabular-nums">
							{column.key === "waiting" && row.waiting_late ? (
								<span>
									{row.waiting} <span className="text-[11px] text-action">({row.waiting_late} late)</span>
								</span>
							) : column.key === "materials_lent" ? (
								<span>
									{row.materials_lent}
									<span className="text-slate-faint"> / {row.materials_total}</span>
								</span>
							) : (
								row[column.key]
							)}
						</Cell>
					))}
				</Row>
			))}
		</Table>
	);
}

/* -------------------------------------------------------------- breakdowns */

function Breakdowns({ view }: { view: Overview }) {
	const { breakdown } = view;

	return (
		<>
			<div className="grid gap-4 lg:grid-cols-2">
				<Card>
					<SectionTitle>Volunteers joining</SectionTitle>
					<ColumnChart columns={trend(breakdown.trend, "volunteers")} />
				</Card>
				<Card>
					<SectionTitle>Memberships taken out</SectionTitle>
					<ColumnChart columns={trend(breakdown.trend, "members")} />
				</Card>
			</div>

			<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
				<Card>
					<SectionTitle>Volunteers by gender</SectionTitle>
					<BarRows rows={bars(breakdown.volunteers.gender)} />
				</Card>
				<Card>
					<SectionTitle>Volunteers by age</SectionTitle>
					<BarRows rows={bars(breakdown.volunteers.age)} />
				</Card>
				<Card>
					<SectionTitle>Volunteers with a disability</SectionTitle>
					<BarRows rows={bars(breakdown.volunteers.disability)} />
				</Card>
				<Card>
					<SectionTitle>Members by gender</SectionTitle>
					<BarRows rows={bars(breakdown.members.gender)} />
				</Card>
				<Card>
					<SectionTitle>Members by age</SectionTitle>
					<BarRows rows={bars(breakdown.members.age)} />
				</Card>
				<Card>
					<SectionTitle>Membership plans</SectionTitle>
					<BarRows rows={bars(breakdown.plans)} />
				</Card>
			</div>

			<Card pad={false}>
				<div className="px-5 pt-5">
					<SectionTitle>Materials</SectionTitle>
				</div>
				{breakdown.materials.length ? (
					<Table head={["Category", "Items", "Held", "Lent out"]} align={["left", "right", "right", "right"]} minWidth={480}>
						{breakdown.materials.map((row) => (
							<Row key={row.category}>
								<Cell className="font-semibold text-ink">{row.category}</Cell>
								<Cell className="text-right tabular-nums">{row.items}</Cell>
								<Cell className="text-right tabular-nums">{row.total}</Cell>
								<Cell className="text-right tabular-nums">{row.lent}</Cell>
							</Row>
						))}
					</Table>
				) : (
					<p className="px-5 pb-6 text-[12.5px] text-slate-faint">No materials recorded here.</p>
				)}
			</Card>
		</>
	);
}

function Figure({ label, value }: { label: string; value: number }) {
	return (
		<div className="rounded-xl border border-card-line bg-white px-4 py-3">
			<div className="text-[12px] text-muted">{label}</div>
			<div className="text-[22px] font-semibold tabular-nums text-ink">{value}</div>
		</div>
	);
}

/* ----------------------------------------------------------------- helpers */

function bars(rows: Count[]): Array<{ label: string; value: number }> {
	return rows.map((row) => ({ label: row.label, value: row.count }));
}

function trend(points: Overview["breakdown"]["trend"], key: "volunteers" | "members"): Column[] {
	return points.map((point) => ({ label: month(point.month), title: month(point.month, true), value: point[key] }));
}

function month(value: string, long = false): string {
	const [year, index] = value.split("-");
	const date = new Date(Number(year), Number(index) - 1, 1);
	if (Number.isNaN(date.getTime())) return value;
	return date.toLocaleDateString(undefined, { month: long ? "long" : "short", year: long ? "numeric" : "2-digit" });
}

function formatDate(value: string): string {
	const date = new Date(`${value}T00:00:00`);
	return Number.isNaN(date.getTime())
		? value
		: date.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
}

function exportRows(view: Overview, unit: string) {
	const cell = (value: unknown) => {
		let text = String(value ?? "");
		// Spreadsheets must read names as data, never as formulas.
		if (/^\s*[=+@-]/.test(text)) text = `'${text}`;
		return `"${text.replaceAll('"', '""')}"`;
	};
	const headers = [unit, ...COLUMNS.map((column) => column.label), "Late", "Materials held"];
	const lines = view.rows.map((row) => [
		row.label,
		...COLUMNS.map((column) => row[column.key]),
		row.waiting_late,
		row.materials_total,
	]);
	const csv = "﻿" + [headers, ...lines].map((line) => line.map(cell).join(",")).join("\r\n");
	const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8;" }));
	const link = document.createElement("a");
	link.href = url;
	link.download = `${(view.area?.label ?? "area").toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${view.as_of}.csv`;
	document.body.append(link);
	link.click();
	link.remove();
	setTimeout(() => URL.revokeObjectURL(url), 1000);
}
