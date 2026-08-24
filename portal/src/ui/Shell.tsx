import {
	Fragment,
	useCallback,
	useEffect,
	useRef,
	useState,
	type ReactNode,
} from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

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
	 * Omit it throughout and the navigation is one ungrouped list.
	 */
	groupKey?: string;
	groupFallback?: string;
	/**
	 * This destination owns a secondary navigation panel of its own.
	 *
	 * Deployments is the one that does. Opening it collapses the global rail to
	 * icons and slides its own panel in beside it — see `Shell`'s `subNav` prop.
	 * Declared on the item rather than sniffed from the route so the rail knows
	 * to collapse *before* the child route has rendered anything.
	 */
	hasSubNav?: boolean;
}

/**
 * A `NavItem` with its own page, that also collapses a clutch of others under
 * it — the console's Registry-and-Analytics style grouping, not the portal's
 * plain headed list.
 *
 * **Expansion follows the route**, so arriving at a child page by bookmark or
 * back button always shows it in place rather than nested inside a heading
 * collapsed shut. The chevron is a manual override on top of that default.
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
 * Which rail item `pathname` belongs to, for the top row's own title. Longest
 * `to` wins: `/admin` is `within` almost every admin route, so without this a
 * detail page nested under a specific tab would read back as whichever tab
 * happens to sort first rather than the one it is actually inside.
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

/**
 * The chevron that opens or closes a `NavGroup`, on its own — never the row's
 * `NavLink` — because a `button` inside an `a` is invalid HTML. A `span`
 * carrying `role="button"` instead, stopping the click before the link beneath
 * it ever sees it.
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
			className="flex-none rounded-full p-1 text-slate-faint transition-colors duration-200 hover:bg-black/[.05] hover:text-ink"
		>
			<Icon.chevron
				size={13}
				className={cx("transition-transform duration-200", expanded && "rotate-180")}
			/>
		</span>
	);
}

/**
 * A tab that leaves this app entirely.
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

/** Where the bell in the top row points, and what it is carrying. */
export interface BellProps {
	to: string;
	count: number;
	labelKey: string;
	fallback: string;
}

/** Rail widths. One place, because three `calc`s and a transition lean on them. */
const RAIL_WIDE = 236;
const RAIL_NARROW = 68;

