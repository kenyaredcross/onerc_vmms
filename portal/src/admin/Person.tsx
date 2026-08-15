import { useContext, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, cardUrl, certificateUrl, errorMessage } from "../lib/api";
import { formatDate, formatHours, formatMoney, geoPath } from "../lib/format";
import {
	Button,
	Card,
	Cell,
	Empty,
	ErrorNote,
	PageHeading,
	Pill,
	Row,
	SectionTitle,
	Spinner,
	StateBadge,
	Table,
	cx,
} from "../ui/primitives";
import type {
	DecisionRow,
	MemberDossier,
	SelectorRow,
	VolunteerDossier,
} from "../portal/types";

/**
 * One person, opened from the registry.
 *
 * **The route names the audience, because a docname cannot.** `VOL-00042` and
 * `MEM-00042` are two different people and nothing about either string says
 * which register it belongs to, so the kind is a path segment rather than
 * something this screen guesses or probes for by calling both endpoints.
 *
 * **One read per person, not seven.** Both dossiers are composed server-side and
 * resolved at a single `as_of`, which is not only about round trips: every block
 * below is derived, and blocks derived at different instants can contradict each
 * other. A certification shown as current beside a deployability indicator
 * computed a second later, after midnight passed, is wrong in the way that is
 * hardest to notice. The endpoints' docstrings argue the same point from the
 * other side.
 *
 * **Nothing here decides what anybody may do.** `can_act` is the server's
 * answer, from the same `write` check the act endpoints enforce, so no role name
 * appears in this file and the buttons cannot offer something the server would
 * refuse. A volunteer following a stale link to their own record reads it
 * through the holder bypass and is offered nothing.
 *
 * **Composed, never merged**, exactly as the DTOs are: a volunteer's current
 * skills and the skills they declared when applying are drawn in two different
 * blocks and never reconciled. One is what is true, the other is what was
 * claimed, and a coordinator comparing them is the point.
 */
export default function Person() {
	const { kind, name } = useParams<{ kind: string; name: string }>();

	if (!name) {
		return <ErrorNote>That link does not name anybody.</ErrorNote>;
	}

	if (kind === "volunteer") {
		return <VolunteerPage name={name} />;
	}

	if (kind === "member") {
		return <MemberPage name={name} />;
	}

	return <ErrorNote>There is no register of that kind.</ErrorNote>;
}

/* ------------------------------------------------------------- the volunteer */

