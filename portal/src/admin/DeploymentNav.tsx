import { SubNav, type SubNavItem } from "../ui/SubNav";

/**
 * The Deployments section's own navigation.
 *
 * **Every entry is a route.** "Create deployment" is a page, not a modal flag;
 * "Ongoing" and "Past" are two addresses over one register rather than a filter
 * somebody has to set again after every reload. That is the difference between
 * a screen a coordinator can send a colleague a link to and one they have to
 * describe how to reach.
 *
 * Ordered plan-then-manage, because that is the order the work happens in: a
 * mission is written, a deployment is raised from it, and then it is run.
 */
export const DEPLOYMENT_NAV: SubNavItem[] = [
	{
		to: "/admin/deployments",
		labelKey: "admin.deployments.nav.dashboard",
		fallback: "Operations overview",
		// The section's index route, so it does not stay selected while a child
		// route is open.
		end: true,
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

/** Is this path inside the section that owns `DEPLOYMENT_NAV`? */
export function inDeployments(pathname: string): boolean {
	return pathname === "/admin/deployments" || pathname.startsWith("/admin/deployments/");
}

export function DeploymentSubNav({ horizontal = false }: { horizontal?: boolean }) {
	return <SubNav title="Operations" items={DEPLOYMENT_NAV} horizontal={horizontal} />;
}
