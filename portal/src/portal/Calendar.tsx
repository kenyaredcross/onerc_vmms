import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import {
	Card,
	Empty,
	ErrorNote,
	NotBuilt,
	PageHeading,
	Pill,
	SectionLabel,
	Skeleton,
	cx,
} from "../ui/primitives";
import {
	MonthGrid,
	eventsOn,
	gridRange,
	isoDate,
	markDays,
	monthLabel,
	todayIso,
} from "../ui/MonthGrid";
import { useAttendance } from "./attendance";
import type { EventCard } from "./types";

/**
 * A month at a time, and what the reader is doing in it.
 *
 * **Its own tab rather than a view on the events page, because it answers a
 * different question.** The events page answers "what is on that I might go
 * to", which is a browsing question and is why that screen is a searchable grid
 * of pictures. This answers "what does my month look like", which is a planning
 * question, and the shape that answers it is a grid of days. Folding one into
 * the other would have meant a search bar over a calendar, which is neither.
 *
 * **One request per month, and it fetches the grid rather than the month.**
 * `gridRange` gives the Monday-to-Sunday window actually drawn, so the days
 * either side that belong to the neighbouring months are marked too. Asking for
 * the calendar month alone would leave those cells looking empty, which is a
 * wrong answer rather than a missing one.
 *
 * **Past months are readable and that is deliberate.** `api/events.calendar`
 * goes through `seam.in_range` rather than `seam.upcoming`, which refuses to
 * look backwards. A calendar that empties itself the moment you page behind
 * today reads as broken, and looking at the day you turned up is half of what a
 * calendar is for.
 */
export default function Calendar() {
	const now = new Date();
	const [year, setYear] = useState(now.getFullYear());
	const [month, setMonth] = useState(now.getMonth());
	const [selected, setSelected] = useState<string | null>(todayIso());
	// Whether to draw the whole society's month or only the reader's own. Not a
	// filter on the fetch: the same answer serves both, and narrowing in the
	// browser is honest here because the response is one bounded window rather
	// than a page of an unbounded list.
	const [mineOnly, setMineOnly] = useState(false);

	const range = useMemo(() => gridRange(year, month), [year, month]);

	const { data, error, isLoading } = useFrappeGetCall<{
		message: { available: boolean; events: EventCard[]; attending: string[] };
	}>(
		API.eventsCalendar,
		{ date_from: range.from, date_to: range.to },
		`portal:calendar:${range.from}:${range.to}`,
	);

	// The verb comes from the same hook the events page uses, so a day panel and
	// a card cannot disagree about whether somebody is going.
	const attendance = useAttendance(true);

	const available = data?.message?.available ?? true;
	const all = data?.message?.events ?? [];

	// Two requests carry the same fact, and the hook's copy is the one a press
	// writes to, so it wins the moment it has an answer of its own. The calendar
	// read stands in only while the hook is still loading, which is what stops
	// the grid drawing itself once unmarked and then again marked.
	const mine = attendance.isLoading
		? new Set(data?.message?.attending ?? [])
		: attendance.answered;

	const shown = mineOnly ? all.filter((row) => mine.has(row.event)) : all;
	const marks = useMemo(() => markDays(shown, mine), [shown, mine]);

	const onDay = selected ? eventsOn(shown, selected) : [];

	const goToday = () => {
		const today = new Date();
		setYear(today.getFullYear());
		setMonth(today.getMonth());
		setSelected(isoDate(today));
	};

	if (!available) {
		return (
			<>
				<Heading />
				<NotBuilt
					what="Calendar"
					needs="Your society has not opened its events listing yet. When it does, everything your branches publish will appear on this calendar."
				/>
			</>
		);
	}

	return (
		<>
			<Heading />

			{error && (
				<div className="mb-6">
					<ErrorNote>{errorMessage(error)}</ErrorNote>
				</div>
			)}

			<div className="mb-5 flex flex-wrap items-center gap-2">
				<button
					type="button"
					onClick={goToday}
					className="rounded-full border border-hairline-strong bg-white px-4 py-2 font-display text-[12px] font-bold text-slate-strong transition hover:border-navy hover:text-navy"
				>
					<EditableText k="portal.calendar.today" fallback="Today" />
				</button>

				<div className="flex rounded-full bg-surface p-1">
					<Toggle active={!mineOnly} onClick={() => setMineOnly(false)}>
						<EditableText k="portal.calendar.filter.all" fallback="Everything on" />
					</Toggle>
					<Toggle active={mineOnly} onClick={() => setMineOnly(true)}>
						<EditableText k="portal.calendar.filter.mine" fallback="Only mine" />
					</Toggle>
				</div>

				<Legend />
			</div>

			<div className="grid items-start gap-6 lg:grid-cols-3">
				<div className="lg:col-span-2">
					<Card>
						{isLoading ? (
							<div className="space-y-2">
								<Skeleton className="h-8 w-40" />
								<Skeleton className="h-64" />
							</div>
						) : (
							<MonthGrid
								year={year}
								month={month}
								marks={marks}
								selected={selected}
								onSelect={setSelected}
								onMonth={(nextYear, nextMonth) => {
									setYear(nextYear);
									setMonth(nextMonth);
									// The selection is cleared rather than carried across,
									// because 31 January followed by a press of "next" is
									// not a day February has, and a panel describing a date
									// that is not on the grid is worse than none.
									setSelected(null);
								}}
							/>
						)}
					</Card>
				</div>

				<div>
					<SectionLabel>
						{selected ? (
							formatDate(selected)
						) : (
							<EditableText k="portal.calendar.day.none" fallback="Pick a day" />
						)}
					</SectionLabel>

					<Card>
						{!selected ? (
							<Empty framed={false} title="Nothing selected" icon={Icon.calendar}>
								Days with something on are pressable. Choose one to see what it is.
							</Empty>
						) : onDay.length === 0 ? (
							<Empty framed={false} title="Nothing on this day" icon={Icon.calendar}>
								{mineOnly
									? "You have nothing on. Turn off “Only mine” to see what else your society has planned."
									: `Nothing is scheduled for ${formatDate(selected)}.`}
							</Empty>
						) : (
							<ul className="space-y-3">
								{onDay.map((row) => (
									<DayEvent
										key={row.event}
										row={row}
										going={mine.has(row.event)}
										busy={attendance.pending === row.event}
										onToggle={() => void attendance.toggle(row.event)}
									/>
								))}
							</ul>
						)}
					</Card>

					<p className="mt-3 px-1 text-[11.5px] leading-relaxed text-slate-faint">
						<EditableText
							k="portal.calendar.note"
							fallback="Saying you are going tells your branch to expect you. It does not book a ticket or hold a place."
						/>
					</p>
				</div>
			</div>

			<p className="sr-only" aria-live="polite">
				{monthLabel(year, month)}
			</p>
		</>
	);
}

