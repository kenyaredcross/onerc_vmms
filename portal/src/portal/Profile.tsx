import { useContext, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { ServiceCertificatePanel } from "../certificates/ServiceCertificates";
import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, geoPath } from "../lib/format";
import {
	BackgroundFields,
	backgroundDateGaps,
	profileLinkGaps,
	type ProfileLinks,
	backgroundFrom,
	backgroundLines,
	backgroundPayload,
	emptyBackground,
	type BackgroundValues,
} from "../ui/Background";
import { Icon } from "../ui/icons";
import { PersonHero } from "../ui/PersonHero";
import { TransferCard } from "./TransferCard";
import { PersonalTab, type SectionKey } from "./ProfileSections";
import {
	Button,
	ButtonLink,
	Card,
	Empty,
	ErrorNote,
	List,
	ListRow,
	PageHeading,
	Pill,
	SectionTitle,
	Spinner,
} from "../ui/primitives";
import type {
	IdentityOptions,
	MembershipRow,
	MyCertifications,
	OpenRegistration,
	ProfileCompleteness,
	RedProfile,
	VolunteerProfile,
} from "./types";

/**
 * The volunteer's own record, and the one part of it they may correct.
 *
 * The distinction the screen draws is the one this app draws everywhere.
 * **Identity is theirs**: name, phone, gender, date of birth and the language
 * they would rather be contacted in live on core's Red Profile, they are facts
 * about the person rather than about any affiliation, and they are edited here
 * through `registration.update_my_profile` — the endpoint named for correcting
 * exactly this. The email is not among them, because it is the login.
 *
 * **The volunteer record is the society's.** Serving branch, joined date,
 * status and certifications are what the branch decided about this person, and
 * a text field over any of them would be a self-service route around an
 * approval. Those stay read-only, and that is not an unfinished screen.
 *
 * **It opens with the same header a coordinator sees.** `PersonHero` is the
 * block the volunteer record, the member record and the review queue all lead
 * with, and this page leads with it too: a volunteer looking at their own
 * profile and a coordinator looking at the same person are looking at the same
 * thing, which is the whole reason to have one component rather than four
 * headers that drifted apart. What this screen adds to it is the person's own:
 * a ring round the photograph showing how complete the profile is, and a pill
 * that takes them to the first thing missing.
 *
 * **Corrected one section at a time**, on the Personal tab — see
 * `ProfileSections.tsx`. "Complete" is the registration's own list, read from
 * `my_profile_completeness`, so the nudge and the submission rules agree.
 */
