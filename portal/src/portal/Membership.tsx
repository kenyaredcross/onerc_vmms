import { useContext, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage, myCertificateUrl } from "../lib/api";
import { branchPath, formatDate, formatMoney } from "../lib/format";
import { Icon } from "../ui/icons";
import { PlanCards, planPrice } from "../ui/PlanCards";
import { HolderCard } from "./Profile";
import { ProofOfMembership } from "./ProofOfMembership";
import {
	Button,
	Card,
	ErrorNote,
	Notice,
	PageHead,
	Spinner,
	StatusBadge,
	cx,
} from "./ui/kit";
import { Modal, useToast } from "./ui/overlays";
import type { Declaration, MembershipRow, PricedType, RedProfile } from "./types";

/**
 * Every membership this person holds, and every one they could hold.
 *
 * **The buttons follow the server's own flags, never a state comparison here.**
 * `certificate_available` is answered by the same gate the download uses, and
 * `renewable` by the same predicate the renewal service uses. A screen that
 * decided for itself when to show "Renew" would eventually show it a moment
 * before or after the server would accept it, and the person clicking would get
 * a refusal they could not explain. So this file compares no dates and no
 * statuses.
 *
 * **A pending application is never called a membership somebody holds.**
 * `is_active` is the server's own answer — see `membership.status` — and the
 * split between the two lists here is that flag and nothing else.
 *
 * **Joining is still the registration wizard.** A plan card starts
 * `/join?path=member&type=…`, which asks for a branch, collects the society's
 * own questions and its declarations, and confirms before anything is written.
 * The prices on this page and in that wizard come from one endpoint, so they
 * cannot disagree.
 */
