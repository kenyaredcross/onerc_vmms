/*
 * ─── DIRECTION CONTRACT ──────────────────────────────────────────────────────
 * THESIS: The volunteer portal is one continuous workspace — a quiet
 *   institutional back-office, not a dashboard. Sidebar, header and canvas share
 *   one ground; hierarchy comes from space and a single restrained blue, never
 *   from colour blocks, stat-tile grids, or the pill-rail it refuses.
 * OWN-WORLD: A deep TRCS navy (#011E41) left rail carrying white text; a cool
 *   paper-grey canvas and a light header beside it (#F4F7FA). White panels held
 *   by a 1px #DFE6ED hairline and the faintest lift. 10–14px radii. IBM Plex Sans
 *   for body, Schibsted Grotesk for headings — the approved concept's two-face
 *   hierarchy, drawn in the two faces this app already loads rather than the two
 *   it names. Navy ink (#102033) on the light side. Blue (#155EEF) is the
 *   interactive colour — primary buttons, links, focus, the active-nav accent.
 *   The active nav row is a restrained translucent-white fill, never a pill. Red
 *   Cross red held back for identity, urgency and destruction. 264px rail,
 *   56px header, 36px nav rows — rows, not pills.
 * STORY: A signed-in volunteer lands, sees the one thing asked of them now at the
 *   top, then what is coming, then their own standing — and acts without hunting.
 * FIRST VIEWPORT: 264px sidebar (brand, 9-item grouped nav, "signed in at"
 *   branch foot). 56px header: breadcrumb left; Availability button, notification
 *   bell, account menu right. Canvas: date line + "Good morning, {name}", then a
 *   two-column grid — left: pending-action card (soft red border, "Action
 *   required"), tasks needing attention, "Coming up"; right (340px): availability
 *   nudge, "Your record", "Discover". The primary action sits in that first card.
 * FORM: Institutional workspace / back-office console. Brief- and prototype-
 *   pinned (the supplied HTML is the spatial contract); no concept roll.
 * FINISH: unreviewed and undocumented is unfinished; this build ends with the
 *   finish review, the verdict, DESIGN.md, and every shipping raster carrying its
 *   provenance.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { EditableText } from "../content/Editable";
import { EditToolbar } from "../content/EditToolbar";
import { BrandLockup } from "../ui/brand";
import { Icon, companionIcon } from "../ui/icons";
import { AccountMenu } from "./chrome/AccountMenu";
import { AvailabilityControl } from "./chrome/AvailabilityControl";
import { NotificationMenu } from "./chrome/NotificationMenu";
import { cx } from "./ui/kit";
import { ToastProvider } from "./ui/overlays";

export interface PortalNavItem {
	to: string;
	labelKey: string;
	fallback: string;
	icon: (props: { size?: number; className?: string }) => ReactNode;
	/** A group heading is drawn whenever this differs from the previous item's. */
	group?: string;
	groupFallback?: string;
	badge?: number;
}

/**
 * A door out of this app. Route and label both come from the server —
 * `api/companions.py` reads each app's own `add_to_apps_screen` declaration —
 * so nothing about where Learning or the service desk is mounted is written
 * down on this side.
 */
export interface PortalCompanion {
	app: string;
	href: string;
	labelKey: string;
	fallback: string;
}

/** Route → header title, for the addresses that are not a nav item. */
const EXTRA_TITLES: Record<string, string> = {
	"/notifications": "Notifications",
	"/profile": "Profile",
	"/availability": "Availability",
	"/training": "Training",
};

function titleFor(pathname: string, items: PortalNavItem[]): { key?: string; fallback: string } {
	let best: PortalNavItem | null = null;
	for (const item of items) {
		if (
			(pathname === item.to || pathname.startsWith(`${item.to}/`)) &&
			(!best || item.to.length > best.to.length)
		) {
			best = item;
		}
	}
	if (best) return { key: best.labelKey, fallback: best.fallback };
	return { fallback: EXTRA_TITLES[pathname] ?? "" };
}

/**
 * The signed-in volunteer's chrome.
 *
 * Forked from the console's `ui/Shell.tsx` on purpose (see the direction
 * contract above). The two share only the icon set, `BrandLockup`, and the
 * content layer; everything visual here is the portal's own.
 */
