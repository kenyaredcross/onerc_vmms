import type { IdentityOptions, PersonalDetails } from "../portal/types";
import { FileLink, fileNameOf } from "./FilePreview";
import { Field, FieldSet, PrivateUpload, RemoveRowButton, RowHeading, SelectInput, TextInput } from "./form";
import { Button } from "./primitives";

type DocumentType = NonNullable<IdentityOptions["supporting_document_types"]>[number];

export function registrationDetailGaps(
	value: PersonalDetails,
	types: DocumentType[] = [],
): string[] {
	const rows = value.supporting_documents ?? [];
	const gaps = types
		.filter(
			(type) => type.is_required && !rows.some((row) => row.type === type.key && row.attachment),
		)
		.map((type) => `Upload ${type.label}`);
	for (const row of rows) {
		if (row.attachment && documentTypeRequiresName(types, row.type) && !row.document_name.trim())
			gaps.push(`Name the ${row.type} document`);
	}
	return gaps;
}

function documentTypeRequiresName(types: DocumentType[], key: string): boolean {
	return Boolean(types.find((type) => type.key === key)?.requires_name);
}

const RESIDENCE_FIELDS = [
	["county", "County of residence"],
	["sub_county", "Sub-county of residence"],
	["ward", "Ward of residence"],
	["administrative_location", "Location of residence"],
	["sub_location", "Sub-location of residence"],
] as const;

const TEXT_FIELDS = [
	["middle_name", "Other names"],
	["mpesa_mobile_phone", "Mobile Money (M-Pesa) phone if different"],
	["place_of_work", "Place of work"],
	["linkedin", "LinkedIn profile"],
	["github", "GitHub profile"],
] as const;
/** Profile links an applicant gave. The server accepts only http and https. */
const PROFILE_LINKS = new Set<string>(["linkedin", "github"]);

export function isWebAddress(value: string): boolean {
	return /^https?:\/\/[^\s]+$/i.test(value.trim());
}

const CHOICE_FIELDS = [
	["marital_status", "Marital status", ["Single", "Married", "Divorced", "Widowed", "Other"]],
	["has_insurance", "KRCS insurance", ["Yes", "No"]],
	["access_to_internet", "Access to internet", ["Yes", "No", "Sometimes"]],
] as const;

