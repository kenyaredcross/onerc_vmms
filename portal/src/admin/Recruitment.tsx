import { useEffect, useState } from "react";
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
import { Link, useNavigate, useParams } from "react-router-dom";

import { API, errorMessage } from "../lib/api";
import { branchPath, formatDate } from "../lib/format";
import { MultiCombo } from "../ui/form";
import { Icon } from "../ui/icons";
import { RowEditor } from "./Mission";
import {
	Avatar,
	BackLink,
	Board,
	BoardCard,
	BoardColumn,
	Button,
	ButtonLink,
	Card,
	Cell,
	Check,
	ConfirmModal,
	DecisionCard,
	Detail,
	DetailList,
	Empty,
	ErrorNote,
	Field,
	FieldGrid,
	FilterSelect,
	FormSection,
	Metric,
	MetricGrid,
	NameCell,
	PageHead,
	Row,
	SearchBox,
	SectionHead,
	Select,
	Spinner,
	StatusBadge,
	Table,
	Tabs,
	TextArea,
	TextInput,
	Toolbar,
	cx,
	useToast,
} from "./ui/kit";

/**
 * Recruitment — the society's job openings, and the people who answered them.
 *
 * **The third door into the society.** Volunteering and membership each have a
 * queue in this console; an opening did not, and a coordinator who wanted to
 * advertise one or read the answers had to go to the Frappe desk. These four
 * screens close that, and they do it without inventing a record: everything
 * below reads and writes HRMS's own `Job Opening` and `Job Applicant` through
 * `api/hr.py`, so a society that also uses HRMS's desk views is looking at
 * exactly one truth. See `hr/services/recruitment.py` for what that costs and
 * what it buys.
 *
 * **Two flags, and they are not the same question.** `status` is whether the
 * society is still recruiting; `publish` is whether the advertisement is on the
 * website at all. An opening can honestly be Open and unpublished — filled by
 * invitation — so the board shows both and neither stands in for the other.
 *
 * **A withdrawal is not a status.** Somebody taking themselves out is a date
 * this app writes, not a decision the society made, so a withdrawn application
 * keeps whatever status the pipeline had reached and carries a separate chip.
 * Overwriting "Shortlisted" with "Withdrawn" would lose the fact that the
 * society had said yes before the person left.
 */

interface Pipeline {
	total: number;
	withdrawn: number;
	[status: string]: number;
}

interface OpeningRow {
	name: string;
	job_title: string;
	status: string;
	designation: string | null;
	department: string | null;
	company: string | null;
	location: string | null;
	vacancies: number | null;
	closes_on: string | null;
	purpose: string | null;
	is_published: boolean;
	is_closing: boolean;
	url: string | null;
	modified: string;
	pipeline: Pipeline;
}

interface OpeningsAnswer {
	available: boolean;
	openings: OpeningRow[];
	statuses: string[];
	totals: {
		openings: number;
		published: number;
		open: number;
		applicants: number;
		waiting: number;
	};
}

interface ApplicantRow {
	name: string;
	applicant_name: string | null;
	email: string | null;
	phone: string | null;
	status: string;
	opening: string | null;
	opening_title: string | null;
	applied_on: string;
	volunteer: string | null;
	geo_node: string | null;
	is_withdrawn: boolean;
}

interface ApplicantsAnswer {
	available: boolean;
	applicants: ApplicantRow[];
	statuses: string[];
	counts: Pipeline;
}

interface OpeningDetail {
	name: string;
	job_title: string;
	designation: string | null;
	company: string | null;
	department: string | null;
	status: string;
	publish: number;
	route: string | null;
	description: string | null;
	posted_on: string | null;
	closes_on: string | null;
	closed_on: string | null;
	staffing_plan: string | null;
	planned_vacancies: number | null;
	job_requisition: string | null;
	job_opening_template: string | null;
	publish_applications_received: boolean;
	prevent_duplicate_applicant: boolean;
	location: string | null;
	vacancies: number | null;
	employment_type: string | null;
	vmms_purpose: string | null;
	vmms_geo_node: string | null;
	vmms_project: string | null;
	vmms_deployment: string | null;
	vmms_available_from: string | null;
	vmms_available_to: string | null;
	vmms_desired_skills: string[];
	vmms_desired_languages: string[];
	vmms_desired_certifications: DesiredCertification[];

	// --- how the post is described, beyond HRMS's four link fields ------------
	opportunity_type: string | null;
	profession: string | null;
	job_location: string | null;

	// --- what it screens for, and how hard -----------------------------------
	enable_autograding: boolean;
	minimum_pass_score: number | null;
	disqualify_if_requirement_not_met: boolean;
	minimum_qualification_level: string | null;
	allow_equivalent_experience: boolean;
	required_gpa__grade: string | null;
	preferred_field_of_study: string | null;
	minimum_years_of_experience: number | null;
	experience_area: string | null;
	disqualify_if_below_minimum: boolean;
	required_attachments: RequiredAttachment[];

	// --- what happens to the people it turns down ----------------------------
	enable_automatic_rejection_notifications: boolean;
	send_rejection_email_immediately: boolean;
	rejection_email_template: string | null;
	notify_unshortlisted_applicants_after: number | null;
	shortlisted_rejection_notification_date: string | null;

	is_published: boolean;
	url: string | null;
	apply_url: string;
	screening_questions: ScreeningQuestion[];
	pipeline: Pipeline;
	can_write: boolean;
}

/** One certification a candidate should hold — `VMMS Deployment Requirement`. */
interface DesiredCertification {
	certification_type: string;
	is_mandatory: boolean;
	requirement_notes: string | null;
}

/** One document an applicant has to upload — `Required Attachments`. */
interface RequiredAttachment {
	type: string;
	document_name: string | null;
}

interface ScreeningQuestion {
	question_id: string;
	question: string;
	question_type: string;
	is_required: boolean;
	is_knock_off: boolean;
	help_text: string | null;
	options: string | null;
	enable_scoring: boolean;
	weight: number | null;
	max_score: number | null;
	expected_answer: string | null;
	depends_on_question: string | null;
	show_if_answer_is: string | null;
}

interface Options {
	available: boolean;
	statuses?: string[];
	purposes?: string[];
	pipeline?: string[];
	designations?: { value: string; label: string }[];
	departments?: { value: string; label: string }[];
	companies?: { value: string; label: string }[];
	employment_types?: { value: string; label: string }[];
	opening_templates?: { value: string; label: string }[];
	geo_nodes?: { value: string; label: string }[];
	deployments?: { value: string; label: string }[];
	skills?: { value: string; label: string }[];
	languages?: { value: string; label: string }[];
	projects?: { value: string; label: string }[];
	professions?: { value: string; label: string }[];
	locations?: { value: string; label: string }[];
	certification_types?: { value: string; label: string }[];
	document_types?: { value: string; label: string }[];
	email_templates?: { value: string; label: string }[];
	opening_types?: string[];
	qualification_levels?: string[];
	question_types?: string[];
}

