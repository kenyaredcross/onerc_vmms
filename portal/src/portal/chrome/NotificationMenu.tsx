import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
import { Link, useNavigate } from "react-router-dom";

import { API } from "../../lib/api";
import { formatDate } from "../../lib/format";
import { Icon } from "../../ui/icons";
import type { NotificationRow } from "../types";
import { cx } from "../ui/kit";
import { usePopover } from "./popover";

/**
 * The header bell and the dropdown behind it.
 *
 * **The badge is the shell's, not this component's.** The count has to be
 * right on every screen including the ones that never open a notification, so
 * the shell polls `unread_count` and passes the number in; this component owns
 * only the short recent list it shows when opened. After "Mark all as read" it
 * asks the shell to refetch rather than keeping its own idea of the count —
 * two places counting is how they end up disagreeing in front of somebody.
 *
 * "Action required" is drawn from the urgency the server assigned, a value
 * from its own closed set, never re-decided here.
 */
export function NotificationMenu({
	unread,
	onCountChange,
}: {
	unread: number;
	onCountChange: () => void;
}) {
	const { open, setOpen, holder, trigger } = usePopover();
	const navigate = useNavigate();

	const feed = useFrappeGetCall<{
		message: { notifications: NotificationRow[]; unread: number };
	}>(API.myNotifications, { limit: 8 }, "portal:my_notifications");

	const markOne = useFrappePostCall(API.markNotificationRead);
	const markAll = useFrappePostCall(API.markAllNotificationsRead);

	const rows = feed.data?.message?.notifications ?? [];

	const openRow = async (row: NotificationRow) => {
		setOpen(false);
		if (!row.read) {
			await markOne.call({ source: row.source, name: row.id });
			void feed.mutate();
			onCountChange();
		}
		navigate(row.href && row.href.startsWith("/") ? row.href : "/notifications");
	};

	return (
		<div ref={holder} className="relative">
			<button
				ref={trigger}
				type="button"
				onClick={() => setOpen((was) => !was)}
				aria-haspopup="menu"
				aria-expanded={open}
				aria-label={`Notifications${unread > 0 ? ` (${unread} unread)` : ""}`}
				className={cx(
					"relative grid h-8 w-8 place-items-center rounded-lg border transition",
					open
						? "border-blue-line bg-blue-soft text-blue-press"
						: "border-rail-line bg-white text-slate-strong hover:border-slate-faint hover:text-ink",
				)}
			>
				<Icon.bell size={16} />
				{unread > 0 && (
					<span className="absolute -right-1 -top-1 grid h-[15px] min-w-[15px] place-items-center rounded-full bg-danger px-1 text-[9px] font-bold leading-none text-white ring-2 ring-canvas">
						{unread > 9 ? "9+" : unread}
					</span>
				)}
			</button>

			{open && (
				<div
					role="menu"
					className="absolute right-0 top-full z-50 mt-2 w-[min(392px,calc(100vw-2rem))] overflow-hidden rounded-xl border border-card-line bg-white shadow-[0_16px_40px_rgba(20,32,46,0.16)]"
				>
					<div className="flex items-center justify-between border-b border-card-line px-4 py-3">
						<span className="text-[13px] font-semibold text-ink">Notifications</span>
						{unread > 0 && (
							<button
								type="button"
								disabled={markAll.loading}
								onClick={() => {
									void markAll.call({}).then(() => {
										void feed.mutate();
										onCountChange();
									});
								}}
								className="text-[12px] font-semibold text-blue transition hover:text-blue-hover disabled:opacity-50"
							>
								Mark all as read
							</button>
						)}
					</div>

					<div className="max-h-[392px] overflow-y-auto">
						{feed.isLoading && (
							<p className="px-4 py-6 text-center text-[12px] text-muted">Loading…</p>
						)}

						{!feed.isLoading && rows.length === 0 && (
							<p className="px-4 py-8 text-center text-[12.5px] text-muted">
								Nothing to read. Alerts and news from your branch arrive here.
							</p>
						)}

						{rows.map((row) => (
							<button
								key={`${row.source}:${row.id}`}
								type="button"
								onClick={() => void openRow(row)}
								className={cx(
									"flex w-full gap-2.5 border-b border-card-line px-4 py-3 text-left transition last:border-b-0 hover:bg-canvas",
									!row.read && "bg-blue-soft/40",
								)}
							>
								<span
									className={cx(
										"mt-1.5 h-1.5 w-1.5 flex-none rounded-full",
										row.read ? "bg-transparent" : "bg-blue",
									)}
									aria-hidden="true"
								/>
								<span className="min-w-0 flex-1">
									<span className="flex items-center gap-2">
										<span
											className={cx(
												"truncate text-[12.5px] text-ink",
												row.read ? "font-medium" : "font-semibold",
											)}
										>
											{row.title}
										</span>
										{row.urgency === "urgent" && (
											<span className="flex-none rounded bg-danger-soft px-1.5 py-0.5 text-[10px] font-semibold text-danger">
												Action
											</span>
										)}
									</span>
									{(row.summary || row.body) && (
										<span className="mt-0.5 line-clamp-2 block text-[11.5px] leading-snug text-muted">
											{row.summary || row.body}
										</span>
									)}
									<span className="mt-1 block text-[10.5px] text-muted">
										{formatDate(row.sent_on)}
									</span>
								</span>
							</button>
						))}
					</div>

					<Link
						to="/notifications"
						onClick={() => setOpen(false)}
						className="block border-t border-card-line bg-canvas px-4 py-3 text-center text-[12.5px] font-semibold text-blue transition hover:bg-rail-hover"
					>
						View all notifications
					</Link>
				</div>
			)}
		</div>
	);
}