export default function Membership() {
	const navigate = useNavigate();

	const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: MembershipRow[] }>(
		API.myMemberships,
		undefined,
		"portal:my_memberships",
	);

	const types = useFrappeGetCall<{
		message: { types: PricedType[]; declarations: Declaration[] };
	}>(API.membershipTypes, undefined, "portal:membership_types");

	// Read only once somebody opens the proof form: the page's ordinary job is
	// listing memberships, and the identity block is the one thing on it that
	// needs the person's own record.
	const [detail, setDetail] = useState<PricedType | null>(null);
	const [proving, setProving] = useState<PricedType | null>(null);

	const profile = useFrappeGetCall<{ message: RedProfile }>(
		API.myProfile,
		undefined,
		proving ? "portal:my_profile" : null,
	);

	const rows = data?.message ?? [];
	const priced = types.data?.message?.types ?? [];

	const held = rows.filter((row) => row.is_active);
	const pending = rows.filter((row) => !row.is_active);
	const holdsType = new Set(held.map((row) => row.membership_type));

	const join = (membershipType: string) =>
		navigate(`/join?path=member&type=${encodeURIComponent(membershipType)}`);

	return (
		<>
			{/* The portal's own page head rather than a centred 40px hero. Every
			    other screen opens this way, and the cards below are what this page
			    is actually about: a heading competing with them for the eye was
			    the loudest thing on a page whose job is a comparison. */}
			<PageHead
				eyebrow={<EditableText k="portal.membership.eyebrow" fallback="Member account" />}
				title={<EditableText k="portal.membership.heading" fallback="Membership" />}
				lead={
					<EditableText
						k="portal.membership.lead"
						fallback="Choose the membership that fits you, then manage every branch membership from one account."
					/>
				}
				actions={
					rows.length > 0 ? (
						<a
							href="#your-memberships"
							className="inline-flex min-h-[38px] items-center rounded-lg border border-card-line bg-white px-3.5 text-[12.5px] font-semibold text-slate-strong transition hover:border-slate-faint hover:text-ink"
						>
							Go to your memberships
						</a>
					) : undefined
				}
			/>

			{error && (
				<div className="mb-6">
					<ErrorNote>{errorMessage(error)}</ErrorNote>
				</div>
			)}

			{/* ------------------------------------------------------------- plans */}
			<section className="mx-auto mb-12 w-full max-w-[1060px]">
				<header className="mb-5 max-w-[640px]">
					<p className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-muted">
						<EditableText k="portal.membership.plans.eyebrow" fallback="Membership types" />
					</p>
					<h2 className="mt-1.5 font-display text-[19px] font-bold tracking-[-0.02em] text-ink">
						{pending.length > 0 ? (
							<EditableText
								k="portal.membership.plans.heading.pending"
								fallback="What your society offers"
							/>
						) : (
							<EditableText
								k="portal.membership.plans.heading"
								fallback="Select a plan to become a member"
							/>
						)}
					</h2>
					<p className="mt-2 text-[12.5px] leading-relaxed text-slate-body">
						{pending.length > 0
							? "Your application is with your branch. There is nothing to choose until they have decided on it."
							: "Review the benefits and eligibility guidance, then join through the branch that serves you."}
					</p>
				</header>

				<PlanCards
					types={priced}
					loading={types.isLoading}
					held={[...holdsType]}
					columns={3}
					empty="Your society has not published any membership types yet. Ask your branch when they will be available."
					// The act, inside the price panel. Nothing to choose while
					// something is undecided: choosing would open a wizard that can
					// only say the application is already in.
					action={(plan) =>
						pending.length > 0 ? (
							<span className="grid min-h-[38px] place-items-center rounded-lg bg-white text-[12.5px] font-semibold text-muted">
								Application in
							</span>
						) : (
							<Button className="w-full" onClick={() => join(plan.membership_type)}>
								{/* The concept says "Join" whether or not the type is
								    already held — a second branch is a second record,
								    which the note under the grid explains once rather
								    than on four buttons. */}
								Join
							</Button>
						)
					}
					footer={(plan) => (
						<>
							<button
								type="button"
								onClick={() => setDetail(plan)}
								className="text-[11.5px] font-semibold text-blue underline-offset-2 transition hover:text-blue-hover hover:underline"
							>
								View details
							</button>
							{/* Claiming this plan rather than joining it, and deliberately
							    the quiet action of the two: a new applicant outnumbers
							    somebody proving an old card many times over. Never on one
							    they already hold, where there is nothing left to prove. */}
							{pending.length === 0 && !holdsType.has(plan.membership_type) && (
								<button
									type="button"
									onClick={() => setProving(plan)}
									className="text-[11.5px] font-semibold text-slate-body underline-offset-2 transition hover:text-ink hover:underline"
								>
									Already a member of this?
								</button>
							)}
						</>
					)}
				/>

				{types.error && (
					<div className="mt-4">
						<ErrorNote>{errorMessage(types.error)}</ErrorNote>
					</div>
				)}

				{priced.length > 0 && (
					<div className="mt-5">
						<Notice>
							<strong className="font-semibold text-ink">Joining another branch?</strong> A new
							branch application creates another membership record. Your existing memberships remain
							unchanged.
						</Notice>
					</div>
				)}
			</section>

			{/* ----------------------------------------------------------- records */}
			<section id="your-memberships" className="mx-auto w-full max-w-[1060px] scroll-mt-20">
				{/* The same header shape as the plans above it, so the page reads as
				    two sections of one thing rather than two designs meeting. */}
				<header className="mb-5 flex flex-wrap items-end justify-between gap-4">
					<div className="min-w-0 max-w-[640px]">
						<p className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-muted">
							Your account
						</p>
						<h2 className="mt-1.5 font-display text-[19px] font-bold tracking-[-0.02em] text-ink">
							Your memberships
						</h2>
						<p className="mt-2 text-[12.5px] leading-relaxed text-slate-body">
							{summarise(held, pending)}
						</p>
					</div>
					{rows.length > 0 && (
						<div className="flex items-center gap-2">
							<span className="rounded-full border border-success-line bg-success-soft px-3 py-1.5 text-[11px] font-semibold text-success">
								{held.length} active
							</span>
							<span className="rounded-full border border-card-line bg-white px-3 py-1.5 text-[11px] font-semibold text-slate-body">
								{rows.length} {rows.length === 1 ? "record" : "records"}
							</span>
						</div>
					)}
				</header>

				{isLoading ? (
					<Spinner label="Loading your memberships…" />
				) : rows.length === 0 ? (
					<div className="rounded-2xl border border-dashed border-card-line bg-white px-6 py-12 text-center">
						<span
							className="mx-auto mb-3.5 grid h-12 w-12 place-items-center rounded-full bg-surface text-slate-strong"
							aria-hidden="true"
						>
							<Icon.card size={20} />
						</span>
						<h3 className="font-display text-[16px] font-bold tracking-[-0.02em] text-ink">
							<EditableText
								k="portal.membership.empty"
								fallback="You do not hold a membership yet"
							/>
						</h3>
						<p className="mx-auto mt-2 max-w-[520px] text-[12.5px] leading-relaxed text-slate-body">
							Choose a membership type and branch above. Membership and volunteer registrations
							are separate, and you may complete both.
						</p>
					</div>
				) : (
					<div className="space-y-3.5">
						{held.map((row) => (
							<MembershipCard key={row.name} row={row} onChanged={() => void mutate()} />
						))}

						{/* The card itself, drawn only for a membership that is active:
						    the endpoint returns nothing for one still under review, and
						    this renders nothing when it does. */}
						{held.length > 0 && <HolderCard kind="member" />}

						{pending.length > 0 && (
							<>
								<div className="pt-4">
									<p className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-muted">
										Not active yet
									</p>
									<p className="mt-1.5 text-[12.5px] text-slate-body">
										Applications still waiting for payment or branch approval.
									</p>
								</div>
								{pending.map((row) => (
									<MembershipCard key={row.name} row={row} onChanged={() => void mutate()} />
								))}
							</>
						)}
					</div>
				)}
			</section>

			<Modal
				open={Boolean(detail)}
				onClose={() => setDetail(null)}
				title={detail?.membership_type_name ?? ""}
				description="Membership option"
				footer={
					detail && pending.length === 0 ? (
						<>
							<Button tone="quiet" onClick={() => setDetail(null)}>
								Close
							</Button>
							<Button onClick={() => join(detail.membership_type)}>Join this membership</Button>
						</>
					) : (
						<Button tone="quiet" onClick={() => setDetail(null)}>
							Close
						</Button>
					)
				}
			>
				{detail && <PlanDetail plan={detail} />}
			</Modal>

			{/* Wide, because it is a form rather than a summary: a date, a second
			    date, four fields and an upload do not read in a column. */}
			<Modal
				open={Boolean(proving)}
				onClose={() => setProving(null)}
				size="lg"
				title="Already a member?"
				description={
					proving
						? `Ask your branch to recognise your ${proving.membership_type_name}`
						: undefined
				}
			>
				{proving && (
					<ProofOfMembership
						plan={proving}
						profile={profile.data?.message ?? null}
						declarations={types.data?.message?.declarations ?? []}
						onCancel={() => setProving(null)}
						onDone={() => {
							setProving(null);
							void mutate();
						}}
					/>
				)}
			</Modal>
		</>
	);
}

