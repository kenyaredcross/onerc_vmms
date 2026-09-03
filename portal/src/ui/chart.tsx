import { useState } from "react";

import { cx } from "../portal/ui/kit";

/**
 * The two chart forms this app draws, and deliberately only two.
 *
 * **Every chart here carries one series.** That is not a limitation worked
 * around, it is the decision: two measures on one frame need either a shared
 * scale they do not have or a second axis, and a second y-scale is the single
 * most misread thing in a dashboard. Volunteers and memberships are counted in
 * different units of meaning, so they are drawn as two small multiples side by
 * side, each with its own frame and its own maximum. A reader compares shapes,
 * which is the honest comparison, rather than heights that were never
 * commensurable.
 *
 * One series also means **no legend and no categorical palette**: the title
 * names the series, the mark carries no identity, and there is no adjacent-hue
 * pair that could fail a colour-vision check. Colour is doing no work here at
 * all, which is why it is one recessive navy everywhere.
 *
 * **Values are labelled selectively, never on every mark.** A number over every
 * column is a table pretending to be a chart. The hover layer carries the exact
 * figure, and the axis carries the maximum, which is what somebody reading a
 * shape actually needs.
 */

/** Recessive by design: the data is the ink, the frame is not. */
const AXIS = "#D8DEE9";
const MARK = "#011E41";
const MARK_MUTED = "#C7CEDB";

/**
 * The two-series pair, for the one chart in this product that honestly has two.
 *
 * **Blue is not among them, and neither is green-and-red.** Blue means "act on
 * this" everywhere in the product and a blue data mark would dilute it; green
 * for income and red for expenditure would reuse the reserved status hues *and*
 * put a moral valence on a figure that has none — a society paying its
 * volunteers is not a society doing something wrong.
 *
 * A retoned violet and amber from the `tint` family instead, stepped until they
 * pass every check in the palette validator against this app's canvas:
 * lightness band, chroma floor, adjacent-pair separation under protanopia and
 * tritanopia, normal-vision separation, and 3:1 against the surface. Colour is
 * still never the only signal — the pair is legended, and the read-out names
 * the series in text.
 */
const SERIES_IN = "#6B4FA8";
const SERIES_OUT = "#A9640F";

export interface Column {
	label: string;
	value: number;
	/** The fuller label for the tooltip, where there is room for one. */
	title?: string;
}

/**
 * A column chart over a short, ordered series — months, most usefully.
 *
 * **Laid out with CSS rather than drawn as SVG**, and that is a correctness
 * decision rather than a preference. An SVG that fills its card has to either
 * carry a resize observer or set `preserveAspectRatio="none"`, and the second
 * stretches the geometry with the box: the 4px rounded data-end becomes an
 * ellipse whose shape depends on how wide the reader's window happens to be.
 * Flex children with a percentage height scale on one axis only, so the corner
 * radius and the 2px gap between marks are the same at every width.
 *
 * **An all-zero series still draws its frame.** A branch that recruited nobody
 * this year has a real answer, and a chart that collapsed to nothing would read
 * as a broken screen rather than as a flat line.
 */
export function ColumnChart({
	columns,
	emptyLabel = "Nothing recorded yet",
}: {
	columns: Column[];
	emptyLabel?: string;
}) {
	const [hover, setHover] = useState<number | null>(null);

	if (columns.length === 0) {
		return <p className="py-8 text-center text-[12.5px] text-slate-faint">{emptyLabel}</p>;
	}

	const max = Math.max(...columns.map((column) => column.value), 1);
	const active = hover === null ? null : columns[hover];

	return (
		<figure className="m-0">
			<figcaption className="mb-1.5 flex items-baseline justify-between">
				<span className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">
					Peak {max}
				</span>
				{/* The value read-out, in text ink rather than the mark's colour:
				    a number wearing the series colour is the chart telling the
				    reader that colour means something, and here it does not. */}
				<span className="min-h-[17px] text-[11.5px] font-semibold text-ink" aria-live="polite">
					{active ? `${active.title ?? active.label} · ${active.value}` : ""}
				</span>
			</figcaption>

			<div
				className="flex h-[132px] items-end gap-[2px] border-b"
				style={{ borderColor: AXIS }}
				onMouseLeave={() => setHover(null)}
			>
				{columns.map((column, index) => (
					<button
						key={column.label}
						type="button"
						// The hit target is the full column height, not the mark: a
						// two-pixel bar for a month with one recruit is not
						// something to ask somebody to point at.
						className="group flex h-full flex-1 cursor-default items-end"
						onMouseEnter={() => setHover(index)}
						onFocus={() => setHover(index)}
						onBlur={() => setHover(null)}
						title={`${column.title ?? column.label}: ${column.value}`}
					>
						<span
							className="w-full rounded-t-[3px] transition-colors"
							style={{
								// A zero is drawn as nothing rather than as a sliver,
								// so "none this month" and "one this month" cannot be
								// confused. A non-zero always gets 2px, so the
								// smallest real value is still visible.
								height: column.value ? `max(${(column.value / max) * 100}%, 2px)` : 0,
								background: hover === null || hover === index ? MARK : MARK_MUTED,
							}}
						/>
					</button>
				))}
			</div>

			<div className="mt-1 flex justify-between text-[10px] text-slate-faint">
				<span>{columns[0]?.label}</span>
				<span>{columns[columns.length - 1]?.label}</span>
			</div>
		</figure>
	);
}

/**
 * One labelled row with a proportional bar behind its count.
 *
 * For a breakdown across the states of a closed vocabulary, where the reader's
 * question is "which of these is most of it" rather than "how has it moved".
 * The bar is scaled against the largest row rather than the total, because a
 * breakdown with one dominant state would otherwise render every other row as
 * an invisible sliver.
 *
 * **Zero rows are drawn, not dropped.** A breakdown that omitted its empty
 * states would change shape as records moved through them, and a list whose
 * rows appear and disappear between refreshes cannot be read at all.
 */
