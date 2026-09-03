import { type ReactNode } from "react";

import type {
	DrivingLicenceRow,
	EducationRow,
	IdentityOptions,
	LicenceRow,
	ReferenceRow,
	TrainingRow,
	VocabularyRow,
	WorkExperienceRow,
} from "../portal/types";
import { Button, cx } from "./primitives";
import { Field, FieldSet, PrivateUpload, TextArea, TextInput, VocabularySelect } from "./form";

/**
 * What somebody has already done: seven person facts, one component.
 *
 * Extracted from the registration wizard because two screens ask for exactly
 * the same thing at two different moments — a volunteer fills this in when they
 * register, and corrects it on their own profile page afterwards. Those are the
 * same seven fields against the same `update_my_profile` endpoint, and a second
 * copy of six repeating-row editors would have been six places to fix the first
 * time one of them was wrong.
 *
 * **It knows nothing about registration.** No step, no wizard, no completion
 * rule: it draws the fields, reports changes, and leaves saving to whoever owns
 * the screen. That is what let the profile page reuse it without inheriting the
 * wizard's idea of what "continue" means.
 *
 * Everything here writes to core's `Red Profile` — see
 * `patches/install_background_fields.py` for why these are person facts rather
 * than application facts, and why every one of them is optional.
 */

/** The seven fields, carried as one value so callers hold one piece of state. */
export interface BackgroundValues {
	profession: string;
	education: EducationRow[];
	training: TrainingRow[];
	work_experience: WorkExperienceRow[];
	licences: LicenceRow[];
	driving_licences: DrivingLicenceRow[];
	references: ReferenceRow[];
}

/** Nothing said yet, which is how every one of these starts. */
export const emptyBackground = (): BackgroundValues => ({
	profession: "",
	education: [],
	training: [],
	work_experience: [],
	licences: [],
	driving_licences: [],
	references: [],
});

/**
 * What a profile holds, as this component's value.
 *
 * Tolerant of every key being absent, because it is fed straight from
 * `my_profile` and a browser can be a deploy ahead of the server that answers
 * it — in which case the honest answer is "nothing recorded", not a crash on
 * somebody's profile page.
 */
type HeldBackground = Partial<Omit<BackgroundValues, "profession">> & { profession?: string | null };

export const backgroundFrom = (held: HeldBackground | null | undefined): BackgroundValues => ({
	...emptyBackground(),
	profession: held?.profession ?? "",
	education: held?.education ?? [],
	training: held?.training ?? [],
	work_experience: held?.work_experience ?? [],
	licences: held?.licences ?? [],
	driving_licences: held?.driving_licences ?? [],
	references: held?.references ?? [],
});

/**
 * The six tables, filtered to the rows somebody actually filled in.
 *
 * The shape `update_my_profile` takes: all six keys always present, because a
 * key that is absent means "leave that table alone" on the server and a table
 * that vanished from the payload when it was emptied could never be emptied.
 */
export const backgroundPayload = (values: BackgroundValues) => ({
	education: values.education.filter(rowIsUsable),
	training: values.training.filter(rowIsUsable),
	work_experience: values.work_experience.filter(rowIsUsable),
	licences: values.licences.filter(rowIsUsable),
	driving_licences: values.driving_licences.filter(rowIsUsable),
	references: values.references.filter(rowIsUsable),
});

/** Whether any of it has been filled in, which is what decides if a panel is drawn. */
export const hasBackground = (values: BackgroundValues): boolean =>
	Boolean(values.profession) || backgroundLines(undefined, values).length > 0;

/* ------------------------------------------------- what they have already done */

/**
 * A repeating block of rows, with the two controls every one of them needs.
 *
 * Six tables on one step, each with its own fields, and the alternative to this
 * was six copies of the same map-with-an-index-and-a-remove-button. What differs
 * between them is the fields inside a row; what does not is the numbering, the
 * separator, the remove control and the refusal to stack blank rows — so those
 * live here once and the caller passes a renderer for the inside.
 *
 * **An empty table is drawn as an invitation, not as a blank row.** Every one of
 * these is optional, and a step that opened with six pre-drawn empty forms would
 * say the opposite: it would look like six things somebody has to fill in. One
 * button per table says "add this if you have it", which is what is actually
 * being asked.
 *
 * **"Add another" is disabled while the last row is empty.** Otherwise a
 * mis-click stacks blanks that the server then silently drops, and somebody
 * scrolls back through four empty forms wondering which one did not save.
 */
