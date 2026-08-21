import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
// `branchPath` rather than `geoPath` in the rows below: every record in this
// console belongs to the same society, so repeating its name down a column
// spends the width of the column saying the one thing that is true of all of
// them. See the helper's own docstring.
import { branchPath, formatDate } from "../lib/format";
import { MultiCombo } from "../ui/form";
import { GeoSelects } from "../ui/GeoSelects";
import { Icon } from "../ui/icons";
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
	Spinner,
	StateBadge,
	Table,
	cx,
} from "../ui/primitives";
import type { ApplicationOptions, GeoNode, PricedType } from "../portal/types";

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
	geo_node: string | null;
	geo_path: string | null;
	deployable: boolean;
}

/** One page of a register. Server-side, so it is not a slice of a capped read. */
const PAGE = 25;

/**
 * Who this coordinator is responsible for — two registers, two routed pages.
 *
 * **Nothing on either page filters by branch, and nothing needs to.** Both
 * endpoints end in `frappe.get_list`, which runs core's permission query
 * condition, so the caller's geo scope is the floor the query stands on rather
 * than something this screen applies on top. A coordinator sees their own
 * branches because of who they are, not because of a parameter the browser
 * sent, and there is consequently no filter here that could be tampered with to
 * widen the result.
 *
 * An empty registry for somebody with no scope is therefore the correct render,
 * not a failure state.
 *
 * **Every control below narrows and none of them widens**, which is the same
 * property stated from the other side: the branch picker names a node *within*
 * the caller's scope, and naming one outside it returns nothing rather than
 * reaching it. That is enforced server-side in `capabilities.search` and
 * `register.search`; this screen could not widen the result if it tried to.
 *
 * **Paging is the server's.** Each page is its own scoped read and `total`
 * comes back with it, so the pager is honest about registers larger than one
 * screen rather than silently capping at whatever the first read returned.
 *
 * **Members and Volunteers used to be one screen with a toggle between them.**
 * They are two routed pages now, each its own sidebar entry under People &
 * Insight, because a coordinator who only ever checks the volunteer roster
 * should be able to link or bookmark that and skip the membership list every
 * time it loads. Splitting the route cost nothing either register's own filter
 * state didn't already have on its own — the two never shared any.
 */
export function MembersRegistry() {
	return (
		<>
			<PageHeading title={<EditableText k="admin.registry.members.heading" fallback="Members" />} />
			<Members />
		</>
	);
}

export function VolunteersRegistry() {
	return (
		<>
			<PageHeading
				title={<EditableText k="admin.registry.volunteers.heading" fallback="Volunteers" />}
			/>
			<Volunteers />
		</>
	);
}

/* --------------------------------------------------------------- volunteers */

