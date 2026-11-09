import { useContext, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { API, errorMessage, licenceCopyUrl } from "../lib/api";
import { formatDate } from "../lib/format";
import { Combo, Field, PrivateUpload, TextArea, TextInput } from "../ui/form";
import { GeoSelects } from "../ui/GeoSelects";
import { Icon } from "../ui/icons";
import { MetricCard } from "../ui/MetricCard";
import {
	Avatar,
	Button,
	Card,
	Cell,
	Empty,
	ErrorNote,
	PageHeading,
	Pill,
	Row,
	SectionTitle,
	Skeleton,
	Spinner,
	Table,
	cx,
} from "../ui/primitives";
import type { GeoNode, SurgeEntry, SurgeRoster, SurgeStanding } from "../portal/types";

/**
 * The surge roster: professionals a branch has checked and can call on.
 *
 * A coordinator puts somebody on it by hand, under one profession, after
 * seeing their professional licence. The server records what was checked and
 * who checked it, and works out each person's standing every time it is read:
 * a licence past its date, or a volunteer no longer active, shows as needing
 * review without anybody having to notice.
 *
 * One screen, reached from two places — the People register and Operations —
 * because the same list answers "who are my professionals" and "who can I send".
 */

const STANDING: Record<SurgeStanding, { label: string; tone: string }> = {
	ready: { label: "Ready", tone: "bg-emerald-50 text-emerald-800" },
	expiring: { label: "Licence expires soon", tone: "bg-amber-50 text-amber-800" },
	licence_expired: { label: "Licence expired", tone: "bg-danger-soft text-danger" },
	volunteer_not_active: { label: "Not an active volunteer", tone: "bg-danger-soft text-danger" },
	stood_down: { label: "Stood down", tone: "bg-surface text-slate-strong" },
};

export function SurgeStandingBadge({ standing }: { standing: SurgeStanding }) {
	const shown = STANDING[standing];

	return (
		<span
			className={cx(
				"inline-flex items-center whitespace-nowrap rounded-full px-3 py-1 text-[11.5px] font-semibold",
				shown.tone,
			)}
		>
			{shown.label}
		</span>
	);
}

export function SurgeRosterPeople() {
	return (
		<SurgeRosterPage
			trail={[{ label: "People", to: "/admin/people" }, { label: "Surge roster" }]}
		/>
	);
}

export function SurgeRosterOperations() {
	return (
		<SurgeRosterPage
			trail={[{ label: "Operations", to: "/admin/deployments" }, { label: "Surge roster" }]}
		/>
	);
}

function SurgeRosterPage({ trail }: { trail: Array<{ label: string; to?: string }> }) {
	const [profession, setProfession] = useState("");
	const [search, setSearch] = useState("");
	const [chain, setChain] = useState<GeoNode[]>([]);
	const [adding, setAdding] = useState(false);
	const geoNode = chain.length > 0 ? chain[chain.length - 1].name : undefined;

	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: SurgeRoster }>(
		API.surgeRoster,
		{ profession: profession || undefined, search: search.trim() || undefined, geo_node: geoNode },
		`admin:surge:${profession}:${search.trim()}:${geoNode ?? ""}`,
	);

	const roster = data?.message;
	const figures = roster?.figures;
	const groups = useMemo(() => {
		const byProfession = new Map<string, NonNullable<typeof roster>["rows"]>();

		for (const row of roster?.rows ?? []) {
			byProfession.set(row.profession, [...(byProfession.get(row.profession) ?? []), row]);
		}

		return [...byProfession.entries()];
	}, [roster]);

	return (
		<>
			<PageHeading
				title="Surge roster"
				lead="Professionals in your area whose licence has been checked, grouped by profession."
				trail={trail}
				actions={
					<Button onClick={() => setAdding((was) => !was)} variant={adding ? "ghost" : "primary"}>
						{adding ? "Close" : "Add a volunteer"}
					</Button>
				}
			/>

			{adding && (
				<AddFromRegister
					onAdded={() => {
						setAdding(false);
						void mutate();
					}}
				/>
			)}

			<div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
				{[
					{ label: "On the roster", value: figures?.people, note: "People with a checked licence", icon: Icon.people },
					{ label: "Ready", value: figures?.ready, note: "Active, licence valid", icon: Icon.check },
					{ label: "Licence expires soon", value: figures?.expiring, note: "Within 60 days", icon: Icon.calendar },
					{ label: "Needs review", value: figures?.needs_review, note: "Licence expired or not active", icon: Icon.info },
				].map((tile) => (
					<MetricCard
						key={tile.label}
						label={tile.label}
						icon={<tile.icon size={19} />}
						value={isLoading && !figures ? <Skeleton className="h-7 w-16" /> : (tile.value ?? 0).toLocaleString()}
						note={tile.note}
					/>
				))}
			</div>

			<Card className="mb-5">
				<div className="flex flex-wrap items-center gap-2.5">
					<div className="relative min-w-[220px] flex-1">
						<span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-faint">
							<Icon.search size={15} />
						</span>
						<input
							type="search"
							value={search}
							onChange={(event) => setSearch(event.target.value)}
							placeholder="Search by name or volunteer number"
							aria-label="Search by name or volunteer number"
							className="w-full rounded-full border border-card-line bg-white py-2.5 pl-11 pr-4 text-[13.5px] outline-none transition placeholder:text-slate-faint focus:border-blue"
						/>
					</div>
				</div>

				{(roster?.professions.length ?? 0) > 0 && (
					<div className="mt-4 flex flex-wrap gap-1.5" role="group" aria-label="Profession">
						<ProfessionChip active={!profession} onClick={() => setProfession("")}>
							All professions
						</ProfessionChip>
						{roster?.professions.map((group) => (
							<ProfessionChip
								key={group.profession}
								active={profession === group.profession}
								onClick={() => setProfession(profession === group.profession ? "" : group.profession)}
							>
								{group.profession}
								<span className="tabular text-[11px] opacity-75">
									{group.ready}/{group.count}
								</span>
							</ProfessionChip>
						))}
					</div>
				)}

				<div className="mt-5 border-t border-card-line pt-5">
					<span className="block text-[12.5px] font-semibold text-slate-strong">Branch</span>
					<span className="mb-2 block text-[11.5px] text-slate-faint">Includes all areas below this branch.</span>
					<GeoSelects scoped chain={chain} onChain={setChain} idPrefix="surge" />
				</div>
			</Card>

			{isLoading && <Spinner label="Loading the roster…" />}
			{error && <ErrorNote>{errorMessage(error)}</ErrorNote>}

			{!isLoading && !error && groups.length === 0 && (
				<Empty title="Nobody is on the surge roster yet">
					Open a volunteer's record, or use Add a volunteer, to put a professional on the roster after checking
					their licence.
				</Empty>
			)}

			{groups.map(([name, rows]) => (
				<Card key={name} className="mb-5">
					<div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
						<SectionTitle>{name}</SectionTitle>
						<span className="text-[12px] text-muted">
							{rows.filter((row) => row.ready).length} of {rows.length} ready
						</span>
					</div>
					<Table head={["Volunteer", "Licence", "Valid until", "Checked", "Standing", ""]}>
						{rows.map((row) => (
							<Row
								key={row.entry}
								to={`/admin/registry/volunteer/${encodeURIComponent(row.volunteer)}`}
								label={`Open ${row.full_name ?? row.volunteer}`}
							>
								<Cell>
									<span className="flex items-center gap-3">
										<Avatar name={row.full_name} photo={row.photo} size={34} />
										<span className="min-w-0">
											<span className="block truncate font-semibold text-ink">{row.full_name ?? row.volunteer}</span>
											<span className="block truncate text-[12px] text-muted">
												{[row.branch, row.phone].filter(Boolean).join(" · ")}
											</span>
										</span>
									</span>
								</Cell>
								<Cell className="text-muted">
									<span className="block font-mono text-[12px] text-ink">{row.licence_number}</span>
									<span className="block text-[12px]">{row.issuing_body}</span>
								</Cell>
								<Cell className="text-muted">{row.licence_expiry ? formatDate(row.licence_expiry) : "No expiry"}</Cell>
								<Cell className="text-muted">
									<span className="block">{formatDate(row.checked_on)}</span>
									{row.checked_by && <span className="block text-[12px]">{row.checked_by}</span>}
								</Cell>
								<Cell>
									<SurgeStandingBadge standing={row.standing} />
								</Cell>
								<Cell className="text-right">
									<Link
										to={`/admin/registry/volunteer/${encodeURIComponent(row.volunteer)}`}
										className="text-[12.5px] font-bold text-ink hover:underline"
									>
										Open
									</Link>
								</Cell>
							</Row>
						))}
					</Table>
				</Card>
			))}
		</>
	);
}