function VolunteerPage({ name }: { name: string }) {
	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: VolunteerDossier }>(
		API.volunteerDossier,
		{ name },
		`admin:volunteer:${name}`,
	);

	const dossier = data?.message;

	if (isLoading) {
		return <Spinner label="Reading this volunteer's record…" page />;
	}

	if (error) {
		return <ErrorNote>{errorMessage(error, "That volunteer could not be read.")}</ErrorNote>;
	}

	if (!dossier) {
		return <Empty title="Nothing to show">That volunteer could not be read.</Empty>;
	}

	const person = dossier.identity;

	return (
		<>
			<PersonHeading
				fullName={person.full_name}
				docname={dossier.volunteer}
				status={person.status}
				asOf={dossier.as_of}
			/>

			{dossier.can_act && (
				<VolunteerActions dossier={dossier} onActed={() => void mutate()} />
			)}

			{/* Drawn only when there is a card to print. `holds_card` is the same
			    predicate `download_card` asserts on, so this link cannot offer
			    something the server would refuse. */}
			{dossier.holds_card && (
				<Card className="mb-5">
					<SectionTitle>Reprint</SectionTitle>
					<a
						href={cardUrl("volunteer", dossier.volunteer)}
						className="inline-flex items-center justify-center rounded-card border border-hairline-strong bg-white px-5 py-2.5 font-display text-[13px] font-bold text-slate-strong transition hover:border-navy hover:text-navy"
					>
						Volunteer card (PDF)
					</a>
				</Card>
			)}

			<Card className="mb-5">
				<SectionTitle>Who they are</SectionTitle>
				<Definitions
					rows={[
						["Email", person.email],
						["Phone", person.phone],
						["Gender", person.gender],
						["Date of birth", formatDate(person.date_of_birth)],
						["Preferred language", person.preferred_language],
						// Two Geo Nodes answering two different questions, under names
						// that differ. Calling either of them simply "branch" is the
						// confusion ACC-02 invites.
						["Serving branch", geoPath(person.geo_path)],
						["Home area", geoPath(person.home_geo_path)],
						["Joined", formatDate(person.joined_on)],
						["Exited", formatDate(person.exited_on)],
					]}
				/>
			</Card>

			<Card className="mb-5">
				<SectionTitle>May they be deployed</SectionTitle>
				<div className="mb-3">
					{dossier.deployability.deployable ? (
						<Pill tone="page">Ready to deploy</Pill>
					) : (
						<Pill tone="page">Blocked</Pill>
					)}
				</div>
				{dossier.deployability.reasons.length === 0 ? (
					<p className="text-[13px] text-slate-body">
						Nothing is standing in the way as at {formatDate(dossier.deployability.as_of)}.
					</p>
				) : (
					<ul className="list-disc space-y-1 pl-5 text-[13px] text-slate-body">
						{dossier.deployability.reasons.map((reason) => (
							<li key={reason}>{reason}</li>
						))}
					</ul>
				)}
			</Card>

			<Card className="mb-5">
				<SectionTitle>What they can do now</SectionTitle>
				<Definitions
					rows={[
						["Skills", labels(dossier.capabilities.skills)],
						["Languages", labels(dossier.capabilities.languages)],
						["Availability", labels(dossier.capabilities.availability)],
					]}
				/>
			</Card>

			<Card className="mb-5">
				<SectionTitle>Certifications held</SectionTitle>
				{dossier.certifications.length === 0 ? (
					<Empty title="No certifications recorded">
						Nothing has been recorded against this volunteer yet.
					</Empty>
				) : (
					<Table head={["Certification", "Completed", "Expires", "Reference", "Standing"]}>
						{dossier.certifications.map((row) => (
							<Row key={row.name}>
								<Cell>
									<span className="font-semibold text-ink">
										{row.certification_type_name}
									</span>
								</Cell>
								<Cell className="text-slate-body">{formatDate(row.completion_date)}</Cell>
								<Cell className="text-slate-body">{formatDate(row.expiry_date)}</Cell>
								<Cell className="text-slate-body">{row.reference_number || "—"}</Cell>
								<Cell>
									{row.lapsed ? (
										<Pill tone="page">
											{row.blocks_deployment ? "Lapsed · blocks deployment" : "Lapsed"}
										</Pill>
									) : (
										<Pill tone="page">Current</Pill>
									)}
								</Cell>
							</Row>
						))}
					</Table>
				)}
			</Card>

			<Card className="mb-5">
				<SectionTitle>Where they have served</SectionTitle>
				{dossier.deployments.length === 0 ? (
					<Empty title="No deployments recorded">
						This volunteer has not been rostered onto anything yet.
					</Empty>
				) : (
					<Table head={["Deployment", "Terms", "From", "To", "Status"]}>
						{dossier.deployments.map((row) => (
							<Row key={`${row.deployment}-${row.joined_on ?? ""}`}>
								<Cell>
									<span className="font-mono text-[12px] text-slate-faint">
										{row.deployment}
									</span>
								</Cell>
								<Cell className="text-slate-body">{row.tor_name || "—"}</Cell>
								{/* The roster row's own dates, so somebody who left early
								    reads as having left rather than as never having been there. */}
								<Cell className="text-slate-body">{formatDate(row.joined_on)}</Cell>
								<Cell className="text-slate-body">{formatDate(row.left_on)}</Cell>
								<Cell>
									<StateBadge state={row.status ?? undefined} />
								</Cell>
							</Row>
						))}
					</Table>
				)}
			</Card>

			<Card className="mb-5">
				<SectionTitle>What they have given</SectionTitle>
				<div className="mb-4 flex flex-wrap gap-2">
					<Pill tone="page">{formatHours(dossier.time.total_hours)} in total</Pill>
					<Pill tone="page">{dossier.time.log_count} logs</Pill>
					{/* Keyed by whatever `log_type` values came back. No kind is named
					    here, the same rule the service itself follows. */}
					{Object.entries(dossier.time.hours_by_type).map(([kind, hours]) => (
						<Pill key={kind} tone="page">
							{kind}: {formatHours(hours)}
						</Pill>
					))}
				</div>
				{dossier.time.recent.length === 0 ? (
					<Empty title="No hours logged">Nothing has been filed against this volunteer.</Empty>
				) : (
					<Table head={["Date", "Category", "Where", "Hours"]}>
						{dossier.time.recent.map((row) => (
							<Row key={row.name}>
								<Cell className="text-slate-body">{formatDate(row.activity_date)}</Cell>
								<Cell className="text-slate-body">{row.category_label || "—"}</Cell>
								<Cell className="text-slate-body">{geoPath(row.geo_path)}</Cell>
								<Cell className="text-slate-body">{formatHours(row.hours)}</Cell>
							</Row>
						))}
					</Table>
				)}
			</Card>

			<Card className="mb-5">
				<SectionTitle>How they were verified</SectionTitle>
				<Verification verification={dossier.application} />
			</Card>

			{dossier.application.declared && (
				<Card>
					<SectionTitle>Declared when they applied</SectionTitle>
					<p className="mb-4 text-[13px] text-slate-body">
						What this person said about themselves on{" "}
						{formatDate(dossier.application.applied_on) || "the day they applied"}. This is not
						what they can currently do, which is above.
					</p>
					<Definitions
						rows={[
							["Skills", labels(dossier.application.declared.skills)],
							["Languages", labels(dossier.application.declared.languages)],
							["Availability", labels(dossier.application.declared.availability)],
							["Motivation", labels(dossier.application.declared.motivation)],
							["Prior experience", dossier.application.declared.prior_experience],
						]}
					/>
				</Card>
			)}
		</>
	);
}

