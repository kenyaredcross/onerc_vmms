import { useCallback, useMemo, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
// `branchPath` rather than `geoPath` in the rows below: every record in this
// console belongs to the same society, so repeating its name down a column
// spends the width of the column saying the one thing that is true of all of
// them. See the helper's own docstring.
import { branchPath, formatDate } from "../lib/format";
import { GeoSelects } from "../ui/GeoSelects";
import { Icon } from "../ui/icons";
import { PersonCard, PersonSummaryBody, type SummaryFact } from "../ui/PersonCard";
import {
	Avatar,
	Card,
	Cell,
	Empty,
	ErrorNote,
	PageHeading,
	Pager,
	Pill,
	Row,
	Skeleton,
	Spinner,
	StateBadge,
	Table,
	cx,
} from "../ui/primitives";
import type {
	GeoNode,
	MemberDossier,
	MemberRegisterSummary,
	PricedType,
	VolunteerDossier,
	VolunteerRegisterSummary,
} from "../portal/types";

interface MemberRow {
	membership: string;
	member: string;
	full_name: string;
	/**
	 * Their photograph, or null — read in bulk with the names by
	 * `register._names_for`, never one query per row. Null is the ordinary case
	 * for anybody registered from a paper form, and `Avatar` draws initials.
	 */
	photo: string | null;
	membership_type: string;
	membership_type_name: string;
	geo_node: string | null;
	geo_path: string | null;
	membership_status: string;
	effective_status: string;
	lapsed: boolean;
	is_current: boolean;
	valid_from: string | null;
	valid_to: string | null;
	membership_source: string | null;
}

interface VolunteerRow {
	volunteer: string;
	red_profile: string;
	full_name: string;
	/** See `MemberRow.photo`. Built by `api/volunteer.py::_match_row`. */
	photo: string | null;
	status: string;
	joined_on: string | null;
	geo_node: string | null;
	geo_path: string | null;
	deployable: boolean;
}

/** One page of a register. Server-side, so it is not a slice of a capped read. */
const PAGE = 25;

/**
 * The two active registers — who this coordinator is actually responsible for.
 *
 * **These are registers of *active* people, and that is the whole change.** They
 * used to be every record in either doctype with a standing filter on top, which
 * made the commonest question — who is on the books here — the one you had to
 * set a control to ask. Prospective, Suspended and Exited volunteers, and
 * memberships that are draft, awaiting payment, awaiting approval, expired or
 * cancelled, are not gone: each is a state with its own screen and its own
 * workflow, and none of them belongs in a list a coordinator staffs from.
 *
 * The volunteer register asks `find_volunteers` for `status="Active"` and the
 * member register asks `find_members` for `current_only=1`. Both are arguments
 * the server enforces, not a filter drawn over a wider read.
 *
 * **Nothing on either page filters by branch, and nothing needs to.** Both
 * endpoints end in `frappe.get_list`, which runs core's permission query
 * condition, so the caller's geo scope is the floor the query stands on rather
 * than something this screen applies on top. A coordinator sees their own
 * branches because of who they are, not because of a parameter the browser sent,
 * and there is consequently no control here that could be tampered with to widen
 * the result. An empty register for somebody with no scope is the correct
 * render, not a failure state.
 *
 * **Every control narrows and none widens**, which is the same property from the
 * other side: the branch picker names a node *within* the caller's scope, and
 * naming one outside it returns nothing rather than reaching it.
 *
 * **Paging is the server's**, and so are the summary figures above the table.
 * Each page is its own scoped read; the tiles come from their own aggregate
 * endpoint rather than from `total`, because a page's length is a page's length
 * however it is labelled.
 *
 * **The skills, languages and availability filters are gone from here.** They
 * are still on the doctype and still drive deployment matching, which is where
 * that question belongs — "who can do this job" is asked while staffing a
 * deployment, against a terms of reference that says what is needed. Asking it
 * in a register meant three identical unlabelled comboboxes above the list
 * everybody actually came for.
 */
export function MembersRegistry() {
	return (
		<>
			<PageHeading
				title={<EditableText k="admin.registry.members.heading" fallback="Active members" />}
				lead="People with a currently active membership inside your geographic scope."
				trail={[{ label: "People", to: "/admin/people" }, { label: "Active members" }]}
			/>
			<Members />
		</>
	);
}

export function VolunteersRegistry() {
	return (
		<>
			<PageHeading
				title={<EditableText k="admin.registry.volunteers.heading" fallback="Active volunteers" />}
				lead="People currently active as volunteers inside your geographic scope."
				trail={[{ label: "People", to: "/admin/people" }, { label: "Active volunteers" }]}
			/>
			<Volunteers />
		</>
	);
}

/**
 * The search term, kept in the URL.
 *
 * So the People overview's "find a person" box can hand this screen a question
 * as a link, and so a coordinator who found somebody can send the address to a
 * colleague. `replace` on every keystroke, because a search box that pushed a
 * history entry per character would make the back button a text-rewinder.
 */
function useQueryTerm(): [string, (value: string) => void] {
	const [params, setParams] = useSearchParams();
	const term = params.get("q") ?? "";

	const set = useCallback(
		(value: string) => {
			const next = new URLSearchParams(params);

			if (value) next.set("q", value);
			else next.delete("q");

			setParams(next, { replace: true });
		},
		[params, setParams],
	);

	return [term, set];
}

/* --------------------------------------------------------------- volunteers */

function Volunteers() {
	const [search, setSearch] = useQueryTerm();
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [page, setPage] = useState(0);

	const geoNode = chain.length > 0 ? chain[chain.length - 1].name : undefined;
	const branchLabel = branchOf(chain);

	/**
	 * Any change to the criteria puts the reader back on the first page.
	 *
	 * Somebody on page three who narrows to four results must not be left
	 * staring at an empty page three — the bug every hand-rolled pager
	 * eventually has. Paging on the server means guarding it here.
	 */
	const narrow =
		<T,>(set: (value: T) => void) =>
		(value: T) => {
			set(value);
			setPage(0);
		};

	// The register's own figures, over the whole scoped register rather than
	// over this page of it. Its own endpoint for exactly that reason.
	const summary = useFrappeGetCall<{ message: VolunteerRegisterSummary }>(
		API.volunteerRegisterSummary,
		undefined,
		"registry:volunteers:summary",
	);

	const { data, error, isLoading } = useFrappeGetCall<{
		message: { count: number; total: number; volunteers: VolunteerRow[] };
	}>(
		API.findVolunteers,
		{
			// Active, always. The register is of active volunteers, and the
			// server is what enforces that rather than a control somebody could
			// clear.
			status: "Active",
			limit: PAGE,
			offset: page * PAGE,
			search: search || undefined,
			geo_node: geoNode,
		},
		`admin:find_volunteers:${page}:${search}:${geoNode ?? ""}`,
	);

	const rows = data?.message?.volunteers ?? [];
	const total = data?.message?.total ?? 0;
	const figures = summary.data?.message;

	return (
		<>
			<SummaryStrip
				loading={summary.isLoading}
				capped={figures?.capped}
				tiles={[
					{ label: "Active volunteers", value: figures?.active, hint: "In your assigned scope" },
					{
						label: "Currently deployed",
						// `null` where this reader may not see deployments at all.
						// The tile draws a dash, and the hint says why rather than
						// claiming nothing is running.
						value: figures?.deployed ?? null,
						hint:
							figures && figures.deployments === null
								? "Deployments are not in your permissions"
								: `Across ${figures?.deployments ?? 0} active deployment${figures?.deployments === 1 ? "" : "s"}`,
					},
					{
						label: "Joined this month",
						value: figures?.joined_month,
						hint: "Approved and activated",
					},
					{
						label: "Branches represented",
						// `null` past the read ceiling; the tile says so rather than
						// showing a number from a truncated read.
						value: figures?.branches ?? null,
						hint: "Distinct serving branches",
					},
				]}
			/>

			<RegisterToolbar
				search={search}
				onSearch={narrow(setSearch)}
				placeholder="Search by name or volunteer number"
				chips={branchLabel ? [{ key: "branch", label: branchLabel, clear: () => narrow(setChain)([]) }] : []}
				onClearAll={() => {
					setSearch("");
					setChain([]);
					setPage(0);
				}}
			>
				<Labelled label="Serving branch" hint="Their branch, and everything under it.">
					{/* One select per rung of the society's own ladder. This screen
					    does not know how deep the hierarchy is or what a rung is
					    called. */}
					<GeoSelects chain={chain} onChain={narrow(setChain)} idPrefix="registry-vol" />
				</Labelled>
			</RegisterToolbar>

			{isLoading && <Spinner label="Loading the register…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && (
				<>
					<div className="mb-4 flex flex-wrap gap-2">
						<Pill tone="page">{total} active volunteers match</Pill>
					</div>

					{rows.length === 0 ? (
						<Empty title="No active volunteers match">
							You see the branches your Geo Assignments cover. If this is empty, either
							nothing here matches what you asked for, there are no active volunteers in
							your scope, or no scope role has been configured yet.
						</Empty>
					) : (
						<>
							<Table head={["Volunteer", "Volunteer number", "Serving branch", "Joined", ""]}>
								{rows.map((row) => (
									<Row key={row.volunteer}>
										<Cell>
											<VolunteerName row={row} />
										</Cell>
										<Cell className="tabular font-mono text-[11.5px] text-slate-faint">
											{row.volunteer}
										</Cell>
										<Cell className="text-muted">{branchPath(row.geo_path)}</Cell>
										<Cell className="text-muted">{formatDate(row.joined_on)}</Cell>
										<Cell className="text-right">
											<Link
												to={recordOf("volunteer", row.volunteer)}
												className="text-[12.5px] font-bold text-ink hover:underline"
											>
												Open
											</Link>
										</Cell>
									</Row>
								))}
							</Table>

							<Pager
								page={page}
								pageCount={Math.max(1, Math.ceil(total / PAGE))}
								total={total}
								noun="volunteers"
								onPage={setPage}
							/>
						</>
					)}
				</>
			)}
		</>
	);
}

