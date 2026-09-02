/*
 * ─── DIRECTION CONTRACT ──────────────────────────────────────────────────────
 * THESIS: The manager console is the same workspace as the volunteer portal,
 *   carrying different work. One face, one canvas, one navy rail, one blue.
 *   A coordinator crossing between the two is changing what they are looking
 *   at, never what product they are in.
 * OWN-WORLD: Inherited, deliberately. Deep TRCS navy (#011E41) rail carrying
 *   white text; cool paper-grey canvas (#F6F8FB) and a light 56px header beside
 *   it. White panels held by a 1px #E7EBF0 hairline. 10–12px radii. IBM Plex
 *   Sans throughout. Blue (#155EEF) is the only interactive colour. Rows, not
 *   pills: the active nav row is a translucent-white fill.
 * WHAT THE CONSOLE ADDS: density the portal does not need — a two-level rail
 *   (groups that open), a section panel for the sections large enough to be
 *   small applications of their own, tables, boards, and a record laid out
 *   beside the panel its decision is made in. All of it in the same tokens.
 * FIRST VIEWPORT: 248px navy rail (brand, grouped nav with live queue counts,
 *   the way back to the person's own portal at its foot). 56px header: page
 *   title left, account right. Canvas: the day's greeting, then what is waiting.
 * FINISH: unreviewed and undocumented is unfinished.
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * **Forked from `ui/Shell.tsx`, which it replaces for `admin/`.** That file
 * served both surfaces with a `tone` prop, and folding the console into the
 * portal's language would have meant one component holding two visual systems
 * behind a branch at every line. The portal already has its own shell for
 * exactly this reason; this is the console's, and the two are close enough to
 * read side by side and separate enough that neither carries the other's
 * conditionals. `ui/Shell.tsx` stays until the last screen still importing its
 * primitives has moved.
 */

