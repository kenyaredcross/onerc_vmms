import { useContext, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
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
	const [smsTemplate, setSmsTemplate] = useState("");
	const [smsDelivery, setSmsDelivery] = useState<"approval" | "scheduled">("approval");
	const [smsScheduledAt, setSmsScheduledAt] = useState("");
	const [smsSourceType, setSmsSourceType] = useState("VMMS Audience");
	const [smsSourceDoctype, setSmsSourceDoctype] = useState("");
	const [smsPhoneField, setSmsPhoneField] = useState("");
	const [smsFilters, setSmsFilters] = useState<SmsFilter[]>([]);
	const [smsCsvFile, setSmsCsvFile] = useState("");
	const [smsPhoneNumbers, setSmsPhoneNumbers] = useState("");
	const [uploadingCsv, setUploadingCsv] = useState(false);
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
	const phoneFields = useFrappeGetCall<{ message: string[] }>(API.smsDoctypeFields, { doctype: smsSourceDoctype }, wantsSms && smsSourceType === "Doctype Query" && smsSourceDoctype ? `sms:phones:${smsSourceDoctype}` : null);
	const filterFields = useFrappeGetCall<{ message: SmsFilterField[] }>(API.smsFilterFields, { doctype: smsSourceDoctype }, wantsSms && smsSourceType === "Doctype Query" && smsSourceDoctype ? `sms:filters:${smsSourceDoctype}` : null);

	const ready =
		Boolean(geoNode) &&
		channels.length > 0 &&
		title.trim().length > 0 &&
		(wantsSms ? smsMessage.trim().length > 0 : body.trim().length > 0) &&
		(!wantsSms || smsDelivery === "approval" || Boolean(smsScheduledAt)) &&
		(!wantsSms || smsSourceType === "VMMS Audience" ||
			(smsSourceType === "Doctype Query" && Boolean(smsSourceDoctype && smsPhoneField)) ||
			(smsSourceType === "CSV Upload" && Boolean(smsCsvFile)) ||
			(smsSourceType === "Manual" && Boolean(smsPhoneNumbers.trim())));

	const send = async () => {
		setBusy(true);
		setFailure(null);

		try {
			const response = await call.post<{ message: CommunicationReport }>(API.communicationSend, {
				title: title.trim(),
				body: wantsSms ? smsMessage.trim() : body.trim(),
				geo_node: geoNode,
				who,
				channels,
				urgency,
				announcement_type: announcementType || undefined,
				sms_message: smsMessage.trim() || undefined,
				sms_template: smsTemplate || undefined,
				sms_scheduled_at: smsDelivery === "scheduled" ? smsScheduledAt : undefined,
				sms_source_type: smsSourceType,
				sms_source_doctype: smsSourceDoctype || undefined,
				sms_phone_field: smsPhoneField || undefined,
				sms_filters: smsFilters,
				sms_csv_file: smsCsvFile || undefined,
				sms_phone_numbers: smsPhoneNumbers || undefined,
			});

			setReport(response.message);
			setConfirming(false);
			// The words go, the audience stays. Somebody who has just told Arusha
			// one thing is quite likely to tell Arusha the next thing, and making
			// them rebuild the picker each time is how a branch stops using this.
			setTitle("");
			setBody("");
			setSmsMessage("");
			setSmsTemplate("");
			setSmsDelivery("approval");
			setSmsScheduledAt("");
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
			const data = new FormData();
			data.append("file", file);
			data.append("is_private", "1");
			const response = await fetch("/api/method/upload_file", { method: "POST", body: data, credentials: "same-origin" });
			const payload = await response.json() as { message?: { file_url?: string }; exception?: string };
			if (!response.ok || !payload.message?.file_url) throw new Error(payload.exception || "CSV upload failed.");
			setSmsCsvFile(payload.message.file_url);
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
	if (!["system", "email", "sms"].includes(channel) || !["compose", "sent"].includes(view)) return <Navigate to="/admin/communication/system/compose" replace />;
	if (view === "sent") return <CommunicationHistory channel={channel} />;
	if (!answer.channels[channelKey as keyof typeof answer.channels]) {
		return <><PageHeading title={`Compose ${channel === "system" ? "notification" : channel}`} /><Card><SectionTitle>Channel unavailable</SectionTitle><p className="text-[13px] leading-relaxed text-slate-body">This channel is not available to your account on this site. Availability is determined by the server and the channel provider’s permissions.</p></Card></>;
	}

	const available = CHANNELS.filter((channel) => answer.channels[channel.key]);

	return (
		<>
			<div className="mb-4 flex flex-wrap items-center gap-3">
				<div>
					<h2 className="font-display text-[24px] font-medium leading-tight tracking-tight text-ink">
						<EditableText k={`admin.communication.${channel}.heading`} fallback={`Compose ${channel === "system" ? "notification" : channel}`} />
					</h2>
					<p className="mt-1 text-[12px] text-slate-faint">
						<EditableText k="admin.communication.lead" fallback="Choose the audience, write the message, then review its real reach before sending." />
					</p>
				</div>
				<div className="ml-auto flex items-center gap-2">
					<span className="hidden rounded-full border border-hairline-strong bg-white px-3 py-2 text-[11px] text-slate-faint sm:block">Drafts and scheduling unavailable</span>
					<Button variant="navy" disabled={!ready || !answer.can_send} onClick={() => setConfirming(true)}>
						{channel === "sms" ? "Create SMS draft" : `Send ${channel === "system" ? "notification" : channel}`}
						{counts ? ` to ${counts[channelKey as keyof CommunicationReach] ?? 0}` : ""}
					</Button>
				</div>
			</div>

			{report && <Report report={report} onDismiss={() => setReport(null)} />}
			{failure && (
				<div className="mb-5">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<div className="grid items-start gap-3 lg:grid-cols-[minmax(0,1fr)_285px]">
				<div className="overflow-hidden rounded-[18px] bg-white shadow-card">
					<ComposerSection number="1" title="Audience" help="Choose a geographic scope and the people within it. The server rechecks this scope when you send.">
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
							{geoNode && (
								<div className="mt-3 flex flex-wrap items-center gap-2">
									<span className="rounded-full border border-blue/20 bg-[#EDF3FF] px-3 py-1.5 text-[11px] font-medium text-blue">{branchOf(chain)}</span>
									<span className="rounded-full border border-blue/20 bg-[#EDF3FF] px-3 py-1.5 text-[11px] font-medium capitalize text-blue">{who}</span>
									{counts && <span className="text-[11px] text-slate-faint">{counts.addressed} people addressed</span>}
								</div>
							)}
						</div>
					</ComposerSection>

					{wantsSms && (
						<ComposerSection number="2" title="Contact source" help="Use the VMMS audience above, or configure the same query, CSV, or manual source offered by OneRC SMS Desk.">
							<label className="mb-4 block">
								<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Source type</span>
								<select value={smsSourceType} onChange={(event) => { setSmsSourceType(event.target.value); setSmsFilters([]); }} className="w-full rounded-card border border-hairline-strong bg-white px-3.5 py-2.5 text-[13.5px] outline-none focus:border-navy">
									<option>VMMS Audience</option><option>Doctype Query</option><option>CSV Upload</option><option>Manual</option>
								</select>
							</label>

							{smsSourceType === "Doctype Query" && <>
								<div className="grid gap-4 sm:grid-cols-2">
									<label><span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Source DocType</span><select value={smsSourceDoctype} onChange={(event) => { setSmsSourceDoctype(event.target.value); setSmsPhoneField(""); setSmsFilters([]); }} className="w-full rounded-card border border-hairline-strong bg-white px-3.5 py-2.5 text-[13.5px] outline-none focus:border-navy"><option value="">Select volunteer or member records</option>{(answer.sms_source_doctypes ?? []).map((doctype) => <option key={doctype.value} value={doctype.value}>{doctype.label}</option>)}</select>{(answer.sms_source_doctypes ?? []).length === 0 && <span className="mt-1.5 block text-[11px] text-slate-faint">No volunteer or member DocTypes are readable by your account.</span>}</label>
									<label><span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Phone field</span><select value={smsPhoneField} onChange={(event) => setSmsPhoneField(event.target.value)} disabled={!smsSourceDoctype || phoneFields.isLoading} className="w-full rounded-card border border-hairline-strong bg-white px-3.5 py-2.5 text-[13.5px] outline-none focus:border-navy"><option value="">Select phone field</option>{(phoneFields.data?.message ?? []).map((field) => <option key={field}>{field}</option>)}</select></label>
								</div>
								<div className="mt-5 border-t border-hairline-soft pt-4">
									<div className="mb-3 flex items-center justify-between"><h4 className="text-[12.5px] font-semibold text-ink">Filters</h4><button type="button" onClick={() => setSmsFilters((rows) => [...rows, { filter_field: "", operator: "Equals", filter_value: "" }])} disabled={!smsSourceDoctype} className="rounded-full border border-hairline-strong bg-white px-3 py-1.5 text-[11px] font-medium text-blue disabled:opacity-50">Add filter</button></div>
									<div className="space-y-2">{smsFilters.map((row, index) => <div key={index} className="grid gap-2 rounded-[12px] bg-surface p-2 sm:grid-cols-[1fr_120px_1fr_30px]">
										<select aria-label={`Filter ${index + 1} field`} value={row.filter_field} onChange={(event) => updateSmsFilter(setSmsFilters, index, "filter_field", event.target.value)} className="min-w-0 rounded-[9px] border border-hairline-strong bg-white px-2.5 py-2 text-[11.5px]"><option value="">Field</option>{(filterFields.data?.message ?? []).map((field) => <option key={field.value} value={field.value}>{field.label}</option>)}</select>
										<select aria-label={`Filter ${index + 1} operator`} value={row.operator} onChange={(event) => updateSmsFilter(setSmsFilters, index, "operator", event.target.value)} className="rounded-[9px] border border-hairline-strong bg-white px-2 py-2 text-[11.5px]">{SMS_FILTER_OPERATORS.map((operator) => <option key={operator}>{operator}</option>)}</select>
										<input aria-label={`Filter ${index + 1} value`} value={row.filter_value} onChange={(event) => updateSmsFilter(setSmsFilters, index, "filter_value", event.target.value)} placeholder="Value" className="min-w-0 rounded-[9px] border border-hairline-strong px-2.5 py-2 text-[11.5px]" />
										<button type="button" aria-label={`Remove filter ${index + 1}`} onClick={() => setSmsFilters((rows) => rows.filter((_, rowIndex) => rowIndex !== index))} className="grid h-[34px] w-[30px] place-items-center rounded-[9px] text-slate-faint hover:bg-white hover:text-signal">×</button>
									</div>)}</div>
								</div>
							</>}

							{smsSourceType === "CSV Upload" && <label className="block"><span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">CSV file</span><input type="file" accept=".csv,text/csv" disabled={uploadingCsv} onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadCsv(file); }} className="w-full rounded-card border border-hairline-strong bg-white px-3 py-2 text-[12px]" /><span className="mt-1.5 block text-[11px] text-slate-faint">{uploadingCsv ? "Uploading…" : smsCsvFile ? `Uploaded: ${smsCsvFile}` : "The file must contain a phone_number column."}</span></label>}
							{smsSourceType === "Manual" && <label className="block"><span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Phone numbers</span><textarea value={smsPhoneNumbers} onChange={(event) => setSmsPhoneNumbers(event.target.value)} rows={6} placeholder={"+255700000001\n+255700000002"} className="w-full resize-y rounded-card border border-hairline-strong px-3.5 py-2.5 font-mono text-[12.5px] outline-none focus:border-navy" /><span className="mt-1.5 block text-[11px] text-slate-faint">One number per line, including country code.</span></label>}
						</ComposerSection>
					)}

					<ComposerSection number={wantsSms ? "3" : "2"} title="Message" help={channel === "sms" ? "Name the campaign, optionally start from a OneRC SMS template, then write the text." : "Write the title and message people will receive."}>
						<label className="mb-4 block">
							<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">
								{channel === "sms" ? "Campaign name" : "Subject"}
							</span>
							<input
								value={title}
								onChange={(event) => setTitle(event.target.value)}
								placeholder={channel === "sms" ? "Community health outreach reminder" : "Branch meeting moved to Saturday"}
								className="w-full rounded-card border border-hairline-strong px-3.5 py-2.5 text-[13.5px] outline-none focus:border-navy"
							/>
						</label>

						{wantsSms && (answer.sms_templates ?? []).length > 0 && (
							<label className="mb-4 block">
								<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Template</span>
								<select
									value={smsTemplate}
									onChange={(event) => {
										const next = event.target.value;
										setSmsTemplate(next);
										const template = (answer.sms_templates ?? []).find((item) => item.name === next);
										if (template) setSmsMessage(template.message);
									}}
									className="w-full rounded-card border border-hairline-strong bg-white px-3.5 py-2.5 text-[13.5px] outline-none focus:border-navy"
								>
									<option value="">Write without a template</option>
									{(answer.sms_templates ?? []).map((template) => <option key={template.name} value={template.name}>{template.template_name}{template.category ? ` · ${template.category}` : ""}</option>)}
								</select>
							</label>
						)}

						{!wantsSms && <label className="mb-4 block">
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
						</label>}

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
									placeholder="Write the SMS message"
									className="w-full resize-y rounded-card border border-hairline-strong px-3.5 py-2.5 text-[13.5px] outline-none focus:border-navy"
								/>
								<span className="mt-1.5 block text-[11.5px] leading-relaxed text-slate-faint">
									Anything over 160 characters is sent as more than one message.
								</span>
							</label>
						)}

						{!wantsSms && <div className="grid gap-4 sm:grid-cols-2">
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
						</div>}
					</ComposerSection>

					<ComposerSection number={wantsSms ? "4" : "3"} title="Delivery" help={channel === "sms" ? "The SMS provider receives a draft campaign for approval; it is not sent immediately." : "Delivery begins after you review and confirm the audience."} last>
						<div className="grid gap-3 sm:grid-cols-2">
							<button type="button" onClick={() => setSmsDelivery("approval")} aria-pressed={!wantsSms || smsDelivery === "approval"} className={cx("rounded-[13px] border p-4 text-left", !wantsSms || smsDelivery === "approval" ? "border-blue/30 bg-[#EDF3FF]" : "border-hairline bg-white")}>
								<div className="flex items-center gap-2 text-[12px] font-semibold text-blue"><Icon.check size={15} />{channel === "sms" ? "As soon as approved" : "Send now"}</div>
								<p className="mt-1 text-[11px] leading-relaxed text-slate-faint">{CHANNELS.find((item) => item.key === channelKey)?.hint}</p>
							</button>
							<button type="button" disabled={!wantsSms} onClick={() => setSmsDelivery("scheduled")} aria-pressed={wantsSms && smsDelivery === "scheduled"} className={cx("rounded-[13px] border p-4 text-left", wantsSms && smsDelivery === "scheduled" ? "border-blue/30 bg-[#EDF3FF]" : "border-hairline bg-surface/70", !wantsSms && "opacity-60")}>
								<div className="text-[12px] font-semibold text-slate-body">Schedule</div>
								<p className="mt-1 text-[11px] text-slate-faint">{wantsSms ? "Provider sends after approval at the chosen time." : "Not supported for this channel."}</p>
							</button>
						</div>
						{wantsSms && smsDelivery === "scheduled" && (
							<label className="mt-4 block">
								<span className="mb-2 block text-[12.5px] font-semibold text-slate-strong">Scheduled at</span>
								<input type="datetime-local" value={smsScheduledAt} onChange={(event) => setSmsScheduledAt(event.target.value)} className="w-full rounded-card border border-hairline-strong bg-white px-3.5 py-2.5 text-[13.5px] outline-none focus:border-navy" />
								<span className="mt-1.5 block text-[11px] text-slate-faint">Stored on the OneRC SMS campaign and evaluated when an approver submits it.</span>
							</label>
						)}
					</ComposerSection>
				</div>

				<aside className="space-y-3 lg:sticky lg:top-6">
					<div className="rounded-[18px] bg-white p-4 shadow-card">
						<div className="mb-4 flex items-center justify-between gap-2">
							<h3 className="font-display text-[13px] font-semibold text-ink">{channel === "system" ? "Notification" : channel.toUpperCase()} preview</h3>
							<span className="rounded-full border border-blue/20 bg-[#EDF3FF] px-2.5 py-1 text-[10px] font-medium text-blue">{counts ? `${counts[channelKey as keyof CommunicationReach] ?? 0} reachable` : "Choose audience"}</span>
						</div>
						<MessagePreview channel={channel} title={title} body={channel === "sms" ? (smsMessage || body) : body} />
					</div>
					<div className="rounded-[18px] bg-white p-4 shadow-card">
						<h3 className="mb-3 font-display text-[13px] font-semibold text-ink">Before you send</h3>

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

						<div className="mt-4 border-t border-hairline pt-4">
							<Button
								variant="navy"
								disabled={!ready || !answer.can_send}
								onClick={() => setConfirming(true)}
								className="w-full"
							>
								{channel === "sms" ? "Create SMS draft" : "Send now"}
							</Button>

							{!answer.can_send && (
								<p className="mt-2 text-[11.5px] leading-relaxed text-slate-faint">
									You may read this screen but not send from it.
								</p>
							)}
						</div>
						<p className="mt-3 text-[10.5px] leading-relaxed text-slate-faint">Recipient selection is resolved from the geographic scope and audience group. Individual selection, reusable templates, and scheduling are not yet supported.</p>
					</div>
				</aside>
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

function ComposerSection({
	number,
	title,
	help,
	last = false,
	children,
}: {
	number: string;
	title: string;
	help: string;
	last?: boolean;
	children: ReactNode;
}) {
	return (
		<section className={cx("grid grid-cols-[34px_minmax(0,1fr)] gap-3 p-4 sm:p-5", !last && "border-b border-hairline-soft")}>
			<div className="grid h-8 w-8 place-items-center rounded-[10px] bg-[#EDF3FF] text-[12px] font-semibold text-blue">{number}</div>
			<div className="min-w-0">
				<h3 className="font-display text-[13px] font-semibold text-ink">{title}</h3>
				<p className="mb-4 mt-1 text-[11px] leading-relaxed text-slate-faint">{help}</p>
				{children}
			</div>
		</section>
	);
}

function MessagePreview({ channel, title, body }: { channel: string; title: string; body: string }) {
	if (channel === "sms") return <><div className="relative mx-auto h-[390px] max-w-[220px] rounded-[34px] border-[7px] border-[#D8DCE2] bg-[#F8F8F8] px-3 pb-4 pt-14 shadow-inner before:absolute before:left-1/2 before:top-3 before:h-4 before:w-[62px] before:-translate-x-1/2 before:rounded-full before:bg-[#E2E5E9]"><div className="rounded-[13px] rounded-bl-[4px] bg-[#E8E8E8] p-3 text-[11px] leading-relaxed text-slate-body">{body || "Your message preview appears here."}</div></div><p className="mt-3 text-[10.5px] leading-relaxed text-slate-faint">{body.length} characters. Segment count is not shown because the provider has not supplied an encoding-aware estimator.</p></>;

	if (channel === "email") return <div className="overflow-hidden rounded-[14px] border border-hairline"><div className="bg-[#24272C] px-4 py-3 text-[11px] font-semibold text-white">Tanzania Red Cross Society</div><div className="bg-white p-4"><p className="mb-3 text-[10px] text-slate-faint">{title || "Your subject"}</p><h4 className="text-[15px] font-medium text-ink">Hello Amina,</h4><p className="mt-3 whitespace-pre-wrap text-[11px] leading-relaxed text-slate-body">{body || "Your email preview appears here."}</p></div></div>;

	return <div className="rounded-[14px] bg-[#F5F5F5] p-3"><div className="grid grid-cols-[32px_minmax(0,1fr)] gap-2.5 rounded-[12px] bg-white p-3 shadow-nav"><span className="grid h-8 w-8 place-items-center rounded-[10px] bg-[#EDF3FF] text-blue"><Icon.bell size={15} /></span><div><h3 className="text-[11px] font-semibold text-ink">{title || "Notification title"}</h3><p className="mt-1 whitespace-pre-wrap text-[10.5px] leading-relaxed text-slate-body">{body || "Your notification preview appears here."}</p></div></div></div>;
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

const SMS_FILTER_OPERATORS = ["Equals", "Not Equals", "Like", "Not Like", "In", "Not In", ">", "<", ">=", "<=", "Between", "Is Set", "Is Not Set"];

function updateSmsFilter(
	setRows: Dispatch<SetStateAction<SmsFilter[]>>,
	index: number,
	field: keyof SmsFilter,
	value: string,
) {
	setRows((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, [field]: value } : row));
}

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
