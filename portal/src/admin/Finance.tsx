import { useMemo, useState } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import { PairedColumnChart } from "../ui/chart";
import {
	Bar,
	Caveat,
	Card,
	Empty,
	ErrorNote,
	FilterSelect,
	Metric,
	MetricGrid,
	Money,
	PageHead,
	SectionHead,
	Spinner,
	StatusBadge,
	Table,
	Cell,
	NameCell,
	Row,
	Toolbar,
	cx,
} from "./ui/kit";

/**
 * What the society took in and what it paid out.
 *
 * **A report, and it says so.** This app keeps no book of account: there is no
 * amount field on a membership and no expense record at all. Every figure here
 * is derived at read time from two registers a coordinator can already open one
 * row at a time — see `finance/services/ledger.py`, which carries the whole
 * argument. The screen's job is to make the derivation visible rather than to
 * imply an exactness that is not there, which is what the caveat under the
 * figures is for and why it is not decoration to be trimmed.
 *
 * **Two honest gaps, stated on the page:**
 * 1. Income is counted at each membership type's *published fee*. A society
 *    that changes a price reprices its own history, and nothing here can know
 *    what was actually taken at the counter.
 * 2. Expenditure is volunteer stipend payments and nothing else. A cost that is
 *    not a stipend cannot be recorded in this product, so a low expenses figure
 *    means "little was paid in stipends", never "the society spent little".
 *
 * **Currency is grouped, never converted.** A site can hold more than one, and
 * picking a rate is not this app's business. Nearly every society has one and
 * the screen reads normally; a society with two sees two totals rather than one
 * wrong one.
 */

interface MoneyTotal {
	currency: string;
	amount: number;
}

interface FinanceSummary {
	from_date: string;
	to_date: string;
	basis: string;
	income: {
		totals: MoneyTotal[];
		count: number;
		by_type: Array<{
			membership_type: string | null;
			label: string;
			count: number;
			amount: number;
			currency: string | null;
			unpriced: boolean;
		}>;
		recent: Array<{
			name: string;
			label: string;
			paid_on: string;
			status: string | null;
			amount: number | null;
			currency: string | null;
		}>;
	};
	expenses: {
		totals: MoneyTotal[];
		count: number;
		by_state: Array<{ state: string; count: number; amount: number; currency: string }>;
		recent: Array<{
			name: string;
			amount: number;
			currency: string;
			period_from: string;
			period_to: string;
			state: string;
			progress_report: string | null;
		}>;
	};
	net: Array<{ currency: string; income: number; expenses: number; net: number }>;
	months: Array<{ month: string; income: MoneyTotal[]; expenses: MoneyTotal[] }>;
}

/**
 * The windows the screen offers, as months back from today.
 *
 * A closed set rather than a date pair, because a coordinator reading a
 * position is asking "this year" or "the last quarter", not "the fourteenth of
 * March to the ninth of June". The endpoint takes arbitrary dates, so a report
 * that needs them has somewhere to go; the screen does not lead with them.
 */
const WINDOWS = [
	{ value: "3", label: "Last 3 months" },
	{ value: "6", label: "Last 6 months" },
	{ value: "12", label: "Last 12 months" },
	{ value: "24", label: "Last 2 years" },
];

/** A month key (`2026-09`) as a short label for an axis. */
function monthLabel(key: string): string {
	const date = new Date(`${key}-01T00:00:00`);
	if (Number.isNaN(date.getTime())) return key;

	return date.toLocaleDateString(undefined, { month: "short" });
}

