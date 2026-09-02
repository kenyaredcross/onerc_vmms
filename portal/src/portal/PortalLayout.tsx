import { useFrappeGetCall } from "frappe-react-sdk";

import { ContentProvider } from "../content/ContentProvider";
import { API } from "../lib/api";
import { geoPath } from "../lib/format";
import { Icon } from "../ui/icons";
import { PortalShell, type PortalCompanion, type PortalNavItem } from "./PortalShell";
import type { DeploymentInvitation, RedProfile, TaskSummary, VolunteerProfile } from "./types";

/**
 * The portal's destinations, in the order the brief names them.
 *
 * Three bands: what is being asked of this person (Home, Calendar, Tasks,
 * Deployments), the record they hold (Memberships, Service hours), and what the
 * society has on (Events, Opportunities, Stories). Availability is not here —
 * it is a header control. Notifications and Profile are not here either; the
 * bell and the avatar in the header are where a person looks for them.
 *
 * Labels are content blocks (`portal.nav.*`) so a society renames its own
 * navigation without a deploy.
 */
const RECORD = { group: "portal.nav.group.record", groupFallback: "My record" };
const SOCIETY = { group: "portal.nav.group.society", groupFallback: "From the society" };

/**
 * The signed-in volunteer and member surface.
 *
 * Four possessive reads, none blocking the chrome: the shell paints on the
 * first frame with no badges, and the badges fill in as their answers land.
 * `my_tasks` and `my_invitations` share their SWR keys with the dashboard, so
 * a person landing on Home pays for them once between the two.
 */
export default function PortalLayout() {
	const volunteer = useFrappeGetCall<{ message: VolunteerProfile | null }>(
		API.myVolunteer,
		undefined,
		"portal:my_volunteer",
	);

	const me = useFrappeGetCall<{ message: RedProfile | null }>(
		API.myProfile,
		undefined,
		"portal:my_profile",
	);

	const unread = useFrappeGetCall<{ message: { unread: number } }>(
		API.unreadCount,
		undefined,
		"portal:unread_count",
	);

	const console_ = useFrappeGetCall<{ message: { available: boolean; sections: string[] } }>(
		API.consoleSections,
		undefined,
		"portal:console_sections",
	);

	const tasks = useFrappeGetCall<{ message: { volunteer: string; tasks: TaskSummary[] } | null }>(
		API.myTasks,
		{ include_closed: 0 },
		"portal:my_tasks:false",
	);

	const invitations = useFrappeGetCall<{
		message: { volunteer: string; waiting: DeploymentInvitation[]; answered: DeploymentInvitation[] } | null;
	}>(API.myInvitations, undefined, "portal:my_invitations");

	// Learning, chat and the service desk, when a society runs them beside this.
	// Shared SWR key with the console's rail: a coordinator who moves between
	// the two surfaces pays for this answer once.
	const companions = useFrappeGetCall<{
		message: { apps: Array<{ app: string; href: string; label_key: string; fallback: string }> };
	}>(API.companionApps, undefined, "portal:companion_apps");

	const openTasks = tasks.data?.message?.tasks.length ?? 0;

	const companionItems: PortalCompanion[] = (companions.data?.message?.apps ?? []).map((row) => ({
		app: row.app,
		href: row.href,
		labelKey: row.label_key,
		fallback: row.fallback,
	}));
	const waitingInvites = invitations.data?.message?.waiting.length ?? 0;

	const items: PortalNavItem[] = [
		{ to: "/dashboard", labelKey: "portal.nav.home", fallback: "Home", icon: Icon.home },
		{ to: "/calendar", labelKey: "portal.nav.calendar", fallback: "Calendar", icon: Icon.calendar },
		{ to: "/tasks", labelKey: "portal.nav.tasks", fallback: "Tasks", icon: Icon.check, badge: openTasks },
		{
			to: "/deployments",
			labelKey: "portal.nav.deployments",
			fallback: "Deployments",
			icon: Icon.truck,
			badge: waitingInvites,
		},
		{ to: "/membership", labelKey: "portal.nav.membership", fallback: "Memberships", icon: Icon.card, ...RECORD },
		{ to: "/hours", labelKey: "portal.nav.hours", fallback: "Service hours", icon: Icon.clock, ...RECORD },
		{ to: "/events", labelKey: "portal.nav.events", fallback: "Events", icon: Icon.sparkle, ...SOCIETY },
		{ to: "/opportunities", labelKey: "portal.nav.opportunities", fallback: "Opportunities", icon: Icon.compass, ...SOCIETY },
		{ to: "/stories", labelKey: "portal.nav.stories", fallback: "Stories", icon: Icon.book, ...SOCIETY },
		// The society's own answers, from core's FAQ. Under "From the society"
		// because that is what it is — what the society says, rather than
		// anything asked of this person.
		{ to: "/help", labelKey: "portal.nav.help", fallback: "Help", icon: Icon.lifebuoy, ...SOCIETY },
	];

	const path = volunteer.data?.message?.geo_path;
	const branch = path ? geoPath(path).split(" · ")[0] || null : null;

	return (
		<ContentProvider surface="chrome,portal">
			<PortalShell
				items={items}
				companions={companionItems}
				unread={unread.data?.message?.unread ?? 0}
				onUnreadChange={() => void unread.mutate()}
				console={console_.data?.message?.available ? "/admin" : null}
				person={me.data?.message?.full_name ?? volunteer.data?.message?.full_name ?? null}
				email={me.data?.message?.email ?? volunteer.data?.message?.email ?? null}
				branch={branch}
			/>
		</ContentProvider>
	);
}
