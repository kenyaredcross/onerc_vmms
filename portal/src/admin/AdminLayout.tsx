import { useFrappeGetCall } from "frappe-react-sdk";
import { Navigate, useLocation } from "react-router-dom";

import { ContentProvider } from "../content/ContentProvider";
import { API } from "../lib/api";
import { Icon } from "../ui/icons";
import { Shell, type NavGroup, type NavItem } from "../ui/Shell";
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
 *
 * **Two of the tabs are `NavGroup`s now — real pages that also collapse a
 * clutch of others under them, the way `Shell.tsx`'s own docstring on
 * `NavGroup` describes.** People & Insight opens Analytics and reveals
 * Members, Volunteers and the review queue beneath it: all four answer "who
 * are my people and how are things going," read-first, nothing here is an
 * act. Operations opens the Deployments hub and reveals Projects and Tasks:
 * all three answer "make something happen." Overview, Stipends, Events,
 * Content and Questions stay outside both — none of them is a register
 * somebody browses for either reason, so grouping them would be tidying for
 * its own sake rather than a question the sidebar is answering.
 */
type TabDef = NavItem & { section: string };

const OVERVIEW: TabDef = {
	section: "overview",
	to: "/admin",
	labelKey: "admin.nav.overview",
	fallback: "Overview",
	icon: Icon.home,
	end: true,
};

// Both "registry": the same doctype permission (`VMMS Volunteer` or
// `VMMS Membership`, either admits) governs both, the same as it did when this
// was one Registry tab with a toggle. See `Registry.tsx`'s own docstring for
// why the toggle became two routed pages.
const MEMBERS: TabDef = {
	section: "registry",
	to: "/admin/registry/members",
	labelKey: "admin.nav.registry.members",
	fallback: "Members",
	icon: Icon.card,
};
const VOLUNTEERS: TabDef = {
	section: "registry",
	to: "/admin/registry/volunteers",
	labelKey: "admin.nav.registry.volunteers",
	fallback: "Volunteers",
	icon: Icon.people,
};
const QUEUE: TabDef = {
	section: "queue",
	to: "/admin/queue",
	labelKey: "admin.nav.queue",
	fallback: "Review queue",
	icon: Icon.inbox,
};
const ANALYTICS: TabDef = {
	section: "analytics",
	to: "/admin/analytics",
	labelKey: "admin.nav.analytics",
	fallback: "Analytics",
	icon: Icon.chart,
};

// Gated on "deployments", the same section `staff/services/permissions.py`
// grants `VMMS Project` under alongside `VMMS Deployment` and `VMMS Terms of
// Reference` — the one scope role named by `vmms_deployment_scope_role`. A
// society has never been able to hand out one without the others, so giving
// this its own section key would invent a distinction the permission model
// does not have. What moved is the URL — a project no longer lives at
// `/admin/deployments/projects`, because it does not need a deployment or a
// terms of reference to exist. See `Deployments.tsx`'s and `Projects.tsx`'s
// own docstrings.
const PROJECTS: TabDef = {
	section: "deployments",
	to: "/admin/projects",
	labelKey: "admin.nav.projects",
	fallback: "Projects",
	icon: Icon.tag,
};
const TASKS: TabDef = {
	section: "tasks",
	to: "/admin/tasks",
	labelKey: "admin.nav.tasks",
	fallback: "Tasks",
	icon: Icon.check,
};

const STIPENDS: TabDef = {
	section: "stipends",
	to: "/admin/stipends",
	labelKey: "admin.nav.stipends",
	fallback: "Stipends",
	icon: Icon.coins,
};
const EVENTS: TabDef = {
	section: "events",
	to: "/admin/events",
	labelKey: "admin.nav.events",
	fallback: "Events",
	icon: Icon.calendar,
};
const CONTENT: TabDef = {
	section: "content",
	to: "/admin/content",
	labelKey: "admin.nav.content",
	fallback: "Page content",
	icon: Icon.pencil,
};
// Admitted by `console.ADMIN_SECTIONS`, which gates it on a doctype no
// configurable role is granted — so it resolves to the administrator and to
// nobody else. Drawn from the section list like every other tab: this file
// still learns nothing about who anybody is.
const QUESTIONS: TabDef = {
	section: "questions",
	to: "/admin/questions",
	labelKey: "admin.nav.questions",
	fallback: "Form questions",
	icon: Icon.book,
};

/** A `NavGroup`'s own row, before its children are known to be allowed. */
interface GroupDef {
	section: string;
	to: string;
	labelKey: string;
	fallback: string;
	icon: NavItem["icon"];
	children: TabDef[];
}

const INSIGHT: GroupDef = {
	section: ANALYTICS.section,
	to: ANALYTICS.to,
	labelKey: "admin.nav.group.insight",
	fallback: "People & Insight",
	icon: ANALYTICS.icon,
	children: [MEMBERS, VOLUNTEERS, QUEUE],
};

