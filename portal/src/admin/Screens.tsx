import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API } from "../lib/api";
import { Card, PageHeading, SectionTitle, Stat } from "../ui/primitives";
import type { ApprovalStatus } from "../portal/types";

/**
 * The coordinator screens that are either a summary of other screens or an
 * honest gap. Grouped in one file because none of them carries enough of its
 * own logic to earn a module.
 */

/* ---------------------------------------------------------------- overview */

export function Overview() {
	const queue = useFrappeGetCall<{ message: ApprovalStatus[] }>(
		API.myQueue,
		undefined,
		"admin:my_queue",
	);
	const members = useFrappeGetCall<{ message: { count: number; member_count: number } }>(
		API.findMembers,
		{ limit: 200 },
		"admin:find_members",
	);
	const volunteers = useFrappeGetCall<{ message: { count: number } }>(
		API.findVolunteers,
		{ limit: 200 },
		"admin:find_volunteers",
	);

	const waiting = queue.data?.message ?? [];
	const overdue = waiting.filter((row) => row.stage?.is_breached).length;

	return (
		<>
			<PageHeading title={<EditableText k="admin.nav.overview" fallback="Overview" />} />

			<div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
				<Card>
					<Stat value={waiting.length} label="Waiting on you" />
				</Card>
				<Card>
					<Stat value={overdue} label="Past their SLA" />
				</Card>
				<Card>
					<Stat value={members.data?.message.member_count ?? "—"} label="Members in scope" />
				</Card>
				<Card>
					<Stat value={volunteers.data?.message.count ?? "—"} label="Volunteers in scope" />
				</Card>
			</div>

			<Card>
				<SectionTitle>Where to start</SectionTitle>
				<ul className="space-y-1">
					<li>
						<Link
							to="/admin/queue"
							className="chev block rounded-card px-3 py-2.5 text-[13px] font-semibold text-navy hover:bg-page"
						>
							Work through your review queue
						</Link>
					</li>
					<li>
						<Link
							to="/admin/registry"
							className="chev block rounded-card px-3 py-2.5 text-[13px] font-semibold text-navy hover:bg-page"
						>
							Look somebody up in the registry
						</Link>
					</li>
					<li>
						<Link
							to="/admin/content"
							className="chev block rounded-card px-3 py-2.5 text-[13px] font-semibold text-navy hover:bg-page"
						>
							Change the wording on the public page
						</Link>
					</li>
				</ul>
			</Card>
		</>
	);
}

/* ---------------------------------------------- what used to live here */
//
// Deployments, Stipends, Events and Analytics were all `NotBuilt` blocks in this
// file. Each now has its own screen reading real endpoints:
//
//   admin/Deployments.tsx  — api/deployment.py: listings, roster, matching
//   admin/Stipends.tsx     — api/stipend.py: reports, payment forms, approval
//   admin/Events.tsx       — api/events.py, over Buzz's published events
//   admin/Analytics.tsx    — api/analytics.py
//
// Two honest gaps survived the move rather than being papered over, and both
// are stated on the screen that owns them: revenue is absent from Analytics
// because a society's income is `onerc_payments`' record, and deciding stipend
// paperwork is refused by the server because departmental routing does not
// exist. Neither is a missing screen, so neither is a `NotBuilt`.
