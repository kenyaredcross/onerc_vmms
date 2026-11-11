import {
	Combo,
	Field,
	FieldSet,
	MultiCombo,
	PrivateUpload,
	RowHeading,
	SelectInput,
	TextArea,
	TextInput,
	VocabularySelect,
} from "./form";
import { Button, Spinner, cx } from "./primitives";
import type {
	ApplicationOptions,
	EmergencyContact,
	IdentificationTypeRow,
	VocabularyRow,
} from "../portal/types";

/*
 * Pieces of the registration form that more than one screen draws.
 *
 * They were written for `guest/Join.tsx` and lived inside it; the volunteer's
 * own profile edits the same records — identification, emergency contacts,
 * citizenship, disability — and has to ask for them in the same words and hold
 * them to the same rules. So they live here, and both screens import them.
 * Every element id defaults to what the registration form has always used.
 */

/**
 * The three answers to the disability question, spelled as the field spells
 * them.
 *
 * A closed list on both sides — `patches/install_disability_fields.py` holds the
 * same three — because it is a `Select` and a fourth word here would be an
 * answer the server refuses. "Prefer not to say" is one of them and not an
 * absence: declining is a real answer and it satisfies the requirement.
 */
export const DISABILITY_ANSWERS = ["No", "Yes", "Prefer not to say"];

/**
 * The one of those three that opens the rest of the question — named rather
 * than compared against a literal in four places, because it is also what
 * `install_disability_vocabulary.py` puts in the field's `depends_on`.
 */
export const DISABILITY_DISCLOSED = "Yes";

/**
 * The one citizenship standing the yes/no question answers on its own, spelled
 * as `Red Profile.citizenship_status` spells it.
 *
 * The rest of the list is not here: it is served on `application_options
 * .citizenship_statuses`, read off the Select itself, so a society that adds a
 * sixth standing gets it on this form with no deploy. Only the word "Citizen"
 * is named locally, because it is the one the question itself decides.
 */
export const CITIZEN = "Citizen";

/* --------------------------------------------------------- identification */

/**
 * One identity document, as this form holds it.
 *
 * Deliberately narrower than the row `Red Profile` stores: `is_primary` is not
 * here because position says it — the first document somebody lists is their
 * main one.
 *
 * `attachment` is here because a society can insist on a copy —
 * `Identification Type.requires_attachment`, served on every row of
 * `options.id_types` — and until this form collected one, an applicant at such
 * a society was refused at submission and told to upload the file to a profile
 * no screen would let them edit. Blank means "nothing to say about the copy",
 * and a scan a branch attached on the desk survives that; see
 * `registration._identification_rows`.
 */
export type Identification = { id_type: string; id_number: string; attachment: string };

export function blankIdentification(): Identification {
	return { id_type: "", id_number: "", attachment: "" };
}

/**
 * One document as it goes on the wire.
 *
 * A blank attachment is left out rather than sent as an empty string, because
 * the two mean different things to `_identification_rows`: nothing said keeps
 * whatever copy the profile already holds, and a value replaces it. A form that
 * always sent the key would be a form that could never leave a scan alone.
 */
export function sentIdentification(row: Identification): Record<string, string> {
	return row.attachment
		? { id_type: row.id_type, id_number: row.id_number, attachment: row.attachment }
		: { id_type: row.id_type, id_number: row.id_number };
}