/* ---------------------------------------------------------------- the member */

function MemberPage({ name }: { name: string }) {
	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: MemberDossier }>(
		API.memberDossier,
		{ name },
		`admin:member:${name}`,
	);

	const dossier = data?.message;

	if (isLoading) {
		return <Spinner label="Reading this member's record…" page />;
	}

	if (error) {
		return <ErrorNote>{errorMessage(error, "That member could not be read.")}</ErrorNote>;
	}

	if (!dossier) {
		return <Empty title="Nothing to show">That member could not be read.</Empty>;
	}

	const person = dossier.identity;

	return (
		<>
			<PersonHeading
				fullName={person.full_name}
				docname={dossier.member}
				status={dossier.standing.status}
				asOf={dossier.as_of}
			/>

			<Card className="mb-5">
				<SectionTitle>Who they are</SectionTitle>
				<Definitions
					rows={[
						["Email", person.email],
						["Phone", person.phone],
						["Gender", person.gender],
						["Date of birth", formatDate(person.date_of_birth)],
						["Preferred language", person.preferred_language],
						["Nationality", person.nationality],
						["Citizenship status", person.citizenship_status],
						["Home area", geoPath(person.home_geo_path)],
					]}
				/>
			</Card>

			<Card className="mb-5">
				<SectionTitle>Where they stand</SectionTitle>
				<div className="mb-4 flex flex-wrap gap-2">
					<Pill tone="page">{dossier.standing.current_count} current</Pill>
					<Pill tone="page">{dossier.standing.lapsed_count} lapsed</Pill>
					<Pill tone="page">{dossier.standing.visible_count} visible to you</Pill>
				</div>
				<Definitions
					rows={[
						["Member since", formatDate(dossier.standing.joined_on)],
						[
							"Currently a member at",
							dossier.standing.current_geo_paths.map((path) => geoPath(path)).join(" · "),
						],
					]}
				/>
				{/* Said out loud because a coordinator seeing "Active" above a plainly
				    expired membership should not have to work out which one carries it. */}
				<p className="mt-4 text-[12px] text-slate-faint">
					Standing is over every membership this person holds. The counts are over the ones
					your scope lets you see.
				</p>
			</Card>

			<Card className="mb-5">
				<SectionTitle>Memberships held</SectionTitle>
				{dossier.memberships.length === 0 ? (
					<Empty title="No memberships in your scope">
						Either this person holds none, or they are all at branches your Geo Assignments
						do not cover.
					</Empty>
				) : (
					<div className="space-y-4">
						{dossier.memberships.map((row) => (
							<MembershipCard
								key={row.name}
								row={row}
								canAct={dossier.can_act}
								onActed={() => void mutate()}
							/>
						))}
					</div>
				)}
			</Card>

			<Card>
				<SectionTitle>How they were verified</SectionTitle>
				{dossier.history.length === 0 ? (
					<Empty title="No decisions recorded">
						Nothing in this person's memberships has been through an approval.
					</Empty>
				) : (
					<Table head={["Decided", "Decision", "Stage", "By", "Membership"]}>
						{dossier.history.map((row, index) => (
							<Row key={`${row.membership}-${index}`}>
								<Cell className="text-slate-body">{formatDate(row.decided_on)}</Cell>
								<Cell>
									<StateBadge state={row.decision ?? undefined} />
								</Cell>
								{/* Display only. Nothing here compares a stage label. */}
								<Cell className="text-slate-body">{row.stage_label || "—"}</Cell>
								<Cell className="text-slate-body">{row.approver || "—"}</Cell>
								<Cell className="font-mono text-[11px] text-slate-faint">
									{row.membership}
								</Cell>
							</Row>
						))}
					</Table>
				)}
			</Card>
		</>
	);
}

