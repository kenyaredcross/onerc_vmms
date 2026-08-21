import { useFrappeGetCall } from "frappe-react-sdk";

import { ContentProvider } from "../content/ContentProvider";
import { API } from "../lib/api";
import { geoPath } from "../lib/format";
import { Icon } from "../ui/icons";
import { Shell, type CompanionItem, type NavItem } from "../ui/Shell";
import type { RedProfile, VolunteerProfile } from "./types";

/**
 * The portal's own screens, in two groups.
 *
 * **The grouping is the question each screen answers, not a taxonomy.** The
 * first six are about this person — when their month is busy, what they have
 * been asked to do, where they have been sent, what they have given, what they
 * hold. The last three are about the society — what is on, what needs doing,
 * what happened. Nine tabs with no headings is a list somebody re-reads top to
 * bottom every time; two short groups is a list they jump into.
 *
 * The calendar sits second, next to the dashboard, because both are overviews
 * and neither is a register. It is in this group rather than the society's even
 * though it draws the society's events: what it answers is "what does my month
 * look like", and the events tab is where somebody goes to browse what is on.
 *
 * Notifications is deliberately absent, and so is Profile. Both are in the top
 * bar: the bell because "what has arrived for me" is wanted from every screen
 * rather than from a screen, and the avatar because the corner is where a
 * person looks for themselves.
 *
 * The companion apps — Learning, chat, the service desk — are not in this list
 * either. They are resolved at runtime from `companions.available`, because
 * whether they exist at all is a property of the site rather than of this file.
 */
const YOURS = { groupKey: "portal.nav.group.yours", groupFallback: "Your work" };
const SOCIETY = { groupKey: "portal.nav.group.society", groupFallback: "Your society" };

const ITEMS: NavItem[] = [
	{ to: "/dashboard", labelKey: "portal.nav.home", fallback: "Home", icon: Icon.home, ...YOURS },
	{ to: "/calendar", labelKey: "portal.nav.calendar", fallback: "Calendar", icon: Icon.calendar, ...YOURS },
	{ to: "/tasks", labelKey: "portal.nav.tasks", fallback: "My tasks", icon: Icon.check, ...YOURS },
	{ to: "/deployments", labelKey: "portal.nav.deployments", fallback: "Deployments", icon: Icon.truck, ...YOURS },
	// Beside Deployments rather than buried in the profile. This is the page a
	// coordinator will ask somebody to go and fill in, and "open your profile and
	// scroll" is a worse sentence to have to say than a link.
	{ to: "/availability", labelKey: "portal.nav.availability", fallback: "My availability", icon: Icon.clock, ...YOURS },
	{ to: "/hours", labelKey: "portal.nav.hours", fallback: "My hours", icon: Icon.clock, ...YOURS },
	{ to: "/membership", labelKey: "portal.nav.membership", fallback: "Membership", icon: Icon.card, ...YOURS },
	// Not the calendar glyph any more: the calendar tab above has it, and two
	// tabs carrying one icon is the rail's only wayfinding cue spent twice.
	// Browsing what is on and planning your own month are the two things a
	// person most needs to tell apart here.
	{ to: "/events", labelKey: "portal.nav.events", fallback: "Events", icon: Icon.sparkle, ...SOCIETY },
	{ to: "/opportunities", labelKey: "portal.nav.opportunities", fallback: "Opportunities", icon: Icon.compass, ...SOCIETY },
	{ to: "/stories", labelKey: "portal.nav.stories", fallback: "Stories", icon: Icon.book, ...SOCIETY },
];

/**
 * The signed-in volunteer and member surface.
 *
 * The sidebar's subtitle is the person's serving branch, read from their own
 * volunteer record. Somebody who is a member but not a volunteer has no branch
 * to show and gets no subtitle, rather than a placeholder.
 *
 * **Three reads, and none of them blocks the chrome.** The sidebar renders on
 * the first paint with no badge and no companion tabs, and both fill in when
 * their answers arrive. A navigation that waits for three round trips before it
 * appears is a navigation somebody stares at, and neither answer changes where
 * any of the seven fixed tabs go.
 */
export default function PortalLayout() {
	const { data } = useFrappeGetCall<{ message: VolunteerProfile | null }>(
		API.myVolunteer,
		undefined,
		"portal:my_volunteer",
	);

	// The badge. Deliberately its own endpoint rather than a count taken from
	// the notifications screen: the number has to be right on every screen,
	// including the ones that never load a notification.
	const unread = useFrappeGetCall<{ message: { unread: number } }>(
		API.unreadCount,
		undefined,
		"portal:unread_count",
	);

	const companions = useFrappeGetCall<{ message: { apps: CompanionItem[] } }>(
		API.companionApps,
		undefined,
		"portal:companion_apps",
	);

	// Whether this person has a manager console, asked of the server rather
	// than inferred from anything on this screen. A volunteer gets `available:
	// false` and no button; somebody holding a staff scope role gets the way
	// across without having to be told an address. Same call `AdminLayout`
	// filters its own tabs with, so the two cannot disagree.
	const console_ = useFrappeGetCall<{ message: { available: boolean; sections: string[] } }>(
		API.consoleSections,
		undefined,
		"portal:console_sections",
	);

	// What this person is called, for the greeting and the avatar in the corner.
	// `my_volunteer` above carries a name too, but only for somebody with a
	// volunteer record — a member-only person has none, and they are as entitled
	// to be greeted by name as anybody. Shares the key the profile screen already
	// uses, so this is the same response rather than a second request.
	const me = useFrappeGetCall<{ message: RedProfile | null }>(
		API.myProfile,
		undefined,
		"portal:my_profile",
	);

	const placement = data?.message?.geo_path;

	return (
		<ContentProvider surface="chrome,portal">
			<Shell
				items={ITEMS}
				companions={companions.data?.message?.apps ?? []}
				bell={{
					to: "/notifications",
					count: unread.data?.message?.unread ?? 0,
					labelKey: "portal.nav.notifications",
					fallback: "Notifications",
				}}
				console={console_.data?.message?.available ? "/admin" : null}
				tone="portal"
				person={me.data?.message?.full_name ?? null}
				subtitle={placement ? geoPath(placement) : null}
			/>
		</ContentProvider>
	);
}
