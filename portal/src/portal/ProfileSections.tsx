import { useContext, useEffect, useState, type ReactNode } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { formatDate, geoPath } from "../lib/format";
import { Combo, Field, SelectInput, TextInput, VocabularySelect } from "../ui/form";
import { Icon } from "../ui/icons";
import { selectedNode } from "../ui/GeoSelects";
import { Avatar, Button, Card, ErrorNote, Spinner } from "../ui/primitives";
import { RegistrationDetails, RegistrationDetailsSummary } from "../ui/RegistrationDetails";
import {
	DisabilityQuestion,
	EmergencyContactsFields,
	IdentificationStep,
	blankContact,
	blankIdentification,
	contactIsUsable,
	identificationIsUsable,
	sentIdentification,
	type Identification,
} from "../ui/RegistrationParts";
import { ResidenceFields } from "../ui/ResidenceFields";
import type {
	ApplicationOptions,
	EmergencyContact,
	GeoNode,
	IdentityOptions,
	PersonalDetails,
	ProfileCompleteness,
	RedProfile,
	VolunteerProfile,
} from "./types";

/**
 * The person's own details, one section at a time.
 *
 * **Each section saves on its own.** This page used to have one "Correct these
 * details" form holding everything, which meant somebody who wanted to add a
 * phone number was handed every question the registration ever asked and could
 * not save the one they came for until the rest held together. Now a section
 * opens alone, sends only its own fields, and closes. `update_my_profile` has
 * always treated an omitted field as "leave this alone", so nothing else moves.
 *
 * **The sections are the profile completeness `section` keys.** The nudge on
 * the overview names a section, and this tab opens exactly that one.
 */
export type SectionKey =
	| "photo"
	| "details"
	| "identification"
	| "citizenship"
	| "residence"
	| "disability"
	| "other"
	| "documents"
	| "emergency";

