import { type ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage } from "../lib/api";
import { formatDate } from "../lib/format";
import type {
	TermsApproach,
	TermsCertificationRequirement,
	TermsItineraryRow,
	TermsMethodology,
	TermsMission,
	TermsResource,
	TermsStakeholder,
	GeoNode,
	ProjectSummary,
} from "../portal/types";
import { GeoSelects, selectedNode } from "../ui/GeoSelects";
import { Button, Card, ErrorNote, SectionTitle, cx } from "../ui/primitives";
import { INPUT, Labelled } from "./Projects";

/**
 * Writing a mission, and reading one.
 *
 * A `VMMS Terms of Reference` is a society's mission document: the situation it
 * answers to, who it has to deal with, what it sets out to achieve and leave
 * behind, how it will go about it, day by day, with what resources, and what a
 * volunteer must hold to take part. Every deployment points at one, and
 * accepting a deployment assignment is accepting exactly this text — there is no
 * separate contract in this app.
 *
 * **That is why it submits, and why the editor is drawn around the submit.**
 * A draft is edited freely. Submitting is a deliberate second act that freezes
 * the wording, and from then on the page is a document rather than a form: a
 * change is an amendment, which is a new record, so what somebody already agreed
 * to is never rewritten underneath them. The screen says which state it is in
 * before somebody starts typing rather than after they press save.
 *
 * **Tabs, because the document has parts and nobody writes them in one sitting.**
 * The four match the shape a mission actually gets written in — the situation and
 * who is involved, then what it is for, then when and with what, then the rules
 * about who may go. Each tab saves on its own, and a tab the editor did not send
 * is left alone on the server rather than emptied, so saving the mission tab
 * cannot silently delete the itinerary on the next one.
 *
 * **The row editors are one component, and the columns are data.** Six tables
 * with six bespoke grids would be six places to get a delete button wrong. What
 * varies between them is a list of fields; what does not vary is add, remove and
 * edit-in-place, and that is written once.
 */

/* ------------------------------------------------------------------ tables */

/** One column of a row editor: which key it writes and how it is drawn. */
export type Column<Row> = {
	key: keyof Row & string;
	label: string;
	kind?: "text" | "area" | "date" | "time" | "number" | "select" | "check";
	/** Roughly how wide, in grid columns out of twelve. */
	span?: number;
	options?: Array<{ value: string; label: string }>;
	placeholder?: string;
};

/**
 * A grid of rows a coordinator adds to, edits in place, and removes from.
 *
 * **Rows are keyed by position, deliberately.** A child row has no identity
 * until it is saved, and inventing a client-side one would be a second identity
 * to reconcile with the server's. Editing is by index and so is removal, which
 * is exactly what the underlying array supports.
 */
export function RowEditor<Row extends object>({
	title,
	lead,
	columns,
	rows,
	onChange,
	blank,
	addLabel,
	empty,
}: {
	title: string;
	lead?: string;
	columns: Array<Column<Row>>;
	rows: Row[];
	onChange: (rows: Row[]) => void;
	blank: () => Row;
	addLabel: string;
	empty: string;
}) {
	// Spreading and overwriting one key produces the same shape back, but TypeScript
	// cannot see that through a generic, so the cast is stated once here rather
	// than at each of the six call sites.
	const set = (index: number, key: string, value: unknown) =>
		onChange(rows.map((row, at) => (at === index ? ({ ...row, [key]: value } as Row) : row)));

	return (
		<div>
			<div className="flex flex-wrap items-baseline justify-between gap-2">
				<p className="text-[12px] font-bold uppercase tracking-wider text-slate-faint">{title}</p>
				<button
					type="button"
					onClick={() => onChange([...rows, blank()])}
					className="text-[12px] font-semibold text-navy hover:underline"
				>
					+ {addLabel}
				</button>
			</div>

			{lead && <p className="mt-1 text-[11.5px] text-slate-faint">{lead}</p>}

			{rows.length === 0 ? (
				<p className="mt-2 text-[12.5px] text-slate-faint">{empty}</p>
			) : (
				<ul className="mt-2.5 space-y-2.5">
					{rows.map((row, index) => (
						<li
							key={index}
							className="rounded-card border border-hairline bg-surface/60 px-3 py-2.5"
						>
							<div className="grid grid-cols-12 gap-2.5">
								{columns.map((column) => (
									<div
										key={column.key}
										className={SPANS[column.span ?? 12] ?? "col-span-12"}
									>
										<label className="block">
											<span className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-slate-faint">
												{column.label}
											</span>
											<Input
												column={column}
												value={row[column.key as keyof Row]}
												onChange={(value) => set(index, column.key, value)}
											/>
										</label>
									</div>
								))}
							</div>

							<div className="mt-2 text-right">
								<button
									type="button"
									onClick={() => onChange(rows.filter((_, at) => at !== index))}
									className="text-[11.5px] font-semibold text-slate-faint hover:text-signal"
								>
									Remove
								</button>
							</div>
						</li>
					))}
				</ul>
			)}
		</div>
	);
}

