import { useState } from "react";
import { Icon } from "../../ui/icons";
import { DocumentIcon } from "../../ui/DocumentIcon";
import { isScheduledCommunication, type CommunicationRecord } from "./history";
const date = (value: string) =>
	new Date(value).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
const time = (value: string) =>
	new Date(value).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
const initials = (value: string) =>
	value
		.split(/\s+/)
		.slice(0, 2)
		.map((part) => part[0])
		.join("");
export function MessageReader({
	channel,
	current,
	history,
	index,
	total,
	onPrevious,
	onNext,
	onBack,
	onPin,
	onDetails,
	onReuse,
}: {
	channel: string;
	current: CommunicationRecord;
	history: CommunicationRecord[];
	index: number;
	total: number;
	onPrevious: () => void;
	onNext: () => void;
	onBack: () => void;
	onPin: () => void;
	onDetails: () => void;
	onReuse: (row: CommunicationRecord) => void;
}) {
	const [message, setMessage] = useState("");
	const chat = channel === "sms" || channel === "whatsapp";
	const previousMessages = history
		.filter(
			(row) => row.branch === current.branch && row.audience === current.audience && row.status !== "Draft",
		)
		.sort((a, b) => a.date.localeCompare(b.date));
 const thread=current.status==="Draft" || isScheduledCommunication(current) ? [current] : previousMessages.filter(row=>!isScheduledCommunication(row));
	const continueMessage = () => {
		onReuse({ ...current, status: "Sent", title: "", body: message });
		setMessage("");
	};
	return (
		<>
			<header className={`comm-reader-toolbar ${chat ? "comm-chat-contact" : ""}`}>
				<button
					type="button"
					className="comm-mobile-back comm-icon-button"
					onClick={onBack}
					aria-label="Back to message history"
				>
					<Icon.back size={15} />
				</button>
				{chat ? (
					<div className="comm-contact-identity">
						<span className="comm-avatar">{initials(current.branch)}</span>
						<div>
							<strong>
								{current.audience} · {current.branch}
							</strong>
							<span>
								{current.recipient_count} recipients ·{" "}
								{channel === "sms" ? "SMS campaigns" : "WhatsApp broadcasts"}
							</span>
						</div>
					</div>
				) : (
					<div className="comm-reader-pagination">
						<button
							type="button"
							className="comm-icon-button"
							disabled={index <= 0}
							onClick={onPrevious}
							aria-label="Previous message"
						>
							<Icon.back size={15} />
						</button>
						<button
							type="button"
							className="comm-icon-button"
							disabled={index >= total - 1}
							onClick={onNext}
							aria-label="Next message"
						>
							<Icon.arrow size={15} />
						</button>
						<span>
							{index + 1} / {total}
						</span>
					</div>
				)}
				<div className="comm-reader-actions">
					<button
						type="button"
						className="comm-icon-button"
						onClick={onPin}
						aria-label={current.pinned ? "Unpin message" : "Pin message"}
						aria-pressed={!!current.pinned}
					>
						<Icon.bookmark size={15} />
					</button>
					<button
						type="button"
						className="comm-icon-button"
						onClick={onDetails}
						aria-label="Show delivery details"
					>
						<Icon.info size={15} />
					</button>
					<button
						type="button"
						className="comm-icon-button"
						onClick={() => onReuse(current)}
						aria-label={current.status === "Draft" ? "Edit draft" : "Use message"}
						title={current.status === "Draft" ? "Edit draft" : "Use message"}
					>
						<Icon.pencil size={15} />
					</button>
				</div>
			</header>
			{chat ? (
				<div className="comm-thread-layout">
					<div className="comm-thread-scroll">
						{(thread.length ? thread : [current]).map((row, i, all) => (
							<div className="comm-thread-entry" key={row.id}>
								{(i === 0 || date(all[i - 1].date) !== date(row.date)) && (
									<div className="comm-thread-day">
										<span>{date(row.date)}</span>
									</div>
								)}
								<div className="comm-thread-outgoing">
									<div>
										<div
											className={`comm-outgoing-bubble ${row.id === current.id ? "is-current-message" : ""}`}
										>
											<p>{row.body}</p>
										</div>
										<span className="comm-bubble-time">
											{time(row.date)} · {row.status}
             {isScheduledCommunication(row)&&row.scheduled_at ? ` · Scheduled for ${new Date(row.scheduled_at).toLocaleString()}` : ""}
											{row.delivered ? ` · ${row.delivered} delivered` : ""}
										</span>
									</div>
									<span className="comm-avatar comm-sender-avatar">{initials(row.sender)}</span>
								</div>
							</div>
						))}
					</div>
					<div className="comm-thread-composer">
						<div className="comm-thread-composer-tabs">
							<span>New message</span>
							<button type="button" onClick={() => onReuse({...current,body:message || current.body})}>
								Campaign settings
							</button>
						</div>
						<textarea
							aria-label="New campaign message"
							value={message}
							onChange={(event) => setMessage(event.target.value)}
							placeholder="Write your message…"
						/>
						<div className="comm-thread-compose-tools">
							<button
								type="button"
								className="comm-icon-button"
								onClick={() => setMessage(current.body)}
								aria-label="Use the selected message text"
								title="Use selected message"
							>
								<Icon.pencil size={16} />
							</button>
							<span>{channel === "sms" ? `${message.length} characters` : "WhatsApp broadcast"}</span>
							<button
								type="button"
								className="comm-quick-send bg-rail text-white"
								disabled={!message.trim()}
								onClick={continueMessage}
								aria-label="Review new campaign"
								title="Review recipients and campaign"
							>
								<Icon.send size={16} />
							</button>
						</div>
					</div>
				</div>
			) : (
				<>
					<div className="comm-reader-scroll">
						<div className="comm-message-heading">
							<div className="comm-subject-heading">
								<h2>{current.title}</h2>
								<span
									className={`comm-status comm-status-${current.status.toLowerCase().replaceAll(" ", "-")}`}
								>
									{current.status}
								</span>
							</div>
							<time dateTime={current.date}>
								{isScheduledCommunication(current)&&current.scheduled_at ? `Scheduled for ${new Date(current.scheduled_at).toLocaleString()}` : `${date(current.date)}, ${time(current.date)}`}
							</time>
						</div>
						<div className="comm-mail-envelope">
							<span className="comm-avatar">{initials(current.sender)}</span>
							<div>
								<div className="comm-from-line">
									<strong>{current.sender}</strong>
									<span>{current.sender_email}</span>
								</div>
								<p>
									To: <strong>{current.audience}</strong> · {current.branch}{" "}
									<span>({current.recipient_count} recipients)</span>
								</p>
							</div>
						</div>
						{!!current.attachments?.length && (
							<details className="comm-attachments" open key={current.id}>
								<summary>Attachments ({current.attachments.length})<Icon.chevron size={13} /></summary>
								<div>
									{current.attachments.map((file) => (
										<a key={file.name} href={file.url} download={file.name}>
											<DocumentIcon size={13} type={file.name.split(".").at(-1)} />
											<strong>{file.name}</strong>
											<span>{file.size}</span>
										</a>
									))}
								</div>
							</details>
						)}
						<article className="comm-email-content">
							{current.body.split("\n\n").map((paragraph, i) => (
								<p key={i}>{paragraph}</p>
							))}
						</article>
					</div>
					<footer className="comm-mail-bottom">
						<div className="comm-mail-delivery">
							<span>
								{current.status === "Sent"
									? `${current.delivered} delivered · ${current.failed} failed`
									: current.status === "Pending approval"
										? "Awaiting approval"
										: current.status === "Draft"
											? "Draft · not sent"
											: current.status}
							</span>
							<button type="button" onClick={onDetails}>
								Delivery details
							</button>
						</div>
						<button
							type="button"
							className="comm-mail-write"
							onClick={() => onReuse({ ...current, status: "Sent", title: "", body: "" })}
						>
							<Icon.pencil size={15} />
							<span>Write a new {channel === "system" ? "notification" : "email"} to this audience…</span>
							<Icon.send size={15} />
						</button>
					</footer>
				</>
			)}
		</>
	);
}