export function PersonalTab({
	profile,
	person,
	completeness,
	focus,
	onSaved,
}: {
	profile: VolunteerProfile;
	person: RedProfile | null;
	completeness: ProfileCompleteness | null;
	/** A section somebody was sent to; opened on arrival. */
	focus: SectionKey | null;
	onSaved: () => void;
}) {
	const [editing, setEditing] = useState<SectionKey | null>(focus);

	useEffect(() => {
		if (!focus) return;
		setEditing(focus === "photo" ? null : focus);
		document.getElementById(`profile-section-${focus}`)?.scrollIntoView?.({ behavior: "smooth", block: "start" });
	}, [focus]);

	const identity = useFrappeGetCall<{ message: IdentityOptions }>(
		API.identityOptions,
		undefined,
		"profile:identity_options",
	);
	const application = useFrappeGetCall<{ message: ApplicationOptions }>(
		API.applicationOptions,
		undefined,
		"profile:application_options",
	);
	const identityOptions = identity.data?.message;
	const applicationOptions = application.data?.message;

	const missing = new Set(
		(completeness?.items ?? []).filter((item) => !item.done).map((item) => item.section),
	);

	if (!person) return <Spinner label="Loading your details…" />;

	const saved = () => {
		setEditing(null);
		onSaved();
	};

	const section = (key: SectionKey, title: string, view: ReactNode, editor: ReactNode, editable = true) => (
		<Section
			key={key}
			id={key}
			title={title}
			missing={missing.has(key)}
			editing={editing === key}
			onEdit={editable ? () => setEditing(key) : undefined}
			view={view}
			editor={editor}
		/>
	);

	const details = person.personal_details ?? {};
	const idLabel = (key: string) =>
		applicationOptions?.id_types.find((type) => type.key === key)?.label ?? key;

	return (
		<Card className="p-0">
			<div className="divide-y divide-card-line">
				{section(
					"photo",
					"Photo",
					<div className="flex items-center gap-4">
						<Avatar name={profile.full_name} photo={profile.profile_photo} size={56} ring />
						<PhotoControl current={profile.profile_photo} onSaved={onSaved} />
					</div>,
					null,
					false,
				)}

				{section(
					"details",
					"Your details",
					<dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
						<Pair label="First name" value={person.first_name} />
						<Pair label="Last name" value={person.last_name} />
						<Pair label="Email" value={person.email} locked />
						<Pair label="Phone number" value={person.phone} />
						<Pair label="Gender" value={person.gender} />
						<Pair label="Date of birth" value={formatDate(person.date_of_birth)} />
						<Pair label="Preferred language" value={person.preferred_language} />
					</dl>,
					<DetailsEditor
						person={person}
						genders={identityOptions?.genders ?? []}
						languages={applicationOptions?.languages ?? []}
						onCancel={() => setEditing(null)}
						onSaved={saved}
					/>,
				)}

				{section(
					"identification",
					"ID documents",
					person.identifications.length ? (
						<ul className="space-y-2 text-[13px] text-ink">
							{person.identifications.map((row, index) => (
								<li key={index}>
									<span className="font-semibold">{idLabel(row.id_type)}</span> · {row.id_number}
									{row.attachment && <span className="text-muted"> · Copy uploaded</span>}
								</li>
							))}
						</ul>
					) : (
						<Empty>No ID document added.</Empty>
					),
					<IdentificationEditor
						person={person}
						options={applicationOptions}
						loading={application.isLoading}
						onCancel={() => setEditing(null)}
						onSaved={saved}
					/>,
				)}

				{section(
					"citizenship",
					"Citizenship",
					<dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
						<Pair label="Country of citizenship" value={person.country_of_citizenship} />
						<Pair label="Citizenship status" value={person.citizenship_status} />
					</dl>,
					<CitizenshipEditor
						person={person}
						countries={applicationOptions?.countries ?? []}
						statuses={applicationOptions?.citizenship_statuses ?? []}
						onCancel={() => setEditing(null)}
						onSaved={saved}
					/>,
				)}

				{section(
					"residence",
					"Contact & Location",
					person.residency_type === "Abroad" ? (
						<dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
							<Pair label="Residence" value="Abroad" />
							<Pair label="Country of residence" value={person.country_of_residence} />
							<Pair label="Address abroad" value={person.residence_address} />
						</dl>
					) : (
						<dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
							<Pair label="Residence" value={person.residency_type} />
							<Pair label="Home area" value={geoPath(profile.home_geo_path)} />
							<Pair label="County" value={details.county} />
							<Pair label="Sub County" value={details.sub_county} />
							<Pair label="Ward" value={details.ward} />
							{details.administrative_location && <Pair label="Location" value={details.administrative_location} />}
							{details.sub_location && <Pair label="Sub Location" value={details.sub_location} />}
						</dl>
					),
					<ResidenceEditor
						person={person}
						profile={profile}
						onCancel={() => setEditing(null)}
						onSaved={saved}
					/>,
				)}

				{section(
					"disability",
					"Disability",
					<dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
						<Pair label="Person with disability" value={person.disability_status} />
						{person.disabilities.length > 0 && (
							<Pair
								label="Disability type"
								value={person.disabilities
									.map((key) => identityOptions?.disabilities.find((row) => row.key === key)?.label ?? key)
									.join(", ")}
							/>
						)}
						{person.disability_needs && <Pair label="Support that would help" value={person.disability_needs} />}
					</dl>,
					<DisabilityEditor
						person={person}
						options={identityOptions?.disabilities ?? []}
						onCancel={() => setEditing(null)}
						onSaved={saved}
					/>,
				)}

				{section(
					"other",
					"Other Details",
					<RegistrationDetailsSummary
						value={withoutResidenceOrDocuments(details)}
						showProfileLinks={false}
					/>,
					<DetailsBlockEditor
						person={person}
						bloodGroups={identityOptions?.blood_groups}
						onCancel={() => setEditing(null)}
						onSaved={saved}
					/>,
				)}

				{section(
					"documents",
					"Supporting documents",
					details.supporting_documents?.length ? (
						<ul className="space-y-2 text-[13px] text-ink">
							{details.supporting_documents.map((row, index) => (
								<li key={index}>
									<span className="font-semibold">{row.type || "Document"}</span>
									{row.document_name && <> · {row.document_name}</>}
									<span className="text-muted"> · {row.attachment ? "Uploaded" : "No file"}</span>
								</li>
							))}
						</ul>
					) : (
						<Empty>No supporting documents uploaded.</Empty>
					),
					<DocumentsEditor
						person={person}
						types={identityOptions?.supporting_document_types ?? []}
						onCancel={() => setEditing(null)}
						onSaved={saved}
					/>,
				)}

				{section(
					"emergency",
					"Emergency contacts",
					profile.emergency_contacts?.length ? (
						<ul className="space-y-2 text-[13px] text-ink">
							{profile.emergency_contacts.map((row, index) => (
								<li key={index}>
									<span className="font-semibold">{row.contact_name}</span> · {row.relationship} ·{" "}
									{row.primary_phone}
									{!row.may_contact_in_emergency && (
										<span className="text-muted"> · Not to be contacted</span>
									)}
								</li>
							))}
						</ul>
					) : (
						<Empty>No emergency contact added.</Empty>
					),
					<EmergencyEditor
						contacts={profile.emergency_contacts ?? []}
						relationships={applicationOptions?.relationships ?? []}
						onCancel={() => setEditing(null)}
						onSaved={saved}
					/>,
				)}
			</div>
		</Card>
	);
}

