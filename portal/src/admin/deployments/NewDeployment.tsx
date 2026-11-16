import { useContext, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../../lib/api";
import { googleMapsUrl } from "../../lib/maps";
import type {
	DeploymentDetail as DeploymentDetailDto,
	DeploymentSetup,
	GeoNode,
	SendingResult,
	TermsOfReference,
} from "../../portal/types";
import { GeoSelects, selectedNode } from "../../ui/GeoSelects";
import { Button, ButtonLink, Card, ErrorNote, PageHeading, SectionTitle, Spinner, cx } from "../../ui/primitives";
import { useCanCreate } from "../creates";
import { INPUT, Labelled } from "../Projects";
import {
	NOTHING_SELECTED,
	NO_NEEDS,
	SendRequestDialog,
	SendingOutcome,
	VolunteerFinder,
	selectionParams,
	type Needs,
	type Selection,
} from "./candidates";
import { type MapPoint } from "./mapLinks";
import { PinTools } from "./PinTools";

/**
 * Setting up a deployment, and asking its people, on one page.
 *
 * The old system's Deployment Request Tool, folded into the deployment itself,
 * in the order the user set (Nov 2026): the details (the terms first, since
 * they fill in the dates), the location,
 * the notifications, and then the volunteers — selected with the old tool's
 * quick filters — found with the filters and asked or placed in the same press.
 * Kenya creates the deployment directly; there is no request record in between.
 *
 * **The county is the coordinator's own.** `deployment_setup` lists the counties
 * core's scope lets this person create a deployment in. A County Coordinator has
 * one, so it is shown, not chosen; somebody with several chooses. Only terms
 * whose location covers that county are offered.
 *
 * **The branch office is the meeting point unless unticked**, read from the
 * county's `VMMS Branch Location`. The site's map pin is optional and needs no
 * paid account: the free place search, a click on the map, or whatever Google
 * Maps in the browser gives when pasted.
 *
 * **The skills, professions and languages filtered by are kept on the
 * deployment** as what it needs, so the deployment's own page starts its search
 * from them later.
 */
export function DeploymentCreate() {
	const [round, setRound] = useState(0);

	return (
		<>
			<PageHeading
				title="New deployment"
				lead="Set up the deployment and ask the volunteers from this page."
				trail={[{ label: "Deployments", to: "/admin/deployments" }, { label: "New deployment" }]}
			/>

			<NewDeploymentForm key={round} onAnother={() => setRound((was) => was + 1)} />
		</>
	);
}

interface Gap {
	anchor: string;
	note: string;
}

const FOCUSABLE = new Set(["INPUT", "SELECT", "TEXTAREA", "BUTTON"]);

/** Bring the control a gap names into view and put the cursor in it. */
function pointAt(anchor: string): void {
	const field = document.getElementById(anchor);
	if (!field) return;

	(field.closest("label") ?? field).scrollIntoView?.({ behavior: "smooth", block: "center" });

	if (!FOCUSABLE.has(field.tagName)) field.setAttribute("tabindex", "-1");
	field.focus({ preventScroll: true });
}

/** Tomorrow at 08:00, as a `datetime-local` value: where a "later" send starts. */
function tomorrowMorning(): string {
	const date = new Date();
	date.setDate(date.getDate() + 1);
	const pad = (value: number) => String(value).padStart(2, "0");
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T08:00`;
}

/**
 * Whether deployment asks may go by SMS. Off, and the box hidden, until the
 * feature is finished (user, Nov 2026): asks go by email and the portal. Turning
 * this on brings the SMS box back here and on the deployment's own page.
 */
export const SMS_READY = false;

const ID = {
	county: "new-deployment-county",
	project: "new-deployment-project",
	attachment: "new-deployment-tor-attachment",
	volunteers: "new-deployment-volunteers",
	terms: "new-deployment-terms",
	title: "new-deployment-title",
	start: "new-deployment-start",
	end: "new-deployment-end",
	sendOn: "new-deployment-send-on",
};

type County = NonNullable<DeploymentSetup["counties"]>[number];

function NewDeploymentForm({ onAnother }: { onAnother: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const canCreate = useCanCreate();

	const setupCall = useFrappeGetCall<{ message: DeploymentSetup }>(
		API.deploymentSetup,
		undefined,
		"admin:deployment:setup",
	);
	const options = useFrappeGetCall<{
		message: { email_templates: Array<{ name: string; subject: string | null }>; professions?: string[] };
	}>(API.deploymentOptions, undefined, "admin:deployment:options");

	const setup = setupCall.data?.message;
	const counties = setup?.counties ?? null;

	// Location
	const [countyName, setCountyName] = useState("");
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [siteName, setSiteName] = useState("");
	const [siteAddress, setSiteAddress] = useState("");
	const [sitePin, setSitePin] = useState<MapPoint | null>(null);
	const [atOffice, setAtOffice] = useState(true);
	const [meetingPoint, setMeetingPoint] = useState("");
	const [meetingAddress, setMeetingAddress] = useState("");
	const [meetingPin, setMeetingPin] = useState<MapPoint | null>(null);
	const [contactName, setContactName] = useState("");
	const [contactPhone, setContactPhone] = useState("");
	const [travelNotes, setTravelNotes] = useState("");

	// Terms and details
	const [project, setProject] = useState("");
	const [terms, setTerms] = useState("");
	// A TOR written outside the system, attached instead of chosen.
	const [attaching, setAttaching] = useState(false);
	const [torFile, setTorFile] = useState<File | null>(null);
	// The file once uploaded, so a second press after a refusal does not upload it again.
	const uploaded = useRef<{ file: File; url: string } | null>(null);
	const [title, setTitle] = useState("");
	const [startDate, setStartDate] = useState("");
	const [endDate, setEndDate] = useState("");
	const [required, setRequired] = useState("");
	const [notes, setNotes] = useState("");
	const filledFromTerms = useRef({ start: "", end: "" });

	// Notifications, and what the deployment needs (from the filters)
	const [needs, setNeeds] = useState<Needs>(NO_NEEDS);
	const [byEmail, setByEmail] = useState(true);
	const [bySms, setBySms] = useState(SMS_READY);
	const [emailTemplate, setEmailTemplate] = useState("");
	const [future, setFuture] = useState(false);
	const [sendOn, setSendOn] = useState(tomorrowMorning);
	const [requiresContract, setRequiresContract] = useState(false);

	// Volunteers and the press
	const [selection, setSelection] = useState<Selection>(NOTHING_SELECTED);
	const [busy, setBusy] = useState<string | null>(null);
	const [failure, setFailure] = useState<string | null>(null);
	const [gapNote, setGapNote] = useState<string | null>(null);
	// Saved first, as in the old tool; then the request is sent to the people
	// selected, after a confirmation that names them.
	const [saved, setSaved] = useState<DeploymentDetailDto | null>(null);
	const [confirming, setConfirming] = useState(false);
	const [created, setCreated] = useState<{ deployment: DeploymentDetailDto; sending: SendingResult } | null>(null);

	// One county is shown, not chosen. Several, and the person chooses.
	const county: County | null =
		counties && counties.length === 1
			? counties[0]
			: (counties?.find((row) => row.name === countyName) ?? null);
	const geoNode = counties ? (county?.name ?? null) : (selectedNode(chain)?.name ?? null);
	const office = county?.branch_office ?? null;
	const meetsAtOffice = Boolean(office) && atOffice;

	const available = useFrappeGetCall<{ message: { terms: TermsOfReference[] } }>(
		API.branchTerms,
		{ active_only: 1, covering: geoNode ?? undefined },
		geoNode ? `admin:terms:covering:${geoNode}` : null,
	);
	const offered = (available.data?.message?.terms ?? []).filter((row) => row.is_offered);
	const timeZone = setup?.time_zone;

	// Every open project, and the projects of the offered terms (one may have
	// closed since its terms were written). As in the old tool, the project is
	// required: it narrows the terms, terms fill it in, and an attached TOR is
	// recorded under it. A deployment's project is its terms' project.
	const projects = [
		...new Map(
			[
				...(setup?.projects ?? []).map((row) => ({ name: row.name, label: row.project_name || row.name })),
				...offered
					.filter((row) => row.project)
					.map((row) => ({ name: row.project as string, label: row.project_name || (row.project as string) })),
			].map((row) => [row.name, row]),
		).values(),
	].sort((a, b) => a.label.localeCompare(b.label));
	const shownTerms = project ? offered.filter((row) => row.project === project) : offered;

	// Where the society approves its terms in the system, nothing may be attached.
	const canAttach = setup?.can_attach_terms ?? false;
	// No terms in the system for this county: attaching is the only way here.
	const mustAttach = canAttach && Boolean(geoNode) && !available.isLoading && offered.length === 0;
	const byAttachment = attaching || mustAttach;

	const chooseProject = (name: string) => {
		setProject(name);
		const current = offered.find((row) => row.name === terms);
		if (name && current && current.project !== name) setTerms("");
	};

	const chooseTerms = (name: string) => {
		setTerms(name);

		const chosen = offered.find((row) => row.name === name);
		if (chosen) setProject(chosen.project ?? "");
		const start = chosen?.expected_start_date?.slice(0, 10) ?? "";
		const end = chosen?.expected_end_date?.slice(0, 10) ?? "";
		const previous = filledFromTerms.current;

		// A date follows the terms while it is blank or still the one the last
		// terms put there. A date the coordinator typed is theirs and stays.
		if (!startDate || startDate === previous.start) setStartDate(start);
		if (!endDate || endDate === previous.end) setEndDate(end);

		filledFromTerms.current = { start, end };
	};

	// In the order of the page, so the first gap is the highest one. The county
	// comes before the terms, though it sits below them: the terms list waits on it.
	const gaps: Gap[] = [];
	if (!geoNode) gaps.push({ anchor: ID.county, note: "Choose the county." });
	if (!project) gaps.push({ anchor: ID.project, note: "Choose the project." });
	if (byAttachment && !torFile) gaps.push({ anchor: ID.attachment, note: "Attach the TOR." });
	if (!byAttachment && !terms) gaps.push({ anchor: ID.terms, note: "Choose the terms of reference." });
	if (!title.trim()) gaps.push({ anchor: ID.title, note: "Give the deployment a title." });
	if (!startDate) gaps.push({ anchor: ID.start, note: "Enter the expected start date." });
	if (!endDate) gaps.push({ anchor: ID.end, note: "Enter the expected end date." });
	if (startDate && endDate && endDate < startDate) {
		gaps.push({ anchor: ID.end, note: "The expected end date is before the expected start date." });
	}
	if (future && (!sendOn || new Date(sendOn) <= new Date())) {
		gaps.push({ anchor: ID.sendOn, note: "Choose a future deployment date that has not passed." });
	}

	// The search needs the place, the terms and the first day; nothing else. An
	// attached TOR asks for no certificates, so the search does not wait on it.
	const searchGap = gaps.find((gap) => [ID.county, ID.terms, ID.start].includes(gap.anchor)) ?? null;

	/** The attached TOR, uploaded as a private file, once. */
	const uploadTor = async (file: File): Promise<string> => {
		if (uploaded.current?.file === file) return uploaded.current.url;

		const body = new FormData();
		body.append("file", file);
		body.append("is_private", "1");

		const response = await fetch("/api/method/upload_file", {
			method: "POST",
			body,
			credentials: "same-origin",
			headers: { "X-Frappe-CSRF-Token": window.csrf_token ?? "" },
		});

		if (!response.ok) throw new Error("The TOR attachment could not be uploaded. Try again.");

		const answer = (await response.json()) as { message: { file_url: string } };
		uploaded.current = { file, url: answer.message.file_url };
		return answer.message.file_url;
	};

	/** Save the deployment. Nobody is asked yet: that is the next press. */
	const save = async () => {
		if (gaps.length) {
			setGapNote(gaps[0].note);
			pointAt(gaps[0].anchor);
			return;
		}

		setGapNote(null);
		setBusy("save");
		setFailure(null);

		try {
			const attachment = byAttachment && torFile ? await uploadTor(torFile) : undefined;

			const reply = await call.post<{
				message: { deployment: DeploymentDetailDto; sending: SendingResult | null };
			}>(API.createDeployment, {
				terms_of_reference: attachment ? "" : terms,
				tor_attachment: attachment,
				project,
				geo_node: geoNode,
				title: title.trim(),
				start_date: startDate,
				end_date: endDate,
				volunteers_required: required ? Number(required) : undefined,
				notes: notes.trim() || undefined,
				skills_needed: needs.skills,
				professions_needed: needs.professions,
				languages_needed: needs.languages,
				notify_by_email: byEmail ? 1 : 0,
				notify_by_sms: SMS_READY && bySms ? 1 : 0,
				email_template: byEmail && emailTemplate ? emailTemplate : undefined,
				requires_contract: requiresContract ? 1 : 0,
				send_on: future ? `${sendOn.replace("T", " ")}:00` : undefined,
				site_name: siteName.trim() || undefined,
				site_address: siteAddress.trim() || undefined,
				site_latitude: sitePin?.latitude,
				site_longitude: sitePin?.longitude,
				meeting_at_branch_office: meetsAtOffice ? 1 : 0,
				meeting_point: meetsAtOffice ? undefined : meetingPoint.trim() || undefined,
				meeting_address: meetsAtOffice ? undefined : meetingAddress.trim() || undefined,
				meeting_latitude: meetsAtOffice ? undefined : meetingPin?.latitude,
				meeting_longitude: meetsAtOffice ? undefined : meetingPin?.longitude,
				local_contact_name: contactName.trim() || undefined,
				local_contact_phone: contactPhone.trim() || undefined,
				travel_notes: travelNotes.trim() || undefined,
			});

			setSaved(reply.message.deployment);
		} catch (problem) {
			setFailure(errorMessage(problem, "The deployment was not created. Try again."));
		} finally {
			setBusy(null);
		}
	};

	/** The confirmation first: who the request goes to, by name. */
	const submit = () => {
		if (selection.count === 0) {
			setGapNote("Select the volunteers to send the request to.");
			pointAt(ID.volunteers);
			return;
		}

		setGapNote(null);
		setConfirming(true);
	};

	const send = async () => {
		if (!saved) return;

		setBusy("send");
		setFailure(null);

		try {
			const reply = await call.post<{ message: SendingResult }>(API.sendToVolunteers, {
				name: saved.name,
				mode: "ask",
				...selectionParams(selection),
			});

			setCreated({ deployment: saved, sending: reply.message });
			window.scrollTo?.({ top: 0, behavior: "smooth" });
		} catch (problem) {
			setFailure(errorMessage(problem, "The deployment request was not sent. Try again."));
		} finally {
			setBusy(null);
			setConfirming(false);
		}
	};

	if (created) {
		const name = created.deployment.name;

		return (
			<Card>
				<SectionTitle>{created.deployment.title || name}</SectionTitle>
				<SendingOutcome result={created.sending} />
				<div className="mt-5 flex flex-wrap gap-2">
					<ButtonLink to={`/admin/deployments/${encodeURIComponent(name)}`}>Open the deployment</ButtonLink>
					<Button variant="quiet" onClick={onAnother}>
						Set up another
					</Button>
				</div>
			</Card>
		);
	}

	if (setupCall.isLoading) return <Spinner label="Loading…" />;
	if (setupCall.error) return <ErrorNote>{errorMessage(setupCall.error)}</ErrorNote>;

	if (counties && counties.length === 0) {
		return (
			<Card>
				<SectionTitle>You cannot set up a deployment</SectionTitle>
				<p className="mt-1.5 text-[12.5px] text-muted">
					Deployments are set up by the County Coordinator of the county. If you coordinate a county, ask
					an administrator to assign you to it.
				</p>
			</Card>
		);
	}

	const count = selection.count;
	const held = gaps.length > 0;
	const deploymentLink = saved ? `/admin/deployments/${encodeURIComponent(saved.name)}` : "";

	return (
		<div className="space-y-5">
			{saved && (
				<p className="rounded-xl bg-success-soft px-4 py-3 text-[12.5px] font-semibold text-success" role="status">
					Saved. To change the details, open the{" "}
					<Link to={deploymentLink} className="underline underline-offset-2">
						deployment
					</Link>
					.
				</p>
			)}

			{/* Locked once saved: from here the deployment's own page edits it. */}
			<fieldset disabled={Boolean(saved)} className="min-w-0 space-y-5">
			{/* -------------------------------------------------------- details */}
			<Section title="Details">
				{/* The terms first: choosing them fills in the dates below. */}
				{!geoNode ? (
					<p className="text-[12.5px] text-muted">
						The terms depend on the county.{" "}
						<button
							type="button"
							className="font-semibold text-blue hover:text-blue-hover"
							onClick={() => pointAt(ID.county)}
						>
							Choose the county
						</button>{" "}
						under Location first.
					</p>
				) : available.isLoading ? (
					<Spinner label="Loading terms of reference…" />
				) : offered.length === 0 && !canAttach ? (
					<div className="rounded-lg border border-dashed border-card-line px-4 py-6 text-center">
						<p className="text-[13px] font-semibold text-ink">No submitted terms of reference for this county</p>
						<p className="mx-auto mt-1.5 max-w-[52ch] text-[12.5px] leading-relaxed text-muted">
							A deployment needs submitted terms of reference. Write and submit the terms first.
						</p>
						<div className="mt-4 flex flex-wrap items-center justify-center gap-2">
							{canCreate("terms") && (
								<ButtonLink to="/admin/deployments/terms?new=1">Write terms of reference</ButtonLink>
							)}
							<ButtonLink to="/admin/deployments/terms" variant="quiet">
								See all terms
							</ButtonLink>
						</div>
					</div>
				) : (
					<>
					<div className="grid gap-4 sm:grid-cols-2">
						<Labelled label="Project" required hint="Choosing one narrows the terms of reference to it.">
							<select
								id={ID.project}
								className={INPUT}
								aria-required="true"
								value={project}
								onChange={(event) => chooseProject(event.target.value)}
							>
								<option value="">Select…</option>
								{projects.map((row) => (
									<option key={row.name} value={row.name}>
										{row.label}
									</option>
								))}
							</select>
						</Labelled>
						{byAttachment ? (
							<TorAttachment file={torFile} onFile={setTorFile} />
						) : (
						<Labelled
							label="Terms of reference"
							required
							hint="Fills in the project and the expected dates, unless you typed the dates."
						>
							<select
								id={ID.terms}
								className={INPUT}
								aria-required="true"
								value={terms}
								onChange={(event) => chooseTerms(event.target.value)}
							>
								<option value="">Select…</option>
								{shownTerms.map((row) => (
									<option key={row.name} value={row.name}>
										{!project && row.project_name ? `${row.project_name} — ${row.tor_name}` : row.tor_name}
									</option>
								))}
							</select>
						</Labelled>
						)}
					</div>
					{mustAttach ? (
						<p className="mt-2 text-[12px] text-muted">
							There are no terms of reference in the system for this county, so attach the TOR.
						</p>
					) : (
						canAttach && (
							<div className="mt-3">
								<Tick
									checked={attaching}
									onChange={(on) => {
										setAttaching(on);
										if (on) setTerms("");
									}}
									label="The TOR is not in the system"
									hint="Attach the TOR document instead. It is kept as the record of these terms."
								/>
							</div>
						)
					)}
					</>
				)}

				<div className="mt-4 grid gap-4 sm:grid-cols-2">
					<Labelled label="Title" required hint="No other open deployment may have the same title.">
						<input
							id={ID.title}
							className={INPUT}
							aria-required="true"
							value={title}
							onChange={(event) => setTitle(event.target.value)}
						/>
					</Labelled>
					<div className="grid grid-cols-2 gap-3">
						<Labelled label="Expected start date" required hint={timeZone}>
							<input
								id={ID.start}
								type="date"
								className={INPUT}
								aria-required="true"
								value={startDate}
								onChange={(event) => setStartDate(event.target.value)}
							/>
						</Labelled>
						<Labelled label="Expected end date" required hint={timeZone}>
							<input
								id={ID.end}
								type="date"
								className={INPUT}
								aria-required="true"
								value={endDate}
								onChange={(event) => setEndDate(event.target.value)}
							/>
						</Labelled>
					</div>
				</div>
				<div className="mt-4 grid gap-4 sm:grid-cols-[220px_1fr]">
					<Labelled label="Number of volunteers required">
						<input
							type="number"
							min="0"
							className={INPUT}
							value={required}
							onChange={(event) => setRequired(event.target.value)}
						/>
					</Labelled>
					<Labelled label="Notes">
						<textarea
							className={cx(INPUT, "min-h-[44px] resize-y")}
							value={notes}
							onChange={(event) => setNotes(event.target.value)}
						/>
					</Labelled>
				</div>
			</Section>

			{/* ------------------------------------------------------- location */}
			<Section title="Location">
				{counties ? (
					counties.length === 1 ? (
						<div id={ID.county}>
							<p className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">County</p>
							<p className="mt-1 text-[14px] font-semibold text-ink">{counties[0].place_name}</p>
						</div>
					) : (
						<div className="sm:max-w-[50%]">
							<Labelled label="County" required>
								<select
									id={ID.county}
									className={INPUT}
									aria-required="true"
									value={countyName}
									onChange={(event) => {
										setCountyName(event.target.value);
										setProject("");
										setTerms("");
										setSitePin(null);
										setMeetingPin(null);
									}}
								>
									<option value="">Select…</option>
									{counties.map((row) => (
										<option key={row.name} value={row.name}>
											{row.place_name}
										</option>
									))}
								</select>
							</Labelled>
						</div>
					)
				) : (
					<div id={ID.county}>
						<GeoSelects scoped chain={chain} onChain={setChain} idPrefix="deployment" />
					</div>
				)}

				<div className="mt-4 grid gap-4 sm:grid-cols-2">
					<Labelled label="Site name" hint="Where the volunteers will work.">
						<input className={INPUT} value={siteName} onChange={(event) => setSiteName(event.target.value)} />
					</Labelled>
					<Labelled label="Address">
						<input
							className={INPUT}
							value={siteAddress}
							onChange={(event) => setSiteAddress(event.target.value)}
						/>
					</Labelled>
				</div>

				<PinCard value={sitePin} onChange={setSitePin} center={county?.point ?? null} label="the site" />

				<div className="mt-5 border-t border-card-line pt-4">
					<p className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">Meeting point</p>
					{office && (
						<label className="mt-2 flex cursor-pointer items-start gap-2.5">
							<input
								type="checkbox"
								className="mt-0.5 h-4 w-4 flex-none accent-navy"
								checked={atOffice}
								onChange={(event) => setAtOffice(event.target.checked)}
							/>
							<span className="text-[13px] text-ink">
								{office.location_name}
								{office.address && <span className="block text-[12px] text-muted">{office.address}</span>}
							</span>
						</label>
					)}
					{!meetsAtOffice && (
						<div className="mt-3 grid gap-4 sm:grid-cols-2">
							<Labelled label="Meeting point" hint="Where the volunteers gather before setting off.">
								<input
									className={INPUT}
									value={meetingPoint}
									onChange={(event) => setMeetingPoint(event.target.value)}
								/>
							</Labelled>
							<Labelled label="Address">
								<input
									className={INPUT}
									value={meetingAddress}
									onChange={(event) => setMeetingAddress(event.target.value)}
								/>
							</Labelled>
						</div>
					)}
					{!meetsAtOffice && (
						<PinCard
							value={meetingPin}
							onChange={setMeetingPin}
							center={sitePin ?? county?.point ?? null}
							label="the meeting point"
						/>
					)}
				</div>

				<div className="mt-5 grid gap-4 border-t border-card-line pt-4 sm:grid-cols-2">
					<Labelled label="Local contact" hint="Who the volunteers ask for on arrival.">
						<input className={INPUT} value={contactName} onChange={(event) => setContactName(event.target.value)} />
					</Labelled>
					<Labelled label="Local contact phone">
						<input
							type="tel"
							className={INPUT}
							value={contactPhone}
							onChange={(event) => setContactPhone(event.target.value)}
						/>
					</Labelled>
				</div>
				<div className="mt-4">
					<Labelled label="Travel notes" hint="Transport, what to bring, how to get there.">
						<textarea
							className={cx(INPUT, "min-h-[64px] resize-y")}
							value={travelNotes}
							onChange={(event) => setTravelNotes(event.target.value)}
						/>
					</Labelled>
				</div>
			</Section>

			{/* -------------------------------------------------- notifications */}
			<Section title="Notifications">
				<p className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">Notification channels</p>
				<div className="mt-2 flex flex-wrap gap-x-6 gap-y-2">
					<Tick checked={byEmail} onChange={setByEmail} label="Email" />
					{SMS_READY && <Tick checked={bySms} onChange={setBySms} label="SMS" />}
				</div>
				<p className="mt-1.5 text-[11.5px] text-slate-faint">A system notification will also be sent to the volunteer.</p>

				{byEmail && (
					<div className="mt-4 sm:max-w-[50%]">
						<Labelled label="Email template">
							<select
								className={INPUT}
								value={emailTemplate}
								onChange={(event) => setEmailTemplate(event.target.value)}
							>
								<option value="">Standard email</option>
								{(options.data?.message?.email_templates ?? []).map((template) => (
									<option key={template.name} value={template.name}>
										{template.name}
									</option>
								))}
							</select>
						</Labelled>
					</div>
				)}

				<div className="mt-4 space-y-3">
					<Tick
						checked={future}
						onChange={setFuture}
						label="Future deployment"
						hint="Send the requests to volunteers on a later date."
					/>
					{future && (
						<div className="pl-[26px] sm:max-w-[50%]">
							<Labelled label="Future deployment date" required hint={timeZone}>
								<input
									id={ID.sendOn}
									type="datetime-local"
									className={INPUT}
									aria-required="true"
									value={sendOn}
									onChange={(event) => setSendOn(event.target.value)}
								/>
							</Labelled>
						</div>
					)}
					<Tick
						checked={requiresContract}
						onChange={setRequiresContract}
						label="Require contract before deployment"
						hint="Not yet in use."
					/>
				</div>
			</Section>

			</fieldset>

			{/* ---------------------------------------------- select volunteers */}
			<Section
				title="Select volunteers"
				lead="Choose the filters, then find. You can also add volunteers after the deployment is created."
			>
				<div id={ID.volunteers}>
				<VolunteerFinder
					terms={terms || null}
					geoNode={geoNode}
					startDate={startDate || null}
					endDate={endDate || null}
					onNeeds={setNeeds}
					professions={options.data?.message?.professions ?? setup?.professions ?? []}
					held={searchGap ? { note: searchGap.note, point: () => pointAt(searchGap.anchor) } : null}
					onSelection={setSelection}
				/>
				</div>
			</Section>

			{/* ---------------------------------------------------------- press */}
			<div className="sticky bottom-0 z-10 -mx-1 flex flex-wrap items-center gap-2 rounded-xl border border-card-line bg-white/95 px-4 py-3 backdrop-blur">
				{saved ? (
					<>
						<Button held={count === 0} busy={busy === "send"} disabled={busy !== null} onClick={submit}>
							Submit and send request
						</Button>
						<ButtonLink to={deploymentLink} variant="quiet">
							Open the deployment
						</ButtonLink>
						<span className="text-[12px] text-slate-faint">
							{count === 1 ? "1 volunteer selected" : `${count.toLocaleString()} volunteers selected`}
						</span>
					</>
				) : (
					<Button held={held} busy={busy === "save"} disabled={busy !== null} onClick={() => void save()}>
						Save deployment
					</Button>
				)}
				{gapNote && (held || (saved && count === 0)) && (
					<p className="text-[12px] font-semibold text-signal">{gapNote}</p>
				)}
				{failure && (
					<div className="w-full">
						<ErrorNote>{failure}</ErrorNote>
					</div>
				)}
			</div>

			{saved && (
				<SendRequestDialog
					open={confirming}
					selection={selection}
					sendOn={saved.sending?.send_on ?? null}
					busy={busy === "send"}
					onSubmit={() => void send()}
					onCancel={() => setConfirming(false)}
				/>
			)}
		</div>
	);
}

function Section({ title, lead, children }: { title: string; lead?: string; children: ReactNode }) {
	return (
		<Card>
			<SectionTitle>{title}</SectionTitle>
			{lead && <p className="mt-1 text-[12px] text-slate-faint">{lead}</p>}
			<div className="mt-4">{children}</div>
		</Card>
	);
}

/**
 * The TOR as a file, for terms written outside the system: a PDF, a Word
 * document or a scan. Uploaded when the deployment is created, never before,
 * so a page abandoned half way leaves nothing behind.
 */
function TorAttachment({ file, onFile }: { file: File | null; onFile: (file: File | null) => void }) {
	return (
		<div>
			<span className="mb-1.5 block text-[10px] font-bold uppercase tracking-wider text-slate-faint">
				TOR attachment
				<span className="ml-1 text-danger" aria-hidden="true">
					*
				</span>
			</span>
			<div className="flex min-h-[42px] flex-wrap items-center gap-3">
				<label className="inline-flex cursor-pointer items-center rounded-lg border border-card-line bg-white px-3.5 py-2 text-[12.5px] font-semibold text-ink transition hover:border-navy focus-within:ring-2 focus-within:ring-navy/30">
					{file ? "Choose another file" : "Choose file"}
					<input
						id={ID.attachment}
						type="file"
						className="sr-only"
						aria-label="TOR attachment"
						aria-required="true"
						accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
						onChange={(event) => {
							const chosen = event.target.files?.[0];
							if (chosen) onFile(chosen);
							event.currentTarget.value = "";
						}}
					/>
				</label>
				{file && (
					<span className="flex min-w-0 items-center gap-2 text-[12.5px] text-ink">
						<span className="truncate">{file.name}</span>
						<button
							type="button"
							className="text-[12px] font-semibold text-slate-faint hover:text-ink"
							onClick={() => onFile(null)}
						>
							Remove
						</button>
					</span>
				)}
			</div>
			<span className="mt-1 block text-[11.5px] text-slate-faint">A PDF, a Word document or a scan.</span>
		</div>
	);
}

function Tick({
	checked,
	onChange,
	label,
	hint,
}: {
	checked: boolean;
	onChange: (value: boolean) => void;
	label: string;
	hint?: string;
}) {
	return (
		<label className="flex cursor-pointer items-start gap-2.5">
			<input
				type="checkbox"
				className="mt-0.5 h-4 w-4 flex-none accent-navy"
				checked={checked}
				onChange={(event) => onChange(event.target.checked)}
			/>
			<span className="text-[13px] text-ink">
				{label}
				{hint && <span className="block text-[11.5px] text-slate-faint">{hint}</span>}
			</span>
		</label>
	);
}

/**
 * A map pin for the site or the meeting point: optional, and three free ways to set it.
 *
 * Search for the place (when this site has a place search switched on), click
 * the map, or paste what Google Maps in the browser gives — the coordinates
 * from right-clicking the spot, the page's address, or a phone's share link.
 */
function PinCard({
	value,
	onChange,
	center,
	label,
}: {
	value: MapPoint | null;
	onChange: (point: MapPoint | null) => void;
	/** Where the map opens without a pin: the site's pin for the meeting point, else the county. */
	center: MapPoint | null;
	/** What is pinned, for the map's accessible name and the buttons: "the site". */
	label: string;
}) {
	const [open, setOpen] = useState(false);

	return (
		<div className="mt-4 rounded-xl border border-card-line px-3.5 py-3">
			<div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
				<div className="min-w-0">
					<p className="text-[12.5px] font-semibold text-ink">Map pin</p>
					<p className="mt-0.5 text-[11.5px] text-muted">
						{value ? `${value.latitude}, ${value.longitude}` : "Shown to volunteers with directions."}
					</p>
				</div>
				<div className="flex flex-wrap items-center gap-2">
					{value && (
						<>
							<a
								href={googleMapsUrl(`${value.latitude},${value.longitude}`)}
								target="_blank"
								rel="noreferrer"
								className="text-[11.5px] font-semibold text-blue hover:text-blue-hover"
							>
								Open ↗
							</a>
							<Button variant="quiet" onClick={() => onChange(null)}>
								Remove
							</Button>
						</>
					)}
					<Button variant="quiet" label={open ? `Close the map for ${label}` : value ? `Move the pin for ${label}` : `Add a pin for ${label}`} onClick={() => setOpen((was) => !was)}>
						{open ? "Close" : value ? "Move the pin" : "Add a pin"}
					</Button>
				</div>
			</div>

			{open && (
				<div className="mt-3">
					<PinTools value={value} center={center} label={label} onPick={(point) => onChange(point)} />
				</div>
			)}
		</div>
	);
}
