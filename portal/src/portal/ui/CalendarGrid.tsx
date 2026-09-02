import { Fragment } from "react";

import { Icon } from "../../ui/icons";
import { isoDate, monthLabel, todayIso } from "../../ui/MonthGrid";
import { cx } from "./kit";

/**
 * A month grid that names what is on a day rather than dotting it.
 *
 * The approved concept's calendar is not a heat map: a day carries the *words*
 * of what is on it — "Deployment response due", "Community first-aid
 * demonstration" — and a deployment runs as one continuous strip across every
 * day it covers, so a twelve-day mission reads as one thing rather than as
 * twelve identical marks. That is the whole difference between a calendar you
 * scan and one you have to click through.
 *
 * **Four categories, and the colour is never the whole of one.** Every chip
 * carries its title, every one has an accessible name that begins with the
 * category, and the legend above the grid spells the four out. Colour is
 * recognition only.
 *
 * Monday-first and locale-neutral: the month name and weekday initials come
 * from the browser, never from a table in this file.
 */

export const CAL_KINDS = ["task", "deployment", "event", "certification"] as const;
export type CalKind = (typeof CAL_KINDS)[number];

/** One thing on the reader's month. Merged in `Calendar.tsx` from four reads. */
export interface CalEntry {
	id: string;
	kind: CalKind;
	title: string;
	/** The day it sits on, or the first day of a span. */
	start: string;
	/** The last day of a span. Equal to `start` for a single-day entry. */
	end: string;
	time?: string;
	meta?: string;
	/** What `meta` actually is, for the detail panel's second fact. */
	metaLabel?: string;
	/** One line of what it is, for the preview and the detail panel. */
	summary?: string;
	/** Where the full record lives, and what the button on to it says. */
	to: string;
	actionLabel: string;
}

export const CAL_META: Record<CalKind, { label: string; dot: string; text: string; chip: string }> =
	{
		task: {
			label: "Deadline",
			dot: "bg-cal-task",
			text: "text-cal-task",
			chip: "bg-red-soft text-red-ink border-l-cal-task",
		},
		deployment: {
			label: "Deployment",
			dot: "bg-cal-deployment",
			text: "text-cal-deployment",
			chip: "bg-rail text-white border-l-red",
		},
		event: {
			label: "Event",
			dot: "bg-cal-event",
			text: "text-cal-event",
			chip: "bg-blue-soft text-blue-press border-l-cal-event",
		},
		certification: {
			label: "Certification",
			dot: "bg-cal-cert",
			text: "text-cal-cert",
			chip: "bg-cal-cert-soft text-cal-cert border-l-cal-cert",
		},
	};

function weekdayNames(): string[] {
	const monday = new Date(1970, 0, 5);
	return Array.from({ length: 7 }, (_, i) => {
		const d = new Date(monday);
		d.setDate(monday.getDate() + i);
		return d.toLocaleDateString(undefined, { weekday: "short" });
	});
}

function weeks(year: number, month: number): Date[][] {
	const first = new Date(year, month, 1);
	const start = new Date(first);
	start.setDate(first.getDate() - ((first.getDay() + 6) % 7));

	const out: Date[][] = [];
	const cursor = new Date(start);
	for (let w = 0; w < 6; w += 1) {
		const row: Date[] = [];
		for (let d = 0; d < 7; d += 1) {
			row.push(new Date(cursor));
			cursor.setDate(cursor.getDate() + 1);
		}
		// A trailing row made entirely of the next month is a band of empty cells
		// nobody reads; a month that needs six rows still gets them.
		if (row.some((date) => date.getMonth() === month)) out.push(row);
	}
	return out;
}

const spans = (entry: CalEntry) => entry.end > entry.start;

/**
 * Which horizontal lane a multi-day entry runs in, so two overlapping missions
 * never draw over each other and each keeps the same height right across the
 * week. Greedy and stable: the earliest-starting entry takes the top lane.
 */
function laneOf(entries: CalEntry[]): Map<string, number> {
	const lanes: CalEntry[][] = [];
	const out = new Map<string, number>();

	for (const entry of [...entries].sort((a, b) => a.start.localeCompare(b.start))) {
		if (!spans(entry)) continue;
		let index = lanes.findIndex(
			(lane) => !lane.some((other) => other.start <= entry.end && other.end >= entry.start),
		);
		if (index === -1) {
			lanes.push([]);
			index = lanes.length - 1;
		}
		lanes[index].push(entry);
		out.set(entry.id, index);
	}

	return out;
}

/** The sentence a screen reader hears in place of the chip's colour. */
function accessibleName(entry: CalEntry): string {
	return [
		CAL_META[entry.kind].label,
		entry.title,
		entry.start === entry.end ? null : "continuing",
		entry.time,
		entry.meta,
	]
		.filter(Boolean)
		.join(" — ");
}

