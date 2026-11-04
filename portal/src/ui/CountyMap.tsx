import { useState, type KeyboardEvent, type ReactNode } from "react";

/**
 * A country drawn county by county, from shapes the server has projected.
 *
 * The drawing only: what each county is coloured, whether it can be chosen and
 * what its read-out says all belong to the screen using it. The console's
 * Region and National tabs and the public locations directory both draw
 * through this, so the country looks the same wherever it appears.
 *
 * Shapes come from the society's attached boundary file, or a dot per county
 * where none is attached. Nothing here knows which country it is.
 */
export interface CountyShapes {
	view_box: string;
	shapes: Array<{ name: string; path: string | null; centre: [number, number] }>;
	has_file: boolean;
	credit: string | null;
}

export const MAP_NAVY = "#011E41";
export const MAP_RED = "#D71920";

export function CountyMap({
	shapes,
	fill,
	interactive,
	onSelect,
	describe,
	readOut,
	label,
	maxHeight = 620,
}: {
	shapes: CountyShapes;
	/** The colour of a county, told whether the pointer is on it. */
	fill: (name: string, hovered: boolean) => string;
	interactive: (name: string) => boolean;
	onSelect: (name: string) => void;
	/** What a screen reader hears for a county it can choose. */
	describe: (name: string) => string | undefined;
	/** The read-out shown above a hovered or focused county. */
	readOut: (name: string) => ReactNode;
	label: string;
	maxHeight?: number;
}) {
	const [hover, setHover] = useState<string | null>(null);
	const [, , width, height] = shapes.view_box.split(" ").map(Number);
	const shown = hover ? shapes.shapes.find((shape) => shape.name === hover) : undefined;
	const content = shown ? readOut(shown.name) : null;
	const dot = Math.max(width, height) / 70;

	const keys = (name: string) => (event: KeyboardEvent) => {
		if (event.key === "Enter" || event.key === " ") {
			event.preventDefault();
			onSelect(name);
		}
	};

	return (
		// Sized to the country's own proportions, so the read-out's position (a
		// percentage of the frame) lands on the county it describes.
		<div className="relative mx-auto" style={{ maxWidth: `${(maxHeight * width) / height}px` }}>
			<svg viewBox={shapes.view_box} className="block h-auto w-full" role="group" aria-label={label}>
				{shapes.shapes.map((shape) => {
					const active = interactive(shape.name);
					const common = {
						fill: fill(shape.name, hover === shape.name),
						stroke: "#FFFFFF",
						strokeWidth: 1,
						strokeLinejoin: "round" as const,
						className: active ? "cursor-pointer outline-none transition-[fill] duration-150" : undefined,
						tabIndex: active ? 0 : undefined,
						role: active ? "button" : undefined,
						"aria-label": active ? describe(shape.name) : undefined,
						onMouseEnter: active ? () => setHover(shape.name) : undefined,
						onMouseLeave: active ? () => setHover(null) : undefined,
						onFocus: active ? () => setHover(shape.name) : undefined,
						onBlur: active ? () => setHover(null) : undefined,
						onClick: active ? () => onSelect(shape.name) : undefined,
						onKeyDown: active ? keys(shape.name) : undefined,
					};

					return shape.path ? (
						<path key={shape.name} d={shape.path} {...common} />
					) : (
						<circle key={shape.name} cx={shape.centre[0]} cy={shape.centre[1]} r={dot} {...common} />
					);
				})}

				{/* The hovered county outlined on top, so its edge is not hidden
				    under a neighbour's. */}
				{shown?.path && (
					<path d={shown.path} fill="none" stroke={MAP_NAVY} strokeWidth={2} pointerEvents="none" />
				)}
			</svg>

			{shown && content && (
				<div
					className="pointer-events-none absolute z-10 min-w-[150px] -translate-x-1/2 -translate-y-[calc(100%+12px)] rounded-md bg-[#24272C] px-3 py-2 text-[12px] text-white shadow-lg"
					style={{ left: `${(shown.centre[0] / width) * 100}%`, top: `${(shown.centre[1] / height) * 100}%` }}
					aria-hidden="true"
				>
					{content}
				</div>
			)}
		</div>
	);
}
