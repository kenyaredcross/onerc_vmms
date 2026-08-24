import { useContext, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";
import { Navigate, useParams } from "react-router-dom";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { GeoSelects } from "../ui/GeoSelects";
import { Icon } from "../ui/icons";
import {
	Button,
	Card,
	ConfirmDialog,
	ErrorNote,
	PageHeading,
	SectionTitle,
	Spinner,
	cx,
} from "../ui/primitives";
import type {
	CommunicationOptions,
	CommunicationReach,
	CommunicationReport,
	GeoNode,
} from "../portal/types";

/**
 * Saying something to the people a branch is responsible for.
 *
 * **One audience, three channels, and the audience is chosen first.** Who
 * hears this is two questions — which part of the society, and which of its
 * people — and both are answered before a word is written. That order is
 * deliberate: a message composed first and addressed afterwards is a message
 * whose reach is discovered at the moment of sending, and this is the one act
 * in the console that cannot be taken back.
 *
 * **The reach is read before the send, not after it.** `preview` counts the
 * same resolved audience the send will use, per channel, because they are
 * genuinely three different numbers: an in-app notification needs a login, an
 * email needs an address, an SMS needs a number with a country code, and a
 * member enrolled at a counter years ago may have only the last of the three.
 * A branch seeing "2,100 addressed, 340 by email" is looking at a data gap it
 * can go and close.
 *
 * **Nothing here decides who may send.** `options.can_send` and the server's
 * own per-node check are the answer; this screen draws what it is told. The
 * geo picker is the same cascading one every other screen uses, so a
 * coordinator can only name a node — whether they may *address* it is asked
 * again, of the anchor, when they press send.
 *
 * **SMS is filed, never sent.** onerc_sms owns an approval workflow of its own,
 * and this screen composes a draft campaign for it rather than reaching around
 * it. The report says so in as many words, and links to where it is finished.
 */
export default function Communication() {
	const { channel = "system", view = "compose" } = useParams<{ channel: string; view: string }>();
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const channelKey = channel === "system" ? "notification" : channel;

	const options = useFrappeGetCall<{ message: CommunicationOptions }>(
		API.communicationOptions,
		undefined,
		"admin:communication_options",
	);

	const [chain, setChain] = useState<GeoNode[]>([]);
	const [who, setWho] = useState("everyone");
	const channels = [channelKey];
	const [title, setTitle] = useState("");
	const [body, setBody] = useState("");
	const [smsMessage, setSmsMessage] = useState("");
	const [urgency, setUrgency] = useState("routine");
	const [announcementType, setAnnouncementType] = useState("");

	const [confirming, setConfirming] = useState(false);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const [report, setReport] = useState<CommunicationReport | null>(null);

	const answer = options.data?.message;
	const geoNode = chain.length > 0 ? chain[chain.length - 1].name : null;

	// Only asked once there is somewhere to ask about. A preview with no anchor
	// would either resolve the whole society or refuse, and neither is a useful
	// thing to show somebody who has not chosen a branch yet.
	const reach = useFrappeGetCall<{ message: CommunicationReach }>(
		API.communicationReach,
		{ geo_node: geoNode, who },
		geoNode ? `admin:reach:${geoNode}:${who}` : null,
	);

	const counts = reach.data?.message;
	const chosen = new Set(channels);
	const wantsSms = chosen.has("sms");

	const ready =
		Boolean(geoNode) &&
		channels.length > 0 &&
		title.trim().length > 0 &&
		body.trim().length > 0 &&
		(!wantsSms || (smsMessage || body).trim().length > 0);

	const send = async () => {
		setBusy(true);
		setFailure(null);

		try {
			const response = await call.post<{ message: CommunicationReport }>(API.communicationSend, {
				title: title.trim(),
				body: body.trim(),
				geo_node: geoNode,
				who,
				channels,
				urgency,
				announcement_type: announcementType || undefined,
				sms_message: smsMessage.trim() || undefined,
			});

			setReport(response.message);
			setConfirming(false);
			// The words go, the audience stays. Somebody who has just told Arusha
			// one thing is quite likely to tell Arusha the next thing, and making
			// them rebuild the picker each time is how a branch stops using this.
			setTitle("");
			setBody("");
			setSmsMessage("");
		} catch (error) {
			setFailure(errorMessage(error, "That was not sent."));
			setConfirming(false);
		} finally {
			setBusy(false);
		}
	};

	if (options.isLoading) {
		return <Spinner page label="Loading the composer…" />;
	}

	if (options.error || !answer) {
		return <ErrorNote>{errorMessage(options.error, "This screen could not be opened.")}</ErrorNote>;
	}
	if (!["system", "email", "sms"].includes(channel) || !["compose", "sent"].includes(view)) return <Navigate to="/admin/communication/system/compose" replace />;
	if (view === "sent") return <CommunicationHistory channel={channel} />;
	if (!answer.channels[channelKey as keyof typeof answer.channels]) {
		return <><PageHeading title={`Compose ${channel === "system" ? "notification" : channel}`} /><Card><SectionTitle>Channel unavailable</SectionTitle><p className="text-[13px] leading-relaxed text-slate-body">This channel is not available to your account on this site. Availability is determined by the server and the channel provider’s permissions.</p></Card></>;
	}

	const available = CHANNELS.filter((channel) => answer.channels[channel.key]);

	return (
		<>
			<PageHeading
				title={<EditableText k={`admin.communication.${channel}.heading`} fallback={`Compose ${channel === "system" ? "notification" : channel}`} />}
				lead={
					<EditableText
						k="admin.communication.lead"
						fallback="Say something to the volunteers and members your branches cover. Choose who hears it before you write it — this is the one thing here that cannot be taken back."
					/>
				}
			/>

			{report && <Report report={report} onDismiss={() => setReport(null)} />}
			{failure && (
				<div className="mb-5">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,340px)]">
				<div className="space-y-5">
					<Card>
						<SectionTitle>Who hears it</SectionTitle>

						<div className="mb-4">
							<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">
								Which part of the society
							</span>
							{/* The same cascading picker every placement form uses, so it
							    draws one control per rung of this society's own ladder and
							    this screen never learns how deep it goes. A branch and
							    everything beneath it is what gets addressed — the server
							    resolves the subtree. */}
							<GeoSelects chain={chain} onChain={setChain} idPrefix="comms" />
						</div>

						<div>
							<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">
								Which of its people
							</span>
							<div className="flex flex-wrap gap-2">
								{answer.audiences.map((option) => (
									<button
										key={option}
										type="button"
										onClick={() => setWho(option)}
										className={cx(
											"rounded-full border px-4 py-2 font-display text-[12.5px] font-bold capitalize transition",
											option === who
												? "border-navy bg-navy text-white"
												: "border-hairline-strong bg-white text-slate-strong hover:border-navy hover:text-navy",
										)}
									>
										{option}
									</button>
								))}
							</div>
							<p className="mt-2 text-[11.5px] leading-relaxed text-slate-faint">
								Everybody currently serving or currently a member at that branch and
								everything under it. Somebody suspended or lapsed is not written to.
							</p>
						</div>
					</Card>

					<Card>
						<SectionTitle>How it reaches them</SectionTitle>
						<div className="grid gap-2.5">
							{available.filter((item) => item.key === channelKey).map((channel) => {
								const on = chosen.has(channel.key);
								const count = counts?.[channel.key];

								return (
									<button
										key={channel.key}
										type="button"
										aria-pressed="true"
										className={cx(
											"rounded-card border p-4 text-left transition",
											on
												? "border-navy bg-navy/[.05]"
												: "border-hairline-strong bg-white hover:border-hairline-strong/70",
										)}
									>
										<span
											className={cx(
												"flex items-center gap-2 font-display text-[13px] font-bold",
												on ? "text-navy" : "text-ink",
											)}
										>
											<channel.icon size={15} />
											{channel.label}
										</span>
										<span className="mt-1.5 block text-[11.5px] leading-relaxed text-slate-faint">
											{channel.hint}
										</span>
										{geoNode && (
											<span className="tabular mt-2 block font-display text-[13px] font-bold text-ink">
												{count ?? "—"} reachable
											</span>
										)}
									</button>
								);
							})}
						</div>

						{channel === "sms" && answer.channels.sms === false && (
							<p className="mt-3 text-[11.5px] leading-relaxed text-slate-faint">
								SMS is not available to you on this site. It needs the SMS app
								installed and the role your society named for it.
							</p>
						)}
					</Card>

					<Card>
						<SectionTitle>What it says</SectionTitle>

						<label className="mb-4 block">
							<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">
								Subject
							</span>
							<input
								value={title}
								onChange={(event) => setTitle(event.target.value)}
								placeholder="Branch meeting moved to Saturday"
								className="w-full rounded-card border border-hairline-strong px-3.5 py-2.5 text-[13.5px] outline-none focus:border-navy"
							/>
						</label>

						<label className="mb-4 block">
							<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">
								Message
							</span>
							<textarea
								value={body}
								onChange={(event) => setBody(event.target.value)}
								rows={6}
								placeholder="Plain words. This is what people read in the portal and in their email."
								className="w-full resize-y rounded-card border border-hairline-strong px-3.5 py-2.5 text-[13.5px] outline-none focus:border-navy"
							/>
						</label>

						{/* Only when SMS was chosen, and separate from the message
						    above on purpose: 160 characters is a different piece of
						    writing from a notice, and merging the two would send
						    either a truncated notice or an essay by text. */}
						{wantsSms && (
							<label className="mb-4 block">
								<span className="mb-2 flex items-center justify-between gap-3 text-[12.5px] font-semibold text-slate-strong">
									<span>Text message</span>
									<span
										className={cx(
											"tabular text-[11.5px] font-bold",
											(smsMessage || body).length > 160
												? "text-signal-dark"
												: "text-slate-faint",
										)}
									>
										{(smsMessage || body).length} characters
									</span>
								</span>
								<textarea
									value={smsMessage}
									onChange={(event) => setSmsMessage(event.target.value)}
									rows={3}
									placeholder="Left empty, the message above is used."
									className="w-full resize-y rounded-card border border-hairline-strong px-3.5 py-2.5 text-[13.5px] outline-none focus:border-navy"
								/>
								<span className="mt-1.5 block text-[11.5px] leading-relaxed text-slate-faint">
									Anything over 160 characters is sent as more than one message.
								</span>
							</label>
						)}

						<div className="grid gap-4 sm:grid-cols-2">
							<label className="block">
								<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">
									How urgent
								</span>
								<select
									value={urgency}
									onChange={(event) => setUrgency(event.target.value)}
									className="w-full rounded-card border border-hairline-strong bg-white px-3.5 py-2.5 text-[13.5px] capitalize outline-none focus:border-navy"
								>
									{answer.urgencies.map((option) => (
										<option key={option} value={option} className="capitalize">
											{option}
										</option>
									))}
								</select>
								<span className="mt-1.5 block text-[11.5px] text-slate-faint">
									Decides how high this sits in somebody's list.
								</span>
							</label>

							{answer.types.length > 0 && (
								<label className="block">
									<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">
										What kind of thing it is
									</span>
									<select
										value={announcementType}
										onChange={(event) => setAnnouncementType(event.target.value)}
										className="w-full rounded-card border border-hairline-strong bg-white px-3.5 py-2.5 text-[13.5px] outline-none focus:border-navy"
									>
										<option value="">Not filed under one</option>
										{answer.types.map((type) => (
											<option key={type.name} value={type.name}>
												{type.name}
											</option>
										))}
									</select>
									<span className="mt-1.5 block text-[11.5px] text-slate-faint">
										Your society's own vocabulary. Filing only, never delivery.
									</span>
								</label>
							)}
						</div>
					</Card>
				</div>

				{/* The standing answer to "who is this going to", beside the
				    composer rather than under it: it has to be readable at the
				    moment somebody presses send, not after they scroll back up. */}
				<div className="space-y-5">
					<MessagePreview channel={channel} title={title} body={channel === "sms" ? (smsMessage || body) : body} />
					<Card className="lg:sticky lg:top-6">
						<SectionTitle>Before you send</SectionTitle>

						{!geoNode ? (
							<p className="text-[12.5px] leading-relaxed text-slate-body">
								Choose a branch on the left and this will say how many people that
								reaches, on each channel.
							</p>
						) : (
							<>
								<p className="mb-4 text-[12.5px] leading-relaxed text-slate-body">
									<b className="text-ink">{branchOf(chain)}</b> and everything under it
									· <span className="capitalize">{who}</span>
								</p>

								{reach.isLoading && <Spinner label="Counting…" />}
								{reach.error && <ErrorNote>{errorMessage(reach.error)}</ErrorNote>}

								{counts && (
									<>
										{/* A list rather than a grid of tiles: these are four
										    numbers that only mean anything against each other,
										    and a tile each would spread the comparison over half
										    a screen. */}
										<dl className="divide-y divide-hairline-soft">
											<div className="flex items-baseline justify-between gap-3 pb-2.5">
												<dt className="text-[12.5px] font-semibold text-ink">
													People addressed
												</dt>
												<dd className="tabular font-display text-[20px] font-extrabold leading-none text-ink">
													{counts.addressed}
												</dd>
											</div>
											{available.map((channel) => (
												<div
													key={channel.key}
													className="flex items-baseline justify-between gap-3 py-2.5"
												>
													<dt
														className={cx(
															"flex items-center gap-2 text-[12.5px]",
															chosen.has(channel.key)
																? "font-semibold text-navy"
																: "text-slate-faint",
														)}
													>
														<channel.icon size={13} />
														{channel.label}
													</dt>
													<dd
														className={cx(
															"tabular font-display text-[16px] font-bold leading-none",
															chosen.has(channel.key)
																? "text-ink"
																: "text-slate-faint",
														)}
													>
														{counts[channel.key]}
													</dd>
												</div>
											))}
										</dl>

										{counts.addressed > 0 && (
											<p className="mt-3 text-[11.5px] leading-relaxed text-slate-faint">
												A channel reaching fewer people than are addressed is a
												gap in what the society holds about them — a missing
												login, address or number — not a smaller audience.
											</p>
										)}
									</>
								)}
							</>
						)}

						<div className="mt-5 border-t border-hairline pt-5">
							<Button
								variant="navy"
								disabled={!ready || !answer.can_send}
								onClick={() => setConfirming(true)}
								className="w-full"
							>
								Send
							</Button>

							{!answer.can_send && (
								<p className="mt-2 text-[11.5px] leading-relaxed text-slate-faint">
									You may read this screen but not send from it.
								</p>
							)}
						</div>
						<p className="mt-3 text-[11.5px] leading-relaxed text-slate-faint">Draft saving, reusable templates, and scheduled delivery are unavailable in the current VMMS communication API. Nothing on this page implies those states are persisted.</p>
					</Card>
				</div>
			</div>

			<ConfirmDialog
				open={confirming}
				title="Send this now?"
				confirmLabel="Yes, send it"
				busy={busy}
				onConfirm={() => void send()}
				onCancel={() => setConfirming(false)}
			>
				<p>
					<b>{title || "This message"}</b> goes to{" "}
					<b>{counts?.addressed ?? 0} people</b> — {who} at{" "}
					{chain[chain.length - 1]?.label ?? "the branch you chose"} and everything under
					it.
				</p>
				<ul className="mt-3 space-y-1.5">
					{available
						.filter((channel) => chosen.has(channel.key))
						.map((channel) => (
							<li key={channel.key} className="flex items-start gap-2">
								<span className="mt-0.5 flex-none text-slate-faint">
									<channel.icon size={14} />
								</span>
								<span>
									<b>{channel.label}</b> — {counts?.[channel.key] ?? 0} reachable
									{channel.key === "sms" && ", filed as a draft campaign for approval"}
								</span>
							</li>
						))}
				</ul>
				<p className="mt-3">
					An announcement cannot be recalled once it is out. Editing it afterwards corrects
					it everywhere at once, which is the only way back.
				</p>
			</ConfirmDialog>
		</>
	);
}

/**
 * The chosen branch, without the society's own name at the head of it.
 *
 * The same rule `branchPath` applies to a server-rendered path, applied to a
 * picker's chain: inside this console every record belongs to the same society,
 * so naming it costs a line and says nothing. The crown stays on when there is
 * nothing under it — somebody addressing the whole society should read that.
 */
function branchOf(chain: GeoNode[]): string {
	return (chain.length > 1 ? chain.slice(1) : chain).map((node) => node.label).join(" · ");
}

function MessagePreview({ channel, title, body }: { channel: string; title: string; body: string }) {
	if (channel === "sms") return <Card><SectionTitle>SMS preview</SectionTitle><div className="mx-auto max-w-[270px] rounded-[28px] bg-[#24272C] p-3 shadow-card"><div className="rounded-[20px] bg-white p-4"><p className="mb-3 text-center text-[11px] font-semibold text-slate-faint">Tanzania Red Cross Society</p><div className="rounded-2xl rounded-bl-sm bg-[#EDF3FF] px-3.5 py-3 text-[13px] leading-relaxed text-ink">{body || "Your message preview appears here."}</div></div></div><p className="mt-3 text-[11.5px] text-slate-faint">{body.length} characters. Segment count is not shown because the provider has not supplied an encoding-aware estimator.</p></Card>;

	if (channel === "email") return <Card><SectionTitle>Email preview</SectionTitle><div className="overflow-hidden rounded-card border border-hairline"><div className="bg-[#24272C] px-4 py-3 text-[12px] font-bold text-white">Tanzania Red Cross Society</div><div className="bg-white p-4"><p className="mb-3 border-b border-hairline pb-3 text-[12px]"><b>Subject:</b> {title || "Your subject"}</p><p className="text-[13px]">Hello Amina,</p><p className="mt-3 whitespace-pre-wrap text-[13px] leading-relaxed text-slate-body">{body || "Your email preview appears here."}</p></div></div></Card>;

	return <Card><SectionTitle>In-app preview</SectionTitle><div className="rounded-card border border-hairline bg-white p-4 shadow-nav"><div className="flex gap-3"><span className="rounded-full bg-[#EDF3FF] p-2 text-blue"><Icon.bell size={16} /></span><div><h3 className="text-[13px] font-bold text-ink">{title || "Notification title"}</h3><p className="mt-1 whitespace-pre-wrap text-[12.5px] leading-relaxed text-slate-body">{body || "Your notification preview appears here."}</p></div></div></div></Card>;
}

function CommunicationHistory({ channel }: { channel: string }) {
	return <><PageHeading title={`Sent ${channel === "system" ? "notifications" : channel}`} lead="A server-paged campaign history will appear here when VMMS exposes a permission-scoped history contract." /><Card><SectionTitle>History unavailable</SectionTitle><p className="text-[13px] leading-relaxed text-slate-body">The current backend can publish announcements and file SMS drafts, but it does not expose a coordinator-safe campaign listing, delivery summary, recipient-level results, or provider status feed. No delivery states are fabricated.</p></Card></>;
}

/**
 * The three channels, and what each of them actually is.
 *
 * The keys match the server's own closed set — `api/communication.py` refuses a
 * channel it does not know rather than silently dropping it, so a typo here is
 * a visible error rather than a message somebody thinks they sent.
 */
const CHANNELS = [
	{
		key: "notification" as const,
		label: "Notification",
		icon: Icon.bell,
		hint: "In the portal, for anybody with a login.",
	},
	{
		key: "email" as const,
		label: "Email",
		icon: Icon.mail,
		hint: "Reaches people who have never signed in.",
	},
	{
		key: "sms" as const,
		label: "SMS",
		icon: Icon.phone,
		hint: "Filed as a draft campaign for approval.",
	},
];

/** What each channel did, said plainly, once. */
function Report({ report, onDismiss }: { report: CommunicationReport; onDismiss: () => void }) {
	const sent = report.announcement;

	return (
		<Card className="mb-5 border border-emerald-200 bg-emerald-50/40">
			<div className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h2 className="font-display text-[15px] font-extrabold text-ink">That went out.</h2>
					<ul className="mt-2 space-y-1 text-[12.5px] text-slate-body">
						{report.notification_sent && sent && (
							<li>
								<b className="text-ink">{sent.delivered}</b> people now hold a copy in
								the portal.
							</li>
						)}
						{report.email_sent && sent && (
							<li>
								Email queued to everybody in that audience with an address on file.
							</li>
						)}
						{report.sms && (
							<li>
								{/* Said as plainly as possible: nothing has been texted yet,
								    and somebody who believes it has will not go and approve
								    it. */}
								<b className="text-ink">Nothing has been texted yet.</b> A draft
								campaign to {report.sms.recipients} numbers is waiting for approval —{" "}
								<a
									href={report.sms.url}
									className="font-semibold text-navy underline underline-offset-2"
								>
									finish it here
								</a>
								{report.sms.malformed > 0 && (
									<>
										{" "}
										· {report.sms.malformed} numbers were left out for having no
										country code
									</>
								)}
								.
							</li>
						)}
					</ul>
				</div>

				<Button variant="quiet" onClick={onDismiss}>
					Dismiss
				</Button>
			</div>
		</Card>
	);
}
