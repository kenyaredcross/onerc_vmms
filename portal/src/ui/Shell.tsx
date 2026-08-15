import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { EditableText } from "../content/Editable";
import { EditToolbar } from "../content/EditToolbar";
import { initials, useSession } from "../lib/session";
import { BrandLockup } from "./brand";
import { Icon } from "./icons";
import { cx } from "./primitives";

export interface NavItem {
	to: string;
	/** Content key for the label, so a society renames its own navigation. */
	labelKey: string;
	fallback: string;
	icon: (props: { size?: number; className?: string }) => ReactNode;
	/** Shown as a count chip on the right of the item. */
	badge?: number;
	end?: boolean;
	/**
	 * The heading this item sits under.
	 *
	 * A label is drawn whenever `groupKey` differs from the previous item's, so
	 * a caller declares grouping by *ordering* rather than by nesting arrays.
	 * Omit it throughout and the navigation is one ungrouped list, which is what
	 * the console passes.
	 *
	 * Nine flat tabs is the shape this sidebar had, and nine things with no
	 * headings is a list somebody reads top to bottom every time rather than
	 * jumping to the third of three short groups.
	 */
	groupKey?: string;
	groupFallback?: string;
}

/**
 * A tab that leaves this app entirely.
 *
 * Learning, chat and the service desk are separate Frappe apps, each mounted at
 * its own route, and a link to one is a real navigation rather than a client
 * route. They are a distinct type rather than a flag on `NavItem` so the two
 * cannot be confused at a call site: a `NavLink` pointed at `/lms` would render
 * an app-shaped hole where the LMS should be, and it would do it silently.
 *
 * Neither the route nor the label is written down in the frontend. Both come
 * from `api/companions.py`, which reads each app's own `add_to_apps_screen`
 * declaration, so a remounted LMS moves its own tab.
 */
export interface CompanionItem {
	app: string;
	href: string;
	labelKey: string;
	fallback: string;
}

/** Where the bell in the top bar points, and what it is carrying. */
export interface BellProps {
	to: string;
	count: number;
	labelKey: string;
	fallback: string;
}

const TOPBAR = 60;

/**
 * The signed-in chrome, for both the volunteer portal and the coordinator
 * console.
 *
 * **Three zones, which is the arrangement the reference set uses and the reason
 * its screens do not run out of room.** A full-width bar across the top carries
 * the society's lockup and the person's own controls; a coloured rail down the
 * left carries the society's work; the rest is the screen. The bar spans *over*
 * the rail rather than beside it, so the lockup sits at the origin of the page
 * and the rail is free to be only navigation.
 *
 * One component with a `tone`, rather than two shells that drift apart. The
 * design distinguishes the two surfaces by depth: the volunteer portal's rail
 * is the brand navy, the coordinator's is nearly black, and that difference is
 * the only signal a person needs that they are now acting on somebody else's
 * records. Everything else about the two is the same, and duplicating it would
 * mean fixing every focus ring twice.
 *
 * `subtitle` is the person's placement, which is real information rather than
 * decoration: a coordinator who covers two branches needs to see which one this
 * session is scoped to.
 *
 * **The avatar is a menu, not a label**, and it is in the top-right corner
 * because that is where a person looks for themselves. It used to be pinned to
 * the foot of the rail, on the same reasoning — the rail is where somebody
 * looks for the society's work, the corner is where they look for themselves —
 * and the top-right is more that corner than the bottom-left ever was. Profile
 * and sign out live behind it together: they are the same kind of thing, and a
 * destructive action sitting permanently under the navigation is one mis-click
 * from ending a session.
 */