function Section({
	id,
	title,
	missing,
	editing,
	onEdit,
	view,
	editor,
}: {
	id: SectionKey;
	title: string;
	missing: boolean;
	editing: boolean;
	onEdit?: () => void;
	view: ReactNode;
	editor: ReactNode;
}) {
	return (
		<section id={`profile-section-${id}`} className="scroll-mt-6 p-5 sm:p-6" aria-labelledby={`profile-heading-${id}`}>
			<div className="mb-4 flex flex-wrap items-center justify-between gap-3">
				<div className="flex items-center gap-2.5">
					<h3 id={`profile-heading-${id}`} className="text-[14px] font-bold text-ink">
						{title}
					</h3>
					{missing && (
						<span className="rounded-md bg-warning-soft px-2 py-0.5 text-[11px] font-semibold text-warning">
							Missing
						</span>
					)}
				</div>
				{onEdit && !editing && (
					<button
						type="button"
						onClick={onEdit}
						className="inline-flex items-center gap-1.5 rounded-lg border border-card-line px-3 py-1.5 text-[12px] font-semibold text-ink transition hover:border-slate-faint"
						aria-label={`Edit ${title}`}
					>
						<Icon.pencil size={13} />
						Edit
					</button>
				)}
			</div>
			{editing ? editor : view}
		</section>
	);
}

function Pair({ label, value, locked }: { label: string; value: string | null | undefined; locked?: boolean }) {
	return (
		<div className="min-w-0">
			<dt className="text-[11px] text-muted">{label}</dt>
			<dd className="mt-1 flex items-center gap-1.5 break-words text-[13px] text-ink">
				{locked && value && (
					<span className="text-slate-faint" aria-label="Cannot be changed here">
						<Icon.lock size={11} />
					</span>
				)}
				{value || <span className="text-slate-faint">Not provided</span>}
			</dd>
		</div>
	);
}

function Empty({ children }: { children: ReactNode }) {
	return <p className="text-[13px] text-slate-faint">{children}</p>;
}

function withoutResidenceOrDocuments(details: PersonalDetails): PersonalDetails {
	return {
		...details,
		county: null,
		sub_county: null,
		ward: null,
		administrative_location: null,
		sub_location: null,
		supporting_documents: [],
	};
}

/* ------------------------------------------------------------- saving */

function useSave() {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const run = async (method: string, payload: Record<string, unknown>, done: () => void) => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(method, payload);
			done();
		} catch (error) {
			setFailure(errorMessage(error, "That change was not saved."));
		} finally {
			setBusy(false);
		}
	};

	return { busy, failure, run };
}

function Actions({
	busy,
	failure,
	onSave,
	onCancel,
}: {
	busy: boolean;
	failure: string | null;
	onSave: () => void;
	onCancel: () => void;
}) {
	return (
		<div className="mt-5 space-y-3">
			{failure && <ErrorNote>{failure}</ErrorNote>}
			<div className="flex items-center gap-2.5">
				<Button variant="navy" onClick={onSave} busy={busy}>
					Save
				</Button>
				<Button variant="ghost" onClick={onCancel} disabled={busy}>
					Cancel
				</Button>
			</div>
		</div>
	);
}

/* ------------------------------------------------------------ editors */