const OPERATIONS: GroupDef = {
	section: "deployments",
	to: "/admin/deployments",
	labelKey: "admin.nav.group.operations",
	fallback: "Operations",
	icon: Icon.truck,
	children: [PROJECTS, TASKS],
};

const GROUPS = [INSIGHT, OPERATIONS];
const FLAT = [OVERVIEW, STIPENDS, EVENTS, CONTENT, QUESTIONS];

/**
 * Every routable tab this console can ever draw, gated or not — flattened out
 * of both `FLAT` and every `GroupDef`'s own row and its children. `sectionOf`
 * is the only reason this exists: a `NavGroup`'s own route (Analytics,
 * Deployments) has to be recognised by the guard below even though it is not
 * a `TabDef` sitting in `FLAT`.
 */
const ALL_ROUTES: { to: string; section: string }[] = [
	...FLAT,
	...GROUPS.map((group) => ({ to: group.to, section: group.section })),
	...GROUPS.flatMap((group) => group.children),
];

/**
 * Which section the current URL belongs to.
 *
 * `/admin` itself is the overview; everything else is its second segment. Kept
 * as a lookup against `ALL_ROUTES` rather than a second list of paths, so a
 * tab and the route it guards cannot drift apart.
 */
function sectionOf(pathname: string): string | null {
	const exact = ALL_ROUTES.find((route) => route.to === pathname.replace(/\/$/, ""));

	return exact?.section ?? null;
}

/**
 * One `GroupDef` narrowed to what this person may actually see.
 *
 * `null` when nobody's children survive — nothing to nest under a heading
 * that would open to a permission error. When exactly one child survives and
 * the group's own landing page is not itself allowed, the group is not drawn
 * at all: nesting that one child under a parent nobody can open would be a
 * heading over a heading, so the child is returned in its place instead,
 * exactly as it would have appeared outside a group.
 */
function narrowGroup(def: GroupDef, allowed: Set<string>): NavItem | NavGroup | null {
	const children = def.children.filter((child) => allowed.has(child.section));

	if (children.length === 0) return null;

	if (children.length === 1 && !allowed.has(def.section)) {
		return children[0];
	}

	return {
		to: allowed.has(def.section) ? def.to : children[0].to,
		labelKey: def.labelKey,
		fallback: def.fallback,
		icon: def.icon,
		children,
	};
}

export default function AdminLayout() {
	const location = useLocation();

	const access = useFrappeGetCall<{
		message: { available: boolean; sections: string[]; desk?: boolean; sms?: boolean };
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

	const withBadge = (item: NavItem): NavItem =>
		item.to === QUEUE.to ? { ...item, badge: waiting } : item;

	// Overview first (ungated, so always present once the console is available
	// at all), then the two groups, then the rest of `FLAT` in its own order —
	// fixed here rather than left to fall out of how the arrays happen to
	// concatenate.
	const flatAllowed = FLAT.filter((tab) => allowed.has(tab.section)).map(withBadge);
	const groups = GROUPS.map((def) => narrowGroup(def, allowed))
		.filter((item): item is NavItem | NavGroup => item !== null)
		.map((item): NavItem | NavGroup =>
			"children" in item ? { ...item, children: item.children.map(withBadge) } : withBadge(item),
		);

	const ordered: (NavItem | NavGroup)[] = [...flatAllowed.slice(0, 1), ...groups, ...flatAllowed.slice(1)];

	return (
		<ContentProvider surface="chrome,admin">
			{/* The way back. A coordinator is also a person with their own record,
			    and the console has been a one-way door since it was built: the only
			    way out was the browser's back button or an address they had to
			    remember. Unconditional here, because everybody who can see this
			    shell has a portal — being staff is a role somebody holds, not a
			    thing they are instead of a volunteer. */}
			<Shell
				items={ordered}
				console="/dashboard"
				// The Frappe desk, for whoever the server says may open it. The
				// console covers the day-to-day; the desk is where the settings,
				// the reports and every doctype without a screen of its own live,
				// and somebody setting a society up should not have to be told the
				// address. `api/console.py` answers with the same function that
				// gates the VMMS tile on the apps screen, so nobody is offered a
				// door that would give them a permission error.
				desk={answer?.desk ? "/app" : null}
				// A second, narrower door: onerc_sms's own campaign builder, for
				// whoever `staff/services/permissions.py` has granted the society's
				// configured SMS role. See `console.sms_access()`'s own docstring
				// for why this doctype cannot be a gated section like the tabs above.
				sms={answer?.sms ? "/app/sms-campaign/new" : null}
				tone="admin"
				subtitle="Manager"
			/>
		</ContentProvider>
	);
}
