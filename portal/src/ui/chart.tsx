import { useState } from "react";

import { cx } from "./primitives";

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
								className={cx("h-1.5 rounded-full", row.value ? "bg-navy" : "bg-transparent")}
								style={{ width: `${(row.value / max) * 100}%` }}
							/>
						</div>
					</div>
					<span className="font-display text-[15px] font-bold tabular-nums text-ink">
						{row.value}
					</span>
				</li>
			))}
		</ul>
	);
}