/**
 * A blank row for each of the six background tables.
 *
 * Every field starts as an empty string rather than undefined, because these
 * are all controlled inputs and React logs a warning the first time one of them
 * flips from uncontrolled to controlled — which is what happens when a value is
 * only defined once somebody types into it.
 */
export const blankEducation = (): EducationRow => ({
	institution: "",
	level: "",
	qualification: "",
	started_in: null,
	finished_in: null,
	is_ongoing: false,
	attachment: null,
});

export const blankTraining = (): TrainingRow => ({
	course_name: "",
	institution: "",
	started_on: "",
	completed_on: "",
	remarks: "",
	attachment: null,
});

export const blankExperience = (): WorkExperienceRow => ({
	organization: "",
	role: "",
	started_on: "",
	ended_on: "",
	is_current: false,
	summary: "",
});

export const blankLicence = (): LicenceRow => ({
	license_type: "",
	license_name: "",
	institution: "",
	registration_no: "",
	valid_from: "",
	valid_to: "",
	does_not_expire: false,
	attachment: null,
});

export const blankDrivingLicence = (): DrivingLicenceRow => ({
	licence_class: "",
	licence_number: "",
	valid_to: "",
	attachment: null,
});

export const blankReference = (): ReferenceRow => ({
	reference_name: "",
	position: "",
	organization: "",
	email: "",
	phone: "",
	relationship: "",
	notes: "",
});

/**
 * Whether a row says anything at all.
 *
 * The one rule the whole background block enforces, and it is not a validation:
 * a form that opens with an empty row in every table would otherwise send six
 * rows of nothing on the first save. Tickboxes do not count, for the reason
 * `registration.py::_has_content` gives — a checkbox always carries a value, so
 * counting it would make every untouched row look answered.
 *
 * The server drops empty rows too. Doing it here as well is not belt and braces:
 * it is what lets "Add another" refuse to stack blanks, which is a thing
 * somebody can see.
 */
export const rowIsUsable = (row: object): boolean =>
	Object.values(row).some(
		(value) => typeof value !== "boolean" && String(value ?? "").trim().length > 0,
	);

/**
 * The background step as lines a confirmation panel can print.
 *
 * Six tables of six different shapes, each reduced to a label and a sentence,
 * because a review screen is for reading back rather than for re-editing: the
 * Edit control goes to the step, which is where every field already is.
 *
 * Keys are resolved to labels here. `education_levels` and
 * `driving_licence_classes` are registers, so the row holds "diploma" and the
 * reader wants "Diploma" — a confirmation screen showing the key would be
 * showing somebody the database.
 */
export function backgroundLines(
	options: IdentityOptions | undefined,
	values: BackgroundValues,
): Array<{ label: string; value: string }> {
	const {
		education,
		training,
		work_experience: experience,
		licences,
		driving_licences: drivingLicences,
		references,
	} = values;

	const labelOf = (vocabulary: VocabularyRow[] | undefined, key: string) =>
		vocabulary?.find((row) => row.key === key)?.label ?? key;

	// Joined with a middle dot rather than a comma, so a qualification that
	// contains a comma still reads as one field.
	const parts = (...values: Array<string | null>) => values.filter(Boolean).join(" · ");

	return [
		...education.filter(rowIsUsable).map((row) => ({
			label: "Studied",
			value: parts(
				row.institution,
				row.qualification,
				row.level ? labelOf(options?.education_levels, row.level) : null,
			),
		})),
		...training.filter(rowIsUsable).map((row) => ({
			label: "Course",
			value: parts(row.course_name, row.institution),
		})),
		...experience.filter(rowIsUsable).map((row) => ({
			label: "Experience",
			value: parts(row.role, row.organization),
		})),
		...licences.filter(rowIsUsable).map((row) => ({
			label: "Licence",
			value: parts(row.license_name, row.institution, row.registration_no),
		})),
		...drivingLicences.filter(rowIsUsable).map((row) => ({
			label: "Driving",
			value: parts(
				row.licence_class ? labelOf(options?.driving_licence_classes, row.licence_class) : null,
				row.licence_number,
			),
		})),
		...references.filter(rowIsUsable).map((row) => ({
			label: "Referee",
			value: parts(row.reference_name, row.relationship || row.position),
		})),
	];
}