/** Person-owned facts; controlled by the caller so step changes never discard them. */
export function RegistrationDetails({
	value,
	onChange,
	documentTypes = [],
	bloodGroups = [],
	documents = true,
	documentsOnly = false,
	idPrefix = "registration-details",
	showOtherNames = true,
	showProfileLinks = true,
}: {
	value: PersonalDetails;
	onChange: (value: PersonalDetails) => void;
	documentTypes?: DocumentType[];
	bloodGroups?: string[];
	documents?: boolean;
	documentsOnly?: boolean;
	idPrefix?: string;
	showOtherNames?: boolean;
	/** False where LinkedIn and GitHub are asked under Professional profiles. */
	showProfileLinks?: boolean;
}) {
	const set = (key: keyof PersonalDetails, next: unknown) => onChange({ ...value, [key]: next });
	const rows = value.supporting_documents ?? [];
	const requiredTypes = documentTypes.filter((type) => type.is_required);
	const requiredKeys = new Set(requiredTypes.map((type) => type.key));
	const optionalTypes = documentTypes.filter((type) => !type.is_required);
	// Required documents are uploaded in their own block above, so the entries
	// here are numbered among themselves: the first one shown is Document 1.
	const documentNumber = (at: number) =>
		rows.slice(0, at + 1).filter((row) => !requiredKeys.has(row.type)).length;
	const updateDocument = (at: number, patch: Partial<(typeof rows)[number]>) =>
		set(
			"supporting_documents",
			rows.map((row, index) => (index === at ? { ...row, ...patch } : row)),
		);
	return (
		<div className="space-y-6">
			{!documentsOnly && (
				<>
					<FieldSet
						title="Other Details"
						
					>
						<div className="grid gap-4 sm:grid-cols-2">
							<Field label="Blood group" htmlFor={`${idPrefix}-blood_group`}>
								<SelectInput id={`${idPrefix}-blood_group`} value={value.blood_group ?? ""}
									options={Array.from(new Set([...bloodGroups, ...(value.blood_group ? [value.blood_group] : [])]))}
									placeholder="Select blood group" onChange={(next) => set("blood_group", next)} />
							</Field>

							{TEXT_FIELDS.filter(
								([key]) =>
									(showOtherNames || key !== "middle_name") &&
									(showProfileLinks || !PROFILE_LINKS.has(key)),
							).map(([key, label]) => (
								<Field key={key} label={label} htmlFor={`${idPrefix}-${key}`}>
									<TextInput
										id={`${idPrefix}-${key}`}
										value={String(value[key] ?? "")}
										onChange={(next) => set(key, next)}
									/>
								</Field>
							))}
							{CHOICE_FIELDS.map(([key, label, options]) => (
								<Field key={key} label={label} htmlFor={`${idPrefix}-${key}`}>
									<SelectInput
										id={`${idPrefix}-${key}`}
										value={String(value[key] ?? "")}
										options={[...options]}
										onChange={(next) => set(key, next)}
									/>
								</Field>
							))}
							<Field label="Number of dependants" htmlFor={`${idPrefix}-dependants`}>
								<TextInput
									id={`${idPrefix}-dependants`}
									type="number"
									min="0"
									step="1"
									value={
										value.number_of_dependants == null ? "" : String(value.number_of_dependants)
									}
									onChange={(next) =>
										set("number_of_dependants", next === "" ? null : Number(next))
									}
								/>
							</Field>
						</div>
					</FieldSet>
					<FieldSet
						title="Additional skills"
						
					>
						{(value.additional_skills ?? []).map((row, index) => (
							<div className="mb-3 flex items-end gap-3" key={index}>
								<div className="flex-1">
									<Field
										label={`Additional skill ${index + 1}`}
										htmlFor={`${idPrefix}-skill-${index}`}
									>
										<TextInput
											id={`${idPrefix}-skill-${index}`}
											value={row.additional_skill}
											onChange={(next) =>
												set(
													"additional_skills",
													(value.additional_skills ?? []).map((held, at) =>
														at === index ? { additional_skill: next } : held,
													),
												)
											}
										/>
									</Field>
								</div>
								<RemoveRowButton
									label={`Remove skill ${index + 1}`}
									onClick={() =>
										set(
											"additional_skills",
											(value.additional_skills ?? []).filter((_, at) => at !== index),
										)
									}
								/>
							</div>
						))}
						<Button
							variant="ghost"
							onClick={() =>
								set("additional_skills", [
									...(value.additional_skills ?? []),
									{ additional_skill: "" },
								])
							}
						>
							Add another skill
						</Button>
					</FieldSet>
					<FieldSet
						title="Allergies"
						
					>
						<div className="space-y-3">
							{(value.allergies ?? []).map((row, index) => (
								<div key={index} className="flex items-end gap-3">
									<div className="flex-1">
										<Field label={`Allergy ${index + 1}`} htmlFor={`${idPrefix}-allergy-${index}`}>
											<TextInput
												id={`${idPrefix}-allergy-${index}`}
												value={row.allergy}
												onChange={(next) =>
													set(
														"allergies",
														(value.allergies ?? []).map((held, at) =>
															at === index ? { allergy: next } : held,
														),
													)
												}
											/>
										</Field>
									</div>
									<RemoveRowButton
										label={`Remove allergy ${index + 1}`}
										onClick={() =>
											set(
												"allergies",
												(value.allergies ?? []).filter((_, at) => at !== index),
											)
										}
									/>
								</div>
							))}
							<Button
								variant="ghost"
								onClick={() => set("allergies", [...(value.allergies ?? []), { allergy: "" }])}
							>
								Add allergy
							</Button>
						</div>
					</FieldSet>
				</>
			)}
			{documents && (
				<>
					{/* A document the society requires is its own field, not a row
					    somebody has to add and then pick a type for. In Kenya that is
					    the Certificate of Good Conduct. Stored as a supporting
					    document of that type, so the server's check is unchanged. */}
					{requiredTypes.length > 0 && (
						<FieldSet title="Required documents">
							<div className="grid gap-4 sm:grid-cols-2">
								{requiredTypes.map((type) => {
									const at = rows.findIndex((row) => row.type === type.key);
									return (
										<Field
											key={type.key}
											label={type.label}
											required
											htmlFor={`${idPrefix}-required-${type.key}`}
										>
											<PrivateUpload
												id={`${idPrefix}-required-${type.key}`}
												value={at === -1 ? "" : (rows[at].attachment ?? "")}
												choose={`Upload ${type.label}`}
												onChange={(next) =>
													at === -1
														? set("supporting_documents", [
																...rows,
																{ type: type.key, document_name: "", attachment: next },
															])
														: updateDocument(at, { attachment: next })
												}
											/>
										</Field>
									);
								})}
							</div>
						</FieldSet>
					)}

					<FieldSet title="Supporting documents">
						<div className="space-y-4">
							{rows.map((row, index) =>
								requiredKeys.has(row.type) ? null : (
									<div key={index} className="space-y-3 rounded-xl border border-card-line p-4">
										<RowHeading
											label={`Document ${documentNumber(index)}`}
											removeLabel={`Remove document ${documentNumber(index)}`}
											onRemove={() =>
												set(
													"supporting_documents",
													rows.filter((_, at) => at !== index),
												)
											}
										/>
										<Field
											label="Document type"
											htmlFor={`${idPrefix}-doc-type-${index}`}
										>
											<select
												id={`${idPrefix}-doc-type-${index}`}
												className="w-full rounded-lg border border-card-line p-2 text-sm"
												value={row.type}
												onChange={(event) => updateDocument(index, { type: event.target.value })}
											>
												<option value="">Select document type…</option>
												{optionalTypes.map((type) => (
													<option key={type.key} value={type.key}>
														{type.label}
													</option>
												))}
												{row.type && !documentTypes.some((type) => type.key === row.type) && (
													<option value={row.type}>{row.type}</option>
												)}
											</select>
										</Field>
										<Field
											label="Document name"
											required={documentTypeRequiresName(documentTypes, row.type)}
											htmlFor={`${idPrefix}-doc-name-${index}`}
											hint="Required for Other documents."
										>
											<TextInput
												id={`${idPrefix}-doc-name-${index}`}
												value={row.document_name}
												onChange={(next) => updateDocument(index, { document_name: next })}
											/>
										</Field>
										<PrivateUpload
											id={`${idPrefix}-doc-file-${index}`}
											value={row.attachment ?? ""}
											choose={`Upload ${row.type || "document"}`}
											onChange={(next) => updateDocument(index, { attachment: next })}
										/>
									</div>
								),
							)}
							<Button
								variant="ghost"
								onClick={() =>
									set("supporting_documents", [
										...rows,
										{ type: "", document_name: "", attachment: "" },
									])
								}
							>
								Add supporting document
							</Button>
						</div>
					</FieldSet>
				</>
			)}
		</div>
	);
}