function ProfessionChip({
	active,
	onClick,
	children,
}: {
	active: boolean;
	onClick: () => void;
	children: ReactNode;
}) {
	return (
		<button
			type="button"
			aria-pressed={active}
			onClick={onClick}
			className={cx(
				"inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12.5px] font-semibold transition",
				active
					? "border-blue bg-blue-soft text-blue-press"
					: "border-card-line bg-white text-slate-strong hover:border-blue hover:text-ink",
			)}
		>
			{children}
		</button>
	);
}

/** Find an active volunteer in the register, then record their licence. */
function AddFromRegister({ onAdded }: { onAdded: () => void }) {
	const [term, setTerm] = useState("");
	const [chosen, setChosen] = useState<{ volunteer: string; full_name: string | null; profession?: string | null } | null>(
		null,
	);
	const asked = term.trim();

	const found = useFrappeGetCall<{
		message: { volunteers: Array<{ volunteer: string; full_name: string | null; photo: string | null; profession?: string | null; on_surge_roster?: boolean }> };
	}>(
		API.findVolunteers,
		{ status: "Active", search: asked, limit: 8 },
		asked.length >= 2 && !chosen ? `admin:surge:find:${asked}` : null,
	);

	return (
		<Card className="mb-5">
			<SectionTitle>Add a volunteer to the surge roster</SectionTitle>

			{chosen ? (
				<>
					<p className="mb-4 text-[13px] text-muted">
						<span className="font-semibold text-ink">{chosen.full_name ?? chosen.volunteer}</span> ·{" "}
						<button type="button" className="underline underline-offset-2" onClick={() => setChosen(null)}>
							Choose someone else
						</button>
					</p>
					<SurgeForm
						volunteer={chosen.volunteer}
						suggestedProfession={chosen.profession ?? ""}
						onDone={onAdded}
						onCancel={() => setChosen(null)}
					/>
				</>
			) : (
				<>
					<Field label="Find an active volunteer" htmlFor="surge-find">
						<TextInput id="surge-find" value={term} onChange={setTerm} placeholder="Name or volunteer number" />
					</Field>
					{found.isLoading && <Spinner label="Searching…" />}
					{(found.data?.message?.volunteers ?? []).length > 0 && (
						<ul className="mt-3 divide-y divide-card-line rounded-xl border border-card-line">
							{found.data?.message?.volunteers.map((row) => (
								<li key={row.volunteer}>
									<button
										type="button"
										onClick={() => setChosen(row)}
										className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-canvas"
									>
										<Avatar name={row.full_name} photo={row.photo} size={30} />
										<span className="min-w-0 flex-1">
											<span className="block truncate text-[13.5px] font-semibold text-ink">
												{row.full_name ?? row.volunteer}
											</span>
											<span className="block truncate text-[12px] text-muted">
												{[row.volunteer, row.profession].filter(Boolean).join(" · ")}
											</span>
										</span>
										{row.on_surge_roster && <Pill tone="signal">On the roster</Pill>}
									</button>
								</li>
							))}
						</ul>
					)}
					{asked.length >= 2 && !found.isLoading && (found.data?.message?.volunteers ?? []).length === 0 && (
						<p className="mt-3 text-[13px] text-muted">No active volunteer in your area matches that.</p>
					)}
				</>
			)}
		</Card>
	);
}

