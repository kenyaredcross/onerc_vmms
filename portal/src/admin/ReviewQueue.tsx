import { useContext, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, geoPath } from "../lib/format";
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
	cx,
} from "../ui/primitives";
import type { ApplicationDecision, ApprovalStatus } from "../portal/types";

/**
 * The one doctype with a structured decision view behind it. Named here rather
 * than branched on elsewhere: a second approvable doctype gains a panel by
 * getting its own endpoint, not by this screen learning what it is.
 */
const APPLICATION_DOCTYPE = "VMMS Volunteer Application";

/** One declared vocabulary, drawn only when the applicant declared anything. */
function Declared({ label, rows }: { label: string; rows: Array<{ key: string; label: string }> }) {
	if (!rows.length) return null;

	return (
		<div className="flex flex-wrap items-baseline gap-x-2 gap-y-1.5">
			<span className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
				{label}
			</span>
			{rows.map((row) => (
				<span
					key={row.key}
					className="rounded-full bg-page px-2.5 py-1 text-[11.5px] font-medium text-slate-body"
				>
					{row.label}
				</span>
			))}
		</div>
	);
}

/**
 * Deciding on what has been routed to you.
 *
 * The design's two-pane console: the queue on the left, one application open on
 * the right with approve and decline on it.
 *
 * **Three rules from the approval engine are visible in this file and none of
 * them is re-implemented here.**
 *
 * 1. *The queue is already the answer.* `my_queue` returns only documents whose
 *    routing still resolves to this user right now, re-checked per row rather
 *    than trusted from a ToDo. So this screen filters nothing.
 * 2. *`can_act` decides whether the buttons exist.* Not the state, not the
 *    stage, not whether the user holds a role. Being *a* coordinator does not
 *    make somebody *this* document's coordinator, which is the whole reason
 *    this app does not use Frappe's native Workflow.
 * 3. *`stage.label` is displayed and never compared.* Stages are society
 *    configuration; the Python side has an AST test that fails the build if a
 *    stage label reaches a comparison, and the same discipline applies here.
 */
export default function ReviewQueue() {
	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: ApprovalStatus[] }>(
		API.myQueue,
		undefined,
		"admin:my_queue",
	);

	const rows = data?.message ?? [];
	const [selected, setSelected] = useState<string | null>(null);

	const open = rows.find((row) => `${row.doctype}:${row.name}` === selected) ?? rows[0] ?? null;

	return (
		<>
			<PageHeading
				title={<EditableText k="admin.queue.heading" fallback="Review queue" />}
				actions={<Pill tone="navy">{rows.length} waiting</Pill>}
			/>

			{isLoading && <Spinner label="Loading the review queue…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && rows.length === 0 && (
				<Empty title={<EditableText k="admin.queue.empty" fallback="Nothing is waiting on you." />}>
					Applications appear here when the engine routes one to you specifically, not to
					everybody who holds your role.
				</Empty>
			)}

			{rows.length > 0 && (
				<div className="grid gap-5 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
					<ul className="space-y-2.5">
						{rows.map((row) => {
							const id = `${row.doctype}:${row.name}`;
							const active = open && `${open.doctype}:${open.name}` === id;

							return (
								<li key={id}>
									<button
										type="button"
										onClick={() => setSelected(id)}
										className={cx(
											"w-full rounded-card border px-4 py-3.5 text-left transition",
											active
												? "border-navy bg-navy/5"
												: "border-hairline bg-white hover:border-hairline-strong",
										)}
									>
										<div className="flex items-center justify-between gap-3">
											<span className="font-mono text-[11.5px] text-slate-faint">
												{row.name}
											</span>
											{row.stage?.is_breached && <Pill tone="signal">Overdue</Pill>}
										</div>
										<div className="mt-1 font-display text-[14px] font-bold text-ink">
											{row.doctype.replace(/^VMMS /, "")}
										</div>
										<div className="mt-0.5 text-[11.5px] text-slate-body">
											{geoPath(row.geo_path)}
										</div>
										{row.stage && (
											<div className="mt-2 text-[11px] font-semibold text-navy">
												{row.stage.label}
											</div>
										)}
									</button>
								</li>
							);
						})}
					</ul>

					{open && <Detail status={open} onDecided={() => void mutate()} />}
				</div>
			)}
		</>
	);
}