function Heading() {
	return (
		<PageHeading
			title={<EditableText k="portal.calendar.heading" fallback="Your calendar" />}
			lead={
				<EditableText
					k="portal.calendar.intro"
					fallback="What your society has on, and which of it you have said you are coming to."
				/>
			}
		/>
	);
}

function Toggle({
	active,
	onClick,
	children,
}: {
	active: boolean;
	onClick: () => void;
	children: ReactNode;
}) {
	return (
		<button
			type="button"
			onClick={onClick}
			aria-pressed={active}
			className={cx(
				"rounded-full px-3.5 py-1.5 font-display text-[12px] font-bold transition",
				active ? "bg-white text-navy shadow-card" : "text-slate-body hover:text-navy",
			)}
		>
			{children}
		</button>
	);
}

/**
 * What the two washes on the grid mean.
 *
 * Drawn rather than assumed, because the distinction between "something is on"
 * and "you are going to it" is the whole point of the screen and it is carried
 * by colour. Colour alone is not an explanation, and it is not accessible on
 * its own either.
 */
function Legend() {
	return (
		<div className="ml-auto flex items-center gap-4 text-[11px] text-slate-faint">
			<span className="flex items-center gap-1.5">
				<span className="h-3 w-3 rounded-[4px] bg-signal" aria-hidden="true" />
				<EditableText k="portal.calendar.legend.mine" fallback="You are going" />
			</span>
			<span className="flex items-center gap-1.5">
				<span className="h-3 w-3 rounded-[4px] bg-tint-navy-soft" aria-hidden="true" />
				<EditableText k="portal.calendar.legend.other" fallback="Something on" />
			</span>
		</div>
	);
}

/** One event in the day panel. */
function DayEvent({
	row,
	going,
	busy,
	onToggle,
}: {
	row: EventCard;
	going: boolean;
	busy: boolean;
	onToggle: () => void;
}) {
	return (
		<li className="rounded-card border border-hairline p-4">
			<div className="flex items-start justify-between gap-3">
				<div className="min-w-0">
					<Link
						to={`/events/${encodeURIComponent(row.event)}`}
						className="font-display text-[13.5px] font-bold leading-snug text-ink transition hover:text-navy [overflow-wrap:anywhere]"
					>
						{row.title}
					</Link>

					<div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11.5px] text-slate-body">
						{row.start_time && (
							<span className="flex items-center gap-1">
								<Icon.clock size={12} className="text-slate-faint" />
								{row.start_time.slice(0, 5)}
								{row.end_time && ` to ${row.end_time.slice(0, 5)}`}
							</span>
						)}
						{(row.venue || row.medium) && (
							<span className="flex min-w-0 items-center gap-1">
								<Icon.pin size={12} className="flex-none text-slate-faint" />
								<span className="truncate">{row.venue || row.medium}</span>
							</span>
						)}
					</div>
				</div>

				{going && (
					<Pill tone="signal">
						<Icon.check size={11} />
						<EditableText k="portal.calendar.day.badge" fallback="Going" />
					</Pill>
				)}
			</div>

			<button
				type="button"
				onClick={onToggle}
				disabled={busy}
				className={cx(
					"mt-3 rounded-full px-3.5 py-1.5 font-display text-[11.5px] font-bold transition disabled:opacity-50",
					going
						? "border border-hairline-strong bg-white text-slate-strong hover:border-navy hover:text-navy"
						: "bg-navy text-white hover:bg-signal",
				)}
			>
				{busy ? (
					<EditableText k="portal.events.attending.saving" fallback="Saving…" />
				) : going ? (
					<EditableText k="portal.calendar.day.withdraw" fallback="I can't make it" />
				) : (
					<EditableText k="portal.calendar.day.attend" fallback="I'm going" />
				)}
			</button>
		</li>
	);
}
