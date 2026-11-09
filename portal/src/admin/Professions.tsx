import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { branchPath } from "../lib/format";
import { Icon } from "../ui/icons";
import { SearchField } from "../ui/patterns";
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
	Table,
} from "../ui/primitives";

/**
 * What a branch's people do: every profession held in the caller's area, with
 * how many active volunteers and current members hold it.
 *
 * **Counts first, names one click away.** The list answers "what skills do we
 * have"; a profession's own page answers "who are they". Both read
 * `api/professions.py`, which stands on the same scoped listings as the
 * registers, so a County Coordinator sees their county and nothing wider.
 *
 * **Short by default.** The busiest professions are shown, and the rest are a
 * search or a "show all" away — a register can hold hundreds, and a page of
 * hundreds is a list to scroll rather than an answer.
 */

interface ProfessionRow {
	profession: string;
	volunteers: number;
	members: number;
	total: number;
}

interface ProfessionSummary {
	professions: ProfessionRow[];
	without: number;
	people: number;
}

interface ProfessionPerson {
	red_profile: string;
	full_name: string;
	photo: string | null;
	volunteer: string | null;
	member: string | null;
	geo_path: string | null;
}

const SHOWN_AT_FIRST = 15;
const PAGE = 25;

export function professionRoute(profession: string): string {
	return `/admin/registry/professions/${encodeURIComponent(profession)}`;
}

export default function Professions() {
	const [search, setSearch] = useState("");
	const [showAll, setShowAll] = useState(false);
	const { data, error, isLoading } = useFrappeGetCall<{ message: ProfessionSummary }>(
		API.professionSummary,
		undefined,
		"admin:professions:summary",
	);

	const summary = data?.message;
	const rows = summary?.professions ?? [];
	const needle = search.trim().toLowerCase();
	const matching = needle ? rows.filter((row) => row.profession.toLowerCase().includes(needle)) : rows;
	const shown = needle || showAll ? matching : matching.slice(0, SHOWN_AT_FIRST);
	const largest = rows[0]?.total ?? 0;

	return (
		<>
			<PageHeading
				title="Professions"
				lead="What your active volunteers and members do. Choose a profession to see who holds it."
				trail={[{ label: "People", to: "/admin/people" }, { label: "Professions" }]}
				actions={
					summary && (
						<div className="flex flex-wrap items-center gap-2">
							<Pill tone="navy">
								{rows.length} {rows.length === 1 ? "profession" : "professions"}
							</Pill>
							<Pill tone="quiet">{summary.people} people</Pill>
						</div>
					)
				}
			/>

			{isLoading && <Spinner label="Counting professions…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{summary && (
				<>
					<SearchField
						className="mb-5 max-w-md"
						label="Find a profession"
						placeholder="Find a profession"
						value={search}
						onChange={setSearch}
					/>

					{rows.length === 0 ? (
						<Empty title="No professions recorded yet">
							None of the people in your area has given a profession.
						</Empty>
					) : shown.length === 0 ? (
						<Empty title={`No profession matches “${search.trim()}”.`} />
					) : (
						<Table head={["Profession", "Volunteers", "Members", "People"]}>
							{shown.map((row) => (
								<Row
									key={row.profession}
									to={professionRoute(row.profession)}
									label={`Open ${row.profession}`}
								>
									<Cell>
										<Link
											to={professionRoute(row.profession)}
											className="font-semibold text-ink hover:underline"
										>
											{row.profession}
										</Link>
									</Cell>
									<Cell className="tabular text-muted">{row.volunteers}</Cell>
									<Cell className="tabular text-muted">{row.members}</Cell>
									<Cell>
										<span className="flex items-center gap-3">
											<span className="tabular w-8 font-semibold text-ink">{row.total}</span>
											<span
												aria-hidden="true"
												className="hidden h-1.5 w-32 overflow-hidden rounded-full bg-surface sm:block"
											>
												<span
													className="block h-full rounded-full bg-blue"
													style={{ width: `${largest ? (row.total / largest) * 100 : 0}%` }}
												/>
											</span>
										</span>
									</Cell>
								</Row>
							))}
						</Table>
					)}

					<div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-[12.5px] text-muted">
						<span>
							{summary.without > 0 &&
								`${summary.without} ${summary.without === 1 ? "person has" : "people have"} not given a profession.`}
						</span>
						{!needle && matching.length > SHOWN_AT_FIRST && (
							<button
								type="button"
								onClick={() => setShowAll((value) => !value)}
								className="font-semibold text-ink hover:underline"
							>
								{showAll ? "Show the top professions only" : `Show all ${matching.length} professions`}
							</button>
						)}
					</div>
				</>
			)}
		</>
	);
}