/**
 * A volunteer's name, opening onto the summary card.
 *
 * **The dossier is fetched on first open and never on load.** A register of two
 * hundred rows must not be two hundred dossier reads to fill four cards; the
 * SWR key is the volunteer's docname, so the second hover over the same person
 * is free and a hover over somebody new is one call.
 */
function VolunteerName({ row }: { row: VolunteerRow }) {
	return (
		<PersonCard
			label={
				<span className="flex items-center gap-3">
					{/* The face, then the name, then the record number — the order
					    somebody scanning a register actually reads in. A coordinator
					    looking for a person they know finds them by recognising them
					    long before they finish reading a column of similar names. */}
					<Avatar name={row.full_name} photo={row.photo} size={34} />
					<span className="min-w-0">
						<span className="block truncate font-semibold text-ink">{row.full_name}</span>
						<span className="mt-0.5 block text-[11px] text-slate-faint">{row.status}</span>
					</span>
				</span>
			}
		>
			{() => <VolunteerSummary row={row} />}
		</PersonCard>
	);
}

function VolunteerSummary({ row }: { row: VolunteerRow }) {
	const { data, error, isLoading } = useFrappeGetCall<{ message: VolunteerDossier }>(
		API.volunteerDossier,
		{ name: row.volunteer },
		`registry:volunteer:card:${row.volunteer}`,
	);

	const dossier = data?.message;
	const person = dossier?.identity;

	const completed = useMemo(
		// Counted from the roster the server already derived, not from a status
		// comparison here: `is_settled` is the deployment module's own answer to
		// whether somebody's part in a deployment is over.
		() => (dossier?.deployments ?? []).filter((entry) => entry.is_settled).length,
		[dossier],
	);

	const facts: SummaryFact[] = [
		{ label: "Volunteer no.", value: row.volunteer },
		{ label: "Phone", value: person?.phone ?? null },
		{ label: "Joined", value: formatDate(row.joined_on) },
		{
			label: "Service hours",
			value: dossier ? `${dossier.time.total_hours} verified` : null,
		},
		{ label: "Deployments", value: dossier ? `${completed} completed` : null },
	];

	return (
		<PersonSummaryBody
			name={row.full_name}
			photo={row.photo}
			place={branchPath(row.geo_path) || null}
			status={<StateBadge state={row.status} />}
			facts={facts}
			phone={person?.phone}
			email={person?.email}
			loading={isLoading}
			error={
				error
					? "The rest of this person's summary could not be read. Open their record to see it."
					: undefined
			}
			open={{ to: recordOf("volunteer", row.volunteer), label: "Open full record" }}
		/>
	);
}