function summarise(held: MembershipRow[], pending: MembershipRow[]): string {
	if (held.length === 0 && pending.length === 0) {
		return "Nothing on your account yet.";
	}
	const branches = new Set([...held, ...pending].map((row) => row.geo_node ?? row.name));
	const parts = [
		`${held.length} active ${held.length === 1 ? "membership" : "memberships"}`,
		pending.length > 0
			? `${pending.length} awaiting payment or approval`
			: null,
	].filter(Boolean);
	return `${parts.join(" and ")} across ${branches.size} ${branches.size === 1 ? "branch" : "branches"}`;
}

/* -------------------------------------------------------------------- plans */

function PlanDetail({ plan }: { plan: PricedType }) {
	const { amount, period, monthly } = planPrice(plan);

	return (
		<div className="space-y-4">
			<div>
				<strong className="font-display text-[26px] font-extrabold tracking-[-0.03em] text-ink">
					{amount}
				</strong>
				{period && <span className="ml-1.5 text-[12px] text-slate-body">{period}</span>}
				{monthly && (
					<p className="mt-1.5 text-[12px] font-medium text-blue-press">{monthly}</p>
				)}
			</div>

			{plan.description && (
				<p className="text-[13px] leading-relaxed text-slate-body">{plan.description}</p>
			)}

			{plan.benefits.length > 0 && (
				<div>
					<strong className="text-[10px] font-bold uppercase tracking-[0.1em] text-rail-label">
						What is included
					</strong>
					<ul className="mt-2.5 space-y-2">
						{plan.benefits.map((benefit) => (
							<li key={benefit.key} className="flex items-start gap-2.5 text-[12.5px] text-ink">
								<Icon.check size={14} className="mt-[3px] flex-none text-success" />
								<span className="min-w-0">
									<span className="block leading-snug">{benefit.label}</span>
									{benefit.description && (
										<span className="mt-0.5 block text-[11.5px] text-muted">
											{benefit.description}
										</span>
									)}
								</span>
							</li>
						))}
					</ul>
				</div>
			)}

			<div className="rounded-xl bg-canvas px-4 py-3 text-[12px] text-slate-body">
				<span className="block text-[10px] font-bold uppercase tracking-[0.09em] text-rail-label">
					{plan.is_lifetime ? "Duration" : "Renewal"}
				</span>
				<span className="mt-1 block font-semibold text-ink">
					{plan.is_lifetime
						? "Lifetime membership, with no renewals"
						: plan.duration_days
							? `Runs for ${plan.duration_days} days, then renews`
							: "Renewable"}
				</span>
				{plan.requires_approver && (
					<span className="mt-1.5 block">
						A branch approver decides on this application before it becomes active.
					</span>
				)}
			</div>
		</div>
	);
}