function monthTitle(key: string): string {
	const date = new Date(`${key}-01T00:00:00`);
	if (Number.isNaN(date.getTime())) return key;

	return date.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

/** The first entry of a totals list, for a society that has one currency. */
function first(totals: MoneyTotal[]): MoneyTotal | null {
	return totals[0] ?? null;
}

export default function Finance() {
	const [months, setMonths] = useState("12");

	const from = useMemo(() => {
		const date = new Date();
		date.setDate(1);
		date.setMonth(date.getMonth() - (Number(months) - 1));

		return date.toISOString().slice(0, 10);
	}, [months]);

	const summary = useFrappeGetCall<{ message: FinanceSummary }>(
		API.financeSummary,
		{ from_date: from },
		`admin:finance:${from}`,
	);

	if (summary.isLoading) return <Spinner page label="Reading the registers…" />;
	if (summary.error) return <ErrorNote>{errorMessage(summary.error)}</ErrorNote>;

	const data = summary.data?.message;
	if (!data) return <ErrorNote>{errorMessage(null, "The figures could not be read.")}</ErrorNote>;

	const income = first(data.income.totals);
	const expenses = first(data.expenses.totals);
	// The society's working currency, for the figures that have to be labelled
	// with one. Income first because it is the register with more rows in it;
	// a site with neither shows bare numbers, which `formatMoney` handles.
	const currency = income?.currency ?? expenses?.currency ?? null;
	const net = data.net.find((entry) => entry.currency === currency) ?? data.net[0] ?? null;
	const multiCurrency = data.income.totals.length + data.expenses.totals.length > 2;

	return (
		<>
			<PageHead
				eyebrow={`${formatDate(data.from_date)} — ${formatDate(data.to_date)}`}
				title="Income & expenses"
				actions={
					<Toolbar>
						<FilterSelect
							label="Period"
							value={months}
							onChange={setMonths}
							options={WINDOWS}
							allLabel={null}
						/>
					</Toolbar>
				}
			/>

			<MetricGrid>
				<Metric
					label="Membership income"
					icon={Icon.receipt}
					value={<Money amount={income?.amount ?? 0} currency={income?.currency} size="lg" />}
					note={`${data.income.count} ${data.income.count === 1 ? "payment" : "payments"} recorded`}
				/>
				<Metric
					label="Stipends paid out"
					icon={Icon.coins}
					value={<Money amount={expenses?.amount ?? 0} currency={expenses?.currency} size="lg" />}
					note={`${data.expenses.count} ${data.expenses.count === 1 ? "payment form" : "payment forms"}`}
				/>
				<Metric
					label="Net"
					icon={Icon.trend}
					value={<Money amount={net?.net ?? 0} currency={currency} size="lg" />}
					note={net && net.net < 0 ? "Paid out more than came in" : "Came in more than was paid out"}
					tone={net && net.net < 0 ? "negative" : "positive"}
				/>
				<Metric
					label="Memberships sold"
					icon={Icon.card}
					value={<span className="tabular">{data.income.count}</span>}
					note="Paid through this system"
					to="/admin/registry/members"
				/>
			</MetricGrid>

			<Card className="mb-4">
				<div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
					<h2 className="text-[13.5px] font-semibold text-ink">Month by month</h2>
					{multiCurrency && (
						<span className="text-[11.5px] font-medium text-warning">
							Charted in {currency} only — other currencies are listed below
						</span>
					)}
				</div>

				<PairedColumnChart
					currency={currency}
					labels={{ a: "In", b: "Out" }}
					months={data.months.map((month) => ({
						label: monthLabel(month.month),
						title: monthTitle(month.month),
						a: month.income.find((entry) => entry.currency === currency)?.amount ?? 0,
						b: month.expenses.find((entry) => entry.currency === currency)?.amount ?? 0,
					}))}
				/>
			</Card>

			<div className="mb-4 grid gap-4 lg:grid-cols-2">
				<IncomeByType rows={data.income.by_type} />
				<ExpensesByState rows={data.expenses.by_state} />
			</div>

			{multiCurrency && <CurrencyBreakdown net={data.net} />}

			<div className="mb-5 grid gap-4 lg:grid-cols-2">
				<RecentIncome rows={data.income.recent} />
				<RecentExpenses rows={data.expenses.recent} />
			</div>

			{/* The two limits, said once, at the foot where a reader who has
			    finished with the figures meets them. Not narration of the screen —
			    a statement about what the numbers on it are, without which somebody
			    would take a derived figure for a receipt. */}
			<div className="space-y-1.5">
				<Caveat>
					Income is counted at each membership type&rsquo;s published fee. The society records that a
					membership was paid for, not the amount taken, so a fee changed since a payment changes
					what this reports for it.
				</Caveat>
				<Caveat>
					Expenditure is volunteer stipend payments. No other cost is recorded in this system, so a
					small figure here means little was paid in stipends rather than that little was spent.
				</Caveat>
			</div>
		</>
	);
}

function IncomeByType({ rows }: { rows: FinanceSummary["income"]["by_type"] }) {
	const max = Math.max(...rows.map((row) => row.amount), 1);

	return (
		<Card pad={false}>
			<SectionHead title="Where income came from" />
			{rows.length === 0 ? (
				<Empty framed={false} title="No membership payments in this period" icon={Icon.receipt} />
			) : (
				<ul className="divide-y divide-card-line">
					{rows.map((row) => (
						<li key={row.membership_type ?? row.label} className="px-[18px] py-3.5">
							<div className="mb-2 flex items-baseline justify-between gap-3">
								<span className="min-w-0 truncate text-[13px] font-semibold text-ink">{row.label}</span>
								{row.unpriced ? (
									<span className="flex-none text-[11.5px] font-medium text-warning">No fee set</span>
								) : (
									<Money amount={row.amount} currency={row.currency} />
								)}
							</div>
							<Bar value={row.amount} max={max} label={`${row.label} income`} tone="in" />
							<div className="mt-1.5 text-[11.5px] text-muted">
								{row.count} {row.count === 1 ? "membership" : "memberships"}
							</div>
						</li>
					))}
				</ul>
			)}
		</Card>
	);
}

function ExpensesByState({ rows }: { rows: FinanceSummary["expenses"]["by_state"] }) {
	const max = Math.max(...rows.map((row) => row.amount), 1);

	return (
		<Card pad={false}>
			<SectionHead title="What was paid out" link={{ to: "/admin/finance/stipends", label: "Stipends" }} />
			{rows.length === 0 ? (
				<Empty framed={false} title="No stipend payments in this period" icon={Icon.coins} />
			) : (
				<ul className="divide-y divide-card-line">
					{rows.map((row) => (
						<li key={row.state} className="px-[18px] py-3.5">
							<div className="mb-2 flex items-baseline justify-between gap-3">
								<span className="min-w-0 truncate text-[13px] font-semibold text-ink">{row.state}</span>
								<Money amount={row.amount} currency={row.currency} />
							</div>
							<Bar
								value={row.amount}
								max={max}
								label={`${row.state} expenditure`}
								tone="out"
							/>
							<div className="mt-1.5 text-[11.5px] text-muted">
								{row.count} {row.count === 1 ? "form" : "forms"}
							</div>
						</li>
					))}
				</ul>
			)}
		</Card>
	);
}

/**
 * Every currency the two registers hold, when there is more than one.
 *
 * Drawn only in that case. A society with one currency does not need a table
 * telling it so, and the headline figures above already read correctly.
 */
function CurrencyBreakdown({ net }: { net: FinanceSummary["net"] }) {
	return (
		<Card pad={false} className="mb-4">
			<SectionHead title="By currency" />
			<Table head={["Currency", "In", "Out", "Net"]} minWidth={480}>
				{net.map((row) => (
					<Row key={row.currency}>
						<Cell nowrap className="font-semibold text-ink">
							{row.currency}
						</Cell>
						<Cell nowrap>
							<Money amount={row.income} currency={row.currency} size="sm" />
						</Cell>
						<Cell nowrap>
							<Money amount={row.expenses} currency={row.currency} size="sm" />
						</Cell>
						<Cell nowrap>
							<Money
								amount={row.net}
								currency={row.currency}
								size="sm"
								className={cx(row.net < 0 && "!text-danger")}
							/>
						</Cell>
					</Row>
				))}
			</Table>
		</Card>
	);
}

function RecentIncome({ rows }: { rows: FinanceSummary["income"]["recent"] }) {
	return (
		<Card pad={false}>
			<SectionHead
				title="Latest membership payments"
				link={{ to: "/admin/registry/members", label: "Members" }}
			/>
			{rows.length === 0 ? (
				<Empty framed={false} title="Nothing recorded in this period" icon={Icon.receipt} />
			) : (
				<Table head={["Membership", "Paid", "Fee"]} minWidth={420}>
					{rows.map((row) => (
						<Row key={row.name}>
							<NameCell title={row.label} meta={row.status ?? undefined} />
							<Cell nowrap>{formatDate(row.paid_on)}</Cell>
							<Cell nowrap>
								{row.amount ? (
									<Money amount={row.amount} currency={row.currency} size="sm" />
								) : (
									<span className="text-[12px] text-warning">No fee set</span>
								)}
							</Cell>
						</Row>
					))}
				</Table>
			)}
		</Card>
	);
}

function RecentExpenses({ rows }: { rows: FinanceSummary["expenses"]["recent"] }) {
	return (
		<Card pad={false}>
			<SectionHead title="Latest stipend payments" link={{ to: "/admin/finance/stipends", label: "All" }} />
			{rows.length === 0 ? (
				<Empty framed={false} title="Nothing recorded in this period" icon={Icon.coins} />
			) : (
				<Table head={["Payment form", "Period", "Total"]} minWidth={420}>
					{rows.map((row) => (
						<Row key={row.name}>
							{/* The stipends screen is one page with its own tabs and no
							    per-document address, so the name is text rather than a
							    link that would land on the same list this row is
							    already beside. */}
							<NameCell title={row.name} meta={<StatusBadge state={row.state} />} />
							<Cell nowrap>
								{formatDate(row.period_from)} — {formatDate(row.period_to)}
							</Cell>
							<Cell nowrap>
								<Money amount={row.amount} currency={row.currency} size="sm" />
							</Cell>
						</Row>
					))}
				</Table>
			)}
		</Card>
	);
}
