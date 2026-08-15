import { useContext, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage } from "../lib/api";
import { formatDate, geoPath } from "../lib/format";
import { initials } from "../lib/session";
import { Field, SelectInput, TextInput, VocabularySelect } from "../ui/form";
import { Icon } from "../ui/icons";
import {
	Button,
	Card,
	Empty,
	ErrorNote,
	List,
	ListRow,
	PageHeading,
	Pill,
	SectionTitle,
	Spinner,
	StateBadge,
} from "../ui/primitives";
import type {
	ApplicationOptions,
	IdentityOptions,
	MyCertifications,
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
 */
export default function Profile() {
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

	const profile = volunteer.data?.message ?? null;
	const certs = training.data?.message?.certifications ?? [];

	return (
		<>
			<PageHeading
				title={<EditableText k="portal.profile.heading" fallback="Profile" />}
				trail={[{ label: "Home", to: "/dashboard" }, { label: "Profile" }]}
				meta={profile?.geo_path ? geoPath(profile.geo_path) : undefined}
			/>

			{volunteer.isLoading && <Spinner label="Loading your profile…" />}
			{volunteer.error && <ErrorNote>{errorMessage(volunteer.error)}</ErrorNote>}

			{!volunteer.isLoading && !profile && (
				<Empty title="You have no volunteer record" icon={Icon.people}>
					Your profile appears here once your branch has verified your application.
				</Empty>
			)}

			{profile && (
				<div className="grid items-start gap-6 lg:grid-cols-3">
					<div className="lg:col-span-1">
						<IdentityCard
							profile={profile}
							person={person.data?.message ?? null}
							onSaved={() => {
								void person.mutate();
								void volunteer.mutate();
							}}
						/>
					</div>
					<div className="space-y-6 lg:col-span-2">
						<HolderCard kind="volunteer" />
						<PlacementCard profile={profile} />
						<CertificationsCard rows={certs} loading={training.isLoading} />
					</div>
				</div>
			)}
		</>
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
export function HolderCard({ kind }: { kind: "volunteer" | "member" }) {
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
				<SectionTitle>Your card</SectionTitle>
				<a
					className="text-[12px] font-semibold text-navy underline underline-offset-2"
					href={`/api/method/vmmsx.api.cards.download_my_card?kind=${kind}`}
				>
					Download PDF
				</a>
			</div>

			<div dangerouslySetInnerHTML={{ __html: card.html }} />

			<p className="mt-4 text-[11.5px] leading-relaxed text-slate-faint">
				The code on your card can be scanned by anybody who needs to check it. They see your name,
				your branch and whether it is current, and nothing else.
			</p>
		</Card>
	);
}

function IdentityCard({
	profile,
	person,
	onSaved,
}: {
	profile: VolunteerProfile;
	person: RedProfile | null;
	onSaved: () => void;
}) {
	const [editing, setEditing] = useState(false);

	return (
		<Card>
			<div className="flex items-center gap-4">
				{profile.profile_photo ? (
					<img
						src={profile.profile_photo}
						alt=""
						className="h-16 w-16 flex-none rounded-full object-cover"
					/>
				) : (
					<div className="grid h-16 w-16 flex-none place-items-center rounded-full bg-navy font-display text-[19px] font-bold text-white">
						{initials(profile.full_name) || "?"}
					</div>
				)}
				<div className="min-w-0">
					<h2 className="truncate font-display text-[19px] font-extrabold tracking-tight text-ink">
						{profile.full_name ?? "—"}
					</h2>
					<div className="mt-1.5">
						<StateBadge state={profile.status} />
					</div>
					<PhotoControl current={profile.profile_photo} onSaved={onSaved} />
				</div>
			</div>

			{editing && person ? (
				<IdentityForm
					person={person}
					onCancel={() => setEditing(false)}
					onSaved={() => {
						setEditing(false);
						onSaved();
					}}
				/>
			) : (
				<>
					<dl className="mt-6 space-y-4 border-t border-hairline pt-5">
						<Line label="Email" value={profile.email} locked />
						<Line label="Phone" value={profile.phone} />
						<Line label="Gender" value={profile.gender} />
						<Line label="Date of birth" value={formatDate(profile.date_of_birth)} />
						<Line label="Preferred language" value={profile.preferred_language} />
					</dl>

					<div className="mt-5 border-t border-hairline pt-4">
						{person ? (
							<>
								<Button variant="quiet" onClick={() => setEditing(true)}>
									Correct these details
								</Button>
								<p className="mt-2.5 text-[11.5px] leading-relaxed text-slate-faint">
									These belong to your person record, which the Society holds once for everything
									you do with it. Your email address is your account and cannot be changed here.
								</p>
							</>
						) : (
							<p className="text-[11.5px] leading-relaxed text-slate-faint">
								Your name and contact details belong to your person record, which the Society
								holds once for everything you do with it.
							</p>
						)}
					</div>
				</>
			)}
		</Card>
	);
}

/**
 * The photograph, uploaded by the person it is of.
 *
 * **Two steps, and the second is the same endpoint the rest of this screen
 * uses.** The file goes through the framework's own `upload_file`, which has
 * already decided what this person may store and how large it may be — the same
 * handler `content/Editable.tsx` and the task proof use, rather than a second
 * uploader here. What comes back is a URL, and that URL is saved through
 * `update_my_profile` like any other correction. The server re-checks that it is
 * one of this site's own upload paths, so nothing here is the only thing
 * standing between an arbitrary URL and a printed card.
 *
 * **Public rather than private**, which is a deliberate difference from the task
 * proof. A private file is readable by its uploader alone unless it is anchored
 * to a document, and this one has to render on a coordinator's screen and inside
 * a PDF card handed to a steward. It is the same treatment Frappe gives its own
 * user image.
 *
 * Removing is offered beside replacing: a photograph is an optional field, and
 * `update_my_profile` clears one on an empty string. Somebody who would rather
 * not have their face on a card can take it off without asking anybody.
 */
function PhotoControl({ current, onSaved }: { current: string | null; onSaved: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const save = async (url: string) => {
		await call.post(API.updateMyProfile, { profile_photo: url });
		onSaved();
	};

	const upload = async (file: File) => {
		setBusy(true);
		setFailure(null);

		try {
			const body = new FormData();
			body.append("file", file);
			body.append("is_private", "0");

			const response = await fetch("/api/method/upload_file", {
				method: "POST",
				body,
				headers: { "X-Frappe-CSRF-Token": window.csrf_token ?? "" },
			});

			if (!response.ok) throw new Error("The upload was refused.");

			const payload = (await response.json()) as { message?: { file_url?: string } };
			const url = payload.message?.file_url;

			if (!url) throw new Error("The upload came back without a file.");

			await save(url);
		} catch (uploadError) {
			setFailure(errorMessage(uploadError, "That photograph could not be saved."));
		} finally {
			setBusy(false);
		}
	};

	const remove = async () => {
		setBusy(true);
		setFailure(null);

		try {
			// An empty string is how this endpoint clears an optional field. Not
			// `null`, which means "leave this alone".
			await save("");
		} catch (removeError) {
			setFailure(errorMessage(removeError, "That photograph could not be removed."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div className="mt-2">
			<div className="flex flex-wrap items-center gap-3">
				<label className="inline-flex cursor-pointer items-center text-[12px] font-semibold text-navy hover:underline">
					{busy ? "Saving…" : current ? "Replace photo" : "Add a photo"}
					<input
						type="file"
						accept="image/*"
						className="hidden"
						disabled={busy}
						onChange={(event) => {
							const file = event.target.files?.[0];

							// Cleared so choosing the same file twice fires again, which
							// it otherwise would not after a failure.
							event.target.value = "";

							if (file) void upload(file);
						}}
					/>
				</label>

				{current && !busy && (
					<button
						type="button"
						onClick={() => void remove()}
						className="text-[12px] font-semibold text-slate-faint hover:text-navy hover:underline"
					>
						Remove
					</button>
				)}
			</div>

			{/* Said here because it is not obvious that this is the picture a
			    steward at a gate will be comparing with a face. */}
			<p className="mt-1 text-[11px] text-slate-faint">
				This is the photograph printed on your card.
			</p>

			{failure && (
				<div className="mt-2">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}
		</div>
	);
}

/**
 * The correction form. Five fields and no email.
 *
 * The vocabularies are fetched only once somebody opens this, because a person
 * reading their own profile is the common case and neither list is worth a
 * round trip for it. `preferred_language` reuses the volunteer application's
 * language list rather than a second endpoint: it is the same Language rows,
 * and a second answer to "what languages exist" would eventually disagree.
 */
function IdentityForm({
	person,
	onCancel,
	onSaved,
}: {
	person: RedProfile;
	onCancel: () => void;
	onSaved: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [firstName, setFirstName] = useState(person.first_name ?? "");
	const [lastName, setLastName] = useState(person.last_name ?? "");
	const [phone, setPhone] = useState(person.phone ?? "");
	const [gender, setGender] = useState(person.gender ?? "");
	const [dateOfBirth, setDateOfBirth] = useState(person.date_of_birth ?? "");
	const [language, setLanguage] = useState(person.preferred_language ?? "");

	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const identity = useFrappeGetCall<{ message: IdentityOptions }>(
		API.identityOptions,
		undefined,
		"profile:identity_options",
	);
	const vocabularies = useFrappeGetCall<{ message: ApplicationOptions }>(
		API.applicationOptions,
		undefined,
		"profile:application_options",
	);

	const save = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.updateMyProfile, {
				first_name: firstName.trim(),
				last_name: lastName.trim(),
				phone: phone.trim(),
				gender,
				date_of_birth: dateOfBirth,
				preferred_language: language,
			});
			onSaved();
		} catch (saveError) {
			setFailure(errorMessage(saveError, "That change was not accepted."));
		} finally {
			setBusy(false);
		}
	};

	const named = Boolean(firstName.trim() && lastName.trim());

	return (
		<div className="mt-6 space-y-4 border-t border-hairline pt-5">
			{failure && <ErrorNote>{failure}</ErrorNote>}

			<Field label="First name" required htmlFor="profile-first">
				<TextInput id="profile-first" value={firstName} onChange={setFirstName} />
			</Field>

			<Field label="Last name" required htmlFor="profile-last">
				<TextInput id="profile-last" value={lastName} onChange={setLastName} />
			</Field>

			<Field label="Phone" htmlFor="profile-phone">
				<TextInput
					id="profile-phone"
					type="tel"
					inputMode="tel"
					value={phone}
					onChange={setPhone}
				/>
			</Field>

			<Field label="Gender" htmlFor="profile-gender">
				<SelectInput
					id="profile-gender"
					value={gender}
					options={identity.data?.message?.genders ?? []}
					onChange={setGender}
					placeholder="Prefer not to say"
				/>
			</Field>

			<Field label="Date of birth" htmlFor="profile-dob">
				<TextInput
					id="profile-dob"
					type="date"
					max={new Date().toISOString().slice(0, 10)}
					value={dateOfBirth}
					onChange={setDateOfBirth}
				/>
			</Field>

			<Field
				label="Preferred language"
				htmlFor="profile-language"
				hint="The language you would rather be contacted in."
			>
				<VocabularySelect
					id="profile-language"
					value={language}
					options={vocabularies.data?.message?.languages ?? []}
					onChange={setLanguage}
					placeholder="No preference"
				/>
			</Field>

			<div className="flex items-center gap-2.5 pt-1">
				<Button variant="navy" onClick={save} disabled={!named || busy}>
					{busy ? "Saving…" : "Save"}
				</Button>
				<Button variant="ghost" onClick={onCancel} disabled={busy}>
					Cancel
				</Button>
			</div>
		</div>
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
				<span className="min-w-0 truncate">{value || "—"}</span>
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
			<dd className="mt-1.5 text-[13.5px] text-ink">{value || "—"}</dd>
		</div>
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
										? "grid h-9 w-9 flex-none place-items-center rounded-control bg-signal/[.08] text-signal-dark"
										: "grid h-9 w-9 flex-none place-items-center rounded-control bg-tint-teal-soft text-tint-teal"
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
									<span className="inline-flex items-center gap-1.5 rounded-full border border-signal/40 bg-signal/[.06] px-2.5 py-1 text-[11px] font-bold text-signal-dark">
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