/* ------------------------------------------------------------------ members */

function Members() {
	const [search, setSearch] = useQueryTerm();
	const [membershipType, setMembershipType] = useState("");
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [page, setPage] = useState(0);

	const types = useFrappeGetCall<{ message: { types: PricedType[] } }>(
		API.membershipTypes,
		undefined,
		"admin:membership_types",
	);

	const summary = useFrappeGetCall<{ message: MemberRegisterSummary }>(
		API.memberRegisterSummary,
		undefined,
		"registry:members:summary",
	);

	const geoNode = chain.length > 0 ? chain[chain.length - 1].name : undefined;
	const branchLabel = branchOf(chain);

	const narrow =
		<T,>(set: (value: T) => void) =>
		(value: T) => {
			set(value);
			setPage(0);
		};

	const { data, error, isLoading } = useFrappeGetCall<{
		message: {
			count: number;
			total: number;
			member_count: number;
			as_of: string;
			rows: MemberRow[];
		};
	}>(
		API.findMembers,
		{
			// Current today, always — the derived status rather than the stored
			// one, so a membership whose validity ran out last night is not listed
			// as active until the nightly sweep notices. Applications, awaiting
			// payment, awaiting approval, expired and cancelled memberships stay in
			// their own workflows.
			current_only: 1,
			limit: PAGE,
			offset: page * PAGE,
			search: search || undefined,
			membership_type: membershipType || undefined,
			geo_node: geoNode,
		},
		`admin:find_members:${page}:${search}:${membershipType}:${geoNode ?? ""}`,
	);

	const message = data?.message;
	const rows = message?.rows ?? [];
	const total = message?.total ?? 0;
	const figures = summary.data?.message;

	return (
		<>
			<SummaryStrip
				loading={summary.isLoading}
				capped={figures?.capped}
				tiles={[
					{ label: "Active memberships", value: figures?.active, hint: "Current as at today" },
					{
						// "Term", not "Annual": a society names its own membership
						// types, and the split is read off `is_lifetime` rather than
						// off a name one society happens to use.
						label: "Term memberships",
						value: figures?.term,
						hint: "Renewable, with an expiry",
					},
					{ label: "Life memberships", value: figures?.lifetime, hint: "No expiry" },
					{
						label: "Renewals approaching",
						value: figures?.renewing,
						hint: figures
							? `Falling due within ${figures.renewal_window_days} days`
							: "Falling due soon",
					},
				]}
			/>

			<RegisterToolbar
				search={search}
				onSearch={narrow(setSearch)}
				placeholder="Search by name or membership number"
				inline={
					<SelectFilter
						label="Membership type"
						value={membershipType}
						onChange={narrow(setMembershipType)}
						any="All membership types"
						options={(types.data?.message?.types ?? []).map((row) => ({
							value: row.membership_type,
							label: row.membership_type_name,
						}))}
					/>
				}
				chips={branchLabel ? [{ key: "branch", label: branchLabel, clear: () => narrow(setChain)([]) }] : []}
				onClearAll={() => {
					setSearch("");
					setMembershipType("");
					setChain([]);
					setPage(0);
				}}
			>
				<Labelled label="Branch" hint="Where the membership is held, and everything under it.">
					<GeoSelects chain={chain} onChain={narrow(setChain)} idPrefix="registry-mem" />
				</Labelled>
			</RegisterToolbar>

			{isLoading && <Spinner label="Loading the register…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && (
				<>
					<div className="mb-4 flex flex-wrap gap-2">
						<Pill tone="page">{total} active memberships match</Pill>
						<Pill tone="page">{message?.member_count ?? 0} people</Pill>
						<Pill tone="page">as at {formatDate(message?.as_of ?? null)}</Pill>
					</div>

					{rows.length === 0 ? (
						<Empty title="No active memberships match">
							You see the branches your Geo Assignments cover. If this is empty, either
							nothing here matches what you asked for, there are no current memberships in
							your scope, or no scope role has been configured yet.
						</Empty>
					) : (
						<>
							<Table head={["Member", "Membership number", "Type", "Branch", "Valid until", ""]}>
								{rows.map((row) => (
									<Row key={row.membership}>
										<Cell>
											<MemberName row={row} />
										</Cell>
										<Cell className="tabular font-mono text-[11.5px] text-slate-faint">
											{row.membership}
										</Cell>
										<Cell>{row.membership_type_name}</Cell>
										<Cell className="text-muted">{branchPath(row.geo_path)}</Cell>
										<Cell className="text-muted">
											{/* A life membership has no expiry, and an empty cell
											    would read as a missing date rather than as the
											    absence of one. */}
											{row.valid_to ? formatDate(row.valid_to) : "No expiry"}
										</Cell>
										<Cell className="text-right">
											<Link
												to={recordOf("member", row.member)}
												className="text-[12.5px] font-bold text-ink hover:underline"
											>
												Open
											</Link>
										</Cell>
									</Row>
								))}
							</Table>

							<Pager
								page={page}
								pageCount={Math.max(1, Math.ceil(total / PAGE))}
								total={total}
								noun="memberships"
								onPage={setPage}
							/>
						</>
					)}
				</>
			)}
		</>
	);
}