import { Fragment, useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { EditableText } from "../content/Editable";
import { EditToolbar } from "../content/EditToolbar";
import { initials, useSession } from "../lib/session";
import { BrandLockup } from "../ui/brand";
import { Icon, companionIcon } from "../ui/icons";
import { cx } from "../portal/ui/kit";
import { ToastProvider } from "../portal/ui/overlays";

export interface NavItem {
	to: string;
	/** Content key for the label, so a society renames its own navigation. */
	labelKey: string;
	fallback: string;
	icon: (props: { size?: number; className?: string }) => ReactNode;
	badge?: number;
	end?: boolean;
	/** A heading is drawn whenever this differs from the previous item's. */
	groupKey?: string;
	groupFallback?: string;
	/**
	 * This destination owns a secondary navigation panel of its own.
	 *
	 * Declared on the item rather than sniffed from the route, so the rail
	 * collapses on the same render the route changes on rather than a frame
	 * later.
	 */
	hasSubNav?: boolean;
}

/**
 * A `NavItem` with its own page that also opens onto a clutch of others.
 *
 * **Expansion follows the route**, so arriving at a child page by bookmark or
 * back button shows it in place rather than nested inside a heading collapsed
 * shut. The chevron is a manual override on top of that default.
 */
export interface NavGroup extends Omit<NavItem, "groupKey" | "groupFallback"> {
	children: NavItem[];
}

/** A tab that leaves this app entirely. Route and label both come from the server. */
export interface CompanionItem {
	app: string;
	href: string;
	labelKey: string;
	fallback: string;
}

function isGroup(item: NavItem | NavGroup): item is NavGroup {
	return "children" in item;
}

function within(pathname: string, base: string): boolean {
	return pathname === base || pathname.startsWith(`${base}/`);
}

/**
 * Which rail item `pathname` belongs to, for the header's own title.
 *
 * Longest `to` wins: `/admin` is `within` almost every console route, so
 * without this a detail page would read back as whichever tab sorts first.
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

/** Rail widths. One place, because the transition and two layouts lean on them. */
const RAIL_WIDE = 248;
const RAIL_NARROW = 68;

/**
 * Where the collapse preference lives.
 *
 * `localStorage` and not the server: a per-device layout preference, not
 * something about the person. Every access is guarded — a private window, or a
 * browser set to block site data, throws rather than returning null.
 */
const COLLAPSE_KEY = "vmms.nav.collapsed";

function readCollapsed(): boolean {
	try {
		return window.localStorage.getItem(COLLAPSE_KEY) === "1";
	} catch {
		return false;
	}
}

function writeCollapsed(value: boolean) {
	try {
		window.localStorage.setItem(COLLAPSE_KEY, value ? "1" : "0");
	} catch {
		/* A preference we could not save is not an error worth showing anybody. */
	}
}

/**
 * The chevron that opens or closes a `NavGroup`.
 *
 * A `span` carrying `role="button"` rather than a real one, because a `button`
 * inside an `a` is invalid HTML. It stops the click before the link beneath it
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
			className="flex-none rounded-md p-0.5 text-white/50 transition hover:bg-white/10 hover:text-white"
		>
			<Icon.chevron size={13} className={cx("transition-transform duration-200", expanded && "rotate-180")} />
		</span>
	);
}

export function ConsoleShell({
	items,
	companions = [],
	portal,
	desk,
	sms,
	subtitle,
	person,
	subNav,
	search,
}: {
	items: (NavItem | NavGroup)[];
	companions?: CompanionItem[];
	/**
	 * Where this person's own portal is.
	 *
	 * A route rather than a boolean, so this component never writes down where
	 * the other surface lives. Unconditional in practice: everybody who can see
	 * this shell has a portal, because being staff is a role somebody holds and
	 * not a thing they are instead of a volunteer.
	 */
	portal?: string | null;
	/** Where the Frappe desk is, for whoever may open it, or nothing. */
	desk?: string | null;
	/** Where onerc_sms's own campaign builder is, or nothing. */
	sms?: string | null;
	subtitle?: string | null;
	person?: string | null;
	/**
	 * The secondary navigation panel, for a section that has one.
	 *
	 * A render function rather than a node, because the panel appears in two
	 * arrangements — a column on a wide screen, a horizontal scroller below
	 * `lg` — and asking the caller for both keeps them one component.
	 */
	subNav?: (horizontal: boolean) => ReactNode;
	/** The global search control, or nothing. What search *does* is the caller's. */
	search?: ReactNode;
}) {
	const { user, logout } = useSession();
	const location = useLocation();
	const [drawer, setDrawer] = useState(false);
	const [menu, setMenu] = useState(false);
	const [collapsed, setCollapsed] = useState(readCollapsed);
	const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
	const account = useRef<HTMLDivElement>(null);
	const drawerPanel = useRef<HTMLDivElement>(null);
	const menuButton = useRef<HTMLButtonElement>(null);

	const current = currentTab(location.pathname, items);

	// A section with its own panel takes the rail down to icons whatever the
	// stored preference says: two expanded navigation columns side by side is
	// not a layout, it is a corridor. The preference is not overwritten, so
	// leaving the section restores whatever it was.
	const forced = Boolean(subNav) || Boolean(current?.hasSubNav);
	const narrow = forced || collapsed;

	const toggleCollapsed = useCallback(() => {
		setCollapsed((value) => {
			writeCollapsed(!value);
			return !value;
		});
	}, []);

	// The header title. Every page names itself the way its own rail row does;
	// the console's own front page says hello instead, because "Overview" above
	// "Good morning, Amina" is the same word twice.
	const onHome = !current || current.to === "/admin";

	const title = onHome ? (
		<EditableText k="admin.nav.overview" fallback="Overview" />
	) : (
		<EditableText k={current.labelKey} fallback={current.fallback} />
	);

	// A menu that stays open after you have clicked past it covers the thing you
	// were trying to reach. Escape closes it too — a pointer is not the only way in.
	useEffect(() => {
		if (!menu) return;

		function onPointer(event: MouseEvent) {
			if (!account.current?.contains(event.target as Node)) setMenu(false);
		}

		function onKey(event: KeyboardEvent) {
			if (event.key === "Escape") {
				setMenu(false);
				menuButton.current?.focus();
			}
		}

		document.addEventListener("mousedown", onPointer);
		document.addEventListener("keydown", onKey);

		return () => {
			document.removeEventListener("mousedown", onPointer);
			document.removeEventListener("keydown", onKey);
		};
	}, [menu]);

	// The mobile drawer is a modal surface: Escape closes it, the page behind it
	// does not scroll, and focus moves into it.
	useEffect(() => {
		if (!drawer) return;

		const previous = document.body.style.overflow;
		document.body.style.overflow = "hidden";

		function onKey(event: KeyboardEvent) {
			if (event.key === "Escape") setDrawer(false);
		}

		document.addEventListener("keydown", onKey);
		const focus = window.setTimeout(() => {
			drawerPanel.current?.querySelector<HTMLElement>("a, button")?.focus();
		}, 0);

		return () => {
			document.body.style.overflow = previous;
			document.removeEventListener("keydown", onKey);
			window.clearTimeout(focus);
		};
	}, [drawer]);

	// Navigating closes the drawer. Keyed on the path rather than written into
	// every link's onClick, so a link added later cannot forget to do it.
	useEffect(() => setDrawer(false), [location.pathname]);

	/**
	 * A rail row.
	 *
	 * A restrained translucent-white fill when selected, never a pill and never
	 * a coloured slab: the rail is one navy field and the current row is a
	 * lighter part of it. `compact` is the mobile drawer, which is always
	 * labelled however the desktop rail is set.
	 */
	const rowClass = (isActive: boolean, compact = false, child = false) =>
		cx(
			"group flex min-h-[36px] items-center rounded-[9px] transition-colors",
			narrow && !compact ? "justify-center px-0 py-2" : "gap-3 px-2.5 py-2",
			child ? "text-[13px]" : "text-[13.5px]",
			isActive
				? "bg-white/[0.12] font-semibold text-white"
				: "font-medium text-white/80 hover:bg-white/[0.06] hover:text-white",
		);

	/** Icon, label and count — what every rail row carries. */
	const rowContent = (item: NavItem, isActive: boolean, compact = false) => (
		<>
			<span
				className={cx(
					"relative flex-none transition-colors",
					isActive ? "text-white" : "text-white/65 group-hover:text-white",
				)}
			>
				<item.icon size={17} />
				{/* On an icon-only rail a count has nowhere to sit beside the label,
				    so it becomes a dot on the glyph. A number would be unreadable at
				    that size; the point it makes — "there is something here" — is
				    the part that survives. */}
				{narrow && !compact && item.badge !== undefined && item.badge > 0 && (
					<span className="absolute -right-1 -top-0.5 h-2 w-2 rounded-full bg-white ring-2 ring-rail" />
				)}
			</span>

			{(!narrow || compact) && (
				<EditableText k={item.labelKey} fallback={item.fallback} className="flex-1 truncate" />
			)}

			{(!narrow || compact) && item.badge !== undefined && item.badge > 0 && (
				<span className="grid h-[18px] min-w-[18px] flex-none place-items-center rounded-full bg-white px-1 text-[11px] font-bold leading-none text-blue-press">
					{item.badge > 99 ? "99+" : item.badge}
				</span>
			)}
		</>
	);

	/**
	 * The accessible name a row needs when the rail is icon-only.
	 *
	 * The label is a content block a society can rewrite and its resolved text
	 * is not available here, so the fallback goes in `aria-label`. A real
	 * limitation, stated rather than hidden: an icon with an English accessible
	 * name is far better than an icon with none, and the expanded rail — the
	 * default — always shows the translated label.
	 */
	const iconName = (item: NavItem, compact: boolean) => (narrow && !compact ? item.fallback : undefined);

	const groupLabel = "px-2.5 pb-1.5 pt-4 text-[10px] font-semibold uppercase tracking-[0.1em] text-white/60";

	/** The navigation itself, shared by the desktop rail and the mobile drawer. */
	const navigation = (compact: boolean) => (
		<nav aria-label="Sections" className="flex flex-col gap-0.5">
			{items.map((item, index) => {
				if (isGroup(item)) {
					const onGroupPage =
						within(location.pathname, item.to) ||
						item.children.some((child) => within(location.pathname, child.to));
					const expanded = openGroups[item.to] ?? onGroupPage;
					const toggle = () => setOpenGroups((state) => ({ ...state, [item.to]: !expanded }));

					return (
						<Fragment key={item.to}>
							{/* Active on any of its children's routes, not only on its own.
							    `NavLink`'s own `isActive` answers for `item.to` alone, and a
							    group's landing page is rarely where somebody is standing —
							    so on an icon-only rail (which is exactly when a section has
							    its own panel, and exactly when the children are hidden)
							    nothing was lit at all and the rail could not say where you
							    were. `onGroupPage` is the honest answer and it is already
							    computed for the expansion default. */}
							<NavLink
								to={item.to}
								end={item.end}
								onClick={toggle}
								aria-label={iconName(item, compact)}
								title={iconName(item, compact)}
								className={({ isActive }) => rowClass(isActive || onGroupPage, compact)}
							>
								{({ isActive }) => (
									<>
										{rowContent(item, isActive || onGroupPage, compact)}
										{(!narrow || compact) && <GroupToggle expanded={expanded} onToggle={toggle} />}
									</>
								)}
							</NavLink>

							{/* Children are hidden while the rail is icon-only: there is
							    nowhere to indent to, and a second column of unlabelled
							    icons is not a hierarchy anybody can read. The group's own
							    row still navigates, which is the way in. */}
							{expanded && (!narrow || compact) && (
								<div className="ml-[20px] mt-0.5 flex flex-col gap-0.5 border-l border-white/15 pl-2.5">
									{item.children.map((child) => (
										<NavLink
											key={child.to}
											to={child.to}
											end={child.end}
											className={({ isActive }) => rowClass(isActive, compact, true)}
										>
											{({ isActive }) => rowContent(child, isActive, compact)}
										</NavLink>
									))}
								</div>
							)}
						</Fragment>
					);
				}

				const previous = items[index - 1];
				const previousGroupKey = previous && !isGroup(previous) ? previous.groupKey : undefined;
				const started = item.groupKey && item.groupKey !== previousGroupKey;

				return (
					<Fragment key={item.to}>
						{started &&
							(narrow && !compact ? (
								// A tracked-out heading has no room in a 68px rail and a
								// truncated one is noise. A rule keeps the grouping the
								// heading carried without pretending to be readable.
								<div aria-hidden="true" className="mx-auto my-2 h-px w-6 bg-white/20" />
							) : (
								<div className={groupLabel}>
									<EditableText k={item.groupKey as string} fallback={item.groupFallback ?? ""} />
								</div>
							))}

						<NavLink
							to={item.to}
							end={item.end}
							aria-label={iconName(item, compact)}
							title={iconName(item, compact)}
							className={({ isActive }) => rowClass(isActive, compact)}
						>
							{({ isActive }) => rowContent(item, isActive, compact)}
						</NavLink>
					</Fragment>
				);
			})}
		</nav>
	);

	/** Companion apps and the way back to a person's own portal — the rail's foot. */
	const railFoot = (compact: boolean) => (
		<>
			{companions.length > 0 && (
				<>
					{/* Separated, because these leave the app: somebody who clicks
					    Learning lands in another product with its own navigation. */}
					{(!narrow || compact) && (
						<div className={groupLabel}>
							<EditableText k="portal.nav.companions" fallback="Also available" />
						</div>
					)}
					<nav aria-label="Other apps" className="flex flex-col gap-0.5">
						{companions.map((item) => {
							// The app's own glyph rather than one arrow for all three:
							// a rail where every companion looks identical is a rail
							// nobody reads, and these are the rows somebody scans for
							// rather than walks through.
							const Glyph = companionIcon(item.app);

							return (
							<a
								key={item.app}
								href={item.href}
								aria-label={narrow && !compact ? item.fallback : undefined}
								title={narrow && !compact ? item.fallback : undefined}
								className={cx(
									"group flex min-h-[36px] items-center rounded-[9px] text-[13.5px] font-medium text-white/80 transition-colors hover:bg-white/[0.06] hover:text-white",
									narrow && !compact ? "justify-center px-0 py-2" : "gap-3 px-2.5 py-2",
								)}
							>
								<span className="flex-none text-white/65 group-hover:text-white">
									<Glyph size={17} />
								</span>
								{(!narrow || compact) && (
									<EditableText k={item.labelKey} fallback={item.fallback} className="flex-1 truncate" />
								)}
							</a>
							);
						})}
					</nav>
				</>
			)}

			{(portal || desk || sms) && (
				<div
					className={cx(
						"mt-auto flex flex-col gap-1 border-t border-white/15 pt-3",
						narrow && !compact && "items-center",
					)}
				>
					{portal && (
						<Link
							to={portal}
							aria-label={narrow && !compact ? "My portal" : undefined}
							title={narrow && !compact ? "My portal" : undefined}
							className={cx(
								"flex min-h-[36px] items-center rounded-[9px] bg-white/[0.12] text-[13.5px] font-semibold text-white transition-colors hover:bg-white/[0.18]",
								narrow && !compact ? "h-9 w-9 justify-center" : "gap-3 px-2.5 py-2",
							)}
						>
							<span className="flex-none">
								<Icon.user size={17} />
							</span>
							{(!narrow || compact) && (
								<>
									<EditableText k="admin.nav.portal" fallback="My portal" className="flex-1 truncate" />
									<Icon.chevron size={14} className="-rotate-90 flex-none text-white/55" />
								</>
							)}
						</Link>
					)}

					{desk && (
						<a
							href={desk}
							aria-label={narrow && !compact ? "Desk" : undefined}
							title={narrow && !compact ? "Desk" : undefined}
							className={cx(
								"flex min-h-[36px] items-center rounded-[9px] text-[13px] font-medium text-white/70 transition-colors hover:bg-white/[0.06] hover:text-white",
								narrow && !compact ? "justify-center px-0 py-2" : "gap-3 px-2.5 py-2",
							)}
						>
							<span className="flex-none text-white/55">
								<Icon.external size={16} />
							</span>
							{(!narrow || compact) && <EditableText k="admin.nav.desk" fallback="Desk" className="flex-1" />}
						</a>
					)}

					{sms && (
						<a
							href={sms}
							aria-label={narrow && !compact ? "Send SMS" : undefined}
							title={narrow && !compact ? "Send SMS" : undefined}
							className={cx(
								"flex min-h-[36px] items-center rounded-[9px] text-[13px] font-medium text-white/70 transition-colors hover:bg-white/[0.06] hover:text-white",
								narrow && !compact ? "justify-center px-0 py-2" : "gap-3 px-2.5 py-2",
							)}
						>
							<span className="flex-none text-white/55">
								<Icon.phone size={16} />
							</span>
							{(!narrow || compact) && <EditableText k="admin.nav.sms" fallback="Send SMS" className="flex-1" />}
						</a>
					)}
				</div>
			)}
		</>
	);

	return (
		<ToastProvider>
			<div className="console-root min-h-screen">
				<div className="flex min-h-screen">
					{/* ---------------------------------------------------------- rail */}
					<aside
						className="portal-rail-scroll sticky top-0 hidden h-screen flex-none flex-col overflow-y-auto bg-rail px-3 pb-4 pt-4 transition-[width] duration-200 ease-out md:flex"
						style={{ width: narrow ? RAIL_NARROW : RAIL_WIDE }}
					>
						<Link
							to="/admin"
							className={cx("mb-3 flex items-center px-2 pt-1", narrow && "justify-center px-0")}
							aria-label="Console home"
						>
							<BrandLockup compact={narrow} wrap={!narrow} tone="dark" />
						</Link>

						{navigation(false)}

						<div className="mt-auto flex flex-col gap-1 pt-4">
							{railFoot(false)}

							{/* The collapse control. A real button whose accessible name
							    says what it will do, not what the rail currently is. */}
							<button
								type="button"
								onClick={toggleCollapsed}
								disabled={forced}
								aria-label={narrow ? "Expand menu" : "Collapse menu"}
								title={
									forced ? "This section uses its own menu" : narrow ? "Expand menu" : "Collapse menu"
								}
								className={cx(
									"mt-1 flex min-h-[34px] items-center rounded-[9px] text-[12.5px] font-medium text-white/60 transition-colors hover:bg-white/[0.06] hover:text-white disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-transparent disabled:hover:text-white/60",
									narrow ? "h-9 w-9 justify-center self-center" : "gap-2.5 px-2.5 py-2",
								)}
							>
								<Icon.chevron
									size={14}
									className={cx("flex-none transition-transform", narrow ? "-rotate-90" : "rotate-90")}
								/>
								{!narrow && (
									<EditableText
										k="chrome.action.collapse"
										fallback="Collapse menu"
										className="flex-1 text-left"
									/>
								)}
							</button>
						</div>
					</aside>

					{/* -------------------------------------------------------- sub-nav */}
					{/* A second navigation column, for a section big enough to be a
					    small application of its own. White on the canvas rather than a
					    second grey: three columns read as rail / section / content. */}
					{subNav && (
						<div className="sticky top-0 hidden h-screen w-[216px] flex-none overflow-y-auto border-r border-card-line bg-white px-3 py-4 lg:block">
							{subNav(false)}
						</div>
					)}

					{/* -------------------------------------------------- content column */}
					<div className="flex min-w-0 flex-1 flex-col">
						<header className="sticky top-0 z-40 flex h-14 flex-none items-center gap-3 bg-canvas/95 px-4 backdrop-blur-sm md:px-7">
							<button
								type="button"
								onClick={() => setDrawer(true)}
								aria-label="Open navigation"
								aria-expanded={drawer}
								className="-ml-1 grid h-8 w-8 flex-none place-items-center rounded-lg text-slate-strong transition hover:bg-rail-hover md:hidden"
							>
								<Icon.menu size={18} />
							</button>

							<Link to="/admin" className="min-w-0 flex-1 md:hidden">
								<BrandLockup compact />
							</Link>

							<h1 className="hidden min-w-0 flex-1 truncate text-[14.5px] font-semibold text-ink md:block">
								{title}
							</h1>

							<div className="ml-auto flex items-center gap-2">
								{search && <div className="hidden lg:block">{search}</div>}

								<div ref={account} className="relative">
									<button
										ref={menuButton}
										type="button"
										onClick={() => setMenu(!menu)}
										aria-haspopup="menu"
										aria-expanded={menu}
										className="flex items-center gap-2 rounded-lg py-1 pl-1 pr-1.5 transition hover:bg-rail-hover sm:pr-2.5"
									>
										<span className="grid h-7 w-7 flex-none place-items-center rounded-full bg-blue/[0.1] text-[11px] font-semibold text-blue-press">
											{initials(person?.trim() || user) || "?"}
										</span>

										<span className="hidden min-w-0 text-left sm:block">
											<span className="block max-w-[150px] truncate text-[12.5px] font-semibold text-ink">
												{person?.trim() || user}
											</span>
											{subtitle && (
												<span className="block max-w-[150px] truncate text-[10.5px] text-muted">
													{subtitle}
												</span>
											)}
										</span>

										<Icon.chevron
											size={13}
											className={cx(
												"hidden flex-none text-slate-faint transition sm:block",
												menu && "rotate-180",
											)}
										/>
									</button>

									{menu && (
										<div
											role="menu"
											className="p-card absolute right-0 top-full z-50 mt-1.5 w-56 overflow-hidden py-1.5 shadow-pop"
										>
											<div className="border-b p-divide px-4 pb-2.5 pt-1 sm:hidden">
												<div className="truncate text-[12.5px] font-semibold text-ink">{user}</div>
												{subtitle && <div className="truncate text-[10.5px] text-muted">{subtitle}</div>}
											</div>

											<Link
												to="/profile"
												role="menuitem"
												onClick={() => setMenu(false)}
												className="flex items-center gap-3 px-4 py-2.5 text-[12.5px] font-medium text-slate-strong transition hover:bg-canvas hover:text-ink"
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
												className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-[12.5px] font-medium text-slate-strong transition hover:bg-canvas hover:text-ink"
											>
												<Icon.signout size={15} />
												<EditableText k="chrome.action.signout" fallback="Sign out" />
											</button>
										</div>
									)}
								</div>
							</div>
						</header>

						{/* The sub-nav's own row on narrow screens, where there is no room
						    for a third column. A scroller rather than a hidden panel: the
						    section's pages have to stay reachable. */}
						{subNav && (
							<div className="border-b border-card-line bg-white px-4 py-2 lg:hidden">
								<div className="-mx-1 overflow-x-auto px-1">{subNav(true)}</div>
							</div>
						)}

						<main className="min-w-0 flex-1 px-4 pb-16 pt-4 md:px-7">
							<Outlet />
						</main>
					</div>
				</div>

				{/* ------------------------------------------------------ mobile drawer */}
				{drawer && (
					<div className="fixed inset-0 z-50 md:hidden">
						<button
							type="button"
							aria-label="Close navigation"
							onClick={() => setDrawer(false)}
							className="absolute inset-0 h-full w-full cursor-default bg-ink/40"
						/>

						<div
							ref={drawerPanel}
							role="dialog"
							aria-modal="true"
							aria-label="Navigation"
							className="portal-rail-scroll absolute inset-y-0 left-0 flex w-[272px] max-w-[86vw] flex-col overflow-y-auto bg-rail px-3 pb-5 pt-4 shadow-[0_18px_55px_rgba(25,30,38,0.24)]"
						>
							<div className="mb-3 flex items-center justify-between gap-2 px-2">
								<Link to="/admin" className="min-w-0">
									<BrandLockup wrap tone="dark" />
								</Link>
								<button
									type="button"
									onClick={() => setDrawer(false)}
									aria-label="Close navigation"
									className="grid h-8 w-8 flex-none place-items-center rounded-lg text-white/70 transition hover:bg-white/10 hover:text-white"
								>
									<Icon.cross size={18} />
								</button>
							</div>

							{navigation(true)}

							<div className="mt-auto flex flex-col gap-1 pt-4">{railFoot(true)}</div>
						</div>
					</div>
				)}

				<EditToolbar />
			</div>
		</ToastProvider>
	);
}
