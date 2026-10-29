import ChannelOverview from "./communication/ChannelOverview";
import { CommunicationWorkspace } from "./communication/CommunicationWorkspace";
import { MessageComposer } from "./communication/MessageComposer";
import { useCommunicationActions, notifyCommunicationChanged } from "./communication/history";
import { useContext, useState, type Dispatch, type SetStateAction } from "react";
import { FrappeContext, useFrappeGetCall, useFrappeFileUpload, type FrappeConfig } from "frappe-react-sdk";
import { Navigate, useParams, useNavigate } from "react-router-dom";

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
import type { CommunicationOptions, CommunicationReach, CommunicationReport, GeoNode } from "../portal/types";

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
	const { channel = "system", view } = useParams();
	if(view === "overview")return <ChannelOverview key={channel} />;
	return <CommunicationContainer key={channel} />;
}

function CommunicationContainer() {
	const navigate = useNavigate();
 const { saveCommunicationDraft } = useCommunicationActions();
	const { upload } = useFrappeFileUpload();
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
	const [waMessage, setWaMessage] = useState("");
	const [smsTemplate, setSmsTemplate] = useState("");
	const [delivery, setDelivery] = useState<"approval" | "scheduled">("approval");
	const [scheduledAt, setScheduledAt] = useState("");
	const [smsSourceType, setSmsSourceType] = useState("VMMS Audience");
	const [smsSourceDoctype, setSmsSourceDoctype] = useState("");
	const [smsPhoneField, setSmsPhoneField] = useState("");
	const [smsFilters, setSmsFilters] = useState<SmsFilter[]>([]);
	const [smsCsvFile, setSmsCsvFile] = useState("");
	const [smsPhoneNumbers, setSmsPhoneNumbers] = useState("");
	const [uploadingCsv, setUploadingCsv] = useState(false);
	const [urgency, setUrgency] = useState("routine");
	// Four fields the record has always had and this composer never offered.
	const [summary, setSummary] = useState("");
	const [expiresOn, setExpiresOn] = useState("");
	const [linkLabel, setLinkLabel] = useState("");
	const [linkHref, setLinkHref] = useState("");
	const [announcementType, setAnnouncementType] = useState("");

	const [confirming, setConfirming] = useState(false);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const [draftId, setDraftId] = useState<string | undefined>();
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
	const wantsWhatsapp = chosen.has("whatsapp");
	// The concept supports scheduling on every channel; campaigns still require approval.
	const requiresApproval = wantsSms || wantsWhatsapp;
	const canSchedule = true;
	const composed = wantsSms ? smsMessage : wantsWhatsapp ? waMessage : body;
	const recipientCount =
		wantsSms && smsSourceType === "Manual"
			? new Set(
					smsPhoneNumbers
						.split(/\n|,/)
						.map((value) => value.trim())
						.filter(Boolean),
				).size
			: (counts?.[channelKey as keyof CommunicationReach] ?? 0);
	const phoneFields = useFrappeGetCall<{ message: string[] }>(
		API.smsDoctypeFields,
		{ doctype: smsSourceDoctype },
		wantsSms && smsSourceType === "Doctype Query" && smsSourceDoctype
			? `sms:phones:${smsSourceDoctype}`
			: null,
	);
	const filterFields = useFrappeGetCall<{ message: SmsFilterField[] }>(
		API.smsFilterFields,
		{ doctype: smsSourceDoctype },
		wantsSms && smsSourceType === "Doctype Query" && smsSourceDoctype
			? `sms:filters:${smsSourceDoctype}`
			: null,
	);

	const ready =
		Boolean(geoNode) &&
		channels.length > 0 &&
		title.trim().length > 0 &&
		composed.trim().length > 0 &&
		(!canSchedule || delivery === "approval" || (Boolean(scheduledAt) && new Date(scheduledAt).getTime() > Date.now())) &&
		(!wantsSms ||
			smsSourceType === "VMMS Audience" ||
			(smsSourceType === "Doctype Query" && Boolean(smsSourceDoctype && smsPhoneField)) ||
			(smsSourceType === "CSV Upload" && Boolean(smsCsvFile)) ||
			(smsSourceType === "Manual" && Boolean(smsPhoneNumbers.trim())));

	const send = async () => {
		setBusy(true);
		setFailure(null);

		try {
			const response = await call.post<{ message: CommunicationReport & { history_id?: string } }>(
				API.communicationSend,
				{
					title: title.trim(),
					chain,
					branch: branchOf(chain),
					draft_id: draftId,
					scheduled_at: delivery === "scheduled" ? scheduledAt : undefined,
					body: composed.trim(),
					geo_node: geoNode,
					who,
					channels,
					urgency,
					announcement_type: announcementType || undefined,
					summary: summary.trim() || undefined,
					expires_on: expiresOn || undefined,
					// The address is what draws the link and the label only names it —
					// the portal falls back to "Open" — so the two are sent
					// independently rather than gated on each other.
					link_label: linkLabel.trim() || undefined,
					link_href: linkHref.trim() || undefined,
					sms_message: smsMessage.trim() || undefined,
					sms_template: smsTemplate || undefined,
					sms_scheduled_at: delivery === "scheduled" ? scheduledAt : undefined,
					sms_source_type: smsSourceType,
					sms_source_doctype: smsSourceDoctype || undefined,
					sms_phone_field: smsPhoneField || undefined,
					sms_filters: smsFilters,
					sms_csv_file: smsCsvFile || undefined,
					sms_phone_numbers: smsPhoneNumbers || undefined,
					whatsapp_message: waMessage.trim() || undefined,
					whatsapp_scheduled_at: delivery === "scheduled" ? scheduledAt : undefined,
				},
			);

			notifyCommunicationChanged();
			setDraftId(undefined);
			setReport(response.message);
			navigate(
				`/admin/communication/${channel}/sent${response.message.history_id ? `?message=${response.message.history_id}` : ""}`,
			);
			setConfirming(false);
			// The words go, the audience stays. Somebody who has just told Arusha
			// one thing is quite likely to tell Arusha the next thing, and making
			// them rebuild the picker each time is how a branch stops using this.
			setTitle("");
			setBody("");
			setSummary("");
			setExpiresOn("");
			setLinkLabel("");
			setLinkHref("");
			setSmsMessage("");
			setWaMessage("");
			setSmsTemplate("");
			setDelivery("approval");
			setScheduledAt("");
		} catch (error) {
			setFailure(errorMessage(error, "That was not sent."));
			setConfirming(false);
		} finally {
			setBusy(false);
		}
	};

	const uploadCsv = async (file: File) => {
		setUploadingCsv(true);
		setFailure(null);
		try {
			const header = (await file.text())
				.split(/\r?\n/, 1)[0]
				.split(",")
				.map((value) => value.trim().replace(/^"|"$/g, ""));
			if (!header.includes("phone_number")) throw new Error("The CSV must include a phone_number column.");
			const uploaded = await upload(file, { isPrivate: true });
			setSmsCsvFile(uploaded.file_url);
		} catch (error) {
			setFailure(errorMessage(error, "The CSV file could not be uploaded."));
		} finally {
			setUploadingCsv(false);
		}
	};

	if (options.isLoading) {
		return <Spinner page label="Loading the composer…" />;
	}

	if (options.error || !answer) {
		return <ErrorNote>{errorMessage(options.error, "This screen could not be opened.")}</ErrorNote>;
	}
	if (!["system", "email", "sms", "whatsapp"].includes(channel) || !["compose", "sent"].includes(view))
		return <Navigate to="/admin/communication/system/compose" replace />;

	if (!answer.channels[channelKey as keyof typeof answer.channels]) {
		const missingSms = channel === "sms" && !answer.sms_installed;
		return (
			<>
				<PageHeading title={`Compose ${channel === "system" ? "notification" : channel}`} />
				<Card>
					<SectionTitle>
						{missingSms ? "Install SMS to use this channel" : "Channel unavailable"}
					</SectionTitle>
					<p className="text-[13px] leading-relaxed text-muted">
						{missingSms
							? "The optional onerc_sms app is not installed on this site. Ask your system administrator to install and migrate onerc_sms, then reload this page. In-app notifications, email and WhatsApp remain available from the channel menu."
							: "This channel is not available to your account on this site. Availability is determined by the server and the channel provider’s permissions."}
					</p>
				</Card>
			</>
		);
	}

	const available = CHANNELS.filter((channel) => answer.channels[channel.key]);
	// The channel's name as a person says it, and the verb on the button. Both
	// were inline ternaries when there were three channels; a fourth is where
	// that stops being readable, and "Compose whatsapp" is what it produced.
	const saveDraft = async () => {
		setFailure(null); setBusy(true);
 try { const draft = await saveCommunicationDraft({
			channel,
			title,
			body: composed,
			geo_node: geoNode,
			who,
			branch: branchOf(chain),
			chain,
			id: draftId,
			draft_fields: {
				urgency,
				summary,
				expiresOn,
				linkLabel,
				linkHref,
				announcementType,
				smsTemplate,
				delivery,
				scheduledAt,
				smsSourceType,
				smsSourceDoctype,
				smsPhoneField,
				smsFilters,
				smsCsvFile,
				smsPhoneNumbers,
			},
		});
		navigate(`/admin/communication/${channel}/sent?status=Draft&message=${draft.id}`);
 } catch(error) { setFailure(errorMessage(error, "The draft could not be saved.")); } finally { setBusy(false); }
	};
	const recipientFields = (
		<>
			<label className="comm-field-label">Branch</label>
			<GeoSelects chain={chain} onChain={setChain} idPrefix="comms" />
			<label className="comm-field-label" htmlFor="comm-audience">
				Audience
			</label>
			<select id="comm-audience" value={who} onChange={(e) => setWho(e.target.value)}>
				{answer.audiences.map((option) => (
					<option key={option} value={option}>
						{option}
					</option>
				))}
			</select>
			{counts && (
				<p className="comm-reach">
					<Icon.people size={15} />
					<strong>{counts[channelKey as keyof CommunicationReach] ?? 0}</strong> reachable recipients ·{" "}
					{counts.addressed} people in this audience
				</p>
			)}
		</>
	);
	const advancedFields = (
		<>
			{wantsSms && (
				<section>
					<h3>Contact source</h3>
					<label className="mb-4 block">
						<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Source type</span>
						<select
							value={smsSourceType}
							onChange={(event) => {
								setSmsSourceType(event.target.value);
								setSmsFilters([]);
							}}
							className="w-full rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink outline-none transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft"
						>
							<option>VMMS Audience</option>
							<option>Doctype Query</option>
							<option>CSV Upload</option>
							<option>Manual</option>
						</select>
					</label>

					{smsSourceType === "Doctype Query" && (
						<>
							<div className="grid gap-4 sm:grid-cols-2">
								<label>
									<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">
										Source DocType
									</span>
									<select
										value={smsSourceDoctype}
										onChange={(event) => {
											setSmsSourceDoctype(event.target.value);
											setSmsPhoneField("");
											setSmsFilters([]);
										}}
										className="w-full rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink outline-none transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft"
									>
										<option value="">Select volunteer or member records</option>
										{(answer.sms_source_doctypes ?? []).map((doctype) => (
											<option key={doctype.value} value={doctype.value}>
												{doctype.label}
											</option>
										))}
									</select>
									{(answer.sms_source_doctypes ?? []).length === 0 && (
										<span className="mt-1.5 block text-[11px] text-slate-faint">
											No volunteer or member DocTypes are readable by your account.
										</span>
									)}
								</label>
								<label>
									<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">
										Phone field
									</span>
									<select
										value={smsPhoneField}
										onChange={(event) => setSmsPhoneField(event.target.value)}
										disabled={!smsSourceDoctype || phoneFields.isLoading}
										className="w-full rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink outline-none transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft"
									>
										<option value="">Select phone field</option>
										{(phoneFields.data?.message ?? []).map((field) => (
											<option key={field}>{field}</option>
										))}
									</select>
								</label>
							</div>
							<div className="mt-5 border-t border-card-line pt-4">
								<div className="mb-3 flex items-center justify-between">
									<h4 className="text-[12.5px] font-semibold text-ink">Filters</h4>
									<button
										type="button"
										onClick={() =>
											setSmsFilters((rows) => [
												...rows,
												{ filter_field: "", operator: "Equals", filter_value: "" },
											])
										}
										disabled={!smsSourceDoctype}
										className="rounded-full border border-card-line bg-white px-3 py-1.5 text-[11px] font-medium text-blue disabled:opacity-50"
									>
										Add filter
									</button>
								</div>
								<div className="space-y-2">
									{smsFilters.map((row, index) => (
										<div
											key={index}
											className="grid gap-2 rounded-[12px] bg-surface p-2 sm:grid-cols-[1fr_120px_1fr_30px]"
										>
											<select
												aria-label={`Filter ${index + 1} field`}
												value={row.filter_field}
												onChange={(event) =>
													updateSmsFilter(setSmsFilters, index, "filter_field", event.target.value)
												}
												className="min-w-0 rounded-[9px] border border-card-line bg-white px-2.5 py-2 text-[11.5px]"
											>
												<option value="">Field</option>
												{(filterFields.data?.message ?? []).map((field) => (
													<option key={field.value} value={field.value}>
														{field.label}
													</option>
												))}
											</select>
											<select
												aria-label={`Filter ${index + 1} operator`}
												value={row.operator}
												onChange={(event) =>
													updateSmsFilter(setSmsFilters, index, "operator", event.target.value)
												}
												className="rounded-[9px] border border-card-line bg-white px-2 py-2 text-[11.5px]"
											>
												{SMS_FILTER_OPERATORS.map((operator) => (
													<option key={operator}>{operator}</option>
												))}
											</select>
											<input
												aria-label={`Filter ${index + 1} value`}
												value={row.filter_value}
												onChange={(event) =>
													updateSmsFilter(setSmsFilters, index, "filter_value", event.target.value)
												}
												placeholder="Value"
												className="min-w-0 rounded-[9px] border border-card-line px-2.5 py-2 text-[11.5px]"
											/>
											<button
												type="button"
												aria-label={`Remove filter ${index + 1}`}
												onClick={() =>
													setSmsFilters((rows) => rows.filter((_, rowIndex) => rowIndex !== index))
												}
												className="grid h-[34px] w-[30px] place-items-center rounded-[9px] text-slate-faint hover:bg-white hover:text-blue"
											>
												×
											</button>
										</div>
									))}
								</div>
							</div>
						</>
					)}

					{smsSourceType === "CSV Upload" && (
						<label className="block">
							<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">CSV file</span>
							<input
								type="file"
								accept=".csv,text/csv"
								disabled={uploadingCsv}
								onChange={(event) => {
									const file = event.target.files?.[0];
									if (file) void uploadCsv(file);
								}}
								className="w-full rounded-xl border border-card-line bg-white px-3 py-2 text-[12px]"
							/>
							<span className="mt-1.5 block text-[11px] text-slate-faint">
								{uploadingCsv
									? "Uploading…"
									: smsCsvFile
										? "CSV attached"
										: "The file must contain a phone_number column."}
							</span>
						</label>
					)}
					{smsSourceType === "Manual" && (
						<label className="block">
							<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Phone numbers</span>
							<textarea
								aria-label="Phone numbers"
								value={smsPhoneNumbers}
								onChange={(event) => setSmsPhoneNumbers(event.target.value)}
								rows={6}
								placeholder={"+255700000001\n+255700000002"}
								className="w-full resize-y rounded-xl border border-card-line px-3.5 py-2.5 font-mono text-[12.5px] outline-none focus:border-blue"
							/>
							<span className="mt-1.5 block text-[11px] text-slate-faint">
								One number per line, including country code.
							</span>
						</label>
					)}
				</section>
			)}
			{!wantsSms && !wantsWhatsapp && (
				<div className="grid gap-4 sm:grid-cols-2">
					<label className="block">
						<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Priority</span>
						<select
							value={urgency}
							onChange={(event) => setUrgency(event.target.value)}
							className="w-full rounded-xl border border-card-line bg-white px-3.5 py-2.5 text-[13.5px] capitalize outline-none focus:border-blue"
						>
							{answer.urgencies.map((option) => (
								<option key={option} value={option} className="capitalize">
									{option}
								</option>
							))}
						</select>
						<span className="mt-1.5 block text-[11.5px] text-slate-faint">
							Sets the notification priority.
						</span>
					</label>

					{answer.types.length > 0 && (
						<label className="block">
							<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Message type</span>
							<select
								value={announcementType}
								onChange={(event) => setAnnouncementType(event.target.value)}
								className="w-full rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink outline-none transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft"
							>
								<option value="">No category</option>
								{answer.types.map((type) => (
									<option key={type.name} value={type.name}>
										{type.name}
									</option>
								))}
							</select>
							<span className="mt-1.5 block text-[11.5px] text-slate-faint">Optional message category.</span>
						</label>
					)}

					{/* The four fields the announcement record has always carried
							    and this composer never asked for. `send()` takes every
							    one of them and `announce.publish` reads them: the summary
							    is what a list row shows, the expiry is what takes it back
							    down, and the pair at the bottom is where it points. An
							    announcement written here had no summary, never expired
							    and could not link anywhere. */}
					<label className="block sm:col-span-2">
						<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">One-line summary</span>
						<input
							value={summary}
							onChange={(event) => setSummary(event.target.value)}
							placeholder="What this is about, in a line"
							className="w-full rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink outline-none transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft"
						/>
						<span className="mt-1.5 block text-[11.5px] text-slate-faint">
							Optional. Shown in people's lists above the message itself.
						</span>
					</label>

					<label className="block">
						<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Take it down on</span>
						<input
							type="date"
							value={expiresOn}
							min={new Date().toISOString().slice(0, 10)}
							onChange={(event) => setExpiresOn(event.target.value)}
							className="w-full rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink outline-none transition focus:border-blue focus:ring-[3px] focus:ring-blue-soft"
						/>
						<span className="mt-1.5 block text-[11.5px] text-slate-faint">
							Optional. It stops being shown after this day; nothing is deleted.
						</span>
					</label>

					<label className="block">
						<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Button text</span>
						<input
							value={linkLabel}
							onChange={(event) => setLinkLabel(event.target.value)}
							placeholder="Read the notice"
							className="w-full rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink outline-none transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft"
						/>
						<span className="mt-1.5 block text-[11.5px] text-slate-faint">
							Optional. Names the link below; without it the button reads "Open".
						</span>
					</label>

					<label className="block sm:col-span-2">
						<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Link URL</span>
						{/* Not `type="url"`. `vmmsx/links.py` accepts a
								    site-relative path, http, https, mailto and tel, and
								    the browser's url validation refuses three of those
								    five — so it would block "/notices/flooding", which
								    is the address a branch is most likely to use. The
								    server is the one that checks. */}
						<input
							value={linkHref}
							onChange={(event) => setLinkHref(event.target.value)}
							placeholder="https://…  or  /notices/flooding"
							className="w-full rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink outline-none transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft"
						/>
						<span className="mt-1.5 block text-[11.5px] text-slate-faint">
							Optional. A page on your own site, another address, or an email or phone link. Without button
							text it reads "Open".
						</span>
					</label>
				</div>
			)}
			<section>
				<h3>Delivery</h3>
				<div className="grid gap-3 sm:grid-cols-2">
					<button
						type="button"
						onClick={() => setDelivery("approval")}
						aria-pressed={!canSchedule || delivery === "approval"}
						className={cx(
							"rounded-[13px] border p-4 text-left",
							!canSchedule || delivery === "approval"
								? "border-blue/30 bg-blue-soft"
								: "border-card-line bg-white",
						)}
					>
						<div className="flex items-center gap-2 text-[12px] font-semibold text-blue">
							<Icon.check size={15} />
							{requiresApproval ? "As soon as approved" : "Send now"}
						</div>
						<p className="mt-1 text-[11px] leading-relaxed text-slate-faint">
							{CHANNELS.find((item) => item.key === channelKey)?.hint}
						</p>
					</button>
					<button
						type="button"
						disabled={!canSchedule}
						onClick={() => setDelivery("scheduled")}
						aria-pressed={canSchedule && delivery === "scheduled"}
						className={cx(
							"rounded-[13px] border p-4 text-left",
							canSchedule && delivery === "scheduled"
								? "border-blue/30 bg-blue-soft"
								: "border-card-line bg-surface/70",
							!canSchedule && "opacity-60",
						)}
					>
						<div className="text-[12px] font-semibold text-muted">Schedule</div>
						<p className="mt-1 text-[11px] text-slate-faint">
							{wantsSms
								? "Provider sends after approval at the chosen time."
								: wantsWhatsapp
									? "Held until this time once it has been approved."
									: "Deliver at the selected date and time."}
						</p>
					</button>
				</div>
				{canSchedule && delivery === "scheduled" && (
					<label className="mt-4 block">
						<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Scheduled at</span>
						<input
							type="datetime-local"
							value={scheduledAt}
							onChange={(event) => setScheduledAt(event.target.value)}
							className="w-full rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] text-ink outline-none transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft"
						/>
						<span className="mt-1.5 block text-[11px] text-slate-faint">
							{wantsSms
								? "Approval is required before the campaign can be sent."
								: requiresApproval ? "Approval is required before the broadcast can be sent." : "Choose a future date and time in your local time zone."}
						</span>
					</label>
				)}
			</section>
		</>
	);
	return (
		<>
			<CommunicationWorkspace
				channel={channel}
				view={view}
				onReuse={(message) => {
					setDraftId(message.status === "Draft" ? message.id : undefined);
					const saved = message.draft_fields;
					if (saved) {
						setUrgency(saved.urgency);
						setSummary(saved.summary);
						setExpiresOn(saved.expiresOn);
						setLinkLabel(saved.linkLabel);
						setLinkHref(saved.linkHref);
						setAnnouncementType(saved.announcementType);
						setSmsTemplate(saved.smsTemplate);
						setDelivery(saved.delivery);
						setScheduledAt(saved.scheduledAt);
						setSmsSourceType(saved.smsSourceType);
						setSmsSourceDoctype(saved.smsSourceDoctype);
						setSmsPhoneField(saved.smsPhoneField);
						setSmsFilters(saved.smsFilters);
						setSmsCsvFile(saved.smsCsvFile);
						setSmsPhoneNumbers(saved.smsPhoneNumbers);
					}
					setChain(message.chain ?? []);
					setWho(message.who || "everyone");
					setTitle(message.title);
					setBody(message.body);
					setSmsMessage(message.body);
					setWaMessage(message.body);
				}}
				composer={
					<MessageComposer
						channel={channel}
						title={title}
						body={composed}
						onTitle={setTitle}
						onBody={wantsSms ? setSmsMessage : wantsWhatsapp ? setWaMessage : setBody}
						audience={
							wantsSms && smsSourceType === "Manual"
								? `${
										new Set(
											smsPhoneNumbers
												.split(/\n|,/)
												.map((value) => value.trim())
												.filter(Boolean),
										).size
									} manual phone numbers · ${branchOf(chain)}`
								: geoNode
									? `${who} · ${branchOf(chain)}`
									: ""
						}
						recipients={recipientFields}
						settings={advancedFields}
						ready={ready}
						canSend={answer.can_send}
						onReview={() => setConfirming(true)}
						onSaveDraft={() => void saveDraft()}
						templates={answer.sms_templates}
						onTemplate={(name) => {
							setSmsTemplate(name);
							const template = answer.sms_templates.find((item) => item.name === name);
							if (template) setSmsMessage(template.message);
						}}
						status={
							<>
								{failure && <ErrorNote>{failure}</ErrorNote>}
								{report && <Report report={report} onDismiss={() => setReport(null)} />}
							</>
						}
					/>
				}
			/>

			<ConfirmDialog
				open={confirming}
				title={requiresApproval ? "Create campaign draft?" : delivery === "scheduled" ? "Schedule message?" : "Send message?"}
				confirmLabel={requiresApproval ? "Create draft" : delivery === "scheduled" ? "Schedule message" : "Send message"}
				busy={busy}
				onConfirm={() => void send()}
				onCancel={() => setConfirming(false)}
			>
				<p>
					<b>{title || "This message"}</b> goes to <b>{recipientCount} recipients</b> — {who} at{" "}
					{chain[chain.length - 1]?.label ?? "the branch you chose"} and everything under it.
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
									<b>{channel.label}</b> —{" "}
									{channel.key === "sms" ? recipientCount : (counts?.[channel.key] ?? 0)} reachable
									{channel.key === "sms" && ", filed as a draft campaign for approval"}
									{channel.key === "whatsapp" && ", filed as a draft broadcast for approval"}
								</span>
							</li>
						))}
				</ul>
				<p className="mt-3">
					{requiresApproval
						? "The campaign is saved for approval before delivery."
						: delivery === "scheduled" ? `Scheduled for ${new Date(scheduledAt).toLocaleString()}.` : "Review the audience before confirming delivery."}
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

