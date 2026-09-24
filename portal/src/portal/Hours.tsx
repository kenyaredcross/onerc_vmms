import { useMemo, useState } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import {
	Card,
	Empty,
	ErrorNote,
	List,
	ListRow,
	Meter,
	PageHeading,
	SectionLabel,
	Skeleton,
	Spinner,
	StatTile,
	TINTS,
	cx,
} from "../ui/primitives";
import type { MyTimeLogs, TimeLogRow, VolunteerProfile } from "./types";

/**
 * The record of time given — read, and only read.
 *
 * **Nobody credits themselves with hours.** The screen used to carry a form, and
 * the form was the wrong idea twice over: a volunteer typing their own figure is
 * a claim nobody stood behind, and the endpoint under it wanted `create` on a
 * doctype a volunteer holds `read` on, so for most people the button answered
 * with a permission error. Hours now arrive the way the work did — a coordinator
 * records what was served when they verify a deployment's attendance, and the
 * server writes that figure onto this person's record.
 *
 * So what is left here is a statement of account: what you have given, and every
 * entry it is made of. `my_time_logs` is possessive and takes no person, so it
 * cannot be pointed at anybody else's history.
 */
export default function Hours() {
	const [showHistory, setShowHistory] = useState(false);
	const [offset, setOffset] = useState(0);
	const { data, isLoading } = useFrappeGetCall<{ message: VolunteerProfile | null }>(
		API.myVolunteer,
		undefined,
		"portal:my_volunteer",
	);

	const logs = useFrappeGetCall<{ message: MyTimeLogs | null }>(
		API.myTimeLogs,
		{ limit: 1 },
		"portal:my_time_logs:summary",
	);
	const history = useFrappeGetCall<{ message: MyTimeLogs | null }>(
		API.myTimeLogs,
		{ limit: 100, offset },
		showHistory ? `portal:my_time_logs:${offset}` : null,
	);

	const profile = data?.message ?? null;

	return (
		<>
			<PageHeading
				title={<EditableText k="portal.hours.heading" fallback="My hours" />}
				trail={[{ label: "Home", to: "/dashboard" }, { label: "My hours" }]}
				lead={
					<EditableText
						k="portal.hours.lead"
						fallback="Your coordinator records the hours you serve when they confirm attendance on a deployment. They appear here, and your branch sees the same figures against your record."
					/>
				}
			/>

			{isLoading && <Spinner label="Loading your hours…" />}

			{!isLoading && !profile && (
				<Card>
					<Empty
						framed={false}
						title="Your hours start once you are a registered volunteer"
						icon={Icon.clock}
					>
						Your record has to be verified by your branch first. After that, the time you serve on a
						deployment is recorded here.
					</Empty>
				</Card>
			)}

			{profile && (
				<>
					<section className="mb-8">
						<SectionLabel>
							<EditableText k="portal.hours.section.total" fallback="What you have given" />
						</SectionLabel>
						<Totals data={logs.data?.message ?? null} loading={logs.isLoading} />
					</section>

					{/* One column. The form that stood beside this list is gone, and
					    nothing has taken its place: a panel invented to balance the
					    row would be furniture. */}
					<section>
						<SectionLabel>
							<EditableText k="portal.hours.section.history" fallback="Hours history" />
						</SectionLabel>
						{!showHistory ? (
							<button type="button" onClick={() => setShowHistory(true)} className="rounded-lg border border-card-line bg-white px-4 py-2 text-sm font-semibold text-ink hover:border-blue">View all hours</button>
						) : (
							<>
								<History data={history.data?.message ?? null} loading={history.isLoading} error={history.error} />
								<div className="mt-4 flex items-center gap-3 text-sm text-muted">
									<span>{history.data?.message?.log_count ? `Showing ${offset + 1}–${Math.min(offset + 100, history.data.message.log_count)} of ${history.data.message.log_count}` : "No entries yet"}</span>
									<button type="button" disabled={offset === 0 || history.isLoading} onClick={() => setOffset(Math.max(0, offset - 100))} className="font-semibold text-ink disabled:opacity-40">Previous</button>
									<button type="button" disabled={history.isLoading || offset + 100 >= (history.data?.message?.log_count ?? 0)} onClick={() => setOffset(offset + 100)} className="font-semibold text-ink disabled:opacity-40">Next</button>
								</div>
							</>
						)}
					</section>
				</>
			)}
		</>
	);
}

/* ------------------------------------------------------------------ totals */

