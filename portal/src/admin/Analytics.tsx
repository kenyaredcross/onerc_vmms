import { useState } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatHours } from "../lib/format";
import { BarRows, ColumnChart, type Column } from "../ui/chart";
import {
	Card,
	Cell,
	Empty,
	ErrorNote,
	PageHeading,
	Row,
	SectionTitle,
	Spinner,
	Stat,
	Table,
} from "../ui/primitives";

/**
 * What a coordinator's own part of the society looks like, in numbers.
 *
 * This screen used to be a `NotBuilt` saying no aggregation endpoint existed.
 * One does now — `api/analytics.py::branch_summary` — and everything drawn here
 * comes out of it. Nothing on this page is computed in the browser except the
 * shapes of the bars.
 *
 * **The scope is still not a control, and the drill-down is not one either.**
 * There is no "choose a branch" select: the endpoint derives the area from the
 * session and each doctype is counted through its own registered scope role, so
 * a coordinator sees their own branch because it is theirs rather than because
 * they picked it out of a list they could have picked something else from.
 *
 * What the trail adds is *narrowing within that*, and it can only ever go
 * downwards. Every rung it offers came out of `coverage`, which is itself
 * computed from what the caller may already see, and `geo_node` is intersected
 * server-side with their scope regardless — so a person who edits the request
 * to name the whole country still gets their branch back. "Everywhere" at the
 * top of the trail means the caller's own whole scope, which for somebody
 * assigned at the root of the ladder is the whole society and for everybody
 * else is less.
 *
 * **Zeroes are shown rather than hidden.** A society that has named its
 * volunteer scope role but not its membership one gets real volunteer numbers
 * beside honest zeroes, which is the truth about what that person may see. A
 * screen that refused to draw, or quietly dropped the empty half, would leave
 * somebody believing their branch has no members.
 *
 * **Money is absent and says so.** A society's income is `onerc_payments`'
 * record; a revenue figure assembled here would be a second answer to a
 * question another app owns.
 */
interface Summary {
	geo_node: string;
	volunteers: { total: number; by_status: Record<string, number> };
	members: { total: number; by_status: Record<string, number> };
	deployments: { total: number; by_status: Record<string, number> };
	tasks: { open: number; awaiting_sign_off: number; overdue: number };
	hours: { total: number; logged_by: number; truncated: boolean };
	trend: Array<{ month: string; volunteers: number; members: number }>;
	coverage: Array<{ geo_node: string; label: string; volunteers: number; members: number }>;
}

/** One rung of where the reader has walked to. `null` name is "everywhere". */
type Rung = { name: string; label: string };