/**
 * The four channels, and what each of them actually is.
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
	{
		key: "whatsapp" as const,
		label: "WhatsApp",
		icon: Icon.chat,
		hint: "Filed for approval, then sent steadily rather than all at once.",
	},
];

interface SmsFilter {
	filter_field: string;
	operator: string;
	filter_value: string;
}

interface SmsFilterField {
	value: string;
	label: string;
	description: string;
}

const SMS_FILTER_OPERATORS = [
	"Equals",
	"Not Equals",
	"Like",
	"Not Like",
	"In",
	"Not In",
	">",
	"<",
	">=",
	"<=",
	"Between",
	"Is Set",
	"Is Not Set",
];

function updateSmsFilter(
	setRows: Dispatch<SetStateAction<SmsFilter[]>>,
	index: number,
	field: keyof SmsFilter,
	value: string,
) {
	setRows((rows) => rows.map((row, rowIndex) => (rowIndex === index ? { ...row, [field]: value } : row)));
}

/** What each channel did, said plainly, once. */
function Report({ report, onDismiss }: { report: CommunicationReport; onDismiss: () => void }) {
	const sent = report.announcement;

	return (
		<Card className="mb-5 border border-emerald-200 bg-emerald-50/40">
			<div className="flex flex-wrap items-start justify-between gap-3">
				<div>
					<h2 className="text-[15px] font-semibold text-ink">Message recorded</h2>
					<ul className="mt-2 space-y-1 text-[12.5px] text-muted">
						{report.notification_sent && sent && (
							<li>
								<b className="text-ink">{sent.delivered}</b> people now hold a copy in the portal.
							</li>
						)}
						{report.email_sent && sent && (
							<li>Email queued to everybody in that audience with an address on file.</li>
						)}
						{report.whatsapp && (
							<li>
								{/* Same plainness as the SMS line, and the extra sentence
								    is there because "approved" does not mean "arrived"
								    on this channel: the sending is paced, so a large
								    branch is still receiving it an hour later. */}
								<b className="text-ink">Nothing has been sent on WhatsApp yet.</b> A draft broadcast to{" "}
								{report.whatsapp.recipients} numbers is waiting for approval —{" "}
								<a href={report.whatsapp.url} className="font-semibold text-ink underline underline-offset-2">
									finish it here
								</a>
								. Once approved it goes out steadily, so a large branch takes a while to reach.
							</li>
						)}
						{report.sms && (
							<li>
								{/* Said as plainly as possible: nothing has been texted yet,
								    and somebody who believes it has will not go and approve
								    it. */}
								<b className="text-ink">Nothing has been texted yet.</b> A draft campaign to{" "}
								{report.sms.recipients} numbers is waiting for approval —{" "}
								<a href={report.sms.url} className="font-semibold text-ink underline underline-offset-2">
									finish it here
								</a>
								{report.sms.malformed > 0 && (
									<> · {report.sms.malformed} numbers were left out for having no country code</>
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