export default function Profile() {
	const [params, setParams] = useSearchParams();
	const tab = (TABS.some(([key]) => key === params.get("tab")) ? params.get("tab") : "overview") as TabKey;
	const edit = params.get("edit");
	const focus = edit && edit !== "background" ? (edit as SectionKey) : null;
	const go = (next: TabKey, edit?: string) =>
		setParams(
			(current) => {
				const after = new URLSearchParams(current);
				after.set("tab", next);
				if (edit) after.set("edit", edit);
				else after.delete("edit");
				return after;
			},
			{ replace: true },
		);

	const volunteer = useFrappeGetCall<{ message: VolunteerProfile | null }>(
		API.myVolunteer,
		undefined,
		"portal:my_volunteer",
	);
	const training = useFrappeGetCall<{ message: MyCertifications | null }>(
		API.myCertifications,
		undefined,
		"portal:my_certifications",
	);
	// The spine itself, because `my_volunteer` returns a composed full name and
	// an edit form needs the two halves it was composed from.
	const person = useFrappeGetCall<{ message: RedProfile | null }>(
		API.myProfile,
		undefined,
		"portal:my_profile",
	);
	// How complete the profile is, and what is missing — the registration's own
	// list, asked of the server so the two can never disagree.
	const completion = useFrappeGetCall<{ message: ProfileCompleteness | null }>(
		API.myProfileCompleteness,
		undefined,
		"portal:my_profile_completeness",
	);

	// Whether this person is also a member, asked of their own memberships
	// endpoint rather than of the cross-register lookup the admin screens use:
	// that one reads the registers through core's scoping, and a volunteer has
	// no scope over the member register — not even their own row.
	const memberships = useFrappeGetCall<{ message: MembershipRow[] }>(
		API.myMemberships,
		undefined,
		"portal:my_memberships",
	);

	// Whether an application of theirs is already with the branch, and whether it
	// has been sent. Without it this screen read "no volunteer record" as "never
	// applied" for everybody. Same key the dashboard uses.
	const open = useFrappeGetCall<{ message: Record<string, OpenRegistration | null> }>(
		API.myOpenRegistrations,
		undefined,
		"portal:open_registrations",
	);

	const profile = volunteer.data?.message ?? null;
	const certs = training.data?.message?.certifications ?? [];
	const held = (memberships.data?.message ?? []).find((row) => row.is_active);
	const application = open.data?.message?.volunteer ?? null;
	const completeness = completion.data?.message ?? null;
	const nextMissing = completeness?.items.find((item) => !item.done) ?? null;

	const refresh = () => {
		void person.mutate();
		void volunteer.mutate();
		void completion.mutate();
	};
	const fix = (item: { section: string }) =>
		item.section === "background" ? go("background", "background") : go("personal", item.section);

	return (
		<>
			<PageHeading
				title={<EditableText k="portal.profile.heading" fallback="Profile" />}
				trail={[{ label: "Home", to: "/dashboard" }, { label: "Profile" }]}
			/>

			{/* The application is waited for as well as the record. This page has
			    three different things to say to somebody with no profile, and two
			    of them are wrong for the other two people — so it says none of them
			    until it knows which person is reading. */}
			{(volunteer.isLoading || open.isLoading) && <Spinner label="Loading your profile…" />}
			{volunteer.error && <ErrorNote>{errorMessage(volunteer.error)}</ErrorNote>}

			{!volunteer.isLoading && !open.isLoading && !profile && (
				<NoRecordYet application={application} />
			)}

			{profile && (
				<PersonHero
					name={profile.full_name}
					photo={profile.profile_photo}
					docname={profile.volunteer}
					subtitle={geoPath(profile.geo_path) || undefined}
					status={profile.status}
					completion={completeness?.percent}
					onCompletion={nextMissing ? () => fix(nextMissing) : undefined}
					badges={
						// Drawn only when they actually hold a current membership: "not a
						// member" is not news to the person reading their own profile.
						held && (
							<Link
								to="/membership"
								className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[11.5px] font-bold text-white transition hover:border-white/40 hover:bg-white/15"
							>
								Also a member
								{held.membership_type_name && (
									<span className="font-semibold text-white/65">
										· {held.membership_type_name}
									</span>
								)}
							</Link>
						)
					}
					facts={[
						{ label: "Email", value: profile.email },
						{ label: "Phone", value: profile.phone },
						{ label: "Joined", value: formatDate(profile.joined_on) },
						{ label: "Home area", value: geoPath(profile.home_geo_path) },
					]}
				/>
			)}

			{profile && (
				<>
					<div className="mb-5 overflow-x-auto border-b border-card-line" role="tablist" aria-label="Profile">
						<div className="flex min-w-max gap-1">
							{TABS.filter(([key]) => key !== "card" || profile.issues_card !== false).map(([key, label]) => (
								<button
									key={key}
									type="button"
									role="tab"
									id={`profile-tab-${key}`}
									aria-selected={tab === key}
									aria-controls="profile-panel"
									onClick={() => go(key)}
									className={`-mb-px border-b-2 px-4 py-2.5 text-[12.5px] font-bold transition ${
										tab === key
											? "border-ink text-ink"
											: "border-transparent text-muted hover:text-ink"
									}`}
								>
									{label}
								</button>
							))}
						</div>
					</div>

					<div id="profile-panel" role="tabpanel" aria-labelledby={`profile-tab-${tab}`}>
						{tab === "overview" && (
							<div className="grid items-start gap-6 lg:grid-cols-3">
								<div className="space-y-6 lg:col-span-2">
									<PlacementCard profile={profile} />
									<ContactCard profile={profile} onEdit={() => go("personal", "emergency")} />
								</div>
								<aside className="space-y-6">
									<CompletionCard completeness={completeness} onFix={fix} />
								</aside>
							</div>
						)}

						{tab === "personal" && (
							<PersonalTab
								profile={profile}
								person={person.data?.message ?? null}
								completeness={completeness}
								focus={focus}
								onSaved={refresh}
							/>
						)}

						{tab === "background" && (
							<BackgroundCard
								person={person.data?.message ?? null}
								openOnArrival={edit === "background"}
								onSaved={refresh}
							/>
						)}
						{tab === "certifications" && <CertificationsCard rows={certs} loading={training.isLoading} />}
						{tab === "requests" && (
							<div className="space-y-6">
								<TransferCard branch={profile.geo_node} active={profile.status === "Active"} />
								<ServiceCertificatePanel />
							</div>
						)}
						{tab === "card" && profile.issues_card !== false && <HolderCard kind="volunteer" />}
					</div>
				</>
			)}
		</>
	);
}