// Tailwind's class scanner needs whole class names in the source, so the spans
// are a lookup rather than a template string.
const SPANS: Record<number, string> = {
	2: "col-span-4 sm:col-span-2",
	3: "col-span-6 sm:col-span-3",
	4: "col-span-6 sm:col-span-4",
	5: "col-span-12 sm:col-span-5",
	6: "col-span-12 sm:col-span-6",
	8: "col-span-12 sm:col-span-8",
	12: "col-span-12",
};

function Input<Row>({
	column,
	value,
	onChange,
}: {
	column: Column<Row>;
	value: unknown;
	onChange: (value: unknown) => void;
}) {
	const shown = value === null || value === undefined ? "" : String(value);

	if (column.kind === "check") {
		return (
			<span className="flex min-h-[38px] items-center gap-2 rounded-card border border-hairline-strong bg-white px-3 py-2 text-[12.5px] text-slate-body">
				<input
					type="checkbox"
					checked={Boolean(value)}
					onChange={(event) => onChange(event.target.checked)}
				/>
				Required
			</span>
		);
	}

	if (column.kind === "area") {
		return (
			<textarea
				className={cx(INPUT, "min-h-[56px] resize-y bg-white")}
				value={shown}
				placeholder={column.placeholder}
				onChange={(event) => onChange(event.target.value)}
			/>
		);
	}

	if (column.kind === "select") {
		return (
			<select
				className={cx(INPUT, "bg-white")}
				value={shown}
				onChange={(event) => onChange(event.target.value)}
			>
				<option value="">Select…</option>
				{(column.options ?? []).map((option) => (
					<option key={option.value} value={option.value}>
						{option.label}
					</option>
				))}
			</select>
		);
	}

	return (
		<input
			type={
				column.kind === "date"
					? "date"
					: column.kind === "time"
						? "time"
						: column.kind === "number"
							? "number"
							: "text"
			}
			className={cx(INPUT, "bg-white")}
			value={shown}
			placeholder={column.placeholder}
			onChange={(event) =>
				onChange(
					column.kind === "number"
						? event.target.value === ""
							? null
							: Number(event.target.value)
						: event.target.value,
				)
			}
		/>
	);
}

/* ------------------------------------------------------------------ editor */