interface ApplicantDetail extends ApplicantRow {
	country: string | null;
	red_profile: string | null;
	source: string | null;
	source_name: string | null;
	designation: string | null;
	employee_referral: string | null;
	cover_letter: string | null;
	resume_attachment: string | null;
	withdrawn_on: string | null;
	withdrawal_reason: string | null;
	answers: Array<{
		question_id: string;
		question: string;
		question_type: string;
		answer: string | null;
		answer_file: string | null;
	}>;
	deployment_assignment: string | null;
	task: string | null;
	statuses: string[];
	can_write: boolean;
}

/** A number from the record as a form value: zero is a number, null is blank. */
function numeric(value: number | null): string {
	return value === null || value === undefined ? "" : String(value);
}

/**
 * Add or remove one value from a multi-select's list.
 *
 * `MultiCombo` reports a *toggle* rather than a new array, which is what keeps
 * it identical wherever it appears — the volunteer application, the membership
 * form and this opening form all hand it the same shape. The list is the
 * caller's to own.
 */
function toggle(values: string[], key: string): string[] {
	return values.includes(key) ? values.filter((value) => value !== key) : [...values, key];
}

/** The pipeline, in the order somebody is moved through it. */
const STAGES = ["Open", "Replied", "Shortlisted", "Hold", "Accepted", "Rejected"] as const;

/** Each stage's dot colour on the board. Never the only signal — the heading names it. */
const STAGE_TONE: Record<string, "neutral" | "info" | "warning" | "success" | "danger"> = {
	Open: "info",
	Replied: "info",
	Shortlisted: "warning",
	Hold: "neutral",
	Accepted: "success",
	Rejected: "danger",
};

/**
 * The one sentence a society without HRMS is shown, on every screen here.
 *
 * Not an error and not machinery: the recruitment tab is drawn from the section
 * list, so somebody only reaches this by following a link from a site that once
 * had HRMS installed. It says what is missing and stops.
 */
function NotInstalled() {
	return (
		<Empty title="Recruitment is not set up on this site" icon={Icon.briefcase}>
			Job openings live in the HR application, which is not installed here.
		</Empty>
	);
}

/* ------------------------------------------------------------------ openings */

export function Openings() {
	const [search, setSearch] = useState("");
	const [status, setStatus] = useState("");
	const [purpose, setPurpose] = useState("");

	const openings = useFrappeGetCall<{ message: OpeningsAnswer }>(
		API.recruitmentOpenings,
		{ search: search || undefined, status: status || undefined, purpose: purpose || undefined },
		`admin:openings:${search}:${status}:${purpose}`,
	);

	if (openings.isLoading) return <Spinner page label="Loading openings…" />;
	if (openings.error) return <ErrorNote>{errorMessage(openings.error)}</ErrorNote>;

	const answer = openings.data?.message;
	if (!answer?.available) return <NotInstalled />;

	const { totals } = answer;

	return (
		<>
			<PageHead
				title="Job openings"
				actions={
					<ButtonLink to="/admin/recruitment/openings/new">
						<Icon.plus size={15} />
						New opening
					</ButtonLink>
				}
			/>

			<MetricGrid>
				<Metric label="Openings" value={totals.openings} icon={Icon.briefcase} />
				<Metric
					label="Still recruiting"
					value={totals.open}
					note={`${totals.published} on the website`}
					icon={Icon.globe}
				/>
				<Metric label="Applications" value={totals.applicants} icon={Icon.inbox} to="/admin/recruitment/applications" />
				<Metric
					label="Not yet looked at"
					value={totals.waiting}
					tone={totals.waiting > 0 ? "negative" : "muted"}
					note={totals.waiting > 0 ? "Waiting on a first decision" : "Nothing waiting"}
					icon={Icon.hourglass}
					to="/admin/recruitment/applications?status=Open"
				/>
			</MetricGrid>

			<Toolbar>
				<SearchBox value={search} onChange={setSearch} placeholder="Search openings" />
				<FilterSelect
					label="Status"
					value={status}
					onChange={setStatus}
					allLabel="Any status"
					options={answer.statuses.map((value) => ({ value, label: value }))}
				/>
				<FilterSelect
					label="Kind"
					value={purpose}
					onChange={setPurpose}
					allLabel="Volunteering and employment"
					options={[
						{ value: "Volunteer", label: "Volunteering" },
						{ value: "Employment", label: "Employment" },
					]}
				/>
			</Toolbar>

			{answer.openings.length === 0 ? (
				<Empty
					title="No openings match"
					icon={Icon.briefcase}
					action={<ButtonLink to="/admin/recruitment/openings/new">New opening</ButtonLink>}
				>
					{search || status || purpose
						? "Try a wider filter."
						: "Advertise a post and the answers arrive in the applications list."}
				</Empty>
			) : (
				<Card pad={false}>
					<Table head={["Opening", "Where", "Applications", "Closes", "State"]} minWidth={860}>
						{answer.openings.map((row) => (
							<Row key={row.name} to={`/admin/recruitment/openings/${encodeURIComponent(row.name)}`} label={`Open ${row.job_title}`}>
								<NameCell
									to={`/admin/recruitment/openings/${encodeURIComponent(row.name)}`}
									title={row.job_title}
									meta={
										[row.designation, row.purpose === "Volunteer" ? "Volunteering" : "Employment"]
											.filter(Boolean)
											.join(" · ") || undefined
									}
								/>
								<Cell>{row.department || row.location || "—"}</Cell>
								<Cell nowrap>
									<PipelineStrip pipeline={row.pipeline} to={`/admin/recruitment/applications?opening=${encodeURIComponent(row.name)}`} />
								</Cell>
								<Cell nowrap>
									{row.closes_on ? (
										<span className={cx(row.is_closing && "font-semibold text-warning")}>
											{formatDate(row.closes_on)}
										</span>
									) : (
										"—"
									)}
								</Cell>
								<Cell nowrap>
									<div className="flex flex-wrap items-center gap-1.5">
										<StatusBadge
											state={row.status}
											tone={row.status === "Open" ? "success" : "neutral"}
										/>
										{/* Published is a second fact, not a second state:
										    an opening can be Open and deliberately not
										    advertised, and one chip could not say both. */}
										{row.is_published ? (
											<StatusBadge tone="info">On the site</StatusBadge>
										) : (
											<StatusBadge tone="neutral">Not advertised</StatusBadge>
										)}
									</div>
								</Cell>
							</Row>
						))}
					</Table>
				</Card>
			)}
		</>
	);
}

/**
 * The pipeline as a row of counts.
 *
 * A strip rather than five columns of numbers: what a recruiter scanning a
 * board wants is "how many, and how many still need me", and the two figures
 * that answer that are the total and the untouched. The rest is one click away.
 */
function PipelineStrip({ pipeline, to }: { pipeline: Pipeline; to: string }) {
	if (!pipeline.total) return <span className="text-muted">No applications</span>;

	return (
		<Link to={to} className="group inline-flex items-baseline gap-2">
			<span className="tabular text-[14px] font-semibold text-ink group-hover:text-blue">
				{pipeline.total}
			</span>
			{pipeline.Open > 0 && (
				<span className="text-[11.5px] font-semibold text-warning">{pipeline.Open} new</span>
			)}
			{pipeline.Accepted > 0 && (
				<span className="text-[11.5px] font-medium text-success">{pipeline.Accepted} accepted</span>
			)}
		</Link>
	);
}

