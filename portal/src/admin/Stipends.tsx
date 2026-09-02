import { useContext, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, formatMoney, geoPath } from "../lib/format";
import type { StipendApproval, StipendPaymentForm, StipendReport } from "../portal/types";
import {
	Button,
	Card,
	Empty,
	ErrorNote,
	PageHeading,
	Pill,
	SectionTitle,
	Spinner,
	StateBadge,
	Table,
	Row,
	Cell,
	cx,
} from "../ui/primitives";

/**
 * The stipends console — the paperwork behind paying volunteers for a period.
 *
 * Two documents, and the order matters: a **progress report** says who worked
 * and on what, and a **payment form** hangs off it and says who attended on
 * which day and what that comes to. The form inherits its place and period from
 * the report rather than asking for them again, because `payment.py`'s own
 * `_assert_same_place` requires the two to describe one period of work in one
 * place, and a field a coordinator can fill in twice is a field they can fill
 * in inconsistently.
 *
 * **Nobody can approve this yet, and the screen says so rather than hiding it.**
 * Stipend approval runs from a supervisor to the head of the volunteer's
 * department, and departmental resolution does not exist in this app. The
 * refusal is the server's — `can_be_decided` is a constant `false` in
 * `stipend/services/approval.py` and `blocked_because` is its sentence — so
 * this screen prints what it was told instead of writing its own explanation or
 * drawing a button that would throw. Submitting for approval and withdrawing
 * both work today; the decision is the part that is honestly absent.
 *
 * **Totals are never typed.** Every figure on a payment form is summed from the
 * attendance grid by `attendance.per_volunteer`, so the answer to "what is owed
 * to this person" cannot disagree with the rows it sums.
 */
export default function AdminStipends() {
	const [tab, setTab] = useState<"reports" | "forms">("reports");

	return (
		<>
			<PageHeading title={<EditableText k="admin.stipends.heading" fallback="Stipends" />} />

			<div className="mb-4 flex flex-wrap gap-2">
				{(
					[
						["reports", "Progress reports"],
						["forms", "Payment forms"],
					] as const
				).map(([key, label]) => (
					<button
						key={key}
						type="button"
						onClick={() => setTab(key)}
						className={cx(
							"rounded-full border px-3.5 py-1.5 text-[12px] font-semibold transition",
							tab === key
								? "border-blue bg-rail text-white"
								: "border-card-line bg-white text-muted hover:border-blue hover:text-ink",
						)}
					>
						{label}
					</button>
				))}
			</div>

			{tab === "reports" ? <ReportList /> : <FormList />}
		</>
	);
}

const REPORT_DOCTYPE = "VMMS Stipend Progress Report";
const PAYMENT_DOCTYPE = "VMMS Stipend Payment Form";

/* --------------------------------------------------------------- approval */

/**
 * The approval strip, shared by both documents because it is genuinely the same
 * question asked twice.
 *
 * Every button here is drawn from a flag the server computed and re-checks on
 * the write. `can_be_decided` is false for both doctypes today and the sentence
 * beside it is `blocked_because`, which this component prints rather than
 * paraphrases.
 */
function ApprovalStrip({
	approval,
	busy,
	onAct,
}: {
	approval: StipendApproval;
	busy: string | null;
	onAct: (label: string, method: string) => void;
}) {
	return (
		<div className="mt-4 border-t border-card-line pt-3">
			<div className="flex flex-wrap items-center justify-between gap-2">
				<div className="flex flex-wrap items-center gap-2">
					<StateBadge state={approval.approval_state} />
					{approval.submitted_on && (
						<span className="text-[11.5px] text-slate-faint">
							submitted {formatDate(approval.submitted_on)}
							{approval.submitted_by ? ` by ${approval.submitted_by}` : ""}
						</span>
					)}
				</div>

				<div className="flex gap-2">
					{!approval.is_pending && (
						<Button
							disabled={busy !== null}
							onClick={() => onAct("submit", API.submitStipendForApproval)}
						>
							{busy === "submit" ? "Submitting…" : "Submit for approval"}
						</Button>
					)}
					{approval.can_be_withdrawn && (
						<Button
							variant="quiet"
							disabled={busy !== null}
							onClick={() => onAct("withdraw", API.withdrawStipend)}
						>
							{busy === "withdraw" ? "Withdrawing…" : "Withdraw"}
						</Button>
					)}
				</div>
			</div>

			{approval.is_pending && approval.blocked_because && (
				<p className="mt-2.5 rounded-xl bg-surface px-3 py-2 text-[11.5px] text-muted">
					{approval.blocked_because}
				</p>
			)}
			{approval.note && (
				<p className="mt-2 text-[11.5px] text-slate-faint">{approval.note}</p>
			)}
		</div>
	);
}

