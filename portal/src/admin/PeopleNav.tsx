import { SubNav, type SubNavItem } from "../ui/SubNav";

/**
 * A panel row, plus the console section a person must hold to be offered it.
 *
 * The same shape `DeploymentNav.tsx` uses, and needed more here: People's rows
 * come from three different sections, so a panel that offered all of them would
 * be offering most people a column of links straight back to `/admin`. The
 * rail's own rows have always been filtered this way — `narrowGroup` — and
 * since the rail no longer lists these, this is the only filter left.
 */
type Destination = SubNavItem & { section?: string };

/**
 * People Management's own column.
 *
 * Three headings, and the order is the answer to "how did this person get
 * here": everybody asking to join, then everybody who already has. The
 * recruitment pair sits under **Coming in** beside the two application queues
 * because a job opening is the third door into the society, and a coordinator
 * clearing job applications is doing the same shape of work as one clearing
 * volunteer applications.
 *
 * **This is the only place these six are listed.** The rail draws People
 * Management as a single row — it declares `hasSubNav`, so arriving here takes
 * the rail down to icons, which hides a group's children and disables the
 * control that would bring them back. See `ConsoleShell`'s `childrenInPanel`.
 */
export const PEOPLE_NAV: Destination[] = [
	// No `section`: the overview is gated on `people`, the key this whole panel
	// stands behind, so anybody seeing the panel holds it.
	{ to: "/admin/people", labelKey: "admin.people.nav.overview", fallback: "Overview", end: true },
	{
		to: "/admin/queue/volunteers",
		labelKey: "admin.people.nav.volunteer_queue",
		fallback: "Volunteer applications",
		groupKey: "admin.people.nav.review",
		groupFallback: "Coming in",
		section: "queue",
	},
	{ to: "/admin/queue/members", labelKey: "admin.people.nav.member_queue", fallback: "Membership applications", groupKey: "admin.people.nav.review", section: "queue" },
	{ to: "/admin/recruitment/applications", labelKey: "admin.people.nav.job_applications", fallback: "Job applications", groupKey: "admin.people.nav.review", section: "recruitment" },
	{
		to: "/admin/recruitment/openings",
		labelKey: "admin.people.nav.openings",
		fallback: "Job openings",
		groupKey: "admin.people.nav.recruit",
		groupFallback: "Recruitment",
		section: "recruitment",
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
		section: "registry",
	},
	{
		to: "/admin/registry/members",
		labelKey: "admin.people.nav.members",
		fallback: "Active members",
		groupKey: "admin.people.nav.insight",
		section: "registry",
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

/**
 * `sections` is what the server said this person holds. Omitted — in a test, or
 * anywhere the answer has not arrived — every row is offered, which is the
 * behaviour this panel had before any of it was gated.
 */
export function PeopleSubNav({
	horizontal = false,
	sections,
}: {
	horizontal?: boolean;
	sections?: ReadonlySet<string>;
}) {
	const items = sections
		? PEOPLE_NAV.filter((item) => !item.section || sections.has(item.section))
		: PEOPLE_NAV;

	return <SubNav title="People" items={items} horizontal={horizontal} />;
}