/* --------------------------------------------------------------- the pieces */

function PersonHeading({
	fullName,
	docname,
	status,
	asOf,
}: {
	fullName: string | null;
	docname: string;
	status?: string | null;
	asOf: string;
}) {
	return (
		<>
			<Link
				to="/admin/registry"
				className="mb-4 inline-block text-[12px] font-semibold text-navy hover:underline"
			>
				← Back to the registry
			</Link>
			<PageHeading
				title={fullName || docname}
				actions={
					<div className="flex flex-wrap items-center gap-2">
						<StateBadge state={status ?? undefined} />
						<Pill tone="page">as at {formatDate(asOf)}</Pill>
					</div>
				}
			/>
			{/* The opaque docname stays visible and copyable: it is what an audit
			    trail, a report and a support conversation refer to. */}
			<p className="-mt-4 mb-6 font-mono text-[12px] text-slate-faint">{docname}</p>
		</>
	);
}

function Verification({
	verification,
}: {
	verification: VolunteerDossier["application"];
}) {
	if (!verification.application) {
		return (
			<Empty title="No application behind this record">
				This volunteer was recorded directly rather than through an application, so there is no
				approval trail to show.
			</Empty>
		);
	}

	return (
		<>
			<Definitions
				rows={[
					["Applied on", formatDate(verification.applied_on)],
					["Outcome", verification.approval_state],
					["Application", verification.application],
					[
						"Applications on file",
						verification.application_count > 1 ? String(verification.application_count) : null,
					],
				]}
			/>
			{verification.decisions.length > 0 && <Decisions rows={verification.decisions} />}
		</>
	);
}

function Decisions({ rows }: { rows: DecisionRow[] }) {
	return (
		<div className="mt-4">
			<Table head={["Decided", "Decision", "Stage", "By", "Reason"]}>
				{rows.map((row, index) => (
					<Row key={index}>
						<Cell className="text-slate-body">{formatDate(row.decided_on)}</Cell>
						<Cell>
							<StateBadge state={row.decision ?? undefined} />
						</Cell>
						{/* Display only, snapshotted by the engine. Never compared. */}
						<Cell className="text-slate-body">{row.stage_label || "—"}</Cell>
						<Cell className="text-slate-body">{row.approver || "—"}</Cell>
						<Cell className="text-slate-body">{row.reason || "—"}</Cell>
					</Row>
				))}
			</Table>
		</div>
	);
}

/** Label/value pairs. A row whose value is empty says so rather than being dropped. */
function Definitions({ rows }: { rows: Array<[string, string | null | undefined]> }) {
	return (
		<dl className="grid gap-4 sm:grid-cols-2">
			{rows.map(([label, value]) => (
				<div key={label}>
					<dt className="text-[11px] font-bold uppercase tracking-wide text-slate-faint">
						{label}
					</dt>
					<dd className={cx("mt-1 text-[14px]", value ? "text-ink" : "text-slate-faint")}>
						{value || "Not recorded"}
					</dd>
				</div>
			))}
		</dl>
	);
}