/** The two verbs both documents share, wired once. */
function useStipendActions(doctype: string, name: string, onChanged: () => void) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);

	const act = async (label: string, method: string, args: Record<string, unknown> = {}) => {
		setBusy(label);
		setFailure(null);

		try {
			await call.post(method, { doctype, name, ...args });
			onChanged();
		} catch (problem) {
			setFailure(errorMessage(problem));
		} finally {
			setBusy(null);
		}
	};

	return { busy, failure, act };
}

/* -------------------------------------------------------- progress reports */

function ReportList() {
	const [open, setOpen] = useState<string | null>(null);

	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: { doctype: string; count: number; paperwork: StipendReport[]; pending_count: number };
	}>(API.branchPaperwork, { doctype: REPORT_DOCTYPE }, "admin:stipend_reports");

	const rows = data?.message?.paperwork ?? [];

	return (
		<>
			{(data?.message?.pending_count ?? 0) > 0 && (
				<div className="mb-3">
					<Pill tone="navy">{data?.message?.pending_count} awaiting approval</Pill>
				</div>
			)}

			{isLoading && <Spinner label="Loading progress reports…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{data && rows.length === 0 && (
				<Empty title="No progress reports in your area">
					A progress report covers one period of work in one place and lists the volunteers it is
					about. Starting one is a desk action; once created it appears here. If you hold no geo
					assignment, this list is empty by design rather than by accident.
				</Empty>
			)}

			{rows.length > 0 && (
				<div className="grid gap-5 lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
					<ul className="space-y-2.5">
						{rows.map((row) => (
							<li key={row.report}>
								<button
									type="button"
									onClick={() => setOpen(row.report)}
									className={cx(
										"w-full rounded-xl border bg-white px-4 py-3 text-left transition",
										(open ?? rows[0]?.report) === row.report
											? "border-blue border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]"
											: "border-card-line hover:border-card-line",
									)}
								>
									<div className="flex items-start justify-between gap-2">
										<span className="text-[13.5px] font-bold text-ink">{row.report}</span>
										<StateBadge state={row.approval.approval_state} />
									</div>
									<div className="mt-1 text-[11.5px] text-muted">
										{geoPath(row.geo_path)}
									</div>
									<div className="mt-0.5 text-[11.5px] text-slate-faint">
										{row.volunteer_count} volunteer(s)
										{row.period_from ? ` · ${formatDate(row.period_from)}` : ""}
										{row.period_to ? ` → ${formatDate(row.period_to)}` : ""}
									</div>
								</button>
							</li>
						))}
					</ul>

					<ReportPane
						report={rows.find((row) => row.report === (open ?? rows[0].report)) ?? rows[0]}
						onChanged={() => void mutate()}
					/>
				</div>
			)}
		</>
	);
}

function ReportPane({ report, onChanged }: { report: StipendReport; onChanged: () => void }) {
	const { busy, failure, act } = useStipendActions(REPORT_DOCTYPE, report.report, onChanged);

	return (
		<Card>
			<div className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<SectionTitle>{report.report}</SectionTitle>
					<p className="text-[12px] text-muted">{geoPath(report.geo_path)}</p>
					<p className="mt-0.5 text-[12px] text-slate-faint">
						{report.period_from ? formatDate(report.period_from) : "No start"}
						{report.period_to ? ` → ${formatDate(report.period_to)}` : ""}
					</p>
				</div>
			</div>

			{report.volunteers.length === 0 ? (
				<p className="mt-3 text-[12.5px] text-slate-faint">
					No volunteers on this report yet. A report has to cover somebody before it can be
					submitted.
				</p>
			) : (
				<div className="mt-3">
					<Table head={["Volunteer", "Activity", "Department", "Notes"]}>
						{report.volunteers.map((row) => (
							<Row key={row.volunteer}>
								<Cell>{row.volunteer}</Cell>
								<Cell>{row.activity || "—"}</Cell>
								<Cell>{row.department || "—"}</Cell>
								<Cell>{row.notes || "—"}</Cell>
							</Row>
						))}
					</Table>
				</div>
			)}

			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<ApprovalStrip approval={report.approval} busy={busy} onAct={(l, m) => void act(l, m)} />
		</Card>
	);
}

