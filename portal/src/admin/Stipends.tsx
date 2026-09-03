import { useContext, useState, type ReactNode } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, formatMoney, geoPath } from "../lib/format";
import type {
	GeoNode,
	StipendApproval,
	StipendPaymentForm,
	StipendReport,
} from "../portal/types";
import { GeoSelects, selectedNode } from "../ui/GeoSelects";
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

/* --------------------------------------------------------------- controls */

// The console's own field styling, matching `admin/Tasks.tsx` and
// `admin/Projects.tsx` rather than introducing a third look for one screen.
const INPUT =
	"w-full rounded-xl border border-card-line px-3 py-2.5 text-[13px] outline-none focus:border-blue";

function Labelled({
	label,
	hint,
	children,
}: {
	label: string;
	hint?: string;
	children: ReactNode;
}) {
	return (
		<label className="block">
			<span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-faint">
				{label}
			</span>
			{children}
			{hint && <span className="mt-1 block text-[11.5px] text-slate-faint">{hint}</span>}
		</label>
	);
}

/* ------------------------------------------------------------ starting one */

/**
 * A collapsed panel that opens into a form. Used by both documents.
 *
 * Collapsed because a console whose first screen is a blank form is a console
 * that puts creating a record above reading the ones already there, and reading
 * is what somebody opening this tab is nearly always doing.
 */
function Starter({
	label,
	title,
	lead,
	children,
	open,
	onOpen,
}: {
	label: string;
	title: string;
	lead: string;
	children: ReactNode;
	open: boolean;
	onOpen: (open: boolean) => void;
}) {
	if (!open) {
		return (
			<Button variant="navy" onClick={() => onOpen(true)}>
				{label}
			</Button>
		);
	}

	return (
		<Card>
			<SectionTitle>{title}</SectionTitle>
			<p className="mt-1 text-[12.5px] leading-relaxed text-muted">{lead}</p>
			<div className="mt-4">{children}</div>
		</Card>
	);
}

/**
 * Starting a progress report from the console.
 *
 * `create_report` has been on the server the whole time and no screen called
 * it: the empty state said "starting one is a desk action", which is a console
 * telling somebody to go somewhere else to begin the work it exists for.
 *
 * **The narrative is asked for here because the record requires it.** It is
 * mandatory on the doctype and it is the substance of the document — what the
 * branch did over the period — so a form that skipped it would create a record
 * the framework refuses, with a field name for a message.
 */