/**
 * What this person has given, as two figures and a breakdown.
 *
 * The per-kind breakdown is built by walking whatever keys `hours_by_type`
 * carries. No literal indexes it, so a society filing only general time gets one
 * bar and one filing deployment time as well gets two, without this file knowing
 * either word. Same discipline the service states: the kinds are dispatched on
 * in one table on the server and compared nowhere else.
 *
 * **The bars are measured against the largest kind, not against the total.**
 * Against the total, a person whose time is split three ways sees three stubs;
 * against the largest, the shape of how they spend their time is readable, which
 * is the only question a breakdown answers.
 */
function Totals({ data, loading }: { data: MyTimeLogs | null; loading: boolean }) {
	const kinds = useMemo(
		() => Object.entries(data?.hours_by_type ?? {}).sort((a, b) => b[1] - a[1]),
		[data],
	);

	const largest = kinds[0]?.[1] ?? 0;

	return (
		// The breakdown takes a third of the row when there is one. When there is
		// not — a society with no time-log categories, or a volunteer who has filed
		// nothing yet — the two figures take the whole width rather than sitting in
		// two thirds of it beside a hole.
		<div className={cx("grid gap-4", kinds.length > 0 && "lg:grid-cols-3")}>
			<div className={cx("grid gap-4 sm:grid-cols-2", kinds.length > 0 && "lg:col-span-2")}>
				<StatTile
					label="Hours logged"
					value={loading ? "…" : hours(data?.total_hours ?? 0)}
					hint="Across everything recorded for you"
					icon={Icon.clock}
					tint="navy"
				/>
				<StatTile
					label="Entries"
					value={loading ? "…" : (data?.log_count ?? 0)}
					hint={
						data?.recent[0]
							? `Last on ${formatDate(data.recent[0].activity_date)}`
							: "Nothing recorded yet"
					}
					icon={Icon.book}
					tint="teal"
				/>
			</div>

			{kinds.length > 0 && (
				<Card>
					<div className="mb-4 text-[11.5px] font-semibold text-muted">By kind of work</div>
					<div className="space-y-3.5">
						{kinds.map(([kind, total], index) => (
							<Meter
								key={kind}
								label={<span className="capitalize">{kind}</span>}
								value={total}
								total={largest}
								figure={`${hours(total)}h`}
								tint={TINTS[index % TINTS.length]}
							/>
						))}
					</div>
				</Card>
			)}
		</div>
	);
}

/* ----------------------------------------------------------------- history */

function History({
	data,
	loading,
	error,
}: {
	data: MyTimeLogs | null;
	loading: boolean;
	error: unknown;
}) {
	if (loading) {
		return (
			<Card>
				<div className="space-y-3">
					<Skeleton className="h-14" />
					<Skeleton className="h-14" />
					<Skeleton className="h-14" />
				</div>
			</Card>
		);
	}

	if (error) {
		return <ErrorNote>{errorMessage(error)}</ErrorNote>;
	}

	if ((data?.recent.length ?? 0) === 0) {
		return (
			<Card>
				<Empty framed={false} title="No hours recorded yet" icon={Icon.clock}>
					Once a coordinator confirms the time you served on a deployment, it appears here, newest
					first.
				</Empty>
			</Card>
		);
	}

	return (
		<Card pad={false}>
			<div className="p-2">
				<List>
					{data?.recent.map((row) => (
						<LogEntry key={row.name} row={row} />
					))}
				</List>
			</div>
		</Card>
	);
}

function LogEntry({ row }: { row: TimeLogRow }) {
	return (
		<ListRow
			lead={
				<span
					className="grid h-9 w-9 flex-none place-items-center rounded-lg bg-tint-navy-soft text-tint-navy"
					aria-hidden="true"
				>
					<Icon.clock size={17} />
				</span>
			}
			// The mission is the title where there is one: what somebody remembers
			// about a fortnight in Kyela is the flood response, not the date it was
			// filed against. A general log keeps the date, because the date is all
			// it is.
			title={row.deployment_title ?? formatDate(row.activity_date)}
			meta={
				<span className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
					{row.deployment_title && <span>{formatDate(row.activity_date)}</span>}
					{row.category_label && (
						<span className="rounded-full bg-rail/[.06] px-2 py-0.5 font-semibold text-ink">
							{row.category_label}
						</span>
					)}
					{row.geo_path && <span>{row.geo_path}</span>}
				</span>
			}
			trailing={
				<span className="tabular text-[13.5px] font-semibold text-ink">
					{hours(row.hours)}h
				</span>
			}
		>
			{row.notes && (
				<p className="pl-[50px] text-[12.5px] leading-relaxed text-muted">{row.notes}</p>
			)}
		</ListRow>
	);
}

/** Whole numbers stay whole; a half hour keeps its half. */
function hours(value: number): string {
	return Number.isInteger(value) ? String(value) : value.toFixed(1);
}
