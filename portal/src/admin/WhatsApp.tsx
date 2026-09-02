import { useFrappeGetCall } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import { Icon } from "../ui/icons";
import {
	Caveat,
	Card,
	Cell,
	Detail,
	DetailList,
	Empty,
	ErrorNote,
	Metric,
	MetricGrid,
	NameCell,
	PageHead,
	Row,
	SectionHead,
	Spinner,
	StatusBadge,
	Table,
	cx,
} from "./ui/kit";

/**
 * The WhatsApp channel itself — the phone behind it, and what it has done.
 *
 * **The one channel with a *thing* behind it.** In-app notifications and email
 * go out through the site; SMS is filed for onerc_sms to release. WhatsApp is a
 * phone in a container somewhere with a session that can drop, a pacing limit
 * that decides how long a broadcast takes, and a list of people who have
 * replied STOP. None of that had a screen, so the answer to "why has this not
 * sent yet" was on the Frappe desk or nowhere.
 *
 * **The gateway is asked separately from the page.** `channel` is the page load
 * and touches nothing outside this site; `connection` is the one call that
 * reaches the container, and it is its own request so a gateway that is slow or
 * down costs a status line rather than the screen. That split is in
 * `api/whatsapp.py` for exactly this reason.
 *
 * **The opt-out list is numbers and nothing else.** An opt-out record holds no
 * name by design — matching one back to a person would turn this list into a
 * way of asking who volunteers for the Red Cross — so the screen shows the
 * number, the date and how they asked, and does not offer to look anybody up.
 */

interface Channel {
	installed: boolean;
	configured: boolean;
	can_send: boolean;
	enabled: boolean;
	gateway_url: string | null;
	session_id: string | null;
	pacing_seconds: number | null;
	daily_limit: number | null;
	opt_out_notice: string | null;
	opt_out_count: number;
}

interface Connection {
	connected: boolean;
	status: string;
	reason: string;
}

interface Broadcast {
	name: string;
	title: string | null;
	status: string;
	audience: string | null;
	geo_node: string | null;
	scheduled_at: string | null;
	sent_on: string | null;
	creation: string;
	addressed: number;
	total_recipients: number;
	total_sent: number;
	total_failed: number;
	total_skipped: number;
	awaiting_release: boolean;
}

interface OptOut {
	name: string;
	phone_number: string;
	opted_out_on: string;
	source: string;
	notes: string | null;
}

/** A broadcast's state, keyed off the doctype's own closed Select. */
const STATUS_TONE: Record<string, "success" | "info" | "warning" | "danger" | "neutral"> = {
	Sent: "success",
	Sending: "info",
	Scheduled: "info",
	"Partly Sent": "warning",
	Draft: "warning",
	Failed: "danger",
	Cancelled: "neutral",
};