function Detail({ status, onDecided }: { status: ApprovalStatus; onDecided: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [reason, setReason] = useState("");
	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);

	/**
	 * The application itself, for the one doctype that has a decision view.
	 *
	 * Fetched beside the approval rather than merged into it, because they are
	 * two different questions with two different permission answers: the engine
	 * decides how much of the approver list this caller may see, and the
	 * application's own read check decides whether they may see the application.
	 * A doctype with no such view simply does not get the panel, which is the
	 * `<NotBuilt>` rule applied to half a screen.
	 */
	const detail = useFrappeGetCall<{ message: ApplicationDecision }>(
		API.applicationDecision,
		{ name: status.name },
		status.doctype === APPLICATION_DOCTYPE ? `review:decision:${status.name}` : null,
	);

	const application = detail.data?.message;

	const decide = async (decision: "Approved" | "Rejected" | "More info requested") => {
		setBusy(decision);
		setFailure(null);

		try {
			await call.post(API.decide, {
				doctype: status.doctype,
				name: status.name,
				decision,
				reason: reason || undefined,
			});
			setReason("");
			onDecided();
		} catch (decideError) {
			setFailure(errorMessage(decideError, "That decision was not recorded."));
		} finally {
			setBusy(null);
		}
	};

	return (
		<Card>
			<div className="mb-5 flex flex-wrap items-start justify-between gap-3">
				<div>
					<h2 className="font-display text-[19px] font-extrabold tracking-tight text-ink">
						{status.doctype.replace(/^VMMS /, "")}
					</h2>
					<p className="mt-1 font-mono text-[12px] text-slate-faint">{status.name}</p>
				</div>
				<StateBadge state={status.state} />
			</div>

			<dl className="grid gap-4 border-y border-hairline py-5 sm:grid-cols-2">
				<Field label="Anchored at" value={geoPath(status.geo_path) || "—"} />
				<Field label="Stage" value={status.stage?.label ?? "—"} />
				<Field
					label="Entered stage"
					value={status.stage ? formatDate(status.stage.entered_on) : "—"}
				/>
				<Field
					label="Due"
					value={
						status.stage?.due_on
							? `${formatDate(status.stage.due_on)}${status.stage.is_breached ? ` · ${status.stage.days_overdue} days over` : ""}`
							: "—"
					}
				/>
				<Field label="Decision rule" value={status.stage?.completion_rule ?? "—"} />
				<Field label="Approvers resolved" value={String(status.approver_count)} />
			</dl>

			{application && (
				<div className="border-b border-hairline py-5">
					<SectionTitle>The applicant</SectionTitle>
					<dl className="grid gap-4 sm:grid-cols-2">
						<Field label="Name" value={application.full_name || "—"} />
						<Field label="Email" value={application.email || "—"} />
						<Field label="Phone" value={application.phone || "—"} />
						<Field
							label="Identification"
							value={
								application.identification?.id_number
									? `${application.identification.id_type_name ?? application.identification.id_type ?? ""} ${application.identification.id_number}`.trim()
									: "—"
							}
						/>
						<Field label="Citizenship" value={application.country_of_citizenship || "—"} />
						<Field
							label="Lives"
							value={
								application.residency_type === "Abroad"
									? [application.country_of_residence, application.residence_address]
											.filter(Boolean)
											.join(" · ") || "Abroad"
									: geoPath(application.home_geo_path) || "—"
							}
						/>
					</dl>

					{(application.skills.length > 0 ||
						application.languages.length > 0 ||
						application.availability.length > 0 ||
						application.motivation.length > 0) && (
						<div className="mt-5 space-y-3">
							<Declared label="Skills" rows={application.skills} />
							<Declared label="Languages" rows={application.languages} />
							<Declared label="Availability" rows={application.availability} />
							<Declared label="Motivation" rows={application.motivation} />
						</div>
					)}

					{application.prior_experience && (
						<div className="mt-5">
							<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
								In their own words
							</dt>
							<dd className="mt-1 whitespace-pre-line text-[13px] leading-relaxed text-ink">
								{application.prior_experience}
							</dd>
						</div>
					)}
				</div>
			)}

			{/* What this society asked for beyond the standard form, and what the
			    applicant answered. The wording is the snapshot taken when they
			    answered, so a question reworded since still reads as it was asked. */}
			{application && application.answers.length > 0 && (
				<div className="border-b border-hairline py-5">
					<SectionTitle>What the society asked</SectionTitle>
					<dl className="grid gap-4 sm:grid-cols-2">
						{application.answers.map((answer) => (
							<div key={answer.question}>
								<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
									{answer.label}
								</dt>
								<dd className="mt-1 text-[13px] text-ink">
									{answer.is_file ? (
										answer.file_url ? (
											<a
												className="font-semibold text-navy underline underline-offset-2"
												href={answer.file_url}
												target="_blank"
												rel="noreferrer"
											>
												Open the file
											</a>
										) : (
											"—"
										)
									) : answer.field_type === "Check" ? (
										answer.value === "1" ? (
											"Yes"
										) : (
											"No"
										)
									) : (
										answer.value || "—"
									)}
								</dd>
							</div>
						))}
					</dl>
				</div>
			)}

			{status.decisions.length > 0 && (
				<div className="border-b border-hairline py-5">
					<SectionTitle>Decisions so far</SectionTitle>
					<ul className="space-y-2">
						{status.decisions.map((decision, index) => (
							<li
								key={index}
								className="flex flex-wrap items-baseline justify-between gap-2 rounded-card bg-page px-3.5 py-2.5 text-[12.5px]"
							>
								<span className="font-semibold text-ink">
									{decision.decision} · {decision.stage_label}
								</span>
								<span className="text-slate-body">
									{decision.decided_by} · {formatDate(decision.decided_on ?? null)}
								</span>
								{decision.reason && (
									<span className="w-full text-slate-body">{decision.reason}</span>
								)}
							</li>
						))}
					</ul>
				</div>
			)}

			{failure && (
				<div className="mt-5">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			{status.can_act ? (
				<div className="mt-5">
					<label
						className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-faint"
						htmlFor="decision-reason"
					>
						Reason {status.stage?.can_reject ? "(required to decline)" : "(optional)"}
					</label>
					<textarea
						id="decision-reason"
						className="min-h-[80px] w-full resize-y rounded-card border border-hairline-strong px-3 py-2.5 text-[13px] outline-none focus:border-navy"
						value={reason}
						onChange={(event) => setReason(event.target.value)}
					/>

					<div className="mt-4 flex flex-wrap gap-2.5">
						<Button
							variant="navy"
							onClick={() => decide("Approved")}
							disabled={busy !== null}
						>
							{busy === "Approved" ? "Approving…" : "Approve"}
						</Button>
						{/* Not a rejection and not an approval: it hands the application
						    back to the applicant to add what is missing. The engine
						    returns it to Draft and clears the stage, so review restarts
						    from the beginning when they resubmit — what the earlier
						    stages endorsed is not what they will be resubmitting. */}
						<Button onClick={() => decide("More info requested")} disabled={busy !== null}>
							{busy === "More info requested" ? "Asking…" : "Ask for more"}
						</Button>

						{status.stage?.can_reject && (
							<Button onClick={() => decide("Rejected")} disabled={busy !== null}>
								{busy === "Rejected" ? "Declining…" : "Decline"}
							</Button>
						)}
					</div>

					<p className="mt-3 text-[11.5px] leading-relaxed text-slate-faint">
						Asking for more sends the application back to the applicant with your reason, and
						review starts again when they resubmit. Declining ends it, and needs a reason.
					</p>
				</div>
			) : (
				<p className="mt-5 rounded-card bg-page px-4 py-3 text-[12.5px] text-slate-body">
					You cannot act on this one right now. The engine resolves approvers per document,
					so holding the role is not the same as being this document's approver.
				</p>
			)}
		</Card>
	);
}

function Field({ label, value }: { label: string; value: string }) {
	return (
		<div>
			<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">{label}</dt>
			<dd className="mt-1 text-[13px] text-ink">{value}</dd>
		</div>
	);
}
