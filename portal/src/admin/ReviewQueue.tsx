import { useContext, useEffect, useMemo, useState } from "react";
import { Link, NavLink, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { branchPath, formatDate, formatMoney, geoPath } from "../lib/format";
import { Icon } from "../ui/icons";
import { PersonHero, RegisterLinks } from "../ui/PersonHero";
import { SearchField } from "../ui/patterns";
import { FileLink, FilePreview } from "../ui/FilePreview";
import { RegistrationDetailsSummary, isWebAddress } from "../ui/RegistrationDetails";
import { BackgroundCard } from "./Person";
import { PostToBooks } from "./PostToBooks";
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
	Pager,
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
	CLOSED_FILTERS,
	bandRoute,
	type QueueBand,
	type QueueKind,
	type QueueSpec,
} from "./queues";
import type {
	AcceptedDeclaration,
	ApplicationDecision,
	ApprovalCases,
	ApprovalStatus,
	AuditEntry,
	MembershipReview,
	RegistrationFile,
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

/** The engine's state, unless the document is holding itself back — then why. */
const CHANGES_REQUESTED = "Changes requested";
const RESUBMITTED = "Resubmitted";

function shownState(status: ApprovalStatus): string {
	if (status.held) return status.held_for?.label ?? "Not ready yet";
	if (status.sent_back) return CHANGES_REQUESTED;
	return status.state;
}

export function VolunteerQueue({ band }: { band?: string } = {}) {
	return <Queue kind="volunteers" band={band} />;
}

export function MembershipQueue({ band }: { band?: string } = {}) {
	return <Queue kind="members" band={band} />;
}

/**
 * One registration's applications, in one of four routed bands.
 *
 * **The two queues never touch each other's endpoints.** `my_cases` takes the
 * doctype off this queue's own spec, so a coordinator on the membership page
 * never asks for volunteer applications and the other way round.
 *
 * **The bands come from the server and none of them is derived here.**
 * `in_review` is Submitted or In Review, with the caller's own decisions first;
 * `drafts` were never submitted; `changes` were sent back; `closed` is one of
 * the four terminal states, optionally narrowed by `?state=`.
 *
 * Seeing a row is not deciding it: every row carries the engine's own
 * `can_act`, and the review page asks the engine again before a decision.
 */
function Queue({ kind, band: segment }: { kind: QueueKind; band?: string }) {
	const spec = QUEUES[kind];
	const band = QUEUE_BANDS.find((row) => row.segment === (segment ?? "")) ?? QUEUE_BANDS[0];
	const isReview = band.key === "in_review";
	const isClosed = band.key === "closed";
	const [params, setParams] = useSearchParams();
	const closedState = isClosed ? (params.get("state") ?? "") : "";
	const [offset, setOffset] = useState(0);
	// What is typed, and what is asked for: the request waits for a pause in
	// typing rather than going out on every keystroke.
	const [typed, setTyped] = useState("");
	const [search, setSearch] = useState("");
	useEffect(() => {
		const wait = window.setTimeout(() => setSearch(typed.trim()), 300);
		return () => window.clearTimeout(wait);
	}, [typed]);
	useEffect(() => setOffset(0), [kind, band.key, closedState, search]);

	const history = useFrappeGetCall<{ message: ApprovalCases }>(
		API.myCases,
		{
			doctype: spec.doctype,
			group: band.key,
			limit: 25,
			offset,
			...(closedState ? { state: closedState } : {}),
			...(search ? { search } : {}),
		},
		`admin:my_cases:${kind}:${band.key}:${closedState}:${search}:${offset}`,
	);

	const rows = history.data?.message?.cases ?? [];
	const total = history.data?.message?.total;
	const { isLoading, error } = history;
	const overdue = rows.filter((row) => row.stage?.is_breached).length;
	const mine = isReview ? rows.filter((row) => row.can_act).length : 0;
	const shown = total ?? rows.length;
	const closedFilter = CLOSED_FILTERS.find((row) => row.key === closedState);

	return (
		<>
			<PageHeading
				title={<EditableText k={spec.headingKey} fallback={spec.heading} />}
				lead={band.lead}
				trail={[{ label: "People", to: "/admin/people" }, { label: spec.heading }]}
				actions={
					<div className="flex flex-wrap items-center gap-2">
						<Pill tone="navy">
							{shown} {total != null ? (shown === 1 ? "application" : "applications") : "shown"}
						</Pill>
						{mine > 0 && <Pill tone="quiet">{mine} for your decision</Pill>}
						{/* Only when there are any. A permanent "0 overdue" is a
						    reassurance nobody reads. */}
						{overdue > 0 && <Pill tone="signal">{overdue} overdue</Pill>}
					</div>
				}
			/>

			<QueueBands spec={spec} current={band} />

			<SearchField
				className="mb-5 max-w-md"
				label={`Search ${spec.heading.toLowerCase()}`}
				placeholder="Search by name, email, phone or reference"
				value={typed}
				onChange={setTyped}
			/>

			{isClosed && (
				<div role="group" aria-label="Show closed applications" className="-mt-2 mb-5 flex flex-wrap gap-1.5">
					{CLOSED_FILTERS.map((filter) => (
						<button
							key={filter.key}
							type="button"
							aria-pressed={filter.key === closedState}
							onClick={() => {
								const updated = new URLSearchParams(params);
								if (filter.key) updated.set("state", filter.key);
								else updated.delete("state");
								setParams(updated, { replace: true });
							}}
							className={cx(
								"rounded-lg border px-3 py-1.5 text-[12px] font-semibold transition",
								filter.key === closedState
									? "border-ink bg-ink text-white"
									: "border-card-line bg-white text-slate-strong hover:border-blue hover:text-ink",
							)}
						>
							{filter.label}
						</button>
					))}
				</div>
			)}

			{isLoading && <Spinner label="Loading the queue…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && rows.length === 0 && (
				<Empty
					title={
						search
							? `No applications match “${search}”.`
							: isReview
							? spec.empty
							: isClosed && closedFilter?.key
								? `No ${closedFilter.label.toLowerCase()} applications.`
								: band.empty
					}
				>
					{band.lead}
				</Empty>
			)}

			{rows.length > 0 && (
				<Table
					head={
						isReview
							? ["Applicant", "Branch", "Stage", "Waiting since", "Due", ""]
							: ["Applicant", "Branch", "State", "Last moved", "Last decision", ""]
					}
				>
					{rows.map((row) => (
						<QueueRow key={row.name} row={row} spec={spec} inReview={isReview} />
					))}
				</Table>
			)}
			{/* Bands that know their total get page numbers like the registers.
			    The draft bands only know whether there is more. */}
			{!error && total != null && total > 25 && (
				<Pager
					page={Math.floor(offset / 25)}
					pageCount={Math.max(1, Math.ceil(total / 25))}
					total={total}
					noun={total === 1 ? "application" : "applications"}
					onPage={(next) => setOffset(next * 25)}
				/>
			)}
			{total == null && !error && (offset > 0 || history.data?.message?.has_more) && (
				<div className="mt-4 flex items-center gap-3 text-sm">
					{/* Only once the page has arrived: while the next page loads its
					    rows are empty, and "Showing 26–25" is not a range. */}
					{rows.length > 0 && (
						<span>
							Showing {offset + 1}–{offset + rows.length}
						</span>
					)}
					<button
						type="button"
						disabled={offset === 0 || isLoading}
						onClick={() => setOffset(Math.max(0, offset - 25))}
						className="font-semibold text-ink disabled:opacity-40"
					>
						Previous
					</button>
					<button
						type="button"
						disabled={!history.data?.message?.has_more || isLoading}
						onClick={() => setOffset(offset + 25)}
						className="font-semibold text-ink disabled:opacity-40"
					>
						Next
					</button>
				</div>
			)}
		</>
	);
}

