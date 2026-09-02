import { NavLink } from "react-router-dom";

import { EditableText } from "../content/Editable";
import { cx } from "../portal/ui/kit";

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
	/** A live count on the right of the row. Omitted when zero. */
	badge?: number;
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
 * **It sits on white now, not on grey.** The console's three columns used to be
 * shell-grey / surface-grey / shell-grey, and the selected row was a white pill
 * lifted off the middle one. In the portal's language the panel is a white
 * surface on the canvas, so a white pill would be invisible: the selected row
 * takes the soft blue wash instead, which is the same "you are here" signal the
 * rest of this world uses.
 *
 * **The same markup serves both layouts.** On a wide screen `ConsoleShell`
 * renders this in a column of its own; below `lg` it renders the same component
 * inside a horizontal scroller under the header, and `horizontal` switches the
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
	const row = (isActive: boolean) =>
		cx(
			"flex min-h-[34px] items-center gap-2 rounded-lg px-3 py-1.5 text-[12.5px] transition-colors",
			isActive
				? "bg-blue-soft font-semibold text-blue-press"
				: "font-medium text-slate-strong hover:bg-canvas hover:text-ink",
		);

	const count = (badge?: number) =>
		badge !== undefined && badge > 0 ? (
			<span className="tabular ml-auto text-[11px] font-semibold text-muted">{badge > 99 ? "99+" : badge}</span>
		) : null;

	if (horizontal) {
		return (
			<nav aria-label={`${title} sections`} className="flex w-max items-center gap-1 py-0.5">
				{items.map((item) => (
					<NavLink
						key={item.to}
						to={item.to}
						end={item.end}
						className={({ isActive }) => cx(row(isActive), "whitespace-nowrap")}
					>
						<EditableText k={item.labelKey} fallback={item.fallback} />
						{count(item.badge)}
					</NavLink>
				))}
			</nav>
		);
	}

	return (
		<div className="flex flex-col">
			<h2 className="px-3 pb-3.5 pt-1 text-[14px] font-semibold tracking-[-0.01em] text-ink">{title}</h2>

			<nav aria-label={`${title} sections`} className="flex flex-col gap-0.5">
				{items.map((item, index) => {
					const previous = items[index - 1];
					const started = item.groupKey && item.groupKey !== previous?.groupKey;

					return (
						<div key={item.to}>
							{started && (
								<div className="px-3 pb-1 pt-4 text-[10px] font-semibold uppercase tracking-[0.09em] text-rail-label">
									<EditableText k={item.groupKey as string} fallback={item.groupFallback ?? ""} />
								</div>
							)}

							<NavLink to={item.to} end={item.end} className={({ isActive }) => row(isActive)}>
								<EditableText k={item.labelKey} fallback={item.fallback} className="min-w-0 truncate" />
								{count(item.badge)}
							</NavLink>
						</div>
					);
				})}
			</nav>
		</div>
	);
}
