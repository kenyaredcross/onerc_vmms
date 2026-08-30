import { NavLink, useLocation } from "react-router-dom";

import { EditableText } from "../content/Editable";
import { cx } from "../ui/primitives";

const channels = ["system", "email", "sms"] as const;
type Channel = (typeof channels)[number];

const channelTitle = (channel: Channel) =>
	channel === "system" ? "System" : channel === "sms" ? "SMS" : "Email";

export function inCommunication(pathname: string) {
	return pathname === "/admin/communication" || pathname.startsWith("/admin/communication/");
}

export function CommunicationSubNav({ horizontal = false }: { horizontal?: boolean }) {
	const { pathname } = useLocation();
	const match = pathname.match(/^\/admin\/communication\/(system|email|sms)\/(compose|sent)$/);
	const channel = (match?.[1] ?? "system") as Channel;
	const title = channelTitle(channel);
	const composeLabel = `Compose ${channel === "system" ? "system notification" : title}`;
	const sentLabel = `Sent ${channel === "system" ? "system notifications" : title}`;

	if (horizontal) {
		return (
			<nav aria-label="Communication sections" className="flex w-max items-center gap-1.5 py-0.5">
				{channels.map((item) => (
					<NavLink key={item} to={`/admin/communication/${item}/compose`} className={cx("rounded-full px-3.5 py-2 text-[12.5px] transition", item === channel ? "bg-white font-medium text-blue shadow-nav" : "text-slate-strong hover:bg-white/70")}>
						{channelTitle(item)}
					</NavLink>
				))}
				<NavLink to={`/admin/communication/${channel}/sent`} className="rounded-full px-3.5 py-2 text-[12.5px] text-slate-strong hover:bg-white/70">Sent</NavLink>
			</nav>
		);
	}

	return (
		<div className="flex flex-col">
			<h2 className="px-3.5 pb-5 pt-1 font-display text-[15px] font-medium tracking-tight text-ink">Communication</h2>

			<nav aria-label="Communication channels" className="grid grid-cols-3 gap-1 rounded-[12px] bg-black/[.055] p-1">
				{channels.map((item) => (
					<NavLink key={item} to={`/admin/communication/${item}/compose`} aria-current={item === channel ? "page" : undefined} className={cx("rounded-[9px] px-1 py-2 text-center text-[10px] transition", item === channel ? "bg-white font-medium text-blue shadow-nav" : "text-slate-body hover:text-ink")}>
						{channelTitle(item)}
					</NavLink>
				))}
			</nav>

			<nav aria-label={`${title} communication actions`} className="mt-4 flex flex-col gap-1">
				<NavLink to={`/admin/communication/${channel}/compose`} className={({ isActive }) => cx("rounded-[12px] px-3.5 py-3 text-[11px] transition", isActive ? "bg-white font-medium text-blue shadow-nav" : "text-slate-strong hover:bg-white/70")}>
					<EditableText k={`admin.communication.nav.${channel}.compose`} fallback={composeLabel} />
				</NavLink>
				<UnavailableItem label="All campaigns" />
				<NavLink to={`/admin/communication/${channel}/sent`} className={({ isActive }) => cx("rounded-[12px] px-3.5 py-3 text-[11px] transition", isActive ? "bg-white font-medium text-blue shadow-nav" : "text-slate-strong hover:bg-white/70")}>
					<EditableText k={`admin.communication.nav.${channel}.sent`} fallback={sentLabel} />
				</NavLink>
				<UnavailableItem label="Scheduled" />
				<UnavailableItem label="Drafts" />
				<UnavailableItem label="Templates" />
			</nav>
		</div>
	);
}

function UnavailableItem({ label }: { label: string }) {
	return (
		<div className="flex items-center justify-between rounded-[12px] px-3.5 py-3 text-[11px] text-slate-faint" aria-disabled="true" title="Not available yet">
			<span>{label}</span>
			<span className="text-[9px]">—</span>
		</div>
	);
}
