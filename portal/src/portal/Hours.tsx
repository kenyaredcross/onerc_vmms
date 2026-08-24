import { useContext, useMemo, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Field, TextArea, VocabularySelect } from "../ui/form";
import { Icon } from "../ui/icons";
import {
	Button,
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
import type { MyTimeLogs, TimeLogRow, VocabularyRow, VolunteerProfile } from "./types";

/**
 * Logging time given, and seeing what has been logged.
 *
 * Both halves are possessive endpoints: `log_time` writes and `my_time_logs`
 * reads, and neither the read nor the write can be pointed at anybody else. The
 * history panel used to be a `NotBuilt` because only the coordinator's dossier
 * existed, which takes a name and is permission checked — calling that with the
 * caller's own name would have been a screen pretending to a rule it did not
 * have. `api/volunteer.py::my_time_logs` is that rule, written where it belongs.
 *
 * The geo node defaults to the volunteer's serving branch, which is the answer
 * in the overwhelming majority of cases and the one they should not have to look
 * up. What a society lets somebody log against is `VMMS Time Log Category`, an
 * open vocabulary this screen draws and never reads the meaning of.
 */
export default function Hours() {
	const { data, isLoading } = useFrappeGetCall<{ message: VolunteerProfile | null }>(
		API.myVolunteer,
		undefined,
		"portal:my_volunteer",
	);

	const logs = useFrappeGetCall<{ message: MyTimeLogs | null }>(
		API.myTimeLogs,
		undefined,
		"portal:my_time_logs",
	);

	const profile = data?.message ?? null;

	return (
		<>
			<PageHeading
				title={<EditableText k="portal.hours.heading" fallback="My hours" />}
				trail={[{ label: "Home", to: "/dashboard" }, { label: "My hours" }]}
				lead={<EditableText k="portal.hours.intro" />}
			/>

			{isLoading && <Spinner label="Loading your hours…" />}

			{!isLoading && !profile && (
				<Card>
					<Empty
						framed={false}
						title="Only a registered volunteer can log time"
						icon={Icon.clock}
					>
						Your record has to be verified by your branch first. Once it is, this is where you file
						the time you give.
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

					<div className="grid items-start gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
						<section>
							<SectionLabel>
								<EditableText k="portal.hours.section.log" fallback="Log time" />
							</SectionLabel>
							<LogForm profile={profile} onLogged={() => void logs.mutate()} />
						</section>

						<section>
							<SectionLabel>
								<EditableText k="portal.hours.section.history" fallback="Your logged time" />
							</SectionLabel>
							<History
								data={logs.data?.message ?? null}
								loading={logs.isLoading}
								error={logs.error}
							/>
						</section>
					</div>
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
					value={loading ? "—" : hours(data?.total_hours ?? 0)}
					hint="Across everything you have filed"
					icon={Icon.clock}
					tint="navy"
				/>
				<StatTile
					label="Entries filed"
					value={loading ? "—" : (data?.log_count ?? 0)}
					hint={
						data?.recent[0]
							? `Last on ${formatDate(data.recent[0].activity_date)}`
							: "Nothing filed yet"
					}
					icon={Icon.book}
					tint="teal"
				/>
			</div>

			{kinds.length > 0 && (
				<Card>
					<div className="mb-4 text-[11.5px] font-semibold text-slate-body">By kind of work</div>
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
				<Empty framed={false} title="Nothing logged yet" icon={Icon.clock}>
					Time you file appears here, newest first, and your branch sees it against your record.
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
					className="grid h-9 w-9 flex-none place-items-center rounded-control bg-tint-navy-soft text-tint-navy"
					aria-hidden="true"
				>
					<Icon.clock size={17} />
				</span>
			}
			title={formatDate(row.activity_date)}
			meta={
				<span className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
					{row.category_label && (
						<span className="rounded-full bg-navy/[.06] px-2 py-0.5 font-semibold text-navy">
							{row.category_label}
						</span>
					)}
					{row.geo_path && <span>{row.geo_path}</span>}
				</span>
			}
			trailing={
				<span className="tabular font-display text-[13.5px] font-extrabold text-navy">
					{hours(row.hours)}h
				</span>
			}
		>
			{row.notes && (
				<p className="pl-[50px] text-[12.5px] leading-relaxed text-slate-body">{row.notes}</p>
			)}
		</ListRow>
	);
}

/** Whole numbers stay whole; a half hour keeps its half. */
function hours(value: number): string {
	return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

/* -------------------------------------------------------------------- form */

function LogForm({ profile, onLogged }: { profile: VolunteerProfile; onLogged: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const options = useFrappeGetCall<{ message: { categories: VocabularyRow[] } }>(
		API.timeLogOptions,
		undefined,
		"portal:time_log_options",
	);

	const categories = options.data?.message?.categories ?? [];

	const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
	const [hoursGiven, setHours] = useState("");
	const [category, setCategory] = useState("");
	const [notes, setNotes] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const [done, setDone] = useState(false);

	const submit = async () => {
		setBusy(true);
		setFailure(null);
		setDone(false);

		try {
			await call.post(API.logTime, {
				volunteer: profile.volunteer,
				geo_node: profile.geo_node,
				activity_date: date,
				hours: Number(hoursGiven),
				log_category: category || undefined,
				notes: notes || undefined,
			});
			setDone(true);
			setHours("");
			setNotes("");
			setCategory("");
			// The totals and the list are now stale by exactly the row just filed.
			onLogged();
		} catch (logError) {
			setFailure(errorMessage(logError, "That time log was not accepted."));
		} finally {
			setBusy(false);
		}
	};

	const field =
		"w-full rounded-full border border-hairline-strong bg-white px-4 py-2.5 text-[13.5px] text-ink transition placeholder:text-slate-faint focus:border-navy focus:outline-none";

	const valid = Boolean(date) && Number(hoursGiven) > 0 && Boolean(profile.geo_node);

	return (
		<Card>
			{failure && (
				<div className="mb-5">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			{done && (
				<p className="mb-5 flex items-center gap-2.5 rounded-card border border-emerald-200 bg-emerald-50 px-4 py-3 text-[13px] font-medium text-emerald-800">
					<Icon.check size={16} />
					Logged. Your branch sees it against your record.
				</p>
			)}

			<div className="space-y-5">
				<div className="grid gap-5 sm:grid-cols-2">
					<Field label="Date" htmlFor="hours-date">
						<input
							id="hours-date"
							type="date"
							className={field}
							value={date}
							onChange={(event) => setDate(event.target.value)}
						/>
					</Field>

					<Field label="Hours" htmlFor="hours-count">
						<input
							id="hours-count"
							type="number"
							min="0"
							step="0.5"
							className={field}
							value={hoursGiven}
							onChange={(event) => setHours(event.target.value)}
							placeholder="3.5"
						/>
					</Field>
				</div>

				{/* Only drawn when a society has configured a vocabulary. An empty
				    select is a question with no answers, and the field is optional. */}
				{categories.length > 0 && (
					<Field label="What kind of work" htmlFor="hours-category">
						<VocabularySelect
							id="hours-category"
							value={category}
							onChange={setCategory}
							options={categories}
							placeholder="Not specified"
						/>
					</Field>
				)}

				{/* Read-only, and `rounded-card` rather than a capsule: a society with
				    a four-rung ladder has a path that wraps, and a two-line capsule
				    puts the first character under the curve. */}
				<Field label="Branch">
					<p className="flex items-start gap-2.5 rounded-card bg-surface px-4 py-3 text-[13px] leading-snug text-slate-strong">
						<Icon.pin size={15} className="mt-px flex-none text-slate-faint" />
						{profile.geo_path ?? "No serving branch on your record"}
					</p>
				</Field>

				<Field label="What you did" htmlFor="hours-notes">
					<TextArea id="hours-notes" value={notes} onChange={setNotes} rows={4} />
				</Field>
			</div>

			<div className="mt-6">
				<Button onClick={submit} disabled={busy || !valid}>
					{busy ? "Logging…" : "Log these hours"}
				</Button>
			</div>
		</Card>
	);
}