const TABS = [
	["overview", "Overview"],
	["personal", "Personal"],
	["background", "Education & experience"],
	["certifications", "Certifications"],
	["requests", "Requests"],
	// Only where the society issues cards (Kenya does not).
	["card", "Volunteer card"],
] as const;

type TabKey = (typeof TABS)[number][0];

/**
 * What is still missing, as things to press.
 *
 * Each row takes them to the one section that fixes it, opened, rather than to
 * a form holding every question: somebody with a phone number to add should not
 * have to find their ID scan first.
 */
function CompletionCard({
	completeness,
	onFix,
}: {
	completeness: ProfileCompleteness | null;
	onFix: (item: ProfileCompleteness["items"][number]) => void;
}) {
	if (!completeness) return null;

	const missing = completeness.items.filter((item) => !item.done);

	return (
		<Card>
			<SectionTitle>Profile completion</SectionTitle>
			<div className="flex items-baseline justify-between gap-3">
				<span className="tabular text-[22px] font-bold text-ink">{completeness.percent}%</span>
				<span className="text-[12px] text-muted">
					{completeness.done} of {completeness.total} done
				</span>
			</div>
			<div
				className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface"
				role="progressbar"
				aria-valuenow={completeness.percent}
				aria-valuemin={0}
				aria-valuemax={100}
				aria-label="Profile completion"
			>
				<span className="block h-full rounded-full bg-success" style={{ width: `${completeness.percent}%` }} />
			</div>

			{missing.length === 0 ? (
				<p className="mt-4 text-[12.5px] text-muted">Your profile is complete.</p>
			) : (
				<ul className="mt-4 divide-y divide-card-line border-t border-card-line">
					{missing.map((item) => (
						<li key={item.key}>
							<button
								type="button"
								onClick={() => onFix(item)}
								className="flex w-full items-center justify-between gap-3 py-2.5 text-left text-[12.5px] font-semibold text-ink transition hover:text-blue"
							>
								{item.label}
								<Icon.chevron size={13} className="-rotate-90 flex-none text-slate-faint" />
							</button>
						</li>
					))}
				</ul>
			)}
		</Card>
	);
}

function ContactCard({ profile, onEdit }: { profile: VolunteerProfile; onEdit: () => void }) {
	const contacts = profile.emergency_contacts ?? [];

	return (
		<Card>
			<div className="mb-4 flex items-center justify-between gap-3">
				<SectionTitle>Emergency contacts</SectionTitle>
				<button type="button" onClick={onEdit} className="text-[12px] font-semibold text-blue hover:underline">
					{contacts.length ? "Change" : "Add a contact"}
				</button>
			</div>
			{contacts.length ? (
				<ul className="space-y-3">
					{contacts.map((row, index) => (
						<li key={index} className="text-[13px] text-ink">
							<span className="font-semibold">{row.contact_name}</span>
							<span className="block text-[12px] text-muted">
								{row.relationship} · {row.primary_phone}
							</span>
						</li>
					))}
				</ul>
			) : (
				<p className="text-[12.5px] text-muted">No emergency contact added.</p>
			)}
		</Card>
	);
}

/**
 * What this page says to somebody who has no volunteer record.
 *
 * **"You have no volunteer record" was the whole of it**, under a sentence
 * promising the profile would appear once a branch had verified an application
 * — which is only true of somebody who has actually sent one. To everybody
 * else it was a dead end: a statement of fact with nothing to do about it, on
 * the page they went to precisely because they wanted to be a volunteer.
 *
 * Three people arrive here with nothing, and only one of them is waiting on a
 * branch:
 *
 * - **Nobody has applied.** The way forward is the registration, so it is a
 *   button and not a sentence.
 * - **A draft is open.** The answers are saved and the form will resume where
 *   they left it, which is worth saying — somebody who thinks their answers are
 *   gone starts again from the first screen.
 * - **It has been sent.** There is genuinely nothing for them to do, and a
 *   button inviting them to apply a second time would be an invitation the
 *   server refuses. So this one gets the sentence and no control.
 */
