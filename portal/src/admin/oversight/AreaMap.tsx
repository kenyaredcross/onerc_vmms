import { CountyMap } from "../../ui/CountyMap";

import type { AreaRow, MapShapes } from "./types";

/**
 * The whole country, county by county.
 *
 * Drawn from `map_shapes`: the society's own boundary file, projected on the
 * server into one frame, or a dot per county where no file is attached. The
 * component does not know which country it is drawing.
 *
 * Two ways of colouring, one per tab:
 *
 * - **highlight** (the region tab): the region's counties navy, the rest of the
 *   country a light red, so a regional head sees where their region sits.
 * - **shade** (the national tab): every county a step of red by the chosen
 *   figure, the chosen region's counties navy on top.
 *
 * The chosen county is filled red. Hovering or focusing a county shows its
 * name and figures.
 *
 * **The map is a way in, not the only way.** Every county it can choose is also
 * a row in the table below, which serves a keyboard or screen-reader user
 * better; the shapes are still focusable and named, so the map is not a dead
 * end for them either.
 */
const NAVY = "#011E41";
const NAVY_HOVER = "#2A4A73";
const OUTSIDE = "#F6D3D6";
const RED = "#D71920";
const NONE = "#E8EDF2";
// Lightest to darkest. The darkest is never the brand red, so the chosen
// county stays the one that stands out.
const STEPS = ["#FBE1E3", "#F6B7BD", "#F08891", "#E95662", "#C9303C"];
const MAX_HEIGHT = 620;

export interface Shading {
	/** The figure each county is shaded by. */
	value: (row: AreaRow) => number;
	label: string;
}

export function AreaMap({
	shapes,
	figures,
	highlight,
	active,
	chosen,
	onSelect,
	label,
	highlightLabel,
	shading,
}: {
	shapes: MapShapes;
	/** Figures by county name, for the read-out and the shading. */
	figures: Map<string, AreaRow>;
	/** Drawn navy. */
	highlight: Set<string>;
	/** May be chosen, and carry a read-out. */
	active: Set<string>;
	/** Filled red. */
	chosen: Set<string>;
	onSelect: (county: string) => void;
	label: string;
	/** What the navy means, in the key. */
	highlightLabel: string;
	/** Present on the national tab: shade every county by this figure. */
	shading?: Shading;
}) {
	const breaks = shading ? steps([...figures.values()].map(shading.value)) : [];
	const navy = highlight.size > 0 && (!shading || highlight.size < figures.size);

	const fill = (name: string, hovered: boolean) => {
		if (chosen.has(name)) return RED;
		if (navy && highlight.has(name)) return hovered ? NAVY_HOVER : NAVY;
		if (shading) {
			const county = figures.get(name);
			const value = county ? shading.value(county) : 0;
			if (!value) return NONE;
			const index = breaks.findIndex((top) => value <= top);
			return STEPS[index === -1 ? STEPS.length - 1 : index];
		}
		return OUTSIDE;
	};

	return (
		<div>
			<CountyMap
				shapes={shapes}
				fill={fill}
				interactive={(name) => active.has(name)}
				onSelect={onSelect}
				describe={(name) => {
					const row = figures.get(name);
					return row ? readOut(row) : undefined;
				}}
				readOut={(name) => {
					const row = figures.get(name);
					return row ? <Figures row={row} /> : null;
				}}
				label={label}
				maxHeight={MAX_HEIGHT}
			/>

			<div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-[12px] text-muted">
				{shading ? (
					<span className="flex items-center gap-2">
						{shading.label}
						<span className="flex items-center">
							{STEPS.map((colour, index) => (
								<span key={colour} className="flex flex-col items-center">
									<span aria-hidden="true" className="block h-2.5 w-8" style={{ background: colour }} />
									<span className="mt-0.5 text-[10.5px] tabular-nums text-slate-faint">
										{index === 0 ? 1 : (breaks[index - 1] ?? 0) + 1}
									</span>
								</span>
							))}
						</span>
					</span>
				) : (
					<Key colour={OUTSIDE} label="Rest of the country" />
				)}
				{navy && <Key colour={NAVY} label={highlightLabel} />}
				<Key colour={RED} label="Chosen" />
			</div>

			{!shapes.has_file && (
				<p className="mt-2 text-[11.5px] text-slate-faint">
					Each dot is a county. Attach the county boundaries in the society settings to draw their shapes.
				</p>
			)}
			{shapes.credit && <p className="mt-2 text-[11px] text-slate-faint">{shapes.credit}</p>}
		</div>
	);
}

function Figures({ row }: { row: AreaRow }) {
	return (
		<>
			<div className="mb-1 text-[13px] font-semibold">{row.label}</div>
			<dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-0.5 text-white/75">
				<dt>Volunteers</dt>
				<dd className="text-right font-semibold tabular-nums text-white">{row.volunteers}</dd>
				<dt>Members</dt>
				<dd className="text-right font-semibold tabular-nums text-white">{row.members}</dd>
				<dt>Waiting for approval</dt>
				<dd className="text-right font-semibold tabular-nums text-white">{row.waiting}</dd>
				<dt>Materials lent out</dt>
				<dd className="text-right font-semibold tabular-nums text-white">{row.materials_lent}</dd>
			</dl>
		</>
	);
}

/**
 * Upper bounds of the five shades: equal steps from nothing to the busiest
 * county. Not quintiles, which would always paint a fifth of the country
 * darkest however close the counties are; equal steps keep the shade a
 * statement about the size of the number.
 */
function steps(values: number[]): number[] {
	const max = Math.max(0, ...values);
	if (!max) return [];
	return STEPS.map((_, index) => Math.ceil((max * (index + 1)) / STEPS.length));
}

function Key({ colour, label }: { colour: string; label: string }) {
	return (
		<span className="flex items-center gap-1.5">
			<span aria-hidden="true" className="inline-block h-3 w-3 rounded-[3px]" style={{ background: colour }} />
			{label}
		</span>
	);
}

function readOut(row: AreaRow): string {
	return `${row.label}: ${row.volunteers} volunteers, ${row.members} members, ${row.waiting} waiting for approval`;
}