function Volunteers() {
	const [search, setSearch] = useState("");
	const [skills, setSkills] = useState<string[]>([]);
	const [languages, setLanguages] = useState<string[]>([]);
	const [availability, setAvailability] = useState<string[]>([]);
	const [status, setStatus] = useState("");
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [page, setPage] = useState(0);

	// The society's own vocabularies, drawn from the same endpoint the join
	// wizard uses. Nothing here writes down what a skill is.
	const options = useFrappeGetCall<{ message: ApplicationOptions }>(
		API.applicationOptions,
		undefined,
		"admin:application_options",
	);

	const geoNode = chain.length > 0 ? chain[chain.length - 1].name : undefined;
	const branchLabel = branchOf(chain);

	/** Any change to the criteria puts the reader back on the first page.
	 *
	 * Somebody on page three who narrows a filter to four results must not be
	 * left staring at an empty page three — the bug every hand-rolled pager
	 * eventually has. `usePaged` guards it for client-side lists; paging on the
	 * server means guarding it here.
	 */
	const narrow = <T,>(set: (value: T) => void) => (value: T) => {
		set(value);
		setPage(0);
	};

	const { data, error, isLoading } = useFrappeGetCall<{
		message: { count: number; total: number; volunteers: VolunteerRow[] };
	}>(
		API.findVolunteers,
		{
			limit: PAGE,
			offset: page * PAGE,
			search: search || undefined,
			skills: skills.length ? skills : undefined,
			languages: languages.length ? languages : undefined,
			availability: availability.length ? availability : undefined,
			status: status || undefined,
			geo_node: geoNode,
		},
		`admin:find_volunteers:${page}:${search}:${status}:${geoNode ?? ""}:${skills.join()}:${languages.join()}:${availability.join()}`,
	);

	const rows = data?.message.volunteers ?? [];
	const total = data?.message.total ?? 0;

	return (
		<>
			<FilterBar
				search={
					<SearchInput
						value={search}
						onChange={narrow(setSearch)}
						placeholder="Search by name or record number"
					/>
				}
				inline={
					<SelectFilter
						label="Standing"
						value={status}
						onChange={narrow(setStatus)}
						any="Any standing"
						options={["Prospective", "Active", "Suspended", "Exited"]}
					/>
				}
				extra={
					skills.length +
					languages.length +
					availability.length +
					(chain.length > 1 ? 1 : 0)
				}
				chips={[
					...(branchLabel ? [{ key: "branch", label: branchLabel, clear: () => narrow(setChain)([]) }] : []),
					...chipsFor(skills, options.data?.message.skills, (key) =>
						narrow(setSkills)(skills.filter((s) => s !== key)),
					),
					...chipsFor(languages, options.data?.message.languages, (key) =>
						narrow(setLanguages)(languages.filter((s) => s !== key)),
					),
					...chipsFor(availability, options.data?.message.availability, (key) =>
						narrow(setAvailability)(availability.filter((s) => s !== key)),
					),
				]}
				onClearAll={() => {
					setSearch("");
					setStatus("");
					setChain([]);
					setSkills([]);
					setLanguages([]);
					setAvailability([]);
					setPage(0);
				}}
			>
				<Labelled
					label="Branch"
					hint="Their serving branch, and everything under it."
				>
					{/* One select per rung of the society's own ladder. This screen does
					    not know how deep the hierarchy is or what a rung is called. */}
					<GeoSelects chain={chain} onChain={narrow(setChain)} idPrefix="registry-vol" />
				</Labelled>

				{/* Each one labelled and told what it searches. These were three
				    identical unlabelled search boxes in a row, which is a control
				    you have to click to find out what it is. */}
				<div className="grid gap-5 sm:grid-cols-3">
					<Labelled label="Skills" hint="Any of the ones you pick.">
						<MultiCombo
							label="Skills"
							placeholder="Search skills…"
							options={options.data?.message.skills ?? []}
							selected={skills}
							onToggle={(key) =>
								narrow(setSkills)(
									skills.includes(key) ? skills.filter((s) => s !== key) : [...skills, key],
								)
							}
						/>
					</Labelled>
					<Labelled label="Languages" hint="Any of the ones you pick.">
						<MultiCombo
							label="Languages"
							placeholder="Search languages…"
							options={options.data?.message.languages ?? []}
							selected={languages}
							onToggle={(key) =>
								narrow(setLanguages)(
									languages.includes(key)
										? languages.filter((s) => s !== key)
										: [...languages, key],
								)
							}
						/>
					</Labelled>
					<Labelled label="Available" hint="Any of the slots you pick.">
						<MultiCombo
							label="Availability"
							placeholder="Search times…"
							options={options.data?.message.availability ?? []}
							selected={availability}
							onToggle={(key) =>
								narrow(setAvailability)(
									availability.includes(key)
										? availability.filter((s) => s !== key)
										: [...availability, key],
								)
							}
						/>
					</Labelled>
				</div>

				{/* Any-of within a vocabulary and all-of across them, which is what a
				    coordinator staffing something means. Said on the page because it
				    is not guessable from three controls that look alike. */}
				<p className="text-[12px] leading-relaxed text-slate-faint">
					A volunteer matches if they hold any of the skills asked for, <b>and</b> any of
					the languages, <b>and</b> any of the slots.
				</p>
			</FilterBar>

			{isLoading && <Spinner label="Loading the registry…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && (
				<>
					<div className="mb-4 flex flex-wrap gap-2">
						<Pill tone="page">{total} volunteers</Pill>
					</div>

					{rows.length === 0 ? (
						<Empty title="No volunteers match">
							You see the branches your Geo Assignments cover. If this is empty, either
							nothing here matches what you asked for, there are no volunteers in your
							scope, or no scope role has been configured yet.
						</Empty>
					) : (
						<>
							<Table head={["Name", "Serving branch", "Deployable", "Status"]}>
								{rows.map((row) => (
									<Row key={row.volunteer}>
										<Cell>
											{/* The face, then the name, then the record number —
											    the order somebody scanning a register actually
											    reads in. A coordinator looking for a person they
											    know finds them by recognising them long before
											    they finish reading a column of similar names,
											    and this column is the only one on the page that
											    could offer that. */}
											<Link
												to={`/admin/registry/volunteer/${encodeURIComponent(row.volunteer)}`}
												className="group flex items-center gap-3"
											>
												<Avatar name={row.full_name} photo={row.photo} size={34} />
												<span className="min-w-0">
													<span className="block truncate font-semibold text-ink group-hover:text-navy group-hover:underline">
														{row.full_name}
													</span>
													<span className="tabular mt-0.5 block font-mono text-[11px] text-slate-faint">
														{row.volunteer}
													</span>
												</span>
											</Link>
										</Cell>
										<Cell className="text-slate-body">{branchPath(row.geo_path)}</Cell>
										<Cell>
											{row.deployable ? (
												<span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-bold text-emerald-700">
													Ready
												</span>
											) : (
												<span className="rounded-full border border-hairline-strong bg-white px-2.5 py-1 text-[11px] font-bold text-slate-body">
													Blocked
												</span>
											)}
										</Cell>
										<Cell>
											<StateBadge state={row.status} />
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

/* ------------------------------------------------------------------ members */

function Members() {
	const [status, setStatus] = useState("");
	const [membershipType, setMembershipType] = useState("");
	const [currentOnly, setCurrentOnly] = useState(false);
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [page, setPage] = useState(0);

	const types = useFrappeGetCall<{ message: { types: PricedType[] } }>(
		API.membershipTypes,
		undefined,
		"admin:membership_types",
	);

	const geoNode = chain.length > 0 ? chain[chain.length - 1].name : undefined;
	const branchLabel = branchOf(chain);

	const narrow = <T,>(set: (value: T) => void) => (value: T) => {
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
			limit: PAGE,
			offset: page * PAGE,
			status: status || undefined,
			membership_type: membershipType || undefined,
			current_only: currentOnly,
			geo_node: geoNode,
		},
		`admin:find_members:${page}:${status}:${membershipType}:${currentOnly}:${geoNode ?? ""}`,
	);

	const message = data?.message;
	const rows = message?.rows ?? [];
	const total = message?.total ?? 0;

	return (
		<>
			<FilterBar
				inline={
					<>
						<SelectFilter
							label="Type"
							value={membershipType}
							onChange={narrow(setMembershipType)}
							any="Any type"
							options={(types.data?.message.types ?? []).map((row) => ({
								value: row.membership_type,
								label: row.membership_type_name,
							}))}
						/>
						<SelectFilter
							label="Recorded status"
							value={status}
							onChange={narrow(setStatus)}
							any="Any status"
							options={[
								"Draft",
								"Awaiting Payment",
								"Awaiting Approval",
								"Active",
								"Expired",
								"Cancelled",
							]}
						/>
						{/* Recorded status is what the database holds; current is
						    derived as at today. They answer different questions, so
						    both are offered — and this one is a toggle rather than a
						    tick-box in a corner, because it is the filter a
						    membership office reaches for most. */}
						<Toggle
							label="Current today"
							on={currentOnly}
							onChange={narrow(setCurrentOnly)}
						/>
					</>
				}
				extra={chain.length > 1 ? 1 : 0}
				chips={
					branchLabel
						? [{ key: "branch", label: branchLabel, clear: () => narrow(setChain)([]) }]
						: []
				}
				onClearAll={() => {
					setStatus("");
					setMembershipType("");
					setCurrentOnly(false);
					setChain([]);
					setPage(0);
				}}
			>
				<Labelled label="Branch" hint="Where the membership is held, and everything under it.">
					<GeoSelects chain={chain} onChain={narrow(setChain)} idPrefix="registry-mem" />
				</Labelled>
			</FilterBar>

			{isLoading && <Spinner label="Loading the registry…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && (
				<>
					<div className="mb-4 flex flex-wrap gap-2">
						<Pill tone="page">{total} memberships</Pill>
						<Pill tone="page">{message?.member_count ?? 0} people</Pill>
						<Pill tone="page">as of {formatDate(message?.as_of ?? null)}</Pill>
					</div>

					{rows.length === 0 ? (
						<Empty title="No memberships match">
							You see the branches your Geo Assignments cover. If this is empty, either
							nothing here matches what you asked for, there are no memberships in your
							scope, or no scope role has been configured yet.
						</Empty>
					) : (
						<>
							<Table head={["Name", "Type", "Branch", "Valid to", "Status"]}>
								{rows.map((row) => (
									<Row key={row.membership}>
										<Cell>
											{/* The dossier is the *member's*, not the membership's:
											    it covers every branch this person holds a membership
											    at, so the link names the person. The face is here
											    for the same reason it is on the volunteer register
											    — see the note there. */}
											<Link
												to={`/admin/registry/member/${encodeURIComponent(row.member)}`}
												className="group flex items-center gap-3"
											>
												<Avatar name={row.full_name} photo={row.photo} size={34} />
												<span className="min-w-0">
													<span className="block truncate font-semibold text-ink group-hover:text-navy group-hover:underline">
														{row.full_name}
													</span>
													<span className="tabular mt-0.5 block font-mono text-[11px] text-slate-faint">
														{row.membership}
													</span>
												</span>
											</Link>
										</Cell>
										<Cell>{row.membership_type_name}</Cell>
										<Cell className="text-slate-body">{branchPath(row.geo_path)}</Cell>
										<Cell className="text-slate-body">{formatDate(row.valid_to)}</Cell>
										<Cell>
											<StateBadge state={row.effective_status} />
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

/* ----------------------------------------------------------------- filters */

/**
 * The filter bar both registers use.
 *
 * **What was wrong with the old one is worth stating, because it is the common
 * way this goes wrong.** Every control a screen could filter by was laid out at
 * equal weight in one open panel: a search box, two dropdowns, a cascading
 * branch picker and three identical unlabelled search fields. Three problems
 * followed. The panel was the tallest thing on the page, so the register it
 * filtered started below the fold. Nothing said which of the three search
 * fields was which, so you had to click one to find out. And with everything
 * always visible there was nowhere for the *answer* — what is currently
 * narrowing this list — to be shown, so the only way to know was to read all
 * seven controls.
 *
 * This is the ordinary arrangement instead, and it is ordinary on purpose:
 *
 *     [ search…                    ] [ dropdown ] [ dropdown ]  [ Filters (2) ]
 *     Arusha · Arusha City ×   Nursing ×   Swahili ×        Clear all
 *
 * One row of the two or three controls people use constantly; everything else
 * behind a disclosure that says how many filters are hiding in it; and a line
 * of chips underneath that is the standing answer to "what am I looking at",
 * each of which removes itself.
 *
 * **The chips are the part that matters most.** A filter you cannot see is a
 * filter you forget you set, and "why is this list empty" is almost always a
 * skill somebody ticked ten minutes ago.
 */
function FilterBar({
	search,
	inline,
	extra,
	chips,
	onClearAll,
	children,
}: {
	/** The search field, when the register behind this has one. */
	search?: ReactNode;
	/** The one or two controls that stay visible. */
	inline?: ReactNode;
	/** How many filters are set inside the disclosure, for its badge. */
	extra: number;
	chips: Array<{ key: string; label: string; clear: () => void }>;
	onClearAll: () => void;
	/** Everything behind the disclosure. */
	children: ReactNode;
}) {
	// Opens when there is something in it, so somebody arriving on a page that
	// already carries filters is not shown a collapsed box hiding the reason
	// their list is short. After that it is theirs to open and close.
	const [open, setOpen] = useState(extra > 0);

	return (
		<Card className="mb-5">
			<div className="flex flex-wrap items-center gap-2.5">
				{search && <div className="min-w-[220px] flex-1">{search}</div>}
				{inline}

				<button
					type="button"
					onClick={() => setOpen((was) => !was)}
					aria-expanded={open}
					className={cx(
						"inline-flex items-center gap-2 rounded-full border px-4 py-2.5 font-display text-[12.5px] font-bold transition",
						open || extra > 0
							? "border-navy bg-navy/[.06] text-navy"
							: "border-hairline-strong bg-white text-slate-strong hover:border-navy hover:text-navy",
					)}
				>
					<Icon.filter size={15} />
					Filters
					{extra > 0 && (
						<span className="tabular rounded-full bg-navy px-1.5 py-0.5 text-[10px] leading-none text-white">
							{extra}
						</span>
					)}
					<svg
						viewBox="0 0 24 24"
						width="13"
						height="13"
						fill="none"
						aria-hidden="true"
						className={cx("transition-transform", open && "rotate-180")}
					>
						<path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
					</svg>
				</button>
			</div>

			{open && (
				<div className="mt-5 space-y-5 border-t border-hairline pt-5">{children}</div>
			)}

			{chips.length > 0 && (
				<div className="mt-4 flex flex-wrap items-center gap-1.5 border-t border-hairline pt-4">
					<span className="mr-1 text-[11px] font-bold uppercase tracking-wide text-slate-faint">
						Showing
					</span>
					{chips.map((chip) => (
						<button
							key={chip.key}
							type="button"
							onClick={chip.clear}
							className="group inline-flex items-center gap-1.5 rounded-full border border-navy/25 bg-navy/[0.06] py-1 pl-3 pr-2 text-[12px] font-semibold text-navy transition hover:border-navy/50 hover:bg-navy/10"
						>
							{chip.label}
							<span
								aria-hidden="true"
								className="grid h-3.5 w-3.5 place-items-center rounded-full bg-navy/15 transition group-hover:bg-navy group-hover:text-white"
							>
								<Icon.cross size={9} />
							</span>
							<span className="sr-only">Remove this filter</span>
						</button>
					))}
					<button
						type="button"
						onClick={onClearAll}
						className="ml-1 text-[12px] font-semibold text-slate-faint underline underline-offset-2 transition hover:text-signal-dark"
					>
						Clear all
					</button>
				</div>
			)}
		</Card>
	);
}

/** The search field, with the magnifier that says what it is without a label. */
function SearchInput({
	value,
	onChange,
	placeholder,
}: {
	value: string;
	onChange: (value: string) => void;
	placeholder: string;
}) {
	return (
		<div className="relative">
			<span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-faint">
				<Icon.search size={15} />
			</span>
			<input
				type="search"
				value={value}
				onChange={(event) => onChange(event.target.value)}
				placeholder={placeholder}
				className="w-full rounded-full border border-hairline-strong bg-white py-2.5 pl-11 pr-4 text-[13.5px] outline-none transition placeholder:text-slate-faint focus:border-navy"
			/>
		</div>
	);
}

/**
 * A dropdown that names itself when nothing is chosen.
 *
 * The "Any" option carries the filter's own word — "Any standing", not "Any" —
 * so a bar of two unset dropdowns still reads as two questions rather than as
 * two identical boxes saying Any. When something *is* chosen the value is the
 * label, which is the state a filter bar spends most of its life in.
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
	options: Array<string | { value: string; label: string | null }>;
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
						? "border-navy bg-navy/[.06] font-semibold text-navy"
						: "border-hairline-strong text-slate-strong hover:border-navy",
				)}
			>
				<option value="">{any}</option>
				{options.map((option) => {
					const key = typeof option === "string" ? option : option.value;
					const text = typeof option === "string" ? option : (option.label ?? option.value);

					return (
						<option key={key} value={key}>
							{text}
						</option>
					);
				})}
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

/** A yes/no filter, as a pill that is plainly on or off. */
function Toggle({
	label,
	on,
	onChange,
}: {
	label: string;
	on: boolean;
	onChange: (on: boolean) => void;
}) {
	return (
		<button
			type="button"
			aria-pressed={on}
			onClick={() => onChange(!on)}
			className={cx(
				"inline-flex items-center gap-2 rounded-full border px-4 py-2.5 font-display text-[12.5px] font-bold transition",
				on
					? "border-navy bg-navy text-white"
					: "border-hairline-strong bg-white text-slate-strong hover:border-navy hover:text-navy",
			)}
		>
			{on && <Icon.check size={13} />}
			{label}
		</button>
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

/** Chosen vocabulary keys as removable chips, labelled from the vocabulary. */
function chipsFor(
	selected: string[],
	options: Array<{ key: string; label: string }> | undefined,
	remove: (key: string) => void,
): Array<{ key: string; label: string; clear: () => void }> {
	return selected.map((key) => ({
		key,
		// The key is the fallback rather than nothing: a chip with no words is a
		// filter somebody cannot identify well enough to decide whether to drop.
		label: options?.find((option) => option.key === key)?.label ?? key,
		clear: () => remove(key),
	}));
}