function DetailsEditor({
	person,
	genders,
	languages,
	onCancel,
	onSaved,
}: {
	person: RedProfile;
	genders: string[];
	languages: Array<{ key: string; label: string }>;
	onCancel: () => void;
	onSaved: () => void;
}) {
	const [firstName, setFirstName] = useState(person.first_name ?? "");
	const [lastName, setLastName] = useState(person.last_name ?? "");
	const [phone, setPhone] = useState(person.phone ?? "");
	const [gender, setGender] = useState(person.gender ?? "");
	const [dateOfBirth, setDateOfBirth] = useState(person.date_of_birth ?? "");
	const [language, setLanguage] = useState(person.preferred_language ?? "");
	const { busy, failure, run } = useSave();

	return (
		<>
			<div className="grid gap-5 sm:grid-cols-2">
				<Field label="First name" required htmlFor="profile-first">
					<TextInput id="profile-first" value={firstName} onChange={setFirstName} />
				</Field>
				<Field label="Last name" required htmlFor="profile-last">
					<TextInput id="profile-last" value={lastName} onChange={setLastName} />
				</Field>
				<Field label="Phone number" htmlFor="profile-phone">
					<TextInput id="profile-phone" type="tel" inputMode="tel" value={phone} onChange={setPhone} />
				</Field>
				<Field label="Gender" htmlFor="profile-gender">
					<SelectInput
						id="profile-gender"
						value={gender}
						options={genders}
						onChange={setGender}
						placeholder="Choose an answer"
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
				<Field label="Preferred language" htmlFor="profile-language">
					<VocabularySelect
						id="profile-language"
						value={language}
						options={languages}
						onChange={setLanguage}
						placeholder="No preference"
					/>
				</Field>
			</div>
			<Actions
				busy={busy}
				failure={failure}
				onCancel={onCancel}
				onSave={() =>
					void run(
						API.updateMyProfile,
						{
							first_name: firstName.trim(),
							last_name: lastName.trim(),
							phone: phone.trim(),
							gender,
							date_of_birth: dateOfBirth,
							preferred_language: language,
						},
						onSaved,
					)
				}
			/>
		</>
	);
}

/** Whole years old, or null while the date of birth is blank. */
function ageFrom(dateOfBirth: string | null): number | null {
	if (!dateOfBirth) return null;
	const born = new Date(dateOfBirth);
	if (Number.isNaN(born.getTime())) return null;
	const now = new Date();
	const hadBirthday =
		now.getMonth() > born.getMonth() || (now.getMonth() === born.getMonth() && now.getDate() >= born.getDate());
	return now.getFullYear() - born.getFullYear() - (hadBirthday ? 0 : 1);
}

function IdentificationEditor({
	person,
	options,
	loading,
	onCancel,
	onSaved,
}: {
	person: RedProfile;
	options?: ApplicationOptions;
	loading: boolean;
	onCancel: () => void;
	onSaved: () => void;
}) {
	const [rows, setRows] = useState<Identification[]>(() =>
		person.identifications.length
			? person.identifications.map((row) => ({
					id_type: row.id_type,
					id_number: row.id_number,
					attachment: row.attachment ?? "",
				}))
			: [blankIdentification()],
	);
	const { busy, failure, run } = useSave();

	return (
		<>
			<IdentificationStep
				options={options}
				loading={loading}
				rows={rows}
				onRows={setRows}
				age={ageFrom(person.date_of_birth)}
				idPrefix="profile"
			/>
			<Actions
				busy={busy}
				failure={failure}
				onCancel={onCancel}
				onSave={() =>
					void run(
						API.updateMyProfile,
						{ identifications: rows.filter(identificationIsUsable).map(sentIdentification) },
						onSaved,
					)
				}
			/>
		</>
	);
}

function CitizenshipEditor({
	person,
	countries,
	statuses,
	onCancel,
	onSaved,
}: {
	person: RedProfile;
	countries: string[];
	statuses: string[];
	onCancel: () => void;
	onSaved: () => void;
}) {
	const [country, setCountry] = useState(person.country_of_citizenship ?? "");
	const [status, setStatus] = useState(person.citizenship_status ?? "");
	const { busy, failure, run } = useSave();

	return (
		<>
			<div className="grid gap-5 sm:grid-cols-2">
				<Field label="Country of citizenship" required htmlFor="profile-citizenship">
					<Combo id="profile-citizenship" value={country} onChange={setCountry} options={countries} />
				</Field>
				{statuses.length > 0 && (
					<Field label="Citizenship status" htmlFor="profile-citizenship-status">
						<SelectInput
							id="profile-citizenship-status"
							value={status}
							onChange={setStatus}
							options={statuses}
							placeholder="Choose an answer"
						/>
					</Field>
				)}
			</div>
			<Actions
				busy={busy}
				failure={failure}
				onCancel={onCancel}
				onSave={() =>
					void run(
						API.updateMyProfile,
						{ country_of_citizenship: country, citizenship_status: status },
						onSaved,
					)
				}
			/>
		</>
	);
}