function MemberName({ row }: { row: MemberRow }) {
	return (
		<PersonCard
			label={
				<span className="flex items-center gap-3">
					<Avatar name={row.full_name} photo={row.photo} size={34} />
					<span className="min-w-0">
						<span className="block truncate font-semibold text-ink">{row.full_name}</span>
						<span className="mt-0.5 block text-[11px] text-slate-faint">
							{row.membership_type_name}
						</span>
					</span>
				</span>
			}
		>
			{() => <MemberSummary row={row} />}
		</PersonCard>
	);
}

/**
 * The member card's body.
 *
 * **The dossier is the *member's*, not the membership's** — it covers every
 * branch this person holds one at — which is why the card is keyed on
 * `row.member` and the link goes to the person. The membership facts on the
 * card are this row's, because this row is the membership the reader is
 * looking at.
 */
function MemberSummary({ row }: { row: MemberRow }) {
	const { data, error, isLoading } = useFrappeGetCall<{ message: MemberDossier }>(
		API.memberDossier,
		{ name: row.member },
		`registry:member:card:${row.member}`,
	);

	const person = data?.message?.identity;

	const facts: SummaryFact[] = [
		{ label: "Membership no.", value: row.membership },
		{ label: "Phone", value: person?.phone ?? null },
		{ label: "Membership", value: row.membership_type_name },
		{ label: "Member since", value: formatDate(row.valid_from) },
		{ label: "Valid until", value: row.valid_to ? formatDate(row.valid_to) : "No expiry" },
	];

	return (
		<PersonSummaryBody
			name={row.full_name}
			photo={row.photo}
			place={branchPath(row.geo_path) || null}
			status={<StateBadge state={row.effective_status} />}
			facts={facts}
			phone={person?.phone}
			email={person?.email}
			loading={isLoading}
			error={
				error
					? "The rest of this person's summary could not be read. Open their record to see it."
					: undefined
			}
			open={{ to: recordOf("member", row.member), label: "Open full record" }}
		/>
	);
}