/** Two or more names, joined the way somebody would say them out loud. */
export function listed(names: string[]): string {
	if (names.length <= 1) return names[0] ?? "";
	if (names.length === 2) return `${names[0]} and ${names[1]}`;

	return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

/** Enough of a document to be worth sending: a kind, and the number on it. */
export function identificationIsUsable(row: Identification): boolean {
	return Boolean(row.id_type && row.id_number.trim());
}

/**
 * Not half-filled. Either the row is untouched, or it is complete.
 *
 * The same bargain `contactIsCoherent` strikes, for the same reason: a passport
 * with no number is not a document anybody can check, and the server refuses
 * the pair rather than storing half of it.
 */
export function identificationIsCoherent(row: Identification): boolean {
	const touched = Boolean(row.id_type || row.id_number.trim());

	return !touched || identificationIsUsable(row);
}

/**
 * The same kind of document listed twice.
 *
 * A person has one national card. The server refuses the set — the required
 * documents check keys by type, so a repeat is a row nobody can see — and this
 * says so on the step rather than at submission.
 */
export function repeatedIdentification(rows: Identification[]): boolean {
	const kinds = rows.filter(identificationIsUsable).map((row) => row.id_type);

	return new Set(kinds).size !== kinds.length;
}

/**
 * The documents this society insists on that the applicant has not listed.
 *
 * The same three rules `application._assert_identity_documents` applies, asked
 * on the step rather than at submission: a society that has ticked nothing
 * requires nothing, a required document below its own minimum age is not
 * insisted on, and everything else has to be produced. Returned as labels
 * because the only thing this is for is telling somebody which document to add.
 *
 * `age` is `null` while the date of birth is still blank, and a minimum-age
 * exemption cannot be granted to an age nobody has given — so every required
 * document is asked for until somebody says how old they are, which is the
 * direction that cannot let an applicant past a rule.
 */
export function missingRequiredDocuments(
	rows: Identification[],
	types: IdentificationTypeRow[],
	age: number | null,
): string[] {
	const held = new Set(rows.filter(identificationIsUsable).map((row) => row.id_type));

	return types
		.filter((type) => type.is_required)
		.filter((type) => !(type.minimum_age && age !== null && age < type.minimum_age))
		.filter((type) => !held.has(type.key))
		.map((type) => type.label);
}

/**
 * The documents listed whose copy this society asks for and which have none.
 *
 * Asked of what the applicant actually listed rather than of the required set:
 * a society can want a copy of a document it does not insist everybody holds,
 * and somebody who has produced that document owes the copy that goes with it.
 */
export function missingDocumentCopies(
	rows: Identification[],
	types: IdentificationTypeRow[],
): string[] {
	const asked = new Map(types.filter((type) => type.requires_attachment).map((type) => [type.key, type.label]));

	return rows
		.filter((row) => identificationIsUsable(row) && asked.has(row.id_type) && !row.attachment)
		.map((row) => asked.get(row.id_type) as string);
}

/* ------------------------------------------------------ emergency contacts */

export function blankContact(): EmergencyContact {
	return {
		contact_name: "",
		relationship: "",
		primary_phone: "",
		alternative_phone: "",
		// Ticked to begin with, because somebody who names an emergency contact
		// means us to call them. Unticking is the deliberate act.
		may_contact_in_emergency: true,
	};
}

/**
 * Enough of a contact to be worth storing: somebody to call, how you know them,
 * and a number.
 *
 * **All three, because the record insists on all three.** `VMMS Emergency
 * Contact` marks `relationship` mandatory alongside the name and the phone, so a
 * row carrying two of them was accepted by this form, sent on the next autosave
 * and refused by the framework with "Row #1: Relationship" — a stack-trace
 * sentence in the middle of somebody's registration. The step marks the field
 * required and `contactIsCoherent` holds the Next button until it is answered,
 * which is the same rule stated where somebody can act on it.
 */
export function contactIsUsable(contact: EmergencyContact): boolean {
	return Boolean(
		contact.contact_name.trim() && contact.relationship.trim() && contact.primary_phone.trim(),
	);
}

/**
 * Not half-filled. Either nothing has been entered, or enough has.
 *
 * A name with no number is not somebody anybody can call, and letting it through
 * would store a contact that satisfies nothing and looks like it does.
 */
export function contactIsCoherent(contact: EmergencyContact): boolean {
	const touched = Boolean(
		contact.contact_name.trim() || contact.relationship.trim() || contact.primary_phone.trim(),
	);

	return !touched || contactIsUsable(contact);
}

/**
 * The relationship picker's choices: the society's active list, plus the value a
 * saved contact already holds if the society has since switched it off, so a
 * resumed draft shows what was chosen rather than an empty select.
 */
export function relationshipChoices(list: VocabularyRow[], current: string): VocabularyRow[] {
	if (!current || list.some((row) => row.key === current)) return list;

	return [...list, { key: current, label: current, description: null }];
}

/* ------------------------------------------------------------- questions */

/**
 * A short closed question, answered by picking one of its answers.
 *
 * A `<select>` for two or three answers is a control that hides what it is
 * asking until somebody opens it, on a form whose whole job is to be read
 * before it is filled in. These are the same answers, visible, and each one is
 * a target big enough for a thumb.
 *
 * A real `<input type="radio">` under each label rather than a styled button,
 * so the group arrows, the name grouping and the announcement are the
 * browser's own. The caller supplies the group's name through a `<legend>`.
 */
export function ChoiceRow({
	name,
	value,
	options,
	onChange,
}: {
	name: string;
	value: string;
	options: string[];
	onChange: (value: string) => void;
}) {
	return (
		<div className="flex flex-wrap gap-2.5">
			{options.map((option, index) => {
				const picked = value === option;

				return (
					<label
						key={option}
						className={cx(
							// `grow` with a small basis and no wrapping inside the pill:
							// three answers that fit sit on one row, and one as long as
							// "Prefer not to say" takes the next row whole rather than
							// breaking itself over three lines in a narrow column.
							"flex grow basis-[104px] cursor-pointer items-center gap-2.5 whitespace-nowrap rounded-[7px] border px-[18px] py-[11px] text-[14px] font-medium transition",
							picked
								? "border-blue bg-blue-soft text-blue-press"
								: "border-[#CDD8E5] bg-white text-ink hover:border-blue-line",
						)}
					>
						<input
							// A group has no element of its own that can take focus, so
							// the first answer in it is what an unanswered question is
							// anchored by — see `Gap`. Numbered rather than named after
							// the answer, because the answers are a society's own words
							// and "join-disability-Prefer not to say" is not an id.
							id={`${name}-${index}`}
							type="radio"
							name={name}
							value={option}
							checked={picked}
							onChange={() => onChange(option)}
							className="h-[17px] w-[17px] flex-none accent-blue"
						/>
						{option}
					</label>
				);
			})}
		</div>
	);
}

/**
 * Whether somebody has a disability, and what would help — asked under Health
 * and Wellness beside blood group and allergies. Only a volunteer (or a member
 * whose type requires identity) is asked; `assert_ready` checks it for them.
 */
export function DisabilityQuestion({
	disability,
	onDisability,
	disabilityNeeds,
	onDisabilityNeeds,
	disabilities,
	onDisabilities,
	disabilityOptions,
	idPrefix = "join",
}: {
	disability: string;
	onDisability: (v: string) => void;
	disabilityNeeds: string;
	onDisabilityNeeds: (v: string) => void;
	disabilities: string[];
	onDisabilities: (v: string[]) => void;
	disabilityOptions: VocabularyRow[];
	/** Prefix for the element ids; `join` is the registration form's own. */
	idPrefix?: string;
}) {
	return (
			<div>
				<fieldset className="min-w-0 border-0 p-0">
					<legend className="mb-3 flex items-center gap-1 text-[14px] font-semibold text-slate-strong">
						Are you a person with disability?
						<span className="text-danger" aria-hidden="true">
							*
						</span>
					</legend>
					{/* Capped rather than full width. The answers are two or
					    three words each and a pill stretched across the whole
					    card is a button pretending to be a banner. */}
					<div className="max-w-[470px]">
						<ChoiceRow
							name={`${idPrefix}-disability`}
							value={disability}
							options={DISABILITY_ANSWERS}
							onChange={onDisability}
						/>
					</div>
					<p className="mt-2.5 text-[12px] leading-relaxed text-muted">
						We will ask how we can support you.
					</p>
				</fieldset>

				{/* A "Yes" needs at least one type. The free-text support request
				    follows it, matching the order somebody answers the questions. */}
				{disability === DISABILITY_DISCLOSED && (
					<div className="rise-in mt-6 grid gap-5 rounded-xl border border-card-line bg-[#F7FAFC] p-5">
						<MultiCombo
							id={`${idPrefix}-disabilities`}
							label="Disability type"
							required
							options={disabilityOptions}
							selected={disabilities}
							onToggle={(key) =>
								onDisabilities(
									disabilities.includes(key)
										? disabilities.filter((entry) => entry !== key)
										: [...disabilities, key],
								)
							}
							placeholder="Search disability types"
							empty="This society has not configured a list to choose from."
						/>

						<Field
							label="What support would be helpful?"
							htmlFor={`${idPrefix}-disability-needs`}
							hint="Optional"
						>
							<TextArea
								id={`${idPrefix}-disability-needs`}
								value={disabilityNeeds}
								onChange={onDisabilityNeeds}
								rows={3}
							/>
						</Field>
					</div>
				)}
			</div>
	);
}

/**
 * Citizenship, asked the way a clerk at a branch counter would ask it.
 *
 * **The overwhelming majority answer "yes", so that is the question.** This was
 * a country picker two hundred entries long, opened on the society's own country
 * and correct for almost everybody who saw it — a control whose only job, nearly
 * every time, was to be scrolled past. A person who is a citizen now answers one
 * button, and the list is drawn for the minority it was actually there for.
 *
 * **The society's own country is the society's own configuration.** It is
 * `application.default_country_of_citizenship`, the same value the field would
 * be filled with on insert, arriving through `application_options`. Nothing here
 * names a country, and a society that has not set one gets the plain picker
 * back — the yes/no question is unanswerable without knowing what "citizen"
 * means here, and guessing would be this file inventing a citizenship country.
 *
 * **"No" clears the answer rather than leaving the default standing.** The step
 * cannot be completed without a country, so somebody who says they are not a
 * citizen is stopped at an empty required field instead of carrying the
 * society's country forward under an answer that contradicts it.
 */
export function CitizenshipAsk({
	countries,
	statuses,
	home,
	value,
	onChange,
	status,
	onStatus,
	isCitizen,
	onIsCitizen,
	idPrefix = "join",
}: {
	countries: string[];
	/** The standings this society's profile field offers, its own words. */
	statuses: string[];
	home: string | null;
	value: string;
	onChange: (value: string) => void;
	status: string;
	onStatus: (value: string) => void;
	isCitizen: boolean | null;
	onIsCitizen: (yes: boolean) => void;
	/** Prefix for the element ids; `join` is the registration form's own. */
	idPrefix?: string;
}) {
	if (!home) {
		return (
			<div className="grid min-w-0 max-w-xl gap-[21px] sm:grid-cols-2">
				<Field label="Country of citizenship" required htmlFor={`${idPrefix}-citizenship`}>
					<Combo id={`${idPrefix}-citizenship`} value={value} onChange={onChange} options={countries} />
				</Field>

				{statuses.length > 0 && (
					<Field
						label="Your standing here"
						htmlFor={`${idPrefix}-citizenship-status`}
						hint="So your branch knows what it may ask of you."
					>
						<SelectInput
							id={`${idPrefix}-citizenship-status`}
							value={status}
							onChange={onStatus}
							options={statuses}
							placeholder="Choose an answer"
						/>
					</Field>
				)}
			</div>
		);
	}

	return (
		<fieldset className="min-w-0 border-0 p-0">
			<legend className="mb-3 flex items-center gap-1 text-[14px] font-semibold text-slate-strong">
				Are you a citizen of {home}?
				<span className="text-danger" aria-hidden="true">
					*
				</span>
			</legend>

			{/* Capped, like the question under it: two pills across a whole card
			    is a pair of banners, not a pair of answers. */}
			<div className="max-w-[470px]">
				<ChoiceRow
					name={`${idPrefix}-is-citizen`}
					value={isCitizen === null ? "" : isCitizen ? "Yes" : "No"}
					options={["Yes", "No"]}
					onChange={(answer) => onIsCitizen(answer === "Yes")}
				/>
			</div>

			{isCitizen === true ? (
				<p className="mt-2.5 text-[12px] leading-relaxed text-muted">
					{home} will be recorded as your country of citizenship.
				</p>
			) : (
				<p className="mt-2.5 text-[12px] leading-relaxed text-muted">
					This determines which identification you will need.
				</p>
			)}
		</fieldset>
	);
}

/**
 * What "no" costs: the country, and the standing this society's own field
 * offers. Drawn under the pair of questions rather than inside one of them,
 * because two fields in half a row is a column of squeezed controls beside a
 * question with nothing under it.
 */
export function CitizenshipDetails({
	countries,
	statuses,
	home,
	value,
	onChange,
	status,
	onStatus,
	idPrefix = "join",
}: {
	countries: string[];
	statuses: string[];
	home: string;
	value: string;
	onChange: (value: string) => void;
	status: string;
	onStatus: (value: string) => void;
	/** Prefix for the element ids; `join` is the registration form's own. */
	idPrefix?: string;
}) {
	// Everything but "Citizen", which the yes/no question has already answered.
	// Offering it again under "No" would be a form contradicting itself.
	const otherStatuses = statuses.filter((entry) => entry !== CITIZEN);

	return (
		<div className="rise-in mt-6 grid gap-5 rounded-xl border border-card-line bg-[#F7FAFC] p-5 sm:grid-cols-2">
			<Field label="Country of citizenship" required htmlFor={`${idPrefix}-citizenship`}>
				<Combo id={`${idPrefix}-citizenship`} value={value} onChange={onChange} options={countries} />
			</Field>

			{/* Drawn only where the society's own field offers something to choose.
			    A site whose Select has been emptied gets the country question and no
			    second one. */}
			{otherStatuses.length > 0 && (
				<Field label={`Citizenship status in ${home}`} required htmlFor={`${idPrefix}-citizenship-status`}>
					<SelectInput
						id={`${idPrefix}-citizenship-status`}
						value={status}
						onChange={onStatus}
						options={otherStatuses}
						placeholder="Choose an answer"
					/>
				</Field>
			)}
		</div>
	);
}

/**
 * The documents somebody produces, however many that is.
 *
 * **One was never the model.** `Red Profile` has held a *table* of
 * identifications since it was written, the coordinator's view has always shown
 * all of them, and a society can mark two different types required at once —
 * which made this step, asking for a single pair, a form that could not satisfy
 * the configuration sitting next to it. So the step lists documents and the
 * person adds the ones they hold.
 *
 * **The first row is the main one, and nothing says so on screen.** Order is
 * the whole statement — the server reads position and sets the flag — because a
 * "primary" radio beside two rows is a control asking somebody to rank their own
 * passport, which is a question nobody has an opinion about.
 *
 * **Removing is only offered when there is something to remove.** A single row
 * has no remove button: emptying the step is not a thing anybody wants, and a
 * control that would leave a required step blank is a trap rather than a
 * choice.
 */
export function IdentificationStep({
	options,
	loading,
	rows,
	onRows,
	age,
	idPrefix = "join",
}: {
	options?: ApplicationOptions;
	loading: boolean;
	rows: Identification[];
	onRows: (next: Identification[]) => void;
	/** Whole years old, or null while the date of birth is still blank. */
	age: number | null;
	/** Prefix for the element ids; `join` is the registration form's own. */
	idPrefix?: string;
}) {
	if (loading || !options) return <Spinner label="Loading…" />;

	if (options.id_types.length === 0) {
		return (
			<p className="rounded-xl bg-surface px-4 py-3 text-[12.5px] leading-relaxed text-muted">
				Registration is not available yet. Please contact your branch.
			</p>
		);
	}

	const set = (index: number, key: keyof Identification, value: string) =>
		onRows(rows.map((row, at) => (at === index ? { ...row, [key]: value } : row)));

	const remove = (index: number) => onRows(rows.filter((_row, at) => at !== index));

	// A kind already listed is not offered again in the other rows' pickers, so
	// the repeat this step refuses cannot be chosen in the first place. The row's
	// own current value always stays in its own list, or choosing it would
	// remove it from under the person who chose it.
	const taken = new Set(rows.map((row) => row.id_type).filter(Boolean));

	// What this society asks of each kind, so a row can say so beside itself
	// rather than at submission. The same rows `missingRequiredDocuments` and
	// `missingDocumentCopies` read, which is why the step's gate and the
	// sentences on it can never disagree.
	const rules = new Map(options.id_types.map((type) => [type.key, type]));
	const outstanding = missingRequiredDocuments(rows, options.id_types, age);

	// A required kind is labelled as required in every picker, so somebody
	// choosing between three documents can see which one their branch insists on
	// before they pick the wrong one.
	const offered = (row: Identification) =>
		options.id_types
			.filter((type) => type.key === row.id_type || !taken.has(type.key))
			.map((type) => ({
				...type,
				label:
					type.is_required && !(type.minimum_age && age !== null && age < type.minimum_age)
						? `${type.label} (required)`
						: type.label,
			}));

	return (
		<div className="max-w-xl space-y-4">
			{rows.map((row, index) => (
				<div
					key={index}
					className={cx(
						"grid gap-5 sm:grid-cols-2",
						index > 0 && "border-t border-card-line pt-4",
					)}
				>
					{rows.length > 1 && (
						<RowHeading
							className="sm:col-span-2"
							label={`ID document ${index + 1}`}
							removeLabel={`Remove ID document ${index + 1}`}
							onRemove={() => remove(index)}
						/>
					)}

					<Field
						label={index === 0 ? "ID type" : "Another ID type"}
						required={index === 0}
						htmlFor={`${idPrefix}-id-type-${index}`}
					>
						<VocabularySelect
							id={`${idPrefix}-id-type-${index}`}
							value={row.id_type}
							onChange={(value) => set(index, "id_type", value)}
							options={offered(row)}
						/>
					</Field>

					<Field
						label="ID number"
						required={index === 0}
						htmlFor={`${idPrefix}-id-number-${index}`}
					>
						<TextInput
							id={`${idPrefix}-id-number-${index}`}
							value={row.id_number}
							onChange={(value) => set(index, "id_number", value)}
						/>
					</Field>

					{/* Only for a kind whose copy this society actually asks for.
					    A file box under every document would be a form asking for
					    scans nobody wants and storing them forever. */}
					{rules.get(row.id_type)?.requires_attachment && (
						<Field
							label="Identification copy"
							required
							htmlFor={`${idPrefix}-id-file-${index}`}
							hint="Upload a photograph or scan. Only your branch can access it."
							className="sm:col-span-2"
						>
							<PrivateUpload
								id={`${idPrefix}-id-file-${index}`}
								value={row.attachment}
								onChange={(value) => set(index, "attachment", value)}
								choose="Choose a copy"
								replace="Replace the copy"
							/>
						</Field>
					)}

				</div>
			))}

			{/* Offered only when the society actually recognises another kind, so
			    a society with one document type gets no button that adds a row
			    with nothing to put in it. */}
			{rows.length < options.id_types.length && (
				<Button
					variant="navy"
					onClick={() => onRows([...rows, blankIdentification()])}
					disabled={!rows.every(identificationIsCoherent)}
				>
					Add another document
				</Button>
			)}

			{outstanding.length > 0 ? (
				// Named rather than counted. "One more document" leaves somebody
				// guessing which; the society's own word for it does not.
				<p className="rounded-xl bg-surface px-4 py-3 text-[12.5px] leading-relaxed text-muted">
					Required: {listed(outstanding)}. Add {outstanding.length === 1 ? "it" : "them"} before continuing.
				</p>
			) : (
				<p className="text-[11.5px] leading-relaxed text-slate-faint">
					Add another document only if required by your branch.
				</p>
			)}
		</div>
	);
}

/**
 * The emergency contacts list: one block of fields per contact, the permission
 * to call each one, and the button that adds another.
 *
 * Lifted out of the registration's emergency step so the profile can edit the
 * same records with the same fields. `idPrefix` names the element ids
 * (`ec-name-0`, `ec-rel-0`, …), and defaults to what the registration form has
 * always used.
 */
export function EmergencyContactsFields({
	contacts,
	onContacts,
	relationships,
	idPrefix = "ec",
}: {
	contacts: EmergencyContact[];
	onContacts: (next: EmergencyContact[]) => void;
	/** `application_options.relationships` — the society's `VMMS Relationship` list. */
	relationships: VocabularyRow[];
	idPrefix?: string;
}) {
	const set = <K extends keyof EmergencyContact>(index: number, key: K, value: EmergencyContact[K]) =>
		onContacts(contacts.map((row, at) => (at === index ? { ...row, [key]: value } : row)));

	return (
		<FieldSet
			title="Emergency contacts"
			description="Add a person who may be contacted in an emergency."
		>
			<div className="space-y-6">
				{contacts.map((contact, index) => (
					<div
						key={index}
						className={cx(
							"grid gap-5 sm:grid-cols-2",
							index > 0 && "border-t border-card-line pt-6",
						)}
					>
						{/* With more than one contact, each is numbered and carries
						    its own remove button at the top right, because two blocks
						    of identically labelled fields on one screen are ambiguous
						    to read and unusable with a screen reader. A single
						    contact has nothing to number and cannot be removed. */}
						{contacts.length > 1 && (
							<RowHeading
								className="sm:col-span-2"
								label={`Contact ${index + 1}`}
								removeLabel={`Remove contact ${index + 1}`}
								onRemove={() => onContacts(contacts.filter((_row, at) => at !== index))}
							/>
						)}

						<Field label="Full name" required htmlFor={`${idPrefix}-name-${index}`}>
							<TextInput
								id={`${idPrefix}-name-${index}`}
								value={contact.contact_name}
								onChange={(value) => set(index, "contact_name", value)}
								placeholder="Full name"
							/>
						</Field>

						<Field label="Relationship" required htmlFor={`${idPrefix}-rel-${index}`}>
							<VocabularySelect
								id={`${idPrefix}-rel-${index}`}
								value={contact.relationship}
								onChange={(value) => set(index, "relationship", value)}
								options={relationshipChoices(relationships, contact.relationship)}
								placeholder="Choose a relationship"
							/>
						</Field>

						<Field label="Phone number" required htmlFor={`${idPrefix}-phone-${index}`}>
							<TextInput
								id={`${idPrefix}-phone-${index}`}
								type="tel"
								value={contact.primary_phone}
								onChange={(value) => set(index, "primary_phone", value)}
								placeholder="Primary phone number"
							/>
						</Field>

						<Field
							label="Alternative phone number"
							htmlFor={`${idPrefix}-alt-${index}`}
							hint="Optional"
						>
							<TextInput
								id={`${idPrefix}-alt-${index}`}
								type="tel"
								value={contact.alternative_phone ?? ""}
								onChange={(value) => set(index, "alternative_phone", value)}
								placeholder="Optional"
							/>
						</Field>

						<div className="sm:col-span-2">
							{/* Not a formality. An unticked box means we hold a number we
							    have been told not to call, which is a different state
							    from holding no number — and the server counts only the
							    contacts somebody actually permitted. */}
							<label
								htmlFor={`${idPrefix}-permission-${index}`}
								className="flex cursor-pointer items-start gap-3 rounded-xl border border-card-line bg-canvas-soft p-4"
							>
								<input
									id={`${idPrefix}-permission-${index}`}
									type="checkbox"
									className="mt-0.5 h-4 w-4 shrink-0 accent-brand"
									checked={Boolean(contact.may_contact_in_emergency)}
									onChange={(event) =>
										set(index, "may_contact_in_emergency", event.target.checked)
									}
								/>
								<span>
									<span className="block text-[13px] font-semibold leading-snug text-ink">
										Permission to contact in an emergency
									</span>
									<span className="mt-1 block text-[11.5px] leading-relaxed text-slate-faint">
										Clear this checkbox if this person may not be contacted.
									</span>
								</span>
							</label>
						</div>

					</div>
				))}

				<Button
					variant="navy"
					onClick={() => onContacts([...contacts, blankContact()])}
					disabled={!contacts.every(contactIsCoherent)}
				>
					Add another contact
				</Button>
			</div>
		</FieldSet>
	);
}
