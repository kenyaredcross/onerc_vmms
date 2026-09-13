import { SubNav, type SubNavItem } from "../ui/SubNav";

/**
 * A panel row, plus the console section a person must hold to be offered it.
 *
 * The rail filters its own rows against the section keys `api/console.py`
 * hands back; a panel that did not would offer somebody a destination
 * `AdminLayout` is about to bounce them out of. Only rows whose section differs
 * from the panel's own need it — see `DeploymentSubNav`.
 */
type Destination = SubNavItem & { section?: string };

/**
 * The Deployments section's own navigation.
 *
 * **Every entry is a route.** "Create deployment" is a page, not a modal flag;
 * "Ongoing" and "Past" are two addresses over one register rather than a filter
 * somebody has to set again after every reload. That is the difference between
 * a screen a coordinator can send a colleague a link to and one they have to
 * describe how to reach.
 *
 * Ordered programme-then-plan-then-manage, because that is the order the work
 * happens in: a programme is opened, a mission is written under it, a
 * deployment is raised from that mission, and then it is run.
 *
 * **Projects and Tasks are here because the rail cannot hold them open.** They
 * are rows under Operations on the global rail, and this section declares
 * `hasSubNav`, so arriving anywhere in Operations takes the rail down to icons
 * — which hides a group's children, and disables the expand control while the
 * panel is up. Before they were listed here, a coordinator standing on the
 * Operations overview had no route to Projects at all on a desktop: not in the
 * rail, not in this panel, and not from the overview's own content. The panel
 * is this section's navigation, and these are two of its destinations.
 */
export const DEPLOYMENT_NAV: Destination[] = [
	{
		to: "/admin/deployments",
		labelKey: "admin.deployments.nav.dashboard",
		fallback: "Operations overview",
		// The section's index route, so it does not stay selected while a child
		// route is open.
		end: true,
	},
	{
		to: "/admin/projects",
		// The rail's own key, not one of this panel's. Both rows point at the
		// same page, and a society that renames Projects on the rail means the
		// panel too — two keys would let the two navigations disagree about what
		// the destination is called.
		labelKey: "admin.nav.projects",
		fallback: "Projects",
		groupKey: "admin.deployments.nav.group.programme",
		groupFallback: "Programme",
		// No `section` of its own: Projects is gated on `deployments`, the same
		// key this whole panel stands behind, so anybody seeing the panel holds
		// it.
	},
	{
		to: "/admin/tasks",
		labelKey: "admin.nav.tasks",
		fallback: "Tasks",
		groupKey: "admin.deployments.nav.group.programme",
		// Its own section, unlike Projects: a society can give somebody
		// deployments without giving them tasks.
		section: "tasks",
	},
	{
		to: "/admin/deployments/terms",
		labelKey: "admin.deployments.nav.terms",
		fallback: "Terms of Reference",
		groupKey: "admin.deployments.nav.group.plan",
		groupFallback: "Plan",
	},
	{
		to: "/admin/deployments/new",
		labelKey: "admin.deployments.nav.create",
		fallback: "Create deployment",
		groupKey: "admin.deployments.nav.group.plan",
	},
	{
		to: "/admin/deployments/ongoing",
		labelKey: "admin.deployments.nav.ongoing",
		fallback: "Ongoing deployments",
		groupKey: "admin.deployments.nav.group.manage",
		groupFallback: "Manage",
	},
	{
		to: "/admin/deployments/requests",
		labelKey: "admin.deployments.nav.requests",
		fallback: "Deployment requests",
		groupKey: "admin.deployments.nav.group.manage",
	},
	{
		to: "/admin/deployments/documents",
		labelKey: "admin.deployments.nav.documents",
		fallback: "Documents",
		groupKey: "admin.deployments.nav.group.manage",
	},
	{
		to: "/admin/deployments/past",
		labelKey: "admin.deployments.nav.past",
		fallback: "Past deployments",
		groupKey: "admin.deployments.nav.group.manage",
	},
];

/**
 * Is this path inside the section that owns `DEPLOYMENT_NAV`?
 *
 * Projects and Tasks count. They are Operations' destinations, listed in this
 * panel and no longer under the rail's Operations row, so a Projects page
 * without the panel would be a page in this section with none of its
 * navigation on it — and no way across to Tasks but back through the hub.
 */
export function inDeployments(pathname: string): boolean {
	return ["/admin/deployments", "/admin/projects", "/admin/tasks"].some(
		(base) => pathname === base || pathname.startsWith(`${base}/`),
	);
}

/**
 * `sections` is what the server said this person holds. Omitted — in a test, or
 * anywhere the answer has not arrived — every row is offered, which is the
 * behaviour this panel had before any of it was gated.
 */
export function DeploymentSubNav({
	horizontal = false,
	sections,
}: {
	horizontal?: boolean;
	sections?: ReadonlySet<string>;
}) {
	const items = sections
		? DEPLOYMENT_NAV.filter((item) => !item.section || sections.has(item.section))
		: DEPLOYMENT_NAV;

	return <SubNav title="Operations" items={items} horizontal={horizontal} />;
}