/* ---------------------------------------------------------- payment forms */

function FormList() {
	const [open, setOpen] = useState<string | null>(null);

	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: {
			doctype: string;
			count: number;
			paperwork: StipendPaymentForm[];
			pending_count: number;
		};
	}>(API.branchPaperwork, { doctype: PAYMENT_DOCTYPE }, "admin:stipend_forms");

	const rows = data?.message?.paperwork ?? [];

	return (
		<>
			{(data?.message?.pending_count ?? 0) > 0 && (
				<div className="mb-3">
					<Pill tone="navy">{data?.message?.pending_count} awaiting approval</Pill>
				</div>
			)}

			{isLoading && <Spinner label="Loading payment forms…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{data && rows.length === 0 && (
				<Empty title="No payment forms in your area">
					A payment form hangs off a progress report and records who attended on which day. It
					inherits the report's place and period, because the two describe one period of work in
					one place.
				</Empty>
			)}

			{rows.length > 0 && (
				<div className="grid gap-5 lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)]">
					<ul className="space-y-2.5">
						{rows.map((row) => (
							<li key={row.payment_form}>
								<button
									type="button"
									onClick={() => setOpen(row.payment_form)}
									className={cx(
										"w-full rounded-xl border bg-white px-4 py-3 text-left transition",
										(open ?? rows[0]?.payment_form) === row.payment_form
											? "border-blue border border-card-line shadow-[0_1px_2px_rgba(30,50,73,0.025)]"
											: "border-card-line hover:border-card-line",
									)}
								>
									<div className="flex items-start justify-between gap-2">
										<span className="text-[13.5px] font-bold text-ink">
											{row.payment_form}
										</span>
										<StateBadge state={row.approval.approval_state} />
									</div>
									<div className="mt-1 text-[11.5px] text-muted">
										{geoPath(row.geo_path)}
									</div>
									<div className="mt-0.5 text-[11.5px] text-slate-faint">
										{formatMoney(row.total_payable, row.currency)} · {row.line_count}{" "}
										attendance line(s)
									</div>
								</button>
							</li>
						))}
					</ul>

					<FormPane
						form={
							rows.find((row) => row.payment_form === (open ?? rows[0].payment_form)) ??
							rows[0]
						}
						onChanged={() => void mutate()}
					/>
				</div>
			)}
		</>
	);
}

function FormPane({ form, onChanged }: { form: StipendPaymentForm; onChanged: () => void }) {
	const { busy, failure, act } = useStipendActions(PAYMENT_DOCTYPE, form.payment_form, onChanged);

	return (
		<Card>
			<div className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<SectionTitle>{form.payment_form}</SectionTitle>
					<p className="text-[12px] text-muted">{geoPath(form.geo_path)}</p>
					<p className="mt-0.5 text-[12px] text-slate-faint">
						{form.period_from ? formatDate(form.period_from) : "No start"}
						{form.period_to ? ` → ${formatDate(form.period_to)}` : ""}
						{form.progress_report ? ` · against ${form.progress_report}` : ""}
					</p>
				</div>
				<div className="text-right">
					<div className="text-[22px] font-bold text-ink">
						{formatMoney(form.total_payable, form.currency)}
					</div>
					<div className="text-[11px] text-slate-faint">total payable</div>
				</div>
			</div>

			{form.per_volunteer.length === 0 ? (
				<p className="mt-3 text-[12.5px] text-slate-faint">
					No attendance recorded on this form yet. Every figure here is summed from the grid, so
					there is nothing to total until somebody is marked present.
				</p>
			) : (
				<div className="mt-3">
					<Table head={["Volunteer", "Days attended", "Days recorded", "Hours", "Payable"]}>
						{form.per_volunteer.map((row) => (
							<Row key={row.volunteer}>
								<Cell>{row.volunteer}</Cell>
								<Cell>{row.days_attended}</Cell>
								<Cell>{row.days_recorded}</Cell>
								<Cell>{row.hours}</Cell>
								<Cell>{formatMoney(row.total_payable, form.currency)}</Cell>
							</Row>
						))}
					</Table>
					<p className="mt-2 text-[11.5px] text-slate-faint">
						Days attended and days recorded differ whenever an absence was marked, which is why
						both are shown: a total that dropped the distinction would hide a patchy period.
					</p>
				</div>
			)}

			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<ApprovalStrip approval={form.approval} busy={busy} onAct={(l, m) => void act(l, m)} />
		</Card>
	);
}