export function BarRows({
	rows,
	emptyLabel = "Nothing recorded yet",
}: {
	rows: Array<{ label: string; value: number }>;
	emptyLabel?: string;
}) {
	if (rows.length === 0) {
		return <p className="py-6 text-center text-[12.5px] text-slate-faint">{emptyLabel}</p>;
	}

	const max = Math.max(...rows.map((row) => row.value), 1);

	return (
		<ul className="space-y-2">
			{rows.map((row) => (
				<li key={row.label} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3">
					<div>
						<div className="mb-1 truncate text-[12px] font-semibold capitalize text-slate-strong">
							{row.label}
						</div>
						<div className="h-1.5 w-full rounded-full bg-surface">
							<div
								className={cx("h-1.5 rounded-full", row.value ? "bg-rail" : "bg-transparent")}
								style={{ width: `${(row.value / max) * 100}%` }}
							/>
						</div>
					</div>
					<span className="text-[15px] font-bold tabular-nums text-ink">
						{row.value}
					</span>
				</li>
			))}
		</ul>
	);
}

/**
 * Two commensurable series over the same months, on one shared axis.
 *
 * **The one exception to this module's single-series rule, and it is a narrow
 * one.** The rule at the top of this file exists because two measures on one
 * frame need a shared scale they usually do not have — volunteers and
 * memberships are counted in different units of meaning, so putting them on one
 * axis invites a comparison that was never valid. Money in and money out are
 * not that case: they are the same unit, in the same currency, over the same
 * months, and "was more paid out than came in" is *the* question the chart is
 * being asked. One axis, one maximum, two marks per month.
 *
 * It is still never a dual axis. The two series share a scale because they are
 * the same quantity, not because a second scale was added to make them fit.
 *
 * **A legend is always drawn**, because there are two series and colour alone
 * may not carry identity. The hover read-out names the series in words as well.
 * A 2px gap sits between the paired marks so the two are separable in print, in
 * greyscale and under `forced-colors`, where the fills collapse.
 */
export function PairedColumnChart({
	months,
	labels,
	currency,
	emptyLabel = "Nothing recorded in this period",
}: {
	months: Array<{ label: string; title?: string; a: number; b: number }>;
	/** What each series is called. Used in the legend and in the read-out. */
	labels: { a: string; b: string };
	/** For the read-out, so a figure is never shown without its money. */
	currency?: string | null;
	emptyLabel?: string;
}) {
	const [hover, setHover] = useState<number | null>(null);

	if (months.length === 0) {
		return <p className="py-8 text-center text-[12.5px] text-slate-faint">{emptyLabel}</p>;
	}

	const max = Math.max(...months.flatMap((month) => [month.a, month.b]), 1);
	const active = hover === null ? null : months[hover];

	const money = (value: number) =>
		currency
			? new Intl.NumberFormat(undefined, {
					style: "currency",
					currency,
					maximumFractionDigits: 0,
				}).format(value)
			: value.toLocaleString();

	/** One mark. Zero is drawn as nothing so "none" and "a little" cannot be confused. */
	const mark = (value: number, colour: string, dimmed: boolean) => (
		<span
			className="w-full rounded-t-[4px] transition-colors"
			style={{
				height: value ? `max(${(value / max) * 100}%, 2px)` : 0,
				background: dimmed ? MARK_MUTED : colour,
			}}
		/>
	);

	return (
		<figure className="m-0">
			<figcaption className="mb-2 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
				<span className="flex items-center gap-3.5">
					{[
						{ colour: SERIES_IN, label: labels.a },
						{ colour: SERIES_OUT, label: labels.b },
					].map((entry) => (
						<span key={entry.label} className="flex items-center gap-1.5 text-[11px] font-medium text-muted">
							<span
								aria-hidden="true"
								className="h-2 w-2 flex-none rounded-[2px]"
								style={{ background: entry.colour }}
							/>
							{entry.label}
						</span>
					))}
				</span>

				{/* The read-out, in text ink rather than a series colour: a number
				    wearing the mark's colour tells the reader the colour carries the
				    value, and it does not — it carries which series. */}
				<span className="min-h-[17px] text-[11.5px] font-semibold text-ink" aria-live="polite">
					{active
						? `${active.title ?? active.label} · ${labels.a} ${money(active.a)} · ${labels.b} ${money(active.b)}`
						: `Peak ${money(max)}`}
				</span>
			</figcaption>

			<div
				className="flex h-[150px] items-end gap-[3px] border-b"
				style={{ borderColor: AXIS }}
				onMouseLeave={() => setHover(null)}
			>
				{months.map((month, index) => (
					<button
						key={month.label}
						type="button"
						// The hit target is the full column height, not the mark: a
						// two-pixel bar for a quiet month is not something to ask
						// somebody to point at.
						className="flex h-full flex-1 cursor-default items-end gap-[2px]"
						onMouseEnter={() => setHover(index)}
						onFocus={() => setHover(index)}
						onBlur={() => setHover(null)}
						title={`${month.title ?? month.label}: ${labels.a} ${money(month.a)}, ${labels.b} ${money(month.b)}`}
					>
						{mark(month.a, SERIES_IN, hover !== null && hover !== index)}
						{mark(month.b, SERIES_OUT, hover !== null && hover !== index)}
					</button>
				))}
			</div>

			<div className="mt-1.5 flex justify-between text-[10.5px] text-slate-faint">
				<span>{months[0]?.label}</span>
				<span>{months[months.length - 1]?.label}</span>
			</div>
		</figure>
	);
}