function NoRecordYet({ application }: { application: OpenRegistration | null }) {
	if (application?.state === "Draft") {
		// "Draft" is two opposite situations — nobody has sent it, or an approver
		// sent it back — and `reviewed` is the server's answer to which. Telling
		// somebody whose branch asked for a certificate that their form is simply
		// unfinished is the same mistake the dashboard's panel used to make.
		const returned = Boolean(application.reviewed);

		return (
			<Empty
				title={
					returned
						? "Your branch has asked for changes"
						: "Your volunteer registration is unfinished"
				}
				icon={Icon.people}
				action={<ButtonLink to="/join?path=volunteer">Continue your registration</ButtonLink>}
			>
				{returned
					? application.reason ||
						"Update your volunteer application and send it again."
					: "Everything you answered has been saved. Pick it up where you left it, and your profile appears here once your branch has accepted it."}
			</Empty>
		);
	}

	if (application) {
		return (
			<Empty title="Your application is with your branch" icon={Icon.people}>
				Your profile appears here once your application is approved.
			</Empty>
		);
	}

	return (
		<Empty
			title="You are not registered as a volunteer"
			icon={Icon.people}
			action={<ButtonLink to="/join?path=volunteer">Become a volunteer</ButtonLink>}
		>
			Volunteering is a separate record from your account. Register, and your profile appears here
			once your branch has accepted it.
		</Empty>
	);
}

/**
 * The card the holder carries, shown where they can find it.
 *
 * **The HTML is the server's and this component adds nothing to it.** The same
 * `VMMS Template` renders what is shown here, what is printed to PDF and what
 * is attached to the congratulations email, so the card in somebody's inbox and
 * the card on their screen cannot come to disagree. A society that rewrites the
 * template rewrites all three.
 *
 * `dangerouslySetInnerHTML` is doing exactly what its name warns about, so it
 * is worth saying what makes it safe here: this markup is a `VMMS Template`
 * body, which is authored on the desk by an administrator and rendered through
 * Frappe's sandbox against a context of plain strings. It is the same trust
 * boundary the membership certificate has always had. It is emphatically not
 * applicant-supplied text: nothing a registrant typed is rendered as markup
 * anywhere in this app.
 *
 * Absent is ordinary and silent. Somebody who is a volunteer but not a member
 * has no member card, and a panel saying so on their own profile would be the
 * software telling them something they know.
 */
export function HolderCard({
	kind,
	title = "Your card",
	note = true,
}: {
	kind: "volunteer" | "member";
	/**
	 * What to call it above the card. Two of these sit together on the home
	 * page, where "Your card" twice would say which of them is which to nobody.
	 */
	title?: string;
	/**
	 * The line explaining what a scan of the QR discloses. True where somebody
	 * has come looking for their card and has room to read about it; false where
	 * the card is one panel among several and the sentence is repeated furniture.
	 */
	note?: boolean;
}) {
	const { data, isLoading } = useFrappeGetCall<{ message: { html: string } | null }>(
		kind === "volunteer" ? API.myVolunteerCard : API.myMemberCard,
		undefined,
		`portal:card:${kind}`,
	);

	const card = data?.message;

	if (isLoading || !card) return null;

	return (
		<Card>
			<div className="mb-4 flex items-center justify-between gap-3">
				<SectionTitle>{title}</SectionTitle>
				<a
					className="text-[12px] font-semibold text-ink underline underline-offset-2"
					href={`/api/method/vmmsx.api.cards.download_my_card?kind=${kind}`}
				>
					Download PDF
				</a>
			</div>

			{/* `portal-wallet` is what the stylesheet's container query hangs on:
			    in a column too narrow for the card as it was drawn, the QR moves
			    under the details rather than squeezing them. */}
			<div className="portal-wallet" dangerouslySetInnerHTML={{ __html: card.html }} />

			{note && (
				<p className="mt-4 text-[11.5px] leading-relaxed text-slate-faint">
					Scanning the code shows only your name, branch and whether your membership is current.
				</p>
			)}
		</Card>
	);
}

