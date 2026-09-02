import { SubNav, type SubNavItem } from "../ui/SubNav";

/**
 * People Management's own column.
 *
 * Three headings, and the order is the answer to "how did this person get
 * here": everybody asking to join, then everybody who already has. The
 * recruitment pair sits under **Coming in** beside the two application queues
 * because a job opening is the third door into the society, and a coordinator
 * clearing job applications is doing the same shape of work as one clearing
 * volunteer applications.
 */
export const PEOPLE_NAV: SubNavItem[] = [
	{ to: "/admin/people", labelKey: "admin.people.nav.overview", fallback: "Overview", end: true },
	{
		to: "/admin/queue/volunteers",
		labelKey: "admin.people.nav.volunteer_queue",
		fallback: "Volunteer applications",
		groupKey: "admin.people.nav.review",
		groupFallback: "Coming in",
	},
	{ to: "/admin/queue/members", labelKey: "admin.people.nav.member_queue", fallback: "Membership applications", groupKey: "admin.people.nav.review" },
	{ to: "/admin/recruitment/applications", labelKey: "admin.people.nav.job_applications", fallback: "Job applications", groupKey: "admin.people.nav.review" },
	{
		to: "/admin/recruitment/openings",
		labelKey: "admin.people.nav.openings",
		fallback: "Job openings",
		groupKey: "admin.people.nav.recruit",
		groupFallback: "Recruitment",
	},
	{
		// "Active volunteers", not "Volunteers": the register is of people
		// currently active, and a row labelled with the wider word would promise
		// a list that includes prospective, suspended and exited records. Each of
		// those is a state with its own screen; none of them belongs in the list
		// a coordinator staffs from.
		to: "/admin/registry/volunteers",
		labelKey: "admin.people.nav.volunteers",
		fallback: "Active volunteers",
		groupKey: "admin.people.nav.insight",
		groupFallback: "The register",
	},
	{
		to: "/admin/registry/members",
		labelKey: "admin.people.nav.members",
		fallback: "Active members",
		groupKey: "admin.people.nav.insight",
	},
];

export function inPeople(pathname: string) {
	return (
		pathname === "/admin/people" ||
		pathname.startsWith("/admin/queue") ||
		pathname.startsWith("/admin/registry") ||
		pathname.startsWith("/admin/recruitment")
	);
}

export function PeopleSubNav({ horizontal = false }: { horizontal?: boolean }) {
	return <SubNav title="People" items={PEOPLE_NAV} horizontal={horizontal} />;
}