/* ------------------------------------------------------------------ shared */

/**
 * Where one person's full record lives.
 *
 * The kind is a path segment because a docname cannot say which register it
 * belongs to, and probing both endpoints to find out would ask the server a
 * question the link already knew.
 */
function recordOf(kind: "volunteer" | "member", name: string): string {
	return `/admin/registry/${kind}/${encodeURIComponent(name)}`;
}

interface SummaryTile {
	label: string;
	/** `undefined` while loading, `null` where the server could not say. */
	value: number | null | undefined;
	hint: string;
}

/**
 * The register's own figures, above the register.
 *
 * **Every one is a scoped server aggregate, and none of them is this page's
 * length.** That distinction is the reason these have their own endpoint: a
 * pager's `total` describes the current filter, and a headline that silently
 * changed when somebody typed in the search box would be believed and wrong.
 */
function SummaryStrip({
	tiles,
	loading,
	capped,
}: {
	tiles: SummaryTile[];
	loading: boolean;
	capped?: boolean;
}) {
	return (
		<div className="mb-5">
			<div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				{tiles.map((tile) => (
					<div key={tile.label} className="rounded-xl border border-card-line bg-white p-4">
						<div className="text-[11px] font-semibold uppercase tracking-[0.06em] text-muted">
							{tile.label}
						</div>
						{loading ? (
							<Skeleton className="mt-2 h-7 w-16" />
						) : (
							<div className="tabular mt-1.5 text-[24px] font-semibold leading-none text-ink">
								{tile.value === null || tile.value === undefined
									? "—"
									: tile.value.toLocaleString()}
							</div>
						)}
						<p className="mt-1.5 text-[11px] text-muted">{tile.hint}</p>
					</div>
				))}
			</div>

			{capped && (
				<p className="mt-2 text-[11px] leading-relaxed text-muted">
					Your scope holds more records than one request can total exactly, so these figures are
					a floor rather than a count. The table below is complete and paged.
				</p>
			)}
		</div>
	);
}