/**
 * The licence check, as a form. Used to add somebody and to record a renewed licence.
 *
 * The button is never greyed out: pressed with something missing, it says what
 * is missing and moves to it.
 */
function SurgeForm({
	volunteer,
	entry,
	suggestedProfession = "",
	onDone,
	onCancel,
}: {
	volunteer: string;
	/** Present when recording a renewed licence for an existing entry. */
	entry?: SurgeEntry;
	suggestedProfession?: string;
	onDone: (surge: SurgeEntry[]) => void;
	onCancel: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const options = useFrappeGetCall<{ message: { professions?: string[] } }>(
		API.identityOptions,
		undefined,
		entry ? null : "admin:surge:professions",
	);
	const [profession, setProfession] = useState(entry?.profession ?? suggestedProfession);
	const [number, setNumber] = useState("");
	const [issuer, setIssuer] = useState(entry?.issuing_body ?? "");
	const [expiry, setExpiry] = useState("");
	const [copy, setCopy] = useState("");
	const [notes, setNotes] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const id = entry ? `surge-${entry.entry}` : `surge-new-${volunteer}`;

	const professions = (options.data?.message?.professions ?? []).filter((name) => name !== "Other");
	const missing = [
		!entry && !profession.trim() && { field: `${id}-profession`, label: "Choose the profession" },
		!number.trim() && { field: `${id}-number`, label: "Enter the licence number" },
		!issuer.trim() && { field: `${id}-issuer`, label: "Enter who issued the licence" },
	].filter(Boolean) as Array<{ field: string; label: string }>;

	const submit = async () => {
		if (missing.length > 0) {
			setFailure(missing[0].label);
			document.getElementById(missing[0].field)?.focus();
			return;
		}

		setBusy(true);
		setFailure(null);

		try {
			const answer = entry
				? await call.post<{ message: { surge: SurgeEntry[] } }>(API.renewSurgeLicence, {
						name: entry.entry,
						licence_number: number,
						issuing_body: issuer,
						licence_expiry: expiry || undefined,
						licence_document: copy || undefined,
					})
				: await call.post<{ message: { surge: SurgeEntry[] } }>(API.addToSurgeRoster, {
						volunteer,
						profession,
						licence_number: number,
						issuing_body: issuer,
						licence_expiry: expiry || undefined,
						licence_document: copy || undefined,
						notes: notes || undefined,
					});
			onDone(answer.message.surge);
		} catch (saveError) {
			setFailure(errorMessage(saveError, "The licence check was not recorded. Try again."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<div className="space-y-4">
			{!entry && (
				<Field label="Profession" required htmlFor={`${id}-profession`}>
					<Combo
						id={`${id}-profession`}
						value={profession}
						onChange={setProfession}
						options={professions}
						placeholder="Start typing a profession…"
					/>
				</Field>
			)}
			<div className="grid gap-4 sm:grid-cols-2">
				<Field label="Licence number" required htmlFor={`${id}-number`}>
					<TextInput id={`${id}-number`} value={number} onChange={setNumber} />
				</Field>
				<Field label="Issued by" required htmlFor={`${id}-issuer`} hint="For example, the Nursing Council of Kenya.">
					<TextInput id={`${id}-issuer`} value={issuer} onChange={setIssuer} />
				</Field>
				<Field label="Valid until" htmlFor={`${id}-expiry`} hint="Leave empty if the licence does not expire.">
					<TextInput id={`${id}-expiry`} type="date" value={expiry} onChange={setExpiry} />
				</Field>
				<Field label="Copy of the licence" htmlFor={`${id}-copy`}>
					<PrivateUpload id={`${id}-copy`} value={copy} onChange={setCopy} choose="Attach the licence" />
				</Field>
			</div>
			{!entry && (
				<Field label="Notes" htmlFor={`${id}-notes`}>
					<TextArea id={`${id}-notes`} value={notes} onChange={setNotes} rows={2} />
				</Field>
			)}
			<p className="text-[12px] text-slate-faint">You are recorded as the person who checked this licence, today.</p>
			{failure && <ErrorNote>{failure}</ErrorNote>}
			<div className="flex gap-2">
				<Button onClick={() => void submit()} busy={busy} held={missing.length > 0}>
					{entry ? "Record the renewed licence" : "Add to the surge roster"}
				</Button>
				<Button variant="ghost" onClick={onCancel} disabled={busy}>
					Cancel
				</Button>
			</div>
		</div>
	);
}

/**
 * The surge roster on one volunteer's record: what was checked, and the acts.
 *
 * `canAct` is the server's answer to whether this reader may change the
 * volunteer; without it the card only reads.
 */
export function SurgeCard({
	volunteer,
	entries,
	canAct,
	volunteerActive,
	suggestedProfession,
	onChanged,
}: {
	volunteer: string;
	entries: SurgeEntry[];
	canAct: boolean;
	volunteerActive: boolean;
	suggestedProfession?: string | null;
	onChanged: () => void;
}) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const [adding, setAdding] = useState(false);
	const [renewing, setRenewing] = useState<string | null>(null);
	const [standingDown, setStandingDown] = useState<string | null>(null);
	const [reason, setReason] = useState("");
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const [showPast, setShowPast] = useState(false);

	const current = entries.filter((entry) => entry.status === "Active");
	const past = entries.filter((entry) => entry.status !== "Active");

	const standDown = async (entry: SurgeEntry) => {
		if (!reason.trim()) {
			setFailure("Give a reason for standing this person down.");
			document.getElementById(`surge-reason-${entry.entry}`)?.focus();
			return;
		}

		setBusy(true);
		setFailure(null);

		try {
			await call.post(API.standDownFromSurge, { name: entry.entry, reason });
			setStandingDown(null);
			setReason("");
			onChanged();
		} catch (actError) {
			setFailure(errorMessage(actError, "That change was not recorded."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card className="mb-5">
			<div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
				<SectionTitle>Surge roster</SectionTitle>
				{canAct && volunteerActive && !adding && (
					<Button variant="quiet" onClick={() => setAdding(true)}>
						Add to the surge roster
					</Button>
				)}
			</div>

			{current.length === 0 && !adding && (
				<p className="text-[13px] text-muted">Not on the surge roster.</p>
			)}

			{current.map((entry) => (
				<div key={entry.entry} className="mb-3 rounded-xl border border-card-line px-4 py-3.5">
					<div className="flex flex-wrap items-center justify-between gap-2">
						<span className="text-[14px] font-semibold text-ink">{entry.profession}</span>
						<SurgeStandingBadge standing={entry.standing} />
					</div>
					<dl className="mt-2 grid gap-x-6 gap-y-1 text-[12.5px] text-muted sm:grid-cols-2">
						<div>
							<dt className="inline">Licence: </dt>
							<dd className="inline font-mono text-ink">{entry.licence_number}</dd>
						</div>
						<div>
							<dt className="inline">Issued by: </dt>
							<dd className="inline">{entry.issuing_body}</dd>
						</div>
						<div>
							<dt className="inline">Valid until: </dt>
							<dd className="inline">{entry.licence_expiry ? formatDate(entry.licence_expiry) : "No expiry"}</dd>
						</div>
						<div>
							<dt className="inline">Checked: </dt>
							<dd className="inline">
								{formatDate(entry.checked_on)}
								{entry.checked_by ? ` by ${entry.checked_by}` : ""}
							</dd>
						</div>
					</dl>
					{entry.notes && <p className="mt-2 text-[12.5px] text-muted">{entry.notes}</p>}
					{entry.licence_document && (
						<a
							href={licenceCopyUrl(entry.entry, true)}
							target="_blank"
							rel="noreferrer"
							className="mt-2 inline-block text-[12.5px] font-semibold text-blue-press underline underline-offset-2"
						>
							View the licence
						</a>
					)}

					{canAct && renewing !== entry.entry && standingDown !== entry.entry && (
						<div className="mt-3 flex flex-wrap gap-2">
							<Button variant="quiet" onClick={() => setRenewing(entry.entry)}>
								Record a renewed licence
							</Button>
							<Button
								variant="ghost"
								onClick={() => {
									setStandingDown(entry.entry);
									setReason("");
									setFailure(null);
								}}
							>
								Stand down
							</Button>
						</div>
					)}

					{renewing === entry.entry && (
						<div className="mt-4 border-t border-card-line pt-4">
							<SurgeForm
								volunteer={volunteer}
								entry={entry}
								onDone={() => {
									setRenewing(null);
									onChanged();
								}}
								onCancel={() => setRenewing(null)}
							/>
						</div>
					)}

					{standingDown === entry.entry && (
						<div className="mt-4 border-t border-card-line pt-4">
							<Field label="Why is this person being stood down?" required htmlFor={`surge-reason-${entry.entry}`}>
								<TextArea id={`surge-reason-${entry.entry}`} value={reason} onChange={setReason} rows={2} />
							</Field>
							{failure && (
								<div className="mt-3">
									<ErrorNote>{failure}</ErrorNote>
								</div>
							)}
							<div className="mt-3 flex gap-2">
								<Button variant="danger" onClick={() => void standDown(entry)} busy={busy} held={!reason.trim()}>
									Stand down
								</Button>
								<Button variant="ghost" onClick={() => setStandingDown(null)} disabled={busy}>
									Cancel
								</Button>
							</div>
						</div>
					)}
				</div>
			))}

			{adding && (
				<div className="rounded-xl border border-card-line px-4 py-4">
					<SurgeForm
						volunteer={volunteer}
						suggestedProfession={suggestedProfession && suggestedProfession !== "Other" ? suggestedProfession : ""}
						onDone={() => {
							setAdding(false);
							onChanged();
						}}
						onCancel={() => setAdding(false)}
					/>
				</div>
			)}

			{past.length > 0 && (
				<div className="mt-3">
					<button
						type="button"
						aria-expanded={showPast}
						onClick={() => setShowPast((was) => !was)}
						className="text-[12.5px] font-semibold text-slate-faint underline underline-offset-2"
					>
						{showPast ? "Hide" : "Show"} earlier entries ({past.length})
					</button>
					{showPast && (
						<ul className="mt-2 space-y-2">
							{past.map((entry) => (
								<li key={entry.entry} className="text-[12.5px] text-muted">
									<span className="font-semibold text-ink">{entry.profession}</span> · stood down{" "}
									{formatDate(entry.stood_down_on)}
									{entry.stood_down_by ? ` by ${entry.stood_down_by}` : ""}
									{entry.stood_down_reason ? `: ${entry.stood_down_reason}` : ""}
								</li>
							))}
						</ul>
					)}
				</div>
			)}
		</Card>
	);
}
