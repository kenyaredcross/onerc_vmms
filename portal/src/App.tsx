import { Suspense, lazy, useEffect, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { loginUrl, useSession } from "./lib/session";
import { Spinner } from "./ui/primitives";

/**
 * Everything the app can be, and who may see it.
 *
 * **Split at the three audiences.** The landing page and the join wizard are
 * what a signed-out visitor loads, and neither should carry the portal's or the
 * console's code. `lazy` keeps them apart, so a first-time visitor downloads a
 * marketing page rather than a coordinator's review queue they will never open.
 *
 * **The root is the landing page, for everybody.** It used to fork — a guest saw
 * the page and anybody signed in was redirected to their dashboard — on the
 * reasoning that a person who has already joined does not want to be sold to.
 * The reasoning was wrong: the landing page is also where the society says what
 * it is doing, and a member who follows a link to it and gets bounced into an
 * application form has been told the public page is not for them. Being signed
 * in changes one control in the header, not which page exists at the address.
 */
const Landing = lazy(() => import("./guest/Landing"));
const Join = lazy(() => import("./guest/Join"));
// Its own chunk, and outside `RequireAuth` on purpose: `api/locations.py` serves
// published locations to a guest, because somebody looking for their nearest
// office does not have an account yet. It also carries Leaflet, which no other
// screen loads, so keeping it separate is what stops a map library reaching a
// volunteer's dashboard.
const Locations = lazy(() => import("./guest/Locations"));
// Its own chunk, and a small one: this is the only screen in the app that is
// routinely opened on a phone camera's browser, on whatever connection a field
// site has.
const Verify = lazy(() => import("./guest/Verify"));

const PortalLayout = lazy(() => import("./portal/PortalLayout"));
const Dashboard = lazy(() => import("./portal/Dashboard"));
const Membership = lazy(() => import("./portal/Membership"));
const Hours = lazy(() => import("./portal/Hours"));
const Profile = lazy(() => import("./portal/Profile"));
const Notifications = lazy(() => import("./portal/Notifications"));
// Its own chunk rather than part of `Discover`: the events screen carries a
// hero, a filter bar and an image grid, and it is the one portal screen a person
// may open without ever touching the rest of the portal.
const Events = lazy(() => import("./portal/Events"));
// Also its own chunk, and for the same reason: a filter bar, a cascading
// location picker and a card grid, opened by people who never touch the rest.
const Opportunities = lazy(() => import("./portal/Opportunities"));
// The calendar is its own chunk rather than part of the events one, even though
// the two share a hook and a grid: a person who browses events may never open a
// calendar and the other way round, and the shared pieces are small enough that
// the bundler puts them where both can reach them.
const Calendar = lazy(() => import("./portal/Calendar"));
// Each detail view shares its listing's chunk: somebody who opens a list is one
// click from opening a row, and splitting them would put a spinner between the
// two for no saving.
const EventDetail = lazy(() => import("./portal/Events").then((m) => ({ default: m.Event })));
const OpportunityDetail = lazy(() =>
	import("./portal/Opportunities").then((m) => ({ default: m.OpportunityDetail })),
);
// Stories and its reader share a chunk: somebody who opens the list is one click
// from opening one, and splitting them would put a spinner between the two.
const Stories = lazy(() => import("./portal/Stories"));
const Story = lazy(() => import("./portal/Stories").then((m) => ({ default: m.Story })));

const Tasks = lazy(() => import("./portal/Tasks"));

const AdminLayout = lazy(() => import("./admin/AdminLayout"));
// The review queue is two lists and one detail page, all in one chunk: an
// approver who opens a queue is one click from opening a row, and splitting
// them would put a spinner between the two for no saving. The two lists share
// a chunk with each other for a different reason — they are the same component
// with a different row in one table, so there is nothing to split.
const VolunteerQueue = lazy(() =>
	import("./admin/ReviewQueue").then((module) => ({ default: module.VolunteerQueue })),
);
const MembershipQueue = lazy(() =>
	import("./admin/ReviewQueue").then((module) => ({ default: module.MembershipQueue })),
);
const ApplicationReview = lazy(() => import("./admin/ReviewQueue"));
// Addressing a branch's own people. Its own chunk because it is the one console
// screen most coordinators will never open, and it carries a composer nothing
// else needs.
const Communication = lazy(() => import("./admin/Communication"));
const PeopleOverview = lazy(() => import("./admin/PeopleOverview"));
const RegistryMembers = lazy(() =>
	import("./admin/Registry").then((module) => ({ default: module.MembersRegistry })),
);
const RegistryVolunteers = lazy(() =>
	import("./admin/Registry").then((module) => ({ default: module.VolunteersRegistry })),
);
// One person in full, from either register. Its own chunk rather than part of
// Registry's: the dossier screens are much the larger of the two, and a
// coordinator scanning a list should not download them until they open somebody.
const Person = lazy(() => import("./admin/Person"));
const ContentAdmin = lazy(() => import("./admin/ContentAdmin"));
// The form builder. Its own chunk like every other tab, and one a coordinator
// never downloads because the section that admits it never reaches them.
const Questions = lazy(() => import("./admin/Questions"));
const AdminTasks = lazy(() => import("./admin/Tasks"));
// Analytics used to be one of the `Screens` gaps and is now a real screen over
// `api/analytics.py`, so it has its own chunk like the rest of them.
const Analytics = lazy(() => import("./admin/Analytics"));

const Deployments = lazy(() =>
	import("./portal/Discover").then((module) => ({ default: module.Deployments })),
);
const Training = lazy(() =>
	import("./portal/Discover").then((module) => ({ default: module.Training })),
);
// When a volunteer can serve. Its own chunk and its own route rather than a
// section of the profile, because it is the one page a coordinator will ask
// somebody to go and fill in, and "go to your profile and scroll" is a worse
// sentence than a link.
const Availability = lazy(() =>
	import("./portal/Availability").then((module) => ({ default: module.Availability })),
);

const Overview = lazy(() =>
	import("./admin/Screens").then((module) => ({ default: module.Overview })),
);
// The deployment console: a hub landing page and three registers under it —
// Terms of Reference, Deployments and Requests — each its own routed page
// rather than a tab, so every record has a URL somebody can link, bookmark or
// come back to. Projects is no longer one of them: it stands on its own at
// `/admin/projects`, its own console section, because a project does not need
// a terms of reference or a deployment to exist. Detail screens share a chunk
// with their own list, like `EventDetail`/`OpportunityDetail` above: whoever
// opens a list is one click from opening a row.
const DeploymentsHub = lazy(() =>
	import("./admin/Deployments").then((module) => ({ default: module.DeploymentsHub })),
);
const DeploymentList = lazy(() =>
	import("./admin/Deployments").then((module) => ({ default: module.DeploymentList })),
);
// The two routed bands over that same register — see `SCOPES` in Deployments.tsx.
// Separate routes rather than a filter somebody sets again after every reload:
// "what is running now" and "what did we do" are different questions, and each
// deserves an address a coordinator can send to a colleague.
const DeploymentsOngoing = lazy(() =>
	import("./admin/Deployments").then((module) => ({
		default: () => <module.DeploymentList scope="ongoing" />,
	})),
);
const DeploymentsPast = lazy(() =>
	import("./admin/Deployments").then((module) => ({
		default: () => <module.DeploymentList scope="past" />,
	})),
);
const DeploymentCreate = lazy(() =>
	import("./admin/Deployments").then((module) => ({ default: module.DeploymentCreate })),
);
const DeploymentDetail = lazy(() =>
	import("./admin/Deployments").then((module) => ({ default: module.DeploymentDetail })),
);
const DeploymentRequestList = lazy(() =>
	import("./admin/Deployments").then((module) => ({ default: module.RequestList })),
);
const ProjectList = lazy(() =>
	import("./admin/Projects").then((module) => ({ default: module.ProjectList })),
);
const ProjectDetail = lazy(() =>
	import("./admin/Projects").then((module) => ({ default: module.ProjectDetail })),
);
const TermsOfReferenceList = lazy(() =>
	import("./admin/Projects").then((module) => ({ default: module.TermsList })),
);
const TermsOfReferenceDetail = lazy(() =>
	import("./admin/Projects").then((module) => ({ default: module.TermsDetail })),
);
const Stipends = lazy(() => import("./admin/Stipends"));
const AdminEvents = lazy(() => import("./admin/Events"));

/**
 * Sends a signed-out visitor to Frappe's login and back again.
 *
 * A hard navigation rather than a client route, because the login page is
 * Frappe's and not part of this bundle. `replace` on the history is
 * deliberate: a person who signs in and then presses Back should land on
 * wherever they came from, not bounce through the login again.
 */
function RequireAuth({ children }: { children: ReactNode }) {
	const { isGuest, isLoading } = useSession();
	const send = !isLoading && isGuest;

	// In an effect, not in the render body. Navigating during render is a side
	// effect in a place React is allowed to call twice, and under StrictMode it
	// does exactly that.
	useEffect(() => {
		if (send) window.location.replace(loginUrl(window.location.pathname));
	}, [send]);

	if (isLoading) return <Spinner page label="Checking your session…" />;
	if (send) return <Spinner page label="Taking you to sign in…" />;

	return <>{children}</>;
}

/**
 * What each route is called, for the "loading" line while its chunk arrives.
 *
 * Keyed on the first path segment, and on the second one under /admin, because
 * that is the whole of the routing table's depth. A path with no entry falls
 * back to a screen-neutral sentence rather than to a guess made out of the URL:
 * a slug is not a title, and "Loading opportunity-detail…" is worse than saying
 * nothing specific.
 *
 * **Plain strings, not content blocks, and this is the one place that is right.**
 * Every other word in this product is a `VMMS Content Block` an administrator can
 * rewrite. These cannot be: they are shown *while* the code that would fetch the
 * wording is still downloading, so a content-driven label would be a spinner
 * waiting on a spinner.
 */
const ROUTE_NAMES: Record<string, string> = {
	"": "the portal",
	join: "the joining form",
	dashboard: "your dashboard",
	locations: "our locations",
	tasks: "your tasks",
	events: "events",
	opportunities: "opportunities",
	stories: "stories",
	notifications: "notifications",
	deployments: "deployments",
	membership: "your membership",
	hours: "your hours",
	profile: "your profile",
	training: "training",
	admin: "the console",
	"admin/queue": "the review queue",
	"admin/communication": "communication",
	"admin/registry": "the registry",
	"admin/tasks": "tasks",
	"admin/projects": "projects",
	"admin/deployments": "deployments",
	"admin/stipends": "stipends",
	"admin/events": "events",
	"admin/analytics": "analytics",
	"admin/content": "page content",
	"admin/questions": "form questions",
};

function RouteFallback() {
	const segments = useLocation().pathname.split("/").filter(Boolean);
	const name =
		ROUTE_NAMES[segments.slice(0, 2).join("/")] ?? ROUTE_NAMES[segments[0] ?? ""] ?? null;

	return <Spinner page label={name ? `Loading ${name}…` : "Loading…"} />;
}

export default function App() {
	return (
		<Suspense fallback={<RouteFallback />}>
			<Routes>
				<Route path="/" element={<Landing />} />
				<Route path="/join" element={<Join />} />
				<Route path="/locations" element={<Locations />} />
				{/* Where a scanned card lands. Guest by design: the person checking a
				    card at a gate has no account and never will. */}
				{/* Both reach the same read. The QR encodes the second; the first is
				    for a card whose code has to be typed, and it navigates to the
				    second so a checked card always has a URL. */}
				<Route path="/verify" element={<Verify />} />
				<Route path="/verify/:token" element={<Verify />} />

				<Route
					element={
						<RequireAuth>
							<PortalLayout />
						</RequireAuth>
					}
				>
					<Route path="/dashboard" element={<Dashboard />} />
					<Route path="/events" element={<Events />} />
					<Route path="/events/:name" element={<EventDetail />} />
					<Route path="/calendar" element={<Calendar />} />
					<Route path="/opportunities" element={<Opportunities />} />
					<Route path="/opportunities/:name" element={<OpportunityDetail />} />
					<Route path="/stories" element={<Stories />} />
					<Route path="/stories/:slug" element={<Story />} />
					<Route path="/notifications" element={<Notifications />} />
					<Route path="/deployments" element={<Deployments />} />
					<Route path="/availability" element={<Availability />} />
					<Route path="/membership" element={<Membership />} />
					<Route path="/hours" element={<Hours />} />
					<Route path="/tasks" element={<Tasks />} />
					<Route path="/profile" element={<Profile />} />
					{/* Learning is a tab in the sidebar, but it is a link out to the
					    LMS rather than a screen here. The route stays so an old
					    bookmark still lands somewhere real. */}
					<Route path="/training" element={<Training />} />
				</Route>

				<Route
					path="/admin"
					element={
						<RequireAuth>
							<AdminLayout />
						</RequireAuth>
					}
				>
					<Route index element={<Overview />} />
					{/* Two queues rather than one mixed list: approving volunteers
					    and approving memberships are two different jobs, and each
					    is a page somebody can link and finish. The bare `queue`
					    address is what every existing bookmark and the sidebar
					    badge used to point at, so it lands on the volunteer one
					    rather than on nothing. */}
					<Route path="queue" element={<Navigate to="/admin/queue/volunteers" replace />} />
					<Route path="queue/volunteers" element={<VolunteerQueue />} />
					<Route path="queue/members" element={<MembershipQueue />} />
					{/* Last of the queue routes, and one segment shorter than none
					    of them — `:kind` would happily match `volunteers`, so the
					    two static routes above have to be declared first for a
					    reader even though React Router ranks them itself. */}
					<Route path="queue/:kind/:name" element={<ApplicationReview />} />
					<Route path="registry/members" element={<RegistryMembers />} />
					<Route path="registry/volunteers" element={<RegistryVolunteers />} />
					{/* The kind is a path segment because a docname cannot say which
					    register it belongs to, and probing both endpoints to find out
					    would ask the server a question the link already knew. */}
					<Route path="registry/:kind/:name" element={<Person />} />
					<Route path="projects" element={<ProjectList />} />
					<Route path="projects/:name" element={<ProjectDetail />} />
					<Route path="deployments" element={<DeploymentsHub />} />
					<Route path="deployments/terms" element={<TermsOfReferenceList />} />
					<Route path="deployments/terms/:name" element={<TermsOfReferenceDetail />} />
					<Route path="deployments/list" element={<DeploymentList />} />
					{/* The section's own navigation points at these three. `list` above
					    stays for every existing bookmark and keeps the unscoped
					    register reachable. */}
					<Route path="deployments/ongoing" element={<DeploymentsOngoing />} />
					<Route path="deployments/past" element={<DeploymentsPast />} />
					<Route path="deployments/new" element={<DeploymentCreate />} />
					<Route path="deployments/requests" element={<DeploymentRequestList />} />
					{/* Last: `deployments/:name` is one segment shorter than every route
					    above it, and React Router matches the more specific static
					    segments first regardless of declaration order, so this never
					    shadows `terms`, `list` or `requests`. */}
					<Route path="deployments/:name" element={<DeploymentDetail />} />
					<Route path="stipends" element={<Stipends />} />
					<Route path="events" element={<AdminEvents />} />
					<Route path="tasks" element={<AdminTasks />} />
					<Route path="analytics" element={<Analytics />} />
					<Route path="people" element={<PeopleOverview />} />
					<Route path="communication" element={<Navigate to="/admin/communication/system/compose" replace />} />
					<Route path="communication/:channel/:view" element={<Communication />} />
					<Route path="content" element={<ContentAdmin />} />
					<Route path="questions" element={<Questions />} />
				</Route>

				{/* Anything unmatched is a mistyped or retired link, not an error
				    worth a page of its own. */}
				<Route path="*" element={<Navigate to="/" replace />} />
			</Routes>
		</Suspense>
	);
}
