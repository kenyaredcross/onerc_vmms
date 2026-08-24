import { Link } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { Icon } from "../ui/icons";
import { Card, ErrorNote, PageHeading, SectionTitle, StatGrid, StatTile } from "../ui/primitives";
import { QUEUES, queueOf } from "./queues";
import type { ApprovalStatus } from "../portal/types";

export default function PeopleOverview() {
	const queue = useFrappeGetCall<{ message: ApprovalStatus[] }>(API.myQueue, undefined, "admin:my_queue");
	const members = useFrappeGetCall<{ message: { total: number; member_count?: number } }>(API.findMembers, { limit: 1 }, "people:member-total");
	const volunteers = useFrappeGetCall<{ message: { total: number } }>(API.findVolunteers, { limit: 1 }, "people:volunteer-total");
	const waiting = queue.data?.message ?? [];
	const count = (kind: "volunteers" | "members") => waiting.filter((row) => queueOf(row.doctype) === kind).length;

	return <>
		<PageHeading title="People Management" lead="Review applications and work with the member and volunteer records you are authorised to see." />
		{(queue.error || members.error || volunteers.error) && <div className="mb-5"><ErrorNote>{errorMessage(queue.error || members.error || volunteers.error, "People totals could not be loaded.")}</ErrorNote></div>}
		<StatGrid className="mb-6">
			<StatTile label="Volunteer applications" value={queue.isLoading ? "—" : count("volunteers")} icon={Icon.inbox} tint="navy" to={QUEUES.volunteers.list} />
			<StatTile label="Membership applications" value={queue.isLoading ? "—" : count("members")} icon={Icon.card} tint="amber" to={QUEUES.members.list} />
			<StatTile label="Volunteers in scope" value={volunteers.isLoading ? "—" : (volunteers.data?.message.total ?? "—")} icon={Icon.people} tint="teal" to="/admin/registry/volunteers" />
			<StatTile label="Members in scope" value={members.isLoading ? "—" : (members.data?.message.total ?? members.data?.message.member_count ?? "—")} icon={Icon.card} tint="violet" to="/admin/registry/members" />
		</StatGrid>
		<Card>
			<SectionTitle>Attention</SectionTitle>
			{waiting.some((row) => row.stage?.is_breached) ? <ul className="space-y-2">{(["volunteers", "members"] as const).map((kind) => {
				const overdue = waiting.filter((row) => queueOf(row.doctype) === kind && row.stage?.is_breached).length;
				return overdue ? <li key={kind}><Link className="chev block rounded-card px-3 py-2.5 text-[13px] font-semibold text-navy hover:bg-surface" to={QUEUES[kind].list}>{overdue} {QUEUES[kind].heading.toLowerCase()} beyond the configured review SLA</Link></li> : null;
			})}</ul> : <p className="text-[13px] text-slate-body">No applications assigned to you are beyond their configured review SLA.</p>}
			<p className="mt-4 border-t border-hairline pt-4 text-[12px] text-slate-faint">Certification expiry, renewal, and unmatched-payment totals are not shown because no permission-scoped aggregate API currently supplies them.</p>
		</Card>
	</>;
}
