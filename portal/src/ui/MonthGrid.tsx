import { Icon } from "./icons";
import { cx } from "./primitives";

/**
 * A month of days, drawn once and used at two sizes.
 *
 * The mini calendar on the events screen and the calendar tab are the same
 * grid with the same marking rules; only the cell size and whether the day
 * panel is beside it differ. Two implementations would have meant a day that
 * counted as "yours" on one screen and not on the other, which is the kind of
 * disagreement nobody notices until somebody misses an event.
 *
 * **A day carries two facts and they are drawn differently on purpose.**
 * Something is on (quiet, a tint) and something of *yours* is on (signal, the
 * one colour in this product that means "act on this"). A grid that marked both
 * the same way would answer the question a listing already answers and not the
 * one somebody opens a calendar for.
 *
 * **Locale-neutral by construction**, like `lib/format.ts`: the month name and
 * the weekday initials come from the browser rather than from a list of English
 * words in this file. The week starts on Monday, which is not the browser's to
 * tell us — `Intl` exposes no reliable first-day-of-week everywhere this runs —
 * and is the one assumption here.
 */

/** What is on for one day: everything, and how much of it is the reader's. */
export interface DayMark {
	total: number;
	mine: number;
}

/**
 * A date as `YYYY-MM-DD` in the reader's own timezone.
 *
 * Not `toISOString().slice(0, 10)`, which converts to UTC first and so reports
 * yesterday for anybody east of Greenwich for part of the day. Every date this
 * app compares against is a plain calendar date with no timezone in it, so the
 * local reading is the correct one.
 */
export function isoDate(date: Date): string {
	const month = String(date.getMonth() + 1).padStart(2, "0");
	const day = String(date.getDate()).padStart(2, "0");

	return `${date.getFullYear()}-${month}-${day}`;
}

/** Today, as the same kind of string. */
export function todayIso(): string {
	return isoDate(new Date());
}

/**
 * The Monday on or before the first of the month, and the Sunday on or after
 * the last: the window the grid actually draws.
 *
 * Exported because it is also what the calendar asks the server for. A grid
 * showing the last days of the previous month with nothing marked on them would
 * be quietly wrong, and asking for the calendar month alone is how that
 * happens.
 */
export function gridRange(year: number, month: number): { from: string; to: string } {
	const first = new Date(year, month, 1);
	const last = new Date(year, month + 1, 0);

	const start = new Date(first);
	start.setDate(first.getDate() - mondayOffset(first));

	const end = new Date(last);
	end.setDate(last.getDate() + (6 - mondayOffset(last)));

	return { from: isoDate(start), to: isoDate(end) };
}

/** How many days into the week this date is, counting Monday as nought. */
function mondayOffset(date: Date): number {
	return (date.getDay() + 6) % 7;
}

/** The weeks of the grid, each seven dates, starting Monday. */
function weeks(year: number, month: number): Date[][] {
	const { from, to } = gridRange(year, month);
	const cursor = new Date(`${from}T00:00:00`);
	const last = new Date(`${to}T00:00:00`);

	const out: Date[][] = [];

	while (cursor <= last) {
		const week: Date[] = [];

		for (let i = 0; i < 7; i += 1) {
			week.push(new Date(cursor));
			cursor.setDate(cursor.getDate() + 1);
		}

		out.push(week);
	}

	return out;
}