/** The people in the caller's area who hold one profession. */
export function ProfessionPeople() {
	const { profession = "" } = useParams<{ profession: string }>();
	const [search, setSearch] = useState("");
	const [offset, setOffset] = useState(0);
	useEffect(() => setOffset(0), [profession, search]);

	const { data, error, isLoading } = useFrappeGetCall<{
		message: { profession: string; total: number; people: ProfessionPerson[] };
	}>(
		API.professionPeople,
		{ profession, search: search.trim() || undefined, limit: PAGE, offset },
		`admin:professions:people:${profession}:${search.trim()}:${offset}`,
	);

	const answer = data?.message;
	const people = answer?.people ?? [];

	return (
		<>
			<Link
				to="/admin/registry/professions"
				className="mb-3 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-ink hover:underline"
			>
				<Icon.back size={14} />
				All professions
			</Link>

			<PageHeading
				title={profession}
				lead="Active volunteers and members in your area who gave this profession."
				trail={[
					{ label: "People", to: "/admin/people" },
					{ label: "Professions", to: "/admin/registry/professions" },
					{ label: profession },
				]}
				actions={
					answer && (
						<Pill tone="navy">
							{answer.total} {answer.total === 1 ? "person" : "people"}
						</Pill>
					)
				}
			/>

			<SearchField
				className="mb-5 max-w-md"
				label="Find a person"
				placeholder="Find a person by name"
				value={search}
				onChange={setSearch}
			/>

			{isLoading && <Spinner label="Finding people…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{answer && people.length === 0 && (
				<Card>
					<Empty title={search.trim() ? `Nobody called “${search.trim()}” holds this profession.` : "Nobody in your area holds this profession."} />
				</Card>
			)}

			{people.length > 0 && (
				<Table head={["Name", "Branch", "Registered as", ""]}>
					{people.map((person) => {
						const to = person.volunteer
							? `/admin/registry/volunteer/${encodeURIComponent(person.volunteer)}`
							: person.member
								? `/admin/registry/member/${encodeURIComponent(person.member)}`
								: undefined;
						return (
							<Row key={person.red_profile} to={to} label={`Open ${person.full_name}`}>
								<Cell>
									<span className="flex items-center gap-3">
										<Avatar name={person.full_name} photo={person.photo} size={32} />
										<span className="font-semibold text-ink">{person.full_name}</span>
									</span>
								</Cell>
								<Cell className="text-muted">{branchPath(person.geo_path) || "—"}</Cell>
								<Cell>
									<span className="flex flex-wrap gap-1.5">
										{person.volunteer && <Pill tone="page">Volunteer</Pill>}
										{person.member && <Pill tone="page">Member</Pill>}
									</span>
								</Cell>
								<Cell className="text-right">
									{to && (
										<Link to={to} className="text-[12.5px] font-bold text-ink hover:underline">
											Open
										</Link>
									)}
								</Cell>
							</Row>
						);
					})}
				</Table>
			)}

			{answer && (
				<Pager
					page={Math.floor(offset / PAGE)}
					pageCount={Math.max(1, Math.ceil(answer.total / PAGE))}
					total={answer.total}
					noun={answer.total === 1 ? "person" : "people"}
					onPage={(next) => setOffset(next * PAGE)}
				/>
			)}
		</>
	);
}
