import { Link, useLocation } from "react-router-dom";
import { useFrappeGetCall } from "frappe-react-sdk";
import { API } from "../lib/api";
import { useSocietyBranding } from "../ui/brand";
import { useSession } from "../lib/session";
import { Icon } from "../ui/icons";
import { isScheduledCommunication, useCommunicationHistory } from "./communication/history";
const channels = [
	{ key: "email", label: "Email", icon: Icon.mail },
	{ key: "sms", label: "SMS", icon: Icon.phone },
	{ key: "whatsapp", label: "WhatsApp", icon: Icon.chat },
	{ key: "system", label: "In-app notifications", icon: Icon.bell },
];
export function inCommunication(pathname: string) {
	return pathname === "/admin/communication" || pathname.startsWith("/admin/communication/");
}
export function CommunicationSubNav({ horizontal = false, showChannels = true }: { horizontal?: boolean; showChannels?: boolean }) {
	const society = useSocietyBranding();
	const { user } = useSession();
	const location = useLocation();
	const channel = location.pathname.split("/")[3] || "email";
	const {rows:history} = useCommunicationHistory(channel);
	const draft = location.search.includes("status=Draft");
	const scheduled = new URLSearchParams(location.search).get("status") === "Scheduled";
	const overview = location.pathname.endsWith("/overview");
	const { data } = useFrappeGetCall<{ message: { sender?: { name: string; email: string } } }>(
		API.communicationOptions, undefined, "admin:communication_options",
	);
	const useSender = channel === "email" || channel === "system";
	const accountName = useSender ? data?.message.sender?.name || society?.name || "Notifications" : history.find((row) => row.sender_email === user)?.sender || "Communication";
	const accountEmail = useSender ? data?.message.sender?.email || "Sending address not configured" : user;
	return (
		<nav
			className={`comm-section-nav ${horizontal ? "is-horizontal" : ""}`}
			aria-label="Communication navigation"
		>
			{!horizontal && (
				<div className="comm-account">
					<span className="comm-account-avatar">
						{accountName
							.split(/\s+/)
							.slice(0, 2)
							.map((part) => part[0])
							.join("")}
					</span>
					<h2>{accountName}</h2>
					<p>{accountEmail}</p>
				</div>
			)}
			<div className="comm-history-links">
				<Link to={`/admin/communication/${channel}/overview`} className={overview ? "is-selected" : ""} aria-current={overview?"page":undefined}><Icon.home size={15} />Overview</Link>
				<Link
					to={`/admin/communication/${channel}/sent`}
					className={!draft && !scheduled && location.pathname.endsWith("/sent") ? "is-selected" : ""}
				>
					<Icon.send size={15} />
					History<span>{history.length}</span>
				</Link>
				<Link to={`/admin/communication/${channel}/sent?status=Scheduled`} className={scheduled ? "is-selected" : ""} aria-current={scheduled?"page":undefined}><Icon.calendar size={15} />Scheduled<span>{history.filter(isScheduledCommunication).length}</span></Link>
				<Link
					to={`/admin/communication/${channel}/sent?status=Draft`}
					className={draft ? "is-selected" : ""} aria-current={draft?"page":undefined}
				>
					<Icon.file size={15} />
					Drafts<span>{history.filter((row) => row.status === "Draft").length}</span>
				</Link>
			</div>
			{showChannels && !horizontal && <h3>Channels</h3>}
			{showChannels && <div className="comm-channel-links">
				{channels.map((item) => (
					<Link
						key={item.key}
						to={`/admin/communication/${item.key}/overview`}
						className={channel === item.key ? "is-selected" : ""}
						aria-current={channel === item.key ? "page" : undefined}
					>
						<item.icon size={16} />
						<span>{item.label}</span>
					</Link>
				))}
			</div>}
			{!horizontal && channel === "whatsapp" && (
				<Link className="comm-channel-settings" to="/admin/communication/whatsapp/channel">
					<Icon.filter size={15} />
					Channel settings
				</Link>
			)}
		</nav>
	);
}
