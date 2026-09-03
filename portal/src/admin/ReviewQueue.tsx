import { useContext, useMemo, useState } from "react";
import { Link, NavLink, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { branchPath, formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import { PersonHero, RegisterLinks } from "../ui/PersonHero";
import { RecordPayment, owesAFee } from "./RecordPayment";
import {
	ActionMenu,
	Avatar,
	Button,
	Card,
	Cell,
	ConfirmDialog,
	Empty,
	ErrorNote,
	PageHeading,
	Pill,
	Row,
	SectionTitle,
	Spinner,
	StateBadge,
	Table,
	Tabs,
	cx,
	type TabDef,
} from "../ui/primitives";
import {
	QUEUES,
	QUEUE_BANDS,
	bandRoute,
	type QueueBand,
	type QueueKind,
	type QueueSpec,
} from "./queues";
import type {
	ApplicationDecision,
	ApprovalCases,
	ApprovalStatus,
	MembershipReview,
	Registers,
	SocietyAnswer,
} from "../portal/types";

/**
 * Deciding on what has been routed to you.
 *
 * **Two queues, not one with a mixed list in it.** This screen used to be a
 * single console over `my_queue` with every governed doctype in the same
 * column, and the reason to split it is not tidiness: approving volunteers and
 * approving memberships are two different jobs, often done by two different
 * people, and reliably done in batches — somebody sits down to clear the
 * membership backlog, not to clear whatever happens to be at the top. One list
 * per registration means each is a page you can link, bookmark and finish.
 *
 * `my_queue` already took a `doctype`, so the split is two calls rather than
 * one call and a filter drawn on top of it: a coordinator with four hundred
 * volunteer applications does not download them to look at eleven memberships.
 *
 * **The list stays what it always was: what is routed to *you*.** Not every
 * application in your branch — `my_queue` returns documents whose routing
 * resolves to this user right now, re-checked per row rather than trusted from
 * a ToDo. What changed is where a row goes when you click it.
 *
 * **A row opens a page, not a panel.** The two-pane console put the whole
 * record in a scrolling column beside the list, which worked while the record
 * was six fields and stopped working once it carried a questionnaire. A routed
 * page gives every application a URL — the thing an approver actually needs
 * when they want a second opinion from a colleague — and lets the record be
 * tabbed rather than stacked. Getting back is a link, and it says which list it
 * goes back to.
 *
 * **Three rules from the approval engine are visible in this file and none of
 * them is re-implemented here.**
 *
 * 1. *The queue is already the answer.* So these screens filter nothing.
 * 2. *`can_act` decides whether the buttons exist.* Not the state, not the
 *    stage, not whether the user holds a role. Being *a* coordinator does not
 *    make somebody *this* document's coordinator, which is the whole reason
 *    this app does not use Frappe's native Workflow.
 * 3. *`stage.label` is displayed and never compared.* Stages are society
 *    configuration; the Python side has an AST test that fails the build if a
 *    stage label reaches a comparison, and the same discipline applies here.
 */

/** Stable empty answers, so a memo over them does not rebuild on every render. */
const NO_ANSWERS: SocietyAnswer[] = [];

/* ------------------------------------------------------------------- lists */

export function VolunteerQueue({ band }: { band?: string } = {}) {
	return <Queue kind="volunteers" band={band} />;
}

export function MembershipQueue({ band }: { band?: string } = {}) {
	return <Queue kind="members" band={band} />;
}

/**
 * One registration's applications, in one of three routed bands.
 *
 * **The two queues never touch each other's endpoints.** `my_queue` and
 * `my_cases` both take the doctype off this queue's own spec, so a coordinator
 * on the membership page never asks for volunteer applications and the other way
 * round. That is not a filter drawn over a mixed read — it is two calls with two
 * arguments, which is why a branch with four hundred volunteer applications
 * costs nothing to somebody clearing eleven memberships.
 *
 * **The bands come from the server and none of them is derived here.**
 * `actionable` is what the engine routes to this user right now; `changes` is a
 * Draft with a recorded "More info requested" decision behind it; `closed` is
 * one of the four terminal states. Filtering an array in the browser could not
 * answer any of the last two, because neither is in this user's queue at all.
 */
function Queue({ kind, band: segment }: { kind: QueueKind; band?: string }) {
	const spec = QUEUES[kind];
	const band = QUEUE_BANDS.find((row) => row.segment === (segment ?? "")) ?? QUEUE_BANDS[0];
	const isActionable = band.key === "actionable";

	// Two reads, and exactly one of them ever runs: `swrKey === null` is how
	// this codebase says "do not ask". The open band is `my_queue`, which
	// re-checks routing per row; the other two are `my_cases`, which reads the
	// governed doctype through a scoped listing because neither band is an
	// assignment anybody holds.
	const open = useFrappeGetCall<{ message: ApprovalStatus[] }>(
		API.myQueue,
		{ doctype: spec.doctype },
		isActionable ? `admin:my_queue:${kind}` : null,
	);
	const history = useFrappeGetCall<{ message: ApprovalCases }>(
		API.myCases,
		{ doctype: spec.doctype, group: band.key },
		isActionable ? null : `admin:my_cases:${kind}:${band.key}`,
	);

	const rows = isActionable ? (open.data?.message ?? []) : (history.data?.message?.cases ?? []);
	const isLoading = isActionable ? open.isLoading : history.isLoading;
	const error = isActionable ? open.error : history.error;
	const overdue = rows.filter((row) => row.stage?.is_breached).length;

	return (
		<>
			<PageHeading
				title={<EditableText k={spec.headingKey} fallback={spec.heading} />}
				lead={band.lead}
				trail={[{ label: "People", to: "/admin/people" }, { label: spec.heading }]}
				actions={
					<div className="flex flex-wrap items-center gap-2">
						<Pill tone="navy">
							{rows.length} {isActionable ? "waiting" : "shown"}
						</Pill>
						{/* Only when there are any. A permanent "0 overdue" is a
						    reassurance nobody reads, and it takes the place of the
						    one that matters. */}
						{overdue > 0 && <Pill tone="signal">{overdue} overdue</Pill>}
					</div>
				}
			/>

			<QueueBands spec={spec} current={band} />

			{isLoading && <Spinner label="Loading the queue…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && rows.length === 0 && (
				<Empty title={isActionable ? spec.empty : band.empty}>{band.lead}</Empty>
			)}

			{rows.length > 0 && (
				<Table
					head={
						isActionable
							? ["Applicant", "Branch", "Stage", "Waiting since", "Due", ""]
							: ["Applicant", "Branch", "State", "Last moved", "Last decision", ""]
					}
				>
					{rows.map((row) => (
						<QueueRow key={row.name} row={row} spec={spec} actionable={isActionable} />
					))}
				</Table>
			)}
		</>
	);
}

/**
 * The band navigation, as three routed links.
 *
 * `NavLink` rather than buttons, so each band is a real address with
 * `aria-current` on the one you are standing in — which is what a screen reader
 * announces, and what colour alone would say nothing about.
 */
function QueueBands({ spec, current }: { spec: QueueSpec; current: QueueBand }) {
	return (
		<nav aria-label={`${spec.heading} states`} className="mb-5 flex flex-wrap gap-1.5">
			{QUEUE_BANDS.map((band) => (
				<NavLink
					key={band.key}
					to={bandRoute(spec, band)}
					end
					className={cx(
						"rounded-full border px-3.5 py-2 text-[12.5px] font-semibold transition",
						band.key === current.key
							? "border-blue bg-blue-soft text-blue-press"
							: "border-card-line bg-white text-slate-strong hover:border-blue hover:text-ink",
					)}
				>
					{band.label}
				</NavLink>
			))}
		</nav>
	);
}

/**
 * One application in a queue.
 *
 * The three right-hand columns differ by band because the questions do: an open
 * application is read for what stage it is at and how late it is, and a closed
 * one for what was decided and when. The applicant, the branch and the way in
 * are the same in both.
 */
function QueueRow({
	row,
	spec,
	actionable,
}: {
	row: ApprovalStatus;
	spec: QueueSpec;
	actionable: boolean;
}) {
	const to = `${spec.list}/${encodeURIComponent(row.name)}`;
	const last = row.decisions.at(-1);

	return (
		<Row>
			<Cell>
				<Link to={to} className="flex items-center gap-3 group">
					<Avatar name={row.applicant?.full_name} photo={row.applicant?.photo} size={34} />
					<span className="min-w-0">
						{/* The whole reason `applicant` was added to the engine's
						    status DTO. A membership used to arrive here as
						    `MSHIP-00042` and a stage label, which is not something
						    anybody can approve. */}
						<span className="block truncate font-semibold text-ink group-hover:text-ink group-hover:underline">
							{row.applicant?.full_name ?? row.name}
						</span>
						<span className="tabular mt-0.5 block font-mono text-[11px] text-slate-faint">
							{row.name}
						</span>
					</span>
				</Link>
			</Cell>

			<Cell className="text-muted">{branchPath(row.geo_path)}</Cell>

			{actionable ? (
				<>
					<Cell>
						{row.stage && (
							<>
								<span className="block text-[12.5px] font-semibold text-ink">
									{row.stage.label}
								</span>
								{/* The stage resolved nobody at its own level, so the
								    engine entered it blocked and escalated upward —
								    which is the only reason this row is in *this*
								    person's queue rather than the branch's. Without
								    the line it reads as an ordinary assignment and
								    the unstaffed branch behind it stays invisible. */}
								{row.stage.is_blocked && (
									<span className="mt-0.5 block text-[11px] text-slate-faint">
										Nobody at this level — escalated to you
									</span>
								)}
							</>
						)}
					</Cell>
					<Cell className="text-muted">{formatDate(row.stage?.entered_on ?? null)}</Cell>
					<Cell>
						{row.stage?.is_breached ? (
							<Pill tone="signal">{row.stage.days_overdue} days over</Pill>
						) : (
							<span className="text-muted">{formatDate(row.stage?.due_on ?? null)}</span>
						)}
					</Cell>
				</>
			) : (
				<>
					<Cell>
						{/* One of the seven in `states.py`. Shown, never compared:
						    the server put this row in this band. */}
						<StateBadge state={row.state} />
					</Cell>
					<Cell className="text-muted">{formatDate(last?.decided_on ?? null)}</Cell>
					<Cell>
						{last ? (
							<>
								<span className="block text-[12.5px] font-semibold text-ink">
									{last.decision}
								</span>
								<span className="mt-0.5 block truncate text-[11px] text-slate-faint">
									{last.stage_label}
								</span>
							</>
						) : (
							<span className="text-muted">No decision recorded</span>
						)}
					</Cell>
				</>
			)}

			<Cell className="text-right">
				<Link to={to} className="text-[12.5px] font-bold text-ink hover:underline">
					Open
				</Link>
			</Cell>
		</Row>
	);
}

/* ------------------------------------------------------------------ review */

/**
 * One application, in full, with the decision on it.
 *
 * Two reads, deliberately not merged into one endpoint: the engine decides how
 * much of the approver chain this caller may see, and the record's own read
 * check decides whether they may see the record. They are two different
 * permission questions about two different documents, and a governed doctype
 * with no decision view simply does not get the tabs — `NotBuilt` applied to
 * half a screen.
 */
export default function ApplicationReview() {
	const { kind, name } = useParams<{ kind: string; name: string }>();
	const [params, setParams] = useSearchParams();
	const navigate = useNavigate();

	const spec = kind && kind in QUEUES ? QUEUES[kind as QueueKind] : null;

	if (!spec || !name) {
		return <ErrorNote>That link does not name an application.</ErrorNote>;
	}

	return (
		<Review
			key={`${kind}:${name}`}
			spec={spec}
			name={name}
			tab={params.get("tab") ?? ""}
			// `replace`, so paging through four tabs does not put four entries in
			// the history and make the back button a tab-rewinder. Built from the
			// existing params rather than from a fresh object, because assigning
			// `{tab}` wholesale would drop every other search param the address
			// happens to carry.
			onTab={(next) => {
				const updated = new URLSearchParams(params);
				updated.set("tab", next);
				setParams(updated, { replace: true });
			}}
			onDecided={() => navigate(spec.list)}
		/>
	);
}

function Review({
	spec,
	name,
	tab,
	onTab,
	onDecided,
}: {
	spec: QueueSpec;
	name: string;
	tab: string;
	onTab: (key: string) => void;
	onDecided: () => void;
}) {
	const approval = useFrappeGetCall<{ message: ApprovalStatus }>(
		API.approvalStatus,
		{ doctype: spec.doctype, name },
		`review:status:${name}`,
	);

	const isVolunteer = spec.doctype === QUEUES.volunteers.doctype;

	// One of the two record endpoints, chosen by which queue this is. The key is
	// `null` for the other one, which is how `useFrappeGetCall` is told not to
	// ask — so opening a membership never calls the volunteer endpoint.
	const application = useFrappeGetCall<{ message: ApplicationDecision }>(
		API.applicationDecision,
		{ name },
		isVolunteer ? `review:decision:${name}` : null,
	);
	const membership = useFrappeGetCall<{ message: MembershipReview }>(
		API.membershipReview,
		{ name },
		isVolunteer ? null : `review:membership:${name}`,
	);

	const status = approval.data?.message;
	const record = application.data?.message;
	const review = membership.data?.message;

	// Whether this applicant is already in either of the society's registers.
	// **This is decision-relevant, which is why it is worth a second read.** An
	// approver deciding a volunteer application is often looking at somebody
	// who has been a member of the branch for fifteen years, and nothing on
	// this screen used to say so. Asked only once the applicant's Red Profile
	// is known — the key is `null` until then, which is how `useFrappeGetCall`
	// is told not to ask.
	const registers = useFrappeGetCall<{ message: Registers }>(
		API.personRegisters,
		{ red_profile: status?.applicant?.red_profile },
		status?.applicant?.red_profile ? `review:registers:${status.applicant.red_profile}` : null,
	);

	// `NO_ANSWERS` rather than a fresh `[]`, so the memo below has a stable
	// dependency while either read is still in flight.
	const answers = record?.answers ?? review?.answers ?? NO_ANSWERS;
	const person = status?.applicant;

	// The society's own questions, grouped by the heading they were asked under.
	// Built from the answers' own snapshots, so an application decided before a
	// society introduced grouping still reads as it was asked.
	const grouped = useMemo(() => groupAnswers(answers), [answers]);

	const tabs: TabDef[] = [
		{ key: "applicant", label: "Applicant" },
		isVolunteer
			? { key: "declaration", label: "What they declared" }
			: { key: "membership", label: "Membership" },
		// The tab that carries the two things this decision can be refused over.
		// Volunteer-only, and only once the record has loaded: an approver who
		// cannot see the emergency contact would press Approve, be told no, and
		// have nowhere to look.
		...(isVolunteer && record ? [{ key: "safeguarding", label: "Contacts and consent" }] : []),
		...grouped.map((group) => ({
			key: `q:${group.name}`,
			label: group.name,
			count: group.answers.length,
		})),
		{ key: "decision", label: "Decision", count: status?.decisions.length || undefined },
	];

	const active = tabs.some((entry) => entry.key === tab) ? tab : tabs[0].key;

	if (approval.isLoading) {
		return <Spinner page label="Opening this application…" />;
	}

	if (approval.error || !status) {
		return <ErrorNote>{errorMessage(approval.error, "That application could not be read.")}</ErrorNote>;
	}

	return (
		<>
			{/* The way back, above the title and in words rather than left to the
			    browser's own button — an approver who arrived here from a
			    colleague's link has no back button that goes anywhere useful, and
			    a page that can only be left by retyping a URL is a dead end. */}
			<Link
				to={spec.list}
				className="mb-3 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-ink hover:underline"
			>
				<Icon.back size={14} />
				All {spec.heading.toLowerCase()}
			</Link>

			{/* The same header the volunteer and member records open with, so an
			    approver who follows the link from here to somebody's full record
			    does not have to re-find the name and the face on arrival. There is
			    no `PageHeading` above it: this block *is* the heading, and a title
			    bar repeating the name over a block that opens with the name reads
			    as a template with a hole in it. */}
			<PersonHero
				name={person?.full_name}
				photo={person?.photo}
				docname={status.name}
				subtitle={branchPath(status.geo_path) || undefined}
				status={status.state}
				badges={
					<RegisterLinks registers={registers.data?.message} />
				}
				facts={[
					{ label: "Email", value: person?.email },
					{ label: "Phone", value: person?.phone },
					...(status.stage
						? [
								{ label: "At stage", value: status.stage.label },
								{
									label: "Due",
									value: status.stage.is_breached
										? `${status.stage.days_overdue} days over`
										: formatDate(status.stage.due_on),
								},
							]
						: []),
				]}
			/>

			<Tabs tabs={tabs} active={active} onSelect={onTab} className="mb-5" />

			{(application.isLoading || membership.isLoading) && (
				<Spinner label="Reading the application…" />
			)}

			{active === "applicant" && (
				<Card>
					{record && <VolunteerApplicant record={record} />}
					{review && <MembershipApplicant review={review} />}
					{!record && !review && !application.isLoading && !membership.isLoading && (
						<Empty title="No decision view for this record">
							This kind of application has no structured view yet, so there is nothing
							here to read beyond the approval trail.
						</Empty>
					)}
				</Card>
			)}

			{active === "declaration" && record && (
				<Card>
					<Declared label="Skills" rows={record.skills} />
					<Declared label="Languages" rows={record.languages} />
					<Declared label="Availability" rows={record.availability} />
					<Declared label="Motivation" rows={record.motivation} />

					{record.prior_experience && (
						<div className="mt-5 border-t border-card-line pt-5">
							<SectionTitle>In their own words</SectionTitle>
							<p className="whitespace-pre-line text-[13px] leading-relaxed text-ink">
								{record.prior_experience}
							</p>
						</div>
					)}
				</Card>
			)}

			{active === "safeguarding" && record && <Safeguarding record={record} />}

			{active === "membership" && review && (
				<MembershipFacts
					review={review}
					onRecorded={() => {
						// Both, and neither is optional: the fee lands on the
						// membership and the approval state moves with it, so a
						// screen refetching one would show the other stale.
						void membership.mutate();
						void approval.mutate();
					}}
				/>
			)}

			{grouped.map(
				(group) =>
					active === `q:${group.name}` && (
						<Card key={group.name}>
							<Answers rows={group.answers} />
						</Card>
					),
			)}

			{active === "decision" && (
				<Decision status={status} noun={spec.noun} person={person?.full_name ?? status.name} onDecided={onDecided} />
			)}
		</>
	);
}

/* ------------------------------------------------------------------ blocks */

function VolunteerApplicant({ record }: { record: ApplicationDecision }) {
	return (
		<dl className="grid gap-4 sm:grid-cols-2">
			<Field label="Full name" value={record.full_name} />
			<Field label="Applied on" value={formatDate(record.applied_on)} />
			<Field label="Email" value={record.email} />
			<Field label="Phone" value={record.phone} />
			<Field label="Gender" value={record.gender} />
			<Field label="Date of birth" value={formatDate(record.date_of_birth)} />
			<Field label="Preferred language" value={record.preferred_language} />
			<Field
				label="Identifications"
				value={
					record.identifications
						.map((row) => `${row.id_type_name ?? row.id_type} ${row.id_number}`.trim())
						.join(" · ") || null
				}
			/>
			<Field label="Citizenship" value={record.country_of_citizenship} />
			<Field
				label="Lives"
				value={
					record.residency_type === "Abroad"
						? [record.country_of_residence, record.residence_address]
								.filter(Boolean)
								.join(" · ") || "Abroad"
						: branchPath(record.home_geo_path)
				}
			/>
			<Field label="Would serve at" value={branchPath(record.geo_path)} />
		</dl>
	);
}

/**
 * The membership applicant — one answer, from core's Red Profile.
 *
 * **There is no "as written on the form" column, and its absence is a
 * decision.** `VMMS Membership` carries `applicant_first_name` and its
 * neighbours, and showing them beside this block would look like the comparison
 * an approver wants — what the clerk typed against what the society holds. Those
 * fields are blanked on every save by `intake.clear_intake`, having first been
 * absorbed into the Red Profile: they are a transport into identity, not a
 * record. Drawing them would be five permanently empty fields implying the
 * society recorded nothing. See `member/services/review.py`.
 */
function MembershipApplicant({ review }: { review: MembershipReview }) {
	const person = review.applicant;

	return (
		<dl className="grid gap-4 sm:grid-cols-2">
			<Field label="Full name" value={person?.full_name} />
			<Field label="Email" value={person?.email} />
			<Field label="Phone" value={person?.phone} />
			<Field label="Gender" value={person?.gender} />
			<Field label="Date of birth" value={formatDate(person?.date_of_birth)} />
			<Field label="Country of citizenship" value={person?.country_of_citizenship} />
			<Field label="Citizenship status" value={person?.citizenship_status} />
			<Field
				label="Residence"
				value={
					person?.residency_type === "Abroad"
						? [person.country_of_residence, person.residence_address].filter(Boolean).join(" · ")
						: branchPath(person?.home_geo_path)
				}
			/>
		</dl>
	);
}

/** The membership itself: what was applied for, and how it was paid for. */
function MembershipFacts({
	review,
	onRecorded,
}: {
	review: MembershipReview;
	/** Refetch: recording a fee moves the membership and the approval both. */
	onRecorded: () => void;
}) {
	const row = review.membership;
	const fee = row.fee;

	return (
		<>
			<Card className="mb-5">
				<SectionTitle>What was applied for</SectionTitle>
				<dl className="grid gap-4 sm:grid-cols-2">
					<Field label="Type" value={row.membership_type_name ?? row.membership_type} />
					<Field label="Branch" value={branchPath(row.membership_geo_path)} />
					<Field label="Recorded status" value={row.membership_status} />
					<Field label="Standing today" value={row.effective_status} />
					<Field label="Valid from" value={formatDate(row.valid_from)} />
					<Field
						label="Valid to"
						value={row.is_lifetime ? "Lifetime" : formatDate(row.valid_to)}
					/>
				</dl>
			</Card>

			<Card>
				<SectionTitle>How it was paid for</SectionTitle>
				<dl className="grid gap-4 sm:grid-cols-2">
					<Field
						label="Fee"
						value={fee ? `${fee.currency ?? ""} ${fee.amount}`.trim() : null}
					/>
					<Field label="Settled" value={row.payment_settled ? "Yes" : "Not yet"} />
					<Field label="Source" value={review.membership_source} />
					<Field label="Paid on" value={formatDate(row.paid_on)} />
					<Field label="Transaction" value={row.payment_transaction} />
					<Field label="Receipt" value={row.payment_receipt} />
				</dl>

				{/* The act that answers the "Not yet" directly above it. This is
				    where a coordinator lands from the members queue, so a fee taken
				    at the counter is recorded on the screen that reports it missing
				    rather than on another one they would have to know about. */}
				{owesAFee(row, review.can_act) && (
					<div className="mt-5 border-t border-card-line pt-5">
						<RecordPayment row={row} canAct={review.can_act} onRecorded={onRecorded} />
					</div>
				)}

				{/* The single thing an approver of a proof-of-payment membership is
				    actually here to look at, so it is a button rather than a field. */}
				{review.proof_attachment && (
					<div className="mt-5 border-t border-card-line pt-5">
						<a
							href={review.proof_attachment}
							target="_blank"
							rel="noreferrer"
							className="inline-flex items-center gap-2 text-[13px] font-bold text-ink hover:underline"
						>
							<Icon.external size={15} />
							Open the proof of payment
						</a>
					</div>
				)}
			</Card>
		</>
	);
}

/**
 * The two things this decision can be refused over, and what was agreed to.
 *
 * **Written to be read before pressing Approve.** `application.assert_approvable`
 * refuses the save that carries an approval when there is no emergency contact
 * the applicant permitted us to call, or when a minor's guardian consent has not
 * been verified — so both are stated here in the terms the refusal will use,
 * with the missing case called out rather than left as an empty field somebody
 * has to notice.
 *
 * The verification itself is not done here: it is a tick on the application in
 * the desk, by whoever actually checked. This screen reports whether it has
 * happened, because that is what the approver needs to know and it is not their
 * job to vouch for it from a queue.
 */
function Safeguarding({ record }: { record: ApplicationDecision }) {
	const callable = record.emergency_contacts.filter((row) => row.may_contact_in_emergency);
	const verified = record.guardian_consents.filter((row) => row.consent_given && row.is_verified);

	return (
		<>
			<Card>
				<SectionTitle>If something happens</SectionTitle>

				{callable.length === 0 && (
					<p className="mb-4 rounded-xl border border-blue/30 bg-blue/[0.06] px-3.5 py-2.5 text-[12.5px] leading-relaxed text-ink">
						{record.emergency_contacts.length === 0
							? "No emergency contact. This application cannot be approved until one is added."
							: "A contact is on file, but the applicant has not agreed to us calling them. This application cannot be approved until one we may contact is added."}
					</p>
				)}

				{record.emergency_contacts.length === 0 ? (
					<Empty title="Nobody has been named yet." />
				) : (
					record.emergency_contacts.map((row, index) => (
						<dl
							key={`${row.contact_name}-${index}`}
							className="mb-5 grid gap-4 border-b border-card-line pb-5 last:mb-0 last:border-0 last:pb-0 sm:grid-cols-2"
						>
							<Field label="Name" value={row.contact_name} />
							<Field label="Relationship" value={row.relationship} />
							<Field label="Phone" value={row.primary_phone} />
							<Field label="Alternative" value={row.alternative_phone} />
							<Field
								label="May we call them"
								value={row.may_contact_in_emergency ? "Yes" : "No — permission withheld"}
							/>
						</dl>
					))
				)}
			</Card>

			{record.is_minor && (
				<Card>
					<SectionTitle>Guardian consent</SectionTitle>

					{verified.length === 0 && (
						<p className="mb-4 rounded-xl border border-blue/30 bg-blue/[0.06] px-3.5 py-2.5 text-[12.5px] leading-relaxed text-ink">
							This applicant is a minor. Their application cannot be approved until a
							guardian's consent has been recorded and somebody has marked it verified on
							the application itself.
						</p>
					)}

					{record.guardian_consents.length === 0 ? (
						<Empty title="No guardian has been recorded." />
					) : (
						record.guardian_consents.map((row, index) => (
							<dl
								key={`${row.guardian_name}-${index}`}
								className="mb-5 grid gap-4 border-b border-card-line pb-5 last:mb-0 last:border-0 last:pb-0 sm:grid-cols-2"
							>
								<Field label="Guardian" value={row.guardian_name} />
								<Field label="Relationship" value={row.relationship} />
								<Field label="Phone" value={row.phone} />
								<Field label="Email" value={row.email} />
								<Field
									label="Consent given"
									value={
										row.consent_given
											? `Yes${row.consent_date ? ` · ${formatDate(row.consent_date)}` : ""}`
											: "Not recorded"
									}
								/>
								<Field
									label="Verified"
									value={
										row.is_verified
											? `Yes · ${row.verified_by ?? "unknown"}${row.verified_on ? ` · ${formatDate(row.verified_on)}` : ""}`
											: "Not yet"
									}
								/>
								{row.consent_evidence && (
									<div className="sm:col-span-2">
										<span className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
											Evidence
										</span>
										<div className="mt-1">
											<a
												href={row.consent_evidence}
												target="_blank"
												rel="noreferrer"
												className="text-[13px] font-semibold text-ink underline"
											>
												Open the uploaded consent
											</a>
										</div>
									</div>
								)}
							</dl>
						))
					)}
				</Card>
			)}

			<Card>
				<SectionTitle>What they agreed to</SectionTitle>

				{record.declarations.length === 0 ? (
					<Empty title="This society asked them to agree to nothing." />
				) : (
					<dl className="grid gap-4 sm:grid-cols-2">
						{record.declarations.map((row) => (
							<div key={row.declaration}>
								<Field
									label={row.title}
									// The version, because that is what identifies the wording
									// stored against this acceptance. The text itself is on the
									// application; reprinting four declarations here would bury
									// the two things above that actually gate the decision.
									value={
										row.accepted
											? `Agreed · version ${row.version}${row.accepted_on ? ` · ${formatDate(row.accepted_on)}` : ""}`
											: "Not agreed"
									}
								/>

								{/* Where the society published the policy on its own site
								    rather than here, the address is the whole of what the
								    register holds — there are no words to fall back on. So
								    it is shown, and shown as what it is: the page as it was
								    addressed on the day, not a promise about what it says
								    now. */}
								{row.source === "Link" && row.external_url && (
									<a
										href={row.external_url}
										target="_blank"
										rel="noreferrer noopener"
										className="mt-1 inline-flex items-center gap-1.5 text-[11.5px] font-semibold text-ink hover:underline"
									>
										<Icon.external size={12} />
										The page they were shown
									</a>
								)}
							</div>
						))}
					</dl>
				)}
			</Card>
		</>
	);
}

/** One declared vocabulary, drawn only when the applicant declared anything. */
function Declared({ label, rows }: { label: string; rows: Array<{ key: string; label: string }> }) {
	if (!rows.length) return null;

	return (
		<div className="mb-4 flex flex-wrap items-baseline gap-x-2 gap-y-1.5 last:mb-0">
			<span className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
				{label}
			</span>
			{rows.map((row) => (
				<span
					key={row.key}
					className="rounded-full bg-surface px-2.5 py-1 text-[11.5px] font-medium text-muted"
				>
					{row.label}
				</span>
			))}
		</div>
	);
}

/**
 * The society's own questions and what this applicant answered.
 *
 * The wording is the snapshot taken when they answered, so a question reworded
 * since still reads as it was asked.
 */
function Answers({ rows }: { rows: SocietyAnswer[] }) {
	return (
		<dl className="grid gap-5 sm:grid-cols-2">
			{rows.map((answer) => (
				<div key={answer.question}>
					<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
						{answer.label}
					</dt>
					<dd className="mt-1 text-[13px] text-ink">
						{answer.is_file ? (
							answer.file_url ? (
								<a
									className="inline-flex items-center gap-1.5 font-semibold text-ink underline underline-offset-2"
									href={answer.file_url}
									target="_blank"
									rel="noreferrer"
								>
									<Icon.external size={13} />
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
	);
}

/**
 * The answers, in the groups a society put them in.
 *
 * **Order comes from the answers, not from an alphabet.** They arrive in the
 * order the form asked them, so the groups come out in the order they were
 * first met — which is the order somebody filled the form in, and therefore the
 * order the approver expects to read them.
 *
 * Anything ungrouped falls under one heading of this screen's choosing. Naming
 * it here rather than inventing a group on the server is the same rule
 * `questions.groups()` follows: an empty group is not a group.
 */
const UNGROUPED = "Questionnaire";

function groupAnswers(answers: SocietyAnswer[]): Array<{ name: string; answers: SocietyAnswer[] }> {
	const groups: Array<{ name: string; answers: SocietyAnswer[] }> = [];

	for (const answer of answers) {
		const name = answer.group?.trim() || UNGROUPED;
		const existing = groups.find((group) => group.name === name);

		if (existing) existing.answers.push(answer);
		else groups.push({ name, answers: [answer] });
	}

	return groups;
}

/* ---------------------------------------------------------------- deciding */

/**
 * The three answers to one question, and the second press that commits one.
 *
 * **A menu, not a row of buttons.** Approve, decline and ask-for-more are not
 * three things an approver might do — they are three answers to one question,
 * exactly one of which will ever be pressed. A row of three equally weighted
 * buttons puts Decline the same distance from a stray click as Approve, and
 * reads as a toolbar rather than as a decision.
 *
 * **Choosing is not deciding.** Picking from the menu sets the intent, shows it
 * as a pill, and opens the reason box; nothing has been sent. The confirm
 * dialog names the person and the act — "Approve Grace Mushi as a volunteer
 * applicant" — because a dialog that asks whether you are sure is dismissed
 * without being read, and one that contains a name is checked.
 *
 * **`can_act` is the server's answer and this file does not second-guess it.**
 * A person holding the role but not routed to this document gets the sentence
 * rather than the menu, and the endpoint would refuse them anyway.
 */
const DECISIONS = {
	Approved: {
		verb: "Approve",
		// The button says the whole sentence rather than `{verb} this {noun}`,
		// which composed to "Ask for more this volunteer applicant" for the one
		// verb that is a phrase rather than a word.
		button: (noun: string) => `Approve this ${noun}`,
		confirm: "Yes, approve",
		tone: "navy" as const,
		pill: "border-emerald-300 bg-emerald-50 text-emerald-700",
		icon: Icon.check,
		hint: "Endorses this application at your stage and moves it on.",
		consequence:
			"This endorses the application at your stage. If yours is the last stage, it is approved outright.",
	},
	"More info requested": {
		verb: "Ask for more",
		button: (noun: string) => `Ask this ${noun} for more`,
		confirm: "Yes, send it back",
		tone: "soft" as const,
		pill: "border-amber-300 bg-amber-50 text-amber-800",
		icon: Icon.back,
		hint: "Hands it back to the applicant with your reason.",
		consequence:
			"The application goes back to the applicant with your reason, and review starts from the beginning when they resubmit — what the earlier stages endorsed is not what they will be resubmitting.",
	},
	Rejected: {
		verb: "Decline",
		button: (noun: string) => `Decline this ${noun}`,
		confirm: "Yes, decline",
		tone: "primary" as const,
		pill: "border-blue/40 bg-blue/[.07] text-blue-press",
		icon: Icon.cross,
		hint: "Ends the application. Needs a reason.",
		consequence: "This ends the application. It cannot be undone from this screen.",
	},
} as const;

type DecisionKey = keyof typeof DECISIONS;

function Decision({
	status,
	noun,
	person,
	onDecided,
}: {
	status: ApprovalStatus;
	noun: string;
	person: string;
	onDecided: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [chosen, setChosen] = useState<DecisionKey | null>(null);
	const [reason, setReason] = useState("");
	const [confirming, setConfirming] = useState(false);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const picked = chosen ? DECISIONS[chosen] : null;
	// Sending a form back and declining both need a reason. Enforced on the
	// server too — this only stops somebody reaching a confirmation they would
	// be refused at.
	const needsReason = chosen === "Rejected" || chosen === "More info requested";
	const ready = Boolean(chosen) && (!needsReason || reason.trim().length > 0);

	const send = async () => {
		if (!chosen) return;

		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.decide, {
				doctype: status.doctype,
				name: status.name,
				decision: chosen,
				reason: reason.trim() || undefined,
			});
			setConfirming(false);
			// Back to the list. The application has left this queue by definition,
			// so staying on a page that now describes something nobody is waiting
			// on would be a screen going quietly stale.
			onDecided();
		} catch (error) {
			setFailure(errorMessage(error, "That decision was not recorded."));
			setConfirming(false);
		} finally {
			setBusy(false);
		}
	};

	const options = (Object.keys(DECISIONS) as DecisionKey[]).filter(
		// Rejection is a stage property: some stages endorse and cannot refuse.
		(key) => key !== "Rejected" || status.stage?.can_reject,
	);

	return (
		<>
			<Card className="mb-5">
				<SectionTitle>Where this stands</SectionTitle>
				<dl className="grid gap-4 sm:grid-cols-2">
					<Field label="Stage" value={status.stage?.label} />
					<Field label="Entered stage" value={formatDate(status.stage?.entered_on)} />
					<Field label="Decision rule" value={status.stage?.completion_rule} />
					<Field label="Approvers resolved" value={String(status.approver_count)} />
				</dl>

				{/* `is_blocked` means the stage found nobody at its own level. It is
				    entered anyway rather than passed — a stage that needs an approver
				    and cannot find one must be visible, not silently satisfied — and
				    the engine escalates upward so the application still moves.
				    Everything in the grid above reads as an ordinary stage, so
				    without this the screen shows an approval with nobody's name
				    against it, which is the case the flag was added to describe. It
				    is a staffing gap, not a broken record, and it is fixed in Geo
				    Assignment rather than here. */}
				{status.stage?.is_blocked && (
					<p className="mt-4 rounded-xl bg-surface px-4 py-3 text-[12.5px] leading-relaxed text-muted">
						Nobody holds <b>{status.stage.required_role}</b> at this stage's level
						here, so it was escalated
						{status.escalated_to?.length ? ` to ${status.escalated_to.join(", ")}` : " upward"}.
						Assigning somebody at that level puts the decision back where the workflow
						intends it.
					</p>
				)}
			</Card>

			{status.decisions.length > 0 && (
				<Card className="mb-5">
					<SectionTitle>Decisions so far</SectionTitle>
					<Table head={["Decision", "Stage", "By", "When"]}>
						{status.decisions.map((decision, index) => (
							<Row key={index}>
								<Cell className="font-semibold text-ink">{decision.decision}</Cell>
								<Cell className="text-muted">{decision.stage_label}</Cell>
								{/* `approver`, not `decided_by`. The column read the
								    latter for as long as it has existed and rendered
								    nothing: the engine's DTO has never had a field by
								    that name, and the type here said it did. */}
								<Cell className="text-muted">{decision.approver}</Cell>
								<Cell className="text-muted">
									{formatDate(decision.decided_on ?? null)}
									{decision.reason && (
										<span className="mt-1 block text-[11.5px] text-slate-faint">
											{decision.reason}
										</span>
									)}
								</Cell>
							</Row>
						))}
					</Table>
				</Card>
			)}

			<Card>
				{failure && (
					<div className="mb-4">
						<ErrorNote>{failure}</ErrorNote>
					</div>
				)}

				{!status.can_act ? (
					<p className="rounded-xl bg-surface px-4 py-3 text-[12.5px] leading-relaxed text-muted">
						You cannot act on this one right now. The engine resolves approvers per
						document, so holding the role is not the same as being this document's
						approver.
					</p>
				) : (
					<>
						<div className="flex flex-wrap items-center justify-between gap-3">
							<div>
								<SectionTitle>Your decision</SectionTitle>
								<p className="-mt-2 text-[12px] text-slate-faint">
									Choose one, say why if you want to, then confirm.
								</p>
							</div>

							<ActionMenu
								label={picked ? `Change: ${picked.verb}` : "Decide"}
								variant={picked ? "quiet" : "navy"}
								actions={options.map((key) => ({
									key,
									label: DECISIONS[key].verb,
									hint: DECISIONS[key].hint,
									icon: DECISIONS[key].icon,
									tone: key === "Rejected" ? "danger" : "default",
								}))}
								onAction={(key) => {
									setChosen(key as DecisionKey);
									setFailure(null);
								}}
							/>
						</div>

						{picked && chosen && (
							<div className="mt-5">
								{/* The status that changes with the selection: what you
								    have chosen, said back to you before anything is sent. */}
								<span
									className={cx(
										"inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[12px] font-bold",
										picked.pill,
									)}
								>
									<picked.icon size={14} />
									{picked.verb}
								</span>

								<p className="mt-3 text-[12.5px] leading-relaxed text-muted">
									{picked.consequence}
								</p>

								<label
									className="mb-1.5 mt-4 block text-[10px] font-bold uppercase tracking-wider text-slate-faint"
									htmlFor="decision-reason"
								>
									Reason {needsReason ? "(required)" : "(optional)"}
								</label>
								<textarea
									id="decision-reason"
									className="min-h-[90px] w-full resize-y rounded-xl border border-card-line px-3.5 py-2.5 text-[13px] outline-none focus:border-blue"
									value={reason}
									onChange={(event) => setReason(event.target.value)}
									placeholder={
										needsReason
											? chosen === "More info requested"
												? "Tell the applicant exactly what to add or correct."
												: "The applicant is told this. Say what was wrong."
											: "Anything the next approver should know."
									}
								/>

								<div className="mt-4 flex flex-wrap gap-2.5">
									<Button
										variant={picked.tone}
										disabled={!ready}
										onClick={() => setConfirming(true)}
									>
										{picked.button(noun)}
									</Button>
									<Button variant="quiet" onClick={() => setChosen(null)}>
										Cancel
									</Button>
								</div>

								{needsReason && !ready && (
									<p className="mt-2 text-[11.5px] text-slate-faint">
										{chosen === "More info requested"
											? "Say what is missing so the applicant knows what to correct."
											: "Declining needs a reason — the applicant is told it."}
									</p>
								)}
							</div>
						)}
					</>
				)}
			</Card>

			<ConfirmDialog
				open={confirming && Boolean(picked)}
				title={`${picked?.verb} ${person}?`}
				confirmLabel={picked?.confirm ?? "Confirm"}
				tone={picked?.tone}
				busy={busy}
				onConfirm={() => void send()}
				onCancel={() => setConfirming(false)}
			>
				<p>
					You are about to <b>{picked?.verb.toLowerCase()}</b> {person} as a {noun}
					{status.stage ? ` at the ${status.stage.label} stage` : ""}.
				</p>
				<p className="mt-2.5">{picked?.consequence}</p>
			</ConfirmDialog>
		</>
	);
}

function Field({ label, value }: { label: string; value?: string | null }) {
	return (
		<div>
			<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">{label}</dt>
			<dd className="mt-1 text-[13px] text-ink">{value || "—"}</dd>
		</div>
	);
}