const RESIDENCE_KEYS = ["county", "sub_county", "ward", "administrative_location", "sub_location"] as const;

function ResidenceEditor({
	person,
	profile,
	onCancel,
	onSaved,
}: {
	person: RedProfile;
	profile: VolunteerProfile;
	onCancel: () => void;
	onSaved: () => void;
}) {
	const [residency, setResidency] = useState<string>(person.residency_type ?? "Local");
	const [sameHome, setSameHome] = useState(false);
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [touched, setTouched] = useState(false);
	const [country, setCountry] = useState(person.country_of_residence ?? "");
	const [address, setAddress] = useState(person.residence_address ?? "");
	const [details, setDetails] = useState<PersonalDetails>(person.personal_details ?? {});
	const { busy, failure, run } = useSave();

	// Where they live now, drawn into the pickers once so they change one rung
	// rather than choosing all of them again.
	const home = useFrappeGetCall<{ message: { chain: GeoNode[] } }>(
		API.geoChain,
		person.home_geo_node ? { node: person.home_geo_node } : undefined,
		person.home_geo_node ? `profile:home_chain:${person.home_geo_node}` : null,
	);
	const serving = useFrappeGetCall<{ message: { chain: GeoNode[] } }>(
		API.geoChain,
		profile.geo_node ? { node: profile.geo_node } : undefined,
		profile.geo_node ? `profile:serving_chain:${profile.geo_node}` : null,
	);

	useEffect(() => {
		const recorded = home.data?.message?.chain;
		if (touched || !recorded?.length) return;
		setChain(recorded);
		setTouched(true);
	}, [home.data, touched]);

	const branchChain = serving.data?.message?.chain ?? [];
	const save = () => {
		const payload: Record<string, unknown> =
			residency === "Abroad"
				? { residency_type: "Abroad", country_of_residence: country, residence_address: address }
				: {
						residency_type: "Local",
						home_geo_node: sameHome ? profile.geo_node : (selectedNode(chain)?.name ?? person.home_geo_node),
						personal_details: Object.fromEntries(RESIDENCE_KEYS.map((key) => [key, details[key] ?? ""])),
					};
		void run(API.updateMyProfile, payload, onSaved);
	};

	return (
		<>
			<ResidenceFields
				residency={residency}
				onResidency={setResidency}
				sameHome={sameHome}
				onSameHome={setSameHome}
				chain={chain}
				onChain={(next) => {
					setTouched(true);
					setChain(next);
				}}
				branchChain={branchChain}
				country={country}
				onCountry={setCountry}
				address={address}
				onAddress={setAddress}
				details={details}
				onDetails={setDetails}
			/>
			<Actions busy={busy} failure={failure} onCancel={onCancel} onSave={save} />
		</>
	);
}

function DisabilityEditor({
	person,
	options,
	onCancel,
	onSaved,
}: {
	person: RedProfile;
	options: IdentityOptions["disabilities"];
	onCancel: () => void;
	onSaved: () => void;
}) {
	const [status, setStatus] = useState(person.disability_status ?? "");
	const [needs, setNeeds] = useState(person.disability_needs ?? "");
	const [types, setTypes] = useState<string[]>(person.disabilities ?? []);
	const { busy, failure, run } = useSave();

	return (
		<>
			<DisabilityQuestion
				disability={status}
				onDisability={setStatus}
				disabilityNeeds={needs}
				onDisabilityNeeds={setNeeds}
				disabilities={types}
				onDisabilities={setTypes}
				disabilityOptions={options}
				idPrefix="profile"
			/>
			<Actions
				busy={busy}
				failure={failure}
				onCancel={onCancel}
				onSave={() =>
					void run(
						API.updateMyProfile,
						{ disability_status: status, disability_needs: needs, disabilities: types },
						onSaved,
					)
				}
			/>
		</>
	);
}

