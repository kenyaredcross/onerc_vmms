import { useContext, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FrappeContext, useFrappeGetCall, type FrappeConfig } from "frappe-react-sdk";

import { EditableText } from "../content/Editable";
import { API, errorMessage, myCertificateUrl } from "../lib/api";
import { branchPath, formatDate, formatMoney } from "../lib/format";
import { Icon } from "../ui/icons";
import { HolderCard } from "./Profile";
import {
	Button,
	Card,
	Empty,
	ErrorNote,
	Notice,
	Spinner,
	StatusBadge,
	cx,
} from "./ui/kit";
import { Modal, useToast } from "./ui/overlays";
import type { MembershipRow, PricedType } from "./types";

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

	const types = useFrappeGetCall<{ message: { types: PricedType[] } }>(
		API.membershipTypes,
		undefined,
		"portal:membership_types",
	);

	const [detail, setDetail] = useState<PricedType | null>(null);

	const rows = data?.message ?? [];
	const priced = types.data?.message?.types ?? [];

	const held = rows.filter((row) => row.is_active);
	const pending = rows.filter((row) => !row.is_active);
	const holdsType = new Set(held.map((row) => row.membership_type));

	const join = (membershipType: string) =>
		navigate(`/join?path=member&type=${encodeURIComponent(membershipType)}`);

	return (
		<>
			<header className="mx-auto mb-9 max-w-[790px] text-center">
				<p className="text-[10px] font-bold uppercase tracking-[0.14em] text-blue">
					<EditableText k="portal.membership.eyebrow" fallback="Member account" />
				</p>
				<h1 className="mt-2.5 font-display text-[32px] font-extrabold leading-[1.08] tracking-[-0.04em] text-ink sm:text-[40px]">
					<EditableText k="portal.membership.heading" fallback="Manage your memberships" />
				</h1>
				<p className="mx-auto mt-2.5 max-w-[650px] text-[13px] leading-relaxed text-slate-body">
					<EditableText
						k="portal.membership.lead"
						fallback="Choose the membership that fits you, then manage every branch membership from one account."
					/>
				</p>
				{rows.length > 0 && (
					<a
						href="#your-memberships"
						className="mt-5 inline-flex rounded-lg bg-rail px-4 py-2.5 text-[12px] font-bold text-white transition hover:bg-rail-soft"
					>
						Go to your memberships
					</a>
				)}
			</header>

			{error && (
				<div className="mb-6">
					<ErrorNote>{errorMessage(error)}</ErrorNote>
				</div>
			)}

			{/* ------------------------------------------------------------- plans */}
			<section className="mb-14">
				<header className="mx-auto mb-6 max-w-[700px] text-center">
					<p className="text-[10px] font-bold uppercase tracking-[0.14em] text-blue">
						<EditableText k="portal.membership.plans.eyebrow" fallback="Membership options" />
					</p>
					<h2 className="mt-1.5 font-display text-[22px] font-extrabold tracking-[-0.03em] text-ink">
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
					<p className="mx-auto mt-2 max-w-[560px] text-[12px] leading-relaxed text-slate-body">
						{pending.length > 0
							? "Your application is with your branch. There is nothing to choose until they have decided on it."
							: "Review the benefits and eligibility guidance, then join through the branch that serves you."}
					</p>
				</header>

				{types.isLoading ? (
					<Spinner label="Loading membership types…" />
				) : priced.length === 0 ? (
					<Empty icon={Icon.card} title="No membership types published">
						Your society has not published any membership types yet. Ask your branch when they will
						be available.
					</Empty>
				) : (
					<div
						className={cx(
							"mx-auto grid w-full gap-3.5 sm:grid-cols-2",
							priced.length > 2 ? "max-w-[1040px] xl:grid-cols-4" : "max-w-[720px]",
						)}
					>
						{priced.map((plan) => (
							<PlanCard
								key={plan.membership_type}
								plan={plan}
								held={holdsType.has(plan.membership_type)}
								// Nothing to choose while something is undecided: choosing
								// would open a wizard that can only say the application is
								// already in.
								onJoin={pending.length > 0 ? undefined : () => join(plan.membership_type)}
								onDetails={() => setDetail(plan)}
							/>
						))}
					</div>
				)}

				{types.error && (
					<div className="mt-4">
						<ErrorNote>{errorMessage(types.error)}</ErrorNote>
					</div>
				)}

				{priced.length > 0 && (
					<div className="mx-auto mt-5 max-w-[1040px]">
						<Notice>
							<strong className="font-semibold text-ink">Joining another branch?</strong> A new
							branch application creates another membership record. Your existing memberships remain
							unchanged.
						</Notice>
					</div>
				)}
			</section>

			{/* ----------------------------------------------------------- records */}
			<section id="your-memberships" className="mx-auto w-full max-w-[1040px] scroll-mt-20">
				<header className="mb-4 flex flex-wrap items-end justify-between gap-4">
					<div>
						<p className="text-[10px] font-bold uppercase tracking-[0.14em] text-blue">
							Your account
						</p>
						<h2 className="mt-1.5 font-display text-[22px] font-extrabold tracking-[-0.03em] text-ink">
							Your memberships
						</h2>
						<p className="mt-1.5 text-[12px] text-slate-body">{summarise(held, pending)}</p>
					</div>
					{rows.length > 0 && (
						<div className="flex items-center gap-2">
							<span className="rounded-full bg-success-soft px-2.5 py-1.5 text-[11px] font-bold text-success">
								{held.length} active
							</span>
							<span className="rounded-full bg-surface px-2.5 py-1.5 text-[11px] font-bold text-slate-body">
								{rows.length} {rows.length === 1 ? "record" : "records"}
							</span>
						</div>
					)}
				</header>

				{isLoading ? (
					<Spinner label="Loading your memberships…" />
				) : rows.length === 0 ? (
					<div className="rounded-2xl border border-dashed border-slate-mute bg-white px-6 py-12 text-center">
						<span
							className="mx-auto mb-3.5 grid h-12 w-12 place-items-center rounded-full bg-blue-soft text-blue-press"
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
							Choose a membership type and branch above. Each application appears here as its own
							record — joining as a member is separate from volunteering, and you may do both.
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
									<p className="text-[10px] font-bold uppercase tracking-[0.12em] text-blue">
										Not active yet
									</p>
									<p className="mt-1 text-[12px] text-slate-body">
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

/** How a type's price reads, in the society's own currency and its own period. */
function price(plan: PricedType): { amount: string; period: string } {
	return {
		amount: plan.free ? "Free" : formatMoney(plan.amount, plan.currency),
		period: plan.is_lifetime
			? "one-off"
			: plan.duration_days === 365
				? "/ year"
				: plan.duration_days
					? `/ ${plan.duration_days} days`
					: "",
	};
}

function PlanCard({
	plan,
	held,
	onJoin,
	onDetails,
}: {
	plan: PricedType;
	held: boolean;
	onJoin?: () => void;
	onDetails: () => void;
}) {
	const { amount, period } = price(plan);

	return (
		<article className="p-card flex min-w-0 flex-col overflow-hidden">
			<span
				aria-hidden="true"
				className={cx("block h-1 w-full flex-none", held ? "bg-red" : "bg-rail/15")}
			/>

			<header className="flex items-start justify-between gap-3 px-5 pt-5">
				<h3 className="font-display text-[15px] font-bold leading-snug tracking-[-0.02em] text-ink">
					{plan.membership_type_name}
				</h3>
				{held && (
					<span className="flex-none rounded-full border border-success-line bg-success-soft px-2 py-1 text-[9.5px] font-bold text-success">
						You hold this
					</span>
				)}
			</header>

			<div className="mx-5 mt-4 border-t border-card-line pt-4">
				<strong className="font-display text-[24px] font-extrabold tracking-[-0.03em] text-ink">
					{amount}
				</strong>
				{period && <span className="ml-1.5 text-[11px] text-slate-body">{period}</span>}
				{plan.description && (
					<p className="mt-2 text-[11.5px] leading-relaxed text-slate-body">{plan.description}</p>
				)}
			</div>

			{plan.benefits.length > 0 && (
				<div className="mx-5 mt-4">
					<strong className="text-[9.5px] font-bold uppercase tracking-[0.1em] text-red">
						What is included
					</strong>
					<ul className="mt-2.5 space-y-2">
						{plan.benefits.map((benefit) => (
							<li key={benefit.key} className="flex items-start gap-2 text-[11.5px] text-ink">
								<span
									className="mt-px grid h-3.5 w-3.5 flex-none place-items-center rounded-full bg-red-soft text-[8px] font-bold text-red"
									aria-hidden="true"
								>
									✓
								</span>
								<span className="min-w-0 leading-snug">{benefit.label}</span>
							</li>
						))}
					</ul>
				</div>
			)}

			<div className="mx-5 mt-auto grid gap-1 border-t border-card-line pt-3.5 text-center text-[10px] text-muted">
				{plan.is_lifetime ? "Duration" : "Renewal"}
				<strong className="text-[11.5px] font-semibold text-ink">
					{plan.is_lifetime
						? "Lifetime membership"
						: plan.duration_days
							? `Runs for ${plan.duration_days} days, then renews`
							: "Renewable"}
				</strong>
				{plan.requires_approver && (
					<span className="text-[10px] text-muted">Branch approval required</span>
				)}
			</div>

			<div className="m-5 mt-3.5 grid gap-2 sm:grid-cols-2">
				<button
					type="button"
					onClick={onDetails}
					className="min-h-[36px] rounded-lg border border-card-line bg-white text-[11px] font-bold text-ink transition hover:border-blue"
				>
					View details
				</button>
				{onJoin ? (
					<button
						type="button"
						onClick={onJoin}
						className="min-h-[36px] rounded-lg bg-rail text-[11px] font-bold text-white transition hover:bg-rail-soft"
					>
						{/* The concept says "Join" whether or not the type is already
						    held — a second branch is a second record, which the note
						    under the grid explains once rather than on four buttons. */}
						Join
					</button>
				) : (
					<span className="grid min-h-[36px] place-items-center rounded-lg bg-surface text-[11px] font-semibold text-muted">
						Application in
					</span>
				)}
			</div>
		</article>
	);
}

function PlanDetail({ plan }: { plan: PricedType }) {
	const { amount, period } = price(plan);

	return (
		<div className="space-y-4">
			<div>
				<strong className="font-display text-[26px] font-extrabold tracking-[-0.03em] text-ink">
					{amount}
				</strong>
				{period && <span className="ml-1.5 text-[12px] text-slate-body">{period}</span>}
			</div>

			{plan.description && (
				<p className="text-[13px] leading-relaxed text-slate-body">{plan.description}</p>
			)}

			{plan.benefits.length > 0 && (
				<div>
					<strong className="text-[10px] font-bold uppercase tracking-[0.1em] text-red">
						What is included
					</strong>
					<ul className="mt-2.5 space-y-2">
						{plan.benefits.map((benefit) => (
							<li key={benefit.key} className="flex items-start gap-2 text-[12.5px] text-ink">
								<span
									className="mt-0.5 grid h-4 w-4 flex-none place-items-center rounded-full bg-red-soft text-[9px] font-bold text-red"
									aria-hidden="true"
								>
									✓
								</span>
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

	const renew = async () => {
		setBusy(true);
		setFailure(null);
		try {
			await call.post(API.renewMembership, { membership: row.name });
			toast("Membership renewed.");
			onChanged();
		} catch (renewError) {
			setFailure(errorMessage(renewError, "That membership could not be renewed."));
		} finally {
			setBusy(false);
		}
	};

	return (
		<Card className={cx("p-[22px]", !row.is_active && "border-dashed")}>
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
						{branchPath(row.geo_path) || row.geo_node || "—"}
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