/* ------------------------------------------------------------------ records */

function MembershipCard({ row, onChanged }: { row: MembershipRow; onChanged: () => void }) {
	const { call } = useContext(FrappeContext) as FrappeConfig;
	const toast = useToast();
	const [busy, setBusy] = useState(false);
	const [failure, setFailure] = useState<string | null>(null);
	const [renewal, setRenewal] = useState<{ membership_status: string; payment?: { transaction?: string | null; message?: string } } | null>(null);

	const renew = async () => {
		setBusy(true);
		setFailure(null);
		try {
			const answer = await call.post<{ message: { membership_status: string; payment?: { transaction?: string | null; message?: string } } }>(API.renewMembership, { membership: row.name });
			setRenewal(answer.message);
			toast(answer.message.membership_status === "Active" ? "Membership renewed." : "Renewal application submitted.");
			onChanged();
		} catch (renewError) {
			setFailure(errorMessage(renewError, "That membership could not be renewed."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card className={cx("rounded-2xl p-[22px]", !row.is_active && "border-dashed")}>
			<div className="flex flex-wrap items-start gap-3.5">
				<span
					className="grid h-[45px] w-[45px] flex-none place-items-center rounded-xl bg-cal-cert-soft text-cal-cert"
					aria-hidden="true"
				>
					<Icon.card size={20} />
				</span>

				<div className="min-w-0 flex-1">
					<div className="flex flex-wrap items-center gap-2.5">
						<strong className="font-display text-[15px] font-bold tracking-[-0.02em] text-ink">
							{row.membership_type_name || row.membership_type}
						</strong>
						{/* The server's own word for the state, never re-derived here. */}
						<StatusBadge state={row.membership_status} />
						{row.is_lifetime && (
							<span className="rounded-full bg-surface px-2 py-1 text-[10px] font-bold text-slate-body">
								Lifetime
							</span>
						)}
					</div>
					<p className="mt-1.5 text-[12px] text-slate-body">
						{branchPath(row.geo_path) || row.geo_node || "Not available"}
					</p>
				</div>

				{/* Full width below the title on a phone: a certificate button beside
				    a type name at 390px squeezes both into two lines each. */}
				<div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
					{row.certificate_available && (
						<a
							href={myCertificateUrl(row.name)}
							className="inline-flex min-h-[34px] items-center gap-2 rounded-full border border-card-line bg-white px-3.5 text-[11.5px] font-bold text-ink transition hover:border-blue"
						>
							<Icon.award size={14} />
							View &amp; print certificate
						</a>
					)}
					{row.renewable && (
						<Button onClick={renew} busy={busy} disabled={busy}>
							Renew
						</Button>
					)}
				</div>
			</div>

			{failure && (
				<div className="mt-4">
					<ErrorNote>{failure}</ErrorNote>
				</div>
			)}
			{renewal && (
				<div className="mt-4 rounded-xl border border-card-line bg-surface p-4 text-[13px] text-ink" role="status">
					<p className="font-semibold">Renewal application: {renewal.membership_status}</p>
					{renewal.payment?.message && <p className="mt-2 whitespace-pre-line">{renewal.payment.message}</p>}
					{renewal.payment?.transaction && <p className="mt-2 font-mono text-[11px]">Reference {renewal.payment.transaction}</p>}
				</div>
			)}

			<dl className="mt-5 grid gap-4 border-t border-card-line pt-4 sm:grid-cols-2 lg:grid-cols-4">
				<Field
					label="Valid from"
					value={row.is_active || row.valid_from ? formatDate(row.valid_from) : "Not active"}
				/>
				<Field
					label="Valid to"
					value={
						row.is_lifetime
							? "No expiry"
							: row.is_active || row.valid_to
								? formatDate(row.valid_to)
								: "Not active"
					}
				/>
				{/* The society's own currency travels with the amount, so a free type
				    reads "Free" rather than a bare zero in nobody's currency. */}
				<Field
					label="Fee"
					value={
						!row.fee || row.fee.amount === 0
							? "Free"
							: formatMoney(row.fee.amount, row.fee.currency)
					}
				/>
				<Field label="Membership ID" value={row.name} mono />
			</dl>

			{/* The two halves of activation, shown as they are: a person whose
			    payment cleared but whose approval has not is entitled to know which
			    of the two they are waiting on. */}
			<div className="mt-4 flex flex-wrap gap-2 border-t border-card-line pt-4">
				<Progress done={row.payment_settled} label="Payment" />
				<Progress
					done={row.approval_settled}
					label={row.requires_approver ? "Approval" : "Approval not required"}
					settledWord={row.requires_approver ? undefined : ""}
				/>
				{row.payment_receipt && (
					<span className="inline-flex items-center rounded-full border border-card-line bg-white px-3 py-1.5 text-[11px] font-semibold text-slate-body">
						Receipt {row.payment_receipt}
					</span>
				)}
			</div>
		</Card>
	);
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
	return (
		<div className="min-w-0">
			<dt className="text-[9.5px] font-bold uppercase tracking-[0.08em] text-rail-label">{label}</dt>
			<dd
				className={cx(
					"mt-1.5 truncate",
					mono ? "font-mono text-[11.5px] text-ink" : "text-[12px] font-semibold text-ink",
				)}
			>
				{value}
			</dd>
		</div>
	);
}

function Progress({
	done,
	label,
	settledWord,
}: {
	done: boolean;
	label: string;
	/** Pass `""` where the label already says the whole thing. */
	settledWord?: string;
}) {
	const tail = settledWord !== undefined ? settledWord : done ? " settled" : " pending";

	return (
		<span
			className={cx(
				"inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-semibold",
				done
					? "border-success-line bg-success-soft text-success"
					: "border-card-line bg-white text-slate-body",
			)}
		>
			<span
				className={cx("h-1.5 w-1.5 rounded-full", done ? "bg-success-dot" : "bg-slate-faint")}
				aria-hidden="true"
			/>
			{label}
			{tail}
		</span>
	);
}