const TABS = [
	{ key: "mission", label: "Mission" },
	{ key: "aims", label: "Aims & approach" },
	{ key: "plan", label: "Itinerary & resources" },
	{ key: "rules", label: "Requirements" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function toDateTimeLocal(value: string | null): string {
	return value ? value.slice(0, 16).replace(" ", "T") : "";
}

/**
 * The mission editor. One tab at a time, each saving only what it holds.
 *
 * **Only for a draft.** A submitted terms of reference is shown by `MissionView`
 * instead, because its wording is what somebody agreed to and the server refuses
 * a write to it — offering a form that would be refused on save is two answers.
 */
export function MissionEditor({
	terms,
	onSaved,
}: {
	terms: TermsMission;
	onSaved: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [tab, setTab] = useState<TabKey>("mission");
	const [busy, setBusy] = useState(false);
	const [saved, setSaved] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const [torName, setTorName] = useState(terms.tor_name);
	const [project, setProject] = useState(terms.project ?? "");
	const [isActive, setIsActive] = useState(terms.is_active);
	const [duration, setDuration] = useState(String(terms.default_duration_days ?? 0));
	const [approvalMode, setApprovalMode] = useState(terms.approval_mode ?? "direct");
	const [notes, setNotes] = useState(terms.notes ?? "");
	const [geoChain, setGeoChain] = useState<GeoNode[]>([]);
	const [geoRestored, setGeoRestored] = useState(!terms.geo_scope);
	const [background, setBackground] = useState(terms.mission_background ?? "");
	const [purpose, setPurpose] = useState(terms.purpose ?? "");
	const [responsibilities, setResponsibilities] = useState(terms.responsibilities ?? "");
	const [startsOn, setStartsOn] = useState(toDateTimeLocal(terms.expected_start_date));
	const [endsOn, setEndsOn] = useState(toDateTimeLocal(terms.expected_end_date));

	const [requirements, setRequirements] = useState<TermsCertificationRequirement[]>(
		terms.certification_requirements ?? [
			...terms.required_certifications.map((certification_type) => ({
				certification_type,
				is_mandatory: true,
				requirement_notes: null,
			})),
			...terms.desirable_certifications.map((certification_type) => ({
				certification_type,
				is_mandatory: false,
				requirement_notes: null,
			})),
		],
	);
	const [stakeholders, setStakeholders] = useState<TermsStakeholder[]>(terms.stakeholders);
	const [objectives, setObjectives] = useState(terms.objectives);
	const [outputs, setOutputs] = useState(terms.expected_outputs);
	const [approach, setApproach] = useState<TermsApproach[]>(terms.approach_methods);
	const [itinerary, setItinerary] = useState<TermsItineraryRow[]>(terms.itinerary);
	const [resources, setResources] = useState<TermsResource[]>(terms.resources);

	const vocabularies = useFrappeGetCall<{
		message: {
			methodologies: TermsMethodology[];
			certification_types: Array<{
				name: string;
				certification_type_name: string;
				description: string | null;
			}>;
		};
	}>(
		API.torMethodologies,
		undefined,
		"admin:tor:vocabularies",
	);

	const projects = useFrappeGetCall<{ message: { projects: ProjectSummary[] } }>(
		API.branchProjects,
		{ mine: 0 },
		"admin:projects:for-terms-editor",
	);

	const restoredGeo = useFrappeGetCall<{ message: { chain: GeoNode[] } }>(
		API.geoChain,
		terms.geo_scope ? { node: terms.geo_scope } : undefined,
		terms.geo_scope ? `geo:path:${terms.geo_scope}` : null,
	);

	useEffect(() => {
		if (geoRestored || !restoredGeo.data?.message?.chain) return;
		setGeoChain(restoredGeo.data.message.chain);
		setGeoRestored(true);
	}, [geoRestored, restoredGeo.data]);

	const methodOptions = useMemo(
		() =>
				(vocabularies.data?.message?.methodologies ?? []).map((row) => ({
				value: row.name,
				label: row.methodology_name,
			})),
		[vocabularies.data],
	);

	const certificationOptions = useMemo(
		() =>
			(vocabularies.data?.message?.certification_types ?? []).map((row) => ({
				value: row.name,
				label: row.certification_type_name,
			})),
		[vocabularies.data],
	);

	const projectOptions = (projects.data?.message?.projects ?? []).filter(
		(row) => row.is_open || row.name === terms.project,
	);
	const geoNode = selectedNode(geoChain);

	// Each tab sends only the fields it owns. A payload carrying every table on
	// every save would make editing the itinerary a write to the objectives, and
	// the last tab saved would quietly win over whatever another window did.
	const payloadFor = (which: TabKey): Record<string, unknown> => {
		if (which === "mission") {
			return {
				tor_name: torName.trim(),
				project: project || null,
				is_active: isActive,
				mission_background: background,
				purpose,
				expected_start_date: startsOn || null,
				expected_end_date: endsOn || null,
				default_duration_days: duration ? Number(duration) : 0,
				geo_scope: geoRestored ? (geoNode?.name ?? null) : terms.geo_scope,
				stakeholders,
			};
		}

		if (which === "aims") {
			return { objectives, expected_outputs: outputs, approach_methods: approach };
		}

		if (which === "plan") {
			return { itinerary, resources };
		}

		return {
			responsibilities,
			approval_mode: approvalMode,
			notes,
			required_certifications: requirements,
		};
	};

	const save = async () => {
		setBusy(true);
		setFailure(null);
		setSaved(false);

		try {
			if (tab === "mission" && !torName.trim()) {
				setFailure("The title of mission is required.");
				return;
			}

			await call.post(API.updateTerms, { name: terms.name, ...payloadFor(tab) });
			setSaved(true);
			onSaved();
		} catch (problem) {
			setFailure(errorMessage(problem, "That was not saved."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card>
			<div className="flex flex-wrap items-center gap-1.5 border-b border-hairline pb-3">
				{TABS.map((entry) => (
					<button
						key={entry.key}
						type="button"
						onClick={() => {
							setTab(entry.key);
							setSaved(false);
						}}
						className={cx(
							"rounded-full px-3.5 py-1.5 text-[12.5px] font-semibold transition",
							tab === entry.key
								? "bg-navy text-white"
								: "text-slate-body hover:bg-surface hover:text-navy",
						)}
					>
						{entry.label}
					</button>
				))}
			</div>

			<div className="pt-4">
				{tab === "mission" && (
					<div className="space-y-5">
						<div className="grid gap-4 sm:grid-cols-2">
							<Labelled label="Title of mission" hint="What your society calls this piece of work.">
								<input
									className={INPUT}
									value={torName}
									onChange={(event) => setTorName(event.target.value)}
								/>
							</Labelled>
							<Labelled label="Reference" hint="Stable after creation; deployments point to this key.">
								<input className={cx(INPUT, "bg-surface")} value={terms.tor_key} readOnly />
							</Labelled>
							<Labelled label="Project" hint="Optional. The programme these terms belong to.">
								<select className={INPUT} value={project} onChange={(event) => setProject(event.target.value)}>
									<option value="">No project</option>
									{terms.project && !projectOptions.some((row) => row.name === terms.project) && (
										<option value={terms.project}>{terms.project_name ?? terms.project}</option>
									)}
									{projectOptions.map((row) => (
										<option key={row.name} value={row.name}>
											{row.project_name}
										</option>
									))}
								</select>
							</Labelled>
							<Labelled label="Availability" hint="Inactive terms take no new deployments or requests.">
								<span className="flex min-h-[38px] items-center gap-2 rounded-card border border-hairline-strong bg-white px-3 py-2 text-[13px] text-slate-body">
									<input
										type="checkbox"
										checked={isActive}
										onChange={(event) => setIsActive(event.target.checked)}
									/>
									Active for new work
								</span>
							</Labelled>
							<Labelled
								label="Expected start"
								hint="Optional. Offered as the default when a deployment is set up under these terms."
							>
								<input
									type="datetime-local"
									className={INPUT}
									value={startsOn}
									onChange={(event) => setStartsOn(event.target.value)}
								/>
							</Labelled>
							<Labelled label="Expected end" hint="Optional, and never a rule.">
								<input
									type="datetime-local"
									className={INPUT}
									value={endsOn}
									onChange={(event) => setEndsOn(event.target.value)}
								/>
							</Labelled>
							<Labelled label="Usual duration (days)" hint="Zero means there is no usual length.">
								<input
									type="number"
									min="0"
									className={INPUT}
									value={duration}
									onChange={(event) => setDuration(event.target.value)}
								/>
							</Labelled>
						</div>

						<div>
							<p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-faint">
								Where these terms may be used
							</p>
							<GeoSelects
								chain={geoChain}
								onChain={setGeoChain}
								idPrefix={`terms-${terms.name}`}
								disabled={!geoRestored}
							/>
							<p className="mt-2 text-[12px] text-slate-faint">
								Optional. Leave it empty to allow these terms anywhere.
							</p>
							{restoredGeo.error && (
								<div className="mt-2">
									<ErrorNote>
										{errorMessage(restoredGeo.error, "The current geographic scope could not be loaded.")}
									</ErrorNote>
								</div>
							)}
						</div>

						<Labelled
							label="Purpose"
							hint="One or two sentences. It appears wherever these terms are listed."
						>
							<textarea
								className={cx(INPUT, "min-h-[64px] resize-y")}
								value={purpose}
								onChange={(event) => setPurpose(event.target.value)}
							/>
						</Labelled>

						<Labelled
							label="Mission background"
							hint="What happened, what is needed, and what has already been done."
						>
							<textarea
								className={cx(INPUT, "min-h-[140px] resize-y")}
								value={background}
								onChange={(event) => setBackground(event.target.value)}
							/>
						</Labelled>

						<RowEditor<TermsStakeholder>
							title="Stakeholders"
							lead="Who this mission has to deal with, and how to reach them. Printed on the document a deployed volunteer carries."
							addLabel="Add a stakeholder"
							empty="Nobody named yet."
							rows={stakeholders}
							onChange={setStakeholders}
							blank={() => ({
								designation: "",
								full_name: "",
								phone_number: "",
								email: "",
							})}
							columns={[
								{ key: "designation", label: "Designation", span: 4, placeholder: "County Commissioner" },
								{ key: "full_name", label: "Name", span: 3 },
								{ key: "phone_number", label: "Phone", span: 3 },
								{ key: "email", label: "Email", span: 2 },
							]}
						/>
					</div>
				)}

				{tab === "aims" && (
					<div className="space-y-6">
						<RowEditor
							title="Objectives"
							lead="What this mission sets out to achieve. Numbered on the printed document in this order."
							addLabel="Add an objective"
							empty="No objectives written yet."
							rows={objectives}
							onChange={setObjectives}
							blank={() => ({ objective: "" })}
							columns={[{ key: "objective", label: "Objective", kind: "area" }]}
						/>

						<RowEditor
							title="Expected outputs"
							lead="What the mission will leave behind."
							addLabel="Add an output"
							empty="No outputs written yet."
							rows={outputs}
							onChange={setOutputs}
							blank={() => ({ output: "" })}
							columns={[{ key: "output", label: "Output", kind: "area" }]}
						/>

						<RowEditor<TermsApproach>
							title="Approach"
							lead={
								methodOptions.length > 0
									? "How the work will be done, from your society's own register of methods."
									: "Your society has not set up any methodologies yet. Add them on the desk and they appear here."
							}
							addLabel="Add a method"
							empty="No approach described yet."
							rows={approach}
							onChange={setApproach}
							blank={() => ({ methodology: "", notes: "" })}
							columns={[
								{
									key: "methodology",
									label: "Methodology",
									kind: "select",
									span: 4,
									options: methodOptions,
								},
								{
									key: "notes",
									label: "What it means here",
									kind: "area",
									span: 8,
									placeholder: "Who it reaches, how many, over what period.",
								},
							]}
						/>
					</div>
				)}

				{tab === "plan" && (
					<div className="space-y-6">
						<RowEditor<TermsItineraryRow>
							title="Itinerary"
							lead="The plan by day. Every date has to fall inside the mission's own period."
							addLabel="Add a day"
							empty="No itinerary yet."
							rows={itinerary}
							onChange={setItinerary}
							blank={() => ({
								activity_date: "",
								activity_time: "",
								activity: "",
								person_responsible: "",
							})}
							columns={[
								{ key: "activity_date", label: "Date", kind: "date", span: 3 },
								{ key: "activity_time", label: "Time", kind: "time", span: 2 },
								{ key: "activity", label: "Activity", kind: "area", span: 4 },
								{ key: "person_responsible", label: "Led by", span: 3 },
							]}
						/>

						<div>
							<RowEditor<TermsResource>
								title="Resources"
								lead="What the mission needs and what it is expected to cost."
								addLabel="Add a resource"
								empty="Nothing listed yet."
								rows={resources}
								onChange={setResources}
								blank={() => ({
									resource: "",
									needed_on: "",
									quantity: null,
									unit: "",
									unit_cost: null,
									donor: "",
								})}
								columns={[
									{ key: "resource", label: "Resource", span: 4, placeholder: "Fuel" },
									{ key: "needed_on", label: "Needed on", kind: "date", span: 2 },
									{ key: "quantity", label: "Qty", kind: "number", span: 2 },
									{ key: "unit", label: "Unit", span: 2, placeholder: "litres" },
									{ key: "unit_cost", label: "Unit cost", kind: "number", span: 2 },
									{ key: "donor", label: "Donor", span: 4 },
								]}
							/>

							<p className="mt-2 text-[11.5px] text-slate-faint">
								Nothing here totals across a project or reconciles against what was actually
								spent. Money paid to volunteers flows through the stipend forms, which are
								anchored to a place and a period rather than to a mission.
							</p>
						</div>
					</div>
				)}

				{tab === "rules" && (
					<div className="space-y-5">
						<Labelled
							label="Responsibilities"
							hint="What a volunteer deployed under these terms is expected to do. One per line."
						>
							<textarea
								className={cx(INPUT, "min-h-[140px] resize-y")}
								value={responsibilities}
								onChange={(event) => setResponsibilities(event.target.value)}
							/>
						</Labelled>

						<RowEditor<TermsCertificationRequirement>
							title="Required certifications"
							lead="Mandatory rows filter candidates; desirable rows rank them higher without excluding them."
							addLabel="Add a certification"
							empty="No certification requirements. Anybody deployable is a candidate."
							rows={requirements}
							onChange={setRequirements}
							blank={() => ({
								certification_type: "",
								is_mandatory: true,
								requirement_notes: "",
							})}
							columns={[
								{
									key: "certification_type",
									label: "Certification type",
									kind: "select",
									span: 5,
									options: certificationOptions,
								},
								{ key: "is_mandatory", label: "Mandatory", kind: "check", span: 3 },
								{ key: "requirement_notes", label: "Notes", span: 4 },
							]}
						/>

						<div className="grid gap-4 sm:grid-cols-2">
							<Labelled
								label="Approval mode"
								hint="Direct fulfils locally; routed sends a deployment request through approval."
							>
								<select
									className={INPUT}
									value={approvalMode}
									onChange={(event) => setApprovalMode(event.target.value)}
								>
									<option value="direct">Direct</option>
									<option value="routed">Routed</option>
								</select>
							</Labelled>

							<Labelled label="Notes" hint="Anything about these terms that is not covered above.">
								<textarea
									className={cx(INPUT, "min-h-[84px] resize-y")}
									value={notes}
									onChange={(event) => setNotes(event.target.value)}
								/>
							</Labelled>
						</div>

						{terms.amended_from && (
							<Labelled label="Amended from" hint="The submitted document this draft replaces.">
								<input className={cx(INPUT, "bg-surface")} value={terms.amended_from} readOnly />
							</Labelled>
						)}
					</div>
				)}
			</div>

			{failure && (
				<div className="mt-4">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}

			<div className="mt-5 flex flex-wrap items-center gap-3 border-t border-hairline pt-4">
				<Button disabled={busy} onClick={() => void save()}>
					{busy ? "Saving…" : `Save ${TABS.find((entry) => entry.key === tab)?.label.toLowerCase()}`}
				</Button>
				{saved && <span className="text-[12px] font-semibold text-navy">Saved.</span>}
				<span className="ml-auto text-[11.5px] text-slate-faint">
					Each tab saves on its own. The others are left exactly as they are.
				</span>
			</div>
		</Card>
	);
}

/* -------------------------------------------------------------------- view */

/**
 * A submitted mission, read rather than edited.
 *
 * The society's own rendered document sits above this on the page — that is the
 * same markup the PDF is built from. What this adds is the structured half a
 * template cannot show as usefully: the itinerary as a list of days, the
 * resources with their totals, the stakeholders with their numbers.
 */
export function MissionView({ terms }: { terms: TermsMission }) {
	const parts: Array<[string, ReactNode]> = [];

	if (terms.mission_background) {
		parts.push(["Mission background", <p className="whitespace-pre-line">{terms.mission_background}</p>]);
	}

	if (terms.objectives.length > 0) {
		parts.push([
			"Objectives",
			<ol className="list-decimal space-y-1 pl-4">
				{terms.objectives.map((row, index) => (
					<li key={index}>{row.objective}</li>
				))}
			</ol>,
		]);
	}

	if (terms.expected_outputs.length > 0) {
		parts.push([
			"Expected outputs",
			<ul className="list-disc space-y-1 pl-4">
				{terms.expected_outputs.map((row, index) => (
					<li key={index}>{row.output}</li>
				))}
			</ul>,
		]);
	}

	if (terms.approach_methods.length > 0) {
		parts.push([
			"Approach",
			<ul className="space-y-1.5">
				{terms.approach_methods.map((row, index) => (
					<li key={index}>
						<span className="font-semibold text-ink">{row.methodology}</span>
						{row.notes ? ` — ${row.notes}` : ""}
					</li>
				))}
			</ul>,
		]);
	}

	if (terms.itinerary.length > 0) {
		parts.push([
			"Itinerary",
			<ul className="space-y-1">
				{terms.itinerary.map((row, index) => (
					<li key={index}>
						<span className="font-semibold text-ink">
							{row.activity_date ? formatDate(row.activity_date) : "—"}
						</span>
						{row.activity_time ? ` ${row.activity_time.slice(0, 5)}` : ""} · {row.activity}
						{row.person_responsible ? ` (${row.person_responsible})` : ""}
					</li>
				))}
			</ul>,
		]);
	}

	if (terms.stakeholders.length > 0) {
		parts.push([
			"Stakeholders",
			<ul className="space-y-1">
				{terms.stakeholders.map((row, index) => (
					<li key={index}>
						<span className="font-semibold text-ink">{row.designation}</span>
						{row.full_name ? ` — ${row.full_name}` : ""}
						{row.phone_number ? ` · ${row.phone_number}` : ""}
						{row.email ? ` · ${row.email}` : ""}
					</li>
				))}
			</ul>,
		]);
	}

	if (terms.resources.length > 0) {
		parts.push([
			"Resources",
			<div className="overflow-x-auto">
				<table className="w-full min-w-[30rem] text-[12.5px]">
					<thead>
						<tr className="text-[11px] uppercase tracking-wide text-slate-faint">
							<th className="pb-1.5 text-left font-bold">Resource</th>
							<th className="pb-1.5 text-left font-bold">Needed on</th>
							<th className="pb-1.5 text-right font-bold">Qty</th>
							<th className="pb-1.5 text-left font-bold">Unit</th>
							<th className="pb-1.5 text-right font-bold">Unit cost</th>
							<th className="pb-1.5 text-right font-bold">Total</th>
							<th className="pb-1.5 text-left font-bold">Donor</th>
						</tr>
					</thead>
					<tbody>
						{terms.resources.map((row, index) => (
							<tr key={index} className="border-t border-hairline">
								<td className="py-1.5">{row.resource}</td>
								<td className="py-1.5">
									{row.needed_on ? formatDate(row.needed_on) : "Throughout"}
								</td>
								<td className="py-1.5 text-right">{row.quantity ?? ""}</td>
								<td className="py-1.5">{row.unit}</td>
								<td className="py-1.5 text-right">{row.unit_cost ?? ""}</td>
								<td className="py-1.5 text-right font-semibold">{row.total_cost ?? ""}</td>
								<td className="py-1.5">{row.donor}</td>
							</tr>
						))}
					</tbody>
					<tfoot>
						<tr className="border-t border-hairline-strong">
							<td className="pt-1.5 font-semibold" colSpan={5}>
								Total
							</td>
							<td className="pt-1.5 text-right font-bold text-ink">{terms.resources_total}</td>
							<td />
						</tr>
					</tfoot>
				</table>
			</div>,
		]);
	}

	if ((terms.certification_requirements ?? []).length > 0) {
		parts.push([
			"Certification requirements",
			<ul className="space-y-1">
				{(terms.certification_requirements ?? []).map((row, index) => (
					<li key={`${row.certification_type}-${index}`}>
						<span className="font-semibold text-ink">{row.certification_type}</span>
						{row.is_mandatory ? " · mandatory" : " · desirable"}
						{row.requirement_notes ? ` — ${row.requirement_notes}` : ""}
					</li>
				))}
			</ul>,
		]);
	}

	if (parts.length === 0) return null;

	return (
		<Card>
			<SectionTitle>The mission in detail</SectionTitle>
			<div className="mt-3 space-y-5">
				{parts.map(([title, body]) => (
					<div key={title}>
						<p className="text-[11px] font-bold uppercase tracking-wider text-slate-faint">
							{title}
						</p>
						<div className="mt-1.5 text-[12.5px] leading-relaxed text-slate-body">{body}</div>
					</div>
				))}
			</div>
		</Card>
	);
}
