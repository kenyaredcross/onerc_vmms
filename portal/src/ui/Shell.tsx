import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { EditableText } from "../content/Editable";
import { EditToolbar } from "../content/EditToolbar";
import { firstName, initials, useSession } from "../lib/session";
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
 * A `NavItem` with its own page, that also collapses a clutch of others under
 * it — the console's Registry-and-Analytics style grouping, not the portal's
 * plain headed list.
 *
 * **Not the same thing as `groupKey`.** A `groupKey` heading is a label over
 * flat siblings that were always going to be shown; nobody expands or
 * collapses it, and `PortalLayout` still uses it exactly that way. A
 * `NavGroup` is a real parent: it has a route of its own, it is a `NavLink`
 * like any other item, and clicking it both opens that route and reveals
 * `children` indented beneath it. The two coexist in one `items` array because
 * they answer different questions — "which heading is this under" against
 * "is there more here than the row shows" — and a screen with a real hierarchy
 * should not have to fake one out of a label.
 *
 * **Expansion follows the route, not a click somebody has to remember to
 * repeat.** A group is open whenever the current page is the group's own or
 * one of `children`'s, so arriving at a child page — by a bookmark, a link
 * from elsewhere, or the browser's back button — always shows it in place
 * rather than nested inside a heading collapsed shut. The chevron is a manual
 * override on top of that default, for glancing at what else is here without
 * leaving the page you are on; see `Shell`'s own `openGroups` state.
 */
export interface NavGroup extends Omit<NavItem, "groupKey" | "groupFallback"> {
	children: NavItem[];
}

function isGroup(item: NavItem | NavGroup): item is NavGroup {
	return "children" in item;
}

/** Is `pathname` the group's own route, or one of `base`'s pages? */
function within(pathname: string, base: string): boolean {
	return pathname === base || pathname.startsWith(`${base}/`);
}

/**
 * Which rail item `pathname` belongs to, for the top bar's own title — the
 * same question `within` answers for one item, asked of every leaf and group
 * child at once. Longest `to` wins: `/admin` is `within` almost every admin
 * route, so without this a detail page nested under a specific tab would read
 * back as whichever tab happens to sort first rather than the one it is
 * actually inside.
 */
function currentTab(pathname: string, items: (NavItem | NavGroup)[]): NavItem | null {
	let best: NavItem | null = null;

	const consider = (item: NavItem) => {
		if (within(pathname, item.to) && (!best || item.to.length > best.to.length)) best = item;
	};

	for (const item of items) {
		consider(item);
		if (isGroup(item)) item.children.forEach(consider);
	}

	return best;
}