/**
 * Where the collapse preference lives.
 *
 * `localStorage` and not the server: this is a per-device layout preference,
 * not something about the person, and somebody who collapses the rail on a
 * small laptop does not mean it should be collapsed on their desktop too.
 * Every read and write is guarded — a private window, or a browser set to block
 * site data, throws on access rather than returning null.
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
 * The signed-in chrome, for both the volunteer portal and the coordinator
 * console.
 *
 * **One continuous grey shell.** The rail, the top row and the gaps between
 * panels are all the same surface; white panels float above it. That is the
 * whole structural idea of the redesign, and it is why there is no wrapper
 * `<div class="bg-white">` around page content anywhere below — a page is a set
 * of panels on the shell, not one white rectangle with things drawn inside it.
 *
 * **The page title lives in the top row**, aligned with the society identity,
 * search and account controls, and the content area begins underneath. A screen
 * that wants a fuller heading draws its own beneath that, which is what
 * `PageHeading` is for.
 *
 * **The rail collapses to an icon-only rail** and the preference persists per
 * device. Collapsing is a layout change and never a navigation: the route is
 * untouched, so nothing is lost and nothing re-fetches. A destination that owns
 * a secondary panel (`hasSubNav`) collapses the rail on arrival regardless of
 * the preference, because two expanded navigation columns side by side is not a
 * layout, it is a corridor.
 *
 * One component with a `tone` rather than two shells that drift apart. The two
 * surfaces differ only in the console's slightly deeper rail treatment and its
 * label; everything else about them is the same, and duplicating it would mean
 * fixing every focus ring twice.
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
	subNav,
	search,
}: {
	items: (NavItem | NavGroup)[];
	companions?: CompanionItem[];
	bell?: BellProps | null;
	/**
	 * Where the console switch points, or nothing at all.
	 *
	 * A route rather than a boolean, so this component never writes down where
	 * the other surface lives and never decides who may go there — the caller
	 * passes it only when `api/console.py::sections` said `available`.
	 */
	console?: string | null;
	/** Where the Frappe desk is, for whoever may open it, or nothing. */
	desk?: string | null;
	/** Where onerc_sms's own campaign builder is, or nothing. */
	sms?: string | null;
	tone: "portal" | "admin";
	subtitle?: string | null;
	/** This person's own name, from their Red Profile. */
	person?: string | null;
	/**
	 * The secondary navigation panel, for a destination that has one.
	 *
	 * Rendered between the global rail and the content, and its presence is what
	 * forces the global rail into its icon-only state. Passed by the layout that
	 * knows the current section rather than assembled here, so this component
	 * never learns what a deployment is.
	 *
	 * A render function rather than a node, because the panel appears twice in
	 * two arrangements — a column on a wide screen, a horizontal scroller under
	 * the top row below `lg` — and asking the caller for both is how the two
	 * stay one component instead of drifting into two.
	 */
	subNav?: (horizontal: boolean) => ReactNode;
	/**
	 * The global search control, or nothing.
	 *
	 * A slot rather than a built-in field: what search *does* differs between
	 * the portal and the console, and a shell that owned the behaviour would
	 * have to know about both.
	 */
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
	// stored preference says — see the component docstring. The preference is
	// not overwritten, so leaving the section restores whatever it was.
	const forced = Boolean(subNav) || Boolean(current?.hasSubNav);
	const narrow = forced || collapsed;

	const home = console_ === "/dashboard" ? "/admin" : "/dashboard";

	const toggleCollapsed = useCallback(() => {
		setCollapsed((value) => {
			writeCollapsed(!value);
			return !value;
		});
	}, []);

	// The page title in the top row. Every page names itself the way its own
	// rail row does; the surface's own home page says hello instead, because
	// "Dashboard" above "Welcome back, Amina" is the same word twice.
	const onHome = !current || current.to === home;

	const topBarTitle = onHome ? (
		<EditableText k={tone === "admin" ? "admin.nav.overview" : "portal.nav.dashboard"} fallback={tone === "admin" ? "Overview" : "Dashboard"} />
	) : (
		<EditableText k={current.labelKey} fallback={current.fallback} />
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
	// does not scroll, and focus moves into it so a keyboard user is not left
	// tabbing through the page underneath.
	useEffect(() => {
		if (!drawer) return;

		const previous = document.body.style.overflow;
		document.body.style.overflow = "hidden";

		function onKey(event: KeyboardEvent) {
			if (event.key === "Escape") setDrawer(false);
		}

		document.addEventListener("keydown", onKey);
		// After paint, so the panel exists to receive it.
		const focus = window.setTimeout(() => {
			drawerPanel.current?.querySelector<HTMLElement>("a, button")?.focus();
		}, 0);

		return () => {
			document.body.style.overflow = previous;
			document.removeEventListener("keydown", onKey);
			window.clearTimeout(focus);
		};
	}, [drawer]);

	// Navigating closes the drawer. In an effect keyed on the path rather than
	// in every link's onClick, so a link added later cannot forget to do it.
	useEffect(() => {
		setDrawer(false);
	}, [location.pathname]);

	/**
	 * A rail row.
	 *
	 * The selected one is a white pill lifted off the grey with blue text and a
	 * blue icon — the redesign's single "you are here" signal, used for
	 * navigation, active tabs and focus alike. Unselected rows carry no surface
	 * at all until they are pointed at, which is what keeps the rail reading as
	 * part of the shell rather than as a panel of its own.
	 */
	const rowClass = (isActive: boolean, compact = false) =>
		cx(
			"group relative flex items-center rounded-full text-[12.5px] transition-colors duration-150",
			narrow ? "justify-center px-0 py-2.5" : "gap-3 px-3.5",
			compact && !narrow ? "py-2" : narrow ? "py-2.5" : "py-2.5",
			isActive
				? "bg-white font-medium text-blue shadow-nav"
				: "font-normal text-slate-strong hover:bg-white/60 hover:text-ink",
		);

	/** Icon, label and badge — the content every rail row carries. */
	const rowContent = (item: NavItem, isActive: boolean) => (
		<>
			<span
				className={cx(
					"flex-none transition-colors duration-150",
					isActive ? "text-blue" : "text-slate-faint group-hover:text-slate-strong",
				)}
			>
				<item.icon size={17} />
			</span>

			{!narrow && <EditableText k={item.labelKey} fallback={item.fallback} className="flex-1 truncate" />}

			{item.badge !== undefined && item.badge > 0 && (
				<span
					className={cx(
						"rounded-full bg-blue text-[10px] font-semibold leading-none text-white",
						narrow
							? "absolute right-1.5 top-1 min-w-[16px] px-1 py-0.5 text-center ring-2 ring-shell"
							: "px-1.5 py-0.5",
					)}
				>
					{item.badge > 99 ? "99+" : item.badge}
				</span>
			)}
		</>
	);

	/**
	 * The accessible name a row needs when the rail is icon-only.
	 *
	 * The label is a content block a society can rewrite, and its resolved text
	 * is not available to this function — so the fallback is what goes in
	 * `aria-label` and `title`. That is a real limitation and the honest
	 * trade-off is stated here rather than hidden: an icon with an English
	 * accessible name is far better than an icon with none, and the expanded
	 * rail — the default — always shows the translated label.
	 */
	const iconName = (item: NavItem) => (narrow ? item.fallback : undefined);

	const groupLabel = cx(
		"pb-1.5 pt-5 text-[9.5px] font-semibold uppercase tracking-[0.14em] text-slate-faint first:pt-1",
		narrow ? "px-0 text-center" : "px-3.5",
	);

	/** The navigation itself, shared by the desktop rail and the mobile drawer. */
	const navigation = (compact: boolean) => (
		<nav aria-label="Sections" className="flex flex-col gap-0.5">
			{items.map((item, index) => {
				if (isGroup(item)) {
					const onGroupsPage =
						within(location.pathname, item.to) ||
						item.children.some((child) => within(location.pathname, child.to));
					const expanded = openGroups[item.to] ?? onGroupsPage;
					const toggle = () =>
						setOpenGroups((state) => ({ ...state, [item.to]: !expanded }));

					return (
						<Fragment key={item.to}>
							<NavLink
								to={item.to}
								end={item.end}
								onClick={toggle}
								aria-label={iconName(item)}
								title={iconName(item)}
								className={({ isActive }) => rowClass(isActive)}
							>
								{({ isActive }) => (
									<>
										{rowContent(item, isActive)}
										{!narrow && <GroupToggle expanded={expanded} onToggle={toggle} />}
									</>
								)}
							</NavLink>

							{/* Children are hidden while the rail is icon-only: there is
							    nowhere to indent to, and a second column of unlabelled
							    icons is not a hierarchy anybody can read. The group's own
							    row still navigates, which is the way in. */}
							{expanded && !narrow && (
								<div className="relative ml-[21px] mt-0.5 flex flex-col gap-0.5 border-l border-hairline pl-3">
									{item.children.map((child) => (
										<div key={child.to} className="relative">
											<span
												aria-hidden="true"
												className="pointer-events-none absolute -left-3 top-1/2 h-px w-3 -translate-y-1/2 bg-hairline"
											/>
											<NavLink
												to={child.to}
												end={child.end}
												className={({ isActive }) => cx(rowClass(isActive, true), "text-[12px]")}
											>
												{({ isActive }) => rowContent(child, isActive)}
											</NavLink>
										</div>
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
								// A tracked-out heading has no room in a 68px rail, and a
								// truncated one is noise. A rule keeps the grouping the
								// heading carried without pretending to be readable.
								<div aria-hidden="true" className="mx-auto my-2 h-px w-6 bg-hairline-strong" />
							) : (
								<div className={cx(groupLabel, compact && "px-3.5 text-left")}>
									<EditableText k={item.groupKey as string} fallback={item.groupFallback ?? ""} />
								</div>
							))}

						<NavLink
							to={item.to}
							end={item.end}
							aria-label={compact ? undefined : iconName(item)}
							title={compact ? undefined : iconName(item)}
							className={({ isActive }) =>
								compact
									? cx(
											"group flex items-center gap-3 rounded-full px-3.5 py-2.5 text-[13px] transition-colors",
											isActive
												? "bg-white font-medium text-blue shadow-nav"
												: "font-normal text-slate-strong hover:bg-white/60",
										)
									: rowClass(isActive)
							}
						>
							{({ isActive }) =>
								compact ? (
									<>
										<span className={cx("flex-none", isActive ? "text-blue" : "text-slate-faint")}>
											<item.icon size={17} />
										</span>
										<EditableText k={item.labelKey} fallback={item.fallback} className="flex-1" />
										{item.badge !== undefined && item.badge > 0 && (
											<span className="rounded-full bg-blue px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white">
												{item.badge > 99 ? "99+" : item.badge}
											</span>
										)}
									</>
								) : (
									rowContent(item, isActive)
								)
							}
						</NavLink>
					</Fragment>
				);
			})}
		</nav>
	);

	/** Companion apps and the surface switch — the foot of the rail. */
	const railFoot = (compact: boolean) => (
		<>
			{companions.length > 0 && (
				<>
					{/* Separated, because these leave the app. Somebody who clicks
					    Learning lands in another product with its own navigation. */}
					{(!narrow || compact) && (
						<div className={cx(groupLabel, compact && "px-3.5 text-left")}>
							<EditableText k="portal.nav.companions" fallback="Also available" />
						</div>
					)}
					<nav aria-label="Other apps" className="flex flex-col gap-0.5">
						{companions.map((item) => (
							<a
								key={item.app}
								href={item.href}
								aria-label={narrow && !compact ? item.fallback : undefined}
								title={narrow && !compact ? item.fallback : undefined}
								className={cx(
									"group flex items-center rounded-full text-[12.5px] font-normal text-slate-strong transition-colors hover:bg-white/60 hover:text-ink",
									narrow && !compact ? "justify-center px-0 py-2.5" : "gap-3 px-3.5 py-2.5",
								)}
							>
								<span className="flex-none text-slate-faint">
									<Icon.external size={17} />
								</span>
								{(!narrow || compact) && (
									<EditableText k={item.labelKey} fallback={item.fallback} className="flex-1" />
								)}
							</a>
						))}
					</nav>
				</>
			)}

			{(console_ || desk || sms) && (
				<div
					className={cx(
						"mt-auto flex flex-col gap-1 border-t border-hairline pt-4",
						narrow && !compact && "items-center",
					)}
				>
					{console_ && (
						<Link
							to={console_}
							aria-label={narrow && !compact ? (tone === "admin" ? "My portal" : "Manager console") : undefined}
							title={narrow && !compact ? (tone === "admin" ? "My portal" : "Manager console") : undefined}
							className={cx(
								"flex items-center rounded-full bg-authority text-[12.5px] font-medium text-white transition-colors hover:bg-authority-soft",
								narrow && !compact ? "h-10 w-10 justify-center" : "gap-3 px-3.5 py-2.5",
							)}
						>
							<span className="flex-none">
								{tone === "admin" ? <Icon.user size={17} /> : <Icon.lock size={17} />}
							</span>
							{(!narrow || compact) && (
								<>
									<EditableText
										k={tone === "admin" ? "admin.nav.portal" : "portal.nav.console"}
										fallback={tone === "admin" ? "My portal" : "Manager console"}
										className="flex-1"
									/>
									<Icon.chevron size={14} className="-rotate-90 flex-none text-white/60" />
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
								"flex items-center rounded-full text-[12.5px] text-slate-strong transition-colors hover:bg-white/60",
								narrow && !compact ? "justify-center px-0 py-2.5" : "gap-3 px-3.5 py-2.5",
							)}
						>
							<span className="flex-none text-slate-faint">
								<Icon.external size={17} />
							</span>
							{(!narrow || compact) && (
								<EditableText k="admin.nav.desk" fallback="Desk" className="flex-1" />
							)}
						</a>
					)}

					{sms && (
						<a
							href={sms}
							aria-label={narrow && !compact ? "Send SMS" : undefined}
							title={narrow && !compact ? "Send SMS" : undefined}
							className={cx(
								"flex items-center rounded-full text-[12.5px] text-slate-strong transition-colors hover:bg-white/60",
								narrow && !compact ? "justify-center px-0 py-2.5" : "gap-3 px-3.5 py-2.5",
							)}
						>
							<span className="flex-none text-slate-faint">
								<Icon.phone size={17} />
							</span>
							{(!narrow || compact) && (
								<EditableText k="admin.nav.sms" fallback="Send SMS" className="flex-1" />
							)}
						</a>
					)}
				</div>
			)}
		</>
	);

	return (
		<div className="app-shell min-h-screen">
			<div className="flex min-h-screen">
				{/* ------------------------------------------------------------ rail */}
				{/* Part of the shell, not a panel on it: no background, no border, no
				    shadow. What separates it from the content is the white panels
				    starting, which is the whole point of a continuous ground. */}
				<aside
					className={cx(
						"rail-scroll sticky top-0 hidden h-screen flex-none flex-col overflow-y-auto px-3 pb-4 pt-4 transition-[width] duration-200 ease-out md:flex",
					)}
					style={{ width: narrow ? RAIL_NARROW : RAIL_WIDE }}
				>
					<Link
						to={home}
						className={cx(
							"mb-5 flex items-center rounded-card px-2 pt-1",
							narrow && "justify-center px-0",
						)}
						aria-label="Home"
					>
						<BrandLockup compact={narrow} wrap={!narrow} />
					</Link>

					{navigation(false)}

					<div className="mt-auto flex flex-col gap-1 pt-4">
						{railFoot(false)}

						{/* The collapse control. A real button with an accessible name
						    that says what it will do, not what the rail currently is. */}
						<button
							type="button"
							onClick={toggleCollapsed}
							disabled={forced}
							aria-label={narrow ? "Expand menu" : "Collapse menu"}
							title={
								forced
									? "This section uses its own menu"
									: narrow
										? "Expand menu"
										: "Collapse menu"
							}
							className={cx(
								"mt-2 flex items-center rounded-full bg-white text-[12px] font-normal text-slate-strong shadow-nav transition-colors hover:text-ink disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:text-slate-strong",
								narrow ? "h-10 w-10 justify-center self-center" : "gap-2 px-3.5 py-2.5",
							)}
						>
							<Icon.chevron
								size={14}
								className={cx("flex-none transition-transform", narrow ? "-rotate-90" : "rotate-90")}
							/>
							{!narrow && (
								<EditableText k="chrome.action.collapse" fallback="Collapse menu" className="flex-1 text-left" />
							)}
						</button>
					</div>
				</aside>

				{/* -------------------------------------------------------- sub-nav */}
				{/* A second navigation column, for a section that has one. Its own
				    surface tone (one step off the shell) so the three columns read
				    as rail / section / content rather than as one grey field. */}
				{subNav && (
					<div className="sticky top-0 hidden h-screen w-[212px] flex-none overflow-y-auto border-r border-hairline bg-surface px-3 py-4 lg:block">
						{subNav(false)}
					</div>
				)}

				{/* -------------------------------------------------- content column */}
				<div className="flex min-w-0 flex-1 flex-col">
					{/* ------------------------------------------------------ top row */}
					{/* Transparent on the shell — the controls are the only surfaces
					    here. The page title sits at the left of the same row, which is
					    what stops a page from needing a title bar of its own. */}
					<header className="sticky top-0 z-40 flex flex-none items-center gap-3 bg-shell/90 px-4 py-3.5 backdrop-blur-sm md:px-7 md:py-4">
						<button
							type="button"
							onClick={() => setDrawer(true)}
							aria-label="Open navigation"
							aria-expanded={drawer}
							className="-ml-1 grid h-10 w-10 flex-none place-items-center rounded-full bg-white text-slate-strong shadow-nav transition hover:text-ink md:hidden"
						>
							<Icon.menu size={18} />
						</button>

						{/* Identity lives on the rail once there is room for it beside the
						    navigation it speaks for; on a phone the rail is a drawer that
						    starts closed, so the mark stands in here until somebody opens
						    it. */}
						<Link to={home} className="min-w-0 md:hidden">
							<BrandLockup compact />
						</Link>

						<h1 className="hidden min-w-0 flex-1 truncate font-display text-[21px] font-medium tracking-tight text-ink md:block">
							{topBarTitle}
						</h1>

						<div className="ml-auto flex items-center gap-2">
							{search && <div className="hidden lg:block">{search}</div>}

							{bell && (
								<NavLink
									to={bell.to}
									className={({ isActive }) =>
										cx(
											"relative grid h-10 w-10 place-items-center rounded-full shadow-nav transition",
											isActive ? "bg-white text-blue" : "bg-white text-slate-strong hover:text-ink",
										)
									}
									aria-label={`${bell.fallback}${bell.count > 0 ? ` (${bell.count} unread)` : ""}`}
								>
									<Icon.bell size={18} />
									{bell.count > 0 && (
										<span className="absolute right-1 top-1 grid h-[17px] min-w-[17px] place-items-center rounded-full bg-blue px-1 text-[9.5px] font-semibold leading-none text-white ring-2 ring-white">
											{bell.count > 99 ? "99+" : bell.count}
										</span>
									)}
								</NavLink>
							)}

							<div ref={account} className="relative">
								<button
									ref={menuButton}
									type="button"
									onClick={() => setMenu(!menu)}
									aria-haspopup="menu"
									aria-expanded={menu}
									className="flex items-center gap-2.5 rounded-full bg-white py-1 pl-1 pr-1 shadow-nav transition sm:pr-3"
								>
									<span className="grid h-9 w-9 flex-none place-items-center rounded-full bg-surface font-display text-[12px] font-medium text-slate-strong">
										{initials(person?.trim() || user) || "?"}
									</span>

									<span className="hidden min-w-0 text-left sm:block">
										<span className="block max-w-[170px] truncate text-[12.5px] font-medium text-ink">
											{person?.trim() || user}
										</span>
										{subtitle && (
											<span className="block max-w-[170px] truncate text-[10.5px] text-muted">
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
										className="absolute right-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-card bg-white py-1.5 shadow-pop ring-1 ring-hairline"
									>
										<div className="border-b border-hairline-soft px-4 pb-2.5 pt-1.5 sm:hidden">
											<div className="truncate text-[12.5px] font-medium text-ink">{user}</div>
											{subtitle && <div className="truncate text-[10.5px] text-muted">{subtitle}</div>}
										</div>

										<Link
											to="/profile"
											role="menuitem"
											onClick={() => setMenu(false)}
											className="flex items-center gap-3 px-4 py-2.5 text-[12.5px] font-normal text-slate-strong transition hover:bg-surface hover:text-ink"
										>
											<Icon.user size={15} />
											<EditableText k="portal.nav.profile" fallback="Profile" />
										</Link>

										<button
											type="button"
											role="menuitem"
											onClick={() => {
												// Frappe clears the session cookie; a hard navigation
												// is wanted here so nothing stale survives in memory.
												void logout().then(() => {
													window.location.href = "/";
												});
											}}
											className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-[12.5px] font-normal text-slate-strong transition hover:bg-surface hover:text-ink"
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
					    for a third column. A horizontal scroller rather than a hidden
					    panel: the section's pages have to stay reachable. */}
					{subNav && (
						<div className="border-b border-hairline bg-surface px-4 py-2 lg:hidden">
							<div className="-mx-1 overflow-x-auto px-1">{subNav(true)}</div>
						</div>
					)}

					<main className="min-w-0 flex-1 px-4 pb-10 pt-1 md:px-7">
						<Outlet />
					</main>
				</div>
			</div>

			{/* ------------------------------------------------------- mobile drawer */}
			{/* Not the desktop rail revealed — a surface of its own, sized and spaced
			    for a thumb, with the society identity at the top of it where the rail
			    keeps it on a wide screen. */}
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
						className="rail-scroll absolute inset-y-0 left-0 flex w-[280px] max-w-[86vw] flex-col overflow-y-auto bg-shell px-3 pb-5 pt-4 shadow-shell"
					>
						<div className="mb-4 flex items-center gap-2 px-2">
							<Link to={home} className="min-w-0 flex-1">
								<BrandLockup wrap />
							</Link>
							<button
								type="button"
								onClick={() => setDrawer(false)}
								aria-label="Close navigation"
								className="grid h-9 w-9 flex-none place-items-center rounded-full bg-white text-slate-strong shadow-nav"
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
	);
}