function Line({
	label,
	value,
	locked,
}: {
	label: string;
	value: string | null | undefined;
	locked?: boolean;
}) {
	return (
		<div className="flex items-baseline justify-between gap-4">
			<dt className="text-[11px] font-bold uppercase tracking-wider text-slate-faint">{label}</dt>
			<dd className="flex min-w-0 items-baseline gap-1.5 text-right text-[13px] text-ink">
				{locked && value && (
					<span className="flex-none self-center text-slate-faint">
						<Icon.lock size={11} />
					</span>
				)}
				<span className="min-w-0 truncate">{value || "Not provided"}</span>
			</dd>
		</div>
	);
}

function PlacementCard({ profile }: { profile: VolunteerProfile }) {
	return (
		<Card>
			<SectionTitle>Placement</SectionTitle>
			<dl className="grid gap-5 sm:grid-cols-2">
				<Block label="Serving branch" value={geoPath(profile.geo_path)} />
				<Block label="Home area" value={geoPath(profile.home_geo_path)} />
				<Block label="Joined" value={formatDate(profile.joined_on)} />
				<Block label="Volunteer ID" value={profile.volunteer} />
			</dl>
		</Card>
	);
}

function Block({ label, value }: { label: string; value: string | null }) {
	return (
		<div>
			<dt className="text-[10px] font-bold uppercase tracking-wider text-slate-faint">{label}</dt>
			<dd className="mt-1.5 text-[13.5px] text-ink">{value || "Not provided"}</dd>
		</div>
	);
}

/**
 * What this person has already done, on the screen where they can correct it.
 *
 * **The gap this closes.** All seven of these are asked once, during
 * registration, and until now there was no second door: somebody who qualified
 * as a nurse in March had to ask a branch to add it, because the only screen
 * that had ever drawn the fields was a wizard they had already finished. They
 * are person-owned facts on core's Red Profile and `update_my_profile` has
 * always been willing to take them — what was missing was somewhere to say so.
 *
 * **The same component the registration draws.** `BackgroundFields` is shared
 * rather than reimplemented, so the two screens cannot drift: a field added to
 * education next year appears in both, and the "still studying clears the finish
 * year" rule is written once.
 *
 * **Read first, edit on request**, like the identity card above it. A profile
 * page is somewhere people mostly *look*, and six repeating-row editors drawn
 * open on arrival would make a page about who you are look like a form you had
 * left unfinished.
 */