export default function WhatsAppChannel() {
	const channel = useFrappeGetCall<{ message: Channel }>(API.whatsappChannel, undefined, "admin:wa:channel");
	// Its own request, and deliberately not awaited by anything else on the
	// page: this one leaves the site.
	const connection = useFrappeGetCall<{ message: Connection }>(
		API.whatsappConnection,
		undefined,
		"admin:wa:connection",
	);
	const broadcasts = useFrappeGetCall<{ message: { broadcasts: Broadcast[] } }>(
		API.whatsappBroadcasts,
		{ limit: 20 },
		"admin:wa:broadcasts",
	);
	const optOuts = useFrappeGetCall<{ message: { opt_outs: OptOut[]; count: number } }>(
		API.whatsappOptOuts,
		{ limit: 50 },
		"admin:wa:optouts",
	);

	if (channel.isLoading) return <Spinner page label="Reading the channel…" />;
	if (channel.error) return <ErrorNote>{errorMessage(channel.error)}</ErrorNote>;

	const config = channel.data?.message;
	if (!config) return <ErrorNote>{errorMessage(null, "The channel could not be read.")}</ErrorNote>;

	if (!config.configured) {
		return (
			<>
				<PageHead title="The WhatsApp channel" />
				<Empty title="No gateway is linked yet" icon={Icon.whatsapp}>
					A society sends on WhatsApp through its own gateway. Until one is set up and a phone is
					linked to it, this channel has nothing to send with.
				</Empty>
			</>
		);
	}

	const rows = broadcasts.data?.message?.broadcasts ?? [];
	const sent = rows.reduce((total, row) => total + (row.total_sent ?? 0), 0);
	const drafts = rows.filter((row) => row.awaiting_release).length;
	const link = connection.data?.message;

	return (
		<>
			<PageHead title="The WhatsApp channel" />

			<MetricGrid>
				<Metric
					label="The link"
					icon={Icon.whatsapp}
					value={
						connection.isLoading ? (
							<span className="text-[15px] font-semibold text-muted">Checking…</span>
						) : (
							<span
								className={cx(
									"text-[17px] font-semibold",
									link?.connected ? "text-success" : "text-danger",
								)}
							>
								{link?.connected ? "Connected" : "Not sending"}
							</span>
						)
					}
					note={link?.connected ? config.session_id ?? undefined : link?.reason}
					tone={link?.connected ? "positive" : "negative"}
				/>
				<Metric
					label="Messages delivered"
					value={sent}
					note={`Across ${rows.length} ${rows.length === 1 ? "broadcast" : "broadcasts"}`}
					icon={Icon.check}
				/>
				<Metric
					label="Waiting to be released"
					value={drafts}
					tone={drafts > 0 ? "negative" : "muted"}
					note={drafts > 0 ? "A second pair of eyes is needed" : "Nothing held"}
					icon={Icon.hourglass}
				/>
				<Metric
					label="Opted out"
					value={optOuts.data?.message?.count ?? 0}
					note="Replied STOP, or taken off by hand"
					icon={Icon.cross}
				/>
			</MetricGrid>

			<div className="mb-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
				<Card pad={false}>
					<SectionHead title="What has been sent" />
					{broadcasts.isLoading ? (
						<Spinner label="Loading broadcasts…" />
					) : rows.length === 0 ? (
						<Empty framed={false} title="Nothing has gone out on this channel yet" icon={Icon.whatsapp} />
					) : (
						<Table head={["Broadcast", "Audience", "Reached", "When", "State"]} minWidth={840}>
							{rows.map((row) => (
								<Row key={row.name}>
									<NameCell title={row.title || row.name} meta={row.name} />
									<Cell nowrap className="capitalize">
										{row.audience ?? "—"}
									</Cell>
									<Cell nowrap>
										{/* Three numbers, because they answer three different
										    questions: how many were addressed, how many the
										    gateway actually delivered to, and how many were
										    skipped — which on this channel usually means an
										    opt-out, and is the channel working rather than
										    failing. */}
										<span className="tabular font-semibold text-ink">{row.total_sent}</span>
										<span className="text-muted"> of {row.total_recipients}</span>
										{row.total_failed > 0 && (
											<span className="ml-2 text-[11.5px] font-semibold text-danger">
												{row.total_failed} failed
											</span>
										)}
										{row.total_skipped > 0 && (
											<span className="ml-2 text-[11.5px] text-muted">{row.total_skipped} skipped</span>
										)}
									</Cell>
									<Cell nowrap>{formatDate(row.sent_on ?? row.scheduled_at ?? row.creation)}</Cell>
									<Cell nowrap>
										<div className="flex flex-wrap items-center gap-1.5">
											<StatusBadge state={row.status} tone={STATUS_TONE[row.status] ?? "neutral"} />
											{/* Only where it says something the status does not. A
											    Draft is by definition unreleased, so "Draft · Held"
											    is one fact wearing two chips; a *Scheduled*
											    broadcast still sitting at docstatus 0 is the case
											    worth flagging. */}
											{row.awaiting_release && row.status !== "Draft" && (
												<StatusBadge tone="warning">Held</StatusBadge>
											)}
										</div>
									</Cell>
								</Row>
							))}
						</Table>
					)}
				</Card>

				<div className="space-y-4">
					<Card>
						<h2 className="mb-3.5 text-[13.5px] font-semibold text-ink">The gateway</h2>
						<DetailList>
							<Detail label="Enabled">{config.enabled ? "Yes" : "No"}</Detail>
							<Detail label="Session">{config.session_id ?? "—"}</Detail>
							<Detail label="Pace">
								{config.pacing_seconds ? `One message every ${config.pacing_seconds}s` : "Not set"}
							</Detail>
							<Detail label="Daily limit">{config.daily_limit || "None"}</Detail>
						</DetailList>

						<div className="mt-4 border-t p-divide pt-3.5">
							<Caveat>
								Pace and daily limit are why a large broadcast takes hours rather than minutes. Both
								are set on the desk.
							</Caveat>
						</div>
					</Card>

					<Card>
						<h2 className="text-[13.5px] font-semibold text-ink">Replies</h2>
						<p className="mt-1.5 text-[12.5px] leading-relaxed text-slate-strong">
							{/* Stated because it is a promise the society is making to
							    everybody it messages, and the person choosing to send
							    should know what it is. */}
							A reply that is an opt-out word takes that number off the list. Anything else is
							acknowledged and goes no further — nobody is reading this number.
						</p>
						{config.opt_out_notice && (
							<p className="mt-3 rounded-lg bg-surface px-3 py-2.5 text-[12px] italic leading-relaxed text-muted">
								{config.opt_out_notice}
							</p>
						)}
					</Card>
				</div>
			</div>

			<Card pad={false}>
				<SectionHead title={`Opted out (${optOuts.data?.message?.count ?? 0})`} />
				{optOuts.isLoading ? (
					<Spinner label="Loading the list…" />
				) : (optOuts.data?.message?.opt_outs ?? []).length === 0 ? (
					<Empty framed={false} title="Nobody has opted out" icon={Icon.check} />
				) : (
					<Table head={["Number", "When", "How"]} minWidth={420}>
						{(optOuts.data?.message?.opt_outs ?? []).map((row) => (
							<Row key={row.name}>
								<Cell nowrap className="tabular font-semibold text-ink">
									{row.phone_number}
								</Cell>
								<Cell nowrap>{formatDate(row.opted_out_on)}</Cell>
								<Cell>{row.source === "Reply" ? "Replied to stop" : row.source}</Cell>
							</Row>
						))}
					</Table>
				)}
			</Card>
		</>
	);
}