export function CalendarGrid({
	year,
	month,
	entries,
	selected,
	onSelect,
	onMonth,
}: {
	year: number;
	month: number;
	entries: CalEntry[];
	/** The selected entry's id, whose detail the panel beside the grid shows. */
	selected: string | null;
	onSelect: (id: string) => void;
	onMonth: (year: number, month: number) => void;
}) {
	const today = todayIso();
	const names = weekdayNames();
	const lanes = laneOf(entries);

	const step = (delta: number) => {
		const next = new Date(year, month + delta, 1);
		onMonth(next.getFullYear(), next.getMonth());
	};

	const onDay = (iso: string) => entries.filter((e) => e.start <= iso && e.end >= iso);

	return (
		<div>
			<div className="mb-4 flex flex-wrap items-center justify-between gap-3">
				<h2 className="font-display text-[17px] font-bold tracking-[-0.02em] text-ink">
					{monthLabel(year, month)}
				</h2>
				<div className="flex items-center gap-1.5">
					<StepButton label="Previous month" onClick={() => step(-1)} rotate="rotate-90" />
					<StepButton label="Next month" onClick={() => step(1)} rotate="-rotate-90" />
				</div>
			</div>

			{/* `min-w-0` so the legend may shrink and wrap: as a flex item its
			    default minimum is its own max-content width, which pushed the
			    fourth swatch off the card on a phone. */}
			<div className="mb-3 flex min-w-0 justify-start md:justify-end">
				<CalendarLegend />
			</div>

			{/* The grid keeps its own minimum width and scrolls sideways inside the
			    card on a phone: a seven-column month squeezed into 390px puts two
			    characters in a cell, which is not a calendar. It scrolls only where
			    it has to. Above `md` the well is
			    `visible`, because an `overflow-x` of `auto` clips vertically too
			    and would cut every hover preview off at the top of the grid. */}
			<div className="-mx-1 overflow-x-auto px-1 pb-1 md:mx-0 md:overflow-visible md:px-0">
				<div className="min-w-[640px] border-l border-t border-card-line md:min-w-0">
					<div className="grid grid-cols-7">
						{names.map((name) => (
							<div
								key={name}
								className="border-b border-r border-card-line px-2 py-2 text-[10px] font-bold uppercase tracking-[0.06em] text-muted"
							>
								{name}
							</div>
						))}

						{weeks(year, month).map((week) => {
							// Lanes are counted per week, not for the whole month: a week with no
							// mission running through it should not carry an empty band in every
							// one of its seven cells.
							const running = week.flatMap((date) => onDay(isoDate(date)).filter(spans));
							const weekLanes = running.length
								? Math.max(...running.map((entry) => lanes.get(entry.id) ?? 0)) + 1
								: 0;

							return (
								<Fragment key={isoDate(week[0])}>
									{week.map((date, column) => {
										const iso = isoDate(date);
										const outside = date.getMonth() !== month;
										const isToday = iso === today;
										const items = onDay(iso);
										const chips = items.filter((entry) => !spans(entry));
										const holdsSelected = items.some((entry) => entry.id === selected);

										return (
											<div
												key={iso}
												className={cx(
													"relative min-h-[96px] border-b border-r border-card-line px-2 pb-2 pt-1.5",
													outside && "bg-canvas",
													holdsSelected && "bg-blue-soft/70 ring-2 ring-inset ring-blue-line",
												)}
											>
												<span
													className={cx(
														"inline-grid h-[22px] min-w-[22px] place-items-center rounded-full px-1 text-[11.5px] font-semibold tabular",
														outside ? "text-slate-faint" : isToday ? "bg-blue text-white" : "text-ink",
													)}
												>
													{date.getDate()}
												</span>

												{/* Lanes first, then single-day chips: a mission strip has to
												    sit at the same height in every cell of its week or it
												    stops reading as one continuous thing. */}
												{weekLanes > 0 && (
													<div className="mt-1.5 space-y-[3px]">
														{Array.from({ length: weekLanes }, (_, lane) => {
															const entry = items.find(
																(candidate) => lanes.get(candidate.id) === lane,
															);
															if (!entry) {
																return <div key={lane} className="h-[19px]" aria-hidden="true" />;
															}

															return (
																<Strip
																	key={lane}
																	entry={entry}
																	startsHere={entry.start === iso || column === 0}
																	endsHere={entry.end === iso || column === 6}
																	selected={entry.id === selected}
																	column={column}
																	onSelect={onSelect}
																/>
															);
														})}
													</div>
												)}

												{chips.length > 0 && (
													<div className="mt-1.5 space-y-[3px]">
														{chips.map((entry) => (
															<Chip
																key={entry.id}
																entry={entry}
																selected={entry.id === selected}
																column={column}
																onSelect={onSelect}
															/>
														))}
													</div>
												)}
											</div>
										);
									})}
								</Fragment>
							);
						})}
					</div>
				</div>
			</div>
		</div>
	);
}

/* -------------------------------------------------------------------- chip */

const CHIP_BASE =
	"group relative block w-full truncate rounded-[5px] border-l-[3px] px-1.5 py-1 text-left text-[10px] font-semibold leading-[13px] transition";