export function RowList<T extends object>({
	title,
	description,
	rows,
	onRows,
	blank,
	add,
	renderRow,
}: {
	title: string;
	description?: string;
	rows: T[];
	onRows: (rows: T[]) => void;
	blank: () => T;
	/** What the button says — named for the thing, so six on one step differ. */
	add: string;
	renderRow: (
		row: T,
		index: number,
		set: <K extends keyof T>(key: K, value: T[K]) => void,
		/**
		 * Two fields at once, and it is not a convenience.
		 *
		 * `set` closes over `rows` as it was when the row was rendered, so two
		 * calls to it in one handler both start from that snapshot and the second
		 * silently discards the first. Every place this step resolves a
		 * contradiction — "still studying" clearing a finish year, "still there"
		 * clearing an end date — is exactly two fields in one handler, so it has
		 * to be one write.
		 */
		patch: (values: Partial<T>) => void,
	) => ReactNode;
}) {
	const patchAt = (index: number) => (values: Partial<T>) =>
		onRows(rows.map((row, at) => (at === index ? { ...row, ...values } : row)));

	return (
		<FieldSet title={title} description={description}>
			<div className="space-y-6">
				{rows.map((row, index) => (
					<div
						key={index}
						className={cx("grid gap-5 sm:grid-cols-2", index > 0 && "border-t border-card-line pt-6")}
					>
						{/* Numbered from the second, for the reason the emergency
						    contacts are: two blocks of identically labelled fields on
						    one screen are ambiguous to read and unusable with a screen
						    reader, and on the common form with one row there is
						    nothing to number. */}
						{index > 0 && (
							<p className="sm:col-span-2 text-[11px] font-bold uppercase tracking-wider text-slate-faint">
								{index + 1}
							</p>
						)}

						{renderRow(
							row,
							index,
							(key, value) => patchAt(index)({ [key]: value } as unknown as Partial<T>),
							patchAt(index),
						)}

						<div className="sm:col-span-2">
							<button
								type="button"
								onClick={() => onRows(rows.filter((_row, at) => at !== index))}
								className="text-[11.5px] font-semibold text-slate-faint underline-offset-2 hover:text-danger hover:underline"
							>
								Remove
							</button>
						</div>
					</div>
				))}

				<Button
					variant="navy"
					onClick={() => onRows([...rows, blank()])}
					disabled={rows.length > 0 && !rowIsUsable(rows[rows.length - 1])}
				>
					{add}
				</Button>
			</div>
		</FieldSet>
	);
}

/**
 * A tickbox with its label, drawn as one clickable card.
 *
 * The same shape the emergency-contact permission box uses, extracted because
 * the background step needs three of them. It is here rather than in `ui/form`
 * for the reason that one is inline: the card treatment belongs to this wizard's
 * language, and a shared component would be a shared decision nobody asked for.
 */
export function Check({
	id,
	checked,
	onChange,
	label,
}: {
	id: string;
	checked: boolean;
	onChange: (on: boolean) => void;
	label: string;
}) {
	return (
		<label
			htmlFor={id}
			className="flex cursor-pointer items-start gap-3 rounded-xl border border-card-line bg-canvas-soft p-4"
		>
			<input
				id={id}
				type="checkbox"
				className="mt-0.5 h-4 w-4 shrink-0 accent-brand"
				checked={checked}
				onChange={(event) => onChange(event.target.checked)}
			/>
			<span className="text-[13px] leading-relaxed text-ink">{label}</span>
		</label>
	);
}

