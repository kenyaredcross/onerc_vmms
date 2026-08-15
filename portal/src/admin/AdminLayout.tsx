import { useFrappeGetCall } from "frappe-react-sdk";
import { Navigate, useLocation } from "react-router-dom";

import { ContentProvider } from "../content/ContentProvider";
import { API } from "../lib/api";
import { Icon } from "../ui/icons";
import { Shell, type NavItem } from "../ui/Shell";
import { Spinner } from "../ui/primitives";
import type { ApprovalStatus } from "../portal/types";

/**
 * The manager console.
 *
 * Same shell as the volunteer portal in a darker skin, which is the design's
 * way of saying "you are acting on other people's records now". The queue count
 * in the sidebar is live and comes from the same `my_queue` the queue screen
 * renders, so the two can never disagree.
 *
 * **There is still no role name in this file, and there is now a role check.**
 * Those are different things, and the file used to conflate them: it drew all
 * nine tabs for everybody on the grounds that hiding one would mean naming a
 * society's coordinator role here. Naming a role here is indeed forbidden — so
 * the answer comes from `api/console.py`, which computes it from the same
 * permission layer every screen behind these tabs already goes through, and
 * hands back section *keys* this app owns. A society that names a Deployment
 * Manager gets a Deployments tab for its holders; nothing in `portal/src/`
 * learns what the role is called.
 *
 * A person holding none of the society's staff scope roles is not shown an
 * empty console — they are sent back to their own portal. An empty queue beside
 * an empty registry is not an honest answer to a volunteer who followed a stale
 * link; it is nine screens that look broken.
 */

/** Every tab the console can draw, keyed by the section that admits it. */
const TABS: (NavItem & { section: string })[] = [
	{
		section: "overview",
		to: "/admin",
		labelKey: "admin.nav.overview",
		fallback: "Overview",
		icon: Icon.home,
		end: true,
	},
	{
		section: "queue",
		to: "/admin/queue",
		labelKey: "admin.nav.queue",
		fallback: "Review queue",
		icon: Icon.inbox,
	},
	{ section: "registry", to: "/admin/registry", labelKey: "admin.nav.registry", fallback: "Registry", icon: Icon.people },
	{ section: "tasks", to: "/admin/tasks", labelKey: "admin.nav.tasks", fallback: "Tasks", icon: Icon.check },
	{
		section: "deployments",
		to: "/admin/deployments",
		labelKey: "admin.nav.deployments",
		fallback: "Deployments",
		icon: Icon.truck,
	},
	{ section: "stipends", to: "/admin/stipends", labelKey: "admin.nav.stipends", fallback: "Stipends", icon: Icon.coins },
	{ section: "events", to: "/admin/events", labelKey: "admin.nav.events", fallback: "Events", icon: Icon.calendar },
	{
		section: "analytics",
		to: "/admin/analytics",
		labelKey: "admin.nav.analytics",
		fallback: "Analytics",
		icon: Icon.chart,
	},
	{ section: "content", to: "/admin/content", labelKey: "admin.nav.content", fallback: "Page content", icon: Icon.pencil },
	// Admitted by `console.ADMIN_SECTIONS`, which gates it on a doctype no
	// configurable role is granted — so it resolves to the administrator and to
	// nobody else. Drawn from the section list like every other tab: this file
	// still learns nothing about who anybody is.
	{
		section: "questions",
		to: "/admin/questions",
		labelKey: "admin.nav.questions",
		fallback: "Form questions",
		icon: Icon.book,
	},
];

/**
 * Which section the current URL belongs to.
 *
 * `/admin` itself is the overview; everything else is its second segment. Kept
 * as a lookup against `TABS` rather than a second list of paths, so a tab and
 * the route it guards cannot drift apart.
 */
function sectionOf(pathname: string): string | null {
	const exact = TABS.find((tab) => tab.to === pathname.replace(/\/$/, ""));

	return exact?.section ?? null;
}

export default function AdminLayout() {
	const location = useLocation();

	const access = useFrappeGetCall<{
		message: { available: boolean; sections: string[]; desk?: boolean };
	}>(
		API.consoleSections,
		undefined,
		"admin:sections",
	);

	const queue = useFrappeGetCall<{ message: ApprovalStatus[] }>(
		API.myQueue,
		undefined,
		"admin:my_queue",
	);

	// Nothing is drawn until the server has answered. Rendering the full sidebar
	// and then removing tabs would show somebody a Stipends tab they are about to
	// lose, which is worse than a moment of nothing.
	if (access.isLoading) {
		return <Spinner page label="Loading the console…" />;
	}

	const answer = access.data?.message;
	const allowed = new Set(answer?.sections ?? []);

	// No staff role at all, or the call failed — either way this is not their
	// screen. A failure sends them somewhere real rather than to a shell that
	// cannot populate itself.
	if (!answer?.available) {
		return <Navigate to="/dashboard" replace />;
	}

	// A section they do not hold, reached by typing the address or following an
	// old bookmark. Back to the console's own front page, not to an empty screen.
	const current = sectionOf(location.pathname);

	if (current && !allowed.has(current)) {
		return <Navigate to="/admin" replace />;
	}

	const waiting = queue.data?.message?.length ?? 0;

	const items: NavItem[] = TABS.filter((tab) => allowed.has(tab.section)).map((tab) =>
		tab.section === "queue" ? { ...tab, badge: waiting } : tab,
	);

	return (
		<ContentProvider surface="chrome,admin">
			{/* The way back. A coordinator is also a person with their own record,
			    and the console has been a one-way door since it was built: the only
			    way out was the browser's back button or an address they had to
			    remember. Unconditional here, because everybody who can see this
			    shell has a portal — being staff is a role somebody holds, not a
			    thing they are instead of a volunteer. */}
			<Shell
				items={items}
				console="/dashboard"
				// The Frappe desk, for whoever the server says may open it. The
				// console covers the day-to-day; the desk is where the settings,
				// the reports and every doctype without a screen of its own live,
				// and somebody setting a society up should not have to be told the
				// address. `api/console.py` answers with the same function that
				// gates the VMMS tile on the apps screen, so nobody is offered a
				// door that would give them a permission error.
				desk={answer?.desk ? "/app" : null}
				tone="admin"
				subtitle="Manager"
			/>
		</ContentProvider>
	);
}
