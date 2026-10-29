import { useRecordPage, RecordPager, RecordCollection } from "../../ui/RecordPagination";
import { Fragment } from "react";
import { MessageReader } from "./MessageReader";
import { type ReactNode, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Icon } from "../../ui/icons";
import { isScheduledCommunication, useCommunicationActions, useCommunicationHistory, type CommunicationRecord } from "./history";

export const channelNames: Record<string, string> = {
	email: "Email",
	sms: "SMS",
	whatsapp: "WhatsApp",
	system: "Notifications",
};
const date = (value: string) =>
	new Date(value).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
const initials = (name: string) =>
	name
		.split(/\s+/)
		.slice(0, 2)
		.map((word) => word[0])
		.join("");
export function CommunicationWorkspace({
	channel,
	view,
	composer,
	onReuse,
}: {
	channel: string;
	view: string;
	composer: ReactNode;
	onReuse: (message: CommunicationRecord) => void;
}) {
	const {rows:history,isLoading:historyLoading,error:historyError} = useCommunicationHistory(channel);
 const { pinCommunication } = useCommunicationActions();
	const [params, setParams] = useSearchParams();
	const [pinError,setPinError]=useState("");
 const [query, setQuery] = useState("");
	const [selected, setSelected] = useState("");
	const [mobileOpen, setMobileOpen] = useState(false);
	const [details, setDetails] = useState(false);
	const [filterOpen, setFilterOpen] = useState(false);
	const chat = channel === "sms" || channel === "whatsapp";
	const status = params.get("status") || "All";
	const filteredRows = history
		.filter(
			(row) =>
				(status === "All" || (status === "Scheduled" ? isScheduledCommunication(row) : row.status === status)) &&
				`${row.title} ${row.body} ${row.branch} ${row.audience}`.toLowerCase().includes(query.toLowerCase()),
		)
		.sort((a, b) => Number(!!b.pinned) - Number(!!a.pinned) || b.date.localeCompare(a.date));
	const seen = new Set<string>();
	const rows = filteredRows.filter((row) => {
		if (!chat) return true;
		const group = `${row.branch}:${row.audience}`;
		if (seen.has(group)) return false;
		seen.add(group);
		return true;
	});
	const paging = useRecordPage(rows);
	const current = filteredRows.find((row) => row.id === (params.get("message") || selected)) || rows[0];
	const index = rows.findIndex((row) =>
		chat ? row.branch === current?.branch && row.audience === current?.audience : row.id === current?.id,
	);
	const navigate = useNavigate();
	const composing = view === "compose";
	const selectMessage = (id: string) => {
		setSelected(id);
		const next = new URLSearchParams(params);
		next.set("message", id);
		setParams(next, { replace: true });
	};
	const backToHistory = () => {
		setMobileOpen(false);
		const next = new URLSearchParams(params);
		next.delete("message");
		setParams(next, { replace: true });
	};
	const choose = (id: string) => {
		setSelected(id);
		setMobileOpen(true);
		const next = new URLSearchParams(params);
		next.set("message", id);
		navigate(`/admin/communication/${channel}/sent?${next}`);
	};
	const reuse = (row: CommunicationRecord) => {
		onReuse(row);
		navigate(`/admin/communication/${channel}/compose`);
	};
	return (
		<div className="communication-page">
  {historyLoading && <p role="status">Loading communication history…</p>}
  {(historyError || pinError) && <p role="alert">{pinError || "Communication history could not be loaded. Reload to try again."}</p>}
   {!composing&&<header className="communication-workspace-heading"><h1>{channelNames[channel]} · {status === "Scheduled" ? "Scheduled" : status === "Draft" ? "Drafts" : "History"}</h1><Link className="channel-new-message" to={`/admin/communication/${channel}/compose`}><Icon.plus size={16}/>{channel === "email" ? "New email" : channel === "system" ? "New notification" : "New message"}</Link></header>}
		<div
			className={`communication-app comm-reference-layout comm-external-nav ${chat ? "is-chat-workspace" : "is-mail-workspace"} ${composing || mobileOpen || params.has("message") ? "comm-mobile-open" : ""} ${details && !composing ? "comm-details-open" : ""}`}
		>
			{chat && (
				<header className="comm-chat-appbar">
					<strong>{channelNames[channel]}</strong>
					<label>
						<Icon.search size={14} />
						<span className="sr-only">Search campaigns</span>
						<input
							placeholder="Search campaigns…"
							value={query}
							onChange={(event) => setQuery(event.target.value)}
						/>
					</label>
					<button
						type="button"
						className="comm-icon-button"
						onClick={() => navigate(`/admin/communication/${channel}/compose`)}
						aria-label="New campaign"
					>
						<Icon.pencil size={15} />
					</button>
				</header>
			)}
			<section className="comm-message-list" aria-label={`${channelNames[channel]} history`}>
				<header className="comm-pane-toolbar">
					<div>
						<h1>{status === "Scheduled" ? "Scheduled" : status === "Draft" ? "Drafts" : "History"}</h1>
					</div>
					<button
						type="button"
						className="comm-icon-button"
						aria-label="Filter message history"
						aria-expanded={filterOpen}
						onClick={() => setFilterOpen(!filterOpen)}
					>
						<Icon.filter size={16} />
					</button>
				</header>
				<label className="comm-search">
					<Icon.search size={15} />
					<span className="sr-only">Search message history</span>
					<input
						value={query}
						onChange={(e) => setQuery(e.target.value)}
						placeholder="Search messages…"
						type="search"
					/>
				</label>
				{filterOpen && (
					<label className="comm-history-filter">
						Status
						<select
							value={status}
							onChange={(e) => {
								const next = new URLSearchParams(params);
								if (e.target.value === "All") next.delete("status");
								else next.set("status", e.target.value);
								setParams(next, { replace: true });
							}}
						>
							{["All", "Sent", "Queued", "Draft", "Pending approval", "Scheduled", "Failed"].map((value) => (
								<option key={value}>{value}</option>
							))}
						</select>
					</label>
				)}
				{chat && (
					<div className="comm-history-tabs" role="group" aria-label="Campaign status">
						{[
							{ label: "All", value: "All" },
							{ label: "Sent", value: "Sent" },
							{ label: "Pending", value: "Pending approval" },
							{ label: "Scheduled", value: "Scheduled" },
							{ label: "Drafts", value: "Draft" },
						].map((tab) => (
							<button
								key={tab.value}
								type="button"
								aria-pressed={status === tab.value}
								onClick={() => {
									const next = new URLSearchParams(params);
									next.delete("message");
									if (tab.value === "All") next.delete("status");
									else next.set("status", tab.value);
									setParams(next, { replace: true });
								}}
							>
								{tab.label} <span>({history.filter((row) => tab.value === "All" || (tab.value === "Scheduled" ? isScheduledCommunication(row) : row.status === tab.value)).length})</span>
							</button>
						))}
					</div>
				)}
				<div className="comm-list-scroll">
					{!rows.length ? (
						<div className="comm-empty">
							<Icon.search size={24} />
							<strong>No messages found</strong>
							<p>Try another search or status.</p>
						</div>
					) : (
						paging.slice.map((row, rowIndex) => (
							<Fragment key={row.id}>
								{(rowIndex === 0 || !!paging.slice[rowIndex - 1].pinned !== !!row.pinned) && (
									<div className="comm-message-group">
										{row.pinned ? "Pinned" : "Recent messages"}{" "}
										<span>({rows.filter((item) => !!item.pinned === !!row.pinned).length})</span>
									</div>
								)}
								<button
									type="button"
									key={row.id}
									onClick={() => choose(row.id)}
									className={`comm-history-row ${!composing && (chat ? current?.branch===row.branch && current?.audience===row.audience : current?.id===row.id) ? "is-selected" : ""}`}
									aria-pressed={!composing && (chat ? current?.branch===row.branch && current?.audience===row.audience : current?.id===row.id)}
								>
									<span className="comm-avatar">{initials(row.branch)}</span>
									<span className="comm-row-content">
										<span className="comm-row-top">
											<strong>{chat ? `${row.audience} · ${row.branch}` : row.branch}</strong>
											<time dateTime={row.date}>{date(row.date)}</time>
										</span>
										<span className="comm-row-title">{row.title}</span>
										<span className="comm-row-preview">{row.body}</span>
										{chat && row.pinned && <span className="comm-row-pinned" title="Pinned campaign"><Icon.bookmark size={12} /><span className="sr-only">Pinned</span></span>}
										<span className="comm-row-bottom">
											<span
												className={`comm-status comm-status-${row.status.toLowerCase().replaceAll(" ", "-")}`}
											>
												{row.status}
											</span>
											<span>
												{row.recipient_count} recipients{row.pinned ? " · Pinned" : ""}
											</span>
										</span>
									</span>
								</button>
							</Fragment>
						))
					)}
				</div>
    <RecordPager {...paging} />
				<footer className="comm-list-footer">
					<Icon.send size={14} />
					<span>Outgoing messages and campaigns</span>
				</footer>
			</section>
			<section className="comm-message-pane" aria-label={composing ? "Compose message" : "Message reader"}>
				{composing ? (
					<>
						<header className="comm-reader-toolbar">
							<Link
								className="comm-mobile-back"
								to={`/admin/communication/${channel}/sent`}
								onClick={backToHistory}
							>
								<Icon.back size={16} />
								History
							</Link>
							<strong>
								New {channel === "email" ? "email" : channel === "system" ? "notification" : "message"}
							</strong>
							<Link
								to={`/admin/communication/${channel}/sent`}
								className="comm-icon-button"
								aria-label="Close composer"
							>
								<Icon.cross size={17} />
							</Link>
						</header>
						{composer}
					</>
				) : current ? (
					<MessageReader
						channel={channel}
						current={current}
						history={history}
						index={index}
						total={rows.length}
						onPrevious={() => selectMessage(rows[index - 1].id)}
						onNext={() => selectMessage(rows[index + 1].id)}
						onBack={backToHistory}
						onPin={() => {
							setSelected(current.id);
							void pinCommunication(current.id).catch(()=>setPinError("The message could not be pinned."));
						}}
						onDetails={() => setDetails(!details)}
						onReuse={reuse}
					/>
				) : (
					<div className="comm-empty">
						<Icon.mail size={32} />
						<strong>No message selected</strong>
						<p>Select a message from history or compose a new one.</p>
					</div>
				)}
			</section>
			{details && !composing && current && (
				<aside className="comm-delivery-panel" aria-label="Delivery details">
					<header>
						<h2>Delivery details</h2>
						<button
							type="button"
							className="comm-icon-button"
							aria-label="Close delivery details"
							onClick={() => setDetails(false)}
						>
							<Icon.cross size={16} />
						</button>
					</header>
					<div className="comm-delivery-numbers">
						<div>
							<strong>{current.recipient_count}</strong>
							<span>Recipients</span>
						</div>
						<div>
							<strong>{current.delivered}</strong>
							<span>Delivered</span>
						</div>
						<div>
							<strong>{current.failed}</strong>
							<span>Failed</span>
						</div>
					</div>
					<h3>Audience</h3>
					<dl>
						<dt>Branch</dt>
						<dd>{current.branch}</dd>
						<dt>Group</dt>
						<dd>{current.audience}</dd>
						<dt>Channel</dt>
						<dd>{channelNames[channel]}</dd>
					</dl>
					<h3>Recipients</h3>
					<RecordCollection as="ul">
						{current.recipients.map((person, i) => (
							<li key={i}>
								<strong>{person.name}</strong>
								<span>{person.address}</span>
								<small>{person.status}</small>
							</li>
						))}
					</RecordCollection>
					{current.recipient_count > current.recipients.length && (
						<p className="comm-recipient-caption">
							Showing {current.recipients.length} of {current.recipient_count} recipients
						</p>
					)}
				</aside>
			)}
		</div>
		</div>
	);
}