/**
 * The one row of controls a register needs, and a disclosure for the rest.
 *
 * **What was wrong with the old one is worth stating, because it is the common
 * way this goes wrong.** Every control the screen could filter by was laid out
 * at equal weight in one open panel: a search box, two dropdowns, a cascading
 * branch picker and three identical unlabelled combo fields. The panel was the
 * tallest thing on the page, so the register it filtered started below the fold;
 * nothing said which of the three combo fields was which; and with everything
 * always visible there was nowhere for the *answer* — what is currently
 * narrowing this list — to be shown.
 *
 * This is the ordinary arrangement instead, and it is ordinary on purpose:
 *
 *     [ search…                          ] [ dropdown ]      [ Filters (1) ]
 *     Arusha · Arusha City ×                              Clear all
 *
 * **The chips are the part that matters most.** A filter you cannot see is a
 * filter you forget you set, and "why is this list empty" is almost always
 * something somebody ticked ten minutes ago.
 */
function RegisterToolbar({
	search,
	onSearch,
	placeholder,
	inline,
	chips,
	onClearAll,
	children,
}: {
	search: string;
	onSearch: (value: string) => void;
	placeholder: string;
	inline?: ReactNode;
	chips: Array<{ key: string; label: string; clear: () => void }>;
	onClearAll: () => void;
	children: ReactNode;
}) {
	// Opens when something is already in it, so somebody arriving on a page that
	// carries filters is not shown a collapsed box hiding the reason their list
	// is short. After that it is theirs to open and close.
	const [open, setOpen] = useState(chips.length > 0);

	return (
		<Card className="mb-5">
			<div className="flex flex-wrap items-center gap-2.5">
				<div className="relative min-w-[220px] flex-1">
					<span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-faint">
						<Icon.search size={15} />
					</span>
					<input
						type="search"
						value={search}
						onChange={(event) => onSearch(event.target.value)}
						placeholder={placeholder}
						aria-label={placeholder}
						className="w-full rounded-full border border-card-line bg-white py-2.5 pl-11 pr-4 text-[13.5px] outline-none transition placeholder:text-slate-faint focus:border-blue"
					/>
				</div>

				{inline}

				<button
					type="button"
					onClick={() => setOpen((was) => !was)}
					aria-expanded={open}
					className={cx(
						"inline-flex items-center gap-2 rounded-full border px-4 py-2.5 text-[12.5px] font-bold transition",
						open || chips.length > 0
							? "border-blue bg-blue-soft text-blue-press"
							: "border-card-line bg-white text-slate-strong hover:border-blue hover:text-ink",
					)}
				>
					<Icon.filter size={15} />
					Filters
					{chips.length > 0 && (
						<span className="tabular rounded-full bg-rail px-1.5 py-0.5 text-[10px] leading-none text-white">
							{chips.length}
						</span>
					)}
				</button>
			</div>

			{open && <div className="mt-5 space-y-5 border-t border-card-line pt-5">{children}</div>}

			{chips.length > 0 && (
				<div className="mt-4 flex flex-wrap items-center gap-1.5 border-t border-card-line pt-4">
					<span className="mr-1 text-[11px] font-bold uppercase tracking-wide text-slate-faint">
						Showing
					</span>
					{chips.map((chip) => (
						<button
							key={chip.key}
							type="button"
							onClick={chip.clear}
							className="group inline-flex items-center gap-1.5 rounded-full border border-blue/25 bg-blue-soft py-1 pl-3 pr-2 text-[12px] font-semibold text-blue-press transition hover:border-blue/50"
						>
							{chip.label}
							<span
								aria-hidden="true"
								className="grid h-3.5 w-3.5 place-items-center rounded-full bg-rail/15 transition group-hover:bg-rail group-hover:text-white"
							>
								<Icon.cross size={9} />
							</span>
							<span className="sr-only">Remove this filter</span>
						</button>
					))}
					<button
						type="button"
						onClick={onClearAll}
						className="ml-1 text-[12px] font-semibold text-slate-faint underline underline-offset-2 transition hover:text-blue-press"
					>
						Clear all
					</button>
				</div>
			)}
		</Card>
	);
}