function BackgroundCard({
	person,
	openOnArrival = false,
	onSaved,
}: {
	person: RedProfile | null;
	/** Sent here by the completion nudge: open the editor once the record is in. */
	openOnArrival?: boolean;
	onSaved: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [editing, setEditing] = useState(false);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const [draft, setDraft] = useState<BackgroundValues>(emptyBackground);
	const [links, setLinks] = useState<ProfileLinks>({ linkedin: "", github: "" });

	const identity = useFrappeGetCall<{ message: IdentityOptions }>(
		API.identityOptions,
		undefined,
		"profile:identity_options",
	);
	const options = identity.data?.message;

	// What the server holds, which is also what Cancel goes back to. Derived on
	// every render rather than kept in state: the card is re-rendered with a
	// fresh `person` after each save, and a copy in state would be the version
	// that stopped updating.
	const held = backgroundFrom(person);
	const lines = backgroundLines(options, held);

	const heldLinks: ProfileLinks = {
		linkedin: person?.personal_details?.linkedin ?? "",
		github: person?.personal_details?.github ?? "",
	};

	const start = () => {
		setDraft(held);
		setLinks(heldLinks);
		setFailure(null);
		setEditing(true);
	};

	const [opened, setOpened] = useState(false);
	useEffect(() => {
		if (!openOnArrival || opened || !person) return;
		setOpened(true);
		start();
		// `start` reads `person`, which is what this waits for.
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [openOnArrival, opened, person]);

	const save = async () => {
		const dateGap = [...profileLinkGaps(links), ...backgroundDateGaps(draft)][0];
		if (dateGap) {
			setFailure(`${dateGap.note}.`);
			document.getElementById(dateGap.anchor)?.focus();
			return;
		}

		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.updateMyProfile, {
				profession: draft.profession,
				other_profession: draft.other_profession,
				background: backgroundPayload(draft),
				// Only these two keys: the server leaves every other personal
				// detail as it is.
				personal_details: { linkedin: links.linkedin.trim() || null, github: links.github.trim() || null },
			});
			setEditing(false);
			onSaved();
		} catch (saveError) {
			setFailure(errorMessage(saveError, "That change was not accepted."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card>
			<SectionTitle>Education and experience</SectionTitle>

			{!person ? (
				<p className="mt-4 text-[12.5px] leading-relaxed text-slate-faint">
					This appears once the Society holds a person record for you.
				</p>
			) : editing ? (
				<div className="mt-5 border-t border-card-line pt-5">
					{failure && <ErrorNote>{failure}</ErrorNote>}

					<BackgroundFields
						options={options}
						profiles={links}
						onProfiles={(patch) => setLinks((current) => ({ ...current, ...patch }))}
						lead="All fields in this section are optional."
						value={draft}
						onChange={(patch) => setDraft((current) => ({ ...current, ...patch }))}
					/>

					<div className="flex items-center gap-2.5 pt-6">
						<Button variant="navy" onClick={save} disabled={busy}>
							{busy ? "Saving…" : "Save"}
						</Button>
						<Button variant="ghost" onClick={() => setEditing(false)} disabled={busy}>
							Cancel
						</Button>
					</div>
				</div>
			) : (
				<>
					{lines.length === 0 && !held.profession && !heldLinks.linkedin && !heldLinks.github ? (
						// Not an `Empty`, which reads as something having gone wrong.
						// Nobody was ever obliged to fill this in, so the absence is
						// an invitation rather than a gap.
						<p className="mt-4 text-[12.5px] leading-relaxed text-slate-faint">
							No education, training, work experience, or licences have been added.
						</p>
					) : (
						<dl className="mt-5 space-y-4 border-t border-card-line pt-5">
							<Line
								label="Profession"
								value={held.profession === "Other" ? held.other_profession || "Other" : held.profession}
							/>
							{heldLinks.linkedin && <Line label="LinkedIn profile" value={heldLinks.linkedin} />}
							{heldLinks.github && <Line label="GitHub profile" value={heldLinks.github} />}
							{lines.map((row, index) => (
								<Line key={index} label={row.label} value={row.value} />
							))}
						</dl>
					)}

					<div className="mt-5 border-t border-card-line pt-4">
						<Button variant="quiet" onClick={start}>
							{lines.length === 0 && !held.profession && !heldLinks.linkedin && !heldLinks.github ? "Add details" : "Update details"}
						</Button>
						<p className="mt-2.5 text-[11.5px] leading-relaxed text-slate-faint">
							Your branch will verify qualifications when required.
						</p>
					</div>
				</>
			)}
		</Card>
	);
}

function CertificationsCard({
	rows,
	loading,
}: {
	rows: MyCertifications["certifications"];
	loading: boolean;
}) {
	return (
		<Card>
			<SectionTitle>Certifications</SectionTitle>

			{loading && <Spinner label="Loading your certifications…" />}

			{!loading && rows.length === 0 && (
				<Empty framed={false} title="Nothing recorded yet" icon={Icon.award}>
					Certifications appear here when your branch records a course you have completed.
				</Empty>
			)}

			<List>
				{rows.map((row) => (
					<ListRow
						key={row.name}
						lead={
							<span
								className={
									row.lapsed
										? "grid h-9 w-9 flex-none place-items-center rounded-lg bg-blue/[.08] text-blue-press"
										: "grid h-9 w-9 flex-none place-items-center rounded-lg bg-tint-teal-soft text-tint-teal"
								}
								aria-hidden="true"
							>
								<Icon.award size={17} />
							</span>
						}
						title={row.certification_type_name || row.certification_type}
						meta={
							<>
								Completed {formatDate(row.completion_date)}
								{row.expiry_date && ` · expires ${formatDate(row.expiry_date)}`}
							</>
						}
						trailing={
							<>
								{row.blocks_deployment && <Pill tone="page">Required</Pill>}
								{row.lapsed ? (
									<span className="inline-flex items-center gap-1.5 rounded-full border border-blue/40 bg-blue/[.06] px-2.5 py-1 text-[11px] font-bold text-blue-press">
										<span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
										Lapsed
									</span>
								) : (
									<span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50/60 px-2.5 py-1 text-[11px] font-bold text-emerald-700">
										<span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" />
										Current
									</span>
								)}
							</>
						}
					/>
				))}
			</List>
		</Card>
	);
}
