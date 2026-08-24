import { SubNav, type SubNavItem } from "../ui/SubNav";

const channels = ["system", "email", "sms"] as const;

export const COMMUNICATION_NAV: SubNavItem[] = channels.flatMap((channel) => {
	const title = channel === "system" ? "System" : channel === "sms" ? "SMS" : "Email";
	return [
		{
			to: `/admin/communication/${channel}/compose`,
			labelKey: `admin.communication.nav.${channel}.compose`,
			fallback: `Compose ${title === "System" ? "notification" : title}`,
			groupKey: `admin.communication.nav.channel.${channel}`,
			groupFallback: title,
		},
		{
			to: `/admin/communication/${channel}/sent`,
			labelKey: `admin.communication.nav.${channel}.sent`,
			fallback: `Sent ${title === "System" ? "notifications" : title}`,
			groupKey: `admin.communication.nav.channel.${channel}`,
		},
	];
});

export function inCommunication(pathname: string) {
	return pathname === "/admin/communication" || pathname.startsWith("/admin/communication/");
}

export function CommunicationSubNav({ horizontal = false }: { horizontal?: boolean }) {
	return <SubNav title="Communication" items={COMMUNICATION_NAV} horizontal={horizontal} />;
}