/**
 * A year, as a number the profile can store or nothing at all.
 *
 * `Int` on the doctype and a number input here, but an empty box has to reach
 * the server as `null` rather than as `0`: a year of zero would be a person who
 * started school before the calendar did, and it would print. Anything that is
 * not a number is dropped for the same reason.
 */
export const asYear = (value: string): number | null => {
	const trimmed = value.trim();

	if (!trimmed) return null;

	const year = Number(trimmed);

	return Number.isFinite(year) ? year : null;
};

/**
 * The seven fields as an editable block: study, training, work, licences, referees.
 *
 * **Nothing here is required and the block says so on its own face.** The lead
 * line says every part is optional and each table opens empty, because the
 * failure mode this could easily have had is somebody reading six tables as six
 * obligations and closing the tab.
 *
 * **It owns no saving.** One `value` in, one `onChange` out with the keys that
 * changed — the wizard autosaves a draft on leaving a step and the profile page
 * saves on a button, and neither of those belongs to a component that draws
 * fields. That separation is what let the second screen reuse the first
 * screen's work without inheriting its idea of what "continue" means.
 *
 * **The whole block writes to the Red Profile, not to any registration.** So it
 * is prefilled for anybody who has registered before, and correcting a
 * qualification corrects it everywhere — which is the argument
 * `install_background_fields.py` makes at length.
 */