function labels(rows: SelectorRow[] | undefined): string {
	return (rows || []).map((row) => row.label).join(", ");
}

/* --------------------------------------------------------------- the acts */

/**
 * What may be done to a volunteer's standing, from where it stands now.
 *
 * A table rather than a chain of conditions, the same shape the desk script and
 * the Python dispatch tables use. **Branching on `status` is allowed and
 * branching on a stage label is not**: a stage is a society's word, and this is
 * a closed Select this app owns with four values. A status this file does not
 * know offers nothing, which is the direction a dispatch table should fail in.
 *
 * Drawn only when the server said `can_act`, and every one of these is re-checked
 * server-side when pressed.
 */
const VOLUNTEER_VERBS: Record<string, Array<keyof typeof VOLUNTEER_ACTS>> = {
	Prospective: ["suspend", "exit"],
	Active: ["suspend", "exit"],
	Suspended: ["reinstate", "exit"],
	Exited: ["reinstate"],
};

const VOLUNTEER_ACTS = {
	suspend: {
		label: "Suspend",
		method: API.suspendVolunteer,
		prompt: "Why is this volunteer being suspended?",
	},
	reinstate: {
		label: "Reinstate",
		method: API.reinstateVolunteer,
		prompt: "Why is this volunteer being reinstated?",
		// Said out loud because it surprises people: reinstating hands the
		// question back to the applications rather than setting somebody Active.
		note: "Standing returns to whatever this volunteer's applications support, which may be Prospective rather than Active.",
	},
	exit: {
		label: "Record exit",
		method: API.recordVolunteerExit,
		prompt: "Why are they leaving?",
		dated: true,
	},
} as const;