/** "August 2026", in the reader's own language. */
export function monthLabel(year: number, month: number): string {
	return new Date(year, month, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

/** The seven initials across the top, from the browser rather than from a list. */
function weekdayInitials(): string[] {
	// Any Monday will do; 5 January 1970 was one.
	const monday = new Date(1970, 0, 5);

	return Array.from({ length: 7 }, (_, index) => {
		const day = new Date(monday);
		day.setDate(monday.getDate() + index);

		return day.toLocaleDateString(undefined, { weekday: "narrow" });
	});
}

export function MonthGrid({
	year,
	month,
	marks,
	selected,
	onSelect,
	onMonth,
	size = "regular",
}: {
	year: number;
	/** Nought to eleven, as `Date` counts them. */
	month: number;
	marks: Record<string, DayMark>;
	selected?: string | null;
	onSelect?: (iso: string) => void;
	/** Omitted draws no arrows, for a grid whose month is decided elsewhere. */
	onMonth?: (year: number, month: number) => void;
	size?: "compact" | "regular";
}) {
	const compact = size === "compact";
	const today = todayIso();
	const initials = weekdayInitials();

	const step = (delta: number) => {
		const next = new Date(year, month + delta, 1);
		onMonth?.(next.getFullYear(), next.getMonth());
	};

	return (
		<div>
			<div className="mb-3 flex items-center justify-between gap-2">
				<h3
					className={cx(
						"font-bold tracking-tight text-ink",
						compact ? "text-[13.5px]" : "text-[16px]",
					)}
				>
					{monthLabel(year, month)}
				</h3>

				{onMonth && (
					<div className="flex items-center gap-1">
						<Step label="Previous month" onClick={() => step(-1)} rotate="rotate-90" />
						<Step label="Next month" onClick={() => step(1)} rotate="-rotate-90" />
					</div>
				)}
			</div>

			<div className="grid grid-cols-7 gap-1">
				{initials.map((initial, index) => (
					<div
						key={index}
						aria-hidden="true"
						className={cx(
							"pb-1 text-center font-bold uppercase text-slate-faint",
							compact ? "text-[9.5px]" : "text-[10px]",
						)}
					>
						{initial}
					</div>
				))}

				{weeks(year, month).map((week) =>
					week.map((date) => {
						const iso = isoDate(date);
						const mark = marks[iso];
						const outside = date.getMonth() !== month;

						return (
							<Day
								key={iso}
								iso={iso}
								day={date.getDate()}
								mark={mark}
								outside={outside}
								today={iso === today}
								selected={iso === selected}
								compact={compact}
								onSelect={onSelect}
							/>
						);
					}),
				)}
			</div>
		</div>
	);
}

/**
 * One day.
 *
 * A day with nothing on it is not a button. Making every cell pressable and
 * then opening an empty panel is the sort of control that teaches somebody
 * their taps do nothing, so a bare day renders as text and only a day with
 * something on it takes a press.
 */
function Day({
	iso,
	day,
	mark,
	outside,
	today,
	selected,
	compact,
	onSelect,
}: {
	iso: string;
	day: number;
	mark?: DayMark;
	outside: boolean;
	today: boolean;
	selected: boolean;
	compact: boolean;
	onSelect?: (iso: string) => void;
}) {
	const mine = (mark?.mine ?? 0) > 0;
	const any = (mark?.total ?? 0) > 0;

	const shape = cx(
		"relative grid place-items-center rounded-lg font-bold tabular-nums transition",
		compact ? "h-8 text-[11.5px]" : "h-11 text-[13px]",
	);

	const tone = selected
		? "bg-rail text-white"
		: mine
			? "bg-blue text-white hover:bg-blue-press"
			: any
				? "bg-tint-navy-soft text-ink hover:bg-card-line"
				: outside
					? "text-slate-faint/60"
					: "text-muted";

	// What the day says out loud. A screen reader gets the whole sentence rather
	// than a number, because "14" on its own is the one thing the visual
	// treatment is *not* communicating.
	const label = [
		new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
			day: "numeric",
			month: "long",
			year: "numeric",
		}),
		mine ? `${mark?.mine} you are attending` : null,
		any && !mine ? `${mark?.total} on` : null,
		today ? "today" : null,
	]
		.filter(Boolean)
		.join(", ");

	if (!any || !onSelect) {
		return (
			<div
				className={cx(shape, tone, today && !selected && !mine && "ring-1 ring-inset ring-blue/35")}
				aria-label={label}
			>
				{day}
			</div>
		);
	}

	return (
		<button
			type="button"
			onClick={() => onSelect(iso)}
			aria-label={label}
			aria-pressed={selected}
			className={cx(
				shape,
				tone,
				"focus:outline-none focus-visible:ring-2 focus-visible:ring-blue focus-visible:ring-offset-1",
				today && !selected && !mine && "ring-1 ring-inset ring-blue/35",
				outside && "opacity-60",
			)}
		>
			{day}
			{/* Something is on that is not the reader's own. The tint behind the
			    number already says so at a glance; the dot is what keeps it legible
			    for somebody who cannot tell the two washes apart. */}
			{any && !mine && !selected && (
				<span
					aria-hidden="true"
					className="absolute bottom-1 h-1 w-1 rounded-full bg-rail/50"
				/>
			)}
		</button>
	);
}

function Step({
	label,
	onClick,
	rotate,
}: {
	label: string;
	onClick: () => void;
	rotate: string;
}) {
	return (
		<button
			type="button"
			onClick={onClick}
			aria-label={label}
			className="grid h-7 w-7 place-items-center rounded-full text-slate-faint transition hover:bg-surface hover:text-ink"
		>
			<Icon.chevron size={15} className={rotate} />
		</button>
	);
}

/**
 * Which days carry what, built from a list of events and the reader's own set.
 *
 * Shared so the two grids cannot disagree about what a multi-day event does to
 * a calendar: it marks **every** day it runs, because an event a person is at
 * for four days is an event on four of their days, and a calendar that marked
 * only the first would show them free on the other three.
 */
export function markDays(
	events: Array<{ event: string; start_date: string; end_date: string }>,
	mine: Set<string>,
): Record<string, DayMark> {
	const marks: Record<string, DayMark> = {};

	for (const row of events) {
		if (!row.start_date) continue;

		const start = new Date(`${row.start_date}T00:00:00`);
		const end = new Date(`${(row.end_date || row.start_date)}T00:00:00`);

		if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) continue;

		const isMine = mine.has(row.event);

		// Bounded, because the end date is another app's field and a typo in a
		// year turns "walk every day it runs" into a loop that hangs the tab. A
		// grid never shows more than six weeks, so anything past that span
		// cannot change what is drawn.
		let guard = 0;

		for (const cursor = new Date(start); cursor <= end && guard < 400; cursor.setDate(cursor.getDate() + 1)) {
			const iso = isoDate(cursor);
			const mark = marks[iso] ?? { total: 0, mine: 0 };

			marks[iso] = { total: mark.total + 1, mine: mark.mine + (isMine ? 1 : 0) };
			guard += 1;
		}
	}

	return marks;
}

/** The events touching one day, in the order they start. */
export function eventsOn<T extends { start_date: string; end_date: string; start_time: string }>(
	events: T[],
	iso: string,
): T[] {
	return events
		.filter((row) => {
			if (!row.start_date) return false;

			return row.start_date <= iso && (row.end_date || row.start_date) >= iso;
		})
		.sort((a, b) => (a.start_time || "").localeCompare(b.start_time || ""));
}