function Chip({
	entry,
	selected,
	column,
	onSelect,
}: {
	entry: CalEntry;
	selected: boolean;
	column: number;
	onSelect: (id: string) => void;
}) {
	return (
		<button
			type="button"
			onClick={() => onSelect(entry.id)}
			aria-pressed={selected}
			aria-label={accessibleName(entry)}
			className={cx(
				CHIP_BASE,
				CAL_META[entry.kind].chip,
				selected && "ring-2 ring-blue ring-offset-1",
			)}
		>
			<span className="block truncate">{entry.title}</span>
			<Preview entry={entry} column={column} />
		</button>
	);
}

/**
 * One day of a multi-day entry, drawn so the run reads as a single bar.
 *
 * It bleeds 9px past the cell on each continuing side — the cell's 8px padding
 * plus its 1px hairline — so the bar crosses the rule between two days instead
 * of stopping at it. Only the first cell of a run carries the words; the rest
 * hold the same bar with an accessible name, so a screen reader is told what
 * the bar is on every day it covers.
 */
function Strip({
	entry,
	startsHere,
	endsHere,
	selected,
	column,
	onSelect,
}: {
	entry: CalEntry;
	startsHere: boolean;
	endsHere: boolean;
	selected: boolean;
	column: number;
	onSelect: (id: string) => void;
}) {
	return (
		<button
			type="button"
			onClick={() => onSelect(entry.id)}
			aria-pressed={selected}
			aria-label={accessibleName(entry)}
			className={cx(
				"group relative z-[1] block h-[19px] truncate bg-rail px-1.5 text-left text-[10px] font-semibold leading-[19px] text-white transition",
				// The bleed is on `width`, not on a negative margin: a negative
				// margin beside `width: 100%` moves the following sibling and leaves
				// this box exactly as wide as its cell, which is what left a hairline
				// gap between one day of a mission and the next.
				startsHere && endsHere && "w-full rounded-[5px]",
				startsHere && !endsHere && "w-[calc(100%+9px)] rounded-l-[5px]",
				!startsHere && endsHere && "-ml-[9px] w-[calc(100%+9px)] rounded-r-[5px]",
				!startsHere && !endsHere && "-ml-[9px] w-[calc(100%+18px)]",
				selected && "ring-2 ring-blue ring-offset-1",
			)}
		>
			<span className={cx("block truncate", !startsHere && "invisible")} aria-hidden="true">
				{entry.title}
			</span>
			<Preview entry={entry} column={column} />
		</button>
	);
}

/**
 * The hover and keyboard-focus preview.
 *
 * `aria-hidden`, because the chip's own accessible name already says all of
 * this — a tooltip a screen reader reads twice is noise. Suppressed below the
 * `md` breakpoint, where the grid is scrolling sideways and a 250px card
 * hanging off a cell would be unreachable anyway.
 */
function Preview({ entry, column }: { entry: CalEntry; column: number }) {
	const flip = column >= 5;

	return (
		<span
			aria-hidden="true"
			className={cx(
				"pointer-events-none absolute bottom-[calc(100%+9px)] z-50 hidden w-[250px] whitespace-normal rounded-xl border border-card-line bg-white p-3.5 text-left shadow-[0_16px_38px_rgba(1,30,65,0.18)]",
				"md:group-hover:block md:group-focus-visible:block",
				flip ? "right-0" : "left-0",
			)}
		>
			<span
				className={cx(
					"block text-[10px] font-bold uppercase tracking-[0.08em]",
					CAL_META[entry.kind].text,
				)}
			>
				{CAL_META[entry.kind].label}
			</span>
			<span className="mt-1.5 block font-display text-[13px] font-bold leading-snug text-ink">
				{entry.title}
			</span>
			{(entry.time || entry.meta) && (
				<span className="mt-1 block text-[11.5px] text-slate-body">
					{[entry.time, entry.meta].filter(Boolean).join(" · ")}
				</span>
			)}
			{entry.summary && (
				<span className="mt-2 block text-[11.5px] leading-relaxed text-slate-body">
					{entry.summary}
				</span>
			)}
		</span>
	);
}

/* ------------------------------------------------------------------ pieces */

function StepButton({
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
			className="grid h-8 w-8 place-items-center rounded-lg border border-card-line bg-white text-slate-faint transition hover:border-slate-faint hover:text-ink"
		>
			<Icon.chevron size={15} className={rotate} />
		</button>
	);
}

/** The row of category swatches above the grid. */
export function CalendarLegend({ kinds }: { kinds?: CalKind[] }) {
	const show = kinds ?? [...CAL_KINDS];
	return (
		<div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
			{show.map((k) => (
				<span key={k} className="flex items-center gap-1.5 text-[11px] text-slate-body">
					<span className={cx("h-2 w-2 rounded-[3px]", CAL_META[k].dot)} aria-hidden="true" />
					{CAL_META[k].label}
				</span>
			))}
		</div>
	);
}