function VolunteerActions({
	dossier,
	onActed,
}: {
	dossier: VolunteerDossier;
	onActed: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [open, setOpen] = useState<keyof typeof VOLUNTEER_ACTS | null>(null);
	const [reason, setReason] = useState("");
	const [onDate, setOnDate] = useState(() => new Date().toISOString().slice(0, 10));
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const verbs = VOLUNTEER_VERBS[dossier.identity.status] || [];

	if (verbs.length === 0) {
		return null;
	}

	const act = open ? VOLUNTEER_ACTS[open] : null;

	const perform = async () => {
		if (!act || !open) {
			return;
		}

		setBusy(true);
		setFailure(null);

		try {
			await call.post(act.method, {
				name: dossier.volunteer,
				reason,
				...("dated" in act && act.dated ? { on_date: onDate } : {}),
			});
			setOpen(null);
			setReason("");
			onActed();
		} catch (actError) {
			setFailure(errorMessage(actError, "That change was not recorded."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card className="mb-5">
			<SectionTitle>Standing</SectionTitle>

			<div className="flex flex-wrap gap-2">
				{verbs.map((verb) => (
					<Button
						key={verb}
						variant={open === verb ? "navy" : "quiet"}
						onClick={() => {
							setOpen(open === verb ? null : verb);
							setFailure(null);
						}}
					>
						{VOLUNTEER_ACTS[verb].label}
					</Button>
				))}
			</div>

			{act && (
				<div className="mt-5 border-t border-hairline pt-5">
					{"note" in act && act.note && (
						<p className="mb-3 text-[13px] text-slate-body">{act.note}</p>
					)}

					{"dated" in act && act.dated && (
						<label className="mb-3 block">
							<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
								Date they stopped volunteering
							</span>
							<input
								type="date"
								value={onDate}
								onChange={(event) => setOnDate(event.target.value)}
								className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
							/>
						</label>
					)}

					<label className="block">
						<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
							{act.prompt}
						</span>
						<textarea
							value={reason}
							onChange={(event) => setReason(event.target.value)}
							rows={3}
							className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
						/>
					</label>

					{/* Required here rather than only server-side: the service records a
					    comment only when a reason is given, which makes it the entire
					    record of why somebody's standing changed. */}
					<p className="mt-2 text-[12px] text-slate-faint">
						A reason is recorded against the volunteer. Nothing else says why this changed.
					</p>

					{failure && (
						<div className="mt-3">
							<ErrorNote>{failure}</ErrorNote>
						</div>
					)}

					<div className="mt-4 flex gap-2">
						<Button onClick={() => void perform()} disabled={busy || !reason.trim()}>
							{busy ? "Recording…" : act.label}
						</Button>
						<Button variant="ghost" onClick={() => setOpen(null)} disabled={busy}>
							Cancel
						</Button>
					</div>
				</div>
			)}
		</Card>
	);
}

/**
 * One membership, with the two acts that apply to it.
 *
 * **Cancel and expire are not two spellings of the same thing.** Cancel ends a
 * membership early and records why; expire closes one whose validity has already
 * run out and carries no reason, because the date is the reason. So expire is
 * offered only when `lapsed` says the window has actually closed — the same
 * predicate the endpoint checks before it will act, derived once server-side so
 * the button and the endpoint cannot disagree.
 *
 * There is no activate button, and the endpoint's docstring says why: activation
 * is a predicate re-evaluated from `on_update`, not a verb somebody performs. A
 * button forcing it would be a way around approval and payment both.
 */
function MembershipCard({
	row,
	canAct,
	onActed,
}: {
	row: MemberDossier["memberships"][number];
	canAct: boolean;
	onActed: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [cancelling, setCancelling] = useState(false);
	const [reason, setReason] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const perform = async (method: string, values: Record<string, unknown>) => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(method, { name: row.name, ...values });
			setCancelling(false);
			setReason("");
			onActed();
		} catch (actError) {
			setFailure(errorMessage(actError, "That change was not recorded."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div className="rounded-card border border-hairline p-4">
			<div className="mb-3 flex flex-wrap items-start justify-between gap-3">
				<div>
					<p className="font-display text-[15px] font-bold text-ink">
						{row.membership_type_name}
					</p>
					<p className="mt-0.5 font-mono text-[11px] text-slate-faint">{row.name}</p>
				</div>
				<StateBadge state={row.effective_status} />
			</div>

			<Definitions
				rows={[
					["Branch", geoPath(row.membership_geo_path)],
					["Valid from", formatDate(row.valid_from)],
					// A lifetime membership has no end date, and the DTO says so rather
					// than leaving a screen to infer it from a missing value.
					["Valid to", row.is_lifetime ? "Lifetime" : formatDate(row.valid_to)],
					["Fee", row.fee ? formatMoney(row.fee.amount, row.fee.currency) : null],
					["Paid on", formatDate(row.paid_on)],
					["Source", row.membership_source],
				]}
			/>

			{/* All three have to be true, and the DTO reports them separately for
			    exactly this reason: there is a certificate, this caller may have
			    it, and the type has a template to render it from. */}
			{row.certificate.available && row.certificate.may_print && row.certificate.configured && (
				<div className="mt-4 border-t border-hairline pt-4">
					<a
						href={certificateUrl(row.name)}
						className="inline-flex items-center justify-center rounded-card border border-hairline-strong bg-white px-5 py-2.5 font-display text-[13px] font-bold text-slate-strong transition hover:border-navy hover:text-navy"
					>
						Certificate (PDF)
					</a>
				</div>
			)}

			{canAct && (
				<div className="mt-4 flex flex-wrap gap-2 border-t border-hairline pt-4">
					{row.membership_status !== "Cancelled" && (
						<Button
							variant="quiet"
							onClick={() => {
								setCancelling(!cancelling);
								setFailure(null);
							}}
						>
							Cancel membership
						</Button>
					)}
					{row.membership_status === "Active" && row.lapsed && (
						<Button
							variant="quiet"
							disabled={busy}
							onClick={() => void perform(API.expireMembership, {})}
						>
							Expire
						</Button>
					)}
				</div>
			)}

			{cancelling && (
				<div className="mt-4">
					<label className="block">
						<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
							Why is this membership being cancelled?
						</span>
						<textarea
							value={reason}
							onChange={(event) => setReason(event.target.value)}
							rows={3}
							className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
						/>
					</label>
					<div className="mt-3 flex gap-2">
						<Button
							onClick={() => void perform(API.cancelMembership, { reason })}
							disabled={busy || !reason.trim()}
						>
							{busy ? "Recording…" : "Cancel membership"}
						</Button>
						<Button variant="ghost" onClick={() => setCancelling(false)} disabled={busy}>
							Keep it
						</Button>
					</div>
				</div>
			)}

			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}
		</div>
	);
}
