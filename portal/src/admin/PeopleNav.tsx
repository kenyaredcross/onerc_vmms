import { SubNav, type SubNavItem } from "../ui/SubNav";

export const PEOPLE_NAV: SubNavItem[] = [
	{ to: "/admin/people", labelKey: "admin.people.nav.overview", fallback: "Overview", end: true },
	{ to: "/admin/queue/volunteers", labelKey: "admin.people.nav.volunteer_queue", fallback: "Volunteer applications", groupKey: "admin.people.nav.review", groupFallback: "Review queue" },
	{ to: "/admin/queue/members", labelKey: "admin.people.nav.member_queue", fallback: "Membership applications", groupKey: "admin.people.nav.review" },
	{ to: "/admin/registry/members", labelKey: "admin.people.nav.members", fallback: "Members", groupKey: "admin.people.nav.insight", groupFallback: "People & Insight" },
	{ to: "/admin/registry/volunteers", labelKey: "admin.people.nav.volunteers", fallback: "Volunteers", groupKey: "admin.people.nav.insight" },
];

export function inPeople(pathname: string) {
	return pathname === "/admin/people" || pathname.startsWith("/admin/queue") || pathname.startsWith("/admin/registry");
}

export function PeopleSubNav({ horizontal = false }: { horizontal?: boolean }) {
	return <SubNav title="People Management" items={PEOPLE_NAV} horizontal={horizontal} />;
}