/**
 * A dropdown that names itself when nothing is chosen.
 *
 * The "any" option carries the filter's own word — "All membership types", not
 * "All" — so an unset dropdown still reads as a question rather than as a box
 * saying All.
 */
function SelectFilter({
	label,
	value,
	onChange,
	any,
	options,
}: {
	label: string;
	value: string;
	onChange: (value: string) => void;
	any: string;
	options: Array<{ value: string; label: string | null }>;
}) {
	return (
		<label className="relative">
			<span className="sr-only">{label}</span>
			<select
				value={value}
				onChange={(event) => onChange(event.target.value)}
				className={cx(
					"appearance-none rounded-full border bg-white py-2.5 pl-4 pr-9 text-[13.5px] outline-none transition",
					value
						? "border-blue bg-blue-soft font-semibold text-blue-press"
						: "border-card-line text-slate-strong hover:border-blue",
				)}
			>
				<option value="">{any}</option>
				{options.map((option) => (
					<option key={option.value} value={option.value}>
						{option.label ?? option.value}
					</option>
				))}
			</select>
			<svg
				viewBox="0 0 24 24"
				width="13"
				height="13"
				fill="none"
				aria-hidden="true"
				className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-faint"
			>
				<path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
			</svg>
		</label>
	);
}

/** A heading and one line of guidance over a control that needs both. */
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
		<div>
			<span className="block text-[12.5px] font-semibold text-slate-strong">{label}</span>
			{hint && <span className="mb-2 block text-[11.5px] text-slate-faint">{hint}</span>}
			<div className={hint ? "" : "mt-2"}>{children}</div>
		</div>
	);
}

/**
 * The chosen branch, without the society's own name at the head of it.
 *
 * The same rule `format.ts::branchPath` applies to a rendered path: inside this
 * console every record belongs to one society, so naming it in a filter chip
 * spends the width of the chip saying nothing. The crown stays on when there is
 * nothing under it.
 */
function branchOf(chain: GeoNode[]): string {
	return (chain.length > 1 ? chain.slice(1) : chain).map((node) => node.label).join(" · ");
}
