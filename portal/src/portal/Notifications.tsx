import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import { Button, Empty, ErrorNote, PageHeading, Spinner, cx } from "../ui/primitives";

/**
 * What the society has told this person, from both places it comes from.
 *
 * The merge happens on the server, in `notifications/services/delivery.py`: a
 * branch's own announcements and the framework's notifications arrive as one
 * list of one shape. This screen therefore has no idea there are two sources
 * and never branches on which one a row came from — it passes `source` back with
 * `id` when marking one read, and that pair is opaque to it.
 *
 * **Urgency is styled, not decided.** `rank` and the ordering are the server's;
 * this only picks a colour from the urgency it was handed. The alternative —
 * a frontend that sorts by its own idea of importance — puts two answers to
 * "what matters" in a system where one of them is the one people act on.
 */

interface Notification {
	id: string;
	source: string;
	title: string;
	summary: string;
	body: string;
	urgency: string;
	rank: number;
	label: string;
	geo_node: string;
	sent_on: string;
	read: boolean;
	link_label: string;
	href: string;
}

/**
 * Colour by urgency. Keyed off the closed set the server owns, exactly as
 * `StateBadge` keys off the approval engine's closed set of states, and for the
 * same reason: these are code-owned values, not a society's vocabulary. An
 * announcement's *type* is the society's vocabulary and is rendered as a plain
 * label with no styling attached to its value.
 */
const URGENCY: Record<string, { chip: string; rail: string; word: string }> = {
	urgent: {
		chip: "border-signal/30 bg-signal/10 text-signal-dark",
		rail: "bg-signal",
		word: "Urgent",
	},
	important: {
		chip: "border-amber-200 bg-amber-50 text-amber-700",
		rail: "bg-amber-400",
		word: "Important",
	},
};

export default function Notifications() {
	const { data, error, isLoading, mutate } = useFrappeGetCall<{
		message: { notifications: Notification[]; unread: number };
	}>(API.myNotifications, undefined, "portal:my_notifications");

	const markOne = useFrappePostCall(API.markNotificationRead);
	const markAll = useFrappePostCall(API.markAllNotificationsRead);

	const rows = data?.message?.notifications ?? [];
	const unread = data?.message?.unread ?? 0;

	// Refetching after a write rather than editing a local copy. The badge in the
	// sidebar reads its own endpoint, and two places keeping their own idea of
	// the unread count is how they end up disagreeing in front of somebody.
	const read = async (row: Notification) => {
		if (row.read) return;

		await markOne.call({ source: row.source, name: row.id });
		await mutate();
	};

	return (
		<>
			<PageHeading
				title={<EditableText k="portal.notifications.heading" fallback="Notifications" />}
				trail={[{ label: "Home", to: "/dashboard" }, { label: "Notifications" }]}
				actions={
					unread > 0 && (
						<Button
							variant="soft"
							disabled={markAll.loading}
							onClick={() => {
								void markAll.call({}).then(() => mutate());
							}}
						>
							<Icon.check size={15} />
							{markAll.loading ? "Marking…" : `Mark all read (${unread})`}
						</Button>
					)
				}
			/>

			{isLoading && <Spinner label="Loading your notifications…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}
			{markOne.error && <ErrorNote>{errorMessage(markOne.error)}</ErrorNote>}

			{!isLoading && !error && rows.length === 0 && (
				<Empty title="Nothing to read" icon={Icon.bell}>
					Alerts, advisories and news from your branch and the national society arrive here.
				</Empty>
			)}

			<ul className="space-y-3">
				{rows.map((row) => {
					const tone = URGENCY[row.urgency];

					return (
						<li
							key={`${row.source}:${row.id}`}
							className={cx(
								"relative overflow-hidden rounded-card bg-white px-5 transition",
								// A read notification recedes to the ground rather than
								// keeping a card's lift: the list is a queue, and what is
								// left in it should be what is left to do.
								row.read ? "border border-hairline-soft" : "shadow-card",
							)}
						>
							{/* The rail is the only thing carrying urgency at a glance, and
							    it is absent for routine news rather than being drawn in a
							    neutral colour: a list where every row has a coloured edge
							    is a list where none of them means anything. */}
							{tone && !row.read && (
								<span className={cx("absolute inset-y-0 left-0 w-1", tone.rail)} aria-hidden="true" />
							)}

							<div className="flex flex-wrap items-start gap-3 py-4">
								<div className="min-w-0 flex-1">
									<div className="flex flex-wrap items-center gap-2">
										{!row.read && (
											<span
												className="h-1.5 w-1.5 flex-none rounded-full bg-signal"
												aria-label="Unread"
											/>
										)}
										<h2
											className={cx(
												"font-display text-[13.5px] leading-snug text-ink",
												row.read ? "font-semibold" : "font-bold",
											)}
										>
											{row.title}
										</h2>
										{tone && (
											<span
												className={cx(
													"rounded-full border px-2 py-0.5 text-[10px] font-bold",
													tone.chip,
												)}
											>
												{tone.word}
											</span>
										)}
										{row.label && (
											<span className="rounded-full border border-hairline-strong px-2 py-0.5 text-[10px] font-semibold text-slate-body">
												{row.label}
											</span>
										)}
									</div>

									{(row.summary || row.body) && (
										<p className="mt-1.5 whitespace-pre-line text-[12.5px] leading-relaxed text-slate-body">
											{row.summary || row.body}
										</p>
									)}

									<div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-slate-faint">
										<span>{formatDate(row.sent_on)}</span>
										{row.href && (
											// Server-validated on save: site-relative, or http,
											// https, mailto or tel. See vmmsx/links.py.
											<a
												href={row.href}
												className="inline-flex items-center gap-1 font-semibold text-navy hover:text-signal"
											>
												{row.link_label || "Open"}
												<Icon.external size={11} />
											</a>
										)}
									</div>
								</div>

								{!row.read && (
									<button
										type="button"
										onClick={() => void read(row)}
										className="flex-none rounded-full px-3 py-1.5 text-[11px] font-bold text-slate-body transition hover:bg-page hover:text-navy"
									>
										Mark read
									</button>
								)}
							</div>
						</li>
					);
				})}
			</ul>
		</>
	);
}