export function BackgroundFields({
	options,
	lead = "Nothing on this screen is required. Fill in what you have and leave the rest.",
	value,
	onChange,
}: {
	options?: IdentityOptions;
	/** The line under the first heading. Two screens, two ways of saying it. */
	lead?: string;
	value: BackgroundValues;
	/** The keys that changed, so a caller holds one piece of state for all seven. */
	onChange: (values: Partial<BackgroundValues>) => void;
}) {
	const {
		profession,
		education,
		training,
		work_experience: experience,
		licences,
		driving_licences: drivingLicences,
		references,
	} = value;

	const onProfession = (next: string) => onChange({ profession: next });
	const onEducation = (rows: EducationRow[]) => onChange({ education: rows });
	const onTraining = (rows: TrainingRow[]) => onChange({ training: rows });
	const onExperience = (rows: WorkExperienceRow[]) => onChange({ work_experience: rows });
	const onLicences = (rows: LicenceRow[]) => onChange({ licences: rows });
	const onDrivingLicences = (rows: DrivingLicenceRow[]) => onChange({ driving_licences: rows });
	const onReferences = (rows: ReferenceRow[]) => onChange({ references: rows });

	// The two name-only registers come back as bare strings, because the doctype
	// behind each of them has no fields at all and the docname is the value. The
	// pickers take `{key, label}`, so they are shaped here rather than in six
	// places below.
	//
	// Optional the whole way down, and not out of habit. The options call is
	// still in flight on first paint, and the bundle and the server are deployed
	// separately — so a session that loaded this against a server predating these
	// vocabularies gets an object without them. An empty picker is something
	// somebody can still walk past; a crash is a form they cannot finish.
	const professions = (options?.professions ?? []).map((name) => ({ key: name, label: name }));
	const licenceTypes = (options?.licence_types ?? []).map((name) => ({ key: name, label: name }));
	const educationLevels = options?.education_levels ?? [];
	const drivingClasses = options?.driving_licence_classes ?? [];

	return (
		<div className="space-y-9">
			<FieldSet title="What you do" description={lead}>
				<div className="grid gap-5 sm:grid-cols-2">
					<Field
						label="Profession"
						htmlFor="bg-profession"
						hint="The nearest one. Your branch can be more specific later."
					>
						<VocabularySelect
							id="bg-profession"
							value={profession}
							onChange={onProfession}
							options={professions}
							placeholder="Choose the closest"
						/>
					</Field>
				</div>
			</FieldSet>

			<RowList
				title="Where you studied"
				description="School, college, university — whichever of them applies."
				rows={education}
				onRows={onEducation}
				blank={blankEducation}
				add="Add somewhere you studied"
				renderRow={(row, index, set, patch) => (
					<>
						<Field label="School or institution" required htmlFor={`ed-place-${index}`}>
							<TextInput
								id={`ed-place-${index}`}
								value={row.institution}
								onChange={(value) => set("institution", value)}
							/>
						</Field>

						<Field label="Level" htmlFor={`ed-level-${index}`}>
							<VocabularySelect
								id={`ed-level-${index}`}
								value={row.level}
								onChange={(value) => set("level", value)}
								options={educationLevels}
								placeholder="Choose a level"
							/>
						</Field>

						<Field
							label="Qualification"
							htmlFor={`ed-qual-${index}`}
							hint="As it is written on the certificate."
						>
							<TextInput
								id={`ed-qual-${index}`}
								value={row.qualification}
								onChange={(value) => set("qualification", value)}
							/>
						</Field>

						{/* Years, not dates. Nobody remembers the day they started
						    secondary school, and a date picker that insisted would be
						    the control people abandon the form on. */}
						<div className="grid grid-cols-2 gap-5">
							<Field label="Started" htmlFor={`ed-from-${index}`}>
								<TextInput
									id={`ed-from-${index}`}
									type="number"
									inputMode="numeric"
									value={row.started_in === null ? "" : String(row.started_in)}
									onChange={(value) => set("started_in", asYear(value))}
									placeholder="Year"
								/>
							</Field>

							<Field label="Finished" htmlFor={`ed-to-${index}`}>
								<TextInput
									id={`ed-to-${index}`}
									type="number"
									inputMode="numeric"
									value={row.finished_in === null ? "" : String(row.finished_in)}
									onChange={(value) => set("finished_in", asYear(value))}
									placeholder="Year"
									disabled={row.is_ongoing}
								/>
							</Field>
						</div>

						<div className="sm:col-span-2">
							<Check
								id={`ed-ongoing-${index}`}
								checked={row.is_ongoing}
								// Still studying and a finish year are contradictory, and
								// the one somebody just pressed is the one they mean.
								// Clearing it here is why the field above is disabled
								// rather than merely ignored — and it is one `patch`
								// rather than two `set`s for the reason `patch` exists.
								onChange={(on) => patch(on ? { is_ongoing: true, finished_in: null } : { is_ongoing: false })}
								label="I am still studying here"
							/>
						</div>

						<Field label="Certificate" htmlFor={`ed-file-${index}`} hint="If you have a copy.">
							<PrivateUpload
								id={`ed-file-${index}`}
								value={row.attachment ?? ""}
								onChange={(value) => set("attachment", value)}
								choose="Attach a certificate"
							/>
						</Field>
					</>
				)}
			/>

			<RowList
				title="Training and courses"
				description="First aid, driving, safeguarding, anything you have been taught. We will not have checked any of it — a branch verifies what it needs to."
				rows={training}
				onRows={onTraining}
				blank={blankTraining}
				add="Add a course"
				renderRow={(row, index, set) => (
					<>
						<Field label="Course" required htmlFor={`tr-name-${index}`}>
							<TextInput
								id={`tr-name-${index}`}
								value={row.course_name}
								onChange={(value) => set("course_name", value)}
							/>
						</Field>

						<Field label="Run by" htmlFor={`tr-by-${index}`} hint="Who taught it.">
							<TextInput
								id={`tr-by-${index}`}
								value={row.institution}
								onChange={(value) => set("institution", value)}
							/>
						</Field>

						<Field label="Started" htmlFor={`tr-from-${index}`}>
							<TextInput
								id={`tr-from-${index}`}
								type="date"
								value={row.started_on}
								onChange={(value) => set("started_on", value)}
							/>
						</Field>

						<Field label="Completed" htmlFor={`tr-to-${index}`}>
							<TextInput
								id={`tr-to-${index}`}
								type="date"
								value={row.completed_on}
								onChange={(value) => set("completed_on", value)}
							/>
						</Field>

						<Field label="Anything to add" htmlFor={`tr-notes-${index}`}>
							<TextArea
								id={`tr-notes-${index}`}
								value={row.remarks}
								onChange={(value) => set("remarks", value)}
								rows={2}
							/>
						</Field>

						<Field label="Certificate" htmlFor={`tr-file-${index}`} hint="If you have a copy.">
							<PrivateUpload
								id={`tr-file-${index}`}
								value={row.attachment ?? ""}
								onChange={(value) => set("attachment", value)}
								choose="Attach a certificate"
							/>
						</Field>
					</>
				)}
			/>

			<RowList
				title="What you have done"
				description="Paid work or unpaid — volunteering counts, and for a great many people it is the part that matters most."
				rows={experience}
				onRows={onExperience}
				blank={blankExperience}
				add="Add something you have done"
				renderRow={(row, index, set, patch) => (
					<>
						<Field label="Organization" required htmlFor={`we-org-${index}`}>
							<TextInput
								id={`we-org-${index}`}
								value={row.organization}
								onChange={(value) => set("organization", value)}
							/>
						</Field>

						<Field label="What you were" htmlFor={`we-role-${index}`}>
							<TextInput
								id={`we-role-${index}`}
								value={row.role}
								onChange={(value) => set("role", value)}
								placeholder="Your role there"
							/>
						</Field>

						<Field label="From" htmlFor={`we-from-${index}`}>
							<TextInput
								id={`we-from-${index}`}
								type="date"
								value={row.started_on}
								onChange={(value) => set("started_on", value)}
							/>
						</Field>

						<Field label="To" htmlFor={`we-to-${index}`}>
							<TextInput
								id={`we-to-${index}`}
								type="date"
								value={row.ended_on}
								onChange={(value) => set("ended_on", value)}
								disabled={row.is_current}
							/>
						</Field>

						<div className="sm:col-span-2">
							<Check
								id={`we-current-${index}`}
								checked={row.is_current}
								onChange={(on) => patch(on ? { is_current: true, ended_on: "" } : { is_current: false })}
								label="I am still there"
							/>
						</div>

						<Field label="What you did" htmlFor={`we-what-${index}`}>
							<TextArea
								id={`we-what-${index}`}
								value={row.summary}
								onChange={(value) => set("summary", value)}
								rows={2}
							/>
						</Field>
					</>
				)}
			/>

			<RowList
				title="Licences and registrations"
				description="A nursing register, a professional body, a trade licence — anything you are formally registered to do."
				rows={licences}
				onRows={onLicences}
				blank={blankLicence}
				add="Add a licence"
				renderRow={(row, index, set, patch) => (
					<>
						<Field label="Kind" htmlFor={`lc-type-${index}`}>
							<VocabularySelect
								id={`lc-type-${index}`}
								value={row.license_type}
								onChange={(value) => set("license_type", value)}
								options={licenceTypes}
								placeholder="Choose a kind"
							/>
						</Field>

						<Field label="What it is called" required htmlFor={`lc-name-${index}`}>
							<TextInput
								id={`lc-name-${index}`}
								value={row.license_name}
								onChange={(value) => set("license_name", value)}
							/>
						</Field>

						<Field label="Who issued it" htmlFor={`lc-issuer-${index}`}>
							<TextInput
								id={`lc-issuer-${index}`}
								value={row.institution}
								onChange={(value) => set("institution", value)}
							/>
						</Field>

						<Field label="Registration number" htmlFor={`lc-no-${index}`}>
							<TextInput
								id={`lc-no-${index}`}
								value={row.registration_no}
								onChange={(value) => set("registration_no", value)}
							/>
						</Field>

						<Field label="Valid from" htmlFor={`lc-from-${index}`}>
							<TextInput
								id={`lc-from-${index}`}
								type="date"
								value={row.valid_from}
								onChange={(value) => set("valid_from", value)}
							/>
						</Field>

						<Field label="Valid until" htmlFor={`lc-to-${index}`}>
							<TextInput
								id={`lc-to-${index}`}
								type="date"
								value={row.valid_to}
								onChange={(value) => set("valid_to", value)}
								disabled={row.does_not_expire}
							/>
						</Field>

						<div className="sm:col-span-2">
							<Check
								id={`lc-forever-${index}`}
								checked={row.does_not_expire}
								onChange={(on) =>
									patch(on ? { does_not_expire: true, valid_to: "" } : { does_not_expire: false })
								}
								label="This one does not expire"
							/>
						</div>

						<Field label="A copy of it" htmlFor={`lc-file-${index}`} hint="If you have one.">
							<PrivateUpload
								id={`lc-file-${index}`}
								value={row.attachment ?? ""}
								onChange={(value) => set("attachment", value)}
								choose="Attach a copy"
							/>
						</Field>
					</>
				)}
			/>

			<RowList
				title="Driving licence"
				description="One row per class. Holding a class here does not mean anybody will ask you to drive — that is a decision your branch makes."
				rows={drivingLicences}
				onRows={onDrivingLicences}
				blank={blankDrivingLicence}
				add="Add a class"
				renderRow={(row, index, set) => (
					<>
						<Field label="Class" required htmlFor={`dl-class-${index}`}>
							<VocabularySelect
								id={`dl-class-${index}`}
								value={row.licence_class}
								onChange={(value) => set("licence_class", value)}
								options={drivingClasses}
								placeholder="Choose a class"
							/>
						</Field>

						<Field label="Licence number" htmlFor={`dl-no-${index}`}>
							<TextInput
								id={`dl-no-${index}`}
								value={row.licence_number}
								onChange={(value) => set("licence_number", value)}
							/>
						</Field>

						<Field label="Valid until" htmlFor={`dl-to-${index}`}>
							<TextInput
								id={`dl-to-${index}`}
								type="date"
								value={row.valid_to}
								onChange={(value) => set("valid_to", value)}
							/>
						</Field>

						<Field label="A copy of it" htmlFor={`dl-file-${index}`} hint="If you have one.">
							<PrivateUpload
								id={`dl-file-${index}`}
								value={row.attachment ?? ""}
								onChange={(value) => set("attachment", value)}
								choose="Attach a copy"
							/>
						</Field>
					</>
				)}
			/>

			<RowList
				title="Someone who would speak for you"
				description="A referee, not an emergency contact — we ask for those separately, and we would not call a referee about an accident."
				rows={references}
				onRows={onReferences}
				blank={blankReference}
				add="Add a referee"
				renderRow={(row, index, set) => (
					<>
						<Field label="Their name" required htmlFor={`rf-name-${index}`}>
							<TextInput
								id={`rf-name-${index}`}
								value={row.reference_name}
								onChange={(value) => set("reference_name", value)}
							/>
						</Field>

						<Field label="How they know you" htmlFor={`rf-rel-${index}`}>
							<TextInput
								id={`rf-rel-${index}`}
								value={row.relationship}
								onChange={(value) => set("relationship", value)}
								placeholder="Former manager, teacher, colleague"
							/>
						</Field>

						<Field label="What they do" htmlFor={`rf-pos-${index}`}>
							<TextInput
								id={`rf-pos-${index}`}
								value={row.position}
								onChange={(value) => set("position", value)}
							/>
						</Field>

						<Field label="Where" htmlFor={`rf-org-${index}`}>
							<TextInput
								id={`rf-org-${index}`}
								value={row.organization}
								onChange={(value) => set("organization", value)}
							/>
						</Field>

						<Field label="Email" htmlFor={`rf-email-${index}`}>
							<TextInput
								id={`rf-email-${index}`}
								type="email"
								value={row.email}
								onChange={(value) => set("email", value)}
							/>
						</Field>

						<Field label="Phone" htmlFor={`rf-phone-${index}`}>
							<TextInput
								id={`rf-phone-${index}`}
								type="tel"
								value={row.phone}
								onChange={(value) => set("phone", value)}
							/>
						</Field>

						<Field label="Anything to add" htmlFor={`rf-notes-${index}`}>
							<TextArea
								id={`rf-notes-${index}`}
								value={row.notes}
								onChange={(value) => set("notes", value)}
								rows={2}
							/>
						</Field>
					</>
				)}
			/>
		</div>
	);
}

