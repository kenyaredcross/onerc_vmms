/**
 * The registrations that have a review queue, and everything that differs
 * between them.
 *
 * **Its own module, and a tiny one, because two chunks need it.** The queue
 * screens draw from it and the console's sidebar counts from it, and the
 * sidebar must not pull in the review screens to know that a volunteer
 * application and a membership are two different lists. No React and no
 * imports, so this costs the layout chunk almost nothing.
 *
 * **A table rather than two components.** Every value here is a label, a route
 * or a doctype name — never a behaviour. A third governed doctype gains a queue
 * by adding a row and a route, not by a screen learning what it is.
 *
 * **This is the one place in the frontend that names a governed doctype**, and
 * it has to be somewhere: a URL segment (`/admin/queue/volunteers`) has to map
 * to the argument `my_queue` takes. It is not a role and not a stage label —
 * the two things this app genuinely forbids the frontend from knowing — and
 * nothing here branches on it.
 */
export interface QueueSpec {
	/** What `approvals.my_queue` and `approvals.get_status` are asked about. */
	doctype: string;
	/** Where the list lives. Detail pages hang under it. */
	list: string;
	heading: string;
	/** Content key for the heading, so a society renames its own screens. */
	headingKey: string;
	/** What the person under review is, for a confirmation sentence. */
	noun: string;
	empty: string;
}

export const QUEUES = {
	volunteers: {
		doctype: "VMMS Volunteer Application",
		list: "/admin/queue/volunteers",
		heading: "Volunteer applications",
		headingKey: "admin.queue.volunteers.heading",
		noun: "volunteer applicant",
		empty: "No volunteer application is waiting on you.",
	},
	members: {
		doctype: "VMMS Membership",
		list: "/admin/queue/members",
		heading: "Membership applications",
		headingKey: "admin.queue.members.heading",
		noun: "membership applicant",
		empty: "No membership application is waiting on you.",
	},
} as const satisfies Record<string, QueueSpec>;

export type QueueKind = keyof typeof QUEUES;

export const QUEUE_KINDS = Object.keys(QUEUES) as QueueKind[];

/** Which queue a doctype belongs to — for a badge count, or a stray link. */
export function queueOf(doctype: string): QueueKind | null {
	return QUEUE_KINDS.find((kind) => QUEUES[kind].doctype === doctype) ?? null;
}