/* ------------------------------------------------------------- opening form */

/**
 * Advertising a post, and amending one.
 *
 * One form for both, because they are one act at two moments and a second form
 * would be a second place the field list drifts. The server keeps writes to a
 * bounded list of fields and protects the question set after applications exist.
 */
export function OpeningForm() {
	const { name } = useParams<{ name: string }>();
	const editing = Boolean(name && name !== "new");
	const navigate = useNavigate();
	const toast = useToast();

	const options = useFrappeGetCall<{ message: Options }>(API.recruitmentOptions, undefined, "admin:recruitment:options");
	const existing = useFrappeGetCall<{ message: OpeningDetail }>(
		API.recruitmentOpening,
		{ name },
		editing ? `admin:opening:${name}` : null,
	);
	const save = useFrappePostCall<{ message: OpeningDetail }>(API.recruitmentSaveOpening);

	const [form, setForm] = useState({
		job_title: "",
		designation: "",
		company: "",
		department: "",
		location: "",
		employment_type: "",
		job_opening_template: "",
		publish_applications_received: false,
		prevent_duplicate_applicant: false,
		vmms_purpose: "Volunteer",
		description: "",
		posted_on: "",
		closes_on: "",
		vmms_geo_node: "",
		vmms_project: "",
		vmms_deployment: "",
		vmms_available_from: "",
		vmms_available_to: "",
		publish: false,
		route: "",
		status: "Open",

		// The rest of what vmmsx puts on an opening. Every one of these was a
		// Custom Field this app installs and this form never drew, so a
		// coordinator wrote half an opening here and finished it on the desk.
		opportunity_type: "",
		profession: "",
		job_location: "",

		enable_autograding: false,
		minimum_pass_score: "",
		disqualify_if_requirement_not_met: false,
		minimum_qualification_level: "",
		allow_equivalent_experience: false,
		required_gpa__grade: "",
		preferred_field_of_study: "",
		minimum_years_of_experience: "",
		experience_area: "",
		disqualify_if_below_minimum: false,

		enable_automatic_rejection_notifications: false,
		send_rejection_email_immediately: false,
		rejection_email_template: "",
		notify_unshortlisted_applicants_after: "",
		shortlisted_rejection_notification_date: "",
	});
	const [skills, setSkills] = useState<string[]>([]);
	const [languages, setLanguages] = useState<string[]>([]);
	const [certifications, setCertifications] = useState<DesiredCertification[]>([]);
	const [attachments, setAttachments] = useState<RequiredAttachment[]>([]);
	const [questions, setQuestions] = useState<ScreeningQuestion[]>([]);
	const [failed, setFailed] = useState<string | null>(null);

	// Fill the form once the record arrives. Keyed on the docname rather than on
	// the whole answer, so a background revalidation cannot overwrite something
	// somebody is halfway through typing.
	const loaded = existing.data?.message;
	useEffect(() => {
		if (!loaded) return;

		setForm({
			job_title: loaded.job_title ?? "",
			designation: loaded.designation ?? "",
			company: loaded.company ?? "",
			department: loaded.department ?? "",
			location: loaded.location ?? "",
			employment_type: loaded.employment_type ?? "",
			job_opening_template: loaded.job_opening_template ?? "",
			publish_applications_received: loaded.publish_applications_received,
			prevent_duplicate_applicant: loaded.prevent_duplicate_applicant,
			vmms_purpose: loaded.vmms_purpose ?? "Volunteer",
			description: loaded.description ?? "",
			posted_on: loaded.posted_on ?? "",
			closes_on: loaded.closes_on ?? "",
			vmms_geo_node: loaded.vmms_geo_node ?? "",
			vmms_project: loaded.vmms_project ?? "",
			vmms_deployment: loaded.vmms_deployment ?? "",
			vmms_available_from: loaded.vmms_available_from ?? "",
			vmms_available_to: loaded.vmms_available_to ?? "",
			publish: loaded.is_published,
			route: loaded.route ?? "",
			status: loaded.status ?? "Open",

			opportunity_type: loaded.opportunity_type ?? "",
			profession: loaded.profession ?? "",
			job_location: loaded.job_location ?? "",

			enable_autograding: loaded.enable_autograding,
			minimum_pass_score: numeric(loaded.minimum_pass_score),
			disqualify_if_requirement_not_met: loaded.disqualify_if_requirement_not_met,
			minimum_qualification_level: loaded.minimum_qualification_level ?? "",
			allow_equivalent_experience: loaded.allow_equivalent_experience,
			required_gpa__grade: loaded.required_gpa__grade ?? "",
			preferred_field_of_study: loaded.preferred_field_of_study ?? "",
			minimum_years_of_experience: numeric(loaded.minimum_years_of_experience),
			experience_area: loaded.experience_area ?? "",
			disqualify_if_below_minimum: loaded.disqualify_if_below_minimum,

			enable_automatic_rejection_notifications:
				loaded.enable_automatic_rejection_notifications,
			send_rejection_email_immediately: loaded.send_rejection_email_immediately,
			rejection_email_template: loaded.rejection_email_template ?? "",
			notify_unshortlisted_applicants_after: numeric(
				loaded.notify_unshortlisted_applicants_after,
			),
			shortlisted_rejection_notification_date:
				loaded.shortlisted_rejection_notification_date ?? "",
		});
		setSkills(loaded.vmms_desired_skills ?? []);
		setLanguages(loaded.vmms_desired_languages ?? []);
		setCertifications(loaded.vmms_desired_certifications ?? []);
		setAttachments(loaded.required_attachments ?? []);
		setQuestions(loaded.screening_questions ?? []);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [loaded?.name]);

	const choices = options.data?.message;
	const set = (key: keyof typeof form) => (value: string | boolean) =>
		setForm((state) => ({ ...state, [key]: value }));

	if (options.isLoading || (editing && existing.isLoading)) {
		return <Spinner page label="Loading the opening…" />;
	}
	if (choices && !choices.available) return <NotInstalled />;
	if (editing && existing.error) return <ErrorNote>{errorMessage(existing.error)}</ErrorNote>;

	const ready = Boolean(form.job_title.trim() && form.company && form.designation);

	const submit = async () => {
		setFailed(null);

		try {
			const answer = await save.call({
				name: editing ? name : undefined,
				payload: {
					...form,
					publish: form.publish ? 1 : 0,
					...(form.posted_on ? { posted_on: form.posted_on } : {}),
					closes_on: form.closes_on || null,
					vmms_available_from: form.vmms_available_from || null,
					vmms_available_to: form.vmms_available_to || null,
					minimum_pass_score: form.minimum_pass_score || null,
					minimum_years_of_experience: form.minimum_years_of_experience || null,
					notify_unshortlisted_applicants_after:
						form.notify_unshortlisted_applicants_after || null,
					shortlisted_rejection_notification_date:
						form.shortlisted_rejection_notification_date || null,
					vmms_desired_skills: skills,
					vmms_desired_languages: languages,
					vmms_desired_certifications: certifications,
					required_attachments: attachments,
					screening_questions: questions,
				},
			});

			toast(editing ? "Opening saved" : "Opening created");
			navigate(`/admin/recruitment/openings/${encodeURIComponent(answer.message.name)}`);
		} catch (error) {
			setFailed(errorMessage(error, "The opening could not be saved."));
		}
	};

	return (
		<>
			<BackLink to={editing ? `/admin/recruitment/openings/${encodeURIComponent(name as string)}` : "/admin/recruitment/openings"}>
				{editing ? "Back to the opening" : "Back to openings"}
			</BackLink>

			<PageHead title={editing ? "Edit opening" : "New opening"} />

			{failed && (
				<div className="mb-4">
					<ErrorNote>{failed}</ErrorNote>
				</div>
			)}

			<div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
				<Card className="space-y-6">
					<FormSection title="The post">
						<FieldGrid>
							<Field label="Job Title" required className="sm:col-span-2">
								<TextInput
									value={form.job_title}
									onChange={set("job_title") as (value: string) => void}
									placeholder="Community health outreach volunteer"
								/>
							</Field>

							<Field
								label="Purpose"
								hint={
									form.vmms_purpose === "Volunteer"
										? "Volunteers apply inside their own portal, with what the society already holds about them filled in."
										: "Applicants answer the public web form."
								}
							>
								<Select
									value={form.vmms_purpose}
									onChange={set("vmms_purpose") as (value: string) => void}
									options={[
										{ value: "Volunteer", label: "Volunteering" },
										{ value: "Employment", label: "Employment" },
									]}
								/>
							</Field>

							<Field label="Designation" required>
								<Select
									value={form.designation}
									onChange={set("designation") as (value: string) => void}
									placeholder="Not set"
									options={choices?.designations ?? []}
								/>
							</Field>

							<Field label="Department">
								<Select
									value={form.department}
									onChange={set("department") as (value: string) => void}
									placeholder="Not set"
									options={choices?.departments ?? []}
								/>
							</Field>

							<Field label="Company" required>
								<Select
									value={form.company}
									onChange={set("company") as (value: string) => void}
									placeholder="Not set"
									options={choices?.companies ?? []}
								/>
							</Field>

							<Field label="Location" hint="From the society's own list of places.">
								<Select
									value={form.job_location}
									onChange={set("job_location") as (value: string) => void}
									placeholder="Not set"
									options={choices?.locations ?? []}
								/>
							</Field>

							<Field label="Profession" hint="What kind of work this is.">
								<Select
									value={form.profession}
									onChange={set("profession") as (value: string) => void}
									placeholder="Not set"
									options={choices?.professions ?? []}
								/>
							</Field>

							{/* Only where the society has configured the Select. A site
							    that has not run the patch gets no control rather than
							    an empty one. */}
							{(choices?.opening_types ?? []).length > 0 && (
								<Field
									label="Opening Type"
									hint="Whether people outside the society may apply."
								>
									<Select
										value={form.opportunity_type}
										onChange={set("opportunity_type") as (value: string) => void}
										placeholder="Not set"
										options={(choices?.opening_types ?? []).map((value) => ({
											value,
											label: value,
										}))}
									/>
								</Field>
							)}


							<Field label="Description" className="sm:col-span-2">
								<TextArea
									rows={8}
									value={form.description}
									onChange={set("description") as (value: string) => void}
									placeholder="What the work is, who it is for, and what somebody would be doing."
								/>
							</Field>
							<Field label="Route" hint="The path used for the published job page.">
								<TextInput value={form.route} onChange={set("route") as (value: string) => void} placeholder="Generated from the title if blank" />
							</Field>
						</FieldGrid>
					</FormSection>

					<FormSection
						title="Desired Attributes"
						hint="Used to match volunteers to the post. Neither is a bar to applying."
					>
						<div className="space-y-4">
							{/* The same control the volunteer application uses for the
							    same vocabularies — search, pick, and the choices tray
							    below. Uniform on purpose: a coordinator writing an
							    opening and a volunteer filling in their own record
							    should be operating the same field. */}
							<MultiCombo
								label="Desired Skills"
								selected={skills}
								onToggle={(key) => setSkills(toggle(skills, key))}
								options={(choices?.skills ?? []).map((option) => ({
									key: option.value,
									label: option.label,
								}))}
								placeholder="Search and add a skill"
								empty="No skills are configured on this site yet."
							/>
							<MultiCombo
								label="Desired Languages"
								selected={languages}
								onToggle={(key) => setLanguages(toggle(languages, key))}
								options={(choices?.languages ?? []).map((option) => ({
									key: option.value,
									label: option.label,
								}))}
								placeholder="Search and add a language"
								empty="No languages are configured on this site yet."
							/>

							{/* The third desired attribute, and the only one of the
							    three with a "must hold" flag on each row: a first-aid
							    certificate can genuinely be a bar where a language is
							    a preference. Same shape a terms of reference uses for
							    the same question. */}
							<RowEditor<DesiredCertification>
								title="Desired Certifications"
								lead="Mandatory rows are a condition of the post; the rest rank a candidate higher."
								addLabel="Add a certification"
								empty="No certifications asked for."
								rows={certifications}
								onChange={setCertifications}
								blank={() => ({
									certification_type: "",
									is_mandatory: true,
									requirement_notes: "",
								})}
								columns={[
									{
										key: "certification_type",
										label: "Certification Type",
										kind: "select",
										span: 5,
										options: choices?.certification_types ?? [],
									},
									{
										key: "is_mandatory",
										label: "Mandatory",
										kind: "check",
										checkedLabel: "Mandatory",
										span: 3,
									},
									{ key: "requirement_notes", label: "Notes", span: 4 },
								]}
							/>
						</div>
					</FormSection>

					<FormSection
						title="Requirements"
						hint="These settings record the opening's screening criteria. Automatic grading is not active yet."
					>
						<div className="space-y-5">
							<Check
								checked={form.enable_autograding}
								onChange={set("enable_autograding") as (value: boolean) => void}
								label="Enable Auto-Grading"
								hint="Records the intended screening rule. Automatic grading is not active yet."
							/>

							<FieldGrid>
								<Field
									label="Minimum Pass Score"
								>
									<TextInput
										type="number"
										min={0}
										value={form.minimum_pass_score}
										onChange={set("minimum_pass_score") as (value: string) => void}
									/>
								</Field>

								<Field label="Minimum Qualification Level">
									<Select
										value={form.minimum_qualification_level}
										onChange={
											set("minimum_qualification_level") as (value: string) => void
										}
										placeholder="No minimum"
										options={(choices?.qualification_levels ?? []).map((value) => ({
											value,
											label: value,
										}))}
									/>
								</Field>

								<Field label="Required GPA / Grade" hint="As the society words it.">
									<TextInput
										value={form.required_gpa__grade}
										onChange={set("required_gpa__grade") as (value: string) => void}
										placeholder="Second class upper, 3.0…"
									/>
								</Field>

								<Field label="Preferred field of study">
									<TextInput
										value={form.preferred_field_of_study}
										onChange={set("preferred_field_of_study") as (value: string) => void}
										placeholder="Public health"
									/>
								</Field>

								<Field label="Minimum Years of Experience">
									<TextInput
										type="number"
										min={0}
										value={form.minimum_years_of_experience}
										onChange={
											set("minimum_years_of_experience") as (value: string) => void
										}
									/>
								</Field>

								<Field label="Experience Area" hint="The area that experience has to be in.">
									<TextInput
										value={form.experience_area}
										onChange={set("experience_area") as (value: string) => void}
										placeholder="Community outreach"
									/>
								</Field>
							</FieldGrid>

							<div className="space-y-3 border-t p-divide pt-4">
								<Check
									checked={form.allow_equivalent_experience}
									onChange={
										set("allow_equivalent_experience") as (value: boolean) => void
									}
									label="Allow Equivalent Experience"
									hint="Somebody who has done the work but does not hold the certificate is still considered."
								/>
								<Check
									checked={form.disqualify_if_below_minimum}
									onChange={
										set("disqualify_if_below_minimum") as (value: boolean) => void
									}
									label="Disqualify if Below Minimum"
									hint="Otherwise they are ranked lower and a person still reads them."
								/>
								<Check
									checked={form.disqualify_if_requirement_not_met}
									onChange={
										set("disqualify_if_requirement_not_met") as (value: boolean) => void
									}
									label="Disqualify if Requirement Not Met"
								/>
							</div>

							<RowEditor<RequiredAttachment>
								title="Required Attachments"
								lead="Documents somebody has to upload before the application form will take their answer."
								addLabel="Add a document"
								empty="Nothing has to be attached."
								rows={attachments}
								onChange={setAttachments}
								blank={() => ({ type: "", document_name: "" })}
								columns={[
									{
										key: "type",
										label: "Type",
										kind: "select",
										span: 5,
										options: choices?.document_types ?? [],
									},
									{
										key: "document_name",
										label: "Document Name",
										span: 7,
									},
								]}
							/>
						</div>
					</FormSection>

					<FormSection title="Screening Questions" hint="Question IDs, types and required flags are locked once someone applies. The server checks this when saving.">
						<RowEditor<ScreeningQuestion>
							title="Screening Questions"
							addLabel="Add a question"
							empty="No screening questions."
							rows={questions}
							onChange={setQuestions}
							blank={() => ({ question_id: "", question: "", question_type: "Text", is_required: false, is_knock_off: false, help_text: "", options: "", enable_scoring: false, weight: null, max_score: null, expected_answer: "", depends_on_question: "", show_if_answer_is: "" })}
							columns={[
								{ key: "question_id", label: "Question ID", span: 3 },
								{ key: "question_type", label: "Question Type", kind: "select", span: 4, options: (choices?.question_types ?? []).map((value) => ({ value, label: value })) },
								{ key: "question", label: "Question", kind: "area", span: 12 },
								{ key: "help_text", label: "Help Text", kind: "area", span: 12 },
								{ key: "options", label: "Options", kind: "area", span: 12 },
								{ key: "is_required", label: "Is Required", kind: "check", checkedLabel: "Required", span: 3 },
								{ key: "is_knock_off", label: "Is Knock Off", kind: "check", checkedLabel: "Knock off", span: 3 },
								{ key: "enable_scoring", label: "Enable Scoring", kind: "check", checkedLabel: "Score", span: 3 },
								{ key: "weight", label: "Weight", kind: "number", span: 3 },
								{ key: "max_score", label: "Max Score", kind: "number", span: 3 },
								{ key: "expected_answer", label: "Expected Answer", kind: "area", span: 12 },
								{ key: "depends_on_question", label: "Depends On Question", span: 6 },
								{ key: "show_if_answer_is", label: "Show If Answer Is", span: 6 },
							]}
						/>
					</FormSection>

					<FormSection
						title="Rejection Notification Settings"
						hint="These settings record notification preferences. Automatic rejection emails are not active yet."
					>
						<div className="space-y-5">
							<Check
								checked={form.enable_automatic_rejection_notifications}
								onChange={
									set("enable_automatic_rejection_notifications") as (
										value: boolean,
									) => void
								}
								label="Enable Automatic Rejection Notifications"
								hint="Records the notification setting configured on the opening."
							/>

							<FieldGrid>
								<Field label="Rejection Email Template" className="sm:col-span-2">
									<Select
										value={form.rejection_email_template}
										onChange={
											set("rejection_email_template") as (value: string) => void
										}
										placeholder="Not set"
										options={choices?.email_templates ?? []}
									/>
								</Field>

								<Field
									label="Notify Unshortlisted Applicants After"
									hint="Before writing to somebody who was never shortlisted."
								>
									<TextInput
										type="number"
										min={0}
										value={form.notify_unshortlisted_applicants_after}
										onChange={
											set("notify_unshortlisted_applicants_after") as (
												value: string,
											) => void
										}
									/>
								</Field>

								<Field
									label="Shortlisted Rejection Notification Date"
									hint="A single date, so everybody interviewed hears on the same day."
								>
									<TextInput
										type="date"
										value={form.shortlisted_rejection_notification_date}
										onChange={
											set("shortlisted_rejection_notification_date") as (
												value: string,
											) => void
										}
									/>
								</Field>
							</FieldGrid>

							<Check
								checked={form.send_rejection_email_immediately}
								onChange={
									set("send_rejection_email_immediately") as (value: boolean) => void
								}
								label="Send Rejection Email Immediately"
								hint="Rather than waiting for the dates above."
							/>
						</div>
					</FormSection>

					<FormSection title="Dates">
						<FieldGrid>
							<Field label="Posted On">
								<TextInput type="datetime-local" value={form.posted_on} onChange={set("posted_on") as (value: string) => void} />
							</Field>
							<Field label="Closes On">
								<TextInput
									type="datetime-local"
									value={form.closes_on}
									onChange={set("closes_on") as (value: string) => void}
								/>
							</Field>
							<Field label="Opportunity Type">
								<Select
									value={form.employment_type}
									onChange={set("employment_type") as (value: string) => void}
									placeholder="Not set"
									options={choices?.employment_types ?? []}
								/>
							</Field>
							<Field label="Needed From">
								<TextInput
									type="date"
									value={form.vmms_available_from}
									onChange={set("vmms_available_from") as (value: string) => void}
								/>
							</Field>
							<Field label="Needed Until">
								<TextInput
									type="date"
									value={form.vmms_available_to}
									onChange={set("vmms_available_to") as (value: string) => void}
								/>
							</Field>
							<Field label="Job Opening Template">
								<Select value={form.job_opening_template} onChange={set("job_opening_template") as (value: string) => void} placeholder="Not set" options={choices?.opening_templates ?? []} />
							</Field>
							<Field label="Owning Geo Node">
								<Select value={form.vmms_geo_node} onChange={set("vmms_geo_node") as (value: string) => void} placeholder="Not set" options={choices?.geo_nodes ?? []} />
							</Field>
							<Field label="Project">
								<Select value={form.vmms_project} onChange={set("vmms_project") as (value: string) => void} placeholder="Not set" options={choices?.projects ?? []} />
							</Field>
							<Field label="Deployment">
								<Select value={form.vmms_deployment} onChange={set("vmms_deployment") as (value: string) => void} placeholder="Not set" options={choices?.deployments ?? []} />
							</Field>
						</FieldGrid>
					</FormSection>
				</Card>

				<div className="space-y-4 lg:sticky lg:top-[76px] lg:self-start">
					<DecisionCard eyebrow={editing ? "Amending" : "New"} title="Publishing">
						<Field label="Status">
							<Select
								value={form.status}
								onChange={set("status") as (value: string) => void}
								options={(choices?.statuses ?? ["Open", "Closed"]).map((value) => ({
									value,
									label: value === "Open" ? "Open — still recruiting" : "Closed",
								}))}
							/>
						</Field>

						<Check
							checked={form.publish}
							onChange={set("publish") as (value: boolean) => void}
							label="Publish on website"
							hint="An open post can be left unadvertised and filled by invitation."
						/>
						<Check checked={form.publish_applications_received} onChange={set("publish_applications_received") as (value: boolean) => void} label="Publish Applications Received" />
						<Check checked={form.prevent_duplicate_applicant} onChange={set("prevent_duplicate_applicant") as (value: boolean) => void} label="Prevent Duplicate Applications" />
					</DecisionCard>

					<div className="grid gap-2">
						<Button onClick={() => void submit()} disabled={!ready} busy={save.loading}>
							{editing ? "Save opening" : "Create opening"}
						</Button>
						<Button
							tone="quiet"
							onClick={() =>
								navigate(
									editing
										? `/admin/recruitment/openings/${encodeURIComponent(name as string)}`
										: "/admin/recruitment/openings",
								)
							}
						>
							Cancel
						</Button>
					</div>

				</div>
			</div>
		</>
	);
}

/* ----------------------------------------------------------- one opening */

export function OpeningDetailPage() {
	const { name } = useParams<{ name: string }>();
	const toast = useToast();
	const [confirm, setConfirm] = useState<"close" | "reopen" | null>(null);

	const opening = useFrappeGetCall<{ message: OpeningDetail }>(
		API.recruitmentOpening,
		{ name },
		`admin:opening:${name}`,
	);
	const applicants = useFrappeGetCall<{ message: ApplicantsAnswer }>(
		API.recruitmentApplicants,
		{ opening: name },
		`admin:opening:applicants:${name}`,
	);
	const setStatus = useFrappePostCall(API.recruitmentSetOpeningStatus);
	const setPublished = useFrappePostCall(API.recruitmentSetOpeningPublished);

	if (opening.isLoading) return <Spinner page label="Loading the opening…" />;
	if (opening.error) return <ErrorNote>{errorMessage(opening.error)}</ErrorNote>;

	const doc = opening.data?.message;
	if (!doc) return <NotInstalled />;

	const rows = applicants.data?.message?.applicants ?? [];

	const move = async (status: "Open" | "Closed") => {
		try {
			await setStatus.call({ name, status });
			toast(status === "Open" ? "Opening reopened" : "Opening closed");
			void opening.mutate();
		} catch (error) {
			toast(errorMessage(error, "That could not be changed."));
		}
		setConfirm(null);
	};

	const publish = async (published: boolean) => {
		try {
			await setPublished.call({ name, published: published ? 1 : 0 });
			toast(published ? "Now on the website" : "Taken off the website");
			void opening.mutate();
		} catch (error) {
			toast(errorMessage(error, "That could not be changed."));
		}
	};

	return (
		<>
			<BackLink to="/admin/recruitment/openings">Back to openings</BackLink>

			<div className="mb-4 flex flex-wrap items-start justify-between gap-3">
				<div className="min-w-0">
					<div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">
						{doc.vmms_purpose === "Volunteer" ? "Volunteering" : "Employment"}
					</div>
					<h1 className="mt-1.5 text-[26px] font-semibold leading-[1.15] tracking-[-0.02em] text-ink">
						{doc.job_title}
					</h1>
					<div className="mt-2 flex flex-wrap items-center gap-2">
						<StatusBadge state={doc.status} tone={doc.status === "Open" ? "success" : "neutral"} />
						{doc.is_published ? (
							<StatusBadge tone="info">On the site</StatusBadge>
						) : (
							<StatusBadge tone="neutral">Not advertised</StatusBadge>
						)}
					</div>
				</div>

				{doc.can_write && (
					<div className="flex flex-wrap gap-2">
						<ButtonLink tone="quiet" to={`/admin/recruitment/openings/${encodeURIComponent(doc.name)}/edit`}>
							Edit
						</ButtonLink>
						<Button tone="quiet" onClick={() => void publish(!doc.is_published)} busy={setPublished.loading}>
							{doc.is_published ? "Take off the site" : "Put on the site"}
						</Button>
						<Button
							tone={doc.status === "Open" ? "danger" : "primary"}
							onClick={() => setConfirm(doc.status === "Open" ? "close" : "reopen")}
						>
							{doc.status === "Open" ? "Close opening" : "Reopen"}
						</Button>
					</div>
				)}
			</div>

			<div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
				<div className="min-w-0 space-y-4">
					{doc.description && (
						<Card>
							<h2 className="mb-3 text-[13.5px] font-semibold text-ink">What the post is</h2>
							<div
								className="article-body text-[13.5px] leading-relaxed text-slate-strong"
								// The description is HRMS's own Text Editor field, so it
								// arrives as HTML this app did not author and cannot
								// re-author. `_safe_html` on the server has already
								// stripped scripts and event handlers.
								dangerouslySetInnerHTML={{ __html: doc.description }}
							/>
						</Card>
					)}

					<Card pad={false}>
						<SectionHead
							title="Applications"
							link={{
								to: `/admin/recruitment/applications?opening=${encodeURIComponent(doc.name)}`,
								label: "Open the pipeline",
							}}
						/>
						{rows.length === 0 ? (
							<Empty framed={false} title="Nobody has applied yet" icon={Icon.inbox} />
						) : (
							<Board>
								{STAGES.map((stage) => {
									const inStage = rows.filter(
										(row) => row.status === stage && !row.is_withdrawn,
									);

									return (
										<BoardColumn key={stage} title={stage} count={inStage.length} tone={STAGE_TONE[stage]}>
											{inStage.map((row) => (
												<BoardCard
													key={row.name}
													to={`/admin/recruitment/applications/${encodeURIComponent(row.name)}`}
													title={row.applicant_name ?? row.name}
													meta={formatDate(row.applied_on)}
													footer={row.volunteer ? <StatusBadge tone="info">Volunteer</StatusBadge> : undefined}
												/>
											))}
										</BoardColumn>
									);
								})}
							</Board>
						)}
					</Card>
				</div>

				<div className="space-y-4 lg:sticky lg:top-[76px] lg:self-start">
					<Card>
						<h2 className="mb-3.5 text-[13.5px] font-semibold text-ink">The opening</h2>
						<DetailList>
							<Detail label="Designation">{doc.designation ?? "—"}</Detail>
							<Detail label="Department">{doc.department ?? "—"}</Detail>
							<Detail label="Location">{doc.job_location ?? "—"}</Detail>
							<Detail label="Vacancies">{doc.vacancies ?? "—"}</Detail>
							<Detail label="Planned number of Positions">{doc.planned_vacancies ?? "—"}</Detail>
							<Detail label="Staffing Plan">{doc.staffing_plan ?? "—"}</Detail>
							<Detail label="Job Requisition">{doc.job_requisition ?? "—"}</Detail>
							<Detail label="Posted On">{doc.posted_on ? formatDate(doc.posted_on) : "—"}</Detail>
							<Detail label="Closes On">{doc.closes_on ? formatDate(doc.closes_on) : "—"}</Detail>
							<Detail label="Closed On">{doc.closed_on ? formatDate(doc.closed_on) : "—"}</Detail>
							<Detail label="Needed From">
								{doc.vmms_available_from ? formatDate(doc.vmms_available_from) : "—"}
							</Detail>
							<Detail label="Needed Until">{doc.vmms_available_to ? formatDate(doc.vmms_available_to) : "—"}</Detail>
							<Detail label="Owning Geo Node">{branchPath(doc.vmms_geo_node) || doc.vmms_geo_node || "—"}</Detail>
							<Detail label="Project">{doc.vmms_project ?? "—"}</Detail>
							<Detail label="Deployment">{doc.vmms_deployment ?? "—"}</Detail>
						</DetailList>

						{(doc.vmms_desired_skills.length > 0 || doc.vmms_desired_languages.length > 0) && (
							<div className="mt-4 border-t p-divide pt-4">
								<h3 className="text-[12px] font-semibold text-slate-strong">Looking for</h3>
								<div className="mt-2 flex flex-wrap gap-1.5">
									{[...doc.vmms_desired_skills, ...doc.vmms_desired_languages].map((value) => (
										<span
											key={value}
											className="rounded-full bg-blue-soft px-2.5 py-1 text-[11.5px] font-medium text-blue-press"
										>
											{value}
										</span>
									))}
								</div>
							</div>
						)}
					</Card>

					{doc.url && (
						<Card>
							<h2 className="text-[13px] font-semibold text-ink">On the website</h2>
							<a
								href={doc.url}
								target="_blank"
								rel="noreferrer"
								className="mt-2 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-blue hover:text-blue-hover"
							>
								Open the advertisement
								<Icon.external size={13} />
							</a>
						</Card>
					)}
				</div>
			</div>

			{confirm && (
				<ConfirmModal
					open
					title={confirm === "close" ? "Close this opening?" : "Reopen this opening?"}
					confirmLabel={confirm === "close" ? "Close it" : "Reopen it"}
					tone={confirm === "close" ? "danger" : "primary"}
					onConfirm={() => void move(confirm === "close" ? "Closed" : "Open")}
					onCancel={() => setConfirm(null)}
				>
					{confirm === "close"
						? "Nobody new will be able to apply. Applications already in the pipeline are untouched."
						: "The society will be recruiting for this post again."}
				</ConfirmModal>
			)}
		</>
	);
}

/* -------------------------------------------------------- the applications */

export function JobApplications() {
	const [search, setSearch] = useState("");
	const [opening, setOpening] = useState("");
	const [tab, setTab] = useState<string>("all");

	const openings = useFrappeGetCall<{ message: OpeningsAnswer }>(
		API.recruitmentOpenings,
		{ limit: 100 },
		"admin:openings:filter",
	);
	const applicants = useFrappeGetCall<{ message: ApplicantsAnswer }>(
		API.recruitmentApplicants,
		{ search: search || undefined, opening: opening || undefined },
		`admin:applicants:${search}:${opening}`,
	);

	if (applicants.isLoading) return <Spinner page label="Loading applications…" />;
	if (applicants.error) return <ErrorNote>{errorMessage(applicants.error)}</ErrorNote>;

	const answer = applicants.data?.message;
	if (!answer?.available) return <NotInstalled />;

	// Filtered here rather than refetched per tab: the list is already bounded
	// and a round trip per tab would make switching feel like navigating.
	const rows = answer.applicants.filter((row) => {
		if (tab === "all") return true;
		if (tab === "withdrawn") return row.is_withdrawn;

		return row.status === tab && !row.is_withdrawn;
	});

	const counts = answer.counts;

	return (
		<>
			<PageHead
				title="Job applications"
				actions={
					<ButtonLink tone="quiet" to="/admin/recruitment/openings">
						<Icon.briefcase size={15} />
						Openings
					</ButtonLink>
				}
			/>

			<Toolbar>
				<SearchBox value={search} onChange={setSearch} placeholder="Search by name" />
				<FilterSelect
					label="Opening"
					value={opening}
					onChange={setOpening}
					allLabel="Every opening"
					options={(openings.data?.message?.openings ?? []).map((row) => ({
						value: row.name,
						label: row.job_title,
					}))}
				/>
			</Toolbar>

			<Tabs
				active={tab}
				onSelect={setTab}
				tabs={[
					{ key: "all", label: "All", count: counts.total },
					...STAGES.map((stage) => ({ key: stage, label: stage, count: counts[stage] ?? 0 })),
					{ key: "withdrawn", label: "Withdrawn", count: counts.withdrawn },
				]}
			/>

			{rows.length === 0 ? (
				<Empty title="Nothing here" icon={Icon.inbox}>
					{tab === "all" ? "No applications match." : "Nothing at this stage."}
				</Empty>
			) : (
				<Card pad={false}>
						<Table head={["Applicant", "Job Opening", "Applied", "Status"]} minWidth={780}>
						{rows.map((row) => (
							<Row key={row.name} to={`/admin/recruitment/applications/${encodeURIComponent(row.name)}`} label={`Open ${row.applicant_name ?? row.name}`}>
								<NameCell
									to={`/admin/recruitment/applications/${encodeURIComponent(row.name)}`}
									lead={<Avatar name={row.applicant_name} size={32} />}
									title={row.applicant_name ?? row.name}
									meta={row.email ?? row.phone ?? undefined}
								/>
								<Cell>{row.opening_title ?? "—"}</Cell>
								<Cell nowrap>{formatDate(row.applied_on)}</Cell>
								<Cell nowrap>
									<div className="flex flex-wrap items-center gap-1.5">
										<StatusBadge state={row.status} />
										{row.is_withdrawn && <StatusBadge tone="neutral">Withdrawn</StatusBadge>}
									</div>
								</Cell>
							</Row>
						))}
					</Table>
				</Card>
			)}
		</>
	);
}

/* ------------------------------------------------------------ one applicant */

export function JobApplicant() {
	const { name } = useParams<{ name: string }>();
	const toast = useToast();
	const [stage, setStage] = useState("");

	const applicant = useFrappeGetCall<{ message: ApplicantDetail }>(
		API.recruitmentApplicant,
		{ name },
		`admin:applicant:${name}`,
	);
	const move = useFrappePostCall(API.recruitmentSetApplicantStatus);
	const convert = useFrappePostCall(API.convertApplication);

	const doc = applicant.data?.message;

	// The select opens on where the person actually is, so choosing the current
	// stage is a no-op rather than the control silently disagreeing with the chip
	// beside it.
	const current = doc?.status ?? "";
	const chosen = stage || current;

	if (applicant.isLoading) return <Spinner page label="Loading the application…" />;
	if (applicant.error) return <ErrorNote>{errorMessage(applicant.error)}</ErrorNote>;
	if (!doc) return <NotInstalled />;

	const decide = async () => {
		try {
			await move.call({ name, status: chosen });
			toast(`Moved to ${chosen}`);
			void applicant.mutate();
		} catch (error) {
			toast(errorMessage(error, "That could not be changed."));
		}
	};

	const place = async () => {
		try {
			await convert.call({ name });
			toast("Placed");
			void applicant.mutate();
		} catch (error) {
			toast(errorMessage(error, "This could not be turned into work."));
		}
	};

	const placed = Boolean(doc.deployment_assignment || doc.task);

	return (
		<>
			<BackLink to="/admin/recruitment/applications">Back to applications</BackLink>

			<div className="mb-4 flex flex-wrap items-center gap-4 rounded-xl bg-rail px-5 py-4 text-white">
				<Avatar name={doc.applicant_name} size={48} />
				<div className="min-w-0 flex-1">
					<h1 className="truncate text-[19px] font-semibold tracking-[-0.015em]">
						{doc.applicant_name ?? doc.name}
					</h1>
					<p className="mt-1 truncate text-[12.5px] text-white/65">
						{doc.opening_title ?? "—"} · applied {formatDate(doc.applied_on)}
					</p>
				</div>
				<div className="flex flex-none flex-wrap items-center gap-2">
					<StatusBadge state={doc.status} />
					{doc.is_withdrawn && <StatusBadge tone="neutral">Withdrawn</StatusBadge>}
				</div>
			</div>

			<div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
				<div className="min-w-0 space-y-4">
					{doc.cover_letter && (
						<Card>
							<h2 className="mb-2.5 text-[13.5px] font-semibold text-ink">Cover Letter</h2>
							<p className="whitespace-pre-wrap text-[13.5px] leading-relaxed text-slate-strong">
								{doc.cover_letter}
							</p>
						</Card>
					)}

					{doc.answers.length > 0 && (
						<Card>
							<h2 className="mb-3.5 text-[13.5px] font-semibold text-ink">Screening answers</h2>
							<ul className="space-y-4">
								{doc.answers.map((answer) => (
									<li key={answer.question_id}>
										{/* The question as it was asked at the time, copied
										    onto the answer when they applied. A society that
										    reworded it since has not reworded this. */}
										<div className="text-[12px] font-medium text-muted">{answer.question}</div>
										<div className="mt-1 text-[13.5px] leading-relaxed text-ink">
											{answer.answer_file ? (
												<a
													href={answer.answer_file}
													target="_blank"
													rel="noreferrer"
													className="inline-flex items-center gap-1.5 font-semibold text-blue hover:text-blue-hover"
												>
													<Icon.file size={14} />
													Open the attachment
												</a>
											) : (
												answer.answer || "—"
											)}
										</div>
									</li>
								))}
							</ul>
						</Card>
					)}

					{doc.is_withdrawn && (
						// The danger hairline, written out here rather than as a `Card`
						// prop: the volunteer portal wanted no red edges on any of its
						// panels, and this is the one console panel that still earns one.
						<Card className="!border-danger/55">
							<h2 className="text-[13.5px] font-semibold text-ink">Withdrawn</h2>
							<p className="mt-1.5 text-[13px] leading-relaxed text-slate-strong">
								{doc.withdrawal_reason || "No reason was given."}
							</p>
							<p className="mt-1 text-[11.5px] text-muted">{formatDate(doc.withdrawn_on)}</p>
						</Card>
					)}
				</div>

				<div className="space-y-4 lg:sticky lg:top-[76px] lg:self-start">
					<Card>
						<h2 className="mb-3.5 text-[13.5px] font-semibold text-ink">Who this is</h2>
						<DetailList>
							<Detail label="Full Name">{doc.applicant_name ?? "—"}</Detail>
							<Detail label="Email Address">{doc.email ?? "—"}</Detail>
							<Detail label="Phone Number">{doc.phone ?? "—"}</Detail>
							<Detail label="Country">{doc.country ?? "—"}</Detail>
							<Detail label="Designation">{doc.designation ?? "—"}</Detail>
							<Detail label="Source">{doc.source ?? "—"}</Detail>
							<Detail label="Source Name">{doc.source_name ?? "—"}</Detail>
							<Detail label="Geo Node">{branchPath(doc.geo_node) || doc.geo_node || "—"}</Detail>
							<Detail label="Volunteer">
								{doc.volunteer ? (
									<Link
										to={`/admin/registry/volunteers/${encodeURIComponent(doc.volunteer)}`}
										className="font-semibold text-blue hover:text-blue-hover"
									>
										Open their record
									</Link>
								) : (
									"Not in the register"
								)}
							</Detail>
							<Detail label="Red Profile">{doc.red_profile ?? "—"}</Detail>
							<Detail label="Employee Referral">{doc.employee_referral ?? "—"}</Detail>
						</DetailList>

						{doc.resume_attachment && (
							<a
								href={doc.resume_attachment}
								target="_blank"
								rel="noreferrer"
								className="mt-4 inline-flex items-center gap-1.5 text-[12.5px] font-semibold text-blue hover:text-blue-hover"
							>
								<Icon.file size={14} />
								Attachment
							</a>
						)}
					</Card>

					{doc.can_write && !doc.is_withdrawn && (
						<DecisionCard eyebrow="Decision" title="Move this application">
							<Field label="Status">
								<Select
									value={chosen}
									onChange={setStage}
									options={doc.statuses.map((value) => ({ value, label: value }))}
								/>
							</Field>

							<Button onClick={() => void decide()} disabled={chosen === current} busy={move.loading}>
								Save status
							</Button>

							{/* Accepting and placing are two decisions, and the server
							    keeps them apart: `convert` is idempotent and refuses a
							    second run, so this appears once and then reports what it
							    produced rather than offering to do it again. */}
							{doc.status === "Accepted" && (
								<div className="border-t p-divide pt-3.5">
									{placed ? (
										<p className="text-[12.5px] leading-relaxed text-success">
											Already placed{doc.deployment_assignment ? " on a deployment" : " on a task"}.
										</p>
									) : (
										<>
											<Button tone="soft" onClick={() => void place()} busy={convert.loading}>
												Turn this into work
											</Button>
											<p className="mt-2 text-[11.5px] leading-relaxed text-muted">
												Creates the deployment assignment or task the opening was for.
											</p>
										</>
									)}
								</div>
							)}
						</DecisionCard>
					)}
				</div>
			</div>
		</>
	);
}
