import { useContext, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, cardUrl, certificateUrl, errorMessage } from "../lib/api";
import { formatDate, formatHours, formatMoney, geoPath } from "../lib/format";
import { MultiCombo } from "../ui/form";
import { PersonHero, RegisterLinks } from "../ui/PersonHero";
import { RecordPayment, owesAFee } from "./RecordPayment";
import {
	Button,
	Card,
	Cell,
	Empty,
	ErrorNote,
	Pill,
	Row,
	SectionTitle,
	Spinner,
	StateBadge,
	Table,
	cx,
} from "../ui/primitives";
import type {
	ApplicationOptions,
	DecisionRow,
	DossierBackground,
	MemberDossier,
	SelectorRow,
	VolunteerDossier,
} from "../portal/types";

/**
 * One person, opened from the registry.
 *
 * **The route names the audience, because a docname cannot.** `VOL-00042` and
 * `MEM-00042` are two different people and nothing about either string says
 * which register it belongs to, so the kind is a path segment rather than
 * something this screen guesses or probes for by calling both endpoints.
 *
 * **One read per person, not seven.** Both dossiers are composed server-side and
 * resolved at a single `as_of`, which is not only about round trips: every block
 * below is derived, and blocks derived at different instants can contradict each
 * other. A certification shown as current beside a deployability indicator
 * computed a second later, after midnight passed, is wrong in the way that is
 * hardest to notice. The endpoints' docstrings argue the same point from the
 * other side.
 *
 * **Nothing here decides what anybody may do.** `can_act` is the server's
 * answer, from the same `write` check the act endpoints enforce, so no role name
 * appears in this file and the buttons cannot offer something the server would
 * refuse. A volunteer following a stale link to their own record reads it
 * through the holder bypass and is offered nothing.
 *
 * **Composed, never merged**, exactly as the DTOs are: a volunteer's current
 * skills and the skills they declared when applying are drawn in two different
 * blocks and never reconciled. One is what is true, the other is what was
 * claimed, and a coordinator comparing them is the point.
 *
 * **Both registers open with the same header**, `PersonHero` — a face, a name,
 * a standing and the four or five facts somebody needs in order to act, with
 * everything else in the cards beneath. That is the same block the review queue
 * and the volunteer's own portal profile open with, so a person looks like a
 * person on every screen in this product rather than like a docname on some of
 * them. See the component for the argument.
 *
 * **A volunteer here can say they are also a member, and the other way round.**
 * The two registers hang off one Red Profile, the server resolves the hop
 * (`api/person.py`), and the chip links straight across. It is the question a
 * counter asks immediately after opening either record, and answering it used
 * to mean leaving the page and searching the other register by name.
 */
export default function Person() {
	const { kind, name } = useParams<{ kind: string; name: string }>();

	if (!name) {
		return <ErrorNote>That link does not name anybody.</ErrorNote>;
	}

	if (kind === "volunteer") {
		return <VolunteerPage name={name} />;
	}

	if (kind === "member") {
		return <MemberPage name={name} />;
	}

	return <ErrorNote>There is no register of that kind.</ErrorNote>;
}

/* ------------------------------------------------------------ shared panels */

/**
 * The branch's own note about a person, on either register.
 *
 * `VMMS Volunteer.notes` and `VMMS Member.notes` have been on their doctypes
 * since they were written, carried by no DTO and writable from no screen — so a
 * note made at the desk was invisible here and a coordinator working from the
 * console could not make one at all. It is the register's margin: why somebody
 * is placed where they are, what a branch agreed with them, what to remember
 * before deploying them again.
 *
 * **Drawn read-only for the person it is about.** `can_act` is the server's own
 * answer and the holder gets `false` — the same split `_writable` enforces, so
 * this panel cannot offer an edit the save would refuse.
 */