function StartReport({ onCreated }: { onCreated: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [open, setOpen] = useState(false);
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [from, setFrom] = useState("");
	const [to, setTo] = useState("");
	const [narrative, setNarrative] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const node = selectedNode(chain);

	// A period that ends before it starts is not a period. Said here so the
	// sentence names the problem rather than the save refusing it.
	const backwards = Boolean(from && to && to < from);
	const ready = Boolean(node && from && to && narrative.trim()) && !backwards;

	const create = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.createStipendReport, {
				geo_node: node?.name,
				period_from: from,
				period_to: to,
				narrative: narrative.trim(),
			});
			setOpen(false);
			setChain([]);
			setFrom("");
			setTo("");
			setNarrative("");
			onCreated();
		} catch (problem) {
			setFailure(errorMessage(problem, "That report was not created."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Starter
			open={open}
			onOpen={setOpen}
			label="Start a progress report"
			title="Start a progress report"
			lead="One period of work in one place, and the volunteers it was about. You add the people to it once it exists."
		>
			<div className="grid gap-4 sm:grid-cols-2">
				<Labelled label="Period from">
					<input
						type="date"
						className={INPUT}
						value={from}
						onChange={(event) => setFrom(event.target.value)}
					/>
				</Labelled>
				<Labelled
					label="Period to"
					hint={backwards ? "This is before the start of the period." : undefined}
				>
					<input
						type="date"
						className={INPUT}
						value={to}
						min={from || undefined}
						onChange={(event) => setTo(event.target.value)}
					/>
				</Labelled>
			</div>

			<div className="mt-4">
				<Labelled
					label="What the branch did"
					hint="The narrative this report is. Required, and it is what the approver reads."
				>
					<textarea
						className={cx(INPUT, "min-h-[120px] resize-y")}
						value={narrative}
						onChange={(event) => setNarrative(event.target.value)}
					/>
				</Labelled>
			</div>

			<div className="mt-4">
				<p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-faint">
					Where this work happened
				</p>
				<GeoSelects chain={chain} onChain={setChain} idPrefix="stipend-report" />
			</div>

			{failure && (
				<div className="mt-4">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<div className="mt-5 flex flex-wrap gap-2">
				<Button disabled={busy || !ready} onClick={() => void create()}>
					{busy ? "Starting…" : "Start the report"}
				</Button>
				<Button variant="navy" onClick={() => setOpen(false)}>
					Cancel
				</Button>
			</div>
		</Starter>
	);
}

/**
 * Starting a payment form against a report.
 *
 * **The place and the period are not asked for and must not be.**
 * `create_payment_form` copies all three off the report it names, because
 * `payment.py`'s own `_assert_same_place` requires the two documents to describe
 * one period of work in one place — a form that asked again is a form somebody
 * can answer inconsistently.
 *
 * Only draft reports are offered. A form hanging off a report that is already
 * with an approver is paperwork about a decision nobody has made yet.
 */
function StartPaymentForm({ onCreated }: { onCreated: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [open, setOpen] = useState(false);
	const [report, setReport] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const reports = useFrappeGetCall<{ message: { paperwork: StipendReport[] } }>(
		API.branchPaperwork,
		{ doctype: REPORT_DOCTYPE },
		open ? "admin:stipend_reports:for-form" : null,
	);

	const options = (reports.data?.message?.paperwork ?? []).filter(
		(row) => row.volunteer_count > 0,
	);

	const create = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.createPaymentForm, { progress_report: report });
			setOpen(false);
			setReport("");
			onCreated();
		} catch (problem) {
			setFailure(errorMessage(problem, "That payment form was not created."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Starter
			open={open}
			onOpen={setOpen}
			label="Start a payment form"
			title="Start a payment form"
			lead="Against a progress report that already covers somebody. It takes the report's place, period and currency, so there is nothing here to answer twice."
		>
			{reports.isLoading ? (
				<Spinner label="Loading reports…" />
			) : options.length === 0 ? (
				<p className="text-[12.5px] leading-relaxed text-slate-faint">
					No progress report covers anybody yet. A payment form pays the volunteers its report
					names, so there has to be a report with people on it first.
				</p>
			) : (
				<>
					<Labelled label="Progress report" hint="The form inherits its place and period.">
						<select
							className={INPUT}
							value={report}
							onChange={(event) => setReport(event.target.value)}
						>
							<option value="">Select…</option>
							{options.map((row) => (
								<option key={row.report} value={row.report}>
									{row.report} — {geoPath(row.geo_path)}
									{row.period_from ? ` · ${formatDate(row.period_from)}` : ""}
								</option>
							))}
						</select>
					</Labelled>

					{failure && (
						<div className="mt-4">
							<ErrorNote>{failure}</ErrorNote>
						</div>
					)}

					<div className="mt-5 flex flex-wrap gap-2">
						<Button disabled={busy || !report} onClick={() => void create()}>
							{busy ? "Starting…" : "Start the form"}
						</Button>
						<Button variant="navy" onClick={() => setOpen(false)}>
							Cancel
						</Button>
					</div>
				</>
			)}
		</Starter>
	);
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

			<div className="mb-4">
				<StartReport onCreated={() => void mutate()} />
			</div>

			{data && rows.length === 0 && (
				<Empty title="No progress reports in your area">
					A progress report covers one period of work in one place and lists the volunteers it is
					about. Start one above. If you hold no geo assignment, this list is empty by design
					rather than by accident.
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

	// The server's own answer, not a comparison written here: `approval.status`
	// reports the state and `_assert_draft` is what actually refuses the write.
	const editable = report.approval.approval_state === "Draft";

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

			<Narrative report={report} editable={editable} onChanged={onChanged} />

			{report.volunteers.length === 0 ? (
				<p className="mt-4 text-[12.5px] text-slate-faint">
					No volunteers on this report yet. A report has to cover somebody before it can be
					submitted.
				</p>
			) : (
				<div className="mt-4">
					<Table
						head={[
							"Volunteer",
							"Activity",
							"Department",
							"Notes",
							...(editable ? [""] : []),
						]}
					>
						{report.volunteers.map((row) => (
							<Row key={row.volunteer}>
								<Cell>{row.volunteer}</Cell>
								<Cell>{row.activity || "—"}</Cell>
								{/* Filled in by the routing service from the volunteer's
								    own record, never typed here — which is why there is
								    no control for it. */}
								<Cell>{row.department || "—"}</Cell>
								<Cell>{row.notes || "—"}</Cell>
								{editable && (
									<Cell>
										<RemoveVolunteer
											report={report.report}
											volunteer={row.volunteer}
											onChanged={onChanged}
										/>
									</Cell>
								)}
							</Row>
						))}
					</Table>
				</div>
			)}

			{/* Frozen once submitted, because the substance of the report is
			    somebody else's to decide until it comes back. The server refuses
			    it either way — `_assert_draft` — and this is the same rule said
			    where a supervisor can act on it. */}
			{editable && <AddVolunteer report={report.report} onChanged={onChanged} />}

			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<ApprovalStrip approval={report.approval} busy={busy} onAct={(l, m) => void act(l, m)} />
		</Card>
	);
}

/**
 * What the branch did, shown and — while the report is a draft — corrected.
 *
 * Stored as a Text Editor field, so it comes back as HTML written by a
 * supervisor on the desk. Rendered as markup for that reason and read-only in
 * that state; the editor here is a plain textarea, because a rich-text control
 * in a console pane is a dependency and a paste-handling problem for a field
 * most people will type three sentences into.
 */
function Narrative({
	report,
	editable,
	onChanged,
}: {
	report: StipendReport;
	editable: boolean;
	onChanged: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [open, setOpen] = useState(false);
	const [draft, setDraft] = useState(report.narrative ?? "");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const save = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.setReportNarrative, {
				name: report.report,
				narrative: draft.trim(),
			});
			setOpen(false);
			onChanged();
		} catch (problem) {
			setFailure(errorMessage(problem, "That narrative was not saved."));
		} finally {
			setBusy(false);
		}
	};

	if (open) {
		return (
			<div className="mt-4">
				<Labelled label="What the branch did" hint="Required. It is what the approver reads.">
					<textarea
						className={cx(INPUT, "min-h-[140px] resize-y")}
						value={draft}
						onChange={(event) => setDraft(event.target.value)}
					/>
				</Labelled>

				{failure && (
					<div className="mt-3">
						<ErrorNote>{failure}</ErrorNote>
					</div>
				)}

				<div className="mt-3 flex flex-wrap gap-2">
					<Button disabled={busy || !draft.trim()} onClick={() => void save()}>
						{busy ? "Saving…" : "Save narrative"}
					</Button>
					<Button
						variant="navy"
						onClick={() => {
							setDraft(report.narrative ?? "");
							setOpen(false);
						}}
					>
						Cancel
					</Button>
				</div>
			</div>
		);
	}

	return (
		<div className="mt-4 rounded-xl bg-surface px-4 py-3.5">
			<div className="flex flex-wrap items-start justify-between gap-2">
				<p className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
					What the branch did
				</p>
				{editable && (
					<button
						type="button"
						onClick={() => setOpen(true)}
						className="text-[11.5px] font-semibold text-ink hover:underline"
					>
						{report.narrative ? "Edit" : "Write it"}
					</button>
				)}
			</div>

			{report.narrative ? (
				<div
					className="article-body mt-2 text-[12.5px] leading-relaxed text-muted"
					// The society's own words, written on the desk or in the editor
					// above. Rendered as the Text Editor field stores them.
					dangerouslySetInnerHTML={{ __html: report.narrative }}
				/>
			) : (
				<p className="mt-2 text-[12.5px] text-slate-faint">
					Nothing written yet. The report cannot be submitted without it.
				</p>
			)}
		</div>
	);
}

/**
 * Putting a volunteer on a report.
 *
 * The identifier goes through `stipend/services/picker.py` on the server, which
 * scope-checks it — so the search here can only ever offer people this session
 * could already see, and typing a name they may not see returns nothing.
 *
 * `activity` and `notes` are the row's own two columns and both are optional.
 * They are asked for beside the person rather than in a second step, because
 * "who, and what were they doing" is one thought.
 */
function AddVolunteer({ report, onChanged }: { report: string; onChanged: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [open, setOpen] = useState(false);
	const [search, setSearch] = useState("");
	const [picked, setPicked] = useState("");
	const [activity, setActivity] = useState("");
	const [notes, setNotes] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const found = useFrappeGetCall<{
		message: { candidates: Array<{ volunteer: string; full_name: string }> };
	}>(
		API.findStipendVolunteers,
		{ search: search || undefined, limit: 20 },
		open ? `admin:stipend:volunteers:${search}` : null,
	);

	const add = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.addVolunteerToReport, {
				name: report,
				identifier: picked,
				activity: activity.trim() || undefined,
				notes: notes.trim() || undefined,
			});
			setPicked("");
			setActivity("");
			setNotes("");
			setSearch("");
			onChanged();
		} catch (problem) {
			setFailure(errorMessage(problem, "That volunteer was not added."));
		} finally {
			setBusy(false);
		}
	};

	if (!open) {
		return (
			<div className="mt-4">
				<Button variant="navy" onClick={() => setOpen(true)}>
					Add a volunteer
				</Button>
			</div>
		);
	}

	return (
		<div className="mt-4 rounded-xl border border-card-line p-4">
			<p className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
				Add a volunteer
			</p>

			<div className="mt-3 grid gap-4 sm:grid-cols-2">
				<Labelled label="Search" hint="By name or email. Only people in your area.">
					<input
						className={INPUT}
						value={search}
						onChange={(event) => setSearch(event.target.value)}
						placeholder="Amina"
					/>
				</Labelled>

				<Labelled label="Volunteer">
					<select
						className={INPUT}
						value={picked}
						onChange={(event) => setPicked(event.target.value)}
					>
						<option value="">Select…</option>
						{(found.data?.message?.candidates ?? []).map((row) => (
							<option key={row.volunteer} value={row.volunteer}>
								{row.full_name || row.volunteer}
							</option>
						))}
					</select>
				</Labelled>

				<Labelled label="Role or activity" hint="What they were doing over the period.">
					<input
						className={INPUT}
						value={activity}
						onChange={(event) => setActivity(event.target.value)}
						placeholder="First aid post"
					/>
				</Labelled>

				<Labelled label="Notes">
					<input
						className={INPUT}
						value={notes}
						onChange={(event) => setNotes(event.target.value)}
						placeholder="Optional"
					/>
				</Labelled>
			</div>

			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<div className="mt-4 flex flex-wrap gap-2">
				<Button disabled={busy || !picked} onClick={() => void add()}>
					{busy ? "Adding…" : "Add to the report"}
				</Button>
				<Button variant="navy" onClick={() => setOpen(false)}>
					Done
				</Button>
			</div>
		</div>
	);
}

/**
 * Taking somebody off a report.
 *
 * The server refuses this while a paired payment form still pays them — a
 * report says who the period was about and a form may only pay those people —
 * so the refusal is shown rather than the button being hidden: "why can I not
 * remove this person" has an answer, and it is the sentence the server sends.
 */
function RemoveVolunteer({
	report,
	volunteer,
	onChanged,
}: {
	report: string;
	volunteer: string;
	onChanged: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const remove = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.removeVolunteerFromReport, { name: report, volunteer });
			onChanged();
		} catch (problem) {
			setFailure(errorMessage(problem, "That volunteer was not removed."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<>
			<button
				type="button"
				disabled={busy}
				onClick={() => void remove()}
				className="text-[11.5px] font-semibold text-slate-faint hover:text-danger hover:underline disabled:opacity-50"
			>
				{busy ? "Removing…" : "Remove"}
			</button>
			{failure && (
				<span className="mt-1 block text-[11px] leading-snug text-danger">{failure}</span>
			)}
		</>
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

			<div className="mb-4">
				<StartPaymentForm onCreated={() => void mutate()} />
			</div>

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

/**
 * Marking one volunteer's one day on a payment form.
 *
 * **A day at a time, deliberately.** `record_attendance` is idempotent per
 * volunteer and per date — a second call for the same pair replaces that day's
 * line rather than adding a second one — which is what keeps a day's total the
 * day's total. So this is a form that records one line and stays open, rather
 * than a grid that submits a fortnight at once and has to reconcile what was
 * already there.
 *
 * **The stipend is typed and the totals never are.** What a person is paid for
 * a day is a decision; what they are owed for the period is arithmetic, and
 * `attendance.per_volunteer` does it. There is no total on this form to type
 * and no way to make one disagree with the rows it sums.
 *
 * **An absence is a record, not a gap.** The tick defaults on, and unticking it
 * files a day the volunteer was expected and did not attend — which is why the
 * table above shows days recorded beside days attended.
 */
function RecordAttendance({
	form,
	onChanged,
}: {
	form: StipendPaymentForm;
	onChanged: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [open, setOpen] = useState(false);
	const [volunteer, setVolunteer] = useState("");
	const [date, setDate] = useState("");
	const [attended, setAttended] = useState(true);
	const [hours, setHours] = useState("");
	const [amount, setAmount] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	// The people the paired report names. A form may pay only those, which is
	// the service's own rule — so the picker is that list rather than a search
	// across the branch, and a name that could only ever be refused is not
	// offered.
	const report = useFrappeGetCall<{ message: StipendReport }>(
		API.getStipendReport,
		{ name: form.progress_report },
		open && form.progress_report ? `admin:stipend:report:${form.progress_report}` : null,
	);

	const covered = report.data?.message?.volunteers ?? [];

	// Outside the period is a line the form should not carry: the two documents
	// describe one period of work, and a day beyond it belongs to another form.
	const outsidePeriod = Boolean(
		date &&
			((form.period_from && date < form.period_from) ||
				(form.period_to && date > form.period_to)),
	);

	const record = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.recordAttendance, {
				name: form.payment_form,
				identifier: volunteer,
				attendance_date: date,
				attended,
				hours: hours || undefined,
				// Always sent. An absence is worth nothing and saying so
				// explicitly is what stops a previous line's figure standing.
				stipend_amount: attended ? amount || 0 : 0,
			});
			// The volunteer and the date stay: a supervisor working through a
			// fortnight records the same person day after day, and clearing the
			// form each time would make them re-pick on every line.
			setHours("");
			onChanged();
		} catch (problem) {
			setFailure(errorMessage(problem, "That day was not recorded."));
		} finally {
			setBusy(false);
		}
	};

	if (!open) {
		return (
			<div className="mt-4">
				<Button variant="navy" onClick={() => setOpen(true)}>
					Record attendance
				</Button>
			</div>
		);
	}

	return (
		<div className="mt-4 rounded-xl border border-card-line p-4">
			<p className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
				Record a day
			</p>
			<p className="mt-1 text-[11.5px] leading-relaxed text-slate-faint">
				One volunteer, one day. Recording the same day again replaces that line rather than
				adding a second one.
			</p>

			{covered.length === 0 ? (
				<p className="mt-3 text-[12.5px] text-slate-faint">
					The report behind this form covers nobody yet. A form pays the volunteers its report
					names, so add them to the report first.
				</p>
			) : (
				<>
					<div className="mt-3 grid gap-4 sm:grid-cols-2">
						<Labelled label="Volunteer">
							<select
								className={INPUT}
								value={volunteer}
								onChange={(event) => setVolunteer(event.target.value)}
							>
								<option value="">Select…</option>
								{covered.map((row) => (
									<option key={row.volunteer} value={row.volunteer}>
										{row.volunteer}
										{row.activity ? ` — ${row.activity}` : ""}
									</option>
								))}
							</select>
						</Labelled>

						<Labelled
							label="Date"
							hint={
								outsidePeriod
									? "This day is outside the form's period."
									: form.period_from
										? `Within ${formatDate(form.period_from)} → ${form.period_to ? formatDate(form.period_to) : "…"}`
										: undefined
							}
						>
							<input
								type="date"
								className={INPUT}
								value={date}
								min={form.period_from ?? undefined}
								max={form.period_to ?? undefined}
								onChange={(event) => setDate(event.target.value)}
							/>
						</Labelled>

						<Labelled label="Hours" hint="Optional.">
							<input
								type="number"
								min="0"
								step="0.5"
								className={INPUT}
								value={hours}
								disabled={!attended}
								onChange={(event) => setHours(event.target.value)}
							/>
						</Labelled>

						<Labelled label={`Stipend (${form.currency ?? ""})`.trim()} hint="For this day.">
							<input
								type="number"
								min="0"
								step="0.01"
								className={INPUT}
								value={amount}
								disabled={!attended}
								onChange={(event) => setAmount(event.target.value)}
							/>
						</Labelled>
					</div>

					<label className="mt-3 flex cursor-pointer items-start gap-2.5">
						<input
							type="checkbox"
							checked={attended}
							onChange={(event) => setAttended(event.target.checked)}
							className="mt-0.5 h-4 w-4 flex-none accent-blue"
						/>
						<span>
							<span className="block text-[12.5px] font-semibold text-ink">
								They were there
							</span>
							<span className="mt-0.5 block text-[11.5px] leading-relaxed text-slate-faint">
								Untick to record a day they were expected and did not attend. It is filed as a
								day recorded and pays nothing.
							</span>
						</span>
					</label>

					{failure && (
						<div className="mt-3">
							<ErrorNote>{failure}</ErrorNote>
						</div>
					)}

					<div className="mt-4 flex flex-wrap gap-2">
						<Button
							disabled={busy || !volunteer || !date || outsidePeriod}
							onClick={() => void record()}
						>
							{busy ? "Recording…" : "Record this day"}
						</Button>
						<Button variant="navy" onClick={() => setOpen(false)}>
							Done
						</Button>
					</div>
				</>
			)}
		</div>
	);
}

function FormPane({ form, onChanged }: { form: StipendPaymentForm; onChanged: () => void }) {
	const { busy, failure, act } = useStipendActions(PAYMENT_DOCTYPE, form.payment_form, onChanged);

	const editable = form.approval.approval_state === "Draft";

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

			{editable && <RecordAttendance form={form} onChanged={onChanged} />}

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
