import { NavLink } from "react-router-dom";

import { EditableText } from "../content/Editable";
import { cx } from "./primitives";

/**
 * One destination inside a section's own navigation.
 *
 * `to` is a real route, never a tab index. Every screen a section owns has an
 * address somebody can link, bookmark and reach with the back button — which is
 * the whole reason this is a routed panel rather than component state.
 */
export interface SubNavItem {
	to: string;
	labelKey: string;
	fallback: string;
	end?: boolean;
	/** The heading this item sits under. Declared by ordering, like the rail's. */
	groupKey?: string;
	groupFallback?: string;
}

/**
 * A section's own navigation, shown between the global rail and the content.
 *
 * **What it is for.** A handful of destinations in the product are not one
 * screen but a small application of their own — Deployments has a dashboard,
 * two registers, a creation flow and a request queue. Hanging six more rows off
 * the global rail would bury every other section; nesting them as tabs inside
 * one page would give six screens one address. So the section gets a column,
 * and the global rail collapses to icons beside it — the global destinations
 * stay one click away as icons rather than being replaced.
 *
 * **The same markup serves both layouts.** On a wide screen `Shell` renders
 * this in a column of its own; below `lg` it renders the same component inside
 * a horizontal scroller under the top row, and `horizontal` switches the
 * arrangement. One component rather than two, because two would drift.
 */
export function SubNav({
	title,
	items,
	horizontal = false,
}: {
	/** The section's name, above its destinations. */
	title: string;
	items: SubNavItem[];
	horizontal?: boolean;
}) {
	if (horizontal) {
		return (
			<nav aria-label={`${title} sections`} className="flex w-max items-center gap-1.5 py-0.5">
				{items.map((item) => (
					<NavLink
						key={item.to}
						to={item.to}
						end={item.end}
						className={({ isActive }) =>
							cx(
								"whitespace-nowrap rounded-full px-3.5 py-2 text-[12.5px] transition-colors",
								isActive
									? "bg-white font-medium text-blue shadow-nav"
									: "font-normal text-slate-strong hover:bg-white/70",
							)
						}
					>
						<EditableText k={item.labelKey} fallback={item.fallback} />
					</NavLink>
				))}
			</nav>
		);
	}

	return (
		<div className="flex flex-col">
			<h2 className="px-3.5 pb-4 pt-1 font-display text-[15px] font-medium tracking-tight text-ink">
				{title}
			</h2>

			<nav aria-label={`${title} sections`} className="flex flex-col gap-0.5">
				{items.map((item, index) => {
					const previous = items[index - 1];
					const started = item.groupKey && item.groupKey !== previous?.groupKey;

					return (
						<div key={item.to}>
							{started && (
								<div className="px-3.5 pb-1.5 pt-4 text-[9.5px] font-semibold uppercase tracking-[0.14em] text-slate-faint">
									<EditableText k={item.groupKey as string} fallback={item.groupFallback ?? ""} />
								</div>
							)}

							<NavLink
								to={item.to}
								end={item.end}
								className={({ isActive }) =>
									cx(
										"block rounded-full px-3.5 py-2 text-[12.5px] transition-colors",
										isActive
											? "bg-white font-medium text-blue shadow-nav"
											: "font-normal text-slate-strong hover:bg-white/70 hover:text-ink",
									)
								}
							>
								<EditableText k={item.labelKey} fallback={item.fallback} />
							</NavLink>
						</div>
					);
				})}
			</nav>
		</div>
	);
}