/**
 * The band navigation, as four routed links.
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
	inReview,
}: {
	row: ApprovalStatus;
	spec: QueueSpec;
	inReview: boolean;
}) {
	const to = `${spec.list}/${encodeURIComponent(row.name)}`;
	const last = row.decisions.at(-1);

	return (
		<Row to={to} label={`Open ${row.applicant?.full_name ?? row.name}`}>
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

			{inReview ? (
				<>
					<Cell>
						{row.stage ? (
							<>
								<span className="flex flex-wrap items-center gap-2">
									<span className="text-[12.5px] font-semibold text-ink">{row.stage.label}</span>
									{/* Sent back once and sent again: this look is a check
									    of what was asked for. */}
									{row.resubmitted && <StateBadge state={RESUBMITTED} />}
								</span>
								{/* The stage resolved nobody at its own level, so the
								    engine entered it blocked and escalated upward —
								    which is the only reason this row is in *this*
								    person's queue rather than the branch's. Without
								    the line it reads as an ordinary assignment and
								    the unstaffed branch behind it stays invisible. */}
								{row.stage.is_blocked && row.can_act && (
									<span className="mt-0.5 block text-[11px] text-slate-faint">
										Escalated to you: no approver at this level
									</span>
								)}
							</>
						) : (
							<StateBadge state={shownState(row)} />
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
						<StateBadge state={shownState(row)} />
					</Cell>
					{/* An open application with no decision yet last moved when it
					    entered its current stage. */}
					<Cell className="text-muted">{formatDate(last?.decided_on ?? row.stage?.entered_on ?? null)}</Cell>
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

	const files = record?.attachments ?? review?.attachments ?? [];
	const memberDeclarations = review?.declarations ?? [];

	const tabs: TabDef[] = [
		{ key: "applicant", label: "Applicant" },
		// In the order the registration form asks: who they are, then what they
		// have done, then what they offer.
		...(isVolunteer ? [{ key: "background", label: "Education and experience" }] : []),
		isVolunteer
			? { key: "declaration", label: "Additional Info" }
			: { key: "membership", label: "Membership" },
		// The tab that carries the two things this decision can be refused over.
		// Volunteer-only, and only once the record has loaded: an approver who
		// cannot see the emergency contact would press Approve, be told no, and
		// have nowhere to look.
		...(isVolunteer && record ? [{ key: "safeguarding", label: "Emergency contact and declarations" }] : []),
		...(!isVolunteer && memberDeclarations.length
			? [{ key: "declarations", label: "Declarations", count: memberDeclarations.length }]
			: []),
		...(record || review ? [{ key: "documents", label: "Documents", count: files.length || undefined }] : []),
		...grouped.map((group) => ({
			key: `q:${group.name}`,
			label: group.name,
			count: group.answers.length,
		})),
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
				status={shownState(status)}
				badges={
					<>
						{status.resubmitted && <StateBadge state={RESUBMITTED} />}
						<RegisterLinks registers={registers.data?.message} />
					</>
				}
				facts={[
					{ label: "Email", value: person?.email },
					{ label: "Phone", value: person?.phone },
					...(status.stage
						? [
								{ label: "Stage", value: status.stage.label },
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

			{/* The decision sits beside the record rather than behind a tab, as in
			    the UI concept: an approver reads the Documents tab and decides
			    without leaving it. Below 1200px the panel moves above the tabs. */}
			<div className="application-review-layout">
			<div className="min-w-0">
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

			{active === "background" && record && (
				<>
					<ProfessionalProfiles
						linkedin={record.personal_details?.linkedin}
						github={record.personal_details?.github}
						profession={record.profession}
					/>
					<BackgroundCard background={record.background} files={files} />
					{!hasBackground(record.background) && (
						<Card>
							<Empty title="No education or experience given." />
						</Card>
					)}
				</>
			)}

			{active === "declaration" && record && (
				<Card>
					<Declared label="Skills" rows={record.skills} />
					<Declared label="Languages" rows={record.languages} />
					<Declared label="Availability" rows={record.availability} />
					<Declared label="Motivation" rows={record.motivation} />

					{record.prior_experience && (
						<div className="mt-5 border-t border-card-line pt-5">
							<SectionTitle>Previous volunteer experience</SectionTitle>
							<p className="whitespace-pre-line text-[13px] leading-relaxed text-ink">
								{record.prior_experience}
							</p>
						</div>
					)}
				</Card>
			)}

			{active === "safeguarding" && record && <Safeguarding record={record} />}

			{active === "declarations" && review && <Declarations rows={memberDeclarations} />}

			{active === "documents" && <Documents files={files} />}



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

			</div>
			<aside className="application-review-sidebar" aria-label="Decision">
				<Decision status={status} noun={spec.noun} person={person?.full_name ?? status.name} onDecided={onDecided} />
			</aside>
			</div>

			{/* Under every tab, as Frappe shows Activity under a form. */}
			<Activity doctype={spec.doctype} name={name} />
		</>
	);
}

/* ------------------------------------------------------------------ blocks */

function VolunteerApplicant({ record }: { record: ApplicationDecision }) {
	return (
		<div className="space-y-6">
		<dl className="grid gap-4 sm:grid-cols-2">
			<Field label="Full name" value={record.full_name} />
			<Field label="Applied on" value={formatDate(record.applied_on)} />
			<Field label="Email" value={record.email} />
			<Field label="Phone" value={record.phone} />
			<Field label="Gender" value={record.gender} />
			<Field label="Date of birth" value={formatDate(record.date_of_birth)} />
			<Field label="Preferred language" value={record.preferred_language} />
			<div>
				<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">Identifications</dt>
				<dd className="mt-1 space-y-1 text-[13px] text-ink">
					{record.identifications.length === 0
						? "—"
						: record.identifications.map((row, index) => {
								const file = record.attachments?.find(
									(entry) => entry.table === "identifications" && entry.index === index,
								);
								return (
									<div key={`${row.id_type}-${index}`} className="flex flex-wrap items-center gap-x-2">
										<span>{`${row.id_type_name ?? row.id_type} ${row.id_number}`.trim()}</span>
										{file && <FileLink url={file.url} name={file.file_name} className="text-[12px]" />}
									</div>
								);
							})}
				</dd>
			</div>
			<Field label="Country of citizenship" value={record.country_of_citizenship} />
			<Field label="Citizenship status" value={record.citizenship_status} />
			<Field
				label="Residence"
				value={
					record.residency_type === "Abroad"
						? [record.country_of_residence, record.residence_address]
								.filter(Boolean)
								.join(" · ") || "Abroad"
						: geoPath(record.home_geo_path)
				}
			/>
			<Field label="Branch / County" value={branchPath(record.geo_path)} />
		</dl>
		<RegistrationDetailsSummary
			value={record.personal_details}
			evidenceContext={{ doctype: "VMMS Volunteer Application", name: record.name }}
			showProfileLinks={false}
			disability={record}
		/>
		</div>
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
		<div className="space-y-6">
		<dl className="grid gap-4 sm:grid-cols-2">
			<Field label="Full name" value={person?.full_name} />
			<Field label="Email" value={person?.email} />
			<Field label="Phone" value={person?.phone} />
			<Field label="Gender" value={person?.gender} />
			<Field label="Date of birth" value={formatDate(person?.date_of_birth)} />
			<Field label="Preferred language" value={person?.preferred_language} />
			<Field
				label="Identifications"
				value={
					(review.identifications ?? [])
						.map((row) => `${row.id_type_name ?? row.id_type} ${row.id_number}`.trim())
						.join(" · ") || null
				}
			/>
			<Field label="Country of citizenship" value={person?.country_of_citizenship} />
			<Field label="Citizenship status" value={person?.citizenship_status} />
			<Field
				label="Residence"
				value={
					person?.residency_type === "Abroad"
						? [person.country_of_residence, person.residence_address].filter(Boolean).join(" · ")
						: geoPath(person?.home_geo_path)
				}
			/>
			{review.profession && <Field label="Profession" value={review.profession} />}
		</dl>
		<RegistrationDetailsSummary
			value={person?.personal_details}
			evidenceContext={{ doctype: "VMMS Membership", name: review.name }}
			disability={review}
		/>

		</div>
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
				<SectionTitle>Membership details</SectionTitle>
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
				<SectionTitle>Payment</SectionTitle>
				<dl className="grid gap-4 sm:grid-cols-2">
					<Field
						label="Fee"
						value={fee ? `${fee.currency ?? ""} ${fee.amount}`.trim() : null}
					/>
					<Field label="Settled" value={row.payment_settled ? "Yes" : "Not yet"} />
					<Field label="Source" value={review.membership_source} />
					<Field label="Paid with" value={row.payment?.gateway} />
					<Field
						label="Amount paid"
						value={
							row.payment?.amount_paid !== null && row.payment?.amount_paid !== undefined && row.payment_settled
								? formatMoney(row.payment.amount_paid, row.payment.currency_paid, true)
								: null
						}
					/>
					<Field
						label={row.payment?.gateway?.toLowerCase().includes("m-pesa") ? "M-Pesa receipt" : "Receipt"}
						value={row.payment_receipt || row.payment?.gateway_receipt}
					/>
					<Field
						label="Paid on"
						value={
							row.payment?.transaction_date || row.paid_on
								? formatDateTime((row.payment?.transaction_date || row.paid_on) as string)
								: null
						}
					/>
					<Field label="Phone number" value={row.payment?.paid_from || row.payer_phone} />
					<Field label="Payment reference" value={row.payment_transaction} />
					<Field
						label="In the books"
						value={
							row.accounting_status === "Posted"
								? "Posted to ERPNext"
								: row.accounting_status === "Failed"
									? `Not posted: ${row.accounting_note ?? "see the membership"}`
									: row.can_post_to_books
										? "Not posted yet"
										: null
						}
					/>
					<Field label="Sales invoice" value={row.sales_invoice} />
					<Field label="Payment entry" value={row.payment_entry} />
				</dl>

				{/* The member's own receipt, as they print it: for a counter query, or
				    to print a copy for somebody who has lost theirs. */}
				{row.paid_on && review.membership_source !== "Proof" && (fee?.amount ?? 0) > 0 && (
					<Link
						to={`/receipt/${encodeURIComponent(row.name)}`}
						target="_blank"
						rel="noreferrer"
						className="mt-4 inline-flex items-center rounded-lg border border-rail-line bg-white px-3.5 py-2 text-[12.5px] font-semibold text-slate-strong transition hover:border-slate-faint hover:text-ink"
					>
						View receipt
					</Link>
				)}

				{/* Accounts staff only: the answer to "Not posted" just above. */}
				{row.can_post_to_books && (
					<div className="mt-5 border-t border-card-line pt-5">
						<PostToBooks row={row} onPosted={onRecorded} />
					</div>
				)}

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
		// Apart, like the cards on every other tab, so the emergency contact,
		// any guardian consent and the declarations read as separate sections.
		<div className="space-y-5">
			<Card>
				<SectionTitle>Emergency contact</SectionTitle>

				{callable.length === 0 && (
					<p className="mb-4 rounded-xl border border-blue/30 bg-blue/[0.06] px-3.5 py-2.5 text-[12.5px] leading-relaxed text-ink">
						{record.emergency_contacts.length === 0
							? "No emergency contact. This application cannot be approved until one is added."
							: "No emergency contact has permission to be contacted. This application cannot be approved until one does."}
					</p>
				)}

				{record.emergency_contacts.length === 0 ? (
					<Empty title="No emergency contact." />
				) : (
					record.emergency_contacts.map((row, index) => (
						<dl
							key={`${row.contact_name}-${index}`}
							className="mb-5 grid gap-4 border-b border-card-line pb-5 last:mb-0 last:border-0 last:pb-0 sm:grid-cols-2"
						>
							<Field label="Name" value={row.contact_name} />
							<Field label="Relationship" value={row.relationship} />
							<Field label="Phone number" value={row.primary_phone} />
							<Field label="Alternative phone number" value={row.alternative_phone} />
							<Field
								label="Permission to contact in an emergency"
								value={row.may_contact_in_emergency ? "Yes" : "No"}
							/>
						</dl>
					))
				)}
			</Card>

			{record.is_minor && (
				<Card>
					<SectionTitle>Parent or guardian consent</SectionTitle>

					{verified.length === 0 && (
						<p className="mb-4 rounded-xl border border-blue/30 bg-blue/[0.06] px-3.5 py-2.5 text-[12.5px] leading-relaxed text-ink">
							This applicant is a minor. This application cannot be approved until parent or
							guardian consent is recorded and verified.
						</p>
					)}

					{record.guardian_consents.length === 0 ? (
						<Empty title="No parent or guardian consent." />
					) : (
						record.guardian_consents.map((row, index) => (
							<dl
								key={`${row.guardian_name}-${index}`}
								className="mb-5 grid gap-4 border-b border-card-line pb-5 last:mb-0 last:border-0 last:pb-0 sm:grid-cols-2"
							>
								<Field label="Parent or guardian's name" value={row.guardian_name} />
								<Field label="Relationship" value={row.relationship} />
								<Field label="Phone number" value={row.phone} />
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
											Consent document
										</span>
										<div className="mt-1 text-[13px]">
											<FileLink url={row.consent_evidence} />
										</div>
									</div>
								)}
							</dl>
						))
					)}
				</Card>
			)}

			<Declarations rows={record.declarations} />
		</div>
	);
}

/** LinkedIn, GitHub and profession together, as the registration form asks them. */
function ProfessionalProfiles({
	linkedin,
	github,
	profession,
}: {
	linkedin?: string | null;
	github?: string | null;
	profession?: string | null;
}) {
	const link = (value?: string | null) =>
		value && isWebAddress(value) ? (
			<a
				href={value}
				target="_blank"
				rel="noopener noreferrer"
				className="break-all font-semibold text-ink underline underline-offset-2"
			>
				{value}
			</a>
		) : (
			value || "—"
		);

	return (
		<Card className="mb-5">
			<SectionTitle>Professional profiles</SectionTitle>
			<dl className="grid gap-4 sm:grid-cols-2">
				<div>
					<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">LinkedIn profile</dt>
					<dd className="mt-1 text-[13px] text-ink">{link(linkedin)}</dd>
				</div>
				<div>
					<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">GitHub profile</dt>
					<dd className="mt-1 text-[13px] text-ink">{link(github)}</dd>
				</div>
				<Field label="Profession" value={profession} />
			</dl>
		</Card>
	);
}

/** Whether any education or experience table has a row. */
function hasBackground(background?: ApplicationDecision["background"]): boolean {
	return Boolean(background && Object.values(background).some((rows) => Array.isArray(rows) && rows.length > 0));
}

/**
 * What the applicant agreed to, and the exact wording of each version.
 *
 * The wording is the snapshot stored with the acceptance, so a declaration
 * reworded since still reads as the version this applicant agreed to.
 */
function Declarations({ rows }: { rows: AcceptedDeclaration[] }) {
	return (
		<Card>
			<SectionTitle>Declarations</SectionTitle>

			{rows.length === 0 ? (
				<Empty title="No declarations required." />
			) : (
				<ul className="divide-y divide-card-line">
					{rows.map((row) => (
						<li key={row.declaration} className="py-4 first:pt-0 last:pb-0">
							<div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
								<span className="text-[13px] font-semibold text-ink">{row.title}</span>
								<span className="text-[12px] text-muted">
									{row.accepted
										? `Agreed · version ${row.version}${row.accepted_on ? ` · ${formatDate(row.accepted_on)}` : ""}`
										: "Not agreed"}
								</span>
							</div>

							{row.body && (
								<details className="group mt-2">
									<summary className="cursor-pointer text-[12px] font-bold text-ink hover:underline">
										Read version {row.version}
									</summary>
									<div
										className="mt-2 max-h-80 overflow-auto rounded-xl border border-card-line bg-surface px-4 py-3 text-[12.5px] leading-relaxed text-ink [&_li]:ml-4 [&_ol]:list-decimal [&_p]:mb-2 [&_ul]:list-disc"
										// The society's own wording as stored with this acceptance.
										// A Text Editor field, sanitised by Frappe when saved, and
										// rendered the same way on the registration form.
										dangerouslySetInnerHTML={{ __html: row.body }}
									/>
								</details>
							)}

							{/* Published on the society's own site rather than here, so the
							    address is all the register holds. */}
							{row.source === "Link" && row.external_url && (
								<a
									href={row.external_url}
									target="_blank"
									rel="noreferrer noopener"
									className="mt-2 inline-flex items-center gap-1.5 text-[12px] font-semibold text-ink hover:underline"
								>
									<Icon.external size={12} />
									Open the declaration
								</a>
							)}
						</li>
					))}
				</ul>
			)}
		</Card>
	);
}

/** Every file the applicant attached, shown as itself, under the step it came from. */
function Documents({ files }: { files: RegistrationFile[] }) {
	if (files.length === 0) {
		return (
			<Card>
				<Empty title="No documents attached." />
			</Card>
		);
	}

	const groups: Array<{ name: string; files: RegistrationFile[] }> = [];
	for (const file of files) {
		const group = groups.find((entry) => entry.name === file.group);
		if (group) group.files.push(file);
		else groups.push({ name: file.group, files: [file] });
	}

	return (
		<div className="space-y-5">
			{groups.map((group) => (
				<Card key={group.name}>
					<SectionTitle>{group.name}</SectionTitle>
					<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
						{group.files.map((file) => (
							<FilePreview key={file.key} url={file.url} name={file.file_name} label={file.label} />
						))}
					</div>
				</Card>
			))}
		</div>
	);
}

/**
 * The record's activity, at the foot of the page as Frappe shows it under a
 * form: who created it, then each save and what it changed, newest first.
 *
 * Read from Frappe's own change log for the application or membership and the
 * applicant's personal details. Approval decisions stay on the Decision tab.
 */
const ACTIVITY_SHOWN = 10;

/**
 * Whether this reader wants the activity shown, remembered in their browser so
 * switching it on once keeps it on for every application they open. Off until
 * they ask; a browser that will not store it simply starts off each time.
 */
const ACTIVITY_PREFERENCE = "vmmsx.review.activity";

function activityWanted(): boolean {
	try {
		return window.localStorage.getItem(ACTIVITY_PREFERENCE) === "on";
	} catch {
		return false;
	}
}

function rememberActivity(on: boolean) {
	try {
		window.localStorage.setItem(ACTIVITY_PREFERENCE, on ? "on" : "off");
	} catch {
		// Not stored: the switch still works on this page.
	}
}

function Activity({ doctype, name }: { doctype: string; name: string }) {
	// Not read until it is shown.
	const [visible, setVisible] = useState(activityWanted);
	const { data, error, isLoading } = useFrappeGetCall<{ message: AuditEntry[] }>(
		API.auditTrail,
		{ doctype, name },
		visible ? `review:activity:${doctype}:${name}` : null,
	);
	const [all, setAll] = useState(false);
	const entries = data?.message ?? [];
	const shown = all ? entries : entries.slice(0, ACTIVITY_SHOWN);

	return (
		<section className="mt-8 border-t border-card-line pt-6" aria-label="Activity">
			<div className="flex items-center justify-between gap-4">
				<h2 id="activity-heading" className="text-[14px] font-bold text-ink">
					Activity
				</h2>
				<button
					type="button"
					role="switch"
					aria-checked={visible}
					aria-labelledby="activity-toggle-label"
					onClick={() => {
						rememberActivity(!visible);
						setVisible(!visible);
					}}
					className="inline-flex items-center gap-2 text-[12px] font-semibold text-muted"
				>
					<span id="activity-toggle-label">Show activity</span>
					<span
						aria-hidden="true"
						className={cx(
							"relative inline-block h-5 w-9 rounded-full transition",
							visible ? "bg-navy" : "bg-rail-line",
						)}
					>
						<span
							className={cx(
								"absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all",
								visible ? "left-[18px]" : "left-0.5",
							)}
						/>
					</span>
				</button>
			</div>

			{visible && (
				<div className="mt-4">
					{isLoading && <Spinner label="Loading activity…" />}
					{error && <ErrorNote>{errorMessage(error, "The activity could not be loaded.")}</ErrorNote>}
					{!isLoading && !error && entries.length === 0 && (
						<p className="text-[12.5px] text-muted">No changes recorded.</p>
					)}

					{shown.length > 0 && (
						<ol className="relative ml-3 border-l border-card-line">
							{shown.map((entry, index) => (
								<li key={`${entry.on}-${index}`} className="relative pb-5 pl-6 last:pb-0">
									<span
										aria-hidden="true"
										className="absolute -left-3 top-0 grid h-6 w-6 place-items-center rounded-full border border-card-line bg-white text-[9.5px] font-bold text-muted"
									>
										{initials(entry.by)}
									</span>
									<ActivityLine entry={entry} />
								</li>
							))}
						</ol>
					)}

					{entries.length > ACTIVITY_SHOWN && (
						<button
							type="button"
							onClick={() => setAll((was) => !was)}
							className="mt-4 text-[12px] font-bold text-ink hover:underline"
						>
							{all ? "Show less" : "Show all activity"}
						</button>
					)}
				</div>
			)}
		</section>
	);
}

/** One save, worded the way Frappe words its timeline. */
function ActivityLine({ entry }: { entry: AuditEntry }) {
	const when = (
		<time dateTime={entry.on} title={formatDateTime(entry.on)} className="text-muted">
			{" · "}
			{timeAgo(entry.on)}
		</time>
	);
	const what = entry.record === "Personal details" ? "personal details" : `this ${entry.record.toLowerCase()}`;

	if (entry.kind === "created") {
		return (
			<p className="pt-0.5 text-[12.5px] text-ink">
				<span className="font-semibold">{entry.by}</span> created {what}
				{when}
			</p>
		);
	}

	const [only] = entry.changes;
	if (entry.changes.length === 1) {
		return (
			<p className="pt-0.5 text-[12.5px] text-ink">
				<span className="font-semibold">{entry.by}</span>{" "}
				{only.row ? (
					<>
						changed {only.field} on {what}: {only.row}
					</>
				) : (
					<>
						changed {only.field} on {what} <Change change={only} />
					</>
				)}
				{when}
			</p>
		);
	}

	return (
		<div className="pt-0.5 text-[12.5px] text-ink">
			<p>
				<span className="font-semibold">{entry.by}</span> changed {what}
				{when}
			</p>
			<ul className="mt-1 space-y-0.5 text-[12px]">
				{entry.changes.map((change, at) => (
					<li key={at}>
						<span className="font-semibold">{change.field}</span>
						{change.row ? <>: {change.row}</> : <> <Change change={change} /></>}
					</li>
				))}
			</ul>
		</div>
	);
}

function Change({ change }: { change: AuditEntry["changes"][number] }) {
	return (
		<>
			from <span className="font-semibold">{change.from ?? "empty"}</span> to{" "}
			<span className="font-semibold">{change.to ?? "empty"}</span>
		</>
	);
}

function initials(name: string): string {
	return (
		name
			.split(/\s+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((part) => part[0]?.toUpperCase() ?? "")
			.join("") || "?"
	);
}

/** "3 hours ago", and the date itself once it is more than a week old. */
function timeAgo(value: string): string {
	const then = new Date(value.replace(" ", "T")).getTime();
	if (Number.isNaN(then)) return value;
	const minutes = Math.round((Date.now() - then) / 60000);
	if (minutes < 1) return "just now";
	if (minutes < 60) return minutes === 1 ? "1 minute ago" : `${minutes} minutes ago`;
	const hours = Math.round(minutes / 60);
	if (hours < 24) return hours === 1 ? "1 hour ago" : `${hours} hours ago`;
	const days = Math.round(hours / 24);
	if (days < 7) return days === 1 ? "1 day ago" : `${days} days ago`;
	return formatDate(value.slice(0, 10));
}

/** A saved moment in the reader's own date and time format. */
function formatDateTime(value: string): string {
	const date = new Date(value.replace(" ", "T"));
	if (Number.isNaN(date.getTime())) return value;
	return `${formatDate(value.slice(0, 10))} ${date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`;
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
								<FileLink url={answer.file_url} />
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
 * buttons puts Reject the same distance from a stray click as Approve, and
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
		// which composed to "Request more information this volunteer applicant" for the one
		// verb that is a phrase rather than a word.
		button: (noun: string) => `Approve this ${noun}`,
		confirm: "Yes, approve",
		tone: "navy" as const,
		pill: "border-emerald-300 bg-emerald-50 text-emerald-700",
		icon: Icon.check,
		hint: "Approves this stage and moves the application on.",
		consequence: "This approves the application at your stage. If this is the last stage, the application is approved.",
	},
	"More info requested": {
		verb: "Request more information",
		button: (noun: string) => `Send the request for more information to this ${noun}`,
		// The settled panel already says what this does, in the pill and the
		// sentence under it, so the button only has to look like the way out of
		// the panel. A soft wash with a long sentence on it read as one more note.
		short: "Send",
		confirm: "Yes, send it back",
		tone: "primary" as const,
		pill: "border-amber-300 bg-amber-50 text-amber-800",
		icon: Icon.back,
		hint: "Returns the application to the applicant with your reason.",
		consequence:
			"The application is returned to the applicant with your reason. When they resubmit, review starts again from the first stage.",
	},
	Rejected: {
		verb: "Reject",
		button: (noun: string) => `Reject this ${noun}`,
		confirm: "Yes, reject",
		tone: "primary" as const,
		pill: "border-blue/40 bg-blue/[.07] text-blue-press",
		icon: Icon.cross,
		hint: "Closes the application. A reason is required.",
		consequence: "This closes the application. It cannot be undone.",
	},
} as const;

type DecisionKey = keyof typeof DECISIONS;

/** A stage's completion rule, as words. The engine's values are code. */
const COMPLETION_RULES: Record<string, string> = {
	single: "One approver",
	any_of: "Any one approver",
	all_of: "All approvers",
};

function completionRule(rule?: string | null): string | undefined {
	return rule ? (COMPLETION_RULES[rule] ?? rule) : undefined;
}

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

	// Held back by the document itself: nobody's to decide yet, so nothing to press.
	if (status.held) {
		return (
			<Card className="mb-5">
				<SectionTitle>{status.held_for?.label ?? "Not ready yet"}</SectionTitle>
				<p className="text-[13px] leading-relaxed text-slate-body">
					{status.held_for?.note ?? "This application is not ready for a decision yet."}
				</p>
			</Card>
		);
	}

	return (
		<>
			<Card className="mb-5">
				{failure && (
					<div className="mb-4">
						<ErrorNote>{failure}</ErrorNote>
					</div>
				)}

				{!status.can_act ? (
					<p className="rounded-xl bg-surface px-4 py-3 text-[12.5px] leading-relaxed text-muted">
						You are not an approver for this application at its current stage.
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
								// Opens rightwards, inside the decision panel: the
								// panel sits at the right edge of the page.
								align="left"
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
												: "Reason for rejection. The applicant will see this."
											: "Anything the next approver should know."
									}
								/>

								<div className="mt-4 flex flex-wrap gap-2.5">
									<Button
										variant={picked.tone}
										disabled={!ready}
										onClick={() => setConfirming(true)}
										label={"short" in picked ? picked.button(noun) : undefined}
									>
										{"short" in picked ? (
											<>
												<Icon.send size={14} />
												{picked.short}
											</>
										) : (
											picked.button(noun)
										)}
									</Button>
									<Button variant="quiet" onClick={() => setChosen(null)}>
										Cancel
									</Button>
								</div>

								{needsReason && !ready && (
									<p className="mt-2 text-[11.5px] text-slate-faint">
										{chosen === "More info requested"
											? "Say what is missing so the applicant knows what to correct."
											: "A reason is required. The applicant will see it."}
									</p>
								)}
							</div>
						)}
					</>
				)}
			</Card>

			<Card className="mb-5">
				<SectionTitle>Approval status</SectionTitle>
				<dl className="grid gap-4 sm:grid-cols-2">
					<Field label="Stage" value={status.stage?.label} />
					<Field label="Stage started" value={formatDate(status.stage?.entered_on)} />
					<Field label="Approval needed from" value={completionRule(status.stage?.completion_rule)} />
					<Field label="Approvers" value={String(status.approver_count)} />
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
						No one holds <b>{status.stage.required_role}</b> at this level, so this
						application was escalated
						{status.escalated_to?.length ? ` to ${status.escalated_to.join(", ")}` : " upward"}.
						Assign someone at this level in Geo Assignment to return it to them.
					</p>
				)}
			</Card>

			{status.decisions.length > 0 && (
				<Card className="mb-5">
					<SectionTitle>Decision history</SectionTitle>
					<ol className="space-y-3">
						{status.decisions.map((decision, index) => (
							<li key={index} className="border-l-2 border-card-line pl-3">
								<span className="block text-[12.5px] font-semibold text-ink">{decision.decision}</span>
								<span className="block text-[11.5px] text-muted">
									{decision.stage_label} · {formatDate(decision.decided_on ?? null)}
								</span>
								{/* `approver`, not `decided_by`: the engine's DTO has
								    never had a field by that name. */}
								<span className="block truncate text-[11.5px] text-slate-faint">{decision.approver}</span>
								{decision.reason && (
									<span className="mt-1 block text-[11.5px] leading-relaxed text-slate-body">
										{decision.reason}
									</span>
								)}
							</li>
						))}
					</ol>
				</Card>
			)}

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