export function PortalShell({
	items,
	companions = [],
	unread,
	onUnreadChange,
	console: consolePath,
	person,
	email,
	branch,
}: {
	items: PortalNavItem[];
	/** Apps installed beside this one, or none. Empty is the ordinary case. */
	companions?: PortalCompanion[];
	unread: number;
	onUnreadChange: () => void;
	/** Where the console switch points, or nothing — passed only when permitted. */
	console: string | null;
	person: string | null;
	email: string | null;
	/** The person's serving branch, for the sidebar foot. */
	branch: string | null;
}) {
	const location = useLocation();
	const [drawer, setDrawer] = useState(false);

	const title = titleFor(location.pathname, items);

	// Close the mobile drawer on navigation, and lock the page behind it.
	useEffect(() => setDrawer(false), [location.pathname]);
	useEffect(() => {
		if (!drawer) return;
		const previous = document.body.style.overflow;
		document.body.style.overflow = "hidden";
		const onKey = (event: KeyboardEvent) => {
			if (event.key === "Escape") setDrawer(false);
		};
		document.addEventListener("keydown", onKey);
		return () => {
			document.body.style.overflow = previous;
			document.removeEventListener("keydown", onKey);
		};
	}, [drawer]);

	const nav = (
		<nav aria-label="Portal" className="flex flex-col gap-0.5">
			{items.map((item, index) => {
				const previous = items[index - 1];
				const startsGroup = item.group && item.group !== previous?.group;

				return (
					<div key={item.to}>
						{startsGroup && (
							<div className="px-2.5 pb-1.5 pt-4 text-[10px] font-semibold uppercase tracking-[0.1em] text-white/60">
								<EditableText k={item.group as string} fallback={item.groupFallback ?? ""} />
							</div>
						)}
						<NavLink
							to={item.to}
							end={item.to === "/dashboard"}
							className={({ isActive }) =>
								cx(
									"group flex min-h-[36px] items-center gap-3 rounded-[9px] px-2.5 py-2 text-[13.5px] transition-colors",
									isActive
										? "bg-white/[0.12] font-semibold text-white"
										: "font-medium text-white/80 hover:bg-white/[0.06] hover:text-white",
								)
							}
						>
							{({ isActive }) => (
								<>
									<span
										className={cx(
											"flex-none transition-colors",
											isActive ? "text-white" : "text-white/65 group-hover:text-white",
										)}
									>
										<item.icon size={17} />
									</span>
									<EditableText
										k={item.labelKey}
										fallback={item.fallback}
										className="flex-1 truncate"
									/>
									{item.badge !== undefined && item.badge > 0 && (
										<span className="grid h-[18px] min-w-[18px] flex-none place-items-center rounded-full bg-white px-1 text-[11px] font-bold leading-none text-blue-press">
											{item.badge > 9 ? "9+" : item.badge}
										</span>
									)}
								</>
							)}
						</NavLink>
					</div>
				);
			})}
		</nav>
	);

	/**
	 * The apps installed beside this one.
	 *
	 * Under a rule of their own and under their own heading, because these are
	 * not destinations in this product: clicking Learning leaves the portal for
	 * another app with its own navigation, and a row that does that sitting in
	 * the same list as Tasks would be a trapdoor. Each carries the app's own
	 * glyph, so the three are told apart at a glance rather than by reading.
	 *
	 * Nothing is drawn when nothing is installed — no heading, no rule, no
	 * empty state. An absent companion app is the ordinary case, not a gap.
	 */
	const companionNav = companions.length > 0 && (
		<div className="mt-4 border-t border-white/15 pt-3">
			<div className="px-2.5 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-white/60">
				<EditableText k="portal.nav.companions" fallback="Also available" />
			</div>
			<nav aria-label="Other apps" className="flex flex-col gap-0.5">
				{companions.map((item) => {
					const Glyph = companionIcon(item.app);

					return (
						<a
							key={item.app}
							href={item.href}
							className="group flex min-h-[36px] items-center gap-3 rounded-[9px] px-2.5 py-2 text-[13.5px] font-medium text-white/80 transition-colors hover:bg-white/[0.06] hover:text-white"
						>
							<span className="flex-none text-white/65 transition-colors group-hover:text-white">
								<Glyph size={17} />
							</span>
							<EditableText k={item.labelKey} fallback={item.fallback} className="flex-1 truncate" />
							{/* The one place the arrow still earns its keep: it is what
							    says this row leaves the product. */}
							<Icon.external size={13} className="flex-none text-white/40" />
						</a>
					);
				})}
			</nav>
		</div>
	);

	const railBody = (
		<>
			<Link
				to="/dashboard"
				className="mb-3 flex items-center px-2 pt-1"
				aria-label="Home"
			>
				<BrandLockup wrap tone="dark" />
			</Link>
			{nav}
			{companionNav}
			{branch && (
				<div className="mt-auto border-t border-white/15 px-2.5 pb-1 pt-4">
					<div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-white/60">
						Signed in at
					</div>
					<div className="mt-1 text-[12px] font-semibold text-white">{branch}</div>
				</div>
			)}
		</>
	);

	return (
		<ToastProvider>
			<div className="portal-root min-h-screen">
				<div className="flex min-h-screen">
					{/* ---------------------------------------------------------- sidebar */}
					<aside
						className="portal-rail-scroll sticky top-0 hidden h-screen w-[264px] flex-none flex-col overflow-y-auto bg-rail px-3 pb-4 pt-4 md:flex"
					>
						{railBody}
					</aside>

					{/* --------------------------------------------------- content column */}
					<div className="flex min-w-0 flex-1 flex-col">
						<header className="sticky top-0 z-40 flex h-14 flex-none items-center gap-3 bg-canvas/95 px-4 backdrop-blur-sm md:px-6">
							<button
								type="button"
								onClick={() => setDrawer(true)}
								aria-label="Open navigation"
								aria-expanded={drawer}
								className="-ml-1 grid h-8 w-8 flex-none place-items-center rounded-lg text-slate-strong transition hover:bg-rail-hover md:hidden"
							>
								<Icon.menu size={18} />
							</button>

							<Link to="/dashboard" className="min-w-0 flex-1 md:hidden">
								<BrandLockup compact />
							</Link>

							{/* The concept's breadcrumb. "Portal" is the trunk and is a link
							    home; the leaf is the section, which for a detail route is
							    still the section the record belongs to — a docname is not a
							    place, and a detail page carries its own way back. */}
							<nav
								aria-label="Breadcrumb"
								className="hidden min-w-0 flex-1 items-center gap-1.5 text-[13px] md:flex"
							>
								<Link
									to="/dashboard"
									className="flex-none text-muted transition-colors hover:text-ink"
								>
									Portal
								</Link>
								{title.fallback && (
									<>
										<span aria-hidden="true" className="flex-none text-slate-faint">
											/
										</span>
										<h1 className="min-w-0 truncate font-semibold text-ink" aria-current="page">
											{title.key ? (
												<EditableText k={title.key} fallback={title.fallback} />
											) : (
												title.fallback
											)}
										</h1>
									</>
								)}
							</nav>

							<div className="ml-auto flex items-center gap-2">
								<AvailabilityControl />
								<NotificationMenu unread={unread} onCountChange={onUnreadChange} />
								<AccountMenu name={person} email={email} console={consolePath} />
							</div>
						</header>

						<main className="min-w-0 flex-1 px-4 pb-16 pt-4 md:px-8">
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
							role="dialog"
							aria-modal="true"
							aria-label="Navigation"
							className="portal-rail-scroll absolute inset-y-0 left-0 flex w-[264px] max-w-[86vw] flex-col overflow-y-auto bg-rail px-3 pb-5 pt-4 shadow-[0_18px_55px_rgba(25,30,38,0.24)]"
						>
							<div className="mb-3 flex items-center justify-between gap-2 px-2">
								<Link to="/dashboard" className="min-w-0">
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
							{nav}
							{companionNav}
							{branch && (
								<div className="mt-auto border-t border-white/15 px-2.5 pb-1 pt-4">
									<div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-white/60">
										Signed in at
									</div>
									<div className="mt-1 text-[12px] font-semibold text-white">{branch}</div>
								</div>
							)}
						</div>
					</div>
				)}

				<EditToolbar />
			</div>
		</ToastProvider>
	);
}
