import type { ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { EditableText } from "../content/Editable";
import { Icon } from "../ui/icons";
import { cx } from "../portal/ui/kit";

const channels = ["system", "email", "sms", "whatsapp"] as const;
type Channel = (typeof channels)[number];

const CHANNEL_TITLES: Record<Channel, string> = {
	system: "In app",
	email: "Email",
	sms: "SMS",
	whatsapp: "WhatsApp",
};

const CHANNEL_ICONS: Record<Channel, (props: { size?: number }) => ReactNode> = {
	system: Icon.bell,
	email: Icon.mail,
	sms: Icon.phone,
	whatsapp: Icon.whatsapp,
};

const channelTitle = (channel: Channel) => CHANNEL_TITLES[channel];

export function inCommunication(pathname: string) {
	return pathname === "/admin/communication" || pathname.startsWith("/admin/communication/");
}

/**
 * Communication's own column.
 *
 * **The channel is chosen first and it is a route, not a tab.** A composer for
 * SMS and a composer for WhatsApp are different forms with different limits, so
 * each one has an address; switching channel is a navigation and the screen is
 * rebuilt rather than half-reused.
 *
 * The four channels are a row of icons rather than four more list rows: they
 * are alternatives to each other, not four separate places, and a segmented
 * control is what that shape reads as. What you *do* on the chosen channel —
 * compose, look at what was sent, look at the channel itself — is the list
 * underneath.
 */
export function CommunicationSubNav({ horizontal = false }: { horizontal?: boolean }) {
	const { pathname } = useLocation();
	const match = pathname.match(/^\/admin\/communication\/(system|email|sms|whatsapp)\/(compose|sent|channel)$/);
	const channel = (match?.[1] ?? "system") as Channel;
	const title = channelTitle(channel);
	const composeLabel = channel === "system" ? "Compose notification" : `Compose ${title}`;
	const sentLabel = channel === "system" ? "Sent notifications" : `Sent ${title}`;

	const row = (isActive: boolean) =>
		cx(
			"flex min-h-[34px] items-center gap-2.5 rounded-lg px-3 py-1.5 text-[12.5px] transition-colors",
			isActive
				? "bg-blue-soft font-semibold text-blue-press"
				: "font-medium text-slate-strong hover:bg-canvas hover:text-ink",
		);

	if (horizontal) {
		return (
			<nav aria-label="Communication sections" className="flex w-max items-center gap-1 py-0.5">
				{channels.map((item) => (
					<NavLink
						key={item}
						to={`/admin/communication/${item}/compose`}
						className={cx(row(item === channel), "whitespace-nowrap")}
					>
						{channelTitle(item)}
					</NavLink>
				))}
				<span aria-hidden="true" className="mx-1 h-4 w-px bg-card-line" />
				<NavLink
					to={`/admin/communication/${channel}/sent`}
					className={({ isActive }) => cx(row(isActive), "whitespace-nowrap")}
				>
					Sent
				</NavLink>
			</nav>
		);
	}

	return (
		<div className="flex flex-col">
			<h2 className="px-3 pb-3.5 pt-1 text-[14px] font-semibold tracking-[-0.01em] text-ink">Communication</h2>

			<div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.09em] text-rail-label">
				Channel
			</div>

			<nav aria-label="Communication channels" className="grid grid-cols-4 gap-1 rounded-xl bg-surface p-1">
				{channels.map((item) => {
					const Glyph = CHANNEL_ICONS[item];
					const selected = item === channel;

					return (
						<NavLink
							key={item}
							to={`/admin/communication/${item}/compose`}
							aria-current={selected ? "page" : undefined}
							title={channelTitle(item)}
							className={cx(
								"grid place-items-center gap-1 rounded-lg px-1 py-2 text-center text-[9.5px] font-semibold transition",
								selected
									? "bg-white text-blue-press shadow-[0_1px_2px_rgba(30,50,73,0.06)]"
									: "text-muted hover:text-ink",
							)}
						>
							<Glyph size={15} />
							<span className="truncate leading-none">{channelTitle(item)}</span>
						</NavLink>
					);
				})}
			</nav>

			<nav aria-label={`${title} actions`} className="mt-4 flex flex-col gap-0.5">
				<NavLink to={`/admin/communication/${channel}/compose`} className={({ isActive }) => row(isActive)}>
					<Icon.pencil size={14} className="flex-none text-slate-faint" />
					<EditableText k={`admin.communication.nav.${channel}.compose`} fallback={composeLabel} />
				</NavLink>
				<NavLink to={`/admin/communication/${channel}/sent`} className={({ isActive }) => row(isActive)}>
					<Icon.check size={14} className="flex-none text-slate-faint" />
					<EditableText k={`admin.communication.nav.${channel}.sent`} fallback={sentLabel} />
				</NavLink>
				{/* WhatsApp is the one channel with a *thing* behind it rather than
				    just a history: a linked phone that can drop, a pacing limit, and
				    a list of people who have replied STOP. The other three have no
				    such surface, so they do not get an empty one. */}
				{channel === "whatsapp" && (
					<NavLink to="/admin/communication/whatsapp/channel" className={({ isActive }) => row(isActive)}>
						<Icon.whatsapp size={14} className="flex-none text-slate-faint" />
						<EditableText k="admin.communication.nav.whatsapp.channel" fallback="The channel" />
					</NavLink>
				)}
			</nav>
		</div>
	);
}