/** Icon, label and badge — the content every rail row carries, group or leaf. */
function railContent(item: NavItem, isActive: boolean) {
	return (
		<>
			<span
				className={cx(
					"flex-none transition-colors duration-200",
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
	);
}

/**
 * The chevron that opens or closes a `NavGroup`, on its own — never the row's
 * `NavLink` — for the reason `Pencil` in `content/Editable.tsx` gives: a
 * `button` inside an `a` is invalid HTML, so this is a `span` carrying
 * `role="button"` instead, and it stops the click before the link beneath it
 * ever sees it.
 */
function GroupToggle({ expanded, onToggle }: { expanded: boolean; onToggle: () => void }) {
	const fire = (event: { preventDefault: () => void; stopPropagation: () => void }) => {
		event.preventDefault();
		event.stopPropagation();
		onToggle();
	};

	return (
		<span
			role="button"
			tabIndex={0}
			onClick={fire}
			onKeyDown={(event) => {
				if (event.key === "Enter" || event.key === " ") fire(event);
			}}
			aria-label={expanded ? "Collapse" : "Expand"}
			className="flex-none rounded-full p-1 text-white/40 transition-colors duration-200 hover:bg-white/10 hover:text-white/80"
		>
			<Icon.chevron size={13} className={cx("transition-transform duration-200", expanded && "rotate-180")} />
		</span>
	);
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

// The margin every floating surface keeps from the viewport edge and from
// each other — the page's own inset, the gap between the rail and the pill,
// and the rail's own clearance top and bottom. One number so the two never
// drift apart in the calc() arithmetic below that leans on it.
const GUTTER = 16;

/**
 * The signed-in chrome, for both the volunteer portal and the coordinator
 * console.
 *
 * **Three zones, floated apart rather than fused.** A rounded rail down the
 * left carries the society's work, its own lockup anchoring the top of it —
 * identity and the navigation that speaks for it are one surface, not a
 * header's height apart. A pill-shaped bar to its right carries the person's
 * own controls, clear of the rail and of the right edge by the same margin
 * `GUTTER` keeps everywhere else. The rest is the screen. Neither surface
 * touches the glass; both sit on the page the way the reference design the
 * request pointed at does, which is the one idea this shell borrows from it
 * wholesale.
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
	sms,
	tone,
	subtitle,
	person,
}: {
	items: (NavItem | NavGroup)[];
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
	/**
	 * Where onerc_sms's own campaign builder is, for whoever may open it, or
	 * nothing.
	 *
	 * The same shape as `desk` and for the same reason: a real navigation out
	 * of the SPA, passed only when the server said so, so this is never drawn
	 * for somebody who would get a permission error at the other end.
	 * Narrower than `desk` — it names one form on a companion app vmmsx does
	 * not require, not the whole framework — so it is its own prop rather
	 * than folded into that one.
	 */
	sms?: string | null;
	tone: "portal" | "admin";
	subtitle?: string | null;
	/**
	 * This person's own name, from their Red Profile — what the society calls
	 * them, rather than what they sign in as.
	 *
	 * The greeting and the avatar were both built from `session.user` alone, which
	 * on almost every site is an email address: `firstName` split it at the `@`
	 * and again at the first separator, so somebody whose login was
	 * `nigelnathann3@…` was greeted every morning as "Nigelnathann3". The society
	 * knows what this person is called — it asked them on the way in — so this is
	 * what it says. The email-derived guess stays as the fallback for the moment
	 * before the profile arrives, and for anybody who has not registered for
	 * anything yet and therefore has no profile at all.
	 */
	person?: string | null;
}) {
	const { user, logout } = useSession();
	const location = useLocation();
	const [open, setOpen] = useState(false);
	const [menu, setMenu] = useState(false);
	// A group's own manual override, keyed by its route. Absent means "follow
	// the current page" — see `NavGroup`'s own docstring — present means
	// somebody clicked the chevron and this group now ignores that default
	// until they click it again.
	const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
	const account = useRef<HTMLDivElement>(null);
	const dark = tone === "admin";

	const rail = dark ? "bg-navy-deep" : "bg-navy";
	// The badge on the bell sits half off the top bar, so its ring has to match
	// whichever navy the bar is wearing — a white one would read as a halo
	// pasted on top rather than a coin cut into the surface underneath it.
	const railRing = dark ? "ring-navy-deep" : "ring-navy";

	// Where the brand mark takes you, wherever it is drawn — the rail's own
	// header on a wide screen, the top bar's on a narrow one. Not really "the
	// other surface": `console_` doubles as a tone signal here (see its own
	// prop doc), so this always lands on *this* surface's home page.
	const home = console_ === "/dashboard" ? "/admin" : "/dashboard";

	// What the top bar says beside the controls. "Good morning, Brian" is the
	// one line of the reference design that lives in the top bar rather than
	// on a page, so it stood in for every screen at first — but a coordinator
	// three tabs deep in Operations does not need reminding what time of day
	// it is, they need to know they are still looking at Tasks. So: the
	// greeting is a *front door*, drawn only on the surface's own home page,
	// and every other page names itself the way its own rail row does.
	const current = currentTab(location.pathname, items);

	const topBarTitle =
		current && current.to !== home ? (
			<EditableText k={current.labelKey} fallback={current.fallback} />
		) : (
			(() => {
				const hour = new Date().getHours();
				const part = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
				// `firstName` handles both shapes: given a real name it takes the
				// first word of it, given an email it does the splitting it always did.
				const name = firstName(person?.trim() || user);

				return name ? `${part}, ${name}` : part;
			})()
		);

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
			"group flex items-center gap-3 rounded-full px-3.5 py-2.5 text-[12.5px] transition-all duration-200 ease-out active:scale-[0.97]",
			isActive
				? "bg-white/[.13] font-bold text-white"
				: "font-semibold text-white/60 hover:bg-white/[.07] hover:text-white",
		);

	const groupLabel = "px-3.5 pb-1.5 pt-5 text-[9.5px] font-bold uppercase tracking-[0.14em] text-white/35 first:pt-1";

	return (
		<div className="min-h-screen bg-page">
			{/* Two variables, so the rail, the pill and the gap between them share
			    one source for how far each sits from the glass and from each
			    other — see `GUTTER` and `TOPBAR`'s own comments. */}
			<div
				className="flex flex-col gap-4 p-4 md:flex-row"
				style={{ "--gutter": `${GUTTER}px`, "--topbar": `${TOPBAR}px` } as React.CSSProperties}
			>
				{/* --------------------------------------------------------------- rail */}
				{/* Its own scroll region, floated clear of every edge. `overflow-y-auto`
				    is unconditional: on a phone it is a drawer of the same shape, and a
				    society with companion apps installed can put more in it than a short
				    screen holds. */}
				<aside
					className={cx(
						"rail-scroll z-30 w-full flex-none flex-col overflow-y-auto rounded-feature px-3 pb-5 pt-4 shadow-card md:sticky md:flex md:h-[calc(100vh_-_var(--gutter)*2)] md:w-[236px]",
						rail,
						open ? "flex h-[calc(100vh_-_var(--topbar)_-_var(--gutter)*3)]" : "hidden md:flex",
					)}
					style={{ top: "var(--gutter)" }}
				>
					<Link to={home} onClick={() => setOpen(false)} className="mb-5 flex items-center px-2 pt-1">
						<BrandLockup tone="dark" wrap />
					</Link>

					<nav aria-label="Sections" className="flex flex-col gap-0.5">
						{items.map((item, index) => {
							if (isGroup(item)) {
								// Open by default whenever the page you are on is this group's
								// own or one of its children's; a manual click overrides that
								// until clicked again — see `openGroups`'s own comment.
								const onGroupsPage =
									within(location.pathname, item.to) ||
									item.children.some((child) => within(location.pathname, child.to));
								const expanded = openGroups[item.to] ?? onGroupsPage;
								// Shared by the row's own click and the chevron below — the row
								// toggles the same way the chevron does, on top of the navigation
								// `NavLink` still performs on its own, so a second click on an
								// open group closes it rather than being a no-op beside the
								// chevron doing the real work.
								const toggle = () => setOpenGroups((current) => ({ ...current, [item.to]: !expanded }));

								return (
									<Fragment key={item.to}>
										<NavLink
											to={item.to}
											end={item.end}
											onClick={() => {
												setOpen(false);
												toggle();
											}}
											className={({ isActive }) => link(isActive)}
										>
											{({ isActive }) => (
												<>
													{railContent(item, isActive)}
													<GroupToggle expanded={expanded} onToggle={toggle} />
												</>
											)}
										</NavLink>

										{expanded && (
											<div className="relative ml-[21px] mt-0.5 flex flex-col gap-0.5 border-l border-white/[.14] pl-3">
												{item.children.map((child) => (
													<div key={child.to} className="relative">
														{/* The horizontal tick from the vertical line to this
														    row, so the connector reads as one tree rather than
														    a line beside an unrelated list. Positioned to
														    exactly close the gap `pl-3` on the line above opens. */}
														<span
															aria-hidden="true"
															className="pointer-events-none absolute -left-3 top-1/2 h-px w-3 -translate-y-1/2 bg-white/[.14]"
														/>
														<NavLink
															to={child.to}
															end={child.end}
															onClick={() => setOpen(false)}
															className={({ isActive }) => cx(link(isActive), "py-2 text-[12px]")}
														>
															{({ isActive }) => railContent(child, isActive)}
														</NavLink>
													</div>
												))}
											</div>
										)}
									</Fragment>
								);
							}

							// A group needs none of this: its own row is the heading. Only a
							// plain item looks back for one, and a group behind it never
							// carries a `groupKey` to continue, so a heading never spans
							// across a group boundary.
							const previous = items[index - 1];
							const previousGroupKey = previous && !isGroup(previous) ? previous.groupKey : undefined;
							const started = item.groupKey && item.groupKey !== previousGroupKey;

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
										{({ isActive }) => railContent(item, isActive)}
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
					{(console_ || desk || sms) && (
						<div className="mt-auto flex flex-col gap-1 border-t border-white/[.12] pt-4">
							{console_ && (
								<Link
									to={console_}
									onClick={() => setOpen(false)}
									className="flex items-center gap-3 rounded-full bg-white/[.10] px-3.5 py-2.5 text-[12.5px] font-bold text-white transition-all duration-200 ease-out hover:bg-white/[.18] active:scale-[0.97]"
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

							{sms && (
								<a href={sms} className={link(false)}>
									<span className="flex-none text-white/55">
										<Icon.phone size={17} />
									</span>
									<EditableText k="admin.nav.sms" fallback="Send SMS" className="flex-1" />
								</a>
							)}
						</div>
					)}
				</aside>

				{/* --------------------------------------------------------- content column */}
				<div className="flex min-w-0 flex-1 flex-col gap-4">
					{/* ------------------------------------------------------------ top bar */}
					<header
						className={cx(
							"sticky z-40 flex flex-none items-center gap-3 rounded-full px-4 shadow-card md:px-5",
							rail,
						)}
						style={{ top: "var(--gutter)", height: TOPBAR }}
					>
						<button
							type="button"
							onClick={() => setOpen(!open)}
							aria-label={open ? "Close navigation" : "Open navigation"}
							aria-expanded={open}
							className="-ml-1 grid h-9 w-9 flex-none place-items-center rounded-full text-white/70 transition hover:bg-white/10 hover:text-white md:hidden"
						>
							{open ? <Icon.cross size={18} /> : <Icon.menu size={18} />}
						</button>

						{/* Identity lives on the rail once there is room for it beside the
						    nav it speaks for; on a phone the rail is a drawer that starts
						    closed, so the mark stands in here until somebody opens it. */}
						<Link to={home} className="min-w-0 md:hidden">
							<BrandLockup tone="dark" compact />
						</Link>

						{/* The top bar's own title — see `topBarTitle`'s own comment. Room
						    for it only opens up once the brand mark has moved to the rail,
						    so it is desktop-only. */}
						<span className="hidden truncate text-[14.5px] font-bold text-white md:block">
							{topBarTitle}
						</span>

						<div className="ml-auto flex items-center gap-1 sm:gap-2">
							{bell && (
						<NavLink
							to={bell.to}
							className={({ isActive }) =>
								cx(
									"relative grid h-10 w-10 place-items-center rounded-full transition",
									isActive
										? "bg-white/[.13] text-white"
										: "text-white/60 hover:bg-white/10 hover:text-white",
								)
							}
							aria-label={`${bell.fallback}${bell.count > 0 ? ` (${bell.count} unread)` : ""}`}
						>
							<Icon.bell size={19} />
							{bell.count > 0 && (
								<span
									className={cx(
										"absolute right-1 top-1 grid h-[17px] min-w-[17px] place-items-center rounded-full bg-signal px-1 text-[9.5px] font-bold leading-none text-white ring-2",
										railRing,
									)}
								>
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
							className="flex items-center gap-2.5 rounded-full py-1 pl-1 pr-1 transition hover:bg-white/10 sm:pr-3"
						>
							<span className="grid h-9 w-9 flex-none place-items-center rounded-full bg-white/15 font-display text-[12px] font-bold text-white">
								{initials(person?.trim() || user) || "?"}
							</span>

							<span className="hidden min-w-0 text-left sm:block">
								{/* The name, with the login underneath it where there is one
								    to show. The corner is where somebody looks to check they
								    are signed in as themselves, and an address is a worse
								    answer to that than a name is. */}
								<span className="block max-w-[170px] truncate text-[12.5px] font-bold text-white">
									{person?.trim() || user}
								</span>
								{subtitle && (
									<span className="block max-w-[170px] truncate text-[10.5px] text-white/55">
										{subtitle}
									</span>
								)}
							</span>

							<Icon.chevron
								size={14}
								className={cx(
									"hidden flex-none text-white/50 transition sm:block",
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

					<main className="min-w-0 flex-1 px-5 py-7 md:px-8 md:py-9">
						<Outlet />
					</main>
				</div>
			</div>

			<EditToolbar />
		</div>
	);
}