export function Shell({
	items,
	companions = [],
	bell,
	console: console_,
	desk,
	tone,
	subtitle,
}: {
	items: NavItem[];
	companions?: CompanionItem[];
	/**
	 * The notifications control, or nothing.
	 *
	 * A bell in the corner rather than a tab in the rail, because "what has
	 * arrived for me" is the one thing a person wants from every screen rather
	 * than from a screen. It carries its own count, so the rail does not have to
	 * hold a tab whose only purpose is to wear a number.
	 */
	bell?: BellProps | null;
	/**
	 * Where the console switch points, or nothing at all.
	 *
	 * A route rather than a boolean, so this component never writes down where
	 * the other surface lives, and never decides who may go there — the caller
	 * passes it only when `api/console.py::sections` said `available`. A person
	 * holding no staff role gets no button, which is the same answer
	 * `AdminLayout` gives them if they arrive by typing the address.
	 */
	console?: string | null;
	/**
	 * Where the Frappe desk is, for whoever may open it, or nothing.
	 *
	 * A real navigation out of the SPA rather than a route, like the companion
	 * apps above — and passed only when the server said so. `api/console.py`
	 * answers with the same function that gates the VMMS tile on the apps
	 * screen, so this is never drawn for somebody who would get a permission
	 * error at the other end.
	 */
	desk?: string | null;
	tone: "portal" | "admin";
	subtitle?: string | null;
}) {
	const { user, logout } = useSession();
	const [open, setOpen] = useState(false);
	const [menu, setMenu] = useState(false);
	const account = useRef<HTMLDivElement>(null);
	const dark = tone === "admin";

	const rail = dark ? "bg-navy-deep" : "bg-navy";

	// A menu that stays open after you have clicked past it is a menu that
	// covers the thing you were trying to reach. Escape closes it too, because a
	// pointer is not the only way in.
	useEffect(() => {
		if (!menu) return;

		function onPointer(event: MouseEvent) {
			if (!account.current?.contains(event.target as Node)) setMenu(false);
		}

		function onKey(event: KeyboardEvent) {
			if (event.key === "Escape") setMenu(false);
		}

		document.addEventListener("mousedown", onPointer);
		document.addEventListener("keydown", onKey);

		return () => {
			document.removeEventListener("mousedown", onPointer);
			document.removeEventListener("keydown", onKey);
		};
	}, [menu]);

	/**
	 * A rail item.
	 *
	 * The active one is a filled pill and its icon takes the signal colour: on
	 * navy, red is the only hue with enough separation to be read at 16px, and
	 * it is the app's own accent rather than a second one invented for the
	 * navigation.
	 */
	const link = (isActive: boolean) =>
		cx(
			"group flex items-center gap-3 rounded-full px-3.5 py-2.5 text-[12.5px] transition",
			isActive
				? "bg-white/[.13] font-bold text-white"
				: "font-semibold text-white/60 hover:bg-white/[.07] hover:text-white",
		);

	const groupLabel = "px-3.5 pb-1.5 pt-5 text-[9.5px] font-bold uppercase tracking-[0.14em] text-white/35 first:pt-1";

	return (
		<div className="min-h-screen bg-page">
			{/* ------------------------------------------------------------ top bar */}
			<header
				className="sticky top-0 z-40 flex items-center gap-3 border-b border-hairline bg-white px-4 md:px-6"
				style={{ height: TOPBAR }}
			>
				<button
					type="button"
					onClick={() => setOpen(!open)}
					aria-label={open ? "Close navigation" : "Open navigation"}
					aria-expanded={open}
					className="-ml-1 grid h-9 w-9 flex-none place-items-center rounded-full text-slate-body transition hover:bg-page hover:text-navy md:hidden"
				>
					{open ? <Icon.cross size={18} /> : <Icon.menu size={18} />}
				</button>

				<Link to={console_ === "/dashboard" ? "/admin" : "/dashboard"} className="min-w-0">
					<BrandLockup tone="light" />
				</Link>

				<div className="ml-auto flex items-center gap-1 sm:gap-2">
					{bell && (
						<NavLink
							to={bell.to}
							className={({ isActive }) =>
								cx(
									"relative grid h-10 w-10 place-items-center rounded-full transition",
									isActive
										? "bg-navy/[.08] text-navy"
										: "text-slate-body hover:bg-page hover:text-navy",
								)
							}
							aria-label={`${bell.fallback}${bell.count > 0 ? ` (${bell.count} unread)` : ""}`}
						>
							<Icon.bell size={19} />
							{bell.count > 0 && (
								<span className="absolute right-1 top-1 grid h-[17px] min-w-[17px] place-items-center rounded-full bg-signal px-1 text-[9.5px] font-bold leading-none text-white ring-2 ring-white">
									{bell.count > 99 ? "99+" : bell.count}
								</span>
							)}
						</NavLink>
					)}

					<div ref={account} className="relative">
						<button
							type="button"
							onClick={() => setMenu(!menu)}
							aria-haspopup="menu"
							aria-expanded={menu}
							className="flex items-center gap-2.5 rounded-full py-1 pl-1 pr-1 transition hover:bg-page sm:pr-3"
						>
							<span className="grid h-9 w-9 flex-none place-items-center rounded-full bg-navy font-display text-[12px] font-bold text-white">
								{initials(user) || "?"}
							</span>

							<span className="hidden min-w-0 text-left sm:block">
								<span className="block max-w-[170px] truncate text-[12.5px] font-bold text-ink">
									{user}
								</span>
								{subtitle && (
									<span className="block max-w-[170px] truncate text-[10.5px] text-slate-faint">
										{subtitle}
									</span>
								)}
							</span>

							<Icon.chevron
								size={14}
								className={cx(
									"hidden flex-none text-slate-faint transition sm:block",
									menu && "rotate-180",
								)}
							/>
						</button>

						{menu && (
							<div
								role="menu"
								className="absolute right-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-card border border-hairline bg-white py-1.5 shadow-pop"
							>
								<div className="border-b border-hairline-soft px-4 pb-2.5 pt-1.5 sm:hidden">
									<div className="truncate text-[12.5px] font-bold text-ink">{user}</div>
									{subtitle && (
										<div className="truncate text-[10.5px] text-slate-faint">{subtitle}</div>
									)}
								</div>

								<Link
									to="/profile"
									role="menuitem"
									onClick={() => {
										setMenu(false);
										setOpen(false);
									}}
									className="flex items-center gap-3 px-4 py-2.5 text-[12.5px] font-semibold text-slate-strong transition hover:bg-page hover:text-navy"
								>
									<Icon.user size={15} />
									<EditableText k="portal.nav.profile" fallback="Profile" />
								</Link>

								<button
									type="button"
									role="menuitem"
									onClick={() => {
										// Frappe clears the session cookie; a hard navigation is
										// wanted here so nothing stale survives in memory.
										void logout().then(() => {
											window.location.href = "/";
										});
									}}
									className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-[12.5px] font-semibold text-slate-strong transition hover:bg-page hover:text-signal"
								>
									<Icon.signout size={15} />
									<EditableText k="chrome.action.signout" fallback="Sign out" />
								</button>
							</div>
						)}
					</div>
				</div>
			</header>

			<div className="md:flex">
				{/* --------------------------------------------------------------- rail */}
				{/* The rail is its own scroll region below the bar. `overflow-y-auto`
				    is unconditional: on a phone it is a drawer of the same height, and
				    a society with companion apps installed can put more in it than a
				    short screen holds. */}
				<aside
					className={cx(
						"z-30 w-full flex-none flex-col overflow-y-auto px-3 pb-5 pt-3 md:sticky md:flex md:w-[238px]",
						rail,
						open ? "flex" : "hidden",
					)}
					style={{ top: TOPBAR, height: `calc(100vh - ${TOPBAR}px)` }}
				>
					<nav aria-label="Sections" className="flex flex-col gap-0.5">
						{items.map((item, index) => {
							const started = item.groupKey && item.groupKey !== items[index - 1]?.groupKey;

							return (
								<Fragment key={item.to}>
									{started && (
										<div className={groupLabel}>
											<EditableText
												k={item.groupKey as string}
												fallback={item.groupFallback ?? ""}
											/>
										</div>
									)}

									<NavLink
										to={item.to}
										end={item.end}
										onClick={() => setOpen(false)}
										className={({ isActive }) => link(isActive)}
									>
										{({ isActive }) => (
											<>
												<span
													className={cx(
														"flex-none transition",
														isActive ? "text-signal" : "text-white/55 group-hover:text-white/80",
													)}
												>
													<item.icon size={17} />
												</span>

												<EditableText k={item.labelKey} fallback={item.fallback} className="flex-1" />

												{item.badge !== undefined && item.badge > 0 && (
													<span className="rounded-full bg-signal px-1.5 py-0.5 text-[10px] font-bold leading-none text-white">
														{item.badge > 99 ? "99+" : item.badge}
													</span>
												)}
											</>
										)}
									</NavLink>
								</Fragment>
							);
						})}
					</nav>

					{companions.length > 0 && (
						<>
							{/* Separated, because these leave the app. Somebody who clicks
							    Learning lands in another product with its own navigation,
							    and the back button is how they return; a tab that behaves
							    differently should look different before it is clicked. */}
							<div className={groupLabel}>
								<EditableText k="portal.nav.companions" fallback="Also available" />
							</div>
							<nav aria-label="Other apps" className="flex flex-col gap-0.5">
								{companions.map((item) => (
									<a
										key={item.app}
										href={item.href}
										onClick={() => setOpen(false)}
										className={link(false)}
									>
										<span className="flex-none text-white/55">
											<Icon.external size={17} />
										</span>
										<EditableText k={item.labelKey} fallback={item.fallback} className="flex-1" />
									</a>
								))}
							</nav>
						</>
					)}

					{/* The way across to the other surface, and it is drawn from the
					    server's answer rather than from a role this file names —
					    `api/console.py::sections`, the same call `AdminLayout` filters its
					    own tabs with, so the button and the console it opens can never
					    disagree about whether somebody has one.

					    Pinned to the foot of the rail, because it is not one of this
					    surface's screens: it is a change of surface, the same kind of move
					    as the companion links, and the one thing a coordinator was
					    previously expected to do by typing an address they had to be
					    told. */}
					{(console_ || desk) && (
						<div className="mt-auto flex flex-col gap-1 border-t border-white/[.12] pt-4">
							{console_ && (
								<Link
									to={console_}
									onClick={() => setOpen(false)}
									className="flex items-center gap-3 rounded-full bg-white/[.10] px-3.5 py-2.5 text-[12.5px] font-bold text-white transition hover:bg-white/[.18]"
								>
									{/* The switch reads in the direction it goes, and which
									    direction that is follows the tone rather than a second
									    prop: the dark shell is the console, so its button can
									    only be the way back. Both labels are content blocks
									    like every other word in the product. */}
									<span className="flex-none text-signal">
										{dark ? <Icon.user size={17} /> : <Icon.lock size={17} />}
									</span>
									<EditableText
										k={dark ? "admin.nav.portal" : "portal.nav.console"}
										fallback={dark ? "My portal" : "Manager console"}
										className="flex-1"
									/>
									<Icon.chevron size={14} className="-rotate-90 flex-none text-white/50" />
								</Link>
							)}

							{desk && (
								<a href={desk} className={link(false)}>
									<span className="flex-none text-white/55">
										<Icon.external size={17} />
									</span>
									<EditableText k="admin.nav.desk" fallback="Desk" className="flex-1" />
								</a>
							)}
						</div>
					)}
				</aside>

				<main className="min-w-0 flex-1 px-5 py-7 md:px-8 md:py-9">
					<Outlet />
				</main>
			</div>

			<EditToolbar />
		</div>
	);
}