function RegisterNotes({
	notes,
	canAct,
	endpoint,
	name,
	onChanged,
}: {
	notes: string | null;
	canAct: boolean;
	endpoint: string;
	name: string;
	onChanged: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [open, setOpen] = useState(false);
	const [draft, setDraft] = useState(notes ?? "");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	// Nothing recorded and nothing anybody here may record: the panel would be
	// an empty box explaining a feature this reader does not have.
	if (!canAct && !notes) return null;

	const save = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(endpoint, { name, notes: draft.trim() });
			setOpen(false);
			onChanged();
		} catch (problem) {
			setFailure(errorMessage(problem, "That note was not saved."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card className="mb-5">
			<div className="flex flex-wrap items-start justify-between gap-2">
				<SectionTitle>Branch notes</SectionTitle>
				{canAct && !open && (
					<button
						type="button"
						onClick={() => {
							setDraft(notes ?? "");
							setOpen(true);
						}}
						className="text-[12px] font-semibold text-ink hover:underline"
					>
						{notes ? "Edit" : "Add a note"}
					</button>
				)}
			</div>

			{open ? (
				<div className="mt-3">
					<textarea
						value={draft}
						rows={5}
						onChange={(event) => setDraft(event.target.value)}
						placeholder="Why they are placed where they are, what was agreed, what to remember."
						className="w-full resize-y rounded-lg border border-rail-line bg-white px-3 py-2 text-[13px] leading-relaxed text-ink outline-none transition placeholder:text-slate-faint focus:border-blue focus:ring-[3px] focus:ring-blue-soft"
					/>
					<p className="mt-1.5 text-[11.5px] leading-relaxed text-muted">
						Seen by coordinators, not by the person it is about. Clearing it removes it.
					</p>

					{failure && (
						<div className="mt-3">
							<ErrorNote>{failure}</ErrorNote>
						</div>
					)}

					<div className="mt-3 flex flex-wrap gap-2">
						<Button onClick={() => void save()} disabled={busy}>
							{busy ? "Saving…" : "Save note"}
						</Button>
						<Button variant="navy" onClick={() => setOpen(false)}>
							Cancel
						</Button>
					</div>
				</div>
			) : notes ? (
				<p className="mt-2 whitespace-pre-line text-[13px] leading-relaxed text-muted">{notes}</p>
			) : (
				<p className="mt-2 text-[13px] text-slate-faint">Nothing recorded.</p>
			)}
		</Card>
	);
}

/**
 * What a volunteer can do now, and correcting it.
 *
 * **The volunteer's own record, not the claim on their application.** That
 * distinction is `volunteer/services/capabilities.py`'s whole reason for
 * existing — what somebody said when they applied is a claim made once, what
 * they can do now is a fact the branch maintains — and until this panel the
 * second could only ever be written by the acceptance that created the record.
 * A volunteer who qualified as a first-aider in March had no way to have it
 * recorded, and every candidate search that filters on skills went on missing
 * them.
 */
function Capabilities({
	volunteer,
	capabilities,
	canAct,
	onChanged,
}: {
	volunteer: string;
	capabilities: VolunteerDossier["capabilities"];
	canAct: boolean;
	onChanged: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;

	const [open, setOpen] = useState(false);
	const [skills, setSkills] = useState<string[]>([]);
	const [languages, setLanguages] = useState<string[]>([]);
	const [availability, setAvailability] = useState<string[]>([]);
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	// The society's own vocabularies, and the same call the registration wizard
	// draws its pickers from — so a coordinator and an applicant are choosing
	// from one list rather than two that could drift apart.
	const options = useFrappeGetCall<{ message: ApplicationOptions }>(
		API.applicationOptions,
		undefined,
		open ? "admin:person:vocabularies" : null,
	);

	const begin = () => {
		setSkills(capabilities.skills.map((row) => row.key));
		setLanguages(capabilities.languages.map((row) => row.key));
		setAvailability(capabilities.availability.map((row) => row.key));
		setOpen(true);
	};

	const save = async () => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.setVolunteerCapabilities, {
				name: volunteer,
				skills,
				languages,
				availability,
			});
			setOpen(false);
			onChanged();
		} catch (problem) {
			setFailure(errorMessage(problem, "That was not saved."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card className="mb-5">
			<div className="flex flex-wrap items-start justify-between gap-2">
				<SectionTitle>What they can do now</SectionTitle>
				{canAct && !open && (
					<button
						type="button"
						onClick={begin}
						className="text-[12px] font-semibold text-ink hover:underline"
					>
						Edit
					</button>
				)}
			</div>

			{open ? (
				<div className="mt-4 space-y-4">
					{options.isLoading ? (
						<Spinner label="Loading the society's lists…" />
					) : (
						<>
							<MultiCombo
								label="Skills"
								selected={skills}
								onToggle={(key) => setSkills(toggled(skills, key))}
								options={options.data?.message?.skills ?? []}
								placeholder="Search and add a skill"
								empty="No skills are configured on this site yet."
							/>
							<MultiCombo
								label="Languages"
								selected={languages}
								onToggle={(key) => setLanguages(toggled(languages, key))}
								options={options.data?.message?.languages ?? []}
								placeholder="Search and add a language"
								empty="No languages are configured on this site yet."
							/>
							<MultiCombo
								label="Availability"
								selected={availability}
								onToggle={(key) => setAvailability(toggled(availability, key))}
								options={options.data?.message?.availability ?? []}
								placeholder="Search and add a slot"
								empty="No availability slots are configured on this site yet."
							/>
						</>
					)}

					{failure && <ErrorNote>{failure}</ErrorNote>}

					<div className="flex flex-wrap gap-2">
						<Button onClick={() => void save()} disabled={busy}>
							{busy ? "Saving…" : "Save"}
						</Button>
						<Button variant="navy" onClick={() => setOpen(false)}>
							Cancel
						</Button>
					</div>
				</div>
			) : (
				<Definitions
					rows={[
						["Skills", labels(capabilities.skills)],
						["Languages", labels(capabilities.languages)],
						["Availability", labels(capabilities.availability)],
					]}
				/>
			)}
		</Card>
	);
}

/** Add or remove one key from a selection. */
function toggled(values: string[], key: string): string[] {
	return values.includes(key) ? values.filter((value) => value !== key) : [...values, key];
}

/* ------------------------------------------------------------- the volunteer */

type VolunteerTab = "overview" | "background" | "service" | "verification" | "notes";
type MemberTab = "overview" | "memberships" | "verification" | "notes";

function DossierTabs<T extends string>({
	value,
	onChange,
	items,
}: {
	value: T;
	onChange: (value: T) => void;
	items: readonly (readonly [T, string])[];
}) {
	return (
		<div className="mb-5 overflow-x-auto rounded-xl bg-surface p-1" role="tablist">
			<div className="flex min-w-max gap-1">
				{items.map(([key, label]) => (
					<button
						key={key}
						type="button"
						role="tab"
						aria-selected={value === key}
						onClick={() => onChange(key)}
						className={cx(
							"rounded-lg px-4 py-2.5 text-[12px] font-bold transition",
							value === key
								? "bg-white text-ink shadow-sm"
								: "text-muted hover:bg-white/60 hover:text-ink",
						)}
					>
						{label}
					</button>
				))}
			</div>
		</div>
	);
}

function VolunteerPage({ name }: { name: string }) {
	const [tab, setTab] = useState<VolunteerTab>("overview");
	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: VolunteerDossier }>(
		API.volunteerDossier,
		{ name },
		`admin:volunteer:${name}`,
	);

	const dossier = data?.message;

	if (isLoading) {
		return <Spinner label="Reading this volunteer's record…" page />;
	}

	if (error) {
		return <ErrorNote>{errorMessage(error, "That volunteer could not be read.")}</ErrorNote>;
	}

	if (!dossier) {
		return <Empty title="Nothing to show">That volunteer could not be read.</Empty>;
	}

	const person = dossier.identity;
	const onChanged = () => void mutate();

	return (
		<>
			<BackToRegister kind="volunteer" />

			<PersonHero
				name={person.full_name}
				photo={person.profile_photo}
				docname={dossier.volunteer}
				// Two Geo Nodes answering two different questions, under names that
				// differ. Calling either of them simply "branch" is the confusion
				// ACC-02 invites, so the serving branch is labelled where it sits
				// and the home area stays a fact below.
				subtitle={geoPath(person.geo_path) || "No serving branch recorded"}
				status={person.status}
				badges={
					<>
						<RegisterLinks registers={dossier.registers} except="volunteer" />
						<Pill tone="page">as at {formatDate(dossier.as_of)}</Pill>
					</>
				}
				facts={[
					{ label: "Email", value: person.email },
					{ label: "Phone", value: person.phone },
					{ label: "Joined", value: formatDate(person.joined_on) },
					{ label: "Home area", value: geoPath(person.home_geo_path) },
				]}
			/>

			{dossier.can_act && (
				<VolunteerActions dossier={dossier} onActed={() => void mutate()} />
			)}

			{/* Drawn only when there is a card to print. `holds_card` is the same
			    predicate `download_card` asserts on, so this link cannot offer
			    something the server would refuse. */}
			{dossier.holds_card && (
				<Card className="mb-5">
					<SectionTitle>Reprint</SectionTitle>
					<a
						href={cardUrl("volunteer", dossier.volunteer)}
						className="inline-flex items-center justify-center rounded-xl border border-card-line bg-white px-5 py-2.5 text-[13px] font-bold text-slate-strong transition hover:border-blue hover:text-ink"
					>
						Volunteer card (PDF)
					</a>
				</Card>
			)}

			<DossierTabs
				value={tab}
				onChange={setTab}
				items={[
					["overview", "Overview"],
					["background", "Background"],
					["service", "Service & deployments"],
					["verification", "Verification"],
					["notes", "Notes & history"],
				]}
			/>

			{/* What the header could not carry. The contact details, the joining
			    date and the home area are above; these are the facts a
			    volunteering office is asked for rather than the ones needed to
			    reach somebody, and here they say "Not recorded" out loud when
			    they are missing — which in a card is a finding rather than a
			    blank. */}
			{tab === "overview" && <><Card className="mb-5">
				<SectionTitle>Who they are</SectionTitle>
				<Definitions
					rows={[
						["Gender", person.gender],
						["Date of birth", formatDate(person.date_of_birth)],
						["Preferred language", person.preferred_language],
						// Two Geo Nodes answering two different questions, under names
						// that differ. Calling either of them simply "branch" is the
						// confusion ACC-02 invites.
						["Serving branch", geoPath(person.geo_path)],
						["Home area", geoPath(person.home_geo_path)],
						["Profession", person.profession],
						["Exited", formatDate(person.exited_on)],
					]}
				/>
			</Card>

			</>}

			{tab === "background" && <BackgroundCard background={person.background} />}

			{tab === "overview" && <><Card className="mb-5">
				<SectionTitle>May they be deployed</SectionTitle>
				<div className="mb-3">
					{dossier.deployability.deployable ? (
						<Pill tone="page">Ready to deploy</Pill>
					) : (
						<Pill tone="page">Blocked</Pill>
					)}
				</div>
				{dossier.deployability.reasons.length === 0 ? (
					<p className="text-[13px] text-muted">
						Nothing is standing in the way as at {formatDate(dossier.deployability.as_of)}.
					</p>
				) : (
					<ul className="list-disc space-y-1 pl-5 text-[13px] text-muted">
						{dossier.deployability.reasons.map((reason) => (
							<li key={reason}>{reason}</li>
						))}
					</ul>
				)}
			</Card>

			<Capabilities
				volunteer={dossier.volunteer}
				capabilities={dossier.capabilities}
				canAct={dossier.can_act}
				onChanged={onChanged}
			/>
			</>}

			{tab === "notes" && <RegisterNotes
				notes={person.notes ?? null}
				canAct={dossier.can_act}
				endpoint={API.setVolunteerNotes}
				name={dossier.volunteer}
				onChanged={onChanged}
			/>}

			{tab === "service" && <><Card className="mb-5">
				<SectionTitle>Certifications held</SectionTitle>
				{dossier.certifications.length === 0 ? (
					<Empty title="No certifications recorded">
						Nothing has been recorded against this volunteer yet.
					</Empty>
				) : (
					<Table head={["Certification", "Completed", "Expires", "Reference", "Standing"]}>
						{dossier.certifications.map((row) => (
							<Row key={row.name}>
								<Cell>
									<span className="font-semibold text-ink">
										{row.certification_type_name}
									</span>
								</Cell>
								<Cell className="text-muted">{formatDate(row.completion_date)}</Cell>
								<Cell className="text-muted">{formatDate(row.expiry_date)}</Cell>
								<Cell className="text-muted">{row.reference_number || "—"}</Cell>
								<Cell>
									{row.lapsed ? (
										<Pill tone="page">
											{row.blocks_deployment ? "Lapsed · blocks deployment" : "Lapsed"}
										</Pill>
									) : (
										<Pill tone="page">Current</Pill>
									)}
								</Cell>
							</Row>
						))}
					</Table>
				)}
			</Card>

			<Card className="mb-5">
				<SectionTitle>Where they have served</SectionTitle>
				{dossier.deployments.length === 0 ? (
					<Empty title="No deployments recorded">
						This volunteer has not been rostered onto anything yet.
					</Empty>
				) : (
					<Table head={["Deployment", "Terms", "From", "To", "Status"]}>
						{dossier.deployments.map((row) => (
							<Row key={`${row.deployment}-${row.joined_on ?? ""}`}>
								<Cell>
									<span className="font-mono text-[12px] text-slate-faint">
										{row.deployment}
									</span>
								</Cell>
								<Cell className="text-muted">{row.tor_name || "—"}</Cell>
								{/* The roster row's own dates, so somebody who left early
								    reads as having left rather than as never having been there. */}
								<Cell className="text-muted">{formatDate(row.joined_on)}</Cell>
								<Cell className="text-muted">{formatDate(row.left_on)}</Cell>
								<Cell>
									<StateBadge state={row.status ?? undefined} />
								</Cell>
							</Row>
						))}
					</Table>
				)}
			</Card>

			<Card className="mb-5">
				<SectionTitle>What they have given</SectionTitle>
				<div className="mb-4 flex flex-wrap gap-2">
					<Pill tone="page">{formatHours(dossier.time.total_hours)} in total</Pill>
					<Pill tone="page">{dossier.time.log_count} logs</Pill>
					{/* Keyed by whatever `log_type` values came back. No kind is named
					    here, the same rule the service itself follows. */}
					{Object.entries(dossier.time.hours_by_type).map(([kind, hours]) => (
						<Pill key={kind} tone="page">
							{kind}: {formatHours(hours)}
						</Pill>
					))}
				</div>
				{dossier.time.recent.length === 0 ? (
					<Empty title="No hours logged">Nothing has been filed against this volunteer.</Empty>
				) : (
					<Table head={["Date", "Category", "Where", "Hours"]}>
						{dossier.time.recent.map((row) => (
							<Row key={row.name}>
								<Cell className="text-muted">{formatDate(row.activity_date)}</Cell>
								<Cell className="text-muted">{row.category_label || "—"}</Cell>
								<Cell className="text-muted">{geoPath(row.geo_path)}</Cell>
								<Cell className="text-muted">{formatHours(row.hours)}</Cell>
							</Row>
						))}
					</Table>
				)}
			</Card></>}

			{tab === "verification" && <><Card className="mb-5">
				<SectionTitle>How they were verified</SectionTitle>
				<Verification verification={dossier.application} />
			</Card>

			{dossier.application.declared && (
				<Card>
					<SectionTitle>Declared when they applied</SectionTitle>
					<p className="mb-4 text-[13px] text-muted">
						What this person said about themselves on{" "}
						{formatDate(dossier.application.applied_on) || "the day they applied"}. This is not
						what they can currently do, which is above.
					</p>
					<Definitions
						rows={[
							["Skills", labels(dossier.application.declared.skills)],
							["Languages", labels(dossier.application.declared.languages)],
							["Availability", labels(dossier.application.declared.availability)],
							["Motivation", labels(dossier.application.declared.motivation)],
							["Prior experience", dossier.application.declared.prior_experience],
						]}
					/>
				</Card>
			)}</>}
		</>
	);
}

/* ---------------------------------------------------------------- the member */

function MemberPage({ name }: { name: string }) {
	const [tab, setTab] = useState<MemberTab>("overview");
	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: MemberDossier }>(
		API.memberDossier,
		{ name },
		`admin:member:${name}`,
	);

	const dossier = data?.message;

	if (isLoading) {
		return <Spinner label="Reading this member's record…" page />;
	}

	if (error) {
		return <ErrorNote>{errorMessage(error, "That member could not be read.")}</ErrorNote>;
	}

	if (!dossier) {
		return <Empty title="Nothing to show">That member could not be read.</Empty>;
	}

	const person = dossier.identity;

	return (
		<>
			<BackToRegister kind="member" />

			<PersonHero
				name={person.full_name}
				photo={person.profile_photo}
				docname={dossier.member}
				// Where they currently hold a membership, which is the thing a
				// membership desk needs beside the name. A person may hold several,
				// so this is every current branch rather than "the" branch.
				subtitle={
					dossier.standing.current_geo_paths.map((path) => geoPath(path)).join(" · ") ||
					"No current membership"
				}
				status={dossier.standing.status}
				badges={
					<>
						<RegisterLinks registers={dossier.registers} except="member" />
						<Pill tone="page">as at {formatDate(dossier.as_of)}</Pill>
					</>
				}
				facts={[
					{ label: "Email", value: person.email },
					{ label: "Phone", value: person.phone },
					{ label: "Member since", value: formatDate(dossier.standing.joined_on) },
					{ label: "Home area", value: geoPath(person.home_geo_path) },
				]}
			/>

			<DossierTabs
				value={tab}
				onChange={setTab}
				items={[
					["overview", "Overview"],
					["memberships", "Memberships"],
					["verification", "Verification"],
					["notes", "Notes & history"],
				]}
			/>

			{/* What the header could not carry — see the volunteer page's note. */}
			{tab === "overview" && <><Card className="mb-5">
				<SectionTitle>Who they are</SectionTitle>
				<Definitions
					rows={[
						["Gender", person.gender],
						["Date of birth", formatDate(person.date_of_birth)],
						["Preferred language", person.preferred_language],
						["Country of citizenship", person.country_of_citizenship],
						["Citizenship status", person.citizenship_status],
						["Residency", person.residency_type],
						[
							"Residence",
							person.residency_type === "Abroad"
								? [person.country_of_residence, person.residence_address]
										.filter(Boolean)
										.join(" · ")
								: geoPath(person.home_geo_path),
						],
					]}
				/>
			</Card>

			<Card className="mb-5">
				<SectionTitle>Where they stand</SectionTitle>
				<div className="mb-4 flex flex-wrap gap-2">
					<Pill tone="page">{dossier.standing.current_count} current</Pill>
					<Pill tone="page">{dossier.standing.lapsed_count} lapsed</Pill>
					<Pill tone="page">{dossier.standing.visible_count} visible to you</Pill>
				</div>
				{/* "Member since" and the current branches are in the header. What is
				    left here is the counting, which is what this card is for. */}
				<Definitions
					rows={[
						[
							"Currently a member at",
							dossier.standing.current_geo_paths.map((path) => geoPath(path)).join(" · "),
						],
					]}
				/>
				{/* Said out loud because a coordinator seeing "Active" above a plainly
				    expired membership should not have to work out which one carries it. */}
				<p className="mt-4 text-[12px] text-slate-faint">
					Standing is over every membership this person holds. The counts are over the ones
					your scope lets you see.
				</p>
			</Card></>}

			{tab === "notes" && <RegisterNotes
				notes={dossier.notes}
				canAct={dossier.can_act}
				endpoint={API.setMemberNotes}
				name={dossier.member}
				onChanged={() => void mutate()}
			/>}

			{tab === "memberships" && <Card className="mb-5">
				<SectionTitle>Memberships held</SectionTitle>
				{dossier.memberships.length === 0 ? (
					<Empty title="No memberships in your scope">
						Either this person holds none, or they are all at branches your Geo Assignments
						do not cover.
					</Empty>
				) : (
					<div className="space-y-4">
						{dossier.memberships.map((row) => (
							<MembershipCard
								key={row.name}
								row={row}
								canAct={dossier.can_act}
								onActed={() => void mutate()}
							/>
						))}
					</div>
				)}
			</Card>}

			{tab === "verification" && <Card>
				<SectionTitle>How they were verified</SectionTitle>
				{dossier.history.length === 0 ? (
					<Empty title="No decisions recorded">
						Nothing in this person's memberships has been through an approval.
					</Empty>
				) : (
					<Table head={["Decided", "Decision", "Stage", "By", "Membership"]}>
						{dossier.history.map((row, index) => (
							<Row key={`${row.membership}-${index}`}>
								<Cell className="text-muted">{formatDate(row.decided_on)}</Cell>
								<Cell>
									<StateBadge state={row.decision ?? undefined} />
								</Cell>
								{/* Display only. Nothing here compares a stage label. */}
								<Cell className="text-muted">{row.stage_label || "—"}</Cell>
								<Cell className="text-muted">{row.approver || "—"}</Cell>
								<Cell className="font-mono text-[11px] text-slate-faint">
									{row.membership}
								</Cell>
							</Row>
						))}
					</Table>
				)}
			</Card>}
		</>
	);
}

/* --------------------------------------------------------------- the pieces */

/**
 * The way back, in words rather than left to the browser's own button.
 *
 * A coordinator who arrived here from a colleague's link has no back button
 * that goes anywhere useful, and a page that can only be left by retyping a URL
 * is a dead end. This is the same link the review queue's decision page draws
 * above its own header, for the same reason.
 *
 * There is no `PageHeading` above it any more: `PersonHero` *is* this page's
 * heading, and a title bar repeating the name above a block that opens with the
 * name reads as a template with a hole in it.
 */
function BackToRegister({ kind }: { kind: "volunteer" | "member" }) {
	return (
		<Link
			to={kind === "volunteer" ? "/admin/registry/volunteers" : "/admin/registry/members"}
			className="mb-4 inline-block text-[12px] font-semibold text-ink hover:underline"
		>
			{kind === "volunteer" ? "← Back to volunteers" : "← Back to members"}
		</Link>
	);
}

function Verification({
	verification,
}: {
	verification: VolunteerDossier["application"];
}) {
	if (!verification.application) {
		return (
			<Empty title="No application behind this record">
				This volunteer was recorded directly rather than through an application, so there is no
				approval trail to show.
			</Empty>
		);
	}

	return (
		<>
			<Definitions
				rows={[
					["Applied on", formatDate(verification.applied_on)],
					["Outcome", verification.approval_state],
					["Application", verification.application],
					[
						"Applications on file",
						verification.application_count > 1 ? String(verification.application_count) : null,
					],
				]}
			/>
			{verification.decisions.length > 0 && <Decisions rows={verification.decisions} />}
		</>
	);
}

function Decisions({ rows }: { rows: DecisionRow[] }) {
	return (
		<div className="mt-4">
			<Table head={["Decided", "Decision", "Stage", "By", "Reason"]}>
				{rows.map((row, index) => (
					<Row key={index}>
						<Cell className="text-muted">{formatDate(row.decided_on)}</Cell>
						<Cell>
							<StateBadge state={row.decision ?? undefined} />
						</Cell>
						{/* Display only, snapshotted by the engine. Never compared. */}
						<Cell className="text-muted">{row.stage_label || "—"}</Cell>
						<Cell className="text-muted">{row.approver || "—"}</Cell>
						<Cell className="text-muted">{row.reason || "—"}</Cell>
					</Row>
				))}
			</Table>
		</div>
	);
}

/** Label/value pairs. A row whose value is empty says so rather than being dropped. */
/**
 * What this person said they have already done.
 *
 * **Everything on this card is a claim, and the card says so.** It is what an
 * applicant typed about themselves during registration; nobody has verified any
 * of it. A branch that needs a qualification to be true issues a
 * `VMMS Certification`, which is a decision somebody makes and appears further
 * down this page under its own heading.
 *
 * **Drawn only when there is something on it.** Every one of these tables is
 * optional for the person filling it in, so five empty tables and a "Not
 * recorded" would report an omission that was never a gap — unlike "Who they
 * are" above, where a missing date of birth genuinely is a finding.
 *
 * **No attachments, and that is not an oversight.** The certificates and licence
 * scans behind these rows are private files anchored to the Red Profile, so the
 * link would resolve to a refusal for most people reading this page. They are
 * opened on the desk, on the profile itself. See `identity._BACKGROUND`.
 */
function BackgroundCard({ background }: { background?: DossierBackground }) {
	if (!background) return null;

	const sections: Array<{ title: string; head: string[]; rows: string[][] }> = [
		{
			title: "Education",
			head: ["Institution", "Qualification", "Level", "Years"],
			rows: background.education.map((row) => [
				row.institution,
				row.qualification,
				row.level,
				[row.started_in, row.is_ongoing ? "now" : row.finished_in].filter(Boolean).join("–"),
			]),
		},
		{
			title: "Training and courses",
			head: ["Course", "Run by", "Completed"],
			rows: background.training.map((row) => [
				row.course_name,
				row.institution,
				formatDate(row.completed_on),
			]),
		},
		{
			title: "Experience",
			head: ["Organization", "Role", "From", "To"],
			rows: background.work_experience.map((row) => [
				row.organization,
				row.role,
				formatDate(row.started_on),
				row.is_current ? "Still there" : formatDate(row.ended_on),
			]),
		},
		{
			title: "Licences",
			head: ["Licence", "Issued by", "Number", "Valid until"],
			rows: background.licences.map((row) => [
				row.license_name,
				row.institution,
				row.registration_no,
				row.does_not_expire ? "Does not expire" : formatDate(row.valid_to),
			]),
		},
		{
			title: "Driving",
			head: ["Class", "Number", "Valid until"],
			rows: background.driving_licences.map((row) => [
				row.licence_class,
				row.licence_number,
				formatDate(row.valid_to),
			]),
		},
		{
			title: "Referees",
			head: ["Name", "How they know them", "Phone", "Email"],
			rows: background.references.map((row) => [
				row.reference_name,
				row.relationship || row.position,
				row.phone,
				row.email,
			]),
		},
	].filter((section) => section.rows.length > 0);

	if (sections.length === 0) return null;

	return (
		<Card className="mb-5">
			<SectionTitle>What they say they have done</SectionTitle>
			<p className="mb-4 text-[12.5px] leading-relaxed text-muted">
				Told to us by this person when they registered. None of it has been checked — what the
				Society has verified is under Certifications held.
			</p>

			<div className="space-y-6">
				{sections.map((section) => (
					<div key={section.title}>
						<p className="mb-2 text-[11px] font-bold uppercase tracking-wide text-slate-faint">
							{section.title}
						</p>
						<Table head={section.head}>
							{section.rows.map((cells, index) => (
								<Row key={index}>
									{cells.map((cell, at) => (
										<Cell key={at} className={cell ? undefined : "text-muted"}>
											{cell || "—"}
										</Cell>
									))}
								</Row>
							))}
						</Table>
					</div>
				))}
			</div>
		</Card>
	);
}

function Definitions({ rows }: { rows: Array<[string, string | null | undefined]> }) {
	return (
		<dl className="grid gap-4 sm:grid-cols-2">
			{rows.map(([label, value]) => (
				<div key={label}>
					<dt className="text-[11px] font-bold uppercase tracking-wide text-slate-faint">
						{label}
					</dt>
					<dd className={cx("mt-1 text-[14px]", value ? "text-ink" : "text-slate-faint")}>
						{value || "Not recorded"}
					</dd>
				</div>
			))}
		</dl>
	);
}

function labels(rows: SelectorRow[] | undefined): string {
	return (rows || []).map((row) => row.label).join(", ");
}

/* --------------------------------------------------------------- the acts */

/**
 * What may be done to a volunteer's standing, from where it stands now.
 *
 * A table rather than a chain of conditions, the same shape the desk script and
 * the Python dispatch tables use. **Branching on `status` is allowed and
 * branching on a stage label is not**: a stage is a society's word, and this is
 * a closed Select this app owns with four values. A status this file does not
 * know offers nothing, which is the direction a dispatch table should fail in.
 *
 * Drawn only when the server said `can_act`, and every one of these is re-checked
 * server-side when pressed.
 */
const VOLUNTEER_VERBS: Record<string, Array<keyof typeof VOLUNTEER_ACTS>> = {
	Prospective: ["suspend", "exit"],
	Active: ["suspend", "exit"],
	Suspended: ["reinstate", "exit"],
	Exited: ["reinstate"],
};

const VOLUNTEER_ACTS = {
	suspend: {
		label: "Suspend",
		method: API.suspendVolunteer,
		prompt: "Why is this volunteer being suspended?",
	},
	reinstate: {
		label: "Reinstate",
		method: API.reinstateVolunteer,
		prompt: "Why is this volunteer being reinstated?",
		// Said out loud because it surprises people: reinstating hands the
		// question back to the applications rather than setting somebody Active.
		note: "Standing returns to whatever this volunteer's applications support, which may be Prospective rather than Active.",
	},
	exit: {
		label: "Record exit",
		method: API.recordVolunteerExit,
		prompt: "Why are they leaving?",
		dated: true,
	},
} as const;

function VolunteerActions({
	dossier,
	onActed,
}: {
	dossier: VolunteerDossier;
	onActed: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [open, setOpen] = useState<keyof typeof VOLUNTEER_ACTS | null>(null);
	const [reason, setReason] = useState("");
	const [onDate, setOnDate] = useState(() => new Date().toISOString().slice(0, 10));
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const verbs = VOLUNTEER_VERBS[dossier.identity.status] || [];

	if (verbs.length === 0) {
		return null;
	}

	const act = open ? VOLUNTEER_ACTS[open] : null;

	const perform = async () => {
		if (!act || !open) {
			return;
		}

		setBusy(true);
		setFailure(null);

		try {
			await call.post(act.method, {
				name: dossier.volunteer,
				reason,
				...("dated" in act && act.dated ? { on_date: onDate } : {}),
			});
			setOpen(null);
			setReason("");
			onActed();
		} catch (actError) {
			setFailure(errorMessage(actError, "That change was not recorded."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card className="mb-5">
			<SectionTitle>Standing</SectionTitle>

			<div className="flex flex-wrap gap-2">
				{verbs.map((verb) => (
					<Button
						key={verb}
						variant={open === verb ? "navy" : "quiet"}
						onClick={() => {
							setOpen(open === verb ? null : verb);
							setFailure(null);
						}}
					>
						{VOLUNTEER_ACTS[verb].label}
					</Button>
				))}
			</div>

			{act && (
				<div className="mt-5 border-t border-card-line pt-5">
					{"note" in act && act.note && (
						<p className="mb-3 text-[13px] text-muted">{act.note}</p>
					)}

					{"dated" in act && act.dated && (
						<label className="mb-3 block">
							<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
								Date they stopped volunteering
							</span>
							<input
								type="date"
								value={onDate}
								onChange={(event) => setOnDate(event.target.value)}
								className="w-full rounded-xl border border-card-line px-3 py-2 text-[14px]"
							/>
						</label>
					)}

					<label className="block">
						<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
							{act.prompt}
						</span>
						<textarea
							value={reason}
							onChange={(event) => setReason(event.target.value)}
							rows={3}
							className="w-full rounded-xl border border-card-line px-3 py-2 text-[14px]"
						/>
					</label>

					{/* Required here rather than only server-side: the service records a
					    comment only when a reason is given, which makes it the entire
					    record of why somebody's standing changed. */}
					<p className="mt-2 text-[12px] text-slate-faint">
						A reason is recorded against the volunteer. Nothing else says why this changed.
					</p>

					{failure && (
						<div className="mt-3">
							<ErrorNote>{failure}</ErrorNote>
						</div>
					)}

					<div className="mt-4 flex gap-2">
						<Button onClick={() => void perform()} disabled={busy || !reason.trim()}>
							{busy ? "Recording…" : act.label}
						</Button>
						<Button variant="ghost" onClick={() => setOpen(null)} disabled={busy}>
							Cancel
						</Button>
					</div>
				</div>
			)}
		</Card>
	);
}

/**
 * One membership, with the two acts that apply to it.
 *
 * **Cancel and expire are not two spellings of the same thing.** Cancel ends a
 * membership early and records why; expire closes one whose validity has already
 * run out and carries no reason, because the date is the reason. So expire is
 * offered only when `lapsed` says the window has actually closed — the same
 * predicate the endpoint checks before it will act, derived once server-side so
 * the button and the endpoint cannot disagree.
 *
 * There is no activate button, and the endpoint's docstring says why: activation
 * is a predicate re-evaluated from `on_update`, not a verb somebody performs. A
 * button forcing it would be a way around approval and payment both.
 *
 * **"Record the payment" is not that button, and the difference is the whole
 * design.** It confirms the *fee*, through the payments app, exactly as a
 * gateway callback would — so a membership on a type that routes to an approver
 * moves from Awaiting Payment to Awaiting Approval and stops there, which is
 * the correct answer and not a half-finished one. It is offered only where
 * there is something to record: a fee was charged, a payment was asked for, and
 * nobody has settled it yet.
 */
function MembershipCard({
	row,
	canAct,
	onActed,
}: {
	row: MemberDossier["memberships"][number];
	canAct: boolean;
	onActed: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [cancelling, setCancelling] = useState(false);
	const [reason, setReason] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);

	const perform = async (method: string, values: Record<string, unknown>) => {
		setBusy(true);
		setFailure(null);

		try {
			await call.post(method, { name: row.name, ...values });
			setCancelling(false);
			setReason("");
			onActed();
		} catch (actError) {
			setFailure(errorMessage(actError, "That change was not recorded."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div className="rounded-xl border border-card-line p-4">
			<div className="mb-3 flex flex-wrap items-start justify-between gap-3">
				<div>
					<p className="text-[15px] font-bold text-ink">
						{row.membership_type_name}
					</p>
					<p className="mt-0.5 font-mono text-[11px] text-slate-faint">{row.name}</p>
				</div>
				<StateBadge state={row.effective_status} />
			</div>

			<Definitions
				rows={[
					["Branch", geoPath(row.membership_geo_path)],
					["Valid from", formatDate(row.valid_from)],
					// A lifetime membership has no end date, and the DTO says so rather
					// than leaving a screen to infer it from a missing value.
					["Valid to", row.is_lifetime ? "Lifetime" : formatDate(row.valid_to)],
					["Fee", row.fee ? formatMoney(row.fee.amount, row.fee.currency) : null],
					["Paid on", formatDate(row.paid_on)],
					["Source", row.membership_source],
				]}
			/>

			{/* All three have to be true, and the DTO reports them separately for
			    exactly this reason: there is a certificate, this caller may have
			    it, and the type has a template to render it from. */}
			{row.certificate.available && row.certificate.may_print && row.certificate.configured && (
				<div className="mt-4 border-t border-card-line pt-4">
					<a
						href={certificateUrl(row.name)}
						className="inline-flex items-center justify-center rounded-xl border border-card-line bg-white px-5 py-2.5 text-[13px] font-bold text-slate-strong transition hover:border-blue hover:text-ink"
					>
						Certificate (PDF)
					</a>
				</div>
			)}

			{/* Above the two acts below rather than beside them: this is the one
			    that moves a membership along, and cancel and expire both end it. */}
			{owesAFee(row, canAct) && (
				<div className="mt-4 border-t border-card-line pt-4">
					<RecordPayment row={row} canAct={canAct} onRecorded={onActed} />
				</div>
			)}

			{canAct && (
				<div className="mt-4 flex flex-wrap gap-2 border-t border-card-line pt-4">
					{row.membership_status !== "Cancelled" && (
						<Button
							variant="quiet"
							onClick={() => {
								setCancelling(!cancelling);
								setFailure(null);
							}}
						>
							Cancel membership
						</Button>
					)}
					{row.membership_status === "Active" && row.lapsed && (
						<Button
							variant="quiet"
							disabled={busy}
							onClick={() => void perform(API.expireMembership, {})}
						>
							Expire
						</Button>
					)}
				</div>
			)}

			{cancelling && (
				<div className="mt-4">
					<label className="block">
						<span className="mb-1 block text-[11px] font-bold uppercase tracking-wide text-slate-faint">
							Why is this membership being cancelled?
						</span>
						<textarea
							value={reason}
							onChange={(event) => setReason(event.target.value)}
							rows={3}
							className="w-full rounded-xl border border-card-line px-3 py-2 text-[14px]"
						/>
					</label>
					<div className="mt-3 flex gap-2">
						<Button
							onClick={() => void perform(API.cancelMembership, { reason })}
							disabled={busy || !reason.trim()}
						>
							{busy ? "Recording…" : "Cancel membership"}
						</Button>
						<Button variant="ghost" onClick={() => setCancelling(false)} disabled={busy}>
							Keep it
						</Button>
					</div>
				</div>
			)}

			{failure && (
				<div className="mt-3">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}
		</div>
	);
}
