import { useState } from "react";
import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, geoPath } from "../lib/format";
import { MultiCombo } from "../ui/form";
import { GeoSelects } from "../ui/GeoSelects";
import {
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
	status: string;
	geo_node: string | null;
	geo_path: string | null;
	deployable: boolean;
}

type Tab = "members" | "volunteers";

/** One page of a register. Server-side, so it is not a slice of a capped read. */
const PAGE = 25;

/**
 * Who this coordinator is responsible for.
 *
 * **Nothing on this page filters by branch, and nothing needs to.** Both
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
 */
export default function Registry() {
	const [tab, setTab] = useState<Tab>("members");

	return (
		<>
			<PageHeading
				title={<EditableText k="admin.registry.heading" fallback="Registry" />}
				actions={
					<div className="flex gap-2">
						{(["members", "volunteers"] as Tab[]).map((id) => (
							<button
								key={id}
								type="button"
								onClick={() => setTab(id)}
								className={cx(
									"whitespace-nowrap rounded-full px-4 py-2 text-[12px] font-semibold capitalize transition",
									tab === id
										? "bg-ink text-white"
										: "border border-hairline-strong bg-white text-slate-strong hover:border-navy",
								)}
							>
								{id}
							</button>
						))}
					</div>
				}
			/>

			{/* Mounted one at a time so each tab's filter state is its own and a
			    coordinator switching back does not inherit the other's criteria. */}
			{tab === "members" ? <Members /> : <Volunteers /> }
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
			<Card className="mb-5">
				<div className="grid gap-4 sm:grid-cols-2">
					<label className="block">
						<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
							Search by name
						</span>
						<input
							type="search"
							value={search}
							onChange={(event) => narrow(setSearch)(event.target.value)}
							placeholder="A person's name, or a volunteer's record number"
							className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
						/>
					</label>

					<label className="block">
						<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
							Standing
						</span>
						<select
							value={status}
							onChange={(event) => narrow(setStatus)(event.target.value)}
							className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
						>
							<option value="">Any</option>
							{["Prospective", "Active", "Suspended", "Exited"].map((value) => (
								<option key={value} value={value}>
									{value}
								</option>
							))}
						</select>
					</label>
				</div>

				<div className="mt-4">
					<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
						Branch
					</span>
					{/* One select per rung of the society's own ladder. This screen does
					    not know how deep the hierarchy is or what a rung is called. */}
					<GeoSelects chain={chain} onChain={narrow(setChain)} idPrefix="registry-vol" />
				</div>

				<div className="mt-4 grid gap-4 sm:grid-cols-3">
					<MultiCombo
						label="Skills"
						options={options.data?.message.skills ?? []}
						selected={skills}
						onToggle={(key) =>
							narrow(setSkills)(
								skills.includes(key) ? skills.filter((s) => s !== key) : [...skills, key],
							)
						}
					/>
					<MultiCombo
						label="Languages"
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
					<MultiCombo
						label="Availability"
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
				</div>

				{/* Any-of within a vocabulary and all-of across them, which is what a
				    coordinator staffing something means. Said on the page because it
				    is not guessable from three identical-looking controls. */}
				<p className="mt-3 text-[12px] text-slate-faint">
					A volunteer matches if they hold any of the skills asked for, and any of the
					languages, and any of the slots.
				</p>
			</Card>

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
											<Link
												to={`/admin/registry/volunteer/${encodeURIComponent(row.volunteer)}`}
												className="font-semibold text-ink hover:text-navy hover:underline"
											>
												{row.full_name}
											</Link>
											<span className="mt-0.5 block font-mono text-[11px] text-slate-faint">
												{row.volunteer}
											</span>
										</Cell>
										<Cell className="text-slate-body">{geoPath(row.geo_path)}</Cell>
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
			<Card className="mb-5">
				<div className="grid gap-4 sm:grid-cols-2">
					<label className="block">
						<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
							Membership type
						</span>
						<select
							value={membershipType}
							onChange={(event) => narrow(setMembershipType)(event.target.value)}
							className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
						>
							<option value="">Any</option>
							{(types.data?.message.types ?? []).map((row) => (
								<option key={row.membership_type} value={row.membership_type}>
									{row.membership_type_name}
								</option>
							))}
						</select>
					</label>

					<label className="block">
						<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
							Recorded status
						</span>
						<select
							value={status}
							onChange={(event) => narrow(setStatus)(event.target.value)}
							className="w-full rounded-card border border-hairline-strong px-3 py-2 text-[14px]"
						>
							<option value="">Any</option>
							{["Draft", "Awaiting Payment", "Awaiting Approval", "Active", "Expired", "Cancelled"].map(
								(value) => (
									<option key={value} value={value}>
										{value}
									</option>
								),
							)}
						</select>
					</label>
				</div>

				<div className="mt-4">
					<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
						Branch
					</span>
					<GeoSelects chain={chain} onChain={narrow(setChain)} idPrefix="registry-mem" />
				</div>

				<label className="mt-4 flex items-center gap-2 text-[13px] text-slate-body">
					<input
						type="checkbox"
						checked={currentOnly}
						onChange={(event) => narrow(setCurrentOnly)(event.target.checked)}
					/>
					{/* Recorded status is what the database holds; current is derived as
					    at today. They answer different questions, so both are offered. */}
					Only memberships that are current today
				</label>
			</Card>

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
											    at, so the link names the person. */}
											<Link
												to={`/admin/registry/member/${encodeURIComponent(row.member)}`}
												className="font-semibold text-ink hover:text-navy hover:underline"
											>
												{row.full_name}
											</Link>
											<span className="mt-0.5 block font-mono text-[11px] text-slate-faint">
												{row.membership}
											</span>
										</Cell>
										<Cell>{row.membership_type_name}</Cell>
										<Cell className="text-slate-body">{geoPath(row.geo_path)}</Cell>
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