function DetailsBlockEditor({
	person,
	bloodGroups,
	onCancel,
	onSaved,
}: {
	person: RedProfile;
	bloodGroups?: string[];
	onCancel: () => void;
	onSaved: () => void;
}) {
	const [details, setDetails] = useState<PersonalDetails>(person.personal_details ?? {});
	const { busy, failure, run } = useSave();

	return (
		<>
			<RegistrationDetails
				value={details}
				onChange={setDetails}
				bloodGroups={bloodGroups}
				documents={false}
				showProfileLinks={false}
				idPrefix="profile-details"
			/>
			<Actions
				busy={busy}
				failure={failure}
				onCancel={onCancel}
				onSave={() => {
					// Everything this section drew, and nothing it did not: the residence
					// keys belong to Contact & Location and the files to their own section.
					const sent: Record<string, unknown> = { ...details };
					for (const key of [...RESIDENCE_KEYS, "supporting_documents"]) delete sent[key];
					void run(API.updateMyProfile, { personal_details: sent }, onSaved);
				}}
			/>
		</>
	);
}

function DocumentsEditor({
	person,
	types,
	onCancel,
	onSaved,
}: {
	person: RedProfile;
	types: NonNullable<IdentityOptions["supporting_document_types"]>;
	onCancel: () => void;
	onSaved: () => void;
}) {
	const [details, setDetails] = useState<PersonalDetails>(person.personal_details ?? {});
	const { busy, failure, run } = useSave();

	return (
		<>
			<RegistrationDetails
				value={details}
				onChange={setDetails}
				documentTypes={types}
				documentsOnly
				idPrefix="profile-documents"
			/>
			<Actions
				busy={busy}
				failure={failure}
				onCancel={onCancel}
				onSave={() =>
					void run(
						API.updateMyProfile,
						{ personal_details: { supporting_documents: details.supporting_documents ?? [] } },
						onSaved,
					)
				}
			/>
		</>
	);
}

function EmergencyEditor({
	contacts,
	relationships,
	onCancel,
	onSaved,
}: {
	contacts: EmergencyContact[];
	relationships: NonNullable<ApplicationOptions["relationships"]>;
	onCancel: () => void;
	onSaved: () => void;
}) {
	const [rows, setRows] = useState<EmergencyContact[]>(() =>
		contacts.length
			? contacts.map((row) => ({ ...row, alternative_phone: row.alternative_phone ?? "" }))
			: [blankContact()],
	);
	const { busy, failure, run } = useSave();

	return (
		<>
			<EmergencyContactsFields
				contacts={rows}
				onContacts={setRows}
				relationships={relationships}
				idPrefix="profile-ec"
			/>
			<Actions
				busy={busy}
				failure={failure}
				onCancel={onCancel}
				onSave={() =>
					void run(
						API.updateMyEmergencyContacts,
						{ emergency_contacts: rows.filter(contactIsUsable) },
						onSaved,
					)
				}
			/>
		</>
	);
}

/**
 * The photograph, uploaded by the person it is of.
 *
 * **Two steps, and the second is the same endpoint the rest of this screen
 * uses.** The file goes through the framework's own `upload_file`, which has
 * already decided what this person may store and how large it may be. What
 * comes back is a URL, and that URL is saved through `update_my_profile` like
 * any other correction. The server re-checks that it is one of this site's own
 * upload paths.
 *
 * **Public rather than private**: it has to render on a coordinator's screen and
 * inside a printed card. Removing is offered beside replacing; a photograph is
 * an optional field and `update_my_profile` clears one on an empty string.
 */
export function PhotoControl({ current, onSaved }: { current: string | null; onSaved: () => void }) {
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
			// An empty string clears an optional field. Not `null`, which means
			// "leave this alone".
			await save("");
		} catch (removeError) {
			setFailure(errorMessage(removeError, "That photograph could not be removed."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div>
			<div className="flex flex-wrap items-center gap-3">
				<label className="inline-flex cursor-pointer items-center rounded-lg border border-card-line px-3 py-1.5 text-[12px] font-semibold text-ink transition hover:border-slate-faint">
					{busy ? "Saving…" : current ? "Replace photo" : "Add a photo"}
					<input
						type="file"
						accept="image/*"
						className="hidden"
						disabled={busy}
						onChange={(event) => {
							const file = event.target.files?.[0];

							// Cleared so choosing the same file twice fires again.
							event.target.value = "";

							if (file) void upload(file);
						}}
					/>
				</label>

				{current && !busy && (
					<button
						type="button"
						onClick={() => void remove()}
						className="text-[12px] font-semibold text-slate-faint hover:text-ink hover:underline"
					>
						Remove
					</button>
				)}
			</div>

			<p className="mt-1.5 text-[11px] text-slate-faint">This is the photograph printed on your card.</p>

			{failure && (
				<div className="mt-2">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}
		</div>
	);
}