export default function Analytics() {
	/**
	 * Where the reader has drilled to, as the path they walked rather than a
	 * single node.
	 *
	 * The path is what makes the way back up honest: popping to a rung shows
	 * exactly the numbers that rung showed on the way down, whereas a single
	 * "current node" would need the ladder re-derived to offer a parent, and
	 * would offer parents *above* what the caller may see.
	 *
	 * **Nothing here widens anything.** `geo_node` is intersected server-side
	 * with the caller's own scope, so a coordinator who edits the query string to
	 * name the country still gets their branch. Walking down is the only
	 * direction that changes the answer; walking up returns to where they
	 * started, which is their whole scope and no more. Somebody assigned at the
	 * root of the ladder starts at the top of the society, which is the whole
	 * of what a national viewer is.
	 */
	const [trail, setTrail] = useState<Rung[]>([]);
	const here = trail.length ? trail[trail.length - 1] : null;

	const { data, error, isLoading } = useFrappeGetCall<{ message: Summary }>(
		API.branchSummary,
		here ? { geo_node: here.name } : undefined,
		`admin:branch_summary:${here?.name ?? "all"}`,
	);

	const summary = data?.message;

	return (
		<>
			<PageHeading title={<EditableText k="admin.nav.analytics" fallback="Analytics" />} />

			<Trail trail={trail} onGoTo={(depth) => setTrail(trail.slice(0, depth))} />

			{isLoading && <Spinner label="Counting your branch…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{summary && (
				<div className="space-y-5">
					<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
						<Card>
							<Stat value={summary.volunteers.total} label="Volunteers" />
						</Card>
						<Card>
							<Stat value={summary.members.total} label="Memberships" />
						</Card>
						<Card>
							<Stat value={formatHours(summary.hours.total)} label="Hours logged" />
						</Card>
						<Card>
							<Stat value={summary.tasks.open} label="Open tasks" />
						</Card>
						<Card>
							<Stat value={summary.deployments.total} label="Deployments" />
						</Card>
					</div>

					{summary.hours.truncated && (
						<p className="text-[12px] text-slate-faint">
							Hours are summed over the first 5,000 volunteers in your area, so this figure is a
							floor rather than a total. Narrow to a branch for an exact one.
						</p>
					)}

					{/* Two small multiples, never one frame with two scales. See the
					    note at the top of `ui/chart.tsx`. */}
					<div className="grid gap-4 lg:grid-cols-2">
						<Card>
							<SectionTitle>Volunteers joining</SectionTitle>
							<ColumnChart columns={trendColumns(summary.trend, "volunteers")} />
						</Card>
						<Card>
							<SectionTitle>Memberships taken out</SectionTitle>
							<ColumnChart columns={trendColumns(summary.trend, "members")} />
						</Card>
					</div>

					<div className="grid gap-4 lg:grid-cols-3">
						<Card>
							<SectionTitle>Volunteers by status</SectionTitle>
							<BarRows rows={breakdown(summary.volunteers.by_status)} />
						</Card>
						<Card>
							<SectionTitle>Memberships by status</SectionTitle>
							<BarRows rows={breakdown(summary.members.by_status)} />
						</Card>
						<Card>
							<SectionTitle>Deployments by status</SectionTitle>
							<BarRows rows={breakdown(summary.deployments.by_status)} />
						</Card>
					</div>

					<Card>
						<SectionTitle>Work outstanding</SectionTitle>
						<div className="grid gap-4 sm:grid-cols-3">
							<Stat value={summary.tasks.open} label="Tasks open" />
							<Stat value={summary.tasks.awaiting_sign_off} label="Waiting on your sign-off" />
							<Stat value={summary.tasks.overdue} label="Past their due date" />
						</div>
					</Card>

					<div>
						<SectionTitle>Where your people are</SectionTitle>

						{summary.coverage.length === 0 ? (
							<Empty title="Nothing below this level">
								You are looking at the bottom of the society's hierarchy, so there is no rung
								underneath to break these numbers down by.
							</Empty>
						) : (
							<>
								<Table head={["Place", "Volunteers", "Memberships", ""]}>
									{summary.coverage.map((row) => (
										<Row key={row.geo_node}>
											<Cell className="font-semibold text-ink">{row.label}</Cell>
											<Cell className="tabular-nums">{row.volunteers}</Cell>
											<Cell className="tabular-nums">{row.members}</Cell>
											<Cell>
												{/* Every rung is walkable, including an empty one: a
												    branch with nobody in it is exactly the branch
												    somebody wants to look inside. */}
												<button
													type="button"
													className="text-[12px] font-semibold text-navy underline underline-offset-2"
													onClick={() =>
														setTrail([...trail, { name: row.geo_node, label: row.label }])
													}
												>
													Look inside
												</button>
											</Cell>
										</Row>
									))}
								</Table>

								<p className="mt-3 text-[12px] leading-relaxed text-slate-faint">
									One rung down, not the whole tree beneath: a region coordinator wants their
									branches rather than every ward in the region. Look inside any of them to
									narrow every figure on this page to it.
								</p>
							</>
						)}
					</div>

					<p className="text-[12px] leading-relaxed text-slate-faint">
						Income is not shown here. A society's payments are recorded by onerc_payments, and a
						revenue figure assembled in this app would be a second answer to a question that one
						owns. Applications waiting for a decision are on the review queue, person by person,
						rather than counted here.
					</p>
				</div>
			)}
		</>
	);
}

/** A trend series as chart columns, labelled by month rather than by date. */
function trendColumns(
	trend: Summary["trend"],
	key: "volunteers" | "members",
): Column[] {
	return trend.map((point) => ({
		label: monthLabel(point.month),
		title: monthLabel(point.month, true),
		value: point[key],
	}));
}

/**
 * `YYYY-MM` as something readable, through the browser's own locale.
 *
 * Not a month-name table written here: the portal is served to whoever a
 * society serves, and twelve English nouns in a source file is the same mistake
 * as a hardcoded country.
 */
function monthLabel(month: string, long = false): string {
	const [year, index] = month.split("-");
	const date = new Date(Number(year), Number(index) - 1, 1);

	if (Number.isNaN(date.getTime())) return month;

	return date.toLocaleDateString(undefined, {
		month: long ? "long" : "short",
		year: long ? "numeric" : "2-digit",
	});
}

/** A status map as bar rows, in the order the server sent them. */
function breakdown(counts: Record<string, number>): Array<{ label: string; value: number }> {
	return Object.entries(counts).map(([label, value]) => ({ label, value }));
}

/**
 * The way back up, and the record of how the reader got here.
 *
 * Drawn even at the top, where it is one word, so the page always says what it
 * is counting. "Everywhere" is the caller's own whole scope rather than the
 * whole society: somebody assigned to one region sees their region under that
 * word, which is the honest label for "no further narrowing applied".
 */
function Trail({ trail, onGoTo }: { trail: Rung[]; onGoTo: (depth: number) => void }) {
	return (
		<nav className="mb-4 flex flex-wrap items-center gap-1.5 text-[12.5px]" aria-label="Where you are looking">
			<Crumb label="Everywhere" active={trail.length === 0} onClick={() => onGoTo(0)} />

			{trail.map((rung, index) => (
				<span key={rung.name} className="flex items-center gap-1.5">
					<span aria-hidden className="text-slate-faint">
						/
					</span>
					<Crumb
						label={rung.label}
						active={index === trail.length - 1}
						onClick={() => onGoTo(index + 1)}
					/>
				</span>
			))}
		</nav>
	);
}

function Crumb({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
	if (active) {
		return <span className="font-semibold text-ink">{label}</span>;
	}

	return (
		<button type="button" className="text-navy underline underline-offset-2" onClick={onClick}>
			{label}
		</button>
	);
}