export function RegistrationDetailsSummary({
	value,
	evidenceContext,
	showProfileLinks = true,
}: {
	value?: PersonalDetails;
	evidenceContext?: { doctype: string; name: string };
	/** False where LinkedIn and GitHub are shown under Professional profiles. */
	showProfileLinks?: boolean;
}) {
	if (!value) return null;
	const items = [
		["blood_group", "Blood group"] as const,
		...TEXT_FIELDS.filter(([key]) => showProfileLinks || !PROFILE_LINKS.has(key)),
		...RESIDENCE_FIELDS,
		...CHOICE_FIELDS.map(([key, label]) => [key, label] as const),
		["number_of_dependants", "Number of dependants"] as const,
	] as const;
	return (
		<div className="space-y-3 text-sm">
			<dl className="grid gap-3 sm:grid-cols-2">
				{items.map(([key, label]) =>
					value[key] != null && value[key] !== "" ? (
						<div key={key}>
							<dt className="text-xs text-muted">{label}</dt>
							<dd className="break-words text-ink">
								{PROFILE_LINKS.has(key) && isWebAddress(String(value[key])) ? (
									<a
										href={String(value[key])}
										target="_blank"
										rel="noopener noreferrer"
										className="font-semibold text-ink underline underline-offset-2"
									>
										{String(value[key])}
									</a>
								) : (
									String(value[key])
								)}
							</dd>
						</div>
					) : null,
				)}
			</dl>
			{!!value.additional_skills?.length && (
				<p>
					Additional skills: {value.additional_skills.map((row) => row.additional_skill).join(", ")}
				</p>
			)}
			{!!value.allergies?.length && (
				<p>Allergies: {value.allergies.map((row) => row.allergy).join(", ")}</p>
			)}
			{!!value.supporting_documents?.length && (
				<ul className="space-y-1">
					{value.supporting_documents.map((row, index) => (
						<li key={index}>
							{[row.type, row.document_name].filter(Boolean).join(" · ") || "Document"}:{" "}
							{row.attachment ? (
								<FileLink
									url={
										evidenceContext
											? `/api/method/vmmsx.api.registration.download_evidence?${new URLSearchParams({ ...evidenceContext, attachment: row.attachment })}`
											: row.attachment
									}
									name={fileNameOf(row.attachment)}
								/>
							) : (
								"No file"
							)}
						</li>
					))}
				</ul>
			)}
		</div>
	);
}
